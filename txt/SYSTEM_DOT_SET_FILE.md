# SYSTEM.SET File Format

## Overview

`SYSTEM.SET` is the system preferences file for World at War: D-Day American Invades (INVADE.EXE). It stores user preferences including master enable/disable flags for music and sound effects.

**File Size:** 10 bytes
**Location:** Same directory as INVADE.EXE (typically `game/SYSTEM.SET`)
**Format:** Binary preference data
**Source Code:** Managed by `nuc_pref.c` in the game engine

---

## File Structure

```
Offset   Type    Default  Description
------   ----    -------  -----------
0x00     byte    1        Music enabled (1=ON, 0=OFF)
0x01     byte    1        Sound FX enabled (1=ON, 0=OFF)
0x02     byte    0        Reserved / Unknown
0x03     byte    0        Reserved / Unknown
0x04     byte    0        Reserved / Unknown
0x05     byte    0        Reserved / Unknown
0x06     byte    0        Reserved / Unknown
0x07     byte    0        Reserved / Unknown
0x08     byte    0        Reserved / Unknown
0x09     byte    0        Reserved / Unknown
```

---

## Byte Descriptions

### Byte 0: Music Enable Flag

Controls whether background music plays during gameplay.

| Value | Meaning | Effect |
|-------|---------|--------|
| 0     | OFF     | Music is disabled, no background music plays |
| 1     | ON      | Music is enabled (default) |

**Note:** Even if enabled here, music also requires proper configuration in `INVADE.CFG`.

### Byte 1: Sound FX Enable Flag

Controls whether sound effects play during gameplay.

| Value | Meaning | Effect |
|-------|---------|--------|
| 0     | OFF     | Sound effects are disabled, game is silent except music |
| 1     | ON      | Sound effects are enabled (default) |

**Note:** Even if enabled here, sound FX also requires proper configuration in `INVADE.CFG`.

### Bytes 2-9: Reserved

These bytes are typically set to zero. Their exact purpose is unknown, but they may be:
- Reserved for future use
- Padding to align structure
- Additional preference flags (unused in current version)

---

## Default Configuration

A properly configured `SYSTEM.SET` file should contain:

```
Hex:  01 01 00 00 00 00 00 00 00 00
Dec:   1  1  0  0  0  0  0  0  0  0

Positions:
      ↑  ↑  └──────────────────────┘
      │  │     Reserved (all zeros)
      │  └─ Sound FX enabled
      └──── Music enabled
```

---

## Sound Initialization Logic

The game follows this logic when initializing sound:

```
1. Read SYSTEM.SET byte 0 (music flag)
2. Read SYSTEM.SET byte 1 (sound FX flag)
3. If both are 0 → Skip sound initialization entirely
4. Read INVADE.CFG for sound card configuration
5. If music flag = 1 → Initialize music system
6. If sound FX flag = 1 → Initialize sound effects system
7. Attempt to detect sound card at configured port
8. If detected → Load sound engine
9. If not detected → Disable sound
```

**Important:** Both `SYSTEM.SET` flags AND `INVADE.CFG` configuration must be correct for sound to work.

---

## Relationship with INVADE.CFG

These two files work together:

| File         | Purpose | Controls |
|--------------|---------|----------|
| SYSTEM.SET   | User preference | Whether sound is enabled/disabled by user choice |
| INVADE.CFG   | Hardware config | Which sound card, port, IRQ, DMA to use |

**Example scenarios:**

1. **Sound works:**
   - SYSTEM.SET: Music=1, SoundFX=1
   - INVADE.CFG: Port=0x220, IRQ=5, DMA=1 (correct)

