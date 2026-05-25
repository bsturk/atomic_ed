#!/usr/bin/env python3
"""
Reinforcement Parser for D-Day Scenario Editor
===============================================

Parses reinforcement schedule data from PTR6 section of scenario files.

Reinforcement Entry Record (20 bytes = 10 words):
    [ptr_lo][ptr_hi][wave_id][script][x][y][x2][y2][0xFFFF][0xFFFF]
    - words[2] = wave_id
    - words[3] = script_id
    - words[4] = entry hex X coordinate
    - words[5] = entry hex Y coordinate
    - words[8:10] = terminator (0xFFFF, 0xFFFF)

Wave-Turn Schedule:
    Consecutive (turn, wave_id) word pairs in PTR6.
    Location varies by scenario (BRADLEY at PTR6 + 0x180).
"""

import struct
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from collections import defaultdict


@dataclass
class ReinforcementEntry:
    """Represents a reinforcement entry record from PTR6"""
    offset: int              # Absolute file offset of this record
    ptr6_offset: int         # Offset within PTR6 section
    wave_id: int             # Wave identifier
    script_id: int           # AI script assignment
    entry_x: int             # Entry hex X coordinate
    entry_y: int             # Entry hex Y coordinate
    entry_x2: int = 0        # Secondary X (alternate entry?)
    entry_y2: int = 0        # Secondary Y (alternate entry?)
    unit_indices: List[int] = field(default_factory=list)  # Units in this wave

    @property
    def entry_hex(self) -> Tuple[int, int]:
        """Entry coordinates as (x, y) tuple"""
        return (self.entry_x, self.entry_y)

    def to_bytes(self) -> bytes:
        """Serialize entry back to 20-byte record"""
        return struct.pack('<10H',
            0,                  # ptr_lo (placeholder)
            0,                  # ptr_hi (placeholder)
            self.wave_id,
            self.script_id,
            self.entry_x,
            self.entry_y,
            self.entry_x2,
            self.entry_y2,
            0xFFFF,             # terminator
            0xFFFF              # terminator
        )


@dataclass
class WaveTurnPair:
    """A (turn, wave_id) pair from the schedule"""
    offset: int       # File offset of this pair
    turn: int         # Turn number when wave enters
    wave_id: int      # Wave identifier

    def to_bytes(self) -> bytes:
        """Serialize pair back to 4 bytes"""
        return struct.pack('<HH', self.turn, self.wave_id)


@dataclass
class ReinforcementSchedule:
    """Complete reinforcement schedule for a scenario"""
    entries: Dict[int, ReinforcementEntry] = field(default_factory=dict)  # wave_id -> entry
    schedule: Dict[int, WaveTurnPair] = field(default_factory=dict)  # wave_id -> turn pair
    turn_count: int = 0
    ptr6_offset: int = 0  # Absolute file offset of PTR6 section

    def get_wave_ids(self) -> List[int]:
        """Get all wave IDs that have entry records"""
        return sorted(self.entries.keys())

    def get_entry(self, wave_id: int) -> Optional[ReinforcementEntry]:
        """Get entry record for a wave"""
        return self.entries.get(wave_id)

    def get_turn(self, wave_id: int) -> Optional[int]:
        """Get entry turn for a wave"""
        pair = self.schedule.get(wave_id)
        return pair.turn if pair else None

    def get_wave_summary(self, wave_id: int) -> Dict:
        """Get summary info for a wave"""
        entry = self.entries.get(wave_id)
        pair = self.schedule.get(wave_id)

        return {
            'wave_id': wave_id,
            'entry_turn': pair.turn if pair else None,
            'entry_x': entry.entry_x if entry else None,
            'entry_y': entry.entry_y if entry else None,
            'script_id': entry.script_id if entry else None,
            'unit_count': len(entry.unit_indices) if entry else 0,
            'entry_offset': entry.offset if entry else None,
            'turn_offset': pair.offset if pair else None,
        }

    def get_all_waves(self) -> List[Dict]:
        """Get summary for all waves, sorted by entry turn"""
        waves = []
        all_ids = set(self.entries.keys()) | set(self.schedule.keys())

        for wave_id in all_ids:
            waves.append(self.get_wave_summary(wave_id))

        # Sort by entry turn (None values last)
        waves.sort(key=lambda w: (w['entry_turn'] is None, w['entry_turn'] or 0))
        return waves


