#!/usr/bin/env python3
"""
D-Day Scenario File Format Parser
==================================

This module provides utilities for reading and analyzing D-Day (.SCN) scenario files.

Format: D-Day .SCN scenario files (magic number 0x1230)
Status: Reverse engineered from 7 D-Day scenario files
Version: 1.0

Usage:
    from lib.scenario_parser import DdayScenario

    scenario = DdayScenario('UTAH.SCN')
    scenario.display_header()
    scenario.display_data_sections()
"""

import struct
import sys
from typing import Dict, List, Tuple, Optional
from pathlib import Path


class DdayScenario:
    """Parser for D-Day scenario (.SCN) files"""
    
    # Format constants
    MAGIC_NUMBER = 0x1230
    MAGIC_BYTES = b'\x30\x12\x00\x00'
    HEADER_SIZE = 0x60  # Header is 96 bytes
    
    # Values shared by the native scenarios. File 0x08-0x28 are the editable
    # casualty scoring weights; none of these are the playable map dimensions.
    FIXED_COUNTS = [
        0x11, 0x05, 0x0a, 0x08, 0x05, 0x08, 0x00,
        0x0a, 0x14, 0x05, 0x7d, 0x64
    ]
    
    # Offset positions in header
    COUNT_OFFSETS = [
        0x04, 0x08, 0x0c, 0x10, 0x14, 0x18, 0x1c,
        0x20, 0x24, 0x28, 0x2c, 0x30
    ]
    
    # Serialized runtime values, not file offsets; some exceed the file size.
    # See txt/DDAY_MAP_FORMAT_RESEARCH.md. Retained for older analysis tools.
    POINTER_OFFSETS = {
        'PTR1': 0x40,
        'PTR2': 0x44,
        'PTR3': 0x48,
        'PTR4': 0x4c,
        'PTR5': 0x50,
        'PTR6': 0x54,
        'PTR7': 0x58,
        'PTR8': 0x5c,
    }
    
    def __init__(self, filename: str):
        """Initialize and parse scenario file"""
        self.filename = Path(filename)
        self.data = b''
        self.is_valid = False
        self.counts: List[int] = []
        self.pointers: Dict[str, int] = {}
        self.sections: Dict[str, bytes] = {}  # Store parsed sections
        self.section_order: List[Tuple[str, int, int]] = []  # (name, start, end) sorted by start

        self._load_file()
    
    def _load_file(self):
        """Load and validate scenario file"""
        try:
            with open(self.filename, 'rb') as f:
                self.data = f.read()
        except Exception as e:
            print(f"Error reading file: {e}")
            return

        self._parse_data()

    @classmethod
    def from_bytes(cls, data, filename):
        """Parse a staged scenario without creating or changing a file."""
        scenario = cls.__new__(cls)
        scenario.filename = Path(filename)
        scenario.data = bytes(data)
        scenario._parse_data()
        return scenario

    def _parse_data(self):
        self.is_valid = False
        self.counts = []
        self.pointers = {}
        self.sections = {}
        self.section_order = []
        if len(self.data) < 0x60:
            print(f"File too small: {len(self.data)} bytes")
            return
        
        # Validate magic number
        magic = struct.unpack('<H', self.data[0:2])[0]
        if magic != self.MAGIC_NUMBER:
            print(f"Invalid magic number: 0x{magic:04x} (expected 0x1230)")
            return
        
        # Parse counts
        self._parse_counts()
        
        # Parse offsets
        self._parse_pointers()

        # Parse data sections
        self._parse_sections()

        self.is_valid = True

    def save_bytes(self, data, output_file, create_backup=False):
        """Atomically save a complete staged file; backups are opt-in."""
        import os
        import shutil
        import tempfile

        target = Path(output_file)
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(dir=target.parent, prefix=target.name + '.',
                                             suffix='.tmp', delete=False) as stream:
                temporary = Path(stream.name)
                stream.write(data)
                stream.flush()
                os.fsync(stream.fileno())
            if create_backup and target.exists():
                shutil.copy2(target, str(target) + '.bak')
            if target.exists():
                shutil.copymode(target, temporary)
            os.replace(temporary, target)
        finally:
            if temporary is not None and temporary.exists():
                temporary.unlink()
    
    def _parse_counts(self):
        """Parse the 12 count fields from header"""
        for offset in self.COUNT_OFFSETS:
            value = struct.unpack('<I', self.data[offset:offset+4])[0]
            self.counts.append(value)

    @property
    def map_width(self) -> int:
        """Playable columns: inclusive right bound in the scenario's map Rect.

        InitGameData copies scenario+0x224 (file 0x228) to wholeMapRect,
        then sets theMapW to right+1. See txt/DDAY_MAP_FORMAT_RESEARCH.md.
        """
        if len(self.data) < 0x230:
            return 0
        return struct.unpack_from('<h', self.data, 0x22e)[0] + 1

    @property
    def map_height(self) -> int:
        """Playable rows: inclusive bottom bound at file offset 0x22c, plus one."""
        if len(self.data) < 0x230:
            return 0
        return struct.unpack_from('<h', self.data, 0x22c)[0] + 1
    
    def _parse_pointers(self):
        """Parse the 8 offset pointers from header"""
        for name, offset in self.POINTER_OFFSETS.items():
            value = struct.unpack('<I', self.data[offset:offset+4])[0]
            self.pointers[name] = value

    def _parse_sections(self):
        """Parse data sections based on pointer offsets"""
        # Collect non-null pointers
        active_ptrs = []
        for name in ['PTR3', 'PTR4', 'PTR5', 'PTR6']:
            ptr = self.pointers.get(name, 0)
            if ptr > 0:
                active_ptrs.append((name, ptr))

        # Sort by file offset (CRITICAL! File order != header order)
        active_ptrs.sort(key=lambda x: x[1])

        # Calculate section boundaries and extract data
        file_size = len(self.data)
        for i, (name, start) in enumerate(active_ptrs):
            # End is either next section start or EOF
            end = active_ptrs[i + 1][1] if i < len(active_ptrs) - 1 else file_size

            # Extract section data
            self.sections[name] = self.data[start:end]
            self.section_order.append((name, start, end))
    
    def validate(self) -> bool:
        """Validate the length-prefixed block layout that LoadGame reads."""
        if not self.is_valid:
            return False
        from lib.unit_roster import UnitRoster
        try:
            UnitRoster(self.data)
        except (ValueError, struct.error) as exc:
            print(f"Warning: {exc}")
            return False
        return True

    def display_header(self):
        """Display parsed header information"""
        if not self.is_valid:
            print("Invalid scenario file")
            return
        
        print("=" * 80)
        print(f"D-DAY SCENARIO FILE: {self.filename.name}")
        print("=" * 80)
        print(f"File Size: {len(self.data):,} bytes")
        print()
        
        # Magic number
        magic = struct.unpack('<H', self.data[0:2])[0]
        print(f"Magic Number: 0x{magic:04x} {'✓' if magic == self.MAGIC_NUMBER else '✗'}")
        print()
        
        print(f"Map: {self.map_width} x {self.map_height} hexes (Scenario rectangle at 0x228)")
        print()

        # Header values; casualty weights are editable per scenario.
        from lib.scenario_rules import LOSS_CLASSES
        print("Header Values (✓ = native default):")
        print("-" * 60)
        count_labels = (["Unknown"] + [f"Casualty weight: {name}" for name in LOSS_CLASSES]
                        + ["Unknown (not the map width)", "Unknown (not the map height)"])
        
        for i, (count, label) in enumerate(zip(self.counts, count_labels)):
            expected = self.FIXED_COUNTS[i]
            match = "✓" if count == expected else "✗"
            offset = self.COUNT_OFFSETS[i]
            print(f"  0x{offset:02x}: {count:3d} (0x{count:02x})  {match}  {label}")
        print()
        
        # Pointers
        print("Header Pointer Values (runtime values, not file offsets):")
        print("-" * 60)
        for name, offset in self.POINTER_OFFSETS.items():
            ptr = self.pointers.get(name, 0)
            if ptr == 0:
                status = "(NULL)"
            else:
                status = f"0x{ptr:06x} ({ptr:,} bytes)"
            print(f"  {name} at 0x{offset:02x}: {status}")
        print()
    
    def display_data_sections(self):
        """Display the length-prefixed blocks in file order."""
        if not self.is_valid:
            print("Invalid scenario file")
            return
        from lib.unit_roster import UnitRoster
        try:
            roster = UnitRoster(self.data)
        except (ValueError, struct.error) as exc:
            print(f"Invalid block layout: {exc}")
            return

        print("Data Blocks (in file order):")
        print("-" * 60)
        offset = 0
        for name, multiple in roster._layout():
            size = len(roster.blocks[name])
            prefix = 4 if multiple else 0
            print(f"  {name:12s}: 0x{offset:06x} - 0x{offset + prefix + size:06x} ({size:,} bytes)")
            offset += prefix + size
        orders = sum(len(value) for value in roster.orders.values())
        print(f"  {'orders':12s}: {len(roster.orders)} saved routes ({orders:,} bytes)")
        if roster.trailer:
            print(f"  {'trailer':12s}: {len(roster.trailer):,} bytes")
        print()

    def find_strings(self, min_length: int = 4) -> List[Tuple[int, str]]:
        """Find ASCII strings in the file"""
        strings = []
        current_str = b''
        start_pos = 0
        
        for i, b in enumerate(self.data):
            if 32 <= b < 127:
                if len(current_str) == 0:
                    start_pos = i
                current_str += bytes([b])
            else:
                if len(current_str) >= min_length:
                    try:
                        s = current_str.decode('ascii')
                        strings.append((start_pos, s))
                    except:
                        pass
                current_str = b''
        
        return strings
    
    def display_strings(self, limit: int = 20):
        """Display ASCII strings found in file"""
        if not self.is_valid:
            print("Invalid scenario file")
            return
        
        strings = self.find_strings()
        print(f"ASCII Strings found ({len(strings)} total, showing {min(limit, len(strings))}):")
        print("-" * 60)
        
        for offset, s in strings[:limit]:
            # Truncate long strings
            display = s[:60] + "..." if len(s) > 60 else s
            print(f"  0x{offset:06x}: {display}")
        
        if len(strings) > limit:
            print(f"  ... and {len(strings) - limit} more")
        print()
    
    def get_statistics(self) -> Dict:
        """Calculate file statistics"""
        if not self.is_valid:
            return {}
        
        # Count zero bytes
        zero_count = sum(1 for b in self.data if b == 0)
        
        return {
            'file_size': len(self.data),
            'zero_bytes': zero_count,
            'zero_percentage': 100.0 * zero_count / len(self.data),
            'data_bytes': len(self.data) - zero_count,
            'string_count': len(self.find_strings()),
        }
    
    def display_statistics(self):
        """Display file statistics"""
        if not self.is_valid:
            print("Invalid scenario file")
            return

        stats = self.get_statistics()
        print("File Statistics:")
        print("-" * 60)
        print(f"  Total Size:       {stats['file_size']:,} bytes")
        print(f"  Zero Bytes:       {stats['zero_bytes']:,} bytes ({stats['zero_percentage']:.1f}%)")
        print(f"  Data Bytes:       {stats['data_bytes']:,} bytes ({100-stats['zero_percentage']:.1f}%)")
        print(f"  ASCII Strings:    {stats['string_count']}")
        print()

    def write(self, filename: str):
        """Write the complete scenario bytes to a file."""
        if not self.is_valid:
            raise ValueError("Cannot write invalid scenario")
        self.save_bytes(self.data, filename)

    def patch_in_place(self, patches: list, output_file: str = None, create_backup: bool = False):
        """
        Apply patches to specific file offsets without rewriting entire file.

        This is the preferred method for saving modifications as it only changes
        the bytes that were actually modified.

        Args:
            patches: List of (offset, bytes) tuples to apply
            output_file: Output filename (defaults to original file)
            create_backup: If True, creates a .bak backup before modifying

        Raises:
            ValueError: If scenario is invalid or patches are out of bounds
        """
        import shutil

        if not self.is_valid:
            raise ValueError("Cannot patch invalid scenario")

        if output_file is None:
            output_file = str(self.filename)

        # Validate all patches before applying any
        for offset, new_bytes in patches:
            if offset < 0:
                raise ValueError(f"Patch offset {offset} is negative")
            if offset + len(new_bytes) > len(self.data):
                raise ValueError(
                    f"Patch at offset {offset} with size {len(new_bytes)} "
                    f"exceeds file size {len(self.data)}"
                )

        # Create backup if requested and modifying original file
        if create_backup and output_file == str(self.filename):
            backup_path = str(self.filename) + '.bak'
            shutil.copy2(str(self.filename), backup_path)

        # Create mutable copy of file data
        data = bytearray(self.data)

        # Apply each patch
        for offset, new_bytes in patches:
            if isinstance(new_bytes, int):
                new_bytes = bytes([new_bytes])
            data[offset:offset + len(new_bytes)] = new_bytes

        # Write patched data
        with open(output_file, 'wb') as f:
            f.write(data)

        # Update internal data if we modified the original file
        if output_file == str(self.filename):
            self.data = bytes(data)

        return len(patches)

    def get_byte(self, offset: int) -> int:
        """Get a single byte at the given offset"""
        if offset < 0 or offset >= len(self.data):
            raise ValueError(f"Offset {offset} out of bounds")
        return self.data[offset]

    def get_word(self, offset: int) -> int:
        """Get a 16-bit little-endian word at the given offset"""
        if offset < 0 or offset + 2 > len(self.data):
            raise ValueError(f"Offset {offset} out of bounds for word read")
        return struct.unpack('<H', self.data[offset:offset+2])[0]

    def get_dword(self, offset: int) -> int:
        """Get a 32-bit little-endian dword at the given offset"""
        if offset < 0 or offset + 4 > len(self.data):
            raise ValueError(f"Offset {offset} out of bounds for dword read")
        return struct.unpack('<I', self.data[offset:offset+4])[0]


def main():
    """Command-line interface"""
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    if len(sys.argv) < 2:
        print("Usage: scenario_parser.py <scenario.scn>")
        sys.exit(1)
    
    filename = sys.argv[1]
    
    scenario = DdayScenario(filename)
    
    if not scenario.is_valid:
        print(f"Error: {filename} is not a valid D-Day scenario file")
        sys.exit(1)
    
    scenario.display_header()
    scenario.display_data_sections()
    scenario.display_statistics()
    scenario.display_strings()
    
    if scenario.validate():
        print("File validation: PASSED ✓")
    else:
        print("File validation: WARNINGS ⚠")


if __name__ == '__main__':
    main()
