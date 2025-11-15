#!/usr/bin/env python3
"""
Unit Stats Analyzer for D-Day Scenario Files

This tool correctly parses and displays unit combat statistics from .SCN files.

IMPORTANT DISCOVERY:
The "strength" value previously shown in the scenario editor is actually the
UNIT INSTANCE INDEX, not a combat stat. The actual unit stats are stored in
a 64-byte record structure before the unit name string.

Unit Record Structure (64 bytes before unit name):
  Bytes 0-1:   Unit Instance Index (NOT strength!)
  Byte 4:      Antitank value
  Bytes 6-7:   X coordinate
  Bytes 8-9:   Y coordinate
  Bytes 55:    Attack base stat
  Bytes 56:    Defense base stat
  Byte 57:     Quality stat
  Byte 58:     Disruption level
  Byte 59:     Fatigue level

Stat Calculation:
  Effective Attack = Attack Base - Fatigue
  Effective Defense = Defense Base - Fatigue

The values shown in game as "X (Y)" represent:
  X = current/effective value (calculated from scenario data)
  Y = base value from unit TYPE definition (in game executable)
"""

import struct
import re
import sys


def parse_unit_stats(filename):
    """Parse unit stats from a scenario file"""

    with open(filename, 'rb') as f:
        data = f.read()

    # Find all unit names - multiple patterns
    # Pattern includes: 1-26-1, 1-304-V, D-745, I-316, etc.
    pattern = rb'\d-\d{2,3}-[VIX\d]+|[A-Z]-\d{3}'

    units = []
    seen_offsets = set()

    for match in re.finditer(pattern, data):
        offset = match.start()

        # Skip duplicates
        if offset in seen_offsets:
            continue
        seen_offsets.add(offset)

        # Get full name (read until non-printable)
        name_bytes = data[offset:offset+20]
        name_end = len(name_bytes)
        for i, b in enumerate(name_bytes):
            if b < 32 or b > 126:
                name_end = i
                break
        name = name_bytes[:name_end].decode('ascii', errors='ignore').strip()

        # Skip if name too short
        if len(name) < 5:
            continue

        # Need at least 64 bytes before name for record
        if offset < 64:
            continue

        # Extract the 64-byte unit record
        record = data[offset-64:offset]

        # Verify this is a valid unit record
        # Check for 0xFF marker at byte 62
        if len(record) >= 63 and record[62] != 0xFF:
            continue

        # Parse unit stats
        unit_index = struct.unpack('<H', record[0:2])[0]

        # Validate - skip if unit_index seems unreasonable
        if unit_index > 1000:
            continue

        antitank = record[4]
        x_coord = struct.unpack('<H', record[6:8])[0]
        y_coord = struct.unpack('<H', record[8:10])[0]

        # Combat stats from last 16 bytes
        attack_base = record[55]
        defense_base = record[56]
        quality = record[57]
        disruption = record[58]
        fatigue = record[59]

        # Armor might be at byte 5 or determined by unit type
        # For now, mark as unknown
        armor = 0  # Infantry typically has 0 armor

        # Calculate effective stats
        effective_attack = attack_base - fatigue
        effective_defense = defense_base - fatigue

        # Determine if off-map (0xFFFF coordinates)
        is_offmap = (x_coord == 0xFFFF or y_coord == 0xFFFF)

        units.append({
            'name': name,
            'offset': offset,
            'unit_index': unit_index,
            'x': x_coord if not is_offmap else -1,
            'y': y_coord if not is_offmap else -1,
            'attack_base': attack_base,
            'defense_base': defense_base,
            'attack_effective': effective_attack,
            'defense_effective': effective_defense,
            'quality': quality,
            'armor': armor,
            'antitank': antitank,
            'disruption': disruption,
            'fatigue': fatigue,
            'is_offmap': is_offmap,
            'raw_record': record.hex()
        })

    return units


def print_unit_stats(units, verbose=False):
    """Print unit stats in a readable format"""

    print("=" * 80)
    print("UNIT COMBAT STATISTICS")
    print("=" * 80)
    print()
    print(f"{'Name':<12} {'Idx':>4} {'X':>3} {'Y':>3} {'Atk':>7} {'Def':>7} {'Qual':>4} {'AT':>3} {'Arm':>3} {'Dis':>3} {'Fat':>3}")
    print("-" * 80)

    for unit in units:
        x_str = str(unit['x']) if not unit['is_offmap'] else 'OFF'
        y_str = str(unit['y']) if not unit['is_offmap'] else 'MAP'

        # Format stats as "effective (base)"
        atk_str = f"{unit['attack_effective']}({unit['attack_base']})"
        def_str = f"{unit['defense_effective']}({unit['defense_base']})"

        print(f"{unit['name']:<12} {unit['unit_index']:>4} {x_str:>3} {y_str:>3} {atk_str:>7} {def_str:>7} "
              f"{unit['quality']:>4} {unit['antitank']:>3} {unit['armor']:>3} {unit['disruption']:>3} {unit['fatigue']:>3}")

        if verbose:
            print(f"    Raw record (first 16 bytes): {unit['raw_record'][:32]}")
            print(f"    Raw record (last 16 bytes):  {unit['raw_record'][96:]}")
            print()

    print()
    print(f"Total units: {len(units)}")


def main():
    if len(sys.argv) < 2:
        print("Usage: python analyze_unit_stats.py <scenario.scn> [-v]")
        print()
        print("Options:")
        print("  -v    Verbose mode (show raw data)")
        print()
        print("Example:")
        print("  python analyze_unit_stats.py game/SCENARIO/BRADLEY.SCN")
        sys.exit(1)

    filename = sys.argv[1]
    verbose = '-v' in sys.argv

    print(f"Analyzing: {filename}")
    print()

    units = parse_unit_stats(filename)
    print_unit_stats(units, verbose)

    print()
    print("NOTE: The 'Idx' column shows the Unit Instance Index (previously")
    print("      mislabeled as 'strength' in the scenario editor).")
    print()
    print("Stat columns show: effective (base)")
    print("  - Effective Attack/Defense = Base - Fatigue")
    print("  - The base values in parens are from the scenario file")
    print("  - The game's displayed (base) values come from unit TYPE definitions")


if __name__ == '__main__':
    main()
