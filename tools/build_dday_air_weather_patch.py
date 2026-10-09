#!/usr/bin/env python3
"""Rebuild the air-weather repair after the previously shipped patch layers."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from lib.air_weather_patch import build_air_weather_patch
from tools.build_dday_music_patch import build as build_music


def build():
    result = build_air_weather_patch(build_music())
    print(f'Built independently reversible air-weather repair: {len(result)}-byte executable')
    return result


if __name__ == '__main__':
    build()
