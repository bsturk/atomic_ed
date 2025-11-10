================================================================================
COMPREHENSIVE SCENARIO FILE FORMAT ANALYSIS REPORT
D-Day Game Scenario Files: New (0x1230) vs Old (0x0f4a/0x0dac) Formats
================================================================================

EXECUTIVE SUMMARY
================================================================================

This report documents the structural differences between:
1. NEW FORMAT: Magic 0x1230 (7 files in /game/SCENARIO/)
2. OLD FORMAT: Multiple magic numbers (17 files in /game/SCENARIO-prev/)
   - 0x0f4a (10 files) - Main old format
   - 0x0dac (6 files) - Alternate old format
   - 0x1230 (1 file) - Already converted

KEY FINDING: The new and old formats are fundamentally different:
- New format uses 32-bit UNSIGNED INTEGERS for header counts
- Old format uses 32-bit IEEE 754 FLOATING POINT for header counts
- The map dimensions are stored differently
- Pointer semantics differ between formats


PART 1: FILE INVENTORY
================================================================================

NEW FORMAT (SCENARIO) - 7 files, 822 KB total:
  BRADLEY.SCN              31,696 bytes   [125x100 hex map]
  CAMPAIGN.SCN            276,396 bytes   [125x100 hex map]
  COBRA.SCN               155,702 bytes   [112x100 hex map - smaller!]
  COUNTER.SCN              31,382 bytes   [125x100 hex map]
  OMAHA.SCN               137,440 bytes   [125x100 hex map]
  STLO.SCN                 48,012 bytes   [125x100 hex map]
  UTAH.SCN                172,046 bytes   [125x100 hex map]

OLD FORMAT (SCENARIO-prev) - 17 files, 1,484 KB total:
  
  Magic 0x0f4a (10 files - Main legacy format):
    CAMPAIGN.SCN            274,044 bytes  (vs new: +2,352 bytes)
    CITY.SCN                117,248 bytes
    CLASH.SCN                47,634 bytes
    HURBERT.SCN              41,084 bytes
    MANSTEIN.SCN             63,198 bytes
    QUIET.SCN               105,576 bytes
    RIVER.SCN                47,634 bytes
    TANKS.SCN                63,198 bytes
    VOLGA.SCN                41,080 bytes
    WINTER.SCN              192,274 bytes
  
  Magic 0x0dac (6 files - Alternate format):
    CRUCAMP.SCN             168,670 bytes
    DUCE.SCN                 27,700 bytes
    HELLFIRE.SCN             60,934 bytes
    RELIEVED.SCN            160,386 bytes
    RESCUE.SCN               54,816 bytes
    TOBRUK.SCN               40,620 bytes
  
  Magic 0x1230 (1 file - NEW FORMAT, already converted):
    COUNTER.SCN              31,382 bytes  (IDENTICAL to new format)

NOTE: COUNTER.SCN is identical in both directories, suggesting it was the
      first file to be converted to the new format and serves as a reference.


PART 2: HEADER STRUCTURE - SIDE-BY-SIDE COMPARISON
================================================================================

