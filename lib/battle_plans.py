"""Authored battlegroup orders for the editor's patched D-Day engine.

The native bgstate/bgdhx/bgdhy arrays are reset by init_for_ai. Orders are
instead kept in an ignored SCN trailer and exported to WAWAI.DAT; the engine
hook applies them to units of the selected HQ as bg_stuff returns their
battlegroup orders. Native force allocation rebuilds OB+82 independently
of HQ assignment at OB+81, so saved battlegroup numbers are not authored IDs.
"""
import struct
import hashlib
import json
from lib.event_rules import (MAGIC as NESTED_MAGIC, ROW_SIZE, extended_plan, encode_row,
    normalize_expression, normalize_action, condition_leaves, expression_for_plan)
from lib.unit_roster import UnitRoster
from lib.scenario_rules import scenario_dates
from lib.unit_definitions import _integer

MAGIC = b'WAWAI001'
EVENT_MAGIC = b'WAWAI002'
ADVANCED_MAGIC = b'WAWAI003'
ORDERS = {1: 'Advance toward hex', 3: 'Retreat toward hex', 6: 'Surround hex',
          7: 'Idle', 8: 'Stay in position'}
KEYS = ('scenario', 'side', 'group', 'first', 'last', 'order', 'x', 'y')
CONDITIONS = {0: 'Always (timed order)', 1: 'Objective controlled by side',
              2: 'Side losses reach casualty points'}
EVENT_KEYS = ('trigger', 'trigger_side', 'objective', 'threshold', 'priority')
DEFAULT_EVENT = dict(trigger=0, trigger_side=0, objective=-1, threshold=0, priority=0)
EVENT_ROW = struct.Struct('<8hBBhHH')  # 24 bytes in the editor document.
MAX_PLANS = 256


def plan_conditions(plan):
    """Return mutable condition dictionaries, including the primary condition."""
    if plan.get('expression') is not None:
        return condition_leaves(plan['expression'])
    return ([plan] if plan.get('trigger') else []) + list(plan.get('extra_conditions', []))


def advanced_plan(plan):
    return bool(plan.get('extra_conditions') or plan.get('latch') or extended_plan(plan))


def _split(trailer):
    from lib.scenario_library import split_library_footer
    trailer, library = split_library_footer(trailer)
    stride = 0 if trailer.endswith((ADVANCED_MAGIC, NESTED_MAGIC)) else EVENT_ROW.size if trailer.endswith(EVENT_MAGIC) else 16
    if not trailer.endswith((MAGIC, EVENT_MAGIC, ADVANCED_MAGIC, NESTED_MAGIC)):
        return trailer+library, b'', stride
    if len(trailer) < 12:
        raise ValueError('Truncated battle plan trailer')
    size = struct.unpack_from('<I', trailer, len(trailer)-12)[0]
    if (stride and (size % stride or size > MAX_PLANS*stride)) or size > 262144 or size > len(trailer)-12:
        raise ValueError('Invalid battle plan trailer')
    return trailer[:-12-size]+library, trailer[-12-size:-12], stride


def battle_plans(roster):
    _, payload, stride = _split(roster.trailer)
    if stride == 0:
        try:
            return normalize_plans(roster, json.loads(payload))
        except (TypeError, KeyError, AttributeError, UnicodeError, ValueError) as exc:
            raise ValueError(f'Invalid advanced battle plan trailer: {exc}') from exc
    if stride == 16:
        return [dict(zip(KEYS, row)) for row in struct.iter_unpack('<8h', payload)]
    return [dict(zip(KEYS+EVENT_KEYS, row)) for row in EVENT_ROW.iter_unpack(payload)]


