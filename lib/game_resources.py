"""Read the games' resource forks without extracting or modifying the originals."""
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
import struct


GAME_ROOT = Path(__file__).resolve().parents[1] / 'game'
if (GAME_ROOT / 'waw' / 'dday').is_dir():
    GAME_ROOT /= 'waw'
GAME_NAMES = {'dday': 'D-Day', 'stalingrad': 'Stalingrad',
              'operation_crusader': 'Operation Crusader'}


@dataclass(frozen=True)
class Resource:
    kind: str
    number: int
    offset: int
    data: bytes


def read_resources(data):
    """Return bounded resource payloads; offsets allow same-size replacements."""
    def within(offset, length, start, end):
        if length < 0 or offset < start or offset + length > end:
            raise ValueError('Truncated or invalid resource fork')

    within(0, 16, 0, len(data))
    data_start, map_start, data_size, map_size = struct.unpack_from('>4I', data)
    within(data_start, data_size, 16, len(data))
    within(map_start, map_size, 16, len(data))
    map_end, data_end = map_start + map_size, data_start + data_size
    within(map_start, 28, map_start, map_end)
    types = map_start + struct.unpack_from('>H', data, map_start + 24)[0]
    within(types, 2, map_start, map_end)
    count = struct.unpack_from('>H', data, types)[0] + 1
    within(types + 2, count * 8, map_start, map_end)
    resources = {}
    for pos in range(types + 2, types + 2 + count * 8, 8):
        kind = data[pos:pos + 4].decode('latin1')
        number, refs = struct.unpack_from('>HH', data, pos + 4)
        refs += types
        within(refs, (number + 1) * 12, map_start, map_end)
        for ref in range(refs, refs + (number + 1) * 12, 12):
            resource_id = struct.unpack_from('>H', data, ref)[0]
            offset = data_start + int.from_bytes(data[ref + 5:ref + 8], 'big')
            within(offset, 4, data_start, data_end)
            size = struct.unpack_from('>I', data, offset)[0]
            offset += 4
            within(offset, size, data_start, data_end)
            key = (kind, resource_id)
            if key in resources:
                raise ValueError(f'Duplicate resource {key}')
            resources[key] = Resource(kind, resource_id, offset, bytes(data[offset:offset + size]))
    return resources


@lru_cache(maxsize=3)
def game_resources(game='dday'):
    if game not in GAME_NAMES:
        raise ValueError(f'Unknown game: {game}')
    path = GAME_ROOT / game / 'DATA' / 'PCWATW.REZ'
    return read_resources(path.read_bytes())


def available_games():
    return tuple(game for game in GAME_NAMES
                 if (GAME_ROOT / game / 'DATA' / 'PCWATW.REZ').is_file())


def add_resources(data, additions):
    """Append resources and rebuild the map, preserving native names/attributes.

    Existing payloads keep their offsets; handles in the on-disk map are zero.
    This is also accepted by the game's DOS resource manager (24-bit offsets).
    """
    if not additions:
        return bytes(data)
    existing = read_resources(data)
    if set(existing) & set(additions):
        raise ValueError('An added resource already exists')
    start, old_map, size, _ = struct.unpack_from('>4I', data)
    types = old_map + struct.unpack_from('>H', data, old_map+24)[0]
    names = old_map + struct.unpack_from('>H', data, old_map+26)[0]
    groups = {}
    name_data = bytearray()
    for p in range(types+2, types+2+8*(struct.unpack_from('>H', data, types)[0]+1), 8):
        kind = data[p:p+4].decode('latin1')
        count, refs = struct.unpack_from('>HH', data, p+4)
        rows = groups.setdefault(kind, [])
        for q in range(types+refs, types+refs+(count+1)*12, 12):
            ref = bytearray(data[q:q+12])
            offset = struct.unpack_from('>H', ref, 2)[0]
            if offset != 0xffff:
                pos = names+offset
                end = pos+1+data[pos]
                if end > len(data):
                    raise ValueError('Truncated resource name')
                struct.pack_into('>H', ref, 2, len(name_data))
                name_data += data[pos:end]
            ref[8:12] = bytes(4)
            rows.append(bytes(ref))
    payload = bytearray(data[:start+size])
    for (kind, number), value in sorted(additions.items()):
        if len(kind.encode('latin1')) != 4 or not 0 <= number <= 32767:
            raise ValueError('Invalid resource type or ID')
        offset = len(payload)-start
        if offset > 0xffffff:
            raise ValueError('Resource fork exceeds DOS offset limits')
        payload += struct.pack('>I', len(value)) + value
        groups.setdefault(kind, []).append(struct.pack('>HHB', number, 0xffff, 0) + offset.to_bytes(3, 'big') + bytes(4))
    type_data = bytearray(struct.pack('>H', len(groups)-1))
    refs = bytearray()
    for kind, rows in groups.items():
        offset = 2+8*len(groups)+len(refs)
        type_data += kind.encode('latin1') + struct.pack('>HH', len(rows)-1, offset)
        refs += b''.join(rows)
    name_offset = 28+len(type_data)+len(refs)
    if name_offset+len(name_data) > 65535:
        raise ValueError('Resource map exceeds DOS limits')
    resource_map = bytearray(28) + type_data + refs + name_data
    resource_map[22:24] = data[old_map+22:old_map+24]
    struct.pack_into('>HH', resource_map, 24, 28, name_offset)
    header = struct.pack('>4I', start, len(payload), len(payload)-start, len(resource_map))
    payload[:16] = resource_map[:16] = header
    result = bytes(payload+resource_map)
    read_resources(result)
    return result
