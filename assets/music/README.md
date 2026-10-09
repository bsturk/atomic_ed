# Background music

The patched D-Day game can play five V for Victory AdLib/FM pieces as a repeating
playlist. The same music is available in D-Day and converted scenarios.

## Set up music

1. Use `INVADE-PATCHED.EXE` as `INVADE.EXE` in your playing copy.
2. Copy `assets/music/V4V.OPL` to `DATA/MUSIC/V4V.OPL` in that copy.
3. Configure Sound Blaster in the game and DOSBox, with matching port, IRQ and
   DMA settings. See the [sound setup guide](../../txt/SOUND_CONFIGURATION_GUIDE.md).
4. Use **Options → Background Music** to turn playback on or off.

Music starts enabled. The game remembers the setting for both sides in
`DATA/MUSIC/MUSIC.CFG`. Sound Effects has its own setting. Enabling music starts
the playlist from the beginning; the five pieces take about 4 minutes 42 seconds
before repeating.

## Rebuilding the data

Place your V4V `V4V.EXE` and `V4V.RES` in `game/v4v`, then run these commands
from the project folder with the editor's Python dependencies installed:

```sh
python3 -m pip install unicorn
python3 tools/build_music_library.py
```

The tool creates `assets/music/V4V.OPL` from the original game's music. Copy the
result to the playing copy as described above.

If Background Music is unavailable in the game, check the `V4V.OPL` location
and Sound Blaster setup. The [patch guide](../../game/waw/patches/README.md)
covers installing and managing the executable patches.
