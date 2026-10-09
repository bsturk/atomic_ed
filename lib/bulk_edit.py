"""Atomic bulk edits of native scenario data; no executable changes.

Translations use hex coordinates, so direction-based saved routes remain valid.
ShowOrders (344e3) walks Orders[OB+86 .. 1] through CalcHexOffs (463c8).
store_orders (69328) writes directions 0..5 and the length at Orders[0].
"""
import copy
import struct

from lib.unit_roster import UnitRoster, short, put_short
from lib.unit_reader import decode_record
from lib.unit_definitions import headquarters, _check_hierarchy, _unlink, refresh_command_spans, _integer
from lib.map_editor import hex_neighbor, _read_terrain_map, _record_at, _write_hex_records, _set_connection
from lib.map_tools import (dimensions, translate_cell, _edges, _write_hills, _hills,
                           _write_places, NO_EDGE)
from lib.scenario_rules import synchronize_occupancy, edit_objective
from lib.scenario_conditions import supply_groups
from lib.battle_plans import battle_plans, set_battle_plans, plan_conditions


class Translation:
    def __init__(self, roster, origin, destination, size=None):
        self.old_size = dimensions(roster)
        self.size = size or self.old_size
        self.origin, self.destination = origin, destination
        self.top, self.left = struct.unpack_from('<2h', roster.header, 0x224)

    def inside(self, cell):
        return 0 <= cell[0] < self.old_size[0] and 0 <= cell[1] < self.old_size[1]

    def point(self, cell, label, padding=False):
        # Off-map/sentinel values stay off map, even when the grid grows.
        if not self.inside(cell):
            return cell
        target = translate_cell(cell, self.origin, self.destination)
        inset = 0 if padding else 1
        left, top = (0, 0) if padding else (self.left, self.top)
        if not (left <= target[0] < self.size[0]-inset and top <= target[1] < self.size[1]-inset):
            raise ValueError(f'{label} at {cell} would move outside the {"map" if padding else "playable map"}: {target}.')
        return target

    def pair(self, block, xoffset, yoffset=None, label='Location', padding=False):
        yoffset = xoffset+2 if yoffset is None else yoffset
        before = (short(block, xoffset), short(block, yoffset))
        x, y = self.point(before, label, padding)
        put_short(block, xoffset, x)
        put_short(block, yoffset, y)


def _unit_label(side, index, record):
    return f'{("Allied", "Axis")[side]} unit {index+1} {decode_record(record)["name"]}'


def _relocate_unit(roster, side, index, transform):
    record = roster.records[side][index]
    label = _unit_label(side, index, record)
    cell = struct.unpack_from('<2h', record, 0x58)
    route = roster.orders.get((side, index))
    if route is not None:
        count = record[0x86]
        if count >= len(route) or any(d > 5 for d in route[1:count+1]):
            raise ValueError(f'{label} has an invalid saved movement route.')
        if not transform.inside(cell):
            raise ValueError(f'{label} has saved orders but no map location.')
        for direction in reversed(route[1:count+1]):
            cell = hex_neighbor(cell, direction)
            if not transform.inside(cell):
                raise ValueError(f'{label} has a saved movement route outside the map.')
            transform.point(cell, label+' route')
        # No rewrite: directions and their ordering survive an axial translation.
    for offset, description in ((0x58, ''), (0x5c, ' target'), (0x60, ' fallback')):
        transform.pair(record, offset, label=label+description, padding=record[0x76] in (5, 6))


def _check_transport(roster, side, selected):
    """A mounted group must move together, including cross-HQ passengers."""
    from lib.unit_operations import transport_groups
    for carrier, passengers in transport_groups(roster, side).items():
        group = {carrier, *passengers}
        if group & selected and not group <= selected:
            raise ValueError('Move the transport and all its mounted passengers together; they belong to different formations.')


def _stack_sizes(roster):
    sizes = {}
    current = struct.unpack_from('<i', roster.blocks['calendar'], 12)[0]
    width, height = dimensions(roster)
    for side in (0, 1):
        for record in roster.records[side][:roster.count(0x240, side)]:
            arrival = struct.unpack_from('<i', record, 8)[0]
            x, y = struct.unpack_from('<2h', record, 0x58)
            if arrival == -1 or arrival >= current or not (0 <= x < width and 0 <= y < height):
                continue
            weight = (4 if roster.header[0x122b] == 1 else 3) if record[0x76] == 7 else record[0x7e]
            sizes[x, y] = sizes.get((x, y), 0)+weight
    return sizes


def _finish(before, roster):
    old = _stack_sizes(UnitRoster(before))
    for cell, size in _stack_sizes(roster).items():
        if size > 15 and size > old.get(cell, 0):
            raise ValueError(f'Stacking at {cell} would exceed the 15-point storage limit ({size}).')
    return synchronize_occupancy(roster.to_bytes())


