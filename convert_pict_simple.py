#!/usr/bin/env python3
"""
Simplified PICT to PNG Converter
Uses a more direct approach to extract pixel data
"""

import struct
import sys
from pathlib import Path
from PIL import Image


def load_clut(clut_path):
    """Load color lookup table (palette) from clut resource"""
    if not Path(clut_path).exists():
        print("Warning: No clut file found, using default grayscale palette")
        palette = []
        for i in range(256):
            palette.extend([i, i, i])
        return palette

    with open(clut_path, 'rb') as f:
        data = f.read()

    seed, flags, num_colors = struct.unpack('>IHH', data[:8])
    num_colors += 1

    print(f"Loading palette: {num_colors} colors")

    palette = []
    offset = 8

    for i in range(num_colors):
        if offset + 8 <= len(data):
            value_idx, r, g, b = struct.unpack('>HHHH', data[offset:offset+8])
            # Convert from 16-bit to 8-bit (take high byte)
            palette.extend([r >> 8, g >> 8, b >> 8])
            offset += 8

    # Pad to 256 colors if needed
    while len(palette) < 768:
        palette.extend([0, 0, 0])

    print(f"Palette loaded: {len(palette)//3} colors")
    return palette


def unpack_packbits(data):
    """Decompress PackBits compressed data"""
    result = []
    i = 0

    while i < len(data):
        if i >= len(data):
            break

        flag = data[i]
        i += 1

        if flag < 128:
            # Copy next (flag + 1) bytes literally
            count = flag + 1
            for j in range(count):
                if i < len(data):
                    result.append(data[i])
                    i += 1
                else:
                    break
        elif flag > 128:
            # Repeat next byte (257 - flag) times
            count = 257 - flag
            if i < len(data):
                byte_to_repeat = data[i]
                i += 1
                for j in range(count):
                    result.append(byte_to_repeat)
        # flag == 128 is a no-op

    return bytes(result)


