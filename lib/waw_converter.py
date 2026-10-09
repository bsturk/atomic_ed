"""Translate complete earlier WaW scenario documents for the D-Day engine.

Source records are read by waw_reader, never by the D-Day parser. Numeric
representations and links are translated explicitly. Engine-rule/artwork
adaptations are returned in the report; see txt/WAW_CONVERSION.md.
"""
from collections import Counter, defaultdict
from functools import lru_cache
import hashlib
import math
from pathlib import Path
import struct

from lib.game_resources import game_path, GAME_NAMES, game_resources
from lib.game_art import decode_bitmap, load_bitmap
from lib.terrain_artwork import TerrainStamp
from lib.terrain_catalog import artwork_catalog
from lib.unit_roster import UnitRoster, put_short
from lib.waw_reader import WawScenario, i16, i32
from lib.weather_reader import CAPACITY, EXTENDED_SIZE


def number(data, offset, scale=1000):
    value = struct.unpack_from('<f', data, offset)[0]
    if not math.isfinite(value) or not -2147483648 <= value*scale <= 2147483647:
        raise ValueError(f'Invalid source number at +{offset:x}')
    return round(value*scale)


def unit_record(source, old, side):
    """Translate the OB fields before resolving scenario-local relationships."""
    unit = bytearray(172)
    if source.stalin:
        unit[:0x44] = old[:0x44]
        unit[0x48:] = old[0x44:]
        for p in range(0x10, 0x40, 4):
            struct.pack_into('<i', unit, p, number(old, p))
    else:
        unit[4:0x10] = old[:4] + old[8:0x10]
        unit[0x14:0x38] = old[0x10:0x34]
        unit[0x40:0x48] = old[0x34:0x3c]
        unit[0x4c:0x50] = old[0x3c:0x40]
        unit[0x54:0x80] = old[0x40:0x6c]
        unit[0x80:0x82] = old[0x6c:0x6e]
        unit[0x84:0x90] = old[0x6e:0x7a]
        unit[0x90:0x92] = bytes((old[0x7b], old[0x7a]))
        unit[0x92:] = old[0x7c:]
        # D-Day has no Commonwealth nationality enumeration. Preserve names,
        # stats and chits; Allied formations use its Allied nationality rules.
        unit[0x75] = 0 if side == 0 else 4 if old[0x61] == 7 else 1
        # CRUSADER GetUnitSize (41f97): 1 for the small flag, 3 otherwise.
        unit[0x7e] = 255 if unit[0x76] == 7 else 1 if old[0x6a] == 1 else 3
    unit[:4] = bytes(4)  # process-local orders pointer
    unit[0x74] = side
    return unit


def weather(source, start, end):
    old = source.blocks['weather']
    result = bytearray(EXTENDED_SIZE)
    if source.stalin:
        scale, scenario = source.header[0xf45], source.header[0xf3a]
        origin = (46974 if scale == 3 else (94074 if scenario == 4 else 94116)
                  if scale == 2 else (93750 if scenario == 0 else 93540))
        temp, cloud, count = 0xf8, 0x61c, 260
        struct.pack_into('<3i', result, 0, *(number(old, p) for p in (0xec, 0xf0, 0xf4)))
        result[0x4bc:0x4be] = old[0x860:0x862]
    else:
        # CRUSADER object 3 +5ba1/+5ba5: historical weather interval.
        origin, temp, cloud, count = 91764, 12, 0x14c, 160
        result[:12] = old[:12]
        result[0x4bc:0x4be] = old[0x1ec:0x1ee]
    if not 0 < end-start+1 <= CAPACITY:
        raise ValueError('Converted calendar exceeds the patched 400-turn weather table')
    sequence = []
    for timestamp in range(start, end+1):
        index = timestamp-origin
        if not 0 <= index < count or old[cloud+index] > 4:
            raise ValueError('Historical weather does not cover the source scenario dates')
        sequence.append((i16(old, temp+2*index), old[cloud+index]))
    for index, (temperature, code) in enumerate(sequence + [sequence[-1]]*(CAPACITY-len(sequence))):
        put_short(result, 12+index*2, temperature)
        result[0x32c+index] = code
    struct.pack_into('<2i', result, 0x4be, start, end)
    return result


