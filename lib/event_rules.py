"""Bounded nested conditions and one-shot scenario actions (WAWAI004)."""
import struct
from lib.unit_definitions import _integer

MAGIC = b'WAWAI004'
ROW_SIZE = 320
MAX_TOKENS = 32
MAX_LEAVES = 16
MAX_DEPTH = 4
MESSAGE_BYTES = 120
ACTIONS = {'order': 'Issue HQ orders', 'release': 'Release HQ reinforcements',
           'message': 'Show public scenario message'}


def condition_leaves(tree):
    if 'children' in tree:
        return [leaf for child in tree['children'] for leaf in condition_leaves(child)]
    return [tree]


def normalize_expression(tree, objective_count):
    count = [0, 0]
    def visit(node, depth):
        count[0] += 1
        if not isinstance(node, dict) or count[0] > MAX_TOKENS or depth > MAX_DEPTH:
            raise ValueError('Conditions allow at most 32 nodes and four nested groups')
        if 'operator' in node or 'children' in node:
            if node.get('operator') not in ('all', 'any'):
                raise ValueError('Choose ALL or ANY for each condition group')
            children = node.get('children')
            if not isinstance(children, (list,tuple)) or not 1 <= len(children) <= MAX_LEAVES:
                raise ValueError('Each condition group needs 1–16 children')
            return dict(operator=node['operator'], children=[visit(c,depth+1) for c in children])
        count[1] += 1
        if count[1] > MAX_LEAVES:
            raise ValueError('An expression supports at most 16 condition checks')
        trigger = _integer(node.get('trigger',0),'Condition',1,2)
        side = _integer(node.get('trigger_side',0),'Condition side',0,1)
        objective = _integer(node.get('objective',-1),'Objective',0,objective_count-1) if trigger==1 else -1
        threshold = _integer(node.get('threshold',0),'Casualty points',1,65535) if trigger==2 else 0
        return dict(trigger=trigger, trigger_side=side, objective=objective, threshold=threshold)
    return visit(tree, 0)


def expression_for_plan(plan):
    if plan.get('expression') is not None:
        return plan['expression']
    conditions = ([plan] if plan.get('trigger') else []) + list(plan.get('extra_conditions',[]))
    return dict(operator=plan.get('match','all'), children=conditions) if conditions else None


def expression_tokens(tree):
    if tree is None:
        return b''
    if 'children' not in tree:
        return struct.pack('<BBH',tree['trigger'],tree['trigger_side'],
                           tree['objective'] if tree['trigger']==1 else tree['threshold'])
    return b''.join(expression_tokens(c) for c in tree['children'])+struct.pack('<BBH',
        16 if tree['operator']=='all' else 17,len(tree['children']),0)


def extended_plan(plan):
    return plan.get('expression') is not None or plan.get('action','order') != 'order'


def normalize_action(roster, plan, result):
    action = plan.get('action','order')
    if action not in ACTIONS:
        raise ValueError('Choose a supported event action')
    if action == 'order':
        return
    result.update(action=action,latch=False,order=7,
                  x=struct.unpack_from('<h',roster.header,0x226)[0],
                  y=struct.unpack_from('<h',roster.header,0x224)[0])
    if action == 'release':
        side,group = result['side'],result['group']
        hqs = [r for r in roster.records[side] if r[0x76]==7 and struct.unpack_from('<i',r,4)[0]==group
               and struct.unpack_from('<i',r,8)[0]!=-1]
        if not hqs:
            raise ValueError('Choose an existing HQ for the reinforcement release')
        flag = plan.get('hold',True)
        result['hold'] = bool(_integer(int(flag) if isinstance(flag,bool) else flag,'Hold reinforcements',0,1))
    else:
        message = plan.get('message','')
        if not isinstance(message,str):
            raise ValueError('Enter a scenario message')
        message = message.strip()
        try: encoded = message.encode('cp437')
        except UnicodeEncodeError:
            raise ValueError('Scenario messages require DOS characters') from None
        if not 1 <= len(encoded) < MESSAGE_BYTES or any(c<32 or c==127 for c in encoded):
            raise ValueError('Scenario messages need 1–119 printable DOS characters')
        result['message'] = message


def encode_row(plan):
    """Every aligned legacy row starts with an unsupported selector.

    First 16 bytes keep the HQ order layout with marker 0x84/0x85. The
    remaining 19 chunks each carry a 0xffff guard and fourteen payload bytes.
    Compact logical layout: header16, action/length/hold/reserved16, RPN128,
    null-terminated message120, reserved2. Total 282 logical /320 physical.
    """
    logical = bytearray(282)
    struct.pack_into('<8H',logical,0,plan['scenario'] | (0x84|int(plan.get('latch',False)))<<8,
                     plan['side'],plan['group'] & 65535,plan['first'],plan['last'],
                     plan['order'],plan['x'],plan['y'])
    tokens=expression_tokens(expression_for_plan(plan))
    if len(tokens)>MAX_TOKENS*4:
        raise ValueError('Condition expression exceeds the runtime limit')
    logical[16]=tuple(ACTIONS).index(plan.get('action','order'))
    logical[17]=len(tokens)//4
    logical[18]=int(plan.get('hold',False)) if plan.get('action')=='release' else 0
    logical[32:32+len(tokens)]=tokens
    if plan.get('action')=='message':
        text=plan['message'].encode('cp437')
        logical[160:160+len(text)]=text
    struct.pack_into('<I',logical,28,sum(logical))
    return bytes(logical[:16])+b''.join(b'\xff\xff'+logical[i:i+14] for i in range(16,282,14))
