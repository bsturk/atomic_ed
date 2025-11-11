#!/usr/bin/env python3
"""
Verify that offset -30 or -29 indicates side across multiple scenarios
"""
import struct
import re
import glob

def analyze_scenario(filename):
    """Analyze units in a scenario file"""
    with open(filename, 'rb') as f:
        data = f.read()

    # Find unit names (null-terminated ASCII strings)
    pattern = rb'[\x20-\x7e]{4,30}\x00'
    matches = re.finditer(pattern, data)

    results = []

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
            ascii_count = sum(1 for b in pre_data[-32:-10] if 0x20 <= b <= 0x7e)
            if ascii_count > 15:  # Too much ASCII text, skip
                continue

            byte_30 = pre_data[-30]
            byte_29 = pre_data[-29]

            # Determine expected side from name
            expected_side = None
            if 'Infantry' in unit_name or 'Airborne' in unit_name or \
               ('Corps' in unit_name and 'Korps' not in unit_name):
                if 'Panzer' not in unit_name:
                    expected_side = 'Allied'
            elif 'Panzer' in unit_name or 'Korps' in unit_name or \
                 'Pz' in unit_name or 'Lehr' in unit_name or \
                 'Schnelle' in unit_name:
                expected_side = 'Axis'

            results.append({
                'name': unit_name,
                'byte_30': byte_30,
                'byte_29': byte_29,
                'expected_side': expected_side
            })

    return results

def main():
    scenarios = glob.glob('/src/proj/mods/atomic_ed/game/SCENARIO/*.SCN')

    print(f"Analyzing {len(scenarios)} scenario files...")
    print(f"{'='*80}\n")

    all_results = {}

    for scn_file in sorted(scenarios):
        scn_name = scn_file.split('/')[-1]
        results = analyze_scenario(scn_file)
        all_results[scn_name] = results

        print(f"{scn_name}: {len(results)} units found")

    # Analyze patterns
    print(f"\n{'='*80}")
    print("SIDE BYTE ANALYSIS")
    print(f"{'='*80}\n")

    allied_byte30 = set()
    allied_byte29 = set()
    axis_byte30 = set()
    axis_byte29 = set()

    for scn_name, results in all_results.items():
        for unit in results:
            if unit['expected_side'] == 'Allied':
                allied_byte30.add(unit['byte_30'])
                allied_byte29.add(unit['byte_29'])
            elif unit['expected_side'] == 'Axis':
                axis_byte30.add(unit['byte_30'])
                axis_byte29.add(unit['byte_29'])

    print(f"Allied units:")
    print(f"  Byte at offset -30: {sorted(allied_byte30)}")
    print(f"  Byte at offset -29: {sorted(allied_byte29)}")

    print(f"\nAxis units:")
    print(f"  Byte at offset -30: {sorted(axis_byte30)}")
    print(f"  Byte at offset -29: {sorted(axis_byte29)}")

    # Check for overlap
    overlap_30 = allied_byte30 & axis_byte30
    overlap_29 = allied_byte29 & axis_byte29

    if not overlap_30:
        print(f"\n*** OFFSET -30 IS A PERFECT SIDE INDICATOR! ***")
        print(f"    Allied: {sorted(allied_byte30)}")
        print(f"    Axis:   {sorted(axis_byte30)}")

    if not overlap_29:
        print(f"\n*** OFFSET -29 IS A PERFECT SIDE INDICATOR! ***")
        print(f"    Allied: {sorted(allied_byte29)}")
        print(f"    Axis:   {sorted(axis_byte29)}")

    # Show samples
    print(f"\n{'='*80}")
    print("SAMPLE UNITS")
    print(f"{'='*80}\n")

    for scn_name, results in list(all_results.items())[:2]:  # First 2 scenarios
        print(f"\n{scn_name}:")
        for unit in results[:10]:  # First 10 units
            side_flag = ''
            if unit['byte_30'] == 0 and unit['byte_29'] == 0:
                side_flag = 'ALLIED?'
            elif unit['byte_30'] == 1 and unit['byte_29'] == 1:
                side_flag = 'AXIS?'
            else:
                side_flag = f'UNKNOWN ({unit["byte_30"]},{unit["byte_29"]})'

            print(f"  [{side_flag:15s}] {unit['name'][:40]:<40s} (expected: {unit['expected_side'] or 'Unknown'})")

if __name__ == '__main__':
    main()
