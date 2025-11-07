#!/usr/bin/env python3
"""
Mission Text Extractor for D-Day Scenarios
Extracts mission briefings from the pre-section data area
"""

from dday_scenario_parser import DdayScenario
import re

class MissionTextExtractor:
    def __init__(self, scenario: DdayScenario):
        self.scenario = scenario
        self.presection_data = self._get_presection_data()

    def _get_presection_data(self):
        """Get data between header and first section"""
        if not self.scenario.section_order:
            return b''

        first_section_start = min(start for _, start, _ in self.scenario.section_order)
        return self.scenario.data[0x60:first_section_start]

    def extract_text_blocks(self, min_length=20):
        """Extract all text blocks from pre-section data"""
        text_blocks = []
        data = self.presection_data

        current = b''
        start_offset = 0

        for i, byte in enumerate(data):
            if 32 <= byte <= 126 or byte in [10, 13, 9]:  # Printable + whitespace
                if not current:
                    start_offset = i
                current += bytes([byte])
            else:
                if len(current) >= min_length:
                    text = current.decode('ascii', errors='ignore').strip()
                    if text:  # Only add non-empty strings
                        abs_offset = 0x60 + start_offset  # Absolute file offset
                        text_blocks.append({
                            'offset': abs_offset,
                            'length': len(current),
                            'text': text
                        })
                current = b''

        # Don't forget last block
        if len(current) >= min_length:
            text = current.decode('ascii', errors='ignore').strip()
            if text:
                abs_offset = 0x60 + start_offset
                text_blocks.append({
                    'offset': abs_offset,
                    'length': len(current),
                    'text': text
                })

        return text_blocks

    def identify_mission_briefings(self):
        """Identify mission briefing text (usually the longest blocks)"""
        blocks = self.extract_text_blocks(min_length=50)

        # Mission briefings are typically the longest text blocks
        # Sort by length and take top ones
        blocks.sort(key=lambda x: len(x['text']), reverse=True)

        return blocks

    def display_mission_text(self):
        """Display extracted mission text in readable format"""
        blocks = self.identify_mission_briefings()

        print(f"Found {len(blocks)} text blocks in pre-section data")
        print("=" * 80)

        for i, block in enumerate(blocks[:10]):  # Show top 10
            print(f"\n[Block {i+1}] Offset: 0x{block['offset']:06x}, Length: {block['length']} bytes")
            print("-" * 80)

            text = block['text']
            # Wrap text for display
            words = text.split()
            lines = []
            current_line = []
            current_length = 0

            for word in words:
                if current_length + len(word) + 1 <= 76:
                    current_line.append(word)
                    current_length += len(word) + 1
                else:
                    if current_line:
                        lines.append(' '.join(current_line))
                    current_line = [word]
                    current_length = len(word)

            if current_line:
                lines.append(' '.join(current_line))

            for line in lines[:10]:  # Show first 10 lines
                print(line)

            if len(lines) > 10:
                print(f"... ({len(lines) - 10} more lines)")

def main():
    import sys

    if len(sys.argv) < 2:
        print("Usage: mission_text_extractor.py <scenario.scn>")
        sys.exit(1)

    scenario = DdayScenario(sys.argv[1])
    if not scenario.is_valid:
        print(f"Error: Invalid scenario file")
        sys.exit(1)

    extractor = MissionTextExtractor(scenario)
    extractor.display_mission_text()

if __name__ == '__main__':
    main()
