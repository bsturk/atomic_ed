"""Regression checks for stacking, map shifts, dates and unapplied form validation.

Requires installed D-Day scenarios; run Tk cases with xvfb-run on headless hosts.
"""
from pathlib import Path
import struct
import sys
import tempfile
import tkinter as tk
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lib.scenario_rules import (synchronize_occupancy, new_scenario, edit_objective,
                                scenario_dates)
from lib.unit_definitions import edit_definition
from lib.scenario_data import set_start_date
from lib.unit_roster import UnitRoster
from lib.game_resources import game_path
from lib.bulk_edit import shift_map
from lib.scenario_conditions import supply_groups
from lib.scenario_parser import DdayScenario
from lib.unit_reader import read_units
from lib.terrain_reader import read_map_layers
from scenario_editor import ImprovedScenarioEditor

SOURCE = game_path('dday', 'SCENARIO', 'BRADLEY.SCN')


def populated_scenario():
    roster = UnitRoster(new_scenario(16, 12))
    source = UnitRoster(SOURCE.read_bytes())
    for side in (0, 1):
        for cls in (7, 0, 1, 4):
            index = next(i for i, u in enumerate(source.records[side]) if u[0x76] == cls)
            added = roster.add(side, index, f'{side}-{cls}', source=source)
            unit = roster.records[side][added]
            struct.pack_into('<2h', unit, 0x58, 4+added, 2 if side == 0 else 9)
            struct.pack_into('<i', unit, 8, scenario_dates(roster)[0]-1)
    return edit_objective(synchronize_occupancy(roster.to_bytes()), None,
        dict(name='Crossroads', x=8, y=6, allied=100, axis=100, radius=0, owner=1))


def stacked_scenario(points=14):
    roster = UnitRoster(populated_scenario())
    infantry, armor, artillery = roster.records[0][1:4]
    infantry[0x7e], armor[0x7e], artillery[0x7e] = 7, points-7, 2
    armor[0x58:0x5c] = infantry[0x58:0x5c]
    return synchronize_occupancy(roster.to_bytes())


@unittest.skipUnless(SOURCE.exists(), 'D-Day scenarios unavailable')
class ScenarioRuleRegressionTests(unittest.TestCase):
    def test_fresh_map_shifts_left_with_empty_battlegroup_goals(self):
        source = new_scenario()
        before = UnitRoster(source)
        changed = shift_map(source, -1, 0)
        after = UnitRoster(changed)
        self.assertEqual(after.to_bytes(), changed)
        self.assertEqual(after.records, [[], []])
        for key in ('bgstate', 'bgshx', 'bgshy'):
            self.assertEqual(after.blocks[key], bytes(800))
        for key in ('bgdhx', 'bgdhy'):
            self.assertEqual(before.blocks[key], b'\xff'*800)
            self.assertEqual(after.blocks[key], before.blocks[key])
        for side in (0, 1):
            old = supply_groups(before, side)[0]['entries'][0]
            new = supply_groups(after, side)[0]['entries'][0]
            self.assertEqual(new, (old[0]-1, old[1], old[2]))
        parsed = DdayScenario.from_bytes(changed, '/tmp/shifted.SCN')
        self.assertEqual(read_map_layers(parsed).terrain[29, 0], (1, 0))

    def test_shift_keeps_an_existing_oversized_stack(self):
        changed = UnitRoster(shift_map(stacked_scenario(18), 1, 0))
        self.assertEqual([struct.unpack_from('<2h', r, 0x58) for r in changed.records[0][1:3]],
                         [(6, 2), (6, 2)])
        word = struct.unpack_from('<I', changed.blocks['zoc'], (2*16+6)*4)[0]
        self.assertEqual((word >> 17) & 15, 15)

    def test_start_date_shifts_destruction_times_but_not_aircraft_strength(self):
        source = SOURCE.read_bytes()
        before = UnitRoster(source)
        after = UnitRoster(set_start_date(source, '1944-07-20'))
        delta = scenario_dates(after)[0]-scenario_dates(before)[0]
        self.assertTrue(delta)
        self.assertTrue(any(u[0x76] == 6 and struct.unpack_from('<i', u, 0x40)[0] > 0
                            for u in before.records[0]))
        for side in (0, 1):
            for old, new in zip(before.records[side], after.records[side]):
                value = struct.unpack_from('<i', old, 0x40)[0]
                expected = value+delta if value > 0 and old[0x76] != 6 else value
                self.assertEqual(struct.unpack_from('<i', new, 0x40)[0], expected)

    def test_definition_cannot_create_an_oversized_stack(self):
        data = stacked_scenario()
        with self.assertRaisesRegex(ValueError, '15-point'):
            edit_definition(data, 0, 1, {'stacking_size': 9})
        changed = UnitRoster(edit_definition(data, 0, 1, {'stacking_size': 8}))
        word = struct.unpack_from('<I', changed.blocks['zoc'], (2*16+5)*4)[0]
        self.assertEqual((word >> 17) & 15, 15)

    def test_definition_preserves_or_reduces_existing_oversized_stacks(self):
        data = stacked_scenario(18)
        changed = UnitRoster(edit_definition(data, 0, 1, {'movement_allowance': 7.25}))
        self.assertEqual([r[0x7e] for r in changed.records[0][1:3]], [7, 11])
        changed = UnitRoster(edit_definition(data, 0, 1, {'stacking_size': 6}))
        self.assertEqual([r[0x7e] for r in changed.records[0][1:3]], [6, 11])
        with self.assertRaisesRegex(ValueError, '15-point'):
            edit_definition(data, 0, 1, {'stacking_size': 8})


