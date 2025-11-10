# Scenario Format Analysis - File Reference Guide

## Analysis Report
**Complete detailed analysis:** `/home/user/atomic_ed/SCENARIO_FORMAT_ANALYSIS.md` (17 KB)

## Scenario Files

### New Format (Magic 0x1230) - `/home/user/atomic_ed/game/SCENARIO/`
- `/home/user/atomic_ed/game/SCENARIO/BRADLEY.SCN` (31,696 bytes)
- `/home/user/atomic_ed/game/SCENARIO/CAMPAIGN.SCN` (276,396 bytes)
- `/home/user/atomic_ed/game/SCENARIO/COBRA.SCN` (155,702 bytes)
- `/home/user/atomic_ed/game/SCENARIO/COUNTER.SCN` (31,382 bytes) **[REFERENCE FILE - IDENTICAL IN BOTH DIRS]**
- `/home/user/atomic_ed/game/SCENARIO/OMAHA.SCN` (137,440 bytes)
- `/home/user/atomic_ed/game/SCENARIO/STLO.SCN` (48,012 bytes)
- `/home/user/atomic_ed/game/SCENARIO/UTAH.SCN` (172,046 bytes)

### Old Format - Magic 0x0f4a - `/home/user/atomic_ed/game/SCENARIO-prev/`
- `/home/user/atomic_ed/game/SCENARIO-prev/CAMPAIGN.SCN` (274,044 bytes)
- `/home/user/atomic_ed/game/SCENARIO-prev/CITY.SCN` (117,248 bytes)
- `/home/user/atomic_ed/game/SCENARIO-prev/CLASH.SCN` (47,634 bytes)
- `/home/user/atomic_ed/game/SCENARIO-prev/HURBERT.SCN` (41,084 bytes)
- `/home/user/atomic_ed/game/SCENARIO-prev/MANSTEIN.SCN` (63,198 bytes)
- `/home/user/atomic_ed/game/SCENARIO-prev/QUIET.SCN` (105,576 bytes)
- `/home/user/atomic_ed/game/SCENARIO-prev/RIVER.SCN` (47,634 bytes)
- `/home/user/atomic_ed/game/SCENARIO-prev/TANKS.SCN` (63,198 bytes)
- `/home/user/atomic_ed/game/SCENARIO-prev/VOLGA.SCN` (41,080 bytes)
- `/home/user/atomic_ed/game/SCENARIO-prev/WINTER.SCN` (192,274 bytes)

### Old Format - Magic 0x0dac - `/home/user/atomic_ed/game/SCENARIO-prev/`
- `/home/user/atomic_ed/game/SCENARIO-prev/CRUCAMP.SCN` (168,670 bytes)
- `/home/user/atomic_ed/game/SCENARIO-prev/DUCE.SCN` (27,700 bytes)
- `/home/user/atomic_ed/game/SCENARIO-prev/HELLFIRE.SCN` (60,934 bytes)
- `/home/user/atomic_ed/game/SCENARIO-prev/RELIEVED.SCN` (160,386 bytes)
- `/home/user/atomic_ed/game/SCENARIO-prev/RESCUE.SCN` (54,816 bytes)
- `/home/user/atomic_ed/game/SCENARIO-prev/TOBRUK.SCN` (40,620 bytes)

### Old Format - Magic 0x1230 (Already Converted) - `/home/user/atomic_ed/game/SCENARIO-prev/`
- `/home/user/atomic_ed/game/SCENARIO-prev/COUNTER.SCN` (31,382 bytes) **[IDENTICAL TO NEW FORMAT]**

## Parsing and Analysis Code

### Primary Parser
**File:** `/home/user/atomic_ed/scenario_parser.py` (380 lines)
- **Class:** `DdayScenario` - Parses NEW FORMAT (0x1230) files
- **Methods:** 
  - `_parse_counts()` - Parse 12 count fields as uint32
  - `_parse_pointers()` - Parse 8 pointer fields
  - `_parse_sections()` - Extract data sections from file
  - `display_header()` - Show formatted header information
  - `display_data_sections()` - Show section information
  - `find_strings()` - Extract ASCII strings from binary
  - `validate()` - Validate file structure
  - `write()` - Write scenario back to file
