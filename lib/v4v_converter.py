"""Experimental V for Victory 2.1 -> World at War: D-Day conversion.

Verified source fields are translated; engine-specific state is rebuilt from
native D-Day templates. Every output includes a report of the substitutions.
See txt/V4V_CONVERSION.md before assessing game balance or AI behavior.
"""
from functools import lru_cache
import hashlib
import math
from pathlib import Path
import struct

from PIL import Image

from lib.game_art import load_bitmap
from lib.game_resources import game_path, game_resources
from lib.terrain_artwork import TerrainStamp
from lib.terrain_reader import TERRAIN_TYPES
from lib.unit_roster import UnitRoster, put_short, short
from lib.v4v_reader import VictoryScenario, read_resources, read_bitmap
from lib.weather_reader import historical_weather_block, validate_weather


# V4V battleset terrain table -> D-Day's fourteen terrain rules.
MASTER_TERRAIN = (0, 1, 2, 3, 4, 5, 6, 9, 10, 13, 7, 8, 12, 11, 14)
LIMITATIONS = [
    'Experimental conversion: structurally validated; see game/waw/patches/README.md for limited DOSBox-X coverage and known failures.',
    'Uses D-Day movement, combat, supply, weather and victory rules; balance is not equivalent to V for Victory.',
    'V4V network bits are retained as provisional D-Day directional masks, except river/slope bits on water tiles are cleared to prevent sea overlays. Cross-engine equivalence needs in-game verification.',
    'V4V VGA indexes are rendered with the D-Day palette. Small and night terrain art is derived from the source large/dim tiles.',
    'D-Day auxiliary weapon and HQ supply records come from matching-name/type/class templates, not a complete V4V weapon-table translation.',
    'Historical temperatures and weather codes are translated into the 400-turn extended block; the patched D-Day engine is required.',
    'V4V snow/ice/wetness seeds and pre-scenario accumulation are not translated; D-Day uses different ground-condition arithmetic.',
    'Supply uses source daily quantities and relocated source supply-entry hexes where available, with D-Day initial stock/depot defaults.',
    'Objective names, positions, side point values and flags are translated; victory tiers use D-Day executable score ratios and native casualty scoring weights.',
    'Scripted AI, garrisons, replacement schedules, leaders and saved orders are reset; HQ staff automation starts disabled.',
    'Scenario-specific D-Day variants are disabled. Air/naval units use D-Day support rules and stay off map.',
    'V4V decorative terrain edges and hilltop markers are not translated; directional slope masks are retained.',
]


def integer(data, offset):
    return struct.unpack_from('<i', data, offset)[0]


def fixed(data, offset):
    value = struct.unpack_from('<f', data, offset)[0]
    if not math.isfinite(value) or abs(value) > 2_000_000:
        raise ValueError('Invalid V4V strength')
    return round(value * 1000)


@lru_cache(maxsize=1)
def templates():
    entries = []
    for path in sorted(game_path('dday', 'SCENARIO').glob('*.SCN')):
        roster = UnitRoster(path.read_bytes())
        for side, records in enumerate(roster.records):
            for record in records:
                auxiliary = roster._auxiliary(record)
                aux = b''
                if auxiliary:
                    kind, _, stride = auxiliary
                    index = integer(record, 4)
                    aux = bytes(roster.blocks[f'{kind}{side}'][index * stride:(index + 1) * stride])
                entries.append((bytes(record), aux, path.name))
    return entries


def template_for(source, side):
    candidates = [entry for entry in templates() if entry[0][0x76] == source[0x1a]]
    if not candidates:
        raise ValueError(f'No D-Day template for unit class {source[0x1a]}')
    name = source[0x6a:].split(b'\0')[0].strip()
    def rank(entry):
        unit = entry[0]
        return (unit[0x74] == side, unit[0x77] == source[0x1b],
                unit[0x92:].split(b'\0')[0].strip() == name,
                unit[0x79] == source[0x1d])
    return max(candidates, key=rank)


