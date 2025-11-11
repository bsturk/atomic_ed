#!/usr/bin/env python3
"""
Scenario Format Converter
========================================

Converts legacy scenario files from World at War: Stalingrad (0x0f4a)
and World at War: Crusader (0x0dac) formats to the newer D-Day format (0x1230).

The key differences:
1. Magic number: 0x0f4a/0x0dac → 0x1230
2. Counts: float32 → uint32 with fixed values
3. Map dimensions: Must be extracted from data → Stored in counts 11-12
4. PTR1/PTR2: float 1.0 → NULL pointers

Usage:
    # Convert a single file
    python3 scenario_converter.py game/scenarios-prev/CITY.SCN -o game/scenarios/CITY.SCN

    # Convert all files in a directory
    python3 scenario_converter.py game/scenarios-prev/ -d game/scenarios/

    # Dry run to see what would happen
    python3 scenario_converter.py game/scenarios-prev/ --dry-run
"""

import struct
import sys
import argparse
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import logging

logging.basicConfig( level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


class CrusaderScenarioReader:
    """Reader for Crusader format (0x0dac) - uses fixed offsets instead of pointers"""

    MAGIC        = 0x0dac
    HEADER_SIZE  = 0x60
    CONFIG_START = 0x60
    DATA_START   = 0x80
    BLOCK_SIZE   = 0x80  # 128-byte alignment

    def __init__(self, filename: str):
        self.filename = Path(filename)
        self.data = b''
        self.magic = 0
        self.is_valid = False
        self.sections = {}  # Data sections

        self._load_and_parse()

    def _load_and_parse(self):
        """Load and parse Crusader format file"""
        try:
            with open(self.filename, 'rb') as f:
                self.data = f.read()
        except Exception as e:
            logger.error(f"Failed to read {self.filename}: {e}")
            return

        if len(self.data) < self.HEADER_SIZE:
            logger.error(f"File too small: {len(self.data)} bytes")
            return

        # Parse magic number
        self.magic = struct.unpack('<H', self.data[0:2])[0]

        if self.magic != self.MAGIC:
            logger.error(f"Not a Crusader file: 0x{self.magic:04x}")
            return

        logger.debug(f"Magic: 0x{self.magic:04x} (World at War: Crusader)")

        # Extract data sections using fixed offsets
        self._extract_sections()

        self.is_valid = True

    def _extract_sections(self):
        """Extract data sections from fixed offsets"""
        # Crusader format stores data at fixed offsets starting at 0x80
        # Text sections are at 128-byte aligned boundaries: 0x80, 0x100, 0x180, etc.
        # Binary data follows after text sections (typically ~0x1000+)

        # NOTE: Crusader format has configuration data at 0x60-0x7F that must NOT be
        # preserved in D-Day format. D-Day format requires 0x60-0x7F to be all zeros.
        # If we preserve this data, it causes game settings corruption (e.g., no sound).
        # Therefore, we create a zero-filled PRE_PTR5 section instead.
        self.sections['PRE_PTR5'] = bytes(32)  # 32 zero bytes for 0x60-0x7F
        logger.debug("PRE_PTR5: Created 32 zero bytes (0x60-0x7F)")

        # Collect all data from 0x80 onwards as one big section
        # We'll treat it as PTR5 to match the expected section naming
        if len(self.data) > self.DATA_START:
            all_data = self.data[self.DATA_START:]

            # Split into text blocks and binary data
            # For now, just store the whole thing
            self.sections['PTR5'] = all_data[:min(len(all_data), 0x1000 - self.DATA_START)]

            # If there's binary data after the text sections
            if len(all_data) > 0x1000:
                self.sections['PTR6'] = all_data[0x1000 - self.DATA_START:]

            logger.debug(f"Extracted Crusader data sections:")
            logger.debug(f"  PTR5 (text area): {len(self.sections.get('PTR5', b''))} bytes")
            logger.debug(f"  PTR6 (binary data): {len(self.sections.get('PTR6', b''))} bytes")

        # NOTE: Crusader format doesn't have PTR3/PTR4 data in the file
        # Create minimal empty PTR3 and PTR4 sections to avoid NULL pointer crashes
        # Based on analysis, minimal PTR3 can be ~16-28 bytes, PTR4 can be minimal too
        # Using a simple zeroed structure
        if 'PTR3' not in self.sections:
            # Create minimal 16-byte PTR3 (smallest seen in COUNTER.SCN)
            self.sections['PTR3'] = bytes(16)
            logger.debug("Created minimal PTR3 section (16 bytes)")

        if 'PTR4' not in self.sections:
            # Create minimal PTR4 - just a few bytes to avoid NULL pointer
            self.sections['PTR4'] = bytes(16)
            logger.debug("Created minimal PTR4 section (16 bytes)")

    def analyze_map_dimensions(self) -> Tuple[int, int]:
        """Determine map dimensions for Crusader scenarios"""
        # Crusader scenarios typically use standard D-Day dimensions
        height, width = 125, 100
        logger.info(f"Using map dimensions: {height}x{width} (Crusader default)")
        return height, width

    def get_info(self) -> str:
        """Get human-readable info about the file"""
        if not self.is_valid:
            return f"Invalid file: {self.filename}"

        lines = [
            f"File: {self.filename.name}",
            f"Size: {len(self.data):,} bytes",
            f"Magic: 0x{self.magic:04x} (World at War: Crusader)",
            "",
            "Data Sections:",
        ]

        for name, data in self.sections.items():
            lines.append(f"  {name}: {len(data):,} bytes")

        return "\n".join(lines)


class LegacyScenarioReader:
    """Reader for Stalingrad format (0x0f4a)"""

    SUPPORTED_MAGICS = {
        0x0f4a: "World at War: Stalingrad",
        0x1230: "D-Day (already converted)"
    }

    HEADER_SIZE = 0x60  # 96 bytes

    def __init__(self, filename: str):
        self.filename = Path(filename)
        self.data = b''
        self.magic = 0
        self.float_counts = []  # 12 float values
        self.extra_floats = []  # 3 extra floats at 0x34-0x3F
        self.pointers = {}  # PTR1-PTR8
        self.sections = {}  # Data sections
        self.is_valid = False

        self._load_and_parse()

    def _load_and_parse(self):
        """Load and parse the legacy file"""
        try:
            with open(self.filename, 'rb') as f:
                self.data = f.read()
        except Exception as e:
            logger.error(f"Failed to read {self.filename}: {e}")
            return

        if len(self.data) < self.HEADER_SIZE:
            logger.error(f"File too small: {len(self.data)} bytes")
            return

        # Parse magic number
        self.magic = struct.unpack('<H', self.data[0:2])[0]

        if self.magic not in self.SUPPORTED_MAGICS:
            logger.error(f"Unsupported magic number: 0x{self.magic:04x}")
            return

        if self.magic == 0x1230:
            logger.warning(f"{self.filename.name} is already in D-Day format")
            self.is_valid = False
            return

        logger.debug(f"Magic: 0x{self.magic:04x} ({self.SUPPORTED_MAGICS[self.magic]})")

        # Parse 12 float counts (0x04-0x33)
        for offset in range(0x04, 0x34, 4):
            value = struct.unpack('<f', self.data[offset:offset+4])[0]
            self.float_counts.append(value)

        # Parse extra floats (0x34-0x3F)
        for offset in range(0x34, 0x40, 4):
            value = struct.unpack('<f', self.data[offset:offset+4])[0]
            self.extra_floats.append(value)

        # Parse pointers (0x40-0x5F)
        # NOTE: PTR1 and PTR2 are actually float 1.0, not pointers!
        pointer_names = ['PTR1', 'PTR2', 'PTR3', 'PTR4', 'PTR5', 'PTR6', 'PTR7', 'PTR8']
        for i, name in enumerate(pointer_names):
            offset = 0x40 + (i * 4)
            if name in ['PTR1', 'PTR2']:
                # These are floats, not pointers
                value = struct.unpack('<f', self.data[offset:offset+4])[0]
                self.pointers[name] = value
            else:
                value = struct.unpack('<I', self.data[offset:offset+4])[0]
                self.pointers[name] = value

        # Extract data sections
        self._extract_sections()

        self.is_valid = True

    def _extract_sections(self):
        """Extract data sections from the file"""
        # First, extract the data between header and PTR5 (if it exists)
        # This contains important game data like scenario descriptions
        ptr5 = self.pointers.get('PTR5', 0)
        if ptr5 > self.HEADER_SIZE:
            pre_ptr5_data = self.data[self.HEADER_SIZE:ptr5]
            if len(pre_ptr5_data) > 0:
                self.sections['PRE_PTR5'] = pre_ptr5_data
                logger.debug(f"PRE_PTR5: 0x{self.HEADER_SIZE:06x}-0x{ptr5:06x} ({len(pre_ptr5_data)} bytes)")

        # Collect non-null pointers (PTR3-PTR8)
        active_ptrs = []
        for name in ['PTR3', 'PTR4', 'PTR5', 'PTR6', 'PTR7', 'PTR8']:
            ptr = self.pointers.get(name, 0)
            if ptr > 0 and ptr < len(self.data):
                active_ptrs.append((name, ptr))

        # Sort by file offset
        active_ptrs.sort(key=lambda x: x[1])

        # Extract sections
        file_size = len(self.data)
        for i, (name, start) in enumerate(active_ptrs):
            end = active_ptrs[i + 1][1] if i < len(active_ptrs) - 1 else file_size
            self.sections[name] = self.data[start:end]
            logger.debug(f"{name}: 0x{start:06x}-0x{end:06x} ({len(self.sections[name])} bytes)")

    def analyze_map_dimensions(self) -> Tuple[int, int]:
        """
        Attempt to determine map dimensions from the data.

        This is a heuristic approach since old format doesn't store dimensions
        in the header. Based on analysis:
        - Most scenarios use 125x100 (same as D-Day standard)
        - Some scenarios like COBRA use 112x100
        - Without explicit markers, we default to 125x100

        Returns: (height, width) tuple
        """
        # Default dimensions based on game type
        if self.magic == 0x0f4a:  # Stalingrad
            # Stalingrad scenarios typically use standard dimensions
            height, width = 125, 100
        elif self.magic == 0x0dac:  # Crusader
            # Crusader scenarios might use different dimensions
            # Some use 112x100, but default to standard
            height, width = 125, 100
        else:
            height, width = 125, 100

        logger.info(f"Using map dimensions: {height}x{width} (default for this game type)")
        return height, width

    def get_info(self) -> str:
        """Get human-readable info about the file"""
        if not self.is_valid:
            return f"Invalid file: {self.filename}"

        lines = [
            f"File: {self.filename.name}",
            f"Size: {len(self.data):,} bytes",
            f"Magic: 0x{self.magic:04x} ({self.SUPPORTED_MAGICS.get(self.magic, 'Unknown')})",
            "",
            "Float Counts:",
        ]

        for i, val in enumerate(self.float_counts):
            lines.append(f"  Count {i+1:2d} (0x{0x04+i*4:02x}): {val:8.1f}")

        lines.append("")
        lines.append("Extra Floats:")
        for i, val in enumerate(self.extra_floats):
            lines.append(f"  Float {i+1} (0x{0x34+i*4:02x}): {val:8.1f}")

        lines.append("")
        lines.append("Pointers:")
        for name, val in self.pointers.items():
            if name in ['PTR1', 'PTR2']:
                lines.append(f"  {name}: {val:8.1f} (float)")
            else:
                lines.append(f"  {name}: 0x{val:06x} ({val})")

        lines.append("")
        lines.append("Data Sections:")
        for name, data in self.sections.items():
            lines.append(f"  {name}: {len(data):,} bytes")

        return "\n".join(lines)


class DdayScenarioWriter:
    """Writer for D-Day format scenarios (0x1230)"""

    MAGIC_NUMBER = 0x1230
    HEADER_SIZE = 0x60

    # Fixed counts for D-Day format (except counts 11-12 which are map dimensions)
    FIXED_COUNTS = [17, 5, 10, 8, 5, 8, 0, 10, 20, 5]

    def __init__(self):
        self.header = bytearray(self.HEADER_SIZE)
        self.sections = {}  # name -> bytes
        self.map_height = 125
        self.map_width = 100

    def set_map_dimensions(self, height: int, width: int):
        """Set map dimensions (counts 11 and 12)"""
        self.map_height = height
        self.map_width = width

    def add_section(self, name: str, data: bytes):
        """Add a data section"""
        self.sections[name] = data

    def build(self) -> bytes:
        """Build the complete scenario file"""
        # Build header
        self._build_header()

        # Order sections: PRE_PTR5 -> PTR5 -> PTR6 -> PTR3 -> PTR4 (typical D-Day order)
        # PRE_PTR5 comes first (between header and PTR5) but is not a pointer
        section_order = []
        for name in ['PRE_PTR5', 'PTR5', 'PTR6', 'PTR3', 'PTR4', 'PTR7', 'PTR8']:
            if name in self.sections and len(self.sections[name]) > 0:
                section_order.append(name)

        # Calculate pointer offsets
        # PRE_PTR5 goes right after header, then PTR5 starts after it
        pointers = {}
        current_offset = self.HEADER_SIZE

        for name in section_order:
            if name == 'PRE_PTR5':
                # PRE_PTR5 is not a pointer, just add its size
                current_offset += len(self.sections[name])
            else:
                # This is a real pointer (PTR3-PTR8)
                pointers[name] = current_offset
                current_offset += len(self.sections[name])

        # Update pointers in header
        self._update_pointers(pointers)

        # Build file: header + padding + data sections
        # (Must copy header AFTER updating pointers!)
        file_data = bytearray(self.header)

        # Append section data
        for name in section_order:
            file_data.extend(self.sections[name])

        return bytes(file_data)

    def _build_header(self):
        """Build the 96-byte header"""
        # Magic number (0x00-0x01)
        struct.pack_into('<H', self.header, 0x00, self.MAGIC_NUMBER)

        # Unknown (0x02-0x03) - always 0x0000
        struct.pack_into('<H', self.header, 0x02, 0x0000)

        # Counts 1-10 (0x04-0x2B) - fixed values
        for i, count in enumerate(self.FIXED_COUNTS):
            offset = 0x04 + (i * 4)
            struct.pack_into('<I', self.header, offset, count)

        # Count 11: Map height (0x2C)
        struct.pack_into('<I', self.header, 0x2C, self.map_height)

        # Count 12: Map width (0x30)
        struct.pack_into('<I', self.header, 0x30, self.map_width)

        # Reserved (0x34-0x3F) - all zeros (already zero in bytearray)

        # Pointers (0x40-0x5F) - will be updated later
        # PTR1 and PTR2 are NULL in new format
        struct.pack_into('<I', self.header, 0x40, 0)  # PTR1
        struct.pack_into('<I', self.header, 0x44, 0)  # PTR2

    def _update_pointers(self, pointers: Dict[str, int]):
        """Update pointer values in header"""
        pointer_offsets = {
            'PTR3': 0x48,
            'PTR4': 0x4C,
            'PTR5': 0x50,
            'PTR6': 0x54,
            'PTR7': 0x58,
            'PTR8': 0x5C,
        }

        for name, file_offset in pointers.items():
            if name in pointer_offsets:
                header_offset = pointer_offsets[name]
                struct.pack_into('<I', self.header, header_offset, file_offset)


class ScenarioConverter:
    """Main converter class"""

    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        if verbose:
            logger.setLevel(logging.DEBUG)

    def convert_file(self, input_path: str, output_path: Optional[str] = None,
                    map_height: Optional[int] = None, map_width: Optional[int] = None) -> bool:
        """
        Convert a single scenario file.

        Args:
            input_path: Path to legacy scenario file
            output_path: Path for output file (optional)
            map_height: Override map height (optional)
            map_width: Override map width (optional)

        Returns:
            True if conversion successful
        """
        input_path = Path(input_path)

        if not input_path.exists():
            logger.error(f"Input file not found: {input_path}")
            return False

        # Peek at magic number to determine format
        logger.info(f"Reading {input_path.name}...")
        with open(input_path, 'rb') as f:
            magic_bytes = f.read(2)
            if len(magic_bytes) < 2:
                logger.error(f"File too small: {input_path.name}")
                return False
            magic = struct.unpack('<H', magic_bytes)[0]

        # Choose appropriate reader based on format
        if magic == 0x0dac:
            logger.debug(f"Detected Crusader format (0x0dac)")
            reader = CrusaderScenarioReader(input_path)
        elif magic == 0x0f4a:
            logger.debug(f"Detected Stalingrad format (0x0f4a)")
            reader = LegacyScenarioReader(input_path)
        elif magic == 0x1230:
            logger.warning(f"{input_path.name} is already in D-Day format")
            return False
        else:
            logger.error(f"Unsupported magic number: 0x{magic:04x}")
            return False

        if not reader.is_valid:
            logger.error(f"Failed to parse {input_path.name}")
            return False

        if self.verbose:
            logger.debug(reader.get_info())

        # Determine map dimensions
        if map_height and map_width:
            height, width = map_height, map_width
            logger.info(f"Using override dimensions: {height}x{width}")
        else:
            height, width = reader.analyze_map_dimensions()

        # Create writer
        writer = DdayScenarioWriter()
        writer.set_map_dimensions(height, width)

        # Copy data sections
        for name, data in reader.sections.items():
            if name in ['PRE_PTR5', 'PTR3', 'PTR4', 'PTR5', 'PTR6', 'PTR7', 'PTR8']:
                writer.add_section(name, data)
                logger.debug(f"Copied {name}: {len(data)} bytes")

        # Build output file
        output_data = writer.build()

        # Determine output path
        if output_path is None:
            output_path = input_path.parent / f"{input_path.stem}_converted.SCN"
        else:
            output_path = Path(output_path)

        # Write output
        logger.info(f"Writing to {output_path}...")
        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'wb') as f:
                f.write(output_data)
            logger.info(f"✓ Converted {input_path.name} -> {output_path.name} ({len(output_data):,} bytes)")
            return True
        except Exception as e:
            logger.error(f"Failed to write {output_path}: {e}")
            return False

    def convert_directory(self, input_dir: str, output_dir: Optional[str] = None,
                         dry_run: bool = False) -> Tuple[int, int]:
        """
        Convert all scenario files in a directory.

        Args:
            input_dir: Directory containing legacy scenarios
            output_dir: Output directory (optional)
            dry_run: If True, don't actually write files

        Returns:
            (success_count, fail_count) tuple
        """
        input_dir = Path(input_dir)

        if not input_dir.is_dir():
            logger.error(f"Input directory not found: {input_dir}")
            return 0, 0

        # Find all .SCN files
        scn_files = list(input_dir.glob("*.SCN")) + list(input_dir.glob("*.scn"))

        if not scn_files:
            logger.warning(f"No .SCN files found in {input_dir}")
            return 0, 0

        logger.info(f"Found {len(scn_files)} scenario files")

        if dry_run:
            logger.info("DRY RUN MODE - No files will be written")

        success = 0
        failed = 0

        for scn_file in sorted(scn_files):
            # Determine output path
            if output_dir:
                out_path = Path(output_dir) / scn_file.name
            else:
                out_path = scn_file.parent / f"{scn_file.stem}_converted.SCN"

            if dry_run:
                logger.info(f"Would convert: {scn_file.name} -> {out_path}")
                # Still parse to check validity
                reader = LegacyScenarioReader(scn_file)
                if reader.is_valid:
                    success += 1
                else:
                    failed += 1
            else:
                if self.convert_file(scn_file, out_path):
                    success += 1
                else:
                    failed += 1

        logger.info(f"\nConversion complete: {success} succeeded, {failed} failed")
        return success, failed


