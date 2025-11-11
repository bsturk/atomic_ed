# Terrain Lookup Data Flow - Complete Disassembly Trace

**Date**: 2025-11-11
**Source**: INVADE.EXE (MS-DOS version) disassembly
**Status**: PARTIAL - DOS version differs from Mac sprite extraction

## Executive Summary

This document traces the complete data flow from terrain ID input through the xlat lookup table to understand how terrain types map to sprite coordinates. The analysis reveals the **transformation layer** but encounters a **platform divergence** issue.

### Key Finding: Platform Divergence

- **Disassembly Source**: INVADE.EXE (MS-DOS executable, x86 16-bit protected mode)
- **Sprite Sheet Source**: PCWATW.REZ (Macintosh resource fork, PICT format)
- **Implication**: DOS version may use **different graphics pipeline** than Mac version

---

## Data Flow Trace - Part 1: Terrain ID → Row Number

### Function: sub_43B4 (lines 6217-6254)

**Purpose**: Transform terrain ID to sprite sheet row number

**Input**:
- AL = terrain type ID (0-19)
- AH = variant selector (0 = use table, non-zero = use AH directly)

**Processing Logic**:

```assembly
seg002:27E4 sub_43B4    proc near
seg002:27E4             mov  byte_CF0, al     ; Save original terrain ID
seg002:27E7             or   ah, ah           ; Check variant selector
seg002:27E9             jnz  short loc_43DD   ; If AH != 0, use AH as row

; Terrain type range validation
seg002:27EB             cmp  byte ptr word_CEE, 3
seg002:27F0             jb   short loc_43CE
seg002:27F2             cmp  al, 22h          ; Check if terrain >= 34
seg002:27F4             jnb  short loc_43D2   ; If so, cap it
seg002:27F6             cmp  al, 20h          ; Check if terrain >= 32
seg002:27F8             jb   short loc_43CE
seg002:27FA             mov  al, 5            ; Map terrain 32-33 to row 5

seg002:27FE loc_43CE:
seg002:27FE             cmp  al, 13h          ; Compare with 19
seg002:2800             jbe  short loc_43D4   ; Valid if <= 19

seg002:2802 loc_43D2:
seg002:2802             mov  al, 13h          ; Cap at terrain ID 19

; THE CRITICAL LOOKUP (line 6242-6243)
seg002:2804 loc_43D4:
seg002:2804             mov  bx, 0D12h        ; Load table address
seg002:2807             xlat                  ; AL = table[AL] - LOOKUP HAPPENS HERE

; Sign-extend and return (lines 6246-6248)
seg002:2808 loc_43D8:
seg002:2808             cbw                   ; Sign-extend AL to AX
seg002:2809             mov  word_CE8, ax     ; Store in global variable
seg002:280C             retn                  ; Return with row number in AX

seg002:280D loc_43DD:   ; Alternate path for direct row selection
seg002:280D             mov  al, ah           ; Use AH as row number
seg002:280F             jmp  short loc_43D8   ; Jump to sign-extend & return
```

**Output**:
- AX = sprite sheet row number (-1 for invalid terrains 14 and 19)
- word_CE8 = same value stored globally

---

## The Lookup Table (seg000:0D12)

**Location**: Lines 608-611
**Size**: 20 bytes (indices 0-19 for terrain IDs)

### Raw Assembly
```assembly
seg000:0D12  db 0, 16h, 2 dup(2), 18h, 0Dh, 9, 3 dup(0Ch), 7, 8, 2 dup(16h)
seg000:0D12  db 0FFh, 2, 0Dh, 12h, 2, 0FFh, 0Eh dup(0), 38h, 0Dh, 6 dup(0)
seg000:0D12  db 4Eh, 0Dh, 2 dup(0), 54h, 0Dh, 2 dup(0), 68h, 0, 58h
seg000:0D12  db 0, 18h, 2Ah, 2 dup(0), 18h, 7 dup(0), 0FFh, 7, 4 dup(0)
```

### Decoded Table (Complete 20-Entry Mapping)

