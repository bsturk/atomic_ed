# Correct Hex Tile Structure - D-Day Game Assets

**Date:** 2025-11-08
**Critical Discovery:** The correct terrain hex sprite sheet is `scan_width_448.png`, NOT `PICT_128.png`

## Important Findings

### Sprite Sheet Organization

**File:** `extracted_images/scan_width_448.png`
**Dimensions:** 448 × 570 pixels
**Structure:** 14 rows of terrain types + 1 partial row of special tiles

### Row-Based Organization

The sprite sheet is organized into **14 horizontal strips (rows)**, where each row represents a terrain type with **13 variants** showing different rotations/orientations.

#### Terrain Rows (0-13)

| Row | Terrain Type | Description | Special Features |
|-----|--------------|-------------|------------------|
| 0 | Light green fields | Grass/open terrain | Base grass texture |
| 1 | Medium green grass | Grass variant | Generic terrain |
| 2 | Dark green forests | Dense trees | Forest coverage |
| 3 | Mixed terrain | Water edges/transitions | River/canal transitions |
| 4 | Urban areas | Towns with brown/gray buildings | Town structures |
| 5 | Ocean | Blue water | **Carriers in columns 1-2** |
| 6 | Beach/sand | Tan coastal areas | Landing zones |
| 7 | Green terrain variant | Medium vegetation | Swamp-like |
| 8 | Tan/brown structures | Roads and paths | Infrastructure |
| 9 | Mixed darker terrain | Mountains/cliffs | Elevated terrain |
| 10 | Towns/buildings | Developed areas | Villages/fortifications |
| 11 | Green vegetation | Dense hedgerows | Bocage (Normandy hedgerows) |
| 12 | Light green/grass | Farm fields | Agricultural land |
| 13 | American flags | Progressive darkening | **Visual progression** |

#### Special Tiles Row (14)

**Row 14** (partial): Contains 3 special tiles
- **Column 0**: Black hex (empty/void)
- **Column 1**: Plane crash animation (angled down-left)
- **Column 2**: Plane crash animation (angled down-right)

### Variants Per Row

Each of the 14 terrain rows contains **13 variant tiles** (columns 0-12). These variants represent:
- **Rotation/orientation changes** - Different hex edge connections
- **Visual variety** - Slight texture variations
- **Edge transitions** - How terrain connects to adjacent hexes
- **Special features** - Like carriers in ocean tiles, or darker flags

### Critical Sprite Sheet Issue

**Offset Problem:** The sprite sheet has a wraparound artifact where the tail (rightmost edge) of each row appears at the beginning of the next row, followed by some garbage pixels, then the correct hexes.

**Resolution:** Extract with a small X-offset (+2 pixels) to skip the wraparound artifact.

## Terrain Type to Row Mapping

Mapping the 17 scenario terrain types to the 14 sprite sheet rows:

```
Scenario Terrain ID -> Sprite Sheet Row, Default Column

 0  Grass/Field      -> Row  0, Column 0
 1  Water/Ocean      -> Row  5, Column 0 (has carriers in col 1-2)
 2  Beach/Sand       -> Row  6, Column 0
 3  Forest           -> Row  2, Column 0
 4  Town             -> Row  4, Column 0
 5  Road             -> Row  8, Column 0
 6  River            -> Row  3, Column 0
 7  Mountains        -> Row  9, Column 0
 8  Swamp            -> Row  7, Column 0
 9  Bridge           -> Row  8, Column 5
10  Fortification    -> Row 10, Column 0
11  Bocage           -> Row 11, Column 0
12  Cliff            -> Row  9, Column 5
13  Village          -> Row 10, Column 5
14  Farm             -> Row 12, Column 0
15  Canal            -> Row  3, Column 5
16  Unknown          -> Row  1, Column 0
```

### Shared Rows

Some terrain types share the same row but use different column variants:
- **Row 3**: River (col 0) and Canal (col 5)
- **Row 8**: Road (col 0) and Bridge (col 5)
- **Row 9**: Mountains (col 0) and Cliff (col 5)
- **Row 10**: Fortification (col 0) and Village (col 5)

This makes sense - these are related terrain types that differ in detail/orientation rather than fundamental appearance.

## Extraction Details

### Tile Dimensions
- **Width**: 34 pixels
- **Height**: 38 pixels

