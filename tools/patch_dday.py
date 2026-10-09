#!/usr/bin/env python3
"""Apply/reverse independent D-Day patches with binary fingerprint checks."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from patching.cli import main


if __name__ == '__main__':
    main()
