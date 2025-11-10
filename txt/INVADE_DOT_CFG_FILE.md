# INVADE.CFG File Format

## Overview

`INVADE.CFG` is the primary configuration file for World at War: D-Day American Invades (INVADE.EXE). It stores sound card configuration for both sound effects and music playback.

**File Size:** 66 bytes
**Location:** Same directory as INVADE.EXE (typically `game/INVADE.CFG`)
**Format:** Binary configuration data

---

## File Structure

The file consists of two configuration blocks:

```
Offset   Size  Description
------   ----  -----------
0x00     33    Sound FX Configuration Block
0x21     33    Music Configuration Block
```

### Block 1: Sound FX Configuration (Bytes 0x00-0x20, 33 bytes)

```
Offset   Type    Value   Description
------   ----    -----   -----------
0x00     byte    varies  Sound card type identifier
0x01     byte    varies  Unknown/reserved
0x02     byte    varies  Unknown/reserved
0x03     byte    varies  Unknown/reserved
0x04     byte    5       IRQ (Interrupt Request) - typically 5 for SoundBlaster
0x05     byte    1       DMA (Direct Memory Access) - typically 1 for SoundBlaster
0x06     word    0x0220  I/O Port (little-endian) - typically 0x0220 (544 decimal)
0x08-0x20 bytes  varies  Additional configuration data
```

### Block 2: Music Configuration (Bytes 0x21-0x41, 33 bytes)

```
Offset   Type    Value   Description
------   ----    -----   -----------
0x21     byte    varies  Unknown/reserved
0x22     byte    0x4D    Marker byte 'M' (0x4D = ASCII 'M' for Music)
0x23-0x24 word   varies  Unknown/reserved
0x25     byte    5       IRQ (Interrupt Request) - typically 5 for SoundBlaster
0x26     byte    1       DMA (Direct Memory Access) - typically 1 for SoundBlaster
0x27     word    0x0220  I/O Port (little-endian) - typically 0x0220 (544 decimal)
0x29-0x40 bytes  varies  Additional configuration data
0x41     byte    0x4D    Marker byte 'M' (0x4D = ASCII 'M' for Music)
```

---

## Standard SoundBlaster Configuration

The default configuration for a standard SoundBlaster 16 card:

| Setting | Value (Hex) | Value (Decimal) | Description |
|---------|-------------|-----------------|-------------|
| Port    | 0x0220      | 544             | I/O base address |
| IRQ     | 5           | 5               | Interrupt request line |
| DMA     | 1           | 1               | DMA channel |

### BLASTER Environment Variable

The equivalent BLASTER environment variable setting:
```
SET BLASTER=A220 I5 D1 H5 T4
```

Where:
- `A220` = Address (port) 0x220
- `I5` = IRQ 5
- `D1` = 8-bit DMA channel 1
- `H5` = 16-bit DMA channel 5
- `T4` = Card type (SB16)

---

## Common Issues and Solutions

### Issue 1: No Sound in Game

**Symptom:** Game runs but has no sound or music

**Cause:** Incorrect I/O port configuration (often set to 0x0100 instead of 0x0220)

**Solution:** Fix bytes 0x06-0x07 and 0x27-0x28:
```
Byte 0x06: 0x20  (port low byte)
Byte 0x07: 0x02  (port high byte)
Byte 0x27: 0x20  (port low byte)
Byte 0x28: 0x02  (port high byte)
```

### Issue 2: Sound Works But Music Doesn't (or vice versa)

**Symptom:** Only sound effects or only music plays

**Cause:** One block is configured correctly, the other is not

**Solution:** Ensure both blocks have identical IRQ/DMA/Port settings

---

## Hex Dump Example (Correct Configuration)

Here's what a correctly configured INVADE.CFG looks like (showing relevant bytes):

```
Offset   Hex Values                          ASCII
------   ---------                           -----
0x0000:  XX XX XX XX 05 01 20 02 ...        ........
         └─────────┘ └─┘ └─┘ └───┘
         (card type) IRQ DMA  Port=0x0220

0x0020:  ... XX 4D XX XX 05 01 20 02 ...    .M......
             └─┘ └─────┘ └─┘ └─┘ └───┘
             'M'  (unkn) IRQ DMA  Port=0x0220
```

---

## Byte Order (Endianness)

**Important:** The I/O port is stored in **little-endian** format:

