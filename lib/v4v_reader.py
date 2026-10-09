"""Bounded reader for the staged V for Victory 2.1 scenarios and battlesets.

This is a distinct format from the later World at War releases. Offset notes
and conversion limits are documented in txt/V4V_CONVERSION.md.
"""
from dataclasses import dataclass
from pathlib import Path
import math
import struct

from PIL import Image

from lib.terrain_reader import _read_block


BATTLESETS = {0: ('UTAH', 'UTAH'), 1: ('VELIKIYE', 'VL'),
             2: ('MARKET', 'MG'), 3: ('GJS', 'GJS')}


def read_blocks(data):
    blocks, offset = [], 0
    while offset < len(data):
        block, offset = _read_block(data, offset)
        blocks.append(block)
    return blocks


def short(data, offset):
    return struct.unpack_from('<h', data, offset)[0]


@dataclass
class VictoryScenario:
    path: Path
    blocks: list
    battleset: bytes
    resource_name: str

    @classmethod
    def read(cls, path):
        path = Path(path)
        blocks = read_blocks(path.read_bytes())
        if len(blocks) not in (26, 27) or len(blocks[0]) != 0xc0c or len(blocks[1]) != 44:
            raise ValueError('Unsupported V for Victory scenario layout')
        sid = blocks[0][1]
        if sid not in BATTLESETS:
            raise ValueError('Unknown V for Victory battleset')
        btl_name, resource = BATTLESETS[sid]
        battle_blocks = read_blocks((path.parent / f'{btl_name}.BTL').read_bytes())
        if len(battle_blocks) != 1 or len(battle_blocks[0]) != 0x6ee or battle_blocks[0][1] != sid:
            raise ValueError('Invalid battleset file')
        result = cls(path, blocks, battle_blocks[0], resource)
        result.validate()
        return result

    @property
    def width(self):
        return short(self.battleset, 12) + 1

    @property
    def height(self):
        return short(self.battleset, 10) + 1

    @property
    def rect(self):
        return struct.unpack_from('<4h', self.blocks[0], 8)

    @property
    def title(self):
        index = short(self.blocks[0], 2)
        start = 0x42f + 25 * index
        return self.battleset[start:start + 25].split(b'\0')[0].decode('mac_roman').strip()

    @property
    def theater(self):
        return self.battleset[0x2e:0x12e].split(b'\0')[0].decode('mac_roman').strip()

    @property
    def units(self):
        return [[block[i:i + 156] for i in range(0, len(block), 156)] for block in self.blocks[5:7]]

    @property
    def briefings(self):
        header = self.blocks[0]
        return tuple('\n'.join(header[0x7e + line * 256 + side * 128:
                                      0x7e + line * 256 + side * 128 + 128]
                               .split(b'\0')[0].decode('mac_roman') for line in range(8)).rstrip('\n')
                     for side in (0, 1))

    @property
    def historical_weather(self):
        """Authored weather for this scenario, not the initially empty live table.

        Verified in V4V overlays 24d1:03ab and 253d:0000. Table indexes are
        relative to the BTL start timestamp. Ground values are seeds at that
        earlier timestamp, before CreateWeather's warm-up loop.
        """
        start, end = struct.unpack_from('<2i', self.blocks[0], 0x16)
        origin, battle_end = struct.unpack_from('<2i', self.battleset, 0x16)
        first, stop = start - origin, end - origin + 1
        if not (0 <= first < stop <= 400 and end <= battle_end):
            raise ValueError('Scenario dates exceed the V4V historical weather table')
        weather = self.blocks[7]
        temperatures = struct.unpack_from(f'<{stop - first}h', weather, 0x414 + 2 * first)
        codes = weather[0xb8 + first:0xb8 + stop]
        if any(code > 4 for code in codes):
            raise ValueError('Unknown V4V historical weather code')
        seed = struct.unpack_from('<3f', weather, 0xb9c)
        if any(not math.isfinite(value) or value < 0 for value in seed):
            raise ValueError('Invalid V4V initial ground conditions')
        return {'mode': self.blocks[0][0x59], 'temperature_mode': self.blocks[0][0x5a],
                'table_origin': origin, 'first_index': first, 'turns': stop - first,
                'temperatures_f': list(temperatures), 'weather_codes': list(codes),
                'ground_seed_at_table_origin': dict(zip(('snow', 'ice', 'wetness'), seed))}

    @property
    def objectives(self):
        block = self.blocks[-12]
        return [block[i:i + 42] for i in range(0, len(block), 42)]

    @property
    def labels(self):
        header = self.blocks[0]
        count = short(header, 0x87e)
        return [header[0x880 + i * 30:0x880 + (i + 1) * 30] for i in range(count)]

    def validate(self):
        b = self.blocks
        if len(b[2]) != self.width * self.height * 2 or len(b[4]) != self.width * self.height * 4:
            raise ValueError('Map size does not match the battleset bounds')
        if not b[3] or len(b[3]) % 4:
            raise ValueError('Invalid shared map records')
        if any(index * 4 >= len(b[3]) for (index,) in struct.iter_unpack('<H', b[2])):
            raise ValueError('Map index outside the shared-record table')
        if any(len(block) % 156 for block in b[5:7]):
            raise ValueError('Truncated unit record')
        top, left, bottom, right = self.rect
        if not (0 <= top < self.height and top <= bottom <= self.height
                and 0 <= left < self.width and left <= right <= self.width):
            raise ValueError('Invalid scenario bounds')
        if len(b[7]) != 2986 or len(b[-13]) != 1632 or len(b[-12]) % 42:
            raise ValueError('Unsupported weather/victory layout')
        if any(len(block) != 160 for block in b[-5:]):
            raise ValueError('Unsupported AI block layout')
        if not 0 <= short(b[0], 0x87e) <= 30:
            raise ValueError('Invalid map-label count')
        for side, records in enumerate(self.units):
            for index, record in enumerate(records):
                if short(record, 0) != index or record[0x1a] > 8:
                    raise ValueError('Unexpected unit ID or class')
                if record[0x1b] > 98:
                    raise ValueError('Unknown unit descriptor')
                name = record[0x6a:].split(b'\0')[0]
                if not name or len(name) > 25:
                    raise ValueError('Unit name cannot fit the D-Day record')


