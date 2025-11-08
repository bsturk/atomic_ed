# D-Day Scenario Creator/Editor

A comprehensive graphical scenario creator and editor for World at War: D-Day scenario files using Python and tkinter.

## Features

### 📊 Overview Tab
- Display scenario header information
- Show file statistics (size, zero bytes, data density)
- List all data sections with offsets and sizes
- Validate scenario format

### 📝 Mission Briefings Tab
- Side-by-side editor for Allied and Axis mission briefings
- Real-time editing with undo/redo support
- Text interleaving preserved automatically
- Character limit warnings

### ⚔️ Unit Roster Tab
- View all units defined in the scenario (PTR3 section)
- Display unit names, type codes, and binary data
- Sortable and searchable unit list
- Unit statistics

### 📍 Coordinates Tab
- View coordinate data from PTR5 section
- Display as 16-bit integers with hex and decimal values
- Useful for understanding unit positions and map data

### 🎮 PTR6 Data Tab
- Hex viewer for specialized/AI data section
- Navigate through sparse data regions
- Identify non-zero data areas

### 🔍 Hex Viewer Tab
- View any section in hexadecimal format
- Toggle between Header, PTR3, PTR4, PTR5, PTR6, and Full File
- Classic hex dump format with ASCII preview
- Offset addresses for precise navigation

## Additional Tools

### Search
- Search for strings across all data sections
- Display results with offset, section, and preview
- Case-insensitive search
- Export search results

### Validation
- Validate scenario format against D-Day specification
- Check magic number (0x1230)
- Verify header counts
- Validate pointer offsets

### Backup Management
- Automatic timestamped backups on save
- Backup browser to view and restore previous versions
- Backup size and date information

### String Extraction
- Extract all ASCII strings from scenario
- Minimum length filtering
- Export to text file
- Useful for localization

## Requirements

- Python 3.8 or higher
- tkinter (usually included with Python)
- `scenario_parser.py` (included)

## Installation

```bash
# No installation needed - just run the script
python3 scenario_creator.py
```

## Usage

### Opening a Scenario

**Method 1: Command line**
```bash
python3 scenario_creator.py game/SCENARIO/OMAHA.SCN
```

**Method 2: File menu**
1. Launch the editor: `python3 scenario_creator.py`
2. Click "File → Open Scenario..." or press `Ctrl+O`
3. Navigate to `game/SCENARIO/` directory
4. Select a .SCN file

### Editing Mission Briefings

1. Open a scenario file
2. Navigate to the "📝 Mission Briefings" tab
3. Edit the Allied briefing (left panel) or Axis briefing (right panel)
4. Click "Apply & Save" or press `Ctrl+S`
5. A backup is automatically created with timestamp

### Viewing Units

1. Open a scenario file
2. Navigate to the "⚔️ Unit Roster" tab
3. Browse the list of units
4. See unit names, type codes, and hex data

### Hex Viewing

1. Open a scenario file
2. Navigate to the "🔍 Hex Viewer" tab
3. Select a section to view (Header, PTR3, PTR4, PTR5, PTR6, or Full File)
4. Browse the hex dump with ASCII representation

### Searching

1. Click "Edit → Search Strings..." or press the 🔍 button
2. Enter search text
3. Click "Find All"
4. Results show offset, section, and text preview

## File Format

The editor works with D-Day scenario files (.SCN) with the following structure:

```
Magic Number: 0x1230
Header Size: 96 bytes (0x60)

Structure:
┌─────────────────────────────────────┐
│ Header (0x00-0x5F)                 │
│ - Magic number                      │
│ - 12 count fields (fixed)           │
│ - 8 offset pointers                 │
├─────────────────────────────────────┤
│ Pre-section data (0x60-PTR5)       │
│ - Mission briefing text             │
│ - Interleaved Allied/Axis           │
├─────────────────────────────────────┤
│ PTR5: Numeric/Coordinate Data      │
│ - 16/32-bit integers                │
│ - Coordinates, stats                │
├─────────────────────────────────────┤
│ PTR6: Specialized/AI Data          │
│ - Mostly sparse (zeros)             │
│ - Scenario-specific features        │
├─────────────────────────────────────┤
│ PTR3: Unit Roster                  │
│ - Unit definitions                  │
│ - Names, types, codes               │
├─────────────────────────────────────┤
│ PTR4: Unit Positioning + Text      │
│ - Unit instances                    │
│ - Additional mission text           │
│ - Location names                    │
└─────────────────────────────────────┘
```

## Keyboard Shortcuts

