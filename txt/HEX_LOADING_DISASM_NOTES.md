# Hex Tile Loading - Disassembly Analysis

**Date:** 2025-11-09
**Purpose:** Document where and how hex tile images are loaded in the D-Day game executable

---

## Summary

**Status:** Disassembly lacks clear symbolic information for PICT resource loading.

The game uses Mac Toolbox resource manager calls to load PICT resources, but the disassembly (`disasm.txt`) contains raw assembly without symbolic labels for resource loading functions.

---

## Known Facts

### Sprite Sheet Resource
- **Resource Type:** PICT
- **Resource ID:** 128 (0x80 in hex)
- **File:** PCWATW.REZ
- **Extracted as:** scan_width_448.png (448×570 pixels)

### Hex Tile Dimensions (Verified by Pixel Analysis)
```
HEX_WIDTH = 32        # Actual hex content width
HEX_HEIGHT = 36       # Actual hex content height
HEX_SPACING = 34      # 0x22 - Distance between hex centers horizontally
HEX_ROW_SPACING = 38  # 0x26 - Distance between row centers vertically
HEX_OFFSET_X = 12     # 0x0C - Where first hex content starts
```

---

## Expected Mac Toolbox Call Sequence

Based on typical Mac resource loading patterns, the game likely uses:

```c
// 1. Load PICT resource
PicHandle picHandle = GetPicture(128);  // Load PICT resource ID 128

// 2. Draw to offscreen buffer or extract pixels
// Likely using CopyBits or direct pixel manipulation

// 3. Extract individual hex tiles
for (row = 0; row < 14; row++) {
    for (col = 0; col < 13; col++) {
        int x = col * 34 + 12;  // 0x22 spacing + 0x0C offset
        int y = row * 38;       // 0x26 spacing

        // Extract 32×36 pixel tile
        extractTile(x, y, 32, 36);  // 0x20 × 0x24
    }
}
```

---

## Disassembly Search Results

### PICT Resource ID (128 / 0x80)
**Search:** `grep -n "#80h\|,80h\|0x80\|128," disasm.txt`
**Result:** No clear PICT resource loading found with ID 128

### Hex Dimensions
**Search patterns tried:**
- `#22h` (34 decimal - HEX_SPACING)
- `#26h` (38 decimal - HEX_ROW_SPACING)
- `#20h` (32 decimal - HEX_WIDTH)
- `#24h` (36 decimal - HEX_HEIGHT)
- `#0Ch` (12 decimal - HEX_OFFSET_X)
- `1C0h` (448 decimal - sprite width)

**Result:** No obvious matches in mov/add/lea instructions

### Mac Toolbox Functions
**Search:** `GetPicture`, `GetResource`, `CopyBits`, `DrawPicture`
**Result:** No symbolic names in disassembly (raw addresses only)

---

## Why Disassembly Analysis Is Difficult

1. **No Symbolic Information**: The disassembly contains only raw addresses and hex values
2. **Mac Toolbox Calls**: Resource manager calls may be indirect through jump tables
3. **Optimized Code**: Constants may be calculated rather than stored as literals
4. **Packed Data**: Dimensions might be packed into composite values (e.g., 34 << 8 | 38)

---

## Recommended Approach for Finding Loading Code

### 1. Search for Known Memory Patterns
Look for sequences that might represent the sprite sheet dimensions:
```bash
# Width 448 (0x01C0) followed by height 570 (0x023A)
grep -E "1C0.*23A|448.*570" disasm.txt
```

### 2. Look for Loop Counters
The extraction would likely have nested loops for 14 rows × 13 columns:
```bash
# Look for counter values 13 (0x0D) and 14 (0x0E)
grep -n "cmp.*0Dh\|cmp.*0Eh" disasm.txt
```

### 3. Find Rectangle/Bounds Structures
Mac QuickDraw uses Rect structures (top, left, bottom, right):
```bash
# Look for rect with width 34 or height 38
grep -n "22h.*26h\|34.*38" disasm.txt
```

### 4. Trace from Known Entry Points
If map drawing functions are identified, trace backward to find tile loading:
```bash
# Search for rendering/drawing functions
grep -in "draw\|render\|plot\|blit" disasm.txt
```

---

## Alternative Analysis Methods

Since direct disassembly search is inconclusive:

1. **Runtime Analysis**
   - Run game in Mac debugger (SheepShaver + MacsBug)
   - Set breakpoint on GetPicture/GetResource
   - Trace resource loading at runtime

2. **Memory Inspection**
   - Dump game memory while running
   - Search for sprite sheet pixel data
   - Find address where tiles are stored

3. **Resource Fork Analysis**
   - We already extracted PICT_128 successfully
   - Dimensions verified: 448×570 sprite sheet
   - Extraction parameters verified by pixel analysis

4. **Code Pattern Matching**
   - Search for 13×14 loop patterns (tile grid)
   - Look for 34-pixel stride calculations
   - Find 38-pixel row advance logic

---

## Verified Information (From Pixel Analysis)

Even without finding the exact loading code in the disassembly, we have **definitively determined** the correct extraction parameters through empirical pixel-level analysis:

### Sprite Sheet Structure
```
File: extracted_images/scan_width_448.png
Dimensions: 448 × 570 pixels
Format: 8-bit indexed color (256-color palette)
Grid: 14 rows × 13 columns (+ partial row with 3 special tiles)
```

### Extraction Parameters
```python
x = col * 34 + 12    # Column calculation
y = row * 38         # Row calculation
width = 32           # Tile content width
height = 36          # Tile content height
```

### Verification Method
1. Extracted tiles with offsets 0, 2, 4, 6, 8, 10, 12, 14
2. Visually inspected each extraction
3. Offset 12 with dimensions 32×36 produced clean tiles with:
   - No wraparound artifacts on left edge
   - No cutoff on right edge
   - No black bars at bottom
   - Proper transparent backgrounds

---

## Conclusion

While the exact hex loading code in the disassembly remains elusive due to lack of symbolic information, we have **successfully reverse-engineered the sprite sheet structure** through empirical analysis.

The correct extraction parameters are documented in:
- `hex_tile_loader.py` - HexTileLoader class with verified constants
- `txt/CORRECT_HEX_TILE_STRUCTURE.md` - Complete sprite sheet documentation
- `txt/HEX_TILE_EXTRACTION_REPORT.md` - Extraction process and results

**Next Steps for Disassembly Analysis:**
1. Use interactive debugger on original Mac environment
2. Trace GetPicture(128) call at runtime
3. Identify function addresses for tile extraction loops
4. Document memory layout of extracted tiles

---

**Status:** EXTRACTION WORKING - Disassembly analysis incomplete but not blocking
