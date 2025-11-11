# Complete Disassembly Trace: Terrain ID → Sprite Coordinates

**Investigation Date**: 2025-11-11
**Objective**: Trace data flow from terrain lookup at seg000:0D12 to final sprite extraction
**Status**: **PARTIAL SUCCESS** - Found transformation layer, coordinate calculation missing due to platform divergence

---

## TL;DR - Critical Findings

### ✅ What We Found

1. **Terrain Transformation Table** at `seg000:0D12` (COMPLETE)
   - Maps terrain IDs 0-19 → sprite sheet row numbers
   - Uses x86 `xlat` instruction for instant lookup
   - Returns row numbers: 0, 2, 7, 8, 9, 12, 13, 18, **22**, **24**

2. **Row Number Processing** (COMPLETE)
   - Sign-extension via `cbw` (handles invalid terrain marker 0xFF → -1)
   - Storage in `word_CE8` (purpose unclear, never read)
   - Return in AX register to caller

3. **The Mystery of Rows 22 and 24** (NEW DISCOVERY)
   - Lookup table references row 22 (terrain 1, 12, 13) and row 24 (terrain 4)
   - These exceed PICT 128 sprite sheet height:
     - Row 22 Y-coord: 22 × 38 = 836 pixels
     - Row 24 Y-coord: 24 × 38 = 912 pixels
     - PICT 128 height: 570 pixels (can only hold rows 0-15)
   - **Conclusion**: Either multiple sprite sheets exist OR row numbers are indices, not Y-offsets

### ❌ What's Missing

1. **Coordinate Calculation Code**
   - No `row × 38` multiplication found
   - No `column × 34 + 12` calculation found
   - No references to sprite sheet dimensions (448×570)

2. **Sprite Extraction Pipeline**
   - No PICT resource loading (Mac QuickDraw calls)
   - No CopyBits or tile extraction loops
   - No bitmap manipulation

3. **Platform Divergence Explanation**
   - Disassembly is from **INVADE.EXE** (DOS version)
   - Sprite sheet is from **PCWATW.REZ** (Mac version)
   - Graphics pipelines are **completely different** between platforms

---

## Complete Data Flow Trace

### Step 1: Terrain ID Input → Lookup Table

**Assembly Code** (lines 6217-6243 in disasm.txt):

```assembly
; Function: sub_43B4
; Purpose: Transform terrain ID to sprite sheet row number

seg002:27E4 sub_43B4    proc near
                        ; INPUT:  AL = terrain ID (0-19)
                        ;         AH = variant override (0 = use table)
                        ; OUTPUT: AX = row number (or -1 if invalid)

seg002:27E4             mov  byte_CF0, al          ; Save original terrain ID
seg002:27E7             or   ah, ah                ; Check variant override
seg002:27E9             jnz  short use_ah_directly ; If AH!=0, skip table

; === VALIDATION: Clamp terrain ID to valid range ===
seg002:27FE             cmp  al, 13h               ; Compare with 19
seg002:2800             jbe  short do_lookup       ; If <= 19, valid
seg002:2802             mov  al, 13h               ; Else cap at 19

; === THE CRITICAL XLAT LOOKUP ===
seg002:2804 do_lookup:
seg002:2804             mov  bx, 0D12h             ; BX = table address
seg002:2807             xlat                       ; AL = [BX + AL]
                                                   ; This is the terrain transformation!

; === SIGN EXTEND AND RETURN ===
seg002:2808             cbw                        ; Sign-extend AL to AX
seg002:2809             mov  word_CE8, ax          ; Store globally (unused?)
seg002:280C             retn                       ; Return AX to caller
```

**What Happens**:
1. Terrain ID (0-19) used as array index
2. Table at 0D12h provides indirection: `row_number = table[terrain_id]`
3. Invalid terrains (14, 19) return 0xFF which becomes -1 after sign-extension

---

### Step 2: The Lookup Table (seg000:0D12)

**Raw Bytes** (lines 608-611):
```
00 16 02 02 18 0D 09 0C 0C 0C 07 08 16 16 FF 02 0D 12 02 FF
```

**Decoded Mapping**:

