#!/usr/bin/env python3
"""Analyze scan_width_448.png to find the correct hex extraction offset"""

from PIL import Image

# Load sprite sheet
img = Image.open('extracted_images/scan_width_448.png')
width, height = img.size
print(f"Sprite sheet: {width}x{height}")

HEX_WIDTH = 34
HEX_HEIGHT = 38

# Get pixel data
pixels = list(img.getdata())

# Check different offset values to see which gives cleanest extraction
print("\nTesting different x-offsets for column boundaries:")
print("(Looking for consistent spacing between hex boundaries)")

for test_offset in range(0, 10):
    print(f"\nOffset {test_offset}:")

    # Sample the first few columns
    for col in range(3):
        x = col * HEX_WIDTH + test_offset
        if x < width:
            # Sample a few pixels from this column start
            sample_colors = []
            for y in [0, 1, 2]:
                if y < height:
                    px_idx = y * width + x
                    if px_idx < len(pixels):
                        sample_colors.append(pixels[px_idx])

            print(f"  Col {col} @ x={x:3d}: colors = {sample_colors[:3]}")

# Check for white pixels (likely background)
print("\n\nChecking for white/background color:")
if img.mode == 'P':
    palette = img.getpalette()
    # Check which color index is white
    for i in range(min(256, len(palette)//3)):
        r = palette[i*3]
        g = palette[i*3 + 1]
        b = palette[i*3 + 2]
        if r > 250 and g > 250 and b > 250:
            print(f"  Color index {i} is white: RGB({r},{g},{b})")
        elif r == 0 and g == 0 and b == 0:
            print(f"  Color index {i} is black: RGB({r},{g},{b})")
