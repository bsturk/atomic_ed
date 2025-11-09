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
    Extract REAL terrain data from a D-Day scenario with variant information.

    Args:
        scenario: DdayScenario object (already loaded)

    Returns:
        dict: (x, y) -> (terrain_type, variant) tuples for all 12,500 hexes

    Format Details (CONFIRMED from disassembly analysis):
        - Location: Offset 0x57E4 in .SCN file
        - Encoding: 1 byte per hex (VVVVTTTT format)
          - Bits 0-3: Terrain type (0-16, capped at 19 in code)
          - Bits 4-7: Variant column (0-12)
        - Size: 12,500 bytes (125×100 hexes)
        - Layout: Left-to-right, top-to-bottom
        - Terrain types: 0-16 (17 types)
        - Variants: 0-12 (13 variants per terrain type)
    """
    MAP_WIDTH = 125
    MAP_HEIGHT = 100
    MAP_DATA_OFFSET = 0x57E4  # Discovered from disassembly analysis
    TOTAL_HEXES = 12500

    if not scenario.is_valid:
        return {}

    # Read raw file data to get map section
    try:
        with open(scenario.filename, 'rb') as f:
            # Seek to map data offset
            f.seek(MAP_DATA_OFFSET)
            map_data = f.read(TOTAL_HEXES)

            if len(map_data) < TOTAL_HEXES:
                return {}

            # Extract terrain and variant from packed bytes
            terrain = {}
            for hex_index in range(TOTAL_HEXES):
                hex_byte = map_data[hex_index]

                # Extract fields (as validated in disassembly)
                terrain_type = hex_byte & 0x0F  # Bits 0-3
                variant = (hex_byte >> 4) & 0x0F  # Bits 4-7

                # Cap terrain at 19 (as game does - see disasm line 8073)
                if terrain_type > 19:
                    terrain_type = 19

                # Calculate coordinates
                x = hex_index % MAP_WIDTH
                y = hex_index // MAP_WIDTH

                # Store as tuple: (terrain_type, variant)
                terrain[(x, y)] = (terrain_type, variant)

            return terrain

    except (FileNotFoundError, IOError):
        return {}


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
