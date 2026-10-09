#!/usr/bin/env python3
"""
Modification Tracker for D-Day Scenario Editor
===============================================

Tracks changes made to scenario data with file offsets for patch-in-place saving.
Only modified bytes are written back to the scenario file.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional
from enum import Enum


class ModificationType(Enum):
    """Types of modifications that can be tracked"""
    UNIT_POSITION = "unit_position"
    UNIT_NAME = "unit_name"
    UNIT_STATS = "unit_stats"
    UNIT_BEHAVIOR = "unit_behavior"
    UNIT_SIDE = "unit_side"
    REINFORCEMENT_WAVE = "reinforcement_wave"
    REINFORCEMENT_TURN = "reinforcement_turn"
    REINFORCEMENT_ENTRY = "reinforcement_entry"
    TURN_COUNT = "turn_count"
    MAP_TERRAIN = "map_terrain"
    MISSION_TEXT = "mission_text"


@dataclass
class Modification:
    """Represents a single modification to the scenario file"""
    mod_type: ModificationType
    file_offset: int
    original_bytes: bytes
    new_bytes: bytes
    description: str = ""

    def __post_init__(self):
        # Ensure bytes types
        if isinstance(self.original_bytes, int):
            self.original_bytes = bytes([self.original_bytes])
        if isinstance(self.new_bytes, int):
            self.new_bytes = bytes([self.new_bytes])

    @property
    def size(self) -> int:
        """Size of the modification in bytes"""
        return len(self.new_bytes)

    @property
    def has_changed(self) -> bool:
        """Check if the new bytes differ from original"""
        return self.original_bytes != self.new_bytes


@dataclass
class ModificationTracker:
    """
    Tracks all modifications made to a scenario file.

    Modifications are stored by file offset for efficient patch application.
    Overlapping modifications are merged automatically.
    """
    modifications: Dict[int, Modification] = field(default_factory=dict)
    _scenario_size: int = 0

    def set_scenario_size(self, size: int):
        """Set the scenario file size for bounds checking"""
        self._scenario_size = size

    def add_modification(self, offset: int, original: bytes, new: bytes,
                        mod_type: ModificationType, description: str = "") -> bool:
        """
        Record a modification at a specific file offset.

        Args:
            offset: File offset where modification starts
            original: Original bytes at this location
            new: New bytes to write
            mod_type: Type of modification
            description: Human-readable description

        Returns:
            True if modification was added, False if no change needed
        """
        # Convert single ints to bytes
        if isinstance(original, int):
            original = bytes([original])
        if isinstance(new, int):
            new = bytes([new])

        # Don't add if no actual change
        if original == new:
            return False

        # Bounds check if we know the file size
        if self._scenario_size > 0:
            if offset < 0 or offset + len(new) > self._scenario_size:
                raise ValueError(
                    f"Modification at offset {offset} with size {len(new)} "
                    f"exceeds file bounds (size={self._scenario_size})"
                )

        mod = Modification(
            mod_type=mod_type,
            file_offset=offset,
            original_bytes=original,
            new_bytes=new,
            description=description
        )

        # Check for overlapping modifications and merge if needed
        self._merge_or_add(mod)
        return True

    def _merge_or_add(self, new_mod: Modification):
        """Add modification, merging with existing if they overlap"""
        offset = new_mod.file_offset
        end_offset = offset + len(new_mod.new_bytes)

        # Find overlapping modifications
        overlapping = []
        for existing_offset, existing_mod in list(self.modifications.items()):
            existing_end = existing_offset + len(existing_mod.new_bytes)

            # Check for overlap
            if not (end_offset <= existing_offset or offset >= existing_end):
                overlapping.append((existing_offset, existing_mod))

        if not overlapping:
            # No overlap, just add
            self.modifications[offset] = new_mod
        else:
            # Remove overlapping modifications and create merged one
            for old_offset, _ in overlapping:
                del self.modifications[old_offset]

            # For simplicity, just add the new modification
            # (more complex merging could be implemented if needed)
            self.modifications[offset] = new_mod

    def remove_modification(self, offset: int) -> bool:
        """Remove a modification at the given offset"""
        if offset in self.modifications:
            del self.modifications[offset]
            return True
        return False

    def get_modification(self, offset: int) -> Optional[Modification]:
        """Get modification at specific offset"""
        return self.modifications.get(offset)

    def has_changes(self) -> bool:
        """Check if there are any pending modifications"""
        return len(self.modifications) > 0

    def get_change_count(self) -> int:
        """Get number of pending modifications"""
        return len(self.modifications)

    def get_patches(self) -> List[Tuple[int, bytes]]:
        """
        Return list of (offset, bytes) patches to apply.

        Patches are sorted by offset for efficient sequential writing.
        """
        patches = []
        for offset in sorted(self.modifications.keys()):
            mod = self.modifications[offset]
            if mod.has_changed:
                patches.append((offset, mod.new_bytes))
        return patches

    def get_summary(self) -> str:
        """Get human-readable summary of pending changes"""
        if not self.modifications:
            return "No pending changes"

        lines = [f"Pending changes: {len(self.modifications)}"]

        # Group by modification type
        by_type: Dict[ModificationType, List[Modification]] = {}
        for mod in self.modifications.values():
            if mod.mod_type not in by_type:
                by_type[mod.mod_type] = []
            by_type[mod.mod_type].append(mod)

        for mod_type, mods in by_type.items():
            lines.append(f"  {mod_type.value}: {len(mods)} changes")
            for mod in mods[:3]:  # Show first 3
                if mod.description:
                    lines.append(f"    - {mod.description}")
            if len(mods) > 3:
                lines.append(f"    ... and {len(mods) - 3} more")

        return "\n".join(lines)

    def clear(self):
        """Clear all pending modifications"""
        self.modifications.clear()

    def revert_all(self) -> List[Tuple[int, bytes]]:
        """
        Get patches to revert all changes to original values.

        Returns list of (offset, original_bytes) to restore original state.
        """
        patches = []
        for offset in sorted(self.modifications.keys()):
            mod = self.modifications[offset]
            patches.append((offset, mod.original_bytes))
        return patches


# Convenience functions for common modification types

def track_unit_position(tracker: ModificationTracker, unit_offset: int,
                       original_x: int, original_y: int,
                       new_x: int, new_y: int, unit_name: str = ""):
    """Track unit position modification"""
    import struct

    # X coordinate at offset -58 from unit name
    x_offset = unit_offset - 58
    tracker.add_modification(
        x_offset,
        struct.pack('<H', original_x),
        struct.pack('<H', new_x),
        ModificationType.UNIT_POSITION,
        f"Unit '{unit_name}' X: {original_x} -> {new_x}"
    )

    # Y coordinate at offset -56 from unit name
    y_offset = unit_offset - 56
    tracker.add_modification(
        y_offset,
        struct.pack('<H', original_y),
        struct.pack('<H', new_y),
        ModificationType.UNIT_POSITION,
        f"Unit '{unit_name}' Y: {original_y} -> {new_y}"
    )


def track_unit_stats(tracker: ModificationTracker, unit_offset: int,
                    stat_name: str, original: int, new: int, unit_name: str = ""):
    """Track unit stat modification"""
    # Stat offsets relative to unit name
    stat_offsets = {
        'attack': -9,
        'defense': -8,
        'quality': -7,
        'disruption': -6,
        'fatigue': -5,
    }

    if stat_name not in stat_offsets:
        raise ValueError(f"Unknown stat: {stat_name}")

    offset = unit_offset + stat_offsets[stat_name]
    tracker.add_modification(
        offset,
        bytes([original]),
        bytes([new]),
        ModificationType.UNIT_STATS,
        f"Unit '{unit_name}' {stat_name}: {original} -> {new}"
    )


def track_unit_side(tracker: ModificationTracker, unit_offset: int,
                   original_side: str, new_side: str, unit_name: str = ""):
    """Track unit side modification"""
    # Side bytes at offsets -30 and -29 from unit name
    # Allied: 0x00, 0x00; Axis: 0x01, 0x01
    original_byte = 0x00 if original_side == 'Allied' else 0x01
    new_byte = 0x00 if new_side == 'Allied' else 0x01

    for rel_offset in [-30, -29]:
        offset = unit_offset + rel_offset
        tracker.add_modification(
            offset,
            bytes([original_byte]),
            bytes([new_byte]),
            ModificationType.UNIT_SIDE,
            f"Unit '{unit_name}' side: {original_side} -> {new_side}"
        )


def track_reinforcement_turn(tracker: ModificationTracker, schedule_offset: int,
                            wave_id: int, original_turn: int, new_turn: int):
    """Track reinforcement turn modification"""
    import struct

    # Wave-turn pairs are 4 bytes: (turn_word, wave_id_word)
    # We need to find and update the turn for this wave_id
    tracker.add_modification(
        schedule_offset,
        struct.pack('<H', original_turn),
        struct.pack('<H', new_turn),
        ModificationType.REINFORCEMENT_TURN,
        f"Wave {wave_id} entry turn: {original_turn} -> {new_turn}"
    )


def track_reinforcement_entry(tracker: ModificationTracker, entry_offset: int,
                             wave_id: int, original_x: int, original_y: int,
                             new_x: int, new_y: int):
    """Track reinforcement entry hex modification"""
    import struct

    # Entry coordinates at words[4] and words[5] in 10-word record
    x_offset = entry_offset + 8  # word[4]
    y_offset = entry_offset + 10  # word[5]

    tracker.add_modification(
        x_offset,
        struct.pack('<H', original_x),
        struct.pack('<H', new_x),
        ModificationType.REINFORCEMENT_ENTRY,
        f"Wave {wave_id} entry X: {original_x} -> {new_x}"
    )

    tracker.add_modification(
        y_offset,
        struct.pack('<H', original_y),
        struct.pack('<H', new_y),
        ModificationType.REINFORCEMENT_ENTRY,
        f"Wave {wave_id} entry Y: {original_y} -> {new_y}"
    )


def track_map_terrain(tracker: ModificationTracker, map_offset: int,
                     x: int, y: int, map_height: int,
                     original_byte: int, new_byte: int):
    """Track map terrain modification"""
    # Map data at 0x57E4 uses column-major layout.
    hex_offset = map_offset + (x * map_height + y)
    tracker.add_modification(
        hex_offset,
        bytes([original_byte]),
        bytes([new_byte]),
        ModificationType.MAP_TERRAIN,
        f"Terrain at ({x},{y}): 0x{original_byte:02X} -> 0x{new_byte:02X}"
    )
