# V for Victory Scenario Converter

## Overview

This tool converts legacy V for Victory scenario files from older games (Stalingrad, Crusader) to the newer D-Day format, allowing them to be used in the D-Day game engine.

## Format Details

### Supported Formats

| Format | Magic | Game | Status |
|--------|-------|------|--------|
| **0x1230** | New format | D-Day (1995) | ✅ Target format |
| **0x0f4a** | Old format | V for Victory: Stalingrad (1993) | ✅ Fully supported |
| **0x0dac** | Old format | V for Victory: Crusader (1992) | ✅ Fully supported |

### Key Differences

The converter handles these critical format differences:

**Stalingrad Format (0x0f4a):**
1. **Magic Number**: Changes from `0x0f4a` → `0x1230`
2. **Header Counts**: Converts `float32` → `uint32` with fixed configuration values
3. **Map Dimensions**: Adds map height/width to counts 11-12 (defaults to 125×100)
4. **Pointer Semantics**: Converts float placeholder values to NULL pointers
5. **Data Preservation**: Preserves all game data sections (PTR3-PTR6)

**Crusader Format (0x0dac):**
1. **Magic Number**: Changes from `0x0dac` → `0x1230`
2. **Data Access**: Converts from fixed-offset layout to pointer-based layout
3. **Configuration Data**: Extracts configuration from 0x60-0x7F area
4. **Text Sections**: Extracts text from 128-byte aligned blocks (0x80, 0x100, etc.)
5. **Binary Data**: Preserves game data starting at ~0x1000

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

### Successfully Converted (ALL 16 Legacy Scenarios!)

#### Stalingrad Scenarios (0x0f4a format) - 10 scenarios

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

#### Crusader Scenarios (0x0dac format) - 6 scenarios

| Scenario | Original Size | Converted Size | Description |
|----------|--------------|----------------|-------------|
| **CRUCAMP.SCN** | 168 KB | 165 KB | Operation Crusader - Full campaign |
| **DUCE.SCN** | 27 KB | 28 KB | Bir el Gubi - Italian armor battle |
| **HELLFIRE.SCN** | 60 KB | 60 KB | Halfaya Pass assault |
| **RELIEVED.SCN** | 160 KB | 157 KB | After Tobruk relief |
| **RESCUE.SCN** | 54 KB | 54 KB | Sidi Rezegh armor clash |
| **TOBRUK.SCN** | 40 KB | 40 KB | Direct assault on fortress |

✅ **Note**: Crusader format (0x0dac) is now fully supported! The converter handles the unique fixed-offset data layout and converts it to pointer-based D-Day format.

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

1. **Map Dimensions**: Old formats (both Stalingrad and Crusader) don't store map dimensions in the header. The converter uses reasonable defaults (125×100) which work for most scenarios. Override with `--height` and `--width` flags if needed.

2. **Unit Types**: Unit type mappings between games may differ. Converted scenarios should be tested in-game to verify unit appearances and behaviors.

3. **Data Layout Differences**: Crusader format uses fixed offsets while D-Day uses pointers. The converter extracts and reorganizes the data, but some subtle data relationships might not be perfectly preserved.

4. **In-Game Testing**: All converted scenarios should be tested in the actual D-Day game engine to verify complete compatibility.

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
- Check that the file is a valid .SCN scenario file

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

1. **Automatic Map Detection**: Analyze data sections to detect actual map dimensions from game data
2. **Unit Mapping**: Create unit type translation tables between games (Soviets → Allies, etc.)
3. **Enhanced Validation**: Automated in-game testing and verification of converted scenarios
4. **Mission Text Extraction**: Parse and display mission briefings from both formats
5. **Batch Analysis**: Generate detailed reports comparing scenarios across different games

## Credits

Converter created based on comprehensive analysis of V for Victory scenario formats:
- D-Day (1995) - Format 0x1230
- Stalingrad (1993) - Format 0x0f4a
- Crusader (1992) - Format 0x0dac

All reverse engineering work done from binary analysis of scenario files.
