"""Checked page growth for the staged D-Day DOS/4G LE executable.

Keep object numbers and in-object offsets stable. Existing code fixups remain
byte-identical; the new code uses relative calls and relocated operand cells.
"""
import struct

LE = 0x290a4
STUB = 0x26654
CODE = 0x53654
EXTENSION = 0xb3000


def u32(data, pos):
    return struct.unpack_from('<I', data, pos)[0]


def grow_code(data, pages=8):
    if data[LE:LE+4] != b'LE\0\0' or not 1 <= pages <= 13:
        raise ValueError('Unsupported LE image or extension size')
    page_size = u32(data, LE+0x28)
    count = u32(data, LE+0x14)
    objects = u32(data, LE+0x40)
    page_map = u32(data, LE+0x48)
    fix_pages = u32(data, LE+0x68)
    fix_records = u32(data, LE+0x6c)
    table_end = u32(data, LE+0x78)
    if (page_size, count, objects, page_map, fix_pages, fix_records, table_end) != (
            4096, 196, 0xc4, 0x10c, 0x429, 0x73d, 0x2a468):
        raise ValueError('Unsupported D-Day page table layout')
    obj = [list(struct.unpack_from('<6I', data, LE+objects+24*i)) for i in range(3)]
    if obj[0] != [EXTENSION, 0x10000, 0x2045, 1, 179, 0]:
        raise ValueError('Apply the version-4 engine patch before extending code')
    if obj[0][1]+EXTENSION+pages*page_size > obj[1][1]:
        raise ValueError('Code extension overlaps the next declared object')
    original_map = data[LE+page_map:LE+page_map+count*4]
    if any(original_map[i*4:i*4+4] != (i+1).to_bytes(3, 'big')+b'\0' for i in range(count)):
        raise ValueError('Expected contiguous, uncompressed LE pages')
    boundaries = list(struct.unpack_from(f'<{count+1}I', data, LE+fix_pages))
    if boundaries != sorted(boundaries) or boundaries[-1] != table_end-fix_records:
        raise ValueError('Invalid fixup-page table')
    new_count = count+pages
    new_map = b''.join(i.to_bytes(3, 'big')+b'\0' for i in range(1, new_count+1))
    new_boundaries = boundaries[:180]+[boundaries[179]]*pages+boundaries[180:]
    header = bytearray(data[LE:LE+page_map])
    header += new_map
    header += data[LE+page_map+count*4:LE+fix_pages]
    header += struct.pack(f'<{new_count+1}I', *new_boundaries)
    header += data[LE+fix_records:LE+table_end]
    if LE+len(header) > CODE:
        raise ValueError('Extended LE tables exceed existing header padding')
    # All following table offsets are LE-relative; the data-page offset is
    # relative to the embedded MZ stub and remains unchanged.
    for field in (0x4c, 0x50, 0x58, 0x5c, 0x68, 0x6c, 0x70, 0x78):
        old = u32(data, LE+field)
        shift = (pages*4 if old >= page_map+count*4 else 0)
        shift += pages*4 if old >= fix_records else 0
        struct.pack_into('<I', header, field, old+shift if old else 0)
    for field, increment in ((0x14, pages), (0x30, pages*4), (0x38, pages*4)):
        struct.pack_into('<I', header, field, u32(data, LE+field)+increment)
    obj[0][0] += pages*page_size
    obj[0][2] |= 2  # extension includes its own writable state, no new fixups
    obj[0][4] += pages
    for item in obj[1:]:
        item[3] += pages
    for i, item in enumerate(obj):
        struct.pack_into('<6I', header, objects+i*24, *item)
    result = bytearray(data)
    result[LE:CODE] = header+bytes(CODE-LE-len(header))
    result[CODE+EXTENSION:CODE+EXTENSION] = bytes(pages*page_size)
    return bytes(result)
