"""Extract installed WaW/V4V units into a portable editor library."""
from pathlib import Path
import base64
import json
import struct
import sys
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lib.game_resources import GAME_ROOT, game_resources
from lib.game_art import decode_bitmap, load_bitmap
from lib.unit_roster import UnitRoster, short
from lib.unit_library import LIBRARY
from lib.v4v_converter import convert_scenario
from lib.v4v_reader import VictoryScenario


def old_roster(path, game):
    """Use the full translator, including source artillery and HQ definitions."""
    from lib.scenario_import import source_game
    from lib.waw_converter import convert_scenario as convert_waw
    if source_game(path) != game:
        raise ValueError(f'Wrong source game: {path}')
    data, _, counters, _ = convert_waw(path)
    yield from native_entries(UnitRoster(data), counters)


def counter_pixels(sheet, index):
    x,y = index%22*22,index//22*23
    if index < 0 or x+22>sheet.width or y+23>sheet.height: raise ValueError(f'Invalid counter {index}')
    return sheet.crop((x,y,x+22,y+23)).tobytes()


def native_entries(roster, counters=None):
    for side, records in enumerate(roster.records):
        number = short(roster.header,0x238)+side
        sheet = decode_bitmap(counters[number],game_resources()['clut',8].data) if counters else load_bitmap(number)
        for record in records:
            aux = b''
            auxiliary = roster._auxiliary(record)
            if auxiliary:
                kind,_,stride = auxiliary
                i = struct.unpack_from('<i',record,4)[0]
                aux = bytes(roster.blocks[f'{kind}{side}'][i*stride:(i+1)*stride])
            yield side,bytes(record),aux,(counter_pixels(sheet,short(record,0x56)) if record[0x76] not in (5,6) else b'')


def build():
    result, seen = [], set()
    def add(game, scenario, rows):
        count=0
        for side,record,aux,chit in rows:
            # Dedupe identical authored templates, retaining different stats,
            # counters and source scenarios when any substantive field differs.
            key=(game,scenario,side,record[0x92:],record[0x14:0x38],record[0x75:0x7c],record[0x89:0x8e],aux,chit)
            if key in seen: continue
            seen.add(key)
            result.append(dict(game=game,scenario=scenario,side=side,
                **{k:base64.b64encode(v).decode() for k,v in dict(record=record,aux=aux,chit=chit).items()}))
            count+=1
        print(game,scenario,count)
    for game in ('dday','stalingrad','operation_crusader'):
        for path in sorted((GAME_ROOT/game/'SCENARIO').glob('*.SCN')):
            rows = native_entries(UnitRoster(path.read_bytes())) if game=='dday' else old_roster(path,game)
            add(game,path.stem,rows)
    for path in sorted((GAME_ROOT.parent/'v4v').rglob('*.SCN')):
        source=VictoryScenario.read(path)
        data,_,counters,_=convert_scenario(path)
        add('v4v_'+source.resource_name.lower(),source.title,native_entries(UnitRoster(data),counters))
    LIBRARY.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(LIBRARY,'w',zipfile.ZIP_DEFLATED) as z:
        z.writestr('units.json',json.dumps(result,separators=(',',':')))
    print(f'{len(result)} templates in {LIBRARY}')

if __name__=='__main__': build()
