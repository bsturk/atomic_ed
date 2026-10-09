"""Verified scenario authoring fields (Calendar, VicLoc and loss scoring).

Code addresses refer to the D-Day protected-mode executable, not the DOS stub.
GetVicLevel 52133h uses fixed 2.0 / 1.25 ratios. TabulateCities 52e78h reads
VicLoc+0xc/+0xe; the dwords at +0/+4 are accumulated scores, not point values.
"""
from datetime import date, timedelta
import struct

from lib.game_resources import GAME_ROOT
from lib.unit_roster import UnitRoster, short, put_short
from lib.weather_reader import EXTENDED_SIZE, NATIVE_DATES

EPOCH = date(1900, 1, 1)
LOSS_CLASSES = ('Infantry', 'Armor', 'Engineer', 'Anti-tank', 'Artillery', 'Ships', 'Aircraft', 'HQ', 'Anti-aircraft')


def synchronize_occupancy(data):
    """InitUnitMap needs saved stacking and ownership to load placed units.

    Preserve other ZOC bits. Only the occupancy nibble and occupied ownership
    derive from the OOB; an empty hex keeps its territorial owner.
    """
    roster = UnitRoster(data)
    width, height = short(roster.header, 0x22a)+1, short(roster.header, 0x228)+1
    current = struct.unpack_from('<i', roster.blocks['calendar'], 12)[0]
    stacks = {}
    for side in (0, 1):
        for record in roster.records[side][:roster.count(0x240, side)]:
            arrival = struct.unpack_from('<i', record, 8)[0]
            x, y = struct.unpack_from('<2h', record, 0x58)
            if record[0x76] == 7:
                hq = struct.unpack_from('<i', record, 4)[0]
                roster.blocks[f'hqs{side}'][hq*58+0x38] = int(
                    arrival != -1 and arrival < current and 0 <= x < width and 0 <= y < height)
            if arrival == -1 or arrival >= current or not (0 <= x < width and 0 <= y < height):
                continue
            owner, size = stacks.get((x, y), (side, 0))
            if owner != side:
                raise ValueError(f'Opposing units cannot occupy the same hex ({x}, {y})')
            weight = (4 if roster.header[0x122b] == 1 else 3) if record[0x76] == 7 else record[0x7e]
            stacks[x, y] = side, size + weight
    block = roster.blocks['zoc']
    if len(block) != width*height*4:
        raise ValueError('Invalid ownership map')
    for y in range(height):
        for x in range(width):
            offset = (y*width+x)*4
            word = struct.unpack_from('<I', block, offset)[0] & ~0x1e0000
            if (x, y) in stacks:
                side, size = stacks[x, y]
                word = (word & ~0x10000) | side << 16 | min(15, size) << 17
            struct.pack_into('<I', block, offset, word)
    return roster.to_bytes()


def scenario_dates(roster):
    return struct.unpack_from('<2i', roster.header, 0x44)


def turns_per_day(roster):
    value = roster.blocks['calendar'][28]
    if value not in (3, 6):
        raise ValueError('Unsupported calendar turn scale')
    return value


def date_label(timestamp, per_day=6):
    return f'{EPOCH + timedelta(days=timestamp // per_day)} · turn {timestamp % per_day + 1} of day'


def authoring_warnings(data):
    """Check actual blocks and identify unfinished parts of a new document."""
    from lib.weather_reader import validate_weather
    roster = UnitRoster(data)
    validate_weather(roster.blocks['weather'])
    notes = []
    if not objectives(roster):
        notes.append('No victory objectives: scoring will depend on enemy losses alone.')
    current = struct.unpack_from('<i', roster.blocks['calendar'], 12)[0]
    for side in (0, 1):
        name = ('Allied', 'Axis')[side]
        if not roster.count(0x23c, side):
            notes.append(f'{name}: add an HQ before playing.')
        if not any(-1 < struct.unpack_from('<i', u, 8)[0] < current and short(u, 0x58) >= 0
                   and short(u, 0x5a) >= 0 for u in roster.records[side][:roster.count(0x240, side)]):
            notes.append(f'{name}: no ground units deployed at the start.')
    synchronize_occupancy(data)  # Also rejects mixed-side stacks.
    return notes


