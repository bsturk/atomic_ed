"""Bounded readers for the retail Stalingrad and Operation Crusader SCNs.

These are serialized, length-prefixed objects, not pointer-based file formats.
Layouts follow each executable's LoadGame/RW routines; see WAW_CONVERSION.md.
Unknown bytes and the unused file tail remain available in ``blocks``.
"""
from dataclasses import dataclass
from pathlib import Path
import struct


LAYOUTS = {0xf4a: 'stalingrad', 0xdac: 'operation_crusader'}


def i16(data, offset):
    return struct.unpack_from('<h', data, offset)[0]


def i32(data, offset):
    return struct.unpack_from('<i', data, offset)[0]


@dataclass
class WawScenario:
    path: Path
    data: bytes
    game: str
    blocks: dict
    offsets: dict

    @classmethod
    def read(cls, path):
        path = Path(path)
        return cls.from_bytes(path.read_bytes(), path)

    @classmethod
    def from_bytes(cls, data, path=Path('IMPORTED.SCN')):
        if len(data) < 4 or (size := i32(data, 0)) not in LAYOUTS:
            raise ValueError('Not a supported Stalingrad or Operation Crusader scenario')
        game, blocks, offsets, cursor = LAYOUTS[size], {}, {}, 0
        stalin = game == 'stalingrad'

        def take(name, multiplier=1):
            nonlocal cursor
            if multiplier:
                if cursor + 4 > len(data):
                    raise ValueError(f'Missing {name} block')
                length = i32(data, cursor) * multiplier
                cursor += 4
            else:
                length = 12 if stalin else 8
            if length < 0 or cursor + length > len(data):
                raise ValueError(f'Truncated {name} block')
            offsets[name] = cursor
            blocks[name] = bytes(data[cursor:cursor+length])
            cursor += length

        for name in ('scenario', 'calendar', 'hexmap', 'uhexes', 'zoc',
                     'ob0', 'ob1', 'weather', 'supply'):
            take(name)
        header = blocks['scenario']
        if stalin:
            for name in ('stock0', 'stock1', 'depot0', 'depot1'):
                take(name)
            if header[0xf3d]:
                take('garrison')
        else:
            for name in ('stock', 'depot0', 'depot1'):
                take(name)
        for name in ('victory', 'vicloc', 'autoart0', 'autoart1', 'autognd0', 'autognd1'):
            take(name)
        for side in (0, 1):
            if header[(0x1fc if stalin else 0x78)+side]:
                take(f'leaders{side}')
        if stalin:
            take('reps0')
            take('reps1')
        take('ai_counts', 0)
        for name in ('bgstate', 'bgshx', 'bgshy', 'bgdhx', 'bgdhy'):
            take(name)
        if stalin:
            for side in (0, 1):
                if i16(header, 0x1e8+side*2):
                    take(f'riders{side}')
            take('tanks0')
            take('tanks1')
        take('planeclass', 2)
        if stalin:
            take('planecounts')
        for side in (0, 1):
            # Crusader writes the HQ unit list AND its sibling list under one
            # byte length. D-Day/Stalingrad store siblings inside the HQ record.
            take(f'hqlist{side}', 1 if stalin else 2)
        if stalin:
            take('hqheads', 2)
        for name in ('hqs0', 'hqs1', 'arty0', 'arty1'):
            take(name)
        offsets['tail'] = cursor
        blocks['tail'] = bytes(data[cursor:])
        result = cls(Path(path), bytes(data), game, blocks, offsets)
        result.validate()
        return result

    @property
    def stalin(self):
        return self.game == 'stalingrad'

    @property
    def header(self):
        return self.blocks['scenario']

    @property
    def stride(self):
        return 168 if self.stalin else 150

    @property
    def type_offset(self):
        return 0x70 if self.stalin else 0x60

    @property
    def units(self):
        return [[block[i:i+self.stride] for i in range(0, len(block), self.stride)]
                for block in (self.blocks['ob0'], self.blocks['ob1'])]

    @property
    def dimensions(self):
        top, left, bottom, right = struct.unpack_from('<4h', self.header, 0x1bc if self.stalin else 0x48)
        if top or left or not 1 <= bottom <= 255 or not 1 <= right <= 255:
            raise ValueError('Unsupported source map rectangle')
        return right+1, bottom+1

    @property
    def title(self):
        titles = {
            'stalingrad': {'CAMPAIGN': 'Operation Uranus', 'CITY': 'Rattenkrieg',
                'HURBERT': 'To the Volga!', 'VOLGA': 'To the Volga!',
                'RIVER': 'A River Too Far', 'CLASH': 'A River Too Far',
                'TANKS': "Manstein's Solution", 'MANSTEIN': "Manstein's Solution",
                'QUIET': 'Quiet Flows the Don', 'WINTER': 'Wintergewitter'},
            'operation_crusader': {'CAMPAIGN': 'Operation Crusader', 'DUCE': "Il Duce's Finest",
                'HELLFIRE': 'Hell Fire Pass', 'RELIEVED': 'Tobruk Relieved',
                'RESCUE': 'To The Rescue!', 'TOBRUK': 'Fortress Tobruk'},
        }
        return titles[self.game].get(self.path.stem.upper(), self.path.stem)

    def validate(self):
        b, h, s = self.blocks, self.header, self.stalin
        def length(key, expected):
            if len(b.get(key, b'')) != expected:
                raise ValueError(f'{key}: expected {expected} bytes, found {len(b.get(key, b""))}')
        length('calendar', 42)
        width, height = self.dimensions
        length('hexmap', width*height*2)
        length('zoc', width*height*4)
        if not b['uhexes'] or len(b['uhexes']) % 4:
            raise ValueError('Invalid shared hex records')
        if any(index*4 >= len(b['uhexes']) for (index,) in struct.iter_unpack('<H', b['hexmap'])):
            raise ValueError('Map references a missing hex record')
        days = i16(b['calendar'], 24)
        if days < 1 or b['calendar'][28] not in (3, 6):
            raise ValueError('Unsupported source calendar')
        length('supply', days*4)
        length('weather', 2146 if s else 494)
        length('victory', 1088 if s else 688)
        length('vicloc', h[0xf3c if s else 0xd9f]*48)
        label_count = h[0xf44 if s else 0xda8]
        if label_count > 40:
            raise ValueError('Invalid source place-name count')
        for index in range(label_count):
            label = h[(0xa3a if s else 0x87c)+index*32:][:32]
            if not 0 <= i16(label, 0) < width or not 0 <= i16(label, 2) < height:
                raise ValueError('Source place name outside the map')
            if s and label[31] not in b'VRI':
                raise ValueError('Unknown source place-name style')
        if s:
            length('garrison', h[0xf3d]*6)
        else:
            length('stock', 220)
        for side in (0, 1):
            total = i16(h, (0x1dc if s else 0x64)+side*2)
            hqs = i16(h, (0x1d4 if s else 0x5c)+side*2)+(not s)
            length(f'ob{side}', total*self.stride)
            length(f'hqlist{side}', hqs*(2 if s else 4))
            length(f'hqs{side}', hqs*(34 if s else 12))
            length(f'arty{side}', i16(h, (0x1e0 if s else 0x68)+side*2)*28)
            for kind in ('autoart', 'autognd'):
                length(f'{kind}{side}', hqs)
            length(f'leaders{side}', h[(0x1fc if s else 0x78)+side]*(36 if s else 30))
            if len(b[f'depot{side}']) % (24 if s else 52):
                raise ValueError('Invalid source depot records')
            if s:
                length(f'reps{side}', days*9)
                length(f'stock{side}', i16(h, 0x1f4+side*2)*136)
                length(f'riders{side}', i16(h, 0x1e8+side*2)*4)
                length(f'tanks{side}', i16(h, 0x1e4+side*2)*10)
            if any(u[self.type_offset+2] > 8 for u in self.units[side]):
                raise ValueError('Unknown source unit class')
