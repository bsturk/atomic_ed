#!/usr/bin/env python3
"""
Map the 14 terrain rows to the 17 terrain types used in D-Day scenarios.

The sprite sheet has 14 rows of terrain variants, but the game uses 17 terrain types.
We need to map correctly, accounting for:
- Multiple visual variants per terrain type
- Rotation/orientation variants within each row
- Special tiles (carriers, flags, planes, etc.)
"""

import json
import os

# The 17 terrain types from the scenario files
TERRAIN_TYPES = {
    0: "Grass/Field",
    1: "Water/Ocean",
    2: "Beach/Sand",
    3: "Forest",
    4: "Town",
    5: "Road",
    6: "River",
    7: "Mountains",
    8: "Swamp",
    9: "Bridge",
    10: "Fortification",
    11: "Bocage",
    12: "Cliff",
    13: "Village",
    14: "Farm",
    15: "Canal",
    16: "Unknown"
}

# Based on visual analysis of scan_width_448.png, map sprite sheet rows to terrain types
# Row descriptions from visual inspection:
# Row 0: Light green fields/grass
# Row 1: Medium green grass variant
# Row 2: Dark green forests
# Row 3: Mixed terrain with water edges
# Row 4: Towns/urban areas (brown/gray)
# Row 5: Ocean with ships/carriers (blue)
# Row 6: Beach/sand (tan)
# Row 7: Green terrain variant
# Row 8: Tan/brown terrain with structures
# Row 9: Mixed terrain
# Row 10: Towns/buildings
# Row 11: Green vegetation
# Row 12: Light green/grass
# Row 13: American flags (getting darker)

# Initial mapping based on visual similarity
# This maps terrain type ID -> (row, default_column)
# Default column is the "base" tile for that terrain type
# The game likely uses different columns for rotation/orientation variants

TERRAIN_TO_ROW_MAPPING = {
    0: (0, 0),   # Grass/Field -> Row 0 (light green fields)
    1: (5, 0),   # Water/Ocean -> Row 5 (blue ocean, has carriers in some variants)
    2: (6, 0),   # Beach/Sand -> Row 6 (tan beach)
    3: (2, 0),   # Forest -> Row 2 (dark green forests)
    4: (4, 0),   # Town -> Row 4 (brown/gray urban)
    5: (8, 0),   # Road -> Row 8 (tan/brown with structures, could be roads)
    6: (3, 0),   # River -> Row 3 (mixed terrain with water edges)
    7: (9, 0),   # Mountains -> Row 9 (mixed terrain, darker)
    8: (7, 0),   # Swamp -> Row 7 (green terrain variant)
    9: (8, 5),   # Bridge -> Row 8 variant (structures)
    10: (10, 0), # Fortification -> Row 10 (towns/buildings)
    11: (11, 0), # Bocage -> Row 11 (green vegetation)
    12: (9, 5),  # Cliff -> Row 9 variant
    13: (10, 5), # Village -> Row 10 variant (buildings)
    14: (12, 0), # Farm -> Row 12 (light green)
    15: (3, 5),  # Canal -> Row 3 variant (water edges)
    16: (1, 0),  # Unknown -> Row 1 (medium green, generic)
}

# Create a configuration for the scenario editor
config = {
    'tiles_directory': 'extracted_images/correct_hex_tiles',
    'source_image': 'extracted_images/scan_width_448.png',
    'grid_info': {
        'rows': 14,
        'cols_per_row': 13,
        'special_tiles': 3
    },
    'terrain_types': TERRAIN_TYPES,
    'terrain_mapping': {}
}

# For each terrain type, provide the default tile and list of variants
for terrain_id, (row, default_col) in TERRAIN_TO_ROW_MAPPING.items():
    terrain_name = TERRAIN_TYPES[terrain_id]

    # Generate list of all variants for this terrain type
    # All 13 columns in the row are variants
    variants = []
    for col in range(13):
        filename = f"hex_tile_r{row:02d}_c{col:02d}.png"
        variants.append({
            'filename': filename,
            'row': row,
            'col': col,
            'is_default': (col == default_col)
        })

    config['terrain_mapping'][terrain_id] = {
        'name': terrain_name,
        'default_tile': f"hex_tile_r{row:02d}_c{default_col:02d}.png",
        'row': row,
        'default_col': default_col,
        'variants': variants
    }

# Add special tiles information
config['special_tiles'] = {
    'black_hex': 'black_hex.png',
    'plane_crash_left': 'plane_left.png',
    'plane_crash_right': 'plane_right.png',
    'flags': [f"hex_tile_r13_c{col:02d}.png" for col in range(13)]  # Row 13 American flags
}

# Add notes about special features
config['notes'] = {
    'carriers': 'Row 5 (Ocean) contains carrier ships in columns 1-2',
    'flags': 'Row 13 contains American flags that get progressively darker',
    'rotation_variants': 'Each row contains ~13 variants showing different rotations/orientations',
    'offset_issue': 'Original sprite sheet has offset - tail of far right hex appears at start of each row'
}

# Save configuration
output_file = 'correct_hex_tile_config.json'
with open(output_file, 'w') as f:
    json.dump(config, f, indent=2)

print(f"Configuration saved to: {output_file}")
print(f"\nTerrain Type Mapping:")
print("=" * 70)
for terrain_id in sorted(TERRAIN_TYPES.keys()):
    if terrain_id in config['terrain_mapping']:
        mapping = config['terrain_mapping'][terrain_id]
        print(f"{terrain_id:2d}. {mapping['name']:20s} -> Row {mapping['row']:2d}, "
              f"Default: {mapping['default_tile']}, "
              f"{len(mapping['variants'])} variants")

print(f"\nSpecial Features:")
print(f"  - Ocean tiles with carriers: {config['notes']['carriers']}")
print(f"  - American flags: {config['notes']['flags']}")
print(f"  - Crash animations: plane_left.png, plane_right.png")
print(f"  - Black hex: black_hex.png")

# Create a simple mapping file for backward compatibility
simple_config = {
    'tiles_directory': 'extracted_images/correct_hex_tiles',
    'tile_mapping': {str(terrain_id): mapping['default_tile']
                     for terrain_id, mapping in config['terrain_mapping'].items()},
    'terrain_names': TERRAIN_TYPES
}

with open('correct_hex_tile_config_simple.json', 'w') as f:
    json.dump(simple_config, f, indent=2)

print(f"\nSimple configuration saved to: correct_hex_tile_config_simple.json")
