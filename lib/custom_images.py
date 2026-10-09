"""Convert imported pictures to the engine's palette and sprite footprints."""
from pathlib import Path

from PIL import Image, ImageEnhance

from lib.game_art import load_bitmap
from lib.presentation_artwork import fit_pixels, indexed_image
from lib.terrain_artwork import TerrainStamp


def read_image(filename):
    with Image.open(filename) as image:
        if image.width * image.height > 16_000_000:
            raise ValueError('Choose an image with at most 16 million pixels')
        image.load()
        return image.copy()


def terrain_from_image(image, name):
    """Solid native hexes at both scales, plus generated dim/night versions."""
    pixels = []
    for brightness in (1, .65, .35):
        source = image if brightness == 1 else ImageEnhance.Brightness(image.convert('RGBA')).enhance(brightness)
        for small in (False, True):
            width, height, dy = (16, 19, 21) if small else (32, 36, 38)
            mask = load_bitmap(138 if small else 128).crop((0, dy, width, dy+height)).tobytes()
            # Terrain is solid inside its hex. Transparent padding becomes the
            # source's opaque background (white), never holes in the map.
            fitted = fit_pixels(source, (width, height), matte=(round(255*brightness),)*3)
            palette = load_bitmap(128).getpalette()
            white = min(range(1, 256), key=lambda i: sum((255-c)**2 for c in palette[i*3:i*3+3]))
            pixels.append(bytes((value or white) if opaque else 0 for value, opaque in zip(fitted, mask)))
    return TerrainStamp(name[:200], *pixels)


def import_terrain(filename):
    return terrain_from_image(read_image(filename), Path(filename).name)


def counter_from_image(image):
    return fit_pixels(image, (22, 23))


def import_counter(filename):
    return counter_from_image(read_image(filename))


def counter_image(pixels):
    return indexed_image(pixels, (22, 23)).convert('RGBA')
