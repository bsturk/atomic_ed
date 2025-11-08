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
        Parse PICT v2 format using ultra-simple brute-force approach.

        Reads header for dimensions, decompresses entire file, rearranges to 448-wide.
        Returns PIL.Image or None if parsing fails.
        """
        # Read PICT header frame (little-endian like extract_pict_images.py)
        if len(pict_data) < 10:
            return None

        pict_size = struct.unpack('>H', pict_data[0:2])[0]
        frame_bytes = pict_data[2:10]
        top, left, bottom, right = struct.unpack('<hhhh', frame_bytes)

        original_width = right - left
        original_height = bottom - top

        # Decompress entire PICT data using PackBits from various starting offsets
        # (brute-force approach - try different offsets until we get ~255K pixels)
        target_pixels = self.SCAN_WIDTH * self.SCAN_HEIGHT  # 448 × 570 = 255,360

        for start_offset in [0, 10, 100, 500, 1000, 5000, 10000]:
            decompressed = []
            i = start_offset

            while i < len(pict_data) and len(decompressed) < target_pixels + 10000:
                if i >= len(pict_data):
                    break

                try:
                    flag = struct.unpack('b', bytes([pict_data[i]]))[0]
                    i += 1

                    if flag >= 0:
                        count = flag + 1
                        if i + count > len(pict_data):
                            break
                        decompressed.extend(pict_data[i:i+count])
                        i += count
                    elif flag != -128:
                        count = -flag + 1
                        if i >= len(pict_data):
                            break
                        decompressed.extend([pict_data[i]] * count)
                        i += 1
                except:
                    break

            # Check if we got reasonable amount of data
            if 250000 < len(decompressed) < 260000:
                # Try rearranging to 448-wide
                pixels = decompressed[:target_pixels]

                img = Image.new('P', (self.SCAN_WIDTH, self.SCAN_HEIGHT))
                img.putpalette(palette)
                img.putdata(pixels)

                # Verify it has reasonable color diversity (not all black)
                unique_colors = len(set(pixels[:10000]))  # Sample first 10K pixels
                if unique_colors > 20:
                    return img

        return None

    def _get_sprite_sheet(self):
        """
        Get the terrain sprite sheet image by extracting from PCWATW.REZ.

        Primary method: Use PICT_128.png (extracted from REZ) and rearrange to 448-wide.
        This is the proven working method that created scan_width_448.png.
        """
        # Primary path: PICT_128.png (already extracted from REZ) rearranged to 448-wide
        pict_128_path = 'extracted_images/PICT_128.png'
        if os.path.exists(pict_128_path):
            try:
                # This PNG was extracted from PICT resource #128 in PCWATW.REZ
                source_img = Image.open(pict_128_path)
                palette = source_img.getpalette()
                pixels = list(source_img.getdata())

                # Rearrange pixels to 448-wide (the key insight!)
                # The pixel data is correct, just arranged as 444-wide originally
                target_width = self.SCAN_WIDTH  # 448
                target_height = len(pixels) // target_width

                rearranged = Image.new('P', (target_width, target_height))
                rearranged.putpalette(palette)
                rearranged.putdata(pixels[:target_width * target_height])

                if rearranged.size == (self.SCAN_WIDTH, self.SCAN_HEIGHT):
                    return rearranged
            except Exception as e:
                print(f"Error rearranging PICT_128.png: {e}")

        # Direct scan_width_448.png if rearrangement fails
        scan_448_path = 'extracted_images/scan_width_448.png'
        if os.path.exists(scan_448_path):
            try:
                img = Image.open(scan_448_path)
                if img.size == (self.SCAN_WIDTH, self.SCAN_HEIGHT):
                    return img
            except:
                pass

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

    def _load_preextracted_tile(self, terrain_id):
        """
        Load a pre-extracted tile from the correct_hex_tiles directory.

        These tiles were extracted using the verified correct method and should
        be used as the primary source before attempting sprite sheet extraction.
        """
        row, col = self.TERRAIN_MAPPING.get(terrain_id, (0, 0))
        preextracted_file = Path('extracted_images/correct_hex_tiles') / f"hex_tile_r{row:02d}_c{col:02d}.png"

        if preextracted_file.exists():
            try:
                img = Image.open(preextracted_file)
                # Pre-extracted tiles may be in palette mode (P), convert to RGBA
                # but preserve the palette information properly
                if img.mode == 'P':
                    # Convert palette image to RGBA while preserving colors
                    return img.convert('RGBA')
                elif img.mode == 'RGBA':
                    return img
                else:
                    return img.convert('RGBA')
            except Exception as e:
                print(f"Error loading pre-extracted tile for terrain {terrain_id}: {e}")
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

        Priority order:
        1. Pre-extracted tiles from correct_hex_tiles/ (verified working)
        2. Cached tiles from .hex_tile_cache/
        3. Extract from sprite sheet (fallback)

        Returns dict mapping terrain_id -> PIL.Image, or None if extraction fails.
        """
        self.tiles = {}

        # First, try to load all tiles from pre-extracted directory (highest priority)
        all_preextracted = True
        for terrain_id in self.TERRAIN_MAPPING.keys():
            tile = self._load_preextracted_tile(terrain_id)
            if tile:
                self.tiles[terrain_id] = tile
            else:
                all_preextracted = False
                break

        if all_preextracted and self.tiles:
            print(f"✓ Loaded {len(self.tiles)} hex tiles from pre-extracted directory")
            return self.tiles

        # Second priority: try to load from cache
        self.tiles = {}
        all_cached = True
        for terrain_id in self.TERRAIN_MAPPING.keys():
            tile = self._load_cached_tile(terrain_id)
            if tile:
                self.tiles[terrain_id] = tile
            else:
                all_cached = False
                break

        if all_cached and self.tiles:
            print(f"✓ Loaded {len(self.tiles)} hex tiles from cache")
            return self.tiles

        # Last resort: load sprite sheet and extract tiles
        print("Loading hex tiles from sprite sheet...")
        self.sprite_sheet = self._get_sprite_sheet()
        if self.sprite_sheet is None:
            print("✗ Failed to load sprite sheet")
            return None

        # Extract individual tiles
        self.tiles = {}
        for terrain_id, (row, col) in self.TERRAIN_MAPPING.items():
            tile = self._extract_tile_from_sheet(row, col)
            if tile:
                self.tiles[terrain_id] = tile
                self._save_tile_to_cache(terrain_id, tile)

        if self.tiles:
            print(f"✓ Extracted {len(self.tiles)} hex tiles from sprite sheet")

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