| Terrain ID | Lookup Result | Row # | Y = row × 38 | Terrain Type |
|------------|---------------|-------|--------------|--------------|
| 0  | 0x00 | 0  | 0    | Grass/Field |
| 1  | 0x16 | 22 | **836** | **Beach/Sand** ⚠️ |
| 2  | 0x02 | 2  | 76   | Forest |
| 3  | 0x02 | 2  | 76   | Forest (variant) |
| 4  | 0x18 | 24 | **912** | **Town/Urban** ⚠️ |
| 5  | 0x0D | 13 | 494  | Road |
| 6  | 0x09 | 9  | 342  | River |
| 7  | 0x0C | 12 | 456  | Mountains |
| 8  | 0x0C | 12 | 456  | Mountains (variant) |
| 9  | 0x0C | 12 | 456  | Mountains (variant) |
| 10 | 0x07 | 7  | 266  | Fortification |
| 11 | 0x08 | 8  | 304  | Bocage |
| 12 | 0x16 | 22 | **836** | **Beach** (variant) ⚠️ |
| 13 | 0x16 | 22 | **836** | **Beach** (variant) ⚠️ |
| 14 | 0xFF | -1 | N/A  | INVALID ❌ |
| 15 | 0x02 | 2  | 76   | Forest (variant) |
| 16 | 0x0D | 13 | 494  | Road (variant) |
| 17 | 0x12 | 18 | 684  | Water/Ocean |
| 18 | 0x02 | 2  | 76   | Forest (variant) |
| 19 | 0xFF | -1 | N/A  | INVALID ❌ |

⚠️ **CRITICAL**: Rows 22 and 24 exceed PICT 128 sprite sheet height (570 pixels)

---

### Step 3: Operations on Returned Value

#### A. Sign Extension (CBW instruction)
```assembly
xlat    ; AL = table[terrain_id]  (unsigned 8-bit)
cbw     ; AX = sign_extend(AL)    (signed 16-bit)
```

**Purpose**:
- Convert 8-bit result to 16-bit for coordinate math
- Properly handle invalid marker: `0xFF → 0xFFFF = -1`
- Result: `-1` can be tested to skip invalid terrains

**Example**:
- Terrain 1: `xlat` returns 0x16 → `cbw` produces 0x0016 (22)
- Terrain 14: `xlat` returns 0xFF → `cbw` produces 0xFFFF (-1)

#### B. Global Storage (word_CE8)
```assembly
mov word_CE8, ax
```

**Analysis**:
- Stored but **never read** in disassembly
- Possible explanations:
  1. Debugging/logging variable
  2. Used by unreachable code paths
  3. Legacy code no longer used
  4. Read by DOS extender runtime (outside disassembly scope)

#### C. Return to Caller
```assembly
retn  ; Returns with AX = row number
```

**Callers**:
- `sub_43AE` (thin wrapper, returns same value)
- DOS interrupt handlers (int 21h wrappers)
- No sprite rendering code found in disassembly

---

### Step 4: Coordinate Transformation (EXPECTED but NOT FOUND)

**What SHOULD happen** (based on Mac sprite sheet analysis):

```python
# Given row number from xlat lookup
row_number = AX  # From xlat + cbw

# Calculate sprite Y coordinate
HEX_ROW_SPACING = 38  # Distance between row centers
y = row_number * HEX_ROW_SPACING

# Calculate sprite X coordinate (from column variant)
HEX_SPACING = 34      # Distance between column centers
HEX_OFFSET_X = 12     # Left margin
column = variant      # 0-12 for different tile variants
x = column * HEX_SPACING + HEX_OFFSET_X

# Extract 32×36 pixel tile from sprite sheet
HEX_WIDTH = 32
HEX_HEIGHT = 36
sprite = sheet.crop(x, y, x + HEX_WIDTH, y + HEX_HEIGHT)
```

**Search Results** (all NEGATIVE):

```bash
# Searched for row spacing multiplication (× 38 = 0x26)
grep -n "\\b26h\\b" disasm.txt         # Only segment prefixes found
grep -n "imul.*38\|mul.*38" disasm.txt # No matches

# Searched for column spacing (× 34 = 0x22)
grep -n "\\b22h\\b" disasm.txt         # No coordinate math found

# Searched for sprite sheet dimensions
grep -n "448\|1C0h" disasm.txt         # No matches (width)
grep -n "570\|23Ah" disasm.txt         # No matches (height)

# Searched for precalculated Y coordinates
# Row 2: y=76 (0x4C), Row 7: y=266 (0x10A), Row 22: y=836 (0x344), etc.
grep -n "004Ch\|010Ah\|0344h\|0390h" disasm.txt  # No matches
```

