#!/usr/bin/env python3
"""
Extract individual hex tiles from PICT_128.png sprite sheet
Analyzes the sprite sheet to detect and extract individual hex tiles
"""

import sys
import json
from pathlib import Path
from PIL import Image
import numpy as np


class HexTileExtractor:
    def __init__(self, sprite_sheet_path):
        self.sprite_sheet_path = Path(sprite_sheet_path)
        self.img = None
        self.width = 0
        self.height = 0
        self.tiles = []

    def load_image(self):
        """Load the sprite sheet"""
        if not self.sprite_sheet_path.exists():
            print(f"Error: Image not found: {self.sprite_sheet_path}")
            return False

        self.img = Image.open(self.sprite_sheet_path)
        self.width, self.height = self.img.size

        print(f"Loaded sprite sheet: {self.width} x {self.height}")
        print(f"Image mode: {self.img.mode}")

        return True

    def analyze_grid(self, tile_width=34, tile_height=39):
        """Analyze the sprite sheet to detect hex tile grid"""
        # Calculate how many tiles can fit
        cols = self.width // tile_width
        rows = self.height // tile_height

        print(f"\nGrid analysis (tile size {tile_width}x{tile_height}):")
        print(f"  Columns: {cols}")
        print(f"  Rows: {rows}")
        print(f"  Total tiles: {cols * rows}")

        # Check coverage
        coverage_w = cols * tile_width
        coverage_h = rows * tile_height
        print(f"  Coverage: {coverage_w}x{coverage_h} ({coverage_w/self.width*100:.1f}% x {coverage_h/self.height*100:.1f}%)")

        return cols, rows

    def detect_empty_tile(self, tile_img):
        """Detect if a tile is empty (all one color or mostly transparent)"""
        # Convert to numpy for easy analysis
        arr = np.array(tile_img)

        # Check if all pixels are the same
        if arr.min() == arr.max():
            return True

        # Check if the tile is mostly one color (>95%)
        unique, counts = np.unique(arr, return_counts=True)
        if len(unique) > 0:
            max_color_ratio = counts.max() / arr.size
            if max_color_ratio > 0.95:
                return True

        return False

    def extract_tiles(self, tile_width=34, tile_height=39, output_dir='hex_tiles'):
        """Extract individual hex tiles from the sprite sheet"""
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)

        cols, rows = self.analyze_grid(tile_width, tile_height)

        print(f"\nExtracting tiles to {output_path}...")

        tile_num = 0
        extracted = 0
        empty = 0

        tile_info = []

        for row in range(rows):
            for col in range(cols):
                # Calculate tile position
                x = col * tile_width
                y = row * tile_height

                # Extract tile
                tile = self.img.crop((x, y, x + tile_width, y + tile_height))

                # Check if tile is empty
                is_empty = self.detect_empty_tile(tile)

                # Save tile
                tile_filename = f"hex_tile_{tile_num:03d}.png"
                tile_path = output_path / tile_filename

                tile.save(tile_path)

                # Record info
                tile_info.append({
                    'id': tile_num,
                    'filename': tile_filename,
                    'position': {'row': row, 'col': col},
                    'bounds': {'x': x, 'y': y, 'width': tile_width, 'height': tile_height},
                    'empty': is_empty
                })

                if is_empty:
                    empty += 1
                else:
                    extracted += 1

                if tile_num < 10 or (tile_num % 50 == 0):
                    status = "empty" if is_empty else "OK"
                    print(f"  Tile {tile_num:3d} (row {row:2d}, col {col:2d}): {status}")

                tile_num += 1

        # Save manifest
        manifest_path = output_path / 'tiles_manifest.json'
        with open(manifest_path, 'w') as f:
            json.dump({
                'source_image': str(self.sprite_sheet_path),
                'tile_size': {'width': tile_width, 'height': tile_height},
                'grid': {'columns': cols, 'rows': rows},
                'total_tiles': tile_num,
                'non_empty_tiles': extracted,
                'empty_tiles': empty,
                'tiles': tile_info
            }, f, indent=2)

        print(f"\nExtraction complete:")
        print(f"  Total tiles: {tile_num}")
        print(f"  Non-empty tiles: {extracted}")
        print(f"  Empty tiles: {empty}")
        print(f"  Manifest saved to: {manifest_path}")

        return tile_num, extracted

    def analyze_patterns(self, output_dir='hex_tiles'):
        """Analyze patterns in the extracted tiles"""
        output_path = Path(output_dir)
        manifest_path = output_path / 'tiles_manifest.json'

        if not manifest_path.exists():
            print("Error: Manifest not found. Run extract_tiles first.")
            return

        with open(manifest_path, 'r') as f:
            manifest = json.load(f)

        print("\n" + "=" * 80)
        print("TILE PATTERN ANALYSIS")
        print("=" * 80)

        # Analyze non-empty tile distribution
        non_empty = [t for t in manifest['tiles'] if not t['empty']]
        print(f"\nNon-empty tiles: {len(non_empty)}")

        # Find bounds of non-empty tiles
        if non_empty:
            min_row = min(t['position']['row'] for t in non_empty)
            max_row = max(t['position']['row'] for t in non_empty)
            min_col = min(t['position']['col'] for t in non_empty)
            max_col = max(t['position']['col'] for t in non_empty)

            print(f"Tile bounds:")
            print(f"  Rows: {min_row} to {max_row} ({max_row - min_row + 1} rows)")
            print(f"  Cols: {min_col} to {max_col} ({max_col - min_col + 1} cols)")

        # Try to identify patterns
        # Show first few non-empty tiles
        print(f"\nFirst 20 non-empty tiles:")
        for i, tile in enumerate(non_empty[:20]):
            print(f"  Tile {tile['id']:3d} at row {tile['position']['row']:2d}, col {tile['position']['col']:2d}")

        # Create a visual grid map
        print(f"\nGrid map (X=non-empty, .=empty):")
        grid = manifest['grid']
        for row in range(grid['rows']):
            line = ""
            for col in range(grid['columns']):
                tile_id = row * grid['columns'] + col
                if tile_id < len(manifest['tiles']):
                    tile = manifest['tiles'][tile_id]
                    line += "." if tile['empty'] else "X"
                else:
                    line += " "
            print(f"  Row {row:2d}: {line}")

    def create_reference_sheet(self, output_dir='hex_tiles', max_tiles_per_sheet=100):
        """Create a reference sheet showing all tiles with labels"""
        output_path = Path(output_dir)
        manifest_path = output_path / 'tiles_manifest.json'

        if not manifest_path.exists():
            print("Error: Manifest not found. Run extract_tiles first.")
            return

        with open(manifest_path, 'r') as f:
            manifest = json.load(f)

        # Get non-empty tiles
        non_empty = [t for t in manifest['tiles'] if not t['empty']]

        if not non_empty:
            print("No non-empty tiles to create reference sheet")
            return

        print(f"\nCreating reference sheet for {len(non_empty)} tiles...")

        # Load first tile to get dimensions
        first_tile = Image.open(output_path / non_empty[0]['filename'])
        tile_w, tile_h = first_tile.size

        # Calculate layout (10 tiles per row)
        tiles_per_row = 10
        num_rows = (len(non_empty) + tiles_per_row - 1) // tiles_per_row

        # Create reference sheet
        # Add space for tile numbers below each tile
        spacing = 5
        number_space = 15

        sheet_width = tiles_per_row * (tile_w + spacing) + spacing
        sheet_height = num_rows * (tile_h + number_space + spacing) + spacing

        ref_sheet = Image.new('RGB', (sheet_width, sheet_height), 'white')

        from PIL import ImageDraw, ImageFont

        draw = ImageDraw.Draw(ref_sheet)

        # Try to load a font, fall back to default if not available
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 10)
        except:
            font = ImageFont.load_default()

        for idx, tile_info in enumerate(non_empty[:max_tiles_per_sheet]):
            row = idx // tiles_per_row
            col = idx % tiles_per_row

            x = spacing + col * (tile_w + spacing)
            y = spacing + row * (tile_h + number_space + spacing)

            # Load and paste tile
            tile_img = Image.open(output_path / tile_info['filename'])
            # Convert palette mode to RGB for pasting
            if tile_img.mode == 'P':
                tile_img = tile_img.convert('RGB')
            ref_sheet.paste(tile_img, (x, y))

            # Draw tile number
            text = str(tile_info['id'])
            # Get text size for centering
            bbox = draw.textbbox((0, 0), text, font=font)
            text_w = bbox[2] - bbox[0]
            text_x = x + (tile_w - text_w) // 2
            text_y = y + tile_h + 2

            draw.text((text_x, text_y), text, fill='black', font=font)

        # Save reference sheet
        ref_path = output_path / 'reference_sheet.png'
        ref_sheet.save(ref_path)

        print(f"Reference sheet saved to: {ref_path}")
        print(f"Showing {min(len(non_empty), max_tiles_per_sheet)} tiles")


def main():
    sprite_sheet = '/home/user/atomic_ed/extracted_images/PICT_128.png'
    output_dir = '/home/user/atomic_ed/extracted_images/hex_tiles'

    # Parse command line arguments
    if len(sys.argv) > 1:
        sprite_sheet = sys.argv[1]
    if len(sys.argv) > 2:
        output_dir = sys.argv[2]

    print("=" * 80)
    print("Hex Tile Extractor")
    print("=" * 80)
    print()

    extractor = HexTileExtractor(sprite_sheet)

    if not extractor.load_image():
        return 1

    # Extract tiles (using approximate dimensions from analysis)
    # You mentioned ~34x39 pixels per tile
    tile_count, non_empty = extractor.extract_tiles(
        tile_width=34,
        tile_height=38,  # Try 38 instead of 39 for better fit
        output_dir=output_dir
    )

    # Analyze patterns
    extractor.analyze_patterns(output_dir=output_dir)

    # Create reference sheet
    extractor.create_reference_sheet(output_dir=output_dir, max_tiles_per_sheet=195)

    print("\n" + "=" * 80)
    print("Extraction complete!")
    print("=" * 80)

    return 0


if __name__ == '__main__':
    sys.exit(main())
