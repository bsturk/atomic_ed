"""Build weather/victory/AI extensions and their reversible, checked IPS patch."""
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import tempfile

from .le import CODE, LE
from .paths import PATCHES, original_executable

CAVE = 0xb2ba0
# Operand locations, checked against references to the Weather pointer. These
# are not a global byte replacement: unrelated branch deltas/data are excluded.
CLOUD_REFS = (
    0xeec6, 0x100b8, 0x18da7, 0x18f3a, 0x1bb25, 0x22e57, 0x2d7e5,
    0x2d856, 0x2d9dd, 0x2da1f, 0x37c97, 0x37d3d, 0x410f3, 0x413b0,
    0x43bd9, 0x43d0c, 0x43d12, 0x43ee7, 0x43f2d, 0x4575f, 0x46958,
    0x469bc, 0x513f0, 0x5149c, 0x514b8, 0x552f6, 0x5d98a, 0x5d9ba,
    0x5de6e, 0x66441, 0x664d5, 0x6665a, 0x66fb8, 0x66ff9, 0x67053, 0x670cb,
)
GROUND_REFS = (0x1916b, 0x1918c, 0x191c0, 0x2a417, 0x2a41d, 0x2ba94, 0x45773, 0x45781)
ICE_REFS = (0x19291, 0x2a42e, 0x2a434)
# Verified references to the Victory pointer (object 3 +7d57). Grow each
# side's 24-byte totals + 260 int16 history entries to 400 history entries.
VICTORY_STRIDE_REFS = (
    0x2cc6f, 0x2cc99, 0x2fc7e, 0x2fc9c, 0x2fcd1, 0x2fcff, 0x2fd44,
    0x2fd5f, 0x2fd8b, 0x4cf04, 0x4cf30, 0x5214e, 0x5218e, 0x521ab,
    0x521f3, 0x52207, 0x52b5d, 0x52b97, 0x52bdf, 0x52c01, 0x52c24,
    0x52c47, 0x52c74, 0x52dd3, 0x52df2, 0x52e0c, 0x52e24, 0x52e47,
    0x52f91, 0x52faa, 0x53017, 0x533e6, 0x53403, 0x5349f, 0x5bb2b,
)


def ips(edits, reverse=False):
    result = bytearray(b'PATCH')
    for edit in edits:
        value = bytes.fromhex(edit['before' if reverse else 'after'])
        result += edit['offset'].to_bytes(3, 'big') + len(value).to_bytes(2, 'big') + value
    return bytes(result) + b'EOF'


def build():
    original = original_executable().read_bytes()
    if hashlib.sha256(original).hexdigest() != 'd28ef2b0e8eea2f5b6bb7eb1e002d3621c770f7d94e9add7480caf14ca8df2ba':
        raise ValueError('Patch builder requires the verified, unmodified D-Day executable')
    if original[LE:LE + 2] != b'LE':
        raise ValueError('Unexpected executable layout')
    if (struct.unpack_from('<I', original, CODE+0x2f889)[0]+4 !=
            struct.unpack_from('<I', original, CODE+0x2f893)[0]):
        raise ValueError('Weather date globals are not adjacent')
    with tempfile.TemporaryDirectory() as tmp:
        output = Path(tmp) / 'cave.bin'
        subprocess.run(['nasm', '-f', 'bin', str(PATCHES / 'dday-weather-400.asm'),
                        '-o', str(output)], check=True)
        cave = output.read_bytes()
        subprocess.run(['nasm', '-f', 'bin', str(PATCHES / 'dday-victory-400.asm'),
                        '-o', str(output)], check=True)
        victory = output.read_bytes()
    if len(victory) != 0x27929-0x27770:
        raise ValueError('Victory reader exceeds its original function space')
    for operand in (0x27856, 0x27867, 0x2787e, 0x278a4, 0x278d1):
        if victory[operand-0x27770:operand-0x27770+4] != original[CODE+operand:CODE+operand+4]:
            raise ValueError('Victory replacement moved an LE relocation operand')
    if len(cave) > 1120 or any(original[CODE + CAVE:CODE + CAVE + 1120]):
        raise ValueError('Code cave does not fit unused final-page padding')
    edits = []
    result = bytearray(original)
    def edit(offset, before, after, reason):
        if len(before) != len(after) or result[offset:offset + len(before)] != before:
            raise ValueError(f'Patch precondition failed at {offset:x}: {reason}')
        edits.append(dict(offset=offset, before=before.hex(), after=after.hex(), reason=reason))
        result[offset:offset + len(after)] = after
    def integer(offset, before, after, reason):
        edit(offset, struct.pack('<I', before), struct.pack('<I', after), reason)
    integer(LE + 0xc4, CAVE, CAVE + len(cave), 'Extend code object within its existing final page')
    for old, new, refs in ((0x214, 0x32c, CLOUD_REFS), (0x318, 0x4bc, GROUND_REFS),
                           (0x319, 0x4bd, ICE_REFS)):
        for ref in refs:
            integer(CODE + ref, old, new, f'Weather field +{old:x} -> +{new:x}')
    targets = struct.unpack_from('<5I', cave)
    for address, target, name in zip((0x27e1a, 0x2f834, 0x2a35d, 0x27dac), targets,
                                      ('RWWeather', 'SetCalUTs', 'ValidateWeather', 'SwapWeather')):
        edit(CODE + address, bytes.fromhex('5356575589'),
             b'\xe9' + struct.pack('<i', target - address - 5), f'Hook {name}')
    address = 0x67b55
    edit(CODE + address, bytes.fromhex('89ec5d5f5e'),
         b'\xe9' + struct.pack('<i', targets[4]-address-5), 'Apply authored HQ battle plans when returning unit orders')
    edit(CODE + CAVE, bytes(len(cave)), cave, 'Position-independent weather and conditional HQ orders')
    edit(CODE+0x27770, original[CODE+0x27770:CODE+0x27929], victory,
         'Read native/extended victory history and save 400 entries per side')
    for old, new, refs in ((0x220, 0x338, VICTORY_STRIDE_REFS),
                           (0x238, 0x350, (0x53051, 0x53058, 0x5347e)),
                           (0x208, 0x320, (0x5345a, 0x53472))):
        for ref in refs:
            integer(CODE+ref, old, new, f'Victory field/size +{old:x} -> +{new:x}')
    edits.sort(key=lambda e: e['offset'])
    encoded, undo = ips(edits), ips(edits, reverse=True)
    destination = PATCHES
    (destination / 'dday-weather-400.ips').write_bytes(encoded)
    (destination / 'dday-weather-400.undo.ips').write_bytes(undo)
    manifest = dict(name='dday-weather-400', version=4,
                    source_sha256=hashlib.sha256(original).hexdigest(),
                    patched_sha256=hashlib.sha256(result).hexdigest(),
                    title_table_offset=0x10eddd,
                    title_table=original[0x10eddd:0x10eddd + 7 * 26].hex(),
                    ips_sha256=hashlib.sha256(encoded).hexdigest(),
                    undo_sha256=hashlib.sha256(undo).hexdigest(),
                    cave_code_offset=CAVE, cave_length=len(cave),
                    entries=dict(zip(('RWWeather', 'SetCalUTs', 'ValidateWeather', 'SwapWeather', 'AuthoredAI'), targets)),
                    weather_size=1222, capacity=400, victory_size=1648,
                    victory_capacity=400, edits=edits)
    (destination / 'dday-weather-400.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print(f'Built {len(encoded)}-byte IPS patch; {len(cave)}-byte cave; {len(edits)} edits')