def terrain_codes(source):
    table = source.battleset[0x1e:0x2e]
    used = {value & 255 for (value,) in struct.iter_unpack('<I', source.blocks[3])}
    if any(code >= len(table) or table[code] >= len(MASTER_TERRAIN) for code in used):
        raise ValueError('Unknown source terrain type')
    return {code: MASTER_TERRAIN[table[code]] for code in used}


def convert_art(source):
    resources = read_resources(source.path.parent / f'{source.resource_name}.RES')
    palette = load_bitmap(128).getpalette()
    white = min(range(1, 256), key=lambda i: sum((255 - v) ** 2 for v in palette[i * 3:i * 3 + 3]))
    sheet = read_bitmap(resources['PICT', 128], palette)
    stamps = {}
    mapping = terrain_codes(source)
    for old_code, code in mapping.items():
        if code == 14:
            continue
        if (code, 0) in stamps:
            raise ValueError('Multiple source tiles map to one D-Day terrain slot')
        pixels = []
        for row in (0, 1, 1):
            tile = sheet.crop((1 + old_code * 33, 1 + row * 37,
                               33 + old_code * 33, 37 + row * 37))
            for small in (False, True):
                size, dy, number = ((16, 19), 21, 138) if small else ((32, 36), 38, 128)
                resized = tile.resize(size, Image.Resampling.NEAREST)
                mask = load_bitmap(number).crop((0, dy, size[0], dy + size[1])).tobytes()
                # Native V4V grid/background is white; preserve a solid hex mask.
                pixels.append(bytes((v or white) if m else 0 for v, m in zip(resized.tobytes(), mask)))
        stamps[code, 0] = TerrainStamp(f'V for Victory {source.resource_name} · {TERRAIN_TYPES[code]}', *pixels)
    counters = {}
    native = game_resources('dday')
    for side in (0, 1):
        old_number, number = 300 + side, 304 + side
        image = read_bitmap(resources['PICT', old_number], palette, resources['clut', old_number])
        data = bytearray(native['PICT', number].data)
        stride = int.from_bytes(data[10:12], 'little') & 0x3fff
        if image.width not in (484, 485) or image.height > short(data, 6):
            raise ValueError('Source unit sheet does not fit in D-Day')
        image = image.crop((0, 0, 484, image.height))
        data[12:] = bytes(len(data) - 12)
        raw = image.tobytes()
        for y in range(image.height):
            data[12 + y * stride:12 + y * stride + image.width] = raw[y * image.width:(y + 1) * image.width]
        for unit in source.units[side]:
            if unit[0x1a] not in (5, 6) and not 0 <= short(unit, 2) < image.height // 23 * 22:
                raise ValueError('Unit counter exceeds its source sheet')
        counters[number] = bytes(data)
    return stamps, counters


