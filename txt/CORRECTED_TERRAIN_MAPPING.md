# Corrected Terrain Mapping Analysis

**Date**: 2025-11-11
**Issue**: Terrain text descriptions don't match hex tile images for types 5-16

## Visual Inspection of Sprite Sheet Rows

From `extracted_images/scan_width_448.png` (448×570, 15 rows):

| Row | Visual Content | Best Match For |
|-----|----------------|----------------|
| 0 | Light grass/field | Grass/Field (Type 0) ✓ |
| 1 | Grass/field variants | Unknown (Type 16) |
| 2 | Dense forest (dark green) | Forest (Type 3) ✓ |
| 3 | River/water (blue wavy) | River (Type 6) ✓ |
| 4 | Towns/buildings | Town (Type 4) ✓ |
| 5 | Deep blue ocean | Water/Ocean (Type 1) ✓ |
| 6 | Beach/sand (tan/yellow) | Beach/Sand (Type 2) ✓ |
| 7 | Light green grass | Swamp? or grass variant |
| 8 | Desert/sand with rocks | Road? or desert |
| 9 | Mountains (grey peaks) | Mountains (Type 7) ✓ |
| 10 | Roads (grey paths) | **Road (Type 5)** ← MISMATCH! |
| 11 | Fortifications (grey walls) | **Fortification (Type 10)** ← MISMATCH! |
| 12 | Bocage (hedgerows) | **Bocage (Type 11)** ← MISMATCH! |
| 13 | Farm/cultivated fields | **Farm (Type 14)** ← MISMATCH! |
| 14 | Buildings (beige/tan) | Village? or Town variant |

## Current Mapping vs Corrected Mapping

| Type | Description | Current Row | Visual at Current | Should Be Row | Visual at Correct | Fix Needed |
|------|-------------|-------------|-------------------|---------------|-------------------|------------|
| 0 | Grass/Field | 0 | Grass ✓ | 0 | Grass | None |
| 1 | Water/Ocean | 5 | Ocean ✓ | 5 | Ocean | None |
| 2 | Beach/Sand | 6 | Beach ✓ | 6 | Beach | None |
| 3 | Forest | 2 | Forest ✓ | 2 | Forest | None |
| 4 | Town | 4 | Town ✓ | 4 | Town | None |
| **5** | **Road** | **8** | Desert ✗ | **10** | Roads ✓ | **YES** |
| 6 | River | 3 | River ✓ | 3 | River | None |
| 7 | Mountains | 9 | Mountains ✓ | 9 | Mountains | None |
| **8** | **Swamp** | **7** | Grass ✗ | **7?** | Grass? | **UNCLEAR** |
| 9 | Bridge | 8, col 5 | Desert variant ✗ | ? | ? | **UNCLEAR** |
| **10** | **Fortification** | **10** | Roads ✗ | **11** | Fortifications ✓ | **YES** |
| **11** | **Bocage** | **11** | Fortifications ✗ | **12** | Bocage ✓ | **YES** |
| 12 | Cliff | 9, col 5 | Mountain variant? | 9, col 5? | Mountain variant | Maybe OK |
| 13 | Village | 10, col 5 | Road variant ✗ | 14? | Buildings | **UNCLEAR** |
| **14** | **Farm** | **12** | Bocage ✗ | **13** | Farm ✓ | **YES** |
| 15 | Canal | 3, col 5 | River variant? | 3, col 5? | River variant | Maybe OK |
| 16 | Unknown | 1 | Grass variant | 1 | Grass variant | Probably OK |

## Definite Fixes Needed

### Type 5: Road
- **Current**: Row 8 (shows desert/sand with rocks)
- **Correct**: Row 10 (shows roads/grey paths)

### Type 10: Fortification
- **Current**: Row 10 (shows roads)
- **Correct**: Row 11 (shows fortifications/grey walls)

### Type 11: Bocage
- **Current**: Row 11 (shows fortifications)
- **Correct**: Row 12 (shows bocage/hedgerows)

### Type 14: Farm
- **Current**: Row 12 (shows bocage)
- **Correct**: Row 13 (shows farm/cultivated fields)

## Pattern Identified

There's a **systematic offset** starting at type 5:
- Types 5, 10, 11, 14 are all shifted by +2 rows from where they should be
- This creates a cascading mismatch:
  - Road (5) uses row 8 instead of 10
  - Fortification (10) uses row 10 instead of 11
  - Bocage (11) uses row 11 instead of 12
  - Farm (14) uses row 12 instead of 13

## Uncertain Cases

### Type 8: Swamp
Row 7 shows "light green grass" but description says "swamp". Possibilities:
1. Swamp visual isn't very distinctive (looks like grass)
2. Wrong row assignment
3. No dedicated swamp row (uses grass row)

### Type 9: Bridge
Currently at row 8, col 5 (desert variant). Should it be:
1. A road variant (row 10, col 5)?
2. A river variant (row 3, col 5) showing bridge over river?
3. Its own row?

### Type 13: Village
Currently row 10, col 5 (road variant). Should it be:
1. Row 14 (buildings/beige/tan)?
2. Row 4, col 5 (town variant)?

## Proposed Corrected Mapping

```python
TERRAIN_MAPPING = {
    0: (0, 0),   # Grass/Field - CORRECT
    1: (5, 0),   # Water/Ocean - CORRECT
    2: (6, 0),   # Beach/Sand - CORRECT
    3: (2, 0),   # Forest - CORRECT
    4: (4, 0),   # Town - CORRECT
    5: (10, 0),  # Road - FIX: was (8, 0)
    6: (3, 0),   # River - CORRECT
    7: (9, 0),   # Mountains - CORRECT
    8: (7, 0),   # Swamp - UNCERTAIN (needs verification)
    9: (10, 5),  # Bridge - PROPOSED: road variant or (3, 5) for river bridge
    10: (11, 0), # Fortification - FIX: was (10, 0)
    11: (12, 0), # Bocage - FIX: was (11, 0)
    12: (9, 5),  # Cliff - MAYBE OK (mountain variant)
    13: (14, 0), # Village - PROPOSED: was (10, 5)
    14: (13, 0), # Farm - FIX: was (12, 0)
    15: (3, 5),  # Canal - MAYBE OK (river variant)
    16: (1, 0),  # Unknown - PROBABLY OK
}
```

## Next Steps

1. **Apply definite fixes** for types 5, 10, 11, 14 (clear row shifts)
2. **Verify uncertain cases** by:
   - Looking at actual scenario data to see where types 8, 9, 13 appear
   - Checking if visual appearance matches expected terrain
   - Consulting game documentation or screenshots
3. **Test in scenario editor** to confirm fixes display correctly

## Root Cause

Likely the original mapping was created by:
1. Manually inspecting the sprite sheet
2. Making assumptions about row order
3. Not carefully matching each terrain description with visual content
4. Creating an off-by-2 error in the middle of the mapping sequence
