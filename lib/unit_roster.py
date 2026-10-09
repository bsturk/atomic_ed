"""D-Day roster mutations, following LoadGame/RWOB and the game's linked lists.

Ground OB numbers are stable: scenario-specific code refers to them directly.
Deleting uses a removed record, not compaction. New ground units go immediately
before support units; support class heads and unit IDs move with their records.
"""
import struct

from lib.unit_reader import decode_record, prepare_unit_changes


def short(data, offset):
    return struct.unpack_from('<h', data, offset)[0]


def put_short(data, offset, value):
    struct.pack_into('<h', data, offset, value)


class UnitRoster:
    def __init__(self, data):
        self.blocks = {}
        self.offset = 0
        self.source = data
        for name, multiple in self._layout():
            if multiple:
                if self.offset + 4 > len(data):
                    raise ValueError(f'Missing {name} block')
                size = struct.unpack_from('<I', data, self.offset)[0] * multiple
                self.offset += 4
            else:
                size = 12
            if self.offset + size > len(data):
                raise ValueError(f'Truncated {name} block')
            self.blocks[name] = bytearray(data[self.offset:self.offset + size])
            self.offset += size
        self.records = [[bytearray(self.blocks[f'ob{s}'][i:i + 172])
                         for i in range(0, len(self.blocks[f'ob{s}']), 172)] for s in (0, 1)]
        self.validate()
        # RestoreOrders reads only units with saved orders. Preserve any extra
        # trailer bytes (some distributed SCNs have an unused orders trailer).
        self.orders = {}
        for side in (0, 1):
            for index, record in enumerate(self.records[side][:self.count(0x240, side)]):
                if record[0x86] and record[0x78] & 15 < 8:
                    size = struct.unpack_from('<H', record, 0x52)[0]
                    if self.offset + size > len(data):
                        raise ValueError('Truncated unit orders')
                    self.orders[side, index] = data[self.offset:self.offset + size]
                    self.offset += size
        self.trailer = data[self.offset:]

    @property
    def header(self):
        return self.blocks['scenario']

    def count(self, offset, side):
        return short(self.header, offset + 2 * side)

    def _layout(self):
        for name in ('scenario', 'calendar', 'hexmap', 'uhexes', 'zoc', 'hedgelist',
                     'hedges', 'ob0', 'ob1', 'weather', 'supply', 'stock0', 'stock1',
                     'depot0', 'depot1'):
            yield name, 1
        if self.header[0x1223]:
            yield 'garrison', 1
        for name in ('victory', 'vicloc', 'autoart0', 'autoart1', 'autognd0', 'autognd1'):
            yield name, 1
        for side in (0, 1):
            if self.header[0x3a2 + side]:
                yield f'leaders{side}', 1
        yield 'reps0', 1
        yield 'reps1', 1
        yield 'ai_counts', 0
        for name in ('bgstate', 'bgshx', 'bgshy', 'bgdhx', 'bgdhy'):
            yield name, 1
        for side in (0, 1):
            if self.count(0x250, side):
                yield f'riders{side}', 1
        yield 'tanks0', 1
        yield 'tanks1', 1
        yield 'planeclass', 2
        yield 'planecounts', 1
        yield 'shipclass', 2
        yield 'hqlist0', 1
        yield 'hqlist1', 1
        yield 'hqheads', 2
        for name in ('hqs0', 'hqs1', 'arty0', 'arty1'):
            yield name, 1

    def validate(self):
        if len(self.header) != 0x1230 or len(self.blocks['calendar']) != 42:
            raise ValueError('Unsupported scenario layout')
        for side in (0, 1):
            for name, count_offset, stride in (('ob', 0x244, 172), ('hqs', 0x23c, 58),
                                               ('hqlist', 0x23c, 2), ('arty', 0x248, 28),
                                               ('tanks', 0x24c, 10), ('riders', 0x250, 4)):
                if len(self.blocks.get(f'{name}{side}', b'')) != self.count(count_offset, side) * stride:
                    raise ValueError(f'{name} count does not match its block')
            if self.count(0x244, side) != sum(self.count(o, side) for o in (0x240, 0x254, 0x258)):
                raise ValueError('Ground and support counts do not match the roster')
        for name, size in (('planeclass', 32), ('shipclass', 40), ('hqheads', 16)):
            if len(self.blocks[name]) != size:
                raise ValueError(f'Unsupported {name} table')
        if len(self.blocks['victory']) not in (1088, 1648):
            raise ValueError('Unsupported victory history table')

    def to_bytes(self):
        for side in (0, 1):
            self.blocks[f'ob{side}'] = b''.join(self.records[side])
        self.validate()
        result = bytearray()
        for name, multiple in self._layout():
            block = self.blocks[name]
            if multiple:
                result += struct.pack('<I', len(block) // multiple)
            result += block
        for key in sorted(self.orders):
            result += self.orders[key]
        result += self.trailer
        return bytes(result)

    def _increment(self, offset, side):
        value = self.count(offset, side) + 1
        if value > 32767:
            raise ValueError('The game cannot store more units in this table')
        put_short(self.header, offset + side * 2, value)
        return value - 1

    def _auxiliary(self, record):
        cls = record[0x76]
        if cls == 7:
            return 'hqs', 0x23c, 58
        if cls == 1:
            return 'tanks', 0x24c, 10
        if cls in (0, 2) and record[0x79] == 0:
            return 'riders', 0x250, 4
        if cls in (4, 5) or cls == 6 and record[0x77] in (36, 37, 38):
            return 'arty', 0x248, 28
        return None

    def _support_group(self, record, side):
        if record[0x76] == 5:
            category = record[0x77] - 30
            if not 0 <= category < 5:
                raise ValueError('Unknown naval category')
            return 'shipclass', 10, side * 5 + category, 0x254
        if record[0x76] == 6:
            category = {37: 0, 38: 0, 36: 1, 94: 2, 95: 3}.get(record[0x77])
            if category is None:
                raise ValueError('Unknown aircraft category')
            return 'planeclass', 8, side * 4 + category, 0x258
        return None

    def add(self, side, template_index, name, source=None):
        template_roster = source or self
        record = bytearray(template_roster.records[side][template_index])
        if source is not None:
            if record[0x76] not in (5, 6, 7) and not self.count(0x23c, side):
                raise ValueError('Add an HQ for this side before adding its ground units')
            if record[0x76] not in (5, 6):
                record[0x80] = 255 if record[0x76] == 7 else 0
                record[0x81] = record[0x84] = 0
                record[0x78] = 9  # Defend; there is no imported route.
            record[0x85] = record[0x86] = record[0x91] = 0
            for offset in (0x58, 0x5a, 0x5c, 0x5e):
                put_short(record, offset, -1)
            # Imported ground units wait in the OOB until explicitly deployed.
            struct.pack_into('<i', record, 8, -1 if record[0x76] not in (5, 6)
                             else struct.unpack_from('<i', self.header, 0x44)[0] - 1)
            put_short(record, 0x64, 7)
        # Reuse the existing name validator and preserve the DOS encoding.
        unit = decode_record(record)
        unit.update(record_offset=0, current_time=struct.unpack_from('<i', self.blocks['calendar'], 12)[0])
        updated, _ = prepare_unit_changes(unit, {'name': name})
        record = bytearray.fromhex(updated['raw_data'])
        group = self._support_group(record, side)
        if group:
            table, slots, category, count_offset = group
            counts = self.blocks[table]
            from lib.support_units import MAX_CATEGORY_UNITS, check_idle
            if short(counts, 2 * category) >= MAX_CATEGORY_UNITS:
                raise ValueError('The game supports at most 20 roster entries in each aircraft/naval category per side')
            check_idle(self, side)
            if short(counts, 2 * category):
                insert = short(counts, 2 * (slots + category)) + short(counts, 2 * category)
            else:
                # Empty class heads need not point into the support tail.
                insert = self.count(0x240, side)
                if table == 'planeclass':
                    insert += self.count(0x254, side)
                # Native categories are contiguous but not necessarily sorted
                # (CAMPAIGN stores monitors before heavy cruisers).
                insert += self.count(count_offset, side)
                put_short(counts, 2*(slots+category), insert)
        else:
            insert = self.count(0x240, side)
            count_offset = 0x240
        if not 0 <= insert <= len(self.records[side]):
            raise ValueError('Invalid support class range')

        # Reserve separate runtime orders storage for the new ground unit.
        record[:4] = bytes(4)
        if not group:
            order_size = struct.unpack_from('<I', self.header, 0x4c + side * 4)[0]
            slot_size = struct.unpack_from('<H', record, 0x52)[0]
            if order_size + slot_size > 65535:
                raise ValueError('This side has reached the game\'s orders storage limit')
            struct.pack_into('<H', record, 0x50, order_size)
            struct.pack_into('<I', self.header, 0x4c + side * 4, order_size + slot_size)

        auxiliary = self._auxiliary(record)
        if auxiliary:
            kind, offset, stride = auxiliary
            original_index = struct.unpack_from('<i', record, 4)[0]
            source_block = template_roster.blocks.get(f'{kind}{side}', bytearray())
            aux = bytearray(source_block[original_index * stride:(original_index + 1) * stride])
            if len(aux) != stride:
                raise ValueError(f'Template has an invalid {kind} record')
            new_index = self._increment(offset, side)
            struct.pack_into('<i', record, 4, new_index)
            if kind in ('tanks', 'riders'):
                aux[:] = bytes(stride)  # New units have no mounted passengers.
            if kind == 'arty':
                aux[0x15:0x1c] = bytes(7)  # No borrowed bombardment/support assignments.
            if kind == 'hqs':
                if new_index >= 43:
                    raise ValueError('D-Day supports at most 43 HQs per side (RWHQs requires a count below 44)')
                # A new HQ inherits authored stock/limits, not an old HQ's
                # accounting-period receipts, calculated demand or consumption.
                aux[8:16] = bytes(8)
                struct.pack_into('<i', self.header, 0x54+side*0xb4+new_index*4, 0)
                level = short(aux, 0x2e)
                if not 0 <= level < 4:
                    raise ValueError('Invalid HQ level')
                head_offset = (side * 4 + level) * 2
                put_short(aux, 0x28, insert)
                put_short(aux, 0x30, short(self.blocks['hqheads'], head_offset))
                if source is not None:
                    aux[12:40] = bytes(28)
                    put_short(aux, 0x32, -1)
                    record[0x7e] = 255  # Imported HQ has no local garrison.
                    aux[0x38] = aux[0x39] = 0
                put_short(self.blocks['hqheads'], head_offset, new_index)
                self.blocks[f'hqlist{side}'] += struct.pack('<h', insert)
                for table_name in ('autoart', 'autognd'):
                    self.blocks[f'{table_name}{side}'].append(
                        0 if source is not None else self.blocks[f'{table_name}{side}'][original_index])
                if source is not None or record[0x80] == record[0x81]:
                    # TraceOneHQ identifies a root by equal parent/own IDs;
                    # 255 would make it dereference the -1 auxiliary parent.
                    record[0x80] = new_index
                record[0x81] = record[0x84] = new_index
            self.blocks[f'{kind}{side}'] = self.blocks.get(f'{kind}{side}', bytearray()) + aux

        # Existing ground unit numbers never move. Shift only the support tail.
        for old_index, old in enumerate(self.records[side]):
            if old_index >= insert:
                put_short(old, 0x54, old_index + 1)
        for table, slots in (('shipclass', 10), ('planeclass', 8)):
            data = self.blocks[table]
            per_side = slots // 2
            for category in range(side * per_side, (side + 1) * per_side):
                if short(data, category * 2) and short(data, (slots + category) * 2) >= insert:
                    put_short(data, (slots + category) * 2, short(data, (slots + category) * 2) + 1)
        if group:
            table, slots, category, _ = group
            old_count = short(self.blocks[table], category * 2)
            put_short(self.blocks[table], category * 2, old_count + 1)
            if table == 'planeclass':
                from lib.support_units import adjust_availability
                adjust_availability(self, side, category % 4, old_count, old_count + 1)
        self._increment(count_offset, side)
        self._increment(0x244, side)
        put_short(record, 0x54, insert)
        put_short(record, 0x6a, -1)
        record[0x7c] = record[0x85] = record[0x86] = record[0x91] = 0
        record[0x90] = 255  # Leaders remain attached to their original unit.
        if record[0x76] not in (5, 6):
            record[0x78] = 9
            record[0x5c:0x60] = record[0x58:0x5c]
            struct.pack_into('<2h', record, 0x60, -1, -1)
        if record[0x76] != 6:
            struct.pack_into('<i', record, 0x40, 0)  # Aircraft use this for full strength.
        if short(record, 0x64) == 0:
            put_short(record, 0x64, 7)
            struct.pack_into('<i', record, 8, struct.unpack_from('<i', self.header, 0x44)[0] - 1)
            for position in (0x58, 0x5a):
                put_short(record, position, short(record, position + 4))
        self.records[side].insert(insert, record)
        if not group and record[0x76] != 7:
            self._link(side, insert)
            if source is not None:
                parent = short(self.blocks[f'hqlist{side}'], record[0x81] * 2)
                record[0x80] = self.records[side][parent][0x80]
        return insert

    def _link(self, side, index):
        record = self.records[side][index]
        hq = record[0x81]
        if hq >= self.count(0x23c, side):
            raise ValueError('Unit has an invalid parent HQ')
        head = short(self.blocks[f'hqlist{side}'], hq * 2)
        parent = self.records[side][head]
        put_short(record, 0x6a, short(parent, 0x6a))
        put_short(parent, 0x6a, index)

    def remove(self, side, index):
        record = self.records[side][index]
        if record[0x76] == 7:
            from lib.battle_plans import battle_plans
            group = struct.unpack_from('<i',record,4)[0]
            if any(p.get('action')=='release' and p['side']==side and p['group']==group
                   for p in battle_plans(self)):
                raise ValueError('This HQ is used by a reinforcement-release event. Change or remove that event first.')
        # Transport lists hold unit IDs. Dismount all occupants of an affected
        # group before removing a vehicle or passenger.
        from lib.unit_operations import transport_groups, dismount
        for carrier, riders in transport_groups(self, side).items():
            if carrier == index or index in riders:
                for rider_id in riders:
                    dismount(self, side, rider_id)
        if record[0x76] not in (5, 6, 7):
            for other in self.records[side][:self.count(0x240, side)]:
                if short(other, 0x6a) == index:
                    put_short(other, 0x6a, short(record, 0x6a))
            put_short(record, 0x6a, -2)
        # HQs retain their administrative node and subordinate chain. Scripts
        # and supply structures can still resolve it without dangling IDs.
        for position in (0x58, 0x5a):
            put_short(record, position + 4, short(record, position))
            put_short(record, position, -1)
        struct.pack_into('<i', record, 8, -1)
        # UnitsOfTypeEligible only offers destroyed units with a nonzero +0x40
        # timestamp for rebuilding. An editor deletion must stay removed.
        if record[0x76] != 6:
            struct.pack_into('<i', record, 0x40, 0)
        put_short(record, 0x64, 0)
        record[0x85] = record[0x86] = record[0x91] = 0
        if record[0x76] not in (5, 6):
            record[0x78] = 9
            if record[0x76] == 4:
                aux = struct.unpack_from('<i', record, 4)[0]*28
                self.blocks[f'arty{side}'][aux+0x15:aux+0x1c] = bytes(7)
        self.orders.pop((side, index), None)

    def restore(self, side, index):
        record = self.records[side][index]
        for position in (0x58, 0x5a):
            put_short(record, position, short(record, position + 4))
        struct.pack_into('<i', record, 8, struct.unpack_from('<i', self.header, 0x44)[0] - 1)
        put_short(record, 0x64, 7)
        if record[0x76] not in (5, 6, 7):
            self._link(side, index)
