#!/usr/bin/env python3
"""
Test script for D-Day Scenario Creator/Editor
Tests non-GUI components without requiring tkinter
"""

from pathlib import Path
from dday_scenario_parser import DdayScenario
import sys


def test_scenario_loading(scenario_file):
    """Test loading a scenario file"""
    print(f"\n{'='*80}")
    print(f"Testing: {scenario_file.name}")
    print(f"{'='*80}")

    try:
        scenario = DdayScenario(scenario_file)

        if not scenario.is_valid:
            print("❌ FAILED: Invalid scenario file")
            return False

        print("✓ Scenario loaded successfully")

        # Test header
        magic = scenario.data[0:2]
        print(f"✓ Magic number: 0x{int.from_bytes(magic, 'little'):04x}")

        # Test counts
        print(f"✓ Header counts: {scenario.counts}")

        # Test pointers
        print(f"✓ Pointers loaded: {len(scenario.pointers)} pointers")

        # Test sections
        print(f"✓ Data sections: {len(scenario.sections)} sections")
        for name, start, end in scenario.section_order:
            size = end - start
            print(f"  - {name}: {size:,} bytes at 0x{start:06x}")

        # Test statistics
        stats = scenario.get_statistics()
        print(f"✓ Statistics:")
        print(f"  - File size: {stats['file_size']:,} bytes")
        print(f"  - Data density: {100 - stats['zero_percentage']:.1f}%")
        print(f"  - ASCII strings: {stats['string_count']}")

        # Test validation
        if scenario.validate():
            print("✓ Validation: PASSED")
        else:
            print("⚠ Validation: WARNINGS")

        return True

    except Exception as e:
        print(f"❌ FAILED: {e}")
        return False


def test_mission_text_extraction(scenario_file):
    """Test mission text extraction"""
    print(f"\n{'='*80}")
    print(f"Mission Text Extraction: {scenario_file.name}")
    print(f"{'='*80}")

    try:
        scenario = DdayScenario(scenario_file)

        # Extract mission text (same logic as editor)
        presection_start = 0x60
        first_section = min(start for _, start, _ in scenario.section_order)
        presection_data = scenario.data[presection_start:first_section]

        # Find text blocks
        mission_blocks = []
        in_text = False
        start = 0
        current_text = b''

        for i, byte in enumerate(presection_data):
            if 32 <= byte <= 126:
                if not in_text:
                    start = i
                    in_text = True
                current_text += bytes([byte])
            else:
                if in_text and len(current_text) >= 30:
                    abs_offset = presection_start + start
                    text = current_text.decode('ascii', errors='ignore').strip()
                    mission_blocks.append({
                        'offset': abs_offset,
                        'text': text,
                        'length': len(current_text)
                    })
                in_text = False
                current_text = b''

        print(f"✓ Found {len(mission_blocks)} mission text blocks")

        # Separate Allied and Axis
        allied_lines = [block['text'] for i, block in enumerate(mission_blocks) if i % 2 == 0]
        axis_lines = [block['text'] for i, block in enumerate(mission_blocks) if i % 2 == 1]

        print(f"\n--- Allied Briefing ({len(allied_lines)} lines) ---")
        for i, line in enumerate(allied_lines[:3], 1):  # Show first 3
            print(f"{i}. {line[:70]}{'...' if len(line) > 70 else ''}")

        print(f"\n--- Axis Briefing ({len(axis_lines)} lines) ---")
        for i, line in enumerate(axis_lines[:3], 1):  # Show first 3
            print(f"{i}. {line[:70]}{'...' if len(line) > 70 else ''}")

        return True

    except Exception as e:
        print(f"❌ FAILED: {e}")
        return False


def test_unit_extraction(scenario_file):
    """Test unit roster extraction"""
    print(f"\n{'='*80}")
    print(f"Unit Roster Extraction: {scenario_file.name}")
    print(f"{'='*80}")

    try:
        scenario = DdayScenario(scenario_file)

        if 'PTR3' not in scenario.sections:
            print("⚠ No PTR3 section found")
            return False

        ptr3_data = scenario.sections['PTR3']
        print(f"✓ PTR3 section size: {len(ptr3_data)} bytes")

        # Parse units (simple extraction)
        units = []
        i = 0

        while i < len(ptr3_data):
            if i + 20 < len(ptr3_data):
                chunk = ptr3_data[i:i+32]

                # Find ASCII strings (unit names)
                name = b''
                for b in chunk[8:24]:
                    if 32 <= b < 127:
                        name += bytes([b])
                    elif name:
                        break

                if len(name) >= 3:
                    unit_name = name.decode('ascii', errors='ignore').strip()
                    units.append(unit_name)
                    i += 32
                else:
                    i += 1
            else:
                break

        print(f"✓ Found {len(units)} potential units")
        print(f"\nUnits:")
        for i, unit in enumerate(units[:10], 1):  # Show first 10
            print(f"  {i}. {unit}")

        if len(units) > 10:
            print(f"  ... and {len(units) - 10} more")

        return True

    except Exception as e:
        print(f"❌ FAILED: {e}")
        return False