@lru_cache(maxsize=512)
def _stamp(source_name, code, variant):
    rows = artwork_catalog(source_name)
    row = rows[code]
    column = variant + (8 if source_name == 'stalingrad_winter' else 0)
    # Crusader's water also uses display columns 1 and 2 as coast variants.
    if column not in row.columns:
        from dataclasses import replace
        row = replace(row, columns=tuple(sorted(set(row.columns+(column,)))))
    return TerrainStamp.from_artwork(row, column, GAME_NAMES.get(row.game, row.game))


def terrain(source, report):
    """Allocate native art slots by usage; never change the chosen terrain rule.

    When a rule needs more than six distinct pictures, retain its six most
    frequent pictures and use the nearest one for the remainder. All original
    pictures remain in the portable terrain library and the source SCN.
    """
    from lib.terrain_catalog import CRUSADER_DDAY_RULES, STALINGRAD_DDAY_RULES
    b = source.blocks
    bank = ('stalingrad_winter' if i16(source.header, 0x1d0) == 304 else 'stalingrad_summer') if source.stalin else source.game
    rules = STALINGRAD_DDAY_RULES if source.stalin else CRUSADER_DDAY_RULES
    counts = Counter(b['uhexes'][index*4] for (index,) in struct.iter_unpack('<H', b['hexmap']))
    groups, stamps = defaultdict(list), {}
    for raw in sorted(counts):
        code, variant = raw & 15, raw >> 4
        if code >= len(rules) or variant > (5 if source.stalin else 10):
            raise ValueError(f'Unknown {source.game} terrain/artwork {raw:02x}')
        rule = rules[code]
        # The source Crusader renderer shows towns using column two on land.
        if not source.stalin and variant == 2 and code != 6:
            rule = 4
        stamps[raw] = _stamp(bank, code, variant)
        groups[rule].append(raw)
    assignments, mapping, substitutions = {}, {}, []
    for code, raws in sorted(groups.items()):
        unique = []
        for raw in sorted(raws, key=lambda r: (-counts[r], r)):
            match = next((r for r in unique if stamps[r].large == stamps[raw].large
                          and stamps[r].small == stamps[raw].small), None)
            if match is None:
                unique.append(raw)
        selected = unique[:6]
        for variant, raw in enumerate(selected):
            assignments[code, variant] = stamps[raw]
        for raw in raws:
            chosen = min(range(len(selected)), key=lambda v: sum(
                a != b for a, b in zip(stamps[raw].large, stamps[selected[v]].large)))
            mapping[raw] = code | chosen << 4
            if stamps[raw].large != stamps[selected[chosen]].large:
                substitutions.append(dict(source=raw, target=mapping[raw], hexes=counts[raw]))
    records = bytearray(b['uhexes'])
    for p in range(0, len(records), 4):
        # Unreferenced source records are also preserved; a safe clear tile
        # replaces an unused code when it has no allocated picture.
        records[p] = mapping.get(records[p], 1)
    report['terrain'] = dict(source_bank=bank, mapping=mapping, artwork_substitutions=substitutions)
    if substitutions:
        report['adaptations'].append(f'{len(substitutions)} artwork choices on {sum(r["hexes"] for r in substitutions)} hexes use a nearby picture with the same D-Day terrain rule (six-picture limit).')
    return records, assignments


