# Manual-Based Terrain Mapping Corrections

**Source**: User manual for D-Day game
**Date**: 2025-11-11

## Manual Row Definitions (1-based indexing)

From the game manual:
- **Row 1** = Bocage
- **Row 2** = Clear
- **Row 3** = Forest
- **Row 7** = Beach

Converting to 0-based (sprite sheet indexing):
- **Row 0** = Bocage
- **Row 1** = Clear
- **Row 2** = Forest
- **Row 6** = Beach

## Current Mapping Analysis

### CORRECT Mappings (verified by user)
- Type 1 (Water/Ocean) → Row 5 ✓
- Type 2 (Beach/Sand) → Row 6 ✓ (matches manual row 7)
- Type 3 (Forest) → Row 2 ✓ (matches manual row 3)
- Type 4 (Town) → Row 4 ✓

### INCORRECT Mappings

**Type 11 (Bocage)**:
- Current: Row 11
- Manual says: Row 0 (manual row 1)
- **FIX**: Type 11 → Row 0

**Type 0 (Grass/Field described as "Clear")**:
- Current: Row 0
- But row 0 is Bocage per manual
- Manual says "Clear" is row 1 (0-based)
- **FIX**: Type 0 → Row 1

## Complete Row Inventory from Manual

Need to find manual documentation for all 15 rows to create complete mapping.

Known from manual:
```
Row 0: Bocage (manual row 1)
Row 1: Clear (manual row 2)
Row 2: Forest (manual row 3)
Row 3: ? (likely River based on visual)
Row 4: ? (likely Town based on visual)
Row 5: ? (Water/Ocean - type 1 uses this correctly)
Row 6: Beach (manual row 7)
Row 7: ?
Row 8: ?
Row 9: ?
Row 10: ?
Row 11: ?
Row 12: ?
Row 13: ?
Row 14: Special tiles (crash animations)
```

## Required Corrected Mapping (Partial)

Based on manual + user confirmation:

```python
TERRAIN_MAPPING = {
    0: (1, 0),   # Grass/Field (Clear) - FIX: was (0, 0)
    1: (5, 0),   # Water/Ocean - CORRECT
    2: (6, 0),   # Beach/Sand - CORRECT
    3: (2, 0),   # Forest - CORRECT
    4: (4, 0),   # Town - CORRECT
    5: (?, 0),   # Road - needs manual lookup
    6: (?, 0),   # River - needs manual lookup
    7: (?, 0),   # Mountains - needs manual lookup
    8: (?, 0),   # Swamp - needs manual lookup
    9: (?, ?),   # Bridge - needs manual lookup
    10: (?, 0),  # Fortification - needs manual lookup
    11: (0, 0),  # Bocage - FIX: was (11, 0), manual says row 0
    12: (?, ?),  # Cliff - needs manual lookup
    13: (?, ?),  # Village - needs manual lookup
    14: (?, 0),  # Farm - needs manual lookup
    15: (?, ?),  # Canal - needs manual lookup
    16: (?, 0),  # Unknown - needs manual lookup
}
```

## Action Required

Need to find complete manual documentation showing:
- What terrain type each of the 15 rows represents
- Then map the 17 terrain type IDs to the correct rows

Manual should have a table showing all rows with their terrain names.
