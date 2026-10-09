"""Scenario authoring for HQ organization and class-dependent unit definitions.

Addresses refer to the protected-mode D-Day executable: AttachUnit 7fe28,
RelinkUnit 7fd61, setHQSpanPoints 7f3e9, hqSpanPoints 7f6f3, unitSpanPoints
7f80f, CalcBaseMoves 2c32a, PrintData 3953a and GetArtilleryAmmo 576ef.
All mutations operate on a private roster and return a complete document.
"""
import struct
from decimal import Decimal, InvalidOperation

from lib.unit_reader import decode_record
from lib.unit_roster import UnitRoster, short, put_short
from lib.unit_types import TYPE_DESCRIPTIONS

CLASSES = ('Infantry', 'Armor', 'Engineer', 'Anti-tank', 'Artillery',
           'Naval support', 'Aircraft', 'HQ', 'Anti-aircraft')
MOBILITY = ('Foot', 'Horse', 'Semi-motorized', 'Unmotorized HQ', 'Bicycle',
            'Motorcycle', 'Truck', 'Armored car', 'Tracked', 'Motorized HQ',
            'Fixed', 'Ski')
NATIONALITIES = ('American', 'German', 'Soviet', 'Romanian', 'Italian')
HQ_LEVELS = ('Regiment / brigade', 'Division', 'Corps', 'Army')
GROUND_CLASSES = (0, 1, 2, 3, 4, 8)

# Auxiliary artillery record: four fixed-point strengths, followed by bytes.
# ModifyStr (14a6e) copies base +8/+12 to adjusted +0/+4. AllocateFPF (f2b2)
# uses the second strength for defensive fire, not anti-armor bombardment.
ARTILLERY_FIELDS = {
    'bombardment': (8, '<i', 1000, 0, 2147483647),
    'defensive_fire': (12, '<i', 1000, 0, 2147483647),
    'range': (0x11, '<B', 1, 0, 255),
    'preparation_turns': (0x10, '<B', 1, 0, 255),
    'ammo_category': (0x13, '<B', 1, 0, 3),
    'shoot_scoot': (0x14, '<B', 1, 0, 1),
}


def _integer(value, label, low, high, scale=1):
    try:
        number = Decimal(str(value)) * scale
        if not number.is_finite() or number != number.to_integral_value():
            raise ValueError()
        number = int(number)
    except (ValueError, InvalidOperation, OverflowError) as exc:
        raise ValueError(f'{label}: enter a whole number' if scale == 1 else
                         f'{label}: use at most three decimal places') from exc
    if not low <= number <= high:
        raise ValueError(f'{label}: value must be between {low / scale:g} and {high / scale:g}')
    return number


def _unit(roster, side, index):
    if side not in (0, 1) or not isinstance(index, int) or not 0 <= index < len(roster.records[side]):
        raise ValueError('Choose a unit from the current roster')
    return roster.records[side][index]


def headquarters(roster, side):
    result = []
    block = roster.blocks[f'hqs{side}']
    for hq in range(roster.count(0x23c, side)):
        index = short(roster.blocks[f'hqlist{side}'], hq * 2)
        record = _unit(roster, side, index)
        if (record[0x76] != 7 or struct.unpack_from('<i', record, 4)[0] != hq
                or record[0x81] != hq or short(block, hq * 58 + 0x28) != index):
            raise ValueError('Inconsistent HQ roster links')
        result.append(dict(id=hq, index=index, name=decode_record(record)['name'],
                           deleted=decode_record(record)['deleted'],
                           parent=short(block, hq * 58 + 0x32),
                           level=short(block, hq * 58 + 0x2e),
                           used=short(block, hq * 58 + 0x34),
                           capacity=short(block, hq * 58 + 0x36)))
    return result


def _check_hierarchy(hqs):
    for hq in hqs:
        if not 0 <= hq['level'] <= 3:
            raise ValueError('Unknown HQ command level')
        seen = {hq['id']}
        parent = hq['parent']
        while parent != -1:
            if not 0 <= parent < len(hqs):
                raise ValueError('HQ parent is outside this side’s organization')
            if parent in seen:
                raise ValueError('An HQ cannot report to itself or one of its subordinates')
            seen.add(parent)
            parent = hqs[parent]['parent']


