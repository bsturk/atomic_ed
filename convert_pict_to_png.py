#!/usr/bin/env python3
"""
PICT to PNG Converter
Converts Mac PICT v2 format files to PNG
Handles 8-bit indexed color with PackBits compression
"""

import struct
import sys
from pathlib import Path
from PIL import Image


class PICTConverter:
    def __init__(self, pict_path, clut_path=None):
        self.pict_path = Path(pict_path)
        self.clut_path = Path(clut_path) if clut_path else None
        self.palette = None
        self.width = 0
        self.height = 0
        self.pixel_data = None

    def load_clut(self):
        """Load color lookup table (palette) from clut resource"""
        if not self.clut_path or not self.clut_path.exists():
            print("Warning: No clut file found, using default grayscale palette")
            # Create default grayscale palette
            palette = []
            for i in range(256):
                palette.extend([i, i, i])
            return palette

        with open(self.clut_path, 'rb') as f:
            data = f.read()

        # Parse clut structure:
        # 4 bytes: seed
        # 2 bytes: flags
        # 2 bytes: color count - 1
        # Then entries: 2 bytes index, 2 bytes R, 2 bytes G, 2 bytes B

        seed, flags, num_colors = struct.unpack('>IHH', data[:8])
        num_colors += 1

        print(f"Loading palette: {num_colors} colors")

        palette = []
        offset = 8

        for i in range(num_colors):
            # Each entry is 8 bytes: 2 bytes value index, 2 bytes each for R, G, B
            if offset + 8 <= len(data):
                value_idx, r, g, b = struct.unpack('>HHHH', data[offset:offset+8])
                # Convert from 16-bit to 8-bit (take high byte)
                palette.extend([r >> 8, g >> 8, b >> 8])
                offset += 8

        # Pad to 256 colors if needed
        while len(palette) < 768:  # 256 * 3
            palette.extend([0, 0, 0])

        print(f"Palette loaded: {len(palette)//3} colors")
        return palette

    def unpack_packbits(self, data, row_bytes):
        """Decompress PackBits compressed data

        PackBits algorithm:
        - If byte n is 0-127: copy next n+1 bytes literally
        - If byte n is 129-255: repeat next byte 257-n times
        - If byte n is 128: no-op
        """
        result = []
        i = 0

        while i < len(data) and len(result) < row_bytes:
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

    def parse_pict(self):
        """Parse PICT file and extract image data"""
        with open(self.pict_path, 'rb') as f:
            # Skip 512-byte header (added during extraction)
            f.seek(512)

            # Read PICT header
            pict_size = struct.unpack('>H', f.read(2))[0]
            frame = struct.unpack('>hhhh', f.read(8))
            top, left, bottom, right = frame

            self.width = right - left
            self.height = bottom - top

            print(f"PICT dimensions: {self.width} x {self.height}")
            print(f"Frame: top={top}, left={left}, bottom={bottom}, right={right}")

            # Now we need to find the DirectBitsRect or PackBitsRect opcode
            # and parse the PixMap structure

            found_pixel_data = False
            max_search = 10000  # Don't search too far
            search_start = f.tell()

            while f.tell() - search_start < max_search:
                pos = f.tell()

                try:
                    opcode = struct.unpack('>H', f.read(2))[0]
                except:
                    break

                # Look for opcodes that contain pixel data
                if opcode == 0x0098:  # PackBitsRect
                    print(f"Found PackBitsRect opcode at offset {pos}")
                    found_pixel_data = True
                    break
                elif opcode == 0x009A:  # DirectBitsRect
                    print(f"Found DirectBitsRect opcode at offset {pos}")
                    found_pixel_data = True
                    break
                elif opcode == 0x00FF:  # OpEndPic
                    print(f"Found end of PICT at offset {pos}")
                    break

            if not found_pixel_data:
                # Try alternative: scan for PixMap structure
                print("Searching for PixMap structure...")
                f.seek(512 + 10)  # Start after header

            # At this point we should be at or near the PixMap structure
            # PixMap structure for PackBitsRect:
            # - rowBytes (2 bytes) - high bit set indicates PixMap vs BitMap
            # - bounds (8 bytes)
            # - version (2 bytes)
            # - packType (2 bytes)
            # - packSize (4 bytes)
            # - hRes (4 bytes)
            # - vRes (4 bytes)
            # - pixelType (2 bytes)
            # - pixelSize (2 bytes)
            # - cmpCount (2 bytes)
            # - cmpSize (2 bytes)
            # - planeBytes (4 bytes)
            # - pmTable (4 bytes - handle to color table)
            # - pmReserved (4 bytes)

            # Read PixMap
            pm_start = f.tell()

            # For PackBitsRect, there's also a pmVersion field before rowBytes
            # Let's try reading the structure
            row_bytes_raw = struct.unpack('>H', f.read(2))[0]
            is_pixmap = (row_bytes_raw & 0x8000) != 0
            row_bytes = row_bytes_raw & 0x3FFF

            print(f"RowBytes: {row_bytes} (PixMap: {is_pixmap})")

            # Read bounds
            pm_bounds = struct.unpack('>hhhh', f.read(8))
            pm_top, pm_left, pm_bottom, pm_right = pm_bounds
            pm_width = pm_right - pm_left
            pm_height = pm_bottom - pm_top

            print(f"PixMap bounds: {pm_bounds} -> {pm_width}x{pm_height}")

            # Update dimensions if needed
            if pm_width > 0 and pm_height > 0:
                self.width = pm_width
                self.height = pm_height

            # Read version, packType, packSize
            version = struct.unpack('>H', f.read(2))[0]
            pack_type = struct.unpack('>H', f.read(2))[0]
            pack_size = struct.unpack('>I', f.read(4))[0]

            print(f"Version: {version}, PackType: {pack_type}, PackSize: {pack_size}")

            # Skip hRes, vRes (8 bytes)
            f.read(8)

            # Read pixel format info
            pixel_type = struct.unpack('>H', f.read(2))[0]
            pixel_size = struct.unpack('>H', f.read(2))[0]
            cmp_count = struct.unpack('>H', f.read(2))[0]
            cmp_size = struct.unpack('>H', f.read(2))[0]

            print(f"PixelType: {pixel_type}, PixelSize: {pixel_size}, CmpCount: {cmp_count}, CmpSize: {cmp_size}")

            # Skip planeBytes, pmTable, pmReserved (12 bytes)
            f.read(12)

            # Now comes the source and destination rects, and mode
            # srcRect (8 bytes)
            src_rect = struct.unpack('>hhhh', f.read(8))
            print(f"Source rect: {src_rect}")

            # dstRect (8 bytes)
            dst_rect = struct.unpack('>hhhh', f.read(8))
            print(f"Dest rect: {dst_rect}")

            # mode (2 bytes)
            mode = struct.unpack('>H', f.read(2))[0]
            print(f"Transfer mode: {mode}")

            # Now comes the actual pixel data
            # For PackBits, each scanline is compressed separately
            print(f"\nReading pixel data for {self.height} rows...")

            pixel_rows = []

            for row in range(self.height):
                # For rowBytes < 8, the count is 1 byte, otherwise 2 bytes
                if row_bytes < 8:
                    packed_size = struct.unpack('>B', f.read(1))[0]
                elif row_bytes > 250:
                    packed_size = struct.unpack('>H', f.read(2))[0]
                else:
                    packed_size = struct.unpack('>B', f.read(1))[0]

                # Read packed data
                packed_data = f.read(packed_size)

                # Decompress
                unpacked = self.unpack_packbits(packed_data, row_bytes)

                # Take only width pixels (in case row_bytes includes padding)
                pixel_rows.append(unpacked[:self.width])

                if row < 3 or row >= self.height - 3:
                    print(f"  Row {row}: packed size={packed_size}, unpacked size={len(unpacked)}")

            # Combine all rows
            self.pixel_data = b''.join(pixel_rows)
            print(f"\nTotal pixel data: {len(self.pixel_data)} bytes")
            print(f"Expected: {self.width * self.height} bytes")

            return True

    def convert_to_png(self, output_path):
        """Convert the parsed PICT data to PNG"""
        if self.pixel_data is None:
            print("Error: No pixel data loaded")
            return False

        # Load palette
        self.palette = self.load_clut()

        # Create PIL image
        img = Image.new('P', (self.width, self.height))
        img.putpalette(self.palette)

        # Set pixel data
        # Ensure we have the right amount of data
        expected_size = self.width * self.height
        actual_size = len(self.pixel_data)

        if actual_size < expected_size:
            print(f"Warning: Pixel data too small ({actual_size} < {expected_size}), padding with zeros")
            self.pixel_data += b'\x00' * (expected_size - actual_size)
        elif actual_size > expected_size:
            print(f"Warning: Pixel data too large ({actual_size} > {expected_size}), truncating")
            self.pixel_data = self.pixel_data[:expected_size]

        img.putdata(list(self.pixel_data))

        # Save as PNG
        output_path = Path(output_path)
        img.save(output_path)

        print(f"\nSaved PNG: {output_path}")
        print(f"Dimensions: {self.width} x {self.height}")

        return True


def main():
    pict_file = '/home/user/atomic_ed/extracted_images/PICT_128.pict'
    clut_file = '/home/user/atomic_ed/extracted_images/clut_8.bin'
    output_file = '/home/user/atomic_ed/extracted_images/PICT_128.png'

    if not Path(pict_file).exists():
        print(f"Error: PICT file not found: {pict_file}")
        return 1

    print("=" * 80)
    print("PICT to PNG Converter")
    print("=" * 80)
    print()

    converter = PICTConverter(pict_file, clut_file)

    if converter.parse_pict():
        if converter.convert_to_png(output_file):
            print("\nConversion successful!")
            return 0
        else:
            print("\nConversion failed!")
            return 1
    else:
        print("\nFailed to parse PICT file!")
        return 1


if __name__ == '__main__':
    sys.exit(main())