| Index | Hex | Dec | After cbw | Y = row * 38 | Terrain Type |
|-------|-----|-----|-----------|--------------|--------------|
| 0  | 0x00 | 0   | 0    | 0    | Grass/Field |
| 1  | 0x16 | 22  | 22   | 836  | Beach/Sand |
| 2  | 0x02 | 2   | 2    | 76   | Forest |
| 3  | 0x02 | 2   | 2    | 76   | Forest (variant) |
| 4  | 0x18 | 24  | 24   | 912  | Town/Urban |
| 5  | 0x0D | 13  | 13   | 494  | Road |
| 6  | 0x09 | 9   | 9    | 342  | River |
| 7  | 0x0C | 12  | 12   | 456  | Mountains |
| 8  | 0x0C | 12  | 12   | 456  | Mountains (variant) |
| 9  | 0x0C | 12  | 12   | 456  | Mountains (variant) |
| 10 | 0x07 | 7   | 7    | 266  | Fortification |
| 11 | 0x08 | 8   | 8    | 304  | Bocage |
| 12 | 0x16 | 22  | 22   | 836  | Beach (variant) |
| 13 | 0x16 | 22  | 22   | 836  | Beach (variant) |
| 14 | 0xFF | 255 | -1   | N/A  | **INVALID** |
| 15 | 0x02 | 2   | 2    | 76   | Forest (variant) |
| 16 | 0x0D | 13  | 13   | 494  | Road (variant) |
| 17 | 0x12 | 18  | 18   | 684  | Water/Ocean |
| 18 | 0x02 | 2   | 2    | 76   | Forest (variant) |
| 19 | 0xFF | 255 | -1   | N/A  | **INVALID** |

### Transformation Analysis

**Unique row values**: 0, 2, 7, 8, 9, 12, 13, 18, 22, 24 (10 distinct rows)

**Note**: Table provides INDIRECTION - not all terrain IDs map to unique rows:
- Terrain 2, 3, 15, 18 → Row 2 (Forest variants)
- Terrain 7, 8, 9 → Row 12 (Mountain variants)
- Terrain 1, 12, 13 → Row 22 (Beach variants)
- Terrain 5, 16 → Row 13 (Road variants)

---

## Data Flow Trace - Part 2: Row Number → Sprite Coordinates

### Problem: Missing DOS Graphics Code

**Search attempts** for coordinate calculation:
1. ❌ No multiplication by 38 (0x26) found
2. ❌ No precalculated Y-coordinate tables (checked hex values: 0x004C, 0x010A, 0x0130, 0x0156, 0x01C8, 0x01EE, 0x02AC, 0x0344, 0x0390)
3. ❌ No references to sprite sheet dimensions (448×570)
4. ❌ No column spacing calculations (multiply by 34, add 12)
5. ❌ word_CE8 only written, never read in the disassembly

**Searched for**:
```bash
# Row spacing constant (38 decimal = 0x26 hex)
grep -n "\\b26h\\b" disasm.txt  # Found only segment prefixes (ES:), not values

# Column spacing (34 decimal = 0x22 hex)
grep -n "\\b22h\\b" disasm.txt  # No coordinate calculations found

# Sprite sheet dimensions
grep -n "448\\|1C0h" disasm.txt  # No matches
grep -n "570\\|23Ah" disasm.txt  # No matches

# Shift-and-add for Y = row * 38 = row * 32 + row * 4 + row * 2
grep -n "shl.*5\\|shl.*6" disasm.txt  # Found unrelated code
```

### Why the Coordinate Code is Missing

**Hypothesis**: DOS version uses **entirely different graphics subsystem**

1. **Platform Evidence**:
   - Disassembly: `INVADE.EXE` (MS-DOS, x86 protected mode with DOS16M extender)
   - Sprite Sheet: `PCWATW.REZ` (Macintosh resource fork, PICT format)

2. **Graphics Pipeline Differences**:
   - **Mac**: Uses QuickDraw, PICT resources, direct pixel manipulation
   - **DOS**: Likely uses VGA modes, different tile storage format (possibly separate .GFX or .PCX files)

3. **Code Architecture**:
   - Terrain lookup table (0D12h) is **game logic** (platform-independent)
   - Sprite extraction is **graphics code** (platform-specific)

---

## Expected Coordinate Calculations (Mac Version)

