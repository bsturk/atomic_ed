# Sound Configuration Editor GUI

A user-friendly graphical tool to edit sound configuration files for World at War: D-Day American Invades.

## Features

- **Tabbed Interface** - Separate tabs for SYSTEM.SET and INVADE.CFG
- **Automatic Backups** - Creates .bak files before saving
- **Input Validation** - Prevents invalid configurations
- **Presets** - Quick setup for SoundBlaster 16 defaults
- **Real-time Info** - Shows current configuration and file details

## Usage

### Basic Usage

```bash
# Run with auto-detection (searches ./game, script_dir/game, or current dir)
python3 sound_config_editor.py

# Specify game directory on command line
python3 sound_config_editor.py --game-dir /path/to/game

# Or just run it and use "Change Directory..." button in the GUI
python3 sound_config_editor.py
```

The GUI now includes a **"Change Directory..."** button at the top that lets you select the folder containing your config files at any time.

### SYSTEM.SET Tab (Preferences)

Simple checkboxes to enable/disable:
- **Music Enabled** - Background music on/off
- **Sound Effects Enabled** - Sound effects on/off

Click **Save Changes** to write the file (creates SYSTEM.SET.bak backup).

### INVADE.CFG Tab (Sound Card)

Configure hardware settings for both Sound Effects and Music blocks:

**Fields:**
- **IRQ** - Interrupt request (typically 5 or 7)
- **DMA** - Direct memory access channel (typically 1)
- **I/O Port** - Base address in hex (typically 220 for 0x0220)

**Presets:**
- **SoundBlaster 16 Default** - Sets both blocks to Port 220, IRQ 5, DMA 1
- **Copy Sound FX to Music** - Copies Sound FX settings to Music block

Click **Save Changes** to write the file (creates INVADE.CFG.bak backup).

## Screenshots

### Main Window
```
┌─────────────────────────────────────────────┐
│ Sound Configuration Editor - D-Day          │
├─────────────────────────────────────────────┤
│ Config Directory: /path/to/game             │
│                        [Change Directory...] │
├─────────────────────────────────────────────┤
│ [SYSTEM.SET (Preferences)] [INVADE.CFG]     │
└─────────────────────────────────────────────┘
```

### SYSTEM.SET Tab
```
┌─────────────────────────────────────────────┐
│ SYSTEM.SET - System Preferences             │
├─────────────────────────────────────────────┤
│ File: /path/to/game/SYSTEM.SET              │
├─────────────────────────────────────────────┤
│ Sound Preferences                           │
│ ☑ Music Enabled                             │
│ ☑ Sound Effects Enabled                     │
├─────────────────────────────────────────────┤
│ File Information                            │
│ File size: 10 bytes                         │
│ Byte 0 (Music):    0x01 (1) - ON           │
│ Byte 1 (Sound FX): 0x01 (1) - ON           │
├─────────────────────────────────────────────┤
│   [Save Changes]  [Reload]  [Browse...]     │
└─────────────────────────────────────────────┘
```

### INVADE.CFG Tab
```
┌─────────────────────────────────────────────┐
│ INVADE.CFG - Sound Card Configuration      │
├─────────────────────────────────────────────┤
│ File: /path/to/game/INVADE.CFG              │
├─────────────────────────────────────────────┤
│ Sound Effects Configuration                 │
│ IRQ:      5      (typically 5 or 7)         │
│ DMA:      1      (typically 1)              │
│ I/O Port: 220    (hex, e.g., 220 for 0x220)│
├─────────────────────────────────────────────┤
│ Music Configuration                         │
│ IRQ:      5      (typically 5 or 7)         │
│ DMA:      1      (typically 1)              │
│ I/O Port: 220    (hex, e.g., 220 for 0x220)│
├─────────────────────────────────────────────┤
│ Presets                                     │
│ [SoundBlaster 16 Default]  [Copy SFX→Music]│
├─────────────────────────────────────────────┤
│ File Information                            │
│ File size: 66 bytes                         │
│                                             │
│ Sound FX Block (bytes 4-7):                 │
│   IRQ:  5                                   │
│   DMA:  1                                   │
│   Port: 0x0220 (544)                        │
├─────────────────────────────────────────────┤
│   [Save Changes]  [Reload]  [Browse...]     │
└─────────────────────────────────────────────┘
```

## Common Tasks

### Fix "No Sound" Issue

1. Open the application
2. Click **INVADE.CFG** tab
3. Click **SoundBlaster 16 Default** button
4. Click **Save Changes**
5. Click **SYSTEM.SET** tab
6. Ensure both checkboxes are checked
7. Click **Save Changes** (if needed)

### Disable All Sound

1. Click **SYSTEM.SET** tab
2. Uncheck both **Music Enabled** and **Sound Effects Enabled**
3. Click **Save Changes**

### Configure Custom Sound Card

1. Click **INVADE.CFG** tab
2. Enter your sound card settings:
   - IRQ (e.g., 7)
   - DMA (e.g., 3)
   - Port (e.g., 240 for 0x0240)
3. Click **Copy Sound FX to Music** to use same settings for both
4. Click **Save Changes**

## Backups

The tool automatically creates backups before saving:

- **SYSTEM.SET.bak** - Backup of SYSTEM.SET
- **INVADE.CFG.bak** - Backup of INVADE.CFG

If something goes wrong, you can restore from backups:

```bash
# Restore SYSTEM.SET
cp game/SYSTEM.SET.bak game/SYSTEM.SET

# Restore INVADE.CFG
cp game/INVADE.CFG.bak game/INVADE.CFG
```

## Requirements

- Python 3.6+
- tkinter (usually included with Python)

To check if tkinter is installed:

```bash
python3 -c "import tkinter; print('tkinter is installed')"
```

If not installed:

```bash
# Ubuntu/Debian
sudo apt-get install python3-tk

# Fedora/RHEL
sudo dnf install python3-tkinter

# macOS
# tkinter is included with Python from python.org
```

## Troubleshooting

### "File not found" warning

The tool will show a warning but continue with default values. You can:
1. Click **Browse...** to select an existing file
2. Click **Save Changes** to create the file with defaults
3. Manually create the file (see documentation)

### Save button is disabled

The save button only enables when you make changes. If you just loaded the file, make a change first.

### Invalid port value error

Port values must be entered in **hexadecimal without 0x prefix**:
- ✓ Correct: `220` (for 0x0220)
- ✗ Wrong: `0x220` or `544`

### Changes don't take effect in game

1. Make sure you saved both files
2. Restart the game
3. Check that files are in the same directory as INVADE.EXE

## Command Line Options

```
usage: sound_config_editor.py [-h] [--game-dir GAME_DIR]

Sound Configuration Editor for World at War: D-Day

optional arguments:
  -h, --help           show this help message and exit
  --game-dir GAME_DIR  Path to game directory (default: ./game)
```

## See Also

- `txt/INVADE_DOT_CFG_FILE.md` - Technical documentation for INVADE.CFG
- `txt/SYSTEM_DOT_SET_FILE.md` - Technical documentation for SYSTEM.SET
- `fix_sound_config.py` - Command-line tool for batch fixes
- `SOUND_CONFIGURATION_GUIDE.md` - Complete troubleshooting guide

## License

This tool is provided as-is for use with World at War: D-Day American Invades.
