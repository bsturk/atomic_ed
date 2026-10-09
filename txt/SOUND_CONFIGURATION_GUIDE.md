# D-Day audio: verified configuration

Verified on 2026-10-08 with the original D-Day executable and the current
`INVADE-PATCHED.EXE` in DOSBox-X 2025.02.01. No executable change is needed.
This replaces the incorrect 2025 sound analysis and its unverified claim of a fix.

## What was wrong

The staged D-Day installation has two independent problems:

- Its 34 WAV files are in `SOUND`, but the executable opens `DATA\SOUND`
  under the installation directory. Crusader already has this layout.
- `SYSTEM.SET` is `01 01 00 00 00 00 00 00 00 00`: 640×480, **No Sound Card**.

The old tools misidentified `SYSTEM.SET`'s resolution word as two audio flags,
then wrote hardware values into unrelated display preferences in `INVADE.CFG`.
The staged `INVADE.CFG` and `INVADE.CFG.fixed` contain those mistaken writes.
Neither file contains Sound Blaster port, IRQ or DMA settings.

Original staged files now live in `game/waw/dday/orig`. Investigation and runtime
repairs used a temporary playing copy; those originals and both executables
were left unchanged.

## Repair a playing copy

Close the game. From its directory in DOS/DOSBox, create `DATA\SOUND` if absent
and copy the WAV files there:

```dos
MD DATA\SOUND
COPY SOUND\*.WAV DATA\SOUND
INVADE /SETUP
```

Select **Sound Blaster** and match its port, IRQ and DMA to the emulator.
Choose **Save and Exit**; the first press can expand the hardware settings,
so check them and press it again to save. Keep your preferred screen resolution.
Restart DOSBox after changing files from the host so its directory cache refreshes.
The old root `SOUND` copy is no longer needed once `DATA\SOUND` is complete.

The tested DOSBox-X settings were:

```ini
[mixer]
nosound=false
[sblaster]
sbtype=sb16
sbbase=220
irq=7
dma=1
hdma=5
```

IRQ 5 also exists in game setup; use it if that is what your emulator is configured
for. Changing only `BLASTER` does not change the hardware saved in `SYSTEM.SET`.

Alternatively, the corrected host-side tool handles the configuration and missing
WAV copies. Supply your **playing copy's** path:

```sh
python3 tools/fix_sound_config.py --game-dir /path/to/playing-copy --fix
```

Its defaults are Sound Blaster, port 220h, IRQ 7, DMA 1. Override with `--irq 5`
when appropriate. It preserves resolution and unrelated preferences, enables
both players' sound effects, copies only missing WAVs and preserves existing
custom WAVs. It leaves the root SOUND directory intact. It creates no backups
unless `--backup` is requested and never modifies an executable or scenario.
Run without `--fix` for a read-only diagnosis.

`--repair-legacy-preferences` optionally resets the two invalid display-option
bytes written by the old sound tool to their native defaults. It recognizes
only that specific corruption pattern; previous user choices cannot be recovered.
This repair is separate from enabling sound.

The graphical equivalent is:

```sh
python3 tools/sound_config_editor.py --game-dir /path/to/playing-copy
```

Use the Sound Blaster preset, **Save settings**, and **Copy missing WAV files**.
It also exposes the actual Allies/Axis sound-effects preferences.

## Verified binary formats

`SYSTEM.SET` is exactly five little-endian 16-bit words:

| Offset | Meaning | Tested value |
| --- | --- | --- |
| 0 | VESA video mode | 0x0101 = 640×480 |
| 2 | Sound card | 1 = Sound Blaster; 0 = none |
| 4 | IRQ | 7 |
| 6 | DMA | 1 |
| 8 | I/O base address | 0x0220 |

The game's own setup generated `01 01 01 00 07 00 01 00 20 02` for those settings.
Other video modes are 0x0103 (800×600), 0x0105 (1024×768), 0x0107 (1280×1024).
Card IDs 2, 3 and 4 are Gravis UltraSound, Disney Sound Source and Pro Audio
Spectrum 16. Those devices were not runtime tested here.

`INVADE.CFG` is a 4-byte little-endian length (62), followed by two 31-byte
player preference records. Each has version 5 at relative offset 0. The effects
switch is at relative offset 9: **absolute offsets 13 and 44** for Allies/Axis.
Keep all other fields unchanged. This decoder is D-Day specific; do not apply
it to Crusader's 70-byte CFG or Stalingrad's FIG.

## Native-code evidence

Addresses below are original protected-mode **code object 1 offsets**, not file
offsets. The code object starts at file offset 0x53654. Debug symbols in the
original EXE identify these functions.

- `nucLoadPrefs` at 0x91BE6 reads five 2-byte words from `system.set`.
  `NucInit` at 0x87FF4 passes video/card addresses and loads IRQ/DMA/port from
  the other three words. `nucSavePrefs` at 0x91CFD writes the same layout.
- `nucInitSounds` at 0x87EB8 maps card 0 to disabled audio and card 1 to Sound
  Blaster. `InitMusic` at 0x8144E supplies the saved hardware values to
  `SB_SetCard` and appends `\data\sound` to the installation path.
- `InitAllSongs` at 0x81322 changes into that directory and checks the filename
  table. All 34 entries are WAV files. A missing directory aborts initialization.
