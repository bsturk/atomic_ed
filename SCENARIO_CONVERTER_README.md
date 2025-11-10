# V for Victory Scenario Converter

## Overview

This tool converts legacy V for Victory scenario files from older games (Stalingrad, Crusader) to the newer D-Day format, allowing them to be used in the D-Day game engine.

## Format Details

### Supported Formats

| Format | Magic | Game | Status |
|--------|-------|------|--------|
| **0x1230** | New format | D-Day (1995) | ✅ Target format |
| **0x0f4a** | Old format | V for Victory: Stalingrad (1993) | ✅ Fully supported |
| **0x0dac** | Old format | V for Victory: Crusader (1992) | ⚠️ Limited support |

### Key Differences

The converter handles these critical format differences:

1. **Magic Number**: Changes from `0x0f4a`/`0x0dac` → `0x1230`
2. **Header Counts**: Converts `float32` → `uint32` with fixed configuration values
3. **Map Dimensions**: Adds map height/width to counts 11-12 (defaults to 125×100)
4. **Pointer Semantics**: Converts float placeholder values to NULL pointers
5. **Data Preservation**: Preserves all game data sections (PTR3-PTR6)

## Usage

### Convert a Single File

```bash
python3 scenario_converter.py game/SCENARIO-prev/CITY.SCN -o game/scenarios/CITY.SCN
```

### Batch Convert a Directory

```bash
python3 scenario_converter.py game/SCENARIO-prev/ -d game/scenarios/
```

### Dry Run (Preview Without Writing)

```bash
python3 scenario_converter.py game/SCENARIO-prev/ --dry-run
```

### Override Map Dimensions

```bash
python3 scenario_converter.py input.SCN -o output.SCN --height 112 --width 100
```

### Verbose Output

```bash
python3 scenario_converter.py input.SCN -o output.SCN -v
```

## Command-Line Options

```
positional arguments:
  input                 Input scenario file or directory

optional arguments:
  -h, --help            Show help message and exit
  -o OUTPUT, --output OUTPUT
                        Output scenario file
  -d OUTPUT_DIR, --output-dir OUTPUT_DIR
                        Output directory (for batch conversion)
  --height HEIGHT       Override map height (in hexes)
  --width WIDTH         Override map width (in hexes)
  --dry-run            Show what would be converted without writing files
  -v, --verbose        Verbose output with detailed logging
```

## Conversion Results

### Successfully Converted (10 Stalingrad Scenarios)

These scenarios converted successfully from 0x0f4a format:

| Scenario | Original Size | Converted Size | Description |
|----------|--------------|----------------|-------------|
| **CAMPAIGN.SCN** | 274 KB | 258 KB | Operation Uranus - Complete Soviet encirclement |
| **CITY.SCN** | 117 KB | 110 KB | Battle of Stalingrad - Urban factory combat |
| **CLASH.SCN** | 47 KB | 44 KB | Operation Wintergewitter - Myshkova River crossing |
| **HURBERT.SCN** | 41 KB | 40 KB | Battle of Stalingrad - Hubert's factory assault |
| **MANSTEIN.SCN** | 63 KB | 60 KB | Operation Uranus - Hypothetical Manstein counter |
| **QUIET.SCN** | 106 KB | 100 KB | Operation Uranus - Soviet breakthrough |
| **RIVER.SCN** | 47 KB | 44 KB | Operation Wintergewitter - German relief attempt |
| **TANKS.SCN** | 63 KB | 60 KB | Operation Uranus - Hypothetical tank battle |
| **VOLGA.SCN** | 41 KB | 40 KB | Battle of Stalingrad - Drive to the Volga |
| **WINTER.SCN** | 192 KB | 181 KB | Operation Wintergewitter - Full winter campaign |

### Partially Converted (6 Crusader Scenarios)

These scenarios use the 0x0dac format which has a different structure. Conversion produces valid headers but data extraction is incomplete:

- CRUCAMP.SCN
- DUCE.SCN
- HELLFIRE.SCN
- RELIEVED.SCN
- RESCUE.SCN
- TOBRUK.SCN

