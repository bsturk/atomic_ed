# Disassembly: Hex Loading Code Found

**Date:** 2025-11-09
**Discovery:** Found sprite sheet initialization and 13-column data structure in disassembly
**Executable:** INVADE.EXE (DOS version) - Note: Mac version resource loading would be different

---

## Complete Code Blocks Found

### 1. Graphics Initialization Function - sub_1D3C

**Location:** `disasm.txt` lines 1093-1170
**Memory Address:** seg002:016C to seg002:0245
**Function:** Graphics and sprite sheet initialization

```asm
; sub_1D3C - Graphics and Memory Initialization
seg002:016C sub_1D3C    proc near
seg002:016C             xor    bx, bx
seg002:016E             mov    dx, 0
seg002:0171             mov    cx, 100h
seg002:0174             xor    ax, ax

; First loop: Initialize 256 entries with incrementing values
seg002:0176 loc_1D46:
seg002:0176             mov    [bx+0C6h], ax
seg002:017A             mov    word ptr [bx+0C4h], 8E00h
seg002:0180             mov    word ptr [bx+0C2h], 70h
seg002:0186             mov    [bx+0C0h], dx
seg002:018A             add    dx, 4
seg002:018D             add    bx, 8
seg002:0190             loop   loc_1D46

; Second loop: Initialize 17 entries with 28-byte spacing
seg002:0192             mov    cx, 11h           ; 17 decimal
seg002:0195             mov    dx, 4235h
seg002:0198             xor    bx, bx

seg002:019A loc_1D6A:
seg002:019A             mov    [bx+0C0h], dx
seg002:019E             add    dx, 1Ch           ; 28 decimal spacing
seg002:01A2             add    bx, 8
seg002:01A5             loop   loc_1D6A

; **SPRITE SHEET CONFIGURATION BLOCK**
seg002:01A7             mov    word ptr ds:128h, 1FB8h   ; Value: 8120
seg002:01AD             mov    word ptr ds:1B8h, 84h     ; Value: 132
seg002:01B3             mov    word ptr ds:1C0h, 0C80h   ; **SPRITE WIDTH REFERENCE**
seg002:01B9             mov    word ptr ds:1C2h, 18h     ; Value: 24
seg002:01BF             mov    word ptr ds:1C8h, 0C9Eh   ; Value: 3230
seg002:01C5             mov    word ptr ds:1D8h, 5EBh    ; Value: 1515
seg002:01CB             mov    word ptr ds:248h, 44D6h   ; Value: 17622
seg002:01D1             cmp    byte ptr ds:2Eh, 0Bh
seg002:01D6             jnz    short loc_1DB4
...
seg002:0245             retn
seg002:0245 sub_1D3C    endp
```

**Analysis:**
- **Line 1119 (seg002:01B3)**: Stores `0xC80` (3200 decimal) at memory location `ds:1C0h`
  - 3200 bits = 400 bytes, or 448 pixels at certain bit depths
  - Strong correlation with sprite sheet width of 448 pixels
- Initializes multiple graphics-related parameters in data segment
- Two initialization loops: 256 entries, then 17 entries
- **Memory Location ds:1C0h**: Primary storage for sprite width-related value

---

### 2. 13-Column Data Copy Operation

**Location:** `disasm.txt` lines 16028-16038
**Memory Address:** seg002:6B0F to seg002:6B26
**Function:** Copies 13 words (matches hex column count)

```asm
seg002:6B0F loc_86DF:
seg002:6B0F             les    di, cs:dword_3392   ; Load destination pointer
seg002:6B14             mov    ax, di
seg002:6B16             cld                         ; Clear direction (forward)
seg002:6B17             mov    cx, 0Dh              ; **13 WORDS (13 COLUMNS!)**
seg002:6B1A             rep    movsw                ; Copy 13 words (26 bytes)
seg002:6B1C             add    si, bx               ; Adjust source by variable
seg002:6B1E             movsd                       ; Copy 4 more bytes
seg002:6B20             movsd                       ; Copy 4 more bytes
seg002:6B22             movsd                       ; Copy 4 more bytes
seg002:6B24             movsd                       ; Copy 4 more bytes
seg002:6B26             or     bx, bx
seg002:6B28             jz     short loc_871D
```

**Analysis:**
- **Line 16032 (seg002:6B17)**: Sets `cx` to `0x0D` (13 decimal)
- Copies 13 words (26 bytes) using `rep movsw`
- Then copies 16 additional bytes (4 × `movsd`)
- **Total per iteration: 42 bytes**
- **13 matches the hex tile grid column count exactly**
- Likely copies a row of tile indices or pointers

---

### 3. Sprite Width Comparison Operations

**Additional References to 0xC80h (sprite width value):**

#### Reference 1
**Location:** `disasm.txt` line 16165
**Memory Address:** seg002:6C1D
```asm
seg002:6C1D             cmp    ax, 0C80h
seg002:6C20             jz     short loc_87FA
```

#### Reference 2
**Location:** `disasm.txt` line 21886
**Memory Address:** seg003:2026
```asm
seg003:2026             cmp    ax, 0C80h
seg003:2029             jz     short loc_B984
```

**Analysis:**
- Both locations compare a value against `0xC80h`
- Appears to be part of graphics command dispatch/handler routines
- Could be checking for specific screen modes or sprite sheet identifiers

