"""Remaining native D-Day scenario records and their roster relationships.

Protected-mode engine references: RWLeaders 28f75, GetLeaderShifts 2f687,
OkToAttachLeader 2eeaa, UpdateReps 1a62e, WithinGarrisonLimits 35c9e,
TraceToSupplySource 54a47, TraceAllDepots 54c2d and SetCalVars 2d831.
Opaque and runtime fields survive edits; all mutations use a private roster.
"""
from datetime import date, timedelta
import struct

from lib.unit_roster import UnitRoster, short, put_short
from lib.unit_reader import decode_record
from lib.unit_definitions import headquarters, _integer
from lib.scenario_rules import EPOCH, scenario_dates

REPLACEMENT_TYPES = {0: 'Infantry', 1: 'Armor', 2: 'Engineer', 3: 'Anti-tank',
                     4: 'Artillery', 5: 'Anti-aircraft', 8: 'Airborne'}


def _side(side):
    return _integer(side, 'Side', 0, 1)


def _flag(value, label):
    return _integer(int(value) if isinstance(value, bool) else value, label, 0, 1)


def _index(index, count, label):
    return _integer(index, label, 0, count - 1)


def _point(roster, x, y):
    top, left, bottom, right = struct.unpack_from('<4h', roster.header, 0x224)
    return (_integer(x, 'Hex X', left, right - 1),
            _integer(y, 'Hex Y', top, bottom - 1))


def _records(roster, key, count, size):
    block = roster.blocks.get(key, bytearray())
    if len(block) != count * size:
        raise ValueError(f'Invalid {key} table')
    return block


def leaders(roster, side):
    side = _side(side)
    b = _records(roster, f'leaders{side}', roster.header[0x3a2 + side], 36)
    return [dict(attack=struct.unpack_from('<i', b, p)[0],
                 defense=struct.unpack_from('<i', b, p+4)[0], counter=short(b, p+8),
                 unit=short(b, p+10), home=short(b, p+12),
                 name=b[p+14:p+30].split(b'\0')[0].decode('cp437'),
                 nationality=b[p+30], restricted=bool(b[p+34]))
            for p in range(0, len(b), 36)]


def edit_leader(data, side, index, values=None, counter_bitmap=None):
    roster = UnitRoster(data)
    side = _side(side)
    rows = leaders(roster, side)
    count = len(rows)
    if index is not None:
        index = _index(index, count, 'Leader')
    b = roster.blocks.setdefault(f'leaders{side}', bytearray())
    if values is None:
        if index is None:
            raise ValueError('Choose a leader to remove')
        del b[index*36:(index+1)*36]
        for unit in roster.records[side]:
            link = unit[0x90]
            if link == index:
                unit[0x90] = 255
            elif index < link < count:
                unit[0x90] -= 1
    else:
        if index is None and count >= 128:
            raise ValueError('A side can have at most 128 leaders')
        try:
            name = values['name'].strip().encode('cp437')
        except UnicodeEncodeError as exc:
            raise ValueError('Use DOS characters in leader names') from exc
        if not 1 <= len(name) <= 15 or any(c < 32 or c == 127 for c in name):
            raise ValueError('Leader names need 1–15 printable DOS characters')
        hqs = headquarters(roster, side)
        home = _index(values['home'], len(hqs), 'Home HQ')
        unit_index = _index(values['unit'], roster.count(0x240, side), 'Attached unit')
        unit = roster.records[side][unit_index]
        if hqs[home]['deleted'] or decode_record(unit)['deleted'] or unit[0x76] == 4:
            raise ValueError('Choose an active roster HQ and a ground unit other than artillery')
        if any(i != index and row['unit'] == unit_index for i, row in enumerate(rows)):
            raise ValueError('That unit already has a leader')
        restricted = _flag(values['restricted'], 'Formation restriction')
        if restricted:
            current, seen = unit[0x81], set()
            while current != home and 0 <= current < len(hqs) and current not in seen:
                seen.add(current)
                current = hqs[current]['parent']
            if current != home:
                raise ValueError('The attached unit must belong to the home HQ’s formation')
        attack = _integer(values['attack'], 'Attack odds shifts', -100, 100)
        defense = _integer(values['defense'], 'Defense odds shifts', -100, 100)
        counter = _integer(values['counter'], 'Chit number', 0, 32767)
        from lib.game_art import unit_counter
        unit_counter(short(roster.header, 0x238)+side, counter, counter_bitmap)
        nationality = _integer(values['nationality'], 'Nationality', 0, 4)
        record = bytearray(36) if index is None else bytearray(b[index*36:(index+1)*36])
        struct.pack_into('<2i3h', record, 0, attack, defense, counter, unit_index, home)
        record[14:30] = name.ljust(16, b'\0')
        record[30] = nationality
        record[31] = unit[0x7c]
        arrival = struct.unpack_from('<i', unit, 8)[0]
        current = struct.unpack_from('<i', roster.blocks['calendar'], 12)[0]
        record[33] = int(arrival != -1 and arrival < current)
        record[34] = restricted
        new_index = count if index is None else index
        for old_unit in roster.records[side]:
            if old_unit[0x90] == new_index:
                old_unit[0x90] = 255
        unit[0x90] = new_index
        if index is None:
            b.extend(record)
        else:
            b[index*36:(index+1)*36] = record
    roster.header[0x3a2 + side] = len(b) // 36
    # RommelPlan can overwrite authored leader assignments on initialization.
    roster.header[0x3d6] = 0
    return roster.to_bytes()


