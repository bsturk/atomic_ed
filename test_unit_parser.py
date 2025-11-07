#!/usr/bin/env python3
"""Test the enhanced unit parser without tkinter"""

from dday_scenario_parser import DdayScenario
import struct
import re

class EnhancedUnitParser:
    """Enhanced parser for unit data with better structure understanding"""

    @staticmethod
    def parse_units_from_scenario(scenario):
        """Parse units from scenario - searches PTR4 and PTR6 sections"""
        units = []

        if not scenario:
            return units

        # Unit names are actually in PTR4 and PTR6, not PTR3!
        # PTR4 contains unit positioning and names
        # PTR6 contains unit definitions

        unit_index = 0

        # Parse from PTR6 (unit definitions)
        ptr6_data = scenario.sections.get('PTR6', b'')
        if ptr6_data:
            units.extend(EnhancedUnitParser._extract_units_from_data(
                ptr6_data, 'PTR6', unit_index))
            unit_index = len(units)

        # Parse from PTR4 (unit instances/positioning)
        ptr4_data = scenario.sections.get('PTR4', b'')
        if ptr4_data:
            # Skip mission text at the beginning (first ~10KB typically)
            # Look for unit names in the latter part
            search_start = min(10000, len(ptr4_data) // 2)
            units.extend(EnhancedUnitParser._extract_units_from_data(
                ptr4_data[search_start:], 'PTR4', unit_index, search_start))

        return units

    @staticmethod
    def _extract_units_from_data(data, section_name, start_index, offset_base=0):
        """Extract unit names from binary data"""
        units = []

        if not data:
            return units

        # Find all ASCII strings that look like unit names
        pattern = b'[\x20-\x7e]{3,30}'
        matches = re.finditer(pattern, data)

        unit_index = start_index

        for match in matches:
            unit_name = match.group().decode('ascii', errors='ignore').strip()

            # Filter for likely unit names
            if not unit_name or len(unit_name) < 3:
                continue

            # Skip common non-unit strings
            skip_words = ['Your', 'The', 'You', 'and', 'are', 'for', 'with',
                         'http', 'www', 'Allied', 'Axis', 'beachhead']
            if any(word in unit_name for word in skip_words):
                continue

            # Look for unit-like patterns
            has_number = any(c.isdigit() for c in unit_name)
            has_roman = any(word in unit_name for word in ['I', 'II', 'III', 'IV', 'V', 'VI', 'VII', 'VIII', 'IX', 'X'])
            has_military = any(word in unit_name for word in ['Corps', 'Infantry', 'Airborne', 'Division', 'FJ', 'Schnelle'])

            if has_number or has_roman or has_military:
                # Get surrounding binary context
                context_start = max(0, match.start() - 16)
                context_end = min(len(data), match.end() + 16)
                context = data[context_start:context_end]

                units.append({
                    'index': unit_index,
                    'name': unit_name,
                    'type': 0,
                    'section': section_name,
                    'offset': offset_base + match.start(),
                    'raw_data': context[:32].hex() if len(context) >= 32 else context.hex()
                })

                unit_index += 1

        return units


if __name__ == '__main__':
    # Test with OMAHA scenario
    scenario = DdayScenario('game/SCENARIO/OMAHA.SCN')

    units = EnhancedUnitParser.parse_units_from_scenario(scenario)

    print(f'Found {len(units)} units in OMAHA.SCN:')
    print()

    # Show first 30
    for unit in units[:30]:
        print(f'{unit["index"]:3d}. {unit["name"]:30s} ({unit["section"]}, 0x{unit["offset"]:06x})')
