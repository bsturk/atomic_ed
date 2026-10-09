"""Map authoring operations on native SCN blocks, committed atomically by the UI."""
import struct
from collections import deque

from lib.unit_roster import UnitRoster, short, put_short
from lib.terrain_reader import read_place_names
from lib.map_editor import (hex_neighbor, _validate_cell, _read_terrain_map,
                            _record_at, _write_hex_records, _set_connection,
                            connection_value, paint_terrain)
from lib.scenario_rules import objectives
from lib.scenario_conditions import supply_groups
from lib.battle_plans import battle_plans

EDGE_FAMILIES = ('Water', 'Bocage', 'Swamp', 'Clear grass', 'Beach')
NO_EDGE = 0xfde8

# PICT 200's surfaces, verified against PICT 128 and native scenario edges.
# Forest has no dedicated fringe sprite; adjacent ground blends into it.
EDGE_SURFACES = {0: 1, 1: 3, 2: None, 3: 2, 4: 3, 5: 0, 6: 4,
                 7: 3, 8: 4, 9: None, 10: None, 11: 3, 12: 3, 13: 4}
# Editor policy, not an engine rule: choose one side of each boundary, with
# water spilling onto shore and vegetation/grass spilling onto sand or woods.
EDGE_PRIORITY = {None: -1, 4: 0, 3: 1, 1: 2, 2: 3, 0: 4}


def dimensions(roster):
    return short(roster.header, 0x22a)+1, short(roster.header, 0x228)+1


def rectangle(first, last):
    return [(x, y) for y in range(min(first[1], last[1]), max(first[1], last[1])+1)
            for x in range(min(first[0], last[0]), max(first[0], last[0])+1)]


def _write_places(header, places):
    if len(places) > 50:
        raise ValueError('D-Day supports at most 50 place names.')
    for i in range(50):
        start = 0xbe0+i*32
        if i < len(places):
            header[start:start+32] = places[i]
        else:
            header[start:start+32] = struct.pack('<2h', -1, -1)+bytes(26)+bytes((12, ord('V')))
    header[0x122a] = len(places)


def edit_place_name(data, index, values=None):
    roster = UnitRoster(data)
    places = read_place_names(roster.header)
    if index is not None and not 0 <= index < len(places):
        raise ValueError('Select a place name.')
    records = [bytes(roster.header[0xbe0+i*32:0xc00+i*32]) for i in range(len(places))]
    if values is None:
        if index is None:
            raise ValueError('Select a place name to remove.')
        del records[index]
    else:
        try:
            name = values['name'].strip().encode('cp437')
        except UnicodeEncodeError as exc:
            raise ValueError('Use DOS characters in place names.') from exc
        if not 1 <= len(name) <= 25 or any(c < 32 or c == 127 for c in name):
            raise ValueError('Place names need 1–25 printable DOS characters.')
        x, y, size = (int(values[k]) for k in ('x', 'y', 'size'))
        _validate_cell((x, y), *dimensions(roster))
        style = values['style']
        if not 10 <= size <= 24 or style not in ('V', 'R', 'I'):
            raise ValueError('Choose a size from 10 to 24 and a label style V, R or I.')
        record = struct.pack('<2h', x, y)+name.ljust(26, b'\0')+bytes((size, ord(style)))
        if index is None:
            records.append(record)
        else:
            if records[index] == record:
                return data
            records[index] = record
    _write_places(roster.header, records)
    return roster.to_bytes()


def _paint_ownership(roster, owners):
    width, height = dimensions(roster)
    if len(roster.blocks['zoc']) != width*height*4:
        raise ValueError('Invalid ownership map.')
    for cell, owner in owners.items():
        _validate_cell(cell, width, height)
        if owner not in (0, 1):
            raise ValueError('Choose Allied or Axis ownership.')
    current = struct.unpack_from('<i', roster.blocks['calendar'], 12)[0]
    for side in (0, 1):
        for record in roster.records[side][:roster.count(0x240, side)]:
            cell = struct.unpack_from('<2h', record, 0x58)
            arrival = struct.unpack_from('<i', record, 8)[0]
            if cell in owners and owners[cell] != side and arrival != -1 and arrival < current:
                raise ValueError(f'Ownership at {cell} conflicts with a deployed {("Allied", "Axis")[side]} unit.')
    for (x, y), owner in owners.items():
        offset = (y*width+x)*4
        word = struct.unpack_from('<I', roster.blocks['zoc'], offset)[0]
        struct.pack_into('<I', roster.blocks['zoc'], offset, (word & ~0x10000) | owner << 16)
    # Keep initial victory control consistent, just as edit_objective does.
    block = roster.blocks['vicloc']
    for i in range(0, len(block), 48):
        cell = struct.unpack_from('<2h', block, i+8)
        if cell in owners and block[i+17] != owners[cell]:
            block[i+17:i+21] = bytes([owners[cell]])*4