NEW FORMAT HEADER (0x00-0x5F, 96 bytes):
--------------------------------------------
Offset  Size  Name              Type      Purpose
----    ----  ----              ----      -------
0x00    2     MAGIC_NUMBER      uint16    Format identifier (0x1230)
0x02    2     UNKNOWN           uint16    Always 0x0000
0x04-   4     COUNT_1           uint32    Terrain/unit types (always 17)
0x08-   4     COUNT_2           uint32    Players/sides (always 5)
0x0C-   4     COUNT_3           uint32    Unknown (always 10)
0x10-   4     COUNT_4           uint32    Unit classes (always 8)
0x14-   4     COUNT_5           uint32    Player types (always 5)
0x18-   4     COUNT_6           uint32    Unit classes (always 8)
0x1C-   4     COUNT_7           uint32    Reserved (always 0)
0x20-   4     COUNT_8           uint32    Unknown (always 10)
0x24-   4     COUNT_9           uint32    Objectives (always 20)
0x28-   4     COUNT_10          uint32    Unknown (always 5)
0x2C-   4     COUNT_11 *** MAP HEIGHT ***  uint32    Height of hex map in rows
0x30-   4     COUNT_12 *** MAP WIDTH ***   uint32    Width of hex map in columns
0x34-   12    RESERVED          uint32s   Padding (always 0x00000000)
0x40-   4     PTR1              uint32    Pointer (usually NULL)
0x44-   4     PTR2              uint32    Pointer (usually NULL)
0x48-   4     PTR3 *** PTR3 (Unit Roster) ***        uint32    Points to unit roster data
0x4C-   4     PTR4 *** PTR4 (Units+Text) ***         uint32    Points to unit positioning + text
0x50-   4     PTR5 *** PTR5 (Numeric Data) ***       uint32    Points to numeric/coordinate data
0x54-   4     PTR6 *** PTR6 (Specialized Data) ***   uint32    Points to AI/specialized data
0x58-   4     PTR7              uint32    Pointer (usually NULL)
0x5C-   4     PTR8              uint32    Pointer (usually NULL)


OLD FORMAT HEADER (0x00-0x5F, 96 bytes):
--------------------------------------------
Offset  Size  Name              Type      Purpose
----    ----  ----              ----      -------
0x00    2     MAGIC_NUMBER      uint16    Format identifier (0x0f4a or 0x0dac)
0x02    2     UNKNOWN           uint16    Always 0x0000
0x04-   4     COUNT_1           float32   Usually 6-7 (variable!)
0x08-   4     COUNT_2           float32   Usually 5.0
0x0C-   4     COUNT_3           float32   Usually 10.0
0x10-   4     COUNT_4           float32   Usually 8.0
0x14-   4     COUNT_5           float32   Variable (1.0 or 5.0)
0x18-   4     COUNT_6           float32   Usually 8.0
0x1C-   4     COUNT_7           float32   Usually 0.0
0x20-   4     COUNT_8           float32   Usually 10.0
0x24-   4     COUNT_9           float32   Usually 20.0
0x28-   4     COUNT_10          float32   Usually 5.0
0x2C-   4     COUNT_11          float32   Always 0.0 (NOT map height!)
0x30-   4     COUNT_12          float32   Variable (1.0-2.0, NOT map width!)
0x34-   4     UNKNOWN           float32   Usually 1.5 or 1.0
0x38-   4     UNKNOWN           float32   Usually 1.0
0x3C-   4     PADDING           float32   Usually 0.0
0x40-   4     PTR1              float32   Always 1.0 (NOT a pointer!)
0x44-   4     PTR2              float32   Always 1.0 (NOT a pointer!)
0x48-   4     PTR3              uint32    Points to unit roster data
0x4C-   4     PTR4              uint32    Points to unit positioning + text
0x50-   4     PTR5              uint32    Points to numeric/coordinate data
0x54-   4     PTR6              uint32    Points to specialized data
0x58-   4     PTR7              uint32    Pointer (usually NULL)
0x5C-   4     PTR8              uint32    Pointer (usually NULL)


