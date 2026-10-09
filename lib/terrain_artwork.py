"""D-Day artwork assignments, portable scenario sidecars and resource-pack export.

The engine has fourteen terrain rules and six base artwork slots per rule.
Imported pixels replace artwork slots, never change the rules or invent codes.
Both native zoom levels and dim/night artwork are carried with each assignment.
"""
from dataclasses import dataclass
from pathlib import Path
import base64
import hashlib
import json
import os
import shutil
import tempfile

from PIL import Image

from lib.game_art import load_bitmap
from lib.game_resources import game_path, read_resources
from lib.terrain_catalog import DDAY_TERRAIN_BY_CODE


PIXEL_FIELDS = ('large', 'small', 'dim_large', 'dim_small', 'night_large', 'night_small')


@dataclass(frozen=True)
class TerrainStamp:
    name: str
    large: bytes
    small: bytes
    dim_large: bytes
    dim_small: bytes
    night_large: bytes
    night_small: bytes

    def __post_init__(self):
        if not isinstance(self.name, str) or not 1 <= len(self.name) <= 200:
            raise ValueError('Invalid imported artwork name')
        for name in PIXEL_FIELDS:
            if len(getattr(self, name)) != (16 * 19 if name.endswith('small') else 32 * 36):
                raise ValueError('Invalid imported artwork dimensions')

    def image(self):
        image = Image.frombytes('P', (32, 36), self.large)
        image.putpalette(load_bitmap(128).getpalette())
        image.info['transparency'] = 0
        return image.convert('RGBA')

    @classmethod
    def from_artwork(cls, row, column, source_name):
        # The staged releases have identical clut 8 palettes. Do not silently
        # miscolour artwork from a different release if that ever changes.
        if load_bitmap(128, row.game).getpalette() != load_bitmap(128).getpalette():
            raise ValueError('This source palette differs from D-Day; colour conversion is required.')
        def pixels(col, small):
            tile = row.tile(col, small)
            # The source sheets contain occasional white (index-zero) pixels
            # inside a hex. Keep a solid D-Day hex mask: zero is transparency
            # in the editor and would otherwise produce pinholes in the map.
            width, height, dy = (16, 19, 21) if small else (32, 36, 38)
            target = load_bitmap(138 if small else 128)
            mask = target.crop((0, dy, width, dy + height)).tobytes()
            palette = target.getpalette()
            white = min(range(1, 256), key=lambda i: sum((255 - c) ** 2 for c in palette[i * 3:i * 3 + 3]))
            return bytes((value or white) if opaque else 0
                         for value, opaque in zip(tile.tobytes(), mask))
        ordinal = row.columns.index(column) + 1
        return cls(f'{source_name} · {row.name} · Artwork {ordinal}',
                   *(pixels(col, small)
                     for col in (column, row.dim_column, row.night_column)
                     for small in (False, True)))


def validate_slot(code, variant):
    if type(code) is not int or type(variant) is not int or code not in DDAY_TERRAIN_BY_CODE or variant not in range(6):
        raise ValueError('D-Day supports fourteen terrain types with six base artwork slots each.')


def automatic_artwork_slot(code, stamp, terrain, assignments):
    """Reuse an assignment or allocate an unused variant without changing a hex.

    Return None if every variant is in use, so replacement remains an explicit
    map-wide edit. Unused assignments are reclaimable: their source artwork
    remains available in the editor library.
    """
    validate_slot(code, 0)
    for variant in range(6):
        existing = assignments.get((code, variant))
        if existing and all(getattr(existing, field) == getattr(stamp, field) for field in PIXEL_FIELDS):
            return variant
    used = set(terrain.values())
    free = [variant for variant in range(6) if (code, variant) not in used]
    return min(free, key=lambda variant: ((code, variant) in assignments, variant)) if free else None


def artwork_path(scenario_path):
    from lib.scenario_files import scenario_asset_path
    return scenario_asset_path(scenario_path, '.terrain.json')


def encode_artwork(assignments, runtime_slot=None, title=None, conversion=None, document=None):
    slots = []
    for (code, variant), stamp in sorted(assignments.items()):
        validate_slot(code, variant)
        slots.append(dict(terrain=code, variant=variant, name=stamp.name,
                          **{key: base64.b64encode(getattr(stamp, key)).decode('ascii') for key in PIXEL_FIELDS}))
    payload = {'version': 1, 'runtime': 'dday', 'palette_sha256': _palette_digest(), 'slots': slots}
    if runtime_slot is not None:
        payload['runtime_slot'] = runtime_slot
    if title is not None:
        payload['title'] = title
    if conversion is not None:
        payload['conversion'] = conversion
    if document is not None:
        payload['document'] = document.to_dict()
    return (json.dumps(payload, indent=2) + '\n').encode('utf-8')


def _palette_digest():
    return hashlib.sha256(bytes(load_bitmap(128).getpalette())).hexdigest()


def decode_artwork(data):
    if len(data) > 8 * 1024 * 1024:
        raise ValueError('Terrain artwork file is too large')
    try:
        payload = json.loads(data)
        if payload['version'] != 1 or payload['runtime'] != 'dday' or len(payload['slots']) > 84:
            raise ValueError('Unsupported terrain artwork file')
        if payload['palette_sha256'] != _palette_digest():
            raise ValueError('Terrain artwork uses a different D-Day palette')
        assignments = {}
        for slot in payload['slots']:
            key = slot['terrain'], slot['variant']
            validate_slot(*key)
            if key in assignments:
                raise ValueError('Duplicate terrain artwork slot')
            assignments[key] = TerrainStamp(slot['name'],
                *(base64.b64decode(slot[field], validate=True) for field in PIXEL_FIELDS))
        return assignments
    except (KeyError, TypeError, UnicodeError, AttributeError) as exc:
        raise ValueError('Invalid terrain artwork file') from exc


