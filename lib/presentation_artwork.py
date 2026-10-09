"""Portable popup portraits, nationality flags and side emblems for D-Day."""
import base64
from dataclasses import dataclass
from functools import lru_cache
import hashlib
import json
import re
import struct
from pathlib import Path

from PIL import Image, ImageOps

from lib.game_art import load_bitmap
from lib.game_resources import GAME_NAMES, game_resources, read_resources, add_resources
from lib.scenario_files import scenario_asset_path
from lib.unit_definitions import NATIONALITIES
from lib.support_units import AIR_NAMES, SHIP_NAMES


LIBRARY = Path(__file__).resolve().parents[1] / 'assets' / 'presentation'


@dataclass(frozen=True)
class Slot:
    key: str
    label: str
    kind: str
    # Resource number and crop rectangle, one per native size.
    targets: tuple

    @property
    def sizes(self):
        return tuple((r-l, b-t) for _, (l, t, r, b) in self.targets)


SLOTS = {}
for side, name in enumerate(('Allied', 'Axis')):
    for variant in range(2):
        key = f'portrait_{side}_{variant}'
        SLOTS[key] = Slot(key, f'{name} popup portrait {variant+1}', 'portrait',
                          ((1100+side*2+variant, (0, 0, 37, 75)),))
for nation, name in enumerate(NATIONALITIES):
    key = f'flag_{nation}'
    SLOTS[key] = Slot(key, f'{name} nationality flag', 'flag',
                      ((560, (nation*34, 0, nation*34+32, 36)),
                       (561, (nation*18, 0, nation*18+16, 19))))
for side, name in enumerate(('Allied', 'Axis')):
    key = f'toolbar_{side}'
    SLOTS[key] = Slot(key, f'{name} toolbar flag', 'toolbar',
                      ((251, (7, 51+side*34, 33, 69+side*34)),))
    key = f'emblem_{side}'
    SLOTS[key] = Slot(key, f'{name} emblem', 'emblem', ((730+side, (0, 0, 43, 43)),))
    key = f'turn_{side}'
    size = (162, 221) if side == 0 else (177, 177)
    SLOTS[key] = Slot(key, f'{name} turn screen', 'turn', ((780+side, (0, 0, *size)),))

# Startup pictures are global: the game has not chosen a scenario yet.
for number, label, size in ((132, 'Game splash', (380, 450)),
                            (141, 'Series splash', (492, 246)),
                            (740, 'Publisher splash', (362, 270))):
    key = f'splash_{number}'
    SLOTS[key] = Slot(key, label, 'splash', ((number, (0, 0, *size)),))

for group, name in enumerate(SHIP_NAMES):
    key = f'ship_{group}'
    SLOTS[key] = Slot(key, f'Naval · {name} (both sides)', 'ship',
                      ((131, (36, group*35, 107, group*35+34)),))
for side, name in enumerate(('Allied', 'Axis')):
    for group, category in enumerate(AIR_NAMES):
        key = f'air_{side}_{group}'
        x = 108 + side*72
        SLOTS[key] = Slot(key, f'{name} aircraft · {category}', 'air',
                          ((131, (x, group*35, x+71, group*35+34)),))
LEADER_PICT_BASE = 12000


def slot_for(key):
    if key in SLOTS:
        return SLOTS[key]
    match = re.fullmatch(r'leader_([01])_(0|[1-9][0-9]{0,2})', key)
    if match and int(match[2]) < 128:
        side, index = map(int, match.groups())
        return Slot(key, f'{("Allied", "Axis")[side]} leader {index+1} portrait', 'leader',
                    ((LEADER_PICT_BASE+side*128+index, (0, 0, 37, 35)),))
    raise ValueError('Unknown presentation artwork slot')


def scenario_slots(roster=None):
    slots = dict(SLOTS)
    if roster is not None:
        from lib.scenario_data import leaders
        for side in (0, 1):
            for index, leader in enumerate(leaders(roster, side)):
                key = f'leader_{side}_{index}'
                slot = slot_for(key)
                slots[key] = Slot(key, f'{("Allied", "Axis")[side]} · {leader["name"]}', slot.kind, slot.targets)
    return slots


def remove_leader_portrait(assignments, side, index):
    result = {}
    for key, art in assignments.items():
        if key.startswith(f'leader_{side}_'):
            i = int(key.rsplit('_', 1)[1])
            if i == index:
                continue
            if i > index:
                key = f'leader_{side}_{i-1}'
        result[key] = art
    return result


def palette_digest():
    return hashlib.sha256(bytes(load_bitmap(128).getpalette())).hexdigest()


def indexed_image(pixels, size):
    image = Image.frombytes('P', size, pixels)
    image.putpalette(load_bitmap(128).getpalette())
    image.info['transparency'] = 0
    return image


