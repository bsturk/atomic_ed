"""Extract the staged games' original terrain sheets as editor data files."""
from pathlib import Path
import hashlib
import json
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lib.game_art import decode_bitmap, TERRAIN_ASSETS
from lib.game_resources import game_resources


def build_library(destination=TERRAIN_ASSETS):
    destination = Path(destination)
    inventory = {'version': 1, 'games': {}}
    for game in ('operation_crusader', 'stalingrad'):
        resources = game_resources(game)
        folder = destination / game
        folder.mkdir(parents=True, exist_ok=True)
        inventory['games'][game] = {}
        for resource_id in (128, 138):
            data = resources['PICT', resource_id].data
            image = decode_bitmap(data, resources['clut', 8].data)
            name = f'PICT_{resource_id}.png'
            image.save(folder / name, transparency=0)
            inventory['games'][game][name] = {
                'resource_sha256': hashlib.sha256(data).hexdigest(),
                'width': image.width, 'height': image.height}
    (destination / 'sources.json').write_text(json.dumps(inventory, indent=2) + '\n')


def build_v4v_library(destination=TERRAIN_ASSETS):
    from PIL import Image
    from lib.game_art import load_bitmap
    from lib.game_resources import GAME_ROOT
    from lib.v4v_reader import VictoryScenario, read_resources, read_bitmap
    from lib.v4v_converter import MASTER_TERRAIN
    from lib.terrain_reader import TERRAIN_TYPES
    palette = load_bitmap(128).getpalette()
    white = min(range(1,256), key=lambda i:sum((255-v)**2 for v in palette[i*3:i*3+3]))
    seen = set()
    for path in sorted((GAME_ROOT.parent/'v4v').rglob('*.SCN')):
        source = VictoryScenario.read(path)
        game = 'v4v_'+source.resource_name.lower()
        if game in seen: continue
        seen.add(game)
        resources = read_resources(path.parent/(source.resource_name+'.RES'))
        original = read_bitmap(resources['PICT',128],palette)
        rows = [(i,MASTER_TERRAIN[t]) for i,t in enumerate(source.battleset[0x1e:0x2e])
                if t < len(MASTER_TERRAIN) and MASTER_TERRAIN[t] < 14 and 33+i*33 <= original.width]
        folder = Path(destination)/game
        folder.mkdir(parents=True,exist_ok=True)
        for small in (False,True):
            width,height,dx,dy,resource = (16,19,18,21,138) if small else (32,36,34,38,128)
            image=Image.new('P',(dx*3,dy*16));image.putpalette(palette)
            mask=load_bitmap(resource).crop((0,dy,width,dy+height)).tobytes()
            for row,code in rows:
                for col,oldrow in enumerate((0,1,1)):
                    tile=original.crop((1+row*33,1+oldrow*37,33+row*33,37+oldrow*37)).resize((width,height),Image.Resampling.NEAREST)
                    pixels=bytes((v or white) if m else 0 for v,m in zip(tile.tobytes(),mask))
                    tile=Image.frombytes('P',(width,height),pixels);tile.putpalette(palette)
                    image.paste(tile,(col*dx,row*dy))
            image.save(folder/f'PICT_{resource}.png',transparency=0)
        (folder/'catalog.json').write_text(json.dumps([dict(row=i,code=c,name=TERRAIN_TYPES[c]) for i,c in rows],indent=2)+'\n')


if __name__ == '__main__':
    build_library()
    build_v4v_library()
    print(f'Terrain library written to {TERRAIN_ASSETS}')
