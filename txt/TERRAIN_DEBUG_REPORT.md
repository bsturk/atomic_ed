# Terrain Display Debug Report

## Problem Description

The terrain data was displaying incorrectly in the scenario editor with:
- Very symmetrical, artificial-looking patterns
- Water hexes with ships appearing in the middle of land masses
- Repeating "checkerboard" style patterns instead of realistic geography

## Investigation Results

### Root Cause: COLUMN-MAJOR vs ROW-MAJOR STORAGE

The terrain data is stored in **COLUMN-MAJOR** order, NOT row-major order as originally assumed.

#### What This Means:

**WRONG (Original Implementation):**
```python
x = hex_index % 125      # Assume row-major
y = hex_index // 125
```

This treats the data as:
- Bytes 0-124: First row (y=0), columns x=0 to x=124
- Bytes 125-249: Second row (y=1), columns x=0 to x=124
- etc.

**CORRECT (Fixed Implementation):**
```python
y = hex_index % 100      # Column-major
x = hex_index // 100
```

This correctly interprets the data as:
- Bytes 0-99: First column (x=0), rows y=0 to y=99
- Bytes 100-199: Second column (x=1), rows y=0 to y=99
- etc.

### Evidence

#### 1. Clustering Analysis

Testing different coordinate mappings and measuring geographic clustering:

```
Row-major (WRONG):  Clustering score: 16,593 (0.49 avg neighbor match)
Column-major (FIX): Clustering score: 24,747 (0.74 avg neighbor match)
Transposed:         Clustering score: 18,973 (0.56 avg neighbor match)
```

**The column-major mapping has 49% better clustering!** This means terrain of the same type is grouped together (water with water, land with land), which is what we expect from realistic geography.

#### 2. Visual Comparison

**BEFORE FIX (Symmetrical Pattern):**
```
..~~..~~..~~..~~..~~..~~..~~..~~..~~..~~..~~..~~..~~..~~..~~
.~~..~~..~~..~~..~~..~~..~~..~~..~~..~~..~~..~~..~~..~~..~~.
~~..~~..~~..~~..~~..~~..~~..~~..~~..~~..~~..~~..~~..~~..~~..
```
Shows obvious repeating pattern - NOT realistic!

**AFTER FIX (Realistic Geography):**
```
.v~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
s...........................................................
F...........................................................
..~~~~~~~~~~~~~~~~~~~.~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
..~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~T~~~~~
```
Shows water clustering together, land clustering together - realistic!

### Other Findings

#### Byte Format: CORRECT
The original byte format interpretation was correct:
- Bits 0-3: Terrain type (0-16)
- Bits 4-7: Variant (0-12)

Testing showed both original and swapped formats produce "sensible" terrain distributions, but the variant distribution confirms the original is correct:
- Variant 0: 72.5% (common default)
- Variant 12: 24.4% (special case, possibly ocean variant)

#### Offset: CORRECT
Offset 0x57E4 is confirmed correct. Testing alternative offsets (0x5000, 0x6000, PTR sections) showed worse data patterns.

## Fix Applied

File: `/home/user/atomic_ed/terrain_reader.py`

Changed coordinate calculation from:
```python
x = hex_index % MAP_WIDTH   # WRONG
y = hex_index // MAP_WIDTH
```

To:
```python
y = hex_index % MAP_HEIGHT  # CORRECT
x = hex_index // MAP_HEIGHT
```

Added documentation explaining the column-major storage format.

## Verification

After fix:
- Terrain distribution is sensible (50.5% grass, 48.6% water for UTAH beach)
- Geographic clustering is realistic
- No more symmetrical patterns
- Ships should now appear in water, not on land

## Testing Commands

To verify the fix:

```bash
# Test terrain extraction
python3 terrain_reader.py game/SCENARIO/UTAH.SCN

# Visualize before/after
python3 visualize_terrain_fix.py game/SCENARIO/UTAH.SCN

# Run full debugging analysis
python3 debug_terrain_display.py game/SCENARIO/UTAH.SCN
```

## Impact

This fix affects:
- `terrain_reader.py` - Core extraction logic (FIXED)
- `scenario_editor.py` - Uses terrain_reader (automatically fixed)
- Any other code reading map data (needs same fix)

## Lessons Learned

1. **Always test coordinate mappings** - Row-major vs column-major is a common source of bugs
2. **Geographic clustering is a good validation metric** - Real terrain should cluster
3. **Visual inspection is valuable** - The symmetrical pattern was an obvious clue
4. **Test multiple scenarios** - Different maps help confirm the fix is general

## Technical Details

**Map Storage Format:**
- Location: Offset 0x57E4 in .SCN file
- Size: 12,500 bytes (125 columns × 100 rows)
- Format: 1 byte per hex
  - Low nibble (bits 0-3): Terrain type (0-16)
  - High nibble (bits 4-7): Variant (0-12)
- Storage order: **COLUMN-MAJOR**
  - Fills each column top-to-bottom before moving to next column
  - Index formula: `index = x * 100 + y`
  - Reverse formula: `x = index // 100`, `y = index % 100`
