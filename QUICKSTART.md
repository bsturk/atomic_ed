# Quick Start Guide - Improved Scenario Editor

## Installation

### Requirements
- Python 3.x
- tkinter (usually included with Python)
- Game scenario files in `game/SCENARIO/` directory

### Verify Installation
```bash
# Check Python version
python3 --version

# Check if tkinter is available
python3 -c "import tkinter; print('tkinter OK')"
```

## Launch the Editor

### Method 1: With a Scenario File
```bash
python3 dday_scenario_editor_improved.py game/SCENARIO/OMAHA.SCN
```

### Method 2: Use File Menu
```bash
python3 dday_scenario_editor_improved.py
# Then: File > Open Scenario...
```

## Quick Tutorial

### 1. Open a Scenario
- Click **Open** button or press `Ctrl+O`
- Navigate to `game/SCENARIO/`
- Select a .SCN file (try OMAHA.SCN or BRADLEY.SCN)
- Click Open

### 2. View the Map (Tab 2)
- Click **Map Viewer** tab
- See your scenario laid out on a grid
- Adjust **Grid Size** for zoom
- Click **Refresh** to redraw

### 3. Edit Units (Tab 3)
- Click **Unit Editor** tab
- Left side: List of all units
- Right side: Properties for selected unit
- Select a unit from the list
- Modify properties in the form:
  - Name
  - Type
  - Position X/Y
  - Strength (0-100)
  - Side (Allied/Axis)
- Click **Apply Changes**

### 4. Edit Mission Briefings (Tab 1)
- Click **Mission Briefings** tab
- Left side: Allied briefing
- Right side: Axis briefing
- Edit text as needed
- Changes saved when you save the scenario

### 5. Adjust Scenario Settings (Tab 5)
- Click **Scenario Settings** tab
- Modify:
  - Scenario name
  - Turn limit
  - Difficulty
  - Weather
  - Victory conditions
- Click **Apply Settings**

### 6. Save Your Work
- Click **Save** button or press `Ctrl+S`
- A backup is created automatically
- Currently saves mission briefings

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| Ctrl+O | Open scenario file |
| Ctrl+S | Save changes |
| F5 | Reload current scenario |

## Tips

1. **Always Keep Backups**
   - The editor creates automatic backups when saving
   - Keep original .SCN files safe

2. **Start with Simple Scenarios**
   - Begin with BRADLEY.SCN (smallest)
   - Move to OMAHA.SCN (medium)
   - Try CAMPAIGN.SCN (largest) when comfortable

3. **Use Data Viewer**
   - Tab 4 shows interpreted scenario data
   - Helps understand what's in the scenario

4. **Mission Briefings Work Best**
   - This feature is fully functional
   - Safe to edit and save

5. **Other Features Are Preview**
   - Unit editing, map editing, settings need more work
   - UI is ready, full save functionality coming

## Common Tasks

### Edit Mission Text
1. Open scenario
2. Go to **Mission Briefings** tab
3. Edit Allied or Axis text
4. Press Ctrl+S to save

### View All Units
1. Open scenario
2. Go to **Unit Editor** tab
3. Browse list of units
4. Select to see properties

### Export Unit List
1. Open scenario
2. Menu: **Tools > Export Unit List**
3. Choose save location
4. Get text file with all units

### See Scenario Structure
1. Open scenario
2. Go to **Data Viewer** tab
3. Review sections, units, coordinates

## Troubleshooting

### "No module named 'tkinter'"
- Install tkinter:
  - **Ubuntu/Debian**: `sudo apt-get install python3-tk`
  - **Fedora**: `sudo dnf install python3-tkinter`
  - **macOS**: Usually included with Python

### "Invalid scenario file format"
- File may be corrupted
- Check magic number is 0x1230
- Try opening in original editor for diagnosis

### Changes Not Saved
- Some features are work-in-progress
- Currently only mission briefings save fully
- Other features need complete format decode

### Editor Looks Different
- This is the **improved** editor
- Original is still available: `dday_scenario_creator.py`
- Both work with same scenario files

## Next Steps

1. **Read Full Documentation**
   - See `SCENARIO_EDITOR_IMPROVEMENTS.md` for details
   - Review feature comparison table

2. **Check Format Documentation**
   - `txt/D_DAY_FORMAT_FINAL_SUMMARY.txt` - Complete format spec
   - `txt/SCENARIO_EDITOR_IMPLEMENTATION_GUIDE.md` - Developer guide

3. **Experiment Safely**
   - Make copies of scenario files
   - Test edits on backups first
   - Original files are in `game/SCENARIO/`

4. **Report Issues**
   - Note what doesn't work
   - Check format documentation
   - Some features awaiting full decode

## What Works Right Now

| Feature | Status |
|---------|--------|
| Opening scenarios | ✓ Fully working |
| Viewing map | ✓ Fully working |
| Viewing units | ✓ Fully working |
| Editing mission text | ✓ Fully working & saving |
| Viewing unit properties | ✓ Fully working |
| Editing unit properties | ○ UI works, save pending |
| Scenario settings | ○ UI works, save pending |
| Add/delete units | ○ UI ready, needs format |

**Legend**: ✓ Complete, ○ Partial/UI ready

## Example Session

```bash
# Open the editor
python3 dday_scenario_editor_improved.py

# File > Open Scenario > select OMAHA.SCN

# Tab 2 (Map Viewer):
#   - See visual layout
#   - Adjust grid size to 25

# Tab 3 (Unit Editor):
#   - Select first unit
#   - View its properties
#   - Change strength to 80

# Tab 1 (Mission Briefings):
#   - Edit Allied briefing
#   - Add new objective

# Ctrl+S to save
# Backup created: OMAHA.20251107_123456.bak

# Tab 4 (Data Viewer):
#   - Review changes
#   - Check unit count

# Tools > Export Unit List
#   - Save as units.txt

# Done!
```

## Support

For more information:
- **Full documentation**: `SCENARIO_EDITOR_IMPROVEMENTS.md`
- **Format specification**: `txt/D_DAY_FORMAT_FINAL_SUMMARY.txt`
- **Implementation guide**: `txt/SCENARIO_EDITOR_IMPLEMENTATION_GUIDE.md`

Happy scenario editing!