def fit_pixels(image, size, *, matte=None):
    """Fit/quantize; flags use index-zero alpha, other UI pictures are opaque."""
    if image.width < 1 or image.height < 1 or image.width*image.height > 16_000_000:
        raise ValueError('Choose an image with at most 16 million pixels')
    if matte is None and image.mode == 'P' and image.size == size and image.getpalette() == load_bitmap(128).getpalette() and image.info.get('transparency') == 0:
        return image.tobytes()
    fitted = ImageOps.contain(image.convert('RGBA'), size, Image.Resampling.NEAREST)
    canvas = Image.new('RGBA', size)
    canvas.paste(fitted, ((size[0]-fitted.width)//2, (size[1]-fitted.height)//2))
    palette = load_bitmap(128).getpalette()
    if matte is not None:
        background = Image.new('RGBA', size, (*matte, 255))
        background.alpha_composite(canvas)
        colors = Image.new('P', (1, 1))
        colors.putpalette(palette)
        return background.convert('RGB').quantize(palette=colors, dither=Image.Dither.NONE).tobytes()
    # Duplicate a nontransparent color at zero so opaque white/black can never
    # accidentally quantize to the engine's transparent index.
    palette[:3] = palette[3:6]
    colors = Image.new('P', (1, 1))
    colors.putpalette(palette)
    quantized = canvas.convert('RGB').quantize(palette=colors, dither=Image.Dither.NONE)
    return bytes((p or 1) if alpha >= 128 else 0
                 for p, alpha in zip(quantized.tobytes(), canvas.getchannel('A').tobytes()))


@dataclass(frozen=True)
class Artwork:
    name: str
    pixels: tuple

    def image(self, key, version=0):
        image = indexed_image(self.pixels[version], slot_for(key).sizes[version])
        if slot_for(key).kind != 'flag':
            image.info.pop('transparency', None)
            image = image.convert('RGB')  # DrawPicture copies white index zero too.
        return image.convert('RGBA')


def from_image(key, image, name):
    slot = slot_for(key)
    matte = (68, 68, 68) if slot.kind == 'leader' else (None if slot.kind == 'flag' else load_bitmap(slot.targets[0][0]).convert('RGB').getpixel(slot.targets[0][1][:2]))
    return Artwork(name[:200], tuple(fit_pixels(image, size, matte=matte) for size in slot.sizes))


def import_image(key, filename):
    with Image.open(filename) as image:
        if image.width*image.height > 16_000_000:
            raise ValueError('Choose an image with at most 16 million pixels')
        image.load()
        return from_image(key, image, Path(filename).name)


@lru_cache(maxsize=64)
def source_bitmap(game, number):
    path = LIBRARY / game / f'PICT_{number}.png'
    if path.exists():
        with Image.open(path) as image:
            image.load()
            return image.copy()
    return load_bitmap(number, game)


def native_artwork(key):
    slot = slot_for(key)
    if slot.kind == 'leader':
        return from_image(key, Image.new('RGB', slot.sizes[0], (68, 68, 68)), 'No portrait')
    return Artwork('D-Day default', tuple(load_bitmap(number).crop(rect).tobytes()
                                         for number, rect in slot.targets))


@dataclass(frozen=True)
class Choice:
    label: str
    game: str
    targets: tuple

    def artwork(self, key):
        slot = slot_for(key)
        images = [source_bitmap(self.game, number).crop(rect) for number, rect in self.targets]
        if slot.kind == 'toolbar':
            # The native flag sheets include transparent cell margins. The
            # toolbar supplies its own pole/frame, so fit just the flag cloth.
            image = images[0].convert('RGBA')
            bounds = image.getbbox()
            return from_image(key, image.crop(bounds) if bounds else image, self.label)
        if slot.kind != 'flag':
            # PNG index-zero metadata is for the transparent flag sheets only.
            images[0].info.pop('transparency', None)
            return from_image(key, images[0].convert('RGB'), self.label)
        return Artwork(self.label, tuple(fit_pixels(images[min(i, len(images)-1)], size)
                                         for i, size in enumerate(slot.sizes)))


@lru_cache(maxsize=10)
def choices(kind):
    if kind == 'leader':
        return choices('portrait')
    if kind == 'splash':
        return ()  # Imports retain the size of the selected startup screen.
    if kind == 'toolbar':
        return choices('flag')
    result = []
    for game, game_name in GAME_NAMES.items():
        if kind in ('ship', 'air'):
            if kind == 'ship':
                cells = [(name, 36, group*35) for group, name in enumerate(SHIP_NAMES)] if game == 'dday' else []
            elif game == 'operation_crusader':
                cells = [(f'{side} · {AIR_NAMES[group]}', 36, (side_id*2+group)*35)
                         for side_id, side in enumerate(('Allied', 'Axis')) for group in range(2)]
            else:
                left = 108 if game == 'dday' else 36
                cells = [(f'{side} · {name}', left+side_id*72, group*35)
                         for side_id, side in enumerate(('Allied', 'Axis')) for group, name in enumerate(AIR_NAMES)]
            for label, x, y in cells:
                result.append(Choice(f'{game_name} · {label}', game, ((131, (x, y, x+71, y+34)),)))
        elif kind == 'flag':
            try:
                count = source_bitmap(game, 560).width//34
            except (OSError, ValueError):
                continue
            # Crusader's extra ensigns are distinct artwork slots. Leave their
            # labels numbered where a nationality mapping is not verified.
            names = (('American', 'German', 'Soviet', 'British', 'Polish', 'Flag 6', 'Flag 7', 'Italian')
                     if game == 'operation_crusader' else NATIONALITIES)
            for i in range(count):
                label = names[i] if i < len(names) else f'Flag {i+1}'
                result.append(Choice(f'{game_name} · {label}', game,
                                     ((560, (i*34, 0, i*34+32, 36)), (561, (i*18, 0, i*18+16, 19)))))
        else:
            ids = {'portrait': range(1100, 1104), 'emblem': (730, 731), 'turn': (780, 781)}[kind]
            for number in ids:
                try:
                    image = source_bitmap(game, number)
                except (OSError, ValueError):
                    continue
                offset = number-min(ids)
                label = (f'{"Allied" if offset < 2 else "Axis"} portrait {offset%2+1}'
                         if kind == 'portrait' else ('Allied' if offset == 0 else 'Axis'))
                result.append(Choice(f'{game_name} · {label}', game, ((number, (0, 0, *image.size)),)))
    return tuple(result)


def validate_artwork(assignments):
    for key, artwork in assignments.items():
        slot = slot_for(key)
        if not isinstance(artwork, Artwork):
            raise ValueError('Unknown presentation artwork slot')
        if not isinstance(artwork.name, str) or not 1 <= len(artwork.name) <= 200:
            raise ValueError('Invalid artwork name')
        sizes = slot.sizes
        if len(artwork.pixels) != len(sizes) or any(not isinstance(p, bytes) or len(p) != w*h
                                                  for p, (w, h) in zip(artwork.pixels, sizes)):
            raise ValueError('Invalid presentation artwork dimensions')
    return assignments


def presentation_path(path):
    return scenario_asset_path(path, '.presentation.json')


def encode_presentation(assignments):
    validate_artwork(assignments)
    payload = dict(version=1, runtime='dday', palette_sha256=palette_digest(), slots={
        key: dict(name=art.name, pixels=[base64.b64encode(p).decode('ascii') for p in art.pixels])
        for key, art in sorted(assignments.items())})
    return (json.dumps(payload, indent=2)+'\n').encode()


def load_presentation(path):
    path = presentation_path(path)
    if not path.exists():
        return {}
    if path.stat().st_size > 4*1024*1024:
        raise ValueError('Presentation artwork file is too large')
    try:
        payload = json.loads(path.read_bytes())
        if payload['version'] != 1 or payload['runtime'] != 'dday' or payload['palette_sha256'] != palette_digest():
            raise ValueError('Unsupported presentation artwork file or palette')
        return validate_artwork({key: Artwork(item['name'], tuple(base64.b64decode(p, validate=True) for p in item['pixels']))
                                 for key, item in payload['slots'].items()})
    except (KeyError, TypeError, AttributeError) as exc:
        raise ValueError('Invalid presentation artwork file') from exc


def patch_presentation(resources, assignments):
    validate_artwork(assignments)
    table = read_resources(resources)
    result = bytearray(resources)
    additions = {}
    for key, art in assignments.items():
        slot = slot_for(key)
        for (number, (left, top, right, bottom)), pixels in zip(slot.targets, art.pixels):
            if slot.kind == 'leader':
                # DOS PICT header followed by tightly packed palette indices.
                additions['PICT', number] = struct.pack('<HhhhhH', 0, 0, 0, bottom, right, right) + pixels
                continue
            record = table['PICT', number]
            native = game_resources()['PICT', number].data
            if len(record.data) != len(native) or record.data[:12] != native[:12]:
                raise ValueError('Presentation artwork requires D-Day resource dimensions')
            stride = int.from_bytes(record.data[10:12], 'little') & 0x3fff
            width = right-left
            for y in range(bottom-top):
                start = record.offset+12+(top+y)*stride+left
                result[start:start+width] = pixels[y*width:(y+1)*width]
    return add_resources(bytes(result), additions)


def startup_resources(assignments):
    from lib.game_resources import game_path
    original = game_path('dday', 'DATA', 'PCWATW.REZ').read_bytes()
    return patch_presentation(original, {k: v for k, v in assignments.items() if slot_for(k).kind == 'splash'})
