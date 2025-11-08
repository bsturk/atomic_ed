"""
Hex Tile Loader - Automatic extraction and loading of terrain hex tiles

This module automatically extracts hex tiles from PCWATW.REZ if needed,
or loads them from cache if already extracted.

Usage in scenario editor:
    from hex_tile_loader import load_hex_tiles

    hex_tiles = load_hex_tiles()  # Returns dict of terrain_id -> PIL.Image
    if hex_tiles:
        # Use the tiles
        pass
"""

import struct
import os
from pathlib import Path
from PIL import Image


class HexTileLoader:
    """Automatic hex tile extraction and loading from game assets"""

    # Tile configuration
    HEX_WIDTH = 34
    HEX_HEIGHT = 38
    SCAN_WIDTH = 448
    SCAN_HEIGHT = 570
    VARIANTS_PER_ROW = 13
    NUM_TERRAIN_ROWS = 14

    # Terrain type to sprite sheet row/column mapping
    TERRAIN_MAPPING = {
        0: (0, 0),   # Grass/Field
        1: (5, 0),   # Water/Ocean
        2: (6, 0),   # Beach/Sand
        3: (2, 0),   # Forest
        4: (4, 0),   # Town
        5: (8, 0),   # Road
        6: (3, 0),   # River
        7: (9, 0),   # Mountains
        8: (7, 0),   # Swamp
        9: (8, 5),   # Bridge
        10: (10, 0), # Fortification
        11: (11, 0), # Bocage
        12: (9, 5),  # Cliff
        13: (10, 5), # Village
        14: (12, 0), # Farm
        15: (3, 5),  # Canal
        16: (1, 0),  # Unknown
    }

    def __init__(self, rez_path='game/DATA/PCWATW.REZ', cache_dir='.hex_tile_cache'):
        """
        Initialize the loader.

        Args:
            rez_path: Path to PCWATW.REZ resource file
            cache_dir: Directory to cache extracted tiles
        """
        self.rez_path = rez_path
        self.cache_dir = cache_dir
        self.sprite_sheet = None
        self.tiles = {}

    def _read_resource_fork(self):
        """Read Mac resource fork structure"""
        with open(self.rez_path, 'rb') as f:
            data = f.read()

        # Parse header
        data_offset = struct.unpack('>I', data[0:4])[0]
        map_offset = struct.unpack('>I', data[4:8])[0]

        return data, data_offset, map_offset

    def _find_resource(self, data, data_offset, map_offset, res_type, res_id):
        """Find a specific resource in the resource fork (following extract_rez.py proven method)"""
        # Parse resource map (same as extract_rez.py)
        map_pos = map_offset + 24
        type_list_offset = struct.unpack('>H', data[map_pos:map_pos+2])[0]
        name_list_offset = struct.unpack('>H', data[map_pos+2:map_pos+4])[0]
        num_types = struct.unpack('>H', data[map_pos+4:map_pos+6])[0] + 1

        # Type list starts at map_offset + type_list_offset + 2
        type_list_pos = map_offset + type_list_offset + 2

        # Search for resource type
        pos = type_list_pos
        for i in range(num_types):
            if pos + 8 > len(data):
                break

            r_type = data[pos:pos+4]
            r_count = struct.unpack('>H', data[pos+4:pos+6])[0] + 1
            ref_list_offset = struct.unpack('>H', data[pos+6:pos+8])[0]

            if r_type == res_type.encode('ascii'):
                # Found type, search for ID
                ref_list_pos = type_list_pos - 2 + ref_list_offset

                for j in range(r_count):
                    ref_pos = ref_list_pos + (j * 12)
                    if ref_pos + 12 > len(data):
                        break

                    r_id = struct.unpack('>H', data[ref_pos:ref_pos+2])[0]

                    if r_id == res_id:
                        # Found it!
                        # Data offset is stored as 3 bytes (24-bit integer)
                        data_offset_bytes = b'\x00' + data[ref_pos+5:ref_pos+8]
                        data_offset_in_map = struct.unpack('>I', data_offset_bytes)[0]

                        # Get actual resource data
                        actual_data_pos = data_offset + data_offset_in_map
                        res_data_len = struct.unpack('>I', data[actual_data_pos:actual_data_pos+4])[0]
                        resource_data = data[actual_data_pos+4:actual_data_pos+4+res_data_len]

                        return resource_data

                break  # Found type but not ID

            pos += 8

        return None

    def _unpackbits(self, data):
        """Decompress PackBits RLE data"""
        output = bytearray()
        i = 0

        while i < len(data):
            n = struct.unpack('b', bytes([data[i]]))[0]
            i += 1

            if n >= 0:
                count = n + 1
                output.extend(data[i:i+count])
                i += count
            elif n != -128:
                count = -n + 1
                if i < len(data):
                    output.extend([data[i]] * count)
                    i += 1

        return bytes(output)

    def _load_palette(self, data, data_offset, map_offset):
        """Load color palette from clut resource #8"""
        clut_data = self._find_resource(data, data_offset, map_offset, 'clut', 8)

        if clut_data and len(clut_data) >= 8:
            num_colors = struct.unpack('>H', clut_data[6:8])[0] + 1
            palette = []
            offset = 8

            for i in range(min(num_colors, 256)):
                if offset + 8 <= len(clut_data):
                    # Each entry: index (2), R (2), G (2), B (2)
                    r = struct.unpack('>H', clut_data[offset+2:offset+4])[0] >> 8
                    g = struct.unpack('>H', clut_data[offset+4:offset+6])[0] >> 8
                    b = struct.unpack('>H', clut_data[offset+6:offset+8])[0] >> 8
                    palette.extend([r, g, b])
                    offset += 8

            return palette

        # Fallback grayscale palette
        return [i for v in range(256) for i in (v, v, v)]

    def _extract_pict_from_rez(self):
        """
        Extract PICT resource #128 directly from PCWATW.REZ.

        Returns PIL.Image with the terrain sprite sheet, or None if extraction fails.
        """
        if not os.path.exists(self.rez_path):
            return None

        try:
            # Read resource fork
            data, data_offset, map_offset = self._read_resource_fork()

            # Load palette from clut resource #8
            palette = self._load_palette(data, data_offset, map_offset)

            # Find PICT resource #128
            pict_data = self._find_resource(data, data_offset, map_offset, 'PICT', 128)
            if not pict_data:
                return None

            # Parse PICT and extract pixel data
            img = self._parse_pict_v2(pict_data, palette)

            return img

        except Exception as e:
            print(f"Error extracting PICT from REZ: {e}")
            return None

    def _parse_pict_v2(self, pict_data, palette):
        """
        Parse PICT v2 format and extract the sprite sheet image.

        Returns PIL.Image or None if parsing fails.
        """
        # PICT data starts after the 512-byte header added during extraction
        # But _find_resource returns raw data without header, so start at beginning
        offset = 0

        # Skip PICT header (2 bytes size + 8 bytes frame)
        offset += 10

        # Search for PackBitsRect opcode (0x0098) with PixMap
        found_pixmap = False
        max_search = min(10000, len(pict_data) - 100)

        while offset < max_search:
            if offset + 2 > len(pict_data):
                break

            opcode = struct.unpack('>H', pict_data[offset:offset+2])[0]

            if opcode == 0x0098:  # PackBitsRect
                # Check if next structure is PixMap (rowBytes high bit set)
                if offset + 4 <= len(pict_data):
                    row_bytes_raw = struct.unpack('>H', pict_data[offset+2:offset+4])[0]
                    is_pixmap = (row_bytes_raw & 0x8000) != 0

                    if is_pixmap:
                        found_pixmap = True
                        offset += 2  # Skip opcode
                        break

            offset += 1

        if not found_pixmap:
            return None

        # Parse PixMap structure
        row_bytes_raw = struct.unpack('>H', pict_data[offset:offset+2])[0]
        row_bytes = row_bytes_raw & 0x3FFF
        offset += 2

        # Read bounds rectangle
        bounds_data = pict_data[offset:offset+8]
        top = struct.unpack('>H', bounds_data[0:2])[0]
        left = struct.unpack('>H', bounds_data[2:4])[0]

        # CRITICAL: Use little-endian for bottom/right to get correct dimensions
        # This is what produces the correct 448×570 size
        bottom = struct.unpack('<H', bounds_data[4:6])[0]
        right = struct.unpack('<H', bounds_data[6:8])[0]
        offset += 8

        width = right - left
        height = bottom - top

        # Skip PixMap fields: version, packType, packSize, hRes, vRes, pixelType,
        # pixelSize, cmpCount, cmpSize, planeBytes, pmTable, pmReserved
        # Total: 2+2+4+4+4+2+2+2+2+4+4+4 = 38 bytes
        offset += 38

        # Skip srcRect (8), dstRect (8), mode (2) = 18 bytes
        offset += 18

        # Now extract packed scanlines
        pixel_rows = []

        for row_num in range(height):
            # Read packed size for this row
            if row_bytes < 8:
                packed_size = pict_data[offset]
                offset += 1
            elif row_bytes > 250:
                packed_size = struct.unpack('>H', pict_data[offset:offset+2])[0]
                offset += 2
            else:
                packed_size = pict_data[offset]
                offset += 1

            # Read and decompress packed data
            packed_row = pict_data[offset:offset+packed_size]
            offset += packed_size

            unpacked = self._unpackbits(packed_row)
            pixel_rows.append(unpacked[:width])

        # Combine all rows
        all_pixels = b''.join(pixel_rows)

        # Ensure we have the right amount of data
        expected_size = width * height
        if len(all_pixels) < expected_size:
            all_pixels += b'\x00' * (expected_size - len(all_pixels))
        elif len(all_pixels) > expected_size:
            all_pixels = all_pixels[:expected_size]

        # Create PIL image
        img = Image.new('P', (width, height))
        img.putpalette(palette)
        img.putdata(list(all_pixels))

        return img

    def _get_sprite_sheet(self):
        """
        Get the terrain sprite sheet image.

        Extracts directly from PCWATW.REZ, producing the equivalent of scan_width_448.png.
        Falls back to pre-extracted files if REZ extraction fails.
        """
        # Try to extract from REZ first
        img = self._extract_pict_from_rez()
        if img and img.size == (self.SCAN_WIDTH, self.SCAN_HEIGHT):
            return img

        # Fall back to pre-extracted files if needed
        known_good_paths = [
            'extracted_images/scan_width_448.png',
            'extracted_images/PICT_128.png',
        ]

        for path in known_good_paths:
            if os.path.exists(path):
                try:
                    img = Image.open(path)
                    # Verify it's the right size
                    if img.size == (self.SCAN_WIDTH, self.SCAN_HEIGHT):
                        return img
                except:
                    continue

        return None

    def _extract_tile_from_sheet(self, row, col):
        """Extract a single hex tile from the sprite sheet"""
        if self.sprite_sheet is None:
            return None

        # Calculate position with offset to skip wraparound artifact
        x = col * self.HEX_WIDTH + 2
        y = row * self.HEX_HEIGHT

        # Extract and convert to RGBA
        tile = self.sprite_sheet.crop((x, y, x + self.HEX_WIDTH, y + self.HEX_HEIGHT))
        return tile.convert('RGBA')

    def _load_cached_tile(self, terrain_id):
        """Load a cached tile if it exists"""
        row, col = self.TERRAIN_MAPPING.get(terrain_id, (0, 0))
        cache_file = Path(self.cache_dir) / f"hex_tile_r{row:02d}_c{col:02d}.png"

        if cache_file.exists():
            try:
                return Image.open(cache_file).convert('RGBA')
            except:
                return None

        return None

    def _save_tile_to_cache(self, terrain_id, tile):
        """Save a tile to the cache"""
        row, col = self.TERRAIN_MAPPING.get(terrain_id, (0, 0))
        cache_dir = Path(self.cache_dir)
        cache_dir.mkdir(exist_ok=True)

        cache_file = cache_dir / f"hex_tile_r{row:02d}_c{col:02d}.png"
        tile.save(cache_file)

    def load_tiles(self):
        """
        Load all terrain hex tiles.

        Returns dict mapping terrain_id -> PIL.Image, or None if extraction fails.
        """
        # Try to load from cache first
        all_cached = True
        for terrain_id in self.TERRAIN_MAPPING.keys():
            tile = self._load_cached_tile(terrain_id)
            if tile:
                self.tiles[terrain_id] = tile
            else:
                all_cached = False
                break

        if all_cached and self.tiles:
            return self.tiles

        # Need to load sprite sheet and extract tiles
        self.sprite_sheet = self._get_sprite_sheet()
        if self.sprite_sheet is None:
            return None

        # Extract individual tiles
        self.tiles = {}
        for terrain_id, (row, col) in self.TERRAIN_MAPPING.items():
            tile = self._extract_tile_from_sheet(row, col)
            if tile:
                self.tiles[terrain_id] = tile
                self._save_tile_to_cache(terrain_id, tile)

        return self.tiles if self.tiles else None


def load_hex_tiles(rez_path='game/DATA/PCWATW.REZ', cache_dir='.hex_tile_cache'):
    """
    Convenience function to load hex tiles.

    Automatically extracts from REZ if needed, or loads from cache.

    Args:
        rez_path: Path to PCWATW.REZ resource file
        cache_dir: Directory to cache extracted tiles

    Returns:
        dict mapping terrain_id (0-16) -> PIL.Image, or None on failure
    """
    loader = HexTileLoader(rez_path, cache_dir)
    return loader.load_tiles()


if __name__ == '__main__':
    # Test the loader
    print("Testing hex tile loader...")
    tiles = load_hex_tiles()

    if tiles:
        print(f"✓ Successfully loaded {len(tiles)} terrain tiles")
        for terrain_id in sorted(tiles.keys()):
            img = tiles[terrain_id]
            print(f"  Terrain {terrain_id:2d}: {img.size[0]}×{img.size[1]} {img.mode}")
    else:
        print("✗ Failed to load tiles")
