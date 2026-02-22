# 🎬 Qwen3-TTS: The Director's Guide

Best practices, style reference, and pro tips for getting the most out of the suite.

---

## 1. The Precision Sliders

These controls apply to **all** tabs — Custom, Design, and Clone.

### Temperature (Creativity & Stability)

Controls how much randomness the model introduces when choosing each sound.

| Range | Zone | Best For |
| :--- | :--- | :--- |
| **0.1 – 0.5** | The News Anchor | Long narration, system announcements, voice clones that sound "drunk" |
| **0.6 – 0.9** | The Sweet Spot *(default)* | Most narration, podcasts, casual dialogue |
| **1.0 – 1.5** | The Drama | Shouting, whispering, crying, intense character acting |

⚠️ High temperature + complex instructions = highest risk of glitching/slurring.

### Top P (Vocabulary Range)

Controls how many token candidates the model considers at each step.

| Range | Effect |
| :--- | :--- |
| **0.1 – 0.5** | Focused, clear pronunciation |
| **0.8 – 1.0** | Diverse, better for character acting and rhythm |

### Seed (Reproducibility)

Pin an integer seed to get a **deterministic, perfectly reproducible** take every time.
- **Empty** → A fresh random seed is chosen at generation time and written back into the field automatically.
- **Number** → That exact seed is used, producing identical audio on every run.

Use 🎲 to roll a random number into the field so you can save and reuse it later.

---

## 2. Voice Design: The Formula

The Voice Design tab creates a character from scratch (zero-shot). The model needs two distinct inputs.

### Field A — Voice Description (The Body)

*What does the person physically sound like at rest?*

| Attribute | Examples |
| :--- | :--- |
| **Age** | "Young child", "Mid-30s", "Elderly", "Ancient" |
| **Gender** | "Male", "Female", "Androgynous" |
| **Texture** | "Gravelly", "Smooth", "Raspy", "Breathy", "Nasal", "Deep" |
| **Accent** | "British RP", "Southern US", "Thick Russian", "Standard American" |
| **Build** | "Deep barrel chest", "Petite and light" |

> **Example:** *"A 60-year-old male smoker with a deep, gravelly throat and a faint Southern drawl."*

### Field B — Style Instruction (The Acting)

*How are they performing right now?*

| Attribute | Examples |
| :--- | :--- |
| **Pace** | "Very slow", "Fast", "Conversational", "Measured" |
| **Emotion** | "Sad", "Angry", "Joyful", "Bored", "Terrified" |
| **Volume** | "Whispering", "Shouting", "Softly spoken", "Projecting" |
| **Context** | "As if confessing a secret", "As if addressing a crowd" |

> **Example:** *"Speaking slowly and quietly, as if sharing a long-buried secret. Barely above a whisper."*

---

## 3. In-Script Action Tags

Insert these directly into your text to trigger specific human sounds.

**Always surround with spaces:** `Hello [ laughter ] how are you?`

| Sound | Tag Syntax | Context Required |
| :--- | :--- | :--- |
| Laughter | `[laughter]` or `<laughter>` | Yes — "Amused, laughing" |
| Breathing | `[breath]` or `<breath>` | Yes — "Running, exhausted" |
| Sighing | `[sigh]` | Yes — "Bored, tired" |
| Gasping | `[gasp]` | Yes — "Shocked, scared" |
| Throat clear | `[clears throat]` | Yes — "Formal, announcement" |
| Crying | `[cry]` | Yes — "Sad, breaking down" |

> **Tip:** High-energy instructions amplify tag intensity. A `[gasp]` inside a "terrified" instruction hits harder than inside a "calm" one.

---

## 4. Tone Recipes (Copy-Paste)

Copy any of these into the **Style Instruction** field for instant results.

### Emotional Archetypes

| Preset | Instruction |
| :--- | :--- |
| **The Heartbroken** | Trembling voice, holding back tears, slow pace, frequent pauses, sorrowful. |
| **The Furious** | Aggressive, shouting, very fast pace, sharp articulation, intense anger. |
| **The Panicked** | Breathless, fast pace, high pitch, stuttering slightly, terrified, hyperventilating. |
| **The Sarcastic** | Bored tone, slow drawl, emphasising the wrong words, dry humour. |
| **The Villain** | Low menacing whisper. Slow and calculated. Arrogant. Cold and gravelly. |
| **The Seductive** | Low pitch, breathy texture, very slow pace, close to microphone, intimate. |

### Cinematic & Atmospheric

