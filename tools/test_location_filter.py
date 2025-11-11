#!/usr/bin/env python3
"""
Test location marker filtering in CAMPAIGN.SCN
"""
import struct
import re

def parse_units_with_filter(data):
    """Parse units with location marker filtering"""
    units = []
    pattern = rb'[\x20-\x7e]{4,30}\x00'
    matches = re.finditer(pattern, data)

    for match in matches:
        unit_name = match.group()[:-1].decode('ascii', errors='ignore').strip()

        # Basic validation
        if not unit_name or len(unit_name) < 4:
            continue

        # NEW: Skip location/objective markers
        if len(unit_name) == 2 or len(unit_name) == 3:
            next_offset = match.end()
            if next_offset + 10 < len(data):
                if data[next_offset] < 0x80 and next_offset + 2 < len(data) and data[next_offset + 1] == 0:
                    continue

        # Reject strings with invalid characters
        invalid_chars = '!@#$%^&*+=[]{}|\\<>?/~`"\';'
        if any(c in invalid_chars for c in unit_name):
            continue

        # Check for military terms
        military_terms = ['Corps', 'Infantry', 'Airborne', 'Division', 'FJ',
                         'Schnelle', 'Panzer', 'Armor', 'Regiment', 'Battalion',
                         'Brigade', 'Artillery', 'Cavalry', 'Recon', 'Engineer',
                         'Korps', 'Pz', 'Lehr']
        has_military = any(term in unit_name for term in military_terms)

        has_number = any(c.isdigit() for c in unit_name)
        has_roman = bool(re.search(r'\b(I|II|III|IV|V|VI|VII|VIII|IX|X|XI|XII)\b', unit_name))

        if not (has_military or has_number or has_roman):
            continue

        # Check type byte to filter narrative and garbage
        if match.start() >= 64:
            pre_check = data[match.start()-64:match.start()]
            if len(pre_check) >= 27:
                type_byte = pre_check[-27]
                if 0x61 <= type_byte <= 0x7a:  # lowercase
                    continue
                if type_byte > 0x80:  # high byte = garbage
                    continue

            # Check if pre-data looks like garbage (too many high bytes)
            high_bytes = sum(1 for b in pre_check[-32:] if b > 0x7F)
            if high_bytes > 15:  # More than half = garbage
                continue

        # Extract data
        if match.start() >= 64:
            pre_data = data[match.start()-64:match.start()]

            unit_type = pre_data[-27]
            strength = struct.unpack('<H', pre_data[-64:-62])[0]
            if strength > 500:
                strength = 0

            x = struct.unpack('<H', pre_data[-58:-56])[0]
            y = struct.unpack('<H', pre_data[-56:-54])[0]

            if x == 0xFFFF or y == 0xFFFF:
                x = -1
                y = -1
            elif x > 125 or y > 100:
                x = 0
                y = 0

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
                'side': side,
            })

    return units

def main():
    filename = '/src/proj/mods/atomic_ed/game/SCENARIO/CAMPAIGN.SCN'

    print(f"Testing location marker filtering: {filename}")
    print(f"{'='*80}\n")

    with open(filename, 'rb') as f:
        data = f.read()

    units = parse_units_with_filter(data)

    print(f"Total units found: {len(units)}\n")

    # Show first 30
    print(f"{'='*80}")
    print("First 30 units:")
    print(f"{'='*80}\n")

    bogus_count = 0
    for i, unit in enumerate(units[:30]):
        name = unit['name']
        side = unit.get('side', 'Unknown')
        strength = unit.get('strength', 0)
        x = unit.get('x', 0)
        y = unit.get('y', 0)

        # Check if looks bogus
        is_bogus = len(name) < 4 or any(c in name for c in '!`"\';.,')

        if is_bogus:
            bogus_count += 1
            status = "BOGUS"
        else:
            status = "OK"

        pos_str = "OFF-MAP" if x == -1 else f"({x:2d},{y:2d})" if x > 0 or y > 0 else "  -   "

        print(f"[{status:6s}] {name:<35s} | {side:<8s} | Pos: {pos_str} | Str: {strength:3d}")

    print(f"\n{'='*80}")
    if bogus_count == 0:
        print(f"✓ SUCCESS: No bogus names in first 30 units!")
    else:
        print(f"✗ FAILURE: Found {bogus_count} bogus names")
    print(f"{'='*80}")

    # Check for expected units
    print(f"\n{'='*80}")
    print("Checking for known units:")
    print(f"{'='*80}\n")

    expected = ['VII Corps', 'V Corps', 'XIX Corps', '101st Airborne', '82nd Airborne']
    for exp in expected:
        found = [u for u in units if exp in u['name']]
        if found:
            print(f"✓ Found: {found[0]['name']}")
        else:
            print(f"✗ Missing: {exp}")

if __name__ == '__main__':
    main()
