"""Native HQ logistics, mounted transport and plotted movement orders.

Protected-mode D-Day references: DrawSupplyData 3a4d0, CalcHQDisbPct 55b2c,
ClearSupplyConsumed 57133, SetHQSupplyLevel 561bc, Ridem 3bc7f, Dismount
3c02a, EligibleToRide 3c86c, store_orders 69328 and ResetUnit 1220f.
These are ordinary SCN records; no executable extension is needed.
"""
import struct
from decimal import Decimal, InvalidOperation

from lib.unit_roster import UnitRoster, short, put_short
from lib.unit_reader import decode_record, TACTICAL_ORDERS, SECONDARY_ORDERS
from lib.unit_definitions import _unit
from lib.map_editor import hex_neighbor

SUPPLY_LEVELS = ('None', 'Minimal', 'Defense', 'General', 'Attack')
ROUTE_MODES = (0, 1, 4, 5, 6, 7)
STANCES = (8, 9, 10)
ORDER_CHOICES = {i: TACTICAL_ORDERS[i] for i in (*ROUTE_MODES, *STANCES)}
SECONDARY_CHOICES = dict(enumerate(('None', *SECONDARY_ORDERS[1:])))
_KEEP = object()


def secondary_choices(roster, side, index):
    """Structural eligibility; stock, supply and enemy action resolve in play."""
    record = _ground(roster, side, index)
    choices = [0, 2]
    # GetRepType: HQs and descriptor 64 (supply) have no replacement pool.
    if record[0x76] != 7 and record[0x77] != 64:
        choices.append(1)
    # BuildButton also admits construction descriptor 93, but excludes 63.
    if (record[0x76] == 2 or record[0x77] == 93) and record[0x77] != 63:
        choices.append(3)
    if record[0x76] == 4:
        block, start = _aux(roster, side, record, 'arty', 28)
        choices.extend((4, 5, 6, 7))
        if block[start+0x14]:
            choices.append(8)
    return {i: SECONDARY_CHOICES[i] for i in sorted(choices)}


