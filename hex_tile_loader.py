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

    # Tile configuration - CRITICAL VALUES determined by sprite sheet analysis
    HEX_WIDTH = 32        # Actual hex content width (NOT 34!)
    HEX_HEIGHT = 36       # Actual hex content height (NOT 38!)
    HEX_SPACING = 34      # Distance between hex centers (column spacing)
    HEX_OFFSET_X = 12     # Where first hex content starts in sprite sheet
    HEX_ROW_SPACING = 38  # Distance between row centers (row spacing)
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

    def __init__(self):
        """
        Initialize the hex tile loader.

        All tiles are extracted in memory from the sprite sheet at runtime.
        No caching, no pre-extracted files.
        """
        self.sprite_sheet = None
        self.tiles = {}

    def _get_sprite_sheet(self):
        """
        Load the terrain sprite sheet from disk.

        The sprite sheet must exist at extracted_images/scan_width_448.png
        Raises RuntimeError if sprite sheet cannot be loaded.
        """
        scan_448_path = 'extracted_images/scan_width_448.png'

        if not os.path.exists(scan_448_path):
            raise RuntimeError(
                f"CRITICAL: Hex tile sprite sheet not found at {scan_448_path}\n"
                f"The terrain hex tile sprite sheet is required for the editor to function.\n"
                f"Please ensure the file exists before running the editor."
            )

        try:
            img = Image.open(scan_448_path)
            if img.size != (self.SCAN_WIDTH, self.SCAN_HEIGHT):
                raise RuntimeError(
                    f"CRITICAL: Sprite sheet has incorrect dimensions {img.size}\n"
                    f"Expected {self.SCAN_WIDTH}x{self.SCAN_HEIGHT}"
                )
            return img
        except Exception as e:
            raise RuntimeError(f"CRITICAL: Failed to load sprite sheet: {e}")

    def _extract_tile_from_sheet(self, row, col):
        """
        Extract a single hex tile from the sprite sheet in memory.

        Handles transparency: makes white background (palette index 0) transparent.
        Returns RGBA image with proper colors and transparent background.
        """
        if self.sprite_sheet is None:
            raise RuntimeError("Sprite sheet not loaded")

        # Calculate position using correct spacing and offset
        # Analysis showed: hexes are spaced 34 pixels apart horizontally (center-to-center)
        # but actual hex content is only 32 pixels wide, starting at x=12
        # Vertically: rows are spaced 38 pixels apart, but content is only 36 pixels tall
        x = col * self.HEX_SPACING + self.HEX_OFFSET_X
        y = row * self.HEX_ROW_SPACING

        # Extract tile from sprite sheet
        tile = self.sprite_sheet.crop((x, y, x + self.HEX_WIDTH, y + self.HEX_HEIGHT))

        # Handle transparency if source is palette mode
        if self.sprite_sheet.mode == 'P':
            # Get the original palette data before conversion
            original_pixels = list(tile.getdata())

            # Convert to RGBA (preserves palette colors)
            tile_rgba = tile.convert('RGBA')
            rgba_pixels = list(tile_rgba.getdata())

            # Make white background (palette index 0) transparent
            new_pixels = []
            for i, palette_idx in enumerate(original_pixels):
                r, g, b, a = rgba_pixels[i]
                if palette_idx == 0:  # White background in original palette
                    new_pixels.append((r, g, b, 0))  # Make transparent
                else:
                    new_pixels.append((r, g, b, 255))  # Keep opaque

            tile_rgba.putdata(new_pixels)
            return tile_rgba
        else:
            # Non-palette image, just convert to RGBA
            return tile.convert('RGBA')


    def load_tiles(self):
        """
        Load all terrain hex tiles by extracting from sprite sheet IN MEMORY.

        No pre-extracted tiles, no caching to disk. Everything happens in memory.
        Raises RuntimeError if sprite sheet cannot be loaded or tiles cannot be extracted.

        Returns dict mapping terrain_id -> PIL.Image (RGBA with transparency)
        """
        # Load sprite sheet (will raise RuntimeError if not available)
        self.sprite_sheet = self._get_sprite_sheet()

        # Extract all terrain tiles in memory
        self.tiles = {}
        for terrain_id, (row, col) in self.TERRAIN_MAPPING.items():
            tile = self._extract_tile_from_sheet(row, col)
            if tile is None:
                raise RuntimeError(
                    f"CRITICAL: Failed to extract terrain tile {terrain_id} "
                    f"from position row={row}, col={col}"
                )
            self.tiles[terrain_id] = tile

        if len(self.tiles) != len(self.TERRAIN_MAPPING):
            raise RuntimeError(
                f"CRITICAL: Expected {len(self.TERRAIN_MAPPING)} terrain tiles, "
                f"but only extracted {len(self.tiles)}"
            )

        return self.tiles

    def get_tile_with_variant(self, terrain_id, variant):
        """
        Get a specific terrain tile with specific variant column.

        Args:
            terrain_id: Terrain type (0-16)
            variant: Variant column (0-12)

        Returns:
            PIL.Image (RGBA) of the specific hex tile variant

        Raises:
            RuntimeError if sprite sheet not loaded or invalid parameters
        """
        if self.sprite_sheet is None:
            self.sprite_sheet = self._get_sprite_sheet()

        # Get base row from terrain mapping (use default column 0)
        if terrain_id not in self.TERRAIN_MAPPING:
            raise RuntimeError(f"Invalid terrain_id: {terrain_id}")

        row, _ = self.TERRAIN_MAPPING[terrain_id]

        # Validate variant range (0-12 for 13 columns)
        if variant < 0 or variant >= self.VARIANTS_PER_ROW:
            # Cap at valid range instead of raising error
            variant = min(max(0, variant), self.VARIANTS_PER_ROW - 1)

        # Extract tile at specific row and variant column
        return self._extract_tile_from_sheet(row, variant)


def load_hex_tiles():
    """
    Convenience function to load hex tiles.

    Extracts all terrain tiles in memory from the sprite sheet.
    Raises RuntimeError if sprite sheet unavailable or extraction fails.

    Returns:
        dict mapping terrain_id (0-16) -> PIL.Image (RGBA with transparency)
    """
    loader = HexTileLoader()
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
