"""Versioned authoring profiles and the bounded DOS rule-table interchange.

Values are in D-Day's thousandths for ground conditions. Earlier floating
point winter models are evaluated in those units, so they are adaptations,
not bit-for-bit reproductions of the earlier engines.
"""
from dataclasses import dataclass, field, replace
import base64
import hashlib
import json
import struct
import zlib
from lib.terrain_rules import TerrainRules, decode_terrain_rules, SIZE as TERRAIN_SIZE

GAMES = {'dday': 'D-Day', 'stalingrad': 'Stalingrad',
         'operation_crusader': 'Operation Crusader', 'v4v': 'V for Victory',
         'v4v_velikiye': 'V for Victory: Velikiye Luki'}
FIELDS = ('winter_model', 'major_victory', 'minor_victory', 'light_snow',
          'heavy_snow', 'light_rain', 'heavy_rain', 'snow_melt', 'drying',
          'ice_divisor', 'ice_threshold', 'ice_step')
DEFAULT = (0, 200, 125, 10, 40, 15, 45, 8, 5, 18, 12000, 200)
DEFAULTS = {
    'dday': DEFAULT,
    'operation_crusader': DEFAULT,  # Winter not verified: explicit D-Day fallback.
    'stalingrad': (1, 200, 125, 100, 400, 15, 45, 80, 50, 18, 12000, 200),
    'v4v': (2, 200, 125, 150, 450, 15, 45, 80, 50, 18, 12000, 200),
    'v4v_velikiye': (3, 200, 125, 150, 450, 15, 45, 80, 50, 18, 12000, 200),
}
LIMITS = ((0, 3), (101, 10000), (100, 9999), *((0, 10000),)*6,
          (1, 1000), (1000, 1000000), (0, 10000))
MAGIC = b'WAWPRO01'
SIZE = 64


def validate_values(values):
    if len(values) != len(FIELDS):
        raise ValueError('Unsupported game rule table')
    for key, value, (low, high) in zip(FIELDS, values, LIMITS):
        if type(value) is not int or not low <= value <= high:
            raise ValueError(f'{key.replace("_", " ")}: enter an integer from {low} to {high}')
    if values[1] <= values[2]:
        raise ValueError('Major victory ratio must exceed minor victory ratio')
    return tuple(values)


@dataclass(frozen=True)
class GameProfile:
    game: str = 'dday'
    overrides: tuple = ()
    terrain: TerrainRules = field(default_factory=TerrainRules)

    def __post_init__(self):
        if self.game not in GAMES:
            raise ValueError('Unknown game profile')
        if len(dict(self.overrides)) != len(self.overrides) or set(dict(self.overrides))-set(FIELDS):
            raise ValueError('Unknown or duplicate game rule override')
        object.__setattr__(self, 'overrides', tuple(sorted(self.overrides)))
        validate_values(self.values)
        if not isinstance(self.terrain, TerrainRules):
            raise ValueError("Invalid terrain rules")

    @property
    def values(self):
        overrides = dict(self.overrides)
        return tuple(overrides.get(k, v) for k, v in zip(FIELDS, DEFAULTS[self.game]))

    def updated(self, game, values):
        values = validate_values(tuple(values))
        return GameProfile(game, tuple((k, v) for k, v, d in zip(FIELDS, values, DEFAULTS[game]) if v != d), self.terrain)

    def to_dict(self):
        return dict(game=self.game, overrides=dict(self.overrides), terrain=self.terrain.to_dict())

    @classmethod
    def from_dict(cls, obj):
        return cls(obj['game'], tuple(sorted(obj.get('overrides', {}).items())),
                   TerrainRules.from_dict(obj['terrain']) if 'terrain' in obj else TerrainRules())

    @property
    def adaptations(self):
        rows = []
        if self.game != 'dday':
            rows += ['Movement and combat use D-Day algorithms with the configured terrain constants; supply and scenario-specific engine scripts remain D-Day behavior.']
        if self.game.startswith('v4v'):
            rows += ['Victory ratios use D-Day defaults; original V4V thresholds are not verified.']
        if self.game == 'operation_crusader':
            rows += ['Crusader winter arithmetic is not yet verified; the default is D-Day winter behavior.']
        if self.values[0]:
            rows += ['Earlier winter arithmetic is adapted to D-Day thousandths; floating point rounding can differ.']
        return rows


def encode_rules(profile):
    values = validate_values(profile.values)
    return struct.pack('<8s13I4s', MAGIC, *values, sum(values), b'RUL1')


def decode_rules(data):
    if len(data) != SIZE:
        raise ValueError('Invalid DOS game profile length')
    magic, *tail = struct.unpack('<8s13I4s', data)
    values, checksum, end = tail[:12], tail[12], tail[13]
    if magic != MAGIC or end != b'RUL1' or sum(values) != checksum:
        raise ValueError('Invalid DOS game profile checksum or version')
    validate_values(values)
    return GameProfile().updated('dday', values)