def replacement_schedule(roster, side):
    side = _side(side)
    days = short(roster.blocks['calendar'], 24)
    b = roster.blocks[f'reps{side}']
    if days < 1 or len(b) % 9:
        raise ValueError('Invalid replacement schedule')
    # Older editor/converter versions wrote only two rows regardless of length.
    b = b + bytes(max(0, days*9 - len(b)))
    return [tuple(b[p:p+9]) for p in range(0, days*9, 9)]


def replacement_pool(roster, side):
    p = 0x3a6 + _side(side)*10
    return tuple(roster.header[p:p+9])


def normalize_replacements(data):
    """Repair short legacy authoring tables on save/export, without losing rows."""
    roster = UnitRoster(data)
    for side in (0, 1):
        rows = replacement_schedule(roster, side)
        key = f'reps{side}'
        if len(roster.blocks[key]) < len(rows)*9:
            roster.blocks[key] = bytearray(v for row in rows for v in row)
    return roster.to_bytes()


def set_replacements(data, side, values, first=None, last=None):
    """Edit a daily range, or the initial pool when first/last are omitted.

    Only the seven categories actually used by D-Day are exposed; preserve the
    two reserved columns and the padding byte in each initial pool.
    """
    roster = UnitRoster(normalize_replacements(data))
    side = _side(side)
    quantities = {key: _integer(values[key], name, 0, 255)
                  for key, name in REPLACEMENT_TYPES.items()}
    if first is None and last is None:
        b, offsets = roster.header, [0x3a6 + side*10]
    else:
        days = short(roster.blocks['calendar'], 24)
        first = _integer(first, 'First day', 1, days)
        last = _integer(last, 'Last day', first, days)
        b, offsets = roster.blocks[f'reps{side}'], range((first-1)*9, last*9, 9)
    for p in offsets:
        for key, value in quantities.items():
            b[p+key] = value
    return roster.to_bytes()


def garrisons(roster):
    b = _records(roster, 'garrison', roster.header[0x1223], 6)
    rows = [dict(x=x, y=y, radius=r, hqs=[]) for x, y, r in struct.iter_unpack('<3h', b)]
    for side in (0, 1):
        for hq in headquarters(roster, side):
            index = roster.records[side][hq['index']][0x7e]
            if index < len(rows):
                rows[index]['hqs'].append((side, hq['id']))
    return rows


