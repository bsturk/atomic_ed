# Hex Variant Selection System Analysis

**Date:** 2025-11-09
**Objective:** Understand how the game selects which hex tile variant to display from the 13-column sprite sheet
**Status:** PARTIAL - Structure found, selection logic remains unknown

---

## Executive Summary

The sprite sheet contains **13 variants per terrain type** (13 columns × 14 terrain rows). Investigation reveals the sprite sheet loading system and 13-column data structure, but the actual **variant selection algorithm** (aesthetic vs. content-based) remains hidden in rendering code not yet identified.

---

## Sprite Sheet Structure (CONFIRMED)

### Layout
```
File: extracted_images/scan_width_448.png
Dimensions: 448 × 570 pixels
Organization: 13 columns × 15 rows

Rows 0-13:  14 terrain types (each with 13 variants)
Row 14:     3 special tiles (black hex, plane crashes)
Columns:    13 variants per terrain type (columns 0-12)
```

### Extraction Parameters (Verified)
```python
HEX_WIDTH = 32          # 0x20 - actual tile content width
HEX_HEIGHT = 36         # 0x24 - actual tile content height
HEX_SPACING = 34        # 0x22 - horizontal center-to-center
HEX_ROW_SPACING = 38    # 0x26 - vertical center-to-center
HEX_OFFSET_X = 12       # 0x0C - starting X offset

# Total grid: 13 columns × 15 rows
# Each hex: 32×36 pixels extracted from 34×38 grid positions
```

---

## Variant Categories

Based on visual analysis of `scan_width_448.png`:

### 1. Aesthetic Variants (Random Visual Variation)
**Purpose:** Visual diversity to prevent repetitive-looking maps

**Examples:**
- **Grass/Fields** (multiple rows): Different grass patterns, subtle color variations
- **Forest**: Different tree arrangements
- **Ocean**: Different wave patterns (without ships)
- **Hills/Mountains**: Different elevation shading

**Likely Selection:** Random column (0-12) when terrain placed, or deterministic based on hex coordinates

### 2. Content Variants (Meaningful Differences)
**Purpose:** Different features on same terrain type

**Examples:**
- **Ocean hexes with ships:**
  - Column 0: Empty ocean
  - Columns 1-2: Ocean with aircraft carrier/battleship
  - Columns 3-12: Wave variations

- **Bridge hexes:**
  - Some columns: Plain terrain
  - Specific column: Bridge structure overlay

- **Flags (Row 13):**
  - Different columns: Progressive darkening (representing capture/control status?)

**Likely Selection:** Game logic based on unit presence, scenario data, or game state

### 3. Edge-Matching Variants (Seamless Transitions)
**Purpose:** Smooth visual transitions between different terrain types

**Possibility:** Some variants designed to match adjacent terrain edges
**Status:** Not confirmed - would require neighbor analysis in rendering code

---

## Disassembly Findings

### 1. Sprite Sheet Storage (FOUND ✅)

**Location:** `disasm.txt` lines 13640-13652, 14018-14021

```assembly
; After loading PICT #128 from PCWATW.REZ
seg002:1A40    mov    ds:0F22h, ax    ; Sprite sheet pointer
seg002:1A46    mov    ds:0CDEh, bx    ; Sprite sheet base address
```

