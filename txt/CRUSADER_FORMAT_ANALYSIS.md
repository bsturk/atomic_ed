# Crusader Scenario Format (Magic 0x0dac) - Complete Analysis Report

## Executive Summary

The Crusader (0x0dac) scenario format is fundamentally different from both the Stalingrad (0x0f4a) and D-Day (0x1230) formats. While all three share a 96-byte header, the Crusader format:

1. **Does NOT use floating-point counts** like Stalingrad
2. **Does NOT use standard file pointers** at 0x40-0x5F like the other formats
3. **Uses fixed offsets** for data sections starting at 0x80
4. **Stores parameters** as 16-bit values at 0x60-0x7F (not the standard locations)
5. **Has persistent header values** that appear in every file at the same offset

## Header Structure (0x00-0x5F)

### Offset 0x00-0x01: Magic Number
- **Value**: 0x0dac (little-endian: `ac 0d`)
- **Type**: uint16
- **Meaning**: Format identifier for V for Victory: Crusader

### Offset 0x02-0x03: Reserved
- **Value**: 0x0000 (always)
- **Type**: uint16
- **Meaning**: Unknown/unused

### Offset 0x04-0x07: First Parameter
- **Value**: 0x00000088 (136 in decimal)
- **Type**: uint32
- **Meaning**: Constant value (appears in all Crusader files)
- **Interpretation**: Possibly a format version or capability flag

### Offset 0x08-0x0B: Second Parameter
- **Value**: Typically 0x00000001 (1)
- **Type**: uint32
- **Meaning**: Usually 1 or 0, varies slightly per file
- **Interpretation**: Possible difficulty level or scenario type indicator

### Offset 0x0C-0x0F: Third Parameter
- **Value**: Typically 0x00000001 (1)
- **Type**: uint32
- **Meaning**: Usually 1, rarely varies
- **Interpretation**: Unknown (possibly scenario variant or player count)

### Offset 0x10-0x13: Mysterious Value 1
- **Value Range**: 0x00016687 to 0x000166BD (91,783 to 91,837)
- **Type**: uint32
- **Consistency**: Appears in EVERY file with almost identical value
- **Meaning**: **NOT a file pointer** (exceeds many file sizes)
- **Interpretation**: Possibly a checksum, hash, or internal game constant

### Offset 0x14-0x17: Mysterious Value 2
- **Value Range**: 0x00016697 to 0x000166D9 (91,799 to 91,865)
- **Type**: uint32
- **Consistency**: Varies per file but related to scenario characteristics
- **Meaning**: **NOT a file pointer** (exceeds many file sizes)
- **Interpretation**: Possibly computed from scenario data size or type

### Offset 0x18-0x5F: Reserved/Padding
- **Value**: All zeros (0x00)
- **Type**: uint32 × 10
- **Meaning**: Unused padding

## Configuration Data (0x60-0x7F)

The 32 bytes at offset 0x60-0x7F contain scenario-specific parameters stored as **16-bit little-endian values**:

### 16-bit Parameters (0x60-0x6F)
```
Offset  Parameter#  Typical Value  Meaning
------  ----------  -------- -----  ---------
0x60    Param 1     2-24            Possibly unit group count or roster size
0x62    Param 2     3-21            Possibly player count or side count
0x64    Param 3     14-169          Possibly objective count or map parameter
0x66    Param 4     18-239          Possibly location count or hex count
0x68    Param 5     26-192          Possibly terrain type count
0x6A    Param 6     24-239          Possibly weather or time parameter
0x6C    Param 7     18-50           Possibly reinforcement count
0x6E    Param 8     18-68           Possibly victory condition count
```

### Byte Parameters (0x70-0x7F)
```
Offset  Parameter#  Value          Meaning
------  ----------  -------        ---------
0x70    Byte 1      0x00 (always)  Reserved
0x71    Byte 2      0x00 (always)  Reserved
0x72    Byte 3      0x00 (always)  Reserved
0x73    Byte 4      0x00 (always)  Reserved
0x74    Byte 5      0x17 (23)      Possibly scenario turn count or phase count
0x75    Byte 6      0x00 (always)  Reserved
0x76    Byte 7      0x13 (19)      Possibly another parameter count
0x77    Byte 8      0x00 (always)  Reserved
0x78-0x7F Reserved (varies, meaning unknown)
```

