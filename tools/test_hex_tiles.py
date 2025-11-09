#!/usr/bin/env python3
"""
Test script to verify hex tile loading works correctly
"""

import json
import os
from PIL import Image

def test_hex_tiles():
    """Test that hex tiles can be loaded properly"""
    print("Testing hex tile loading...")

    # Load configuration
    config_path = 'hex_tile_config.json'
    if not os.path.exists(config_path):
        print(f"ERROR: Config not found: {config_path}")
        return False

    with open(config_path, 'r') as f:
        config = json.load(f)

    tiles_dir = config['tiles_directory']
    tile_mapping = config['tile_mapping']
    terrain_names = config['terrain_names']

    print(f"\nTiles directory: {tiles_dir}")
    print(f"Number of terrain types: {len(tile_mapping)}")

    # Test loading each terrain type's tile
    success_count = 0
    for terrain_id, tile_filename in tile_mapping.items():
        terrain_id = int(terrain_id)
        terrain_name = terrain_names.get(str(terrain_id), f"Type {terrain_id}")

        # tile_filename is already the filename string (e.g., "hex_tile_r00_c00.png")
        tile_path = os.path.join(tiles_dir, tile_filename)

        if os.path.exists(tile_path):
            try:
                img = Image.open(tile_path)
                width, height = img.size
                mode = img.mode
                print(f"✓ Terrain {terrain_id:2d} ({terrain_name:20s}): {tile_filename} ({width}x{height}, {mode})")
                success_count += 1
            except Exception as e:
                print(f"✗ Terrain {terrain_id:2d} ({terrain_name:20s}): ERROR loading {tile_filename}: {e}")
        else:
            print(f"✗ Terrain {terrain_id:2d} ({terrain_name:20s}): File not found: {tile_path}")

    print(f"\nSuccessfully loaded {success_count}/{len(tile_mapping)} terrain tile images")

    if success_count == len(tile_mapping):
        print("\n✓ All hex tiles loaded successfully!")
        return True
    else:
        print(f"\n✗ Failed to load {len(tile_mapping) - success_count} hex tiles")
        return False

if __name__ == '__main__':
    test_hex_tiles()
