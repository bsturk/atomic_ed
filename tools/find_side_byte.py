#!/usr/bin/env python3
"""
Find the byte that indicates unit side (Allied vs Axis)
"""
import struct
import re

def find_unit_data(filename):
    """Find units and their surrounding binary data"""
    with open(filename, 'rb') as f:
        data = f.read()

    # Find unit names (null-terminated ASCII strings)
    pattern = rb'[\x20-\x7e]{4,30}\x00'
    matches = re.finditer(pattern, data)

    known_allied = []
    known_axis = []

    for match in matches:
        unit_name = match.group()[:-1].decode('ascii', errors='ignore')

        # Skip non-unit text
        if not any(c.isdigit() or c in 'IVXLCDM' for c in unit_name):
            continue
        if len(unit_name) < 3:
            continue

        if match.start() >= 64:
            pre_data = data[match.start()-64:match.start()]

            # Check if preceding data looks like unit data (not ASCII text)
            # Unit data should have mostly low bytes and nulls, not printable ASCII
            ascii_count = sum(1 for b in pre_data[-32:-10] if 0x20 <= b <= 0x7e)
            if ascii_count > 15:  # Too much ASCII text, skip
                continue

            # Known Allied units - be more specific
            if ('Infantry' in unit_name and 'Panzer' not in unit_name) or \
               'Airborne' in unit_name or \
               ('Corps' in unit_name and 'Korps' not in unit_name and 'Pz' not in unit_name):
                known_allied.append({
                    'name': unit_name,
                    'pre_data': pre_data,
                    'offset': match.start()
                })
            # Known Axis units
            elif 'Panzer' in unit_name or 'Korps' in unit_name or \
                 'Pz' in unit_name or 'Lehr' in unit_name or \
                 'Schnelle' in unit_name:
                known_axis.append({
                    'name': unit_name,
                    'pre_data': pre_data,
                    'offset': match.start()
                })

    return known_allied, known_axis

def main():
    filename = '/src/proj/mods/atomic_ed/game/SCENARIO/BRADLEY.SCN'

    allied, axis = find_unit_data(filename)

    print(f"Found {len(allied)} Allied units")
    for u in allied[:10]:
        print(f"  - {u['name']}")

    print(f"\nFound {len(axis)} Axis units")
    for u in axis[:10]:
        print(f"  - {u['name']}")

    if not allied or not axis:
        print("\nError: Need both Allied and Axis units to compare!")
        return

    # Compare each byte position
    print(f"\n{'='*80}")
    print("Searching for bytes that differ between Allied and Axis units...")
    print(f"{'='*80}\n")

    for offset in range(-64, 0):
        allied_vals = set()
        axis_vals = set()

        for unit in allied:
            if len(unit['pre_data']) >= abs(offset):
                allied_vals.add(unit['pre_data'][offset])

        for unit in axis:
            if len(unit['pre_data']) >= abs(offset):
                axis_vals.add(unit['pre_data'][offset])

        # If the sets don't overlap, this byte might indicate side
        if allied_vals and axis_vals:
            overlap = allied_vals & axis_vals
            if not overlap:
                print(f"Offset {offset:3d}: POTENTIAL SIDE INDICATOR!")
                print(f"  Allied values: {', '.join(f'0x{v:02x} ({v})' for v in sorted(allied_vals))}")
                print(f"  Axis values:   {', '.join(f'0x{v:02x} ({v})' for v in sorted(axis_vals))}")
                print()

    # Show some sample data
    print(f"\n{'='*80}")
    print("Sample Allied unit data:")
    print(f"{'='*80}\n")
    if allied:
        u = allied[0]
        print(f"{u['name']} at offset 0x{u['offset']:04x}")
        for i in range(-32, 0):
            if len(u['pre_data']) >= abs(i):
                val = u['pre_data'][i]
                print(f"  {i:3d}: 0x{val:02x} ({val:3d})")

    print(f"\n{'='*80}")
    print("Sample Axis unit data:")
    print(f"{'='*80}\n")
    if axis:
        u = axis[0]
        print(f"{u['name']} at offset 0x{u['offset']:04x}")
        for i in range(-32, 0):
            if len(u['pre_data']) >= abs(i):
                val = u['pre_data'][i]
                print(f"  {i:3d}: 0x{val:02x} ({val:3d})")

if __name__ == '__main__':
    main()
