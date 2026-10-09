"""Original D-Day terrain variants, edge blending and directional networks."""
from functools import lru_cache
import struct

from PIL import Image

from lib.game_art import load_bitmap


# SpOff, object 3 + 0x7de9: (column, row) for each network drawing style.
NETWORK_ORIGINS = ((6, 0), (6, 2), (0, 0), (0, 2), (0, 0), (6, 3),
                   (6, 1), (0, 1), (0, 3), (0, 1), (6, 4), (0, 2), (6, 2))


def network_sprites(record):
    """Yield PICT 129 (row, column) in DrawSpecials order.

    Four six-bit fields encode stream/river/ridge and dirt/paved/rail links.
    Directions are W, NW, NE, E, SE, SW. Joined road/rail curves use the
    pre-drawn long sprites selected by CalcSrcRect/FindLongs.
    """
    a, b, c, d = ((record >> shift) & 63 for shift in (8, 14, 20, 26))
    nets = (a & ~b, b & ~a, c & ~d, d & ~c, 0, c & d, a & b)
    for feature, mask in enumerate(nets):
        count = (nets[2] | nets[3]).bit_count() if feature in (2, 3) else mask.bit_count()
        for direction in range(6):
            if not mask & (1 << direction):
                continue
            style, rotation = feature, direction
            if feature in (2, 3, 5) and count == 2:
                if mask & (1 << ((direction + 2) % 6)):
                    style += 5
                elif mask & (1 << ((direction + 4) % 6)):
                    style += 5
                    rotation += 4
            col, row = NETWORK_ORIGINS[style]
            yield row, col + rotation
            if style in (7, 8, 10):
                break


class HexTileLoader:
    HEX_WIDTH = 32
    HEX_HEIGHT = 36
    HEX_SPACING = 34
    HEX_OFFSET_X = 0
    HEX_ROW_SPACING = 38
    VARIANTS_PER_ROW = 13
    NUM_TERRAIN_ROWS = 15
    TERRAIN_MAPPING = {terrain_id: (terrain_id, 0) for terrain_id in range(15)}

    def __init__(self):
        self.sprite_sheet = None
        self.tiles = {}
        self.artwork = {}

    def _get_sprite_sheet(self):
        return load_bitmap(128)

    @staticmethod
    @lru_cache(maxsize=1024)
    def _sprite(resource_id, row, col):
        sheet = load_bitmap(resource_id)
        x, y = col * 34, row * 38
        if x < 0 or y < 0 or x + 32 > sheet.width or y + 36 > sheet.height:
            raise ValueError(f'Tile ({row}, {col}) is outside PICT {resource_id}')
        return sheet.crop((x, y, x + 32, y + 36)).convert('RGBA')

    def _extract_tile_from_sheet(self, row, col):
        return self._sprite(128, row, col).copy()

    def get_tile_position(self, terrain_id, variant=0):
        if terrain_id not in self.TERRAIN_MAPPING:
            raise ValueError(f'Invalid terrain_id: {terrain_id}')
        col = 0 if variant is None else min(max(0, variant), self.VARIANTS_PER_ROW - 1)
        return terrain_id, col

    def load_tiles(self):
        self.sprite_sheet = self._get_sprite_sheet()
        # Fail early if a required overlay asset is missing.
        load_bitmap(129)
        load_bitmap(200)
        self.tiles = {code: self.get_tile_with_variant(code, 0) for code in self.TERRAIN_MAPPING}
        return self.tiles

    def get_tile_with_variant(self, terrain_id, variant):
        if (terrain_id, variant) in self.artwork:
            return self.artwork[terrain_id, variant].image()
        row, col = self.get_tile_position(terrain_id, variant)
        return self._extract_tile_from_sheet(row, col)

    def compose_tile(self, terrain_id, variant, record=0, edges=b'', hilltop=False):
        """Draw base variant, terrain edge blends, networks, then hill marker."""
        tile = self.get_tile_with_variant(terrain_id, variant)
        if edges:
            mask = struct.unpack_from('<H', edges)[0]
            for direction in range(6):
                if mask & (1 << direction):
                    style = edges[2 + direction]
                    row = (style >> 4) * 3 + (style & 15)
                    tile.alpha_composite(self._sprite(200, row, direction))
        for row, col in network_sprites(record):
            tile.alpha_composite(self._sprite(129, row, col))
        if hilltop:
            tile.alpha_composite(self._sprite(129, 5, 6))
        return tile

    def compose_map(self, width, height, layers):
        """Join the original sprites before zooming to avoid raster seams.

        At native resolution, tiles touch on a 32×27 grid with even rows
        shifted 16 pixels. Their stepped transparency masks fit at that
        spacing; independently rounding/resizing them breaks the joins.
        """
        raster = Image.new('RGBA', (width * 32 + 16, (height - 1) * 27 + 36))
        tiles = {}
        for (x, y), (terrain, variant) in layers.terrain.items():
            key = (terrain, variant, layers.records.get((x, y), 0),
                   layers.edges.get((x, y), b''), (x, y) in layers.hilltops)
            if key not in tiles:
                try:
                    tiles[key] = self.compose_tile(*key)
                except ValueError:
                    # Keep valid base terrain visible if an overlay is corrupt.
                    tiles[key] = self.get_tile_with_variant(terrain, variant)
            raster.alpha_composite(tiles[key], (x * 32 + 16 * (1 - y % 2), y * 27))
        return raster


def load_hex_tiles():
    return HexTileLoader().load_tiles()