def convert_scenario(path):
    source = VictoryScenario.read(path)
    roster = UnitRoster(game_path('dday', 'SCENARIO', 'BRADLEY.SCN').read_bytes())
    b, h = roster.blocks, roster.header
    report = {'version': 4, 'source': str(source.path), 'title': source.title,
              'theater': source.theater, 'source_sha256': hashlib.sha256(source.path.read_bytes()).hexdigest(),
              'limitations': list(LIMITATIONS), 'adjustments': [], 'unit_templates': []}
    weather = source.historical_weather
    report['source_weather'] = weather
    report['runtime_status'] = 'requires_dday_weather_400_patch'
    report['engine_patch'] = 'dday-weather-400'
    b['weather'] = historical_weather_block(source)
    h[0x1227] = 0  # Keep the authored historical sequence.
    top, left, bottom, right = source.rect
    if bottom >= source.height or right >= source.width:
        report['adjustments'].append('Clamped scenario bounds to the stored battleset map.')
    bottom, right = min(bottom, source.height - 1), min(right, source.width - 1)
    if top % 2:
        report['adjustments'].append('Included one extra northern map row to preserve staggered hex geometry.')
        top -= 1
    width, height = right - left + 1, bottom - top + 1
    report.update(map_origin=[left, top], map_size=[width, height], source_rect=list(source.rect))
    def position(x, y):
        return (x - left, y - top) if left <= x <= right and top <= y <= bottom else (-1, -1)

    start, end = integer(source.blocks[0], 0x16), integer(source.blocks[0], 0x1a)
    struct.pack_into('<2i', h, 0x44, start, end)
    struct.pack_into('<4h', h, 0x224, 0, 0, height - 1, width - 1)
    h[0x22c:0x234] = h[0x224:0x22c]
    struct.pack_into('<2h', h, 0x234, width // 2, height // 2)
    put_short(h, 0x238, 304)
    # Source interleaving is identical, but the Scenario block offset changed.
    h[0x3e0:0xbe0] = source.blocks[0][0x7e:0x87e]
    h[0x260:0x31c] = bytes(0xbc)  # D-Day map markers, including hilltops.
    h[0xbe0:0x1220] = bytes(50 * 32)
    labels = []
    for label in source.labels:
        x, y = position(*struct.unpack_from('<2h', label))
        if x < 0:
            continue
        labels.append(struct.pack('<2h', x, y) + label[5:30].ljust(26, b'\0') + bytes([label[4], 86]))
    h[0xbe0:0xbe0 + len(labels) * 32] = b''.join(labels)
    h[0x1220:0x1224] = bytes(4)
    h[0x122a] = len(labels)  # NameInHex; +1221 is difficulty, not the label count.
    h[0x1229] = 0
    h[0x3a2:0x3a4] = bytes(2)  # No D-Day leaders.
    for offset in (0x3ca, 0x3cb, 0x3cc, 0x3ce, 0x3cf, *range(0x3d2, 0x3d8)):
        h[offset] = 0

    cal = source.blocks[1]
    days = short(cal, 18)
    if days <= 0 or len(source.blocks[8]) != days * 4:
        raise ValueError('Source duration and daily supply length disagree')
    b['calendar'] = bytearray(b['calendar'])
    c = b['calendar']
    # Start a standalone D-Day scenario so supply indexes begin at day zero.
    struct.pack_into('<6i', c, 0, start, start, end, start, 0, 0)
    struct.pack_into('<2h', c, 24, days, short(cal, 28))
    c[28] = 6
    c[30:32] = cal[16:18]
    c[34:37] = bytes([cal[25], short(cal, 26), short(cal, 30)])
    c[37:] = bytes(5)

    mapping = terrain_codes(source)
    records = [word for (word,) in struct.iter_unpack('<I', source.blocks[3])]
    translated = []
    for word in records:
        code = mapping[word & 255]
        new = (word & ~255) | code
        if code == 5:
            # V4V keeps edge/feature bits even across open sea. D-Day renders
            # those as river/slope lines on the water. Retain the source bytes
            # in the original file; omit these overlays from the adaptation.
            new &= ~0xfff00
        translated.append(new)
    b['uhexes'] = b''.join(struct.pack('<I', word) for word in translated)
    def crop(data, stride):
        return b''.join(data[(y * source.width + left) * stride:(y * source.width + right + 1) * stride]
                        for y in range(top, bottom + 1))
    b['hexmap'] = crop(source.blocks[2], 2)
    water_cleanups = sum(mapping[records[i] & 255] == 5 and bool(records[i] & 0xfff00)
                         for (i,) in struct.iter_unpack('<H', b['hexmap']))
    if water_cleanups:
        report['adjustments'].append(f'Cleared river/slope overlays on {water_cleanups} water hexes; source water-edge interpretation remains unresolved.')
    # Both engines store hex ownership in bit 16. D-Day's InitUnitMap needs
    # ownership AND nonzero stacking (bits 17..20) before it loads a hex's
    # units. InitHexZOCs only recalculates influence, not this saved state.
    # Keep territorial control, then rebuild stacking from the converted OB.
    b['zoc'] = b''.join(struct.pack('<I', word & 0x10000)
                        for (word,) in struct.iter_unpack('<I', crop(source.blocks[4], 4)))
    b['hedgelist'] = struct.pack('<H', 0xfde8) * (width * height)
    # RWHexEdges asserts rSize != 0 even when every hex uses the no-edge
    # sentinel. Keep one unreferenced empty eight-byte edge record.
    b['hedges'] = bytes(8)
    report['terrain_mapping'] = {str(k): {'dday_code': v, 'name': TERRAIN_TYPES[v]} for k, v in sorted(mapping.items())}

    objectives = []
    for obj in source.objectives:
        x, y = position(*struct.unpack_from('<2h', obj))
        if x < 0:
            report['adjustments'].append('Omitted objective outside scenario bounds: ' + obj[16:].split(b'\0')[0].decode('mac_roman'))
            continue
        new = bytearray(48)
        struct.pack_into('<2i2h', new, 0, short(obj, 8), short(obj, 10), x, y)
        new[12:20] = obj[4:8] + obj[12:16]
        new[22:48] = obj[16:42]
        objectives.append(new)
    if not 0 < len(objectives) <= 255:
        raise ValueError('Invalid converted objective count')
    b['vicloc'] = b''.join(objectives)
    h[0x1222] = len(objectives)
    report['objectives'] = len(objectives)

    roster.records = [[], []]
    roster.orders, roster.trailer = {}, b''
    b['hqheads'] = bytearray(b'\xff' * 16)
    b['planeclass'], b['shipclass'] = bytearray(32), bytearray(40)
    for side, units in enumerate(source.units):
        ground = [u for u in units if u[0x1a] not in (5, 6)]
        ships = sorted((u for u in units if u[0x1a] == 5), key=lambda u: u[0x1b])
        plane_group = {37: 0, 38: 0, 36: 1, 94: 2, 95: 3}
        planes = sorted((u for u in units if u[0x1a] == 6), key=lambda u: plane_group[u[0x1b]])
        ordered = ground + ships + planes
        hqs = [u for u in ground if u[0x1a] == 7]
        hq_index = {u[0x61]: i for i, u in enumerate(hqs)}
        if len(hq_index) != len(hqs) or not 0 < len(hqs) < 128:
            raise ValueError('Invalid source HQ identifiers')
        for key in ('hqs', 'hqlist', 'arty', 'tanks', 'riders'):
            b[f'{key}{side}'] = bytearray()
        for offset, count in ((0x23c, len(hqs)), (0x240, len(ground)), (0x244, len(units)),
                              (0x248, 0), (0x24c, 0), (0x250, 0),
                              (0x254, len(ships)), (0x258, len(planes))):
            put_short(h, offset + side * 2, count)
        order_offset = 0
        for index, old in enumerate(ordered):
            native, aux_template, filename = template_for(old, side)
            unit = bytearray(native)
            cls, descriptor = old[0x1a:0x1c]
            name = old[0x6a:].split(b'\0')[0]
            report['unit_templates'].append({'side': side, 'source_id': short(old, 0), 'id': index,
                'name': name.decode('cp437'), 'template_scenario': filename,
                'template_unit': native[0x92:].split(b'\0')[0].decode('cp437')})
            unit[:8] = bytes(8)
            unit[8:12] = old[0x10:0x14]
            # Float source combat ratings -> D-Day fixed-point integers.
            for src, dst in ((0x20, 0x10), (0x24, 0x14), (0x28, 0x18), (0x2c, 0x20),
                             (0x30, 0x24), (0x36, 0x28), (0x3a, 0x2c), (0x36, 0x30), (0x3a, 0x34)):
                struct.pack_into('<i', unit, dst, fixed(old, src))
            struct.pack_into('<i', unit, 0x1c, short(old, 0x34) * 1000)
            unit[0x40:0x4c] = bytes(12)
            unit[0x4c:0x50] = old[0x4a:0x4e]
            slot_size = 129 if cls not in (5, 6) else 0
            if order_offset + slot_size > 65535:
                raise ValueError('Ground roster exceeds D-Day orders storage')
            struct.pack_into('<2H', unit, 0x50, order_offset, slot_size)
            order_offset += slot_size
            put_short(unit, 0x54, index)
            unit[0x56:0x58] = old[2:4]
            x, y = position(short(old, 4), short(old, 6)) if cls not in (5, 6) else (-1, -1)
            if x < 0 and cls not in (5, 6) and integer(old, 0x10) != -1:
                raise ValueError(f'Active ground unit outside map: {name!r}')
            struct.pack_into('<4h', unit, 0x58, x, y, x, y)
            unit[0x60:0x64] = b'\xff' * 4
            arrival = integer(unit, 8)
            put_short(unit, 0x64, 1 if arrival == -1 else 7 if arrival < start else 2)
            unit[0x66:0x74] = bytes(14)
            put_short(unit, 0x6a, -1)
            unit[0x74:0x7c] = old[0x18:0x20]
            unit[0x74] = side
            unit[0x7c:0x89] = bytes(13)
            # V4V 1845:0432 returns one stacking point for +5e == 1,
            # otherwise three. D-Day GetUnitSize reads +7e literally for
            # non-HQs; 255 is only a valid HQ sentinel.
            unit[0x7e] = 255 if cls == 7 else 1 if old[0x5e] == 1 else 3
            if cls not in (5, 6):
                parent, assigned = old[0x60], old[0x61]
                if parent not in hq_index or assigned not in hq_index:
                    raise ValueError(f'Unknown HQ assignment: {name!r}')
                # TraceOneHQ compares +81 (own HQ) with +80 (parent HQ)
                # before following the auxiliary parent. Root HQs must match.
                unit[0x80] = hq_index[parent]
                unit[0x81] = unit[0x84] = hq_index[assigned]
            unit[0x89:0x8e] = old[0x4f:0x54]
            unit[0x8e:0x90] = old[0x54:0x56]
            unit[0x90:0x92] = b'\xff\0'
            unit[0x92:] = name.ljust(26, b'\0')
            auxiliary = roster._auxiliary(unit)
            if auxiliary:
                kind, count_offset, stride = auxiliary
                new_index = len(b[f'{kind}{side}']) // stride
                struct.pack_into('<i', unit, 4, new_index)
                aux = bytearray(aux_template) if len(aux_template) == stride else bytearray(stride)
                if kind in ('riders', 'tanks'):
                    aux[:] = bytes(stride)
                elif kind == 'hqs':
                    level = (3 if descriptor in (43, 70, 92) else 2 if descriptor in (17, 18, 83)
                             else 1 if descriptor in (19, 20, 88) else 0)
                    # Initialize administrative state without borrowed roster links.
                    aux[12:40] = bytes(28)
                    put_short(aux, 0x28, index)
                    put_short(aux, 0x2e, level)
                    head_offset = 2 * (side * 4 + level)
                    put_short(aux, 0x30, short(b['hqheads'], head_offset))
                    put_short(b['hqheads'], head_offset, new_index)
                    parent = hq_index[old[0x60]]
                    put_short(aux, 0x32, -1 if parent == new_index else parent)
                    # TraceAllHQs trusts this cached active flag and does not
                    # check arrival itself. Never borrow it from the template.
                    aux[0x38] = int(0 <= arrival < start)
                    aux[0x39] = 0
                    b[f'hqlist{side}'] += struct.pack('<h', index)
                b[f'{kind}{side}'] += aux
                put_short(h, count_offset + 2 * side, new_index + 1)
            roster.records[side].append(unit)
        struct.pack_into('<I', h, 0x4c + side * 4, order_offset)
        for index, unit in enumerate(roster.records[side][:len(ground)]):
            if unit[0x76] != 7:
                roster._link(side, index)
        for table, groups, support, initial in (('shipclass', 5, ships, len(ground)),
                                                 ('planeclass', 4, planes, len(ground) + len(ships))):
            cursor = initial
            for category in range(groups):
                count = sum((u[0x1b] - 30 if table == 'shipclass' else plane_group[u[0x1b]]) == category for u in support)
                slot = side * groups + category
                put_short(b[table], 2 * slot, count)
                put_short(b[table], 2 * (2 * groups + slot), cursor)
                cursor += count
        b[f'autoart{side}'] = bytes(len(hqs))
        b[f'autognd{side}'] = bytes(len(hqs))
        # UpdateReps indexes nine unsigned quantities per calendar day.
        b[f'reps{side}'] = bytes(short(b['calendar'], 24)*9)

    b['ai_counts'] = bytes(12)
    for key in ('bgstate', 'bgshx', 'bgshy', 'bgdhx', 'bgdhy'):
        b[key] = bytes(800)
    b['supply'] = source.blocks[8]
    # Each V4V stock record starts with count + 20 Xs + 20 Ys. Select the
    # first side pair; additional stock groups remain documented in the source.
    stock_report = []
    for side in (0, 1):
        src = source.blocks[9][side * 118:(side + 1) * 118]
        count = short(src, 0)
        if not 0 <= count <= 20:
            raise ValueError('Unknown V4V supply-entry layout')
        points = [position(short(src, 2 + 2 * i), short(src, 42 + 2 * i)) for i in range(count)]
        points = [p for p in points if p[0] >= 0]
        if not points:
            fallback = next((u for u in roster.records[side] if u[0x76] == 7 and short(u, 0x58) >= 0), None)
            if fallback is None:
                fallback = next(u for u in roster.records[side] if short(u, 0x58) >= 0)
            points = [struct.unpack_from('<2h', fallback, 0x58)]
            report['adjustments'].append(f'Side {side}: no supply-entry hex inside crop; used first on-map HQ/unit.')
        stock = bytearray(b[f'stock{side}'][:136])
        # SwapStock/TraceToSupplySource: 26 Xs at +4, 26 Ys at +38h,
        # count at +6ch, followed by 26 unavailable flags at +6eh.
        stock[4:] = bytes(132)
        for index, (x, y) in enumerate(points):
            put_short(stock, 4 + 2 * index, x)
            put_short(stock, 56 + 2 * index, y)
        put_short(stock, 108, len(points))
        b[f'stock{side}'] = stock
        put_short(h, 0x25c + side * 2, 1)
        stock_report.append(points)
    report['supply_entry_hexes'] = stock_report
    report['unit_counts'] = [len(units) for units in roster.records]
    report['source_unit_counts'] = [len(units) for units in source.units]
    b['zoc'] = initial_control_map(roster, report['adjustments'])
    data = roster.to_bytes()
    validate_conversion(data)
    stamps, counters = convert_art(source)
    report['output_sha256'] = hashlib.sha256(data).hexdigest()
    return data, stamps, counters, report


def initial_control_map(roster, adjustments=None):
    """Rebuild D-Day's saved occupancy while retaining unoccupied ownership.

    InitUnitMap (31420h) gates loading on the stacking nibble, selects the OB
    with bit 16, then finds every in-play ground unit at that coordinate.
    CalcStacking/GetUnitSize use stacking points, not the number of units.
    """
    width = short(roster.header, 0x22a) + 1
    height = short(roster.header, 0x228) + 1
    current = integer(roster.blocks['calendar'], 12)
    words = [word & 0x10000 for (word,) in struct.iter_unpack('<I', roster.blocks['zoc'])]
    stacks = {}
    for side, units in enumerate(roster.records):
        for unit in units[:roster.count(0x240, side)]:
            arrival = integer(unit, 8)
            if arrival == -1 or arrival >= current:
                continue
            x, y = struct.unpack_from('<2h', unit, 0x58)
            if not (0 <= x < width and 0 <= y < height):
                raise ValueError('In-play ground unit is outside the converted map')
            cell = y * width + x
            owner, size = stacks.get(cell, (side, 0))
            if owner != side:
                raise ValueError('Opposing units occupy the same converted hex')
            weight = (4 if roster.header[0x122b] == 1 else 3) if unit[0x76] == 7 else unit[0x7e]
            if not 1 <= weight <= 15:
                raise ValueError('Invalid converted unit stacking size')
            stacks[cell] = side, size + weight
    for cell, (side, size) in stacks.items():
        if size > 15:
            # UBCARTER starts with 16 points in one hex. Wrapping the nibble
            # to zero makes the entire stack disappear during InitUnitMap.
            if adjustments is not None:
                adjustments.append(f'Hex ({cell % width}, {cell // width}): capped saved stacking at 15 for {size} points; retained every unit and its individual size.')
        words[cell] = (side << 16) | (min(size, 15) << 17)
    return b''.join(struct.pack('<I', word) for word in words)


def validate_conversion(data):
    """Check engine indexes, auxiliary records and complete serialization."""
    from lib.scenario_library import split_library_footer, library_metadata
    # DOS export appends a checked identity for resource selection/save-resume.
    library_metadata(data)
    data, _ = split_library_footer(data)
    r = UnitRoster(data)
    validate_weather(r.blocks['weather'])
    if not r.blocks['hedges'] or len(r.blocks['hedges']) % 8:
        raise ValueError('D-Day requires a nonempty terrain-edge table')
    if r.to_bytes() != data or r.trailer:
        raise ValueError('Converted scenario did not round-trip exactly')
    width, height = short(r.header, 0x22a) + 1, short(r.header, 0x228) + 1
    for key, stride in (('hexmap', 2), ('zoc', 4), ('hedgelist', 2)):
        if len(r.blocks[key]) != width * height * stride:
            raise ValueError('Converted map dimensions disagree')
    if r.blocks['zoc'] != initial_control_map(r):
        raise ValueError('Converted ownership/stacking disagrees with the roster')
    for (index,) in struct.iter_unpack('<H', r.blocks['hexmap']):
        if 4 * index >= len(r.blocks['uhexes']):
            raise ValueError('Invalid converted map index')
    for side, units in enumerate(r.records):
        hq_count = r.count(0x23c, side)
        for index, unit in enumerate(units):
            if short(unit, 0x54) != index:
                raise ValueError('Invalid converted OB identifier')
            cls = unit[0x76]
            x, y = struct.unpack_from('<2h', unit, 0x58)
            if (x, y) != (-1, -1) and not (0 <= x < width and 0 <= y < height):
                raise ValueError('Invalid converted unit coordinates')
            if cls not in (5, 6) and unit[0x81] >= hq_count:
                raise ValueError('Invalid converted unit HQ')
            aux = r._auxiliary(unit)
            if aux and not 0 <= integer(unit, 4) < r.count(aux[1], side):
                raise ValueError('Invalid converted auxiliary index')
        linked = set()
        for (unit_id,) in struct.iter_unpack('<h', r.blocks[f'hqlist{side}']):
            if units[unit_id][0x76] != 7:
                raise ValueError('HQ list points at a non-HQ')
            cursor = short(units[unit_id], 0x6a)
            while cursor != -1:
                if not 0 <= cursor < len(units) or cursor in linked:
                    raise ValueError('Invalid subordinate chain')
                linked.add(cursor)
                cursor = short(units[cursor], 0x6a)
        expected = {i for i, u in enumerate(units) if u[0x76] not in (5, 6, 7)}
        if linked != expected:
            raise ValueError('Missing subordinate link')
    return r