def objectives(roster):
    block = roster.blocks['vicloc']
    if len(block) != roster.header[0x1222] * 48:
        raise ValueError('Objective count does not match the victory-location block')
    return [dict(name=block[i+22:i+48].split(b'\0')[0].decode('cp437'),
                 x=short(block, i+8), y=short(block, i+10),
                 allied=short(block, i+12), axis=short(block, i+14),
                 radius=block[i+16], owner=block[i+17])
            for i in range(0, len(block), 48)]


def edit_objective(data, index, values=None):
    """Add/update/delete a VicLoc, preserving scores and opaque state on edit."""
    roster = UnitRoster(data)
    count = len(objectives(roster))
    if index is not None and not 0 <= index < count:
        raise ValueError('Choose an objective')
    block = roster.blocks['vicloc']
    if values is None:
        if index is None:
            raise ValueError('Choose an objective to remove')
        from lib.battle_plans import battle_plans, set_battle_plans, plan_conditions
        plans = battle_plans(roster)
        conditions = [c for p in plans for c in plan_conditions(p)]
        if any(p.get('trigger') == 1 and p['objective'] == index for p in conditions):
            raise ValueError('This objective is used by a Battle Plans condition. Change or remove that plan first.')
        for plan in conditions:
            if plan.get('trigger') == 1 and plan['objective'] > index:
                plan['objective'] -= 1
        del block[index*48:(index+1)*48]
    else:
        if index is None and count >= 30:
            raise ValueError('The editor supports up to 30 objectives')
        try:
            name = values['name'].strip().encode('cp437')
        except UnicodeEncodeError as exc:
            raise ValueError('Use DOS characters in objective names') from exc
        if not 1 <= len(name) <= 25 or any(c < 32 or c == 127 for c in name):
            raise ValueError('Objective names need 1–25 printable DOS characters')
        v = {key: int(values[key]) for key in ('x', 'y', 'allied', 'axis', 'radius', 'owner')}
        for key, maximum in (('x', short(roster.header, 0x22a)-1), ('y', short(roster.header, 0x228)-1),
                             ('allied', 32767), ('axis', 32767), ('radius', 2), ('owner', 1)):
            if not 0 <= v[key] <= maximum:
                raise ValueError(f'{key.capitalize()} must be between 0 and {maximum}')
        record = bytearray(48) if index is None else bytearray(block[index*48:(index+1)*48])
        old = objectives(roster)[index] if index is not None else None
        struct.pack_into('<4h', record, 8, v['x'], v['y'], v['allied'], v['axis'])
        record[16] = v['radius']
        if old is None or any(old[k] != v[k] for k in ('x', 'y', 'owner')):
            # Initial control has to agree with the hex ownership map as well.
            for side, units in enumerate(roster.records):
                for unit in units[:roster.count(0x240, side)]:
                    arrival = struct.unpack_from('<i', unit, 8)[0]
                    current = struct.unpack_from('<i', roster.blocks['calendar'], 12)[0]
                    if (side != v['owner'] and arrival != -1 and arrival < current
                            and struct.unpack_from('<2h', unit, 0x58) == (v['x'], v['y'])):
                        raise ValueError('Initial owner conflicts with a deployed unit at this hex')
            record[17:21] = bytes((v['owner'], v['owner'], v['owner'], v['owner']))
            offset = (v['y'] * (short(roster.header, 0x22a) + 1) + v['x']) * 4
            word = struct.unpack_from('<I', roster.blocks['zoc'], offset)[0]
            struct.pack_into('<I', roster.blocks['zoc'], offset, (word & ~0x10000) | v['owner'] << 16)
        record[22:48] = name.ljust(26, b'\0')
        if index is None:
            block.extend(record)
        else:
            block[index*48:(index+1)*48] = record
    roster.header[0x1222] = len(block) // 48
    if values is None and plans:
        return set_battle_plans(roster.to_bytes(), plans)
    return roster.to_bytes()


