"""Decode the DOS game's indexed PICT bitmaps and original unit counters.

These resources contain a 12-byte little-endian bitmap header, not a Mac
QuickDraw instruction stream. Extracted .pict files add a 512-byte wrapper.
"""
from functools import lru_cache
from pathlib import Path
import struct

from PIL import Image

from lib.game_resources import game_resources


ASSETS = Path(__file__).resolve().parents[1] / 'extracted_images'
TERRAIN_ASSETS = Path(__file__).resolve().parents[1] / 'assets' / 'terrain'


def decode_bitmap(data, clut):
    """Decode a DOS PICT using its own game's palette (index zero is transparent)."""
    if len(data) < 12 or len(clut) < 8:
        raise ValueError('Truncated DOS bitmap or palette')
    _size, top, left, bottom, right, stride = struct.unpack_from('<HhhhhH', data)
    stride &= 0x3fff
    width, height = right - left, bottom - top
    if not 0 < width <= stride or height <= 0 or len(data) != 12 + stride * height:
        raise ValueError('Invalid DOS bitmap')
    image = Image.frombytes('P', (stride, height), data[12:])
    count = struct.unpack_from('>H', clut, 6)[0] + 1
    if count > 256 or len(clut) < 8 + count * 8:
        raise ValueError('Invalid game palette')
    palette = [0] * 768
    sequential = bool(struct.unpack_from('>H', clut, 4)[0] & 0x8000)
    for ordinal, (index, red, green, blue) in enumerate(struct.iter_unpack('>4H', clut[8:8 + count * 8])):
        if sequential:
            index = ordinal
        if index > 255:
            raise ValueError('Invalid palette index')
        palette[index * 3:index * 3 + 3] = (red >> 8, green >> 8, blue >> 8)
    image.putpalette(palette)
    image.info['transparency'] = 0
    return image.crop((0, 0, width, height))


@lru_cache(maxsize=32)
def load_bitmap(resource_id, game='dday'):
    # The editor owns these extracted assets; the earlier games need not remain
    # installed after the library has been built from the user's staged files.
    library_path = TERRAIN_ASSETS / game / f'PICT_{resource_id}.png'
    if game != 'dday' and library_path.is_file():
        with Image.open(library_path) as image:
            image.load()
            if image.mode != 'P' or image.info.get('transparency') != 0:
                raise ValueError(f'Invalid indexed terrain asset: {library_path}')
            return image.copy()
    try:
        resources = game_resources(game)
    except FileNotFoundError:
        # Keep the editor usable with the previously extracted D-Day assets.
        if game != 'dday':
            raise
        paths = sorted(ASSETS.glob(f'PICT_{resource_id}[_.]*'))
        if not paths:
            raise RuntimeError(f'Missing game bitmap PICT {resource_id}')
        return decode_bitmap(paths[0].read_bytes()[512:], (ASSETS / 'clut_8.bin').read_bytes())
    try:
        return decode_bitmap(resources['PICT', resource_id].data, resources['clut', 8].data)
    except KeyError as exc:
        raise ValueError(f'{game}: missing resource {exc}') from exc


@lru_cache(maxsize=1024)
def unit_counter(resource_id, counter_index, bitmap=None):
    """NewCalcPxPy: 22 columns of 22×23 counters, selected by OB+0x56."""
    sheet = (_counter_sheet(bitmap)
             if bitmap is not None else load_bitmap(resource_id))
    x, y = counter_index % 22 * 22, counter_index // 22 * 23
    if counter_index < 0 or x + 22 > sheet.width or y + 23 > sheet.height:
        raise ValueError(f'Counter {counter_index} is outside PICT {resource_id}')
    return sheet.crop((x, y, x + 22, y + 23)).convert('RGBA')


@lru_cache(maxsize=8)
def _counter_sheet(bitmap):
    return decode_bitmap(bitmap, game_resources('dday')['clut', 8].data)


@lru_cache(maxsize=128)
def support_unit_icon(unit_class, type_code, side, artwork=None):
    """PICT 131 ship/air class buttons, as laid out by InitPSButtons.

    Ships occupy x=36; Allied/Axis aircraft x=108/180. Each button is
    71×34 with a one-pixel row separator. Aircraft categories follow the
    scenarios' pClassCnt/pClassHds rosters, not their ground-chit indexes.
    """
    if side not in ('Allied', 'Axis'):
        raise ValueError(f'Unknown support-unit side: {side}')
    if artwork is not None:
        from lib.support_units import artwork_key
        return artwork.image(artwork_key(unit_class, type_code, int(side == 'Axis')))
    if unit_class == 5 and 30 <= type_code <= 34:
        x, row = 36, type_code - 30
    elif unit_class == 6 and type_code in (36, 37, 38, 94, 95):
        x = 108 if side == 'Allied' else 180
        row = {37: 0, 38: 0, 36: 1, 94: 2, 95: 3}[type_code]
    else:
        raise ValueError(f'No support artwork for class {unit_class}, type {type_code}')
    y = row * 35
    image = load_bitmap(131).crop((x, y, x + 71, y + 34))
    image.info.pop('transparency', None)
    return image.convert('RGBA')
