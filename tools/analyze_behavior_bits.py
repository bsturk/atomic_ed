#!/usr/bin/env python3
"""
Analyze behavior bytes as bit flags to discover meaning
"""

import sys
from pathlib import Path
from collections import defaultdict
sys.path.insert(0, str(Path(__file__).parent.parent))

from lib.scenario_parser import DdayScenario

# Unit type mappings
UNIT_TYPE_NAMES = {
    0x00: 'Infantry-Bn', 0x01: 'Airborne-Bn', 0x02: 'Infantry-Bn', 0x04: 'SS-Bn',
    0x08: 'Glider-Bn', 0x0b: 'SS-Regiment', 0x0f: 'FJ-Co', 0x1d: 'Static-Bn',
    0x27: 'Panzer-Co', 0x32: 'Heavy-Co', 0x35: 'Panzer-Bn', 0x38: 'FJ-Heavy',
    0x41: 'PzGren-Bn', 0x62: 'FJ-Heavy', 0x0d: 'Panzer-Heavy', 0x28: 'Tank-Bn',
    0x29: 'Tank-Bn', 0x2a: 'Tank-Co', 0x60: 'Combat-Cmd-A', 0x61: 'Combat-Cmd-B',
    0x18: 'Artillery', 0x24: 'Arty-Group', 0x25: 'Arty-Group', 0x43: 'Artillery',
    0x1b: 'Engineer', 0x16: 'Eng-Co', 0x34: 'Assault-Gun', 0x10: 'Flak-Regt',
    0x36: 'AAA/Heavy', 0x40: 'Cavalry', 0x5f: 'Recon', 0x26: 'Luftwaffe',
    0x07: 'Division-HQ', 0x11: 'Corps', 0x12: 'Korps', 0x13: 'Division',
    0x14: 'Static-Div', 0x15: 'Regiment', 0x17: 'Company', 0x1c: 'Static-HQ',
    0x2b: 'Army-HQ', 0x5e: 'Static-Regt',
}

