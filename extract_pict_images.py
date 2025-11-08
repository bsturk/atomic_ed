#!/usr/bin/env python3
"""
Extract and convert PICT resources from PCWATW.REZ to PNG images
"""

import struct
import sys
from pathlib import Path
from PIL import Image

def read_color_table(f, data_offset, map_offset):
    """Read the color lookup table from the resource file"""
    # Find clut resource
    f.seek(map_offset + 24)
    type_list_offset, name_list_offset = struct.unpack('>HH', f.read(4))
    num_types = struct.unpack('>H', f.read(2))[0] + 1

    type_list_pos = map_offset + type_list_offset + 2
    f.seek(type_list_pos)

    for i in range(num_types):
        res_type = f.read(4).decode('ascii', errors='ignore')
        res_count = struct.unpack('>H', f.read(2))[0] + 1
        ref_list_offset = struct.unpack('>H', f.read(2))[0]

        if res_type == 'clut':
            ref_list_pos = type_list_pos - 2 + ref_list_offset
            f.seek(ref_list_pos)

            res_id = struct.unpack('>H', f.read(2))[0]
            name_offset = struct.unpack('>h', f.read(2))[0]
            attributes = f.read(1)[0]
            data_offset_bytes = b'\x00' + f.read(3)
            res_data_offset = struct.unpack('>I', data_offset_bytes)[0]

            # Get the data
            actual_data_pos = data_offset + res_data_offset
            f.seek(actual_data_pos)
            clut_len = struct.unpack('>I', f.read(4))[0]

            # Parse color table
            f.seek(actual_data_pos + 4)
            ct_seed = struct.unpack('>I', f.read(4))[0]
            ct_flags = struct.unpack('>H', f.read(2))[0]
            ct_size = struct.unpack('>H', f.read(2))[0] + 1

            palette = []
            for i in range(ct_size):
                value = struct.unpack('>H', f.read(2))[0]
                r = struct.unpack('>H', f.read(2))[0] >> 8  # Convert 16-bit to 8-bit
                g = struct.unpack('>H', f.read(2))[0] >> 8
                b = struct.unpack('>H', f.read(2))[0] >> 8
                palette.extend([r, g, b])

            print(f"Loaded color table with {ct_size} colors")
            return palette

    return None

def find_pict_resources(f, data_offset, map_offset):
    """Find all PICT resources"""
    f.seek(map_offset + 24)
    type_list_offset, name_list_offset = struct.unpack('>HH', f.read(4))
    num_types = struct.unpack('>H', f.read(2))[0] + 1

    type_list_pos = map_offset + type_list_offset + 2
    f.seek(type_list_pos)

    pict_resources = []

    for i in range(num_types):
        res_type = f.read(4).decode('ascii', errors='ignore')
        res_count = struct.unpack('>H', f.read(2))[0] + 1
        ref_list_offset = struct.unpack('>H', f.read(2))[0]

        if res_type == 'PICT':
            ref_list_pos = type_list_pos - 2 + ref_list_offset

            for j in range(res_count):
                ref_pos = ref_list_pos + (j * 12)
                f.seek(ref_pos)

                res_id = struct.unpack('>H', f.read(2))[0]
                name_offset = struct.unpack('>h', f.read(2))[0]
                attributes = f.read(1)[0]
                data_offset_bytes = b'\x00' + f.read(3)
                res_data_offset = struct.unpack('>I', data_offset_bytes)[0]

                # Get resource name
                res_name = ''
                if name_offset != -1:
                    name_pos = map_offset + name_list_offset + name_offset
                    f.seek(name_pos)
                    name_len = f.read(1)[0]
                    res_name = f.read(name_len).decode('ascii', errors='ignore')

                # Get data info
                actual_data_pos = data_offset + res_data_offset
                f.seek(actual_data_pos)
                pict_len = struct.unpack('>I', f.read(4))[0]

                pict_resources.append({
                    'id': res_id,
                    'name': res_name,
                    'data_pos': actual_data_pos + 4,
                    'data_len': pict_len
                })

            break

    return pict_resources

def extract_pict_to_png(f, pict_info, palette, output_path):
    """Extract a PICT resource and save as PNG"""
    f.seek(pict_info['data_pos'])

    # Read PICT header
    pict_size = struct.unpack('>H', f.read(2))[0]

    # Read frame - using LITTLE-ENDIAN for the coordinates!
    frame_bytes = f.read(8)
    top, left, bottom, right = struct.unpack('<hhhh', frame_bytes)

    width = right - left
    height = bottom - top

    print(f"\nPICT {pict_info['id']}{' (' + pict_info['name'] + ')' if pict_info['name'] else ''}:")
    print(f"  Dimensions: {width} x {height}")
    print(f"  Data length: {pict_info['data_len']} bytes")

    # For now, save basic info
    # Full PICT parsing is complex - we'll extract what we can

    # Look for PackBitsRect opcode (0x0098) or DirectBitsRect (0x009A)
    # These contain the actual pixel data

    f.seek(pict_info['data_pos'])
    pict_data = f.read(pict_info['data_len'])

    # Search for pixel data opcodes
    for i in range(len(pict_data) - 100):
        # Check for PackBitsRect with PixMap
        if i + 2 < len(pict_data):
            opcode = struct.unpack('>H', pict_data[i:i+2])[0]

            if opcode == 0x0098:  # PackBitsRect
                # Check if next bytes indicate a PixMap structure
                if i + 52 < len(pict_data):
                    row_bytes_raw = struct.unpack('>H', pict_data[i+2:i+4])[0]
                    is_pixmap = (row_bytes_raw & 0x8000) != 0
                    row_bytes = row_bytes_raw & 0x3FFF

                    if is_pixmap and row_bytes > 0 and row_bytes < 10000:
                        # This looks like a PixMap!
                        print(f"  Found PixMap at offset {i}, rowBytes={row_bytes}")

                        # Parse PixMap structure
                        pm_bounds = struct.unpack('>hhhh', pict_data[i+4:i+12])
                        pm_width = pm_bounds[3] - pm_bounds[1]
                        pm_height = pm_bounds[2] - pm_bounds[0]

                        print(f"  PixMap dimensions: {pm_width} x {pm_height}")

                        # Try to extract pixel data
                        try:
                            success = extract_packbits_image(
                                pict_data[i:],
                                pm_width,
                                pm_height,
                                row_bytes,
                                palette,
                                pict_info,
                                output_path
                            )
                            if success:
                                return True
                        except Exception as e:
                            print(f"  Error extracting: {e}")

                break

    return False