**Memory Locations:**
- `ds:0F22h` - Loaded sprite sheet pointer (PICT #128 data)
- `ds:0CDEh` - Sprite sheet base address
- `ds:1C0h` - Width value 0xC80 (3200 = 448 pixels × 8 bits)

### 2. 13-Column Data Structure (FOUND ✅)

**Location:** `disasm.txt` lines 16028-16038
**Memory Address:** seg002:6B0F to seg002:6B26

```assembly
seg002:6B0F loc_86DF:
seg002:6B0F    les    di, cs:dword_3392   ; Load destination pointer
seg002:6B14    mov    ax, di
seg002:6B16    cld                         ; Forward direction
seg002:6B17    mov    cx, 0Dh              ; *** 13 COLUMNS ***
seg002:6B1A    rep    movsw                ; Copy 13 words (26 bytes)
seg002:6B1C    add    si, bx               ; Adjust source
seg002:6B1E    movsd                       ; Copy 4 more bytes
seg002:6B20    movsd                       ; Copy 4 more bytes
seg002:6B22    movsd                       ; Copy 4 more bytes
seg002:6B24    movsd                       ; Copy 4 more bytes
```

**Analysis:**
- Copies **13 words** (26 bytes) using `rep movsw`
- Then copies **16 additional bytes** (4 × `movsd`)
- **Total: 42 bytes per iteration**
- **13 matches hex column count exactly**
- Likely a table of sprite sheet column offsets or tile indices

**Hypothesis:** This could be:
1. A row of 13 pre-calculated sprite offsets
2. A table mapping variant numbers (0-12) to sprite sheet X positions
3. Part of rendering pipeline that processes 13 tiles at once

### 3. Variant Selection Logic (NOT FOUND ❌)

**Expected patterns we searched for:**

#### Random Variant Selection
```assembly
; Expected (NOT FOUND):
call   get_random          ; Get random number
and    ax, 0Ch             ; Mask to 0-12 (13 variants)
mov    [variant], ax       ; Store variant column
```

**Search Results:**
- ❌ No explicit random number generation calls
- ❌ No INT 1Ah timer access (common random seed)
- ❌ No modulo 13 (div by 0x0D) operations
- ⚠️ Found 7 instances of `and ax, 0Fh` (modulo 16) - could be related

#### Content-Based Selection
```assembly
; Expected (NOT FOUND):
cmp    [unit_type], CARRIER    ; Check for naval unit
jnz    normal_ocean
mov    [variant], 1            ; Use carrier ocean sprite
```

**Search Results:**
- ❌ No conditional logic tied to unit presence
- ❌ No special case handling for ships/bridges visible
- ❌ No variant tables mapping features to columns

### 4. Hex Rendering Loop (NOT FOUND ❌)

**Expected pattern:**
```assembly
; Expected main rendering loop (NOT FOUND):
for row = 0 to 99:              ; Map height
    for col = 0 to 124:          ; Map width
        terrain_type = map[row][col] & 0x0F     ; Low 4 bits
        variant = (map[row][col] >> 4) & 0x0F   ; High 4 bits

        sprite_row = terrain_to_row[terrain_type]
        sprite_col = variant

        x_offset = sprite_col * 34 + 12
        y_offset = sprite_row * 38

        blit_tile(sprite_base, x_offset, y_offset, 32, 36, screen_x, screen_y)
```

**Search Results:**
- ❌ No loops with 125 (0x7D) or 100 (0x64) iterations (map dimensions)
- ❌ No multiplication by 34 (0x22) or 38 (0x26) for sprite positioning
- ❌ No 32×36 (0x20×0x24) tile dimension constants
- ❌ No blitting operations with sprite sheet pointers

---

## Likely Implementation (Hypothesis)

Based on what we found and didn't find, the variant selection likely works as follows:

### Storage Format

**Option 1: Packed Byte (Most Likely)**
```
Each hex = 1 byte:
  Bits 0-3: Terrain type (0-16, needs 5 bits but 4 reserved)
  Bits 4-7: Variant column (0-12, needs 4 bits)

Map data = 125 × 100 = 12,500 bytes
```

**Option 2: Separate Arrays**
```
terrain_data[12500]  ; 1 byte per hex: terrain type
variant_data[12500]  ; 1 byte per hex: variant column
Total: 25,000 bytes
```

**Option 3: Compressed/Sparse**
```
Run-length encoding or sparse storage
Only non-default terrain/variants stored
Reduces memory footprint
```

### Selection Strategies

#### 1. Pre-Determined (Stored in Scenario)
**Aesthetic variants:** Selected when scenario created, stored in map data
```python
# Scenario editor:
for each hex:
    terrain = select_terrain_type()
    variant = random(0, 12)  # Random aesthetic variation
    save_to_map(terrain, variant)
```

#### 2. Deterministic (Calculated from Position)
**Pseudo-random based on coordinates:**
```assembly
; Calculate variant from hex position
mov  ax, [row]
xor  ax, [col]           ; XOR coordinates
and  ax, 0Ch             ; Mask to 0-12
mov  [variant], ax       ; Use as variant column
```

**Advantage:** No storage needed, consistent appearance

#### 3. Context-Sensitive (Based on Neighbors/Units)
**Ships in ocean:**
```assembly
; Check for naval units on hex
call  get_unit_at_hex
cmp   [unit_type], BATTLESHIP
jz    use_battleship_ocean
cmp   [unit_type], CARRIER
jz    use_carrier_ocean
; Otherwise use random ocean variant
```

**Bridges/Roads:**
```assembly
; Check adjacent hexes for roads
call  analyze_neighbors
; Select variant that matches connections
```

---

## Why Rendering Code Is Hidden

### 1. Indirect Addressing
```assembly
; Function pointers in tables
call  word ptr ds:[render_func_table + bx]
; Static analysis can't resolve runtime addresses
```

### 2. External Graphics Library
- Game may use DOS graphics library (not in INVADE.EXE)
- Blitting functions in separate DLL/library
- Only call stubs visible in disassembly

### 3. Compiler Optimization
- Loop unrolling hides iteration patterns
- Constants pre-computed in data segment
- Inline functions make code flow unclear

### 4. Table-Driven Rendering
- Pre-computed sprite offsets in lookup tables
- No explicit calculations at render time
- Direct memory-to-memory copies

---

## Map Data Investigation

### Scenario File Structure
**File:** `game/SCENARIO/UTAH.SCN` (172,046 bytes)

**Known Values:**
```
Map Width:  125 hexes (0x7D)
Map Height: 100 hexes (0x64)
Total Hexes: 12,500
Terrain Types: 17 (0-16)
```

**Data Sections:**
```
PTR5 (0x002a03): 765 bytes       - Too small for full map
PTR6 (0x002d00): 85,849 bytes    - Sparse data (52% zeros)
PTR4 (0x017cf3): 74,523 bytes    - Mixed binary/text
```

**Problem:** Terrain data location not definitively identified

**Possibilities:**
1. **Compressed in PTR6** - Run-length or sparse encoding
2. **Bit-packed** - 5 bits per hex = 7,813 bytes (fits in PTR5 × 10)
3. **Embedded in PTR4** - Mixed with unit positioning data
4. **External file** - Separate .MAP or .TER file (not found)

---

## Evidence Summary

| Component | Status | Location | Notes |
|-----------|--------|----------|-------|
| Sprite sheet loading | ✅ FOUND | Lines 13640-13652 | PICT #128 → ds:0F22h, ds:0CDEh |
| Sprite width constant | ✅ FOUND | Line 1119 | 0xC80 (448×8) at ds:1C0h |
| 13-column structure | ✅ FOUND | Lines 16028-16038 | Copies 13 words + 16 bytes |
| Map data format | ⚠️ PARTIAL | Scenario files | 125×100 confirmed, storage unknown |
| Variant selection | ❌ NOT FOUND | — | No random/conditional logic visible |
| Hex rendering loop | ❌ NOT FOUND | — | No 34×38 calculations found |
| Tile blitting | ❌ NOT FOUND | — | No sprite-to-screen operations |

---

## Next Steps for Investigation

### Option 1: Dynamic Analysis (Recommended)
```bash
# Run game in DOSBox debugger
dosbox-x game/INVADE.EX -debug

# Set memory breakpoints:
- Read breakpoint on ds:0F22h (sprite sheet access)
- Write breakpoint on video memory (screen updates)
- Read breakpoint on scenario data sections

# Trace execution:
1. Load scenario
2. Draw map screen
3. Identify rendering function
4. Trace back to variant selection
```

### Option 2: Scenario File Experimentation
```python
# Modify terrain data in UTAH.SCN
# Change specific byte ranges
# Reload in game
# Observe which hexes change appearance
# → Reveals map data format and variant storage
```

### Option 3: Memory Dump Analysis
```bash
# Run game, load scenario
# Dump memory to file
# Search for patterns:
- 12,500 bytes with values 0-16 (terrain types)
- Adjacent bytes 0-12 (variant columns)
- Repeating geographic patterns
```

### Option 4: Graphics Trace Logging
```bash
# Enable DOSBox video logging
# Capture sprite → screen copy operations
# Identify source offsets in sprite sheet
# Calculate row/column from offsets
# Reverse engineer selection algorithm
```

---

## Memory Locations Reference

### Graphics System
```assembly
ds:128h   = 0x1FB8     ; Graphics parameter
ds:1B8h   = 0x84       ; Graphics parameter
ds:1C0h   = 0xC80      ; Sprite width (448 pixels × 8 bits)
ds:1C2h   = 0x18       ; Segment value
ds:1C8h   = 0xC9E      ; Graphics parameter
ds:1D8h   = 0x5EB      ; Graphics parameter
ds:248h   = 0x44D6     ; Graphics parameter
```

### Resource System
```assembly
ds:0E70h  = File handle for PCWATW.REZ
ds:0F22h  = Loaded sprite sheet pointer (PICT #128)
ds:0CDEh  = Sprite sheet base address
ds:1190h  = 256-byte file path buffer
```

### Code Pointers
```assembly
cs:dword_3392 = Far pointer for 13-word copy operation (seg002:6B0F)
```

---

## Conclusions

### What We Know ✅
1. **Sprite sheet structure:** 13 columns × 15 rows, 448×570 pixels
2. **Variant count:** 13 variants per terrain type (columns 0-12)
3. **Resource loading:** Complete PCWATW.REZ → memory pipeline documented
4. **13-column data structure:** Found copy operation handling 13 words
5. **Storage locations:** Sprite sheet at ds:0F22h and ds:0CDEh

### What Remains Unknown ❌
1. **Variant selection algorithm:** Random, deterministic, or context-based?
2. **Map data format:** How terrain + variant stored in scenario files?
3. **Rendering pipeline:** Where/how tiles drawn to screen?
4. **Special case handling:** How ships, bridges, flags selected?
5. **Edge matching:** Do variants auto-select based on neighbors?

### Key Insight
The game uses **table-driven, indirect rendering** making static disassembly insufficient. The variant selection logic is likely:
- Pre-computed when scenario loads
- Stored in map data (terrain + variant per hex)
- Accessed through lookup tables during rendering
- Optimized away by compiler (no visible loops/calculations)

**Dynamic debugging required** to observe actual variant selection at runtime.

---

## Files Referenced

**Disassembly:**
- `disasm.txt` - Complete game executable disassembly

**Documentation:**
- `txt/DISASM_HEX_LOADING_FOUND.md` - Resource loading system
- `txt/CORRECT_HEX_TILE_STRUCTURE.md` - Sprite sheet structure
- `txt/TERRAIN_DATA_INVESTIGATION.md` - Map data analysis

**Sprite Sheets:**
- `extracted_images/scan_width_448.png` - 448×570 hex sprite sheet
- `extracted_images/PICT_128.png` - Original extracted PICT

**Scenario Files:**
- `game/SCENARIO/UTAH.SCN` - Example scenario (172KB)

**Python Tools:**
- `hex_tile_loader.py` - Runtime sprite sheet extraction
- `scenario_editor.py` - Map viewer using sprite tiles
- `map_terrain_to_tiles.py` - Terrain-to-sprite mapping

---

**Investigation Status:** PARTIAL SUCCESS
**Resource Loading:** ✅ Complete
**Sprite Structure:** ✅ Complete
**Variant Selection:** ❌ Requires dynamic analysis

**Recommended Next Step:** Run game in DOSBox debugger with memory breakpoints to trace variant selection at runtime.
