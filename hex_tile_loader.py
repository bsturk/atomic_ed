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
        """Find a specific resource in the resource fork"""
        map_data = data[map_offset:]

        # Parse type list
        type_list_offset = struct.unpack('>H', map_data[24:26])[0]
        num_types = struct.unpack('>H', map_data[type_list_offset:type_list_offset+2])[0] + 1

        # Search for resource type
        for i in range(num_types):
            type_entry_offset = type_list_offset + 2 + (i * 8)
            r_type = map_data[type_entry_offset:type_entry_offset+4]
            r_count = struct.unpack('>H', map_data[type_entry_offset+4:type_entry_offset+6])[0] + 1
            ref_list_offset = struct.unpack('>H', map_data[type_entry_offset+6:type_entry_offset+8])[0]

            if r_type == res_type.encode('ascii'):
                # Found type, search for ID
                for j in range(r_count):
                    ref_entry_offset = type_list_offset + ref_list_offset + (j * 12)
                    r_id = struct.unpack('>H', map_data[ref_entry_offset:ref_entry_offset+2])[0]

                    if r_id == res_id:
                        # Found it!
                        data_offset_in_map = struct.unpack('>I', map_data[ref_entry_offset+4:ref_entry_offset+7] + b'\x00')[0]
                        data_offset_abs = data_offset + data_offset_in_map

                        # Read resource data
                        data_length = struct.unpack('>I', data[data_offset_abs:data_offset_abs+4])[0]
                        resource_data = data[data_offset_abs+4:data_offset_abs+4+data_length]

                        return resource_data

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

    def _extract_sprite_sheet(self):
        """Extract terrain sprite sheet from PCWATW.REZ"""
        if not os.path.exists(self.rez_path):
            return None

        # Read resource fork
        data, data_offset, map_offset = self._read_resource_fork()

        # Get PICT resource #128 (terrain sprite sheet)
        pict_data = self._find_resource(data, data_offset, map_offset, 'PICT', 128)
        if not pict_data:
            return None

        # Get color palette
        palette = self._load_palette(data, data_offset, map_offset)

        # Find and decompress pixel data
        # Look for PackBits compressed data after PICT header
        search_offset = 512
        pixel_data = None

        for offset in range(search_offset, min(len(pict_data) - 1000, search_offset + 50000), 128):
            try:
                test_data = pict_data[offset:]
                decompressed = self._unpackbits(test_data[:self.SCAN_WIDTH * self.SCAN_HEIGHT * 2])

                if len(decompressed) >= self.SCAN_WIDTH * self.SCAN_HEIGHT:
                    pixel_data = decompressed[:self.SCAN_WIDTH * self.SCAN_HEIGHT]
                    break
            except:
                continue

        if not pixel_data:
            return None

        # Create image
        img = Image.new('P', (self.SCAN_WIDTH, self.SCAN_HEIGHT))
        img.putpalette(palette)
        img.putdata(pixel_data)

        return img

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

        # Need to extract from REZ
        if not os.path.exists(self.rez_path):
            return None

        # Extract sprite sheet
        self.sprite_sheet = self._extract_sprite_sheet()
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
