"""Bounded map edits for the D-Day scenario format."""
import struct

from lib.terrain_reader import _read_block
from lib.terrain_catalog import DDAY_TERRAIN_BY_CODE
from lib.unit_reader import prepare_unit_changes, arrival_time_from_form


DIRECTIONS = ('W', 'NW', 'NE', 'E', 'SE', 'SW')
# The value selects a two-bit code in paired six-bit masks, not adjacent bits.
NETWORK_FEATURES = {
    'Dirt road': (20, 1), 'Paved road': (20, 2), 'Railway': (20, 3),
    'Stream': (8, 1), 'River': (8, 2),
    'Uphill slope': (8, 3), 'Downhill slope': (8, 3),
}
MAP_FEATURES = (*NETWORK_FEATURES, 'Hilltop')


def hex_neighbor(cell, direction):
    """CalcHexOffs: even rows are shifted half a column to the right."""
    if not isinstance(direction, int) or not 0 <= direction < 6:
        raise ValueError('Choose one of the six hex directions.')
    x, y = cell
    dx, dy = ((-1, 0), (-(y % 2), -1), (1 - y % 2, -1),
              (1, 0), (1 - y % 2, 1), (-(y % 2), 1))[direction]
    return x + dx, y + dy


def connection_value(record, shift, direction):
    return ((record >> (shift + direction)) & 1) | (((record >> (shift + 6 + direction)) & 1) << 1)


def _set_connection(record, shift, direction, value):
    mask = (1 << (shift + direction)) | (1 << (shift + 6 + direction))
    return ((record & ~mask) | ((value & 1) << (shift + direction))
            | ((value >> 1) << (shift + 6 + direction)))


def _read_terrain_map(data):
    header, offset = _read_block(data, 0)
    calendar, offset = _read_block(data, offset)
    if len(header) != 0x1230 or len(calendar) != 42:
        raise ValueError('Unsupported scenario layout')
    width = struct.unpack_from('<h', header, 0x22a)[0] + 1
    height = struct.unpack_from('<h', header, 0x228)[0] + 1
    map_start = offset
    indexes, offset = _read_block(data, offset)
    records, tail = _read_block(data, offset)
    if width <= 0 or height <= 0 or len(indexes) != width * height * 2 or not records or len(records) % 4:
        raise ValueError('Invalid terrain map')
    if any(index * 4 >= len(records) for (index,) in struct.iter_unpack('<H', indexes)):
        raise ValueError('Invalid shared terrain record reference')
    return header, width, height, map_start, tail, indexes, records


def _validate_cell(cell, width, height):
    x, y = cell
    if not isinstance(x, int) or not isinstance(y, int) or not (0 <= x < width and 0 <= y < height):
        raise ValueError('Choose a hex inside the map.')


