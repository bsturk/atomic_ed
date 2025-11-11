#!/usr/bin/env python3
"""
Attempt to decode PTR6 data structure
"""
import struct
import sys
sys.path.insert(0, '/src/proj/mods/atomic_ed')
from lib.scenario_parser import DdayScenario

def analyze_ptr6_structure(data):
    """Try to understand PTR6 structure"""

    print("PTR6 Data Structure Analysis")
    print("="*80)
    print(f"Total size: {len(data)} bytes\n")

    # Try interpreting as 16-bit values
    print("First 128 bytes as 16-bit little-endian values:")
    print("-"*80)
    for i in range(0, min(128, len(data)), 16):
        offset_str = f"0x{i:04x}:"
        hex_vals = []
        dec_vals = []
        for j in range(i, min(i+16, len(data)), 2):
            if j+1 < len(data):
                val = struct.unpack('<H', data[j:j+2])[0]
                hex_vals.append(f'{val:04x}')
                dec_vals.append(f'{val:5d}')

        print(f"{offset_str:8s} {' '.join(hex_vals)}")
        print(f"         {' '.join(dec_vals)}")
        print()

    # Look for patterns
    print("\nLooking for repeating patterns...")
    print("-"*80)

    # Check if it's command/data pairs
    print("\nHypothesis: Command/Data Structure")
    print("Interpreting as [command byte][param bytes]...")
    print()

    i = 0
    count = 0
    while i < min(256, len(data)) and count < 20:
        if i + 1 >= len(data):
            break

        # Try different interpretations
        cmd = data[i]

        if cmd == 0x00:
            # Maybe a run of zeros or end marker
            zero_run = 1
            while i + zero_run < len(data) and data[i + zero_run] == 0:
                zero_run += 1
            print(f"0x{i:04x}: [00 x {zero_run}] - Zero padding or separator")
            i += zero_run
        elif cmd < 0x10:
            # Small command, maybe 1-2 bytes of data
            if i + 2 < len(data):
                param = struct.unpack('<H', data[i+1:i+3])[0]
                print(f"0x{i:04x}: [{cmd:02x}] param={param:04x} ({param})")
                i += 3
            else:
                i += 1
        else:
            # Just show the bytes
            if i + 7 < len(data):
                bytes_str = ' '.join(f'{data[i+j]:02x}' for j in range(8))
                print(f"0x{i:04x}: {bytes_str}")
                i += 8
            else:
                i += 1

        count += 1

def find_strings_in_ptr6(data):
    """Find any embedded strings in PTR6"""
    import re

    print("\n\nSearching for embedded strings in PTR6...")
    print("="*80)

    pattern = rb'[\x20-\x7e]{4,}\x00'
    matches = re.finditer(pattern, data)

    strings = []
    for match in matches:
        s = match.group()[:-1].decode('ascii', errors='ignore')
        strings.append((match.start(), s))

    print(f"Found {len(strings)} potential strings:\n")
    for offset, s in strings[:30]:
        print(f"  0x{offset:04x}: \"{s}\"")

def main():
    scn = DdayScenario('/src/proj/mods/atomic_ed/game/SCENARIO/CAMPAIGN.SCN')
    ptr6_data = scn.sections.get('PTR6', b'')

    if not ptr6_data:
        print("No PTR6 data found!")
        return

    analyze_ptr6_structure(ptr6_data)
    find_strings_in_ptr6(ptr6_data)

    # Check the specific offset where "P! I0! I" appears
    print("\n\nChecking offset 0x18c8 (where 'P! I0! I' appears in PTR6):")
    print("="*80)

    offset = 0x18c8
    if offset < len(ptr6_data):
        start = max(0, offset - 32)
        end = min(len(ptr6_data), offset + 32)

        for i in range(start, end, 16):
            hex_str = ' '.join(f'{ptr6_data[j]:02x}' for j in range(i, min(i+16, end)))
            ascii_str = ''.join(chr(ptr6_data[j]) if 32 <= ptr6_data[j] < 127 else '.' for j in range(i, min(i+16, end)))
            marker = ' <--' if i <= offset < i+16 else ''
            print(f"0x{i:04x}: {hex_str:<48s}  {ascii_str}{marker}")

if __name__ == '__main__':
    main()