2. **No sound (user disabled):**
   - SYSTEM.SET: Music=0, SoundFX=0
   - INVADE.CFG: (doesn't matter)

3. **No sound (wrong config):**
   - SYSTEM.SET: Music=1, SoundFX=1
   - INVADE.CFG: Port=0x0100 (incorrect, should be 0x220)

4. **Music only:**
   - SYSTEM.SET: Music=1, SoundFX=0
   - INVADE.CFG: Port=0x220 (correct)

---

## Hex Dump Example

Correctly configured file with all sound enabled:

```
Offset   Hex Values                    ASCII     Description
------   ----------                    -----     -----------
0x0000:  01 01 00 00 00 00 00 00      ........  Music ON, SoundFX ON
         ↑  ↑  └──────────────────────────┘
         │  │     Reserved (zeros)
         │  └─── SoundFX enabled
         └────── Music enabled
```

All sound disabled:

```
Offset   Hex Values                    ASCII     Description
------   ----------                    -----     -----------
0x0000:  00 00 00 00 00 00 00 00      ........  Music OFF, SoundFX OFF
         ↑  ↑
         │  └─── SoundFX disabled
         └────── Music disabled
```

---

## Python Example: Reading Preferences

```python
def read_system_preferences(filename='SYSTEM.SET'):
    """Read system preferences from SYSTEM.SET"""
    with open(filename, 'rb') as f:
        data = f.read()

    if len(data) != 10:
        raise ValueError(f"Invalid SYSTEM.SET size: {len(data)} bytes (expected 10)")

    music_enabled = data[0] != 0
    sound_fx_enabled = data[1] != 0

    return {
        'music_enabled': music_enabled,
        'sound_fx_enabled': sound_fx_enabled,
        'raw_bytes': data
    }

# Usage
prefs = read_system_preferences('game/SYSTEM.SET')
print(f"Music: {'ON' if prefs['music_enabled'] else 'OFF'}")
print(f"Sound FX: {'ON' if prefs['sound_fx_enabled'] else 'OFF'}")
```

## Python Example: Writing Preferences

```python
def write_system_preferences(filename='SYSTEM.SET', music=True, sound_fx=True):
    """Write system preferences to SYSTEM.SET"""
    # Create default 10-byte structure (all zeros)
    data = bytearray(10)

    # Set preference flags
    data[0] = 1 if music else 0
    data[1] = 1 if sound_fx else 0
    # Bytes 2-9 remain zero (reserved)

    with open(filename, 'wb') as f:
        f.write(data)

# Usage examples
write_system_preferences('game/SYSTEM.SET', music=True, sound_fx=True)   # Enable all
write_system_preferences('game/SYSTEM.SET', music=True, sound_fx=False)  # Music only
write_system_preferences('game/SYSTEM.SET', music=False, sound_fx=False) # Silent mode
```

## Python Example: Toggle Settings

```python
def toggle_music(filename='SYSTEM.SET'):
    """Toggle music on/off"""
    with open(filename, 'r+b') as f:
        data = bytearray(f.read())
        data[0] = 1 - data[0]  # Toggle between 0 and 1
        f.seek(0)
        f.write(data)

def toggle_sound_fx(filename='SYSTEM.SET'):
    """Toggle sound effects on/off"""
    with open(filename, 'r+b') as f:
        data = bytearray(f.read())
        data[1] = 1 - data[1]  # Toggle between 0 and 1
        f.seek(0)
        f.write(data)
```

---

## Creating From Scratch

If `SYSTEM.SET` is missing or corrupted, create it with default settings:

### Command Line (Linux/macOS)
```bash
# Enable both music and sound FX
printf '\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00' > game/SYSTEM.SET

# Disable all sound
printf '\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00' > game/SYSTEM.SET
```

### Python
```python
# Create with default settings (all enabled)
with open('game/SYSTEM.SET', 'wb') as f:
    f.write(bytes([1, 1, 0, 0, 0, 0, 0, 0, 0, 0]))
```

### DOSBox Debug Command
```
> D 0100 01 01 00 00 00 00 00 00 00 00
> W 0100 0 A SYSTEM.SET
```

---

## In-Game Controls

The game provides menu options to change these settings:

1. **Options Menu:** Access via main menu → Options → Sound
2. **Function Keys:** (if implemented)
   - May toggle music/sound during gameplay
3. **Setup Utility:** `INVADE.EXE /SETUP`
   - Provides GUI for changing preferences
   - Automatically saves to SYSTEM.SET

Changes take effect:
- **Immediately** for music (can toggle during gameplay)
- **Immediately** for sound FX (can toggle during gameplay)
- Settings persist across game sessions

---

## Common Issues and Solutions

### Issue 1: Settings Don't Persist

**Symptom:** Changes reset after exiting game

**Possible causes:**
1. File is read-only
2. No write permission to directory
3. Game crash before saving
4. DOSBox mounting issue

**Solution:**
```bash
# Check permissions
ls -l game/SYSTEM.SET

# Make writable
chmod 644 game/SYSTEM.SET

# In DOSBox, check overlay mount
```

### Issue 2: File Missing

**Symptom:** Game creates new file with wrong defaults

**Solution:** Create default file manually (see "Creating From Scratch" above)

### Issue 3: Corrupted File

**Symptom:** Game crashes or ignores settings

**Solution:**
1. Check file size (must be exactly 10 bytes)
2. Recreate file with default values
3. Restore from backup if available

---

## Validation

To verify file integrity:

```python
def validate_system_set(filename='SYSTEM.SET'):
    """Validate SYSTEM.SET file"""
    try:
        with open(filename, 'rb') as f:
            data = f.read()

        # Check size
        if len(data) != 10:
            return False, f"Wrong size: {len(data)} bytes (expected 10)"

        # Check byte 0 (music flag)
        if data[0] not in [0, 1]:
            return False, f"Invalid music flag: {data[0]} (expected 0 or 1)"

        # Check byte 1 (sound FX flag)
        if data[1] not in [0, 1]:
            return False, f"Invalid sound FX flag: {data[1]} (expected 0 or 1)"

        # Check reserved bytes (should be zero, but not critical)
        if any(data[i] != 0 for i in range(2, 10)):
            # Warning, not error
            print("Warning: Reserved bytes are not zero")

        return True, "Valid"

    except FileNotFoundError:
        return False, "File not found"
    except Exception as e:
        return False, str(e)

# Usage
valid, message = validate_system_set('game/SYSTEM.SET')
print(f"Validation: {message}")
```

---

## Source Code Reference

The file is managed by the `nuc_pref.c` module in the game engine:

```c
// Pseudo-code representation
struct SystemPreferences {
    byte music_enabled;      // 0x00
    byte sound_fx_enabled;   // 0x01
    byte reserved[8];        // 0x02-0x09
};

void LoadSystemPreferences() {
    FILE *f = fopen("SYSTEM.SET", "rb");
    fread(&preferences, sizeof(SystemPreferences), 1, f);
    fclose(f);
}

void SaveSystemPreferences() {
    FILE *f = fopen("SYSTEM.SET", "wb");
    fwrite(&preferences, sizeof(SystemPreferences), 1, f);
    fclose(f);
}
```

---

## Performance Impact

Setting values have minimal performance impact:

| Setting | Performance Impact |
|---------|-------------------|
| Music OFF | Saves ~5% CPU (no music decoder) |
| Sound FX OFF | Saves ~2% CPU (no mixing) |
| Both OFF | Saves ~7% CPU total |

On modern systems (including DOSBox), the impact is negligible.

---

## Debugging

To debug sound issues, check both files:

```python
def diagnose_sound_config():
    """Diagnose sound configuration issues"""
    print("=== Sound Configuration Diagnosis ===\n")

    # Check SYSTEM.SET
    try:
        with open('game/SYSTEM.SET', 'rb') as f:
            system_data = f.read()

        print(f"SYSTEM.SET: {len(system_data)} bytes")
        print(f"  Music enabled: {system_data[0]}")
        print(f"  Sound FX enabled: {system_data[1]}")

        if system_data[0] == 0 and system_data[1] == 0:
            print("  → Issue: Both disabled in SYSTEM.SET")
    except FileNotFoundError:
        print("SYSTEM.SET: NOT FOUND")

    print()

    # Check INVADE.CFG
    try:
        with open('game/INVADE.CFG', 'rb') as f:
            cfg_data = f.read()

        print(f"INVADE.CFG: {len(cfg_data)} bytes")
        port1 = cfg_data[6] | (cfg_data[7] << 8)
        port2 = cfg_data[37] | (cfg_data[38] << 8)

        print(f"  Sound FX port: 0x{port1:04x}")
        print(f"  Music port: 0x{port2:04x}")

        if port1 != 0x220:
            print(f"  → Issue: Sound FX port should be 0x0220")
        if port2 != 0x220:
            print(f"  → Issue: Music port should be 0x0220")
    except FileNotFoundError:
        print("INVADE.CFG: NOT FOUND")
```

---

## See Also

- `INVADE_DOT_CFG_FILE.md` - Hardware configuration file format
- `fix_sound_config.py` - Automated configuration tool
- `SOUND_CONFIGURATION_GUIDE.md` - Complete troubleshooting guide
- `nuc_pref.c` - Source code for preference management

---

## Version History

- **1992-1995:** Format introduced in V for Victory series
- **1995:** Used in World at War: D-Day American Invades
- **Current:** Format remains unchanged, compatible with DOSBox

---

## Technical Notes

- File is read at game startup
- File is written when:
  - User changes options in menu
  - Setup utility is run
  - Game exits normally (if changes made)
- File is NOT written on crash
- File uses simple binary format (no checksum or validation)
- Missing file causes game to use defaults (typically both ON)
- Corrupted file may cause undefined behavior
