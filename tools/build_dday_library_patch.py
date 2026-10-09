#!/usr/bin/env python3
"""Build separate, reversible LE expansion and scenario-library components."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from patching.build_library import build


if __name__ == '__main__':
    build()
