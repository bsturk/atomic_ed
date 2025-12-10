#!/usr/bin/env python3
"""
Parse PTR6 reinforcement schedule and entry hexes for D-Day scenarios.

What this script does:
  - Reads turn count using the same search logic described in txt/TURN_COUNT_FORMAT.md
  - Extracts reinforcement entry records from PTR6 (10-word blocks ending in 0xFFFF 0xFFFF)
  - Extracts a wave->turn schedule from the first 0x200-byte PTR6 record that is a list of word pairs
    (turn, wave_id). This matches what BRADLEY/COUNTER expose and aligns with disasm sub_6FB0 handling.
  - Outputs, per scenario:
      * turn count
      * wave -> earliest scheduled turn (from the pair list)
      * wave -> entry hex (x, y) from the 10-word records

This is read-only and does not modify scenario files.
"""

import glob
import struct
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from lib.scenario_parser import DdayScenario


def find_turn_count(data: bytes) -> int | None:
    """Search for turn count per TURN_COUNT_FORMAT.md."""
    common_bases = [0x0246, 0x02EA, 0x1462, 0x1F7A, 0x1976, 0x2220]

    def is_candidate(base: int) -> int | None:
        turn = struct.unpack_from("<H", data, base + 6)[0]
        if not (1 <= turn <= 255):
            return None
        w0 = struct.unpack_from("<H", data, base)[0]
        w1 = struct.unpack_from("<H", data, base + 2)[0]
        w2 = struct.unpack_from("<H", data, base + 4)[0]
        if all(0 <= w <= 1000 for w in (w0, w1, w2)):
            return turn
        return None

    for base in common_bases:
        if base + 8 < len(data):
            t = is_candidate(base)
            if t:
                return t

    # Search before PTR5
    ptr5 = struct.unpack_from("<I", data, 0x50)[0]
    ptr6 = struct.unpack_from("<I", data, 0x54)[0]
    first = min(ptr5 or len(data), ptr6 or len(data))
    for base in range(0x60, max(0x60, first - 8), 2):
        if base + 8 >= len(data):
            break
        t = is_candidate(base)
        if t:
            return t

    # Search PTR5 section if needed
    if ptr5 and ptr6 and ptr5 < ptr6:
        ptr5_data = data[ptr5:ptr6]
        for i in range(0, len(ptr5_data) - 24, 2):
            turn = struct.unpack_from("<H", ptr5_data, i + 6)[0]
            if not (1 <= turn <= 255):
                continue
            w0, w1, w2 = struct.unpack_from("<3H", ptr5_data, i)
            if all(0 <= w <= 1000 for w in (w0, w1, w2)):
                return turn

    return None


def parse_reinforcement_entries(ptr6: bytes):
    """Return dict wave_id -> list of entries with x,y,script."""
    entries = defaultdict(list)
    for i in range(0, len(ptr6) - 20, 2):
        block = ptr6[i : i + 20]
        if len(block) < 20:
            continue
        words = struct.unpack("<10H", block)
        if words[8] != 0xFFFF or words[9] != 0xFFFF:
            continue
        wave_id = words[2]
        script_id = words[3]
        x = words[4]
        y = words[5]
        entries[wave_id].append({"x": x, "y": y, "script": script_id, "offset": i})
    return entries


def parse_wave_turn_pairs(ptr6: bytes, turn_limit: int):
    """
    The first length-prefixed record of size 0x200 (512) in BRADLEY is a 256-word array,
    interpreted as (turn, wave) pairs. We scan all word pairs in PTR6 and accept pairs
    where turn <= turn_limit.
    """
    words = [struct.unpack_from("<H", ptr6, i)[0] for i in range(0, len(ptr6) - 1, 2)]
    pairs = defaultdict(list)
    for i in range(0, len(words) - 1):
        turn, wave = words[i], words[i + 1]
        if 1 <= turn <= turn_limit:
            pairs[wave].append(turn)
    # Reduce to earliest turn per wave
    earliest = {wave: min(ts) for wave, ts in pairs.items()}
    return earliest


def analyze_scenario(path: Path):
    s = DdayScenario(str(path))
    tc = find_turn_count(s.data)
    ptr6 = s.sections.get("PTR6", b"")
    reinf_entries = parse_reinforcement_entries(ptr6)
    wave_turns = parse_wave_turn_pairs(ptr6, tc or 0)

    report = {
        "scenario": path.name,
        "turn_count": tc,
        "waves_with_turns": len(wave_turns),
        "waves_with_entries": len(reinf_entries),
        "entries": reinf_entries,
        "turns": wave_turns,
    }
    return report


def main():
    scenarios = sorted(Path("game/SCENARIO").glob("*.SCN"))
    for scn in scenarios:
        rpt = analyze_scenario(scn)
        print(f"{rpt['scenario']}: turns={rpt['turn_count']} "
              f"waves(turns)={rpt['waves_with_turns']} waves(entries)={rpt['waves_with_entries']}")
        # Show first few waves with both turn and entry
        shown = 0
        for wave in sorted(rpt["turns"].keys()):
            turn = rpt["turns"][wave]
            entry = rpt["entries"].get(wave, [])
            if entry:
                xy = (entry[0]['x'], entry[0]['y'])
            else:
                xy = None
            print(f"  wave {wave}: turn {turn} entry {xy}")
            shown += 1
            if shown >= 6:
                break
        print()


if __name__ == "__main__":
    main()
