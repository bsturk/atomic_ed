#!/usr/bin/env python3
"""
D-Day Scenario File Format Parser
==================================

This module provides utilities for reading and analyzing D-Day (.SCN) scenario files.

Format: D-Day .SCN scenario files (magic number 0x1230)
Status: Reverse engineered from 7 D-Day scenario files
Version: 1.0

Usage:
    from dday_scenario_parser import DdayScenario
    
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
    
    # Expected fixed header counts (mostly fixed, but dimensions can vary)
    # Note: Count 11 (height) and Count 12 (width) vary by scenario
    # Most scenarios: 100 wide × 125 tall, but COBRA.SCN is 100 wide × 112 tall
    FIXED_COUNTS = [
        0x11, 0x05, 0x0a, 0x08, 0x05, 0x08, 0x00,
        0x0a, 0x14, 0x05, 0x7d, 0x64
    ]
    
    # Offset positions in header
    COUNT_OFFSETS = [
        0x04, 0x08, 0x0c, 0x10, 0x14, 0x18, 0x1c,
        0x20, 0x24, 0x28, 0x2c, 0x30
    ]
    
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
    
    def _parse_counts(self):
        """Parse the 12 count fields from header"""
        for offset in self.COUNT_OFFSETS:
            value = struct.unpack('<I', self.data[offset:offset+4])[0]
            self.counts.append(value)

    @property
    def map_height(self) -> int:
        """Map height in hexes (Count 11 at offset 0x2c) - rows (vertical)"""
        return self.counts[10] if len(self.counts) > 10 else 125

    @property
    def map_width(self) -> int:
        """Map width in hexes (Count 12 at offset 0x30) - columns (horizontal)"""
        return self.counts[11] if len(self.counts) > 11 else 100
    
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
        """Validate scenario file integrity"""
        if not self.is_valid:
            return False

        # Check counts match expected
        if self.counts != self.FIXED_COUNTS:
            print("Warning: Counts don't match expected values")
            return False

        # Check pointer ordering (file order, not header order!)
        # Expected file order: PTR5 -> PTR6 -> PTR3 -> PTR4
        if len(self.section_order) >= 2:
            for i in range(len(self.section_order) - 1):
                if self.section_order[i][1] >= self.section_order[i + 1][1]:
                    print(f"Warning: Section ordering violated between {self.section_order[i][0]} and {self.section_order[i+1][0]}")
                    return False

        # Check pointers within bounds
        file_size = len(self.data)
        for name, ptr in self.pointers.items():
            if ptr > 0 and ptr >= file_size:
                print(f"Warning: {name} = 0x{ptr:06x} exceeds file size {file_size}")
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
        
        # Counts
        print("Header Counts (Fixed across all scenarios):")
        print("-" * 60)
        count_labels = [
            "Count 1  (terrain/unit types?)",
            "Count 2  (players/sides?)",
            "Count 3  (unknown)",
            "Count 4  (unit classes?)",
            "Count 5  (player types?)",
            "Count 6  (unit classes?)",
            "Count 7  (reserved)",
            "Count 8  (unknown)",
            "Count 9  (objectives?)",
            "Count 10 (unknown)",
            "Count 11 (MAP HEIGHT in hexes - rows/vertical)",
            "Count 12 (MAP WIDTH in hexes - columns/horizontal)",
        ]
        
        for i, (count, label) in enumerate(zip(self.counts, count_labels)):
            expected = self.FIXED_COUNTS[i]
            match = "✓" if count == expected else "✗"
            offset = self.COUNT_OFFSETS[i]
            print(f"  0x{offset:02x}: {count:3d} (0x{count:02x})  {match}  {label}")
        print()
        
        # Pointers
        print("Offset Pointers (Vary per scenario):")
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
        """Display data section information"""
        if not self.is_valid:
            print("Invalid scenario file")
            return

        print("Data Sections (in file order):")
        print("-" * 60)

        # Display sections in file order
        for name, start, end in self.section_order:
            size = end - start

            # Add descriptive labels
            labels = {
                'PTR3': 'Unit Roster',
                'PTR4': 'Unit Positioning + Text',
                'PTR5': 'Numeric/Coordinate Data',
                'PTR6': 'Specialized/AI Data'
            }
            label = labels.get(name, 'Unknown')

            print(f"  {name} ({label:25s}): 0x{start:06x} - 0x{end:06x} ({size:,} bytes)")

            # Show first 32 bytes
            if start < len(self.data):
                sample = self.data[start:min(start+32, end)]
                hex_str = ' '.join(f'{b:02x}' for b in sample)
                ascii_str = ''.join(chr(b) if 32 <= b < 127 else '.' for b in sample)
                print(f"      Hex:   {hex_str}")
                print(f"      ASCII: {ascii_str}")
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
        """Write scenario to file

        CRITICAL: The file structure includes data before the first pointer!
        Also critical: Section order varies by file! Use actual parsed order.
        """
        if not self.is_valid:
            raise ValueError("Cannot write invalid scenario")

        with open(filename, 'wb') as f:
            # Find the offset of the first section
            first_section_offset = min(start for _, start, _ in self.section_order)

            # Write everything from start of file up to first section
            # This includes header (96 bytes) + any additional data structures
            f.write(self.data[0:first_section_offset])

            # Write data sections in ACTUAL file order (not assumed order!)
            for name, _, _ in self.section_order:
                f.write(self.sections[name])


def main():
    """Command-line interface"""
    if len(sys.argv) < 2:
        print("Usage: dday_scenario_parser.py <scenario.scn>")
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