- `Ctrl+O` - Open scenario
- `Ctrl+S` - Save scenario
- `Ctrl+N` - New scenario
- `F5` - Reload current scenario

## Safety Features

### Automatic Backups
Every save operation creates a timestamped backup:
```
OMAHA.20251107_143022.bak
```

### Validation
Before saving, the editor validates:
- Magic number integrity
- Header counts (must match fixed values)
- Pointer offsets within bounds
- Section ordering

### Modification Tracking
- Modified indicator in status bar
- Confirmation dialogs for destructive operations
- Revert functionality for mission text

## Available Scenarios

The editor works with all 7 D-Day scenarios:

1. **OMAHA.SCN** (137 KB) - Omaha Beach landing
2. **UTAH.SCN** (172 KB) - Utah Beach landing
3. **BRADLEY.SCN** (31 KB) - Bradley scenario
4. **COUNTER.SCN** (31 KB) - Counter-offensive
5. **COBRA.SCN** (153 KB) - Operation Cobra
6. **STLO.SCN** (47 KB) - St. Lo scenario
7. **CAMPAIGN.SCN** (270 KB) - Full campaign

## Tips and Best Practices

### Mission Text Editing
- Keep text under 127 characters per line
- Use ASCII characters only (no Unicode)
- The game displays text in fixed-width font
- Test in-game after editing

### Unit Editing
- PTR3 unit data is tightly packed binary
- Changing unit count requires updating header (not recommended)
- Safer to modify existing units than add/remove

### Backup Strategy
- Always test changes on backup copies first
- Keep original .SCN files pristine
- Use "Save As" to create variants

### Testing Changes
1. Edit scenario
2. Save with backup
3. Copy to game directory
4. Test in DOSBox
5. Verify scenario loads and plays correctly

## Troubleshooting

### "Invalid scenario file format"
- Check magic number is 0x1230
- Verify file is not corrupted
- Try another scenario to test editor

### "Failed to save scenario"
- Check file permissions
- Ensure enough disk space
- Verify scenario is valid

### Mission text not displaying in-game
- Text may be too long (max ~127 chars)
- Check for non-ASCII characters
- Verify text is null-padded correctly

### Game crashes on loading
- Restore from backup
- Validate scenario format
- Check header counts unchanged
- Verify pointer offsets

## Technical Details

### Parser
The editor uses `scenario_parser.py` which:
- Validates magic number (0x1230)
- Parses 12 fixed header counts
- Reads 8 offset pointers (4 active, 4 null)
- Extracts data sections in file order
- Preserves unknown binary data

### Data Sections

**PTR5 (Numeric Data)**
- Size: 1-3 KB
- Contains coordinates, numeric values
- 16-bit and 32-bit integers
- Map positions, unit stats

**PTR6 (Specialized)**
- Size: 2-90 KB
- Mostly sparse (zeros)
- AI data, fog of war, objectives
- Highly variable by scenario

**PTR3 (Unit Roster)**
- Size: 100-200 bytes
- Unit definitions
- Names like "III-5-3FJ", "B-801-VII"
- Type codes and flags

**PTR4 (Unit Positioning)**
- Size: 40-180 KB
- Unit instance data
- Additional mission text
- Location names

## Development

### Architecture
- `DdayScenario` class: Core parser
- `DdayScenarioCreator` class: GUI application
- Widget classes: `HexViewer`, `UnitEditor`, `CoordinateViewer`, `StringSearcher`

### Extending
To add features:
1. Add new tab to notebook
2. Create widget class
3. Implement data loading method
4. Add to `_load_scenario_data()`

# Test editor (requires display)
python3 scenario_creator.py game/SCENARIO/UTAH.SCN
```

## References

- **D_DAY_FORMAT_FINAL_SUMMARY.txt** - Complete format specification
- **SCENARIO_EDITOR_IMPLEMENTATION_GUIDE.md** - Development guide
- **invade.txt** - D-Day disassembly (27,915 lines)

## Version History

### Version 1.0 (2025-11-07)
- Initial release
- Mission text editor
- Unit roster viewer
- Hex viewer
- Coordinate viewer
- String search
- Validation
- Backup management

## License

Created for research and educational purposes.

## Credits

Format reverse-engineered from 7 D-Day scenario files (852 KB analyzed).

## Support

For issues or questions, refer to:
- Format documentation in `txt/` directory
- Parser source code: `scenario_parser.py`
- Implementation guide: `txt/SCENARIO_EDITOR_IMPLEMENTATION_GUIDE.md`

---

**Happy scenario editing!** 🎮