def _command_points(record, factor):
    if record[0x76] not in (0, 1):
        return 0
    return (3 if record[0x7e] == 3 else 1) if factor == 1 else (3 if record[0x7e] == 3 else 0)


def refresh_command_spans(roster, side):
    """Recompute command costs/capacity using the executable's exact rules."""
    hqs = headquarters(roster, side)
    factor = 1 if roster.header[0x122b] == 3 else 3
    block = roster.blocks[f'hqs{side}']
    used = [0] * len(hqs)
    for record in roster.records[side][:roster.count(0x240, side)]:
        if record[0x76] != 7 and not decode_record(record)['deleted']:
            hq = record[0x81]
            if hq >= len(hqs):
                raise ValueError('Unit has an invalid controlling HQ')
            used[hq] += _command_points(record, factor)
    for hq in hqs:
        if hq['parent'] >= 0:
            used[hq['parent']] += (3 * factor, 9 * factor, 27 * factor, 1000)[hq['level']]
    for hq in hqs:
        record = roster.records[side][hq['index']]
        reduced = record[0x75] in (3, 4)
        capacity = ((12 if side == 0 and record[0x77] == 19 else 5), 15,
                    45 if reduced else 90, 108 if reduced else 243)[hq['level']] * factor
        if used[hq['id']] > 32767:
            raise ValueError('HQ command cost exceeds the game’s storage limit')
        put_short(block, hq['id'] * 58 + 0x34, used[hq['id']])
        put_short(block, hq['id'] * 58 + 0x36, capacity)


def _unlink(roster, side, index):
    record = roster.records[side][index]
    hq = record[0x81]
    if hq >= roster.count(0x23c, side):
        raise ValueError('Invalid original HQ assignment')
    previous = short(roster.blocks[f'hqlist{side}'], hq * 2)
    seen = set()
    while previous >= 0 and previous not in seen:
        seen.add(previous)
        old = _unit(roster, side, previous)
        link = short(old, 0x6a)
        if link == index:
            put_short(old, 0x6a, short(record, 0x6a))
            put_short(record, 0x6a, -1)
            return
        previous = link
    raise ValueError('Unit is missing from its HQ subordinate chain')


def edit_organization(data, side, index, *, hq=None, parent=None, level=None):
    roster = UnitRoster(data)
    record = _unit(roster, side, index)
    if record[0x76] in (5, 6):
        raise ValueError('Aircraft and naval support do not belong to ground HQs')
    if decode_record(record)['deleted']:
        raise ValueError('Restore this unit before changing its organization')
    hqs = headquarters(roster, side)
    _check_hierarchy(hqs)
    changed = False
    if record[0x76] == 7:
        if hq is not None:
            raise ValueError('Choose a parent HQ for a headquarters')
        own = record[0x81]
        old = hqs[own]
        parent = old['parent'] if parent is None else _integer(parent, 'Parent HQ', -1, len(hqs)-1)
        level = old['level'] if level is None else _integer(level, 'HQ level', 0, 3)
        if parent == old['parent'] and level == old['level']:
            return data
        if parent >= 0 and hqs[parent]['deleted']:
            raise ValueError('Choose a headquarters that has not been deleted')
        hqs[own] = dict(old, parent=parent, level=level)
        _check_hierarchy(hqs)
        if parent >= 0 and hqs[parent]['level'] <= level:
            raise ValueError('The parent HQ must have a higher command level')
        if any(h['parent'] == own and h['level'] >= level for h in hqs):
            raise ValueError('Move subordinate HQs first, or choose a level above theirs')
        block = roster.blocks[f'hqs{side}']
        put_short(block, own * 58 + 0x32, parent)
        put_short(block, own * 58 + 0x2e, level)
        put_short(block, own * 58 + 0x2a, -1 if parent == -1 else -2)
        record[0x80] = own if parent == -1 else parent
        for member in roster.records[side][:roster.count(0x240, side)]:
            if member[0x76] != 7 and member[0x81] == own:
                member[0x80] = record[0x80]
        if level != old['level']:
            # RWHQHeads links all HQs of each command level through HQ+0x30.
            for lev in range(4):
                chain = [h['id'] for h in hqs if h['level'] == lev]
                put_short(roster.blocks['hqheads'], (side * 4 + lev) * 2, chain[0] if chain else -1)
                for i, item in enumerate(chain):
                    put_short(block, item * 58 + 0x30, chain[i+1] if i+1 < len(chain) else -1)
        changed = True
    else:
        if parent is not None or level is not None:
            raise ValueError('Only headquarters have a parent and command level')
        hq = record[0x81] if hq is None else _integer(hq, 'Controlling HQ', 0, len(hqs)-1)
        if hq == record[0x81]:
            return data
        if hqs[hq]['deleted']:
            raise ValueError('Choose a headquarters that has not been deleted')
        if hq != record[0x81]:
            _unlink(roster, side, index)
            record[0x81] = hq
            roster._link(side, index)
            changed = True
        # Scenario organization is permanent, unlike a temporary in-game attachment.
        parent_id = roster.records[side][hqs[hq]['index']][0x80]
        if record[0x84] != hq or record[0x80] != parent_id:
            record[0x84], record[0x80] = hq, parent_id
            changed = True
    if not changed:
        return data
    refresh_command_spans(roster, side)
    return roster.to_bytes()


