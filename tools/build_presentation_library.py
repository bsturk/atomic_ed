#!/usr/bin/env python3
"""Extract popup portraits, flags and emblems from the user's staged WaW games."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lib.game_art import decode_bitmap
from lib.game_resources import available_games, game_resources
from lib.presentation_artwork import LIBRARY


def build_library(destination=LIBRARY):
    for game in available_games():
        folder = Path(destination)/game
        folder.mkdir(parents=True, exist_ok=True)
        resources = game_resources(game)
        for number in (131, 560, 561, 730, 731, 780, 781, 1100, 1101, 1102, 1103):
            image = decode_bitmap(resources['PICT', number].data, resources['clut', 8].data)
            image.save(folder/f'PICT_{number}.png', transparency=0)


if __name__ == '__main__':
    build_library()
    print(f'Presentation artwork written to {LIBRARY}')
