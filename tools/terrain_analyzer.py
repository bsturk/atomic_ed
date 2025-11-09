#!/usr/bin/env python3
"""
Terrain Data Analyzer for D-Day Scenarios
==========================================

Reverse engineers the terrain data format by analyzing scenario files.
"""

import struct
import sys
from pathlib import Path
from collections import Counter
from scenario_parser import DdayScenario


class TerrainAnalyzer:
    """Analyzes scenario files to find terrain data"""

    MAP_WIDTH = 125
    MAP_HEIGHT = 100
    TOTAL_HEXES = 12500
    TERRAIN_TYPES = 17  # 0-16

    def __init__(self, scenario_files):
        """Load multiple scenario files for comparison"""
        self.scenarios = {}

        for file_path in scenario_files:
            scn = DdayScenario(file_path)
            if scn.is_valid:
                self.scenarios[Path(file_path).name] = scn
                print(f"Loaded: {Path(file_path).name}")
            else:
                print(f"FAILED: {Path(file_path).name}")

    def analyze_section_sizes(self):
        """Compare section sizes across scenarios"""
        print("\n" + "="*80)
        print("SECTION SIZE COMPARISON")
        print("="*80)

        section_names = ['PTR3', 'PTR4', 'PTR5', 'PTR6']

        for section_name in section_names:
            print(f"\n{section_name} Section:")
            print("-" * 60)

            sizes = {}
            for name, scn in self.scenarios.items():
                section = scn.sections.get(section_name, b'')
                sizes[name] = len(section)

            for name, size in sorted(sizes.items()):
                # Calculate how many terrain maps could fit
                if size >= self.TOTAL_HEXES:
                    maps_count = size / self.TOTAL_HEXES
                    print(f"  {name:20s}: {size:7,} bytes ({maps_count:.2f} terrain maps)")
                else:
                    print(f"  {name:20s}: {size:7,} bytes")

            # Check if sizes are constant
            unique_sizes = set(sizes.values())
            if len(unique_sizes) == 1:
                print(f"  → CONSTANT SIZE across all scenarios")
            else:
                print(f"  → VARIABLE SIZE - {len(unique_sizes)} different sizes")

    def find_terrain_candidates(self, section_name='PTR4'):
        """Find regions that could be terrain data"""
        print(f"\n" + "="*80)
        print(f"TERRAIN CANDIDATE SEARCH IN {section_name}")
        print("="*80)

        for name, scn in self.scenarios.items():
            print(f"\n{name}:")
            print("-" * 60)

            section = scn.sections.get(section_name, b'')
            if not section:
                print("  Section not found!")
                continue

            print(f"  Section size: {len(section):,} bytes")

            # Search for exact size matches
            self._check_exact_size(section, self.TOTAL_HEXES, "1 byte per hex")
            self._check_exact_size(section, self.TOTAL_HEXES // 2, "4 bits per hex (packed)")
            self._check_exact_size(section, self.TOTAL_HEXES * 2, "2 bytes per hex")

            # Search for blocks with values in range 0-16
            self._find_terrain_blocks(section)

    def _check_exact_size(self, data, target_size, description):
        """Check if section contains a block of exact target size"""
        print(f"\n  Looking for {target_size:,} byte blocks ({description}):")

        if len(data) == target_size:
            print(f"    ✓ Entire section is exactly {target_size} bytes!")
            self._analyze_block(data, 0)
        elif len(data) > target_size:
            # Check for block at various offsets
            for offset in [0, 64, 96, 128, 256, 512, 1024]:
                if offset + target_size <= len(data):
                    block = data[offset:offset + target_size]
                    print(f"    Testing offset 0x{offset:04x}...")
                    if self._looks_like_terrain(block):
                        print(f"      ✓✓✓ STRONG CANDIDATE at offset 0x{offset:04x}!")
                        self._analyze_block(block, offset)

    def _find_terrain_blocks(self, data):
        """Find blocks where most bytes are in terrain range (0-16)"""
        print(f"\n  Scanning for terrain-like byte patterns:")

        block_size = self.TOTAL_HEXES
        stride = 256  # Check every 256 bytes

        candidates = []

        for offset in range(0, len(data) - block_size, stride):
            block = data[offset:offset + block_size]

            # Count bytes in terrain range
            terrain_range_count = sum(1 for b in block if b <= 16)
            percentage = 100 * terrain_range_count / len(block)

            if percentage > 90:  # More than 90% in valid range
                candidates.append((offset, percentage))

        if candidates:
            print(f"    Found {len(candidates)} candidate blocks:")
            for offset, pct in candidates[:5]:  # Show top 5
                print(f"      Offset 0x{offset:06x}: {pct:.1f}% in range [0-16]")
                self._analyze_block(data[offset:offset + block_size], offset)
        else:
            print(f"    No strong candidates found (need >90% bytes in range 0-16)")

    def _looks_like_terrain(self, block):
        """Quick check if block looks like terrain data"""
        # Check if most bytes are in valid terrain range
        terrain_count = sum(1 for b in block if b <= 16)
        return (terrain_count / len(block)) > 0.85

    def _analyze_block(self, block, offset):
        """Analyze a potential terrain block"""
        # Count byte values
        counter = Counter(block)

        # Calculate stats
        terrain_count = sum(count for val, count in counter.items() if val <= 16)
        total = len(block)
        pct = 100 * terrain_count / total

        print(f"      Stats for block at 0x{offset:06x}:")
        print(f"        Total bytes: {total:,}")
        print(f"        In range [0-16]: {terrain_count:,} ({pct:.1f}%)")
        print(f"        Unique values: {len(counter)}")

        # Show distribution of values
        print(f"        Value distribution:")
        for val in range(17):
            count = counter.get(val, 0)
            if count > 0:
                bar = '█' * min(50, count // 100)
                print(f"          {val:2d}: {count:5,} ({100*count/total:5.1f}%) {bar}")

        # Check for values > 16
        high_values = [(val, count) for val, count in counter.items() if val > 16]
        if high_values:
            print(f"        Values > 16: {len(high_values)} different values")
            for val, count in sorted(high_values)[:5]:
                print(f"          {val:3d}: {count:5,} occurrences")

    def compare_scenarios(self, section_name='PTR4'):
        """Compare same section across different scenarios"""
        print(f"\n" + "="*80)
        print(f"CROSS-SCENARIO COMPARISON - {section_name}")
        print("="*80)

        # Get all sections
        sections = {}
        for name, scn in self.scenarios.items():
            section = scn.sections.get(section_name, b'')
            sections[name] = section

        # Find common and different regions
        print("\nSearching for variable regions (likely terrain/unit data):")
        print("-" * 60)

        if len(sections) < 2:
            print("Need at least 2 scenarios to compare!")
            return

        # Compare byte-by-byte
        names = list(sections.keys())
        min_size = min(len(s) for s in sections.values())

        print(f"Comparing first {min_size:,} bytes across {len(sections)} scenarios...")

        # Find regions that differ
        diff_regions = []
        in_diff = False
        start = 0

        WINDOW = 100  # Look at 100-byte windows
        for offset in range(0, min_size - WINDOW, WINDOW):
            # Compare this window across all scenarios
            windows = [sections[name][offset:offset+WINDOW] for name in names]

            # Check if all windows are identical
            all_same = all(w == windows[0] for w in windows)

            if not all_same:
                if not in_diff:
                    start = offset
                    in_diff = True
            else:
                if in_diff:
                    diff_regions.append((start, offset))
                    in_diff = False

        if in_diff:
            diff_regions.append((start, min_size))

        print(f"\nFound {len(diff_regions)} variable regions:")
        for start, end in diff_regions[:10]:
            size = end - start
            print(f"  0x{start:06x} - 0x{end:06x} ({size:6,} bytes)")

            # Check if size matches terrain expectations
            if size >= self.TOTAL_HEXES * 0.9 and size <= self.TOTAL_HEXES * 1.1:
                print(f"    ✓✓✓ SIZE MATCHES TERRAIN MAP! (~{self.TOTAL_HEXES:,} bytes)")

    def extract_terrain_at_offset(self, scenario_name, section_name, offset, output_file=None):
        """Extract and visualize terrain data at a specific offset"""
        print(f"\n" + "="*80)
        print(f"EXTRACTING TERRAIN DATA")
        print("="*80)

        scn = self.scenarios.get(scenario_name)
        if not scn:
            print(f"Scenario {scenario_name} not found!")
            return None

        section = scn.sections.get(section_name, b'')
        if not section:
            print(f"Section {section_name} not found!")
            return None

        if offset + self.TOTAL_HEXES > len(section):
            print(f"Offset {offset} + {self.TOTAL_HEXES} exceeds section size!")
            return None

        # Extract terrain data
        terrain_data = section[offset:offset + self.TOTAL_HEXES]

        print(f"Extracted {len(terrain_data)} bytes from {scenario_name}")
        print(f"Section: {section_name}, Offset: 0x{offset:06x}")

        # Parse as terrain map
        terrain = {}
        for i, byte in enumerate(terrain_data):
            x = i % self.MAP_WIDTH
            y = i // self.MAP_WIDTH
            terrain[(x, y)] = byte

        # Analyze
        print(f"\nTerrain Statistics:")
        counter = Counter(terrain_data)
        for val in range(17):
            count = counter.get(val, 0)
            if count > 0:
                pct = 100 * count / self.TOTAL_HEXES
                print(f"  Type {val:2d}: {count:5,} hexes ({pct:5.1f}%)")

        # Check for invalid values
        invalid = [val for val in counter.keys() if val > 16]
        if invalid:
            print(f"\n⚠ WARNING: Found invalid terrain types: {invalid}")

        # Visualize small portion (top-left corner)
        print(f"\nTop-left corner (first 10x10 hexes):")
        for y in range(min(10, self.MAP_HEIGHT)):
            row = ""
            for x in range(min(10, self.MAP_WIDTH)):
                val = terrain.get((x, y), 99)
                if val <= 9:
                    row += str(val)
                elif val <= 16:
                    row += chr(ord('A') + val - 10)  # A=10, B=11, etc.
                else:
                    row += "?"
            print(f"  {row}")

        # Save to file if requested
        if output_file:
            with open(output_file, 'w') as f:
                f.write(f"# Terrain map from {scenario_name}\n")
                f.write(f"# Section: {section_name}, Offset: 0x{offset:06x}\n")
                f.write(f"# Map size: {self.MAP_WIDTH}x{self.MAP_HEIGHT}\n\n")

                for y in range(self.MAP_HEIGHT):
                    for x in range(self.MAP_WIDTH):
                        val = terrain.get((x, y), 0)
                        f.write(f"{val:2d} ")
                    f.write("\n")

            print(f"\nTerrain data saved to: {output_file}")

        return terrain

    def test_bit_packing(self, section_name='PTR4'):
        """Test if data is bit-packed (4 bits per hex)"""
        print(f"\n" + "="*80)
        print(f"BIT-PACKING ANALYSIS")
        print("="*80)

        packed_size = self.TOTAL_HEXES // 2  # 4 bits per hex = half the bytes

        for name, scn in self.scenarios.items():
            print(f"\n{name}:")
            print("-" * 60)

            section = scn.sections.get(section_name, b'')

            # Search for blocks of packed_size
            for offset in [0, 64, 96, 128, 256, 512, 1024]:
                if offset + packed_size <= len(section):
                    block = section[offset:offset + packed_size]

                    # Unpack 4-bit values
                    unpacked = []
                    for byte in block:
                        low = byte & 0x0F
                        high = (byte >> 4) & 0x0F
                        unpacked.extend([low, high])

                    # Check if unpacked values are in terrain range
                    valid_count = sum(1 for v in unpacked if v <= 16)
                    pct = 100 * valid_count / len(unpacked)

                    if pct > 90:
                        print(f"  Offset 0x{offset:04x}: {pct:.1f}% valid (4-bit unpacked)")
                        print(f"    Sample unpacked values: {unpacked[:50]}")

                        # Show distribution
                        counter = Counter(unpacked)
                        print(f"    Value distribution:")
                        for val in range(17):
                            count = counter.get(val, 0)
                            if count > 0:
                                print(f"      {val:2d}: {count:5,} ({100*count/len(unpacked):5.1f}%)")


def main():
    """Main entry point"""

    # Find all scenario files
    scenario_dir = Path('game/SCENARIO')
    if not scenario_dir.exists():
        print(f"Error: {scenario_dir} not found!")
        sys.exit(1)

    scenario_files = list(scenario_dir.glob('*.SCN'))

    print("="*80)
    print("D-DAY TERRAIN DATA ANALYZER")
    print("="*80)
    print(f"\nFound {len(scenario_files)} scenario files")

    # Load key scenarios for analysis
    key_scenarios = ['UTAH.SCN', 'OMAHA.SCN', 'BRADLEY.SCN']
    scenario_paths = [scenario_dir / name for name in key_scenarios]
    scenario_paths = [p for p in scenario_paths if p.exists()]

    if not scenario_paths:
        print("Error: No key scenario files found!")
        sys.exit(1)

    # Create analyzer
    analyzer = TerrainAnalyzer(scenario_paths)

    if not analyzer.scenarios:
        print("Error: No valid scenarios loaded!")
        sys.exit(1)

    # Run analyses
    analyzer.analyze_section_sizes()
    analyzer.find_terrain_candidates('PTR4')
    analyzer.find_terrain_candidates('PTR6')
    analyzer.test_bit_packing('PTR4')
    analyzer.compare_scenarios('PTR4')

    print("\n" + "="*80)
    print("ANALYSIS COMPLETE")
    print("="*80)


if __name__ == '__main__':
    main()
