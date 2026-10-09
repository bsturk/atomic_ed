#!/usr/bin/env python3
"""Build weather/victory/AI extensions and their reversible, checked IPS patch."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from patching.build_engine import build


if __name__ == '__main__':
    build()