def counters(source, roster, report):
    resources, native = game_resources(source.game), game_resources('dday')
    base = i16(source.header, 0x1d0) if source.stalin else 300
    result = {}
    for side in (0, 1):
        image = decode_bitmap(resources['PICT', base+side].data, resources['clut', 8].data)
        if image.getpalette() != load_bitmap(128).getpalette():
            raise ValueError('Source counter palette differs from D-Day')
        target = bytearray(native['PICT', 304+side].data)
        stride = int.from_bytes(target[10:12], 'little') & 0x3fff
        height = i16(target, 6)
        target[12:] = bytes(len(target)-12)
        # Campaign sheets are taller than D-Day's. Deduplicate identical chits
        # and repack only referenced unit/leader pictures, without dropping art.
        pixels, mapping = {}, {}
        def assign(index):
            if index in mapping:
                return mapping[index]
            x, y = index % 22*22, index//22*23
            if index < 0 or x+22 > image.width or y+23 > image.height:
                raise ValueError(f'Source counter {index} is outside its sheet')
            tile = image.crop((x, y, x+22, y+23)).tobytes()
            if tile not in pixels:
                number = len(pixels)
                if number >= height//23*22:
                    raise ValueError('Unique source chits exceed D-Day counter capacity')
                pixels[tile] = number
                x, y = number % 22*22, number//22*23
                for row in range(23):
                    offset = 12+(y+row)*stride+x
                    target[offset:offset+22] = tile[row*22:(row+1)*22]
            mapping[index] = pixels[tile]
            return mapping[index]
        for unit in roster.records[side]:
            if unit[0x76] not in (5, 6):
                put_short(unit, 0x56, assign(i16(unit, 0x56)))
        leaders = roster.blocks.get(f'leaders{side}', bytearray())
        for pos in range(0, len(leaders), 36):
            put_short(leaders, pos+8, assign(i16(leaders, pos+8)))
        report.setdefault('counter_mapping', []).append(mapping)
        result[304+side] = bytes(target)
    return result


