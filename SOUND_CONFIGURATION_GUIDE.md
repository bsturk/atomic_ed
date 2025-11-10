# Sound Configuration Guide for World at War: America Invades!

## Problem Summary

The base game (INVADE.EXE) had no sound due to **incorrect port configuration** in the `INVADE.CFG` file.

## Root Cause Analysis

### Investigation Results

**Configuration Files:**
- `/game/SYSTEM.SET` (10 bytes) - Controls sound enable/disable flags
- `/game/INVADE.CFG` (66 bytes) - Contains sound card hardware settings

**Issue Identified:**
The `INVADE.CFG` file had the SoundBlaster port configured as `0x0100` (256) instead of the correct default `0x0220` (544).

### Configuration File Structure

#### SYSTEM.SET (10 bytes)
```
Offset  Value  Purpose
------  -----  -------
0x00    0x01   Music enabled (1=ON, 0=OFF)
0x01    0x01   Sound FX enabled (1=ON, 0=OFF)
0x02-09 0x00   Reserved (unused)
```

#### INVADE.CFG (66 bytes)
The file contains two configuration blocks:

**Block 1: Sound FX Configuration (bytes 0-32)**
```
Offset  Size  Value     Purpose
------  ----  -----     -------
0x00    4     0x3e...   Header/size marker
0x04    1     5         IRQ number
0x05    1     1         DMA channel
0x06    2     0x0100    Port address (16-bit little-endian) ← WAS WRONG
0x08-32 25    varies    Flags and other settings
```

**Block 2: Music Configuration (bytes 33-65)**
```
Offset  Size  Value     Purpose
------  ----  -----     -------
0x21    1     0x00      Padding
0x22    1     0x4d      'M' marker (77 decimal = 'M' for Music)
0x23    1     5         IRQ number
0x24    1     1         DMA channel
0x25    2     0x0100    Port address (16-bit little-endian) ← WAS WRONG
0x27-40 varies varies   Flags and other settings
0x41    1     0x4d      'M' marker (end of music block)
```

### The Problem

**Incorrect Settings (Before Fix):**
- Port: `0x0100` (256 decimal)
- IRQ: 5 ✓ (Correct)
- DMA: 1 ✓ (Correct)

**Correct Settings (After Fix):**
- Port: `0x0220` (544 decimal) ✓
- IRQ: 5 ✓
- DMA: 1 ✓

**Why This Caused No Sound:**
The game was trying to communicate with a SoundBlaster card at I/O port 0x100, but:
1. Standard SoundBlaster cards are configured to port 0x220 by default
2. DOSBox emulates SoundBlaster at port 0x220
3. Real hardware SoundBlaster cards use port 0x220 (220h)
4. Port 0x100 is not a valid SoundBlaster port address

## Solution

### Automated Fix (Recommended)

Use the provided Python tool:

```bash
cd /home/user/atomic_ed
python3 fix_sound_config.py --backup --set-defaults
```

This will:
1. Backup your current config files (`INVADE.CFG.bak`, `SYSTEM.SET.bak`)
2. Set the correct SoundBlaster settings:
   - Port: 0x220 (544)
   - IRQ: 5
   - DMA: 1
3. Enable music and sound FX if disabled

### Manual Fix

If you prefer to fix manually:

**Option 1: Run the game's setup utility**
```
cd game
INVADE.EXE /SETUP
```
Then select:
- Sound Card: SoundBlaster
- Port: 220h
- IRQ: 5
- DMA: 1

**Option 2: Hex edit INVADE.CFG**
Using a hex editor, change these bytes:
```
Offset 0x06: Change 0x00 to 0x20
Offset 0x07: Change 0x01 to 0x02
Offset 0x25: Change 0x00 to 0x20  (offset 37 decimal)
Offset 0x26: Change 0x01 to 0x02  (offset 38 decimal)
```

**Option 3: Use Python to patch**
```python
with open('game/INVADE.CFG', 'r+b') as f:
    data = bytearray(f.read())
    port = (0x220).to_bytes(2, 'little')  # 0x20 0x02
    data[6:8] = port    # Block 1
    data[37:39] = port  # Block 2
    f.seek(0)
    f.write(data)
```

## DOSBox Configuration

Even with correct config files, ensure DOSBox is properly configured:

### dosbox.conf Settings

Add to `[sblaster]` section:
```ini
[sblaster]
sbtype=sb16
sbbase=220
irq=5
dma=1
hdma=5
sbmixer=true
oplmode=auto
oplemu=default
oplrate=49716
```

