#!/usr/bin/env python3
"""Quick test of all D-Day scenario files"""

from dday_scenario_parser import DdayScenario
from pathlib import Path

scenario_dir = Path('game/dday/game/SCENARIO')
scenarios = sorted(scenario_dir.glob('*.SCN'))

print("Testing all D-Day scenario files")
print("=" * 80)

results = []
for scn_file in scenarios:
    scenario = DdayScenario(scn_file)
    is_valid = scenario.is_valid
    file_size = len(scenario.data) if scenario.data else 0
    magic_ok = scenario.pointers.get('magic', 0) if scenario.is_valid else False

    results.append({
        'name': scn_file.name,
        'valid': is_valid,
        'size': file_size
    })

    status = "✓" if is_valid else "✗"
    print(f"{status} {scn_file.name:15s} {file_size:>8,} bytes")

print("\n" + "=" * 80)
passed = sum(1 for r in results if r['valid'])
print(f"Results: {passed}/{len(results)} scenarios parsed successfully")
print("=" * 80)