```
Port 0x0220 is stored as:
  Byte 0x06: 0x20 (low byte)
  Byte 0x07: 0x02 (high byte)
```

To read: `port = byte[0] | (byte[1] << 8)`
To write: `byte[0] = port & 0xFF; byte[1] = (port >> 8) & 0xFF`

---

## Python Example: Reading Configuration

```python
with open('INVADE.CFG', 'rb') as f:
    data = f.read()

# Read Sound FX block
sfx_irq = data[4]
sfx_dma = data[5]
sfx_port = data[6] | (data[7] << 8)

# Read Music block
music_irq = data[35]  # 0x23
music_dma = data[36]  # 0x24
music_port = data[37] | (data[38] << 8)

print(f"Sound FX: Port=0x{sfx_port:04x}, IRQ={sfx_irq}, DMA={sfx_dma}")
print(f"Music:    Port=0x{music_port:04x}, IRQ={music_irq}, DMA={music_dma}")
```

## Python Example: Writing Configuration

```python
with open('INVADE.CFG', 'r+b') as f:
    data = bytearray(f.read())

    # Set both blocks to port 0x0220
    port = 0x0220

    # Sound FX block
    data[6] = port & 0xFF
    data[7] = (port >> 8) & 0xFF

    # Music block
    data[37] = port & 0xFF
    data[38] = (port >> 8) & 0xFF

    # Write back
    f.seek(0)
    f.write(data)
```

---

## Supported Sound Cards

The game supports multiple sound cards:

1. **SoundBlaster / SoundBlaster 16** (most common)
   - Port: 0x220
   - IRQ: 5
   - DMA: 1

2. **Pro Audio Spectrum**
   - Various configurations

3. **Gravis Ultrasound**
   - Various configurations

4. **Personal Sound System**
   - Various configurations

---

## Game Initialization Sequence

When INVADE.EXE starts:

1. Reads `INVADE.CFG` into memory
2. Reads `SYSTEM.SET` to check if sound/music are enabled
3. Attempts to initialize sound card at the configured port
4. If card not found at specified address, disables sound
5. If found, initializes sound engine and loads WAV files

---

## Setup Utility

The game includes a built-in setup utility:

```
INVADE.EXE /SETUP
```

This allows interactive configuration of:
- Sound card type
- I/O port
- IRQ
- DMA channel
- Enable/disable sound effects
- Enable/disable music

The setup utility writes the configuration to `INVADE.CFG`.

---

## Related Files

- **SYSTEM.SET** - Master enable/disable flags for sound and music (see SYSTEM_DOT_SET_FILE.md)
- **SOUND/*.WAV** - 34 WAV files for game sound effects
- **Sound engine** - Initialized by `INITSOUNDENGINE` function

---

## DOSBox Configuration

For DOSBox users, add to your `dosbox.conf`:

```ini
[sblaster]
sbtype=sb16
sbbase=220
irq=5
dma=1
hdma=5

[cpu]
cycles=max

[autoexec]
SET BLASTER=A220 I5 D1 H5 T4
```

---

## Troubleshooting

### Sound works in DOSBox but not in game

1. Check `INVADE.CFG` port setting (should be 0x0220)
2. Check `SYSTEM.SET` flags (both bytes 0-1 should be 1)
3. Verify DOSBox SoundBlaster is configured correctly

### Setup utility fails to save settings

1. Check file permissions on `INVADE.CFG`
2. Ensure file is not read-only
3. Verify disk has write permissions

### Music plays but no sound effects (or vice versa)

1. Both blocks must have identical IRQ/DMA/Port settings
2. Check `SYSTEM.SET` byte 0 (music) and byte 1 (sound FX)

---

## Version History

- **1992-1995:** Original format used in V for Victory series
- **1995:** Format used in World at War: D-Day American Invades
- **Current:** Format remains compatible with modern DOSBox

---

## Technical Notes

- The file format is game-specific and not standardized
- Similar configuration formats used across Atomic Games titles
- The 'M' marker bytes (0x4D) may be used for validation
- Exact purpose of some bytes remains unknown
- Configuration is read at startup only (no hot-reload)

---

## See Also

- `SYSTEM_DOT_SET_FILE.md` - Master sound enable/disable configuration
- `fix_sound_config.py` - Automated configuration tool
- `SOUND_CONFIGURATION_GUIDE.md` - Complete troubleshooting guide
