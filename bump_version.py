"""
bump_version.py — Single-command version updater for Qwen3 Studio.

Usage:
    python bump_version.py 4.6.0

The script uses release_config.json as the single source of truth.
It updates every hardcoded version string in the project so nothing
gets accidentally left behind.
"""
import sys
import json
import re
from pathlib import Path

ROOT = Path(__file__).parent

# ---------------------------------------------------------------------------
# Files that contain simple string replacements.
# Each entry: (relative_path, old_pattern, new_value_template)
# Use {v} as a placeholder for the new version string.
# ---------------------------------------------------------------------------
SIMPLE_REPLACEMENTS = [
    # Python source
    ("app_main.py",         r'APP_VERSION = "\d+\.\d+\.\d+"',       'APP_VERSION = "{v}"'),
    ("app_launcher.py",     r'local_version = "\d+\.\d+\.\d+"',      'local_version = "{v}"'),
    # installer download URL
    ("installer.py",        r'Qwen3Studio_v[\d.]+\.zip',              'Qwen3Studio_v{v}.zip'),
    # deploy workflow print strings
    ("deploy_workflow.py",  r'Tag: v[\d.]+',                          'Tag: v{v}'),
    ("deploy_workflow.py",  r'Title: Qwen3 Studio v[\d.]+',           'Title: Qwen3 Studio v{v}'),
    # Documentation headers
    ("README.md",           r'Qwen3-TTS Pro Suite v[\d.]+',           'Qwen3-TTS Pro Suite v{v}'),
    ("FEATURES.md",         r'Functional Specification \(v[\d.]+\)',  'Functional Specification (v{v})'),
]

def load_config():
    cfg_path = ROOT / "release_config.json"
    with open(cfg_path, "r", encoding="utf-8") as f:
        return json.load(f), cfg_path

def save_config(cfg, cfg_path, new_version):
    old_version = cfg.get("app_version", "")
    cfg["app_version"] = new_version
    old_bundle = cfg.get("app_bundle_name", "")
    cfg["app_bundle_name"] = re.sub(r"v[\d.]+", f"v{new_version}", old_bundle)
    with open(cfg_path, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)
    print(f"  release_config.json  :: app_version  {old_version!r} → {new_version!r}")
    print(f"  release_config.json  :: app_bundle_name  {old_bundle!r} → {cfg['app_bundle_name']!r}")

def apply_replacements(new_version):
    for rel_path, pattern, template in SIMPLE_REPLACEMENTS:
        filepath = ROOT / rel_path
        if not filepath.exists():
            print(f"  SKIP (not found): {rel_path}")
            continue
        text = filepath.read_text(encoding="utf-8")
        new_value = template.replace("{v}", new_version)
        new_text, n = re.subn(pattern, new_value, text)
        if n:
            filepath.write_text(new_text, encoding="utf-8")
            print(f"  {rel_path:<30} :: {n} replacement(s)")
        else:
            print(f"  {rel_path:<30} :: no match (already up to date?)")

def main():
    if len(sys.argv) != 2:
        print("Usage: python bump_version.py <new_version>")
        print("Example: python bump_version.py 4.6.0")
        sys.exit(1)

    new_version = sys.argv[1].strip()
    if not re.fullmatch(r"\d+\.\d+\.\d+", new_version):
        print(f"Error: version must be in X.Y.Z format, got {new_version!r}")
        sys.exit(1)

    cfg, cfg_path = load_config()
    current = cfg.get("app_version", "?")

    print(f"\nBumping version  {current}  →  {new_version}\n")
    save_config(cfg, cfg_path, new_version)
    apply_replacements(new_version)
    print(f"\nDone. All version strings updated to {new_version}.")

if __name__ == "__main__":
    main()
