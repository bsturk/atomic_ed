#!/usr/bin/env python3
"""
Example: Using D-Day Terrain Extraction
========================================

This script demonstrates practical uses of the terrain extraction functionality.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from lib.terrain_reader import extract_terrain_from_file, TERRAIN_TYPES
from collections import Counter


def example_1_basic_extraction():
    """Example 1: Basic terrain extraction"""
    print("="*80)
    print("EXAMPLE 1: Basic Terrain Extraction")
    print("="*80)

    # Extract terrain from a scenario file
    terrain = extract_terrain_from_file('game/SCENARIO/UTAH.SCN')

    print(f"\nExtracted {len(terrain)} hexes from UTAH.SCN")
    print(f"Map dimensions: 125×100")

    # Access terrain at specific coordinates
    terrain_at_origin = terrain.get((0, 0), 0)
    terrain_name = TERRAIN_TYPES.get(terrain_at_origin, 'Unknown')

    print(f"\nTerrain at (0, 0): Type {terrain_at_origin} = {terrain_name}")
    print(f"Terrain at (50, 50): Type {terrain.get((50, 50), 0)}")
    print(f"Terrain at (100, 75): Type {terrain.get((100, 75), 0)}")


def example_2_terrain_analysis():
    """Example 2: Analyzing terrain distribution"""
    print("\n" + "="*80)
    print("EXAMPLE 2: Terrain Distribution Analysis")
    print("="*80)

    terrain = extract_terrain_from_file('game/SCENARIO/UTAH.SCN')

    # Count terrain types
    counter = Counter(terrain.values())

    print("\nTerrain distribution:")
    print("-"*80)
    for terrain_type, count in counter.most_common():
        name = TERRAIN_TYPES.get(terrain_type, 'Unknown')
        pct = 100 * count / len(terrain)
        bar = '█' * int(pct / 2)  # Scale to ~50 chars max
        print(f"{terrain_type:2d} {name:15s}: {count:5,} ({pct:5.1f}%) {bar}")


def example_3_find_water_hexes():
    """Example 3: Find all water hexes"""
    print("\n" + "="*80)
    print("EXAMPLE 3: Finding Specific Terrain Types")
    print("="*80)

    terrain = extract_terrain_from_file('game/SCENARIO/UTAH.SCN')

    # Find all water hexes (type 1)
    water_hexes = [(x, y) for (x, y), t in terrain.items() if t == 1]

    print(f"\nFound {len(water_hexes)} water hexes")
    print(f"First 10 water hexes:")
    for x, y in water_hexes[:10]:
        print(f"  ({x:3d}, {y:3d})")


def example_4_compare_scenarios():
    """Example 4: Compare terrain between scenarios"""
    print("\n" + "="*80)
    print("EXAMPLE 4: Comparing Scenarios")
    print("="*80)

    utah = extract_terrain_from_file('game/SCENARIO/UTAH.SCN')
    omaha = extract_terrain_from_file('game/SCENARIO/OMAHA.SCN')

    utah_counter = Counter(utah.values())
    omaha_counter = Counter(omaha.values())

    print("\nTerrain comparison (UTAH vs OMAHA):")
    print("-"*80)
    print(f"{'Type':<15} {'UTAH':>10} {'OMAHA':>10} {'Difference':>12}")
    print("-"*80)

    for terrain_type in [0, 1, 2, 3, 4]:  # Show first 5 types
        name = TERRAIN_TYPES.get(terrain_type, 'Unknown')
        utah_count = utah_counter.get(terrain_type, 0)
        omaha_count = omaha_counter.get(terrain_type, 0)
        diff = omaha_count - utah_count

        print(f"{name:<15} {utah_count:>10,} {omaha_count:>10,} {diff:>+12,}")


def example_5_export_terrain():
    """Example 5: Export terrain to a different format"""
    print("\n" + "="*80)
    print("EXAMPLE 5: Exporting Terrain Data")
    print("="*80)

    terrain = extract_terrain_from_file('game/SCENARIO/UTAH.SCN')

    # Export as CSV
    output_file = '/tmp/utah_terrain.csv'
    with open(output_file, 'w') as f:
        f.write("X,Y,TerrainType,TerrainName\n")
        for (x, y), terrain_type in sorted(terrain.items()):
            name = TERRAIN_TYPES.get(terrain_type, 'Unknown')
            f.write(f"{x},{y},{terrain_type},{name}\n")

    print(f"\nExported terrain to CSV: {output_file}")
    print(f"Total rows: {len(terrain)}")

    # Show first few lines
    with open(output_file, 'r') as f:
        lines = f.readlines()[:6]
    print("\nFirst 5 rows:")
    for line in lines:
        print(f"  {line.strip()}")


def example_6_terrain_at_area():
    """Example 6: Analyze terrain in a specific area"""
    print("\n" + "="*80)
    print("EXAMPLE 6: Analyzing a Specific Map Region")
    print("="*80)

    terrain = extract_terrain_from_file('game/SCENARIO/UTAH.SCN')

    # Analyze top-left corner (landing area)
    x_start, y_start = 0, 0
    x_end, y_end = 20, 20

    print(f"\nAnalyzing region ({x_start},{y_start}) to ({x_end},{y_end}):")

    region_terrain = {}
    for x in range(x_start, x_end):
        for y in range(y_start, y_end):
            t = terrain.get((x, y), 0)
            region_terrain[t] = region_terrain.get(t, 0) + 1

    total = sum(region_terrain.values())
    print(f"\nRegion terrain distribution ({total} hexes):")
    for terrain_type, count in sorted(region_terrain.items()):
        name = TERRAIN_TYPES.get(terrain_type, 'Unknown')
        pct = 100 * count / total
        print(f"  {terrain_type:2d} {name:15s}: {count:3d} ({pct:5.1f}%)")


def example_7_ascii_map():
    """Example 7: Create ASCII art map"""
    print("\n" + "="*80)
    print("EXAMPLE 7: ASCII Art Terrain Map")
    print("="*80)

    terrain = extract_terrain_from_file('game/SCENARIO/UTAH.SCN')

    # Character mapping
    chars = {
        0: '.', 1: '~', 2: ':', 3: 'T', 4: '#',
        5: '-', 6: '≈', 7: '^', 8: 'w', 9: '=',
        10: 'F', 11: '%', 12: 'Λ', 13: 'v', 14: 'f',
        15: '~', 16: '?'
    }

    # Draw a section
    print("\nUTAH Beach landing area (first 60×15 hexes):")
    print("-"*60)
    for y in range(15):
        row = ""
        for x in range(60):
            t = terrain.get((x, y), 0)
            row += chars.get(t, '?')
        print(row)


def main():
    """Run all examples"""
    print("\n" + "="*80)
    print("D-DAY TERRAIN EXTRACTION - PRACTICAL EXAMPLES")
    print("="*80)
    print("\nThis script demonstrates how to use the terrain extraction functionality.")

    try:
        example_1_basic_extraction()
        example_2_terrain_analysis()
        example_3_find_water_hexes()
        example_4_compare_scenarios()
        example_5_export_terrain()
        example_6_terrain_at_area()
        example_7_ascii_map()

        print("\n" + "="*80)
        print("ALL EXAMPLES COMPLETED SUCCESSFULLY!")
        print("="*80)
        print("\nYou can now:")
        print("  1. Extract terrain from any D-Day scenario")
        print("  2. Analyze terrain distributions")
        print("  3. Find specific terrain types")
        print("  4. Compare scenarios")
        print("  5. Export to different formats")
        print("  6. Visualize terrain as ASCII art")
        print("\nSee the code in this file for implementation details!")

    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
