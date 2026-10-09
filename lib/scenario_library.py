"""Portable DOS scenario identity shared by exported SCNs and browser saves."""
import re
import struct

MAGIC = b'WAWLIB01'
FOOTER = struct.Struct('<8s13s27sII8s')
SIZE = FOOTER.size
REQUIRE_ASSETS = 1
REQUIRE_PROFILE = 2
REQUIRE_TERRAIN = 4


def dos_filename(name):
    name = str(name).upper()
    if not re.fullmatch(r'[A-Z0-9_!#$%&\-@^`{}~]{1,8}\.SCN', name):
        raise ValueError('DOS scenario names must use 1–8 letters, digits or DOS filename characters, followed by .SCN')
    return name


def split_library_footer(data):
    if len(data) >= SIZE and data[-8:] == MAGIC and data[-SIZE:-SIZE+8] == MAGIC:
        return data[:-SIZE], data[-SIZE:]
    return data, b''


def library_metadata(data):
    _, footer = split_library_footer(data)
    if not footer:
        return None
    _, filename, title, flags, reserved, _ = FOOTER.unpack(footer)
    if filename[-1] or title[-1]:
        raise ValueError('Unterminated scenario library metadata')
    name = filename.split(b'\0', 1)[0].decode('ascii')
    dos_filename(name)
    if flags not in (0, 1, 3, 7) or reserved:
        raise ValueError('Unsupported scenario library metadata')
    result = dict(filename=name, title=title.split(b'\0', 1)[0].decode('cp437'),
                  require_assets=bool(flags & REQUIRE_ASSETS))
    if flags & REQUIRE_PROFILE:
        result['require_profile'] = True
    if flags & REQUIRE_TERRAIN:
        result['require_terrain'] = True
    return result


def with_library_metadata(data, filename, title, *, require_assets=True, require_profile=False, require_terrain=False):
    if require_terrain and not require_profile:
        raise ValueError("Terrain rules require a game profile")
    if require_profile and not require_assets:
        raise ValueError('Game profiles require companion assets')
    filename = dos_filename(filename)
    title = ''.join(c for c in title if c >= ' ' and c != '\x7f').strip() or filename[:-4]
    encoded = title.encode('cp437', errors='replace')[:26]
    base, _ = split_library_footer(data)
    return base+FOOTER.pack(MAGIC, filename.encode('ascii'), encoded,
                            (REQUIRE_ASSETS if require_assets else 0) | (REQUIRE_PROFILE if require_profile else 0) | (REQUIRE_TERRAIN if require_terrain else 0), 0, MAGIC)


def build_overviews(resources, data, assignments, title):
    """Render authored terrain into the engine's existing preview resources."""
    from PIL import Image, ImageDraw, ImageFont
    from lib.game_art import load_bitmap
    from lib.game_resources import read_resources
    from lib.hex_tile_loader import HexTileLoader
    from lib.scenario_parser import DdayScenario
    from lib.terrain_reader import read_map_layers

    scenario = DdayScenario.from_bytes(data, 'EXPORT.SCN')
    layers = read_map_layers(scenario)
    loader = HexTileLoader()
    loader.artwork = assignments
    raster = loader.compose_map(scenario.map_width, scenario.map_height, layers)
    rgb = Image.new('RGB', raster.size, (0, 0, 0))
    rgb.paste(raster, mask=raster.getchannel('A'))
    palette = load_bitmap(128)
    result = bytearray(resources)
    table = read_resources(resources)
    slot = data[4+0x1220]
    for number in (144, 145+slot, 4500+slot, 4600+slot):
        resource = table['PICT', number]
        _length, top, left, bottom, right, pitch = struct.unpack_from('<HhhhhH', resource.data)
        width, height, stride = right-left, bottom-top, pitch & 0x3fff
        if number >= 4600:
            image = Image.new('RGB', (width, height), (20, 35, 20))
            font = ImageFont.load_default()
            text = title.encode('ascii', 'replace').decode('ascii')[:60]
            bounds = font.getbbox(text)
            text_image = Image.new('RGB', (max(1, bounds[2]+4), max(1, bounds[3]+4)), (20, 35, 20))
            ImageDraw.Draw(text_image).text((2, 0), text, fill=(220, 235, 190), font=font)
            scale = min(2, width/text_image.width, height/text_image.height)
            text_image = text_image.resize((max(1, int(text_image.width*scale)), max(1, int(text_image.height*scale))), Image.Resampling.NEAREST)
            image.paste(text_image, ((width-text_image.width)//2, (height-text_image.height)//2))
        else:
            image = rgb.resize((width, height), Image.Resampling.BOX)
        indexed = image.quantize(palette=palette, dither=Image.Dither.NONE)
        pixels = indexed.tobytes()
        for y in range(height):
            start = resource.offset+12+y*stride
            result[start:start+width] = pixels[y*width:(y+1)*width]
    return bytes(result)
