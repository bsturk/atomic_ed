#!/usr/bin/env python3
"""
Terrain Reader for D-Day Scenarios
===================================

Simple module to extract real terrain data from scenario files.
Use this in the scenario editor to display actual terrain instead of generated data.
"""

from scenario_parser import DdayScenario


def extract_terrain_from_scenario(scenario):
    """
    Extract REAL terrain data from a D-Day scenario.

    Args:
        scenario: DdayScenario object (already loaded)

    Returns:
        dict: (x, y) -> terrain_type mapping for all 12,500 hexes

    Format Details:
        - Location: PTR4 section, offset 0x0000
        - Encoding: 4-bit packed (2 hexes per byte, low nibble first)
        - Size: 6,250 bytes (12,500 hexes)
        - Layout: Left-to-right, top-to-bottom
        - Terrain types: 0-16
    """
    MAP_WIDTH = 125
    MAP_HEIGHT = 100
    TOTAL_HEXES = 12500

    if not scenario.is_valid:
        return {}

    ptr4_data = scenario.sections.get('PTR4', b'')
    if not ptr4_data:
        return {}

    # Terrain is 4-bit packed at offset 0
    packed_size = TOTAL_HEXES // 2  # 6,250 bytes

    if len(ptr4_data) < packed_size:
        return {}

    # Unpack 4-bit values (2 per byte)
    terrain = {}
    hex_index = 0

    for i in range(packed_size):
        byte = ptr4_data[i]

        # Low nibble (first hex)
        low = byte & 0x0F
        x = hex_index % MAP_WIDTH
        y = hex_index // MAP_WIDTH
        terrain[(x, y)] = low
        hex_index += 1

        # High nibble (second hex)
        high = (byte >> 4) & 0x0F
        x = hex_index % MAP_WIDTH
        y = hex_index // MAP_WIDTH
        terrain[(x, y)] = high
        hex_index += 1

    return terrain


def extract_terrain_from_file(scenario_path):
    """
    Extract terrain directly from scenario file path.

    Args:
        scenario_path: Path to .SCN file

    Returns:
        dict: (x, y) -> terrain_type mapping
    """
    scenario = DdayScenario(scenario_path)
    return extract_terrain_from_scenario(scenario)


# Terrain type information
TERRAIN_TYPES = {
    0: 'Grass/Field',
    1: 'Water/Ocean',
    2: 'Beach/Sand',
    3: 'Forest',
    4: 'Town',
    5: 'Road',
    6: 'River',
    7: 'Mountains',
    8: 'Swamp',
    9: 'Bridge',
    10: 'Fortification',
    11: 'Bocage',
    12: 'Cliff',
    13: 'Village',
    14: 'Farm',
    15: 'Canal',
    16: 'Unknown',
}


if __name__ == '__main__':
    # Simple test
    import sys
    if len(sys.argv) > 1:
        terrain = extract_terrain_from_file(sys.argv[1])
        print(f"Extracted {len(terrain)} hexes from {sys.argv[1]}")

        # Count terrain types
        from collections import Counter
        counter = Counter(terrain.values())
        print("\nTerrain distribution:")
        for terrain_type, count in sorted(counter.items()):
            name = TERRAIN_TYPES.get(terrain_type, 'Unknown')
            pct = 100 * count / len(terrain)
            print(f"  {terrain_type:2d} {name:15s}: {count:5,} ({pct:5.1f}%)")
