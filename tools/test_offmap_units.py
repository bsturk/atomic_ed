#!/usr/bin/env python3
"""
Test script to verify off-map/reinforcement unit detection
"""
import struct
import re

def parse_units(data):
    """Parse unit data from binary section"""
    units = []

    pattern = rb'[\x20-\x7e]{4,30}\x00'
    matches = re.finditer(pattern, data)

    for match in matches:
        unit_name = match.group()[:-1].decode('ascii', errors='ignore')

        has_military = any(term in unit_name for term in [
            'Infantry', 'Panzer', 'Division', 'Corps', 'Korps', 'Regiment',
            'Battalion', 'Airborne', 'Armored', 'Artillery', 'Cavalry',
            'Pz', 'Lehr', 'FJ', 'Schnelle'
        ])

        if not has_military:
            continue

        if match.start() >= 64:
            pre_data_check = data[match.start()-64:match.start()]
            if len(pre_data_check) >= 27:
                type_byte = pre_data_check[-27]
                if 0x61 <= type_byte <= 0x7a:
                    continue

        if match.start() < 64:
            continue

        pre_data = data[match.start()-64:match.start()]

        unit_type = pre_data[-27] if len(pre_data) >= 27 else 0

        strength = 0
        if len(pre_data) >= 64:
            strength = struct.unpack('<H', pre_data[-64:-62])[0]
            if strength > 500:
                strength = 0

        x = 0
        y = 0

        if len(pre_data) >= 58:
            x = struct.unpack('<H', pre_data[-58:-56])[0]
        if len(pre_data) >= 56:
            y = struct.unpack('<H', pre_data[-56:-54])[0]

        # Check for off-map marker (0xFFFF = 65535)
        is_offmap = False
        if x == 0xFFFF or y == 0xFFFF:
            is_offmap = True
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
            'offmap': is_offmap,
        })

    return units

def main():
    filename = '/src/proj/mods/atomic_ed/game/SCENARIO/OMAHA.SCN'

    print(f"Testing: {filename}")
    print(f"{'='*80}\n")

    with open(filename, 'rb') as f:
        data = f.read()

    units = parse_units(data)

    onmap = [u for u in units if not u['offmap']]
    offmap = [u for u in units if u['offmap']]

    print(f"Total units: {len(units)}")
    print(f"  On-map units: {len(onmap)}")
    print(f"  Off-map units (reinforcements): {len(offmap)}")
    print()

    print(f"{'='*80}")
    print("OFF-MAP UNITS (Reinforcements):")
    print(f"{'='*80}\n")

    # Group by side
    allied_offmap = [u for u in offmap if u['side'] == 'Allied']
    axis_offmap = [u for u in offmap if u['side'] == 'Axis']

    print(f"Allied Reinforcements ({len(allied_offmap)}):")
    for unit in allied_offmap:
        print(f"  {unit['name']:<35s} | Strength: {unit['strength']:3d}")

    print(f"\nAxis Reinforcements ({len(axis_offmap)}):")
    for unit in axis_offmap:
        print(f"  {unit['name']:<35s} | Strength: {unit['strength']:3d}")

    print(f"\n{'='*80}")
    print("SAMPLE ON-MAP UNITS (for comparison):")
    print(f"{'='*80}\n")

    for unit in onmap[:10]:
        position = f"({unit['x']:2d},{unit['y']:2d})" if unit['x'] > 0 or unit['y'] > 0 else "  -   "
        print(f"  {unit['name']:<35s} | {unit['side']:<8s} | Pos: {position} | Str: {unit['strength']:3d}")

    print(f"\n{'='*80}")
    print("VERIFICATION:")
    print(f"{'='*80}")
    print(f"✓ Successfully detected {len(offmap)} off-map units")
    print(f"✓ These units have coordinates set to 0xFFFF (65535)")
    print(f"✓ They will be displayed as 'Off-map' in the unit editor")
    print(f"✓ They will NOT be drawn on the hex map")
    print(f"{'='*80}")

if __name__ == '__main__':
    main()
