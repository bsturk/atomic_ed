# Sound effects and background music

D-Day uses WAV files for sound effects. The patched game also supports a
repeating V for Victory AdLib/FM playlist. Set up audio in your playing copy
of the game.

## Sound effects

Put the game's WAV files in **DATA\SOUND**. If they are in a top-level `SOUND`
folder, run these commands from the game directory in DOSBox:

```dos
MD DATA\SOUND
COPY SOUND\*.WAV DATA\SOUND
INVADE /SETUP
```

In setup, select **Sound Blaster**, choose the port, IRQ and DMA that match
DOSBox, and use **Save and Exit**. If the first press opens the hardware
settings, check the values and press it again to save. Enable **Sound Effects**
for the player side you are using.

Example DOSBox-X configuration:

```ini
[cpu]
core=auto
cycles=fixed 30000

[mixer]
nosound=false
blocksize=2048
prebuffer=40

[sblaster]
sbtype=sb16
sbbase=220
irq=7
dma=1
hdma=5
oplmode=auto
```

For this configuration, use **port 220h, IRQ 7, DMA 1** in D-Day's setup.
Restart DOSBox after copying files into a mounted folder from the host.

## Configure audio from the host

The setup tool can configure a playing copy and copy missing WAV files:

```sh
python3 tools/fix_sound_config.py --game-dir /path/to/playing-copy --fix
```

It defaults to Sound Blaster at 220h, IRQ 7, DMA 1 and enables both sides'
sound effects. It preserves video settings, other preferences and existing
custom WAV files. Use `--irq 5` if your emulator uses IRQ 5. Add `--backup`
to keep copies of configuration files before changing them.

Run the command without `--fix` to check the setup. For a graphical version:

```sh
python3 tools/sound_config_editor.py --game-dir /path/to/playing-copy
```

Choose the Sound Blaster preset, **Save settings**, and **Copy missing WAV files**.

## Background music

Use the patched executable and put **V4V.OPL** in **DATA/MUSIC**. The
[music guide](../assets/music/README.md) explains how to create this file from
your V for Victory installation.

**Options → Background Music** controls the repeating five-piece playlist.
The game remembers this setting for both sides in `DATA/MUSIC/MUSIC.CFG`.
Sound Effects remains a separate preference for each player side.

## Troubleshooting

| Symptom | Check |
| --- | --- |
| Silent sound effects | WAV files are in `DATA/SOUND`, Sound Blaster is selected, and the current side has Sound Effects enabled. |
| Music option unavailable | `DATA/MUSIC/V4V.OPL` is present and the game uses the patched executable with Sound Blaster enabled. |
| Choppy audio | Try the fixed CPU speed and mixer buffering shown above, then adjust for your host. |
| Settings appear correct but sound is silent | Match the game's saved port/IRQ/DMA to DOSBox, then restart DOSBox. |

`SYSTEM.SET` holds hardware and video settings. `INVADE.CFG` holds player
preferences. Use the game's setup or the supplied tools to edit these files.
