#!/usr/bin/env python3
"""
Extract hex tiles correctly from scan_width_448.png
Based on user analysis:
- 14 strips (rows) of similar terrain with variants
- Strip 6 has ocean tiles with carriers
- Strip 14 has American flags getting darker
- Last row has: black hex, plane down-left, plane down-right
- Starting point offset issue: tail of far right hex, garbage, then correct hexes
"""

from PIL import Image
import json
import os

# Open the correct sprite sheet
img = Image.open('extracted_images/scan_width_448.png')
width, height = img.size

print(f"Image size: {width} × {height}")

# Analyze the structure
# Hex tiles appear to be approximately 34 pixels wide, 38 pixels tall
HEX_WIDTH = 34
HEX_HEIGHT = 38

# Calculate grid dimensions
cols_estimate = width // HEX_WIDTH
rows_estimate = height // HEX_HEIGHT

print(f"Estimated grid: {cols_estimate} columns × {rows_estimate} rows")

# User says there are 14 strips (rows) of terrain types
# Let's figure out the exact positioning

# First, let's examine the actual dimensions more carefully
print(f"\nActual dimensions:")
print(f"  Width: {width} ({width / HEX_WIDTH:.2f} hex widths)")
print(f"  Height: {height} ({height / HEX_HEIGHT:.2f} hex heights)")

# The user mentioned there's an offset at the start showing the tail of the far right hex
# Let's try to find the correct starting offset

# Based on visual inspection, each row should have about 13 variants
VARIANTS_PER_ROW = 13
NUM_TERRAIN_ROWS = 14  # Plus one partial row with special tiles

# Let's try to extract with careful positioning
# The image shows hexes arranged in rows

# Looking at the image, it appears each hex is 32 pixels wide in the packed arrangement
# and rows are 38 pixels apart

# Let me examine more carefully - the width is 448, and we have ~13 hexes per row
# 448 / 13 ≈ 34.46

# Let's calculate based on what we can see
actual_hex_width = width / VARIANTS_PER_ROW
print(f"\nCalculated hex width for {VARIANTS_PER_ROW} per row: {actual_hex_width:.2f} pixels")

# Create output directory
output_dir = 'extracted_images/correct_hex_tiles'
os.makedirs(output_dir, exist_ok=True)

# Extract tiles
tiles_extracted = []
tile_id = 0

# Extract main terrain rows (14 rows)
for row in range(NUM_TERRAIN_ROWS):
    y_offset = row * HEX_HEIGHT

    for col in range(VARIANTS_PER_ROW):
        # Try to account for the offset issue
        # The user says there's garbage at the start, so let's try a small offset
        x_offset = col * HEX_WIDTH + 2  # Small offset to skip garbage

        # Extract the hex tile
        try:
            tile = img.crop((x_offset, y_offset, x_offset + HEX_WIDTH, y_offset + HEX_HEIGHT))

            # Save the tile
            filename = f"hex_tile_r{row:02d}_c{col:02d}.png"
            filepath = os.path.join(output_dir, filename)
            tile.save(filepath)

            tiles_extracted.append({
                'id': tile_id,
                'row': row,
                'col': col,
                'filename': filename,
                'position': {'x': x_offset, 'y': y_offset}
            })

            tile_id += 1
        except Exception as e:
            print(f"Error extracting tile at row {row}, col {col}: {e}")

# Extract special tiles from last row (row 14)
# Black hex, plane left, plane right
special_row = NUM_TERRAIN_ROWS
y_offset = special_row * HEX_HEIGHT

special_tiles = [
    ('black_hex', 0),
    ('plane_left', 1),
    ('plane_right', 2)
]

for name, col in special_tiles:
    x_offset = col * HEX_WIDTH + 2

    try:
        tile = img.crop((x_offset, y_offset, x_offset + HEX_WIDTH, y_offset + HEX_HEIGHT))
        filename = f"{name}.png"
        filepath = os.path.join(output_dir, filename)
        tile.save(filepath)

        tiles_extracted.append({
            'id': tile_id,
            'row': special_row,
            'col': col,
            'filename': filename,
            'type': 'special',
            'name': name,
            'position': {'x': x_offset, 'y': y_offset}
        })

        tile_id += 1
    except Exception as e:
        print(f"Error extracting special tile {name}: {e}")

print(f"\nExtracted {len(tiles_extracted)} tiles total")
print(f"  - {NUM_TERRAIN_ROWS} terrain rows × {VARIANTS_PER_ROW} variants = {NUM_TERRAIN_ROWS * VARIANTS_PER_ROW} terrain tiles")
print(f"  - {len(special_tiles)} special tiles")

# Save manifest
manifest = {
    'source_image': 'extracted_images/scan_width_448.png',
    'image_size': {'width': width, 'height': height},
    'tile_size': {'width': HEX_WIDTH, 'height': HEX_HEIGHT},
    'grid': {
        'terrain_rows': NUM_TERRAIN_ROWS,
        'variants_per_row': VARIANTS_PER_ROW,
        'special_tiles': len(special_tiles)
    },
    'total_tiles': len(tiles_extracted),
    'tiles': tiles_extracted,
    'terrain_row_descriptions': {
        0: "Light green fields/grass",
        1: "Medium green grass variant",
        2: "Dark green forests",
        3: "Mixed terrain with water edges",
        4: "Towns/urban areas (brown/gray)",
        5: "Ocean with ships/carriers (blue)",
        6: "Beach/sand (tan)",
        7: "Green terrain variant",
        8: "Tan/brown terrain with structures",
        9: "Mixed terrain",
        10: "Towns/buildings",
        11: "Green vegetation",
        12: "Light green/grass",
        13: "American flags (getting darker)"
    }
}

manifest_path = os.path.join(output_dir, 'tiles_manifest.json')
with open(manifest_path, 'w') as f:
    json.dump(manifest, f, indent=2)

print(f"\nManifest saved to: {manifest_path}")
print(f"Tiles saved to: {output_dir}/")

# Analyze row 5 (ocean with carriers) and row 13 (flags)
print("\nSpecial rows:")
print(f"  Row 5 (ocean): Should contain carriers in some tiles")
print(f"  Row 13 (flags): Should show American flags getting darker")