def extract_pict_data(pict_path, width, height):
    """Extract pixel data from PICT file using heuristics"""

    with open(pict_path, 'rb') as f:
        # Skip 512-byte header
        f.seek(512)

        # Read all data
        data = f.read()

        print(f"Total PICT data: {len(data)} bytes")

        # Method 1: Look for the 0x0098 opcode (PackBitsRect)
        found_offset = -1
        for i in range(min(10000, len(data) - 2)):
            word = struct.unpack('>H', data[i:i+2])[0]
            if word == 0x0098:
                # Check if this looks like the start of a PixMap structure
                # PixMap should have rowBytes with high bit set
                if i + 2 < len(data):
                    potential_rowbytes = struct.unpack('>H', data[i+2:i+4])[0]
                    if (potential_rowbytes & 0x8000) and (potential_rowbytes & 0x3FFF) < 1000:
                        found_offset = i + 2
                        print(f"Found potential PixMap at offset {found_offset}")
                        break

        if found_offset < 0:
            print("Could not find PixMap structure, trying fallback...")
            # Fallback: look for a structure that looks like it starts with rowBytes
            for i in range(10, min(1000, len(data) - 50)):
                potential_rowbytes = struct.unpack('>H', data[i:i+2])[0]
                if (potential_rowbytes & 0x8000):
                    row_bytes = potential_rowbytes & 0x3FFF
                    # Check if there's a reasonable bounds rectangle after
                    try:
                        bounds = struct.unpack('>hhhh', data[i+2:i+10])
                        w = bounds[3] - bounds[1]
                        h = bounds[2] - bounds[0]
                        # Use little-endian interpretation if needed
                        if not (400 < w < 600 and 500 < h < 600):
                            # Try little-endian for bottom/right
                            bottom = struct.unpack('<H', data[i+6:i+8])[0]
                            right = struct.unpack('<H', data[i+8:i+10])[0]
                            w = right
                            h = bottom

                        if 400 < w < 600 and 500 < h < 600:
                            found_offset = i
                            print(f"Found PixMap-like structure at offset {found_offset}")
                            print(f"  rowBytes={row_bytes}, dimensions={w}x{h}")
                            break
                    except:
                        pass

        if found_offset < 0:
            print("Error: Could not locate PixMap structure")
            return None

        # Parse PixMap structure starting at found_offset
        offset = found_offset

        row_bytes_raw = struct.unpack('>H', data[offset:offset+2])[0]
        row_bytes = row_bytes_raw & 0x3FFF
        offset += 2

        # Bounds - try both interpretations
        bounds_data = data[offset:offset+8]
        top = struct.unpack('>H', bounds_data[0:2])[0]
        left = struct.unpack('>H', bounds_data[2:4])[0]
        bottom = struct.unpack('<H', bounds_data[4:6])[0]  # Little-endian
        right = struct.unpack('<H', bounds_data[6:8])[0]   # Little-endian
        offset += 8

        actual_width = right - left
        actual_height = bottom - top

        print(f"\nPixMap info:")
        print(f"  rowBytes: {row_bytes}")
        print(f"  bounds: top={top}, left={left}, bottom={bottom}, right={right}")
        print(f"  dimensions: {actual_width} x {actual_height}")

        # Skip PixMap fields (version, packType, packSize, hRes, vRes, pixelType, etc.)
        # Total: 2 + 2 + 4 + 4 + 4 + 2 + 2 + 2 + 2 + 4 + 4 + 4 = 38 bytes
        offset += 38

        # Skip pmTable - this is a handle to a color table
        # It's followed by the source rect, dest rect, and mode
        # srcRect (8), dstRect (8), mode (2) = 18 bytes
        offset += 18

        print(f"Starting pixel data extraction at offset {offset}")

        # Now extract packed scanlines
        pixel_data = []

        for row_num in range(actual_height):
            # Read the packed size for this row
            if row_bytes < 8:
                packed_size = data[offset]
                offset += 1
            elif row_bytes > 250:
                packed_size = struct.unpack('>H', data[offset:offset+2])[0]
                offset += 2
            else:
                packed_size = data[offset]
                offset += 1

            # Read packed data
            packed_row = data[offset:offset+packed_size]
            offset += packed_size

            # Decompress
            unpacked = unpack_packbits(packed_row)
            pixel_data.append(unpacked[:actual_width])

            if row_num < 3 or row_num >= actual_height - 3:
                print(f"  Row {row_num}: packed={packed_size} bytes, unpacked={len(unpacked)} bytes")

        # Combine all rows
        all_pixels = b''.join(pixel_data)
        print(f"\nExtracted {len(all_pixels)} bytes of pixel data")
        print(f"Expected: {actual_width * actual_height} bytes")

        return all_pixels, actual_width, actual_height


def main():
    pict_file = '/home/user/atomic_ed/extracted_images/PICT_128.pict'
    clut_file = '/home/user/atomic_ed/extracted_images/clut_8.bin'
    output_file = '/home/user/atomic_ed/extracted_images/PICT_128.png'

    # Known dimensions from analysis
    expected_width = 442
    expected_height = 570

    print("=" * 80)
    print("PICT to PNG Converter (Simplified)")
    print("=" * 80)
    print()

    # Load palette
    palette = load_clut(clut_file)

    # Extract pixel data
    result = extract_pict_data(pict_file, expected_width, expected_height)

    if result is None:
        print("Failed to extract pixel data")
        return 1

    pixel_data, width, height = result

    # Create PNG
    img = Image.new('P', (width, height))
    img.putpalette(palette)

    # Ensure we have the right amount of data
    expected_size = width * height
    actual_size = len(pixel_data)

    if actual_size < expected_size:
        print(f"Warning: Padding pixel data ({actual_size} -> {expected_size})")
        pixel_data += b'\x00' * (expected_size - actual_size)
    elif actual_size > expected_size:
        print(f"Warning: Truncating pixel data ({actual_size} -> {expected_size})")
        pixel_data = pixel_data[:expected_size]

    img.putdata(list(pixel_data))
    img.save(output_file)

    print(f"\nConversion successful!")
    print(f"Saved: {output_file}")
    print(f"Dimensions: {width} x {height}")

    return 0


if __name__ == '__main__':
    sys.exit(main())
