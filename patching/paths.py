"""Shared locations for patch sources and the original D-Day executable."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATCHES = ROOT / 'game/waw/patches'


def original_executable():
    source = ROOT / 'game/waw/dday/orig/INVADE.EXE'
    if not source.is_file():
        source = ROOT / 'game/waw/dday/INVADE.EXE'
    return source
