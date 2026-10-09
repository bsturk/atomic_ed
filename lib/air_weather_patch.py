"""Repair the four previous-turn weather reads missed by the 400-turn patch."""
import json
import struct

from lib.binary_patch import digest, write_patch
from lib.dday_patch import PATCHES
from lib.le_executable import CODE

# Native RepairFromMoveOut advances Calendar before resolving these missions.
# Each instruction intentionally reads clouds[current - start - 1]. Growing
# temperatures[260] to [400] moved clouds from +214h to +32ch, so the biased
# displacement must move from +213h to +32bh as well.
READS = (
    (0x220b, b'\x8a\x80', 'PerformAirReconMissions storm gate'),
    (0x2247, b'\x8a\x80', 'PerformAirReconMissions visibility penalty'),
    (0x78629, b'\x8a\x88', 'PerformSupplyDrop delivery penalty'),
    (0x78730, b'\x8a\x80', 'PerformAirResupplyMissions storm gate'),
)


def build_air_weather_patch(source):
    previous = json.loads((PATCHES/'dday-music.json').read_bytes())
    if digest(source) != previous['patched_sha256']:
        raise ValueError('Air weather repair requires the verified music executable')
    result, edits = bytearray(source), []
    for address, opcode, reason in READS:
        before = opcode + struct.pack('<I', 0x213)
        after = opcode + struct.pack('<I', 0x32b)
        offset = CODE + address
        if source[offset:offset+len(before)] != before:
            raise ValueError(f'Unexpected native weather read at {address:x}')
        result[offset:offset+len(after)] = after
        edits.append(dict(address=address, offset=offset,
                          before=before.hex(), after=after.hex(), reason=reason))
    result = bytes(result)
    write_patch(PATCHES, 'dday-air-weather', source, result, version=1,
                requires='dday-music version 2', edits=edits,
                cloud_offset=0x32c, previous_turn_displacement=0x32b)
    return result