def definition(roster, side, index):
    record = _unit(roster, side, index)
    result = dict(unit_class=record[0x76], type=record[0x77], nationality=record[0x75],
                  mobility=record[0x79], movement_allowance=struct.unpack_from('<H', record, 0x4c)[0] / 1000,
                  stacking_size=record[0x7e])
    aux = roster._auxiliary(record)
    if aux and aux[0] == 'arty':
        offset = struct.unpack_from('<i', record, 4)[0] * 28
        block = roster.blocks[f'arty{side}']
        if not 0 <= offset <= len(block)-28:
            raise ValueError('Invalid artillery record')
        result.update({key: struct.unpack_from(fmt, block, offset+pos)[0] / scale
                       for key, (pos, fmt, scale, _, _) in ARTILLERY_FIELDS.items()})
    return result


def _new_auxiliary(roster, side, record, old_aux):
    new_aux = roster._auxiliary(record)
    if new_aux == old_aux:
        return
    if new_aux:
        name, count_offset, stride = new_aux
        data = bytearray(stride)
        if name == 'arty':
            # Fresh gun data, no borrowed target or barrage state.
            struct.pack_into('<4i', data, 0, 1000, 1000, 1000, 1000)
            data[0x11] = 1
            data[0x13] = 1
        idx = roster._increment(count_offset, side)
        roster.blocks[f'{name}{side}'] = roster.blocks.get(f'{name}{side}', bytearray()) + data
        struct.pack_into('<i', record, 4, idx)
    else:
        record[4:8] = bytes(4)
    # Old auxiliary slots remain reserved, so every other unit's indices survive.