def find_turn_count(data: bytes) -> Optional[int]:
    """
    Search for turn count in scenario file.

    Based on TURN_COUNT_FORMAT.md - the turn count is at offset +6 in a
    parameter array where the first 3 words are < 1000.
    """
    common_bases = [0x0246, 0x02EA, 0x1462, 0x1F7A, 0x1976, 0x2220]

    def is_candidate(base: int) -> Optional[int]:
        if base + 8 > len(data):
            return None
        turn = struct.unpack_from("<H", data, base + 6)[0]
        if not (1 <= turn <= 255):
            return None
        w0 = struct.unpack_from("<H", data, base)[0]
        w1 = struct.unpack_from("<H", data, base + 2)[0]
        w2 = struct.unpack_from("<H", data, base + 4)[0]
        if all(0 <= w <= 1000 for w in (w0, w1, w2)):
            return turn
        return None

    # Try common offsets first
    for base in common_bases:
        if base + 8 < len(data):
            t = is_candidate(base)
            if t:
                return t

    # Search before PTR5
    if len(data) >= 0x54:
        ptr5 = struct.unpack_from("<I", data, 0x50)[0]
        ptr6 = struct.unpack_from("<I", data, 0x54)[0]
        first = min(ptr5 or len(data), ptr6 or len(data))
        for base in range(0x60, max(0x60, first - 8), 2):
            if base + 8 >= len(data):
                break
            t = is_candidate(base)
            if t:
                return t

    return None


def parse_reinforcement_entries(ptr6_data: bytes, ptr6_file_offset: int = 0) -> List[ReinforcementEntry]:
    """
    Parse 10-word reinforcement entry records from PTR6.

    Looks for records ending with 0xFFFF, 0xFFFF terminator.

    Args:
        ptr6_data: Raw bytes of PTR6 section
        ptr6_file_offset: Absolute file offset where PTR6 starts

    Returns:
        List of ReinforcementEntry objects
    """
    entries = []

    # Scan for 10-word blocks ending in 0xFFFF, 0xFFFF
    for i in range(0, len(ptr6_data) - 20, 2):
        block = ptr6_data[i:i + 20]
        if len(block) < 20:
            continue

        words = struct.unpack("<10H", block)

        # Check for terminator pattern
        if words[8] != 0xFFFF or words[9] != 0xFFFF:
            continue

        # Valid entry found
        entry = ReinforcementEntry(
            offset=ptr6_file_offset + i,
            ptr6_offset=i,
            wave_id=words[2],
            script_id=words[3],
            entry_x=words[4],
            entry_y=words[5],
            entry_x2=words[6],
            entry_y2=words[7],
        )
        entries.append(entry)

    return entries


def parse_wave_turn_schedule(ptr6_data: bytes, turn_limit: int,
                            ptr6_file_offset: int = 0,
                            valid_waves: Optional[set] = None) -> List[WaveTurnPair]:
    """
    Parse (turn, wave_id) pairs from PTR6.

    Scans for word pairs where:
    - turn <= turn_limit (scenario turn count)
    - wave_id matches a known wave (if valid_waves provided)

    Args:
        ptr6_data: Raw bytes of PTR6 section
        turn_limit: Maximum valid turn number
        ptr6_file_offset: Absolute file offset where PTR6 starts
        valid_waves: Set of valid wave IDs (from entry records)

    Returns:
        List of WaveTurnPair objects
    """
    if turn_limit <= 0:
        return []

    pairs = []
    seen_waves = set()  # Track which waves we've found

    # Parse all words
    words = []
    for i in range(0, len(ptr6_data) - 1, 2):
        words.append(struct.unpack_from("<H", ptr6_data, i)[0])

    # Scan for (turn, wave_id) pairs
    for i in range(len(words) - 1):
        turn = words[i]
        wave_id = words[i + 1]

        # Turn must be within valid range
        if not (1 <= turn <= turn_limit):
            continue

        # If we have valid waves, wave_id must be in the set
        if valid_waves is not None and wave_id not in valid_waves:
            continue

        # Skip if we already have this wave (take first occurrence)
        if wave_id in seen_waves:
            continue

        seen_waves.add(wave_id)
        pairs.append(WaveTurnPair(
            offset=ptr6_file_offset + i * 2,
            turn=turn,
            wave_id=wave_id
        ))

    return pairs


