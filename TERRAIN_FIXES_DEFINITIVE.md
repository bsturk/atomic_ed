# Terrain Mapping Fixes - Definitive Analysis

**Date**: 2025-11-11
**Source**: User verification + Game manual

## Confirmed Mismatches

### Type 0 (Grass/Field)
- **Current**: Row 0 → Shows **bocage** (dark green hedgerows)
- **Should be**: Row 1 → Clear/Grass fields
- **Fix**: Swap with Type 11

### Type 11 (Bocage)
- **Current**: Row 11 → Shows unknown terrain
- **Should be**: Row 0 → Bocage (dark green hedgerows)
- **Fix**: Swap with Type 0

### Type 5 (Road)
- **Current**: Row 8 → Shows **beach with bunkers** (fortifications)
- **Should be**: Row 10 or similar → Actual roads
- **Fix**: Likely swap with Type 10

### Type 7 (Mountains)
- **Current**: Row 9 → Shows **fortress** (defensive structure)
- **Should be**: Different row → Actual mountains
- **Fix**: Needs investigation

### Type 10 (Fortification)
- **Current**: Row 10 → Unknown
- **Should be**: Row 8 → Beach fortifications/bunkers
- **Fix**: Likely swap with Type 5

### Type 16 (Unknown)
- **Current**: Row 1 → Shows clear/grass ✓ IMAGE CORRECT
- **Fix**: Just rename description from "Unknown" to "Clear" or "Grass"

## Proposed Corrected Mapping

```python
TERRAIN_MAPPING = {
    0: (1, 0),   # Grass/Field (Clear) - FIX: was (0, 0) - SWAP with Type 11
    1: (5, 0),   # Water/Ocean - CORRECT
    2: (6, 0),   # Beach/Sand - CORRECT
    3: (2, 0),   # Forest - CORRECT
    4: (4, 0),   # Town - CORRECT
    5: (10, 0),  # Road - FIX: was (8, 0) - SWAP with Type 10
    6: (3, 0),   # River - ASSUMED CORRECT
    7: (?, 0),   # Mountains - FIX: was (9, 0) - needs new row
    8: (7, 0),   # Swamp - ASSUMED CORRECT
    9: (8, 5),   # Bridge - ASSUMED CORRECT (variant of road/fortification?)
    10: (8, 0),  # Fortification - FIX: was (10, 0) - SWAP with Type 5
    11: (0, 0),  # Bocage - FIX: was (11, 0) - SWAP with Type 0
    12: (9, 5),  # Cliff - ASSUMED CORRECT (variant of mountains?)
    13: (10, 5), # Village - needs verification
    14: (12, 0), # Farm - ASSUMED CORRECT
    15: (3, 5),  # Canal - ASSUMED CORRECT (variant of river)
    16: (1, 0),  # Unknown → rename to "Clear" - IMAGE CORRECT
}
```

## Swaps Needed

1. **Swap Type 0 ↔ Type 11**:
   - Type 0: (0,0) → (1,0)
   - Type 11: (11,0) → (0,0)

2. **Swap Type 5 ↔ Type 10**:
   - Type 5: (8,0) → (10,0)
   - Type 10: (10,0) → (8,0)

3. **Fix Type 7 (Mountains)**:
   - Current: (9,0) shows fortress
   - Need to find which row shows mountains
   - Candidates: Row 11, 12, or 13?

4. **Rename Type 16**:
   - Keep mapping (1,0)
   - Change description from "Unknown" to "Clear" or "Grass Variant"

## Questions for User

1. **What does row 9 actually show?** (Type 7 currently maps here, shows fortress)
2. **What does row 10 actually show?** (Type 10 currently maps here)
3. **What does row 11 actually show?** (Type 11 currently maps here)
4. **Which row shows mountains?** (Need to fix Type 7)

## Row Inventory from Analysis

```
Row  0: Bocage (manual confirmed, dark green hedgerows)
Row  1: Clear/Grass (manual confirmed, light green fields)
Row  2: Forest (manual confirmed, user verified)
Row  3: River (assumed, has blue/water tones)
Row  4: Town (user verified)
Row  5: Water/Ocean (user verified, deep blue)
Row  6: Beach (manual confirmed, user verified, tan sand)
Row  7: Unknown (light green)
Row  8: Fortifications (beach with bunkers/Atlantic Wall)
Row  9: Fortress (large defensive structure)
Row 10: Unknown (dark green - roads?)
Row 11: Unknown (mixed/complex)
Row 12: Unknown (light green - farm fields?)
Row 13: Unknown (mixed with reddish tones)
Row 14: Special tiles (crash animations)
```

## Immediate Fixes to Apply

These are certain based on user feedback:

1. Type 0: (0, 0) → (1, 0)
2. Type 11: (11, 0) → (0, 0)
3. Type 5: (8, 0) → (10, 0)
4. Type 10: (10, 0) → (8, 0)

Still need to determine:
- Where Type 7 (Mountains) should map
- Verify Types 6, 8, 9, 12-15