Based on empirical analysis of PCWATW.REZ sprite sheet:

### Sprite Sheet Structure (Mac PICT Resource 128)
```
Dimensions: 448 × 570 pixels
Format: 8-bit indexed color (256-color palette)
Grid: 14 rows × 13 columns of hex tiles
```

### Extraction Formula
```python
# Given: row number from xlat, column variant (0-12)
HEX_WIDTH = 32         # Actual tile content width
HEX_HEIGHT = 36        # Actual tile content height
HEX_SPACING = 34       # Column spacing (center-to-center)
HEX_ROW_SPACING = 38   # Row spacing (center-to-center)
HEX_OFFSET_X = 12      # Left margin before first column

# Calculate sprite position
x = column * HEX_SPACING + HEX_OFFSET_X  # = col * 34 + 12
y = row * HEX_ROW_SPACING                # = row * 38

# Extract tile
sprite = sheet.crop(x, y, x + HEX_WIDTH, y + HEX_HEIGHT)
```

### Example: Terrain ID 1 (Beach)
```
Input:  terrain_id = 1, variant_column = 0
Lookup: table[1] = 0x16 = 22
Coords: x = 0 * 34 + 12 = 12
        y = 22 * 38 = 836
Extract: sprite = sheet.crop(12, 836, 44, 872)  # 32×36 tile
```

---

## Operations Performed on Returned Value

### 1. Sign Extension (cbw)
```assembly
xlat           ; AL = table[terrain_id] (unsigned byte)
cbw            ; AX = sign_extend(AL)
```

**Purpose**: Convert 8-bit lookup result to 16-bit for:
- Invalid terrain markers (0xFF → 0xFFFF = -1)
- Compatibility with 16-bit coordinate arithmetic

### 2. Global Storage (word_CE8)
```assembly
mov word_CE8, ax
```

**Purpose**: Unknown (variable is written but never read in disassembly)
**Speculation**: May be debugging aid or unused legacy code

### 3. Return to Caller
```assembly
retn  ; Returns with AX = row number
```

**Purpose**: Caller receives row number for further processing

---

## Modulo, Masking, and Transformations

### Range Clamping
```assembly
cmp al, 13h    ; Compare with 19
jbe valid      ; Jump if terrain_id <= 19
mov al, 13h    ; Otherwise, cap at 19
```

**Effect**: Invalid terrain IDs (≥20) treated as terrain 19 (which maps to 0xFF = invalid)

### Special Case: High Terrain IDs
```assembly
cmp byte ptr word_CEE, 3  ; Check version/mode flag?
jb  skip_special
cmp al, 22h               ; If terrain >= 34 (0x22)
jnb cap_terrain
cmp al, 20h               ; If terrain >= 32 (0x20)
jb  skip_special
mov al, 5                 ; Map terrain 32-33 to row 5
```

**Effect**: Extended terrain range (20-33) if `word_CEE >= 3`
- Terrain 32-33 → Row 5
- Terrain 34+ → Capped to terrain 19 → Row 0xFF (invalid)

### No Coordinate Transformations Found

❌ No modulo operations
❌ No bit masking (AND/OR/XOR for coordinates)
❌ No row*38 multiplication
❌ No column*34 + 12 calculation

**Conclusion**: Coordinate transformation happens **elsewhere** (Mac-specific code, not in DOS disassembly)

---

## Evidence of Multiple Sprite Sheets

### Hints from Lookup Table

**Table shows gaps in row usage**:
- Rows used: 0, 2, 7, 8, 9, 12, 13, 18, 22, 24
- Rows unused: 1, 3, 4, 5, 6, 10, 11, 14, 15, 16, 17, 19, 20, 21, 23

**Sprite sheet has 14 rows total** (0-13 visible in 448×570 image)

**Row 22 and 24 exceed visible sheet!**
- Row 22 * 38 = 836 pixels (sheet height = 570)
- Row 24 * 38 = 912 pixels (sheet height = 570)

### Possible Explanations

1. **Multiple Sprite Sheets**:
   - PICT 128 contains rows 0-13
   - Additional PICT resource(s) contain rows 14-24
   - Game loads multiple sheets and composites them