DETAILED EXAMPLE: BRADLEY.SCN (New Format):
---------------------------------------------
Offset  Hex bytes                        Interpreted
0x0000: 30 12 00 00                     Magic: 0x1230 ✓
0x0002: 00 00                           Unknown: 0x0000
0x0004: 11 00 00 00                     Count 1: 17 (0x11)
0x0008: 05 00 00 00                     Count 2: 5 (0x05)
0x000C: 0A 00 00 00                     Count 3: 10 (0x0A)
0x0010: 08 00 00 00                     Count 4: 8 (0x08)
0x0014: 05 00 00 00                     Count 5: 5 (0x05)
0x0018: 08 00 00 00                     Count 6: 8 (0x08)
0x001C: 00 00 00 00                     Count 7: 0 (reserved)
0x0020: 0A 00 00 00                     Count 8: 10 (0x0A)
0x0024: 14 00 00 00                     Count 9: 20 (0x14) [objectives]
0x0028: 05 00 00 00                     Count 10: 5 (0x05)
0x002C: 7D 00 00 00                     Count 11: 125 (0x7D) [MAP HEIGHT]
0x0030: 64 00 00 00                     Count 12: 100 (0x64) [MAP WIDTH]
0x0034-0x3F: All zeros (reserved)
0x0040: 00 00 00 00                     PTR1: NULL
0x0044: 00 00 00 00                     PTR2: NULL
0x0048: 77 7C 01 00                     PTR3: 0x017C77 (97,399 bytes into file)
0x004C: 81 7C 01 00                     PTR4: 0x017C81 (97,409 bytes into file)
0x0050: 48 07 00 00                     PTR5: 0x000748 (1,864 bytes into file)
0x0054: A4 10 00 00                     PTR6: 0x0010A4 (4,260 bytes into file)
0x0058: 00 00 00 00                     PTR7: NULL
0x005C: 00 00 00 00                     PTR8: NULL


DETAILED EXAMPLE: CLASH.SCN (Old Format 0x0f4a):
-------------------------------------------------
Offset  Hex bytes                        Interpreted (as float32 / uint32)
0x0000: 4A 0F 00 00                     Magic: 0x0f4a ✓
0x0002: 00 00                           Unknown: 0x0000
0x0004: 00 00 C0 40    [as float: 6.0]  Count 1: 6.0 (variable!)
0x0008: 00 00 A0 40    [as float: 5.0]  Count 2: 5.0
0x000C: 00 00 20 41    [as float: 10.0] Count 3: 10.0
0x0010: 00 00 00 41    [as float: 8.0]  Count 4: 8.0
0x0014: 00 00 A0 40    [as float: 5.0]  Count 5: 5.0
0x0018: 00 00 00 41    [as float: 8.0]  Count 6: 8.0
0x001C: 00 00 00 00    [as float: 0.0]  Count 7: 0.0
0x0020: 00 00 20 41    [as float: 10.0] Count 8: 10.0
0x0024: 00 00 A0 41    [as float: 20.0] Count 9: 20.0
0x0028: 00 00 A0 40    [as float: 5.0]  Count 10: 5.0
0x002C: 00 00 00 00    [as float: 0.0]  Count 11: 0.0 (NOT map height!)
0x0030: 00 00 C0 3F    [as float: 1.5]  Count 12: 1.5 (variable! NOT map width!)
0x0034: 00 00 C0 3F    [as float: 1.5]  Unknown: 1.5
0x0038: 00 00 80 3F    [as float: 1.0]  Unknown: 1.0
0x003C: 00 00 00 00    [as float: 0.0]  Padding: 0.0
0x0040: 00 00 80 3F    [as float: 1.0]  PTR1: 1.0 (float! Not a pointer)
0x0044: 00 00 80 3F    [as float: 1.0]  PTR2: 1.0 (float! Not a pointer)
0x0048: AB 6F 01 00    [as uint32]       PTR3: 0x016FAB (94,123 bytes)
0x004C: C1 6F 01 00    [as uint32]       PTR4: 0x016FC1 (94,145 bytes)
0x0050: E0 0A 00 00    [as uint32]       PTR5: 0x000AE0 (2,784 bytes)
0x0054: 8D 0D 00 00    [as uint32]       PTR6: 0x000D8D (3,469 bytes)
0x0058: 00 00 00 00    [as uint32]       PTR7: NULL
0x005C: 00 00 00 00    [as uint32]       PTR8: NULL


PART 3: KEY STRUCTURAL DIFFERENCES
================================================================================

1. MAGIC NUMBER:
   New Format: 0x1230
   Old Format: 0x0f4a (main) or 0x0dac (alternate)