@dataclass(frozen=True)
class ScenarioDocument:
    """Authoring metadata independent of the editable DOS record projection.

    Source data is immutable provenance, never a competing copy of current
    edits. Keep it when a translation cannot represent a source field yet.
    The SCN remains the current editable projection; DOS export omits provenance.
    """
    profile: GameProfile = field(default_factory=GameProfile)
    source_game: str = 'dday'
    source_name: str = ''
    source_data: bytes = field(default=b'', repr=False)  # zlib, exact original SCN
    battleset: bytes = field(default=b'', repr=False)   # V4V BTL payload

    def with_profile(self, profile):
        return replace(self, profile=profile)

    def to_dict(self):
        result = dict(version=1, profile=self.profile.to_dict(), source_game=self.source_game,
                      source_name=self.source_name)
        if self.source_data:
            result.update(source_zlib=base64.b64encode(self.source_data).decode('ascii'),
                          source_sha256=hashlib.sha256(self.original_bytes()).hexdigest(),
                          battleset=base64.b64encode(self.battleset).decode('ascii'))
        return result

    def source_blocks(self):
        """Read preserved source tables without requiring the installed game."""
        if not self.source_data:
            return {}
        data = self.original_bytes()
        if self.source_game.startswith('v4v'):
            from lib.v4v_reader import read_blocks
            return {str(i): block for i, block in enumerate(read_blocks(data))}
        from lib.waw_reader import WawScenario
        if self.source_game != 'dday':
            return dict(WawScenario.from_bytes(data).blocks)
        from lib.unit_roster import UnitRoster
        return dict(UnitRoster(data).blocks)

    def original_bytes(self):
        if not self.source_data:
            return b''
        unpacker = zlib.decompressobj()
        data = unpacker.decompress(self.source_data, 8*1024*1024+1)
        if len(data) > 8*1024*1024 or not unpacker.eof or unpacker.unused_data:
            raise ValueError('Invalid or oversized preserved source scenario')
        return data

    @classmethod
    def from_dict(cls, obj):
        if obj.get('version') != 1 or obj.get('source_game') not in GAMES:
            raise ValueError('Unsupported scenario authoring model')
        result = cls(GameProfile.from_dict(obj['profile']), obj['source_game'], obj.get('source_name', ''),
                     base64.b64decode(obj.get('source_zlib', ''), validate=True),
                     base64.b64decode(obj.get('battleset', ''), validate=True))
        if result.source_data and hashlib.sha256(result.original_bytes()).hexdigest() != obj.get('source_sha256'):
            raise ValueError('Preserved scenario source checksum mismatch')
        if result.battleset and len(result.battleset) != 0x6ee:
            raise ValueError('Invalid preserved V4V battleset')
        return result

    @classmethod
    def import_source(cls, path):
        from pathlib import Path
        from lib.scenario_import import source_game
        game = source_game(path)
        battleset = b''
        if game == 'v4v':
            from lib.v4v_reader import VictoryScenario
            source = VictoryScenario.read(path)
            battleset = source.battleset
            if source.blocks[0][1] == 1:
                game = 'v4v_velikiye'
        return cls(GameProfile(game), game, Path(path).name,
                   zlib.compress(Path(path).read_bytes(), 9), battleset)


def load_document(path):
    from lib.terrain_artwork import artwork_path
    sidecar = artwork_path(path)
    if sidecar.exists():
        payload = json.loads(sidecar.read_bytes())
        if 'document' in payload:
            return ScenarioDocument.from_dict(payload['document'])
        # Existing conversions keep their current D-Day behavior until the user
        # explicitly selects source defaults. Do not reinterpret older saves.
        report = payload.get('conversion') or {}
        game = report.get('source_game', 'v4v' if report.get('theater') else 'dday')
        return ScenarioDocument(source_game=game, source_name=report.get('source', ''))
    from pathlib import Path
    path = Path(path)
    if path.exists():
        from lib.scenario_library import library_metadata
        with path.open('rb') as stream:
            stream.seek(max(0, path.stat().st_size-64))
            metadata = library_metadata(stream.read())
        if metadata and metadata.get('require_profile'):
            resource = path.with_suffix('.REZ')
            with resource.open('rb') as stream:
                stream.seek(-SIZE, 2)
                profile = decode_rules(stream.read())
                if metadata.get('require_terrain'):
                    stream.seek(-SIZE-TERRAIN_SIZE, 2)
                    profile = replace(profile, terrain=decode_terrain_rules(stream.read(TERRAIN_SIZE)))
            return ScenarioDocument(profile)
    return ScenarioDocument()


def ground_step(profile, code, temperature, snow, ice, wetness, scale=1):
    """Reference for the native patched routine, using thousandths and truncation."""
    model, _, _, light, heavy, rain, downpour, melt, drying, divisor, threshold, step = profile.values
    factor = scale if model < 2 else 1
    snow_delta = wet_delta = 0
    if temperature <= 32:
        snow_delta = light if code == 3 else heavy if code == 4 else 0
    else:
        if snow > 0 and temperature > 35:
            snow_delta = -(temperature-35)*melt
        wet_delta = (rain if code == 3 else downpour if code == 4 else
                     ((code+(temperature-32)//10-4) if model else (-code-(temperature-32)//10))*drying)
        if not model:
            wet_delta -= int(snow_delta/10)
    if model:
        delta = round((32-temperature)*1000000/((ice+1000)*divisor))
        if model == 3 and ice >= threshold and ice+delta < threshold:
            delta = 0
        if ice < threshold <= ice+delta:
            ice += step
        elif ice >= threshold > ice+delta:
            ice -= step
        ice = max(0, ice+delta*factor)
    return max(0, snow+snow_delta*factor), ice, max(0, wetness+wet_delta*factor)