def load_artwork(scenario_path):
    path = artwork_path(scenario_path)
    return decode_artwork(path.read_bytes()) if path.exists() else {}


def save_with_artwork(data, target, assignments, *, runtime_slot=None, title=None, extra_files=None,
                      staged_directory=None, include_artwork=True):
    """Commit a scenario and generated assets together, rolling back on failure.

    Extra files update an existing managed game. A staged directory installs a
    new game only after all file replacements succeed. The caller owns staging.
    Runtime installation omits editor artwork: its pixels are already in REZ.
    """
    target = Path(target)
    payloads = {target: data}
    sidecar = artwork_path(target)
    if include_artwork and (assignments or sidecar.exists()):
        if title is None and sidecar.exists():
            title = json.loads(sidecar.read_bytes()).get('title')
        payloads[sidecar] = encode_artwork(assignments, runtime_slot, title)
    payloads.update(extra_files or {})
    with tempfile.TemporaryDirectory(prefix='.waw-save-', dir=target.parent) as tmp:
        staged, originals = {}, {}
        for index, (path, payload) in enumerate(payloads.items()):
            path.parent.mkdir(parents=True, exist_ok=True)
            staged[path] = Path(tmp) / f'new-{index}'
            with staged[path].open('wb') as stream:
                stream.write(payload)
                stream.flush()
                os.fsync(stream.fileno())
            if path.exists():
                shutil.copymode(path, staged[path])
                originals[path] = Path(tmp) / f'old-{index}'
                shutil.copy2(path, originals[path])
        replaced = []
        try:
            for path, new in staged.items():
                os.replace(new, path)
                replaced.append(path)
            if staged_directory:
                source, destination = staged_directory
                if Path(destination).exists():
                    raise FileExistsError(f'Game folder already exists: {destination}')
                os.rename(source, destination)
        except OSError:
            for path in reversed(replaced):
                if path in originals:
                    os.replace(originals[path], path)
                else:
                    path.unlink()
            raise


def build_terrain_resources(original, assignments):
    """Patch only pixel regions in PICT 128/138; all other bytes stay identical."""
    resources = read_resources(original)
    result = bytearray(original)
    for resource_id, small in ((128, False), (138, True)):
        resource = resources['PICT', resource_id]
        width, height, dx, dy = (16, 19, 18, 21) if small else (32, 36, 34, 38)
        stride = int.from_bytes(resource.data[10:12], 'little') & 0x3fff
        expected_width, expected_height = (234, 314) if small else (442, 570)
        if (int.from_bytes(resource.data[8:10], 'little'),
                int.from_bytes(resource.data[6:8], 'little')) != (expected_width, expected_height):
            raise ValueError('Destination does not have the D-Day terrain-sheet layout')
        if len(resource.data) != 12 + stride * int.from_bytes(resource.data[6:8], 'little'):
            raise ValueError('Invalid destination terrain sheet')
        # A row has one night tile shared by every variant. Pick its lowest
        # assigned variant deterministically, independent of assignment order.
        night_rows = set()
        for (code, variant), stamp in sorted(assignments.items()):
            validate_slot(code, variant)
            fields = [(variant, stamp.small if small else stamp.large),
                      (variant + 6, stamp.dim_small if small else stamp.dim_large)]
            if code not in night_rows:
                fields.append((12, stamp.night_small if small else stamp.night_large))
                night_rows.add(code)
            for column, pixels in fields:
                for row in range(height):
                    offset = 12 + (code * dy + row) * stride + column * dx
                    if offset + width > len(resource.data):
                        raise ValueError('Artwork exceeds destination sheet')
                    result[resource.offset + offset:resource.offset + offset + width] = pixels[row * width:(row + 1) * width]
    return bytes(result)


def export_terrain_pack(destination, scenario_name, data, assignments):
    """Export a new overlay folder; never overwrite the staged game installations."""
    destination = Path(destination)
    if destination.exists():
        raise ValueError('Choose a new folder for the terrain pack.')
    if Path(scenario_name).name != scenario_name or not scenario_name.upper().endswith('.SCN'):
        raise ValueError('Invalid scenario filename')
    if len(data) < 0x1234 or int.from_bytes(data[:4], 'little') != 0x1230:
        raise ValueError('Only D-Day scenarios can be exported; earlier scenario formats need conversion.')
    original = game_path('dday', 'DATA', 'PCWATW.REZ').read_bytes()
    resource_data = build_terrain_resources(original, assignments)
    with tempfile.TemporaryDirectory(prefix='.waw-export-', dir=destination.parent) as tmp:
        pack = Path(tmp) / 'pack'
        (pack / 'DATA').mkdir(parents=True)
        (pack / 'SCENARIO').mkdir()
        (pack / 'DATA' / 'PCWATW.REZ').write_bytes(resource_data)
        target = pack / 'SCENARIO' / scenario_name
        target.write_bytes(data)
        artwork_path(target).parent.mkdir(parents=True)
        artwork_path(target).write_bytes(encode_artwork(assignments))
        (pack / 'INSTALL.txt').write_text(
            'D-Day terrain pack\n\n'
            'Copy DATA and SCENARIO into a separate copy of D-Day, replacing PCWATW.REZ.\n'
            'Run that copy of INVADE.EXE. This pack uses D-Day movement/combat rules.\n'
            'Imported artwork does not add Crusader or Stalingrad rules to the engine.\n'
            'The resource file is shared by every scenario in that game installation.\n'
            'The .terrain.json file preserves artwork assignments when reopening in the editor.\n'
            'This does not convert an earlier game scenario into D-Day format.\n', encoding='utf-8')
        os.rename(pack, destination)