def edit_definition(data, side, index, values, *, return_index=False):
    roster = UnitRoster(data)
    record = _unit(roster, side, index)
    before = definition(roster, side, index)
    if decode_record(record)['deleted']:
        raise ValueError('Restore this unit before changing its definition')
    unknown = set(values) - set(before) - set(ARTILLERY_FIELDS)
    if unknown:
        raise ValueError(f'Unsupported definition field: {sorted(unknown)[0]}')
    fields = dict(before, **values)
    cls = _integer(fields['unit_class'], 'Class', 0, 8)
    old_cls = before['unit_class']
    if cls != old_cls and (cls not in GROUND_CLASSES or old_cls not in GROUND_CLASSES):
        raise ValueError('HQ, aircraft and naval roles require their own roster entries; add a unit of that role')
    descriptor = _integer(fields['type'], 'Descriptor', 0, len(TYPE_DESCRIPTIONS)-1)
    support_change = old_cls in (5, 6) and descriptor != before['type']
    nationality = _integer(fields['nationality'], 'Nationality', 0, 4)
    mobility = _integer(fields['mobility'], 'Mobility', 0, 255)
    if old_cls not in (5, 6) and mobility >= len(MOBILITY):
        raise ValueError('Choose a ground movement class')
    if old_cls in (5, 6) and mobility != before['mobility']:
        raise ValueError('Support units use their template’s flight/naval movement rules')
    # DrawMovementPointsAboveCounter divides calcMP's fixed-point result by 1000.
    moves = _integer(fields['movement_allowance'], 'Movement allowance', 0, 32767, 1000)
    stacking = _integer(fields['stacking_size'], 'Stacking size', 0, 255)
    if old_cls in (5, 6, 7):
        if stacking != before['stacking_size']:
            raise ValueError('HQ and support stacking sizes are determined by the engine')
    elif not 1 <= stacking <= 15:
        raise ValueError('Ground units must occupy between 1 and 15 stacking points')
    if record[0x91] and stacking != before['stacking_size']:
        raise ValueError('Dismount the unit and its passengers under Transport before changing stacking size')
    structural = cls != old_cls or mobility != before['mobility']
    if structural and (record[0x91] or record[0x86]):
        raise ValueError('Clear saved movement orders and mounted transport links before changing class or mobility')
    if cls != old_cls and record[0x78] >> 4:
        raise ValueError('Clear the secondary order under Orders before changing class')
    old_aux = roster._auxiliary(record)
    if support_change:
        from lib.support_units import change_profile
        change_profile(roster, side, record, descriptor)
        old_aux = roster._auxiliary(record)
        mobility = record[0x79]
    record[0x75:0x78] = bytes((nationality, cls, descriptor))
    record[0x79], record[0x7e] = mobility, stacking
    struct.pack_into('<H', record, 0x4c, moves)
    _new_auxiliary(roster, side, record, old_aux)
    aux = roster._auxiliary(record)
    for key, (pos, fmt, scale, low, high) in ARTILLERY_FIELDS.items():
        if key not in values:
            continue
        if not aux or aux[0] != 'arty':
            # Hidden fields from the old class must not leak into another role.
            if key in before and str(values[key]) == str(before[key]):
                continue
            raise ValueError('Bombardment fields require an artillery-capable unit')
        number = _integer(values[key], key.replace('_', ' ').capitalize(), low, high, scale)
        if key == 'shoot_scoot' and not number and record[0x78] >> 4 == 8:
            raise ValueError('Change the Shoot ’n scoot order before disabling its capability')
        start = struct.unpack_from('<i', record, 4)[0] * 28
        struct.pack_into(fmt, roster.blocks[f'arty{side}'], start + pos, number)
        if key in ('bombardment', 'defensive_fire') and number != round(before.get(key, -1) * scale):
            struct.pack_into(fmt, roster.blocks[f'arty{side}'], start + pos - 8, number)
    if roster.to_bytes() == data:
        return (data, index) if return_index else data
    if support_change:
        from lib.support_units import regroup
        index = regroup(roster, side, record)
    if old_cls not in (5, 6) and (cls != old_cls or nationality != before['nationality'] or descriptor != before['type'] or stacking != before['stacking_size']):
        refresh_command_spans(roster, side)
    from lib.scenario_rules import synchronize_occupancy
    result = synchronize_occupancy(roster.to_bytes())
    return (result, index) if return_index else result


def transfer_unit(data, side, index, destination, *, counter=None, hq=None):
    """Move to the other OOB without renumbering script-addressable ground IDs.

    Retire the original slot and allocate a fresh destination record. A ground
    unit waits off map until placed, so transfer cannot create an enemy stack.
    """
    from types import SimpleNamespace
    roster = UnitRoster(data)
    record = bytearray(_unit(roster, side, index))
    if destination not in (0, 1) or destination == side:
        raise ValueError('Choose the other side')
    if record[0x76] == 7:
        raise ValueError('Create an HQ on the other side and transfer its units individually')
    if decode_record(record)['deleted']:
        raise ValueError('Restore this unit before transferring it')
    rows = [[], []]
    blocks = {}
    aux = roster._auxiliary(record)
    if aux:
        kind, _, stride = aux
        offset = struct.unpack_from('<i', record, 4)[0] * stride
        blocks[f'{kind}{destination}'] = roster.blocks[f'{kind}{side}'][offset:offset+stride]
        struct.pack_into('<i', record, 4, 0)
    record[0x74] = destination
    if counter is not None:
        put_short(record, 0x56, counter)
    rows[destination] = [record]
    source = SimpleNamespace(records=rows, blocks=blocks)
    added = roster.add(destination, 0, decode_record(record)['name'], source=source)
    roster.remove(side, index)
    result = roster.to_bytes()
    if record[0x76] not in (5, 6):
        result = edit_organization(result, destination, added, hq=0 if hq is None else hq)
    roster = UnitRoster(result)
    refresh_command_spans(roster, side)
    refresh_command_spans(roster, destination)
    from lib.scenario_rules import synchronize_occupancy
    return synchronize_occupancy(roster.to_bytes()), added