2. COUNTS INTERPRETATION:
   New Format: 12 unsigned 32-bit integers (always same values)
               Counts 1-6 and 8-10 are configuration constants
               Counts 11-12 are map HEIGHT and WIDTH
   Old Format: 12 IEEE 754 floating-point values (variable)
               Counts 1-6 vary per file
               Counts 11-12 don't represent map dimensions

3. MAP DIMENSIONS STORAGE:
   New Format: Count 11 = height (rows), Count 12 = width (columns)
               Example: 125 rows x 100 columns (found in counts at 0x2C and 0x30)
   Old Format: Map dimensions are NOT stored in counts
               Different mechanism for storing map size

4. POINTER USAGE:
   New Format: Pointers at 0x40 and 0x44 are typically NULL
               Pointers at 0x48-0x54 point to actual data sections
               All pointers are unsigned 32-bit integers
   Old Format: Pointers at 0x40 and 0x44 contain float value 1.0 (not pointers!)
               Pointers at 0x48-0x54 point to data sections
               Pointers are stored as unsigned integers despite header confusion

5. DATA AFTER HEADER (0x60 - first pointer):
   New Format: Padding of zero bytes until PTR5
   Old Format: Similar padding to PTR5
   Similarity: Both have padding/reserved space after header

6. DATA SECTION SIZES:
   New Format: PTR5 typically larger (~2,400+ bytes)
               PTR6 very large (often 90,000+ bytes)
   Old Format: PTR5 smaller (~700 bytes with actual data)
               PTR6 also large but structured differently
   
   Example (BRADLEY.SCN new vs CLASH.SCN old):
   PTR5: 2,396 bytes → 685 bytes (3.5x difference)
   PTR6: 93,139 bytes → 90,654 bytes (similar range)


PART 4: PARSING CODE REFERENCE
================================================================================

The file scenario_parser.py contains a DdayScenario class that parses
the NEW FORMAT (0x1230). Key implementation details:

```python
class DdayScenario:
    MAGIC_NUMBER = 0x1230
    MAGIC_BYTES = b'\x30\x12\x00\x00'
    HEADER_SIZE = 0x60  # 96 bytes
    
    # Fixed counts (always these values in new format)
    FIXED_COUNTS = [0x11, 0x05, 0x0a, 0x08, 0x05, 0x08, 0x00,
                    0x0a, 0x14, 0x05, 0x7d, 0x64]
    
    # Offset positions for the 12 counts
    COUNT_OFFSETS = [0x04, 0x08, 0x0c, 0x10, 0x14, 0x18, 0x1c,
                     0x20, 0x24, 0x28, 0x2c, 0x30]
    
    # Offset positions for 8 pointers
    POINTER_OFFSETS = {
        'PTR1': 0x40,
        'PTR2': 0x44,
        'PTR3': 0x48,  # Unit roster
        'PTR4': 0x4c,  # Unit positioning
        'PTR5': 0x50,  # Numeric data
        'PTR6': 0x54,  # Specialized data
        'PTR7': 0x58,
        'PTR8': 0x5c,
    }
    
    @property
    def map_height(self) -> int:
        return self.counts[10]  # Count 11 at offset 0x2c
    
    @property
    def map_width(self) -> int:
        return self.counts[11]  # Count 12 at offset 0x30
```

IMPORTANT NOTE: The data sections are not in header order!
File order is typically: PTR5 → PTR6 → PTR3 → PTR4
Section boundaries must be calculated from file position.


PART 5: CONVERSION STRATEGY (High-Level)
================================================================================

For converting OLD FORMAT files to NEW FORMAT:

1. HEADER CONVERSION:
   - Change magic from 0x0f4a/0x0dac to 0x1230
   - Convert float counts to fixed integer counts:
     * Counts 1-10: Use FIXED_COUNTS array
     * Counts 11-12: Determine map dimensions from data analysis
   - Zero out unknown float fields
   - Recalculate pointers if data is reorganized

