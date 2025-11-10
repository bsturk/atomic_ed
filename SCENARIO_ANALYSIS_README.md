# Scenario File Format Analysis - Complete Documentation Index

This directory contains comprehensive analysis of the scenario file formats used in the D-Day game.

## Quick Start

**You have 3 files to read:**

1. **SCENARIO_FORMAT_ANALYSIS.md** (17 KB) - START HERE
   - Complete technical documentation
   - Binary structure comparison
   - Detailed examples and hex dumps
   - Conversion strategy guide

2. **SCENARIO_FILE_REFERENCE.md** (6.2 KB) - USE FOR LOOKUP
   - Quick reference for all files
   - Absolute paths to all scenario files
   - Parser code locations
   - Conversion checklist

3. This file (SCENARIO_ANALYSIS_README.md)
   - Overview and navigation guide

## Key Findings Summary

### Format Overview
- **NEW FORMAT**: Magic 0x1230, 7 files, 822 KB (standardized)
- **OLD FORMAT**: Magic 0x0f4a/0x0dac, 17 files, 1,484 KB (legacy)

### Critical Difference #1: Data Type
```
NEW: Counts are 32-bit UNSIGNED INTEGERS (12 values)
OLD: Counts are 32-bit IEEE 754 FLOATS (12 values)
```

### Critical Difference #2: Map Dimensions
```
NEW: Stored in Counts 11-12 (height × width)
OLD: NOT stored in header counts, must determine differently
```

### Critical Difference #3: Pointer Semantics
```
NEW: PTR1 & PTR2 are NULL (0x00000000)
OLD: PTR1 & PTR2 are float 1.0 (0x3F800000) - NOT pointers!
```

## File Locations

### Scenario Files
- New format: `/home/user/atomic_ed/game/SCENARIO/` (7 files)
- Old format: `/home/user/atomic_ed/game/SCENARIO-prev/` (17 files)

### Reference Implementation
- Parser: `/home/user/atomic_ed/scenario_parser.py` (DdayScenario class)
- Editor: `/home/user/atomic_ed/scenario_editor.py` (full GUI)

## Next Steps for Converter Development

1. **Read** SCENARIO_FORMAT_ANALYSIS.md (all sections)
2. **Use** SCENARIO_FILE_REFERENCE.md as lookup guide
3. **Study** scenario_parser.py to understand new format
4. **Test** on COUNTER.SCN (reference file - identical in both dirs)
5. **Analyze** CAMPAIGN.SCN differences (2,352 byte growth)
6. **Build** converter using the specifications provided

## Important Discovery

**COUNTER.SCN is identical in both directories!**
- `/home/user/atomic_ed/game/SCENARIO/COUNTER.SCN` (31,382 bytes)
- `/home/user/atomic_ed/game/SCENARIO-prev/COUNTER.SCN` (31,382 bytes)

This is the perfect reference file for validating conversion results.

## Key Constants for New Format

```python
MAGIC_NUMBER = 0x1230
HEADER_SIZE = 0x60  # 96 bytes
FIXED_COUNTS = [17, 5, 10, 8, 5, 8, 0, 10, 20, 5]  # First 10 counts
COUNT_OFFSETS = [0x04, 0x08, 0x0c, 0x10, 0x14, 0x18, 
                 0x1c, 0x20, 0x24, 0x28, 0x2c, 0x30]
POINTER_OFFSETS = {
    'PTR3': 0x48,  # Unit Roster
    'PTR4': 0x4c,  # Unit Positioning + Text
    'PTR5': 0x50,  # Numeric Data
    'PTR6': 0x54,  # Specialized/AI Data
}
```

## Data Section Sizes in New Format

Using BRADLEY.SCN as example:
- PTR5 (Numeric Data): 2,396 bytes (0x000748 - 0x0010A4)
- PTR6 (AI Data): 93,139 bytes (0x0010A4 - 0x017C77)
- PTR3 (Unit Roster): 10 bytes (0x017C77 - 0x017C81)
- PTR4 (Units+Text): Remainder of file (extends to EOF)

## Data Section Sizes in Old Format (0x0f4a)

