# D-Day Scenario File Format: Terrain Data Investigation Summary

## Overview
Investigated the D-Day (.SCN) scenario file format to understand how terrain/map data is stored. Analyzed the scenario parser, scenario editor, binary file structure, and existing documentation.

## Key Findings

### 1. File Structure Summary

**File Organization (UTAH.SCN example):**
- **Total file size:** 172,046 bytes
- **Header:** 96 bytes (fixed, contains magic number and pointers)
- **PTR5** (Numeric/Coordinate Data): 765 bytes (0x002a03 - 0x002d00)
- **PTR6** (Specialized Data): 85,849 bytes (0x002d00 - 0x017c59)
- **PTR3** (Unit Roster): 154 bytes (0x017c59 - 0x017cf3)
- **PTR4** (Unit Positioning + Text): 74,523 bytes (0x017cf3 - 0x02a00e)

**File Order:** PTR5 → PTR6 → PTR3 → PTR4 (not the order listed in header!)

### 2. Current Terrain Implementation (Procedural, NOT Data-Driven)

**From scenario_editor.py (lines 527-549):**
The current implementation does NOT use stored terrain data. Instead, it:

1. Extracts numeric values from PTR5 as 16-bit integers
2. Uses these values to GENERATE terrain procedurally
3. Creates terrain variation by mixing different indices: `terrain_type = (value1 + value2) % 17`
4. Results in RANDOM/NOISY terrain that varies by scenario but isn't realistic

```python
# Current approach creates random terrain patches
for y in range(self.MAP_HEIGHT):
    for x in range(self.MAP_WIDTH):
        idx = (y * self.MAP_WIDTH + x) % len(coords)
        idx2 = (x * 17 + y * 23) % len(coords)
        value1 = coords[idx].get('value', 0)
        value2 = coords[idx2].get('value', 0)
        terrain_type = (value1 + value2) % 17  # Creates noise
        self.terrain[(x, y)] = terrain_type
```

### 3. What Data IS in Each Section

#### PTR5: Numeric/Coordinate Data (765 bytes in UTAH.SCN)
- **Content:** Binary numeric data, mostly 16-bit little-endian integers
- **First bytes example:** `02 b8 02 70 00 61 00 fd 00 01 03 1b 03 31 03 26...`
- **Pattern:** Some numeric values (large: 0x0270=624, 0x03b8=696), followed by lots of zeros
- **Interpretation:** Likely contains:
  - Unit positions as coordinate pairs (X, Y)
  - Unit strengths/damage values
  - Turn timings
  - Supply/fuel values
  - Trigger conditions
- **Size:** Too small for full terrain data (only 765 bytes for 12,500 hexes)

#### PTR6: Specialized/Sparse Data (85,849 bytes in UTAH.SCN)
- **Content:** Highly sparse binary data - 52% zeros, 48% non-zero data
- **Structure:** 15,563 separate non-zero "blocks" averaging 2 bytes each
- **Pattern:** Scattered throughout the section, organized as small chunks separated by zero-padding
- **Likely contents:**
  - Fog of war state
  - AI decision data
  - Optional objectives
  - Reinforcement scheduling
  - Victory condition state
  - Preallocated space for runtime use
- **NOT:** Raw terrain data (too sparse, wrong size, wrong organization)

#### PTR3: Unit Roster (154 bytes in UTAH.SCN)
- **Content:** Unit definitions with binary headers + ASCII names
- **Structure:** Binary codes + ASCII unit name
- **Example:** `06 02 02 03 00 ff 00 42 2d 38 30 31 2d 56 49 49` = "B-801-VII"
- **Units found:** About 10-30 units per scenario

#### PTR4: Unit Positioning + Text (74,523 bytes in UTAH.SCN)
- **Content:** Complex binary data mixed with ASCII text
- **Contains:** Mission briefings, location names, unit positioning data, objectives
- **Examples of text found:** "As Commander of the VII Corps", "Utah Beach", "Omaha Beach", etc.

---

## Terrain Data Storage: Current Status

### What We Know
1. **Terrain Type Count:** Fixed at 17 types (stored as Count 1 in header = 0x11)
2. **Map Dimensions:** Fixed at 125 × 100 hexes (counts 11 & 12 in header)
3. **Total Map Cells:** 12,500 hexagonal tiles
4. **Terrain Types Identified (from location analysis):**
   - Grass/Field, Water/Ocean, Beach/Sand
   - Forest/Woods, Town/Urban, Road/Path
   - River, Mountains/Hills, Swamp/Marsh
   - Bridge, Fortification, Bocage
   - Cliff/Escarpment, Village, Farm
   - Canal, Unknown/Unused

### What We DON'T Know
1. **WHERE is the terrain data stored?**
   - NOT in PTR5 (too small: 765 bytes vs. 12,500 needed)
   - Probably NOT in PTR6 (wrong structure, too sparse)
   - Possibly in PTR4 (large enough: 74,523 bytes)
   - Possibly in pre-section area (0x60 - PTR5) for mission text

