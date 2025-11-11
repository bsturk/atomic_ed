#!/usr/bin/env python3
"""Test that hex tiles have actual colors (not black)"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from lib.hex_tile_loader import load_hex_tiles

tiles = load_hex_tiles()
if not tiles:
    print("✗ Failed to load tiles")
    exit(1)

print(f"✓ Loaded {len(tiles)} tiles")
print()

# Check each terrain type
for terrain_id in sorted(tiles.keys()):
    tile = tiles[terrain_id]
    pixels = list(tile.getdata())

    # Count non-black, non-transparent pixels
    colored_pixels = 0
    for px in pixels:
        if px[3] > 0:  # Has some alpha
            if px[0] > 10 or px[1] > 10 or px[2] > 10:  # Not pure black
                colored_pixels += 1

    total_pixels = len(pixels)
    percent_colored = (colored_pixels / total_pixels) * 100

    # Get unique colors
    unique_colors = len(set(pixels))

    status = "✓" if percent_colored > 50 else "✗"
    print(f"{status} Terrain {terrain_id:2d}: {colored_pixels:4d}/{total_pixels} colored pixels ({percent_colored:.1f}%), {unique_colors} unique colors")
