#!/usr/bin/env python3
"""
D-Day Scenario Editor - Command Line Interface
A fully functional scenario editor without GUI dependencies
"""

from dday_scenario_parser import DdayScenario
from pathlib import Path
import shutil
import tempfile
import os
import subprocess

class ScenarioEditorCLI:
    """Command-line scenario editor"""

    def __init__(self):
        self.scenario = None
        self.scenario_file = None
        self.mission_blocks = []

    def load_scenario(self, filename):
        """Load a scenario file"""
        try:
            self.scenario = DdayScenario(filename)
            if not self.scenario.is_valid:
                print("❌ ERROR: Invalid scenario file format!")
                return False

            self.scenario_file = Path(filename)
            self._extract_mission_text()

            print(f"✓ Loaded: {self.scenario_file.name}")
            print(f"  File size: {len(self.scenario.data):,} bytes")
            print(f"  Mission text blocks: {len(self.mission_blocks)}")
            return True

        except Exception as e:
            print(f"❌ ERROR: Failed to load scenario: {e}")
            return False

    def _extract_mission_text(self):
        """Extract mission text blocks from scenario"""
        presection_start = 0x60
        first_section = min(start for _, start, _ in self.scenario.section_order)
        presection_data = self.scenario.data[presection_start:first_section]

        # Find all text blocks
        self.mission_blocks = []
        in_text = False
        start = 0
        current_text = b''

        for i, byte in enumerate(presection_data):
            if 32 <= byte <= 126:  # Printable ASCII
                if not in_text:
                    start = i
                    in_text = True
                current_text += bytes([byte])
            else:
                if in_text and len(current_text) >= 30:
                    abs_offset = presection_start + start
                    text = current_text.decode('ascii', errors='ignore').strip()
                    self.mission_blocks.append({
                        'offset': abs_offset,
                        'text': text,
                        'length': len(current_text)
                    })
                in_text = False
                current_text = b''

    def display_mission_text(self):
        """Display current mission text"""
        if not self.scenario:
            print("❌ No scenario loaded!")
            return

        allied_lines = [block['text'] for i, block in enumerate(self.mission_blocks) if i % 2 == 0]
        axis_lines = [block['text'] for i, block in enumerate(self.mission_blocks) if i % 2 == 1]

        print("\n" + "=" * 80)
        print(f"SCENARIO: {self.scenario_file.name}")
        print("=" * 80)

        print("\n📋 ALLIED BRIEFING:")
        print("-" * 80)
        for i, line in enumerate(allied_lines, 1):
            print(f"  [{i}] {line}")

        print("\n📋 AXIS BRIEFING:")
        print("-" * 80)
        for i, line in enumerate(axis_lines, 1):
            print(f"  [{i}] {line}")

        print("\n" + "=" * 80)

    def edit_mission_text_interactive(self):
        """Interactive mission text editing"""
        if not self.scenario:
            print("❌ No scenario loaded!")
            return

        while True:
            self.display_mission_text()

            print("\nEDIT OPTIONS:")
            print("  [a] Edit Allied briefing")
            print("  [x] Edit Axis briefing")
            print("  [s] Save and exit")
            print("  [q] Quit without saving")

            choice = input("\nChoice: ").strip().lower()

            if choice == 'a':
                self._edit_side_text('allied')
            elif choice == 'x':
                self._edit_side_text('axis')
            elif choice == 's':
                if self.save_scenario():
                    print("\n✓ Scenario saved successfully!")
                    break
            elif choice == 'q':
                if input("Quit without saving? (y/n): ").strip().lower() == 'y':
                    print("Exiting without saving.")
                    break
            else:
                print("Invalid choice!")

    def _edit_side_text(self, side):
        """Edit text for one side"""
        is_allied = (side == 'allied')
        lines = [block['text'] for i, block in enumerate(self.mission_blocks) if (i % 2 == 0) == is_allied]

        print(f"\n{'ALLIED' if is_allied else 'AXIS'} BRIEFING - Current Lines:")
        for i, line in enumerate(lines, 1):
            print(f"  [{i}] {line}")

        print("\nEnter line number to edit (or 'done'):")
        while True:
            choice = input("> ").strip().lower()

            if choice == 'done':
                break

            try:
                line_num = int(choice)
                if 1 <= line_num <= len(lines):
                    old_text = lines[line_num - 1]
                    print(f"\nCurrent text: {old_text}")
                    print(f"Max length: ~120 characters")

                    new_text = input("New text: ").strip()

                    if len(new_text) > 120:
                        print("⚠ WARNING: Text too long, truncating to 120 chars")
                        new_text = new_text[:120]

                    # Update in mission_blocks
                    block_idx = (line_num - 1) * 2 if is_allied else (line_num - 1) * 2 + 1
                    if block_idx < len(self.mission_blocks):
                        self.mission_blocks[block_idx]['text'] = new_text
                        print(f"✓ Updated line {line_num}")
                    else:
                        print("❌ Invalid line index")
                else:
                    print(f"Invalid line number! (1-{len(lines)})")
            except ValueError:
                print("Invalid input! Enter a number or 'done'")

    def save_scenario(self, output_file=None):
        """Save scenario with modifications"""
        if not self.scenario or not self.scenario_file:
            print("❌ No scenario loaded!")
            return False

        try:
            # Determine output file
            if output_file is None:
                output_file = self.scenario_file
            else:
                output_file = Path(output_file)

            # Create backup
            backup_file = Path(str(output_file) + '.bak')
            if output_file.exists():
                shutil.copy(output_file, backup_file)
                print(f"✓ Backup created: {backup_file}")

            # Apply mission text changes
            self._apply_mission_text_changes()

            # Write modified scenario
            self.scenario.write(output_file)

            print(f"✓ Saved: {output_file}")
            return True

        except Exception as e:
            print(f"❌ ERROR: Failed to save scenario: {e}")
            return False

    def _apply_mission_text_changes(self):
        """Apply mission text edits to scenario data"""
        data_array = bytearray(self.scenario.data)

        # Replace each text block with potentially modified text
        for block in self.mission_blocks:
            offset = block['offset']
            new_text = block['text']

            # Encode
            new_bytes = new_text.encode('ascii', errors='ignore')

            # Get original length
            original_length = block['length']

            # Pad or truncate to match original length
            if len(new_bytes) < original_length:
                new_bytes = new_bytes + (b' ' * (original_length - len(new_bytes)))
            elif len(new_bytes) > original_length:
                new_bytes = new_bytes[:original_length]

            # Replace in data
            data_array[offset:offset+len(new_bytes)] = new_bytes

        # Update scenario data
        self.scenario.data = bytes(data_array)

        # DON'T re-parse sections! The sections haven't changed,
        # only the pre-section data (mission text) has changed.
        # Re-parsing would extract sections from wrong offsets.

    def batch_edit(self, allied_lines=None, axis_lines=None, output_file=None):
        """Non-interactive batch editing"""
        if not self.scenario:
            print("❌ No scenario loaded!")
            return False

        # Update Allied lines
        if allied_lines:
            for i, new_text in enumerate(allied_lines):
                block_idx = i * 2
                if block_idx < len(self.mission_blocks):
                    self.mission_blocks[block_idx]['text'] = new_text

        # Update Axis lines
        if axis_lines:
            for i, new_text in enumerate(axis_lines):
                block_idx = i * 2 + 1
                if block_idx < len(self.mission_blocks):
                    self.mission_blocks[block_idx]['text'] = new_text

        return self.save_scenario(output_file)


def main():
    """Main CLI interface"""
    import sys

    print("=" * 80)
    print("D-DAY SCENARIO EDITOR - Command Line Interface")
    print("=" * 80)

    if len(sys.argv) < 2:
        print("\nUsage:")
        print("  Interactive mode:")
        print("    python3 scenario_editor_cli.py <scenario.scn>")
        print("\n  View mode:")
        print("    python3 scenario_editor_cli.py <scenario.scn> --view")
        print("\n  Batch mode:")
        print("    python3 scenario_editor_cli.py <scenario.scn> --batch")
        print("\nExample:")
        print("  python3 scenario_editor_cli.py game/dday/game/SCENARIO/OMAHA.SCN")
        sys.exit(1)

    scenario_file = sys.argv[1]

    # Create editor
    editor = ScenarioEditorCLI()

    # Load scenario
    if not editor.load_scenario(scenario_file):
        sys.exit(1)

    # Check mode
    if len(sys.argv) > 2 and sys.argv[2] == '--view':
        # View only mode
        editor.display_mission_text()
    else:
        # Interactive edit mode
        editor.edit_mission_text_interactive()


if __name__ == '__main__':
    main()