### BLASTER Environment Variable

Add to `[autoexec]` section:
```ini
[autoexec]
SET BLASTER=A220 I5 D1 H5 T4
```

Format breakdown:
- `A220` - Port address (220h)
- `I5` - IRQ 5
- `D1` - 8-bit DMA channel 1
- `H5` - 16-bit DMA channel 5
- `T4` - Type 4 (SB16)

## Verification

### Check Configuration
```bash
python3 fix_sound_config.py --analyze
```

Expected output:
```
Block 1 (Sound FX):
  Port: 0x0220 (544) ✓
  IRQ:  5 ✓
  DMA:  1 ✓

Block 2 (Music):
  Port: 0x0220 (544) ✓
  IRQ:  5 ✓
  DMA:  1 ✓

✓ Configuration looks reasonable
```

### Test in Game

1. Launch DOSBox
2. Run the game:
   ```
   cd game
   INVADE.EXE
   ```
3. You should now hear:
   - Menu music
   - Battle sound effects
   - Unit movement sounds

## Additional Notes

### Why Port 0x220?

The SoundBlaster standard uses these default settings:
- **Port 220h (544)** - Most common, industry standard
- Port 240h (576) - Alternative
- Port 260h (608) - Alternative
- Port 280h (640) - Alternative

DOSBox and most emulators default to 220h.

### Sound Card Detection

The game detects sound cards by:
1. Reading INVADE.CFG for port/IRQ/DMA settings
2. Checking BLASTER environment variable (if set)
3. Probing the specified port for a SoundBlaster DSP
4. Falling back to no sound if detection fails

### Converted Scenarios

Note: This fix addresses the base game configuration. The recent commit `f9aab5e` fixed a separate issue where **converted Crusader scenarios** were corrupting sound settings by preserving configuration data at offsets 0x60-0x7F in scenario files.

Both issues are now resolved:
- ✓ Base game config fixed (this guide)
- ✓ Converted scenarios fixed (commit f9aab5e)

## Related Files

- `/home/user/atomic_ed/fix_sound_config.py` - Automated fix tool
- `/home/user/atomic_ed/game/INVADE.CFG` - Sound card configuration
- `/home/user/atomic_ed/game/SYSTEM.SET` - Sound enable/disable flags
- `/home/user/atomic_ed/scenario_converter.py` - Handles scenario conversion (includes sound fix for converted files)

## Troubleshooting

### Still No Sound?

1. **Verify config files are correct:**
   ```bash
   python3 fix_sound_config.py --analyze
   ```

2. **Check DOSBox audio is enabled:**
   - Look for "SB:Initializing" message on startup
   - Verify sbtype=sb16 in dosbox.conf

3. **Run setup utility:**
   ```
   INVADE.EXE /SETUP
   ```
   Manually select SoundBlaster and port 220h

4. **Test with /NOCHK flag:**
   ```
   INVADE.EXE /NOCHK
   ```
   Skips sound card check (may help diagnose)

5. **Check game volume:**
   - In-game options may have volume sliders
   - Ensure they're not set to 0

### Error Messages

**"Invalid SB IRQ"** - IRQ not in valid range (2, 5, 7, 10)
- Fix: Use IRQ 5 or 7

**"Invalid SB DMA"** - DMA not in valid range (0, 1, 3)
- Fix: Use DMA 1

**"Please run setup again"** - Config file corrupted
- Fix: Run `python3 fix_sound_config.py --set-defaults`

## Technical Details

### Port Storage Format

The port is stored as a 16-bit unsigned integer in **little-endian** format:
- Port 220h (0x0220) is stored as: `20 02` (bytes 0x20, 0x02)
- Port 100h (0x0100) was stored as: `00 01` (bytes 0x00, 0x01) ← Wrong

### Why Two Blocks?

The game has separate audio subsystems:
- **Block 1:** Digital sound effects (explosions, gunfire)
- **Block 2:** Music playback (background music)

Both can use the same sound card but with independent volume/routing settings.

### Game Sound System

From strings analysis of INVADE.EXE:
- Uses MTM music format (`mt_music.c`)
- Digital sound mixer (`dig_volume_control`)
- Supports multiple cards: SoundBlaster, Pro Audio Spectrum, Gravis Ultrasound
- Music and SFX can be independently enabled/disabled

## Credits

Analysis and fix by Claude (2025-11-10)
Based on investigation of INVADE.EXE, INVADE.CFG, and SYSTEM.SET files