2. **HOW is terrain encoded?**
   - Bit-packed? (5 bits per hex = 6,250 bytes, but PTR5 is 765)
   - Run-length encoded? (variable length records)
   - Compressed? (LZSS, RLE, or other compression)
   - Stored only for non-default terrain? (sparse encoding)

3. **WHAT is the binary format?**
   - One value per hex? (16-bit, 8-bit, 4-bit, or 2-bit)
   - Grouped into chunks? (rows, sectors, regions)
   - Interleaved with unit data?

---

## Technical Analysis

### Storage Size Constraints
```
Available space for terrain in PTR5: 765 bytes = 6,120 bits
Required for 12,500 hexes (17 types = 5 bits each): 62,500 bits ≈ 7,813 bytes
Result: PTR5 is TOO SMALL for uncompressed terrain data
```

### PTR6 Structure Analysis
- Total size: 85,849 bytes (theoretical max for terrain + overhead)
- Non-zero data: 44,615 bytes (52%)
- Non-zero blocks: 15,563 separate chunks
- Average block size: 2.8 bytes
- **Conclusion:** Size is plausible for terrain (12,500 hexes + padding/overhead)
- **But:** Structure doesn't match expected row/column organization

### Hypothesis: Terrain Location
**Most Likely:** PTR4 section (74,523 bytes)
- Large enough to hold compressed terrain + units + text
- Complex structure matches "mixed binary + ASCII"
- Parser hasn't fully reverse-engineered it yet

**Alternative:** Run-length encoded in sparse format
- Only store differences from default terrain
- Or store terrain as linked list of regions
- Explains why PTR6 is sparse with small blocks

---

## Existing Code Analysis

### scenario_parser.py
- ✅ Correctly parses header and section offsets
- ✅ Handles non-standard file order (PTR5→PTR6→PTR3→PTR4)
- ⚠️ PTR5 parsing treats data as generic 16-bit integers
- ❌ No terrain-specific parsing implemented

### scenario_editor.py
- ✅ Loads PTR5 coordinate data
- ❌ Generates terrain PROCEDURALLY (not from stored data)
- ❌ Creates noisy/random terrain patterns
- ⚠️ Recognizes that "Full terrain data parsing is not yet implemented"

### MapViewer class
- Displays 125×100 hex grid with 17 terrain colors
- Currently maps procedural values to colors (0-16)
- No actual terrain data loading mechanism

---

## Recommendations for Terrain Implementation

### Option 1: Extract Terrain from PTR4 (Reverse Engineering)
1. Manually hex-edit a test scenario file
2. Change one hex's terrain value
3. Reload in DOSBox/INVADE.EXE
4. Observe what changed
5. Document the offset and format
6. Repeat for multiple hexes to confirm pattern
7. Build decoder based on findings

**Advantages:**
- Most accurate (real game data)
- Helps understand PTR4 structure
- Enables real terrain editing

**Challenges:**
- Time-consuming
- Requires DOSBox setup
- May need to decode PTR4 unit positioning first

### Option 2: Use Terrain from Location Names
1. Parse location names from PTR4 (already found: 50+ locations)
2. Map each location to map coordinates (in PTR5)
3. Generate terrain around those locations
4. Interpolate between known locations
5. Use geographically realistic patterns (real Normandy terrain)

**Advantages:**
- Works with current data
- Realistic terrain based on actual geography
- No reverse engineering needed

**Challenges:**
- May not match exact game terrain
- Requires geographic knowledge of D-Day invasion area
- Won't match all hex values

### Option 3: Implement Terrain File Format Detection
1. Compare multiple scenario files
2. Look for repeating patterns that change between scenarios
3. Identify correlations with known locations
4. Build probabilistic terrain decoder

**Advantages:**
- Works with available files
- Comparative analysis may reveal patterns

**Challenges:**
- Complex statistical analysis
- May not fully succeed without more files

---

## Summary Table: Data Section Contents

| Section | Size | Content | Decoded? | Notes |
|---------|------|---------|----------|-------|
| **PTR5** | 765 B | Coordinates, values | ~50% | Small numeric pairs, followed by zeros |
| **PTR6** | 85 KB | AI, FOW, objectives | ~10% | Highly sparse, small chunks scattered |
| **PTR3** | 154 B | Unit roster | ~80% | Binary headers + ASCII unit names extracted |
| **PTR4** | 74 KB | Units + text + ??? | ~40% | Mission briefings extracted, terrain unknown |

---

## Conclusion

**Current State:**
- Terrain is generated procedurally from PTR5 values (NOISE, not data-driven)
- Actual terrain data location is UNKNOWN
- Likely in PTR4 but format not yet reverse-engineered

**Next Steps:**
1. Manual reverse engineering of PTR4 using DOSBox testing
2. OR: Implement location-based terrain generation for realistic patterns
3. OR: Comparative analysis of multiple scenario files to detect patterns

**Why This Matters:**
- Current random terrain defeats the purpose of realistic Normandy scenarios
- Real terrain data would enable proper scenario editing/creation
- Terrain affects unit movement and combat in wargames
