#!/usr/bin/env python3
"""
PTR6 AI/Game Parameter Parser

Parses the PTR6 section of D-Day scenario files and extracts structured data.
"""
import struct
import sys
from typing import List, Dict, Any

sys.path.insert(0, '/src/proj/mods/atomic_ed')
from lib.scenario_parser import DdayScenario


class PTR6Record:
    """Represents a single PTR6 record"""

    def __init__(self, offset: int, length: int, data: bytes):
        self.offset = offset
        self.length = length
        self.data = data
        self.type = self._detect_type()

    def _detect_type(self) -> str:
        """Detect the likely type of this record"""
        if self.length == 0:
            return "padding"
        elif self.length == 1:
            return "flag"
        elif self.length == 449:
            return "sparse_array_449"
        elif self.length < 20:
            return "small_params"
        elif self.length < 100:
            return "medium_data"
        else:
            return "large_data"

    def as_words(self) -> List[int]:
        """Interpret data as 16-bit little-endian words"""
        words = []
        for i in range(0, len(self.data) - 1, 2):
            w = struct.unpack('<H', self.data[i:i+2])[0]
            words.append(w)
        return words

    def find_coordinates(self) -> List[tuple]:
        """Find potential map coordinates in the data"""
        coords = []
        words = self.as_words()

        for i in range(0, len(words) - 1, 2):
            x, y = words[i], words[i+1]
            if 0 < x <= 125 and 0 < y <= 100:
                coords.append((x, y))

        return coords

    def __repr__(self):
        return f"PTR6Record(offset=0x{self.offset:04x}, length={self.length}, type={self.type})"


class PTR6Parser:
    """Parser for PTR6 AI/game parameter data"""

    def __init__(self, data: bytes):
        self.data = data
        self.records = []
        self._parse()

    def _parse(self):
        """Parse PTR6 data into records"""
        i = 0

        while i + 2 <= len(self.data):
            # Read length field
            length = struct.unpack('<H', self.data[i:i+2])[0]

            # Handle padding
            if length == 0:
                zero_start = i
                while i < len(self.data) and self.data[i] == 0:
                    i += 1
                # Record padding segment
                if i - zero_start > 2:
                    self.records.append(PTR6Record(zero_start, 0, b''))
                continue

            # Validate length
            if length > 2048 or i + 2 + length > len(self.data):
                # Invalid length, skip ahead
                i += 2
                continue

            # Extract record data
            record_data = self.data[i+2:i+2+length]
            self.records.append(PTR6Record(i, length, record_data))

            # Move to next record
            i += 2 + length

    def get_records_by_type(self, record_type: str) -> List[PTR6Record]:
        """Get all records of a specific type"""
        return [r for r in self.records if r.type == record_type]

    def find_all_coordinates(self) -> List[tuple]:
        """Find all coordinate pairs across all records"""
        all_coords = []
        for record in self.records:
            coords = record.find_coordinates()
            if coords:
                all_coords.extend(coords)
        return all_coords

    def get_statistics(self) -> Dict[str, Any]:
        """Get statistics about the PTR6 data"""
        type_counts = {}
        length_counts = {}

        for record in self.records:
            type_counts[record.type] = type_counts.get(record.type, 0) + 1
            length_counts[record.length] = length_counts.get(record.length, 0) + 1

        return {
            'total_records': len(self.records),
            'type_distribution': type_counts,
            'length_distribution': length_counts,
            'total_size': len(self.data)
        }


def main():
    """Example usage"""
    import sys

    if len(sys.argv) > 1:
        filename = sys.argv[1]
    else:
        filename = '/src/proj/mods/atomic_ed/game/SCENARIO/CAMPAIGN.SCN'

    print(f"Parsing PTR6 from: {filename}")
    print("="*80)

    scn = DdayScenario(filename)
    ptr6_data = scn.sections.get('PTR6', b'')

    if not ptr6_data:
        print("No PTR6 data found!")
        return

    # Parse
    parser = PTR6Parser(ptr6_data)

    # Statistics
    stats = parser.get_statistics()

    print(f"\nPTR6 Statistics:")
    print(f"  Total size: {stats['total_size']} bytes")
    print(f"  Total records: {stats['total_records']}")

    print(f"\nRecord types:")
    for rtype, count in sorted(stats['type_distribution'].items()):
        print(f"  {rtype:20s}: {count:4d} records")

    print(f"\nCommon lengths:")
    sorted_lengths = sorted(stats['length_distribution'].items(),
                           key=lambda x: x[1], reverse=True)
    for length, count in sorted_lengths[:10]:
        print(f"  {length:4d} bytes: {count:4d} records")

    # Show some examples
    print(f"\n\nExample Records:")
    print("="*80)

    for record_type in ['flag', 'small_params', 'sparse_array_449']:
        records = parser.get_records_by_type(record_type)
        if records:
            print(f"\n{record_type.upper()} (showing first 3):")
            for record in records[:3]:
                print(f"  {record}")
                if record.type != 'flag' and len(record.data) >= 16:
                    words = record.as_words()[:8]
                    print(f"    First words: {words}")
                    coords = record.find_coordinates()
                    if coords:
                        print(f"    Coordinates: {coords[:5]}{'...' if len(coords) > 5 else ''}")

    # Coordinate analysis
    all_coords = parser.find_all_coordinates()
    if all_coords:
        print(f"\n\nCoordinate Analysis:")
        print("="*80)
        print(f"Total coordinate pairs found: {len(all_coords)}")
        print(f"Sample coordinates: {all_coords[:20]}")


if __name__ == '__main__':
    main()
