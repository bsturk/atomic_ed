"""Read D-Day's two fixed-record order-of-battle blocks (RWOB)."""
import struct
from decimal import Decimal, InvalidOperation

from lib.unit_types import unit_type_name

from lib.terrain_reader import _read_block
from lib.counter_artwork import load_counters


def read_units(scenario, counters=None, presentation=None):
    if not scenario or not scenario.is_valid:
        return []
    blocks, starts = [], []
    offset = 0
    try:
        for _ in range(9):
            starts.append(offset + 4)
            block, offset = _read_block(scenario.data, offset)
            blocks.append(block)
        header, calendar = blocks[:2]
        if len(header) != 0x1230 or len(calendar) != 0x2a:
            return []
        # UNIT_IN_PLAY compares arrival with Calendar+0x0c, strictly less.
        current_time = struct.unpack_from('<i', calendar, 0x0c)[0]
        start_time, end_time = struct.unpack_from('<2i', header, 0x44)
        counter_resource = struct.unpack_from('<h', header, 0x238)[0]
        counts = struct.unpack_from('<2H', header, 0x244)
        if any(len(blocks[7 + side]) != counts[side] * 0xac for side in (0, 1)):
            return []
    except (ValueError, struct.error):
        return []

    automation = _read_hq_automation(scenario.data, header, offset)
    counters = load_counters(scenario.filename) if counters is None else counters
    if presentation is None:
        from lib.presentation_artwork import load_presentation
        presentation = load_presentation(scenario.filename)
    units = []
    for side, side_name in enumerate(('Allied', 'Axis')):
        block = blocks[7 + side]
        for index in range(counts[side]):
            offset = index * 0xac
            record = block[offset:offset + 0xac]
            arrival = struct.unpack_from('<i', record, 8)[0]
            units.append({
                'index': len(units), 'side_index': index,
                'side': side_name, 'map_width': scenario.map_width,
                'map_height': scenario.map_height,
                'arrival_time': arrival, 'current_time': current_time,
                'start_time': start_time, 'end_time': end_time,
                'in_play': arrival != -1 and arrival < current_time,
                'counter_index': struct.unpack_from('<h', record, 0x56)[0],
                'counter_resource': counter_resource + record[0x74],
                'counter_bitmap': counters.get(counter_resource + record[0x74]),
                'section': f'OB {side_name}',
                'offset': starts[7 + side] + offset + 0x92,
                'record_offset': starts[7 + side] + offset,
                **decode_record(record),
            })
    hq_names = {(u['side'], struct.unpack_from('<h', bytes.fromhex(u['raw_data']), 4)[0]): u['name']
                for u in units if u['unit_class'] == 7}
    for unit in units:
        if unit['unit_class'] in (5, 6):
            from lib.support_units import artwork_key
            try:
                key = artwork_key(unit['unit_class'], unit['type'], int(unit['side'] == 'Axis'))
                unit['support_artwork'] = presentation.get(key)
            except ValueError:
                pass  # Preserve an unknown native descriptor for inspection.
            continue
        side = 0 if unit['side'] == 'Allied' else 1
        hq = unit['hq_index']
        unit['hq_name'] = hq_names.get((unit['side'], hq), f'HQ {hq + 1}')
        for key in HQ_AUTOMATION_FIELDS:
            if (side, key) in automation:
                start, block = automation[side, key]
                if hq < len(block):
                    unit[key] = block[hq]
                    unit[key + '_offset'] = start + hq
    return units


HQ_AUTOMATION_FIELDS = ('hq_auto_ground', 'hq_auto_artillery')


def _read_hq_automation(data, header, offset):
    """LoadGame: four per-HQ byte arrays after Victory/VicLoc.

    Keep OB reading usable if the optional metadata is missing or truncated;
    in that case the editor must not offer automation edits.
    """
    try:
        # Weather, supply, two stock arrays, two depot arrays; optional garrison;
        # then victory and victory-location arrays.
        for _ in range(8 + bool(header[0x1223])):
            _, offset = _read_block(data, offset)
        counts = struct.unpack_from('<2H', header, 0x23c)
        result = {}
        for key in ('hq_auto_artillery', 'hq_auto_ground'):
            for side in (0, 1):
                start = offset + 4
                block, offset = _read_block(data, offset)
                if len(block) != counts[side]:
                    return {}
                result[side, key] = start, block
        return result
    except (ValueError, struct.error):
        return {}


