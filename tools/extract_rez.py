#!/usr/bin/env python3
"""
Mac Resource Fork Parser for PCWATW.REZ
Extracts and analyzes resources from Apple HFS/HFS+ resource fork files
"""

import struct
import os
from pathlib import Path
from collections import defaultdict
from PIL import Image
import io

class MacResourceFork:
    def __init__(self, filepath):
        self.filepath = filepath
        self.resources = defaultdict(list)

    def read_header(self, data):
        """Read the resource fork header"""
        # Resource fork header format:
        # Offset 0: Data offset (4 bytes)
        # Offset 4: Map offset (4 bytes)
        # Offset 8: Data length (4 bytes)
        # Offset 12: Map length (4 bytes)
        data_offset, map_offset, data_length, map_length = struct.unpack('>IIII', data[:16])

        print(f"Resource Fork Header:")
        print(f"  Data offset: 0x{data_offset:x}")
        print(f"  Map offset: 0x{map_offset:x}")
        print(f"  Data length: 0x{data_length:x} ({data_length} bytes)")
        print(f"  Map length: 0x{map_length:x} ({map_length} bytes)")
        print()

        return {
            'data_offset': data_offset,
            'map_offset': map_offset,
            'data_length': data_length,
            'map_length': map_length
        }

    def read_resource_map(self, data, map_offset):
        """Read the resource map section"""
        # Resource map format:
        # Offset 0: Copy of header data/map offsets (16 bytes)
        # Offset 16: Next resource map handle (4 bytes)
        # Offset 20: File reference number (2 bytes)
        # Offset 22: Resource fork attributes (2 bytes)
        # Offset 24: Type list offset (2 bytes)
        # Offset 26: Name list offset (2 bytes)
        # Offset 28: Resource type count - 1 (2 bytes)

        map_pos = map_offset + 24  # Skip to type list offset
        type_list_offset, name_list_offset = struct.unpack('>HH', data[map_pos:map_pos+4])
        num_types = struct.unpack('>H', data[map_pos+4:map_pos+6])[0] + 1  # Count is -1

        print(f"Resource Map:")
        print(f"  Type list offset: 0x{type_list_offset:x}")
        print(f"  Name list offset: 0x{name_list_offset:x}")
        print(f"  Number of resource types: {num_types}")
        print()

        # Type list starts at map_offset + type_list_offset + 2
        type_list_pos = map_offset + type_list_offset + 2

        return {
            'type_list_offset': type_list_offset,
            'name_list_offset': name_list_offset,
            'num_types': num_types,
            'type_list_pos': type_list_pos
        }

    def read_resource_types(self, data, map_info, header_info):
        """Read all resource types and their resources"""
        resources = []

        pos = map_info['type_list_pos']

        for i in range(map_info['num_types']):
            # Each type entry is 8 bytes:
            # Type (4 bytes) - FourCC
            # Resource count - 1 (2 bytes)
            # Reference list offset (2 bytes)

            if pos + 8 > len(data):
                break

            res_type = data[pos:pos+4].decode('ascii', errors='ignore')
            res_count = struct.unpack('>H', data[pos+4:pos+6])[0] + 1
            ref_list_offset = struct.unpack('>H', data[pos+6:pos+8])[0]

            print(f"Resource Type: '{res_type}' ({res_count} resources)")

            # Reference list is relative to the type list
            ref_list_pos = map_info['type_list_pos'] - 2 + ref_list_offset

            for j in range(res_count):
                # Each reference entry is 12 bytes:
                # ID (2 bytes)
                # Name offset (2 bytes) - relative to name list
                # Attributes (1 byte)
                # Resource data offset (3 bytes) - in data section
                # Reserved handle (4 bytes)

                ref_pos = ref_list_pos + (j * 12)
                if ref_pos + 12 > len(data):
                    break

                res_id = struct.unpack('>H', data[ref_pos:ref_pos+2])[0]
                name_offset = struct.unpack('>h', data[ref_pos+2:ref_pos+4])[0]
                attributes = data[ref_pos+4]

                # Data offset is stored as 3 bytes (24-bit integer)
                data_offset_bytes = b'\x00' + data[ref_pos+5:ref_pos+8]
                data_offset = struct.unpack('>I', data_offset_bytes)[0]

                # Get resource name if present
                res_name = ''
                if name_offset != -1:
                    name_pos = header_info['map_offset'] + map_info['name_list_offset'] + name_offset
                    if name_pos < len(data):
                        name_len = data[name_pos]
                        if name_pos + 1 + name_len <= len(data):
                            res_name = data[name_pos+1:name_pos+1+name_len].decode('ascii', errors='ignore')

                # Get actual resource data
                actual_data_pos = header_info['data_offset'] + data_offset
                if actual_data_pos + 4 <= len(data):
                    res_data_len = struct.unpack('>I', data[actual_data_pos:actual_data_pos+4])[0]
                    res_data_start = actual_data_pos + 4
                    res_data_end = res_data_start + res_data_len

                    if res_data_end <= len(data):
                        res_data = data[res_data_start:res_data_end]

                        resources.append({
                            'type': res_type,
                            'id': res_id,
                            'name': res_name,
                            'attributes': attributes,
                            'data_offset': data_offset,
                            'data_length': res_data_len,
                            'data': res_data
                        })

                        print(f"  ID: {res_id:5d}, Size: {res_data_len:8d} bytes, Name: {res_name if res_name else '(unnamed)'}")

            print()
            pos += 8

        return resources

    def parse(self):
        """Parse the entire resource fork"""
        with open(self.filepath, 'rb') as f:
            data = f.read()

        print(f"Parsing: {self.filepath}")
        print(f"File size: {len(data)} bytes")
        print("=" * 80)
        print()

        header_info = self.read_header(data)
        map_info = self.read_resource_map(data, header_info['map_offset'])
        resources = self.read_resource_types(data, map_info, header_info)

        # Organize by type
        for res in resources:
            self.resources[res['type']].append(res)

        return resources

    def extract_images(self, output_dir='extracted_images'):
        """Extract image resources to files"""
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)

        extracted_count = 0

        # Try to extract PICT resources
        if 'PICT' in self.resources:
            print(f"\nExtracting PICT resources...")
            for res in self.resources['PICT']:
                try:
                    self._extract_pict(res, output_path)
                    extracted_count += 1
                except Exception as e:
                    print(f"  Error extracting PICT {res['id']}: {e}")

        # Try to extract cicn (color icon) resources
        if 'cicn' in self.resources:
            print(f"\nExtracting cicn (color icon) resources...")
            for res in self.resources['cicn']:
                try:
                    self._extract_cicn(res, output_path)
                    extracted_count += 1
                except Exception as e:
                    print(f"  Error extracting cicn {res['id']}: {e}")

        # Try to extract ppat (pixel pattern) resources
        if 'ppat' in self.resources:
            print(f"\nExtracting ppat (pixel pattern) resources...")
            for res in self.resources['ppat']:
                try:
                    self._extract_ppat(res, output_path)
                    extracted_count += 1
                except Exception as e:
                    print(f"  Error extracting ppat {res['id']}: {e}")

        # Try to extract PAT resources
        if 'PAT ' in self.resources:
            print(f"\nExtracting PAT resources...")
            for res in self.resources['PAT ']:
                try:
                    self._extract_pat(res, output_path)
                    extracted_count += 1
                except Exception as e:
                    print(f"  Error extracting PAT {res['id']}: {e}")

        # Try generic bitmap extraction for unknown types
        for res_type in self.resources:
            if res_type not in ['PICT', 'cicn', 'ppat', 'PAT ']:
                print(f"\nAttempting to extract {res_type} resources as raw data...")
                for res in self.resources[res_type]:
                    try:
                        # Save raw data
                        filename = f"{res_type}_{res['id']}.bin"
                        output_file = output_path / filename
                        with open(output_file, 'wb') as f:
                            f.write(res['data'])
                        print(f"  Saved raw data: {filename}")
                    except Exception as e:
                        print(f"  Error saving {res_type} {res['id']}: {e}")

        print(f"\nTotal images extracted: {extracted_count}")
        print(f"Output directory: {output_path.absolute()}")

    def _extract_pict(self, res, output_path):
        """Extract PICT resource"""
        # PICT format is complex - attempt basic extraction
        name_suffix = f"_{res['name']}" if res['name'] else ''
        filename = f"PICT_{res['id']}{name_suffix}.pict"
        output_file = output_path / filename

        # Save raw PICT data (may need external tools to convert)
        with open(output_file, 'wb') as f:
            # PICT files typically have a 512-byte header
            f.write(b'\x00' * 512)
            f.write(res['data'])

        print(f"  Saved PICT: {filename} ({res['data_length']} bytes)")

    def _extract_cicn(self, res, output_path):
        """Extract cicn (color icon) resource"""
        data = res['data']

        # cicn format:
        # PixMap structure followed by mask, bitmap, and color data
        # This is a simplified extraction

        if len(data) < 50:
            return

        try:
            # Try to parse basic structure
            # PixMap starts with bounds rectangle
            top, left, bottom, right = struct.unpack('>HHHH', data[14:22])
            width = right - left
            height = bottom - top

            name_suffix = f"_{res['name']}" if res['name'] else ''
            filename = f"cicn_{res['id']}{name_suffix}.bin"
            output_file = output_path / filename

            with open(output_file, 'wb') as f:
                f.write(res['data'])

            print(f"  Saved cicn: {filename} ({width}x{height}, {res['data_length']} bytes)")
        except:
            filename = f"cicn_{res['id']}.bin"
            output_file = output_path / filename
            with open(output_file, 'wb') as f:
                f.write(res['data'])
            print(f"  Saved cicn: {filename} ({res['data_length']} bytes)")

    def _extract_ppat(self, res, output_path):
        """Extract ppat (pixel pattern) resource"""
        # ppat is typically a small pattern (8x8 or similar)
        name_suffix = f"_{res['name']}" if res['name'] else ''
        filename = f"ppat_{res['id']}{name_suffix}.bin"
        output_file = output_path / filename

        with open(output_file, 'wb') as f:
            f.write(res['data'])

        print(f"  Saved ppat: {filename} ({res['data_length']} bytes)")

    def _extract_pat(self, res, output_path):
        """Extract PAT (pattern) resource"""
        # PAT is 8x8 monochrome pattern (8 bytes)
        if len(res['data']) == 8:
            try:
                # Create an 8x8 monochrome image
                img = Image.new('1', (8, 8))
                pixels = []

                for byte in res['data']:
                    for bit in range(8):
                        pixels.append((byte >> (7 - bit)) & 1)

                img.putdata(pixels)

                # Scale up for visibility
                img = img.resize((64, 64), Image.NEAREST)

                name_suffix = f"_{res['name']}" if res['name'] else ''
                filename = f"PAT_{res['id']}{name_suffix}.png"
                output_file = output_path / filename
                img.save(output_file)

                print(f"  Saved PAT: {filename} (8x8 pattern)")
            except Exception as e:
                print(f"  Error creating PAT image: {e}")
        else:
            # Save as binary if not standard size
            filename = f"PAT_{res['id']}.bin"
            output_file = output_path / filename
            with open(output_file, 'wb') as f:
                f.write(res['data'])
            print(f"  Saved PAT: {filename} ({res['data_length']} bytes)")

    def analyze_resources(self):
        """Analyze and summarize resources"""
        print("\n" + "=" * 80)
        print("RESOURCE SUMMARY")
        print("=" * 80)
        print()

        total_resources = sum(len(resources) for resources in self.resources.values())
        print(f"Total resources: {total_resources}")
        print(f"Resource types found: {len(self.resources)}")
        print()

        for res_type in sorted(self.resources.keys()):
            count = len(self.resources[res_type])
            total_size = sum(r['data_length'] for r in self.resources[res_type])
            avg_size = total_size / count if count > 0 else 0

            print(f"{res_type:8s}: {count:4d} resources, "
                  f"total size: {total_size:10d} bytes, "
                  f"avg size: {avg_size:8.1f} bytes")

            # Show some details for image-like resources
            if res_type in ['PICT', 'cicn', 'ppat', 'PAT ']:
                for res in self.resources[res_type][:5]:  # Show first 5
                    name_str = f" '{res['name']}'" if res['name'] else ''
                    print(f"    ID {res['id']:5d}{name_str}: {res['data_length']} bytes")
                if count > 5:
                    print(f"    ... and {count - 5} more")

def main():
    rez_file = '/home/user/atomic_ed/game/DATA/PCWATW.REZ'

    if not os.path.exists(rez_file):
        print(f"Error: File not found: {rez_file}")
        return

    # Parse the resource fork
    parser = MacResourceFork(rez_file)
    resources = parser.parse()

    # Analyze resources
    parser.analyze_resources()

    # Extract images
    print("\n" + "=" * 80)
    print("EXTRACTING IMAGES")
    print("=" * 80)
    parser.extract_images()

if __name__ == '__main__':
    main()
