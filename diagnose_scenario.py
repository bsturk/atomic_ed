#!/usr/bin/env python3
"""
Diagnostic script to check scenario loading and parsing
Run this to verify your installation is working correctly
"""

from dday_scenario_parser import DdayScenario
import sys

def diagnose_scenario(filename):
    print("=" * 70)
    print("D-Day Scenario Editor - Diagnostic Tool")
    print("=" * 70)
    print()

    print(f"Testing scenario: {filename}")
    print()

    # Step 1: Load scenario
    print("[1/5] Loading scenario file...")
    try:
        scenario = DdayScenario(filename)
        if scenario.is_valid:
            print(f"✓ Scenario loaded successfully ({len(scenario.data):,} bytes)")
        else:
            print("✗ Scenario failed validation")
            return False
    except Exception as e:
        print(f"✗ Failed to load: {e}")
        return False
    print()

    # Step 2: Check sections
    print("[2/5] Checking data sections...")
    for name, start, end in scenario.section_order:
        size = end - start
        print(f"  {name}: 0x{start:06x}-0x{end:06x} ({size:,} bytes)")
    print()

    # Step 3: Parse units
    print("[3/5] Parsing units...")
    try:
        # Import the parser from the GUI file
        sys.path.insert(0, '.')
        from test_unit_parser import EnhancedUnitParser

        units = EnhancedUnitParser.parse_units_from_scenario(scenario)
        print(f"✓ Found {len(units)} units")

        if units:
            print(f"  Sample units:")
            for unit in units[:5]:
                strength = unit.get('strength', 0)
                print(f"    - {unit['name']} (Str: {strength}, Section: {unit['section']})")
        else:
            print("  ⚠ Warning: No units found")
    except Exception as e:
        print(f"✗ Unit parsing failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    print()

    # Step 4: Parse mission text
    print("[4/5] Parsing mission briefings...")
    try:
        presection_start = 0x60
        first_section = min(start for _, start, _ in scenario.section_order)
        presection_data = scenario.data[presection_start:first_section]

        mission_blocks = []
        in_text = False
        current_text = b''

        for i, byte in enumerate(presection_data):
            if 32 <= byte <= 126:
                if not in_text:
                    in_text = True
                current_text += bytes([byte])
            else:
                if in_text and len(current_text) >= 30:
                    text = current_text.decode('ascii', errors='ignore').strip()
                    mission_blocks.append(text)
                in_text = False
                current_text = b''

        print(f"✓ Found {len(mission_blocks)} mission text blocks")
        if mission_blocks:
            allied_blocks = [b for i, b in enumerate(mission_blocks) if i % 2 == 0]
            axis_blocks = [b for i, b in enumerate(mission_blocks) if i % 2 == 1]
            print(f"  Allied briefing: {len(allied_blocks[0])} chars" if allied_blocks else "  No Allied briefing")
            print(f"  Axis briefing: {len(axis_blocks[0])} chars" if axis_blocks else "  No Axis briefing")
        else:
            print("  ⚠ Warning: No mission text found")
    except Exception as e:
        print(f"✗ Mission text parsing failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    print()

    # Step 5: Parse coordinates
    print("[5/5] Parsing coordinate data...")
    try:
        ptr5_data = scenario.sections.get('PTR5', b'')

        coords = []
        import struct
        for i in range(0, min(len(ptr5_data), 512), 2):
            if i + 2 <= len(ptr5_data):
                value = struct.unpack('<H', ptr5_data[i:i+2])[0]
                if value > 0:
                    coords.append(value)

        print(f"✓ Found {len(coords)} non-zero coordinate values")
        if coords:
            print(f"  Value range: {min(coords)} - {max(coords)}")
    except Exception as e:
        print(f"✗ Coordinate parsing failed: {e}")
        return False
    print()

    # Summary
    print("=" * 70)
    print("✓ All diagnostic checks passed!")
    print("=" * 70)
    print()
    print("Your scenario editor installation appears to be working correctly.")
    print()
    print("If the GUI editor shows empty tabs:")
    print("1. Check the console for error messages")
    print("2. Try opening a different scenario file")
    print("3. Ensure you're using Python 3.7+")
    print("4. Verify tkinter is installed: python3 -c 'import tkinter'")
    print()

    return True


if __name__ == '__main__':
    if len(sys.argv) > 1:
        filename = sys.argv[1]
    else:
        filename = 'game/SCENARIO/OMAHA.SCN'

    success = diagnose_scenario(filename)
    sys.exit(0 if success else 1)
