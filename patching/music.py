"""Build the independently reversible FM music layer after startup-selection."""
import json
from pathlib import Path
import struct
import subprocess
import tempfile

from .ips import apply_component, digest, write_patch
from .engine import apply_engine_patch
from .le import CODE
from .paths import PATCHES, original_executable

ORIGIN = 0xbc000
ENTRY_NAMES = ('MusicSync', 'MusicMenu', 'MusicToggle', 'MusicShutdown', 'MusicTick',
               'MusicData', 'MusicCursor', 'MusicEnd', 'MusicWait', 'MusicRunning',
               'MusicEnabled', 'MusicService', 'MusicAttempted', 'MusicMenuHandle', 'End', 'MusicPhase')


def build_music_patch(source):
    previous = json.loads((PATCHES/'dday-startup-selection.json').read_bytes())
    if digest(source) != previous['patched_sha256']:
        raise ValueError('Music requires the verified startup-selection executable')
    if any(source[CODE+ORIGIN:CODE+0xc0000]):
        raise ValueError('Music code space is already occupied')
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp)/'music.bin'
        subprocess.run(['nasm','-f','bin',str(PATCHES/'dday-music.asm'),'-o',str(out)],check=True)
        code = out.read_bytes()
    if len(code) > 0xc0000-ORIGIN:
        raise ValueError('Music exceeds reserved code capacity')
    entries = dict(zip(ENTRY_NAMES, struct.unpack_from('<16I',code)))
    result = bytearray(source)
    result[CODE+ORIGIN:CODE+ORIGIN+len(code)] = code
    hooks = []
    for address, target, call, expected in (
        (0x1462,'MusicSync',False,bytes.fromhex('5356575589e5')),
        (0x41de2,'MusicToggle',False,bytes.fromhex('5356575589e5')),
        (0x4434e,'MusicMenu',True,0x8343d),
        (0x5bd7c,'MusicShutdown',True,0x8165f),
        (0x881fe,'MusicShutdown',True,0x8165f)):
        size = 5 if call else 6
        before = source[CODE+address:CODE+address+size]
        if call:
            if before[0] != 0xe8 or address+5+struct.unpack_from('<i',before,1)[0] != expected:
                raise ValueError(f'Unexpected native call at {address:x}')
        elif before != expected:
            raise ValueError(f'Unexpected native prologue at {address:x}')
        result[CODE+address:CODE+address+size] = bytes([0xe8 if call else 0xe9])+struct.pack('<i',entries[target]-address-5)+b'\x90'*(size-5)
        hooks.append(dict(address=address,target=target,before=before.hex()))
    result = bytes(result)
    write_patch(PATCHES,'dday-music',source,result,version=2,
                requires='dday-startup-selection version 1',entries=entries,hooks=hooks,
                code_length=len(code),code_offset=ORIGIN,
                music_file='DATA/MUSIC/V4V.OPL',settings_file='DATA/MUSIC/MUSIC.CFG',tick_rate=100,native_timer_rate=140,callback_result=0)
    return result


def build():
    data = apply_engine_patch(original_executable().read_bytes())
    for component in ('code-space','scenario-library','presentation','custom-artwork',
                      'advanced-orders','support-artwork','game-profiles','terrain-rules',
                      'nested-events','startup-selection'):
        data = apply_component(data,PATCHES,'dday-'+component)
    result = build_music_patch(data)
    print(f'Built independently reversible music layer: {len(result)}-byte executable')
    return result