# PrintMode indexes ModeStr / Mode2Str with the low / high nibble of OB+0x78.
TACTICAL_ORDERS = ('Tactical movement', 'Strategic movement', 'Passenger', 'Auto movement',
                   'Probe', 'Assault without advance', 'Assault', 'All-out assault',
                   'Retreat if attacked', 'Defend if attacked', 'Hold at all costs')
SECONDARY_ORDERS = ('', 'Replace', 'Dig in', 'Fortify', 'Prepare', 'Target', 'On call',
                    'Counter battery', "Shoot 'n scoot")


def unit_order_label(unit):
    if unit['unit_class'] in (5, 6):
        return 'Not applicable to aircraft or ships'
    mode = unit['order_mode']
    primary, secondary = mode & 15, mode >> 4
    order = TACTICAL_ORDERS[primary] if primary < len(TACTICAL_ORDERS) else f'Unknown order ({primary})'
    extra = SECONDARY_ORDERS[secondary] if secondary < len(SECONDARY_ORDERS) else f'Unknown modifier ({secondary})'
    return f'{order} · {extra}' if extra else order


# Values called "Attack"/"Defense" by the old editor were quality bytes.
# PrintData displays these fixed-point strengths in units of 1,000.
STRENGTH_FIELDS = {
    'attack_base': 0x14, 'defense_base': 0x18,
    'attack_current': 0x20, 'defense_current': 0x24,
    'armor_base': 0x28, 'antitank_base': 0x2c,
    'armor_current': 0x30, 'antitank_current': 0x34,
}
QUALITY_FIELDS = {'quality': 0x89, 'attack_quality': 0x8a, 'defense_quality': 0x8b,
                  'disruption': 0x8c, 'fatigue': 0x8d}
EDITABLE_FIELDS = {
    'name': (0x92, 'name', 1), 'x': (0x58, '<h', 1), 'y': (0x5a, '<h', 1),
    'arrival_time': (0x08, '<i', 1),
    'counter_index': (0x56, '<h', 1),
    **{key: (offset, '<i', 1000) for key, offset in STRENGTH_FIELDS.items() if key.endswith('_base')},
    **{key: (QUALITY_FIELDS[key], '<b', 1) for key in ('quality', 'disruption', 'fatigue')},
}


def decode_record(record):
    unit_class, type_code = record[0x76:0x78]
    return {
        'arrival_time': struct.unpack_from('<i', record, 8)[0],
        'deleted': (struct.unpack_from('<i', record, 8)[0] == -1
                    and struct.unpack_from('<h', record, 0x64)[0] == 0
                    and struct.unpack_from('<2h', record, 0x58) == (-1, -1)),
        'name': record[0x92:0xac].split(b'\0', 1)[0].decode('cp437').strip(),
        'x': struct.unpack_from('<h', record, 0x58)[0],
        'counter_index': struct.unpack_from('<h', record, 0x56)[0],
        'y': struct.unpack_from('<h', record, 0x5a)[0],
        'type': type_code, 'unit_class': unit_class,
        'order_mode': record[0x78], 'hq_index': record[0x81],
        'type_name': unit_type_name(type_code, unit_class),
        **{key: struct.unpack_from('<i', record, offset)[0] / 1000
           for key, offset in STRENGTH_FIELDS.items()},
        **{key: struct.unpack_from('<b', record, offset)[0] for key, offset in QUALITY_FIELDS.items()},
        'raw_data': record.hex(),
    }


def unit_status(unit):
    if unit.get('deleted'):
        return 'Deleted'
    if unit['arrival_time'] == -1:
        return 'Inactive'
    if not unit['in_play']:
        return 'Reinforcement'
    if unit['x'] < 0 or unit['y'] < 0:
        return 'Off map'
    if unit['x'] >= unit['map_width'] or unit['y'] >= unit['map_height']:
        return 'Outside map'
    return 'In play'


def unit_arrival_label(unit):
    if unit['arrival_time'] == -1:
        return 'Inactive'
    if unit['arrival_time'] < unit['start_time']:
        return 'At start'
    return f"Turn {unit['arrival_time'] - unit['start_time'] + 1}"