- `LoadPrefs` at 0x3016B, `SavePrefs` at 0x302DA and `InitPrefs` at 0x3035C
  handle the two preference records. `NumPrefs` is 31 and `PrefsVersion` is 5.
- `SetAuralParams` at 0x1473 loads `SoundFXAllowed` from player preference +9
  and explicitly sets `MusicAllowed` to zero. `SongLogic` at 0x1462 is empty.
  `PlaySnd` at 0x81544 gates WAV playback on `SoundFXAllowed`.

D-Day's native **background music is disabled in code**. Fixing WAV effects does
not by itself add V for Victory's FM soundtrack. The `InitMusic` name and generic DMX
music-library routines do not establish that D-Day plays background music.

## Runtime verification

Using native Bradley, Sound Blaster 220/IRQ7/DMA1, 48 kHz stereo WAV captures:

| Test | Result |
| --- | --- |
| Correct hardware, WAVs only in root SOUND | 22.775 seconds of exact digital silence |
| Original EXE, correct hardware and DATA/SOUND | 18.553 seconds; PCM peak 28,512, RMS 1,723 |
| Pre-music patched EXE, same configuration/assets | 26.359 seconds; PCM peak 28,522, RMS 1,446 |

Both working runs reached the Bradley map and returned to the DOS prompt through
Quit without hanging. This confirms actual audio output, not just a settings
screen. The missing-directory run also reproduced an exit hang; this does not
establish that every possible exit failure has the same cause.

Captures used DOSBox-X's [WAV recording function](https://dosbox-x.com/wiki/Home)
(F12+W on Linux), with SDL's dummy host audio driver. PCM samples were inspected
rather than sound being heard through physical speakers. These checks cover WAV
playback at startup and entering Bradley; they do not exercise every battle sound.

Configuration-preservation and GUI regression checks:

```sh
xvfb-run -a python3 tools/test_sound_config.py
```

## Optional background music patch

The latest `INVADE-PATCHED.EXE` now includes the separately reversible `dday-music`
layer. Copy `assets/music/V4V.OPL` into the playing copy as
`DATA/MUSIC/V4V.OPL`. This adds five V for Victory background pieces, recorded
from its original AdLib/FM sequencer. They are not Standard MIDI files.
No external MIDI synthesizer or soundfont is needed.

Use **Options → Background Music** to toggle it. It defaults to on; the choice
is saved in `DATA/MUSIC/MUSIC.CFG` (ASCII 0/1) for both sides. Music is independent
of the existing per-side Sound Effects preference. D-Day preference +8 controls
Center Map on Battles; it must not be treated as a music switch. Missing/corrupt
music data disables the new item and leaves the native game operational.

DOSBox-X verification with the new layer and native Bradley:

- Music enabled: 16.730-second capture, nonzero output in every second, peak 24,284.
- Muted: 9.913-second capture; release tail in the first second, then exact digital silence.
- Restart while muted: 34.602-second capture; initial WAV tail, then silence.
- WAV effect triggered while music remained off: 15.371-second capture, peak 21,504;
  output ended after the effect rather than continuing as background music.
- Converted Stalingrad CLASH: 54.679-second capture, continuous music, peak 25,492;
  the new menu item also toggled correctly with the scenario companion resources.
- Tested native/converted runs returned to the DOS prompt cleanly.

`tools/test_music_patch.py` executes the assembled x86 routines under Unicorn at
two relocation addresses, including menu enable flags after InsertMenu, delay
scheduling, saved mute, missing files/hardware, malformed streams, failed timer
creation, clean shutdown and exact patch reversal. See
[patch instructions](../game/waw/patches/README.md) and
[music extraction details](../assets/music/README.md).

## Choppy music / stuck-note report: version 2 correction

The first music build passed audio-presence tests but had a timer callback ABI
bug. It restored EAX rather than returning the zero status required to advance
TSM's next deadline. This caused updates at the wrong rate. Version 2 returns
zero explicitly and divides the native 140 Hz interrupt stream to exactly
100 music ticks per second. Replace `INVADE.EXE`; `V4V.OPL` is unchanged.

Tests now execute the native scheduler instead of mocking it. They cover the
callback deadline, playback rate, looping, pause/resume, and another periodic
service running concurrently. The original version fails this regression.

The playing copy also uses these explicit DOSBox-X settings for repeatable
testing, instead of inheriting CPU speed and mixer buffering from the shared
configuration:

```ini
[cpu]
core=auto
cycles=fixed 30000

[mixer]
nosound=false
blocksize=2048
prebuffer=40
```

These are tested local settings, not proof that the previous host configuration
caused the reported stutter. DOSBox-X documents that excessive CPU cycles can
cause audio dropouts, and larger mixer buffers trade some latency for additional
margin. See its [CPU guide](https://dosbox-x.com/wiki/Guide:CPU-settings-in-DOSBox%E2%80%90X)
and [reference configuration](https://github.com/joncampbell123/dosbox-x/blob/master/dosbox-x.reference.conf).

Version-2 DOSBox-X runtime check: native Bradley, `core=auto`, fixed 30,000 cycles,
2048-sample mixer blocks and 40 ms prebuffer. A 326-second OPL capture covered all
five pieces and the start of the next playlist cycle. All 11,836 recorded note
transitions matched the asset; timing error was -29 to +6 ms across the run.
Map redraws remained responsive during recording. This verifies the emulated
note sequence and timing; the Windows host's physical audio device is not
available in this environment.