def hex_distance(origin, target):
    # Even-row offset coordinates -> axial; agrees with hex_rdir_rdist_hdist.
    a, b = ((x-(y+1)//2, y) for x, y in (origin, target))
    dx, dy = a[0]-b[0], a[1]-b[1]
    return max(abs(dx), abs(dy), abs(dx+dy))


def _terrain(roster, cell):
    width = short(roster.header, 0x22a)+1
    slot = struct.unpack_from('<H', roster.blocks['hexmap'], 2*(cell[1]*width+cell[0]))[0]
    return min(roster.blocks['uhexes'][slot*4] & 15, 14)


def fire_pattern(roster, side, target):
    """SetFireTarget (34fbc): six adjacent friendly-support hexes, then center.

    1 is bombardment, 2 is friendly support. These are mission assignments,
    not merely display flags. Read the same occupancy/ownership bits as native
    FRIENDinHEX; territorial ownership alone does not make a hex friendly.
    """
    def friendly(cell):
        if not _inside(roster, cell):
            return False
        width = short(roster.header, 0x22a)+1
        word = struct.unpack_from('<I', roster.blocks['zoc'], 4*(cell[1]*width+cell[0]))[0]
        return bool(word & 0x1e0000) and (word >> 16) & 1 == side
    return bytes([2 if friendly(hex_neighbor(target, d)) else 0 for d in range(6)]
                 + [2 if friendly(target) else 1])


def _aux(roster, side, record, kind, stride):
    offset = struct.unpack_from('<i', record, 4)[0] * stride
    block = roster.blocks.get(f'{kind}{side}', b'')
    if not 0 <= offset <= len(block)-stride:
        raise ValueError(f'Invalid {kind} record for this unit.')
    return block, offset


def _ground(roster, side, index):
    record = _unit(roster, side, index)
    if record[0x76] in (5, 6) or decode_record(record)['deleted']:
        raise ValueError('Choose a ground unit that has not been deleted.')
    return record


def _inside(roster, cell):
    return (short(roster.header, 0x226) <= cell[0] < short(roster.header, 0x22a)
            and short(roster.header, 0x224) <= cell[1] < short(roster.header, 0x228))


def _active(roster, record):
    return (_in_play(roster, record)
            and short(record, 0x64) != 0 and _inside(roster, struct.unpack_from('<2h', record, 0x58)))


def _in_play(roster, record):
    arrival = struct.unpack_from('<i', record, 8)[0]
    return arrival != -1 and arrival < struct.unpack_from('<i', roster.blocks['calendar'], 12)[0]


def _tons(value):
    try:
        number = Decimal(str(value)) * 100
        if not number.is_finite() or number != number.to_integral_value() or not 0 <= number <= 2147483647:
            raise ValueError()
        return int(number)
    except (ValueError, InvalidOperation, OverflowError) as exc:
        raise ValueError('Supply must be 0–21,474,836.47 tons, with at most two decimal places.') from exc


def supply_state(roster, side, index):
    record = _ground(roster, side, index)
    result = dict(carried=struct.unpack_from('<i', record, 0x0c)[0] / 100,
                  level=record[0x8e], path=record[0x8f], hq=record[0x76] == 7)
    if result['hq']:
        block, start = _aux(roster, side, record, 'hqs', 58)
        for key, offset in (('reserve', 0), ('distribution', 4), ('received', 8), ('request', 12)):
            result[key] = struct.unpack_from('<i', block, start+offset)[0] / 100
        hq = start//58
        result.update(source=short(block, start+0x2a), entry=short(block, start+0x2c), path=block[start+0x39])
        result['consumed'] = (struct.unpack_from('<i', roster.header, 0x54+side*0xb4+hq*4)[0]/100
                              if hq < 45 else None)
    return result


def edit_supply(data, side, index, *, carried=None, reserve=None, distribution=None,
                level=None, apply_members=False):
    roster = UnitRoster(data)
    record = _ground(roster, side, index)
    if carried is not None:
        struct.pack_into('<i', record, 0x0c, _tons(carried))
    if reserve is not None or distribution is not None or apply_members:
        if record[0x76] != 7:
            raise ValueError('Reserve and subordinate distribution settings belong to HQs.')
        block, start = _aux(roster, side, record, 'hqs', 58)
        for value, offset in ((reserve, 0), (distribution, 4)):
            if value is not None:
                struct.pack_into('<i', block, start+offset, _tons(value))
    if level is not None:
        if level not in range(5):
            raise ValueError('Choose one of the five supply levels.')
        record[0x8e] = level
        if apply_members:
            # SetHQSupplyLevel visits this HQ's direct OB chain, not child HQs.
            member = short(record, 0x6a)
            seen = {index}
            while member >= 0:
                if member in seen:
                    raise ValueError('The HQ subordinate chain contains a cycle.')
                seen.add(member)
                unit = _ground(roster, side, member)
                if unit[0x76] == 7 or unit[0x81] != record[0x81]:
                    raise ValueError('Inconsistent HQ subordinate chain.')
                if _in_play(roster, unit) and unit[0x8f] != 4 and unit[0x79] != 10:
                    unit[0x8e] = level
                member = short(unit, 0x6a)
    return roster.to_bytes()


def transport_groups(roster, side):
    """Validate both ends of every mounted group before changing linked units."""
    groups, passengers = {}, set()
    for index, record in enumerate(roster.records[side][:roster.count(0x240, side)]):
        if record[0x76] != 1:
            continue
        block, start = _aux(roster, side, record, 'tanks', 10)
        count = block[start+9]
        if count > 3:
            raise ValueError('Invalid transport passenger count (maximum three).')
        ids = [short(block, start+i*2) for i in range(count)]
        if bool(count) != bool(record[0x91]):
            raise ValueError('Inconsistent carrier mounted flag.')
        if not count:
            continue
        if decode_record(record)['deleted']:
            raise ValueError('A deleted carrier still has mounted passengers.')
        if index == 0 or len(set(ids)) != count or set(ids) & passengers:
            raise ValueError('Invalid or duplicate mounted passenger reference.')
        size = 0
        for passenger in ids:
            rider = _unit(roster, side, passenger)
            if decode_record(rider)['deleted']:
                raise ValueError('A deleted unit is still listed as a passenger.')
            if rider[0x76] not in (0, 2) or rider[0x79] != 0:
                raise ValueError('Only foot infantry and engineers can ride armor.')
            riders, pos = _aux(roster, side, rider, 'riders', 4)
            if (short(riders, pos) != index or short(riders, pos+2) != short(block, start+6)
                    or not rider[0x91] or rider[0x78] & 15 != 2 or rider[0x86]
                    or rider[0x58:0x5c] != record[0x58:0x5c]):
                raise ValueError('Inconsistent passenger/carrier links, location or orders.')
            size += rider[0x7e]
            if not 1 <= rider[0x7e] <= record[0x7e]:
                raise ValueError('A passenger is larger than its carrier.')
        if size != block[start+8] or size > 3:
            raise ValueError('Inconsistent transport load (maximum three size points).')
        groups[index] = ids
        passengers.update(ids)
    for index, record in enumerate(roster.records[side][:roster.count(0x240, side)]):
        if record[0x76] in (0, 2) and record[0x79] == 0:
            riders, pos = _aux(roster, side, record, 'riders', 4)
            if bool(short(riders, pos)) != (index in passengers):
                raise ValueError('A passenger refers to a carrier that does not list it.')
        if record[0x91] and index not in passengers and index not in groups:
            raise ValueError('Unrecognized mounted transport link.')
    return groups


def dismount(roster, side, passenger):
    """Private-roster mutation; caller validates the group before entering."""
    rider = _unit(roster, side, passenger)
    riders, pos = _aux(roster, side, rider, 'riders', 4)
    carrier = short(riders, pos)
    if not carrier:
        return
    tank = _unit(roster, side, carrier)
    tanks, start = _aux(roster, side, tank, 'tanks', 10)
    ids = [short(tanks, start+i*2) for i in range(tanks[start+9])]
    ids.remove(passenger)
    tanks[start:start+6] = struct.pack('<3h', *(ids+[0]*(3-len(ids))))
    tanks[start+8] -= rider[0x7e]
    tanks[start+9] = len(ids)
    if not ids:
        put_short(tanks, start+6, 0)
        tank[0x91] = 0
    riders[pos:pos+4] = bytes(4)
    rider[0x91], rider[0x78] = 0, 9


def edit_transport(data, side, passenger, carrier=None):
    roster = UnitRoster(data)
    groups = transport_groups(roster, side)
    rider = _ground(roster, side, passenger)
    if rider[0x76] not in (0, 2) or rider[0x79] != 0:
        raise ValueError('Only foot infantry and engineers can ride armor.')
    riders, pos = _aux(roster, side, rider, 'riders', 4)
    old = short(riders, pos)
    if old == (0 if carrier is None else carrier) and carrier != 0:
        return data
    if carrier is None:
        dismount(roster, side, passenger)
        return roster.to_bytes()
    tank = _ground(roster, side, carrier)
    if tank[0x76] != 1 or carrier == 0:
        raise ValueError('Choose armor with a nonzero OB index; index zero means dismounted in the game.')
    if not _active(roster, rider) or not _active(roster, tank) or rider[0x58:0x5c] != tank[0x58:0x5c]:
        raise ValueError('Deploy the passenger and carrier in the same hex before mounting.')
    if rider[0x7c] or tank[0x7c]:
        raise ValueError('Units already linked to a battle cannot change transport here.')
    size = rider[0x7e]
    load = sum(roster.records[side][i][0x7e] for i in groups.get(carrier, []))
    if not 1 <= size <= tank[0x7e] or size+load > 3 or len(groups.get(carrier, [])) >= 3:
        raise ValueError('The carrier needs room: at most three passengers and three total size points; each passenger must fit its size.')
    if load and (size > 1 or load > 1):
        # Ridem evicts its first passenger in this case even though the table
        # has three slots. Require an explicit dismount instead of silently
        # replacing an existing passenger when selecting a carrier.
        raise ValueError('Dismount an existing passenger first. The game mounts one larger unit or two size-1 units on armor.')
    if old:
        dismount(roster, side, passenger)
    tanks, start = _aux(roster, side, tank, 'tanks', 10)
    color = short(tanks, start+6)
    if not color:
        used = set()
        for other in groups:
            unit = roster.records[side][other]
            if unit[0x58:0x5c] == tank[0x58:0x5c]:
                block, off = _aux(roster, side, unit, 'tanks', 10)
                used.add(short(block, off+6))
        color = next((c for c in (3, 4, 5, 6) if c not in used), 1)
    put_short(tanks, start+tanks[start+9]*2, passenger)
    put_short(tanks, start+6, color)
    tanks[start+8] += size
    tanks[start+9] += 1
    struct.pack_into('<2h', riders, pos, carrier, color)
    tank[0x91] = rider[0x91] = 1
    rider[0x78], rider[0x86] = 2, 0
    roster.orders.pop((side, passenger), None)
    transport_groups(roster, side)
    return roster.to_bytes()


def dismount_all(data, side, carrier):
    roster = UnitRoster(data)
    groups = transport_groups(roster, side)
    for passenger in groups.get(carrier, []):
        dismount(roster, side, passenger)
    return roster.to_bytes()


def saved_orders(roster, side, index):
    record = _ground(roster, side, index)
    cell = struct.unpack_from('<2h', record, 0x58)
    path = [cell]
    count = record[0x86]
    slot = struct.unpack_from('<H', record, 0x52)[0]
    if count and record[0x78] & 15 < 8:
        route = roster.orders.get((side, index), b'')
        if count >= len(route) or len(route) != slot:
            raise ValueError('Invalid saved movement buffer.')
        # PlotMove does not refresh Orders[0]; OB+86 is the authoritative count.
        for direction in reversed(route[1:count+1]):
            cell = hex_neighbor(cell, direction)
            if not _inside(roster, cell):
                raise ValueError('A saved movement route leaves the playable map.')
            path.append(cell)
    result = dict(path=path, mode=record[0x78] & 15, modifier=record[0x78] >> 4,
                target=struct.unpack_from('<2h', record, 0x5c),
                automatic=struct.unpack_from('<2h', record, 0x60),
                limit=max(0, min(255, slot-1)))
    result['fire_target'] = result['target'] if result['modifier'] in (5, 8) and count else None
    if record[0x76] == 4:
        block, start = _aux(roster, side, record, 'arty', 28)
        result.update(preparation=block[start+0x12], preparation_turns=block[start+0x10],
                      range=block[start+0x11], shoot_scoot=bool(block[start+0x14]),
                      pattern=bytes(block[start+0x15:start+0x1c]))
    return result


def edit_orders(data, side, index, path=(), mode=9, *, modifier=None,
                target=_KEEP, preparation=None):
    """Replace a route/stance and explicitly chosen native secondary order.

    Omitted modifier/target/preparation preserve existing authored choices.
    Pass modifier=0 to clear the secondary order, or target=None to clear a
    plotted fire mission while keeping the artillery ready for targeting.
    """
    roster = UnitRoster(data)
    record = _ground(roster, side, index)
    previous_modifier = record[0x78] >> 4
    modifier = previous_modifier if modifier is None else modifier
    old_target = (struct.unpack_from('<2h', record, 0x5c)
                  if previous_modifier in (5, 8) and record[0x86] else None)
    if target is _KEEP:
        target = old_target if modifier in (5, 8) else None
    if target is not None:
        if (not isinstance(target, (tuple, list)) or len(target) != 2
                or any(not isinstance(v, int) for v in target) or not _inside(roster, target)):
            raise ValueError('Choose a fire target inside the playable map.')
        target = tuple(target)
    if mode not in ORDER_CHOICES:
        raise ValueError('Choose a movement or defensive order; use Transport to assign passengers.')
    if record[0x78] & 15 == 2 or (record[0x91] and record[0x76] != 1):
        raise ValueError('Dismount this passenger before changing its orders.')
    if record[0x7c]:
        raise ValueError('This unit is linked to an active battle; its battle records must remain intact.')
    origin = struct.unpack_from('<2h', record, 0x58)
    path = [tuple(cell) for cell in path] or [origin]
    if path[0] != origin:
        raise ValueError('The route must start at the unit’s current hex.')
    count = len(path)-1
    gun, aux, remaining = None, None, None
    if record[0x76] == 4:
        gun, aux = _aux(roster, side, record, 'arty', 28)
        remaining = gun[aux+0x12]
        old_pattern = bytes(gun[aux+0x15:aux+0x1c])
        if preparation is None:
            preparation = (0 if record[0x79] == 10 else gun[aux+0x10]) if (
                modifier == 4 and previous_modifier != 4) else remaining
    elif preparation is not None:
        raise ValueError('Preparation time belongs to artillery units.')
    # An unchanged form must not normalize native state, recalculate a target
    # pattern, erase automatic goals, or rewrite stale route-buffer padding.
    try:
        old = saved_orders(roster, side, index)
        if (mode == old['mode'] and modifier == previous_modifier and path == old['path']
                and target == old_target and preparation == remaining):
            return data
    except ValueError:
        pass  # An explicitly replaced route may repair an invalid old buffer.
    if modifier not in secondary_choices(roster, side, index):
        raise ValueError('This unit cannot use that secondary order. Choose an available order or None.')
    if modifier and mode not in STANCES:
        raise ValueError('Secondary orders require a defensive stance. Choose None before plotting movement.')
    if modifier in (1, 4, 5, 6, 7, 8) and mode != 9:
        raise ValueError('Replace and artillery missions use the Defend if attacked stance.')
    if modifier and not _active(roster, record):
        raise ValueError('Deploy this unit before assigning a secondary order.')
    if modifier in (2, 3) and _terrain(roster, origin) in (3, 7, 8, 9):
        raise ValueError('The game cannot dig in or fortify this terrain.')
    if target is not None and modifier not in (5, 8):
        raise ValueError('Only Target and Shoot ’n scoot take a plotted fire target.')
    if gun is not None:
        if not isinstance(preparation, int) or not 0 <= preparation <= 18:
            raise ValueError('Artillery preparation remaining must be a whole number from 0 to 18 turns.')
        if modifier in (5, 6, 7, 8) and preparation:
            raise ValueError('This artillery is still preparing. Choose Prepare or set preparation remaining to zero.')
        if modifier == 4 and (not preparation or record[0x79] == 10):
            raise ValueError('Prepare needs 1–18 turns and mobile artillery. Use Target for ready or fixed guns.')
        if target is not None:
            if _terrain(roster, target) == 5:
                raise ValueError('The game cannot plot a ground bombardment in water.')
            if hex_distance(origin, target) > gun[aux+0x11]:
                raise ValueError(f'Target is beyond this artillery’s range of {gun[aux+0x11]} hexes.')
    if count and mode not in ROUTE_MODES:
        raise ValueError('A defensive stance cannot include a movement route. Clear the route first.')
    if mode in ROUTE_MODES and (not _active(roster, record) or record[0x79] == 10 or not count):
        raise ValueError('Movement requires a deployed, mobile unit and at least one route step.')
    slot = struct.unpack_from('<H', record, 0x52)[0]
    if count > min(255, max(0, slot-1)):
        raise ValueError(f'This unit’s movement buffer holds at most {max(0, min(255, slot-1))} steps.')
    directions = []
    for previous, cell in zip(path, path[1:]):
        if not _inside(roster, cell):
            raise ValueError('Every route step must be inside the playable map.')
        direction = next((d for d in range(6) if hex_neighbor(previous, d) == cell), None)
        if direction is None:
            raise ValueError('Add adjacent hexes in movement order.')
        directions.append(direction)
    if count:
        start = struct.unpack_from('<H', record, 0x50)[0]
        total = struct.unpack_from('<I', roster.header, 0x4c+side*4)[0]
        if start+slot > total:
            raise ValueError('The unit’s movement buffer lies outside its side’s orders storage.')
        for other, unit in enumerate(roster.records[side][:roster.count(0x240, side)]):
            offset, size = struct.unpack_from('<2H', unit, 0x50)
            if other != index and size and max(start, offset) < min(start+slot, offset+size):
                raise ValueError('The unit’s movement buffer overlaps another unit’s storage.')
        buffer = bytearray(slot)
        buffer[0] = count
        buffer[1:count+1] = bytes(reversed(directions))
        roster.orders[side, index] = bytes(buffer)
    else:
        roster.orders.pop((side, index), None)
    record[0x78], record[0x85], record[0x86] = mode | modifier << 4, 0, count
    leader = struct.unpack_from('<b', record, 0x90)[0]
    if leader >= 0:
        leaders = roster.blocks.get(f'leaders{side}', b'')
        if len(leaders) < (leader+1)*36:
            raise ValueError('Invalid attached leader record.')
        leaders[leader*36+0x1f] = 0  # ResetUnit -> SetLeaderBattID
    struct.pack_into('<4h', record, 0x5c, *path[-1], -1, -1)
    if count or modifier or short(record, 0x64) == -1:
        put_short(record, 0x64, -1 if count or modifier in (1, 2, 3, 6, 7) or target else 7)
    if gun is not None:
        gun[aux+0x12] = preparation
        gun[aux+0x15:aux+0x1c] = bytes(7)
        if modifier >= 4:
            struct.pack_into('<2h', record, 0x5c, *(target or (-1, -1)))
        if target is not None:
            record[0x86] = 1
            # Keep existing coverage when only switching Target/Shoot 'n scoot.
            # A newly plotted target follows the native SetFireTarget default.
            gun[aux+0x15:aux+0x1c] = (old_pattern if target == old_target
                                      else fire_pattern(roster, side, target))
    return roster.to_bytes()