⚠️ **Note**: Crusader scenarios require additional reverse engineering to fully support the 0x0dac format structure.

### Already Converted

- **COUNTER.SCN** - Already in D-Day format (0x1230), identical in both directories

## Validation

To verify a converted scenario file:

```bash
python3 scenario_parser.py game/scenarios/CITY.SCN
```

This will display:
- Magic number validation
- Header counts verification
- Pointer locations
- Data section information
- Extracted text strings

## Technical Details

### Conversion Process

1. **Read Legacy File**
   - Parse magic number (0x0f4a or 0x0dac)
   - Extract float counts from header
   - Parse pointer offsets
   - Extract data sections (PTR3-PTR6)

2. **Transform Data**
   - Convert magic to 0x1230
   - Replace float counts with fixed integer configuration
   - Determine map dimensions (defaults to 125×100)
   - Set PTR1/PTR2 to NULL

3. **Write New Format**
   - Build new header with integer counts
   - Recalculate section pointers
   - Write data in D-Day order: PTR5 → PTR6 → PTR3 → PTR4
   - Validate output

### Data Section Order

New format typically uses this order in the file:
- Header (0x00-0x5F): 96 bytes
- PTR5: Numeric/coordinate data
- PTR6: Specialized/AI data
- PTR3: Unit roster
- PTR4: Unit positioning + mission text

### Map Dimensions

The converter uses these defaults:
- **Stalingrad (0x0f4a)**: 125 rows × 100 columns (standard)
- **Crusader (0x0dac)**: 125 rows × 100 columns (standard)

You can override these with `--height` and `--width` flags.

## Known Limitations

1. **Crusader Format (0x0dac)**: Data structure is different and not fully understood. Conversions produce valid headers but incomplete data.

2. **Map Dimensions**: Old formats don't store map dimensions in the header. The converter uses reasonable defaults (125×100) which work for most scenarios.

3. **PTR5 Data**: In the old format, PTR5 is typically ~700 bytes. In the new format, PTR5 is usually ~2,400 bytes. The converter preserves the original data, which may need adjustment for full compatibility.

4. **Unit Types**: Unit type mappings between games may differ. Converted scenarios should be tested in-game to verify unit appearances.

## Troubleshooting

### "Unsupported magic number"
- The file is not a recognized V for Victory scenario format
- Check that you're converting from a .SCN file

### "File too small"
- The file is corrupted or truncated
- Minimum file size is 96 bytes (header size)

### "Failed to parse"
- The file structure doesn't match expected format
- May be from an unsupported game version

### Converted file is only 96 bytes
- This happens with Crusader (0x0dac) format files
- Data extraction is not working for this format
- Manual conversion may be required

### Scenario doesn't load in game
- Verify with `scenario_parser.py` first
- Check that map dimensions are reasonable
- Test in the actual game engine

## Files Created

The converter produces the following in the repository:

- `scenario_converter.py` - Main conversion tool
- `game/scenarios/` - Directory with converted Stalingrad scenarios
- `SCENARIO_CONVERTER_README.md` - This documentation

## Background Research

For detailed analysis of the format differences, see:
- `txt/CROSS_GAME_SCENARIO_ANALYSIS.md` - Comprehensive format comparison
- `SCENARIO_FORMAT_ANALYSIS.md` - Technical format specifications
- `SCENARIO_FILE_REFERENCE.md` - Quick reference guide
- `scenario_parser.py` - D-Day format parser implementation

## Future Improvements

1. **Full 0x0dac Support**: Reverse engineer the Crusader format data structure
2. **Automatic Map Detection**: Analyze data sections to detect actual map dimensions
3. **Unit Mapping**: Create unit type translation tables between games
4. **Data Transformation**: Handle PTR5 data expansion/transformation
5. **Validation**: In-game testing and adjustment of converted scenarios

## Credits

Converter created based on comprehensive analysis of V for Victory scenario formats:
- D-Day (1995) - Format 0x1230
- Stalingrad (1993) - Format 0x0f4a
- Crusader (1992) - Format 0x0dac

All reverse engineering work done from binary analysis of scenario files.
