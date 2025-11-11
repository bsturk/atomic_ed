#!/usr/bin/env python3
"""
Test that CAMPAIGN.SCN units are parsed correctly without bogus location markers
"""
import sys
sys.path.insert(0, '/src/proj/mods/atomic_ed')

from scenario_editor import EnhancedUnitParser
from lib.scenario_parser import DdayScenario

def main():
    filename = '/src/proj/mods/atomic_ed/game/SCENARIO/CAMPAIGN.SCN'

    print(f"Testing: {filename}")
    print(f"{'='*80}\n")

    scenario = DdayScenario(filename)

    all_units = []
    for section_name, section_data in scenario.sections.items():
        if section_name in ['PTR4', 'PTR6']:
            units = EnhancedUnitParser.parse_units(section_data, section_name, 0)
            all_units.extend(units)

    print(f"Total units found: {len(all_units)}\n")

    # Show first 30 units
    print(f"{'='*80}")
    print("First 30 units:")
    print(f"{'='*80}\n")

    bogus_count = 0
    for i, unit in enumerate(all_units[:30]):
        name = unit['name']
        side = unit.get('side', 'Unknown')
        strength = unit.get('strength', 0)
        x = unit.get('x', 0)
        y = unit.get('y', 0)

        # Check if this looks bogus
        is_bogus = len(name) < 4 or any(c in name for c in '!`"')

        status = "BOGUS!" if is_bogus else "OK"
        if is_bogus:
            bogus_count += 1

        pos_str = "OFF-MAP" if x == -1 else f"({x:2d},{y:2d})" if x > 0 else "  -   "

        print(f"[{status:6s}] {name:<35s} | {side:<8s} | Pos: {pos_str} | Str: {strength:3d}")

    print(f"\n{'='*80}")
    print(f"Bogus entries in first 30: {bogus_count}")
    print(f"{'='*80}")

    if bogus_count > 0:
        print("\nERROR: Still finding bogus unit names!")
        print("These are likely location markers being misidentified as units.")
    else:
        print("\nSUCCESS: No bogus unit names found!")
        print("Location markers are being filtered correctly.")

    # Show some real units we expect to find
    print(f"\n{'='*80}")
    print("Searching for known good units:")
    print(f"{'='*80}\n")

    expected_units = ['VII Corps', 'V Corps', 'XIX Corps', '101st Airborne', '82nd Airborne']

    for expected in expected_units:
        found = [u for u in all_units if expected in u['name']]
        if found:
            u = found[0]
            print(f"✓ Found: {u['name']:<30s} | {u.get('side', 'Unknown'):<8s} | Strength: {u.get('strength', 0)}")
        else:
            print(f"✗ NOT FOUND: {expected}")

if __name__ == '__main__':
    main()