def _write_hex_records(data, parsed, replacements):
    """Copy shared records on write; retain every unrelated block byte for byte."""
    _header, width, _height, map_start, tail, indexes, records = parsed
    indexes, records = bytearray(indexes), bytearray(records)
    lookup = {}
    for start in range(0, len(records), 4):
        lookup.setdefault(bytes(records[start:start + 4]), start // 4)
    for (x, y), word in replacements.items():
        slot = (y * width + x) * 2
        index = struct.unpack_from('<H', indexes, slot)[0]
        start = index * 4
        replacement = struct.pack('<I', word)
        if replacement == records[start:start + 4]:
            continue
        if replacement not in lookup:
            new_index = len(records) // 4
            if new_index > 65535:
                raise ValueError('The game has reached its shared terrain record limit.')
            lookup[replacement] = new_index
            records += replacement
        struct.pack_into('<H', indexes, slot, lookup[replacement])
    return (data[:map_start] + struct.pack('<I', len(indexes)) + indexes
            + struct.pack('<I', len(records)) + records + data[tail:])


def _record_at(parsed, cell):
    _header, width, _height, _start, _tail, indexes, records = parsed
    x, y = cell
    index = struct.unpack_from('<H', indexes, (y * width + x) * 2)[0]
    return struct.unpack_from('<I', records, index * 4)[0]


def paint_terrain(data, cells, terrain, variant=0):
    """Change base terrain, preserving networks, edge artwork, hilltops and OOB."""
    if not isinstance(terrain, int) or terrain not in DDAY_TERRAIN_BY_CODE:
        raise ValueError('Choose a normal terrain type from Bocage through Invasion Beach.')
    if not isinstance(variant, int) or variant not in DDAY_TERRAIN_BY_CODE[terrain].variants:
        raise ValueError('Terrain variants must be between 0 and 5.')
    parsed = _read_terrain_map(data)
    replacements = {}
    for cell in sorted(set(cells)):
        _validate_cell(cell, parsed[1], parsed[2])
        replacements[cell] = (_record_at(parsed, cell) & ~255) | terrain | (variant << 4)
    return _write_hex_records(data, parsed, replacements)


def edit_map_feature(data, cell, feature, direction=None, remove=False):
    """Edit a connection or hilltop using the game's native map fields.

    Roads/railways and streams/rivers have matching connections on both hexes.
    A slope is stored ONLY on the low side, pointing toward higher ground.
    Replacing a feature clears the same paired-mask slot on the other side;
    roads and water/slope slots remain independent. Erasing removes only the
    requested feature (either orientation for slopes), leaving other types.
    """
    if feature not in MAP_FEATURES:
        raise ValueError('Choose a map feature.')
    parsed = _read_terrain_map(data)
    header, width, height = parsed[:3]
    _validate_cell(cell, width, height)
    if feature == 'Hilltop':
        return _edit_hilltop(data, header, cell, remove)
    neighbor = hex_neighbor(cell, direction)
    opposite = (direction + 3) % 6
    inside = 0 <= neighbor[0] < width and 0 <= neighbor[1] < height
    if feature == 'Downhill slope' and not inside and not remove:
        raise ValueError('A downhill slope needs a neighboring hex inside the map.')
    shift, value = NETWORK_FEATURES[feature]
    replacements = {}
    slope = shift == 8 and value == 3
    for target, heading in ((cell, direction), (neighbor, opposite)):
        if target == neighbor and not inside:
            continue
        word = _record_at(parsed, target)
        old = connection_value(word, shift, heading)
        if remove:
            if old != value:
                continue
            new = 0
        elif slope:
            low_side = cell if feature == 'Uphill slope' else neighbor
            new = 3 if target == low_side else 0
        else:
            new = value
        replacements[target] = _set_connection(word, shift, heading, new)
    return _write_hex_records(data, parsed, replacements)


def _edit_hilltop(data, header, cell, remove):
    count = struct.unpack_from('<h', header, 0x2a2)[0]
    if not 0 <= count <= 30:
        raise ValueError('Invalid hilltop count in this scenario.')
    cells = [(struct.unpack_from('<h', header, 0x2a4 + 2 * i)[0],
              struct.unpack_from('<h', header, 0x2e0 + 2 * i)[0]) for i in range(count)]
    if remove:
        updated = [c for c in cells if c != cell]
    elif cell in cells:
        return data
    elif count == 30:
        raise ValueError('D-Day supports at most 30 hilltops. Remove one before adding another.')
    else:
        updated = cells + [cell]
    if updated == cells:
        return data
    result = bytearray(data)
    struct.pack_into('<h', result, 4 + 0x2a2, len(updated))
    for i in range(max(count, len(updated))):
        x, y = updated[i] if i < len(updated) else (0, 0)
        struct.pack_into('<h', result, 4 + 0x2a4 + 2 * i, x)
        struct.pack_into('<h', result, 4 + 0x2e0 + 2 * i, y)
    return bytes(result)


def hex_feature_labels(layers, cell):
    """Describe stored features, including downhill slopes on the other hex."""
    labels = []
    word = layers.records.get(cell, 0)
    for direction, name in enumerate(DIRECTIONS):
        water = connection_value(word, 8, direction)
        road = connection_value(word, 20, direction)
        features = []
        if road:
            features.append(('', 'Dirt road', 'Paved road', 'Railway')[road])
        if water:
            features.append(('', 'Stream', 'River', 'Uphill slope')[water])
        neighbor = layers.records.get(hex_neighbor(cell, direction), 0)
        if connection_value(neighbor, 8, (direction + 3) % 6) == 3:
            features.append('Downhill slope')
        if features:
            labels.append(f'{name}: ' + ', '.join(features))
    if cell in layers.hilltops:
        labels.append('Hilltop')
    return labels


def prepare_map_unit_changes(unit, cell, deployment='Deploy at start'):
    """Move an existing ground unit or retain it in the OOB without deployment."""
    if unit.get('deleted'):
        raise ValueError('Restore this unit on the Units page before placing it.')
    if unit['unit_class'] in (5, 6):
        raise ValueError('Aircraft and naval support operate off map. Choose a ground unit.')
    record = bytes.fromhex(unit['raw_data'])
    # Relocating a saved route or one member of a mounted group also requires
    # editing those linked structures; do not leave them pointing to old hexes.
    if record[0x86] or record[0x91]:
        raise ValueError('Clear the unit’s route under Units → Orders and dismount it under Units → Transport first, '
                         'or use a formation move to relocate linked units together.')
    if cell is None:
        values = {'x': -1, 'y': -1, 'arrival_time': -1}
    else:
        x, y = cell
        if not (0 <= x < unit['map_width']-1 and 0 <= y < unit['map_height']-1):
            raise ValueError('Choose a playable hex. The last row and column are the game’s boundary padding.')
        values = {'x': x, 'y': y}
        if deployment == 'Deploy at start':
            values['arrival_time'] = arrival_time_from_form(unit, 'At start', '')
        elif deployment == 'Keep arrival turn':
            if unit['arrival_time'] == -1:
                raise ValueError('This unit is inactive. Choose Deploy at start or schedule it on the Units page.')
        else:
            raise ValueError('Choose Deploy at start or Keep arrival turn.')
    return prepare_unit_changes(unit, values)