### Grid Layout
- **Columns per row**: 13
- **Terrain rows**: 14
- **Special tiles row**: 1 (partial, 3 tiles)
- **Total tiles extracted**: 185
  - 182 terrain tiles (14 × 13)
  - 3 special tiles

### File Naming Convention

**Terrain tiles**: `hex_tile_r{ROW:02d}_c{COL:02d}.png`
- Examples: `hex_tile_r00_c00.png`, `hex_tile_r05_c01.png`

**Special tiles**:
- `black_hex.png` - Empty/void hex
- `plane_left.png` - Crash animation (down-left)
- `plane_right.png` - Crash animation (down-right)

## Special Features

### Ocean Tiles with Carriers

**Row 5** (Water/Ocean) contains naval carrier ships in specific columns:
- **Column 1**: Ocean hex with carrier (white ship graphic)
- **Column 2**: Ocean hex with carrier (white ship graphic)

These represent naval units or points of interest in the ocean hexes.

### American Flag Progression

**Row 13** contains American flags that progressively darken from left to right:
- Columns 0-12 show flags getting darker
- Likely represents different states (captured, controlled, etc.)
- Could also be time-of-day variants (daylight → dusk → night)

### Crash Animations

The two plane sprites (row 14, columns 1-2) show aircraft in descending positions:
- Angled down and to the left
- Angled down and to the right

These are likely crash/destruction animations for air units.

## Comparison to Incorrect Extraction

### Previous (Incorrect) Extraction

**File used**: `PICT_128.png`
- Dimensions: 444 × 575 pixels
- Grid: 13 × 15 (195 tiles)
- Issue: Wrong file with horizontal banding artifacts
- Result: Extracted corrupted tiles

### Current (Correct) Extraction

**File used**: `scan_width_448.png`
- Dimensions: 448 × 570 pixels
- Grid: 13 × 15 (14 terrain rows + 1 special)
- Result: Clean, proper hex tiles with all features visible

## Usage in Scenario Editor

The scenario editor (`scenario_editor.py`) loads tiles based on `hex_tile_config.json`:

```json
{
  "tiles_directory": "extracted_images/correct_hex_tiles",
  "tile_mapping": {
    "0": "hex_tile_r00_c00.png",
    "1": "hex_tile_r05_c00.png",
    ...
  },
  "terrain_names": { ... }
}
```

### Future Enhancements

Potential improvements:
1. **Variant selection**: Use different columns based on adjacent hex terrain
2. **Edge matching**: Select column variant that best matches neighbor connections
3. **Special tiles**: Display carriers in ocean hexes where naval units are present
4. **Flag states**: Use flag darkness to indicate control/capture status
5. **Animations**: Use crash sprites for destroyed air units

## Verification

Run `test_hex_tiles.py` to verify all tiles load correctly:

```bash
python3 test_hex_tiles.py
```

Expected output:
```
Testing hex tile loading...
✓ All 17/17 terrain tile images loaded successfully
```

## Files Created

**Extraction scripts**:
- `extract_correct_hex_tiles.py` - Extracts tiles from scan_width_448.png
- `map_terrain_to_tiles.py` - Creates terrain type mappings

**Configuration**:
- `correct_hex_tile_config.json` - Full config with variants
- `correct_hex_tile_config_simple.json` - Simple config for editor
- `hex_tile_config.json` - Active config (copied from simple)

**Assets**:
- `extracted_images/correct_hex_tiles/` - 185 tile PNGs
- `extracted_images/correct_hex_tiles/tiles_manifest.json` - Complete metadata

**Documentation**:
- `txt/CORRECT_HEX_TILE_STRUCTURE.md` - This document

## Conclusion

The correct hex tile extraction reveals a well-organized sprite sheet with:
- **14 terrain type rows** with 13 variants each
- **Rotation/orientation variants** within each row
- **Special features**: Carriers, flags, crash animations
- **Edge-matching system** using column variants

This structure enables rich, varied terrain rendering with proper edge transitions and special graphical features beyond simple terrain type display.

---

**Key Takeaway**: Always verify visual output when working with extracted game assets. The correct file (`scan_width_448.png`) shows clear, properly aligned hex tiles, while the incorrect file (`PICT_128.png`) had obvious artifacts.