def edit_garrison(data, index, values=None):
    roster = UnitRoster(data)
    rows = garrisons(roster)
    if index is not None:
        index = _index(index, len(rows), 'Garrison')
    b = roster.blocks.setdefault('garrison', bytearray())
    if values is None:
        if index is None:
            raise ValueError('Choose a garrison to remove')
        del b[index*6:(index+1)*6]
        for side in (0, 1):
            for hq in headquarters(roster, side):
                unit = roster.records[side][hq['index']]
                if unit[0x7e] == index:
                    unit[0x7e] = 255
                elif index < unit[0x7e] < len(rows):
                    unit[0x7e] -= 1
    else:
        if index is None and len(rows) >= 128:
            raise ValueError('A scenario can have at most 128 garrisons')
        x, y = _point(roster, values['x'], values['y'])
        radius = _integer(values['radius'], 'Garrison radius', 0, 32767)
        assigned = set()
        for side, hq in values['hqs']:
            side = _side(side)
            hqs = headquarters(roster, side)
            hq = _index(hq, len(hqs), 'HQ')
            if hqs[hq]['deleted']:
                raise ValueError('Restore the HQ before assigning a garrison')
            assigned.add((side, hq))
        new_index = len(rows) if index is None else index
        for side in (0, 1):
            for hq in headquarters(roster, side):
                unit = roster.records[side][hq['index']]
                if (side, hq['id']) in assigned:
                    unit[0x7e] = new_index
                elif unit[0x7e] == new_index:
                    unit[0x7e] = 255
        record = struct.pack('<3h', x, y, radius)
        if index is None:
            b.extend(record)
        else:
            b[index*6:(index+1)*6] = record
    roster.header[0x1223] = len(b)//6
    # Prevent the Cherbourg variant from replacing authored HQ assignments.
    roster.header[0x3d2] = 0
    return roster.to_bytes()


def invalidate_supply_entries(roster, side):
    """HQ+2c and Depot+18 cache ENTRY indices in the first stock record."""
    hqs = roster.blocks[f'hqs{side}']
    for p in range(0, len(hqs), 58):
        put_short(hqs, p+0x2c, 99)
    b = roster.blocks[f'depot{side}']
    for p in range(24, len(b), 24):
        b[p+18] = 99


def add_supply_group(data, side):
    roster = UnitRoster(data)
    side = _side(side)
    count = roster.count(0x25c, side)
    _records(roster, f'stock{side}', count, 136)
    if count >= 32767:
        raise ValueError('Supply group limit reached')
    record = bytearray(136)
    record[4:108] = b'\xff'*104
    roster.blocks[f'stock{side}'].extend(record)
    put_short(roster.header, 0x25c+side*2, count+1)
    return roster.to_bytes()


def remove_supply_group(data, side, index):
    roster = UnitRoster(data)
    side = _side(side)
    count = roster.count(0x25c, side)
    b = _records(roster, f'stock{side}', count, 136)
    index = _index(index, count, 'Supply group')
    if count <= 1:
        raise ValueError('Keep at least one supply group for each side')
    del b[index*136:(index+1)*136]
    put_short(roster.header, 0x25c+side*2, count-1)
    if index == 0:
        invalidate_supply_entries(roster, side)
    return roster.to_bytes()


def depots(roster, side):
    side = _side(side)
    b = _records(roster, f'depot{side}', roster.header[0x3a0+side], 24)
    return [dict(stock=struct.unpack_from('<i', b, p)[0],
                 capacity=struct.unpack_from('<i', b, p+4)[0],
                 x=short(b, p+12), y=short(b, p+14),
                 captured=bool(b[p+20]), land=bool(b[p+21]), distribute=bool(b[p+22]))
            for p in range(0, len(b), 24)]


def edit_depot(data, side, index, values=None):
    roster = UnitRoster(data)
    side = _side(side)
    rows = depots(roster, side)
    if index is not None:
        index = _index(index, len(rows), 'Depot')
    b = roster.blocks[f'depot{side}']
    if values is None:
        if index is None or index == 0:
            raise ValueError('The reserve depot must remain in the scenario')
        del b[index*24:(index+1)*24]
        hqs = roster.blocks[f'hqs{side}']
        for p in range(0, len(hqs), 58):
            cached = short(hqs, p+0x2a)
            if cached == index:
                put_short(hqs, p+0x2a, -4)
            elif index < cached < len(rows):
                put_short(hqs, p+0x2a, cached-1)
    else:
        if index is None and len(rows) >= 255:
            raise ValueError('A side can have at most 255 depots including its reserve')
        stock = _integer(values['stock'], 'Depot stock', 0, 2147483647)
        capacity = _integer(values['capacity'], 'Depot capacity', 0, 2147483647)
        record = bytearray(24) if index is None else bytearray(b[index*24:(index+1)*24])
        struct.pack_into('<2i', record, 0, stock, capacity)
        if index != 0:
            x, y = _point(roster, values['x'], values['y'])
            struct.pack_into('<2h', record, 12, x, y)
            for key, offset in (('captured', 20), ('land', 21), ('distribute', 22)):
                record[offset] = _flag(values[key], key.capitalize())
            if index is None or (x, y, bool(record[21])) != (rows[index]['x'], rows[index]['y'], rows[index]['land']):
                record[17], record[18] = 252, 99
        if index is None:
            b.extend(record)
        else:
            b[index*24:(index+1)*24] = record
    roster.header[0x3a0+side] = len(b)//24
    return roster.to_bytes()


