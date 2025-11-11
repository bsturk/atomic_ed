#!/usr/bin/env python3
"""
Analyze binary data around units to determine side/allegiance encoding
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
    unknown = []

    for match in matches:
        unit_name = match.group()[:-1].decode('ascii', errors='ignore')

        # Skip non-unit text
        if not any(c.isdigit() or c in 'IVXLCDM' for c in unit_name):
            continue
        if len(unit_name) < 3:
            continue

        if match.start() >= 64:
            pre_data = data[match.start()-64:match.start()]

            # Known Allied units
            if 'Infantry' in unit_name or 'Airborne' in unit_name or 'Corps' in unit_name:
                if 'Panzer' not in unit_name and 'Korps' not in unit_name:
                    known_allied.append({
                        'name': unit_name,
                        'pre_data': pre_data,
                        'offset': match.start()
                    })
            # Known Axis units
            elif 'Panzer' in unit_name or 'Korps' in unit_name or 'Pz' in unit_name or 'Lehr' in unit_name:
                known_axis.append({
                    'name': unit_name,
                    'pre_data': pre_data,
                    'offset': match.start()
                })
            else:
                unknown.append({
                    'name': unit_name,
                    'pre_data': pre_data,
                    'offset': match.start()
                })

    return known_allied, known_axis, unknown

def analyze_bytes(units, label):
    """Analyze common byte patterns in unit data"""
    print(f"\n{'='*80}")
    print(f"{label} - Total units: {len(units)}")
    print(f"{'='*80}")

    if not units:
        print("No units found!")
        return

    # Show first 3 units in detail
    for i, unit in enumerate(units[:3]):
        print(f"\n{unit['name']} (offset: 0x{unit['offset']:04x})")
        print(f"  Offset from name start:")

        pre = unit['pre_data']

        # Show key offsets
        offsets_to_check = [
            (-64, 2, 'Strength'),
            (-62, 2, ''),
            (-60, 2, ''),
            (-58, 2, 'X coord?'),
            (-56, 2, 'Y coord?'),
            (-54, 2, ''),
            (-52, 2, ''),
            (-50, 2, ''),
            (-48, 2, ''),
            (-46, 2, ''),
            (-44, 2, ''),
            (-42, 2, ''),
            (-40, 2, ''),
            (-38, 2, ''),
            (-36, 2, ''),
            (-34, 2, ''),
            (-32, 2, ''),
            (-30, 2, ''),
            (-28, 2, ''),
            (-27, 1, 'Unit Type'),
            (-26, 2, ''),
            (-24, 2, ''),
            (-22, 2, ''),
            (-20, 2, ''),
            (-18, 2, ''),
            (-16, 2, ''),
            (-14, 2, ''),
            (-12, 2, ''),
            (-10, 2, ''),
            (-8, 2, ''),
            (-6, 2, ''),
            (-4, 2, ''),
            (-2, 2, ''),
        ]

        for offset, size, desc in offsets_to_check:
            if len(pre) >= abs(offset):
                if size == 1:
                    val = pre[offset]
                    print(f"    {offset:3d}: 0x{val:02x} ({val:3d})  {desc}")
                elif len(pre) >= abs(offset) + size:
                    val = struct.unpack('<H', pre[offset:offset+size])[0]
                    print(f"    {offset:3d}: 0x{val:04x} ({val:5d})  {desc}")

    # Look for common byte values at each position
    print(f"\n\nCommon byte patterns across all {len(units)} {label}:")
    print(f"{'Offset':<8} {'Byte Values (hex)':<40} {'Description'}")
    print(f"{'-'*80}")

    # Check single-byte positions
    for offset in [-27, -26, -25, -24, -23, -22, -21, -20, -19, -18, -17, -16, -15, -14, -13, -12, -11, -10]:
        if all(len(u['pre_data']) >= abs(offset) for u in units):
            byte_vals = [u['pre_data'][offset] for u in units]
            unique_vals = set(byte_vals)

            if len(unique_vals) <= 5:  # Show if there are few unique values
                hex_str = ', '.join(f'0x{v:02x}' for v in sorted(unique_vals))

                desc = ''
                if offset == -27:
                    desc = 'Unit Type'
                elif len(unique_vals) == 1:
                    desc = '*** CONSTANT ***'

                print(f"{offset:<8} {hex_str:<40} {desc}")

def main():
    filename = '/src/proj/mods/atomic_ed/game/SCENARIO/BRADLEY.SCN'

    allied, axis, unknown = find_unit_data(filename)

    analyze_bytes(allied, "KNOWN ALLIED UNITS")
    analyze_bytes(axis, "KNOWN AXIS UNITS")

    # Compare specific bytes
    print(f"\n\n{'='*80}")
    print("COMPARATIVE ANALYSIS - Looking for discriminating bytes")
    print(f"{'='*80}")

    # Check each position for differences between Allied and Axis
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
        if allied_vals and axis_vals and not (allied_vals & axis_vals):
            print(f"\nOffset {offset}: POTENTIAL SIDE INDICATOR!")
            print(f"  Allied values: {', '.join(f'0x{v:02x}' for v in sorted(allied_vals))}")
            print(f"  Axis values:   {', '.join(f'0x{v:02x}' for v in sorted(axis_vals))}")

if __name__ == '__main__':
    main()
