#!/usr/bin/env python3
"""
Analyze behavior bytes in D-Day scenarios to find unknown values
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from lib.scenario_parser import DdayScenario

# Unit type mappings (extracted from scenario_editor.py to avoid GUI dependencies)
UNIT_TYPE_NAMES = {
    # Infantry Types
    0x00: 'Infantry-Bn', 0x01: 'Airborne-Bn', 0x02: 'Infantry-Bn', 0x04: 'SS-Bn',
    0x08: 'Glider-Bn', 0x0b: 'SS-Regiment', 0x0f: 'FJ-Co', 0x1d: 'Static-Bn',
    0x27: 'Panzer-Co', 0x32: 'Heavy-Co', 0x35: 'Panzer-Bn', 0x38: 'FJ-Heavy',
    0x41: 'PzGren-Bn', 0x62: 'FJ-Heavy',
    # Armor Types
    0x0d: 'Panzer-Heavy', 0x28: 'Tank-Bn', 0x29: 'Tank-Bn', 0x2a: 'Tank-Co',
    0x60: 'Combat-Cmd-A', 0x61: 'Combat-Cmd-B',
    # Artillery Types
    0x18: 'Artillery', 0x24: 'Arty-Group', 0x25: 'Arty-Group', 0x43: 'Artillery',
    # Support Types
    0x1b: 'Engineer', 0x16: 'Eng-Co', 0x34: 'Assault-Gun', 0x10: 'Flak-Regt',
    0x36: 'AAA/Heavy', 0x40: 'Cavalry', 0x5f: 'Recon',
    # Air Units
    0x26: 'Luftwaffe',
    # Command Levels
    0x07: 'Division-HQ', 0x11: 'Corps', 0x12: 'Korps', 0x13: 'Division',
    0x14: 'Static-Div', 0x15: 'Regiment', 0x17: 'Company', 0x1c: 'Static-HQ',
    0x2b: 'Army-HQ', 0x5e: 'Static-Regt',
}

def get_unit_type_name(type_code):
    """Convert unit type code to human-readable name"""
    return UNIT_TYPE_NAMES.get(type_code, f'Type-{type_code:02x}')

def analyze_behavior_bytes(scenario_file):
    """Extract and analyze behavior bytes from a scenario"""

    print(f"Analyzing: {scenario_file}")
    print("=" * 80)

    scenario = DdayScenario(scenario_file)

    if not scenario.is_valid:
        print("ERROR: Invalid scenario file")
        return

    # Known behavior mappings
    known_behaviors = {
        0x00: 'Idle/Ready',
        0xF2: 'Waiting/Defending',
        0x80: 'Active/Moving',
        0x92: 'Executing Order',
        0x02: 'Advance (Offensive)',
        0x10: 'Defend If Attacked',
        0x82: 'Retreat If Attacked',
        0x0B: 'Hold At All Costs'
    }

    # Look for 8-byte unit records in PTR6 section (unit definitions)
    ptr6_data = scenario.sections.get('PTR6', b'')

    if not ptr6_data:
        print("No PTR6 section found!")
        return

    print(f"PTR6 Section size: {len(ptr6_data)} bytes")
    print()

    # Unit records appear to be 8 bytes each
    # Format (hypothesized):
    #   Byte 0: Type code
    #   Byte 1-4: Unknown/positioning?
    #   Byte 5: Behavior byte
    #   Byte 6-7: More data

    print("Analyzing unit records (8-byte structures):")
    print("-" * 80)
    print(f"{'Offset':<10} {'Type':<12} {'Behavior':<10} {'Full Record (hex)':<40}")
    print("-" * 80)

    behavior_counts = {}
    unit_type_behavior = []  # Store (type, behavior) pairs

    # Scan through PTR6 looking for unit records
    # Try to identify records by looking for valid unit type codes
    valid_unit_types = set(UNIT_TYPE_NAMES.keys())

    offset = 0
    while offset + 8 <= len(ptr6_data):
        # Extract 8-byte record
        record = ptr6_data[offset:offset+8]

        type_byte = record[0]
        behavior_byte = record[5]  # Behavior at offset +5

        # Check if this looks like a unit record
        # (type byte should be a known unit type)
        if type_byte in valid_unit_types:
            type_name = get_unit_type_name(type_byte)
            behavior_name = known_behaviors.get(behavior_byte, f'UNKNOWN')

            # Count behavior occurrences
            if behavior_byte not in behavior_counts:
                behavior_counts[behavior_byte] = 0
            behavior_counts[behavior_byte] += 1

            # Store pairing
            unit_type_behavior.append((type_byte, type_name, behavior_byte))

            # Format record as hex
            hex_record = ' '.join(f'{b:02X}' for b in record)

            # Highlight unknown behaviors
            if behavior_byte not in known_behaviors:
                print(f"0x{offset:06X}  {type_name:<12} 0x{behavior_byte:02X} **** {hex_record}")
            else:
                print(f"0x{offset:06X}  {type_name:<12} 0x{behavior_byte:02X}      {hex_record}")

        offset += 8

    print()
    print("=" * 80)
    print("BEHAVIOR BYTE STATISTICS")
    print("=" * 80)
    print(f"{'Byte Value':<15} {'Count':<8} {'Status':<20} {'Known As':<30}")
    print("-" * 80)

    # Sort by count (most common first)
    for byte_val, count in sorted(behavior_counts.items(), key=lambda x: -x[1]):
        status = "KNOWN" if byte_val in known_behaviors else "*** UNKNOWN ***"
        known_as = known_behaviors.get(byte_val, "???")
        print(f"0x{byte_val:02X}            {count:<8} {status:<20} {known_as:<30}")

    # Find unknown bytes
    unknown_bytes = set(behavior_counts.keys()) - set(known_behaviors.keys())

    if unknown_bytes:
        print()
        print("=" * 80)
        print("UNKNOWN BEHAVIOR BYTES FOUND")
        print("=" * 80)

        for byte_val in sorted(unknown_bytes):
            print(f"\nBehavior Byte 0x{byte_val:02X} (appears {behavior_counts[byte_val]} times):")
            print("  Used by unit types:")

            # Find which unit types use this behavior
            types_using = {}
            for type_byte, type_name, behavior in unit_type_behavior:
                if behavior == byte_val:
                    if type_name not in types_using:
                        types_using[type_name] = 0
                    types_using[type_name] += 1

            for type_name, count in sorted(types_using.items(), key=lambda x: -x[1]):
                print(f"    - {type_name}: {count} units")

    # Print raw PTR6 hex dump for manual inspection
    print()
    print("=" * 80)
    print("PTR6 RAW HEX DUMP (first 512 bytes)")
    print("=" * 80)
    for i in range(0, min(512, len(ptr6_data)), 16):
        hex_str = ' '.join(f'{b:02X}' for b in ptr6_data[i:i+16])
        ascii_str = ''.join(chr(b) if 32 <= b < 127 else '.' for b in ptr6_data[i:i+16])
        print(f"0x{i:06X}:  {hex_str:<48}  {ascii_str}")


if __name__ == '__main__':
    if len(sys.argv) < 2:
        scenario_file = '/src/proj/mods/atomic_ed/game/SCENARIO/BRADLEY.SCN'
        print(f"No file specified, using default: {scenario_file}")
    else:
        scenario_file = sys.argv[1]

    analyze_behavior_bytes(scenario_file)
