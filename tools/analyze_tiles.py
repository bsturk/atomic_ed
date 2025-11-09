#!/usr/bin/env python3
"""
Analyze extracted hex tiles and create a mapping to the 17 terrain types.
This script examines tile colors and creates a configuration for the scenario editor.
"""

import os
import json
from PIL import Image
from collections import defaultdict
import colorsys

# Terrain types from the scenario editor
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

def get_dominant_color(image_path):
    """Get the dominant color of an image."""
    img = Image.open(image_path)
    img = img.convert('RGB')

    # Get all pixels
    pixels = list(img.getdata())

    # Count colors, excluding very light colors (likely background)
    color_count = defaultdict(int)
    for pixel in pixels:
        # Skip near-white pixels (background)
        if sum(pixel) < 700:  # Avoid pure white (255+255+255=765)
            color_count[pixel] += 1

    if not color_count:
        return (255, 255, 255)  # Return white if only white pixels

    # Return the most common color
    dominant = max(color_count.items(), key=lambda x: x[1])[0]
    return dominant

def get_average_color(image_path):
    """Get the average color of non-white pixels."""
    img = Image.open(image_path)
    img = img.convert('RGB')

    pixels = list(img.getdata())

    # Filter out very light pixels
    dark_pixels = [p for p in pixels if sum(p) < 700]

    if not dark_pixels:
        return (255, 255, 255)

    avg_r = sum(p[0] for p in dark_pixels) / len(dark_pixels)
    avg_g = sum(p[1] for p in dark_pixels) / len(dark_pixels)
    avg_b = sum(p[2] for p in dark_pixels) / len(dark_pixels)

    return (int(avg_r), int(avg_g), int(avg_b))

def rgb_to_hue(rgb):
    """Convert RGB to hue."""
    r, g, b = [x/255.0 for x in rgb]
    h, s, v = colorsys.rgb_to_hsv(r, g, b)
    return h * 360

def analyze_tiles(tiles_dir):
    """Analyze all tiles and group them by visual characteristics."""
    tile_analysis = []

    for i in range(195):
        tile_path = os.path.join(tiles_dir, f"hex_tile_{i:03d}.png")
        if os.path.exists(tile_path):
            avg_color = get_average_color(tile_path)
            dom_color = get_dominant_color(tile_path)
            hue = rgb_to_hue(avg_color)

            tile_analysis.append({
                'id': i,
                'filename': f"hex_tile_{i:03d}.png",
                'avg_color': avg_color,
                'dom_color': dom_color,
                'hue': hue,
                'row': i // 13,
                'col': i % 13
            })

    return tile_analysis

def categorize_tiles(tile_analysis):
    """Categorize tiles into terrain types based on color analysis."""
    # Manual mapping based on sprite sheet analysis
    # Row 0 (tiles 0-12): appears to be grass/field variations
    # This is a starting point - may need adjustment based on visual inspection

    terrain_mapping = defaultdict(list)

    for tile in tile_analysis:
        tile_id = tile['id']
        row = tile['row']
        col = tile['col']
        hue = tile['hue']
        avg_color = tile['avg_color']

        # Analyze based on row position and color
        # This is an educated guess based on typical sprite sheet organization

        if row == 0:  # First row - likely grass/field variations
            terrain_mapping[0].append(tile_id)  # Grass/Field
        elif row == 1:  # Second row - possibly water/ocean
            terrain_mapping[1].append(tile_id)  # Water/Ocean
        elif row == 2:  # Beach/sand or forest
            if avg_color[1] > 150:  # More yellow/sand-like
                terrain_mapping[2].append(tile_id)  # Beach/Sand
            else:
                terrain_mapping[3].append(tile_id)  # Forest
        elif row == 3:  # Forest or mountains
            if avg_color[1] > avg_color[0]:  # More green
                terrain_mapping[3].append(tile_id)  # Forest
            else:
                terrain_mapping[7].append(tile_id)  # Mountains
        elif row == 4:  # Towns/roads
            if sum(avg_color) < 300:  # Dark
                terrain_mapping[4].append(tile_id)  # Town
            else:
                terrain_mapping[5].append(tile_id)  # Road
        elif row == 5:  # Rivers/canals
            if avg_color[2] > 150:  # Blue-ish
                terrain_mapping[6].append(tile_id)  # River
            else:
                terrain_mapping[15].append(tile_id)  # Canal
        elif row == 6:  # Mountains/cliffs
            terrain_mapping[7].append(tile_id)  # Mountains
        elif row == 7:  # Swamp/bocage
            if avg_color[1] > avg_color[0]:  # Greenish
                terrain_mapping[11].append(tile_id)  # Bocage
            else:
                terrain_mapping[8].append(tile_id)  # Swamp
        elif row == 8:  # Bridges/fortifications
            terrain_mapping[9].append(tile_id)  # Bridge
        elif row == 9:  # Fortifications
            terrain_mapping[10].append(tile_id)  # Fortification
        elif row == 10:  # Cliff variations
            terrain_mapping[12].append(tile_id)  # Cliff
        elif row == 11:  # Village variations
            terrain_mapping[13].append(tile_id)  # Village
        elif row == 12:  # Farm variations
            terrain_mapping[14].append(tile_id)  # Farm
        else:  # Unknown/extra tiles
            terrain_mapping[16].append(tile_id)  # Unknown

    return terrain_mapping

