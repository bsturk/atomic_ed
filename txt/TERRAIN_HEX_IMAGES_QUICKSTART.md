# Terrain Hex Images - Quick Start Guide

## Overview

The D-Day Scenario Editor now uses **actual game graphics** from the original PCWATW.REZ resource file instead of simple colored hexagons!

## What's New?

### Map Viewer
- ✅ Displays authentic 34×38 pixel hex tile images
- ✅ Automatically scales with zoom level
- ✅ 17 different terrain types with unique textures
- ✅ Extracted from original game assets

### Terrain Reference Tab
- ✅ Shows 60×68 pixel previews of actual hex tiles
- ✅ Each terrain type displays with game graphics
- ✅ Improved visual identification

## How It Works

1. **Automatic Loading**
   - Editor checks for `hex_tile_config.json` on startup
   - If found, loads 17 base hex tile images
   - Scales images dynamically based on zoom level

2. **Graceful Fallback**
   - If images not available, uses colored hexagons
   - No functionality lost - purely visual enhancement
   - Works in both graphical and headless environments

## File Locations

```
/home/user/atomic_ed/
├── hex_tile_config.json              ← Configuration (required)
├── extracted_images/
│   └── hex_tiles/
│       ├── hex_tile_000.png          ← Grass/Field
│       ├── hex_tile_013.png          ← Water/Ocean
│       ├── hex_tile_026.png          ← Beach/Sand
│       ├── hex_tile_039.png          ← Forest
│       ├── hex_tile_052.png          ← Town
│       ├── hex_tile_065.png          ← Road
│       ├── hex_tile_078.png          ← River
│       ├── hex_tile_091.png          ← Mountains
│       ├── hex_tile_104.png          ← Swamp
│       ├── hex_tile_117.png          ← Bridge
│       ├── hex_tile_130.png          ← Fortification
│       ├── hex_tile_143.png          ← Bocage
│       ├── hex_tile_156.png          ← Cliff
│       ├── hex_tile_169.png          ← Village
│       ├── hex_tile_182.png          ← Farm
│       └── ... (195 total tiles)
└── scenario_editor.py                ← Updated editor
```

## Terrain Type → Tile Mapping

| ID | Terrain Type     | Image File         | Description                    |
|----|------------------|--------------------|--------------------------------|
| 0  | Grass/Field      | hex_tile_000.png   | Light green fields             |
| 1  | Water/Ocean      | hex_tile_013.png   | Blue water                     |
| 2  | Beach/Sand       | hex_tile_026.png   | Sandy beaches                  |
| 3  | Forest           | hex_tile_039.png   | Dark green trees               |
| 4  | Town             | hex_tile_052.png   | Gray urban areas               |
| 5  | Road             | hex_tile_065.png   | Brown roads                    |
| 6  | River            | hex_tile_078.png   | Blue waterways                 |
| 7  | Mountains        | hex_tile_091.png   | Gray/brown peaks               |
| 8  | Swamp            | hex_tile_104.png   | Olive marshland                |
| 9  | Bridge           | hex_tile_117.png   | Bridge structures              |
| 10 | Fortification    | hex_tile_130.png   | Defensive positions            |
| 11 | Bocage           | hex_tile_143.png   | Hedgerows (Normandy)           |
| 12 | Cliff            | hex_tile_156.png   | Steep terrain                  |
| 13 | Village          | hex_tile_169.png   | Small settlements              |
| 14 | Farm             | hex_tile_182.png   | Agricultural land              |
| 15 | Canal            | hex_tile_078.png   | Canals (reuses River)          |
| 16 | Unknown          | hex_tile_000.png   | Default (reuses Grass)         |

## Usage

### Running the Editor

```bash
# With a scenario file
python3 scenario_editor.py game/SCENARIO/UTAH.SCN

# Without (will prompt for file)
python3 scenario_editor.py
```

### Zoom Controls
- **Zoom In:** Click "+ Zoom In" button
- **Zoom Out:** Click "- Zoom Out" button
- **Reset:** Click "Reset View" button
- **Mouse Wheel:** Scroll to zoom (if supported)

Hex tiles automatically scale to match zoom level!

### Grid Toggle
- **Show Grid:** Displays hex outlines over images
- **Hide Grid:** Shows only terrain images

## Testing

Verify hex tiles load correctly:

```bash
python3 test_hex_tiles.py
```

Expected output:
```
Testing hex tile loading...
✓ Terrain  0 (Grass/Field): hex_tile_000.png (34x38, P)
✓ Terrain  1 (Water/Ocean): hex_tile_013.png (34x38, P)
...
✓ All hex tiles loaded successfully!
```

## Troubleshooting

### Images Not Showing

**Problem:** Map shows colored hexagons instead of images

**Solutions:**
1. Check `hex_tile_config.json` exists in project root
2. Verify `extracted_images/hex_tiles/` directory exists
3. Ensure all 17 terrain tile PNGs are present
4. Check console output for error messages

### Missing Dependencies

**Problem:** `ModuleNotFoundError: No module named 'PIL'`

**Solution:**
```bash
pip3 install Pillow
```

### Display Issues

**Problem:** Images appear blurry or pixelated

**Explanation:** Images use LANCZOS resampling for quality, but very small/large zoom levels may show artifacts. This is normal.

## Performance Notes

- **Memory Usage:** Images are cached after first scaling
- **Initial Load:** ~17 base images loaded on startup
- **Runtime:** Images scaled on-demand as you zoom
- **Cache:** Automatically managed, grows with zoom level variety

## Source Information

**Original Asset:** `game/DATA/PCWATW.REZ` (5.3 MB)
**Extraction Date:** 2025-11-08
**Format:** Converted from Apple PICT v2 to PNG
**Resolution:** 34×38 pixels per hex tile
**Total Tiles Extracted:** 195 (13 columns × 15 rows sprite sheet)

## Credits

- **Original Game:** D-Day: June 6, 1944 (Atomic Games)
- **Resource File:** PCWATW.REZ (Mac version)
- **Extraction Tools:** Custom Python scripts using PIL/Pillow
- **Integration:** Claude (AI Assistant)

## Further Reading

- `HEX_TILE_EXTRACTION_REPORT.md` - Complete technical report
- `REZ_ANALYSIS_REPORT.md` - Resource file analysis
- `PICT_CONVERSION_REPORT.md` - Image format conversion details
- `scenario_editor.py` - Source code with comments

---

**Questions or issues?** Check the comprehensive documentation in `txt/HEX_TILE_EXTRACTION_REPORT.md`
