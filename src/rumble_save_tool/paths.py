"""Shared paths for source checkouts and PyInstaller builds."""
from pathlib import Path
import os
import sys


def _application_root() -> Path:
    """Return the directory containing bundled files or the source tree."""
    bundled_root = getattr(sys, "_MEIPASS", None)
    if bundled_root:
        return Path(bundled_root)
    return Path(__file__).resolve().parents[2]


ROOT = _application_root()
RESOURCES = ROOT / "resources"
DATA = RESOURCES / "data"
RUMBLE_ICONS = RESOURCES / "rumble_icons"


def default_dolphin_save() -> Path:
    """Return Dolphin's conventional Wii save path for the current OS."""
    if sys.platform == "win32":
        dolphin_root = Path(os.environ.get("USERPROFILE", str(Path.home()))) / "Documents" / "Dolphin Emulator"
    elif sys.platform == "darwin":
        dolphin_root = Path.home() / "Library" / "Application Support" / "Dolphin Emulator"
    else:
        dolphin_root = Path.home() / ".dolphin-emu"
    return dolphin_root / "Wii" / "title" / "00010001" / "57505345" / "data" / "savedata.bin"
