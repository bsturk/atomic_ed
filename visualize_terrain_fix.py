#!/usr/bin/env python3
"""
Visualize Terrain Fix
=====================

Shows the terrain map before and after the coordinate fix.
"""

import sys
from scenario_parser import DdayScenario


def visualize_terrain(terrain_map, width, height, title):
    """Create a simple ASCII visualization"""
    print(f"\n{title}")
    print("=" * min(width, 80))

    # Terrain symbols
    symbols = {
        0: '.',  # Grass
        1: '~',  # Water
        2: 's',  # Beach/Sand
        3: 'T',  # Forest
        4: '#',  # Town
        5: '=',  # Road
        6: '-',  # River
        7: '^',  # Mountains
        8: '%',  # Swamp
        9: '=',  # Bridge
        10: 'F',  # Fortification
        11: 'H',  # Bocage
        12: '|',  # Cliff
        13: 'v',  # Village
        14: 'f',  # Farm
        15: 'c',  # Canal
        16: '?',  # Unknown
    }

    # Show a sample region (top-left 60x30)
    sample_width = min(60, width)
    sample_height = min(30, height)

    for y in range(sample_height):
        line = ""
        for x in range(sample_width):
            terrain_data = terrain_map.get((x, y), (0, 0))
            if isinstance(terrain_data, tuple):
                terrain = terrain_data[0]
            else:
                terrain = terrain_data
            line += symbols.get(terrain, '?')
        print(line)


def extract_with_mapping(data, coord_func, name):
    """Extract terrain with a specific coordinate mapping"""
    terrain_map = {}
    for hex_index in range(12500):
        byte = data[hex_index]
        terrain = byte & 0x0F
        variant = (byte >> 4) & 0x0F
        x, y = coord_func(hex_index)
        terrain_map[(x, y)] = (terrain, variant)

    # Count terrain types
    from collections import Counter
    terrain_counter = Counter()
    for (t, v) in terrain_map.values():
        terrain_counter[t] += 1

    print(f"\n{name} Terrain Distribution:")
    terrain_names = {
        0: 'Grass', 1: 'Water', 2: 'Beach', 3: 'Forest', 4: 'Town',
        5: 'Road', 6: 'River', 7: 'Mountains', 8: 'Swamp', 9: 'Bridge',
        10: 'Fort', 11: 'Bocage', 12: 'Cliff', 13: 'Village', 14: 'Farm',
        15: 'Canal', 16: 'Unknown'
    }
    for terrain, count in sorted(terrain_counter.items())[:10]:
        name_str = terrain_names.get(terrain, 'Unknown')
        pct = 100 * count / 12500
        print(f"  {terrain:2d} {name_str:10s}: {count:5,} ({pct:5.1f}%)")

    return terrain_map


def main():
    if len(sys.argv) < 2:
        print("Usage: python visualize_terrain_fix.py <scenario.scn>")
        sys.exit(1)

    scenario_file = sys.argv[1]
    scenario = DdayScenario(scenario_file)

    if not scenario.is_valid:
        print("Invalid scenario!")
        sys.exit(1)

    # Read terrain data
    with open(scenario_file, 'rb') as f:
        f.seek(0x57E4)
        data = f.read(12500)

    print("="*80)
    print("TERRAIN DATA VISUALIZATION")
    print("="*80)

    # WRONG mapping (current)
    print("\n" + "="*80)
    print("BEFORE FIX: Row-major (x = i % 125, y = i // 125)")
    print("="*80)
    wrong_map = extract_with_mapping(
        data,
        lambda i: (i % 125, i // 125),
        "WRONG"
    )
    visualize_terrain(wrong_map, 125, 100, "WRONG - Should look scrambled/symmetrical")

    # CORRECT mapping
    print("\n" + "="*80)
    print("AFTER FIX: Column-major (y = i % 100, x = i // 100)")
    print("="*80)
    correct_map = extract_with_mapping(
        data,
        lambda i: (i // 100, i % 100),
        "CORRECT"
    )
    visualize_terrain(correct_map, 125, 100, "CORRECT - Should look like realistic geography")

    print("\n" + "="*80)
    print("ANALYSIS")
    print("="*80)
    print("The CORRECT mapping shows much better geographic clustering.")
    print("Water (~) should cluster together, land (.) should cluster together.")
    print("The WRONG mapping produces symmetrical/artificial patterns.")


if __name__ == '__main__':
    main()