## Data Sections

### Text Sections (Fixed Offset Layout)
The Crusader format stores mission briefing and other text strings at **fixed offsets**, not via pointers:

```
Offset      Section Name              Content Type
--------    ----------------------    ------------------
0x80        Mission Briefing           Main scenario description (50-100 bytes)
0x100       Secondary Briefing         Unit assignment description
0x180       Tertiary Briefing          Objective description
0x200       Additional Text 1          Victory conditions text
0x280       Additional Text 2          Map features text
...         (pattern continues)        Additional scenario information
```

**Pattern**: Text sections appear to be stored in 128-byte (0x80) aligned blocks, with actual text padded with zeros to fill the block.

### Binary Data Sections
Following the text sections (approximately after offset 0x1000), binary data sections contain:
- Unit rosters
- Unit positioning
- Numeric parameters
- AI behavior data
- Terrain data

## Comparison Table: Format Differences

| Aspect | 0x0f4a (Stalingrad) | 0x0dac (Crusader) | 0x1230 (D-Day) |
|--------|---------------------|-------------------|---|
| **Magic Number** | 0x0f4a | 0x0dac | 0x1230 |
| **Header Size** | 96 bytes | 96 bytes | 96 bytes |
| **Counts Storage** | Floats (0x04-0x33) | Uint32 (0x04-0x17) | Uint32 (0x04-0x2F) |
| **Pointers** | At 0x40-0x5F (8 pointers) | **Not standard** | At 0x40-0x5F (8 pointers) |
| **Parameters** | None | At 0x60-0x7F (16-bit) | None |
| **Data Access** | File pointer based | Fixed offset based | File pointer based |
| **Text Location** | Via pointer (PTR3/PTR4) | Fixed at 0x80+ | Via pointer (PTR3/PTR4) |
| **Padding** | Minimal | Extensive (65%+ zeros) | Minimal |

## Key Findings

### Finding 1: Header Constants
- Values at 0x04-0x07 (0x88) are **identical across all Crusader files**
- Values at 0x10-0x17, while varying, are **never valid file pointers**
- These are likely **internal game format constants**, not runtime data

### Finding 2: Parameters at 0x60-0x7F
- These 16-bit values are **scenario-specific configuration parameters**
- They vary dramatically between scenarios (2-239 range)
- They appear to represent: unit counts, objective counts, dimensions, turn counts
- **This is the key differentiation from Stalingrad format**

### Finding 3: Fixed Offset Data Layout
- Data is stored at **fixed, predictable offsets** (0x80, 0x100, 0x180, 0x200, etc.)
- Text blocks are **padded with zeros to fixed sizes** (appears to be 128-byte alignment)
- **No file pointers are needed** because layout is predetermined
- This is simpler but less flexible than the pointer-based approach

### Finding 4: Data Section Alignment
- Each data block appears to be aligned on 128-byte (0x80) boundaries
- Text content is followed by zero-padding to fill the block
- This alignment pattern continues throughout the file
- Makes the file size highly dependent on scenario content

## Conversion Implications

### When Converting Crusader to D-Day Format

**Current Issue**: The converter tries to use Stalingrad parsing logic for Crusader files, assuming:
1. Floats at 0x04-0x33 ❌ **WRONG** - Crusader has uint32 values
2. Pointers at 0x40-0x5F ❌ **WRONG** - Crusader has configuration data at 0x60-0x7F
3. Data referenced via file pointers ❌ **WRONG** - Crusader uses fixed offsets

**Required Changes**:
1. **Different header parser** for 0x04-0x17 values
2. **Configuration parameter extraction** from 0x60-0x7F
3. **Fixed offset scanning** instead of pointer-based
4. **Map dimension detection** from configuration parameters
5. **Text extraction** from fixed offsets (0x80+) instead of via pointers

### Recommended Conversion Strategy
1. Parse Crusader header and config (0x00-0x7F)
2. Scan for data blocks at fixed offsets
3. Extract and reorganize data sections
4. Create new D-Day format file with proper pointers
5. Verify map dimensions from Crusader config