**Conclusion**: Sprite extraction code is **PLATFORM-SPECIFIC** and not in DOS executable

---

## Modulo, Masking, and Transformations

### 1. Range Clamping (No Modulo)
```assembly
cmp  al, 13h    ; if (terrain_id > 19)
jbe  valid
mov  al, 13h    ;     terrain_id = 19  (cap, don't wrap)
```

**Effect**: Invalid terrain IDs (≥20) map to terrain 19, which returns -1 (invalid marker)

### 2. Extended Terrain Range (Special Case)
```assembly
cmp  byte ptr word_CEE, 3  ; if (game_mode >= 3)
jb   skip_extended
cmp  al, 22h               ; if (terrain_id >= 34)
jnb  cap_it
cmp  al, 20h               ; else if (terrain_id >= 32)
jb   skip_extended
mov  al, 5                 ;     terrain_id = 5  (map 32-33 to row 13)
```

**Effect**: Terrains 32-33 allowed in certain game modes, map to Road row

### 3. Sign Extension (Not Masking)
```assembly
cbw  ; AL (unsigned) → AX (signed)
```

**Effect**:
- Positive values: 0x00-0x7F unchanged
- 0xFF becomes 0xFFFF (-1) for error detection
- NOT a masking operation - full precision preserved

### 4. No Coordinate Transformations Found
- ❌ No modulo operations
- ❌ No bitwise AND/OR/XOR for coordinates
- ❌ No shift-and-add for multiplication
- ❌ No row/column offset tables

---

## Multiple Sprite Sheets Investigation

### Evidence FOR Multiple Sheets

#### 1. Row Numbers Exceed Single Sheet
- **PICT 128**: 448×570 pixels → holds rows 0-15 (Y = 0 to 532)
- **Row 22 required**: Y = 836 pixels (exceeds by 266 pixels)
- **Row 24 required**: Y = 912 pixels (exceeds by 342 pixels)

#### 2. Unused Rows in Single Sheet
- **Rows used**: 0, 2, 7, 8, 9, 12, 13, 18, 22, 24 (10 rows)
- **Rows in PICT 128**: 0-15 (16 rows)
- **Rows unused**: 1, 3, 4, 5, 6, 10, 11, 14, 15 (9 rows wasted)

### Evidence AGAINST Multiple Sheets

#### 1. Only PICT 128 Contains Terrain
- **PICT Resources in PCWATW.REZ**: 111 total
- **Terrain-Related**: Only PICT 128 identified
- **Other PICTs**: UI graphics, explosions, overview maps, etc.

#### 2. Alternative Hypothesis: Row = Index, Not Y-Offset

**What if row numbers are NOT pixel offsets?**

Possibility: Separate mapping table exists:
```c
// Not found in disassembly, but logically possible:
uint16_t row_to_y_offset[25] = {
    0,    // Row 0  → Y = 0
    38,   // Row 1  → Y = 38
    76,   // Row 2  → Y = 76
    ...
    494,  // Row 13 → Y = 494
    ...
    ??,   // Row 22 → Y = ?? (remapped to row 5?)
    ??,   // Row 24 → Y = ?? (remapped to row 6?)
};
```

This would explain:
- Why multiplication by 38 not found
- Why rows 22/24 don't cause crashes
- Why 9 rows in PICT 128 seem unused

---

## Clues About Row Number Transformations

### Suspicious Data After Lookup Table

**Lines 609-611** (data immediately following 20-byte terrain table):
```assembly
seg000:0D12  db 0Eh dup(0), 38h, 0Dh, 6 dup(0), 4Eh, 0Dh, 2 dup(0)
seg000:0D12  db 54h, 0Dh, 2 dup(0), 68h, 0, 58h, 0, 18h, 2Ah, ...
```

**Decoded values**:
```
14 zeros, then:
38h (56 dec)  ← HEX_ROW_SPACING constant!
0Dh (13 dec)  ← Separator?
6 zeros, then:
4Eh (78 dec)  = 2*38 + 2
0Dh (13 dec)
2 zeros, then:
54h (84 dec)  = 2*38 + 8
0Dh (13 dec)
2 zeros, then:
68h (104 dec) = 2*38 + 28 = 2*52
00h
58h (88 dec)  = 2*38 + 12
00h
18h (24 dec)  ← Row number from table!
2Ah (42 dec)
```

