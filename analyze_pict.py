#!/usr/bin/env python3
"""
Enhanced PICT analyzer to extract image information
"""

import struct
import sys

def analyze_pict(filepath):
    """Analyze a PICT file structure"""
    with open(filepath, 'rb') as f:
        # Skip 512-byte header (added by our export)
        f.seek(512)

        # Read PICT header
        pict_size = struct.unpack('>H', f.read(2))[0]
        frame = struct.unpack('>hhhh', f.read(8))  # signed shorts for rect
        top, left, bottom, right = frame

        print(f"File: {filepath}")
        print(f"PICT size field: 0x{pict_size:04x}")
        print(f"Frame (as read): top={top}, left={left}, bottom={bottom}, right={right}")

        # Try alternative interpretation
        width = right - left
        height = bottom - top
        print(f"Dimensions (if rect): {width} x {height}")

        # Look for PICT version opcode
        while True:
            pos = f.tell()
            if pos > 512 + 500:  # Don't search too far
                break

            try:
                opcode = struct.unpack('>H', f.read(2))[0]
            except:
                break

            if opcode == 0x0011:
                print(f"\nFound PICT v1 version opcode (0x0011) at offset {pos}")
                version = struct.unpack('>H', f.read(2))[0]
                print(f"Version: {version}")
                break
            elif opcode == 0x0098:
                print(f"\nFound PICT v2 version opcode (0x0098) at offset {pos}")
                # Version opcode for PICT v2
                # Followed by version number
                version = struct.unpack('>H', f.read(2))[0]
                print(f"Version: 0x{version:04x}")
                break
            elif opcode == 0x001E:
                print(f"\nFound DefHilite opcode (0x001E) at offset {pos}")
            elif opcode == 0x009A:
                print(f"\nFound DirectBitsRect opcode (0x009A) at offset {pos}")
                # This is the actual pixel data for PICT v2
                break
            elif opcode == 0x0098:
                print(f"\nFound Version opcode (0x0098) at offset {pos}")
                break
            elif opcode == 0x00FF:
                print(f"\nFound OpEndPic opcode (0x00FF) at offset {pos}")
                break
            elif (opcode & 0xFF00) == 0x8000:
                # Reserved opcodes
                f.seek(pos + 2)
            else:
                # Unknown opcode, try next position
                f.seek(pos + 1)

        # Try to find PixMap data (look for 0x9A opcode - DirectBitsRect)
        f.seek(512)
        data = f.read(2000)

        # Look for DirectBitsRect (0x009A) or PackBitsRect (0x0098)
        for i in range(len(data) - 2):
            word = struct.unpack('>H', data[i:i+2])[0]
            if word == 0x009A:
                print(f"\nFound DirectBitsRect at offset {512 + i}")
            elif word == 0x0098:
                print(f"\nFound PackBitsRect at offset {512 + i}")
            elif word == 0x009C:
                print(f"\nFound PackBitsRgn at offset {512 + i}")

        # Look for common pixel depths
        print("\nSearching for PixMap structures (pixel depth markers)...")
        for i in range(len(data) - 50):
            # PixMap has a pixelSize field
            if i + 28 < len(data):
                pixel_size = struct.unpack('>H', data[i+28:i+30])[0]
                if pixel_size in [1, 2, 4, 8, 16, 24, 32]:
                    # Might be a PixMap - check bounds too
                    bounds = struct.unpack('>hhhh', data[i+8:i+16])
                    w = bounds[3] - bounds[1]
                    h = bounds[2] - bounds[0]
                    if 10 < w < 2000 and 10 < h < 2000:
                        print(f"  Possible PixMap at offset {512 + i}:")
                        print(f"    Bounds: {bounds} -> {w}x{h}")
                        print(f"    Pixel depth: {pixel_size} bits")

def main():
    files_to_check = [
        '/home/user/atomic_ed/extracted_images/PICT_128.pict',
        '/home/user/atomic_ed/extracted_images/PICT_200_Large Hex Edges.pict',
        '/home/user/atomic_ed/extracted_images/PICT_130.pict',
    ]

    for filepath in files_to_check:
        print("=" * 80)
        try:
            analyze_pict(filepath)
        except Exception as e:
            print(f"Error analyzing {filepath}: {e}")
        print()

if __name__ == '__main__':
    main()