def normalize_plans(roster, plans):
    if not isinstance(plans, (list, tuple)) or len(plans) > MAX_PLANS:
        raise ValueError('At most 256 battle plan phases are supported')
    start, end = scenario_dates(roster)
    top,left,bottom,right = struct.unpack_from('<4h',roster.header,0x224)
    normalized=[]
    for plan in plans:
        if plan.get('expression') is not None:
            plan={**plan,**DEFAULT_EVENT,'priority':plan.get('priority',0),'extra_conditions':[]}
        p={k:_integer(plan[k], k.capitalize(), -32768, 32767) for k in KEYS if k!='scenario'}
        p['scenario']=roster.header[0x1220]
        message = plan.get('action') == 'message'
        if p['side'] not in (0,1) or (not message and not 0 <= p['group'] < roster.count(0x23c,p['side'])):
            raise ValueError('Choose an existing HQ battlegroup')
        if not 1 <= p['first'] <= p['last'] <= end-start+1:
            raise ValueError('Battle plan turns must fall within the scenario')
        if p['order'] not in ORDERS:
            raise ValueError('Unknown battlegroup order')
        if not (left <= p['x'] < right and top <= p['y'] < bottom):
            raise ValueError('Battle plan goals must be within the playable map')
        if message:
            p['group'] = -1
        p.update({k: _integer(plan.get(k, default), k.replace('_', ' ').capitalize(),
                              -1 if k == 'objective' else 0, 65535 if k == 'threshold' else 255)
                  for k, default in DEFAULT_EVENT.items()})
        if p['trigger'] not in CONDITIONS:
            raise ValueError('Choose a supported condition')
        if p['trigger_side'] not in (0, 1):
            raise ValueError('Choose the side whose control or losses to test')
        if p['trigger'] == 1 and not 0 <= p['objective'] < roster.header[0x1222]:
            raise ValueError('Choose an existing victory objective')
        if p['trigger'] == 2 and not 1 <= p['threshold'] <= 65535:
            raise ValueError('Loss threshold must be 1–65535 casualty points')
        if p['trigger'] != 1:
            p['objective'] = -1
        if p['trigger'] != 2:
            p['threshold'] = 0
        if p['trigger'] == 0:
            p['trigger_side'] = 0
        extras = plan.get('extra_conditions', [])
        if not isinstance(extras, (list, tuple)) or len(extras) > 2:
            raise ValueError('A plan supports up to three conditions')
        match = plan.get('match', 'all')
        if match not in ('all', 'any'):
            raise ValueError('Choose ALL or ANY conditions')
        latch = plan.get('latch', 0)
        latch = _integer(int(latch) if isinstance(latch, bool) else latch, 'Keep active after matching', 0, 1)
        if extras and not p['trigger']:
            raise ValueError('Choose a first condition before adding more conditions')
        normalized_extras = []
        for condition in extras:
            if not isinstance(condition, dict) or condition.get('extra_conditions') or condition.get('latch'):
                raise ValueError('Invalid additional condition')
            if condition.get('trigger', 0) == 0:
                raise ValueError('Additional conditions must test an objective or losses')
            if 'children' in condition or 'operator' in condition:
                raise ValueError('Use the nested condition editor for condition groups')
            normalized_extras.append(normalize_expression(condition, roster.header[0x1222]))
        if normalized_extras or latch:
            p.update(extra_conditions=normalized_extras, match=match, latch=bool(latch))
        if plan.get('expression') is not None:
            p['expression'] = normalize_expression(plan['expression'], roster.header[0x1222])
            p.update(DEFAULT_EVENT | {'priority': p['priority']})
            p.pop('extra_conditions', None)
            p.pop('match', None)
        normalize_action(roster,plan,p)
        for old in normalized:
            if (old.get('action','order') == p.get('action','order') == 'order' and old['side']==p['side'] and old['group']==p['group'] and old['priority']==p['priority']
                    and max(old['first'],p['first'])<=min(old['last'],p['last'])):
                raise ValueError('Overlapping plans for this HQ need different priorities; the highest matching priority wins')
        normalized.append(p)
    return normalized


