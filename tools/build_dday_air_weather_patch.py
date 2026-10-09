#!/usr/bin/env python3
"""Rebuild the air-weather repair after the previously shipped patch layers."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from patching.air_weather import build


if __name__ == '__main__':
    build()
