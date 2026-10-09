"""Authored weather and supply, using the engine's RWWeather/RWStock layouts."""
import struct

from lib.unit_roster import UnitRoster, short, put_short
from lib.weather_reader import NATIVE_SIZE, EXTENDED_SIZE, NATIVE_DATES, CAPACITY
from lib.scenario_rules import scenario_dates

WEATHER_NAMES = ('Clear', 'Light overcast', 'Moderate overcast', 'Heavy overcast', 'Storm')


def weather_sequence(roster):
    block = roster.blocks['weather']
    start, end = scenario_dates(roster)
    if len(block) == NATIVE_SIZE:
        origin, last = NATIVE_DATES[roster.header[0x1220]]
        code_offset = 0x214
    elif len(block) == EXTENDED_SIZE:
        origin, last = struct.unpack_from('<2i', block, 0x4be)
        code_offset = 0x32c
    else:
        raise ValueError('Unsupported weather layout')
    if not 0 < end-start+1 <= CAPACITY:
        raise ValueError('Weather supports at most 400 turns')
    result = []
    for timestamp in range(start, end+1):
        i = max(0, min(timestamp, last)-origin)
        if i >= (260 if code_offset == 0x214 else CAPACITY):
            raise ValueError('Weather dates exceed the stored table')
        result.append((short(block, 12+2*i), block[code_offset+i]))
    return result


def set_weather(data, first, last, temperature, code):
    roster = UnitRoster(data)
    sequence = weather_sequence(roster)
    first, last, temperature, code = map(int, (first, last, temperature, code))
    if not 1 <= first <= last <= len(sequence):
        raise ValueError('Choose a turn range within the scenario')
    if not -100 <= temperature <= 150 or not 0 <= code <= 4:
        raise ValueError('Temperature must be −100 to 150 °F; weather code must be 0–4')
    sequence[first-1:last] = [(temperature, code)] * (last-first+1)
    store_weather(roster, sequence)
    roster.header[0x1227] = 0  # Historical: use the authored sequence.
    return roster.to_bytes()


def store_weather(roster, sequence):
    """Store relative weather against the current authored scenario dates."""
    sequence = list(sequence) + [sequence[-1]] * (CAPACITY-len(sequence))
    old = roster.blocks['weather']
    block = bytearray(EXTENDED_SIZE)
    block[:12] = old[:12]
    flag = 0x318 if len(old) == NATIVE_SIZE else 0x4bc
    block[0x4bc:0x4be] = old[flag:flag+2]
    for i, (temp, condition) in enumerate(sequence):
        put_short(block, 12+i*2, temp)
        block[0x32c+i] = condition
    struct.pack_into('<2i', block, 0x4be, *scenario_dates(roster))
    roster.blocks['weather'] = block


def supply_groups(roster, side):
    block = roster.blocks[f'stock{side}']
    if len(block) != roster.count(0x25c, side)*136:
        raise ValueError('Invalid supply stock table')
    groups = []
    for pos in range(0, len(block), 136):
        count = short(block, pos+108)
        if not 0 <= count <= 26:
            raise ValueError('Invalid supply entry count')
        groups.append(dict(stock=struct.unpack_from('<i', block, pos)[0], entries=[
            (short(block, pos+4+i*2), short(block, pos+56+i*2), block[pos+110+i])
            for i in range(count)]))
    return groups


def set_supply_group(data, side, group, stock, entries):
    roster = UnitRoster(data)
    side, group, stock = map(int, (side, group, stock))
    if side not in (0, 1) or not 0 <= group < roster.count(0x25c, side):
        raise ValueError('Select a supply group')
    if not 0 <= stock <= 2147483647 or len(entries) > 26:
        raise ValueError('Stock must be nonnegative; a group holds at most 26 entry hexes')
    top, left, bottom, right = struct.unpack_from('<4h', roster.header, 0x224)
    normalized = [tuple(map(int, row)) for row in entries]
    if any(not (left <= x < right and top <= y < bottom and 0 <= flag <= 255)
           for x, y, flag in normalized):
        raise ValueError('Supply entries must be within the playable map')
    if len({(x, y) for x, y, _ in normalized}) != len(normalized):
        raise ValueError('Duplicate supply entry hex')
    if group == 0 and supply_groups(roster, side)[0]['entries'] != normalized:
        from lib.scenario_data import invalidate_supply_entries
        invalidate_supply_entries(roster, side)
    block = roster.blocks[f'stock{side}']
    pos = group*136
    struct.pack_into('<i', block, pos, stock)
    block[pos+4:pos+108] = b'\xff'*104
    put_short(block, pos+108, len(normalized))
    block[pos+110:pos+136] = bytes(26)
    for i, (x, y, flag) in enumerate(normalized):
        put_short(block, pos+4+i*2, x)
        put_short(block, pos+56+i*2, y)
        block[pos+110+i] = flag
    return roster.to_bytes()


def daily_supply(roster):
    block = roster.blocks['supply']
    if len(block) != short(roster.blocks['calendar'], 24)*4:
        raise ValueError('Invalid daily supply table')
    return list(struct.iter_unpack('<2h', block))


def set_daily_supply(data, first, last, allied, axis):
    roster = UnitRoster(data)
    rows = daily_supply(roster)
    first, last, allied, axis = map(int, (first, last, allied, axis))
    if not 1 <= first <= last <= len(rows) or not all(0 <= v <= 32767 for v in (allied, axis)):
        raise ValueError('Choose valid days and daily quantities between 0 and 32767')
    for day in range(first-1, last):
        struct.pack_into('<2h', roster.blocks['supply'], day*4, allied, axis)
    return roster.to_bytes()