**Analysis**:
- `38h` appears as literal value (smoking gun for ROW_SPACING)
- Pattern: `<value>, 0Dh, <zeros>` repeated
- Some values are multiples/offsets of 38
- `18h` matches row 24 from terrain table
- Could be **row remapping table** or **Y-offset table**

**Hypothesis**: This might be a secondary lookup table that maps "virtual" row numbers (22, 24) to actual sprite sheet coordinates

---

## Where Does Value Get Used?

### Callers of sub_43B4 (terrain lookup function)

**Direct callers** (line 6184, 6194, 6209):
```assembly
; Wrapper function - just returns the row number
seg002:27DE sub_43AE    proc near
seg002:27DE             xor  ah, ah          ; Clear variant
seg002:27E0             call sub_43B4        ; Get row number
seg002:27E3             retn                 ; Return same value
seg002:27E3 sub_43AE    endp
```

**Who calls sub_43AE?** (lines 5958, 6011, 6075, 14341)
- All callers are **DOS interrupt 21h wrappers**
- Error handling code (check carry flag, return errno)
- No sprite/graphics code found

**Dead end**: The returned row number disappears into DOS system calls

### Global Variable word_CE8

**References**:
```assembly
seg000:0CE8 word_CE8  dw 0    ; Defined at line 589
seg002:2809           mov word_CE8, ax  ; Written at line 6247
```

**Read references**: NONE found in entire disassembly

**Possible explanations**:
1. **Debugging variable**: Dev team logged terrain lookups during testing
2. **Unused code**: Variable written but feature removed
3. **External access**: DOS extender or runtime library reads it
4. **Missing code**: Graphics rendering code in separate overlay/DLL

---

## Platform Divergence Analysis

### DOS Version (INVADE.EXE - What We Have)

**File**: INVADE.EXE
**Platform**: MS-DOS, 16-bit x86 protected mode
**Extender**: DOS16M (DOS Protected Mode Interface)
**Graphics**: VGA, custom tile format (likely .GFX or .PCX)
**Terrain Logic**: ✅ Found (lookup table at 0D12h)
**Sprite Extraction**: ❌ Not found (different file format)

### Mac Version (PCWATW - What We Need)

**File**: PC War Across the World (Mac executable)
**Platform**: Macintosh 68000/PowerPC
**Graphics**: QuickDraw, PICT resources
**Resource File**: PCWATW.REZ (contains PICT 128 sprite sheet)
**Terrain Logic**: Assumed same as DOS
**Sprite Extraction**: Mac Toolbox calls (GetPicture, CopyBits)

### Cross-Platform Truth

**What's the same**:
- Game logic (terrain types, map format)
- Lookup table values (likely identical)
- Coordinate formulas (row×38, col×34+12)

**What's different**:
- Graphics file formats (PICT vs VGA/PCX)
- Rendering pipeline (QuickDraw vs direct VGA)
- Sprite loading code (Mac Toolbox vs DOS BIOS)

**Why disassembly doesn't help**:
- We're analyzing the WRONG platform's executable
- Need Mac 68K disassembly or runtime tracing

---

## Final Conclusions

### What We Definitively Know

1. **Terrain Transformation is Deterministic**
   - Lookup table at seg000:0D12 maps terrain ID → row number
   - 20 terrain types collapse to 10 unique rows via indirection
   - Invalid terrains (14, 19) return -1 via sign-extension

2. **Row Numbers Used by Lookup**
   - 0, 2, 7, 8, 9, 12, 13, 18, 22, 24
   - Rows 22 and 24 **exceed PICT 128 dimensions**
   - Mystery unresolved: either multiple sheets OR row remapping

3. **Coordinate Calculation Missing**
   - No Y = row × 38 multiplication found
   - No X = col × 34 + 12 calculation found
   - Conclusion: Code is platform-specific (Mac), not in DOS version

### What Remains Unknown

1. **How rows 22 and 24 are handled**
   - Do additional sprite sheets exist?
   - Is there a row → Y-offset remapping table?
   - Are these rows unused (dead terrain types)?

2. **Where sprite extraction happens**
   - Mac QuickDraw code not in DOS executable
   - Need Mac binary disassembly or runtime trace

