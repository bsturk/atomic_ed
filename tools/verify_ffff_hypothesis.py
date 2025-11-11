#!/usr/bin/env python3
"""
Verify the 0xFFFF hypothesis across all scenarios
Check if units with 0xFFFF coordinates have other consistent patterns
"""
import struct
import re
import glob

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

        x_raw = 0
        y_raw = 0

        if len(pre_data) >= 58:
            x_raw = struct.unpack('<H', pre_data[-58:-56])[0]
        if len(pre_data) >= 56:
            y_raw = struct.unpack('<H', pre_data[-56:-54])[0]

        # Determine side
        side = 'Unknown'
        if len(pre_data) >= 30:
            side_byte_30 = pre_data[-30]
            side_byte_29 = pre_data[-29]

            if side_byte_30 == 0 and side_byte_29 == 0:
                side = 'Allied'
            elif side_byte_30 == 1 and side_byte_29 == 1:
                side = 'Axis'

        # Get surrounding bytes for pattern analysis
        bytes_around_coords = {}
        for offset in range(-60, -46):
            if len(pre_data) >= abs(offset):
                bytes_around_coords[offset] = pre_data[offset]

        units.append({
            'name': unit_name,
            'type': unit_type,
            'strength': strength,
            'x_raw': x_raw,
            'y_raw': y_raw,
            'side': side,
            'bytes_around': bytes_around_coords,
        })

    return units

def analyze_all_scenarios():
    scenarios = glob.glob('/src/proj/mods/atomic_ed/game/SCENARIO/*.SCN')

    print(f"Analyzing {len(scenarios)} scenarios for 0xFFFF pattern...")
    print(f"{'='*80}\n")

    all_ffff_units = []
    all_normal_units = []

    for scn_file in sorted(scenarios):
        scn_name = scn_file.split('/')[-1]

        with open(scn_file, 'rb') as f:
            data = f.read()

        units = parse_units(data)

        ffff_units = [u for u in units if u['x_raw'] == 0xFFFF or u['y_raw'] == 0xFFFF]
        normal_units = [u for u in units if 0 < u['x_raw'] <= 125 and 0 < u['y_raw'] <= 100]

        all_ffff_units.extend(ffff_units)
        all_normal_units.extend(normal_units)

        if ffff_units:
            print(f"{scn_name}: {len(ffff_units)} units with 0xFFFF coordinates")

    print(f"\n{'='*80}")
    print(f"TOTALS:")
    print(f"  Units with 0xFFFF: {len(all_ffff_units)}")
    print(f"  Units with normal coords: {len(all_normal_units)}")
    print(f"{'='*80}\n")

    # Check if 0xFFFF units have other consistent patterns
    print("Checking byte patterns around 0xFFFF coordinates...")
    print()

    # Check bytes at offsets -54 to -50 (after the coordinates)
    for offset in [-54, -53, -52, -51, -50]:
        ffff_bytes = set()
        normal_bytes = set()

        for u in all_ffff_units:
            if offset in u['bytes_around']:
                ffff_bytes.add(u['bytes_around'][offset])

        for u in all_normal_units[:100]:  # Sample
            if offset in u['bytes_around']:
                normal_bytes.add(u['bytes_around'][offset])

        if ffff_bytes and normal_bytes:
            overlap = ffff_bytes & normal_bytes
            if not overlap or len(ffff_bytes) == 1:
                print(f"Offset {offset:3d}:")
                print(f"  0xFFFF units: {', '.join(f'0x{b:02x}' for b in sorted(ffff_bytes)[:10])}")
                print(f"  Normal units: {', '.join(f'0x{b:02x}' for b in sorted(normal_bytes)[:10])}")
                if not overlap:
                    print(f"  *** DISTINCT - NO OVERLAP ***")
                elif len(ffff_bytes) == 1:
                    print(f"  *** 0xFFFF units have CONSTANT value: 0x{list(ffff_bytes)[0]:02x} ***")
                print()

    # Check if BOTH X and Y are ALWAYS 0xFFFF together
    print(f"{'='*80}")
    print("Checking if X and Y are always both 0xFFFF together...")
    print(f"{'='*80}\n")

    x_only_ffff = [u for u in all_ffff_units if u['x_raw'] == 0xFFFF and u['y_raw'] != 0xFFFF]
    y_only_ffff = [u for u in all_ffff_units if u['y_raw'] == 0xFFFF and u['x_raw'] != 0xFFFF]
    both_ffff = [u for u in all_ffff_units if u['x_raw'] == 0xFFFF and u['y_raw'] == 0xFFFF]

    print(f"Units with ONLY X = 0xFFFF: {len(x_only_ffff)}")
    print(f"Units with ONLY Y = 0xFFFF: {len(y_only_ffff)}")
    print(f"Units with BOTH X and Y = 0xFFFF: {len(both_ffff)}")

    if len(both_ffff) == len(all_ffff_units):
        print(f"\n*** PERFECT PATTERN: ALL 0xFFFF units have BOTH coordinates = 0xFFFF ***")
    else:
        print(f"\nMixed pattern detected - not all units have both coords as 0xFFFF")

    # Show some examples
    print(f"\n{'='*80}")
    print("Sample 0xFFFF units:")
    print(f"{'='*80}\n")

    for unit in all_ffff_units[:10]:
        print(f"{unit['name']:<35s} | X: 0x{unit['x_raw']:04x} | Y: 0x{unit['y_raw']:04x} | {unit['side']:<8s} | Str: {unit['strength']:3d}")

    # Check if 0xFFFF units have valid strength and side
    print(f"\n{'='*80}")
    print("Validating 0xFFFF units have valid other properties:")
    print(f"{'='*80}\n")

    valid_side = sum(1 for u in all_ffff_units if u['side'] in ['Allied', 'Axis'])
    valid_strength = sum(1 for u in all_ffff_units if u['strength'] > 0)

    print(f"Units with valid side: {valid_side}/{len(all_ffff_units)} ({100*valid_side/len(all_ffff_units):.1f}%)")
    print(f"Units with valid strength: {valid_strength}/{len(all_ffff_units)} ({100*valid_strength/len(all_ffff_units):.1f}%)")

    if valid_side > 0.9 * len(all_ffff_units) and valid_strength > 0.9 * len(all_ffff_units):
        print(f"\n*** 0xFFFF units appear to be VALID units, just without map positions ***")
        print(f"*** This strongly supports the 'reinforcement/off-map' hypothesis ***")

if __name__ == '__main__':
    analyze_all_scenarios()