| Preset | Instruction |
| :--- | :--- |
| **Horror Narrator** | Deep gravelly whisper, slow and ominous, eerie pauses, threatening tone. |
| **News Anchor** | Professional, neutral tone, clear articulation, even pacing, authoritative. |
| **Old Radio (1950s)** | Mid-Atlantic accent, fast pace, energetic, sharp and punchy, announcer style. |
| **ASMR** | Soft whisper, extremely close to mic, mouth sounds, slow and gentle, relaxing. |
| **Exhausted** | Yawning, heavy sighs, monotone, very slow, dragging words, barely awake. |
| **Dying Breath** | Weak, fading voice, long pauses, shallow breathing, barely audible. |

### Speed Modifiers

| Modifier | Instruction |
| :--- | :--- |
| **The Auctioneer** | Speaking extremely fast, rapid fire, high energy, no pauses. |
| **The Slow Motion** | Speaking very slowly, dragging every word, lethargic. |

### Voice Design Character Presets

Use these in the **Voice Description** field (Voice Design tab).

| Character | Voice Description | Style Instruction |
| :--- | :--- | :--- |
| **Cowboy Narrator** | Gritty elderly male, gravelly texture, slow. | Slow and gritty, measured. |
| **Ancient Witch** | Very old female, raspy, creaky, high pitch. | Sinister, slow, cackling. |
| **Cyber-Droid** | Neutral gender, metallic, flat pitch, robotic. | Monotone, rapid, precise. |
| **The Villain** | Middle-aged male, deep baritone, smooth. | Cold, menacing, slow. Enunciate every word. |
| **Sleep Story** | Female, mid-40s, very soft and warm. | Whispering, extremely slow, soothing. |
| **Documentary** | Older male, British accent, rich texture. | Calm, observant, measured. |

---

## 5. Batch Studio Tips

### Review Workflow
1. Run generation — completed blocks turn **Yellow** (review).
2. Click the status icon on a block to approve (Green) or reject (Red).
3. Hit **Run** again — only rejected and pending blocks are re-generated. Approved blocks are skipped.

### Per-Block Controls
- **⚡ Gen** — Generates only this block without touching anything else.
- **🎲 x3 (Multi-Take)** — Generates 3 variations silently in the background, then opens a picker to choose the best. The winning seed is saved into the block automatically.
- **Seed field** — Pin a number to lock in a reproducible take. Leave empty for a random one (which is written back so you can rerun it).

### Auto-Verify Batch

Enable the **🔍 Auto-Verify Batch** checkbox in the toolbar before running a scene to trigger an automatic quality audit after every generation.

The audit runs two checks on every completed block:
- **Silence scan** — flags any block with an unnatural pause longer than 2 seconds (RMS dropout detection).
- **Transcription match** — uses Faster-Whisper to transcribe the audio and fuzzy-match it against your original script. A score below 75% indicates likely hallucination or garbled speech.

Failed blocks are marked **yellow** with a hover tooltip stating the exact failure reason. The VRAM cycle is handled automatically — the speech engine is purged before Whisper loads, and reloaded after the audit, so you can regenerate flagged blocks immediately.

> **Requires:** `pip install faster-whisper`. If not installed, a one-time error dialog appears and the batch completes normally without the audit.

### Batch Efficiency
- Group blocks by engine (Custom → Custom → Custom, then Clone → Clone) to minimise model switching time.
- Enable **⚡ Auto-Switch** to let the director handle engine changes automatically.

---

## 6. Pro Tips

### The Pause Trick
The AI respects line breaks. For dramatic pauses, press **Enter** between sentences instead of using commas or ellipses. The silence becomes part of the performance.

### Fix Slurring
If the voice sounds drunk or garbled:
1. Lower Temperature to **0.3 – 0.5**.
2. Simplify the instruction — remove conflicting emotions (e.g., "sarcastically depressed" → "sad").
3. Check tag spacing — `Hello<laugh>world` vs `Hello [ laugh ] world`.

### Accent Forcing
Use the **Lang** selector to force an accent without changing the text.
- English text + **German** language = English spoken with a German accent.
- Useful for creating foreign-character voices without writing in the target language.

### Locking a Voice Design
If you generate a Voice Design voice you love:
1. **Save WAV** from the output area.
2. Switch to the **Voice Clone** tab (or add a Clone Block in Batch Studio).
3. Load the saved WAV as Source Audio.
4. Provide a short transcript of what was spoken.
5. The Clone engine now treats that WAV as a stable persona — reproduce it across any text.

### Golden Rule of Prompting
**Do not combine conflicting instructions.**
- ❌ Bad: "Shouting angrily but also whispering quietly."
- ✅ Good: "Intense angry whisper, sharp and controlled."

Conflicting instructions produce garbled output. Consistent logic produces clean performance.

---

© 2026 Blues Creative Engineering.
