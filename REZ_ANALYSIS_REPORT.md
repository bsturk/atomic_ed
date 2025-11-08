# PCWATW.REZ Resource Fork Analysis Report

## Overview
Successfully analyzed and extracted data from `/home/user/atomic_ed/game/DATA/PCWATW.REZ`, an Apple HFS/HFS+ resource fork file containing game assets for "PC War Across the World" (PCWATW).

## File Information
- **File Size**: 5,552,097 bytes (5.3 MB)
- **Format**: Apple HFS/HFS+ resource fork
- **Data Offset**: 0x100
- **Map Offset**: 0x549f24
- **Data Length**: 5,545,508 bytes
- **Map Length**: 6,333 bytes
- **Resource Types**: 17

## Resource Summary

### Total Resources: 301

| Resource Type | Count | Total Size | Avg Size | Description |
|--------------|-------|------------|----------|-------------|
| **PICT** | 111 | 5,423,280 bytes | 48,858 bytes | Picture resources (images/graphics) |
| STR# | 77 | 6,529 bytes | 85 bytes | String lists |
| crsr | 34 | 9,196 bytes | 271 bytes | Cursors |
| FONT | 22 | 85,234 bytes | 3,874 bytes | Bitmap fonts |
| DITL | 16 | 1,982 bytes | 124 bytes | Dialog item lists |
| ALRT | 10 | 128 bytes | 13 bytes | Alert dialogs |
| PAT  | 8 | 64 bytes | 8 bytes | 8x8 monochrome patterns |
| MENU | 6 | 951 bytes | 159 bytes | Menu resources |
| mctb | 6 | 1,422 bytes | 237 bytes | Menu color tables |
| DLOG | 4 | 87 bytes | 22 bytes | Dialog templates |
| clut | 1 | 2,068 bytes | 2,068 bytes | **256-color palette** |
| ppat | 1 | 8,326 bytes | 8,326 bytes | Pixel pattern |
| itab | 1 | 4,620 bytes | 4,620 bytes | Index table |
| vers | 1 | 93 bytes | 93 bytes | Version info |
| ics# | 1 | 64 bytes | 64 bytes | Small icon mask |
| ics8 | 1 | 256 bytes | 256 bytes | Small 8-bit icon |
| uAGI | 1 | 4 bytes | 4 bytes | Owner resource |

## Key Graphics Resources

### Color Palette (clut #8)
- **256 colors** in RGB format
- Standard Mac color table format
- Each entry: 16-bit RGB values (converted to 8-bit for display)
- First few colors are variations of white, yellow, pink, orange

### Important PICT Resources

#### PICT 128 - **Main Terrain Hex Sheet** (PRIMARY TARGET)
- **Dimensions**: 442 x 570 pixels
- **Size**: 255,372 bytes (250 KB)
- **Format**: 8-bit indexed color with PackBits compression
- **Purpose**: Likely contains all terrain hex tiles in a sprite sheet
- **File**: `extracted_images/PICT_128.pict`

#### PICT 200 - "Large Hex Edges"
- **Dimensions**: 408 x 570 pixels
- **Size**: 234,852 bytes (229 KB)
- **Purpose**: Large-size hex edge graphics
- **File**: `extracted_images/PICT_200_Large Hex Edges.pict`

#### PICT 201 - "Small Hex Edges"
- **Dimensions**: 216 x 315 pixels
- **Size**: 69,312 bytes
- **Purpose**: Small-size hex edge graphics
- **File**: `extracted_images/PICT_201_Small Hex Edges.pict`

#### PICT 202 - "Large Night Hex Edges"
- **Dimensions**: 408 x 570 pixels
- **Size**: 234,852 bytes
- **Purpose**: Nighttime version of large hex edges
- **File**: `extracted_images/PICT_202_Large Night Hex Edges.pict`

#### PICT 203 - "Small Night Hex Edges"
- **Dimensions**: 216 x 315 pixels
- **Size**: 69,312 bytes
- **Purpose**: Nighttime version of small hex edges
- **File**: `extracted_images/PICT_203_Small Night Hex Edges.pict`

#### PICT 130
- **Dimensions**: 529 x 306 pixels
- **Size**: 164,028 bytes
- **Purpose**: Unknown (possibly additional terrain or UI graphics)
- **File**: `extracted_images/PICT_130.pict`

#### PICT 132
- **Dimensions**: 380 x 450 pixels
- **Size**: 172,812 bytes
- **Purpose**: Unknown (possibly additional terrain or UI graphics)
- **File**: `extracted_images/PICT_132.pict`

#### PICT 137 - "Explosions.rsrc"
- **Dimensions**: 170 x 190 pixels
- **Size**: 33,452 bytes
- **Purpose**: Explosion animations/effects
- **File**: `extracted_images/PICT_137_Explosions.rsrc.pict`

#### PICT 251 - "Toolbox Graphics"
- **Dimensions**: 564 x 110 pixels
- **Size**: 62,492 bytes
- **Purpose**: UI toolbox elements
- **File**: `extracted_images/PICT_251_Toolbox Graphics.pict`