def _units(source, roster, report):
    b, h, oldb = roster.blocks, roster.header, source.blocks
    roster.records, roster.orders, roster.trailer = [[], []], {}, b''
    b['hqheads'] = bytearray(b'\xff'*16)
    b['planeclass'], b['shipclass'], b['planecounts'] = bytearray(32), bytearray(40), bytearray(80)
    plane_group = {37: 0, 38: 0, 36: 1, 94: 2, 95: 3}
    report['units'] = []
    for side, originals in enumerate(source.units):
        rows = [unit_record(source, u, side) for u in originals]
        ground = [i for i, u in enumerate(rows) if u[0x76] not in (5, 6)]
        ships = sorted((i for i, u in enumerate(rows) if u[0x76] == 5), key=lambda i: rows[i][0x77])
        planes = sorted((i for i, u in enumerate(rows) if u[0x76] == 6), key=lambda i: plane_group[rows[i][0x77]])
        ordering = ground+ships+planes
        ids = {old: new for new, old in enumerate(ordering)}
        hq_ids = [i for i in ground if rows[i][0x76] == 7]
        hq_map = {i32(rows[i], 4): n for n, i in enumerate(hq_ids)}
        if len(hq_map) != len(hq_ids) or not 0 < len(hq_ids) < 128:
            raise ValueError('Invalid source HQ identifiers')
        for name in ('hqs', 'hqlist', 'arty', 'tanks', 'riders'):
            b[f'{name}{side}'] = bytearray()
        for offset, count in ((0x23c, len(hq_ids)), (0x240, len(ground)), (0x244, len(rows)),
                              (0x248, 0), (0x24c, 0), (0x250, 0), (0x254, len(ships)), (0x258, len(planes))):
            put_short(h, offset+2*side, count)
        order_offset = 0
        for index, old_index in enumerate(ordering):
            unit, old = rows[old_index], originals[old_index]
            old_aux, cls = i32(unit, 4), unit[0x76]
            report['units'].append(dict(side=side, source_id=old_index, id=index,
                                       source_nationality=old[source.type_offset+1]))
            size = (i16(old, 0x4e) if source.stalin else 129) if cls not in (5, 6) else 0
            if size < 0 or order_offset+size > 65535:
                raise ValueError('Source orders exceed D-Day storage')
            struct.pack_into('<2H', unit, 0x50, order_offset, size)
            order_offset += size
            put_short(unit, 0x54, index)
            put_short(unit, 0x6a, -1)
            # Paths and tactical caches belong to the source engine. Preserve
            # the authored order mode, quality and availability, rebuild links.
            unit[0x82:0x84] = bytes(2)
            unit[0x85:0x89] = bytes(4)
            if cls in (5, 6):
                struct.pack_into('<4h', unit, 0x58, -1, -1, -1, -1)
            else:
                for field in (0x80, 0x81, 0x84):
                    if unit[field] not in hq_map:
                        raise ValueError(f'Unknown HQ {unit[field]} for {unit[0x92:]!r}')
                    unit[field] = hq_map[unit[field]]
            auxiliary = roster._auxiliary(unit)
            if auxiliary:
                kind, count_offset, stride = auxiliary
                target_index = len(b[f'{kind}{side}'])//stride
                struct.pack_into('<i', unit, 4, target_index)
                aux = bytearray(stride)
                if kind == 'hqs':
                    oldstride = 34 if source.stalin else 12
                    original = oldb[f'hqs{side}'][old_aux*oldstride:(old_aux+1)*oldstride]
                    if len(original) != oldstride:
                        raise ValueError('Missing source HQ auxiliary record')
                    if source.stalin:
                        aux[:12] = original[:12]
                        aux[36:] = original[12:]
                        level = i16(aux, 0x2e)
                        parent = i16(original, 0x1a)
                        parent = -1 if parent == -1 else hq_map[parent]
                    else:
                        aux[:4] = original[:4]
                        # Crusader stores one current supply amount, whereas
                        # D-Day needs a distribution limit and separate net-
                        # received accounting. Use the existing conversion's
                        # distribution policy, but initialize accounting to zero.
                        struct.pack_into('<2i', aux, 4, i32(original, 0), 0)
                        level = (3 if unit[0x77] in (43, 70, 92) else 2 if unit[0x77] in (17, 18, 83)
                                 else 1 if unit[0x77] in (19, 20, 88) else 0)
                        parent = -1 if unit[0x80] == unit[0x81] else unit[0x80]
                        put_short(aux, 0x2a, -4)
                        put_short(aux, 0x2c, 99)
                    if not 0 <= level < 4:
                        raise ValueError('Unknown HQ command level')
                    put_short(aux, 0x28, index)
                    put_short(aux, 0x2e, level)
                    put_short(aux, 0x32, parent)
                    unit[0x80] = target_index if parent == -1 else parent
                    unit[0x81] = unit[0x84] = target_index
                    head = (side*4+level)*2
                    put_short(aux, 0x30, i16(b['hqheads'], head))
                    put_short(b['hqheads'], head, target_index)
                    aux[0x38] = int(0 <= i32(unit, 8) < i32(h, 0x44))
                    aux[0x39] = 0
                    b[f'hqlist{side}'] += struct.pack('<h', index)
                elif kind == 'arty':
                    original = oldb[f'arty{side}'][old_aux*28:(old_aux+1)*28]
                    if len(original) != 28:
                        raise ValueError('Missing source artillery definition')
                    aux[:] = original
                    if source.stalin:
                        for offset in range(0, 16, 4):
                            struct.pack_into('<i', aux, offset, number(original, offset))
                # Mounted passenger links are runtime state, not definitions.
                b[f'{kind}{side}'] += aux
                put_short(h, count_offset+2*side, target_index+1)
            else:
                unit[4:8] = bytes(4)
            roster.records[side].append(unit)
        struct.pack_into('<I', h, 0x4c+side*4, order_offset)
        for index, unit in enumerate(roster.records[side][:len(ground)]):
            if unit[0x76] != 7:
                roster._link(side, index)
        for name in ('autoart', 'autognd'):
            b[f'{name}{side}'] = bytearray(oldb[f'{name}{side}'][old] for old in hq_map)
        for table, groups, support, initial in (('shipclass', 5, ships, len(ground)),
                                               ('planeclass', 4, planes, len(ground)+len(ships))):
            cursor = initial
            for category in range(groups):
                count = sum((rows[i][0x77]-30 if table == 'shipclass' else plane_group[rows[i][0x77]]) == category for i in support)
                slot = side*groups+category
                put_short(b[table], slot*2, count)
                put_short(b[table], (groups*2+slot)*2, cursor)
                cursor += count
        _leaders(source, roster, side, ids, hq_map)
        from lib.unit_definitions import refresh_command_spans
        refresh_command_spans(roster, side)


