"""Native aircraft/ship categories, availability and safe roster regrouping.

SetupCurrentPlaneClass/SetupCurrentShipClass consume contiguous category ranges.
AirAvail is a 2 x 4 x 5 table of available squadrons, not a cached roster count.
"""
import struct

AIR_TYPES = {37: 0, 38: 0, 36: 1, 94: 2, 95: 3}
AIR_NAMES = ('Fighter / light bomber', 'Medium bomber', 'Transport', 'Reconnaissance')
SHIP_NAMES = ('Battleship', 'Heavy cruiser', 'Monitor', 'Light cruiser', 'Destroyer')
MAX_CATEGORY_UNITS = 20  # sScreenUnitID / ScreenUnitID are int16[20].


def category(unit_class, descriptor):
    if unit_class == 5 and 30 <= descriptor <= 34:
        return descriptor - 30
    if unit_class == 6 and descriptor in AIR_TYPES:
        return AIR_TYPES[descriptor]
    raise ValueError('Choose a supported aircraft or naval category')


def artwork_key(unit_class, descriptor, side):
    group = category(unit_class, descriptor)
    return f'ship_{group}' if unit_class == 5 else f'air_{side}_{group}'


def adjust_availability(roster, side, group, old_count, new_count):
    """New squadrons are available at all five levels; retain other reserves.

    Removal reduces available counts first. Clamp only the affected category:
    some shipped scenarios contain unused out-of-range values at other levels.
    """
    if old_count == new_count:
        return
    block = roster.blocks['planecounts']
    if len(block) != 80:
        raise ValueError('Unsupported aircraft availability table')
    for level in range(5):
        offset = ((side * 4 + group) * 5 + level) * 2
        old = struct.unpack_from('<h', block, offset)[0]
        value = min(new_count, max(0, old + new_count - old_count))
        struct.pack_into('<h', block, offset, value)


def check_idle(roster, side):
    for record in roster.records[side][roster.count(0x240, side):]:
        if record[0x86] or record[0x7c] or record[0x90] != 255:
            raise ValueError('Finish or clear this side’s support missions before changing its roster categories')


def regroup(roster, side, selected):
    """Rebuild only the support tail; ground IDs and their orders stay fixed."""
    start = roster.count(0x240, side)
    tail = roster.records[side][start:]
    tail.sort(key=lambda r: (r[0x76], category(r[0x76], r[0x77])))
    roster.records[side][start:] = tail
    for index, record in enumerate(tail, start):
        struct.pack_into('<h', record, 0x54, index)
        struct.pack_into('<h', record, 0x70, -1)  # Rebuilt by the support panel.
    for cls, name, groups in ((5, 'shipclass', 5), (6, 'planeclass', 4)):
        block = roster.blocks[name]
        for group in range(groups):
            slot = side * groups + group
            old_count = struct.unpack_from('<h', block, slot * 2)[0]
            members = [i for i, r in enumerate(roster.records[side])
                       if r[0x76] == cls and category(cls, r[0x77]) == group]
            count = len(members)
            struct.pack_into('<h', block, slot * 2, count)
            struct.pack_into('<h', block, (groups * 2 + slot) * 2, members[0] if members else -1)
            if cls == 6:
                adjust_availability(roster, side, group, old_count, count)
    return next(i for i, record in enumerate(roster.records[side]) if record is selected)


def change_profile(roster, side, record, descriptor):
    """Adopt a native role profile without replacing identity or aircraft counts.

    Combat-to-combat edits retain authored bombardment ratings. A former
    transport/recon receives native bombardment ratings scaled to its strength.
    Old auxiliary slots stay reserved so unrelated references remain stable.
    """
    from lib.unit_library import unit_library
    new_category = category(record[0x76], descriptor)
    if new_category != category(record[0x76], record[0x77]):
        count = sum(r[0x76] == record[0x76] and category(r[0x76], r[0x77]) == new_category
                    for r in roster.records[side] if r[0x76] in (5, 6))
        if count >= MAX_CATEGORY_UNITS:
            raise ValueError('The game supports at most 20 roster entries in each aircraft/naval category per side')
    check_idle(roster, side)
    old_aux = roster._auxiliary(record)
    templates = [item for item in unit_library() if item['game'] == 'dday'
                 and item['record'][0x76] == record[0x76]
                 and item['record'][0x77] == descriptor]
    if not templates:
        raise ValueError('The unit library is missing the native profile for this category')
    template = next((item for item in templates if item['side'] == side), templates[0])
    source = template['record']
    record[0x77] = descriptor
    if record[0x76] == 6:
        for offset, size in ((0x10, 4), (0x14, 4), (0x20, 4), (0x78, 2), (0x7d, 1), (0x8e, 1)):
            record[offset:offset+size] = source[offset:offset+size]
        record[0x7b] = (1, 1, 2, 3)[AIR_TYPES[descriptor]]
    else:
        record[0x7d] = source[0x7d]
        record[0x7b] = 1
    for offset in (0x5c, 0x5e, 0x60, 0x62):
        struct.pack_into('<h', record, offset, -1)
    record[0x85] = record[0x86] = record[0x7c] = 0
    new_aux = roster._auxiliary(record)
    if new_aux and not old_aux:
        aux = bytearray(template['aux'])
        if len(aux) != 28:
            raise ValueError('Invalid native bombardment profile')
        for offset in (0, 4, 8, 12):
            strength = struct.unpack_from('<i', aux, offset)[0]
            struct.pack_into('<i', aux, offset, strength * record[0x80] // max(1, source[0x80]))
        aux[0x15:] = bytes(7)
        index = roster._increment(0x248, side)
        roster.blocks[f'arty{side}'] += aux
        struct.pack_into('<i', record, 4, index)
    elif not new_aux:
        record[4:8] = bytes(4)
