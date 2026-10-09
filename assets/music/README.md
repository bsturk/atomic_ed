# V for Victory background music for patched D-Day

The extracted `V4V.OPL` is generated locally and excluded from Git. Build it
from your own V4V installation as described below, then copy it to
`DATA/MUSIC/V4V.OPL` in the playing copy. Install the latest
`game/waw/dday/INVADE-PATCHED.EXE` as `INVADE.EXE` and configure Sound Blaster
220h/IRQ7/DMA1, with matching DOSBox settings. No MIDI soundfont is required.
The five background pieces play in sequence and repeat, for every scenario.

**Options → Background Music** toggles playback independently of Sound Effects.
It defaults to on; the game saves ASCII `0` or `1` in `DATA/MUSIC/MUSIC.CFG`.
This setting applies to the installation, across both player sides. Muting stops
notes; enabling starts the playlist again. Missing or invalid music data disables
the menu item and leaves the rest of the game usable.

## Rebuilding the data

```sh
python3 -m pip install unicorn
python3 tools/build_music_library.py
```

Requires Unicorn and Pillow, plus the staged `game/v4v/V4V.EXE` and `V4V.RES`.
The tool verifies the executable fingerprint before calling its original
16-bit AdLib sequencer under CPU emulation. It records the actual FM register
writes at 100 Hz, preserving instruments and timing. These songs are native
AdLib/FM sequencer data, not Standard MIDI files. Song resources 1–5 are short
cues; resources 6–10 are the five background pieces included here. A two-second
tail separates them. The playlist lasts about 4 minutes 42 seconds.

Verified source EXE SHA-256:
`9918b8011aeb5366b8b8019e9a43f0b6e66331be585b078e348a79ee60b207d1`

## File and runtime format

`WAM1`, little-endian uint16 rate (100), uint16 reserved (0), uint32 event count,
then `(uint8 register, uint8 value, uint16 delay_after_write)` for each event.
Delays are 1/100 second; zero means write the next register immediately.
The last event must have a nonzero delay. OPL detection timer writes are omitted.
The file has 44,653 events and is 178,624 bytes. The runtime validates its length,
registers and maximum immediate burst before installing a timer service.

Version 2 of `dday-music` runs the stream through the native TSM timer service.
It requests the native 140 Hz interrupt rate, divides that explicitly to 100 Hz,
and returns the scheduler's required zero status after every callback.
Its bounded interrupt callback does no file I/O or allocation. Muting pauses the
service and releases melodic/percussion voices; shutdown removes the service
and frees the buffer before the original sound-system shutdown.
It uses the remaining expanded code space at object offset `0xbc000`, adding
no executable pages and no scenario-format changes. Sound Blaster is the
supported hardware setting; other original card drivers are left alone.

Source, manifest, forward patch and exact inverse are under
[`game/waw/patches`](../../game/waw/patches/README.md). The music layer can be
removed without removing earlier patches. The supplied music derives from the
user-provided game resources and remains subject to their original rights.

The first shipped music patch returned the incoming EAX register instead of a
TSM status. The dispatcher therefore left its deadline unchanged and called
music too often. Version 2 corrects this and avoids the native fractional-rate
calculation. The asset file is unchanged; replace the executable when upgrading.
Native-timer regression tests cover deadlines, exact playback rate, playlist
wrap, pause/resume, and a second concurrently scheduled service.