def encode_plans(roster, plans):
    """Export runtime rows, highest priority first.

    Legacy files use 16-byte rows; high bytes carry the trigger and argument.
    Combined/latching rules use a fingerprinted header and 32-byte rows.
    Earlier engines safely skip the advanced table, including fallback rows.
    """
    normalized = sorted(normalize_plans(roster, plans), key=lambda p: -p['priority'])
    if any(extended_plan(p) for p in normalized):
        result = b''.join(encode_row(p) for p in normalized)
        fingerprint = hashlib.blake2s(result,digest_size=16).digest()
        header = NESTED_MAGIC+struct.pack('<HH',len(normalized),ROW_SIZE)+fingerprint[:4]
        return header+b'\xff\xff'+fingerprint[4:]+b'\0\0'+result
    if any(advanced_plan(p) for p in normalized):
        result = bytearray()
        for p in normalized:
            row = [p[k] for k in KEYS]
            row[0] |= (0x80 | int(p.get('latch', False))) << 8
            conditions = plan_conditions(p)
            result += struct.pack('<8H', *row)
            result += struct.pack('<HBB', 0xffff, int(p.get('match', 'all') == 'any'), len(conditions))
            for c in conditions:
                result += struct.pack('<BBH', c['trigger'], c['trigger_side'],
                                      c['objective'] if c['trigger'] == 1 else c['threshold'])
            result += bytes(4*(3-len(conditions)))
        # Every 16-byte chunk has an unmatchable/unsupported selector in the
        # older engine. A partial downgrade cannot accidentally execute data.
        fingerprint = hashlib.blake2s(result, digest_size=16).digest()
        header = ADVANCED_MAGIC + struct.pack('<HH', len(normalized), 32) + fingerprint[:4]
        return header + b'\xff\xff' + fingerprint[4:] + b'\0\0' + result
    result = bytearray()
    for p in normalized:
        row = list(p[k] for k in KEYS)
        if p['trigger']:
            row[0] |= (1 + (p['trigger']-1)*2 + p['trigger_side']) << 8
            argument = p['objective'] if p['trigger'] == 1 else p['threshold']
            row[1] |= (argument & 255) << 8
            row[2] |= (argument >> 8) << 8
        result.extend(struct.pack('<8H', *row))
    return bytes(result)


def set_battle_plans(data, plans):
    from lib.scenario_library import split_library_footer
    roster=UnitRoster(data)
    rows = normalize_plans(roster, plans)
    advanced = any(advanced_plan(p) for p in rows)
    extended = any(p['trigger'] or p['priority'] for p in rows)
    if advanced:
        payload = json.dumps(rows, sort_keys=True, separators=(',', ':')).encode('utf-8')
    elif extended:
        payload = b''.join(EVENT_ROW.pack(*(p[k] for k in KEYS+EVENT_KEYS)) for p in rows)
    else:
        payload = b''.join(struct.pack('<8h', *(p[k] for k in KEYS)) for p in rows)
    base, _, _ = _split(roster.trailer)
    base, library = split_library_footer(base)
    magic = NESTED_MAGIC if any(extended_plan(p) for p in rows) else ADVANCED_MAGIC if advanced else EVENT_MAGIC if extended else MAGIC
    roster.trailer=base+(payload+struct.pack('<I',len(payload))+magic if payload else b'')+library
    return roster.to_bytes()


def _condition_label(plan, objectives):
    kind = plan.get('trigger', 0)
    if not kind:
        return 'Always'
    side = ('Allied', 'Axis')[plan['trigger_side']]
    if kind == 2:
        return f"{side} losses ≥ {plan['threshold']} casualty points"
    index = plan['objective']
    name = objectives[index]['name'] if 0 <= index < len(objectives) else f'Missing objective {index}'
    return f'{side} controls {name}'


def condition_label(plan, objectives):
    if plan.get('expression') is not None:
        def describe(node):
            if 'children' not in node:
                return _condition_label(node, objectives)
            return '('+(' AND ' if node['operator']=='all' else ' OR ').join(describe(c) for c in node['children'])+')'
        return ('Keep active once matched: ' if plan.get('latch') else '')+describe(plan['expression'])
    conditions = plan_conditions(plan)
    join = ' AND ' if plan.get('match', 'all') == 'all' else ' OR '
    text = join.join(_condition_label(c, objectives) for c in conditions) or 'Always'
    return ('Keep active once matched: ' if plan.get('latch') else '') + text


def export_plans(data):
    roster=UnitRoster(data)
    return encode_plans(roster,battle_plans(roster))
