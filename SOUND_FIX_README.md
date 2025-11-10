# Sound Fix for World at War: America Invades!

## Quick Start

**Problem:** No sound in INVADE.EXE game
**Solution:** SoundBlaster port was configured incorrectly
**Status:** ✓ FIXED

### Apply the Fix

```bash
cd /home/user/atomic_ed
python3 fix_sound_config.py --backup --set-defaults
```

That's it! The game should now have sound in DOSBox.

## What Was Wrong?

The `INVADE.CFG` file had the SoundBlaster I/O port set to **0x0100** (256) instead of the standard **0x0220** (544).

**Before:**
```
Block 1 Port: 0x0100 (256)  ✗ WRONG
Block 2 Port: 0x0100 (256)  ✗ WRONG
```

**After:**
```
Block 1 Port: 0x0220 (544)  ✓ CORRECT
Block 2 Port: 0x0220 (544)  ✓ CORRECT
```

## Files Changed

| File | Change |
|------|--------|
| `game/INVADE.CFG` | Bytes 6-7 and 37-38 changed to set port 0x220 |
| `game/SYSTEM.SET` | Already correct (music/sound enabled) |

## Configuration Details

### INVADE.CFG Structure (66 bytes)

**Block 1: Sound FX (bytes 0-32)**
- IRQ: 5 ✓
- DMA: 1 ✓
- Port: 0x220 ✓ (was 0x0100)

**Block 2: Music (bytes 33-65)**
- IRQ: 5 ✓
- DMA: 1 ✓
- Port: 0x220 ✓ (was 0x0100)

### SYSTEM.SET Structure (10 bytes)

- Byte 0: Music enabled (1 = ON) ✓
- Byte 1: Sound FX enabled (1 = ON) ✓

## Tools Provided

### 1. fix_sound_config.py

Automated sound configuration tool:

```bash
# Analyze current configuration
python3 fix_sound_config.py --analyze

# Fix the configuration
python3 fix_sound_config.py --backup --set-defaults

# Enable sound if disabled
python3 fix_sound_config.py --enable
```

### 2. Documentation

- **SOUND_FIX_SUMMARY.txt** - Complete technical analysis
- **SOUND_CONFIGURATION_GUIDE.md** - Detailed guide with troubleshooting
- **SOUND_FIX_README.md** - This file (quick reference)

## DOSBox Setup

### Recommended dosbox.conf Settings

```ini
[sblaster]
sbtype=sb16
sbbase=220
irq=5
dma=1
hdma=5
sbmixer=true

[autoexec]
SET BLASTER=A220 I5 D1 H5 T4
```

## Verification

Check if the fix worked:

```bash
python3 fix_sound_config.py --analyze
```

Expected output:
```
✓ Configuration looks reasonable
```

## Troubleshooting

### Still No Sound?

1. **Verify config is correct:**
   ```bash
   python3 fix_sound_config.py --analyze
   ```

2. **Check DOSBox audio:**
   - Look for "SB:Initializing" on startup
   - Verify sbtype=sb16 in dosbox.conf

3. **Run game setup:**
   ```
   cd game
   INVADE.EXE /SETUP
   ```
   Select SoundBlaster, port 220h, IRQ 5, DMA 1

4. **Test with /NOCHK:**
   ```
   INVADE.EXE /NOCHK
   ```
   Skips sound card detection

### Common Issues

| Error | Solution |
|-------|----------|
| "Invalid SB IRQ" | Port is wrong, run fix tool |
| "Invalid SB DMA" | DMA should be 1, run fix tool |
| No sound in game | Check DOSBox volume and config |

## Technical Summary

**Root Cause:**
I/O port misconfiguration (0x0100 vs 0x0220)

**Files Investigated:**
- `/home/user/atomic_ed/game/INVADE.CFG` - Sound card settings
- `/home/user/atomic_ed/game/SYSTEM.SET` - Enable/disable flags
- `/home/user/atomic_ed/game/INVADE.EXE` - Game executable (string analysis)

**Bytes Changed:**
- Byte 6: `0x00` → `0x20`
- Byte 7: `0x01` → `0x02`
- Byte 37: `0x00` → `0x20`
- Byte 38: `0x01` → `0x02`

**Standard SoundBlaster Settings:**
- Port: 0x220 (544 decimal)
- IRQ: 5
- DMA: 1
- Type: SB16

## Related Fixes

This fix addresses the **base game** configuration. A previous commit ([f9aab5e](https://github.com/bsturk/atomic_ed/commit/f9aab5e)) fixed a separate issue where **converted Crusader scenarios** were corrupting sound settings.

Both issues are now resolved:
- ✓ Base game config (this fix)
- ✓ Converted scenarios (commit f9aab5e)

## See Also

- **SOUND_CONFIGURATION_GUIDE.md** - Full documentation
- **SOUND_FIX_SUMMARY.txt** - Technical analysis report
- **fix_sound_config.py** - Configuration tool source

## Credits

Investigation and fix: Claude (Anthropic)
Date: 2025-11-10
Method: Binary analysis of INVADE.CFG, SYSTEM.SET, and executable strings