def formation_members(roster, side, hq, descendants=True):
    side = _integer(side, 'Side', 0, 1)
    hqs = headquarters(roster, side)
    _check_hierarchy(hqs)
    hq = _integer(hq, 'HQ', 0, len(hqs)-1)
    if hqs[hq]['deleted']:
        raise ValueError('Restore the HQ before moving its formation.')
    groups = {hq}
    if descendants:
        while True:
            expanded = groups | {h['id'] for h in hqs if h['parent'] in groups}
            if expanded == groups:
                break
            groups = expanded
    members = {i for i, u in enumerate(roster.records[side][:roster.count(0x240, side)])
               if u[0x81] in groups and not decode_record(u)['deleted']}
    return hqs, groups, members


def move_formation(data, side, hq, destination, descendants=True, move_goals=True):
    roster = UnitRoster(data)
    side = _integer(side, 'Side', 0, 1)
    hqs, groups, members = formation_members(roster, side, hq, descendants)
    hq = _integer(hq, 'HQ', 0, len(hqs)-1)
    origin = struct.unpack_from('<2h', roster.records[side][hqs[hq]['index']], 0x58)
    target = tuple(_integer(v, 'Destination', 0, 32767) for v in destination)
    transform = Translation(roster, origin, target)
    if not transform.inside(origin):
        raise ValueError('Place the selected HQ on the map before moving its formation.')
    if target == origin:
        return data
    _check_transport(roster, side, members)
    for index in members:
        _relocate_unit(roster, side, index, transform)
    plans = battle_plans(roster)
    if move_goals:
        for plan in plans:
            if plan.get('action','order') == 'order' and plan['side'] == side and plan['group'] in groups:
                plan['x'], plan['y'] = transform.point((plan['x'], plan['y']), 'Battle plan goal')
        # A shared garrison is a geographic restriction for every assigned HQ.
        for g in range(roster.header[0x1223]):
            assigned = {(s, i) for s in (0, 1) for i, u in enumerate(roster.records[s])
                        if u[0x76] == 7 and u[0x7e] == g}
            selected = {(side, i) for i in members}
            if assigned & selected:
                if not assigned <= selected:
                    raise ValueError('A garrison is shared with another formation. Disable moving goals and garrisons, or move all assigned HQs together.')
                transform.pair(roster.blocks['garrison'], g*6, label='Garrison')
    result = _finish(data, roster)
    return set_battle_plans(result, plans) if plans and move_goals else result


