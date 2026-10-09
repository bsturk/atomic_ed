"""Build separate, reversible LE expansion and scenario-library components."""
import json
from pathlib import Path
import struct
import subprocess
import tempfile

from .ips import write_patch
from .engine import apply_engine_patch
from .music import build_music_patch
from .air_weather import build_air_weather_patch
from .le import grow_code, CODE, EXTENSION
from .paths import ROOT, PATCHES, original_executable

ENTRY_NAMES = ('InitialPreview', 'SelectRow', 'InitSecondary', 'DrawLabel',
               'GetResource', 'LoadIdentity', 'SaveIdentity', 'OpenOrders',
               'Count', 'Selected', 'Page', 'Active', 'Records', 'Identifiers',
               'RefreshRows', 'Scan', 'NativeRead', 'NativeResource', 'NativeSecondary', 'End')


def assemble(expanded, engine, *, presentation=False, custom_artwork=False, advanced_orders=False, support_artwork=False, game_profiles=False, terrain_rules=False, nested_events=False, startup_selection=False):
    """Keep the original library build byte-identical; artwork is another layer."""
    with tempfile.TemporaryDirectory() as folder:
        path = Path(folder)/'library.bin'
        source = original_executable()
        command = ['nasm', '-f', 'bin', '-D', f'SOURCE_EXE="{source}"']
        if presentation:
            command += ['-D', 'PRESENTATION=1']
        if custom_artwork:
            command += ['-D', 'CUSTOM_ARTWORK=1']
        if advanced_orders:
            command += ['-D', 'ADVANCED_ORDERS=1']
        if support_artwork:
            command += ['-D', 'SUPPORT_ARTWORK=1']
        if game_profiles:
            command += ['-D', 'GAME_PROFILES=1']
        if terrain_rules:
            command += ['-D', 'TERRAIN_RULES=1']
        if nested_events:
            command += ['-D', 'NESTED_EVENTS=1']
        if startup_selection:
            command += ['-D', 'STARTUP_SELECTION=1']
        command += [str(PATCHES/'dday-scenario-library.asm'), '-o', str(path)]
        subprocess.run(command, cwd=ROOT, check=True)
        code = path.read_bytes()
    capacity = (13 if nested_events else 8)*4096
    if len(code) > capacity:
        raise ValueError('Scenario library exceeds its reserved pages')
    entries = dict(zip(ENTRY_NAMES, struct.unpack_from('<20I', code)))
    if custom_artwork:
        entries['LeaderPortrait'] = struct.unpack_from('<I', code, 80)[0]
    if advanced_orders:
        entries.update(zip(('AdvancedOrders', 'EventsInitialize', 'EventsRestore', 'EventState', 'EventsConditions'),
                           struct.unpack_from('<5I', code, 84)))
    if support_artwork:
        entries.update(zip(('MoreAirSupport', 'InitialPlaneCategory', 'InitialShipCategory'),
                           struct.unpack_from('<3I', code, 104)))
    if game_profiles:
        entries.update(zip(('ProfileVictory', 'ProfileGround', 'GameRules', 'ReadGameRules'),
                           struct.unpack_from('<4I', code, 116)))
    if terrain_rules:
        entries.update(zip(('TerrainBaseCost', 'TerrainDefense', 'TerrainBarrage', 'TerrainRules', 'ReadTerrainRules', 'CommitTerrainRules'),
                           struct.unpack_from('<6I', code, 132)))
    if nested_events:
        entries.update(zip(('NestedProcess','NestedConditions','NestedReadRow','NestedStart','NestedTurn',
                            'NestedMessage','NestedDrawMessage','MessageCursor'),struct.unpack_from('<8I',code,156)))
    result = bytearray(expanded)
    result[CODE+EXTENSION:CODE+EXTENSION+len(code)] = code
    hooks = []
    def hook(address, target, count=6, call=False):
        before = engine[CODE+address:CODE+address+count]
        if call:
            if count != 5 or before[0] != 0xe8:
                raise ValueError(f'Expected CALL at {address:x}')
        elif before not in (b'\x53\x56\x57\x55\x89\xe5', b'\x53\x56\xc8\x08\x00\x00'):
            raise ValueError(f'Unexpected function prologue at {address:x}')
        payload = bytes([0xe8 if call else 0xe9])+struct.pack('<i', entries[target]-address-5)
        result[CODE+address:CODE+address+count] = payload+b'\x90'*(count-5)
        hooks.append(dict(address=address, target=target, before=before.hex()))
    for address, target in ((0x26f52, 'InitialPreview'), (0x3d421, 'SelectRow'),
                            (0x3ee76, 'InitSecondary'), (0x8486f, 'GetResource')):
        hook(address, target)
    for address, target in ((0x3ed06, 'DrawLabel'), (0x259f8, 'LoadIdentity'),
                            (0x266e5, 'SaveIdentity')):
        hook(address, target, 5, True)
    manifest = json.loads((PATCHES/'dday-weather-400.json').read_bytes())
    start = manifest['entries']['AuthoredAI']
    found = []
    for offset in range(start, 0xb3000-4):
        if engine[CODE+offset] == 0xe8 and offset+5+struct.unpack_from('<i', engine, CODE+offset+1)[0] == 0x8f3bf:
            found.append(offset)
    if len(found) != 1:
        raise ValueError('Cannot locate the authored-order file-open hook')
    hook(found[0], 'OpenOrders', 5, True)
    if custom_artwork:
        hook(0x2ee34, 'LeaderPortrait', 5, True)
    if support_artwork:
        hook(0x514c6, 'MoreAirSupport')
        hook(0x5ce91, 'InitialPlaneCategory', 5, True)
        hook(0x5ceb8, 'InitialShipCategory', 5, True)
    if game_profiles:
        hook(0x52133, 'ProfileVictory')
        hook(0x43a12, 'ProfileGround')
    if terrain_rules:
        hook(0x2ba81, 'TerrainBaseCost')
        for address, target, expected in ((0x14e96, 'TerrainDefense', bytes.fromhex('8b45fc8945d4')),
                                          (0xd69b, 'TerrainBarrage', bytes.fromhex('66837de80d'))):
            before = engine[CODE+address:CODE+address+len(expected)]
            if before != expected:
                raise ValueError(f'Unexpected terrain arithmetic at {address:x}')
            result[CODE+address:CODE+address+len(before)] = b'\xe9'+struct.pack('<i', entries[target]-address-5)+b'\x90'*(len(before)-5)
            hooks.append(dict(address=address, target=target, before=before.hex()))
    if nested_events:
        hook(0x30119,'NestedStart',5,True)
        hook(0x112b2,'NestedTurn',5,True)
        hook(0x1f627,'NestedDrawMessage',5,True)
    if advanced_orders:
        address = 0x67b55
        before = engine[CODE+address:CODE+address+5]
        if before[0] != 0xe9 or address+5+struct.unpack_from('<i', before, 1)[0] != 0xb2e21:
            raise ValueError('Expected version-4 authored-order hook')
        result[CODE+address:CODE+address+5] = b'\xe9'+struct.pack('<i', entries['AdvancedOrders']-address-5)
        hooks.append(dict(address=address, target='AdvancedOrders', before=before.hex()))
    return bytes(result), entries, hooks, len(code)