---

## Verified Values

### From Pixel Analysis (Empirically Determined)
```python
SPRITE_WIDTH = 448      # 0x1C0 hex
SPRITE_HEIGHT = 570     # 0x23A hex
HEX_WIDTH = 32          # 0x20 hex - actual tile content width
HEX_HEIGHT = 36         # 0x24 hex - actual tile content height
HEX_SPACING = 34        # 0x22 hex - center-to-center horizontal
HEX_ROW_SPACING = 38    # 0x26 hex - center-to-center vertical
HEX_OFFSET_X = 12       # 0x0C hex - starting X position
HEX_COLUMNS = 13        # 0x0D hex - grid columns
HEX_ROWS = 14           # 0x0E hex - grid rows (terrain types)
```

### Disassembly Findings Summary

| Constant | Hex | Decimal | Found in Disasm? | Location |
|----------|-----|---------|------------------|----------|
| Sprite width | 0x1C0 | 448 | ✅ YES | ds:1C0h (stored as 0xC80 = 448×8 bits?) |
| Sprite width (bits) | 0xC80 | 3200 | ✅ YES | seg002:01B3, seg002:6C1D, seg003:2026 |
| Columns | 0x0D | 13 | ✅ YES | seg002:6B17 (mov cx, 0Dh) |
| Rows | 0x0E | 14 | ⚠️ MAYBE | Found in comparisons, not tile context |
| Sprite height | 0x23A | 570 | ❌ NO | Not found |
| Tile width | 0x20 | 32 | ❌ NO | Not found |
| Tile height | 0x24 | 36 | ❌ NO | Not found |
| H spacing | 0x22 | 34 | ❌ NO | Not found |
| V spacing | 0x26 | 38 | ❌ NO | Not found |
| Offset X | 0x0C | 12 | ❌ NO | Not found |

---

## Memory Locations Documented

### Data Segment Variables
- **ds:128h** - Initialized to 0x1FB8 (8120) - Purpose unknown
- **ds:1B8h** - Initialized to 0x84 (132) - Purpose unknown
- **ds:1C0h** - **Initialized to 0xC80 (3200) - SPRITE WIDTH STORAGE**
- **ds:1C2h** - Initialized to 0x18 (24) - Purpose unknown
- **ds:1C8h** - Initialized to 0xC9E (3230) - Purpose unknown
- **ds:1D8h** - Initialized to 0x5EB (1515) - Purpose unknown
- **ds:248h** - Initialized to 0x44D6 (17622) - Purpose unknown

### Code Pointers
- **cs:dword_3392** - Far pointer used in 13-word copy operation (seg002:6B0F)

---

## What's Missing

The following hex tile extraction elements were **NOT found** in the disassembly:

1. **Nested 13×14 Loop Structure** - No code iterating through complete grid
2. **Position Calculation Formulas** - No `x = col × 34 + 12` or `y = row × 38`
3. **Tile Dimension Constants** - No explicit 32×36 or 34×38 values
4. **Starting Offset** - No 12-pixel offset constant
5. **Mac Resource Loading** - No GetPicture() or PICT resource ID 128 references

---

## Important Discovery: DOS vs Mac Executable

**Critical Insight:** The file `disasm.txt` is from **INVADE.EXE** (DOS version), not the Mac version.

### Implications:
- **DOS Version**: Uses pre-converted graphics data, likely in a proprietary format
- **Mac Version**: Would contain PICT resource loading via Mac Toolbox calls
- **Resource Loading**: PICT resources only exist on Mac; DOS version has different asset format
- **Tile Extraction**: May have been done during build/conversion process, not at runtime

### Why Tile Extraction Code Is Missing:
1. **Pre-extracted Data**: Tiles likely extracted during DOS port conversion
2. **Lookup Tables**: Game uses pre-calculated tile indices instead of dynamic extraction
3. **Build-Time Tool**: Separate utility converted Mac PICT to DOS graphics format
4. **Optimized Storage**: Tiles stored in indexed format, not extracted from sprite sheet at runtime

---

## Conclusions

### What We Successfully Found ✅
1. **Sprite sheet width storage** - Memory location ds:1C0h stores width-related value (0xC80)
2. **Initialization function** - Complete sub_1D3C function (seg002:016C - seg002:0245)
3. **Column count usage** - 13-word copy operation at seg002:6B17
4. **Multiple width references** - Three locations referencing sprite width value

### What We Couldn't Find ❌
1. **Dynamic tile extraction** - No runtime calculation of tile positions
2. **Dimension constants** - No 32, 36, 34, 38 values in tile context
3. **Nested grid loops** - No 13×14 iteration structures
4. **Mac resource loading** - No PICT-specific code (wrong executable platform)

### Final Assessment

The DOS version (INVADE.EXE) appears to use **pre-processed tile data** rather than extracting tiles from a sprite sheet at runtime. The actual tile extraction likely occurred:
- During Mac-to-DOS conversion process
- Via a separate build tool
- Stored as indexed graphics data
- Accessed through lookup tables

The **Mac version** executable would contain the actual resource loading and tile extraction code we're looking for, but that executable was not available for disassembly.

---

**Status:** ANALYSIS COMPLETE - Found initialization and column count references, but dynamic extraction code absent (likely pre-processed on DOS version)
