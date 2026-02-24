import tkinter as tk
from tkinter import ttk, messagebox, filedialog, scrolledtext
import threading
import time
import sys
import os
import json
import re
import subprocess
import gc
import random
import shutil
if os.name == 'nt':
    import msvcrt
else:
    msvcrt = None
import importlib.util
import faulthandler
import traceback
import logging
import hashlib
import atexit
from typing import Optional, Dict, Any, List

# ---------------------------------------------------------------------------
# DIAGNOSTICS — captures Python exceptions (all threads), native C crashes
# (PortAudio segfaults/access violations), and Tkinter callback errors.
# Log file: debug.log next to this script.  Open it after a crash.
# ---------------------------------------------------------------------------
_LOG_PATH  = None
_log_file  = None  # kept open so faulthandler can write to it

def _setup_diagnostics():
    """Call once at startup, before the Tk window is created."""
    global _log_file, _LOG_PATH
    _LOG_PATH = os.path.join(APP_DATA_ROOT, "debug.log")

    # 1. File-based logger (append so history survives across runs)
    logging.basicConfig(
        filename=_LOG_PATH,
        level=logging.DEBUG,
        format="%(asctime)s [%(threadName)-16s] %(levelname)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    logging.info("=" * 60)
    logging.info("App starting — Python %s", sys.version.split()[0])

    # 2. faulthandler: writes a Python stack trace on ANY native crash
    #    (segfault, PortAudio access violation, etc.)
    _log_file = open(_LOG_PATH, "a", encoding="utf-8")
    faulthandler.enable(file=_log_file, all_threads=True)
    logging.info("faulthandler enabled → %s", _LOG_PATH)

    # 3. Catch unhandled exceptions in background threads
    def _thread_excepthook(args):
        logging.error(
            "Unhandled exception in thread '%s':\n%s",
            getattr(args.thread, "name", "?"),
            "".join(traceback.format_exception(
                args.exc_type, args.exc_value, args.exc_traceback)),
        )
    threading.excepthook = _thread_excepthook

def _log_audio(action: str, detail: str = ""):
    """Thin wrapper — call before every sd.play() / sd.stop()."""
    logging.debug("AUDIO %-6s %-30s %s", action, detail,
                  f"thread={threading.current_thread().name}")

def _open_url(url):
    """Open a URL in the default browser, cross-platform."""
    import webbrowser
    webbrowser.open(url)
try:
    import winsound
except ImportError:
    winsound = None

# --- GLOBALS ---
BASE_DIR = ""
APP_DATA_ROOT = ""
ENGINE_ROOT = ""
sox_path = ""
VERSION_FILE = ""
CONFIG_FILE = ""
MODULES_DIR = ""
APP_VERSION = "4.6.1"
MODEL_CUSTOM = ""
MODEL_BASE = ""
MODEL_DESIGN = ""

def setup_environment():
    """Configures all system paths and environment variables.
    Must be called BEFORE UI or Locking starts."""
    global BASE_DIR, APP_DATA_ROOT, ENGINE_ROOT, sox_path
    global VERSION_FILE, CONFIG_FILE, MODULES_DIR, APP_VERSION
    global MODEL_CUSTOM, MODEL_BASE, MODEL_DESIGN

    # 1. Internal Assets (Icons, Sox, JSONs) - "Where am I unpacked?"
    is_frozen = getattr(sys, 'frozen', False)
    if is_frozen:
        # In --onefile mode, assets are in sys._MEIPASS (volatile temp dir)
        BASE_DIR = sys._MEIPASS
    else:
        BASE_DIR = os.path.dirname(os.path.abspath(__file__))

    # 2. External Data (The Engine) - "Where is the heavy stuff?"
    # We use LOCALAPPDATA so it persists even if the EXE is moved/deleted.
    APP_DATA_ROOT = os.path.join(os.getenv('LOCALAPPDATA'), "Qwen3Studio")
    os.makedirs(APP_DATA_ROOT, exist_ok=True)
    ENGINE_ROOT = os.path.join(APP_DATA_ROOT, "Qwen3-TTS")

    # 3. Setup Dependencies (Sox)
    sox_path = os.path.join(BASE_DIR, "sox")
    if os.path.exists(sox_path):
        # Force absolute path for environment variables
        abs_sox = os.path.abspath(sox_path)
        os.environ["SOX_PATH"] = abs_sox
        # Add to beginning of PATH to ensure priority
        if abs_sox not in os.environ["PATH"]:
            os.environ["PATH"] = abs_sox + os.pathsep + os.environ["PATH"]
        # On Windows, some libraries also look at 'sox' in PATH
        os.environ["sox"] = os.path.join(abs_sox, "sox.exe")

    # 4. CONFIG FILE — always lives in APP_DATA_ROOT (survives frozen temp wipe)
    VERSION_FILE = os.path.join(BASE_DIR, "version.json")  # read-only bundled asset
    CONFIG_FILE = os.path.join(APP_DATA_ROOT, "app_config.json")

    # Migrate: first run in dev mode may have config only in BASE_DIR
    _base_config = os.path.join(BASE_DIR, "app_config.json")
    if not os.path.exists(CONFIG_FILE) and os.path.exists(_base_config):
        try:
            shutil.copy2(_base_config, CONFIG_FILE)
        except Exception:
            pass

    # Load Version
    if os.path.exists(VERSION_FILE):
        try:
            with open(VERSION_FILE, 'r') as f:
                APP_VERSION = json.load(f).get("version", APP_VERSION)
        except Exception as e:
            logging.warning("Failed to load version file: %s", e)

    # 5. MODULES DIR — persistent in APP_DATA_ROOT when frozen, repo root in dev
    if is_frozen:
        MODULES_DIR = os.path.join(APP_DATA_ROOT, "modules")
        os.makedirs(MODULES_DIR, exist_ok=True)
        # Seed defaults on first frozen run by copying bundled plugins
        bundled_modules = os.path.join(BASE_DIR, "modules")
        if os.path.isdir(bundled_modules):
            for fname in os.listdir(bundled_modules):
                if fname.endswith(".py") and not fname.startswith("__"):
                    dest = os.path.join(MODULES_DIR, fname)
                    if not os.path.exists(dest):
                        try:
                            shutil.copy2(os.path.join(bundled_modules, fname), dest)
                        except Exception:
                            pass
    else:
        MODULES_DIR = os.path.join(BASE_DIR, "modules")

    # 6. Local Path Mappings (Forced Stability)
    MODEL_CUSTOM = os.path.join(ENGINE_ROOT, "custom")
    MODEL_BASE = os.path.join(ENGINE_ROOT, "base")
    MODEL_DESIGN = os.path.join(ENGINE_ROOT, "design")

# --- INITIALIZE ENVIRONMENT IMMEDIATELY ---
setup_environment()

# --- THIRD PARTY IMPORTS ---
import torch
import soundfile as sf
import sounddevice as sd
import numpy as np
from PIL import Image, ImageTk

try:
    import windnd
except ImportError:
    windnd = None

WHISPER_ERROR = None
try:
    from faster_whisper import WhisperModel
    WHISPER_AVAILABLE = True
except Exception as e:
    WHISPER_AVAILABLE = False
    WHISPER_ERROR = str(e)

# --- LOCAL IMPORTS ---
try:
    from qwen_tts import Qwen3TTSModel
except Exception:
    Qwen3TTSModel = None

# --- NEW IMPORT ---
from batch_director import BatchDirector

# --- CONFIG & CONSTANTS ---
# Repository Mappings
MODEL_REPOS = {
    "custom": "Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice",
    "base":   "Qwen/Qwen3-TTS-12Hz-1.7B-Base",
    "design": "Qwen/Qwen3-TTS-12Hz-1.7B-VoiceDesign"
}

DEVICE = "cuda:0" if torch.cuda.is_available() else "cpu"
STATS_FILE = "generation_stats.json"
MAX_WAVEFORM_POINTS = 2000  # UI optimization

class ModuleHub:
    """Handles synchronization with GitHub and managing enabled/disabled states."""
    def __init__(self, modules_dir):
        self.modules_dir = modules_dir
        self.registry_file = os.path.join(os.getenv('LOCALAPPDATA'), "Qwen3Studio", "enabled_modules.json")
        
        self.registry = self.load_registry()
        self.repo_url = "https://api.github.com/repos/1verysimple-lab/Qwen3-Studio-Official/contents/modules"
        self.raw_base_url = "https://raw.githubusercontent.com/1verysimple-lab/Qwen3-Studio-Official/main/modules"
        self.on_refresh = None # Callback for UI refresh

    def load_registry(self):
        """Loads module states and enforces essential defaults."""
        defaults = {
            "tutorial_plugin.py": True,
            "peak_meter_plugin.py": True,
            "text_parser_plugin.py": True,
            "style_profile_manager_plugin.py": True,
            "autoscript_plugin.py": False,
        }
        if os.path.exists(self.registry_file):
            try:
                with open(self.registry_file, "r") as f:
                    self.registry = json.load(f)
                # Back-fill any bundled plugins missing from older registry files
                changed = False
                for name, state in defaults.items():
                    if name not in self.registry:
                        self.registry[name] = state
                        changed = True
                if changed:
                    self.save_registry()
            except Exception as e:
                logging.warning("Failed to load module registry, using defaults: %s", e)
                self.registry = defaults
        else:
            self.registry = defaults
            self.save_registry()
        return self.registry

    def save_registry(self):
        try:
            with open(self.registry_file, 'w') as f:
                json.dump(self.registry, f, indent=4)
        except Exception as e:
            logging.warning("Failed to save module registry: %s", e)

    def is_enabled(self, filename):
        # Default to False — unknown files never load without explicit opt-in
        return self.registry.get(filename, False)

    def toggle_module(self, module_name, state):
        """Saves the state immediately to cure the 'amnesia' bug."""
        self.registry[module_name] = state
        self.save_registry() # Critical: Burn the choice into the JSON file
        if self.on_refresh: self.on_refresh()

    def verify_file_hash(self, file_content_bytes, expected_hash):
        """Returns True if SHA-256 of file_content_bytes matches expected_hash."""
        actual = hashlib.sha256(file_content_bytes).hexdigest()
        return actual == expected_hash

    def sync_from_github(self, callback=None):
        """Securely fetches modules from GitHub, verifying SHA-256 against manifest.json."""
        def task():
            try:
                import requests

                # Step 1: Fetch manifest (trust anchor — committed to same repo, served over TLS)
                manifest_url = f"{self.raw_base_url}/manifest.json"
                r_manifest = requests.get(manifest_url, timeout=10)
                if r_manifest.status_code != 200:
                    if callback: callback("error", f"Failed to fetch manifest: {r_manifest.status_code}", [])
                    return
                try:
                    manifest = r_manifest.json()
                except Exception as e:
                    if callback: callback("error", f"Invalid manifest JSON: {e}", [])
                    return

                # Step 2: Fetch GitHub API file list
                headers = {'Accept': 'application/vnd.github.v3+json'}
                r = requests.get(self.repo_url, headers=headers, timeout=10)
                if r.status_code != 200:
                    if callback: callback("error", f"GitHub API Error: {r.status_code}", [])
                    return

                files = r.json()
                py_files = [f for f in files if isinstance(f, dict)
                            and f.get('name', '').endswith('.py')
                            and not f.get('name', '').startswith('__')]
                newly_downloaded = []

                # Step 3: For each .py file — gate on manifest, skip existing, verify hash
                for f in py_files:
                    name = f['name']

                    # Block anything not explicitly approved in the manifest
                    if name not in manifest:
                        print(f"[SECURITY BLOCK] '{name}' is not in manifest.json — skipping.")
                        continue

                    target_path = os.path.join(self.modules_dir, name)

                    # Skip files already on disk (no re-download)
                    if os.path.exists(target_path):
                        continue

                    # Download and verify integrity before writing
                    raw_url = f"{self.raw_base_url}/{name}"
                    r_code = requests.get(raw_url, timeout=15)
                    if r_code.status_code != 200:
                        print(f"[WARN] Failed to download '{name}': HTTP {r_code.status_code}")
                        continue

                    content_bytes = r_code.content
                    if self.verify_file_hash(content_bytes, manifest[name]):
                        with open(target_path, 'wb') as mod_file:
                            mod_file.write(content_bytes)
                        newly_downloaded.append(name)
                        if name not in self.registry:
                            self.registry[name] = False  # disabled until user manually enables
                    else:
                        print(f"[SECURITY CRITICAL] Hash mismatch for '{name}' — file discarded.")

                # Step 4: Persist registry and fire callback
                self.save_registry()
                msg = f"Sync Complete. Found {len(py_files)} plugins, downloaded {len(newly_downloaded)} new modules."
                if callback:
                    callback("success", msg, newly_downloaded)
                elif self.on_refresh:
                    self.on_refresh()
            except Exception as e:
                if callback: callback("error", str(e), [])

        threading.Thread(target=task, daemon=True).start()

SUPPORTED_LANGUAGES = [
    "English", "Chinese", "Japanese", "Korean", "Cantonese", 
    "German", "French", "Russian", "Portuguese", "Spanish", 
    "Italian", "Auto"
]

WHISPER_LANGUAGES = {
    "Auto": None,
    "English": "en",
    "Chinese": "zh",
    "Cantonese": "yue",
    "Japanese": "ja",
    "Korean": "ko",
    "French": "fr",
    "German": "de",
    "Spanish": "es",
    "Russian": "ru",
    "Portuguese": "pt",
    "Italian": "it",
    "Dutch": "nl",
    "Turkish": "tr",
    "Polish": "pl",
    "Indonesian": "id",
    "Vietnamese": "vi"
}

# --- DATA: VOICE RECIPES ---
def get_voice_recipes() -> Dict[str, Dict[str, Any]]:
    return {
        "1. Broadcaster": {
            "instruct": "Read clearly and confidently. Neutral tone. Even pacing.", 
            "desc": "Middle-aged male, deep baritone, clear standard American accent, professional.", 
            "script": "Tonight’s top story: A breakthrough in renewable energy promises to cut costs by half within the next decade. Experts say this could be the turning point we've been waiting for.",
            "temp": 0.4, "top_p": 0.5
        },
        "2. Bedtime Story": {
            "instruct": "Read softly and slowly. Warm, reassuring tone.", 
            "desc": "Female, mid-40s, very soft and warm texture, soothing and gentle.", 
            "script": "Once upon a time, in a forest where the leaves whispered secrets to the wind, a little fox curled up in his den. The stars above blinked like sleepy eyes, watching over the world.",
            "temp": 0.6, "top_p": 0.8
        },
        "3. Podcast Host": {
            "instruct": "Conversational but focused. Moderate pace. Friendly clarity.", 
            "desc": "Young adult male, energetic, bright, slightly casual tone.", 
            "script": "Welcome back to the show. Today we’re diving into something that affects all of us—how we spend our time. It’s not just about productivity; it’s about what actually matters.",
            "temp": 0.7, "top_p": 0.8
        },
        "4. Documentary": {
            "instruct": "Measured, observant tone. Slightly slower than conversational.", 
            "desc": "Older male, British accent, rich texture, deep and resonant.", 
            "script": "The desert at night is a place of stark contrasts. As the heat of the day dissipates, life begins to stir from the shadows, adapted perfectly to this harsh, beautiful landscape.",
            "temp": 0.5, "top_p": 0.7
        },
        "5. Erotic (Soft)": {
            "instruct": "Low and intimate tone. Slow pace. Soft emphasis.", 
            "desc": "Young female, breathy texture, soft and intimate, close to microphone.", 
            "script": "The room was warm, the air heavy with the scent of jasmine. He leaned closer, his voice barely a whisper against her ear, sending a shiver down her spine.",
            "temp": 0.7, "top_p": 0.9
        },
        "6. AI Assistant": {
            "instruct": "Neutral tone. Even pacing. No emotion. Clear pronunciation.", 
            "desc": "Neutral gender, flat pitch, crisp articulation, no breathiness, robotic.", 
            "script": "System check complete. All modules are functioning within normal parameters. Please select a command to proceed.",
            "temp": 0.3, "top_p": 0.1
        },
        "7. Motivational": {
            "instruct": "Steady and encouraging. Moderate pace. Confidence without urgency.", 
            "desc": "30s male, clear and resonant, projecting authority, confident.", 
            "script": "You have everything you need right now. It’s not about waiting for the perfect moment; it’s about taking that first step and trusting that the path will appear.",
            "temp": 0.6, "top_p": 0.8
        },
        "8. Academic": {
            "instruct": "Formal but accessible. Measured pace. Clear articulation.", 
            "desc": "Elderly female, crisp articulation, formal tone, intellectual.", 
            "script": "In this lecture, we will examine the fundamental principles of quantum mechanics. Note specifically how the observer effect challenges our traditional understanding of reality.",
            "temp": 0.4, "top_p": 0.6
        },
        "9. Audiobook": {
            "instruct": "Narrative tone. Moderate pace. Smooth flow.", 
            "desc": "Middle-aged female, smooth texture, expressive and clear, storytelling voice.", 
            "script": "She stood at the edge of the cliff, the wind tearing at her coat. Below, the ocean churned, grey and unforgiving. It was here that the journey had begun, and here it would end.",
            "temp": 0.6, "top_p": 0.8
        },
        "10. Internal Monologue": {
            "instruct": "Quiet, thoughtful tone. Slow pace. Longer pauses.", 
            "desc": "Young male, soft, slightly raspy, whispering, close to the mic.", 
            "script": "I wonder if I made the right choice. It felt right at the time... but looking back, everything seems different. Maybe that's just how memory works.",
            "temp": 0.7, "top_p": 0.8
        },
        "11. Sales (Soft)": {
            "instruct": "Friendly and confident. Light emphasis on benefits. No pressure.", 
            "desc": "Young adult female, energetic, bright, smiling voice, trustworthy.", 
            "script": "Imagine a solution that just works. No complicated setup, no hidden fees. Just simple, reliable performance that gives you your time back.",
            "temp": 0.7, "top_p": 0.8
        },
        "12. Meditation": {
            "instruct": "Very slow pace. Low, steady tone. Long pauses.", 
            "desc": "Androgynous, very soft, calm, slow and deep, hypnotic.", 
            "script": "Take a deep breath in... and let it out slowly. Feel the tension leaving your shoulders. For the next few moments, there is nowhere else you need to be.",
            "temp": 0.5, "top_p": 0.8
        },
        "13. Technical": {
            "instruct": "Precise, neutral tone. Even pace. Clear pronunciation.", 
            "desc": "Middle-aged male, precise, flat pitch, no accent, dry tone.", 
            "script": "The hydraulic pressure must be maintained at 2000 PSI. If the gauge drops below this threshold, the safety valve will automatically engage to prevent system failure.",
            "temp": 0.3, "top_p": 0.5
        },
        "14. Dramatic": {
            "instruct": "Low, controlled tone. Slow pace. Clear pauses.", 
            "desc": "Middle-aged male, deep, gravelly, intense, movie trailer style.", 
            "script": "In a world where silence is the only weapon... one man must scream to be heard. Coming this summer.",
            "temp": 1.0, "top_p": 0.9
        },
        "15. Casual": {
            "instruct": "Relaxed, natural tone. Conversational pace.", 
            "desc": "Young female, relaxed, slightly high-pitched, informal, fast.", 
            "script": "Hey! Just wanted to check in and see how you're doing. Let's grab coffee sometime next week if you're free. Talk soon!",
            "temp": 0.8, "top_p": 0.9
        },
        "Tutorial Wizard": {
            "instruct": "Slow, deliberate, and wise. Calm and commanding.",
            "desc": "An elderly man in his seventies. Deep, gravelly bass voice, masculine and husky. Resonant chest voice with a rough, raspy texture. Slow-paced and deliberate.",
            "script": "Knowledge is the only treasure that grows when shared. Welcome to my sanctum.",
            "temp": 0.7, "top_p": 0.8
        }
    }

CUSTOM_VOICE_SCRIPTS = {
    "Vivian": "Hello there! I hope you're having a wonderful day. It's so nice to meet you.",
    "Serena": "Can you hear me? I'm speaking softly, just for you. Listen closely.",
    "Ryan": "Hey! Let's get moving! There's so much to do and I can't wait to get started!",
    "Aiden": "Relax. Take a deep breath. Everything is going to be just fine.",
    "Eric": "This is a test of the broadcast system. I'm reading this clearly and with authority.",
    "Dylan": "Hi! I'm Dylan. I'm here to help you with whatever you need.",
    "Uncle_Fu": "Greetings. Let us take a moment to reflect on the beauty around us.",
    "Ono_Anna": "Konnichiwa! I'm so excited to be here and chat with you today!",
    "Sohee": "Hello. I hope my voice can bring some comfort and warmth to your day."
}

# Default scripts for styles if the user includes them in a Voice Set
STYLE_DEMO_SCRIPTS = {
    "Furious": "I told you to leave me alone! Get out!",
    "Heartbroken": "I... I just don't know what to do anymore.",
    "Panicked": "Did you hear that? Someone is in the house.",
    "Overjoyed": "Oh my god! I won! I actually won!",
    "Sarcastic": "Oh, wow. What a genius idea that was.",
    "Seductive": "The room was warm, the air heavy with the scent of jasmine.",
    "Villain": "You have no idea what is coming for you.",
    "Horror Narrator": "And then... the scratching stopped.",
    "News Anchor": "Tonight's top story: A breakthrough in renewable energy.",
    "The Drunk": "I... I'm not drunk, you're the one who's spinning.",
    "Old Radio": "And now, for our feature presentation!",
    "Exhausted": "I can't... I just need to sleep for a while.",
    "ASMR": "Take a deep breath in... and let it out slowly.",
    "Dying Breath": "It... it's getting dark..."
}
# Fallback script for unknown styles
GENERIC_SCRIPT = "I wonder if I made the right choice. It felt right at the time."

# --- HELP RENDERING HELPERS ---

def _configure_help_tags(widget, colors, base_h1=15):
    """Configure text tags used by _render_help_text on any tk.Text widget."""
    widget.tag_configure("h1",
        font=("Segoe UI", base_h1, "bold"),
        foreground=colors["accent"],
        spacing1=2, spacing3=10)
    widget.tag_configure("divider",
        font=("Segoe UI", 3),
        foreground=colors["border"],
        spacing1=0, spacing3=8)
    widget.tag_configure("h2",
        font=("Segoe UI", 10, "bold"),
        foreground=colors["fg"],
        spacing1=12, spacing3=3)
    widget.tag_configure("bullet",
        font=("Segoe UI", 10),
        lmargin1=20, lmargin2=32,
        spacing1=2)
    widget.tag_configure("numbered",
        font=("Segoe UI", 10),
        lmargin1=20, lmargin2=32,
        spacing1=2)
    widget.tag_configure("body",
        font=("Segoe UI", 10),
        spacing1=1, spacing3=1)
    widget.tag_configure("indent",
        font=("Consolas", 9),
        foreground=colors["muted"],
        lmargin1=28, lmargin2=28,
        spacing1=1)


def _render_help_text(widget, text):
    """Parse and insert formatted help text into a tk.Text widget.

    Recognises:
      • First non-blank line      → h1 title + divider rule
      • Lines starting with '## ' → h2 sub-header
      • Lines starting with '• '  → bullet
      • Lines starting with digit+'.'+space → numbered item
      • Lines starting with two spaces      → indented (code/example)
      • Empty lines               → body spacer
      • Everything else           → body
    """
    lines = text.strip().split("\n")
    first_line = True
    for line in lines:
        if first_line and line.strip():
            widget.insert(tk.END, line.strip() + "\n", "h1")
            widget.insert(tk.END, "─" * 55 + "\n", "divider")
            first_line = False
        elif line.startswith("## "):
            widget.insert(tk.END, line[3:] + "\n", "h2")
        elif line.startswith("• "):
            widget.insert(tk.END, line + "\n", "bullet")
        elif len(line) > 2 and line[0].isdigit() and line[1] in ".":
            widget.insert(tk.END, line + "\n", "numbered")
        elif line.startswith("  ") and line.strip():
            widget.insert(tk.END, line + "\n", "indent")
        elif line.strip() == "":
            widget.insert(tk.END, "\n", "body")
        else:
            widget.insert(tk.END, line + "\n", "body")


# --- HELP CONTENT ---
HELP_ENGINES = """The 3 Creative Engines\n

## 🟢 Custom Voice  (Green)
Uses high-stability pre-trained personas — best for consistency and long-form narration where the voice must not drift.
Speakers: Vivian, Serena, Ryan, Aiden, Eric, Dylan, Uncle_Fu, Ono_Anna, Sohee

## 🔵 Voice Design  (Blue)
Zero-shot generation. Describe a person and the AI creates them from scratch.
Ideal for unique or one-off characters without reference audio.

## 🟣 Voice Clone  (Purple)
The Replica engine. Provide reference audio and it mimics that voice.
The closer the recording quality to studio conditions, the more accurate the clone.

## System Notes
• Audio processing uses the bundled sox folder for normalisation.
• MP3 conversion: FFmpeg (in PATH) is tried first; falls back to SoX + libmp3lame-0.dll (place in the sox folder)."""

HELP_PERSONAS = """Preset Speaker Personas (Custom Engine)\n

Pre-trained speakers have a native language where they sound most natural — but all can speak any supported language.

## English
• Ryan — Dynamic male, strong rhythmic drive.
• Aiden — Sunny American male, clear midrange.

## Chinese
• Vivian — Bright, edgy young female.
• Serena — Warm, gentle young female.
• Eric — Lively male, slightly husky brightness.  (Sichuan accent)
• Dylan — Youthful male, clear and natural.  (Beijing accent)
• Uncle_Fu — Seasoned male, low and mellow.

## Other Languages
• Ono_Anna — Playful Japanese female.  (Native: Japanese)
• Sohee — Warm Korean female, rich emotion.  (Native: Korean)"""

HELP_TAGS = """In-Script Action Tags\n

Insert these tags directly into your text to trigger human sounds.

## Available Tags
• [laughter] or <laughter> — Natural laugh
• [breath] or <breath> — Audible inhale / exhale
• [sigh] — Long, soft sigh
• [gasp] — Sharp intake of breath
• [clears throat] — Throat-clearing sound
• [cry] — Emotional crying

## Tips
• Wrap tags with spaces: "Hello [ laughter ] how are you?" for best results.
• Effectiveness varies with temperature and instruction energy.
• High-energy instructions amplify tag intensity.
• Try placing [breath] before a dramatic line for added naturalism."""

HELP_RECIPES = """Tone Recipes (Voice Design & Custom)\n

Copy any of these into the Instruction field for instant character results.

## Drama & Emotion
• Heartbroken — Trembling voice, holding back tears, slow pace.
• Furious — Aggressive, shouting, very fast pace, intense anger.
• Villain — Low menacing whisper. Slow and calculated. Cold.
• Terrified — Shaking, whimpering, barely holding it together.

## Performance Styles
• ASMR — Soft whisper, extremely close to mic, intimate mouth sounds.
• News Anchor — Professional, neutral tone, clear articulation.
• Old Radio — Mid-Atlantic accent, fast pace, energetic, sharp.
• Seductive — Low pitch, breathy texture, very slow, intimate.

## Mixing Tip
Combine a recipe with context for best results.
Example: "News Anchor, but visibly exhausted, struggling to stay composed." """

HELP_BATCH = """Batch Studio: The Production Line\n

The Batch Studio is a non-linear script editor for producing multi-voice audio scenes.

## Workflow
1. Add blocks — one block equals one line of dialogue.
2. Assign each block a Speaker, Style, Language, and optionally a Seed.
3. Hit Run to generate the whole scene, or use per-block controls for surgical edits.

## Block Status System
• Grey — Pending. Not yet generated.
• Blue — Busy. Generating right now.
• Yellow — Review. Done, awaiting your approval.
• Green — Accepted. Will be skipped on the next Run.
• Red — Rejected. Queued for re-generation.

## Per-Block Controls
• ⚡ Gen — Generates only this block without touching any others.
• 🎲 x3 — Multi-Take: generates 3 variations silently, opens a picker to choose the best. The winning seed is saved automatically.
• Seed field — Pin a number for a reproducible result, or leave empty for a fresh random take.

## Scene Controls
• ⚡ Auto-Switch — Automatically swaps engines between blocks so you never have to wait.
• Play All — Plays the accepted scene audio in sequence.

## Saving & Loading
Save your entire scene (including audio and seeds) as a JSON file to resume later."""

HELP_DESC = """Field A: Voice Description (The Body)\n

Describes the physical characteristics of the voice — what it sounds like at rest, independent of emotion.

## Attributes to Describe
• Age — "Young child", "Mid-30s", "Elderly", "Ancient"
• Gender — "Male", "Female", "Androgynous"
• Texture — "Gravelly", "Smooth", "Raspy", "Breathy", "Nasal"
• Accent — "British RP", "Southern US", "Thick Russian", "Standard American"
• Build — "Deep barrel chest", "Petite and light"

## Example
A 60-year-old male smoker with a deep, gravelly throat and a faint Southern drawl."""

HELP_INSTR = """Field B: Style Instruction (The Acting)\n

Defines how the voice is performing right now — the acting direction, independent of the physical voice.

## Attributes to Direct
• Pace — "Very slow", "Fast", "Conversational", "Measured"
• Emotion — "Sad", "Angry", "Joyful", "Bored", "Terrified"
• Volume — "Whispering", "Shouting", "Softly spoken", "Distant"
• Context — "Like confessing a secret", "As if addressing a crowd"

## Example
Speaking slowly and quietly, as if sharing a long-buried secret. Barely above a whisper."""

HELP_LOCK = """Locking the Perfect Voice\n

Once you've designed a voice you love, use the Clone engine to permanently lock and stabilise it.

## Steps
1. Generate a voice you're happy with in the Voice Design tab.
2. Click Save WAV to export it.
3. Switch to the Voice Clone tab (or add a Clone Block in Batch Studio).
4. Load your saved WAV as the Source Audio.
5. Provide a short transcript of what was spoken in the reference clip.

## Result
The Clone engine treats that WAV as a reference persona, reproducing the same voice identity with high consistency across any new text."""

HELP_TIPS = """Pro-Tips for Better Generation\n

## The Pause Trick
The AI respects line breaks. For dramatic pauses between sentences, press Enter to put them on separate lines instead of using commas or ellipses.

## Fix Slurring
If a voice sounds drunk or garbled, lower Temperature to 0.3–0.5 and simplify the instruction. Complexity and high temperature together cause most slurring.

## Accent Forcing
Use the Lang selector to push an accent onto any text.
Example: English text + German language = English spoken with a German accent.

## Deterministic Takes
Enter a number in the Seed field before generating. The same seed always produces the same audio. Leave it empty for a fresh result each time — the chosen seed is written back automatically.

## Multi-Take Workflow
Use 🎲 x3 on any block to generate 3 variations side-by-side, then pick the best one. Accepting a take writes its seed back into the block so you can reproduce it.

## Engine Reset
If generation gets stuck or a VRAM crash occurs, click 🔄 Reset in the Engine Status header to abort and reload the model cleanly."""

HELP_SLIDERS = """The Precision Sliders\n

## Temperature  (Creativity & Stability)
Controls how much randomness the model introduces.
• 0.1 – 0.5 — The News Anchor. Flat, stable, consistent. Best for long narration.
• 0.6 – 0.9 — The Sweet Spot. Natural human variation. Recommended for most work.
• 1.0 – 1.5 — The Drama. High emotion and expressiveness. Higher risk of artifacts.

## Top P  (Vocabulary Range)
Controls how many token candidates the model considers at each step.
• 0.1 – 0.5 — Focused. Best for crisp, clear pronunciation.
• 0.8 – 1.0 — Diverse. Better for character acting and rhythmic flow.

## Seed  (Reproducibility)
Pins the random state for a deterministic, repeatable result.
• Empty — A fresh random seed is chosen and written back automatically after generation.
• Number — That exact seed is used every time, producing identical audio output."""

HELP_PLUGINS = """Plugins & Automation\n

Qwen3 Studio is built on an extensible plugin architecture. All plugins live in the ./modules/ folder and are managed from the Modules tab.

## Bundled Plugins
• Tutorial Plugin — The interactive multi-chapter tutorial experience.
• Peak Meter Plugin — Adds a 📶 VU button to the header. Opens a floating real-time peak meter to monitor levels and prevent clipping.
• Style & Profile Manager — Manage, enable/disable, and inline-edit your Styles and Voice Design Profiles from a single panel.
• Autoscript Plugin (disabled) — Demo showing how the app can be driven by external automation scripts.

## Building Your Own
Drop any Python file into ./modules/. It must export one function:
  initialize(app)  →  called once at startup with the QwenTTSApp instance.

## Plugin Ideas
• Watch Folder — Monitor a folder and auto-generate audio for any new .txt file dropped in.
• Local API — Expose a small HTTP server so other tools can request audio on demand.
• Custom Exporter — Push finished audio straight to your game engine, DAW, or editor."""

TIP_TEMP = """Temperature (Creativity & Stability)
• Low (0.1 - 0.5): The "News Anchor". Stable, consistent.
• Med (0.6 - 0.9): The "Sweet Spot". Natural variation.
• High (1.0 - 1.5): The "Drama". High emotion, risk of artifacts."""

TIP_TOP_P = """Top P (Vocabulary Range)
• Low (0.1 - 0.5): Focused. Best for clear pronunciation.
• High (0.8 - 1.0): Diverse. Best for character acting."""


# --- UI UTILITIES ---
class StatusIndicator(tk.Canvas):
    def __init__(self, master, size=30):
        try:
            bg = master.cget("background")
        except:
            bg = "SystemButtonFace"
        super().__init__(master, width=size, height=size, bg=bg, highlightthickness=0)
        
        # Fancy LED: Outer ring (darker), Inner circle (color), Gloss (white hint)
        self.size = size
        pad = 4
        self.outer = self.create_oval(pad, pad, size-pad, size-pad, fill="grey", outline="#555", width=1)
        self.inner = self.create_oval(pad+2, pad+2, size-pad-2, size-pad-2, fill="#777", outline="", width=0)
        self.state_map = {
            "idle": ("grey", "#777"), 
            "busy": ("#f1c40f", "#f39c12"), # Yellow/Orange
            "ready": ("#2ecc71", "#27ae60"), # Green
            "error": ("#e74c3c", "#c0392b")  # Red
        }
    
    def set_state(self, state):
        fill, inner_fill = self.state_map.get(state, ("grey", "#777"))
        self.itemconfig(self.outer, fill=fill)
        self.itemconfig(self.inner, fill=inner_fill)

class CreateToolTip(object):
    def __init__(self, widget, text='widget info'):
        self.waittime = 500
        self.wraplength = 300
        self.widget = widget
        self.text = text # Fix: Assign the text parameter to an instance variable
        self.widget.bind("<Enter>", self.enter)
        self.widget.bind("<Leave>", self.leave)
        self.id = None
        self.tw = None

    def enter(self, event=None):
        self.schedule()

    def leave(self, event=None):
        self.unschedule()
        self.hidetip()

    def schedule(self):
        self.unschedule()
        self.id = self.widget.after(self.waittime, self.showtip)

    def unschedule(self):
        if self.id:
            self.widget.after_cancel(self.id)
            self.id = None

    def showtip(self, event=None):
        x = y = 0
        x, y, cx, cy = self.widget.bbox("insert")
        x += self.widget.winfo_rootx() + 25
        y += self.widget.winfo_rooty() + 20
        self.tw = tk.Toplevel(self.widget)
        self.tw.wm_overrideredirect(True)
        self.tw.wm_geometry("+%d+%d" % (x, y))
        label = tk.Label(self.tw, text=self.text, justify='left', background="#ffffe0", relief='solid', borderwidth=1, wraplength=self.wraplength, font=("Segoe UI", 9))
        label.pack(ipadx=4, ipady=4)

    def hidetip(self):
        if self.tw:
            self.tw.destroy()
            self.tw = None

# --- MAIN APPLICATION ---
class QwenTTSApp:
    def __init__(self, root, start_mode="custom"):
        self.root = root
        self.root.title(f"Qwen3-TTS Pro Suite v{APP_VERSION}")
        self.root.geometry("1170x850")
        
        # Paths
        self.temp_dir = os.path.join(APP_DATA_ROOT, "temp_outputs")
        os.makedirs(self.temp_dir, exist_ok=True)

        self.assets_dir = os.path.join(APP_DATA_ROOT, "saved_assets")
        os.makedirs(self.assets_dir, exist_ok=True)

        self.model_dir = ENGINE_ROOT 

        # Module Hub Initialization
        self.modules_dir = MODULES_DIR
        if not os.path.exists(self.modules_dir):
            os.makedirs(self.modules_dir, exist_ok=True)
        self.hub = ModuleHub(self.modules_dir)
        self.loaded_plugins = set()
        self._new_modules = set()

        # Config & Profiles - LOAD THIS FIRST
        self.app_config = self.load_app_config()
        self.voice_configs = self.app_config.get("saved_voices", {})
        self.design_profiles = self.app_config.get("design_profiles", {})
        self.voice_recipes = get_voice_recipes()
        
        # Merge Recipes into Design Profiles (Ensures Tutorial Wizard exists)
        for name, data in self.voice_recipes.items():
            if name not in self.design_profiles:
                self.design_profiles[name] = {
                    "desc": data.get("desc", ""),
                    "instruct": data.get("instruct", ""),
                    "script": data.get("script", ""),
                    "temp": data.get("temp", 0.8),
                    "top_p": data.get("top_p", 0.8)
                }
        
        self.setup_styles()

        self.model = None
        self.current_model_type = None 
        self.generated_audio = None
        self.sample_rate = 24000
        self.locked_voice_prompt = None

        # Threading & Events
        self.playback_thread = None
        self.gen_thread = None
        self.history_playback_thread = None
        self.history_stop_event = threading.Event()
        self._audio_gen = 0  # single counter for ALL audio — guards every finally: sd.stop()
        self.history_audio_data = None  # keeps the numpy array alive during PortAudio playback
        self.stop_event = threading.Event()
        self.pause_event = threading.Event()
        self.cancel_signal = threading.Event()
        self._app_alive = True  # set to False on window close to signal daemon threads
        self._model_load_event = threading.Event()

        # Audio Helper Data
        self.helper_audio_data = None
        self.helper_samplerate = 44100
        self.helper_current_frame = 0
        self.helper_is_playing = False
        self.helper_file_path = None 
        self.helper_start_time = 0
        self.audio_history = []
        self.trim_start = 0
        self.trim_end = 0
        
        # Recording
        self.is_recording = False
        self.recording_stream = None
        self.recorded_frames = []
        self.recording_start_time = 0
        self.mic_devices = {}
        self.mic_device_var = tk.StringVar(value=self.app_config.get("mic_device", "Default"))
        
        # Tutorial Data
        self.CHAPTERS = {
            "Chapter 1: Welcome": "Tutorial_01_Welcome",
            "Chapter 2: UI Overview": "Tutorial_02_UI_Overview",
            "Chapter 3: Custom Mastery": "Tutorial_03_CustomMastery",
            "Chapter 4: Voice Designer": "Tutorial_04_VoiceDesigner",
            "Chapter 5: Directing with Instructions": "Tutorial_05_Directing_with_Instructions",
            "Chapter 6: Voice Design": "Tutorial_06_Voice_Design",
            "Chapter 7: The Art of Description": "Tutorial_07_The_Art_of_Description",
            "Chapter 8: The Voice Clone Engine": "Tutorial_08_The_Voice_Clone_Engine",
            "Chapter 9: Preparing Clone Audio": "Tutorial_09_Preparing_Clone_Audio",
            "Chapter 10: The Lock Voice Feature": "Tutorial_10_The_Lock_Voice_Feature",
            "Chapter 11: Batch Studio Sequencing": "Tutorial_11_Batch_Studio_Sequencing",
            "Chapter 12: Batch Studio Review": "Tutorial_12_Batch_Studio_Review",
            "Chapter 13: The Transcript Helper": "Tutorial_13_The_Transcript_Helper",
            "Chapter 14: Pro Tips Precision Sliders": "Tutorial_14_Pro_Tips_Precision_Sliders",
            "Chapter 15: Pro Tips Tags and Punctuation": "Tutorial_15_Pro_Tips_Tags_and_Punctuation",
            "Chapter 16: Final Words": "Tutorial_16_Final_Words",
        }
        self.tutorial_lang_var = tk.StringVar(value="English")
        self.tutorial_chapter_var = tk.StringVar(value="Chapter 1: Welcome")

        # UI Construction
        self.root.configure(bg=self.colors["bg"])
        self.setup_ui()
        self.populate_mic_list()
        if windnd: self.setup_dnd()
        self.populate_default_styles()
        self.save_app_config()

        # Startup
        self.set_busy(True, "Initializing Engine...")
        self.notebook.select(self.notebook.tabs()[0])  # Always start on Custom Voice
        
        # Initial Model Load
        self.switch_model("custom") # Start with custom
        
        # Start helper loop (idling)
        self._update_helper_timer()
        
        # Ensure UI is drawn before positioning history
        self.root.update()
        self.setup_history_panel()

        # Load External Modules (Extensions)
        self.load_external_modules()

        # Start System Monitors
        self._start_vram_monitor()

    def setup_styles(self):
        self.colors = {
            "bg": "#f4f6f9",
            "fg": "#2c3e50",
            "accent": "#3498db",
            "accent_hover": "#2980b9",
            "header_bg": "#ecf0f1",
            "panel_bg": "#ffffff",
            "success": "#2ecc71",
            "warning": "#e67e22",
            "danger": "#e74c3c",
            "text_bg": "#ffffff",
            "text_fg": "#2c3e50",
            # UI system colors — use these instead of hardcoding
            "muted": "#7f8c8d",        # secondary / dimmed text
            "border": "#dfe6e9",       # status bar, dividers
            "separator": "#bdc3c7",    # inline "|" separators
            "row_selected": "#d6eaf8", # history row highlight (accent-tinted)
            "preview_bg": "#1e2d3d",   # waveform / dark canvas background
        }

        style = ttk.Style()
        style.theme_use('clam')
        
        c = self.colors
        
        # General Defaults
        style.configure(".", background=c["bg"], foreground=c["fg"], font=("Segoe UI", 10))
        style.configure("TFrame", background=c["bg"])
        style.configure("TLabelframe", background=c["bg"], borderwidth=1, relief="solid")
        style.configure("TLabelframe.Label", font=("Segoe UI", 10, "bold"), background=c["bg"], foreground=c["accent"])
        
        # Notebook
        style.configure("TNotebook", background=c["bg"], tabposition='n', borderwidth=0)
        style.configure("TNotebook.Tab", font=("Segoe UI", 9, "bold"), padding=[14, 7], 
                        background="#dfe6e9", foreground="#7f8c8d")
        style.map("TNotebook.Tab", 
            background=[("selected", c["panel_bg"]), ("active", "#b2bec3")], 
            foreground=[("selected", c["accent"]), ("active", c["fg"])]
        )
        
        # Buttons
        style.configure("TButton", font=("Segoe UI", 9, "bold"), padding=6, 
                        background="#bdc3c7", 
                        foreground=c["fg"], borderwidth=0)
        style.map("TButton", 
            background=[("active", "#b2bec3"), ("disabled", "#ecf0f1")]
        )
        
        # Custom Buttons
        style.configure("Big.TButton", font=("Segoe UI", 11, "bold"), padding=10, background=c["accent"], foreground="white")
        style.map("Big.TButton", background=[("active", c["accent_hover"])])
        
        style.configure("Panic.TButton", font=("Segoe UI", 11, "bold"), padding=10, background=c["danger"], foreground="white")
        style.map("Panic.TButton", background=[("active", "#c0392b")])

        style.configure("Flat.TButton", font=("Segoe UI", 9, "bold"), padding=6,
                        borderwidth=0, relief="flat",
                        background="#e2e6ea", foreground="#2c3e50")
        style.map("Flat.TButton", background=[("active", "#d2d6da"), ("disabled", "#ecf0f1")])
        
        # Headers
        style.configure("HelperHeader.TLabel", font=("Segoe UI", 14, "bold"), foreground=c["accent"], background=c["bg"])
        
        # Inputs
        style.configure("TEntry", fieldbackground=c["text_bg"], padding=5)
        style.configure("TCombobox", fieldbackground=c["text_bg"], padding=5)

    def setup_ui(self):
        hbg = self.colors["header_bg"]

        # ── OUTER HEADER WRAPPER (always visible) ─────────────────────────
        # This thin strip holds the title + collapse toggle at all times.
        self.header_wrapper = tk.Frame(self.root, bg=hbg)
        self.header_wrapper.pack(fill=tk.X)

        # Title bar row: always visible
        title_bar = tk.Frame(self.header_wrapper, bg=hbg, padx=15, pady=6)
        title_bar.pack(fill=tk.X)

        tk.Label(title_bar, text="Qwen3 TTS Pro", font=("Segoe UI", 16, "bold"),
                 bg=hbg, fg=self.colors["fg"]).pack(side=tk.LEFT)

        support_row = tk.Frame(title_bar, bg=hbg)
        support_row.pack(side=tk.LEFT, padx=(12, 0))
        lbl_link = tk.Label(support_row, text="App by Blues", font=("Segoe UI", 9, "underline"),
                             bg=hbg, fg=self.colors["accent"], cursor="hand2")
        lbl_link.pack(side=tk.LEFT)
        lbl_link.bind("<Button-1>", lambda e: _open_url("https://blues-lab.pro"))
        tk.Label(support_row, text=" | ", bg=hbg, fg=self.colors["separator"]).pack(side=tk.LEFT)
        lbl_help = tk.Label(support_row, text="❓ Help", font=("Segoe UI", 9, "underline"),
                             bg=hbg, fg=self.colors["accent"], cursor="hand2")
        lbl_help.pack(side=tk.LEFT)
        lbl_help.bind("<Button-1>", lambda e: self.show_help_guide())
        tk.Label(support_row, text=" | ", bg=hbg, fg=self.colors["separator"]).pack(side=tk.LEFT)
        lbl_coffee = tk.Label(support_row, text="Support", font=("Segoe UI", 9, "bold"),
                               bg=hbg, fg=self.colors["warning"], cursor="hand2")
        lbl_coffee.pack(side=tk.LEFT)
        lbl_coffee.bind("<Button-1>", lambda e: self.show_support_modal())

        # ── SINGLE CONTROLS ROW ───────────────────────────────────────────────
        controls_row = tk.Frame(self.header_wrapper, bg=hbg, padx=15, pady=5)
        controls_row.pack(fill=tk.X)

        # === RIGHT SIDE — two stacked rows: buttons top, options bottom ===
        right_area = tk.Frame(controls_row, bg=hbg)
        right_area.pack(side=tk.RIGHT, padx=(8, 0))

        # Top row: History + VU
        right_top = tk.Frame(right_area, bg=hbg)
        right_top.pack(fill=tk.X, pady=(0, 3))

        self.btn_history = tk.Button(
            right_top, text="📜 History",
            command=self.setup_history_panel,
            bg=self.colors["accent"], fg="white",
            font=("Segoe UI", 9, "bold"),
            activebackground=self.colors["accent_hover"], activeforeground="white",
            relief="flat", bd=0
        )
        self.btn_history.pack(side=tk.LEFT, ipady=2)

        self.vu_button_container = tk.Frame(right_top, height=26, width=70, bg=hbg)
        self.vu_button_container.pack(side=tk.LEFT, padx=(4, 0), fill=tk.Y)
        self.vu_button_container.pack_propagate(False)

        # Bottom row: Auto-Play + Ready Sound + Time
        right_bot = tk.Frame(right_area, bg=hbg)
        right_bot.pack(fill=tk.X)

        self.autoplay_var = tk.BooleanVar(value=self.app_config.get("autoplay", True))
        ttk.Checkbutton(right_bot, text="Auto-Play", variable=self.autoplay_var, command=self.save_app_config).pack(side=tk.LEFT)

        self.sound_on_ready_var = tk.BooleanVar(value=self.app_config.get("sound_on_ready", False))
        cb_snd = ttk.Checkbutton(right_bot, text="Ready Sound", variable=self.sound_on_ready_var, command=self.save_app_config)
        cb_snd.pack(side=tk.LEFT, padx=(4, 0))
        sound_name = os.path.basename(self.app_config.get("custom_notification_sound") or "Default Beep")
        self.cb_snd_tooltip = CreateToolTip(cb_snd, f"Current Sound: {sound_name}\n(Right-click to reset)")
        self.snd_popup = tk.Menu(self.root, tearoff=0)
        self.snd_popup.add_command(label="Reset to Default Beep", command=self.reset_notification_sound)
        cb_snd.bind("<Button-3>", lambda e: self.snd_popup.tk_popup(e.x_root, e.y_root))

        self.lbl_last_time = tk.Label(right_bot, text="Time: --", font=("Segoe UI", 9),
                                       fg=self.colors["accent"], bg=hbg)
        self.lbl_last_time.pack(side=tk.RIGHT)

        # === LEFT SIDE ===
        # Status indicator + model label
        self.status_icon = StatusIndicator(controls_row, size=14)
        self.status_icon.pack(side=tk.LEFT, padx=(0, 5))
        self.lbl_active_model = tk.Label(controls_row, text="Initializing...",
                                          font=("Segoe UI", 9, "bold"), fg=self.colors["muted"],
                                          bg=hbg)
        self.lbl_active_model.pack(side=tk.LEFT)

        # Action buttons
        self.btn_cancel = tk.Button(
            controls_row, text="STOP",
            command=self.cancel_generation,
            bg="#e74c3c", fg="white",
            font=("Segoe UI", 9, "bold"),
            activebackground="#c0392b", activeforeground="white",
            relief="flat", bd=0, width=5
        )
        self.btn_cancel.pack(side=tk.LEFT, padx=(8, 2), pady=2)
        ttk.Button(controls_row, text="🔄 Reset", command=self.force_reset_model, width=8).pack(side=tk.LEFT, padx=2, pady=2)
        ttk.Button(controls_row, text="⚙", command=self.show_settings_dialog, width=3).pack(side=tk.LEFT, padx=(2, 6), pady=2)

        # Separator
        tk.Label(controls_row, text="│", fg=self.colors["separator"], bg=hbg, font=("Segoe UI", 13)).pack(side=tk.LEFT, padx=4)

        # Precision sliders — inline
        for label, var, tip in [("Temp", "temp", TIP_TEMP), ("Top P", "top_p", TIP_TOP_P)]:
            tk.Label(controls_row, text=label, font=("Segoe UI", 9, "bold"), bg=hbg).pack(side=tk.LEFT, padx=(6, 2))
            val_var = tk.DoubleVar(value=self.app_config.get(var, 0.8))
            setattr(self, f"{var}_var", val_var)
            s = ttk.Scale(controls_row, from_=0.1, to=1.5 if var=="temp" else 1.0,
                          variable=val_var, orient=tk.HORIZONTAL, length=90,
                          command=self.update_precision_labels)
            s.pack(side=tk.LEFT, padx=2)
            CreateToolTip(s, tip)
            lbl_val = tk.Label(controls_row, text="0.80", width=5, anchor=tk.W,
                               font=("Consolas", 9), fg=self.colors["muted"], bg=hbg)
            lbl_val.pack(side=tk.LEFT, padx=(0, 4))
            setattr(self, f"lbl_{var}_val", lbl_val)

        # Seed
        tk.Label(controls_row, text="Seed", font=("Segoe UI", 9, "bold"), bg=hbg).pack(side=tk.LEFT, padx=(4, 2))
        self.seed_var = tk.StringVar(value=self.app_config.get("seed", ""))
        _seed_entry = ttk.Entry(controls_row, textvariable=self.seed_var, width=9)
        _seed_entry.pack(side=tk.LEFT, padx=2)
        CreateToolTip(_seed_entry,
            "Seed — controls output reproducibility.\n\n"
            "Empty  →  a fresh random seed every generation (output varies each time).\n"
            "Number  →  deterministic; the same seed always produces the same take.\n\n"
            "🎲  rolls a new random number into this field so you can save and reuse it.")
        tk.Button(controls_row, text="🎲",
                  command=lambda: self.seed_var.set(str(random.randint(0, 0xFFFFFFFF))),
                  bd=0, cursor="hand2", font=("Segoe UI", 10), bg=hbg).pack(side=tk.LEFT)

        # Lock sliders
        self.lock_sliders_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(controls_row, text="Lock", variable=self.lock_sliders_var).pack(side=tk.LEFT, padx=(4, 6))

        self.update_precision_labels()

        # 2. Status Bar (Packed Bottom FIRST so it sticks)
        self.status_var = tk.StringVar(value="Ready")
        self.lbl_status = tk.Label(self.root, textvariable=self.status_var, relief=tk.FLAT, anchor=tk.W, padx=12, pady=6, bg=self.colors["border"], font=("Segoe UI", 9))
        self.lbl_status.pack(side=tk.BOTTOM, fill=tk.X)

        # 3. Notebook (Fills remaining space)
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=(8, 0))
        
        # Tabs
        self.tab_tutorial = ttk.Frame(self.notebook)
        self.tab_helper = ttk.Frame(self.notebook)
        self.tab_clone = ttk.Frame(self.notebook)
        self.tab_design = ttk.Frame(self.notebook)
        self.tab_custom = ttk.Frame(self.notebook)
        self.tab_batch = ttk.Frame(self.notebook)
        self.tab_hub = ttk.Frame(self.notebook)
        
        # Tabs ordered by frequency of use — power tools first, utilities last
        self.notebook.add(self.tab_custom,  text="⭐ Custom Voice")
        self.notebook.add(self.tab_clone,   text="🎙 Voice Clone")
        self.notebook.add(self.tab_design,  text="🎨 Voice Design")
        self.notebook.add(self.tab_batch,   text="🎬 Batch Studio")
        self.notebook.add(self.tab_helper,  text="📝 Transcript")
        self.notebook.add(self.tab_hub,     text="🧩 Modules")
        if self.hub.is_enabled('tutorial_plugin.py'):
            self.notebook.add(self.tab_tutorial, text="🎓 Tutorial")

        self.notebook.bind("<<NotebookTabChanged>>", self.on_tab_change)

        # Init Tab Content (order matches addition order above)
        self.setup_custom_tab()
        self.setup_clone_tab()
        self.setup_design_tab()
        self.setup_batch_tab()
        self.setup_helper_tab()
        self.setup_hub_tab()
        if self.hub.is_enabled('tutorial_plugin.py'):
            self.setup_tutorial_tab()

        # Open History by default
        self.root.after(500, self.setup_history_panel)

    def on_tab_change(self, event):
        # 1. Identify Tab
        try:
            tab_id = self.notebook.index(self.notebook.select())
            tab_text = self.notebook.tab(tab_id, "text")
        except tk.TclError:
            return # Tab is being destroyed

        # 2. Define Engine Mappings & Colors
        eng_map = {
            "🎓 Tutorial": (None,     "#e9ecef", "Interactive Learning Environment"),
            "⭐ Custom Voice": ("custom", "#d5f5e3", "Requires: Custom Engine (Green)"),
            "🎨 Voice Design": ("design", "#d6eaf8", "Requires: Design Engine (Blue)"),
            "🎙 Voice Clone":  ("base",   "#e8daef", "Requires: Clone Engine (Purple)"),
            "🎬 Batch Studio": (None,     "#fcf3cf", "Multi-Engine Support (Auto-Switching)"),
            "📝 Transcript": (None, "#e9ecef", "Utility Tool (No Engine Required)"),
            "🧩 Modules": (None, "#d1f2eb", "Plugin Manager (No Engine Required)")
        }
        
        req_engine, bg_color, hint = eng_map.get(tab_text, (None, "#e9ecef", "Ready"))
        
        # 3. Update Status Bar Look
        self.lbl_status.config(bg=bg_color)
        
        # 4. Check Mismatch
        if req_engine:
            if self.current_model_type and self.current_model_type != req_engine:
                self.status_var.set(f"CAUTION: {hint} - Current: {self.current_model_type.upper()}")
            else:
                self.status_var.set(f"READY: {hint}")
        else:
            self.status_var.set(hint)

    def setup_playback_controls(self, parent):
        frame = ttk.Frame(parent)
        frame.pack(side=tk.LEFT)
        self.btn_play = ttk.Button(frame, text="Play", command=self.on_play_click, width=12)
        self.btn_play.pack(side=tk.LEFT)
        self.btn_pause = ttk.Button(frame, text="Pause", command=self.on_pause_click, state=tk.DISABLED, width=8)
        self.btn_pause.pack(side=tk.LEFT, padx=2)
        self.btn_stop = ttk.Button(frame, text="Stop", command=self.on_stop_click, state=tk.DISABLED, width=10)
        self.btn_stop.pack(side=tk.LEFT, padx=2)
        ttk.Separator(frame, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=10)
        ttk.Button(frame, text="Save WAV", command=self.save_audio).pack(side=tk.LEFT)

    # --- TAB SETUP METHODS ---
    def setup_tutorial_tab(self):
        f = self.tab_tutorial
        f.columnconfigure(0, weight=1)

        header = ttk.Frame(f, padding=(20, 10))
        header.grid(row=0, column=0, sticky="ew")
        ttk.Label(header, text="🎓 Interactive Tutorial", style="HelperHeader.TLabel").pack(anchor="w")
        ttk.Label(header, text="Learn the app by loading pre-made scripts into the Batch Studio.",
                  font=("Segoe UI", 10), background=self.colors["bg"]).pack(anchor="w", pady=(2, 10))
        
        # Controls Frame
        ctrl_f = ttk.LabelFrame(f, text="Select a Lesson", padding=20)
        ctrl_f.grid(row=1, column=0, sticky="ew", padx=20, pady=10)
        ctrl_f.columnconfigure(1, weight=1)

        # Language Selector
        ttk.Label(ctrl_f, text="Language:").grid(row=0, column=0, sticky="w", padx=(0, 10))
        lang_combo = ttk.Combobox(ctrl_f, textvariable=self.tutorial_lang_var, 
                                  values=["English", "Spanish", "Chinese"], 
                                  state="readonly", width=15)
        lang_combo.grid(row=0, column=1, sticky="w")

        # Chapter Selector
        ttk.Label(ctrl_f, text="Chapter:").grid(row=1, column=0, sticky="w", padx=(0, 10), pady=(10,0))
        chapter_combo = ttk.Combobox(ctrl_f, textvariable=self.tutorial_chapter_var, 
                                     values=list(self.CHAPTERS.keys()),
                                     state="readonly")
        chapter_combo.grid(row=1, column=1, sticky="ew", pady=(10,0))

        # Load Button
        load_btn = ttk.Button(ctrl_f, text="Load Tutorial Script", style="Big.TButton", 
                              command=self.load_tutorial_script)
        load_btn.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(20, 0))

    def load_tutorial_script(self):
        lang = self.tutorial_lang_var.get()
        chapter_key = self.tutorial_chapter_var.get()
        
        base_filename = self.CHAPTERS.get(chapter_key)
        if not base_filename:
            messagebox.showerror("Error", "Invalid chapter selected.")
            return

        lang_suffix_map = {"English": "", "Spanish": "_ES", "Chinese": "_CN"}
        model_lang_map = {"English": "English", "Spanish": "Spanish", "Chinese": "Chinese"}
        
        suffix = lang_suffix_map.get(lang, "")
        model_lang = model_lang_map.get(lang, "English")

        filename = f"{base_filename}{suffix}.json"
        filepath = os.path.join(BASE_DIR, "tutorials", filename)

        if not os.path.exists(filepath):
            messagebox.showerror("File Not Found", f"Could not find the tutorial file:\n{filepath}\n\nPlease ensure the 'tutorials' folder is intact.")
            return
            
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Force the correct language for the engine blocks
            for block in data:
                block["language"] = model_lang
            
            # Switch to Batch Tab
            self.notebook.select(self.tab_batch)
            
            # Load data into the director
            if hasattr(self, 'director'):
                self.director.load_script_data(data, name=f"{chapter_key} ({lang})")
                self.status_var.set(f"Loaded Tutorial: {chapter_key}")
            else:
                 messagebox.showerror("Error", "Batch Director not found.")
                 
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load tutorial script:\n{e}")

    def setup_custom_tab(self):
        f = self.tab_custom
        f.columnconfigure(0, weight=1); f.rowconfigure(2, weight=1)

        ttk.Label(f, text="Custom Voice — Generate with built-in speaker presets", style="HelperHeader.TLabel").grid(row=0, column=0, sticky="w", padx=15, pady=(10, 0))

        top_f = ttk.Frame(f, padding=15)
        top_f.grid(row=1, column=0, sticky="ew")
        
        ttk.Label(top_f, text="Language:").pack(side=tk.LEFT)
        self.lang_var_custom = tk.StringVar(value="English")
        ttk.Combobox(top_f, textvariable=self.lang_var_custom, values=SUPPORTED_LANGUAGES, state="readonly", width=12).pack(side=tk.LEFT, padx=(5, 20))
        
        ttk.Label(top_f, text="Speaker Preset:").pack(side=tk.LEFT)
        self.speaker_var = tk.StringVar(value="Ryan")
        spks = sorted([
            "Ryan (English Male)", 
            "Aiden (English Male)",
            "Vivian (Chinese Female)", 
            "Serena (Chinese Female)", 
            "Eric (Sichuan Male)", 
            "Dylan (Beijing Male)", 
            "Uncle_Fu (Chinese Male)", 
            "Ono_Anna (Japanese Female)", 
            "Sohee (Korean Female)"
        ])
        self.speaker_combo = ttk.Combobox(top_f, textvariable=self.speaker_var, values=spks, state="readonly", width=30)
        self.speaker_combo.pack(side=tk.LEFT, padx=5)
        self.speaker_combo.bind("<<ComboboxSelected>>", self.on_custom_speaker_select)
        
        ttk.Button(top_f, text="📖 Load Demo", command=self.load_custom_demo_script).pack(side=tk.LEFT, padx=5)

        mid_f = ttk.LabelFrame(f, text="Text to Speak", padding=10)
        mid_f.grid(row=2, column=0, sticky="nsew", padx=15, pady=5)
        self.text_input_custom = scrolledtext.ScrolledText(mid_f, font=("Segoe UI", 11), wrap=tk.WORD)
        self.text_input_custom.pack(fill=tk.BOTH, expand=True)
        self.text_input_custom.insert("1.0", "Welcome to the new Qwen interface.")
        
        bot_f = ttk.Frame(f, padding=15)
        bot_f.grid(row=3, column=0, sticky="ew")

        instr_f = ttk.Frame(bot_f)
        instr_f.pack(fill=tk.X, pady=(0, 10))
        ttk.Label(instr_f, text="Instruction (Style/Pace):").pack(side=tk.LEFT)
        self.instruct_input = ttk.Entry(instr_f, font=("Segoe UI", 10))
        self.instruct_input.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=10)
        
        # Style Manager Row
        style_f = ttk.Frame(bot_f)
        style_f.pack(fill=tk.X, pady=(0, 15))
        ttk.Label(style_f, text="Saved Styles:").pack(side=tk.LEFT)
        self.style_var_custom = tk.StringVar()
        self.style_combo_custom = ttk.Combobox(style_f, textvariable=self.style_var_custom, state="readonly", width=30)
        self.style_combo_custom.pack(side=tk.LEFT, padx=5)
        self.style_combo_custom.bind("<<ComboboxSelected>>", lambda e: self.on_style_select("custom"))
        self.update_style_combo()
        
        ttk.Label(style_f, text="| Save As:").pack(side=tk.LEFT, padx=5)
        self.new_style_name_custom = ttk.Entry(style_f, width=15)
        self.new_style_name_custom.pack(side=tk.LEFT)
        ttk.Button(style_f, text="Save", command=lambda: self.on_save_style("custom")).pack(side=tk.LEFT, padx=2)
        ttk.Button(style_f, text="Delete", command=lambda: self.on_delete_style("custom")).pack(side=tk.LEFT, padx=2)
        
        action_area = ttk.Frame(bot_f)
        action_area.pack(fill=tk.X)
        self.btn_generate_custom = ttk.Button(action_area, text="GENERATE AUDIO", style="Big.TButton", command=self.start_gen_custom)
        self.btn_generate_custom.pack(side=tk.LEFT, padx=(0, 10))
        
        ttk.Button(action_area, text="Generate Voice Set", command=lambda: self.open_voice_set_dialog("custom"), width=20).pack(side=tk.LEFT, padx=5)
        
        self.setup_playback_controls(action_area)

    def setup_helper_tab(self):
        f = self.tab_helper
        f.columnconfigure(0, weight=1)
        f.rowconfigure(3, weight=1) # Give weight to the text editor row
        
        ttk.Label(f, text="Step 1: Prep Audio & Transcript", style="HelperHeader.TLabel").grid(row=0, column=0, sticky="w", padx=15, pady=(10,0))

        # Audio Workbench
        wb_f = ttk.LabelFrame(f, text="", padding=10) # Title is now manual
        wb_f.grid(row=1, column=0, sticky="ew", padx=15, pady=5)
        
        # -- NEW HEADER ROW --
        wb_header_f = ttk.Frame(wb_f)
        wb_header_f.pack(fill=tk.X, pady=(0, 5))

        ttk.Label(wb_header_f, text="Audio Workbench", style="TLabelframe.Label").pack(side=tk.LEFT)
        
        # -- Microphone widgets moved here, packed to the right --
        mic_f = ttk.Frame(wb_header_f)
        mic_f.pack(side=tk.RIGHT)
        ttk.Label(mic_f, text="Microphone:", font=("Segoe UI", 9)).pack(side=tk.LEFT, padx=(0,5))
        self.mic_combo = ttk.Combobox(mic_f, textvariable=self.mic_device_var, state="readonly")
        self.mic_combo.pack(side=tk.LEFT, padx=(0, 5))
        self.mic_combo.bind("<<ComboboxSelected>>", lambda e: self.save_app_config())
        ttk.Button(mic_f, text="🔄", command=self.populate_mic_list, width=3).pack(side=tk.LEFT)

        # -- Original content of the workbench --
        self.wave_canvas = tk.Canvas(wb_f, height=100, bg="#222", highlightthickness=0) # Slightly reduced height
        self.wave_canvas.pack(fill=tk.X, pady=5)
        self.wave_canvas.bind("<Button-1>", self.on_wave_click)
        self.wave_canvas.bind("<Button-3>", self.on_wave_click)
        
        ctrl_row = ttk.Frame(wb_f)
        ctrl_row.pack(fill=tk.X, pady=5)
        
        # Transport
        trans_f = ttk.Frame(ctrl_row)
        trans_f.pack(side=tk.LEFT)
        self.btn_record = ttk.Button(trans_f, text="Record", command=self.toggle_recording, width=10)
        self.btn_record.pack(side=tk.LEFT, padx=2)
        ttk.Button(trans_f, text="⏪ 5s", command=lambda: self.helper_seek(-5), width=6).pack(side=tk.LEFT)
        self.btn_helper_play = ttk.Button(trans_f, text="Play", command=self.helper_toggle_play, width=10)
        self.btn_helper_play.pack(side=tk.LEFT)
        ttk.Button(trans_f, text="Stop", command=self.helper_stop_audio, width=10).pack(side=tk.LEFT)
        ttk.Button(trans_f, text="5s ⏩", command=lambda: self.helper_seek(5), width=6).pack(side=tk.LEFT)
        self.lbl_helper_time = ttk.Label(trans_f, text="00:00 / 00:00", font=("Segoe UI", 9))
        self.lbl_helper_time.pack(side=tk.LEFT, padx=10)
        
        # File Ops
        file_f = ttk.Frame(ctrl_row)
        file_f.pack(side=tk.RIGHT)
        self.lbl_helper_file = ttk.Label(file_f, text="No Audio Loaded", font=("Segoe UI", 9, "italic"), foreground=self.colors["muted"])
        self.lbl_helper_file.pack(side=tk.TOP, anchor=tk.E, padx=2)
        ttk.Button(file_f, text="Open", command=self.helper_load_audio).pack(side=tk.LEFT, padx=2)
        self.btn_save_rec = ttk.Button(file_f, text="Save WAV", command=self.save_recorded_audio, state=tk.DISABLED)
        self.btn_save_rec.pack(side=tk.LEFT, padx=2)
        ttk.Separator(file_f, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=5)
        self.btn_crop = ttk.Button(file_f, text="Crop", command=self.crop_audio, state=tk.DISABLED, width=8)
        self.btn_crop.pack(side=tk.LEFT, padx=2)
        self.btn_undo = ttk.Button(file_f, text="Undo", command=self.undo_audio, state=tk.DISABLED, width=8)
        self.btn_undo.pack(side=tk.LEFT, padx=2)
        
        # Recipes
        recipe_f = ttk.LabelFrame(f, text="Voice Coach", padding=10)
        recipe_f.grid(row=2, column=0, sticky="ew", padx=15, pady=5)
        r_top = ttk.Frame(recipe_f)
        r_top.pack(fill=tk.X, pady=5)
        ttk.Label(r_top, text="Select Style:").pack(side=tk.LEFT)
        self.recipe_var = tk.StringVar()
        self.recipe_combo = ttk.Combobox(r_top, textvariable=self.recipe_var, state="readonly", values=sorted(list(self.voice_recipes.keys())), width=40)
        self.recipe_combo.pack(side=tk.LEFT, padx=10)
        self.recipe_combo.bind("<<ComboboxSelected>>", self.on_recipe_select)
        ttk.Button(r_top, text="Load Script", command=self.load_recipe_script).pack(side=tk.LEFT)
        self.lbl_recipe_instruct = tk.Label(recipe_f, text="Select a style above...", justify=tk.LEFT, bg="#e9ecef", relief=tk.FLAT, anchor="w", padx=10, pady=10, font=("Segoe UI", 10, "italic"))
        self.lbl_recipe_instruct.pack(fill=tk.X)
        
        # Transcript Editor
        trans_editor_f = ttk.LabelFrame(f, text="Transcript Editor", padding=10)
        trans_editor_f.grid(row=3, column=0, sticky="nsew", padx=15, pady=5)
        trans_editor_f.columnconfigure(0, weight=1)
        trans_editor_f.rowconfigure(1, weight=1)

        t_tools = ttk.Frame(trans_editor_f)
        t_tools.grid(row=0, column=0, sticky="ew", pady=(0,5))
        self.btn_whisper = ttk.Button(t_tools, text="Audio -> Text", command=self.run_whisper_task)
        self.btn_whisper.pack(side=tk.LEFT)
        
        self.lbl_whisper_lang = ttk.Label(t_tools, text="Lang:")
        self.lbl_whisper_lang.pack(side=tk.LEFT, padx=(10, 2))
        
        self.whisper_lang_var = tk.StringVar(value="Auto")
        self.whisper_lang_combo = ttk.Combobox(t_tools, textvariable=self.whisper_lang_var, values=list(WHISPER_LANGUAGES.keys()), state="readonly", width=10)
        self.whisper_lang_combo.pack(side=tk.LEFT, padx=2)
        self.whisper_lang_combo.bind("<<ComboboxSelected>>", self.on_whisper_lang_change)

        ttk.Button(t_tools, text="Clean Timestamps", command=self.on_clean_script_click).pack(side=tk.LEFT, padx=5)
        
        self.helper_text_area = scrolledtext.ScrolledText(trans_editor_f, font=("Segoe UI", 11), wrap=tk.WORD)
        self.helper_text_area.grid(row=1, column=0, sticky="nsew")
        
        # Profile Management
        final_f = ttk.Frame(f, padding=15)
        final_f.grid(row=4, column=0, sticky="ew", pady=(10,0))
        
        prof_area = ttk.Frame(final_f)
        prof_area.pack(side=tk.LEFT)
        ttk.Label(prof_area, text="Profile:").pack(side=tk.LEFT)
        self.profile_var = tk.StringVar()
        self.profile_combo = ttk.Combobox(prof_area, textvariable=self.profile_var, state="readonly", width=15)
        self.profile_combo.pack(side=tk.LEFT, padx=5)
        self.update_profile_combo()
        ttk.Button(prof_area, text="Load", command=self.on_load_profile, width=6).pack(side=tk.LEFT)
        ttk.Button(prof_area, text="Update", command=lambda: self.update_current_profile("helper"), width=7).pack(side=tk.LEFT, padx=2)
        
        ttk.Label(prof_area, text="| New:").pack(side=tk.LEFT, padx=(10, 5))
        self.new_profile_name = ttk.Entry(prof_area, width=15)
        self.new_profile_name.pack(side=tk.LEFT)
        ttk.Button(prof_area, text="Save", command=self.on_save_profile, width=6).pack(side=tk.LEFT, padx=2)
        ttk.Button(prof_area, text="Del", command=self.on_delete_profile, width=6).pack(side=tk.LEFT, padx=2)
        
        ttk.Button(final_f, text="➡️ Send All to Voice Clone Tab", style="Big.TButton", command=self.send_to_voice_clone).pack(side=tk.RIGHT)

    def setup_clone_tab(self):
        f = self.tab_clone
        f.columnconfigure(0, weight=1); f.rowconfigure(3, weight=1)
        
        ttk.Label(f, text="Step 2: Generate Voice Clone", style="HelperHeader.TLabel").grid(row=0, column=0, sticky="w", padx=15, pady=(10,0))

        # Profile Loader
        prof_f = ttk.Frame(f, padding=15)
        prof_f.grid(row=0, column=0, sticky="e")
        ttk.Label(prof_f, text="Load Profile:").pack(side=tk.LEFT)
        self.clone_profile_var = tk.StringVar()
        self.clone_profile_combo = ttk.Combobox(prof_f, textvariable=self.clone_profile_var, state="readonly", width=15)
        self.clone_profile_combo.pack(side=tk.LEFT, padx=5)
        self.update_clone_profile_combo()
        ttk.Button(prof_f, text="Load", command=self.load_clone_profile, width=6).pack(side=tk.LEFT)
        ttk.Button(prof_f, text="Update", command=lambda: self.update_current_profile("clone"), width=7).pack(side=tk.LEFT, padx=2)

        # Source Audio
        src_f = ttk.LabelFrame(f, text="1. Source Voice (Reference)", padding=10)
        src_f.grid(row=1, column=0, sticky="ew", padx=15, pady=10)
        row1 = ttk.Frame(src_f)
        row1.pack(fill=tk.X, pady=5)
        self.ref_audio_path = tk.StringVar()
        ttk.Entry(row1, textvariable=self.ref_audio_path, state='readonly').pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0,5))
        ttk.Button(row1, text="Browse...", command=self.browse_audio).pack(side=tk.LEFT)
        self.btn_transcribe_clone = ttk.Button(row1, text="📝 Transcribe", command=self.transcribe_ref_audio)
        self.btn_transcribe_clone.pack(side=tk.LEFT, padx=2)
        self.btn_lock = ttk.Button(row1, text="🔒 Lock Voice", command=self.toggle_lock_voice)
        self.btn_lock.pack(side=tk.LEFT, padx=2)
        ttk.Button(row1, text="?", width=3, command=lambda: self.show_context_help("Locking the Voice", HELP_LOCK)).pack(side=tk.LEFT, padx=5)
        
        row2 = ttk.Frame(src_f)
        row2.pack(fill=tk.X, pady=5)
        ttk.Label(row2, text="Transcript of Reference:").pack(side=tk.LEFT)
        self.x_vector_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(row2, text="Ignore Text", variable=self.x_vector_var).pack(side=tk.RIGHT)
        self.ref_text_input = tk.Text(src_f, height=3, font=("Segoe UI", 10), wrap=tk.WORD, bg="#f8f9fa")
        self.ref_text_input.pack(fill=tk.X, pady=(5,0))
        
        # Target Meta
        tgt_meta_f = ttk.Frame(f, padding=15)
        tgt_meta_f.grid(row=2, column=0, sticky="ew")
        ttk.Label(tgt_meta_f, text="2. Target Language:").pack(side=tk.LEFT)
        self.lang_var_clone = tk.StringVar(value="English")
        ttk.Combobox(tgt_meta_f, textvariable=self.lang_var_clone, values=SUPPORTED_LANGUAGES, state="readonly", width=15).pack(side=tk.LEFT, padx=10)
        
        self.use_segments_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(tgt_meta_f, text="Multi-Part Mode (Split by '||')", variable=self.use_segments_var).pack(side=tk.LEFT, padx=20)
        
        # Target Text
        tgt_f = ttk.LabelFrame(f, text="3. Target Text to Speak", padding=10)
        tgt_f.grid(row=3, column=0, sticky="nsew", padx=15, pady=5)
        
        mon_f = ttk.Frame(tgt_f)
        mon_f.pack(fill=tk.X, pady=(0,5))
        
        # Left: Split Controls
        ttk.Label(mon_f, text="Split Limit:").pack(side=tk.LEFT)
        self.split_length_var = tk.IntVar(value=35)
        ttk.Entry(mon_f, textvariable=self.split_length_var, width=4).pack(side=tk.LEFT, padx=(5,5))
        ttk.Button(mon_f, text="Auto Split", command=self.auto_split_script, width=9).pack(side=tk.LEFT, padx=2)
        ttk.Button(mon_f, text="Clear", command=self.clear_split_cues, width=6).pack(side=tk.LEFT, padx=2)
        ttk.Button(mon_f, text="+ ||", command=self.insert_split_cue, width=5).pack(side=tk.LEFT, padx=10)
        
        # Right: Health Monitor
        self.lbl_script_health = tk.Label(mon_f, text="Max: 0 w", font=("Segoe UI", 9, "bold"), fg="grey")
        self.lbl_script_health.pack(side=tk.RIGHT)
        
        self.target_text_input = scrolledtext.ScrolledText(tgt_f, font=("Segoe UI", 11), wrap=tk.WORD)
        self.target_text_input.pack(fill=tk.BOTH, expand=True)
        self.target_text_input.bind("<KeyRelease>", self.monitor_script_health)
        
        # Actions
        bot_f = ttk.Frame(f, padding=15)
        bot_f.grid(row=4, column=0, sticky="ew")
        self.btn_generate_clone = ttk.Button(bot_f, text="▶ CLONE VOICE", style="Big.TButton", command=self.start_gen_clone)
        self.btn_generate_clone.pack(side=tk.LEFT, padx=(0, 10))
        
        # Removed Voice Set button per user request (Cloning engine lacks style control)
        
        self.setup_playback_controls(bot_f)

    def setup_design_tab(self):
        f = self.tab_design
        f.columnconfigure(0, weight=1); f.rowconfigure(4, weight=1)

        ttk.Label(f, text="Voice Design — Create voices from description", style="HelperHeader.TLabel").grid(row=0, column=0, sticky="w", padx=15, pady=(10, 0))

        # Profiles
        prof_f = ttk.Frame(f, padding=15)
        prof_f.grid(row=1, column=0, sticky="ew")
        ttk.Label(prof_f, text="Design Profile:").pack(side=tk.LEFT)
        self.des_profile_var = tk.StringVar()
        self.des_profile_combo = ttk.Combobox(prof_f, textvariable=self.des_profile_var, state="readonly", width=30)
        self.des_profile_combo.pack(side=tk.LEFT, padx=5)
        self.des_profile_combo.bind("<<ComboboxSelected>>", lambda e: self.load_design_profile())
        self.update_des_profile_combo()
        ttk.Button(prof_f, text="Load", command=self.load_design_profile, width=6).pack(side=tk.LEFT)
        ttk.Button(prof_f, text="Del", command=self.delete_design_profile, width=6).pack(side=tk.LEFT, padx=5)
        
        self.lock_design_script_var = tk.BooleanVar(value=False)
        tk.Checkbutton(prof_f, text="🔒 Lock Script", variable=self.lock_design_script_var, bg=self.colors["bg"], font=("Segoe UI", 9)).pack(side=tk.LEFT, padx=5)

        ttk.Label(prof_f, text="| Save As:").pack(side=tk.LEFT, padx=10)
        self.new_des_profile_name = ttk.Entry(prof_f, width=20)
        self.new_des_profile_name.pack(side=tk.LEFT)
        ttk.Button(prof_f, text="Save", command=self.save_design_profile).pack(side=tk.LEFT, padx=5)
        
        # Description
        desc_f = ttk.Frame(f, padding=(15, 5))
        desc_f.grid(row=2, column=0, sticky="ew")
        d_head = ttk.Frame(desc_f)
        d_head.pack(fill=tk.X)
        ttk.Label(d_head, text="Voice Description", font=("Segoe UI", 10, "bold")).pack(side=tk.LEFT)
        ttk.Button(d_head, text="?", width=3, command=lambda: self.show_context_help("Voice Description", HELP_DESC)).pack(side=tk.LEFT, padx=5)
        
        self.txt_design_desc = tk.Text(desc_f, height=4, font=("Segoe UI", 10), wrap=tk.WORD, bg="#f4f4f8")
        self.txt_design_desc.pack(fill=tk.X)
        CreateToolTip(self.txt_design_desc, "Describe the voice's physical qualities (Age, Gender, Texture).")
        self.txt_design_desc.insert("1.0", "A grizzled old narrator with a deep, gravelly voice.")
        
        # Instruction
        instr_f = ttk.Frame(f, padding=(15, 5))
        instr_f.grid(row=3, column=0, sticky="ew")
        i_head = ttk.Frame(instr_f)
        i_head.pack(fill=tk.X)
        ttk.Label(i_head, text="Style Instruction", font=("Segoe UI", 10, "bold")).pack(side=tk.LEFT)
        ttk.Button(i_head, text="?", width=3, command=lambda: self.show_context_help("Style Instruction", HELP_INSTR)).pack(side=tk.LEFT, padx=5)
        
        self.txt_design_instruct = ttk.Entry(instr_f, font=("Segoe UI", 10))
        self.txt_design_instruct.pack(fill=tk.X, pady=(2,0))
        CreateToolTip(self.txt_design_instruct, "Describe the performance style (Pace, Emotion).")
        self.txt_design_instruct.insert(0, "Somber and slow")
        
        # Style Manager Row (Shared with Custom tab)
        style_mgr_f = ttk.Frame(instr_f)
        style_mgr_f.pack(fill=tk.X, pady=5)
        ttk.Label(style_mgr_f, text="Saved Styles:", font=("Segoe UI", 9)).pack(side=tk.LEFT)
        self.style_var_design = tk.StringVar()
        self.style_combo_design = ttk.Combobox(style_mgr_f, textvariable=self.style_var_design, state="readonly", width=30)
        self.style_combo_design.pack(side=tk.LEFT, padx=5)
        self.style_combo_design.bind("<<ComboboxSelected>>", lambda e: self.on_style_select("design"))
        
        ttk.Label(style_mgr_f, text="| Save As:").pack(side=tk.LEFT, padx=5)
        self.new_style_name_design = ttk.Entry(style_mgr_f, width=15)
        self.new_style_name_design.pack(side=tk.LEFT)
        ttk.Button(style_mgr_f, text="Save", command=lambda: self.on_save_style("design"), width=8).pack(side=tk.LEFT, padx=2)
        ttk.Button(style_mgr_f, text="Del", command=lambda: self.on_delete_style("design"), width=8).pack(side=tk.LEFT, padx=2)
        
        self.update_style_combo()
        
        # Target Text
        tgt_f = ttk.LabelFrame(f, text="Text to Speak", padding=10)
        tgt_f.grid(row=4, column=0, sticky="nsew", padx=15, pady=5)
        self.txt_design_target = scrolledtext.ScrolledText(tgt_f, font=("Segoe UI", 11), wrap=tk.WORD)
        self.txt_design_target.pack(fill=tk.BOTH, expand=True)
        
        # Actions
        bot_f = ttk.Frame(f, padding=15)
        bot_f.grid(row=5, column=0, sticky="ew")
        self.btn_gen_design = ttk.Button(bot_f, text="GENERATE DESIGN", style="Big.TButton", command=self.start_gen_design)
        self.btn_gen_design.pack(side=tk.LEFT, padx=(0, 10))
        
        ttk.Button(bot_f, text="Generate Voice Set", command=lambda: self.open_voice_set_dialog("design"), width=20).pack(side=tk.LEFT, padx=5)
        
        self.setup_playback_controls(bot_f)

    def setup_batch_tab(self):
        # Initialize the new Scene Director module
        # passing 'self' so it can access self.model, self.voice_configs, etc.
        self.director = BatchDirector(self.tab_batch, self)
        self.director.pack(fill=tk.BOTH, expand=True)

    # --- LOGIC & HELPERS ---
    def set_busy(self, is_busy, message=""):
        if is_busy:
            self.root.config(cursor="wait")
            self.status_icon.set_state("busy")
            self.status_var.set(message)
            self.btn_cancel.config(state=tk.NORMAL)
            self.cancel_signal.clear()
        else:
            self.root.config(cursor="")
            self.status_icon.set_state("ready")
            self.status_var.set(message if message else "Ready")
            self.btn_cancel.config(state=tk.DISABLED)

    def load_app_config(self):
        default = {
            "saved_voices": {}, "design_profiles": {}, 
            "style_instructions": {},
            "temp": 0.8, "top_p": 0.8, "seed": "",
            "autoplay": True, "sound_on_ready": False,
            "last_out_dir": "",
            "custom_notification_sound": None,
            "mic_device": "Default"
        }
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    return {**default, **json.load(f)}
            except Exception as e:
                logging.warning("Failed to load config: %s", e)
        return default

    def save_app_config(self):
        self.app_config.update({
            "temp": self.temp_var.get(),
            "top_p": self.top_p_var.get(),
            "seed": self.seed_var.get(),
            "autoplay": self.autoplay_var.get(),
            "sound_on_ready": self.sound_on_ready_var.get(),
            "mic_device": self.mic_device_var.get()
        })
        try:
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.app_config, f, indent=4)
        except Exception as e:
            logging.warning("Failed to save config: %s", e)

    def update_precision_labels(self, event=None):
        t = self.temp_var.get()
        p = self.top_p_var.get()
        self.lbl_temp_val.config(text=f"{t:.2f}")
        self.lbl_top_p_val.config(text=f"{p:.2f}")

    def populate_mic_list(self):
        """Finds, scores, and filters audio input devices to provide a clean list."""
        try:
            devices = sd.query_devices()
            hostapis = sd.query_hostapis()
            
            candidates = []
            default_input_idx = sd.default.device[0]

            for i, device in enumerate(devices):
                if device['max_input_channels'] == 0:
                    continue

                name = device['name']
                score = 0
                
                # Clean up name
                try:
                    # Remove the host API in parentheses, e.g., " (Windows WASAPI)"
                    api_name = hostapis[device['hostapi']]['name']
                    if name.endswith(f" ({api_name})"):
                        name = name[:-len(f" ({api_name})")].strip()
                except:
                    pass # Couldn't parse, use original name

                # Score the device
                lower_name = name.lower()
                if 'loopback' in lower_name or 'stereo mix' in lower_name or 'what u hear' in lower_name:
                    score += 100
                    name += " (System Audio)"
                if i == default_input_idx:
                    score += 50
                # WASAPI is generally preferred on Windows
                if 'wasapi' in hostapis[device['hostapi']]['name'].lower():
                    score += 10
                
                candidates.append({'id': i, 'name': name, 'score': score})

            # De-duplicate: keep the best-scoring device for each name
            best_devices = {}
            for c in candidates:
                if c['name'] not in best_devices or c['score'] > best_devices[c['name']]['score']:
                    best_devices[c['name']] = c

            # Sort the unique devices by score
            sorted_devices = sorted(best_devices.values(), key=lambda x: x['score'], reverse=True)
            
            # Final list for the UI
            self.mic_devices = {"Default": None}
            final_names = ["Default"]
            for d in sorted_devices:
                self.mic_devices[d['name']] = d['id']
                final_names.append(d['name'])
            
            self.mic_combo['values'] = final_names
            if self.mic_device_var.get() not in self.mic_devices:
                self.mic_device_var.set("Default")
            
            # Dynamically set width
            if final_names:
                max_len = max(len(name) for name in final_names)
                self.mic_combo['width'] = max_len + 2

        except Exception as e:
            print(f"Could not query audio devices: {e}")
            self.mic_combo['values'] = ["Default"]
            self.mic_device_var.set("Default")

    # --- HELPER & EDITOR METHODS (REFACTORED) ---
    def helper_load_audio(self):
        """Opens a file dialog to load audio into the helper tab."""
        initial_dir = os.path.join(os.getcwd(), 'temp')
        if not os.path.exists(initial_dir):
            initial_dir = os.getcwd()
            
        path = filedialog.askopenfilename(
            initialdir=initial_dir,
            filetypes=[("Audio Files", "*.wav *.mp3 *.ogg *.flac")]
        )
        if path:
            self.load_helper_audio_from_path(path)
    def load_helper_audio_from_path(self, path: str):
        """Loads audio data from a specific path."""
        try:
            data, sr = sf.read(path)
            self.helper_audio_data = data
            self.helper_samplerate = sr
            self.helper_current_frame = 0
            self.helper_file_path = path
            
            # Update UI
            self.btn_save_rec.config(state=tk.NORMAL)
            self.draw_waveform()
            self.helper_update_time_label()
            self.lbl_helper_file.config(text=os.path.basename(path))
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load audio:\n{str(e)}")

    def helper_toggle_play(self):
        """Toggles playback state for the helper tab."""
        if self.helper_is_playing:
            self.helper_stop_audio()
        else:
            if self.helper_audio_data is None:
                return
            
            # Play from current frame
            sd.play(self.helper_audio_data[self.helper_current_frame:], self.helper_samplerate)
            self.helper_is_playing = True
            self.helper_start_time = time.time()
            self.btn_helper_play.config(text="Is Pause")
            self._update_helper_timer()

    def helper_stop_audio(self):
        """Stops playback and resets state."""
        sd.stop()
        self.helper_is_playing = False
        self.helper_current_frame = 0 
        self.btn_helper_play.config(text="Play")
        self.helper_update_time_label()

    def helper_seek(self, seconds: int):
        """Seeks forward or backward by N seconds."""
        if self.helper_audio_data is None:
            return
            
        was_playing = self.helper_is_playing
        self.helper_stop_audio()
        
        # Calculate new frame position
        step = int(seconds * self.helper_samplerate)
        new_frame = self.helper_current_frame + step
        
        # Clamp between 0 and total length
        self.helper_current_frame = int(np.clip(new_frame, 0, len(self.helper_audio_data) - 1))
        
        self.helper_update_time_label()
        
        # Resume if it was playing
        if was_playing:
            self.helper_toggle_play()

    def _update_helper_timer(self):
        """Updates the playback timer label."""
        if self.helper_is_playing:
            elapsed_frames = int((time.time() - self.helper_start_time) * self.helper_samplerate)
            current_pos = self.helper_current_frame + elapsed_frames
            
            if current_pos > len(self.helper_audio_data):
                self.helper_stop_audio()
            else:
                self._disp_time(current_pos)
                # Reschedule only if still playing
                self.root.after(100, self._update_helper_timer)

    def helper_update_time_label(self):
        self._disp_time(self.helper_current_frame)

    def _disp_time(self, frame_idx):
        if self.helper_audio_data is None:
            return
            
        current_sec = frame_idx / self.helper_samplerate
        total_sec = len(self.helper_audio_data) / self.helper_samplerate
        
        self.lbl_helper_time.config(
            text=f"{int(current_sec//60):02d}:{int(current_sec%60):02d} / {int(total_sec//60):02d}:{int(total_sec%60):02d}"
        )

    def on_whisper_lang_change(self, event=None):
        lang = self.whisper_lang_var.get()
        # "Auto" is neutral. Others checked against Qwen support.
        if lang == "Auto" or lang in SUPPORTED_LANGUAGES:
            self.lbl_whisper_lang.config(foreground=self.colors["fg"])
        else:
            self.lbl_whisper_lang.config(foreground="purple")
            
    def run_whisper_task(self):
        global WHISPER_AVAILABLE
        if not WHISPER_AVAILABLE:
            messagebox.showerror(
                "Whisper Not Found",
                "faster-whisper is not installed.\n\n"
                "Run:  pip install faster-whisper\n"
                "then restart the application."
            )
            return

        if self.helper_audio_data is None:
            return messagebox.showwarning("No Audio", "Please load or record audio first.")

        # Always save current buffer to a temp file for Whisper to ensure we transcribe EXACTLY what's on screen
        ts = time.strftime("%H%M%S")
        temp_path = os.path.join(self.temp_dir, f"whisper_buffer_{ts}.wav")
        try:
            sf.write(temp_path, self.helper_audio_data, self.helper_samplerate)
        except Exception as e:
            return messagebox.showerror("Error", f"Failed to prepare audio for Whisper: {e}")

        self.set_busy(True, "Transcribing...")
        self.btn_whisper.config(state=tk.DISABLED)
        
        # Get language code
        lang_name = self.whisper_lang_var.get()
        lang_code = WHISPER_LANGUAGES.get(lang_name, None)
        
        threading.Thread(target=self._whisper_thread, args=(temp_path, lang_code), daemon=True).start()

    def _whisper_thread(self, path, lang_code=None):
        try:
            device = "cuda" if torch.cuda.is_available() else "cpu"
            compute_type = "float16" if device == "cuda" else "int8"
            
            model = WhisperModel("small", device=device, compute_type=compute_type)
            segments, _ = model.transcribe(path, language=lang_code)
            
            text = " ".join([s.text for s in segments]).strip()
            
            self.root.after(0, lambda: [
                self.helper_text_area.delete("1.0", tk.END),
                self.helper_text_area.insert("1.0", text)
            ])
            
            del model
            gc.collect()
            torch.cuda.empty_cache()
            
        except Exception as e:
            err_msg = str(e)
            self.root.after(0, lambda: messagebox.showerror("Transcription Error", err_msg))
        finally:
            self.root.after(0, lambda: [
                self.btn_whisper.config(state=tk.NORMAL),
                self.set_busy(False)
            ])

    def on_recipe_select(self, event):
        name = self.recipe_var.get()
        if name in self.voice_recipes:
            self.lbl_recipe_instruct.config(text=self.voice_recipes[name]["instruct"])

    def load_recipe_script(self):
        name = self.recipe_var.get()
        if name in self.voice_recipes:
            self.helper_text_area.delete("1.0", tk.END)
            self.helper_text_area.insert("1.0", self.voice_recipes[name]["script"])

    def on_clean_script_click(self):
        text = self.helper_text_area.get("1.0", tk.END)
        # Remove timestamps
        text = re.sub(r'\d{1,2}:\d{2}:\d{2}([,.]\d+)?', '', text)
        # Remove float sequences at start of lines
        text = re.sub(r'^\s*\d+\.\d+\s+\d+\.\d+', '', text, flags=re.MULTILINE)
        
        self.helper_text_area.delete("1.0", tk.END)
        self.helper_text_area.insert("1.0", text)

    def browse_batch_out(self):
        initial_dir = os.path.join(os.getcwd(), 'tutorials', 'scripts')
        if not os.path.exists(initial_dir):
            initial_dir = os.path.join(os.getcwd(), 'tutorials')
            if not os.path.exists(initial_dir):
                initial_dir = os.getcwd()
            
        d = filedialog.askdirectory(initialdir=initial_dir)
        if d:
            self.batch_out_dir.set(d)

    def start_batch_run(self):
        raw_text = self.batch_text.get("1.0", tk.END).strip()
        lines = raw_text.splitlines()
        tasks = [l.split("|") for l in lines if "|" in l and len(l.split("|")) >= 3]
        
        if not tasks:
            messagebox.showwarning("Batch Error", "No valid tasks found. Format: Filename | Speaker | Text")
            return

        self._lock_interface(True)
        self.set_busy(True, f"Processing {len(tasks)} items...")
        
        self.batch_progress["value"] = 0
        self.batch_progress["maximum"] = len(tasks)
        
        threading.Thread(target=self.run_batch_task, args=(tasks,), daemon=True).start()

    def run_batch_task(self, tasks):
        output_dir = self.batch_out_dir.get()
        temp = self.temp_var.get()
        top_p = self.top_p_var.get()

        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        for i, task in enumerate(tasks):
            if self.cancel_signal.is_set():
                break
                
            try:
                fname, speaker_raw, text = [x.strip() for x in task]
                speaker_clean = speaker_raw.split(" ")[0]
                
                known_speakers = ["Vivian", "Eric", "Ryan", "Aiden", "Serena"]
                
                if speaker_clean in known_speakers:
                    final_speaker = speaker_clean
                    instruction = None
                else:
                    final_speaker = "Eric" 
                    instruction = speaker_raw 

                wavs, sr = self.model.generate_custom_voice(
                    text=text,
                    speaker=final_speaker,
                    instruct=instruction,
                    temperature=temp,
                    top_p=top_p
                )
                
                sf.write(os.path.join(output_dir, f"{fname}.wav"), wavs[0], sr)
                self.root.after(0, lambda v=i+1: self.batch_progress.configure(value=v))
                
            except Exception as e:
                print(f"Batch failed on item {i}: {e}")

        self.root.after(0, lambda: [
            self.set_busy(False),
            self._lock_interface(False),
            messagebox.showinfo("Batch Complete", "Batch processing finished.")
        ])

    def draw_waveform(self):
        self.wave_canvas.delete("all")
        if self.helper_audio_data is None:
            return

        is_dark = self.app_config.get("dark_mode", False)
        wave_color = "#00ff00" if not is_dark else "#4ec9b0" # Bright Green or Teal
        
        w = self.wave_canvas.winfo_width()
        h = self.wave_canvas.winfo_height()
        data = self.helper_audio_data
        
        if len(data.shape) > 1:
            data = data[:, 0]

        # Optimization: Cap at MAX_WAVEFORM_POINTS
        step = max(1, len(data) // MAX_WAVEFORM_POINTS)
        vis_data = data[::step]
        
        # Normalize
        max_val = np.max(np.abs(vis_data))
        if max_val > 0:
            vis_data = vis_data / max_val
            
        mid = h / 2
        scale = (h / 2) * 0.9
        
        points = []
        for i, val in enumerate(vis_data):
            x = (i / len(vis_data)) * w
            y = mid - (val * scale)
            points.extend([x, y])

        if points:
            self.wave_canvas.create_line(points, fill=wave_color, width=1)
            
        if self.trim_start > 0:
            x = (self.trim_start / len(data)) * w
            self.wave_canvas.create_line(x, 0, x, h, fill="#f1c40f" if not is_dark else "#d19a66", width=2)
            
        if self.trim_end > 0:
            x = (self.trim_end / len(data)) * w
            self.wave_canvas.create_line(x, 0, x, h, fill="#e74c3c" if not is_dark else "#f44747", width=2)

    # --- OTHER METHODS (Kept largely the same but reformatted) ---
    
    def populate_default_styles(self):
        defaults = {
            "Heartbroken": "Trembling voice, holding back tears, slow pace, frequent pauses, sorrowful and broken.",
            "Furious": "Aggressive, shouting, very fast pace, sharp articulation, intense anger, slamming words.",
            "Panicked": "Breathless, fast pace, high pitch, stuttering slightly, terrified, hyperventilating.",
            "Sarcastic": "Bored tone, slow drawl, emphasizing the wrong words, rolling eyes, dry humor.",
            "Overjoyed": "Laughing voice, high energy, fast pace, smiling while speaking, ecstatic.",
            "Seductive": "Low pitch, breathy texture, very slow, close to microphone, intimate whisper.",
            "Villain": "Low, menacing whisper. Slow and calculated. Arrogant tone. Cold and gravelly.",
            "Horror Narrator": "Deep, gravelly whisper, slow and ominous, eerie pauses, threatening tone.",
            "News Anchor": "Professional, neutral tone, clear articulation, even pacing, authoritative, no emotion.",
            "The Drunk": "Slurred speech, uneven rhythm, fluctuating pitch, hiccuping, slow and confused.",
            "Old Radio": "Mid-Atlantic accent, fast pace, energetic, sharp and punchy, enthusiastic announcer.",
            "Exhausted": "Yawning, heavy sighs, monotone, very slow, dragging words, sleepy.",
            "ASMR": "Soft whisper, extremely close to mic, mouth sounds, slow and gentle, relaxing.",
            "Dying Breath": "Weak, fading voice, long pauses, shallow breathing, barely audible."
        }
        
        if "style_instructions" not in self.app_config:
            self.app_config["style_instructions"] = {}
            
        # Only add if empty or missing defaults
        for name, instr in defaults.items():
            if name not in self.app_config["style_instructions"]:
                self.app_config["style_instructions"][name] = instr
        
        self.update_style_combo()

    def update_style_combo(self):
        styles = sorted(list(self.app_config.get("style_instructions", {}).keys()))
        if hasattr(self, 'style_combo_custom'):
            self.style_combo_custom['values'] = styles
        if hasattr(self, 'style_combo_design'):
            self.style_combo_design['values'] = styles

    def open_voice_set_dialog(self, mode="design"):
        """Opens a dialog to select styles for generating a voice set."""
        # 1. Ensure Model
        target_model = "design" if mode == "design" else ("custom" if mode == "custom" else "base")
        if not self.ensure_model(target_model):
            return

        # 2. Setup Dialog
        d = tk.Toplevel(self.root)
        d.title("Generate Voice Set")
        d.geometry("400x500")
        try:
            x = self.root.winfo_rootx() + 50
            y = self.root.winfo_rooty() + 50
            d.geometry(f"+{x}+{y}")
        except: pass

        tk.Label(d, text="Select Styles to Generate", font=("Segoe UI", 12, "bold"), pady=10).pack()
        
        # 3. List Styles
        scroll = scrolledtext.ScrolledText(d, width=40, height=20, cursor="arrow")
        scroll.pack(padx=10, pady=5, fill=tk.BOTH, expand=True)
        
        style_vars = {}
        styles = sorted(list(self.app_config.get("style_instructions", {}).keys()))
        
        # Default checked items
        defaults = ["ASMR", "Furious", "Heartbroken", "Overjoyed", "News Anchor", "Seductive"]
        
        chk_frame = tk.Frame(scroll.window_create("end", window=tk.Frame(scroll))) # Trick to put frame in text
        
        for s in styles:
            var = tk.BooleanVar(value=(s in defaults))
            cb = tk.Checkbutton(scroll, text=s, variable=var, bg=self.colors["panel_bg"], anchor="w")
            scroll.window_create("end", window=cb)
            scroll.insert("end", "\n")
            style_vars[s] = var
            
        scroll.configure(state="disabled")

        # 4. Run Button
        def on_run():
            selected = [s for s, v in style_vars.items() if v.get()]
            if not selected:
                messagebox.showwarning("Empty", "Select at least one style.")
                return
            d.destroy()
            self.run_voice_set_generation(mode, selected)

        tk.Button(d, text="▶ Generate Set", command=on_run, bg=self.colors["accent"], fg="white", font=("Segoe UI", 10, "bold"), pady=5).pack(fill=tk.X, padx=10, pady=10)

    def run_voice_set_generation(self, mode, selected_styles):
        voice_name = ""
        current_script = ""
        
        if mode == "design":
            voice_name = self.new_des_profile_name.get().strip() or "NewDesign"
            current_script = self.txt_design_target.get("1.0", tk.END).strip()
        elif mode == "custom":
            raw_spk = self.speaker_var.get()
            voice_name = raw_spk.split(" ")[0]
            current_script = self.text_input_custom.get("1.0", tk.END).strip()
        else:
            voice_name = self.clone_profile_var.get() or "CloneVoice"
            current_script = self.target_text_input.get("1.0", tk.END).strip()

        self.set_busy(True, f"Generating set for {voice_name}...")
        self._lock_interface(True)
        
        threading.Thread(target=self._voice_set_worker, args=(mode, voice_name, selected_styles, current_script), daemon=True).start()

    def _voice_set_worker(self, mode, voice_name, styles, script_override=""):
        try:
            ts = time.strftime("%Y%m%d-%H%M%S")
            folder_name = f"Set_{voice_name}_{ts}"
            target_dir = os.path.join(self.temp_dir, folder_name)
            os.makedirs(target_dir, exist_ok=True)
            
            temp = self.temp_var.get()
            top_p = self.top_p_var.get()
            
            total = len(styles)
            
            for i, style_name in enumerate(styles):
                if self.cancel_signal.is_set(): break
                
                self.root.after(0, lambda m=f"Generating: {style_name} ({i+1}/{total})...": self.status_var.set(m))
                
                instruct = self.app_config["style_instructions"].get(style_name, "")
                
                # Priority: 1. Current UI script, 2. Demo script, 3. Generic
                text = script_override if script_override else STYLE_DEMO_SCRIPTS.get(style_name, GENERIC_SCRIPT)
                
                if mode == "design":
                    wavs, sr = self.model.generate_voice_design(
                        text=text,
                        voice_description=self.txt_design_desc.get("1.0", tk.END).strip(),
                        instruct=instruct,
                        temperature=temp, top_p=top_p
                    )
                elif mode == "custom":
                    raw_spk = self.speaker_var.get()
                    clean_spk = raw_spk.split(" ")[0]
                    wavs, sr = self.model.generate_custom_voice(
                        text=text,
                        speaker=clean_spk,
                        instruct=instruct,
                        temperature=temp, top_p=top_p
                    )
                else:
                    # Clone mode
                    ref = self.ref_audio_path.get()
                    if self.locked_voice_prompt:
                        wavs, sr = self.model.generate_voice_clone(
                            text=text, language=self.lang_var_clone.get(),
                            voice_clone_prompt=self.locked_voice_prompt,
                            temperature=temp, top_p=top_p
                        )
                    else:
                        wavs, sr = self.model.generate_voice_clone(
                            text=text, language=self.lang_var_clone.get(),
                            ref_audio=ref, ref_text=self.ref_text_input.get("1.0", tk.END).strip(),
                            x_vector_only_mode=self.x_vector_var.get(),
                            temperature=temp, top_p=top_p
                        )
                
                # Save
                fname = f"{voice_name}_{style_name}.wav"
                sf.write(os.path.join(target_dir, fname), wavs[0], sr)
                
            self.root.after(0, lambda: [
                self.set_busy(False, "Set Complete"),
                self._lock_interface(False),
                self.refresh_history_list(),
                messagebox.showinfo("Complete", f"Voice Set finished!\nFiles saved in: {folder_name}")
            ])
        except Exception as e:
            err_msg = str(e)
            self.root.after(0, lambda: [self.set_busy(False), self._lock_interface(False), messagebox.showerror("Error", err_msg)])

    def on_save_style(self, tab="custom"):
        if tab == "custom":
            instr = self.instruct_input.get().strip()
            name = self.new_style_name_custom.get().strip()
        else:
            instr = self.txt_design_instruct.get().strip()
            name = self.new_style_name_design.get().strip()
            
        if not instr:
            messagebox.showwarning("Error", "Instruction field is empty.")
            return
            
        if not name:
            messagebox.showwarning("Error", "Please enter a name for the style.")
            return
            
        self.app_config["style_instructions"][name] = instr
        self.save_app_config()
        self.update_style_combo()
        if tab == "custom":
            self.style_var_custom.set(name)
        else:
            self.style_var_design.set(name)
        messagebox.showinfo("Success", f"Style '{name}' saved.")

    def on_delete_style(self, tab="custom"):
        name = self.style_var_custom.get() if tab == "custom" else self.style_var_design.get()
        if name in self.app_config.get("style_instructions", {}):
            if messagebox.askyesno("Confirm", f"Delete style '{name}'?"):
                del self.app_config["style_instructions"][name]
                self.save_app_config()
                self.update_style_combo()
                if tab == "custom": self.style_var_custom.set("")
                else: self.style_var_design.set("")

    def on_style_select(self, tab="custom"):
        name = self.style_var_custom.get() if tab == "custom" else self.style_var_design.get()
        instr = self.app_config.get("style_instructions", {}).get(name)
        if instr:
            if tab == "custom":
                self.instruct_input.delete(0, tk.END)
                self.instruct_input.insert(0, instr)
            else:
                self.txt_design_instruct.delete(0, tk.END)
                self.txt_design_instruct.insert(0, instr)

    def on_custom_speaker_select(self, event=None):
        # We no longer auto-overwrite the script. 
        # This is now handled by load_custom_demo_script.
        pass

    def load_custom_demo_script(self):
        val = self.speaker_var.get()
        name = val.split(" ")[0]
        if name in CUSTOM_VOICE_SCRIPTS:
            if not self.text_input_custom.get("1.0", tk.END).strip() or messagebox.askyesno("Load Demo", "Overwrite current text with speaker demo script?"):
                self.text_input_custom.delete("1.0", tk.END)
                self.text_input_custom.insert("1.0", CUSTOM_VOICE_SCRIPTS[name])

    def on_wave_click(self, event):
        if self.helper_audio_data is None:
            return
        frame = int((event.x / self.wave_canvas.winfo_width()) * len(self.helper_audio_data))
        if event.num == 1:
            self.trim_start = frame
        elif event.num == 3:
            self.trim_end = frame
        self.draw_waveform()
        self.btn_crop.config(state=tk.NORMAL)

    def crop_audio(self):
        if self.helper_audio_data is None: return
        start = self.trim_start
        end = self.trim_end
        if end == 0: end = len(self.helper_audio_data)
        
        if start >= end:
            messagebox.showwarning("Crop Error", "Invalid selection. Left-click for Start, Right-click for End.")
            return

        self.audio_history.append(self.helper_audio_data.copy())
        self.helper_audio_data = self.helper_audio_data[start:end]
        self.trim_start = 0
        self.trim_end = 0
        
        # Update temp file so other tabs/Whisper use the cropped version
        try:
            ts = time.strftime("%H%M%S")
            temp_path = os.path.join(self.temp_dir, f"crop_temp_{ts}.wav")
            sf.write(temp_path, self.helper_audio_data, self.helper_samplerate)
            self.helper_file_path = temp_path
        except: pass

        self.draw_waveform()
        self.helper_update_time_label()
        self.btn_undo.config(state=tk.NORMAL)
        self.btn_crop.config(state=tk.DISABLED)

    def undo_audio(self):
        if not self.audio_history: return
        self.helper_audio_data = self.audio_history.pop()
        self.trim_start = 0
        self.trim_end = 0

        # Update temp file for consistency
        try:
            ts = time.strftime("%H%M%S")
            temp_path = os.path.join(self.temp_dir, f"undo_temp_{ts}.wav")
            sf.write(temp_path, self.helper_audio_data, self.helper_samplerate)
            self.helper_file_path = temp_path
        except: pass

        self.draw_waveform()
        self.helper_update_time_label()
        if not self.audio_history:
            self.btn_undo.config(state=tk.DISABLED)

    def toggle_recording(self):
        if self.is_recording: self.stop_recording()
        else: self.start_recording()

    def start_recording(self):
        # Ensure 'temp' directory exists in the current working directory for recordings
        recording_temp_dir = os.path.join(os.getcwd(), 'temp')
        os.makedirs(recording_temp_dir, exist_ok=True)
        self.helper_stop_audio()
        self.recorded_frames = []
        self.is_recording = True
        self.btn_record.config(text="⏹ Stop", style="Panic.TButton")
        self.btn_save_rec.config(state=tk.DISABLED)
        
        self.recording_start_time = time.time()
        self._update_recording_timer()
        
        def cb(indata, frames, time_info, status):
            if status:
                print(f"Recording status: {status}")
            self.recorded_frames.append(indata.copy())
        
        try:
            device_name = self.mic_device_var.get()
            device_id = self.mic_devices.get(device_name)

            self.recording_stream = sd.InputStream(
                device=device_id,
                channels=1, 
                callback=cb, 
                samplerate=44100
            )
            self.recording_stream.start()
        except Exception as e:
            messagebox.showerror("Recording Error", f"Failed to start recording:\n{str(e)}\n\nPlease check:\n1. Microphone is connected\n2. Microphone permissions are enabled\n3. No other app is using the microphone")
            self.stop_recording()
    def stop_recording(self):
        if self.recording_stream:
            try:
                self.recording_stream.stop()
                self.recording_stream.close()
            except Exception as e:
                print(f"Error closing recording stream: {e}")
            
        self.is_recording = False
        self.btn_record.config(text="🔴 Record", style="TButton")
        
        if not self.recorded_frames:
            # Check if any audio was actually captured.
            messagebox.showwarning(
                "Recording Error",
                "No audio was recorded. Please check that your microphone is connected and that the application has permission to use it."
            )
            return

        if self.recorded_frames:
            self.helper_audio_data = np.concatenate(self.recorded_frames, axis=0)
            self.btn_save_rec.config(state=tk.NORMAL)
            self.draw_waveform()
            self.helper_update_time_label()
            self.lbl_helper_file.config(text="[Recorded Audio]")

            # Auto-Save Recording to History
            try:
                ts = time.strftime("%Y%m%d-%H%M%S")
                # Grab text from helper text area for the filename snippet
                txt_src = self.helper_text_area.get("1.0", tk.END).strip()
                if not txt_src: 
                    txt_src = "Recording"
                
                txt_snip = re.sub(r'[^a-zA-Z0-9]', '', txt_src)[:15]
                fname = f"{ts}_Rec_{txt_snip}.wav"
                
                save_path = os.path.join(self.temp_dir, fname)
                sf.write(save_path, self.helper_audio_data, 44100)
                self.helper_samplerate = 44100
                self.helper_file_path = save_path
                
                self.root.after(0, self.refresh_history_list)
            except Exception as e:
                print(f"Auto-save recording failed: {e}")

    def _update_recording_timer(self):
        if self.is_recording:
            elapsed = time.time() - self.recording_start_time
            mins = int(elapsed // 60)
            secs = int(elapsed % 60)
            self.lbl_helper_time.config(text=f"Recording: {mins:02d}:{secs:02d}")
            self.root.after(100, self._update_recording_timer)

    def save_recorded_audio(self):
        """Save the recorded audio with proper path handling."""
        if self.helper_audio_data is None:
            messagebox.showwarning("No Recording", "No audio to save.")
            return

        # Ensure saved_assets folder exists
        os.makedirs(self.assets_dir, exist_ok=True)
        
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        filename = f"{timestamp}_Rec_Recording.wav"
        filepath = os.path.join(self.assets_dir, filename)
        
        try:
            sf.write(filepath, self.helper_audio_data, 44100)
            
            messagebox.showinfo("Saved", f"Recording saved to:\n{filepath}")
            self.refresh_history_list()
            
        except Exception as e:
            messagebox.showerror("Save Failed", f"Could not save recording:\n{e}")

    def _ensure_permanent_asset(self, path):
        """Moves a file from temp to assets folder if needed to prevent deletion."""
        if not path or not os.path.exists(path):
            return path
        
        # Check if it's already in assets or outside temp
        abs_path = os.path.abspath(path)
        abs_temp = os.path.abspath(self.temp_dir)
        abs_assets = os.path.abspath(self.assets_dir)
        
        if abs_temp in abs_path:
            # It's a temp file, copy to assets
            fname = os.path.basename(path)
            dst = os.path.join(self.assets_dir, fname)
            
            # Avoid collision
            if os.path.exists(dst):
                ts = time.strftime("%H%M%S")
                fname = f"{ts}_{fname}"
                dst = os.path.join(self.assets_dir, fname)
            
            try:
                shutil.copy2(path, dst)
                return dst
            except Exception as e:
                print(f"Failed to copy asset: {e}")
                return path
        return path

    def on_save_profile(self):
        n = self.new_profile_name.get()
        if not n:
            messagebox.showwarning("Error", "Please enter a profile name.")
            return
            
        txt = self.helper_text_area.get("1.0", tk.END).strip()
        
        if not self.helper_file_path and self.helper_audio_data is not None:
            if messagebox.askyesno("Save Audio", "You must save the recorded audio to a file before creating a profile. Save now?"):
                self.save_recorded_audio()
                
        if not self.helper_file_path:
            messagebox.showwarning("Error", "No audio file associated with this profile.")
            return

        # Ensure the file is permanent
        final_path = self._ensure_permanent_asset(self.helper_file_path)

        self.voice_configs[n] = {
            "audio_path": final_path,
            "transcript": txt,
            "temp": self.temp_var.get(),
            "top_p": self.top_p_var.get(),
            "whisper_lang": self.whisper_lang_var.get()
        }
        self.save_app_config()
        self.update_profile_combo()
        self.profile_var.set(n)
        messagebox.showinfo("Success", f"Profile '{n}' saved (Asset secured).")
        
        # --- NEW: Refresh Batch Director ---
        if hasattr(self, 'director'):
            # This forces the block creation logic to see new profiles
            pass # The Director pulls dynamically on "Add Block", so strictly not needed, 
                 # but good to know for future updates.

    def on_load_profile(self):
        n = self.profile_var.get()
        if n in self.voice_configs:
            data = self.voice_configs[n]
            if os.path.exists(data["audio_path"]):
                self.load_helper_audio_from_path(data["audio_path"])
            else:
                messagebox.showwarning("Warning", f"Audio file not found: {data['audio_path']}")
            
            self.helper_text_area.delete("1.0", tk.END)
            self.helper_text_area.insert("1.0", data["transcript"])
            
            if not self.lock_sliders_var.get():
                if "temp" in data: self.temp_var.set(data["temp"])
                if "top_p" in data: self.top_p_var.set(data["top_p"])
                self.update_precision_labels()
            
            if "whisper_lang" in data:
                self.whisper_lang_var.set(data["whisper_lang"])
            else:
                self.whisper_lang_var.set("Auto")

            self.on_whisper_lang_change()

    def update_current_profile(self, tab="helper"):
        n = self.profile_var.get() if tab == "helper" else self.clone_profile_var.get()
        if not n or n not in self.voice_configs:
            messagebox.showwarning("Error", "No profile loaded to update.")
            return
            
        if messagebox.askyesno("Update Profile", f"Overwrite '{n}' slider values with current settings?"):
            self.voice_configs[n]["temp"] = self.temp_var.get()
            self.voice_configs[n]["top_p"] = self.top_p_var.get()
            self.save_app_config()
            messagebox.showinfo("Success", f"Profile '{n}' updated.")

    def on_delete_profile(self):
        n = self.profile_var.get()
        if n in self.voice_configs:
            if messagebox.askyesno("Confirm", f"Delete profile '{n}'?"):
                del self.voice_configs[n]
                self.save_app_config()
                self.update_profile_combo()
                self.profile_var.set("")

    # --- MISSING PROFILE METHODS ---
    def update_profile_combo(self):
        """Updates the profile combobox in the Helper tab."""
        profiles = sorted(list(self.voice_configs.keys()))
        self.profile_combo['values'] = profiles
        if profiles:
            current = self.profile_var.get()
            if current not in profiles:
                 self.profile_combo.current(0)
        # Sync with Clone tab
        if hasattr(self, 'clone_profile_combo'):
            self.clone_profile_combo['values'] = profiles

    def update_clone_profile_combo(self):
        """Updates the profile combobox in the Clone tab."""
        profiles = sorted(list(self.voice_configs.keys()))
        self.clone_profile_combo['values'] = profiles
        if profiles:
            current = self.clone_profile_var.get()
            if current not in profiles:
                self.clone_profile_combo.current(0)

    def load_clone_profile(self):
        """Loads a saved profile into the Clone tab."""
        n = self.clone_profile_var.get()
        if n in self.voice_configs:
            data = self.voice_configs[n]
            if os.path.exists(data["audio_path"]):
                self.ref_audio_path.set(data["audio_path"])
            else:
                messagebox.showwarning("Warning", f"Audio file not found: {data['audio_path']}")
            
            self.ref_text_input.delete("1.0", tk.END)
            self.ref_text_input.insert("1.0", data["transcript"])
            
            if not self.lock_sliders_var.get():
                if "temp" in data: self.temp_var.set(data["temp"])
                if "top_p" in data: self.top_p_var.set(data["top_p"])
                self.update_precision_labels()
            
            self.status_var.set(f"Loaded profile: {n}")

    def update_des_profile_combo(self):
        """Updates the profile combobox in the Design tab."""
        profiles = sorted(list(self.design_profiles.keys()))
        self.des_profile_combo['values'] = profiles
        if profiles:
             current = self.des_profile_var.get()
             if current not in profiles:
                self.des_profile_combo.current(0)

    def load_design_profile(self, event=None):
        """Loads a design profile."""
        n = self.des_profile_var.get()
        if n in self.design_profiles:
            data = self.design_profiles[n]
            
            self.txt_design_desc.delete("1.0", tk.END)
            self.txt_design_desc.insert("1.0", data.get("desc", ""))
            
            self.txt_design_instruct.delete(0, tk.END)
            self.txt_design_instruct.insert(0, data.get("instruct", ""))
            
            if not self.lock_design_script_var.get():
                self.txt_design_target.delete("1.0", tk.END)
                self.txt_design_target.insert("1.0", data.get("script", ""))
            
            # Also set temp/top_p if they exist in profile
            if "temp" in data: self.temp_var.set(data["temp"])
            if "top_p" in data: self.top_p_var.set(data["top_p"])
            self.update_precision_labels()
            
            self.status_var.set(f"Loaded design: {n}")

    def save_design_profile(self):
        """Saves the current design inputs as a profile."""
        n = self.new_des_profile_name.get().strip()
        if not n:
            messagebox.showwarning("Error", "Please enter a name for the design profile.")
            return
            
        self.design_profiles[n] = {
            "desc": self.txt_design_desc.get("1.0", tk.END).strip(),
            "instruct": self.txt_design_instruct.get().strip(),
            "script": self.txt_design_target.get("1.0", tk.END).strip(),
            "temp": self.temp_var.get(),
            "top_p": self.top_p_var.get()
        }
        self.save_app_config()
        self.update_des_profile_combo()
        self.des_profile_var.set(n)
        messagebox.showinfo("Success", f"Design profile '{n}' saved.")

    def delete_design_profile(self):
        """Deletes the selected design profile."""
        n = self.des_profile_var.get()
        if n in self.design_profiles:
            if n in self.voice_recipes:
                messagebox.showwarning("Protected", "Cannot delete built-in recipes.")
                return
                
            if messagebox.askyesno("Confirm", f"Delete design profile '{n}'?"):
                del self.design_profiles[n]
                self.save_app_config()
                self.update_des_profile_combo()
                self.des_profile_var.set("")

    def send_to_voice_clone(self):
        if not self.helper_file_path and self.helper_audio_data is not None:
             if messagebox.askyesno("Unsaved Audio", "Save audio now to use in Voice Clone?"):
                 self.save_recorded_audio()

        if self.helper_file_path: 
            self.ref_audio_path.set(self.helper_file_path)
            self.ref_text_input.delete("1.0", tk.END)
            self.ref_text_input.insert("1.0", self.helper_text_area.get("1.0", tk.END).strip())
            self.notebook.select(self.tab_clone)
            self.status_var.set(f"Sent audio and transcript to Voice Clone tab.")
        else:
            messagebox.showwarning("No Audio", "Please load or record (and save) audio first.")

    def show_context_help(self, title, content):
        h = tk.Toplevel(self.root)
        h.title(title)
        h.geometry("460x400")
        h.resizable(True, True)
        try:
            x = self.root.winfo_x() + (self.root.winfo_width()//2) - 230
            y = self.root.winfo_y() + (self.root.winfo_height()//2) - 200
            h.geometry(f"+{x}+{y}")
        except: pass

        # Header bar
        bar = tk.Frame(h, bg=self.colors["accent"], pady=7)
        bar.pack(fill=tk.X)
        tk.Label(bar, text=f"  {title}", font=("Segoe UI", 11, "bold"),
                 bg=self.colors["accent"], fg="white").pack(side=tk.LEFT, padx=8)

        # Content
        txt = tk.Text(h, font=("Segoe UI", 10), wrap=tk.WORD, bg="white",
                      fg=self.colors["fg"], relief=tk.FLAT, padx=18, pady=14,
                      cursor="arrow")
        _configure_help_tags(txt, self.colors, base_h1=13)
        _render_help_text(txt, content)
        txt.config(state=tk.DISABLED)

        scroll = ttk.Scrollbar(h, orient="vertical", command=txt.yview)
        txt.configure(yscrollcommand=scroll.set)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        txt.pack(fill=tk.BOTH, expand=True)

        close_bar = tk.Frame(h, bg=self.colors["header_bg"], pady=5)
        close_bar.pack(fill=tk.X, side=tk.BOTTOM)
        ttk.Button(close_bar, text="Close", command=h.destroy).pack(pady=2)

    def show_settings_dialog(self):
        d = tk.Toplevel(self.root)
        d.title("System Status")
        d.geometry("500x150")
        d.resizable(False, False)
        try:
            x = self.root.winfo_rootx() + (self.root.winfo_width()//2) - 250
            y = self.root.winfo_rooty() + (self.root.winfo_height()//2) - 75
            d.geometry(f"+{x}+{y}")
        except: pass

        main_frame = ttk.Frame(d, padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(main_frame, text="System Status", font=("Segoe UI", 12, "bold")).pack(pady=(0, 15))

        # SoX Status
        sox_f = ttk.Frame(main_frame)
        sox_f.pack(fill=tk.X)
        ttk.Label(sox_f, text="SoX Audio Utility:", font=("Segoe UI", 10, "bold")).pack(side=tk.LEFT)
        
        sox_found = os.path.exists(os.path.join(sox_path, "sox.exe"))
        status_text = "✅ Loaded Successfully" if sox_found else "❌ NOT FOUND"
        status_color = self.colors["success"] if sox_found else self.colors["danger"]
        
        tk.Label(sox_f, text=status_text, fg=status_color, font=("Segoe UI", 10, "bold")).pack(side=tk.LEFT, padx=10)

        path_label = ttk.Label(main_frame, text=f"Path: {sox_path}", font=("Consolas", 9), foreground="grey", wraplength=450, justify=tk.LEFT)
        path_label.pack(anchor="w", pady=(5,0))

        ttk.Button(main_frame, text="Close", command=d.destroy).pack(side=tk.BOTTOM, pady=(15,0))

    def setup_hub_tab(self):
        """Builds the Module Manager interface inside the main notebook."""
        f = tk.Frame(self.tab_hub, padx=30, pady=20)
        f.pack(fill=tk.BOTH, expand=True)
        
        header = tk.Frame(f)
        header.pack(fill=tk.X, pady=(0, 20))
        
        tk.Label(header, text="Module Manager & Extension Hub", font=("Segoe UI", 16, "bold"), fg=self.colors["accent"]).pack(side=tk.LEFT)
        
        sync_btn = ttk.Button(header, text="Check for New Plugins", width=25)
        sync_btn.pack(side=tk.RIGHT)

        # Info Panel
        info_f = tk.Frame(f, bg=self.colors["header_bg"], padx=15, pady=15)
        info_f.pack(fill=tk.X, pady=(0, 20))
        tk.Label(info_f, text="Dynamically extend Qwen3 Studio by enabling plugins below. Newly enabled plugins appear as new tabs immediately.",
                 font=("Segoe UI", 10, "italic"), bg=self.colors["header_bg"], fg=self.colors["muted"]).pack(anchor="w")

        # Scrollable List Area
        list_f = ttk.LabelFrame(f, text=" Plugin Inventory ", padding=10)
        list_f.pack(fill=tk.BOTH, expand=True)
        
        canvas = tk.Canvas(list_f, highlightthickness=0, bg="#ffffff")
        scroll = ttk.Scrollbar(list_f, orient="vertical", command=canvas.yview)
        scroll_f = tk.Frame(canvas, bg="#ffffff")
        
        scroll_f.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scroll_f, anchor="nw", width=1050)
        canvas.configure(yscrollcommand=scroll.set)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        def refresh_hub_list():
            try:
                dir_contents = os.listdir(self.modules_dir)
            except Exception as e:
                dir_contents = [f"ERROR: {e}"]

            for widget in scroll_f.winfo_children(): widget.destroy()
            
            if not os.path.exists(self.modules_dir):
                os.makedirs(self.modules_dir, exist_ok=True)
                tk.Label(scroll_f, text=f"Modules folder created at:\n{self.modules_dir}\n(Add .py plugin files here)", font=("Segoe UI", 10, "italic"), bg="#ffffff").pack(pady=40)
                return
                
            files = [f for f in dir_contents if f.endswith(".py") and not f.startswith("__")]
            if not files:
                tk.Label(scroll_f, text="No modules found in ./modules/", font=("Segoe UI", 10, "italic"), bg="#ffffff").pack(pady=40)
                return
                
            for f_name in sorted(files):
                # Safeguard: Never show the module manager plugin in its own list.
                if f_name == "autoscript_plugin.py":
                    continue
                    
                is_enabled = self.hub.is_enabled(f_name)
                is_loaded = f_name in self.loaded_plugins
                is_new = f_name in self._new_modules
                
                # Container row
                row = tk.Frame(scroll_f, pady=5, bg="#ffffff", bd=1, relief="flat")
                row.pack(fill=tk.X, pady=2, padx=5)
                
                # Status Color
                color = "#2ecc71" if is_enabled else "#e74c3c" # Green or Red
                if is_new: color = "#f1c40f" # Yellow for new
                
                lbl_status = tk.Label(row, text="●", fg=color, bg="#ffffff", font=("Segoe UI", 14))
                lbl_status.pack(side=tk.LEFT, padx=10)
                
                display_text = f_name
                if is_new: display_text += " [NEW!]"
                if is_loaded and is_enabled: display_text += " (Loaded)"
                
                # Module Name & Toggle
                def toggle(name=f_name):
                    current = self.hub.is_enabled(name)
                    self.hub.toggle_module(name, not current)
                    if not current: # Just enabled
                        self.load_external_modules()
                    # Refresh is handled by toggle_module -> on_refresh
                
                btn_style = "TButton"
                btn = tk.Button(row, text=display_text, font=("Segoe UI", 11, "bold" if is_enabled else "normal"), 
                                anchor="w", relief=tk.FLAT, bg="#ffffff", command=toggle,
                                activebackground="#f0f0f0", fg=self.colors["fg"] if is_enabled else "#95a5a6")
                btn.pack(side=tk.LEFT, fill=tk.X, expand=True)

                # Valid Header Indicator
                try:
                    with open(os.path.join(self.modules_dir, f_name), 'r', encoding='utf-8') as mod_file:
                        content = mod_file.read()
                        if "def initialize(app):" in content:
                            tk.Label(row, text="[Blues-Approved]", fg=self.colors["accent"], font=("Segoe UI", 9, "bold"), bg=self.colors["panel_bg"]).pack(side=tk.RIGHT, padx=15)
                except: pass

                # Enable/Disable switch
                switch_text = "DISABLE" if is_enabled else "ENABLE"
                switch_color = "#e74c3c" if is_enabled else "#2ecc71"
                tk.Button(row, text=switch_text, command=toggle, bg=switch_color, fg="white",
                          font=("Segoe UI", 9, "bold"), width=10, bd=0).pack(side=tk.RIGHT, padx=5)

        self.hub.on_refresh = lambda: self.root.after(0, refresh_hub_list)
        refresh_hub_list()
        
        def run_sync():
            sync_btn.config(state=tk.DISABLED, text="Checking GitHub...")
            def on_sync_done(status, msg, new_files):
                if status == "success":
                    self._new_modules.update(new_files)
                
                self.root.after(0, lambda: [
                    sync_btn.config(state=tk.NORMAL, text="Check for New Plugins"),
                    refresh_hub_list(),
                    messagebox.showinfo("Sync", msg) if status == "success" else messagebox.showerror("Sync Error", msg)
                ])
            self.hub.sync_from_github(on_sync_done)
            
        sync_btn.config(command=run_sync)

    def show_help_guide(self):
        if hasattr(self, 'help_window') and self.help_window is not None and self.help_window.winfo_exists():
            self.help_window.lift()
            return

        self.help_window = tk.Toplevel(self.root)
        self.help_window.title("Director's Guide")
        self.help_window.geometry("940x660")
        self.help_window.minsize(700, 480)
        try:
            icon_path = os.path.join(BASE_DIR, "pq.ico")
            if os.path.exists(icon_path):
                self.help_window.iconbitmap(icon_path)
        except: pass

        # ── Title bar ─────────────────────────────────────────────────────────
        top_bar = tk.Frame(self.help_window, bg=self.colors["accent"], pady=9)
        top_bar.pack(fill=tk.X)
        tk.Label(top_bar, text="  Director's Guide",
                 font=("Segoe UI", 13, "bold"),
                 bg=self.colors["accent"], fg="white").pack(side=tk.LEFT, padx=10)
        tk.Label(top_bar, text="Reference documentation for Qwen3 Studio",
                 font=("Segoe UI", 9),
                 bg=self.colors["accent"], fg="#d6eaf8").pack(side=tk.LEFT)

        # ── Main pane ─────────────────────────────────────────────────────────
        main_pane = ttk.PanedWindow(self.help_window, orient=tk.HORIZONTAL)
        main_pane.pack(fill=tk.BOTH, expand=True)

        # Left: topic tree
        tree_outer = tk.Frame(main_pane, bg=self.colors["header_bg"])
        tk.Label(tree_outer, text="Topics",
                 font=("Segoe UI", 9, "bold"),
                 bg=self.colors["header_bg"], fg=self.colors["muted"],
                 padx=10, pady=6).pack(anchor="w")
        tree_inner = tk.Frame(tree_outer, bg=self.colors["header_bg"])
        tree_inner.pack(fill=tk.BOTH, expand=True)

        tree = ttk.Treeview(tree_inner, show="tree", selectmode="browse")
        tree_scroll = ttk.Scrollbar(tree_inner, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=tree_scroll.set)
        tree_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        tree.tag_configure("category", font=("Segoe UI", 9, "bold"))
        tree.tag_configure("topic",    font=("Segoe UI", 9))
        main_pane.add(tree_outer, weight=1)

        # Right: content panel
        content_outer = tk.Frame(main_pane, bg="white")
        content_text = tk.Text(content_outer,
                               font=("Segoe UI", 10), wrap=tk.WORD,
                               padx=24, pady=18, bd=0, relief="flat",
                               bg="white", fg=self.colors["fg"],
                               cursor="arrow")
        _configure_help_tags(content_text, self.colors, base_h1=15)
        content_scroll = ttk.Scrollbar(content_outer, orient="vertical",
                                       command=content_text.yview)
        content_text.configure(yscrollcommand=content_scroll.set)
        content_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        content_text.pack(fill=tk.BOTH, expand=True)
        content_text.configure(state="disabled")
        main_pane.add(content_outer, weight=3)

        # ── Topic data ────────────────────────────────────────────────────────
        help_topics = {
            "Getting Started": {
                "Engines":          HELP_ENGINES,
                "Speaker Personas": HELP_PERSONAS,
                "Pro-Tips":         HELP_TIPS,
            },
            "Core Features": {
                "Voice Description": HELP_DESC,
                "Style Instruction":  HELP_INSTR,
                "Cloning a Voice":    HELP_LOCK,
                "Batch Studio":       HELP_BATCH,
                "Precision Sliders":  HELP_SLIDERS,
                "Action Tags":        HELP_TAGS,
            },
            "Advanced": {
                "Plugins & Modules": HELP_PLUGINS,
                "Tone Recipes":      HELP_RECIPES,
            },
        }

        for category, topics in help_topics.items():
            cat_id = tree.insert("", "end", text=f"  {category}",
                                 open=True, tags=("category",))
            for topic, raw in topics.items():
                tree.insert(cat_id, "end", text=f"    {topic}",
                            values=(raw,), tags=("topic",))

        def on_topic_select(event):
            sel = tree.focus()
            if sel:
                vals = tree.item(sel, "values")
                if vals:
                    content_text.configure(state="normal")
                    content_text.delete("1.0", tk.END)
                    _render_help_text(content_text, vals[0])
                    content_text.configure(state="disabled")
                    content_text.yview_moveto(0)

        tree.bind("<<TreeviewSelect>>", on_topic_select)

        try:
            first_cat   = tree.get_children()[0]
            first_topic = tree.get_children(first_cat)[0]
            tree.selection_set(first_topic)
            tree.focus(first_topic)
        except IndexError:
            pass

    def show_support_modal(self):
        modal = tk.Toplevel(self.root)
        modal.title("Support the Developer")
        modal.geometry("420x580")
        modal.configure(bg="white")
        modal.resizable(False, False)
        
        # Center modal relative to root
        try:
            x = self.root.winfo_rootx() + (self.root.winfo_width() // 2) - 210
            y = self.root.winfo_rooty() + (self.root.winfo_height() // 2) - 290
            modal.geometry(f"+{x}+{y}")
        except:
            pass
            
        modal.transient(self.root)
        modal.grab_set()
        
        # Title
        tk.Label(modal, text="Support Qwen3 Creative Suite", font=("Segoe UI", 16, "bold"), bg="white", pady=20).pack()
        
        # QR Code / Image Area
        qr_path = os.path.join(BASE_DIR, "qr-code.png")
        if os.path.exists(qr_path):
            try:
                img = Image.open(qr_path)
                # Resize to fit nicely (e.g., max 250px)
                img.thumbnail((250, 250), Image.Resampling.LANCZOS)
                self.qr_img = ImageTk.PhotoImage(img)
                
                # Make image clickable
                img_lbl = tk.Label(modal, image=self.qr_img, bg="white", borderwidth=1, relief="solid", cursor="hand2")
                img_lbl.pack(pady=10)
                img_lbl.bind("<Button-1>", lambda e: _open_url("https://buymeacoffee.com/appbyblues"))
                CreateToolTip(img_lbl, "Click to open support page")
            except Exception as e:
                print(f"Error loading image: {e}")
                tk.Label(modal, text="[Support Image]", bg="white", fg="grey", font=("Segoe UI", 10)).pack(pady=10)
        
        # Message
        msg = "If you find this tool useful, consider supporting its development.\nEvery coffee helps keep the engine running!"
        tk.Label(modal, text=msg, font=("Segoe UI", 11), bg="white", pady=15, justify="center").pack()
        
        # Branded Link Button (BMC Yellow: #FFDD00)
        btn_frame = tk.Frame(modal, bg="#FFDD00", bd=0)
        btn_frame.pack(pady=15)
        
        coffee_btn = tk.Button(
            btn_frame, 
            text="☕ Buy me a coffee", 
            command=lambda: _open_url("https://buymeacoffee.com/appbyblues"),
            font=("Segoe UI", 14, "bold"),
            bg="#FFDD00",
            fg="black",
            activebackground="#f1c40f",
            relief="flat",
            padx=30,
            pady=10,
            cursor="hand2"
        )
        coffee_btn.pack()
        
        tk.Label(modal, text="https://buymeacoffee.com/appbyblues", font=("Segoe UI", 9, "underline"), bg="white", fg=self.colors["accent"], cursor="hand2").pack()
        
        ttk.Button(modal, text="Close", command=modal.destroy).pack(side=tk.BOTTOM, pady=20)

    def run_sox_command(self, args):
        # 1. SPECIAL CASE: Use FFmpeg for MP3 if available
        # This bypasses 32-bit/64-bit DLL mismatch issues with SoX
        is_mp3 = any(str(a).lower().endswith(".mp3") for a in args)
        
        if is_mp3:
            try:
                # Check for ffmpeg in PATH
                si = subprocess.STARTUPINFO()
                si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                
                # Simple check: ffmpeg -version
                subprocess.check_call(["ffmpeg", "-version"], startupinfo=si, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                
                # If we are here, ffmpeg works. 
                # Parse args to find src and dst
                # on_history_convert passes [src, dst] or [src, "-b", "16", "-C", "192", dst]
                src = args[0]
                dst = args[-1]
                
                # FFmpeg command: ffmpeg -i src -b:a 192k dst -y
                ff_args = ["ffmpeg", "-i", src, "-b:a", "192k", dst, "-y"]
                subprocess.check_call(ff_args, startupinfo=si)
                return True
            except:
                # ffmpeg not found or failed, fall back to SoX
                pass

        # 2. STANDARD: Use configured sox_path
        sox_exe = os.path.join(sox_path, "sox.exe")
        
        if not os.path.exists(sox_exe):
            # Fallback to local if configured path fails
            sox_exe = os.path.join(BASE_DIR, "sox", "sox.exe")
            
        if not os.path.exists(sox_exe):
            messagebox.showerror("Error", f"SoX not found at: {sox_exe}\n\nPlease check your System Settings (⚙).")
            return False
        
        try:
            # hide console window
            si = subprocess.STARTUPINFO()
            si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            
            # Prepare environment with custom DLL path if set
            env = os.environ.copy()
            custom_dll = self.app_config.get("mp3_dll_path")
            if custom_dll and os.path.exists(custom_dll):
                # Ensure the name is exactly what SoX expects
                if os.path.basename(custom_dll).lower() != "libmp3lame-0.dll":
                    messagebox.showwarning("DLL Name Warning", 
                        f"SoX usually requires the file to be named exactly 'libmp3lame-0.dll'.\n\n"
                        f"Your selected file is: {os.path.basename(custom_dll)}\n\n"
                        "If conversion fails, please rename your file to 'libmp3lame-0.dll'.")
                
                dll_dir = os.path.dirname(custom_dll)
                env["PATH"] = dll_dir + os.pathsep + env.get("PATH", "")

            subprocess.check_call([sox_exe] + args, startupinfo=si, env=env)
            return True
        except subprocess.CalledProcessError as e:
            msg = f"SoX Error (Exit Code {e.returncode})\n\n"
            if "mp3" in str(args).lower():
                # Diagnostic check for DLL
                folder = os.path.dirname(sox_exe)
                files = os.listdir(folder)
                dll_found = any("libmp3lame" in f.lower() for f in files)
                correct_name = "libmp3lame-0.dll"
                
                if not dll_found:
                    msg += f"MP3 Support is missing. Please download '{correct_name}' and place it in:\n{folder}"
                else:
                    # Check for common typos
                    actual_dll = next((f for f in files if "libmp3lame" in f.lower()), None)
                    if actual_dll and actual_dll.lower() != correct_name:
                        msg += f"DLL name mismatch!\nFound: {actual_dll}\nShould be: {correct_name}\n\nPlease rename the file."
                    else:
                        msg += "SoX failed to encode the MP3. This can happen if the audio format is incompatible or the DLL is 32-bit instead of 64-bit."
            else:
                msg += str(e)
            messagebox.showerror("Sox Error", msg)
            return False
        except Exception as e:
            messagebox.showerror("Sox Error", str(e))
            return False

    def on_history_normalize(self):
        if not self.selected_history_files: return
        files = list(self.selected_history_files)
        self.set_busy(True, f"Normalizing {len(files)} files...")
        
        def _task():
            for f in files:
                src = os.path.join(self.temp_dir, f)
                name, ext = os.path.splitext(f)
                dst = os.path.join(self.temp_dir, f"{name}_norm{ext}")
                self.run_sox_command([src, dst, "--norm=-1"])
            self.root.after(0, lambda: [self.refresh_history_list(), self.set_busy(False)])
        threading.Thread(target=_task, daemon=True).start()

    def on_history_convert(self, target_ext="ogg"):
        if not self.selected_history_files: return
        files = list(self.selected_history_files)
        
        # If 1 file, treat as "Export" and ask for path
        if len(files) == 1:
            src = os.path.join(self.temp_dir, files[0])
            name, _ = os.path.splitext(files[0])
            ext_map = [("Audio file", f"*.{target_ext}")]
            dst = filedialog.asksaveasfilename(defaultextension=f".{target_ext}", filetypes=ext_map, initialfile=f"{name}.{target_ext}")
            if not dst: return
            
            self.set_busy(True, f"Exporting to {target_ext.upper()}...")
            def _task_single():
                cmd_args = [src]
                if target_ext.lower() == "mp3":
                    cmd_args += ["-b", "16", "-C", "192", dst]
                else:
                    cmd_args.append(dst)
                self.run_sox_command(cmd_args)
                self.root.after(0, lambda: [self.refresh_history_list(), self.set_busy(False)])
            threading.Thread(target=_task_single, daemon=True).start()
        else:
            # Batch conversion in temp folder
            self.set_busy(True, f"Converting {len(files)} files to {target_ext.upper()}...")
            def _task_batch():
                for f in files:
                    src = os.path.normpath(os.path.join(self.temp_dir, f))
                    name, _ = os.path.splitext(f)
                    dst = os.path.normpath(os.path.join(self.temp_dir, f"{name}.{target_ext}"))
                    cmd_args = [src]
                    if target_ext.lower() == "mp3":
                        cmd_args += ["-b", "16", "-C", "192", dst]
                    else:
                        cmd_args.append(dst)
                    self.run_sox_command(cmd_args)
                self.root.after(0, lambda: [self.refresh_history_list(), self.set_busy(False)])
            threading.Thread(target=_task_batch, daemon=True).start()

    def setup_dnd(self):
        for attr, handler in [('helper_text_area', self.on_file_drop_helper), ('ref_text_input', self.on_file_drop_clone_text), ('entry_ref_audio', self.on_file_drop_clone_audio)]:
            if hasattr(self, attr):
                windnd.hook_dropfiles(getattr(self, attr), handler)

    def _decode_path(self, b):
        try:
            return b.decode('gbk')
        except:
            return b.decode('utf-8')

    def on_file_drop_helper(self, files):
        for f in files:
            p = self._decode_path(f)
            ext = os.path.splitext(p)[1].lower()
            if ext == '.txt':
                self.load_text_to_widget(p, self.helper_text_area)
            elif ext in ['.wav', '.mp3', '.ogg', '.flac']:
                self.load_helper_audio_from_path(p)

    def on_file_drop_clone_text(self, files):
        if files:
            self.load_text_to_widget(self._decode_path(files[0]), self.ref_text_input)

    def on_file_drop_clone_audio(self, files):
        if files:
            self.ref_audio_path.set(self._decode_path(files[0]))

    def load_text_to_widget(self, path, widget):
        try:
            with open(path, "r", encoding="utf-8") as f:
                c = f.read()
            widget.delete("1.0", tk.END)
            widget.insert("1.0", c)
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def setup_history_panel(self):
        if hasattr(self, 'history_window') and self.history_window is not None and self.history_window.winfo_exists():
            self.history_window.lift()
            return

        self.history_window = tk.Toplevel(self.root)
        self.history_window.title("Session History")
        self.history_window.geometry("340x600")
        self.history_window.configure(bg=self.colors["bg"])
        
        # Position to the right of main window
        self.root.update_idletasks()
        try:
            x = self.root.winfo_x() + self.root.winfo_width() + 10
            y = self.root.winfo_y()
            if x < 0: x = 10
            self.history_window.geometry(f"+{x}+{y}")
        except: 
            self.history_window.geometry("340x600+100+100")

        self.selected_history_files = set()
        self.history_item_widgets = {}

        # Scrollable Container
        container = ttk.Frame(self.history_window)
        container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.hist_canvas = tk.Canvas(container, bg=self.colors["text_bg"], highlightthickness=0)
        scrollbar = ttk.Scrollbar(container, orient="vertical", command=self.hist_canvas.yview)
        
        self.hist_scroll_frame = ttk.Frame(self.hist_canvas)
        self.hist_scroll_frame.bind("<Configure>", lambda e: self.hist_canvas.configure(scrollregion=self.hist_canvas.bbox("all")))
        
        self.hist_window_id = self.hist_canvas.create_window((0, 0), window=self.hist_scroll_frame, anchor="nw")
        self.hist_canvas.bind("<Configure>", lambda e: self.hist_canvas.itemconfig(self.hist_window_id, width=e.width))
        self.hist_canvas.configure(yscrollcommand=scrollbar.set)
        
        self.hist_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # MouseWheel — scoped to canvas only (bind_all would steal scroll from entire app)
        def _on_mousewheel(event):
            if event.delta:
                units = int(-1 * (event.delta / 120)) if abs(event.delta) >= 120 else int(-1 * event.delta)
            else:
                units = 0
            self.hist_canvas.yview_scroll(units, "units")
        def _bind_hist_mw(event):
            self.hist_canvas.bind("<MouseWheel>", _on_mousewheel)
        def _unbind_hist_mw(event):
            self.hist_canvas.unbind("<MouseWheel>")
        self.hist_canvas.bind("<Enter>", _bind_hist_mw)
        self.hist_canvas.bind("<Leave>", _unbind_hist_mw)
        if hasattr(self, 'hist_scroll_frame'):
            self.hist_scroll_frame.bind("<Enter>", _bind_hist_mw)
            self.hist_scroll_frame.bind("<Leave>", _unbind_hist_mw)

        # Preview Canvas (New)
        self.hist_preview_canvas = tk.Canvas(self.history_window, height=60, bg=self.colors["preview_bg"], highlightthickness=0)
        self.hist_preview_canvas.pack(fill=tk.X, padx=5, pady=(0, 5))

        # Context Menu
        self.hist_popup = tk.Menu(self.history_window, tearoff=0)
        self.hist_popup.add_command(label="Play", command=lambda: self.on_history_play())
        self.hist_popup.add_command(label="➡️ Send to Transcript Helper", command=self.on_history_send_to_helper)
        self.hist_popup.add_command(label="🔔 Set as Notification Sound", command=self.on_history_set_notification)
        self.hist_popup.add_command(label="Save As...", command=self.on_history_save)
        self.hist_popup.add_separator()
        self.hist_popup.add_command(label="📉 Normalize (-1dB)", command=self.on_history_normalize)
        self.hist_popup.add_command(label="🔁 Convert to OGG", command=lambda: self.on_history_convert("ogg"))
        self.hist_popup.add_command(label="🎵 Convert to MP3", command=lambda: self.on_history_convert("mp3"))
        self.hist_popup.add_separator()
        self.hist_popup.add_command(label="Delete", command=self.on_history_delete)

        # Controls
        btn_f = ttk.Frame(self.history_window, padding=5)
        btn_f.pack(fill=tk.X)
        ttk.Button(btn_f, text="▶ Play", width=8, command=lambda: self.on_history_play()).pack(side=tk.LEFT)
        ttk.Button(btn_f, text="⏹ Stop", width=8, command=self.on_stop_click).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_f, text="💾 Save", width=8, command=self.on_history_save).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_f, text="❌ Del", width=8, command=self.on_history_delete).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_f, text="🗑️ Clear All", width=10, command=self.on_history_clear).pack(side=tk.RIGHT)
        
        self.refresh_history_list()

    def refresh_history_list(self):
        if not hasattr(self, 'hist_scroll_frame') or not self.hist_scroll_frame.winfo_exists(): return
        
        for widget in self.hist_scroll_frame.winfo_children():
            widget.destroy()
        self.history_item_widgets = {}
        self.selected_history_files = set()

        if not os.path.exists(self.temp_dir): return
        
        # Recursive search for supported audio files
        all_wavs = []
        extensions = (".wav", ".mp3", ".ogg", ".flac")
        for root, dirs, filenames in os.walk(self.temp_dir):
            for f in filenames:
                if f.lower().endswith(extensions):
                    full_path = os.path.join(root, f)
                    rel_path = os.path.relpath(full_path, self.temp_dir)
                    all_wavs.append((rel_path, os.path.getmtime(full_path)))
        
        # Sort by modification time (newest first)
        all_wavs.sort(key=lambda x: x[1], reverse=True)
        
        for f_rel, _ in all_wavs:
            self._add_history_row(f_rel)

    def _add_history_row(self, filename):
        row = tk.Frame(self.hist_scroll_frame, bg=self.colors["panel_bg"], bd=1, relief="solid")
        row.pack(fill=tk.X, pady=2, padx=2)

        def _on_click(event): self._select_history_item(filename, event)
        def _on_right_click(event):
            if filename not in self.selected_history_files:
                self._select_history_item(filename, event)
            self.hist_popup.tk_popup(event.x_root, event.y_root)

        lbl = tk.Label(row, text=filename, font=("Segoe UI", 9), bg=self.colors["panel_bg"], anchor="w")
        lbl.pack(fill=tk.X, padx=4, pady=2)
        lbl.bind("<Button-1>", _on_click)
        lbl.bind("<Button-3>", _on_right_click)

        row.bind("<Button-1>", _on_click)
        row.bind("<Button-3>", _on_right_click)
        self.history_item_widgets[filename] = row

    def _select_history_item(self, filename, event=None):
        # Check for Ctrl key (state & 0x0004 on Windows)
        ctrl_pressed = event and (event.state & 0x0004)
        
        bg_normal   = self.colors["panel_bg"]
        bg_selected = self.colors["row_selected"]

        if not ctrl_pressed:
            # Standard click: clear others
            for f in list(self.selected_history_files):
                if f in self.history_item_widgets:
                    w = self.history_item_widgets[f]
                    w.config(bg=bg_normal)
                    for c in w.winfo_children(): c.config(bg=bg_normal)
            self.selected_history_files = {filename}
        else:
            # Ctrl+Click: toggle
            if filename in self.selected_history_files:
                self.selected_history_files.remove(filename)
                if filename in self.history_item_widgets:
                    w = self.history_item_widgets[f]
                    w.config(bg=bg_normal)
                    for c in w.winfo_children(): c.config(bg=bg_normal)
            else:
                self.selected_history_files.add(filename)

        # Highlight all selected
        for f in self.selected_history_files:
            if f in self.history_item_widgets:
                w = self.history_item_widgets[f]
                w.config(bg=bg_selected)
                for c in w.winfo_children(): c.config(bg=bg_selected)

        # Draw Preview for the LAST selected item
        if filename in self.selected_history_files:
            path = os.path.join(self.temp_dir, filename)
            if hasattr(self, 'hist_preview_canvas') and os.path.exists(path):
                self.hist_preview_canvas.delete("all")
                try:
                    data, sr = self.load_audio_file(path)
                    if data is not None:
                        if len(data.shape) > 1: data = data[:, 0]
                        w = self.hist_preview_canvas.winfo_width()
                        h = self.hist_preview_canvas.winfo_height()
                        if w < 10: w = 300 
                        step = max(1, len(data) // 500)
                        vis = data[::step]
                        mx = np.max(np.abs(vis))
                        if mx > 0: vis = vis / mx
                        mid = h / 2
                        scale = mid * 0.9
                        pts = []
                        for i, v in enumerate(vis):
                            x = (i / len(vis)) * w
                            pts.extend([x, mid - (v * scale)])
                        if pts: self.hist_preview_canvas.create_line(pts, fill="#00ff00", width=1)
                except: pass

    def load_audio_file(self, path):
        """Helper to load audio files, with fallback to SoX for formats like MP3 if needed."""
        try:
            # Soundfile handles many formats, but MP3 can be tricky without a backend
            data, sr = sf.read(path)
            return data, sr
        except Exception as e:
            # If sf.read fails, try to use SoX to convert to a temporary wav
            if path.lower().endswith((".mp3", ".ogg")):
                # Use a unique temp file to prevent race conditions during playback/preview
                temp_wav = os.path.join(self.temp_dir, f"_preview_temp_{time.time_ns()}.wav")
                try:
                    if self.run_sox_command([path, temp_wav]):
                        data, sr = sf.read(temp_wav)
                        return data, sr
                    else:
                        # run_sox_command failed
                        return None, None
                except Exception as read_err:
                    print(f"Failed to read converted file {temp_wav}: {read_err}")
                finally:
                    # Ensure the temporary file is cleaned up
                    if os.path.exists(temp_wav):
                        try:
                            os.remove(temp_wav)
                        except OSError:
                            # File might be in use, but we tried
                            pass
            
            print(f"Failed to load audio {path}: {e}")
            return None, None

    def on_history_play(self):
        if not self.selected_history_files:
            return
        filename = list(self.selected_history_files)[0]
        path = os.path.join(self.temp_dir, filename)
        if not os.path.exists(path):
            return

        data, sr = self.load_audio_file(path)
        if data is None:
            return

        # Keep the array alive on the instance so the GC can't free it
        # while PortAudio's C callback thread is still reading it.
        self.history_audio_data = data

        self._audio_gen += 1
        self._stop_playback_safe()
        try:
            _log_audio("PLAY", f"history:{filename}  sr={sr}  gen={self._audio_gen}")
            sd.play(self.history_audio_data, sr)
            logging.debug("AUDIO PLAY  history: sd.play() returned OK")
        except Exception as e:
            logging.error("AUDIO PLAY  history FAILED: %s\n%s", e, traceback.format_exc())

    def _stop_history_playback(self):
        """Signal any history monitor thread to stop. Caller handles sd.stop()."""
        self.history_stop_event.set()
        if self.history_playback_thread and self.history_playback_thread.is_alive():
            self.history_playback_thread.join(timeout=0.3)
        self.history_playback_thread = None
        self.history_stop_event.clear()

    def on_history_send_to_helper(self):
        if not self.selected_history_files: return
        filename = list(self.selected_history_files)[0]
        path = os.path.join(self.temp_dir, filename)
        if os.path.exists(path):
            self.load_helper_audio_from_path(path)
            self.notebook.select(self.tab_helper)
            self.status_var.set(f"Sent {filename} to Transcript Helper.")

    def on_history_save(self):
        if not self.selected_history_files: return
        files = list(self.selected_history_files)
        if len(files) == 1:
            src = os.path.join(self.temp_dir, files[0])
            ext_map = [("WAV files", "*.wav"), ("MP3 files", "*.mp3"), ("OGG files", "*.ogg"), ("FLAC files", "*.flac")]
            dst = filedialog.asksaveasfilename(defaultextension=".wav", filetypes=ext_map, initialfile=files[0])
            if dst:
                target_ext = os.path.splitext(dst)[1].lower()
                if target_ext == ".wav":
                    data, sr = self.load_audio_file(src)
                    if data is not None: sf.write(dst, data, sr)
                else:
                    # Use SoX for conversion during save
                    cmd_args = [src]
                    if target_ext == ".mp3":
                        cmd_args += ["-b", "16", "-C", "192", dst]
                    else:
                        cmd_args.append(dst)
                    self.run_sox_command(cmd_args)
        else:
            # Batch save to folder (WAV by default)
            dst_dir = filedialog.askdirectory(title="Select Folder to Save Selected Clips")
            if dst_dir:
                for f in files:
                    src = os.path.join(self.temp_dir, f)
                    data, sr = self.load_audio_file(src)
                    if data is not None:
                        sf.write(os.path.join(dst_dir, f), data, sr)
                messagebox.showinfo("Success", f"Saved {len(files)} files.")

    def on_history_delete(self):
        if not self.selected_history_files: return
        count = len(self.selected_history_files)
        msg = f"Delete {count} selected files?" if count > 1 else f"Delete {list(self.selected_history_files)[0]}?"
        if messagebox.askyesno("Confirm", msg):
            for f in list(self.selected_history_files):
                try:
                    os.remove(os.path.join(self.temp_dir, f))
                except Exception as e:
                    print(f"Delete failed for {f}: {e}")
            self.refresh_history_list()

    def on_history_clear(self):
        if messagebox.askyesno("Clear History", "Delete all temporary files?"):
            # Stop all possible playback sources
            sd.stop()
            if hasattr(self, 'on_stop_click'): self.on_stop_click()
            if hasattr(self, 'helper_stop_audio'): self.helper_stop_audio()
            
            # Force cleanup to release file handles
            self.generated_audio = None
            self.helper_audio_data = None
            gc.collect()
            
            errors = []
            for f in os.listdir(self.temp_dir):
                p = os.path.join(self.temp_dir, f)
                try: 
                    if os.path.isfile(p): os.remove(p)
                except Exception as e: 
                    errors.append(f"{f}: {e}")
            
            self.refresh_history_list()
            
            if errors:
                msg = "Could not delete some files (likely in use):\n" + "\n".join(errors[:5])
                if len(errors) > 5: msg += f"\n...and {len(errors)-5} more."
                messagebox.showwarning("Incomplete", msg)

    def on_history_set_notification(self):
        if not self.selected_history_files: return
        filename = list(self.selected_history_files)[0]
        temp_path = os.path.join(self.temp_dir, filename)
        
        # Secure the file in assets folder
        path = self._ensure_permanent_asset(temp_path)
        
        self.app_config["custom_notification_sound"] = path
        self.save_app_config()
        
        sound_name = os.path.basename(path)
        if hasattr(self, 'cb_snd_tooltip'):
             self.cb_snd_tooltip.text = f"Current Sound: {sound_name}\n(Right-click to reset)"
             
        messagebox.showinfo("Notification Sound", f"Set '{sound_name}' as the ready sound (Asset secured).")

    def reset_notification_sound(self):
        self.app_config["custom_notification_sound"] = None
        self.save_app_config()
        if hasattr(self, 'cb_snd_tooltip'):
            self.cb_snd_tooltip.text = "Current Sound: Default Beep\n(Right-click to reset)"
        messagebox.showinfo("Reset", "Notification sound reset to system beep.")

    # --- GENERATION EXECUTION ---
    def flush_vram(self):
        """Aggressively release all cached GPU memory."""
        gc.collect()
        gc.collect()  # Second pass catches circular refs freed by the first
        if torch.cuda.is_available():
            torch.cuda.synchronize()  # Wait for all pending CUDA ops before freeing
            torch.cuda.empty_cache()
            torch.cuda.ipc_collect()

    def switch_model(self, mtype, on_success=None):
        if self.current_model_type == mtype:
            if on_success: on_success()
            return
        self._model_load_event.clear()
        self.set_busy(True, f"Switching to {mtype}...")
        self._lock_interface(True)
        threading.Thread(target=self._load_model_thread, args=(mtype, on_success), daemon=True).start()

    def _load_model_thread(self, mtype, on_success=None):
        try:
            # 1. Aggressive Cleanup
            # Always run — even when model is None a worker thread may have severed it
            # without draining VRAM, so we must synchronize before loading anything new.
            if getattr(self, 'model', None) is not None:
                print("Unloading previous engine...")
                try:
                    if hasattr(self.model, 'model'):
                        del self.model.model      # destroy the heavy HF model first
                except Exception:
                    pass
                try:
                    if hasattr(self.model, 'processor'):
                        del self.model.processor
                except Exception:
                    pass
                del self.model
                self.model = None
            self.flush_vram()                     # synchronize + empty_cache always runs
            if torch.cuda.is_available():
                torch.cuda.synchronize()
            time.sleep(2)                         # give the CUDA driver time to reclaim pages
            
            p = MODEL_CUSTOM if mtype == "custom" else (MODEL_DESIGN if mtype == "design" else MODEL_BASE)
            repo_id = MODEL_REPOS.get(mtype)
            
            if self.cancel_signal.is_set(): raise Exception("Cancelled by user.")
            
            # 2. Check and Download if missing
            if not os.path.exists(os.path.join(p, "config.json")):
                print(f"Engine files missing at {p}. Downloading from {repo_id}...")
                self.root.after(0, lambda: self.set_busy(True, f"Downloading {mtype} engine..."))
                try:
                    from huggingface_hub import snapshot_download
                    snapshot_download(repo_id=repo_id, local_dir=p)
                except ImportError:
                    raise Exception("huggingface_hub library missing.")
                except Exception as e:
                    raise Exception(f"Download failed: {e}")

            print(f"Loading {mtype} engine into VRAM...")
            
    # 3. Robust Loading with Hardware Fallback (V4.0 Universal)
            try:
                if Qwen3TTSModel:
                    # Attempt GPU loading with your specific settings
                    self.model = Qwen3TTSModel.from_pretrained(
                        p, 
                        device_map="auto", 
                        torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32
                    )
                else:
                    time.sleep(1)
            except RuntimeError as e:
                # Catch "no kernel image" errors for your girlfriend's 8GB rig
                if "kernel image" in str(e).lower() or "cuda" in str(e).lower():
                    print(f"CUDA Hardware Mismatch: {e}. Falling back to CPU...")
                    self.model = Qwen3TTSModel.from_pretrained(
                        p,
                        device_map={"": "cpu"},
                        torch_dtype=torch.float32
                    )
                    self.root.after(0, lambda: messagebox.showwarning(
                        "Hardware Notice", "GPU mismatch detected. Running in CPU mode for stability."))
                else:
                    raise e
            
            self.current_model_type = mtype
            self._model_load_event.set()  # Signal waiting threads that the model is ready
            self.root.after(0, lambda: self.on_model_loaded(on_success))

        except Exception as e:
            err_msg = str(e)
            print(f"Model Load Failed: {err_msg}")
            self._model_load_event.set()  # Unblock any waiting threads even on failure
            self.root.after(0, lambda: [
                self.set_busy(False, "Load Failed"),
                messagebox.showerror("Error", err_msg),
                self._lock_interface(False)
            ])
    def on_model_loaded(self, on_success=None):
        mode_colors = {
            "custom": "#27ae60", # Green
            "design": "#2980b9", # Blue
            "base":   "#8e44ad"  # Purple
        }
        color = mode_colors.get(self.current_model_type, "#555")
        
        self.set_busy(False, f"Loaded {self.current_model_type}")
        self.lbl_active_model.config(text=f"Active: {self.current_model_type.title()} Engine", fg=color)
        self._lock_interface(False)
        
        # Trigger tab check to update status bar
        if hasattr(self, 'on_tab_change'):
            self.on_tab_change(None)
        
        if self.sound_on_ready_var.get():
            custom_sound = self.app_config.get("custom_notification_sound")
            played_custom = False
            
            if custom_sound and os.path.exists(custom_sound):
                try:
                    if winsound:
                        winsound.PlaySound(custom_sound, winsound.SND_FILENAME | winsound.SND_ASYNC)
                        played_custom = True
                    else:
                        # Fallback for non-windows
                        data, sr = sf.read(custom_sound)
                        sd.play(data, sr)
                        played_custom = True
                except Exception as e:
                    print(f"Sound error: {e}")
            
            if not played_custom and winsound:
                try:
                    winsound.MessageBeep(winsound.MB_OK)
                except:
                    pass
        
        if on_success:
            on_success()

    def _lock_interface(self, lock):
        state = tk.DISABLED if lock else tk.NORMAL
        
        buttons = [self.btn_generate_custom, self.btn_generate_clone, self.btn_gen_design, self.btn_lock]
        if hasattr(self, 'director'):
            buttons.append(self.director.btn_run)
            
        for b in buttons:
            if b.winfo_exists():
                b.config(state=state)

    def ensure_model(self, mtype, callback=None, *args, **kwargs):
        if self.current_model_type != mtype:
            if messagebox.askyesno("Switch Model", f"This action requires the {mtype} model. Switch now?"):
                self.switch_model(mtype, on_success=lambda: callback(*args, **kwargs) if callback else None)
            return False
        return True

    def browse_audio(self): 
        initial_dir = os.path.join(os.getcwd(), 'temp')
        if not os.path.exists(initial_dir):
            initial_dir = os.getcwd()
            
        p = filedialog.askopenfilename(initialdir=initial_dir)
        if p:
            self.ref_audio_path.set(p)

    def toggle_lock_voice(self):
        if self.locked_voice_prompt: 
            self.locked_voice_prompt = None
            self.btn_lock.config(text="🔒 Lock Voice", style="TButton")
        else:
            if not self.ensure_model("base", callback=self.toggle_lock_voice):
                return
            self.set_busy(True, "Locking...") 
            try: 
                self.locked_voice_prompt = self.model.create_voice_clone_prompt(self.ref_audio_path.get(), self.ref_text_input.get("1.0", tk.END).strip())
                self.btn_lock.config(text="🔓 Unlock Voice", style="Panic.TButton")
            except Exception as e:
                messagebox.showerror("Error", str(e))
            finally:
                self.set_busy(False)

    def insert_split_cue(self):
        self.target_text_input.insert(tk.INSERT, " || ")
        self.monitor_script_health()

    def insert_batch_pipe(self):
        self.batch_text.insert(tk.INSERT, " | ")

    def monitor_script_health(self, event=None):
        text = self.target_text_input.get("1.0", tk.END).strip()
        
        if not text:
            self.lbl_script_health.config(text="Max Segment: 0 words", fg="grey")
            return
            
        parts = text.split("||")
        max_words = 0
        for p in parts:
            w = len(p.split())
            if w > max_words: max_words = w
            
        if max_words < 200:
            status = "Safe"; color = "#28a745"
        elif max_words < 300:
            status = "Caution"; color = "#fd7e14"
        else:
            status = "Risky"; color = "#dc3545"
            
        self.lbl_script_health.config(text=f"Max Segment: {max_words} words ({status})", fg=color)

    def auto_split_script(self):
        text = self.target_text_input.get("1.0", tk.END).strip()
        if not text: return
        
        try:
            limit = int(self.split_length_var.get())
        except:
            limit = 35
            
        # 1. Remove existing splits
        text = text.replace("||", "")
        
        # 2. Split into sentences (simple regex)
        # Matches period, exclamation, question mark followed by space or end of string
        sentences = re.split(r'(?<=[.!?])\s+', text)
        
        chunks = []
        current_chunk = []
        current_count = 0
        
        for sent in sentences:
            if not sent.strip(): continue
            
            words = sent.split()
            word_count = len(words)
            
            if current_count + word_count > limit:
                # If current chunk has content, push it
                if current_chunk:
                    chunks.append(" ".join(current_chunk))
                    current_chunk = []
                    current_count = 0
                
                # If single sentence is huge, just add it (or split further? sticking to simple for now)
                if word_count > limit:
                    chunks.append(sent)
                else:
                    current_chunk.append(sent)
                    current_count += word_count
            else:
                current_chunk.append(sent)
                current_count += word_count
                
        if current_chunk:
            chunks.append(" ".join(current_chunk))
            
        new_text = " || ".join(chunks)
        self.target_text_input.delete("1.0", tk.END)
        self.target_text_input.insert("1.0", new_text)
        self.monitor_script_health()

    def clear_split_cues(self):
        text = self.target_text_input.get("1.0", tk.END)
        text = text.replace("||", " ")
        # Clean up double spaces
        text = re.sub(r'\s+', ' ', text)
        self.target_text_input.delete("1.0", tk.END)
        self.target_text_input.insert("1.0", text.strip())
        self.monitor_script_health()

    def cancel_generation(self):
        self.cancel_signal.set()
        self.status_var.set("Cancelling...")
        # Don't disable the button immediately, allow multiple clicks if it feels stuck
        self.root.after(1000, lambda: self.btn_cancel.config(state=tk.NORMAL))
        
    def force_reset_model(self):
        """Emergency function to unlock UI and reload model if generation hangs."""
        if messagebox.askyesno("Force Reset", "This will abort the current process and reload the model. Use this only if the app is hanging. Proceed?"):
            self.cancel_signal.set()
            self.set_busy(False, "Resetting Engine...")
            self._lock_interface(False)
            
            # Deep teardown — destroy internal HF model before dropping wrapper ref
            if getattr(self, 'model', None) is not None:
                try:
                    if hasattr(self.model, 'model'):
                        del self.model.model
                except Exception:
                    pass
                try:
                    if hasattr(self.model, 'processor'):
                        del self.model.processor
                except Exception:
                    pass
                del self.model
                self.model = None
            self.flush_vram()

            # Delay reload — give the CUDA driver time to reclaim pages before
            # _load_model_thread tries to allocate 7–8 GB again.
            mtype = self.current_model_type or "custom"
            self.current_model_type = None
            self.root.after(2000, lambda: self.switch_model(mtype))

    def start_gen_custom(self, on_complete=None):
        if not self.ensure_model("custom", callback=lambda: self.start_gen_custom(on_complete)): return
        self._lock_interface(True); self.save_app_config(); self.set_busy(True, "Generating...")
        self.gen_thread = threading.Thread(target=self.gen_task, args=("custom", on_complete), daemon=True)
        self.gen_thread.start()

    def start_gen_clone(self, on_complete=None):
        if not self.ensure_model("base", callback=lambda: self.start_gen_clone(on_complete)): return
        self._lock_interface(True); self.save_app_config(); self.set_busy(True, "Cloning...")
        self.gen_thread = threading.Thread(target=self.gen_task, args=("base", on_complete), daemon=True)
        self.gen_thread.start()
        
    def start_gen_design(self, on_complete=None):
        if not self.ensure_model("design", callback=lambda: self.start_gen_design(on_complete)): return
        self._lock_interface(True); self.save_app_config(); self.set_busy(True, "Designing...")
        self.gen_thread = threading.Thread(target=self.gen_task, args=("design", on_complete), daemon=True)
        self.gen_thread.start()

    def gen_task(self, mode, on_complete=None):
        try:
            if self.cancel_signal.is_set(): raise Exception("Cancelled.")
            start_time = time.time()
            temp = self.temp_var.get()
            top_p = self.top_p_var.get()
            try:
                seed = int(self.seed_var.get().strip())
                if seed < 0:
                    raise ValueError
            except (ValueError, AttributeError):
                seed = random.randint(0, 0xFFFFFFFF)
            wavs = None
            sr = None
            char_count = 0

            if mode == "custom":
                txt = self.text_input_custom.get("1.0", tk.END).strip()
                char_count = len(txt)
                raw_spk = self.speaker_var.get()
                clean_spk = raw_spk.split(" ")[0]
                wavs, sr = self.model.generate_custom_voice(
                    text=txt,
                    language=self.lang_var_custom.get() if self.lang_var_custom.get() != "Auto" else None,
                    speaker=clean_spk,
                    instruct=self.instruct_input.get().strip(),
                    temperature=temp, top_p=top_p, seed=seed
                )

            elif mode == "design":
                txt = self.txt_design_target.get("1.0", tk.END).strip()
                char_count = len(txt)
                wavs, sr = self.model.generate_voice_design(
                    text=txt,
                    voice_description=self.txt_design_desc.get("1.0", tk.END).strip(),
                    instruct=self.txt_design_instruct.get().strip(),
                    temperature=temp, top_p=top_p, seed=seed
                )

            elif mode == "base":
                ref = self.ref_audio_path.get()
                text_to_process = self.target_text_input.get("1.0", tk.END).strip()
                char_count = len(text_to_process)

                if not self.locked_voice_prompt and not os.path.exists(ref): raise Exception("No Ref Audio.")

                if self.use_segments_var.get() and "||" in text_to_process:
                    chunks = [c.strip() for c in text_to_process.split("||") if c.strip()]
                    all_parts = []
                    sr = 24000
                    for i, chunk in enumerate(chunks):
                        if self.cancel_signal.is_set(): raise Exception("Cancelled.")
                        self.set_busy(True, f"Cloning Part {i+1}/{len(chunks)}...")
                        if self.locked_voice_prompt:
                            w, sr = self.model.generate_voice_clone(
                                text=chunk, language=self.lang_var_clone.get(),
                                voice_clone_prompt=self.locked_voice_prompt,
                                temperature=temp, top_p=top_p, seed=seed
                            )
                        else:
                            w, sr = self.model.generate_voice_clone(
                                text=chunk, language=self.lang_var_clone.get(),
                                ref_audio=ref, ref_text=self.ref_text_input.get("1.0", tk.END).strip(),
                                x_vector_only_mode=self.x_vector_var.get(),
                                temperature=temp, top_p=top_p, seed=seed
                            )
                        all_parts.append(w[0])
                    final_wave = np.concatenate(all_parts)
                    wavs = [final_wave]
                else:
                    if self.locked_voice_prompt:
                        wavs, sr = self.model.generate_voice_clone(
                            text=text_to_process, language=self.lang_var_clone.get(),
                            voice_clone_prompt=self.locked_voice_prompt,
                            temperature=temp, top_p=top_p, seed=seed
                        )
                    else:
                        wavs, sr = self.model.generate_voice_clone(
                            text=text_to_process, language=self.lang_var_clone.get(),
                            ref_audio=ref, ref_text=self.ref_text_input.get("1.0", tk.END).strip(),
                            x_vector_only_mode=self.x_vector_var.get(),
                            temperature=temp, top_p=top_p, seed=seed
                        )
            
            if self.cancel_signal.is_set(): raise Exception("Cancelled.")
            self.generated_audio = wavs[0]
            self.sample_rate = sr
            elapsed = time.time() - start_time
            
            try:
                ts = time.strftime("%Y%m%d-%H%M%S")
                if mode == "custom":
                    txt_src = self.text_input_custom.get("1.0", tk.END)
                    label = f"Cst_{self.speaker_var.get().split()[0]}"
                elif mode == "design":
                    txt_src = self.txt_design_target.get("1.0", tk.END)
                    label = "Dsn"
                else:
                    txt_src = self.target_text_input.get("1.0", tk.END)
                    label = "Cln"
                txt_snip = re.sub(r'[^a-zA-Z0-9]', '', txt_src.strip())[:15]
                fname = f"{ts}_{label}_{txt_snip}.wav"
                sf.write(os.path.join(self.temp_dir, fname), self.generated_audio, self.sample_rate)
                self.root.after(0, self.refresh_history_list)
            except Exception as save_err:
                print(f"Auto-save failed: {save_err}")

            self.root.after(0, lambda: self.on_gen_success(mode, elapsed, char_count, on_complete))
        except Exception as e: 
            err = str(e)
            msg = "Cancelled." if "Cancelled" in err else f"Error: {err}"
            self.root.after(0, lambda: [self.status_var.set(msg), self.set_busy(False), self._lock_interface(False)])

    def on_gen_success(self, mode, duration=0.0, char_count=0, on_complete=None):
        self.set_busy(False, f"{mode} Complete ({duration:.2f}s)")
        if self.lbl_last_time:
            self.lbl_last_time.config(text=f"Time: {duration:.2f}s")
        
        # Write the last generation time to a file
        try:
            with open("last_generation_time.txt", "w", encoding="utf-8") as f:
                f.write(f"Last generation took: {duration:.2f} seconds.")
        except Exception as e:
            print(f"Failed to write last generation time: {e}")

        self._lock_interface(False)
        if on_complete:
            on_complete({
                "status": "success", "mode": mode, "audio": self.generated_audio,
                "sample_rate": self.sample_rate, "duration": duration
            })
        if self.autoplay_var.get() and not self.cancel_signal.is_set():
            self.on_play_click()

    def _stop_playback_safe(self):
        """Stop all audio and signal all playback threads to exit.
        Calls sd.stop() FIRST so Pa_StopStream() runs here (explicit, main thread)
        rather than inside the next sd.play() call — which is what causes the freeze."""
        logging.debug("_stop_playback_safe  gen=%s  pb=%s  hist=%s",
                      self._audio_gen,
                      self.playback_thread.is_alive() if self.playback_thread else "None",
                      self.history_playback_thread.is_alive() if self.history_playback_thread else "None")
        self.stop_event.set()
        self.pause_event.clear()
        self.history_stop_event.set()
        # Stop the stream NOW before joining threads.  This unblocks any monitor
        # thread waiting on sd.get_stream().active and guarantees the stream is
        # fully closed before the next sd.play() call — preventing Pa_StopStream()
        # from blocking inside sd.play() and freezing the UI.
        try:
            _log_audio("STOP", f"_stop_playback_safe  gen={self._audio_gen}")
            sd.stop()
        except Exception:
            pass
        for t in [self.playback_thread, self.history_playback_thread]:
            if t and t.is_alive():
                t.join(timeout=0.4)
        self.playback_thread = None
        self.history_playback_thread = None

    def on_play_click(self):
        if self.generated_audio is None:
            return
        self._audio_gen += 1
        my_gen = self._audio_gen
        self._stop_playback_safe()
        try:
            _log_audio("PLAY", f"tab  sr={self.sample_rate}  gen={self._audio_gen}")
            sd.play(self.generated_audio, self.sample_rate)
            logging.debug("AUDIO PLAY  tab: sd.play() returned OK")
        except Exception as e:
            logging.error("AUDIO PLAY  tab FAILED: %s\n%s", e, traceback.format_exc())
            return
        self.stop_event.clear()
        self.history_stop_event.clear()
        self.playback_thread = threading.Thread(target=self.playback_worker, args=(my_gen,), daemon=True)
        self.playback_thread.start()
        self.btn_play.config(state=tk.DISABLED)
        self.btn_pause.config(state=tk.NORMAL)
        self.btn_stop.config(state=tk.NORMAL)

    def playback_worker(self, my_gen):
        """Monitor-only thread. sd.play() was already called on the main thread.
        No sd.play() or sd.stop() calls here — routes them via root.after()."""
        try:
            while not self.stop_event.is_set():
                time.sleep(0.05)
                try:
                    if not sd.get_stream().active:
                        break
                except Exception:
                    break  # stream closed or replaced — exit quietly
                if self.pause_event.is_set():
                    self.root.after(0, sd.stop)  # stop on main thread
                    while self.pause_event.is_set() and not self.stop_event.is_set():
                        time.sleep(0.05)
                    break  # after unpause, exit — user clicks Play to restart
        except Exception:
            pass
        self.root.after(0, lambda: [self.btn_play.config(state=tk.NORMAL), self.btn_pause.config(state=tk.DISABLED), self.btn_stop.config(state=tk.DISABLED)])

    def on_pause_click(self):
        if self.pause_event.is_set():
            self.pause_event.clear()
        else:
            self.pause_event.set()

    def on_stop_click(self):
        self._audio_gen += 1
        self._stop_playback_safe()
        try:
            _log_audio("STOP", f"on_stop_click  gen={self._audio_gen}")
            sd.stop()
        except Exception as e:
            logging.error("AUDIO STOP  on_stop_click FAILED: %s", e)

    def save_audio(self):
        if self.generated_audio is None:
            return
        p = filedialog.asksaveasfilename(defaultextension=".wav")
        if p:
            sf.write(p, self.generated_audio, self.sample_rate)

    def transcribe_ref_audio(self):
        global WHISPER_AVAILABLE
        if not WHISPER_AVAILABLE:
            messagebox.showerror(
                "Whisper Not Found",
                "faster-whisper is not installed.\n\n"
                "Run:  pip install faster-whisper\n"
                "then restart the application."
            )
            return
        
        p = self.ref_audio_path.get()
        if not p or not os.path.exists(p):
            messagebox.showwarning("No Audio", "Please browse for an audio file first.")
            return

        self.set_busy(True, "Transcribing Ref...")
        self.btn_transcribe_clone.config(state=tk.DISABLED)
        
        def _task():
            try:
                device = "cuda" if torch.cuda.is_available() else "cpu"
                compute_type = "float16" if device == "cuda" else "int8"
                model = WhisperModel("small", device=device, compute_type=compute_type)
                segs, _ = model.transcribe(p)
                text = " ".join([s.text for s in segs]).strip()
                self.root.after(0, lambda: [self.ref_text_input.delete("1.0", tk.END), self.ref_text_input.insert("1.0", text)])
                del model; gc.collect(); torch.cuda.empty_cache()
            except Exception as e:
                err_msg = str(e)
                self.root.after(0, lambda: messagebox.showerror("Error", err_msg))
            finally:
                self.root.after(0, lambda: [self.btn_transcribe_clone.config(state=tk.NORMAL), self.set_busy(False)])
        
        threading.Thread(target=_task, daemon=True).start()
    def load_external_modules(self):
        """Scans the 'modules' folder and initializes any plugins found."""
        # This is where the original tutorial button was.
        # By moving the logic to the main app, we can just let this run.
        # The new tutorial tab will be created if the plugin is enabled.
        if self.hub.is_enabled('tutorial_plugin.py'):
            # The button is now part of the main UI, so we just need to ensure it's visible.
            # And its command points to the new tab.
            pass

        if not os.path.exists(self.modules_dir):
            os.makedirs(self.modules_dir, exist_ok=True)
            return
        import importlib.util
        if self.modules_dir not in sys.path:
            sys.path.append(self.modules_dir)
        for item in os.listdir(self.modules_dir):
            if item.endswith(".py") and not item.startswith("__"):
                # Skip if already loaded
                if item in self.loaded_plugins: continue

                # Use Hub to check if enabled
                if not self.hub.is_enabled(item):
                    continue

                try:
                    module_name = item[:-3]
                    if module_name == 'tutorial_plugin': # Don't re-initialize this
                        continue
                    module_path = os.path.join(self.modules_dir, item)
                    spec = importlib.util.spec_from_file_location(module_name, module_path)
                    mod = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(mod)
                    if hasattr(mod, "initialize"):
                        mod.initialize(self)
                        self.loaded_plugins.add(item)
                        print(f"Module '{module_name}' loaded successfully.")
                except Exception as e:
                    print(f"Failed to load module '{item}': {e}")

    def _start_vram_monitor(self):
        """Starts a background thread to monitor VRAM usage."""
        self.vram_var = tk.StringVar(value="VRAM: 0/0 MB")
        self.vram_lbl = tk.Label(
            self.root, 
            textvariable=self.vram_var, 
            font=("Segoe UI", 9, "bold"), 
            bg="#e9ecef", 
            fg="#2c3e50",
            padx=5
        )
        self.vram_lbl.place(relx=1.0, rely=1.0, anchor="se", x=-5, y=-5)
        
        def loop():
            while True:
                try:
                    if not self._app_alive: break
                    used, total = self._get_vram_usage()
                    color = "#2c3e50"
                    if total > 0:
                        pct = used / total
                        if pct > 0.9: color = "#c0392b"
                        elif pct > 0.7: color = "#d35400"

                    status_text = f"VRAM: {used}/{total} MB"
                    self.root.after(0, lambda t=status_text, c=color: [self.vram_var.set(t), self.vram_lbl.config(fg=c)])
                except Exception:
                    break
                time.sleep(2)
        
        threading.Thread(target=loop, daemon=True).start()

    def _get_vram_usage(self):
        """Query nvidia-smi with explicit path fallbacks for frozen/bundled builds."""
        si = None
        if os.name == 'nt':
            si = subprocess.STARTUPINFO()
            si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            si.wShowWindow = subprocess.SW_HIDE

        query = ["--query-gpu=memory.used,memory.total", "--format=csv,nounits,noheader"]

        # Explicit paths tried without shell first; bare name via shell as final fallback
        attempts = [
            (False, [r"C:\Windows\System32\nvidia-smi.exe"] + query),
            (False, [r"C:\Program Files\NVIDIA Corporation\NVSMI\nvidia-smi.exe"] + query),
            (True,  "nvidia-smi --query-gpu=memory.used,memory.total --format=csv,nounits,noheader"),
        ]

        for use_shell, cmd in attempts:
            try:
                output = subprocess.check_output(
                    cmd,
                    startupinfo=si,
                    stderr=subprocess.DEVNULL,
                    shell=use_shell,
                ).decode("utf-8").strip()
                used, total = map(int, output.split(","))
                return used, total
            except Exception:
                continue

        return 0, 0

# =========================================================================
# 🚀 LAUNCHER LOGIC
# =========================================================================

LOCK_HANDLE = None

def _cleanup_on_exit():
    """Release file lock and close log handle on exit."""
    global LOCK_HANDLE, _log_file
    if LOCK_HANDLE is not None:
        try:
            if msvcrt:
                msvcrt.locking(LOCK_HANDLE.fileno(), msvcrt.LK_UNLCK, 1)
        except Exception:
            pass
        try:
            LOCK_HANDLE.close()
        except Exception:
            pass
        LOCK_HANDLE = None
    if _log_file is not None:
        try:
            _log_file.close()
        except Exception:
            pass
        _log_file = None

atexit.register(_cleanup_on_exit)

def acquire_lock():
    """Prevents multiple instances using a file lock in AppData (Shared Location)."""
    global LOCK_HANDLE

    # APP_DATA_ROOT is already initialized by setup_environment() at module level
    # Place lock in APPDATA (Persists across runs)
    lock_file = os.path.join(APP_DATA_ROOT, "app.lock")
    
    # Ensure the folder exists
    try:
        os.makedirs(APP_DATA_ROOT, exist_ok=True)
    except OSError:
        pass

    try:
        LOCK_HANDLE = open(lock_file, "a")
        try:
            if msvcrt:
                msvcrt.locking(LOCK_HANDLE.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(LOCK_HANDLE.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            return True
        except IOError:
            return False
    except PermissionError:
        return False

def launch_studio():
    """Main entry point called by the Installer."""
    # 0. Diagnostics first — before anything else
    _setup_diagnostics()

    # 1. Instance Lock
    if not acquire_lock():
        # Using a hidden root to show the error since main root isn't created yet
        temp_root = tk.Tk()
        temp_root.withdraw() 
        messagebox.showwarning("Already Running", "Qwen3 Studio is already open.")
        temp_root.destroy()
        return

    # 2. Launch UI
    try:
        root = tk.Tk()

        # Catch exceptions that occur inside Tkinter event callbacks
        # (button clicks, bindings, etc.) — normally swallowed silently.
        def _tk_excepthook(exc_type, exc_value, exc_tb):
            logging.error(
                "Tkinter callback exception:\n%s",
                "".join(traceback.format_exception(exc_type, exc_value, exc_tb)),
            )
        root.report_callback_exception = _tk_excepthook

        # Set Icon
        icon_path = os.path.join(BASE_DIR, "pq.ico")
        if os.path.exists(icon_path):
            root.iconbitmap(icon_path)

        logging.info("Tk window created — entering mainloop")
        app = QwenTTSApp(root)

        def _on_closing():
            app._app_alive = False
            root.destroy()
        root.protocol("WM_DELETE_WINDOW", _on_closing)

        root.mainloop()
        logging.info("mainloop exited cleanly")

    except Exception as e:
        logging.critical("Top-level crash:\n%s", traceback.format_exc())
        log_path = _LOG_PATH or os.path.join(APP_DATA_ROOT, "debug.log")
        messagebox.showerror("Critical Error", f"App Crashed.\nLog saved to: {log_path}\n\nError: {e}")

if __name__ == "__main__":
    launch_studio()
