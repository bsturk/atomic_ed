#!/usr/bin/env python3
"""Test the enhanced unit parser without tkinter"""

from dday_scenario_parser import DdayScenario
import struct
import re

class EnhancedUnitParser:
    """Enhanced parser for unit data with better structure understanding"""

    # Unit type code mappings (reverse-engineered from binary data)
    UNIT_TYPE_NAMES = {
        0x00: 'Battalion',      # Generic battalion
        0x01: 'Battalion',      # Infantry battalion
        0x02: 'Battalion',      # Special battalion
        0x07: 'Division-HQ',    # Division headquarters
        0x08: 'Battalion',      # Glider battalion
        0x11: 'Corps',          # Corps level
        0x13: 'Division',       # Division level
        0x15: 'Regiment',       # Regiment level
        0x17: 'Company',        # Company level
        0x18: 'Artillery',      # Artillery battalion
        0x1b: 'Engineer',       # Engineer battalion
        0x28: 'Tank-Bn',        # Tank battalion
        0x29: 'Tank-Bn',        # Tank battalion (variant)
        0x2a: 'Tank-Co',        # Tank company (detachment)
        0x36: 'AAA',            # Anti-aircraft artillery
        0x40: 'Cavalry',        # Cavalry squadron
        0x41: 'Battalion',      # Airborne battalion
        0x43: 'Artillery',      # Artillery battalion
        0x60: 'Combat-Cmd-A',   # Combat Command A (armor)
        0x61: 'Combat-Cmd-B',   # Combat Command B (armor)
    }

    @staticmethod
    def get_unit_type_name(type_code):
        """Convert unit type code to human-readable name"""
        return EnhancedUnitParser.UNIT_TYPE_NAMES.get(type_code, f'Type-{type_code:02x}')

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

        # Find null-terminated ASCII strings (more accurate for unit names)
        pattern = b'[\x20-\x7e]{4,30}\x00'
        matches = re.finditer(pattern, data)

        unit_index = start_index

        for match in matches:
            # Remove the null terminator
            unit_name = match.group()[:-1].decode('ascii', errors='ignore').strip()

            # More strict validation
            if not unit_name or len(unit_name) < 4:
                continue

            # Reject strings with too many special characters
            special_count = sum(1 for c in unit_name if c in '!@#$%^&*()+=[]{}|\\<>?/~`')
            if special_count > 2:
                continue

            # Must start with alphanumeric
            if not unit_name[0].isalnum():
                continue

            # Skip common non-unit strings
            skip_words = ['Your', 'The', 'You', 'and', 'are', 'for', 'with', 'that',
                         'http', 'www', 'Allied', 'Axis', 'beachhead', 'capture',
                         'attack', 'defend', 'objective', 'must', 'will', 'have']
            if any(word.lower() in unit_name.lower() for word in skip_words):
                continue

            # Look for unit-like patterns
            has_number = any(c.isdigit() for c in unit_name)

            # Check for Roman numerals (whole words only)
            roman_pattern = r'\b(I|II|III|IV|V|VI|VII|VIII|IX|X|XI|XII)\b'
            has_roman = bool(re.search(roman_pattern, unit_name))

            military_terms = ['Corps', 'Infantry', 'Airborne', 'Division', 'FJ',
                             'Schnelle', 'Panzer', 'Armor', 'Regiment', 'Battalion',
                             'Brigade', 'Artillery', 'Cavalry', 'Recon', 'Engineer']
            has_military = any(term in unit_name for term in military_terms)

            # Common unit naming patterns
            dash_pattern = r'^\d+[A-Z]?-\d+[A-Z]?-\d+[A-Z]*$|^[A-Z]-\d+-[IVX]+$|^[IVX]+-\d+-[A-Z0-9]+$'
            matches_pattern = bool(re.match(dash_pattern, unit_name))

            # "101st", "82nd", "3rd" style
            ordinal_pattern = r'\d+(st|nd|rd|th)\b'
            has_ordinal = bool(re.search(ordinal_pattern, unit_name))

            if has_number or has_roman or has_military or matches_pattern or has_ordinal:
                # Get surrounding binary context for stats
                context_start = max(0, match.start() - 32)
                context_end = min(len(data), match.end() + 32)
                context = data[context_start:context_end]

                # Try to extract stats from binary data before the name
                strength = 0
                unit_type = 0

                if match.start() >= 32:
                    # Look at bytes before the unit name
                    # Unit type is at offset -27 (27 bytes before name)
                    # Strength appears to be at offset -4
                    pre_data = data[match.start()-32:match.start()]

                    # Extract unit type from byte at position -27
                    if len(pre_data) >= 27:
                        unit_type = pre_data[-27]

                    # Extract strength from byte at position -4
                    if len(pre_data) >= 4:
                        strength_byte = pre_data[-4]
                        # Strength seems to be in range 1-10, might be a category
                        # or base strength value
                        if 1 <= strength_byte <= 100:
                            strength = strength_byte

                units.append({
                    'index': unit_index,
                    'name': unit_name,
                    'type': unit_type,
                    'strength': strength,
                    'section': section_name,
                    'offset': offset_base + match.start(),
                    'raw_data': context[:64].hex() if len(context) >= 64 else context.hex()
                })

                unit_index += 1

        return units


if __name__ == '__main__':
    # Test with OMAHA scenario
    scenario = DdayScenario('game/SCENARIO/OMAHA.SCN')

    units = EnhancedUnitParser.parse_units_from_scenario(scenario)

    print(f'Found {len(units)} units in OMAHA.SCN:')
    print()
    print(f'{"#":>3s} {"Unit Name":30s} {"Str":>4s} {"Type":15s} {"Section":7s} {"Offset":8s}')
    print('-' * 80)

    # Show first 40
    for unit in units[:40]:
        strength = unit.get('strength', 0)
        strength_str = str(strength) if strength > 0 else '-'
        type_code = unit.get('type', 0)
        type_name = EnhancedUnitParser.get_unit_type_name(type_code)
        print(f'{unit["index"]:3d}. {unit["name"]:30s} {strength_str:>4s} {type_name:15s} {unit["section"]:7s} 0x{unit["offset"]:06x}')

    if len(units) > 40:
        print(f'\n... and {len(units) - 40} more units')

    # Show statistics
    print()
    print('=== Statistics ===')
    units_with_strength = [u for u in units if u.get('strength', 0) > 0]
    print(f'Total units: {len(units)}')
    print(f'Units with strength data: {len(units_with_strength)} ({100*len(units_with_strength)//len(units)}%)')
    if units_with_strength:
        strengths = [u['strength'] for u in units_with_strength]
        print(f'Strength range: {min(strengths)} - {max(strengths)}')
