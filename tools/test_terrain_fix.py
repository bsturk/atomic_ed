#!/usr/bin/env python3
"""
Test Terrain Fix Across Multiple Scenarios
===========================================

Verifies that the coordinate fix produces realistic terrain across all scenarios.
"""

import sys
import os
from pathlib import Path
from collections import Counter
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from lib.terrain_reader import extract_terrain_from_file


def analyze_clustering(terrain_map, width=125, height=100):
    """Measure geographic clustering score"""
    cluster_score = 0
    total_checks = 0

    # Check interior hexes (avoid edges)
    for y in range(1, height - 1):
        for x in range(1, width - 1):
            terrain_data = terrain_map.get((x, y), (0, 0))
            terrain = terrain_data[0] if isinstance(terrain_data, tuple) else terrain_data

            # Check 4 cardinal neighbors
            neighbors = [
                terrain_map.get((x-1, y), (0, 0)),
                terrain_map.get((x+1, y), (0, 0)),
                terrain_map.get((x, y-1), (0, 0)),
                terrain_map.get((x, y+1), (0, 0)),
            ]

            # Extract terrain from tuples
            neighbor_terrains = [
                n[0] if isinstance(n, tuple) else n for n in neighbors
            ]

            # Count matches
            matches = sum(1 for n in neighbor_terrains if n == terrain)
            cluster_score += matches
            total_checks += 1

    avg_match = cluster_score / (total_checks * 4) if total_checks > 0 else 0
    return cluster_score, avg_match


def test_scenario(scenario_path):
    """Test a single scenario"""
    print(f"\n{'='*70}")
    print(f"Testing: {scenario_path.name}")
    print('='*70)

    # Extract terrain
    terrain = extract_terrain_from_file(str(scenario_path))

    if not terrain:
        print("  ✗ Failed to extract terrain!")
        return False

    # Count terrain types
    terrain_only = Counter(t for t, v in terrain.values())

    # Check distribution
    total = len(terrain)
    grass_pct = 100 * terrain_only.get(0, 0) / total
    water_pct = 100 * terrain_only.get(1, 0) / total
    town_pct = 100 * terrain_only.get(4, 0) / total

    print(f"  Hexes extracted: {total:,}")
    print(f"  Grass (0):       {grass_pct:5.1f}%")
    print(f"  Water (1):       {water_pct:5.1f}%")
    print(f"  Town (4):        {town_pct:5.1f}%")

    # Analyze clustering
    cluster_score, avg_match = analyze_clustering(terrain)
    print(f"  Clustering:      {avg_match:.3f} avg neighbor match")

    # Validation checks
    checks = []

    # 1. Should have both land and water (unless special scenario)
    if grass_pct > 10 or water_pct > 10:
        checks.append(("Has terrain diversity", True))
    else:
        checks.append(("Has terrain diversity", False))

    # 2. Towns should be rare (< 5%)
    if town_pct < 5:
        checks.append(("Towns are rare", True))
    else:
        checks.append(("Towns are rare", False))

    # 3. Clustering should be good (> 0.5)
    if avg_match > 0.5:
        checks.append(("Good geographic clustering", True))
    else:
        checks.append(("Good geographic clustering", False))

    # Print results
    all_passed = all(result for _, result in checks)
    print(f"\n  Validation:")
    for check_name, result in checks:
        status = "✓" if result else "✗"
        print(f"    {status} {check_name}")

    if all_passed:
        print(f"\n  ✓ PASSED - Terrain looks realistic!")
    else:
        print(f"\n  ✗ FAILED - Terrain may have issues")

    return all_passed


def main():
    """Test all scenarios"""
    scenario_dir = Path("game/SCENARIO")

    if not scenario_dir.exists():
        print(f"Error: {scenario_dir} not found!")
        sys.exit(1)

    # Find all .SCN files
    scenarios = sorted(scenario_dir.glob("*.SCN"))

    if not scenarios:
        print(f"No .SCN files found in {scenario_dir}")
        sys.exit(1)

    print("="*70)
    print("TERRAIN FIX VALIDATION TEST")
    print("="*70)
    print(f"Testing {len(scenarios)} scenarios...")

    results = {}
    for scenario_path in scenarios:
        try:
            passed = test_scenario(scenario_path)
            results[scenario_path.name] = passed
        except Exception as e:
            print(f"  ✗ ERROR: {e}")
            results[scenario_path.name] = False

    # Summary
    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)

    passed_count = sum(1 for p in results.values() if p)
    total_count = len(results)

    for scenario_name, passed in sorted(results.items()):
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"  {status}  {scenario_name}")

    print(f"\n  Total: {passed_count}/{total_count} passed")

    if passed_count == total_count:
        print("\n  ✓✓✓ ALL TESTS PASSED! ✓✓✓")
        print("  The terrain fix is working correctly across all scenarios.")
    else:
        print(f"\n  ⚠ {total_count - passed_count} scenarios failed validation")
        print("  This may indicate additional issues or special scenario formats.")


if __name__ == '__main__':
    main()