- **Constants:**
  - `MAGIC_NUMBER = 0x1230`
  - `HEADER_SIZE = 0x60` (96 bytes)
  - `FIXED_COUNTS` - The 12 expected count values for new format

### Scenario Editor
**File:** `/home/user/atomic_ed/scenario_editor.py` (2000+ lines)
- Full GUI editor for scenario files
- **Class:** `EnhancedUnitParser` - Parses unit data from scenarios
- Unit type mappings and advanced unit parsing
- Mission text and objective handling

### Analysis Tools
**File:** `/home/user/atomic_ed/tools/analyze_unique_scenarios.py`
- Analyzes legacy scenario files
- Extracts mission text, units, locations
- Theater classification

**File:** `/home/user/atomic_ed/tools/analyze_legacy_scenarios.py`
- Analyzes scenarios from different game versions
- String extraction and content analysis

## Key Format Constants

### New Format (0x1230)
```
Magic: 0x1230
Counts: 12 × uint32 values
Fixed count values: [17, 5, 10, 8, 5, 8, 0, 10, 20, 5, HEIGHT, WIDTH]
Counts 11-12: Map dimensions (height and width in hexes)
Standard map: 125 rows × 100 columns
Exception: COBRA.SCN uses 112 rows × 100 columns
```

### Old Format (0x0f4a)
```
Magic: 0x0f4a
Counts: 12 × float32 values
Count 1: Variable (typically 6-7)
Counts 2-10: Similar to new format but as floats
Counts 11-12: NOT map dimensions (0.0 and 1.0-2.0)
PTR1 & PTR2: Float values 1.0 (not actual pointers!)
```

### Old Format (0x0dac)
```
Magic: 0x0dac
All counts: 0.0 (completely different structure)
Alternate format, may be from different game or version
```

## Data Section Structure

### Header (0x00-0x5F, 96 bytes)
- 0x00-0x01: Magic number
- 0x02-0x03: Unknown (usually 0x0000)
- 0x04-0x33: 12 count fields (4 bytes each)
- 0x34-0x3F: Reserved/Padding (6 dwords)
- 0x40-0x5F: 8 pointer fields (4 bytes each)

### Data Sections
**PTR3 (0x48):** Unit Roster - Small section (10-22 bytes)
**PTR4 (0x4C):** Unit Positioning + Text - Large section (contains mission briefing)
**PTR5 (0x50):** Numeric/Coordinate Data - Expanded in new format (685→2396 bytes)
**PTR6 (0x54):** Specialized/AI Data - Large section (90K+ bytes)

## File Order in Binary
**New Format typical order:** PTR5 → PTR6 → PTR3 → PTR4
**Note:** File order is NOT header order!

## Conversion Checklist

For building a converter from OLD (0x0f4a) to NEW (0x1230):

- [ ] Read old file header, parse magic
- [ ] Parse 12 float values from old format
- [ ] Parse pointers (accounting for float PTR1/PTR2)
- [ ] Extract all data sections
- [ ] Determine map dimensions (from data analysis)
- [ ] Create new header with:
  - [ ] Magic: 0x1230
  - [ ] Counts: [17, 5, 10, 8, 5, 8, 0, 10, 20, 5, HEIGHT, WIDTH]
  - [ ] Zeros for reserved bytes (0x34-0x3F)
  - [ ] Recalculated pointers
- [ ] Reorganize data sections (PTR5 → PTR6 → PTR3 → PTR4)
- [ ] Write new file with proper byte offsets
- [ ] Validate with scenario_parser.py

## Quick Test Command

Test the new format parser on a file:
```bash
python3 /home/user/atomic_ed/scenario_parser.py /home/user/atomic_ed/game/SCENARIO/BRADLEY.SCN
```

## Important Notes

1. **Reference File:** COUNTER.SCN is identical in both directories - use as validation reference
2. **Float Parsing:** Old format uses IEEE 754 floats, NOT integers!
3. **Map Dimensions:** Only new format stores them in counts 11-12
4. **Pointer Recalculation:** MUST be done based on actual file offsets after reorganization
5. **Data Preservation:** Mission text, unit names, and AI data must be preserved exactly
