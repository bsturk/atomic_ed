#!/usr/bin/env python3
"""Rebuild the optional music patch from the previous verified patch layers."""
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from lib.binary_patch import apply_component
from lib.dday_patch import PATCHES, apply_engine_patch
from lib.music_patch import build_music_patch


def build():
    path = ROOT/'game/waw/dday/orig/INVADE.EXE'
    if not path.is_file():
        path = ROOT/'game/waw/dday/INVADE.EXE'
    data = apply_engine_patch(path.read_bytes())
    for component in ('code-space','scenario-library','presentation','custom-artwork',
                      'advanced-orders','support-artwork','game-profiles','terrain-rules',
                      'nested-events','startup-selection'):
        data = apply_component(data,PATCHES,'dday-'+component)
    result = build_music_patch(data)
    print(f'Built independently reversible music layer: {len(result)}-byte executable')
    return result


if __name__ == '__main__':
    build()
