#!/usr/bin/env python3
"""
Analyze CAMPAIGN.SCN from SCENARIO-all directory
"""

import struct
import re
from pathlib import Path

def extract_strings(data, min_length=4):
    """Extract ASCII strings from binary data"""
    strings = []
    current = b''
    start_pos = 0

    for i, b in enumerate(data):
        if 32 <= b < 127:  # Printable ASCII
            if len(current) == 0:
                start_pos = i
            current += bytes([b])
        else:
            if len(current) >= min_length:
                try:
                    s = current.decode('ascii')
                    strings.append((start_pos, s))
                except:
                    pass
            current = b''

    return strings

filepath = Path('/home/user/atomic_ed/game/SCENARIO-all/CAMPAIGN.SCN')

with open(filepath, 'rb') as f:
    data = f.read()

magic = struct.unpack('<H', data[0:2])[0]

print("=" * 80)
print("CAMPAIGN.SCN (from SCENARIO-all)")
print("=" * 80)
print(f"File Size: {len(data)//1024}K ({len(data):,} bytes)")
print(f"Magic Number: 0x{magic:04x}")
print()

# Extract strings
all_strings = extract_strings(data, min_length=10)

print("Long Text Strings (20+ chars):")
print("-" * 80)
long_strings = [(off, s) for off, s in all_strings if len(s) >= 20]
for offset, s in long_strings[:50]:
    if len(s) > 70:
        s = s[:70] + "..."
    print(f"  0x{offset:04x}: {s}")

print()
print(f"Total strings found: {len(all_strings)}")
print(f"Long strings (20+): {len(long_strings)}")