def ground_conditions(roster):
    return struct.unpack_from('<3i', roster.blocks['weather'])


def set_ground_conditions(data, snow, ice, wetness):
    roster = UnitRoster(data)
    values = [_integer(v, name, 0, 2147480000)
              for v, name in zip((snow, ice, wetness), ('Snow', 'Ice', 'Wetness'))]
    struct.pack_into('<3i', roster.blocks['weather'], 0, *values)
    return roster.to_bytes()


def refresh_calendar(roster):
    """Refresh UTParser/SetCalVars date fields without touching relative counters."""
    from lib.scenario_conditions import weather_sequence
    from lib.scenario_rules import turns_per_day
    per_day = turns_per_day(roster)
    cal = roster.blocks['calendar']
    current = struct.unpack_from('<i', cal, 12)[0]
    end = struct.unpack_from('<i', cal, 8)[0]
    today, last = [EPOCH + timedelta(days=t//per_day) for t in (current, end)]
    put_short(cal, 26, today.year)
    cal[30:32] = bytes((last.day, last.month-1))
    month, phase = today.month-1, current % per_day
    season = 0 if month in (0, 10, 11) else 1 if month <= 3 else 2 if month >= 7 else 3
    night = (phase == 2 if season == 0 and roster.header[0x122b] == 3
             else phase in ((0, 5) if season == 3 else (0, 4, 5)))
    moon = int(current / 22.151) % 8
    start, _ = scenario_dates(roster)
    sequence = weather_sequence(roster)
    weather = sequence[max(0, min(len(sequence)-1, current-start))][1]
    visibility = (1 if moon == 4 and weather < 3 else 2) if night else int(weather == 4)
    new_day = phase == (0 if roster.header[0x122b] == 3 else 1)
    cal[33:41] = bytes((phase, today.day, month, season, moon, visibility, int(night), int(new_day)))


def set_start_date(data, start_date):
    """Rebase absolute dates, retaining phase, duration and relative schedules."""
    from lib.scenario_conditions import weather_sequence, store_weather
    from lib.scenario_rules import turns_per_day
    roster = UnitRoster(data)
    try:
        day = date.fromisoformat(start_date)
    except (TypeError, ValueError) as exc:
        raise ValueError('Enter the start date as YYYY-MM-DD') from exc
    if not 1939 <= day.year <= 1945:
        raise ValueError('Choose a date from 1939 through 1945')
    start, end = scenario_dates(roster)
    per_day = turns_per_day(roster)
    delta = ((day-EPOCH).days - start//per_day)*per_day
    if not delta:
        return data
    sequence = weather_sequence(roster)
    struct.pack_into('<2i', roster.header, 0x44, start+delta, end+delta)
    for offset in (0, 4, 8, 12):
        cal = roster.blocks['calendar']
        struct.pack_into('<i', cal, offset, struct.unpack_from('<i', cal, offset)[0]+delta)
    for units in roster.records:
        for unit in units:
            arrival = struct.unpack_from('<i', unit, 8)[0]
            if arrival != -1:
                struct.pack_into('<i', unit, 8, arrival+delta)
            destroyed = struct.unpack_from('<i', unit, 0x40)[0]
            if destroyed > 0:
                struct.pack_into('<i', unit, 0x40, destroyed+delta)
    store_weather(roster, sequence)
    refresh_calendar(roster)
    return roster.to_bytes()