def set_rules(data, turns, loss_values):
    roster = UnitRoster(data)
    start, end = scenario_dates(roster)
    turns = int(turns)
    # Patch v4 extends both weather and victory history to 400 turns.
    if turns != end - start + 1:
        if not 2 <= turns <= 400:
            raise ValueError('Choose 2–400 turns')
        new_end = start + turns - 1
        current = struct.unpack_from('<i', roster.blocks['calendar'], 12)[0]
        if new_end < current:
            raise ValueError('The end must not precede the current turn')
        late = [u for side in roster.records for u in side
                if end >= struct.unpack_from('<i', u, 8)[0] > new_end]
        if late:
            raise ValueError('Move scheduled reinforcements earlier before shortening the scenario')
        from lib.battle_plans import battle_plans
        if any(p['last'] > turns for p in battle_plans(roster)):
            raise ValueError('Shorten battle plan phases before shortening the scenario')
        weather = roster.blocks['weather']
        if len(weather) == EXTENDED_SIZE:
            weather_start, weather_end = struct.unpack_from('<2i', weather, 0x4be)
            temp_offset, code_offset = 12, 0x32c
        elif len(weather) == 794 and roster.header[0x1220] < 7:
            weather_start, weather_end = NATIVE_DATES[roster.header[0x1220]]
            temp_offset, code_offset = 12, 0x214
        else:
            raise ValueError('Unsupported weather layout')
        extended = bytearray(EXTENDED_SIZE)
        extended[:12] = weather[:12]
        flags = 0x4bc if len(weather) == EXTENDED_SIZE else 0x318
        extended[0x4bc:0x4be] = weather[flags:flags+2]
        for i in range(400):
            source = max(0, min(start + i, weather_end) - weather_start)
            struct.pack_into('<h', extended, 12 + 2*i, short(weather, temp_offset + 2*source))
            extended[0x32c+i] = weather[code_offset+source]
        struct.pack_into('<2i', extended, 0x4be, start, new_end)
        roster.blocks['weather'] = extended
        struct.pack_into('<i', roster.header, 0x48, new_end)
        cal = roster.blocks['calendar']
        struct.pack_into('<i', cal, 8, new_end)
        supply_start = struct.unpack_from('<i', cal, 4)[0]
        per_day = turns_per_day(roster)
        days = new_end // per_day - supply_start // per_day + 1
        put_short(cal, 24, days)
        end_date = EPOCH + timedelta(days=new_end // per_day)
        cal[30:32] = bytes((end_date.day, end_date.month - 1))
        supply = roster.blocks['supply']
        roster.blocks['supply'] = (supply + supply[-4:] * days)[:days*4]
        for side in (0, 1):
            # Future days start with no replacements; retain existing rows.
            block = roster.blocks[f'reps{side}']
            roster.blocks[f'reps{side}'] = (block + bytes(days*9))[:days*9]
    if len(loss_values) != len(LOSS_CLASSES):
        raise ValueError('Missing casualty scoring values')
    for i, value in enumerate(loss_values):
        value = int(value)
        if not 0 <= value <= 10000:
            raise ValueError('Casualty scoring weights must be between 0 and 10000')
        struct.pack_into('<i', roster.header, 4 + i*4, value)
    return roster.to_bytes()


def new_scenario(width=30, height=24, terrain=1, start_date='1944-06-12', turns=12):
    """Empty authoring document using native D-Day structural defaults.

    Cobra (ID 3) supplies ordinary attack/defend AI roles without Bradley's
    coordinate-specific special objectives. Native engine artwork remains valid.
    """
    width, height, terrain, turns = map(int, (width, height, terrain, turns))
    if not 4 <= width <= 125 or not 4 <= height <= 125:
        raise ValueError('Map size must be 4–125 columns by 4–125 rows')
    if not 0 <= terrain <= 13 or not 2 <= turns <= 400:
        raise ValueError('Choose terrain 0–13 and a duration of 2–400 turns')
    day = date.fromisoformat(start_date)
    if not 1939 <= day.year <= 1945:
        raise ValueError('Choose a date from 1939 through 1945')
    start = (day - EPOCH).days * 6 + 1  # native scenarios open in the morning
    end = start + turns - 1
    last = EPOCH + timedelta(days=end//6)
    days = end//6 - start//6 + 1
    roster = UnitRoster((GAME_ROOT / 'dday/SCENARIO/BRADLEY.SCN').read_bytes())
    b, h = roster.blocks, roster.header
    struct.pack_into('<2i', h, 0x44, start, end)
    h[0x4c:0x54] = bytes(8)
    struct.pack_into('<4h', h, 0x224, 0, 0, height-1, width-1)
    h[0x22c:0x234] = h[0x224:0x22c]
    struct.pack_into('<2h', h, 0x234, width//2, height//2)
    h[0x23c:0x260] = bytes(0x24)
    h[0x260:0x31c] = bytes(0xbc)
    h[0x3a0:0x3a4] = bytes((1, 1, 0, 0))  # one depot descriptor per side
    h[0x3a6:0x3ba] = bytes(20)  # empty initial replacement pools
    h[0x3ca:0x3d9] = bytes(15)  # no optional scenario variants
    h[0x3e0:0x1220] = bytes(0xe40)  # empty briefings and all 50 label slots
    # NameInHex reads the label count at +122a, not +1221. Clear it and
    # initialize unused labels off map with valid drawing styles.
    h[0x122a] = 0
    for i in range(50):
        struct.pack_into('<2h', h, 0xbe0+i*32, -1, -1)
        h[0xbfe+i*32:0xc00+i*32] = bytes((12, ord('V')))
    h[0x1220:0x1224] = bytes((3, 0, 0, 0))
    h[0x1227] = h[0x1229] = 0
    cal = b['calendar']
    struct.pack_into('<6i2h', cal, 0, start, start, end, start, 0, 0, days, day.year)
    cal[28] = 6
    cal[30:32] = bytes((last.day, last.month-1))
    cal[33:37] = bytes((start % 6, day.day, day.month-1, 3))
    cal[37:] = bytes(5)
    b['hexmap'] = bytes(width*height*2)
    b['uhexes'] = struct.pack('<I', terrain)
    b['zoc'] = b''.join(struct.pack('<I', (y >= height//2) << 16)
                        for y in range(height) for x in range(width))
    b['hedgelist'] = struct.pack('<H', 0xfde8) * width*height
    b['hedges'] = bytes(8)
    b['weather'] = bytearray(EXTENDED_SIZE)
    struct.pack_into('<400h', b['weather'], 12, *([65]*400))
    struct.pack_into('<2i', b['weather'], 0x4be, start, end)
    b['supply'] = struct.pack('<2h', 1250, 1250) * days
    for side in (0, 1):
        for key in ('ob', 'hqs', 'hqlist', 'arty', 'tanks', 'riders', 'autoart', 'autognd'):
            b[f'{key}{side}'] = bytearray()
        b[f'reps{side}'] = bytes(days*9)
        stock = bytearray(136)
        struct.pack_into('<i', stock, 0, 50000)
        put_short(stock, 4, width//2)
        put_short(stock, 56, 0 if side == 0 else height-2)
        put_short(stock, 108, 1)
        b[f'stock{side}'] = stock
        put_short(h, 0x25c+side*2, 1)
        b[f'depot{side}'] = bytearray(b[f'depot{side}'][:24])
    b['victory'] = bytes(1088)
    b['vicloc'] = bytearray()
    b['ai_counts'] = bytes(12)
    for key in ('bgstate', 'bgshx', 'bgshy', 'bgdhx', 'bgdhy'):
        b[key] = bytes(800)
    for key in ('planeclass', 'planecounts', 'shipclass'):
        b[key] = bytes(len(b[key]))
    b['hqheads'] = b'\xff' * 16
    roster.records, roster.orders, roster.trailer = [[], []], {}, b''
    from lib.scenario_data import refresh_calendar
    refresh_calendar(roster)
    return roster.to_bytes()
