#!/usr/bin/env python3
"""
Round-trip test for D-Day scenario parser
Tests: Read -> Write -> Binary compare
"""

from dday_scenario_parser import DdayScenario
from pathlib import Path
import filecmp
import os
import hashlib

def compute_hash(filename):
    """Compute SHA256 hash of file"""
    sha256 = hashlib.sha256()
    with open(filename, 'rb') as f:
        while chunk := f.read(8192):
            sha256.update(chunk)
    return sha256.hexdigest()

def test_roundtrip(scenario_file):
    """Test read -> write -> verify for a scenario"""
    print(f"\nTesting: {scenario_file.name}")
    print("-" * 60)

    # Read original
    scenario = DdayScenario(scenario_file)
    if not scenario.is_valid:
        print(f"  ✗ FAIL: Could not parse {scenario_file.name}")
        return False

    original_size = len(scenario.data)
    original_hash = compute_hash(scenario_file)
    print(f"  Original: {original_size:,} bytes, hash: {original_hash[:16]}...")

    # Write to temp file
    temp_file = scenario_file.parent / f"{scenario_file.stem}_TEST.SCN"
    try:
        scenario.write(temp_file)
    except Exception as e:
        print(f"  ✗ FAIL: Write failed - {e}")
        return False

    # Verify written file
    if not temp_file.exists():
        print(f"  ✗ FAIL: Output file not created")
        return False

    written_size = temp_file.stat().st_size
    written_hash = compute_hash(temp_file)
    print(f"  Written:  {written_size:,} bytes, hash: {written_hash[:16]}...")

    # Binary comparison
    if original_hash == written_hash:
        print(f"  ✓ PASS: Files are binary identical!")
        temp_file.unlink()
        return True
    else:
        print(f"  ✗ FAIL: Files differ!")

        # Show size difference
        if original_size != written_size:
            diff = written_size - original_size
            print(f"    Size difference: {diff:+,} bytes")

        # Keep the temp file for inspection
        print(f"    Temp file saved for inspection: {temp_file}")
        return False

def main():
    """Run round-trip tests on all scenarios"""
    scenario_dir = Path('game/dday/game/SCENARIO')
    scenarios = sorted(scenario_dir.glob('*.SCN'))

    print("=" * 80)
    print("D-DAY SCENARIO ROUND-TRIP TEST")
    print("=" * 80)
    print(f"Testing {len(scenarios)} scenario files")
    print("Goal: Read -> Write -> Verify binary identical")

    results = []
    for scn_file in scenarios:
        passed = test_roundtrip(scn_file)
        results.append((scn_file.name, passed))

    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)

    passed_count = sum(1 for _, passed in results if passed)
    total_count = len(results)

    for name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"  {status}: {name}")

    print()
    print(f"Results: {passed_count}/{total_count} scenarios passed")

    if passed_count == total_count:
        print("\n🎉 ALL TESTS PASSED! Round-trip is working correctly.")
        return 0
    else:
        print(f"\n⚠️  {total_count - passed_count} test(s) failed. Check output above.")
        return 1

if __name__ == '__main__':
    exit(main())
