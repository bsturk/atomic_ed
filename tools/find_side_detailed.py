#!/usr/bin/env python3
"""
Detailed analysis of unit side determination
"""
import struct
import re

def main():
    filename = '/src/proj/mods/atomic_ed/game/SCENARIO/BRADLEY.SCN'

    with open(filename, 'rb') as f:
        data = f.read()

    # Find specific known units by name
    units_to_find = [
        (b'1st Infantry\x00', 'Allied'),
        (b'47th Pz Korps\x00', 'Axis'),
        (b'2nd Panzer\x00', 'Axis'),
        (b'130th Pz Lehr\x00', 'Axis'),
        (b'1-16-1\x00', 'Allied'),  # Part of 1st Infantry Division
        (b'2-66-2A\x00', 'Allied'),  # Part of 2nd Armored Division
    ]

    print(f"{'='*80}")
    print("DETAILED UNIT DATA ANALYSIS")
    print(f"{'='*80}\n")

    for unit_name_bytes, expected_side in units_to_find:
        offset = data.find(unit_name_bytes)
        if offset == -1:
            print(f"NOT FOUND: {unit_name_bytes.decode('ascii', errors='ignore')}")
            continue

        unit_name = unit_name_bytes[:-1].decode('ascii')

        print(f"\n{unit_name} (Expected: {expected_side})")
        print(f"Found at offset: 0x{offset:04x}")

        # Show 64 bytes before the name
        if offset >= 64:
            pre_data = data[offset-64:offset]

            # Show all bytes in groups
            print(f"\nByte data before unit name:")
            for i in range(0, 64, 8):
                offset_labels = ' '.join(f'{-64+i+j:3d}' for j in range(8))
                hex_values = ' '.join(f'{pre_data[i+j]:02x}' for j in range(8) if i+j < 64)
                dec_values = ' '.join(f'{pre_data[i+j]:3d}' for j in range(8) if i+j < 64)
                print(f"  Offsets: {offset_labels}")
                print(f"  Hex:     {hex_values}")
                print(f"  Dec:     {dec_values}")
                print()

    # Now let's do a comprehensive comparison
    print(f"\n\n{'='*80}")
    print("COMPREHENSIVE BYTE COMPARISON")
    print(f"{'='*80}\n")

    # Get data for comparison units
    allied_units = []
    axis_units = []

    for unit_name_bytes, expected_side in units_to_find:
        offset = data.find(unit_name_bytes)
        if offset >= 64:
            pre_data = data[offset-64:offset]
            if expected_side == 'Allied':
                allied_units.append((unit_name_bytes[:-1].decode('ascii'), pre_data))
            else:
                axis_units.append((unit_name_bytes[:-1].decode('ascii'), pre_data))

    # Compare byte by byte
    print(f"{'Offset':<8} {'Allied Values':<30} {'Axis Values':<30} {'Match?'}")
    print(f"{'-'*80}")

    for offset_idx in range(64):
        offset = offset_idx - 64

        allied_vals = set(pre[offset_idx] for name, pre in allied_units)
        axis_vals = set(pre[offset_idx] for name, pre in axis_units)

        allied_str = ', '.join(f'0x{v:02x}' for v in sorted(allied_vals))
        axis_str = ', '.join(f'0x{v:02x}' for v in sorted(axis_vals))

        overlap = allied_vals & axis_vals
        match_str = 'YES' if overlap else '*** NO ***'

        # Highlight interesting differences
        if not overlap and len(allied_vals) <= 2 and len(axis_vals) <= 2:
            print(f"{offset:<8} {allied_str:<30} {axis_str:<30} {match_str} <---")
        elif offset in [-27, -64, -58, -56]:
            print(f"{offset:<8} {allied_str:<30} {axis_str:<30} {match_str}")

if __name__ == '__main__':
    main()