def build():
    original = original_executable().read_bytes()
    engine = apply_engine_patch(original)
    expanded = grow_code(engine)
    write_patch(PATCHES, 'dday-code-space', engine, expanded, version=1,
                requires='dday-weather-400 version 4', added_code_bytes=32768,
                code_offset=EXTENSION)
    library, entries, hooks, length = assemble(expanded, engine)
    write_patch(PATCHES, 'dday-scenario-library', expanded, library, version=1,
                requires='dday-code-space version 1', entries=entries, hooks=hooks,
                capacity=256, code_length=length)
    result, entries, hooks, length = assemble(expanded, engine, presentation=True)
    write_patch(PATCHES, 'dday-presentation', library, result, version=1,
                requires='dday-scenario-library version 1', entries=entries, hooks=hooks,
                capacity=256, code_length=length,
                picture_resources=[251, 560, 561, 730, 731, 780, 781, 1100, 1101, 1102, 1103])
    custom, entries, hooks, length = assemble(expanded, engine, presentation=True, custom_artwork=True)
    write_patch(PATCHES, 'dday-custom-artwork', result, custom, version=1,
                requires='dday-presentation version 1', entries=entries, hooks=hooks,
                capacity=256, code_length=length, leader_picture_range=[12000, 12255])
    advanced, entries, hooks, length = assemble(expanded, engine, presentation=True, custom_artwork=True, advanced_orders=True)
    write_patch(PATCHES, 'dday-advanced-orders', custom, advanced, version=1,
                requires='dday-custom-artwork version 1', entries=entries, hooks=hooks,
                capacity=256, code_length=length, conditions_per_plan=3, saved_event_bytes=80)
    support, entries, hooks, length = assemble(expanded, engine, presentation=True, custom_artwork=True,
                                               advanced_orders=True, support_artwork=True)
    write_patch(PATCHES, 'dday-support-artwork', advanced, support, version=1,
                requires='dday-advanced-orders version 1', entries=entries, hooks=hooks,
                capacity=256, code_length=length, picture_resources=[131], cached_picture_buffer=13)
    profiles, entries, hooks, length = assemble(expanded, engine, presentation=True, custom_artwork=True,
                                                advanced_orders=True, support_artwork=True, game_profiles=True)
    write_patch(PATCHES, 'dday-game-profiles', support, profiles, version=1,
                requires='dday-support-artwork version 1', entries=entries, hooks=hooks,
                capacity=256, code_length=length, profile_bytes=64)
    terrain, entries, hooks, length = assemble(expanded, engine, presentation=True, custom_artwork=True,
        advanced_orders=True, support_artwork=True, game_profiles=True, terrain_rules=True)
    write_patch(PATCHES, 'dday-terrain-rules', profiles, terrain, version=1,
        requires='dday-game-profiles version 1', entries=entries, hooks=hooks,
        capacity=256, code_length=length, terrain_rule_bytes=844)
    nested, entries, hooks, length = assemble(grow_code(engine,pages=13), engine, presentation=True,
        custom_artwork=True,advanced_orders=True,support_artwork=True,game_profiles=True,
        terrain_rules=True,nested_events=True)
    write_patch(PATCHES,'dday-nested-events',terrain,nested,version=1,requires='dday-terrain-rules version 1',
        entries=entries,hooks=hooks,capacity=256,code_length=length,added_code_bytes=53248,
        event_row_bytes=320,condition_tokens=32)
    startup, entries, hooks, length = assemble(grow_code(engine,pages=13), engine, presentation=True,
        custom_artwork=True,advanced_orders=True,support_artwork=True,game_profiles=True,
        terrain_rules=True,nested_events=True,startup_selection=True)
    write_patch(PATCHES,'dday-startup-selection',nested,startup,version=1,requires='dday-nested-events version 1',
        entries=entries,hooks=hooks,capacity=256,code_length=length,startup_request='WAWSTART.TXT')
    print(f'Built library and independent layers: {length} bytes in 53248 added bytes; {len(hooks)} hooks')
    return build_air_weather_patch(build_music_patch(startup))