def arrival_time_from_form(unit, availability, turn):
    """Convert scenario-relative arrival controls to the stored game time."""
    if availability == 'Inactive':
        return -1
    if availability == 'At start':
        # Preserve earlier arrival dates when the form was not changed.
        if unit['arrival_time'] != -1 and unit['arrival_time'] < unit['start_time']:
            return unit['arrival_time']
        return unit['start_time'] - 1
    if availability != 'Scheduled':
        raise ValueError('Choose At start, Scheduled, or Inactive.')
    try:
        number = int(turn)
    except (TypeError, ValueError) as exc:
        raise ValueError('Arrival turn must be a whole number.') from exc
    last_turn = max(1, unit['end_time'] - unit['start_time'] + 1)
    if not 1 <= number <= last_turn:
        raise ValueError(f'Arrival turn must be between 1 and {last_turn}.')
    return unit['start_time'] + number - 1


def prepare_unit_changes(unit, values):
    """Validate every form field before producing exact, bounded file patches.

    Derived strengths, unit class/side and unknown bytes are not editable here.
    The game recomputes adjusted combat values during play.
    """
    record = bytearray.fromhex(unit['raw_data'])
    patches = []
    automation_updates = {}
    for key, value in values.items():
        if key in HQ_AUTOMATION_FIELDS:
            if key not in unit or key + '_offset' not in unit:
                raise ValueError('HQ automation is unavailable for this unit')
            if value not in (0, 1):
                raise ValueError('HQ automation must be enabled or disabled')
            # Preserve the stored byte if the checkbox has not changed.
            if bool(value) != bool(unit[key]):
                automation_updates[key] = int(value)
                patches.append((unit[key + '_offset'], bytes((int(value),)), key))
            continue
        if key not in EDITABLE_FIELDS:
            raise ValueError(f'{key} is not editable')
        offset, fmt, scale = EDITABLE_FIELDS[key]
        if str(value) == str(unit[key]):
            continue
        if key == 'name':
            value = str(value).strip()
            try:
                encoded = value.encode('cp437')
            except UnicodeEncodeError as exc:
                raise ValueError('Name must use characters supported by the DOS game') from exc
            if not encoded or len(encoded) > 25 or any(b < 32 or b == 127 for b in encoded):
                raise ValueError('Name must contain 1–25 printable DOS characters')
            new = encoded.ljust(26, b'\0')
        else:
            try:
                number = Decimal(str(value)) * scale
                if not number.is_finite() or number != number.to_integral_value():
                    raise ValueError()
                number = int(number)
            except (ValueError, InvalidOperation, OverflowError) as exc:
                raise ValueError(f'{key.replace("_", " ")}: enter a number'
                                 + (' with at most three decimal places' if scale == 1000 else ' with no decimal places')) from exc
            if key == 'counter_index':
                if unit['unit_class'] in (5, 6):
                    raise ValueError('Aircraft and ship icons are determined by their class')
                from lib.game_art import unit_counter
                unit_counter(unit['counter_resource'], number, unit.get('counter_bitmap'))
                low, high = 0, 32767
            elif key in ('x', 'y'):
                # The last stored row/column are the map's boundary padding;
                # HEX_IN_BOUNDS uses strict right/bottom bounds.
                limit = unit['map_width' if key == 'x' else 'map_height'] - (1 if unit['unit_class'] in (5, 6) else 2)
                low, high = -1, limit
            elif key == 'arrival_time':
                low, high = -1, 2147483647
            elif scale == 1000:
                low, high = 0, 2147483647
            else:
                low, high = 0, 15
            if not low <= number <= high:
                raise ValueError(f'{key.replace("_", " ")}: value is outside the allowed range')
            new = struct.pack(fmt, number)
        if record[offset:offset + len(new)] != new:
            if key in ('x', 'y', 'arrival_time') and (record[0x86] or record[0x91]):
                raise ValueError('Clear the unit’s route or fire target under Orders and dismount it under Transport before '
                                 'changing its position or arrival. Use the map’s formation move to move linked units together.')
            patches.append((unit['record_offset'] + offset, new, key))
            record[offset:offset + len(new)] = new
    updated = dict(unit, **decode_record(record))
    updated.update(automation_updates)
    updated['in_play'] = updated['arrival_time'] != -1 and updated['arrival_time'] < unit['current_time']
    return updated, patches