def shift_map(data, dx, dy, width=None, height=None, terrain=1, variant=0, owner=0):
    roster = UnitRoster(data)
    old_w, old_h = dimensions(roster)
    dx, dy = (_integer(v, 'Shift', -32767, 32767) for v in (dx, dy))
    width = _integer(old_w if width is None else width, 'Columns', 4, max(125, old_w))
    height = _integer(old_h if height is None else height, 'Rows', 4, max(125, old_h))
    if (dx, dy, width, height) == (0, 0, old_w, old_h):
        return data
    terrain = _integer(terrain, 'Terrain', 0, 13)
    variant = _integer(variant, 'Variant', 0, 5)
    owner = _integer(owner, 'Owner', 0, 1)
    transform = Translation(roster, (0, 0), (dx, dy), (width, height))
    if width-1 <= transform.left or height-1 <= transform.top:
        raise ValueError('The new map must include the playable origin.')
    parsed = _read_terrain_map(data)
    _edges(roster)
    if len(roster.blocks['zoc']) != old_w*old_h*4:
        raise ValueError('Invalid ownership map.')
    for side in (0, 1):
        for index in range(len(roster.records[side])):
            _relocate_unit(roster, side, index, transform)
        for g, group in enumerate(supply_groups(roster, side)):
            for i in range(len(group['entries'])):
                transform.pair(roster.blocks[f'stock{side}'], g*136+4+i*2, g*136+56+i*2, 'Supply entry')
        # Depot zero is the off-map reserve, not a map location.
        for offset in range(24, len(roster.blocks[f'depot{side}']), 24):
            transform.pair(roster.blocks[f'depot{side}'], offset+12, label='Depot')
    for offset in range(0, len(roster.blocks['vicloc']), 48):
        transform.pair(roster.blocks['vicloc'], offset+8, label='Objective')
    for i in range(roster.header[0x122a]):
        transform.pair(roster.header, 0xbe0+i*32, label='Place name', padding=True)
    _write_hills(roster.header, [transform.point(c, 'Hilltop', True) for c in _hills(roster.header)])
    for i in range(0, len(roster.blocks.get('garrison', b'')), 6):
        transform.pair(roster.blocks['garrison'], i, label='Garrison')
    count = short(roster.header, 0x260)
    if not 0 <= count <= 16:
        raise ValueError('Invalid naval range marker count.')
    for i in range(count):
        transform.pair(roster.header, 0x262+i*2, 0x282+i*2, 'Naval range marker')
    for i in range(len(roster.blocks['bgstate'])//2):
        start = (short(roster.blocks['bgshx'], i*2), short(roster.blocks['bgshy'], i*2))
        goal = (short(roster.blocks['bgdhx'], i*2), short(roster.blocks['bgdhy'], i*2))
        # Native empty slots have state=0, start=(0,0), goal=(-1,-1).
        if short(roster.blocks['bgstate'], i*2) == 0 and start == (0, 0) and goal == (-1, -1):
            continue
        for xkey, ykey, cell in (('bgshx', 'bgshy', start), ('bgdhx', 'bgdhy', goal)):
            x, y = transform.point(cell, 'Saved battlegroup location')
            put_short(roster.blocks[xkey], i*2, x)
            put_short(roster.blocks[ykey], i*2, y)
    plans = battle_plans(roster)
    for plan in plans:
        if plan.get('action','order') != 'order':continue
        plan['x'], plan['y'] = transform.point((plan['x'], plan['y']), 'Battle plan goal')
    fill = struct.pack('<I', terrain | variant << 4)
    records = roster.blocks['uhexes']
    index = next((i//4 for i in range(0, len(records), 4) if records[i:i+4] == fill), None)
    if index is None:
        index = len(records)//4
        if index > 65535:
            raise ValueError('The shared terrain table is full.')
        records.extend(fill)
    targets = {}
    for name, stride, blank in (('hexmap', 2, struct.pack('<H', index)),
                                 ('hedgelist', 2, struct.pack('<H', NO_EDGE)),
                                 ('zoc', 4, struct.pack('<I', owner << 16))):
        old = roster.blocks[name]
        block = bytearray(blank*(width*height))
        for y in range(old_h):
            for x in range(old_w):
                target = translate_cell((x, y), (0, 0), (dx, dy))
                tx, ty = target
                if 0 <= tx < width and 0 <= ty < height:
                    block[(ty*width+tx)*stride:(ty*width+tx+1)*stride] = old[(y*old_w+x)*stride:(y*old_w+x+1)*stride]
                    if name == 'hexmap':
                        targets[target] = _record_at(parsed, (x, y))
        roster.blocks[name] = block
    struct.pack_into('<2h', roster.header, 0x228, height-1, width-1)
    roster.header[0x22c:0x234] = roster.header[0x224:0x22c]
    center = translate_cell(struct.unpack_from('<2h', roster.header, 0x234), (0, 0), (dx, dy))
    struct.pack_into('<2h', roster.header, 0x234, max(0, min(width-2, center[0])), max(0, min(height-2, center[1])))
    # Remove road/river/slope stubs into newly filled cells or past the border.
    replacements = {}
    for cell, word in targets.items():
        changed = word
        for d in range(6):
            if hex_neighbor(cell, d) not in targets:
                changed = _set_connection(_set_connection(changed, 8, d, 0), 20, d, 0)
        if changed != word:
            replacements[cell] = changed
    result = roster.to_bytes()
    result = _write_hex_records(result, _read_terrain_map(result), replacements)
    result = _finish(data, UnitRoster(result))
    return set_battle_plans(result, plans) if plans else result


def paste_scenario_items(data, region, destination, *, units=False, objectives=False, places=False):
    """Add snapshot contents, preserving originals and allocating new unit/HQ IDs."""
    if not any((units, objectives, places)):
        return data
    if 'document' not in region:
        raise ValueError('Copy this region again to include units, objectives and place names.')
    source = UnitRoster(region['document'])
    roster = UnitRoster(data)
    from lib.scenario_rules import objectives as read_objectives
    original_objectives = read_objectives(source)
    current_objectives = read_objectives(roster)
    selected = set(region['cells'])
    transform = Translation(source, region['origin'], destination, dimensions(roster))
    transform.top, transform.left = struct.unpack_from('<2h', roster.header, 0x224)
    if places:
        existing = [bytes(roster.header[0xbe0+i*32:0xc00+i*32]) for i in range(roster.header[0x122a])]
        for i in range(source.header[0x122a]):
            record = bytearray(source.header[0xbe0+i*32:0xc00+i*32])
            if struct.unpack_from('<2h', record) in selected:
                transform.pair(record, 0, label='Copied place name', padding=True)
                existing.append(bytes(record))
        _write_places(roster.header, existing)
    objective_map = {}
    if objectives:
        for i, item in enumerate(original_objectives):
            if (item['x'], item['y']) in selected:
                x, y = transform.point((item['x'], item['y']), 'Copied objective')
                objective_map[i] = roster.header[0x1222]
                roster = UnitRoster(edit_objective(roster.to_bytes(), None, dict(item, x=x, y=y)))
    plans = battle_plans(roster)
    if units:
        if short(roster.header, 0x238) != short(source.header, 0x238):
            raise ValueError('Unit copies require the same scenario counter bank.')
        garrison_map = {}
        for side in (0, 1):
            hqs = headquarters(source, side)
            existing_hqs = headquarters(roster, side)
            _check_hierarchy(hqs)
            chosen = [i for i, record in enumerate(source.records[side][:source.count(0x240, side)])
                      if not decode_record(record)['deleted'] and struct.unpack_from('<2h', record, 0x58) in selected]
            # HQs first, so a copied unit can resolve a newly created command.
            chosen.sort(key=lambda i: source.records[side][i][0x76] != 7)
            hq_map, unit_map = {}, {}
            for i in chosen:
                original = source.records[side][i]
                cell = transform.point(struct.unpack_from('<2h', original, 0x58), 'Copied unit')
                new = roster.add(side, i, decode_record(original)['name'][:20]+' copy', source=source)
                unit_map[i] = new
                record = roster.records[side][new]
                record[8:12] = original[8:12]  # Preserve deployment/reinforcement time.
                struct.pack_into('<2h', record, 0x58, *cell)
                struct.pack_into('<4h', record, 0x5c, -1, -1, -1, -1)
                record[0x78] = 9  # Fresh Defend order; no borrowed routes/targets.
                if original[0x76] == 7:
                    hq_map[original[0x81]] = record[0x81]
            for old, new in hq_map.items():
                original = source.records[side][hqs[old]['index']]
                record = roster.records[side][unit_map[hqs[old]['index']]]
                parent = hqs[old]['parent']
                if parent >= 0 and parent not in hq_map and (parent >= len(existing_hqs) or existing_hqs[parent]['deleted']):
                    raise ValueError('The copied HQ’s parent no longer exists. Copy the region again.')
                parent = hq_map.get(parent, parent)
                put_short(roster.blocks[f'hqs{side}'], new*58+0x32, parent)
                record[0x80] = new if parent == -1 else parent
                for name in ('autoart', 'autognd'):
                    roster.blocks[f'{name}{side}'][new] = source.blocks[f'{name}{side}'][old]
                g = original[0x7e]
                if g < source.header[0x1223]:
                    row = bytearray(source.blocks['garrison'][g*6:(g+1)*6])
                    if struct.unpack_from('<2h', row) in selected:
                        if g not in garrison_map:
                            if roster.header[0x1223] >= 128:
                                raise ValueError('A scenario can have at most 128 garrisons.')
                            transform.pair(row, 0, label='Copied garrison')
                            garrison_map[g] = roster.header[0x1223]
                            roster.blocks.setdefault('garrison', bytearray()).extend(row)
                            roster.header[0x1223] += 1
                        g = garrison_map[g]
                    elif g >= roster.header[0x1223] or roster.blocks['garrison'][g*6:(g+1)*6] != row:
                        raise ValueError('The copied HQ’s garrison changed. Copy the region again.')
                    record[0x7e] = g
            for old, new in unit_map.items():
                original = source.records[side][old]
                if original[0x76] == 7:
                    continue
                old_hq = original[0x81]
                if old_hq not in hq_map and (old_hq >= len(existing_hqs) or existing_hqs[old_hq]['deleted']):
                    raise ValueError('The copied unit’s HQ no longer exists. Copy the region again.')
                hq = hq_map.get(old_hq, old_hq)
                current = headquarters(roster, side)
                if hq >= len(current) or current[hq]['deleted']:
                    raise ValueError('The copied unit’s HQ no longer exists. Copy the region again.')
                _unlink(roster, side, new)
                record = roster.records[side][new]
                record[0x81] = record[0x84] = hq
                record[0x80] = roster.records[side][current[hq]['index']][0x80]
                roster._link(side, new)
            if chosen:
                _check_hierarchy(headquarters(roster, side))
                refresh_command_spans(roster, side)
            for plan in battle_plans(source):
                if plan['side'] == side and plan['group'] in hq_map:
                    plan = copy.deepcopy(plan)
                    plan['group'] = hq_map[plan['group']]
                    if (plan['x'], plan['y']) in selected:
                        plan['x'], plan['y'] = transform.point((plan['x'], plan['y']), 'Copied battle plan')
                    for condition in plan_conditions(plan):
                        if condition['trigger'] == 1:
                            index = condition['objective']
                            if index not in objective_map and (index >= len(current_objectives) or
                                    any(original_objectives[index][k] != current_objectives[index][k] for k in ('name', 'x', 'y'))):
                                raise ValueError('An objective referenced by a copied HQ plan changed. Copy the region again.')
                            condition['objective'] = objective_map.get(index, index)
                    plans.append(plan)
    result = _finish(data, roster)
    return set_battle_plans(result, plans) if plans else result
