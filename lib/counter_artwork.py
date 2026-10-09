"""Portable imported unit sheets, kept in scenario assets through Save As."""
import base64
import json
import struct

from lib.game_art import decode_bitmap
from lib.game_resources import game_resources, read_resources
from lib.scenario_files import scenario_asset_path


def counter_path(path):
    return scenario_asset_path(path, '.counters.json')


def validate_counters(sheets):
    original = game_resources('dday')
    for number, data in sheets.items():
        if number not in (304, 305):
            raise ValueError('Unsupported imported unit sheet')
        native = original['PICT', number].data
        if len(data) != len(native) or data[:12] != native[:12]:
            raise ValueError('Imported unit sheet must retain the D-Day dimensions')
        decode_bitmap(data, original['clut', 8].data)
    return sheets


def encode_counters(sheets):
    validate_counters(sheets)
    return (json.dumps({'version': 1, 'runtime': 'dday', 'sheets': {
        str(k): base64.b64encode(v).decode('ascii') for k, v in sorted(sheets.items())}}, indent=2) + '\n').encode()


def load_counters(path):
    path = counter_path(path)
    if not path.exists():
        return {}
    data = path.read_bytes()
    if len(data) > 1024 * 1024:
        raise ValueError('Unit artwork file is too large')
    try:
        payload = json.loads(data)
        if payload['version'] != 1 or payload['runtime'] != 'dday':
            raise ValueError('Unsupported unit artwork file')
        return validate_counters({int(k): base64.b64decode(v, validate=True)
                                  for k, v in payload['sheets'].items()})
    except (KeyError, TypeError, AttributeError) as exc:
        raise ValueError('Invalid unit artwork file') from exc


def patch_counters(resources, sheets):
    validate_counters(sheets)
    directory = read_resources(resources)
    result = bytearray(resources)
    for number, data in sheets.items():
        record = directory['PICT', number]
        if len(data) != len(record.data):
            raise ValueError('Unit sheet size differs from destination')
        result[record.offset:record.offset + len(data)] = data
    return bytes(result)


def allocate_counter(roster, sheets, side, pixels):
    """Reuse identical art or replace an unused slot, preserving every OOB chit."""
    if len(pixels) != 22*23 or side not in (0, 1):
        raise ValueError('Invalid unit chit')
    number = struct.unpack_from('<h', roster.header, 0x238)[0] + side
    if number not in (304, 305):
        raise ValueError('Unsupported destination counter bank')
    data = bytearray(sheets.get(number, game_resources()['PICT', number].data))
    stride = int.from_bytes(data[10:12], 'little') & 0x3fff
    count = struct.unpack_from('<h', data, 6)[0]//23*22
    used = {struct.unpack_from('<h', r, 0x56)[0] for r in roster.records[side] if r[0x76] not in (5, 6)}
    leaders = roster.blocks.get(f'leaders{side}', b'')
    used.update(struct.unpack_from('<h', leaders, p+8)[0] for p in range(0, len(leaders), 36))
    def tile(index):
        x, y = index%22*22, index//22*23
        return b''.join(data[12+(y+i)*stride+x:12+(y+i)*stride+x+22] for i in range(23))
    for index in range(count):
        if tile(index) == pixels:
            return index, dict(sheets)
    index = next((i for i in range(count) if i not in used), None)
    if index is None:
        raise ValueError('Every chit slot for this side is in use')
    x, y = index%22*22, index//22*23
    for row in range(23):
        offset = 12+(y+row)*stride+x
        data[offset:offset+22] = pixels[row*22:(row+1)*22]
    updated = dict(sheets)
    updated[number] = bytes(data)
    return index, updated