def main():
    parser = argparse.ArgumentParser(
        description="Convert World at War scenario files to D-Day format",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Convert a single file
  %(prog)s game/scenarios-prev/CITY.SCN -o game/scenarios/CITY.SCN

  # Convert all files in directory
  %(prog)s game/scenarios-prev/ -d game/scenarios/

  # Dry run to see what would happen
  %(prog)s game/scenarios-prev/ --dry-run

  # Convert with custom map dimensions
  %(prog)s game/scenarios-prev/TOBRUK.SCN -o output.SCN --height 112 --width 100
"""
    )

    parser.add_argument('input', help='Input scenario file or directory')
    parser.add_argument('-o', '--output', help='Output scenario file')
    parser.add_argument('-d', '--output-dir', help='Output directory (for batch conversion)')
    parser.add_argument('--height', type=int, help='Override map height')
    parser.add_argument('--width', type=int, help='Override map width')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be converted without writing files')
    parser.add_argument('-v', '--verbose', action='store_true', help='Verbose output')

    args = parser.parse_args()

    converter = ScenarioConverter(verbose=args.verbose)

    input_path = Path(args.input)

    if input_path.is_file():
        # Convert single file
        success = converter.convert_file(
            args.input,
            args.output,
            args.height,
            args.width
        )
        sys.exit(0 if success else 1)
    elif input_path.is_dir():
        # Convert directory
        success, failed = converter.convert_directory(
            args.input,
            args.output_dir or args.output,
            args.dry_run
        )
        sys.exit(0 if failed == 0 else 1)
    else:
        logger.error(f"Input not found: {args.input}")
        sys.exit(1)


if __name__ == '__main__':
    main()