def read_resources(path):
    """V4V RES: uint16 count, then (reversed type, uint16 ID, uint32 offset)."""
    data = Path(path).read_bytes()
    if len(data) < 2:
        raise ValueError('Truncated V4V resources')
    count = struct.unpack_from('<H', data)[0]
    start = 2 + 10 * count
    if start > len(data):
        raise ValueError('Truncated V4V resource directory')
    entries = [struct.unpack_from('<4sHI', data, 2 + i * 10) for i in range(count)]
    offsets = sorted({offset for _, _, offset in entries} | {len(data)})
    if len(offsets) != count + 1 or offsets[0] < start:
        raise ValueError('Invalid V4V resource offsets')
    ends = dict(zip(offsets, offsets[1:]))
    return {(kind[::-1].decode('ascii'), number): data[offset:ends[offset]]
            for kind, number, offset in entries}


def read_bitmap(data, palette, colors=None):
    """Decode the 66-byte DOS bitmap structure, including its inclusive Rect."""
    if len(data) < 66:
        raise ValueError('Truncated V4V bitmap')
    stride, top, left, bottom, right = struct.unpack_from('<H4h', data, 4)
    depth = short(data, 16)
    width, height = right - left + 1, bottom - top + 1
    if depth not in (4, 8) or top or left or not 0 < width <= stride * (8 // depth) or height <= 0 or len(data) != 66 + stride * height:
        raise ValueError('Unsupported V4V bitmap')
    pixels = data[66:]
    if depth == 4:
        if colors is None or len(colors) != 18 or short(colors, 0) != 16:
            raise ValueError('Missing V4V counter palette')
        # The low nibble is the left pixel; clut entries are VGA indexes.
        pixels = bytes(colors[2 + n] for byte in pixels for n in (byte & 15, byte >> 4))
    image = Image.frombytes('P', (stride * (8 // depth), height), pixels)
    image.putpalette(palette)
    return image.crop((0, 0, width, height))
