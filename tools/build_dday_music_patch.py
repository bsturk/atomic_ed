#!/usr/bin/env python3
"""Rebuild the optional music patch from the previous verified patch layers."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from patching.music import build


if __name__ == '__main__':
    build()