Using CLASH.SCN as example:
- PTR5 (Numeric Data): 685 bytes (0x000AE0 - 0x000D8D)
- PTR6 (AI Data): 90,654 bytes (0x000D8D - 0x016FAB)
- PTR3 (Unit Roster): 22 bytes (0x016FAB - 0x016FC1)
- PTR4 (Units+Text): Remainder of file

**Note: PTR5 grows 3.5x in new format (685→2,396 bytes)**

## Header Structure Comparison

### Offsets 0x00-0x3F
| Offset | New (0x1230) | Old (0x0f4a) |
|--------|-------------|-------------|
| 0x00-01 | Magic 0x1230 | Magic 0x0f4a |
| 0x04-33 | 12 × uint32 | 12 × float32 |
| 0x34-3F | zeros | floats |

### Offsets 0x40-0x5F
| Offset | New | Old |
|--------|-----|-----|
| 0x40-47 | PTR1-2 NULL | PTR1-2 float 1.0 |
| 0x48-5F | PTR3-8 | PTR3-8 |

## Testing Guide

### Test New Format Parser
```bash
python3 /home/user/atomic_ed/scenario_parser.py \
  /home/user/atomic_ed/game/SCENARIO/BRADLEY.SCN
```

### Compare Reference Files
```bash
# Both should be identical
ls -l /home/user/atomic_ed/game/SCENARIO/COUNTER.SCN
ls -l /home/user/atomic_ed/game/SCENARIO-prev/COUNTER.SCN
```

### Study Format Differences
```python
from scenario_parser import DdayScenario
import struct

# Parse new format
new = DdayScenario('/home/user/atomic_ed/game/SCENARIO/BRADLEY.SCN')
print(f"Map: {new.map_width} × {new.map_height}")

# Analyze old format header manually
with open('/home/user/atomic_ed/game/SCENARIO-prev/CLASH.SCN', 'rb') as f:
    data = f.read(0x60)
    magic = struct.unpack('<H', data[0:2])[0]
    count1_as_float = struct.unpack('<f', data[0x04:0x08])[0]
    print(f"Magic: 0x{magic:04x}, Count1: {count1_as_float}")
```

## Gotchas to Watch For

1. **Float vs Integer**: Old format uses floats, not ints
2. **Pointer Confusion**: Old format PTR1/2 are floats, not pointers
3. **File Order**: Data sections in file order, not header order
4. **No Header Size**: Can't determine section sizes from header alone
5. **Map Dimensions**: Old format doesn't store them in counts
6. **Data Expansion**: PTR5 grows 3.5x during conversion

## Success Criteria for Converter

- [ ] Reads old format (0x0f4a) correctly
- [ ] Extracts all 4 data sections
- [ ] Creates new header with magic 0x1230
- [ ] Calculates correct map dimensions
- [ ] Preserves all data sections
- [ ] Recalculates pointers correctly
- [ ] Validates against scenario_parser.py
- [ ] Produces byte-for-byte identical output for COUNTER.SCN

## Questions to Investigate

1. **Where does map size come from in old format?**
   - Not in counts 11-12
   - Must be in data sections or determinable from game context

2. **Why does PTR5 grow 3.5x?**
   - Data transformation/reformatting
   - Study CAMPAIGN.SCN (2,352 byte difference) to understand

3. **What are counts 11-12 in old format?**
   - Currently unknown
   - Not map dimensions
   - May be game difficulty or other settings

## Document Structure

### SCENARIO_FORMAT_ANALYSIS.md Contains:
1. Executive Summary
2. File Inventory
3. Header Structure Comparison
4. Key Structural Differences
5. Parsing Code Reference
6. Conversion Strategy
7. Critical Implementation Notes
8. Specific Conversion Examples
9. Summary Table

### SCENARIO_FILE_REFERENCE.md Contains:
1. Complete file listings with paths
2. Parsing code reference
3. Key format constants
4. Data section structure
5. Conversion checklist
6. Important notes

---

**Analysis Date:** November 10, 2025
**Status:** COMPLETE - Ready for converter development
**Last Updated:** 2025-11-10
