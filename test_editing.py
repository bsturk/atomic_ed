#!/usr/bin/env python3
"""
Test actual scenario editing functionality
"""

from scenario_editor_cli import ScenarioEditorCLI
from dday_scenario_parser import DdayScenario
import hashlib
from pathlib import Path

def test_edit_scenario():
    """Test editing a scenario"""
    print("=" * 80)
    print("TESTING SCENARIO EDITING FUNCTIONALITY")
    print("=" * 80)

    # Load scenario
    original_file = 'game/dday/game/SCENARIO/OMAHA.SCN'
    test_file = 'OMAHA_EDITED_TEST.SCN'

    editor = ScenarioEditorCLI()

    print("\n1. Loading original scenario...")
    if not editor.load_scenario(original_file):
        print("❌ Failed to load!")
        return False

    print("\n2. Original mission text:")
    editor.display_mission_text()

    print("\n3. Modifying mission text...")
    # Batch edit - change first lines for both sides
    new_allied = [
        "TEST EDIT: Your primary mission is to secure the beaches!",
        "the Omaha and Utah beacheads by taking Isigny and Carentan.",
        "Secondary objectives are to liberate Caumont and St. Lo while",
        "inflicting more casualties than you incur.  It is a long, hard road",
        "but you hold the fate of Europe in your hands."
    ]

    new_axis = [
        "TEST EDIT: You must defend the Normandy coast at all costs!",
        "fighting 352nd Division is at your disposal, along with other,",
        "smaller formations.  You must prevent the Allies from linking up",
        "their two small beachheads and slow any attempted advance",
        "inland until the panzer reserve can be brought into action."
    ]

    if not editor.batch_edit(allied_lines=new_allied, axis_lines=new_axis, output_file=test_file):
        print("❌ Failed to save edited scenario!")
        return False

    print(f"\n4. Verifying edited scenario...")
    # Load the edited file
    edited_scenario = DdayScenario(test_file)
    if not edited_scenario.is_valid:
        print("❌ Edited file is invalid!")
        return False

    # Create new editor to view changes
    verify_editor = ScenarioEditorCLI()
    verify_editor.load_scenario(test_file)

    print("\n5. Modified mission text:")
    verify_editor.display_mission_text()

    # Check if text actually changed
    edited_blocks = verify_editor.mission_blocks
    if "TEST EDIT" in edited_blocks[0]['text'] and "TEST EDIT" in edited_blocks[1]['text']:
        print("\n✅ SUCCESS: Mission text was modified correctly!")

        # Compare file sizes
        original_size = Path(original_file).stat().st_size
        edited_size = Path(test_file).stat().st_size

        print(f"\nFile size comparison:")
        print(f"  Original: {original_size:,} bytes")
        print(f"  Edited:   {edited_size:,} bytes")

        if original_size == edited_size:
            print("  ✓ File size preserved!")
        else:
            print(f"  ⚠ File size changed by {edited_size - original_size:+,} bytes")

        return True
    else:
        print("\n❌ FAILED: Text was not modified!")
        return False


if __name__ == '__main__':
    success = test_edit_scenario()
    exit(0 if success else 1)