2. **Overscan/Hidden Data**:
   - PICT resource has larger canvas than visible
   - Rows 14-24 stored below visible area
   - Need to re-extract PICT with full dimensions

3. **Row Number is NOT Y-coordinate**:
   - Row number is an INDEX, not a pixel offset
   - Separate mapping table: row_index → actual_y_offset
   - Would explain why row*38 calculation not found

4. **Platform Difference**:
   - DOS version uses different row numbering
   - Mac version may remap row 22/24 to different rows
   - Lookup table is DOS-specific, Mac has different table

---

## Data Flow Summary

### Complete Trace (as far as traceable in DOS disassembly)

```
┌─────────────────────┐
│  Terrain ID (0-19)  │
│  Variant (column)   │
└──────────┬──────────┘
           │
           v
┌─────────────────────┐
│  Range Validation   │
│  - Cap at 19        │
│  - Special: 32-33→5 │
└──────────┬──────────┘
           │
           v
┌─────────────────────┐
│  XLAT Lookup        │
│  BX = 0D12h         │
│  AL = table[AL]     │
└──────────┬──────────┘
           │
           v
┌─────────────────────┐
│  Sign Extend (cbw)  │
│  AX = row number    │
│  (or -1 if invalid) │
└──────────┬──────────┘
           │
           v
┌─────────────────────┐
│  Store & Return     │
│  word_CE8 = AX      │
│  Return AX          │
└──────────┬──────────┘
           │
           v
┌─────────────────────┐
│   ??? MISSING ???   │
│                     │
│  Expected (Mac):    │
│  Y = row * 38       │
│  X = col * 34 + 12  │
│  Extract 32×36 tile │
└─────────────────────┘
```

### Data Lost at Platform Boundary

**What we know (DOS)**:
- Terrain ID → Row number transformation (COMPLETE)
- Row numbers: 0, 2, 7, 8, 9, 12, 13, 18, 22, 24

**What we don't know (Mac-specific)**:
- How row number becomes Y coordinate
- Where sprite sheet is loaded
- How 32×36 tiles are extracted
- How rows 22 and 24 are accessed (beyond visible sheet)

---

## Recommendations

### 1. Find Mac Disassembly or Binary
- Original Mac executable would show QuickDraw calls
- Search for: GetPicture(128), CopyBits, sprite extraction loops

### 2. Re-extract PICT 128 with Full Canvas
```bash
# Check if PICT resource has more data than extracted
# Current extraction: 448×570
# Needed for row 24: 448×912 minimum
```

### 3. Search for Additional PICT Resources
```bash
# List all PICT resources in PCWATW.REZ
# Check for PICT 129, 130, etc. that might contain rows 14-24
```

### 4. Verify Row Number Semantics
- Test hypothesis: row number is INDEX, not Y-offset
- Search for separate row_offset_table in data segments

### 5. Cross-Reference with Other Scenarios
- Examine different .SCN files to see which terrain IDs are used
- If terrain 1 (row 22) or terrain 4 (row 24) appear, sprite must exist somewhere

---

## Conclusion

### What the Disassembly Reveals

✅ **Terrain Transformation Layer** (COMPLETE):
- Lookup table at seg000:0D12 definitively maps terrain IDs to row numbers
- 20 terrain types (0-19), with 2 invalid (14, 19)
- Indirection allows multiple terrain IDs to share sprite rows

✅ **Validation Logic** (COMPLETE):
- Range checking prevents out-of-bounds access
- Special handling for extended terrain range (32-33)

❌ **Sprite Extraction** (MISSING):
- DOS disassembly does not contain Mac graphics pipeline
- Coordinate calculation (row*38, col*34+12) not found
- Sprite sheet loading code not in INVADE.EXE

### The Mystery of Rows 22 and 24

**Critical Question**: How does the game access sprite rows that exceed the visible sheet height?

**Most Likely**: Multiple PICT resources or larger canvas than extracted

**Action Item**: Re-examine PCWATW.REZ for:
1. Full dimensions of PICT 128
2. Additional PICT resources (129+)
3. Alternative tile storage formats

---

**Next Steps**: Investigate Mac resource fork for complete sprite data and find Mac executable for graphics pipeline code.