def test_coordinate_data(scenario_file):
    """Test coordinate data extraction"""
    print(f"\n{'='*80}")
    print(f"Coordinate Data: {scenario_file.name}")
    print(f"{'='*80}")

    try:
        scenario = DdayScenario(scenario_file)

        if 'PTR5' not in scenario.sections:
            print("⚠ No PTR5 section found")
            return False

        ptr5_data = scenario.sections['PTR5']
        print(f"✓ PTR5 section size: {len(ptr5_data)} bytes")

        # Parse as 16-bit integers
        values = []
        for i in range(0, min(len(ptr5_data), 64), 2):
            if i + 2 <= len(ptr5_data):
                import struct
                value = struct.unpack('<H', ptr5_data[i:i+2])[0]
                values.append(value)

        print(f"✓ Extracted {len(values)} 16-bit values")
        print(f"\nFirst 10 values (decimal):")
        print(f"  {values[:10]}")
        print(f"\nFirst 10 values (hex):")
        print(f"  {[f'0x{v:04x}' for v in values[:10]]}")

        return True

    except Exception as e:
        print(f"❌ FAILED: {e}")
        return False


def test_string_search(scenario_file, query):
    """Test string searching"""
    print(f"\n{'='*80}")
    print(f"String Search: '{query}' in {scenario_file.name}")
    print(f"{'='*80}")

    try:
        scenario = DdayScenario(scenario_file)

        results = []
        query_lower = query.lower()

        # Search all sections
        for section_name, section_data in scenario.sections.items():
            i = 0
            while i < len(section_data):
                text_start = i
                text = b''

                while i < len(section_data) and 32 <= section_data[i] < 127:
                    text += bytes([section_data[i]])
                    i += 1

                if len(text) >= len(query):
                    text_str = text.decode('ascii', errors='ignore')
                    if query_lower in text_str.lower():
                        results.append((section_name, text_start, text_str))

                i += 1

        print(f"✓ Found {len(results)} matches")

        for section, offset, text in results[:5]:  # Show first 5
            preview = text[:60] + ('...' if len(text) > 60 else '')
            print(f"  {section} @ 0x{offset:06x}: {preview}")

        if len(results) > 5:
            print(f"  ... and {len(results) - 5} more matches")

        return True

    except Exception as e:
        print(f"❌ FAILED: {e}")
        return False


def main():
    """Run all tests"""
    print("""
╔═══════════════════════════════════════════════════════════════════════════╗
║                D-Day Scenario Creator/Editor - Test Suite                 ║
╚═══════════════════════════════════════════════════════════════════════════╝
    """)

    # Find scenario files
    scenario_dir = Path("game/SCENARIO")

    if not scenario_dir.exists():
        print(f"❌ Scenario directory not found: {scenario_dir}")
        return 1

    scenario_files = list(scenario_dir.glob("*.SCN"))

    if not scenario_files:
        print(f"❌ No scenario files found in {scenario_dir}")
        return 1

    print(f"Found {len(scenario_files)} scenario files")

    # Test with OMAHA.SCN as primary test case
    test_file = scenario_dir / "OMAHA.SCN"

    if not test_file.exists():
        test_file = scenario_files[0]

    print(f"\nPrimary test file: {test_file.name}")

    results = []

    # Run tests
    results.append(("Loading", test_scenario_loading(test_file)))
    results.append(("Mission Text", test_mission_text_extraction(test_file)))
    results.append(("Units", test_unit_extraction(test_file)))
    results.append(("Coordinates", test_coordinate_data(test_file)))
    results.append(("Search", test_string_search(test_file, "Corps")))

    # Test all scenarios for loading
    print(f"\n{'='*80}")
    print(f"Testing All Scenarios")
    print(f"{'='*80}")

    all_valid = True
    for scn_file in scenario_files:
        try:
            scenario = DdayScenario(scn_file)
            status = "✓" if scenario.is_valid and scenario.validate() else "⚠"
            print(f"{status} {scn_file.name:20s} - {len(scenario.data):,} bytes")
            if not (scenario.is_valid and scenario.validate()):
                all_valid = False
        except Exception as e:
            print(f"❌ {scn_file.name:20s} - ERROR: {e}")
            all_valid = False

    # Summary
    print(f"\n{'='*80}")
    print(f"Test Summary")
    print(f"{'='*80}")

    passed = sum(1 for _, result in results if result)
    total = len(results)

    print(f"\nComponent Tests: {passed}/{total} passed")
    for test_name, result in results:
        status = "✓ PASS" if result else "❌ FAIL"
        print(f"  {status}: {test_name}")

    print(f"\nScenario Loading: {'✓ ALL VALID' if all_valid else '⚠ SOME WARNINGS'}")
    print(f"  {len(scenario_files)} scenarios tested")

    if passed == total and all_valid:
        print(f"\n🎉 All tests passed! The editor is ready to use.")
        print(f"\nTo launch the GUI editor:")
        print(f"  python3 dday_scenario_creator.py game/SCENARIO/OMAHA.SCN")
        return 0
    else:
        print(f"\n⚠ Some tests failed. Check output above.")
        return 1


if __name__ == '__main__':
    sys.exit(main())
