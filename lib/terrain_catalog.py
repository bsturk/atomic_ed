"""Verified terrain choices, independent of the contents of a scenario.

Each game's catalog must be mapped to its own executable and artwork. D-Day's
normal terrain rows are 0–13; 14 is special display graphics, and columns 6–12
are shading/display modes rather than additional terrain variants.
"""
from dataclasses import dataclass

from lib.game_art import load_bitmap
from lib.terrain_reader import TERRAIN_TYPES


@dataclass(frozen=True)
class TerrainDefinition:
    code: int
    name: str
    variants: tuple = tuple(range(6))


DDAY_TERRAIN = tuple(TerrainDefinition(code, TERRAIN_TYPES[code]) for code in range(14))
DDAY_TERRAIN_BY_CODE = {entry.code: entry for entry in DDAY_TERRAIN}


def terrain_catalog(game='dday'):
    """Return only catalogs whose code/artwork mapping has been verified."""
    if game != 'dday':
        raise ValueError(f'Terrain mapping is not yet verified for {game}.')
    return DDAY_TERRAIN


@dataclass(frozen=True)
class ArtworkRow:
    """Sprite coordinates, never a claim about the source game's terrain enum."""
    game: str
    row: int
    name: str
    columns: tuple
    dim_column: int
    night_column: int
    dday_terrain: int

    def terrain_for_column(self, column):
        # Crusader's second selectable tile has a town drawn on the base.
        return 4 if self.game == 'operation_crusader' and column == 2 and self.row != 9 else self.dday_terrain

    def tile(self, column, small=False):
        if column not in self.columns + (self.dim_column, self.night_column):
            raise ValueError('Invalid artwork column')
        width, height, dx, dy = (16, 19, 18, 21) if small else (32, 36, 34, 38)
        sheet = load_bitmap(138 if small else 128, self.game)
        x, y = column * dx, self.row * dy
        if x + width > sheet.width or y + height > sheet.height:
            raise ValueError('Artwork extends outside the sprite sheet')
        return sheet.crop((x, y, x + width, y + height))


ART_SOURCES = {'dday': 'D-Day', 'operation_crusader': 'Operation Crusader',
               'stalingrad_summer': 'Stalingrad · Summer',
               'stalingrad_winter': 'Stalingrad · Winter',
               'v4v_utah': 'V4V · Utah Beach', 'v4v_vl': 'V4V · Velikiye Luki',
               'v4v_mg': 'V4V · Market Garden', 'v4v_gjs': 'V4V · Gold–Juno–Sword'}

# Visual descriptions of the original artwork, not inferred terrain-code names.
# In Crusader columns 1 and 11 are dim display copies; column 2 depicts a town.
# In Stalingrad each eight-column seasonal bank ends with two dim display copies.
CRUSADER_ART_NAMES = ('Desert', 'Scrub', 'Rocky ground', 'Marsh',
                      'Scattered buildings', 'Town', 'Water')
STALINGRAD_ART_NAMES = ('Open ground', 'Woodland', 'Marsh', 'City blocks A',
                       'Ruined blocks A', 'Town', 'Water A', 'City blocks B',
                       'Airfield', 'Water B', 'Industrial blocks A',
                       'Industrial blocks B', 'Ruined blocks B',
                       'Residential blocks', 'Destroyed industrial blocks')

# Editor defaults for D-Day gameplay, not the earlier executables' enum values.
# Dry scrub/broken ground use Clear; buildings use Town/City and ruins Rubble.
CRUSADER_DDAY_RULES = (1, 1, 1, 3, 4, 4, 5)
STALINGRAD_DDAY_RULES = (1, 2, 3, 10, 11, 4, 5, 10, 12, 5, 10, 10, 11, 10, 11)


def artwork_catalog(source):
    if source.startswith('v4v_') and source in ART_SOURCES:
        import json
        from lib.game_art import TERRAIN_ASSETS
        rows = json.loads((TERRAIN_ASSETS / source / 'catalog.json').read_bytes())
        return tuple(ArtworkRow(source, r['row'], r['name'], (0,), 1, 2, r['code']) for r in rows)
    if source == 'operation_crusader':
        return tuple(ArtworkRow(source, row, name, tuple(range(11)) if row == 9 else (0, *range(2, 11)), 1, 11, rules)
                     for row, (name, rules) in enumerate(zip(CRUSADER_ART_NAMES, CRUSADER_DDAY_RULES), 3))
    if source in ('stalingrad_summer', 'stalingrad_winter'):
        start = 8 if source.endswith('winter') else 0
        return tuple(ArtworkRow('stalingrad', row, name, tuple(range(start, start + 6)),
                                start + 6, start + 7, rules)
                     for row, (name, rules) in enumerate(zip(STALINGRAD_ART_NAMES, STALINGRAD_DDAY_RULES), 3))
    raise ValueError(f'Unknown artwork source: {source}')