def parse_reinforcements(scenario) -> ReinforcementSchedule:
    """
    Parse complete reinforcement data from a scenario.

    Args:
        scenario: DdayScenario object

    Returns:
        ReinforcementSchedule with entries and timing
    """
    schedule = ReinforcementSchedule()

    if not scenario.is_valid:
        return schedule

    # Get turn count
    schedule.turn_count = find_turn_count(scenario.data) or 0

    # Get PTR6 data and offset
    ptr6_data = scenario.sections.get('PTR6', b'')
    if not ptr6_data:
        return schedule

    # Find PTR6 file offset
    ptr6_offset = scenario.pointers.get('PTR6', 0)
    schedule.ptr6_offset = ptr6_offset

    # Parse entry records
    entries = parse_reinforcement_entries(ptr6_data, ptr6_offset)
    for entry in entries:
        schedule.entries[entry.wave_id] = entry

    # Get valid wave IDs for schedule parsing
    valid_waves = set(schedule.entries.keys())

    # Parse wave-turn schedule
    pairs = parse_wave_turn_schedule(
        ptr6_data,
        schedule.turn_count,
        ptr6_offset,
        valid_waves
    )
    for pair in pairs:
        schedule.schedule[pair.wave_id] = pair

    return schedule


def link_units_to_waves(units: List[dict], schedule: ReinforcementSchedule):
    """
    Link off-map units to their reinforcement waves.

    Units with x=-1 or y=-1 are considered off-map/reinforcements.
    This modifies the schedule.entries in place to add unit indices.

    Args:
        units: List of unit dicts from EnhancedUnitParser
        schedule: ReinforcementSchedule to update
    """
    for unit in units:
        x = unit.get('x', 0)
        y = unit.get('y', 0)

        # Check if unit is off-map
        if x != -1 and y != -1:
            continue

        # Try to determine wave_id from unit data
        # This may need refinement based on actual unit record structure
        wave_id = unit.get('wave_id', 0)

        if wave_id and wave_id in schedule.entries:
            schedule.entries[wave_id].unit_indices.append(unit.get('index', 0))


def get_reinforcement_display_data(scenario, units: List[dict]) -> List[Dict]:
    """
    Get reinforcement data formatted for UI display.

    Args:
        scenario: DdayScenario object
        units: List of unit dicts

    Returns:
        List of dicts with display-ready wave information
    """
    schedule = parse_reinforcements(scenario)
    link_units_to_waves(units, schedule)

    display_data = []
    for wave_summary in schedule.get_all_waves():
        # Get unit names for this wave
        wave_units = []
        entry = schedule.entries.get(wave_summary['wave_id'])
        if entry:
            for unit_idx in entry.unit_indices:
                for unit in units:
                    if unit.get('index') == unit_idx:
                        wave_units.append(unit.get('name', f'Unit {unit_idx}'))
                        break

        display_data.append({
            **wave_summary,
            'unit_names': wave_units,
            'display_turn': wave_summary['entry_turn'] or '?',
            'display_hex': f"({wave_summary['entry_x']}, {wave_summary['entry_y']})"
                          if wave_summary['entry_x'] is not None else '?',
        })

    return display_data


# Convenience function for creating new reinforcement entries
def create_reinforcement_entry(wave_id: int, entry_x: int, entry_y: int,
                               script_id: int = 0) -> bytes:
    """
    Create a new 20-byte reinforcement entry record.

    Args:
        wave_id: Wave identifier
        entry_x: Entry hex X coordinate
        entry_y: Entry hex Y coordinate
        script_id: AI script ID (default 0)

    Returns:
        20-byte record ready to insert into PTR6
    """
    return struct.pack('<10H',
        0,              # ptr_lo
        0,              # ptr_hi
        wave_id,
        script_id,
        entry_x,
        entry_y,
        entry_x,        # x2 = x
        entry_y,        # y2 = y
        0xFFFF,         # terminator
        0xFFFF          # terminator
    )


def create_wave_turn_pair(turn: int, wave_id: int) -> bytes:
    """
    Create a 4-byte wave-turn pair.

    Args:
        turn: Turn number
        wave_id: Wave identifier

    Returns:
        4-byte pair ready to insert into schedule
    """
    return struct.pack('<HH', turn, wave_id)


if __name__ == '__main__':
    # Test the parser
    import sys
    sys.path.insert(0, str(__file__).rsplit('/', 1)[0])
    from scenario_parser import DdayScenario

    from pathlib import Path

    scenarios = sorted(Path("game/SCENARIO").glob("*.SCN"))
    for scn_path in scenarios:
        scenario = DdayScenario(str(scn_path))
        schedule = parse_reinforcements(scenario)

        print(f"\n{scn_path.name}: turns={schedule.turn_count}")
        print(f"  Entry records: {len(schedule.entries)}")
        print(f"  Scheduled waves: {len(schedule.schedule)}")

        # Show first few waves
        for wave in schedule.get_all_waves()[:5]:
            print(f"  Wave {wave['wave_id']}: turn {wave['entry_turn']} "
                  f"entry ({wave['entry_x']}, {wave['entry_y']})")
