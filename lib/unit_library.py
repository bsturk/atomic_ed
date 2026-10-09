"""Portable D-Day unit templates and their indexed counter pixels.

Earlier WaW games contribute translated OB, artillery and HQ definitions and
original chits. V4V auxiliary records still use matching D-Day templates.
"""
import base64
from functools import lru_cache
import json
from pathlib import Path
from types import SimpleNamespace
import zipfile

from lib.unit_reader import decode_record

LIBRARY = Path(__file__).resolve().parents[1] / 'assets/units/library.zip'


@lru_cache(maxsize=1)
def unit_library():
    if not LIBRARY.exists():
        return []
    with zipfile.ZipFile(LIBRARY) as archive:
        entries = json.loads(archive.read('units.json'))
    for i, item in enumerate(entries):
        for key in ('record', 'aux', 'chit'):
            item[key] = base64.b64decode(item[key], validate=True)
        if len(item['record']) != 172 or len(item['chit']) not in (0, 506):
            raise ValueError('Invalid unit library entry')
        item['library_id'] = i
    return entries


def library_template(item, side):
    """Minimal source accepted by UnitRoster.add; never carries foreign links."""
    import struct
    from lib.unit_roster import UnitRoster
    record = bytearray(item['record'])
    record[0x74] = side
    struct.pack_into('<i', record, 4, 0)
    rows = [[], []]
    rows[side] = [record]
    blocks = {}
    auxiliary = UnitRoster._auxiliary(None, record)
    if auxiliary:
        kind, _, stride = auxiliary
        if len(item['aux']) != stride:
            raise ValueError(f'Invalid library {kind} record')
        blocks[f'{kind}{side}'] = item['aux']
    return SimpleNamespace(records=rows, blocks=blocks)


def template_choices(source, side):
    return [dict(decode_record(item['record']), library_id=item['library_id'],
                 side=('Allied','Axis')[side], side_index=0, index=0,
                 provenance=item['scenario'])
            for item in unit_library() if item['game'] == source and item['side'] == side]
