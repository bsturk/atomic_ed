"""Detect supported source formats and dispatch their explicit translations."""
from pathlib import Path

from lib.waw_reader import LAYOUTS


def source_game(path):
    with Path(path).open('rb') as stream:
        prefix = stream.read(4)
    size = int.from_bytes(prefix, 'little')
    if size in LAYOUTS:
        return LAYOUTS[size]
    if size == 0xc0c:
        return 'v4v'
    if size == 0x1230:
        return 'dday'
    raise ValueError('Unsupported scenario format')


def convert_scenario(path):
    game = source_game(path)
    if game in LAYOUTS.values():
        from lib.waw_converter import convert_scenario as convert
    elif game == 'v4v':
        from lib.v4v_converter import convert_scenario as convert
    else:
        raise ValueError('This scenario is already in D-Day format; open it directly')
    data, terrain, counters, report = convert(path)
    from lib.game_profiles import ScenarioDocument, ground_step
    document = ScenarioDocument.import_source(path)
    if game == 'v4v':
        from lib.v4v_reader import VictoryScenario
        from lib.unit_roster import UnitRoster
        import struct
        source = VictoryScenario.read(path)
        weather = source.historical_weather
        ground = tuple(round(weather['ground_seed_at_table_origin'][key]*1000) for key in ('snow', 'ice', 'wetness'))
        for turn in range(weather['first_index']):
            temperature = struct.unpack_from('<h', source.blocks[7], 0x414+turn*2)[0]
            code = source.blocks[7][0xb8+turn]
            if code > 4:
                raise ValueError('Invalid historical weather before scenario start')
            ground = ground_step(document.profile, code, temperature, *ground)
        roster = UnitRoster(data)
        struct.pack_into('<3i', roster.blocks['weather'], 0, *ground)
        data = roster.to_bytes()
        report['initial_ground_profile'] = dict(zip(('snow', 'ice', 'wetness'), ground))
        report['limitations'] = [line for line in report.get('limitations', []) if 'ground' not in line.lower() and 'snow' not in line.lower()]
    report['document'] = document.to_dict()
    report.setdefault('adaptations', report.get('limitations', []))
    report['adaptations'] = [line.replace('supply, weather and victory rules', 'supply and victory rules')
                             for line in report['adaptations']] + document.profile.adaptations
    return data, terrain, counters, report