### Other Notable PICT Resources
- **PICT 304-307**: Winter terrain graphics for Russian/German units (213-235 KB each)
- **PICT 4500-4606**: Scenario overview pictures and banners
- **PICT 1000-1003**: PBEM (Play By Email) status graphics

## Technical Details

### Mac PICT Format
The PICT resources use the classic Macintosh PICT format with the following characteristics:
- **Version**: PICT v2 format
- **Compression**: PackBits RLE compression
- **Color Depth**: 8-bit indexed color (256 colors)
- **Coordinate System**: QuickDraw coordinates stored in mixed/little-endian format (unusual for Mac)
- **Structure**:
  - 2-byte size field
  - 8-byte bounding rectangle (top, left, bottom, right)
  - Opcode-based drawing commands
  - PixMap structures with PackBits-compressed pixel data

### Extraction Challenges
1. **Complex Format**: PICT is an opcode-based metafile format, not a simple bitmap
2. **Compression**: PackBits RLE compression requires proper decompression
3. **Endianness**: Coordinates appear to use little-endian encoding (non-standard for Mac)
4. **Structure Parsing**: Requires parsing PixMap headers, color tables, and opcodes

## Files Created

### Python Scripts
1. **`extract_rez.py`** - Main resource fork parser
   - Parses Mac resource fork format
   - Lists all resources by type
   - Extracts resources to binary files
   - Converts PAT patterns to PNG (8 patterns successfully extracted)

2. **`analyze_pict.py`** - PICT structure analyzer
   - Analyzes PICT file structure
   - Identifies opcodes and PixMap data
   - Helps understand PICT format

3. **`extract_pict_images.py`** - PICT to PNG converter (partial)
   - Attempts to convert PICT to PNG
   - Correctly identifies dimensions
   - PackBits decompression implementation (needs refinement)

### Extracted Files
Located in `/home/user/atomic_ed/extracted_images/`:

- **111 PICT files** (`.pict` format with 512-byte header)
- **8 PAT patterns** (`.png` format, 64x64 scaled from 8x8)
- **Numerous binary resource files** for fonts, cursors, strings, etc.

## Recommendations for Next Steps

### Option 1: Convert PICT Files (Recommended)
Use external tools to convert the extracted .pict files to PNG:

```bash
# On macOS with ImageMagick:
convert PICT_128.pict PICT_128.png

# Or use GraphicConverter, QuickTime Player (older versions), or online converters
```

### Option 2: Enhanced Python Parser
Refine the `extract_pict_images.py` script to:
1. Better locate PackBits pixel data within PICT structure
2. Handle PICT opcodes more comprehensively
3. Properly parse PixMap headers
4. Implement full PackBits decompression for all variants

### Option 3: Use Specialized Tools
- **ResEdit** (Classic Mac OS) - Can view and export PICT resources natively
- **GraphicConverter** (macOS) - Can open PICT files
- **Basilisk II/SheepShaver** (Mac emulators) - Run classic Mac software
- **resedit** (Linux) - Open-source resource fork editor

## Analysis of PICT 128 (Main Hex Sheet)

Based on the dimensions (442 x 570 pixels) and file size, PICT 128 likely contains:
- **Hex tile dimensions**: Possibly 34x39 pixels per hex (common for this era)
- **Grid layout**: Approximately 13 columns x 15 rows of hex tiles
- **Total tiles**: ~195 different terrain hex variations
- **Purpose**: Master sprite sheet for all terrain types in the game

### Estimated Hex Breakdown
If using 34x39 pixel hexes:
- 442 ÷ 34 ≈ 13 hexes wide
- 570 ÷ 39 ≈ 15 hexes tall
- Total: 195 hex tiles (covers all terrain types, variations, and transitions)

## Success Metrics
✅ Successfully parsed Mac resource fork format
✅ Extracted all 301 resources
✅ Identified 111 PICT image resources
✅ Determined exact dimensions of all key graphics
✅ Extracted 256-color palette
✅ Converted 8 PAT patterns to PNG
✅ Located main terrain hex sheet (PICT 128)
❌ Complete PICT to PNG conversion (requires additional work)

## Conclusion

The resource fork has been successfully analyzed and all resources extracted in their raw formats. The most important finding is **PICT 128** (442 x 570 pixels, 250 KB), which appears to be the main terrain hex sprite sheet containing all game terrain graphics. The hex edge graphics (PICT 200-203) provide additional visual elements for hex rendering.

To use these graphics, the `.pict` files need to be converted to a modern format (PNG) using one of the methods recommended above. The color palette (clut #8) has been successfully extracted and can be used for proper color mapping during conversion.

## Script Location
- Main extraction script: `/home/user/atomic_ed/extract_rez.py`
- Extracted resources: `/home/user/atomic_ed/extracted_images/`
- This report: `/home/user/atomic_ed/REZ_ANALYSIS_REPORT.md`
