#!/usr/bin/env python3
"""
Terrain Reader for D-Day Scenarios
===================================

Simple module to extract real terrain data from scenario files.
Use this in the scenario editor to display actual terrain instead of generated data.

Format: Terrain is stored at PTR4 section start as 4-bit packed nibbles.
        Two hexes per byte: low nibble = first hex, high nibble = second hex.
        Map is 125 hexes wide × 100 hexes tall = 12,500 total hexes.
        Terrain data is 6,250 bytes (12,500 / 2).
"""

from lib.scenario_parser import DdayScenario
from collections import Counter

# Map dimensions - fixed for all D-Day scenarios
# Note: This differs from header counts which have height=125, width=100
# The PTR4 terrain format uses 125 columns × 100 rows based on TERRAIN_FORMAT.md
PTR4_MAP_WIDTH = 125   # Columns (X axis)
PTR4_MAP_HEIGHT = 100  # Rows (Y axis)
PTR4_TOTAL_HEXES = PTR4_MAP_WIDTH * PTR4_MAP_HEIGHT  # 12,500


def extract_terrain_from_scenario(scenario, fallback_scenario_dir=None):
    """
    Extract terrain data from a D-Day scenario using PTR4 4-bit packed format.

    Args:
        scenario: DdayScenario object (already loaded)
        fallback_scenario_dir: Directory to look for fallback scenario if needed

    Returns:
        dict: (x, y) -> (terrain_type, variant) tuples for all hexes
              variant is always 0 for PTR4 format (no variant data stored)
              Returns empty dict if terrain not found and no fallback available

    Format Details (from TERRAIN_FORMAT.md):
        - Location: PTR4 section start
        - Encoding: 4-bit packed nibbles (2 hexes per byte)
          - Low nibble (bits 0-3): terrain type for hex 2N
          - High nibble (bits 4-7): terrain type for hex 2N+1
        - Size: 6,250 bytes for 12,500 hexes
        - Layout: Left-to-right, top-to-bottom
          - hex_index = y * 125 + x
        - Map dimensions: 125 wide × 100 tall
    """
    terrain = _extract_terrain_from_ptr4(scenario)

    # If no terrain found, try fallback scenarios
    if not terrain and fallback_scenario_dir:
        import os
        fallback_scenarios = ['UTAH.SCN', 'OMAHA.SCN', 'COBRA.SCN', 'CAMPAIGN.SCN']
        for fallback_name in fallback_scenarios:
            fallback_path = os.path.join(fallback_scenario_dir, fallback_name)
            if os.path.exists(fallback_path):
                fallback = DdayScenario(fallback_path)
                terrain = _extract_terrain_from_ptr4(fallback)
                if terrain:
                    break

    return terrain


def _extract_terrain_from_ptr4(scenario):
    """
    Extract terrain from PTR4 section using 4-bit packed nibble format.

    Args:
        scenario: DdayScenario object

    Returns:
        dict: (x, y) -> (terrain_type, variant) tuples
              variant is 0 (no variant info in PTR4 format)
    """
    if not scenario.is_valid:
        return {}

    ptr4_offset = scenario.pointers.get('PTR4', 0)
    if ptr4_offset == 0:
        return {}

    terrain_bytes = PTR4_TOTAL_HEXES // 2  # 6,250 bytes

    # Check if PTR4 section has enough data
    if ptr4_offset + terrain_bytes > len(scenario.data):
        return {}

    terrain_data = scenario.data[ptr4_offset:ptr4_offset + terrain_bytes]

    # Validate: check that we get reasonable terrain distribution
    test_types = Counter()
    for byte in terrain_data[:500]:
        test_types[byte & 0x0F] += 1
        test_types[(byte >> 4) & 0x0F] += 1

    # Should have some variety (not all zeros)
    if len(test_types) < 3:
        return {}

    # Extract terrain from packed nibbles
    terrain = {}
    hex_index = 0

    for byte in terrain_data:
        # Low nibble = first hex terrain type
        low = byte & 0x0F
        x = hex_index % PTR4_MAP_WIDTH
        y = hex_index // PTR4_MAP_WIDTH
        terrain[(x, y)] = (low, 0)  # (terrain_type, variant=0)
        hex_index += 1

        # High nibble = second hex terrain type
        high = (byte >> 4) & 0x0F
        x = hex_index % PTR4_MAP_WIDTH
        y = hex_index // PTR4_MAP_WIDTH
        terrain[(x, y)] = (high, 0)  # (terrain_type, variant=0)
        hex_index += 1

    return terrain


def extract_terrain_from_file(scenario_path):
    """
    Extract terrain directly from scenario file path.

    Args:
        scenario_path: Path to .SCN file

    Returns:
        dict: (x, y) -> (terrain_type, variant) mapping
    """
    scenario = DdayScenario(scenario_path)
    return extract_terrain_from_scenario(scenario)


# Terrain type information
# Based on TERRAIN_FORMAT.md and PTR4 data analysis:
# - Terrain 0 is 79% of UTAH = Grass/Field (open countryside)
# - Terrain 1 is 1.3% = Water/Ocean
# - Terrain 2 is 1.2% = Beach/Sand
# - Terrain 15 is 8.4% = Canal (waterways)
TERRAIN_TYPES = {
    0: 'Grass/Field',     # 79% - open grassland
    1: 'Water/Ocean',     # Deep water, impassable
    2: 'Beach/Sand',      # Coastal landing zones
    3: 'Forest',          # Dense woodland
    4: 'Town',            # Urban areas
    5: 'Road',            # Paved roads
    6: 'River',           # Rivers and streams
    7: 'Mountains',       # Mountainous terrain
    8: 'Swamp',           # Marshland
    9: 'Bridge',          # Bridge crossings
    10: 'Fortification',  # Defensive structures
    11: 'Bocage',         # Norman hedgerows
    12: 'Cliff',          # Steep cliffs
    13: 'Village',        # Small villages
    14: 'Farm',           # Farmland
    15: 'Canal',          # Canals and waterways
    16: 'Clear',          # Clear terrain variant
}


if __name__ == '__main__':
    # Simple test
    import sys
    if len(sys.argv) > 1:
        terrain = extract_terrain_from_file(sys.argv[1])
        print(f"Extracted {len(terrain)} hexes from {sys.argv[1]}")

        # Count terrain types (extract just terrain from (terrain, variant) tuples)
        terrain_only = Counter(t for t, v in terrain.values())
        print("\nTerrain distribution:")
        for terrain_type, count in sorted(terrain_only.items()):
            name = TERRAIN_TYPES.get(terrain_type, 'Unknown')
            pct = 100 * count / len(terrain)
            print(f"  {terrain_type:2d} {name:15s}: {count:5,} ({pct:5.1f}%)")