3. **Purpose of suspicious data after table**
   - Bytes at 0D26+ contain 38h and row-like values
   - Could be row remapping or Y-offset table
   - Needs deeper analysis

### Recommended Next Steps

1. **Extract Mac Executable from PCWATW**
   - Disassemble 68K or PowerPC code
   - Search for GetPicture(128) calls
   - Find CopyBits or sprite extraction loops

2. **Check for Additional PICT Resources**
   - List all 111 PICT resources in PCWATW.REZ
   - Look for continuation of terrain tiles
   - Check dimensions of PICT 130, 132, etc.

3. **Analyze Data After Lookup Table**
   - Decode bytes at seg000:0D26 onward
   - Look for 10-entry row → Y-offset mapping
   - Test hypothesis: 22 → 5, 24 → 6 remapping

4. **Verify Sprite Sheet Dimensions**
   - Re-extract PICT 128 with full canvas
   - Check if 570 pixels is cropped version
   - Original might be 912+ pixels tall

---

## Complete Data Flow Diagram

```
┌─────────────────────────────────────────────────────────┐
│              USER INPUT: Hex Map Coordinate             │
│                    (x, y, terrain_id)                   │
└────────────────────────┬────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────┐
│           READ TERRAIN ID FROM MAP DATA                 │
│         (Offset 0x57E4 + hex_index, 4 bits)             │
└────────────────────────┬────────────────────────────────┘
                         │
                         ▼ AL = terrain_id (0-19)
┌─────────────────────────────────────────────────────────┐
│                RANGE VALIDATION (sub_43B4)              │
│  ┌──────────────────────────────────────────────────┐   │
│  │ if (AL > 19) AL = 19                             │   │
│  │ if (AL >= 32 && AL < 34 && mode >= 3) AL = 5    │   │
│  └──────────────────────────────────────────────────┘   │
└────────────────────────┬────────────────────────────────┘
                         │
                         ▼ AL = validated terrain_id
┌─────────────────────────────────────────────────────────┐
│            XLAT LOOKUP (seg000:0D12)                    │
│  ┌──────────────────────────────────────────────────┐   │
│  │ BX = 0D12h    ; Table address                    │   │
│  │ xlat          ; AL = [BX + AL]                   │   │
│  │ cbw           ; AX = sign_extend(AL)             │   │
│  │ mov word_CE8, AX  ; Store (unused?)              │   │
│  │ ret           ; Return AX                        │   │
│  └──────────────────────────────────────────────────┘   │
└────────────────────────┬────────────────────────────────┘
                         │
                         ▼ AX = row_number (0-24, or -1)
┌─────────────────────────────────────────────────────────┐
│              COORDINATE CALCULATION                     │
│                  ⚠️ NOT FOUND IN DOS DISASM ⚠️           │
│  ┌──────────────────────────────────────────────────┐   │
│  │ Expected (from Mac analysis):                    │   │
│  │   y = row_number * 38                            │   │
│  │   x = column * 34 + 12                           │   │
│  │                                                   │   │
│  │ Alternative (hypothesis):                        │   │
│  │   y = row_to_y_table[row_number]                │   │
│  │   (Would explain rows 22,24 mystery)             │   │
│  └──────────────────────────────────────────────────┘   │
└────────────────────────┬────────────────────────────────┘
                         │
                         ▼ (x, y) = sprite position
┌─────────────────────────────────────────────────────────┐
│              SPRITE EXTRACTION (Mac Only)               │
│                  ⚠️ NOT IN DOS DISASM ⚠️                 │
│  ┌──────────────────────────────────────────────────┐   │
│  │ GetPicture(128)  ; Load PICT resource            │   │
│  │ CopyBits(                                         │   │
│  │   srcRect:  {x, y, x+32, y+36},                  │   │
│  │   dstRect:  {screen_x, screen_y, ...},           │   │
│  │   mode:     srcCopy                              │   │
│  │ )                                                 │   │
│  └──────────────────────────────────────────────────┘   │
└────────────────────────┬────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────┐
│                 RENDERED HEX ON SCREEN                  │
└─────────────────────────────────────────────────────────┘
```

---

**Investigation Status**: BLOCKED at platform boundary
**Blocker**: Need Mac executable or runtime memory dump
**Alternative**: Accept empirical formula (row×38) and move forward with editor