def analyze_bit_patterns(scenario_file):
    """Analyze behavior bytes as bit flags"""

    print(f"Analyzing: {scenario_file}")
    print("=" * 80)

    scenario = DdayScenario(scenario_file)

    if not scenario.is_valid:
        print("ERROR: Invalid scenario file")
        return

    ptr6_data = scenario.sections.get('PTR6', b'')

    if not ptr6_data:
        print("No PTR6 section found!")
        return

    print("BIT PATTERN ANALYSIS")
    print("=" * 80)
    print()

    # Collect all behavior bytes
    behavior_bytes = []
    valid_unit_types = set(UNIT_TYPE_NAMES.keys())

    offset = 0
    while offset + 8 <= len(ptr6_data):
        record = ptr6_data[offset:offset+8]
        type_byte = record[0]
        behavior_byte = record[5]

        if type_byte in valid_unit_types:
            behavior_bytes.append((type_byte, behavior_byte, offset))

        offset += 8

    # Analyze individual bits
    print("BIT FREQUENCY ANALYSIS (which bits are set most often)")
    print("-" * 80)

    bit_counts = [0] * 8
    total_non_zero = 0

    for type_byte, behavior, offset in behavior_bytes:
        if behavior != 0x00:
            total_non_zero += 1
            for bit in range(8):
                if behavior & (1 << bit):
                    bit_counts[bit] += 1

    print(f"Total records: {len(behavior_bytes)}")
    print(f"Non-zero behavior bytes: {total_non_zero}")
    print()
    print(f"{'Bit':<8} {'Hex Mask':<12} {'Count':<10} {'Percentage':<15} {'Interpretation'}")
    print("-" * 80)

    for bit in range(8):
        mask = 1 << bit
        count = bit_counts[bit]
        pct = (count / total_non_zero * 100) if total_non_zero > 0 else 0

        # Propose interpretation based on frequency
        if pct > 80:
            interp = "COMMON FLAG - likely status bit"
        elif pct > 40:
            interp = "FREQUENT FLAG - major state"
        elif pct > 10:
            interp = "Occasional flag"
        elif pct > 1:
            interp = "Rare flag"
        else:
            interp = "Very rare"

        print(f"Bit {bit:<4} 0x{mask:02X}        {count:<10} {pct:>5.1f}%         {interp}")

    print()
    print("=" * 80)
    print("COMMON BIT COMBINATIONS")
    print("=" * 80)
    print()

    # Find common bit patterns
    pattern_counts = defaultdict(int)
    for type_byte, behavior, offset in behavior_bytes:
        if behavior != 0x00:
            pattern_counts[behavior] += 1

    # Show top patterns
    print(f"{'Value':<8} {'Binary':<12} {'Count':<8} {'Bits Set':<12} {'Possible Meaning'}")
    print("-" * 80)

    for behavior, count in sorted(pattern_counts.items(), key=lambda x: -x[1])[:30]:
        binary = f"{behavior:08b}"
        bits_set = [str(i) for i in range(8) if behavior & (1 << i)]
        bits_str = ",".join(bits_set) if bits_set else "none"

        # Try to infer meaning
        meaning = infer_meaning(behavior)

        print(f"0x{behavior:02X}     {binary}    {count:<8} {bits_str:<12} {meaning}")

    # Analyze specific values mentioned by user
    print()
    print("=" * 80)
    print("USER-SPECIFIED VALUES ANALYSIS (0x28, 0x1B, 0x25)")
    print("=" * 80)
    print()

    user_values = [0x28, 0x1B, 0x25]

    for val in user_values:
        print(f"Value: 0x{val:02X} = {val:3d} = 0b{val:08b}")
        print(f"  Bit pattern: ", end="")
        for bit in range(7, -1, -1):
            if val & (1 << bit):
                print(f"Bit{bit} ", end="")
        print()

        # Find where this value appears
        matches = [(t, o) for t, b, o in behavior_bytes if b == val]
        if matches:
            print(f"  Appears {len(matches)} times")
            print(f"  Unit types using this:")
            type_counts = defaultdict(int)
            for type_byte, offset in matches:
                type_counts[UNIT_TYPE_NAMES.get(type_byte, f"0x{type_byte:02X}")] += 1
            for unit_type, count in sorted(type_counts.items(), key=lambda x: -x[1]):
                print(f"    - {unit_type}: {count}")
        else:
            print(f"  NOT FOUND in this scenario")

        print(f"  Possible interpretation: {infer_meaning(val)}")
        print()


def infer_meaning(byte_val):
    """Infer possible meaning from bit pattern"""

    if byte_val == 0x00:
        return "Idle/Default state"

    if byte_val == 0xFF:
        return "All flags set - special/invalid marker?"

    if byte_val == 0xFD:
        return "Almost all flags - disabled/template unit?"

    meanings = []

    # Check common patterns
    if byte_val & 0x01:
        meanings.append("Bit0: Active/Enabled?")
    if byte_val & 0x02:
        meanings.append("Bit1: Mobile/Can move?")
    if byte_val & 0x04:
        meanings.append("Bit2: Combat capable?")
    if byte_val & 0x08:
        meanings.append("Bit3: Special orders?")
    if byte_val & 0x10:
        meanings.append("Bit4: Defensive stance?")
    if byte_val & 0x20:
        meanings.append("Bit5: Aggressive/Attack?")
    if byte_val & 0x40:
        meanings.append("Bit6: Reserved/Hold?")
    if byte_val & 0x80:
        meanings.append("Bit7: High-priority/Critical?")

    if len(meanings) > 3:
        return f"{len(meanings)} flags set"

    return " | ".join(meanings) if meanings else "Unknown pattern"


if __name__ == '__main__':
    if len(sys.argv) < 2:
        scenario_file = '/src/proj/mods/atomic_ed/game/SCENARIO/BRADLEY.SCN'
        print(f"No file specified, using default: {scenario_file}")
    else:
        scenario_file = sys.argv[1]

    analyze_bit_patterns(scenario_file)
