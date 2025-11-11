#!/usr/bin/env python3
"""
Terrain Extractor for D-Day Scenarios
======================================

Extracts the REAL terrain data from scenario files.
Format: 4-bit packed nibbles at offset 0 in PTR4
"""

import struct
import sys
import os
from pathlib import Path
from collections import Counter
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from lib.scenario_parser import DdayScenario


class TerrainExtractor:
    """Extracts terrain data from D-Day scenario files"""

    MAP_WIDTH = 125
    MAP_HEIGHT = 100
    TOTAL_HEXES = 12500

    # Terrain type names
    TERRAIN_NAMES = {
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

    def __init__(self, scenario_path):
        """Load scenario file"""
        self.scenario = DdayScenario(scenario_path)
        self.scenario_name = Path(scenario_path).name
        self.terrain = {}

    def extract_terrain(self):
        """Extract terrain from PTR4 section (4-bit packed format)"""
        if not self.scenario.is_valid:
            raise ValueError("Invalid scenario file!")

        ptr4_data = self.scenario.sections.get('PTR4', b'')
        if not ptr4_data:
            raise ValueError("PTR4 section not found!")

        # Terrain is 4-bit packed at offset 0
        # 12,500 hexes * 4 bits = 6,250 bytes
        packed_size = self.TOTAL_HEXES // 2

        if len(ptr4_data) < packed_size:
            raise ValueError(f"PTR4 too small! Need {packed_size} bytes, got {len(ptr4_data)}")

        # Unpack 4-bit values
        packed_data = ptr4_data[0:packed_size]
        unpacked = []

        for byte in packed_data:
            # Low nibble first, then high nibble
            low = byte & 0x0F
            high = (byte >> 4) & 0x0F
            unpacked.extend([low, high])

        # Verify we got exactly TOTAL_HEXES values
        if len(unpacked) != self.TOTAL_HEXES:
            raise ValueError(f"Wrong terrain size! Got {len(unpacked)}, expected {self.TOTAL_HEXES}")

        # Parse into (x, y) dictionary
        self.terrain = {}
        for i in range(self.TOTAL_HEXES):
            x = i % self.MAP_WIDTH
            y = i // self.MAP_WIDTH
            self.terrain[(x, y)] = unpacked[i]

        return self.terrain

    def analyze_terrain(self):
        """Analyze extracted terrain"""
        if not self.terrain:
            raise ValueError("No terrain data! Call extract_terrain() first")

        print("="*80)
        print(f"TERRAIN ANALYSIS: {self.scenario_name}")
        print("="*80)

        # Count terrain types
        counter = Counter(self.terrain.values())

        print(f"\nTerrain Type Distribution:")
        print("-"*80)

        total = sum(counter.values())
        for terrain_type in range(17):
            count = counter.get(terrain_type, 0)
            pct = 100 * count / total if total > 0 else 0
            name = self.TERRAIN_NAMES.get(terrain_type, 'Unknown')

            if count > 0:
                bar = '█' * int(pct / 2)  # Scale to ~50 chars max
                print(f"  {terrain_type:2d} {name:15s}: {count:5,} hexes ({pct:5.1f}%) {bar}")

        # Check for invalid terrain types
        invalid = [t for t in counter.keys() if t > 16]
        if invalid:
            print(f"\n⚠ WARNING: Found invalid terrain types: {invalid}")
        else:
            print(f"\n✓ All terrain types are valid (0-16)")

        return counter

    def visualize_terrain(self, x_start=0, y_start=0, width=50, height=30):
        """Visualize a portion of the terrain map"""
        if not self.terrain:
            raise ValueError("No terrain data! Call extract_terrain() first")

        print(f"\nTerrain Visualization ({x_start},{y_start}) to ({x_start+width},{y_start+height}):")
        print("-"*80)

        # Character mapping for visualization
        char_map = {
            0: '.',   # Grass
            1: '~',   # Water
            2: ':',   # Beach
            3: 'T',   # Forest
            4: '#',   # Town
            5: '-',   # Road
            6: '≈',   # River
            7: '^',   # Mountains
            8: 'w',   # Swamp
            9: '=',   # Bridge
            10: 'F',  # Fortification
            11: '%',  # Bocage
            12: 'Λ',  # Cliff
            13: 'v',  # Village
            14: 'f',  # Farm
            15: '~',  # Canal
            16: '?',  # Unknown
        }

        for y in range(y_start, min(y_start + height, self.MAP_HEIGHT)):
            row = ""
            for x in range(x_start, min(x_start + width, self.MAP_WIDTH)):
                terrain_type = self.terrain.get((x, y), 16)
                char = char_map.get(terrain_type, '?')
                row += char
            print(f"  {y:3d}: {row}")

    def export_to_dict(self):
        """Export terrain as Python dictionary"""
        if not self.terrain:
            raise ValueError("No terrain data! Call extract_terrain() first")

        return dict(self.terrain)

    def export_to_file(self, output_path):
        """Export terrain data to a file"""
        if not self.terrain:
            raise ValueError("No terrain data! Call extract_terrain() first")

        with open(output_path, 'w') as f:
            f.write(f"# Terrain map from {self.scenario_name}\n")
            f.write(f"# Format: 4-bit packed nibbles at offset 0 in PTR4\n")
            f.write(f"# Map size: {self.MAP_WIDTH}x{self.MAP_HEIGHT}\n\n")

            # Write as grid
            for y in range(self.MAP_HEIGHT):
                for x in range(self.MAP_WIDTH):
                    terrain_type = self.terrain.get((x, y), 0)
                    f.write(f"{terrain_type:2d} ")
                f.write("\n")

        print(f"\n✓ Terrain data exported to: {output_path}")

    def export_to_python(self, output_path):
        """Export as Python code that can be imported"""
        if not self.terrain:
            raise ValueError("No terrain data! Call extract_terrain() first")

        with open(output_path, 'w') as f:
            f.write(f"# Terrain map from {self.scenario_name}\n")
            f.write(f"# Auto-generated by terrain_extractor.py\n\n")

            f.write(f"MAP_WIDTH = {self.MAP_WIDTH}\n")
            f.write(f"MAP_HEIGHT = {self.MAP_HEIGHT}\n\n")

            f.write("# Terrain data: (x, y) -> terrain_type\n")
            f.write("TERRAIN = {\n")

            for y in range(self.MAP_HEIGHT):
                f.write("    # Row {}\n".format(y))
                for x in range(self.MAP_WIDTH):
                    terrain_type = self.terrain.get((x, y), 0)
                    f.write(f"    ({x}, {y}): {terrain_type},\n")

            f.write("}\n")

        print(f"\n✓ Python terrain data exported to: {output_path}")


def extract_terrain_from_scenario(scenario_path):
    """Extract terrain from a scenario file and return as dict"""
    extractor = TerrainExtractor(scenario_path)
    terrain = extractor.extract_terrain()
    return terrain


def main():
    """Main entry point"""
    if len(sys.argv) < 2:
        print("Usage: terrain_extractor.py <scenario.scn> [output.txt]")
        print("\nExamples:")
        print("  python3 terrain_extractor.py game/SCENARIO/UTAH.SCN")
        print("  python3 terrain_extractor.py game/SCENARIO/OMAHA.SCN omaha_terrain.txt")
        sys.exit(1)

    scenario_path = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 else None

    if not Path(scenario_path).exists():
        print(f"Error: File not found: {scenario_path}")
        sys.exit(1)

    try:
        # Extract terrain
        extractor = TerrainExtractor(scenario_path)
        terrain = extractor.extract_terrain()

        # Analyze
        extractor.analyze_terrain()

        # Visualize different regions
        print("\n" + "="*80)
        print("TERRAIN VISUALIZATION")
        print("="*80)

        # Top-left (landing beaches)
        print("\n--- Top-left corner (Utah/Omaha beach area) ---")
        extractor.visualize_terrain(0, 0, 60, 20)

        # Middle section
        print("\n--- Middle section ---")
        extractor.visualize_terrain(30, 40, 60, 20)

        # Export to file if requested
        if output_path:
            extractor.export_to_file(output_path)

        print("\n" + "="*80)
        print("SUCCESS! Terrain data successfully extracted and decoded!")
        print("="*80)
        print("\nFormat Details:")
        print("  - Location: PTR4 section, offset 0x0000")
        print("  - Encoding: 4-bit packed (2 hexes per byte)")
        print("  - Size: 6,250 bytes (12,500 hexes)")
        print("  - Layout: Low nibble first, then high nibble")
        print("  - Order: Left-to-right, top-to-bottom")

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