def _leaders(source, roster, side, ids, hq_map):
    old = source.blocks.get(f'leaders{side}', b'')
    stride = 36 if source.stalin else 30
    records = bytearray()
    for index, p in enumerate(range(0, len(old), stride)):
        original = old[p:p+stride]
        leader = bytearray(36)
        if source.stalin:
            leader[:] = original
            struct.pack_into('<2i', leader, 0, number(original, 0, 1), number(original, 4, 1))
            home = hq_map[i16(original, 12)]
        else:
            leader[:12] = original[:12]
            leader[14:30] = original[12:28]
            attached = roster.records[side][ids[i16(original, 10)]]
            home = attached[0x81]
            leader[30] = attached[0x75]
        attached = ids[i16(original, 10)]
        put_short(leader, 10, attached)
        put_short(leader, 12, home)
        roster.records[side][attached][0x90] = index
        records += leader
    roster.blocks[f'leaders{side}'] = records
    roster.header[0x3a2+side] = len(records)//36


def _supply(source, roster, report):
    b, h, old = roster.blocks, roster.header, source.blocks
    b['supply'] = bytearray(old['supply'])
    for side in (0, 1):
        if source.stalin:
            b[f'stock{side}'] = bytearray(old[f'stock{side}'])
            b[f'depot{side}'] = bytearray(old[f'depot{side}'])
            b[f'reps{side}'] = bytearray(old[f'reps{side}'])
            h[0x3a6+side*10:0x3b0+side*10] = source.header[0x200+side*10:0x20a+side*10]
        else:
            # Crusader RWStock: two 110-byte records in one block. Twenty
            # entries become D-Day's 26-entry stock record, retaining flags.
            original = old['stock'][side*110:(side+1)*110]
            count = original[88]
            if not 0 <= count <= 20:
                raise ValueError('Invalid Crusader supply entry count')
            stock = bytearray(136)
            stock[:4] = original[:4]
            stock[4:44] = original[8:48]
            stock[56:96] = original[48:88]
            put_short(stock, 108, count)
            stock[110:130] = original[90:110]
            b[f'stock{side}'] = stock
            # Crusader's supply distribution records have no D-Day-style
            # stocked reserve depot. Keep every location and create the reserve.
            depots = bytearray(24)
            struct.pack_into('<2h', depots, 12, -1, -1)
            depots[21] = 1
            for p in range(0, len(old[f'depot{side}']), 52):
                original = old[f'depot{side}'][p:p+52]
                depot = bytearray(24)
                depot[12:16] = original[40:44]
                depot[17:19] = bytes((252, 99))
                depot[21:23] = bytes((1, 1))
                depots += depot
            b[f'depot{side}'] = depots
            b[f'reps{side}'] = bytearray(i16(b['calendar'], 24)*9)
        put_short(h, 0x25c+side*2, len(b[f'stock{side}'])//136)
        h[0x3a0+side] = len(b[f'depot{side}'])//24
    if not source.stalin:
        report['adaptations'].append('Crusader supply locations and quantities are retained; D-Day adds a reserve depot and HQ distribution limits. Crusader has no serialized daily replacement table.')


def convert_scenario(path):
    source = WawScenario.read(path)
    roster = UnitRoster(game_path('dday', 'SCENARIO', 'BRADLEY.SCN').read_bytes())
    b, h, old = roster.blocks, roster.header, source.blocks
    report = dict(version=1, source=str(source.path), source_game=source.game, title=source.title,
                  source_sha256=hashlib.sha256(source.data).hexdigest(), adaptations=[],
                  runtime_slot='COBRA.SCN', engine_patch='dday-weather-400',
                  source_blocks={k: dict(offset=source.offsets[k], bytes=len(v), sha256=hashlib.sha256(v).hexdigest()) for k, v in old.items()})
    width, height = source.dimensions
    # D-Day retains the earlier operational-scale calendar. Its UTParser uses
    # Calendar+28 and its scale-3 routines expect three phases, not six.
    start = i32(source.header, 0x44 if source.stalin else 0xc)
    end = i32(source.header, 0x48 if source.stalin else 0x10)
    report.update(map_size=[width, height], unit_counts=[len(u) for u in source.units],
                  source_turns_per_day=old['calendar'][28], turns=end-start+1)
    struct.pack_into('<2i', h, 0x44, start, end)
    struct.pack_into('<4h', h, 0x224, 0, 0, height-1, width-1)
    offset = 0x1c4 if source.stalin else 0x50
    h[0x22c:0x238] = source.header[offset:offset+12]
    put_short(h, 0x238, 304)
    h[0x260:0x3e0] = bytes(0x180)
    if source.stalin:
        for p in range(4, 0x28, 4):
            struct.pack_into('<i', h, p, number(source.header, p, 1))
        # Stalingrad KIAVicPen multiplies by float nationality weights;
        # D-Day stores the same weights as integer percentages.
        for p in range(0x28, 0x44, 4):
            struct.pack_into('<i', h, p, number(source.header, p, 100))
    else:
        # Crusader has no serialized casualty-weight table. In particular,
        # Bradley's zero Italian weight would disable their casualty scoring.
        struct.pack_into('<7i', h, 0x28, *([100]*7))
    brief = 0x23a if source.stalin else 0x7c
    h[0x3e0:0xbe0] = source.header[brief:brief+0x800]
    h[0xbe0:0x1220] = source.header[brief+0x800:brief+0xd00]+bytes(320)
    h[0x1220:] = bytes(16)
    h[0x1220] = 3
    h[0x122a] = source.header[0xf44 if source.stalin else 0xda8]
    if not source.stalin:
        # Crusader DrawTownName (1dfb0..1e1a8) ignores the final label byte
        # and uses one color. D-Day interprets that byte as V/R/I and rejects
        # Crusader's numeric values. Use the ordinary place-name style.
        for index in range(h[0x122a]):
            h[0xbff+index*32] = ord('V')
    h[0x122b] = source.header[0xf45] if source.stalin else 2
    h[0x1222] = len(old['vicloc'])//48
    b['vicloc'] = bytearray(old['vicloc'])
    for p in range(0, len(b['vicloc']), 48):
        if source.stalin:
            for q in (p, p+4):
                struct.pack_into('<i', b['vicloc'], q, number(old['vicloc'], q))
        else:
            b['vicloc'][p+8:p+16] = old['vicloc'][p+12:p+16]+old['vicloc'][p+8:p+12]
    b['garrison'] = bytearray(old.get('garrison', b''))
    h[0x1223] = len(b['garrison'])//6
    b['calendar'] = bytearray(old['calendar'])
    struct.pack_into('<6i', b['calendar'], 0, start, start, end, start, 0, 0)
    b['calendar'][28] = old['calendar'][28]
    b['weather'] = weather(source, start, end)
    for key in ('hexmap', 'zoc'):
        b[key] = bytearray(old[key])
    b['uhexes'], art = terrain(source, report)
    b['hedgelist'] = bytearray(b'\xe8\xfd'*(width*height))
    b['hedges'] = bytearray(8)
    _units(source, roster, report)
    _supply(source, roster, report)
    # These arrays are runtime allocation state: init_for_ai resets them in
    # every engine. Source bytes remain available through WawScenario.blocks.
    b['ai_counts'] = bytearray(12)
    for key in ('bgstate', 'bgshx', 'bgshy', 'bgdhx', 'bgdhy'):
        b[key] = bytearray(800)
    b['victory'] = bytearray(1088)
    from lib.scenario_data import refresh_calendar
    refresh_calendar(roster)
    from lib.v4v_converter import initial_control_map, validate_conversion
    b['zoc'] = initial_control_map(roster, report['adaptations'])
    sheets = counters(source, roster, report)
    data = roster.to_bytes()
    validate_conversion(data)
    report['adaptations'].extend([
        'D-Day supplies the combat, movement, nationality and victory-tier rules. Source scenario-specific executable scripts are not present in SCN data and are not translated.',
        'Original HQ automation is retained. Runtime battlegroup allocations, accumulated victory scores, mounted links and saved movement paths are rebuilt for a fresh scenario.',
        'Source climate-generation parameters remain in the source data; the authored historical weather sequence and initial snow/ice/wetness are translated.',
    ])
    if not source.stalin:
        report['adaptations'].append('Commonwealth/Polish nationality codes use D-Day Allied nationality rules; Italian units use its Italian code. Names, statistics and original chits are retained.')
        report['adaptations'].append('Crusader has no serialized casualty weights; D-Day class weights are used with equal 100% nationality weighting. Place-name colors are translated to D-Day label styles.')
    report['output_sha256'] = hashlib.sha256(data).hexdigest()
    return data, art, sheets, report
