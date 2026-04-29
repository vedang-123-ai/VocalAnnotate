"""User preferences persisted to ~/.vocalannotate/preferences.json."""

import json
from pathlib import Path

PREF_DIR = Path.home() / ".vocalannotate"
PREF_PATH = PREF_DIR / "preferences.json"

DEFAULTS = {
    "appearance_mode": "light",  # "light" | "dark"
}


def load() -> dict:
    if not PREF_PATH.exists():
        return dict(DEFAULTS)
    try:
        data = json.loads(PREF_PATH.read_text())
    except (json.JSONDecodeError, OSError):
        return dict(DEFAULTS)
    merged = dict(DEFAULTS)
    merged.update({k: v for k, v in data.items() if k in DEFAULTS})
    return merged


def save(prefs: dict) -> None:
    PREF_DIR.mkdir(parents=True, exist_ok=True)
    PREF_PATH.write_text(json.dumps(prefs, indent=2))
