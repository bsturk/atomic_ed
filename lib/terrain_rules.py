"""Verified D-Day terrain constants; native movement/combat algorithms stay intact.

Dry/light-mud movement entries are half-hex contributions in hundredths (native ×10).
A uniform-terrain step costs entry/50 MP before crossings and visibility.
Road entries are native half-step thousandths (whole step = entry/500 MP).
"""
from dataclasses import dataclass
import struct

TERRAINS, MOBILITIES = 14, 12
GROUPS = (0, 1, 2, 3, 4, 5, 7, 1, 7, 6, 6, 8, 1, 7)
_NORMAL = (
    (75,50,100,200,50,0,50,50,75,0),
    (100,50,100,0,50,0,50,75,100,0),
    (100,50,100,0,50,0,50,75,100,0),
    (100,50,100,0,50,0,50,75,100,0),
    (75,50,100,200,50,0,50,50,75,0),
    (200,50,100,0,50,0,50,100,200,0),
    (200,50,100,0,50,0,50,100,200,0),
    (150,50,100,0,50,0,50,50,150,0),
    (150,50,100,0,50,0,50,50,150,0),
    (200,50,100,0,50,0,50,100,200,0),
    (0,)*10,
    (75,50,100,200,200,0,50,50,75,0),
)
_MUD = tuple(tuple((100,175,175,175,100,275,275,175,175,275,0,75)[m] if c == 0 else
                            (75,100,100,100,75,100,100,75,75,100,0,50)[m] if c == 1 else
                            250 if c == 3 and m in (0,4) else v
                            for c,v in enumerate(row)) for m,row in enumerate(_NORMAL))
MOVEMENT_DEFAULT = tuple(row[t] for table in (_NORMAL, _MUD) for row in table for t in GROUPS)
ROAD_DEFAULT = tuple(v for row in ((375,250,375), (325,250,250), (325,250,250),
    (325,250,250), (325,150,250), (325,125,250), (325,125,250), (325,125,250),
    (325,165,250), (325,125,250), (0,0,0), (375,250,375)) for v in row)
DEFENSE_DEFAULT = (100,100,100,100,100,100,100,150,150,200,100,100,100,100)
ANTI_ARMOR_DEFAULT = (200,100,150,150,150,100,100,200,200,300,200,250,100,100)
BARRAGE_DEFAULT = (75,100,80,80,80,100,100,50,50,25,50,50,100,100)
DEFAULT = MOVEMENT_DEFAULT + ROAD_DEFAULT + DEFENSE_DEFAULT + ANTI_ARMOR_DEFAULT + BARRAGE_DEFAULT
MOVEMENT_COUNT, ROAD_START, COMBAT_START = 336, 336, 372
COUNT = len(DEFAULT)  # 414 unsigned words
SIZE = 16+COUNT*2
MAGIC = b'WAWTER01'


def movement_index(terrain, mobility, muddy=False):
    return (int(muddy)*MOBILITIES+mobility)*TERRAINS+terrain


def validate(values):
    if len(values) != COUNT:
        raise ValueError('Unsupported terrain rule table')
    for i, value in enumerate(values):
        maximum = 500 if i < ROAD_START else 5000 if i < COMBAT_START else 400
        if type(value) is not int or not 0 <= value <= maximum:
            raise ValueError(f'Terrain rule {i}: enter an integer from 0 to {maximum}')
        if i < ROAD_START and (i % TERRAINS == 5 or i//TERRAINS % MOBILITIES == 10) and value:
            raise ValueError('Water and fixed-unit movement must remain blocked')
        if ROAD_START <= i < COMBAT_START:
            fixed = (i-ROAD_START)//3 == 10
            if (fixed and value) or (not fixed and not value):
                raise ValueError('Road costs must be positive for mobile classes and zero for Fixed')
    return tuple(values)


@dataclass(frozen=True)
class TerrainRules:
    values: tuple = DEFAULT

    def __post_init__(self):
        object.__setattr__(self, 'values', validate(tuple(self.values)))

    @property
    def changed(self):
        return sum(a != b for a,b in zip(self.values, DEFAULT))

    def to_dict(self):
        return dict(version=1, overrides={str(i): v for i,v in enumerate(self.values) if v != DEFAULT[i]})

    @classmethod
    def from_dict(cls, obj):
        if obj.get('version') != 1 or not isinstance(obj.get('overrides'), dict):
            raise ValueError('Unsupported terrain rules')
        values = list(DEFAULT)
        for key, value in obj['overrides'].items():
            i = int(key)
            if str(i) != key or not 0 <= i < COUNT:
                raise ValueError('Unknown terrain rule')
            values[i] = value
        return cls(tuple(values))


def encode_terrain_rules(rules):
    return struct.pack(f'<8sII{COUNT}H', MAGIC, SIZE, sum(rules.values), *rules.values)


def decode_terrain_rules(blob):
    if len(blob) != SIZE:
        raise ValueError('Invalid DOS terrain rules length')
    magic, size, checksum, *values = struct.unpack(f'<8sII{COUNT}H', blob)
    if magic != MAGIC or size != SIZE or checksum != sum(values):
        raise ValueError('Invalid DOS terrain rules checksum or version')
    return TerrainRules(tuple(values))
