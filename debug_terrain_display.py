#!/usr/bin/env python3
"""
Debug Terrain Display Issues
=============================

This script investigates terrain data extraction problems by:
1. Analyzing raw hex data at different offsets
2. Testing different byte format interpretations
3. Testing different coordinate mappings
4. Comparing with PTR section data
"""

from scenario_parser import DdayScenario
from collections import Counter
import struct


def hex_dump(data, offset=0, length=200):
    """Create a formatted hex dump"""
    lines = []
    for i in range(0, min(length, len(data)), 16):
        hex_bytes = ' '.join(f'{b:02x}' for b in data[i:i+16])
        ascii_bytes = ''.join(chr(b) if 32 <= b < 127 else '.' for b in data[i:i+16])
        lines.append(f"0x{offset+i:06x}: {hex_bytes:48s} | {ascii_bytes}")
    return '\n'.join(lines)


def analyze_data_patterns(data, name="Data"):
    """Analyze byte patterns in data"""
    print(f"\n=== {name} Analysis ===")
    print(f"Length: {len(data):,} bytes")

    # Count value distribution
    counter = Counter(data)

    # Check for clustering (geographic patterns)
    print(f"Unique values: {len(counter)}")
    print(f"Most common values:")
    for value, count in counter.most_common(10):
        pct = 100 * count / len(data)
        print(f"  0x{value:02x} ({value:3d}): {count:5,} ({pct:5.1f}%)")

    # Check for runs (repeated values)
    max_run = 0
    current_run = 1
    for i in range(1, len(data)):
        if data[i] == data[i-1]:
            current_run += 1
            max_run = max(max_run, current_run)
        else:
            current_run = 1
    print(f"Max consecutive run: {max_run} bytes")

    # Check bit distribution
    low_nibbles = Counter(b & 0x0F for b in data)
    high_nibbles = Counter((b >> 4) & 0x0F for b in data)
    print(f"Low nibble unique values: {len(low_nibbles)}")
    print(f"High nibble unique values: {len(high_nibbles)}")

    return counter


def test_byte_format(data, format_name, terrain_func, variant_func):
    """Test a specific byte format interpretation"""
    print(f"\n--- Testing: {format_name} ---")

    terrain_values = Counter()
    variant_values = Counter()

    for byte in data[:12500]:
        terrain = terrain_func(byte)
        variant = variant_func(byte)
        terrain_values[terrain] += 1
        variant_values[variant] += 1

    print(f"Terrain values (0-16 expected):")
    for val in sorted(terrain_values.keys()):
        count = terrain_values[val]
        pct = 100 * count / 12500
        print(f"  {val:2d}: {count:5,} ({pct:5.1f}%)")

    print(f"Variant values (0-12 expected):")
    for val in sorted(variant_values.keys()):
        count = variant_values[val]
        pct = 100 * count / 12500
        print(f"  {val:2d}: {count:5,} ({pct:5.1f}%)")

    # Check for sensible distribution
    # Ocean (1) and Grass (0) should be common
    # Town (4) should be rare
    terrain_makes_sense = (
        terrain_values.get(0, 0) + terrain_values.get(1, 0) > 5000 and
        terrain_values.get(4, 0) < 1000
    )

    print(f"Seems sensible: {terrain_makes_sense}")
    return terrain_makes_sense


def test_coordinate_mapping(data, mapping_name, coord_func):
    """Test a specific coordinate mapping"""
    print(f"\n--- Testing: {mapping_name} ---")

    # Build terrain map
    terrain_map = {}
    for hex_index in range(12500):
        byte = data[hex_index]
        terrain = byte & 0x0F
        x, y = coord_func(hex_index)
        terrain_map[(x, y)] = terrain

    # Check for geographic clustering
    # Good terrain should have water clustered together, land together
    cluster_score = 0
    for y in range(10, 90):  # Sample interior
        for x in range(10, 115):
            terrain = terrain_map.get((x, y), 0)
            # Check 4 neighbors
            neighbors = [
                terrain_map.get((x-1, y), 0),
                terrain_map.get((x+1, y), 0),
                terrain_map.get((x, y-1), 0),
                terrain_map.get((x, y+1), 0),
            ]
            # Count how many neighbors match
            matches = sum(1 for n in neighbors if n == terrain)
            cluster_score += matches

    print(f"Clustering score: {cluster_score} (higher = more geographic)")
    print(f"Average neighbor matches: {cluster_score / (80 * 105 * 4):.2f}")

    return cluster_score


