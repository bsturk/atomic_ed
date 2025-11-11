#!/usr/bin/env python3
"""
Test script to verify side detection is working correctly
"""
from lib.scenario_parser import DdayScenario
from scenario_editor import EnhancedUnitParser

def main():
    filename = '/src/proj/mods/atomic_ed/game/SCENARIO/BRADLEY.SCN'

    print(f"Loading scenario: {filename}")
    print(f"{'='*80}\n")

    # Load scenario
    scenario = DdayScenario(filename)

    # Parse units
    units = []
    for section_name, section_data in scenario.sections.items():
        if section_name in ['PTR4', 'PTR6']:
            section_units = EnhancedUnitParser.parse_units(section_data, section_name, 0)
            units.extend(section_units)

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
    print("ALLIED UNITS (first 10):")
    print(f"{'='*80}")
    allied_units = [u for u in units if u['side'] == 'Allied']
    for unit in allied_units[:10]:
        unit_type_name = EnhancedUnitParser.get_unit_type_name(unit['type'])
        print(f"  {unit['name']:<30s} | {unit_type_name:<15s} | Str: {unit['strength']:3d} | ({unit['x']}, {unit['y']})")

    print(f"\n{'='*80}")
    print("AXIS UNITS (first 10):")
    print(f"{'='*80}")
    axis_units = [u for u in units if u['side'] == 'Axis']
    for unit in axis_units[:10]:
        unit_type_name = EnhancedUnitParser.get_unit_type_name(unit['type'])
        print(f"  {unit['name']:<30s} | {unit_type_name:<15s} | Str: {unit['strength']:3d} | ({unit['x']}, {unit['y']})")

    print(f"\n{'='*80}")
    print("UNKNOWN SIDE UNITS (first 10):")
    print(f"{'='*80}")
    unknown_units = [u for u in units if u['side'] == 'Unknown']
    for unit in unknown_units[:10]:
        unit_type_name = EnhancedUnitParser.get_unit_type_name(unit['type'])
        print(f"  {unit['name']:<30s} | {unit_type_name:<15s} | Str: {unit['strength']:3d} | ({unit['x']}, {unit['y']})")

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
            actual_side = matching[0]['side']
            status = '✓' if actual_side == expected_side else '✗'
            print(f"  {status} {unit_name:<30s} Expected: {expected_side:<8s} Got: {actual_side}")
            if actual_side != expected_side:
                all_correct = False
        else:
            print(f"  ✗ {unit_name:<30s} NOT FOUND")
            all_correct = False

    print(f"\n{'='*80}")
    if all_correct:
        print("SUCCESS: All known units have correct sides!")
    else:
        print("FAILURE: Some units have incorrect sides")
    print(f"{'='*80}")

if __name__ == '__main__':
    main()