2. DATA SECTION HANDLING:
   - Preserve PTR5 and PTR6 content (may require reformatting)
   - Preserve PTR3 and PTR4 content (unit data and text)
   - Reorganize if necessary to match expected file order

3. POINTER RECALCULATION:
   - After reorganizing sections, recalculate all pointers
   - Point from actual byte offsets in file
   - Ensure PTR5 comes before PTR6

4. VALIDATION:
   - Verify magic number is 0x1230
   - Verify counts match FIXED_COUNTS (except 11-12)
   - Verify map dimensions (counts 11-12) are reasonable
   - Verify all pointers point within file bounds


PART 6: CRITICAL IMPLEMENTATION NOTES
================================================================================

1. INTEGER VS FLOAT PARSING:
   Do NOT assume counts are integers - parse as floats first in old format.
   In new format, always parse as unsigned 32-bit integers.

2. BYTE ORDER:
   All multi-byte values use little-endian byte order.
   Example: 0x77 0x7C 0x01 0x00 = 0x017C77

3. POINTER FILE ORDERING:
   File order is NOT header order! Must parse actual file offset order:
   New format typically: PTR5 (smallest) → PTR6 → PTR3 → PTR4 (largest)

4. SECTION BOUNDARIES:
   Section end = start of next section (or EOF)
   Cannot trust header-provided sizes; calculate from pointer sequence

5. MAP DIMENSIONS:
   New format: Counts 11-12 are definitive (125x100 is standard)
   Old format: Must determine from data content or markers within sections

6. DATA PRESERVATION:
   Ensure mission briefing text is preserved (usually in PTR4 or PTR6)
   Ensure unit names and positions are preserved (PTR3, PTR4)
   Ensure AI/scripting data is preserved (PTR6)


PART 7: SPECIFIC CONVERSION EXAMPLES
================================================================================

Example 1: Convert simple file (CLASH.SCN - 0x0f4a → 0x1230)
-----------------------------------------------------------

Old file structure:
- Size: 47,634 bytes
- Header: 0x000000-0x00005F (96 bytes)
- PTR5: 0x000AE0-0x000D8D (685 bytes)
- PTR6: 0x000D8D-0x016FAB (90,654 bytes)
- PTR3: 0x016FAB-0x016FC1 (22 bytes)
- PTR4: 0x016FC1-0x02A8D2 (remaining bytes) [NOTE: actual file ends before this]

New file should have:
- New header with magic 0x1230
- New counts: [17, 5, 10, 8, 5, 8, 0, 10, 20, 5, ?, ?]
  (Counts 11-12 need to be determined from data)
- Preserved data sections
- Recalculated pointers

Example 2: CAMPAIGN.SCN differences
------------------------------------

New version: 276,396 bytes
Old version: 274,044 bytes
Difference: +2,352 bytes (0.9% larger)

This suggests:
- Some data was added or reformatted
- Possibly additional AI scripting data
- Possibly expanded mission briefing text
- Possibly reorganized sections with padding


PART 8: SUMMARY TABLE OF KEY VALUES
================================================================================

Property                  NEW (0x1230)          OLD (0x0f4a/0x0dac)
-------                  ---------------       ------------------
Magic Number             0x1230                0x0f4a or 0x0dac
Count Type               uint32                float32
Count 1                  17 (fixed)            6-7 (variable)
Count 2                  5 (fixed)             5 (usually)
Counts 11-12             Map H × W             Not map dimensions
Reserved Bytes           0x34-0x3F all zero    Floats (confusing!)
PTR1                     NULL or uint32        float 1.0
PTR2                     NULL or uint32        float 1.0
PTR3-PTR6                Pointer values        Pointer values
Data Order in File       PTR5→PTR6→PTR3→PTR4   Varies
Header Validation        Fixed counts check    Float value check
Map Dimension Source     Count 11-12           Internal data markers

================================================================================
END OF REPORT
================================================================================
