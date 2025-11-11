# Sprite Sheet Row Analysis - Visual Verification

**Date**: 2025-11-11
**File**: `extracted_images/scan_width_448.png` (448×570 pixels, 15 rows)

## Color Analysis of Each Row

Automated color sampling from multiple tiles in each row:

| Row | Dominant Colors | Auto-Classification | Manual Inspection Needed |
|-----|----------------|---------------------|--------------------------|
| 0 | Green/brown mix | MIXED | Likely grass/field base |
| 1 | Light green (36% RGB(102,153,0)) | GRASS | Grass variants |
| 2 | Light green (38% RGB(102,153,51)) | GRASS | Forest? (needs verification) |
| 3 | Light green + some blue | GRASS | River? (needs verification) |
| 4 | Light green + some red | GRASS | Town? (needs verification) |
| 5 | **Deep blue (71% RGB(0,51,204))** | **WATER/OCEAN** | ✓ Confirmed water |
| 6 | **Tan/yellow (26% RGB(204,204,102))** | **BEACH/SAND** | ✓ Confirmed beach |
| 7 | Light green | GRASS | Swamp? or grass variant |
| 8 | Tan/yellow (22% RGB(204,204,102)) | BEACH/SAND | Desert/road? |
| 9 | Dark/grey (23% black) | MIXED | Mountains? |
| 10 | Light green + grey | GRASS | Roads? |
| 11 | Mixed black + green | MIXED | Fortifications? |
| 12 | Green + grey | GRASS | Bocage? |
| 13 | **Reddish (25% red tones)** | **DESERT/BROWN** | Farm fields? |
| 14 | **White/grey (69% white)** | **URBAN/GREY** | Buildings? |

## Current Terrain Mapping vs Row Analysis

| Type | Description | Current Mapping | Row Colors | Match? | Issues |
|------|-------------|----------------|------------|--------|--------|
| 0 | Grass/Field | Row 0 | Green/brown mix | ✓ | None |
| 1 | Water/Ocean | Row 5 | **71% deep blue** | ✓✓ | None - perfect match |
| 2 | Beach/Sand | Row 6 | **Tan/yellow** | ✓✓ | None - perfect match |
| 3 | Forest | Row 2 | Light green | ✓ | Likely correct |
| 4 | Town | Row 4 | Light green + red | ✓ | Likely correct (buildings) |
| **5** | **Road** | **Row 8** | **Tan/yellow** | **?** | Shows beach/desert, not roads |
| 6 | River | Row 3 | Light green + blue | ✓ | Likely correct |
| 7 | Mountains | Row 9 | Dark/grey/black | ✓ | Likely correct |
| **8** | **Swamp** | **Row 7** | **Light green** | **?** | Just looks like grass |
| 9 | Bridge | Row 8, col 5 | Tan/yellow variant | ? | Same as type 5 issue |
| **10** | **Fortification** | **Row 10** | **Light green + grey** | **?** | Looks more like roads |
| **11** | **Bocage** | **Row 11** | **Mixed black/green** | **?** | Could be fortifications |
| 12 | Cliff | Row 9, col 5 | Dark grey variant | ? | Mountain variant |
| 13 | Village | Row 10, col 5 | Green/grey variant | ? | Same as type 10 issue |
| **14** | **Farm** | **Row 12** | **Green + grey** | **?** | Doesn't match farm description |
| 15 | Canal | Row 3, col 5 | Green + blue variant | ? | River variant |
| 16 | Unknown | Row 1 | Light green | ✓ | Generic grass |

## Key Observations

### Definite Matches (Types 1-4)
- **Row 5 (Type 1)**: 71% deep blue = Water/Ocean ✓✓
- **Row 6 (Type 2)**: Tan/yellow = Beach/Sand ✓✓
- These are **unquestionably correct**

### Problematic Areas

1. **Rows 8-14 (Types 5-16)**: Color analysis shows inconsistencies
   - Row 8: Tan/yellow (beach-like), used for "Road" (type 5)
   - Row 10: Green + grey, used for "Fortification" (type 10) but might be roads
   - Row 11: Black/green mix, used for "Bocage" (type 11) but might be fortifications
   - Row 13: Reddish/brown, not currently mapped but could be farm
   - Row 14: White/grey buildings, not currently mapped

2. **Multiple rows look like grass/green** (rows 1, 2, 3, 4, 7, 10, 12)
   - Hard to distinguish without seeing actual tile graphics
   - Color alone isn't enough to identify terrain type

## Hypothesis: Row Order Issues

Looking at rows 10-14:
- Row 10: Green + grey (17% grey) - could be **roads** (grey paths through grass)
- Row 11: Black + green (17% black) - could be **fortifications** (dark walls)
- Row 12: Green + grey (17% grey) - could be **bocage** (hedgerows)
- Row 13: Red/brown (25% red) - could be **farm** (cultivated fields)
- Row 14: White/grey (69% white) - could be **village/buildings** (structures)

If this hypothesis is correct:
- Type 5 (Road) should map to row 10 (not row 8)
- Type 10 (Fortification) should map to row 11 (not row 10)
- Type 11 (Bocage) should map to row 12 (not row 11)
- Type 14 (Farm) should map to row 13 (not row 12)
- Type 13 (Village) should map to row 14 (not row 10 col 5)

This would be a **systematic +2 offset error** starting around row 8.

## Recommended Next Steps

1. **Visual inspection required**: Color analysis alone isn't conclusive for rows 8-14
2. **Extract sample tiles**: Create actual PNG previews of tiles from each row
3. **Compare with game screenshots**: If available, match terrain appearance
4. **Test fixes incrementally**:
   - First fix the clear mismatches (rows 10-13)
   - Then address uncertain cases (swamp, bridge, etc.)

## Terrain Gameplay Parameters

**Investigation Result**: No explicit movement cost or passability tables found in disassembly.

**The table at seg000:0D12 is NOT a sprite row mapping** because:
- Values 22, 24, 18 would require 950+ pixel sprite sheet
- Actual sprite sheet is only 570 pixels (15 rows max)
- These values likely represent gameplay parameters (movement costs, defense bonuses)

**Likely implementation**: Terrain effects hardcoded in movement/combat functions based on terrain type ID.