@unittest.skipUnless(SOURCE.exists(), 'D-Day scenarios unavailable')
class FormRegressionTests(unittest.TestCase):
    def setUp(self):
        try:
            self.app = ImprovedScenarioEditor()
        except tk.TclError as exc:
            self.skipTest(str(exc))
        self.app.root.withdraw()
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / 'BRADLEY.SCN'
        self.original = populated_scenario()
        self.path.write_bytes(self.original)
        self.errors = []
        self.callbacks = []
        self.app.root.report_callback_exception = lambda *args: self.callbacks.append(args)
        for target, kwargs in (
                ('scenario_editor.messagebox.showerror', dict(side_effect=lambda *a, **k: self.errors.append(a))),
                ('scenario_editor.messagebox.showinfo', {}),
                ('scenario_editor.messagebox.showwarning', {}),
                ('scenario_editor.messagebox.askyesno', dict(return_value=True)),
                ('scenario_editor.ask_save_changes', dict(return_value=None))):
            mock = patch(target, **kwargs)
            mock.start()
            self.addCleanup(mock.stop)
        self.app.open_scenario(str(self.path))
        self.app.root.update()

    def tearDown(self):
        if hasattr(self, 'app'):
            if not self.app._closing:
                for timer in self.app.root.tk.call('after', 'info'):
                    self.app.root.tk.call('after', 'cancel', timer)
                self.app.root.destroy()
            self.temp.cleanup()
            self.assertFalse(self.callbacks)
            self.assertFalse(self.errors)

    def name(self, text):
        widget = self.app.unit_props_editor.name_entry
        widget.delete('0', 'end')
        widget.insert('0', text)

    def select_unit(self, index):
        editor = self.app.unit_props_editor
        editor.unit_combo.current(index)
        editor.on_unit_selected(None)

    def load_data(self, data):
        self.original = data
        self.path.write_bytes(self.original)
        with patch('scenario_editor.ask_save_changes', return_value='discard'):
            self.app.open_scenario(str(self.path))
        self.app.root.update()

    def load_stack(self, points=14):
        self.load_data(stacked_scenario(points))

    def assert_overflow_rejected(self):
        self.assertEqual(self.app._staged_data(), self.original)
        self.assertEqual(self.path.read_bytes(), self.original)
        self.assertEqual(self.app.history.position, 0)
        self.assertEqual(self.app.history.entries, [])
        self.assertEqual(len(self.errors), 1)
        self.assertIn('15-point', str(self.errors[0]))
        self.errors.clear()

    def test_map_placement_rejects_stack_overflow(self):
        for points in (14, 18):
            with self.subTest(points=points):
                self.load_stack(points)
                self.app.place_map_unit(self.app.units[3], (5, 2), 'Deploy at start')
                self.assert_overflow_rejected()

    def test_copying_a_unit_rejects_stack_overflow(self):
        self.load_stack()
        self.assertFalse(self.app.create_unit(self.app.units[1], 'Copied unit'))
        self.assert_overflow_rejected()

    def test_unit_properties_reject_stack_overflow(self):
        for points in (14, 18):
            with self.subTest(points=points):
                self.load_stack(points)
                self.select_unit(3)
                self.app.unit_props_editor.pos_x_spin.set(5)
                self.assertFalse(self.app.unit_props_editor.apply_changes())
                self.assertTrue(self.app.unit_props_editor.draft.pending())
                self.assert_overflow_rejected()

    def test_save_rejects_hidden_draft_stack_overflow_atomically(self):
        for points in (14, 18):
            with self.subTest(points=points):
                self.load_stack(points)
                self.select_unit(3)
                self.app.unit_props_editor.pos_x_spin.set(5)
                self.select_unit(0)
                self.name('Other valid draft')
                self.assertFalse(self.app.save_scenario())
                self.assertTrue(self.app.unit_props_editor.draft.pending())
                # The error selects the draft that causes the overflow.
                self.assertEqual(self.app.unit_props_editor.current_unit['side_index'], 3)
                self.assert_overflow_rejected()

    def test_restoring_a_unit_rejects_stack_overflow(self):
        roster = UnitRoster(stacked_scenario())
        roster.remove(0, 3)
        struct.pack_into('<2h', roster.records[0][3], 0x5c, 5, 2)
        self.load_data(synchronize_occupancy(roster.to_bytes()))
        self.app.unit_filter_var.set('Deleted')
        self.assertEqual(self.app.unit_props_editor.current_unit['side_index'], 3)
        self.app.delete_unit()
        self.assert_overflow_rejected()

    def test_each_edit_path_accepts_exactly_15_points(self):
        for mode in ('map', 'properties', 'draft'):
            with self.subTest(mode=mode):
                self.load_stack(13)
                if mode == 'map':
                    self.app.place_map_unit(self.app.units[3], (5, 2), 'Deploy at start')
                else:
                    self.select_unit(3)
                    self.app.unit_props_editor.pos_x_spin.set(5)
                    if mode == 'properties':
                        self.assertTrue(self.app.unit_props_editor.apply_changes())
                    else:
                        self.assertTrue(self.app._apply_form_drafts())
                self.assertEqual(self.app.units[3]['x'], 5)
                word = struct.unpack_from('<I', UnitRoster(self.app._staged_data()).blocks['zoc'],
                                          (2*16+5)*4)[0]
                self.assertEqual((word >> 17) & 15, 15)

    def test_existing_oversized_stack_can_shrink_through_each_edit_path(self):
        for mode in ('map', 'properties', 'draft'):
            with self.subTest(mode=mode):
                roster = UnitRoster(stacked_scenario(18))
                struct.pack_into('<2h', roster.records[0][3], 0x58, 5, 2)
                self.load_data(synchronize_occupancy(roster.to_bytes()))
                if mode == 'map':
                    self.app.place_map_unit(self.app.units[3], (8, 2), 'Deploy at start')
                else:
                    self.select_unit(3)
                    self.app.unit_props_editor.pos_x_spin.set(8)
                    if mode == 'properties':
                        self.assertTrue(self.app.unit_props_editor.apply_changes())
                    else:
                        self.assertTrue(self.app._apply_form_drafts())
                self.assertEqual(self.app.units[3]['x'], 8)
                self.assertEqual(self.app.history.position, 1)
                # The original 20-point stack shrank to 18, still above 15.
                roster = UnitRoster(self.app._staged_data())
                self.assertEqual([r[0x7e] for r in roster.records[0][1:3]], [7, 11])

    def test_edits_preserve_unaffected_oversized_stacks(self):
        for mode in ('map', 'properties', 'draft'):
            with self.subTest(mode=mode):
                self.load_stack(18)
                if mode == 'map':
                    self.app.place_map_unit(self.app.units[3], (8, 2), 'Deploy at start')
                else:
                    self.select_unit(1)
                    self.name('Renamed oversized stack')
                    if mode == 'properties':
                        self.assertTrue(self.app.unit_props_editor.apply_changes())
                    else:
                        self.assertTrue(self.app._apply_form_drafts())
                self.assertEqual(self.app.history.position, 1)
                roster = UnitRoster(self.app._staged_data())
                self.assertEqual([r[0x7e] for r in roster.records[0][1:3]], [7, 11])

    def test_arrival_edits_reject_activating_an_oversized_stack(self):
        for mode in ('properties', 'draft'):
            with self.subTest(mode=mode):
                roster = UnitRoster(stacked_scenario())
                unit = roster.records[0][3]
                struct.pack_into('<2h', unit, 0x58, 5, 2)
                struct.pack_into('<i', unit, 8, scenario_dates(roster)[0]+2)
                self.load_data(synchronize_occupancy(roster.to_bytes()))
                self.select_unit(3)
                self.app.unit_props_editor.availability_var.set('At start')
                if mode == 'properties':
                    self.assertFalse(self.app.unit_props_editor.apply_changes())
                else:
                    self.assertFalse(self.app._apply_form_drafts())
                self.assert_overflow_rejected()

    def test_drafts_check_the_combined_final_stack(self):
        self.load_stack()
        self.select_unit(3)
        self.app.unit_props_editor.pos_x_spin.set(5)
        self.select_unit(1)
        self.app.unit_props_editor.pos_x_spin.set(7)
        # The first draft alone would overflow; the two together are valid.
        self.assertTrue(self.app._apply_form_drafts())
        self.assertEqual([u['x'] for u in self.app.units[1:4]], [7, 5, 5])
        self.assertEqual(self.app.history.position, 1)

    def test_validate_includes_hidden_drafts_without_applying_them(self):
        app = self.app
        self.name('Hidden pending name')
        self.select_unit(1)
        app.settings_editor.turn_spin.set(18)
        app.allied_text.insert('1.0', 'Pending briefing ')
        app.root.update()
        before = app._staged_data()
        drafts = [form.pending() for form in app._draft_forms()]
        history = dict(app.history.__dict__)
        history['entries'] = list(app.history.entries)
        with patch('scenario_editor.authoring_warnings', return_value=[]) as validate:
            app.validate_scenario()
        candidate = validate.call_args.args[0]
        parsed = DdayScenario.from_bytes(candidate, str(self.path))
        self.assertEqual(read_units(parsed)[0]['name'], 'Hidden pending name')
        start, end = scenario_dates(UnitRoster(candidate))
        self.assertEqual(end-start+1, 18)
        self.assertEqual(app._staged_data(), before)
        self.assertEqual([form.pending() for form in app._draft_forms()], drafts)
        self.assertEqual(app.history.__dict__, history)
        self.assertTrue(app.modified)
        self.assertEqual(self.path.read_bytes(), self.original)
        self.assertTrue(app.save_scenario())
        self.assertEqual(self.path.read_bytes(), candidate)

    def test_validate_reports_invalid_hidden_draft_without_committing(self):
        app = self.app
        self.select_unit(1)
        app.unit_props_editor.stat_spins['quality'].set('invalid')
        self.select_unit(0)
        self.name('Valid pending draft')
        app.root.update()
        drafts = [form.pending() for form in app._draft_forms()]
        with patch('scenario_editor.authoring_warnings') as validate:
            app.validate_scenario()
        validate.assert_not_called()
        self.assertEqual(len(self.errors), 1)
        self.errors.clear()
        self.assertEqual(app._staged_data(), self.original)
        self.assertEqual(app.history.entries, [])
        self.assertEqual([form.pending() for form in app._draft_forms()], drafts)

    def test_validate_rejects_draft_stack_overflow_without_applying(self):
        self.load_stack()
        self.select_unit(3)
        self.app.unit_props_editor.pos_x_spin.set(5)
        self.select_unit(0)
        self.name('Other valid draft')
        self.app.validate_scenario()
        self.assertTrue(self.app.unit_props_editor.draft.pending())
        self.assertEqual(self.app.unit_props_editor.current_unit['side_index'], 3)
        self.assert_overflow_rejected()


if __name__ == '__main__':
    unittest.main()