def paint_ownership(data, cells, owner):
    roster = UnitRoster(data)
    _paint_ownership(roster, dict.fromkeys(cells, int(owner)))
    return roster.to_bytes()


def _edges(roster):
    width, height = dimensions(roster)
    indexes, records = roster.blocks['hedgelist'], roster.blocks['hedges']
    if len(indexes) != width*height*2 or len(records) % 8:
        raise ValueError('Invalid cosmetic edge map.')
    result = {}
    for i, (index,) in enumerate(struct.iter_unpack('<H', indexes)):
        if index == NO_EDGE:
            result[i % width, i // width] = bytes(8)
        elif index*8+8 <= len(records):
            result[i % width, i // width] = bytes(records[index*8:index*8+8])
        else:
            raise ValueError('Invalid cosmetic edge reference.')
    return result


def _write_edges(roster, replacements):
    width, height = dimensions(roster)
    records, indexes = roster.blocks['hedges'], roster.blocks['hedgelist']
    lookup = {bytes(records[i:i+8]): i//8 for i in range(0, len(records), 8) if i//8 != NO_EDGE}
    for cell, record in replacements.items():
        _validate_cell(cell, width, height)
        if not short(record, 0) & 63:
            index = NO_EDGE
        else:
            if record not in lookup:
                index = len(records)//8
                if index == NO_EDGE:
                    records.extend(bytes(8))
                    index += 1
                if index > 65535:
                    raise ValueError('The shared edge artwork table is full.')
                lookup[record] = index
                records.extend(record)
            index = lookup[record]
        struct.pack_into('<H', indexes, (cell[1]*width+cell[0])*2, index)


def edit_cosmetic_edge(data, cell, direction, family=0, variant=0, remove=False):
    if direction not in range(6) or family not in range(5) or variant not in range(3):
        raise ValueError('Choose a direction, edge artwork and variant (0–2).')
    roster = UnitRoster(data)
    _validate_cell(cell, *dimensions(roster))
    old = _edges(roster)[cell]
    record = bytearray(old)
    mask = short(record, 0)
    put_short(record, 0, mask & ~(1 << direction) if remove else mask | (1 << direction))
    record[2+direction] = 0 if remove else family*16+variant
    if record == old or (remove and not mask & 1 << direction):
        return data
    _write_edges(roster, {cell: bytes(record)})
    return roster.to_bytes()


def _blend_record(families):
    """Pack clockwise runs into native one-, two- and three-side sprites.

    A sprite at direction d with variant v covers d, d-1, ... d-v. These
    are different spans, not random textures. Split long runs at three sides.
    """
    start = next((d for d in range(6) if families[d] != families[(d-1) % 6]), 0)
    record = bytearray(8)
    mask, offset = 0, 0
    while offset < 6:
        direction = (start+offset) % 6
        family = families[direction]
        length = 1
        while (length < 3 and offset+length < 6
               and families[(direction+length) % 6] == family):
            length += 1
        if family is not None:
            end = (direction+length-1) % 6
            mask |= 1 << end
            record[2+end] = family*16+length-1
        offset += length
    struct.pack_into('<H', record, 0, mask)
    return bytes(record)


def blend_terrain_edges(data, cells=None, *, exclude_slots=()):
    """Rebuild cosmetic edges for the map, or selected cells and their neighbors.

    Overwrites manual edges in that area. Imported/custom slots can be excluded;
    their hexes and immediate neighbors retain their complete original records.
    Unknown terrain codes are likewise preserved. Changes touch only HEdges
    and HEdgeList, and are deterministic and idempotent.
    """
    parsed = _read_terrain_map(data)
    width, height = parsed[1:3]
    slots = {c: (_record_at(parsed, c) & 15, (_record_at(parsed, c) >> 4) & 15)
             for c in rectangle((0, 0), (width-1, height-1))}
    targets = set(slots) if cells is None else set(cells)
    for cell in targets:
        _validate_cell(cell, width, height)
    targets |= {hex_neighbor(c, d) for c in list(targets) for d in range(6)} & slots.keys()
    excluded = set(exclude_slots)
    protected = {c for c, slot in slots.items() if slot in excluded or slot[0] not in EDGE_SURFACES}
    protected |= {hex_neighbor(c, d) for c in list(protected) for d in range(6)}
    roster = UnitRoster(data)
    existing = _edges(roster)
    replacements = {}
    for cell in sorted(targets-protected):
        surface = EDGE_SURFACES[slots[cell][0]]
        families = []
        for direction in range(6):
            neighbor = slots.get(hex_neighbor(cell, direction))
            family = EDGE_SURFACES.get(neighbor[0]) if neighbor else None
            families.append(family if EDGE_PRIORITY[family] > EDGE_PRIORITY[surface] else None)
        record = _blend_record(families)
        old = existing[cell]
        # Ignore unused style bytes on empty records; avoid rewriting aliases
        # or growing the table when the rendered result is already identical.
        mask = struct.unpack_from('<H', record)[0]
        if (mask != struct.unpack_from('<H', old)[0]
                or any(record[2+d] != old[2+d] for d in range(6) if mask & 1 << d)):
            replacements[cell] = record
    if not replacements:
        return data
    _write_edges(roster, replacements)
    return roster.to_bytes()


def paint_blended_terrain(data, cells, terrain, variant=0, *, blend=False, exclude_slots=()):
    cells = tuple(cells)
    changed = paint_terrain(data, cells, terrain, variant)
    return blend_terrain_edges(changed, cells, exclude_slots=exclude_slots) if blend else changed


def flood_cells(data, start, layer='terrain'):
    parsed = _read_terrain_map(data)
    width, height = parsed[1:3]
    _validate_cell(start, width, height)
    if layer == 'terrain':
        values = {c: _record_at(parsed, c) & 15 for c in rectangle((0, 0), (width-1, height-1))}
    elif layer == 'ownership':
        block = UnitRoster(data).blocks['zoc']
        if len(block) != width*height*4:
            raise ValueError('Invalid ownership map.')
        values = {(i % width, i // width): (v >> 16) & 1 for i, (v,) in enumerate(struct.iter_unpack('<I', block))}
    else:
        raise ValueError('Choose terrain or ownership fill.')
    seen, queue = {start}, deque([start])
    while queue:
        for d in range(6):
            neighbor = hex_neighbor(queue[0], d)
            if neighbor not in seen and values.get(neighbor) == values[start]:
                seen.add(neighbor)
                queue.append(neighbor)
        queue.popleft()
    return seen


def flood_terrain(data, start, terrain, variant=0, *, blend=False, exclude_slots=()):
    return paint_blended_terrain(data, flood_cells(data, start), terrain, variant,
                                 blend=blend, exclude_slots=exclude_slots)


def flood_ownership(data, start, owner):
    return paint_ownership(data, flood_cells(data, start, 'ownership'), owner)


def _hills(header):
    count = short(header, 0x2a2)
    if not 0 <= count <= 30:
        raise ValueError('Invalid hilltop count.')
    return [(short(header, 0x2a4+i*2), short(header, 0x2e0+i*2)) for i in range(count)]


def _write_hills(header, hills):
    if len(hills) > 30:
        raise ValueError('D-Day supports at most 30 hilltops.')
    put_short(header, 0x2a2, len(hills))
    for i in range(30):
        x, y = hills[i] if i < len(hills) else (0, 0)
        put_short(header, 0x2a4+i*2, x)
        put_short(header, 0x2e0+i*2, y)


def _axial(cell):
    x, y = cell
    return x-(y+1)//2, y


def translate_cell(cell, origin, destination):
    """Translate in hex space, preserving adjacency across odd/even rows."""
    q, r = _axial(cell)
    oq, oy = _axial(origin)
    dq, dy = _axial(destination)
    y = r-oy+dy
    return q-oq+dq+(y+1)//2, y


def copy_region(data, first, last):
    parsed = _read_terrain_map(data)
    _validate_cell(first, *parsed[1:3])
    _validate_cell(last, *parsed[1:3])
    roster = UnitRoster(data)
    edges, hills = _edges(roster), set(_hills(roster.header))
    cells = rectangle(first, last)
    selected = set(cells)
    from lib.unit_reader import decode_record
    counts = dict(units=sum(struct.unpack_from('<2h', u, 0x58) in selected and not decode_record(u)['deleted']
                            for side in (0, 1) for u in roster.records[side][:roster.count(0x240, side)]),
                  objectives=sum((o['x'], o['y']) in selected for o in objectives(roster)),
                  places=sum((p['x'], p['y']) in selected for p in read_place_names(roster.header)))
    width = parsed[1]
    downhill = set()
    for cell in cells:
        for direction in range(6):
            neighbor = hex_neighbor(cell, direction)
            if (neighbor not in selected and 0 <= neighbor[0] < width and 0 <= neighbor[1] < parsed[2]
                    and connection_value(_record_at(parsed, neighbor), 8, (direction+3) % 6) == 3):
                downhill.add((cell, direction))
    return dict(origin=(min(first[0], last[0]), min(first[1], last[1])),
                downhill=downhill, document=bytes(data), counts=counts,
                cells={c: (_record_at(parsed, c), edges[c], c in hills,
                           (struct.unpack_from('<I', roster.blocks['zoc'], (c[1]*width+c[0])*4)[0] >> 16) & 1)
                       for c in cells})


def paste_region(data, region, destination, ownership=False, units=False, objectives=False, places=False):
    parsed = _read_terrain_map(data)
    width, height = parsed[1:3]
    _validate_cell(destination, width, height)
    targets = {translate_cell(c, region['origin'], destination): values for c, values in region['cells'].items()}
    for c in targets:
        _validate_cell(c, width, height)  # No partial paste if the stamp crosses the border.
    replacements = {c: values[0] for c, values in targets.items()}
    downhill = {(translate_cell(c, region['origin'], destination), d) for c, d in region['downhill']}
    # At stamp boundaries extend/erase the opposite network endpoint; slopes
    # remain one-sided. Interior connections were already translated together.
    for cell, (record, _edge, _hill, _owner) in targets.items():
        for d in range(6):
            neighbor = hex_neighbor(cell, d)
            if neighbor in targets or not (0 <= neighbor[0] < width and 0 <= neighbor[1] < height):
                continue
            word = replacements.get(neighbor, _record_at(parsed, neighbor))
            for shift in (8, 20):
                value = connection_value(record, shift, d)
                if shift == 8:
                    value = 0 if value == 3 else 3 if value == 0 and (cell, d) in downhill else value
                word = _set_connection(word, shift, (d+3) % 6, value)
            replacements[neighbor] = word
    changed = _write_hex_records(data, parsed, replacements)
    roster = UnitRoster(changed)
    _write_edges(roster, {c: values[1] for c, values in targets.items()})
    hills = [c for c in _hills(roster.header) if c not in targets]
    hills.extend(c for c, values in targets.items() if values[2])
    if hills != _hills(roster.header):
        _write_hills(roster.header, hills)
    if ownership:
        _paint_ownership(roster, {c: values[3] for c, values in targets.items()})
    from lib.bulk_edit import paste_scenario_items
    return paste_scenario_items(roster.to_bytes(), region, destination,
                                units=units, objectives=objectives, places=places)


def resize_conflicts(roster, width, height):
    """Report references that a southeast crop would push out of bounds."""
    old_w, old_h = dimensions(roster)
    conflicts = []
    def check(name, x, y, padding=False):
        inset = 0 if padding else 1
        # Ignore existing off-map/sentinel values; never introduce a new one.
        if 0 <= x < old_w-inset and 0 <= y < old_h-inset and not (x < width-inset and y < height-inset):
            conflicts.append(f'{name} at ({x}, {y})')
    for side in (0, 1):
        title = ('Allied', 'Axis')[side]
        for i, record in enumerate(roster.records[side][:roster.count(0x240, side)]):
            if (struct.unpack_from('<i', record, 8)[0] == -1 and short(record, 0x64) == 0
                    and struct.unpack_from('<2h', record, 0x58) == (-1, -1)):
                continue
            name = record[0x92:0xac].split(b'\0')[0].decode('cp437').strip()
            check(f'{title} unit {i} {name}', *struct.unpack_from('<2h', record, 0x58))
            # Unit destination / fallback target; routes use additional packed hexes.
            for pos in (0x5c, 0x60):
                check(f'{title} unit {i} target', *struct.unpack_from('<2h', record, pos))
        for i, group in enumerate(supply_groups(roster, side)):
            for x, y, _ in group['entries']:
                check(f'{title} supply group {i+1}', x, y)
        for i in range(0, len(roster.blocks[f'depot{side}']), 24):
            check(f'{title} depot {i//24+1}', *struct.unpack_from('<2h', roster.blocks[f'depot{side}'], i+12))
    for item in objectives(roster):
        check('Objective '+item['name'], item['x'], item['y'])
    for item in read_place_names(roster.header):
        check('Place '+item['name'], item['x'], item['y'], True)
    for cell in _hills(roster.header):
        check('Hilltop', *cell, True)
    for item in battle_plans(roster):
        if item.get('action','order') == 'order':
            check('Battle plan goal', item['x'], item['y'])
    for xkey, ykey in (('bgshx', 'bgshy'), ('bgdhx', 'bgdhy')):
        for (x,), (y,) in zip(struct.iter_unpack('<h', roster.blocks[xkey]),
                              struct.iter_unpack('<h', roster.blocks[ykey])):
            check('Saved battlegroup location', x, y)
    for i in range(0, len(roster.blocks.get('garrison', b'')), 6):
        check('Garrison', *struct.unpack_from('<2h', roster.blocks['garrison'], i))
    count = short(roster.header, 0x260)
    if not 0 <= count <= 16:
        raise ValueError('Invalid naval range marker count.')
    for i in range(count):
        check('Naval range marker', short(roster.header, 0x262+i*2), short(roster.header, 0x282+i*2))
    if (width < old_w or height < old_h) and roster.orders:
        conflicts.append('Saved movement routes (clear orders before cropping)')
    return conflicts


def resize_map(data, width, height, terrain=1, variant=0, owner=0):
    width, height, terrain, variant, owner = map(int, (width, height, terrain, variant, owner))
    roster = UnitRoster(data)
    old_w, old_h = dimensions(roster)
    if (width, height) == (old_w, old_h):
        return data
    if not 4 <= width <= max(125, old_w) or not 4 <= height <= max(125, old_h):
        raise ValueError('Choose 4–125 rows/columns (or retain an existing larger dimension).')
    if width-1 <= short(roster.header, 0x226) or height-1 <= short(roster.header, 0x224):
        raise ValueError('The resized map must include the scenario’s playable origin.')
    if terrain not in range(14) or variant not in range(6) or owner not in (0, 1):
        raise ValueError('Choose valid terrain, artwork and ownership for the new hexes.')
    conflicts = resize_conflicts(roster, width, height)
    if conflicts:
        raise ValueError('Move or remove these before shrinking the map:\n'+ '\n'.join(conflicts[:12])
                         + (f'\n…and {len(conflicts)-12} more.' if len(conflicts) > 12 else ''))
    _read_terrain_map(data)
    _edges(roster)  # Validate the indexed layer before altering row strides.
    if len(roster.blocks['zoc']) != old_w*old_h*4:
        raise ValueError('Invalid ownership map.')
    # Reuse terrain records and preserve row slices of every map-sized array.
    records = roster.blocks['uhexes']
    fill = struct.pack('<I', terrain | variant << 4)
    index = next((i//4 for i in range(0, len(records), 4) if records[i:i+4] == fill), None)
    if index is None:
        index = len(records)//4
        if index > 65535:
            raise ValueError('The shared terrain table is full.')
        records.extend(fill)
    for name, stride, blank in (('hexmap', 2, struct.pack('<H', index)),
                                 ('hedgelist', 2, struct.pack('<H', NO_EDGE)),
                                 ('zoc', 4, struct.pack('<I', owner << 16))):
        old = roster.blocks[name]
        block = bytearray(blank*(width*height))
        for y in range(min(height, old_h)):
            count = min(width, old_w)*stride
            block[y*width*stride:y*width*stride+count] = old[y*old_w*stride:y*old_w*stride+count]
        roster.blocks[name] = block
    h = roster.header
    struct.pack_into('<2h', h, 0x228, height-1, width-1)
    h[0x22c:0x234] = h[0x224:0x22c]
    struct.pack_into('<2h', h, 0x234, width//2, height//2)
    return roster.to_bytes()
