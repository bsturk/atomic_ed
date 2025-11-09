#!/usr/bin/env python3
"""
Re-extract hex tiles with correct offset and transparent background
"""

from PIL import Image
import os

# Load sprite sheet
img = Image.open('extracted_images/scan_width_448.png')
width, height = img.size
print(f"Sprite sheet: {width}x{height}, mode: {img.mode}")

HEX_WIDTH = 34
HEX_HEIGHT = 38
VARIANTS_PER_ROW = 13
NUM_TERRAIN_ROWS = 14

# Get the palette to identify white/background color
if img.mode == 'P':
    palette = img.getpalette()

    # Find white color index (background to make transparent)
    white_index = None
    black_index = None
    for i in range(256):
        r = palette[i*3]
        g = palette[i*3 + 1]
        b = palette[i*3 + 2]
        if r > 250 and g > 250 and b > 250:
            white_index = i
            print(f"White background at index {i}")
        if r == 0 and g == 0 and b == 0:
            black_index = i

    # Convert to RGBA mode for transparency
    img = img.convert('RGBA')
    pixels = img.load()

    # Make white background transparent
    if white_index is not None:
        original_palette_img = Image.open('extracted_images/scan_width_448.png')
        original_pixels = list(original_palette_img.getdata())

        for y in range(height):
            for x in range(width):
                idx = y * width + x
                if original_pixels[idx] == white_index:
                    pixels[x, y] = (255, 255, 255, 0)  # Transparent

        print(f"Made white (index {white_index}) transparent")

# Create output directory
output_dir = 'extracted_images/correct_hex_tiles'
os.makedirs(output_dir, exist_ok=True)

# Extract tiles with NO offset (offset 0)
tiles_extracted = 0
print(f"\nExtracting {NUM_TERRAIN_ROWS} rows x {VARIANTS_PER_ROW} columns...")

for row in range(NUM_TERRAIN_ROWS):
    y_offset = row * HEX_HEIGHT

    for col in range(VARIANTS_PER_ROW):
        # Use offset 0 - no offset!
        x_offset = col * HEX_WIDTH

        # Extract tile
        tile = img.crop((x_offset, y_offset, x_offset + HEX_WIDTH, y_offset + HEX_HEIGHT))

        # Save
        filename = f"hex_tile_r{row:02d}_c{col:02d}.png"
        filepath = os.path.join(output_dir, filename)
        tile.save(filepath)
        tiles_extracted += 1

print(f"✓ Extracted {tiles_extracted} tiles with offset=0 and transparent backgrounds")
print(f"✓ Saved to {output_dir}/")
