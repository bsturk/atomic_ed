#!/usr/bin/env python3
"""
Investigate units with missing/invalid positions
"""
import struct
import re

def parse_units(data):
    """Parse unit data from binary section"""
    units = []

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

        if not has_military:
            continue

        # Skip if the unit type byte looks like ASCII text
        if match.start() >= 64:
            pre_data_check = data[match.start()-64:match.start()]
            if len(pre_data_check) >= 27:
                type_byte = pre_data_check[-27]
                if 0x61 <= type_byte <= 0x7a:  # lowercase letters
                    continue

        if match.start() < 64:
            continue

        pre_data = data[match.start()-64:match.start()]

        # Extract all relevant fields
        unit_type = pre_data[-27] if len(pre_data) >= 27 else 0

        strength = 0
        if len(pre_data) >= 64:
            strength = struct.unpack('<H', pre_data[-64:-62])[0]
            if strength > 500:
                strength = 0

        # Extract coordinates
        x = 0
        y = 0
        x_raw = 0
        y_raw = 0

        if len(pre_data) >= 58:
            x_raw = struct.unpack('<H', pre_data[-58:-56])[0]
            x = x_raw
        if len(pre_data) >= 56:
            y_raw = struct.unpack('<H', pre_data[-56:-54])[0]
            y = y_raw

        # Validate coordinates (D-Day map is 125x100)
        coords_valid = True
        if x > 125 or y > 100:
            coords_valid = False
            x = 0
            y = 0

        # Determine side
        side = 'Unknown'
        if len(pre_data) >= 30:
            side_byte_30 = pre_data[-30]
            side_byte_29 = pre_data[-29]

            if side_byte_30 == 0 and side_byte_29 == 0:
                side = 'Allied'
            elif side_byte_30 == 1 and side_byte_29 == 1:
                side = 'Axis'

        units.append({
            'name': unit_name,
            'type': unit_type,
            'strength': strength,
            'x': x,
            'y': y,
            'x_raw': x_raw,
            'y_raw': y_raw,
            'coords_valid': coords_valid,
            'side': side,
            'offset': match.start(),
            'pre_data': pre_data,
        })

    return units

def analyze_position_patterns(units):
    """Analyze patterns in units with/without valid positions"""

    with_pos = [u for u in units if u['coords_valid'] and (u['x'] > 0 or u['y'] > 0)]
    no_pos = [u for u in units if not u['coords_valid'] or (u['x'] == 0 and u['y'] == 0)]

    print(f"Units with valid positions: {len(with_pos)}")
    print(f"Units without valid positions: {len(no_pos)}")
    print()

    # Show units without positions
    print(f"{'='*80}")
    print("UNITS WITHOUT VALID POSITIONS:")
    print(f"{'='*80}\n")

    for unit in no_pos:
        print(f"{unit['name']:<35s} | Side: {unit['side']:<8s} | Str: {unit['strength']:3d} | Raw coords: ({unit['x_raw']}, {unit['y_raw']})")

        # Show relevant bytes around coordinate area
        pre = unit['pre_data']
        if len(pre) >= 64:
            print(f"  Offset -58 to -56 (X): {pre[-58]:02x} {pre[-57]:02x} = 0x{struct.unpack('<H', pre[-58:-56])[0]:04x} ({struct.unpack('<H', pre[-58:-56])[0]})")
            print(f"  Offset -56 to -54 (Y): {pre[-56]:02x} {pre[-55]:02x} = 0x{struct.unpack('<H', pre[-56:-54])[0]:04x} ({struct.unpack('<H', pre[-56:-54])[0]})")
            print()

    # Show units with positions for comparison
    print(f"\n{'='*80}")
    print("UNITS WITH VALID POSITIONS (for comparison):")
    print(f"{'='*80}\n")

    for unit in with_pos[:5]:
        print(f"{unit['name']:<35s} | Side: {unit['side']:<8s} | Str: {unit['strength']:3d} | Coords: ({unit['x']}, {unit['y']})")

        pre = unit['pre_data']
        if len(pre) >= 64:
            print(f"  Offset -58 to -56 (X): {pre[-58]:02x} {pre[-57]:02x} = 0x{struct.unpack('<H', pre[-58:-56])[0]:04x} ({struct.unpack('<H', pre[-58:-56])[0]})")
            print(f"  Offset -56 to -54 (Y): {pre[-56]:02x} {pre[-55]:02x} = 0x{struct.unpack('<H', pre[-56:-54])[0]:04x} ({struct.unpack('<H', pre[-56:-54])[0]})")
            print()

    # Look for patterns in the binary data
    print(f"\n{'='*80}")
    print("PATTERN ANALYSIS:")
    print(f"{'='*80}\n")

    # Check if there's a flag or marker for off-map units
    print("Checking for potential 'off-map' or 'reinforcement' indicators...\n")

    # Compare various byte positions between on-map and off-map units
    for offset in [-60, -59, -54, -53, -52, -51, -50, -49, -48, -47, -46, -45]:
        with_pos_bytes = set()
        no_pos_bytes = set()

        for u in with_pos:
            if len(u['pre_data']) >= abs(offset):
                with_pos_bytes.add(u['pre_data'][offset])

        for u in no_pos:
            if len(u['pre_data']) >= abs(offset):
                no_pos_bytes.add(u['pre_data'][offset])

        # If there's no overlap, this might be a discriminator
        if with_pos_bytes and no_pos_bytes and not (with_pos_bytes & no_pos_bytes):
            print(f"Offset {offset:3d}: POTENTIAL INDICATOR!")
            print(f"  Units with position: {', '.join(f'0x{b:02x}' for b in sorted(with_pos_bytes))}")
            print(f"  Units without position: {', '.join(f'0x{b:02x}' for b in sorted(no_pos_bytes))}")
            print()

def main():
    import sys

    if len(sys.argv) > 1:
        filename = sys.argv[1]
    else:
        filename = '/src/proj/mods/atomic_ed/game/SCENARIO/OMAHA.SCN'

    print(f"Analyzing: {filename}")
    print(f"{'='*80}\n")

    with open(filename, 'rb') as f:
        data = f.read()

    units = parse_units(data)

    print(f"Total units found: {len(units)}\n")

    analyze_position_patterns(units)

if __name__ == '__main__':
    main()
