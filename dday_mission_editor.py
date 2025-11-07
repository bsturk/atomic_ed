#!/usr/bin/env python3
"""
D-Day Mission Text Editor
Extracts and modifies mission briefings from D-Day scenario files
"""

from dday_scenario_parser import DdayScenario
from pathlib import Path
import struct

class MissionEditor:
    """Editor for D-Day scenario mission text"""

    BLOCK_SIZE = 128  # Each text line is 128 bytes

    def __init__(self, scenario_file):
        self.scenario = DdayScenario(scenario_file)
        if not self.scenario.is_valid:
            raise ValueError(f"Invalid scenario file: {scenario_file}")

        self.mission_texts = self._extract_mission_texts()

    def _get_presection_data(self):
        """Get data between header (0x60) and first section"""
        if not self.scenario.section_order:
            return b''
        first_section_start = min(start for _, start, _ in self.scenario.section_order)
        return self.scenario.data[0x60:first_section_start]

    def _extract_mission_texts(self):
        """Extract mission text blocks

        Mission texts are INTERLEAVED: Allied line 1, Axis line 1, Allied line 2, Axis line 2, etc.
        Each text starts at specific offset and is null-padded to fill its block.
        """
        presection = self._get_presection_data()

        # Scan for all text regions (contiguous printable ASCII)
        text_regions = []
        in_text = False
        start = 0
        current_text = b''

        for i, byte in enumerate(presection):
            if 32 <= byte <= 126:  # Printable ASCII
                if not in_text:
                    start = i
                    in_text = True
                current_text += bytes([byte])
            else:
                if in_text and len(current_text) >= 30:  # Min length for mission text
                    abs_offset = 0x60 + start
                    text = current_text.decode('ascii', errors='ignore').strip()
                    text_regions.append({
                        'offset': abs_offset,
                        'text': text
                    })
                in_text = False
                current_text = b''

        return text_regions

    def get_allied_briefing(self):
        """Get Allied mission briefing lines

        Mission text is interleaved: odd indices (0, 2, 4...) are Allied
        """
        return [block['text'] for i, block in enumerate(self.mission_texts) if i % 2 == 0]

    def get_axis_briefing(self):
        """Get Axis mission briefing lines

        Mission text is interleaved: even indices (1, 3, 5...) are Axis
        """
        return [block['text'] for i, block in enumerate(self.mission_texts) if i % 2 == 1]

    def display_mission_texts(self):
        """Display both mission briefings"""
        print("=" * 80)
        print(f"SCENARIO: {self.scenario.filename.name}")
        print("=" * 80)

        print("\n📋 ALLIED BRIEFING:")
        print("-" * 80)
        for line in self.get_allied_briefing():
            print(f"  {line}")

        print("\n📋 AXIS BRIEFING:")
        print("-" * 80)
        for line in self.get_axis_briefing():
            print(f"  {line}")

        print("\n" + "=" * 80)
        print(f"Total mission text blocks: {len(self.mission_texts)}")

    def replace_text(self, old_text, new_text):
        """Replace mission text in scenario

        IMPORTANT: new_text must fit within 128-byte block limit!
        """
        if len(new_text) > 127:
            raise ValueError(f"Text too long! Maximum 127 characters, got {len(new_text)}")

        old_bytes = old_text.encode('ascii')
        new_bytes = new_text.encode('ascii')

        # Find the text in the data
        pos = self.scenario.data.find(old_bytes)
        if pos < 0:
            raise ValueError(f"Text not found: {old_text[:50]}...")

        # Determine which 128-byte block this is in
        presection_start = 0x60
        first_section_start = min(start for _, start, _ in self.scenario.section_order)

        if pos < presection_start or pos >= first_section_start:
            raise ValueError("Text not in mission briefing area")

        # Calculate block alignment
        offset_in_presection = pos - presection_start
        block_start = presection_start + (offset_in_presection // self.BLOCK_SIZE) * self.BLOCK_SIZE

        # Create new block (pad with nulls)
        new_block = new_bytes + (b'\x00' * (self.BLOCK_SIZE - len(new_bytes)))

        # Replace the block
        data_array = bytearray(self.scenario.data)
        data_array[block_start:block_start + self.BLOCK_SIZE] = new_block
        self.scenario.data = bytes(data_array)

        # Re-parse sections since data changed
        self.scenario._parse_sections()

    def save(self, output_file):
        """Save modified scenario"""
        self.scenario.write(output_file)
        print(f"✓ Saved to: {output_file}")


def main():
    import sys

    if len(sys.argv) < 2:
        print("Usage: dday_mission_editor.py <scenario.scn>")
        print("\nExample:")
        print("  python3 dday_mission_editor.py game/dday/game/SCENARIO/OMAHA.SCN")
        sys.exit(1)

    scenario_file = sys.argv[1]
    editor = MissionEditor(scenario_file)
    editor.display_mission_texts()


if __name__ == '__main__':
    main()
