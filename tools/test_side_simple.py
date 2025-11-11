#!/usr/bin/env python3
"""
Simple test of side detection without GUI dependencies
"""
import struct
import re

def parse_units(data, section_name, offset_base):
    """Parse unit data from binary section"""
    units = []
    unit_index = 0

    # Find null-terminated strings that look like unit names
    pattern = rb'[\x20-\x7e]{4,30}\x00'
    matches = re.finditer(pattern, data)

    for match in matches:
        unit_name = match.group()[:-1].decode('ascii', errors='ignore')

        # Skip non-unit text - must have military identifier or German abbreviation
        has_military = any(term in unit_name for term in [
            'Infantry', 'Panzer', 'Division', 'Corps', 'Korps', 'Regiment',
            'Battalion', 'Airborne', 'Armored', 'Artillery', 'Cavalry',
            'Pz', 'Lehr', 'FJ', 'Schnelle'
        ])

        # Also skip if it looks like narrative text (mostly lowercase with spaces)
        if not has_military:
            continue

        # Skip if the unit type byte looks like ASCII text (indicates it's narrative, not a unit)
        if match.start() >= 64:
            pre_data_check = data[match.start()-64:match.start()]
            if len(pre_data_check) >= 27:
                type_byte = pre_data_check[-27]
                # If type byte is printable ASCII, it's probably narrative text
                if 0x61 <= type_byte <= 0x7a:  # lowercase letters
                    continue

        strength = 0
        unit_type = 0
        x = 0
        y = 0
        side = 'Unknown'

        if match.start() >= 64:
            pre_data = data[match.start()-64:match.start()]

            # Extract unit type from byte at position -27
            if len(pre_data) >= 27:
                unit_type = pre_data[-27]

            # Extract strength as 16-bit little-endian value at position -64
            if len(pre_data) >= 64:
                strength = struct.unpack('<H', pre_data[-64:-62])[0]
                if strength > 500:
                    strength = 0

            # Extract coordinates from offset -58 (X) and -56 (Y)
            if len(pre_data) >= 58:
                x = struct.unpack('<H', pre_data[-58:-56])[0]
            if len(pre_data) >= 56:
                y = struct.unpack('<H', pre_data[-56:-54])[0]

            # Validate coordinates (D-Day map is 125x100)
            if x > 125 or y > 100:
                x = 0
                y = 0

            # Determine side from binary data at offset -30 and -29
            # Allied units: both bytes = 0x00
            # Axis units: both bytes = 0x01
            if len(pre_data) >= 30:
                side_byte_30 = pre_data[-30]
                side_byte_29 = pre_data[-29]

                if side_byte_30 == 0 and side_byte_29 == 0:
                    side = 'Allied'
                elif side_byte_30 == 1 and side_byte_29 == 1:
                    side = 'Axis'
                else:
                    side = 'Unknown'

        units.append({
            'name': unit_name,
            'type': unit_type,
            'strength': strength,
            'x': x,
            'y': y,
            'side': side,
        })

        unit_index += 1

    return units

def main():
    filename = '/src/proj/mods/atomic_ed/game/SCENARIO/BRADLEY.SCN'

    print(f"Loading scenario: {filename}")
    print(f"{'='*80}\n")

    with open(filename, 'rb') as f:
        data = f.read()

    units = parse_units(data, 'ALL', 0)

    print(f"Found {len(units)} total units\n")

    # Count by side
    allied_count = sum(1 for u in units if u['side'] == 'Allied')
    axis_count = sum(1 for u in units if u['side'] == 'Axis')
    unknown_count = sum(1 for u in units if u['side'] == 'Unknown')

    print(f"Side Distribution:")
    print(f"  Allied:  {allied_count}")
    print(f"  Axis:    {axis_count}")
    print(f"  Unknown: {unknown_count}")

    # Show sample units from each side
    print(f"\n{'='*80}")
    print("ALLIED UNITS (first 15):")
    print(f"{'='*80}")
    allied_units = [u for u in units if u['side'] == 'Allied']
    for unit in allied_units[:15]:
        print(f"  {unit['name']:<30s} | Type: 0x{unit['type']:02x} | Str: {unit['strength']:3d} | ({unit['x']}, {unit['y']})")

    print(f"\n{'='*80}")
    print("AXIS UNITS (first 15):")
    print(f"{'='*80}")
    axis_units = [u for u in units if u['side'] == 'Axis']
    for unit in axis_units[:15]:
        print(f"  {unit['name']:<30s} | Type: 0x{unit['type']:02x} | Str: {unit['strength']:3d} | ({unit['x']}, {unit['y']})")

    print(f"\n{'='*80}")
    print("UNKNOWN SIDE UNITS:")
    print(f"{'='*80}")
    unknown_units = [u for u in units if u['side'] == 'Unknown']
    for unit in unknown_units[:15]:
        print(f"  {unit['name']:<30s} | Type: 0x{unit['type']:02x} | Str: {unit['strength']:3d} | ({unit['x']}, {unit['y']})")

    # Verify specific known units
    print(f"\n{'='*80}")
    print("VERIFICATION OF KNOWN UNITS:")
    print(f"{'='*80}")

    known_checks = [
        ('1st Infantry', 'Allied'),
        ('47th Pz Korps', 'Axis'),
        ('2nd Panzer', 'Axis'),
        ('130th Pz Lehr', 'Axis'),
    ]

    all_correct = True
    for unit_name, expected_side in known_checks:
        matching = [u for u in units if unit_name in u['name']]
        if matching:
            print(f"\n  Searching for: '{unit_name}'")
            for m in matching:
                actual_side = m['side']
                status = 'OK' if actual_side == expected_side else 'FAIL'
                print(f"    [{status}] {m['name']:<35s} Expected: {expected_side:<8s} Got: {actual_side}")
                if actual_side != expected_side:
                    all_correct = False
        else:
            print(f"\n  [FAIL] '{unit_name}' NOT FOUND")
            all_correct = False

    print(f"\n{'='*80}")
    if all_correct:
        print("SUCCESS: All known units have correct sides!")
    else:
        print("FAILURE: Some units have incorrect sides")
    print(f"{'='*80}")

if __name__ == '__main__':
    main()