def extract_packbits_image(pict_data, width, height, row_bytes, palette, pict_info, output_path):
    """Extract PackBits compressed image data"""
    # Skip to pixel data section
    # PixMap structure is 50 bytes, then comes ColorTable, then srcRect, dstRect, mode

    # For now, let's try a simplified approach
    # We'll look for the start of PackBits data after the PixMap header

    offset = 50  # After PixMap

    # Skip color table if present (look for it)
    if offset + 8 < len(pict_data):
        # Color table starts with seed and flags
        ct_seed = struct.unpack('>I', pict_data[offset:offset+4])[0]
        ct_flags = struct.unpack('>H', pict_data[offset+4:offset+6])[0]
        ct_size = struct.unpack('>H', pict_data[offset+6:offset+8])[0] + 1

        if ct_size > 0 and ct_size <= 256:
            # Skip color table (8 bytes per entry)
            offset += 8 + (ct_size * 8)
            print(f"  Skipped color table with {ct_size} entries")

    # Skip srcRect, dstRect, mode (8 + 8 + 2 = 18 bytes)
    offset += 18

    print(f"  PackBits data starts at offset {offset}")

    # Now we should be at the PackBits data
    # Decompress using PackBits algorithm
    pixels = []

    pos = offset
    for row in range(height):
        # Each row is preceded by a byte count
        if row_bytes > 250:
            if pos + 2 > len(pict_data):
                break
            byte_count = struct.unpack('>H', pict_data[pos:pos+2])[0]
            pos += 2
        else:
            if pos + 1 > len(pict_data):
                break
            byte_count = pict_data[pos]
            pos += 1

        # Decompress this row
        row_data = []
        end_pos = pos + byte_count

        while pos < end_pos and pos < len(pict_data):
            flag = struct.unpack('b', pict_data[pos:pos+1])[0]  # signed byte
            pos += 1

            if flag >= 0:
                # Copy next flag+1 bytes literally
                count = flag + 1
                if pos + count > len(pict_data):
                    break
                row_data.extend(pict_data[pos:pos+count])
                pos += count
            elif flag != -128:
                # Repeat next byte (-flag+1) times
                count = -flag + 1
                if pos >= len(pict_data):
                    break
                byte_val = pict_data[pos]
                pos += 1
                row_data.extend([byte_val] * count)

        # Trim or pad to width
        if len(row_data) > width:
            row_data = row_data[:width]
        while len(row_data) < width:
            row_data.append(0)

        pixels.extend(row_data)

    if len(pixels) < width * height:
        print(f"  Warning: Only extracted {len(pixels)} pixels, expected {width * height}")
        # Pad with zeros
        pixels.extend([0] * (width * height - len(pixels)))

    # Create image
    img = Image.new('P', (width, height))
    if palette:
        img.putpalette(palette)
    img.putdata(pixels[:width * height])

    # Save
    name_suffix = f"_{pict_info['name']}" if pict_info['name'] else ''
    filename = f"PICT_{pict_info['id']}{name_suffix}.png"
    output_file = output_path / filename
    img.save(output_file)

    print(f"  Saved: {filename}")
    return True

def main():
    rez_file = '/home/user/atomic_ed/game/DATA/PCWATW.REZ'
    output_dir = Path('/home/user/atomic_ed/extracted_images_png')
    output_dir.mkdir(exist_ok=True)

    with open(rez_file, 'rb') as f:
        # Read header
        f.seek(0)
        data_offset, map_offset, data_length, map_length = struct.unpack('>IIII', f.read(16))

        print(f"Reading resource file: {rez_file}")
        print(f"Data offset: 0x{data_offset:x}, Map offset: 0x{map_offset:x}")
        print()

        # Load color table
        palette = read_color_table(f, data_offset, map_offset)
        if not palette:
            print("Warning: No color table found, using grayscale")
            palette = list(range(256)) * 3
        print()

        # Find all PICT resources
        pict_resources = find_pict_resources(f, data_offset, map_offset)
        print(f"Found {len(pict_resources)} PICT resources")
        print()

        # Extract specific important ones
        important_ids = [128, 130, 132, 137, 200, 201, 202, 203, 251]

        for pict in pict_resources:
            if pict['id'] in important_ids:
                try:
                    extract_pict_to_png(f, pict, palette, output_dir)
                except Exception as e:
                    print(f"Error extracting PICT {pict['id']}: {e}")
                    import traceback
                    traceback.print_exc()

if __name__ == '__main__':
    main()