def check_ptr_sections(scenario):
    """Check if PTR sections contain map data"""
    print("\n=== Checking PTR Sections for Map Data ===")

    for name in ['PTR3', 'PTR4', 'PTR5', 'PTR6']:
        data = scenario.sections.get(name, b'')
        if not data:
            continue

        offset = scenario.pointers.get(name, 0)
        print(f"\n{name} at 0x{offset:06x} ({len(data):,} bytes):")

        # Check if it could be map data (12,500 bytes)
        if len(data) >= 12500:
            print(f"  ✓ Large enough for map data")
            # Show first 200 bytes
            print(hex_dump(data[:200], offset))
            analyze_data_patterns(data[:12500], f"{name} first 12500 bytes")
        else:
            print(f"  Too small for map data")


def main():
    import sys

    if len(sys.argv) < 2:
        print("Usage: python debug_terrain_display.py <scenario.scn>")
        sys.exit(1)

    scenario_file = sys.argv[1]
    print(f"Analyzing: {scenario_file}")

    # Load scenario
    scenario = DdayScenario(scenario_file)
    if not scenario.is_valid:
        print("Invalid scenario file!")
        sys.exit(1)

    # 1. Check PTR sections
    check_ptr_sections(scenario)

    # 2. Read data at offset 0x57E4 (current implementation)
    print("\n" + "="*80)
    print("TASK 1: Verify Current Offset (0x57E4)")
    print("="*80)

    with open(scenario_file, 'rb') as f:
        f.seek(0x57E4)
        current_data = f.read(12500)

    print("\nFirst 200 bytes at offset 0x57E4:")
    print(hex_dump(current_data, 0x57E4, 200))

    analyze_data_patterns(current_data, "Current offset 0x57E4")

    # 3. Test different byte formats
    print("\n" + "="*80)
    print("TASK 2: Test Byte Format Variants")
    print("="*80)

    test_byte_format(
        current_data,
        "Original (terrain=low, variant=high)",
        lambda b: b & 0x0F,
        lambda b: (b >> 4) & 0x0F
    )

    test_byte_format(
        current_data,
        "SWAPPED (terrain=high, variant=low)",
        lambda b: (b >> 4) & 0x0F,
        lambda b: b & 0x0F
    )

    test_byte_format(
        current_data,
        "Full byte as terrain (no variant)",
        lambda b: b,
        lambda b: 0
    )

    # 4. Test different coordinate mappings
    print("\n" + "="*80)
    print("TASK 3: Test Coordinate Mappings")
    print("="*80)

    test_coordinate_mapping(
        current_data,
        "Row-major (current): x = i % 125, y = i // 125",
        lambda i: (i % 125, i // 125)
    )

    test_coordinate_mapping(
        current_data,
        "Column-major: y = i % 100, x = i // 100",
        lambda i: (i // 100, i % 100)
    )

    test_coordinate_mapping(
        current_data,
        "Transposed: y = i % 125, x = i // 125",
        lambda i: (i // 125, i % 125)
    )

    # 5. Try other potential offsets
    print("\n" + "="*80)
    print("TASK 4: Test Alternative Offsets")
    print("="*80)

    # Check a few common patterns
    test_offsets = [
        0x5000,  # Round offset
        0x6000,  # Round offset
        scenario.pointers.get('PTR5', 0),  # PTR5 start
        scenario.pointers.get('PTR6', 0),  # PTR6 start
    ]

    for offset in test_offsets:
        if offset == 0:
            continue
        print(f"\n--- Testing offset 0x{offset:06x} ---")
        with open(scenario_file, 'rb') as f:
            f.seek(offset)
            test_data = f.read(12500)

        if len(test_data) >= 12500:
            analyze_data_patterns(test_data[:12500], f"Offset 0x{offset:06x}")

    print("\n" + "="*80)
    print("RECOMMENDATIONS:")
    print("="*80)
    print("1. Compare the hex dumps above")
    print("2. Look for geographic clustering (similar values together)")
    print("3. Check which format produces sensible terrain distribution")
    print("4. Water (1) and Grass (0) should be most common")
    print("5. Towns (4) should be rare")


if __name__ == '__main__':
    main()