def create_simple_mapping():
    """Create a simple 1-to-1 mapping for initial testing.
    Maps each terrain type to one representative tile.
    """
    # Use first tile from each row as representative
    simple_mapping = {
        0: 0,   # Grass/Field - tile 0
        1: 13,  # Water/Ocean - tile 13
        2: 26,  # Beach/Sand - tile 26
        3: 39,  # Forest - tile 39
        4: 52,  # Town - tile 52
        5: 65,  # Road - tile 65
        6: 78,  # River - tile 78
        7: 91,  # Mountains - tile 91
        8: 104, # Swamp - tile 104
        9: 117, # Bridge - tile 117
        10: 130,# Fortification - tile 130
        11: 143,# Bocage - tile 143
        12: 156,# Cliff - tile 156
        13: 169,# Village - tile 169
        14: 182,# Farm - tile 182
        15: 78, # Canal - reuse River for now (tile 78)
        16: 0   # Unknown - reuse Grass (tile 0)
    }
    return simple_mapping

def main():
    tiles_dir = "extracted_images/hex_tiles"

    print("Analyzing hex tiles...")
    tile_analysis = analyze_tiles(tiles_dir)

    print(f"Analyzed {len(tile_analysis)} tiles")

    # Create categorization
    terrain_mapping = categorize_tiles(tile_analysis)

    # Create simple 1-to-1 mapping
    simple_mapping = create_simple_mapping()

    # Create output configuration
    config = {
        'tiles_directory': tiles_dir,
        'total_tiles': len(tile_analysis),
        'terrain_types': TERRAIN_TYPES,
        'simple_mapping': simple_mapping,
        'full_mapping': {k: v for k, v in terrain_mapping.items()},
        'tile_analysis': tile_analysis
    }

    # Save configuration
    with open('terrain_tile_mapping.json', 'w') as f:
        json.dump(config, f, indent=2)

    print("\nTerrain Tile Mapping Summary:")
    print("=" * 60)
    for terrain_id in range(17):
        terrain_name = TERRAIN_TYPES[terrain_id]
        simple_tile = simple_mapping.get(terrain_id, 0)
        num_variations = len(terrain_mapping.get(terrain_id, []))
        print(f"{terrain_id:2d}. {terrain_name:20s} -> Tile {simple_tile:3d} ({num_variations} variations)")

    print(f"\nConfiguration saved to: terrain_tile_mapping.json")

    # Also create a simpler config file for the scenario editor
    simple_config = {
        'tiles_directory': 'extracted_images/hex_tiles',
        'tile_mapping': simple_mapping,
        'terrain_names': TERRAIN_TYPES
    }

    with open('hex_tile_config.json', 'w') as f:
        json.dump(simple_config, f, indent=2)

    print(f"Simple configuration saved to: hex_tile_config.json")

if __name__ == '__main__':
    main()
