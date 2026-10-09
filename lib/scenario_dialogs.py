"""Scenario creation, verified rules, objective and counter controls."""
import struct
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

from PIL import Image, ImageTk

from lib.game_art import load_bitmap, _counter_sheet
from lib.terrain_reader import TERRAIN_TYPES
from lib.unit_roster import UnitRoster
from lib.form_drafts import FormDraft, field_variable
from lib.game_profiles import GAMES, GameProfile
from lib.game_profile_dialog import GameProfilePanel
from lib.conditions_dialog import ConditionsEditor, BattlePlanEditor
from lib.scenario_data_dialog import DataEditor
from lib.scenario_data import set_start_date
from lib.scenario_rules import (new_scenario, scenario_dates, date_label, objectives,
                                edit_objective, set_rules, LOSS_CLASSES)


class NewScenarioDialog(tk.Toplevel):
    def __init__(self, app):
        super().__init__(app.root)
        self.app = app
        self.title('New Scenario')
        self.transient(app.root)
        body = ttk.Frame(self, padding=18)
        body.pack(fill='both', expand=True)
        self.values = {}
        for row, (key, title, default) in enumerate((('width', 'Map columns', '30'),
                ('height', 'Map rows', '24'), ('start_date', 'Start date (YYYY-MM-DD)', '1944-06-12'),
                ('turns', 'Duration (2–400 turns)', '12'))):
            ttk.Label(body, text=title).grid(row=row, column=0, sticky='w', pady=5)
            variable = tk.StringVar(value=default)
            ttk.Entry(body, textvariable=variable, width=22).grid(row=row, column=1, padx=10)
            self.values[key] = variable
        ttk.Label(body, text='Fill terrain').grid(row=4, column=0, sticky='w', pady=5)
        self.terrain = ttk.Combobox(body, state='readonly', values=[TERRAIN_TYPES[i] for i in range(14)])
        self.terrain.grid(row=4, column=1, padx=10)
        self.terrain.current(1)
        ttk.Label(body, text='Game profile').grid(row=5, column=0, sticky='w', pady=5)
        self.profile = ttk.Combobox(body, state='readonly', values=tuple(GAMES.values()), width=28)
        self.profile.grid(row=5, column=1, padx=10)
        self.profile.current(0)
        ttk.Label(body, text='Creates a blank map, empty briefings, and an empty roster.\n'
            'Add an HQ for each side on Units, then add and deploy its units.\n'
            'Set victory objectives on Scenario Settings.\n\n'
            'Starts with clear weather and supply entries at the north/south edges.\n'
            'Uses the selected profile and patched D-Day executable for DOS play.', wraplength=470).grid(
                row=6, column=0, columnspan=2, sticky='w', pady=15)
        buttons = ttk.Frame(body)
        buttons.grid(row=7, column=0, columnspan=2, sticky='e')
        ttk.Button(buttons, text='Cancel', command=self.destroy).pack(side='left', padx=5)
        ttk.Button(buttons, text='Create', command=self.submit).pack(side='left')
        self.bind('<Escape>', lambda e: self.destroy())
        self.grab_set()

    def submit(self):
        try:
            data = new_scenario(**{k: v.get() for k, v in self.values.items()}, terrain=self.terrain.current())
        except (ValueError, OSError) as exc:
            messagebox.showerror('Cannot Create Scenario', str(exc), parent=self)
            return
        self.app.create_scenario(data, GameProfile(tuple(GAMES)[self.profile.current()]))
        self.destroy()


class CounterDialog(tk.Toplevel):
    def __init__(self, parent, unit, selected, callback):
        super().__init__(parent)
        self.title(f"Choose chit — {unit['side']}")
        self.transient(parent.winfo_toplevel())
        self.callback = callback
        self.sheet = (_counter_sheet(unit['counter_bitmap']) if unit.get('counter_bitmap') is not None
                      else load_bitmap(unit['counter_resource']))
        self.selected = selected
        self.columns, self.rows = min(22, self.sheet.width//22), self.sheet.height//23
        ttk.Label(self, text='Click a chit, then Choose. This changes artwork, not unit type.', padding=10).pack()
        frame = ttk.Frame(self)
        frame.pack(fill='both', expand=True)
        self.canvas = tk.Canvas(frame, width=self.columns*44, height=min(460, self.rows*46), background='#dddddd')
        bar = ttk.Scrollbar(frame, orient='vertical', command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=bar.set, scrollregion=(0, 0, self.columns*44, self.rows*46))
        bar.pack(side='right', fill='y')
        self.canvas.pack(side='left', fill='both', expand=True)
        self.photo = ImageTk.PhotoImage(self.sheet.convert('RGBA').resize(
            (self.sheet.width*2, self.sheet.height*2), Image.Resampling.NEAREST))
        self.canvas.create_image(0, 0, image=self.photo, anchor='nw')
        self.outline = self.canvas.create_rectangle(0, 0, 0, 0, outline='#ff6600', width=3)
        self.label = ttk.Label(self, padding=8)
        self.label.pack(side='left')
        ttk.Button(self, text='Choose', command=self.choose).pack(side='right', padx=10, pady=8)
        ttk.Button(self, text='Cancel', command=self.destroy).pack(side='right')
        ttk.Button(self, text='Export Selected…', command=self.export_selected).pack(side='right', padx=8)
        self.canvas.bind('<Button-1>', self.select)
        self.canvas.bind('<Button-4>', lambda e: self.canvas.yview_scroll(-3, 'units'))
        self.canvas.bind('<Button-5>', lambda e: self.canvas.yview_scroll(3, 'units'))
        self.canvas.bind('<MouseWheel>', lambda e: self.canvas.yview_scroll(-1 if e.delta > 0 else 1, 'units'))
        self.show_selection()
        self.canvas.yview_moveto(max(0, selected//22-3)/max(1, self.rows))
        self.bind('<Escape>', lambda e: self.destroy())
        self.grab_set()

    def select(self, event):
        x, y = int(self.canvas.canvasx(event.x)//44), int(self.canvas.canvasy(event.y)//46)
        if 0 <= x < self.columns and 0 <= y < self.rows:
            self.selected = y*22+x
            self.show_selection()

    def show_selection(self):
        x, y = self.selected % 22 * 44, self.selected // 22 * 46
        self.canvas.coords(self.outline, x+1, y+1, x+43, y+45)
        self.label.config(text=f'Chit {self.selected}')

    def choose(self):
        self.callback(self.selected)
        self.destroy()

    def export_selected(self):
        filename = filedialog.asksaveasfilename(parent=self, title='Export Chit Image',
            initialfile=f'chit_{self.selected}.png', defaultextension='.png', filetypes=[('PNG image', '*.png')])
        if filename:
            try:
                x, y = self.selected%22*22, self.selected//22*23
                self.sheet.crop((x, y, x+22, y+23)).save(filename, format='PNG', transparency=0)
            except OSError as exc:
                messagebox.showerror('Cannot Export Chit', str(exc), parent=self)


class ScenarioSettingsEditor(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, padding=12)
        self.app, self.scenario = app, None
        self.tabs = ttk.Notebook(self)
        self.tabs.pack(fill='both', expand=True)
        victory = ttk.Frame(self.tabs)
        self.tabs.add(victory, text='Victory')
        self.profiles = GameProfilePanel(self.tabs, app)
        self.tabs.add(self.profiles, text='Game Profile')
        self.conditions = [self.profiles]
        for kind in ('weather', 'supply'):
            panel = ConditionsEditor(self.tabs, app, kind)
            self.tabs.add(panel, text=kind.title())
            self.conditions.append(panel)
        plans = BattlePlanEditor(self.tabs, app)
        self.tabs.add(plans, text='Battle Plans')
        self.conditions.append(plans)
        for kind in ('leaders', 'replacements', 'garrisons', 'depots'):
            panel = DataEditor(self.tabs, app, kind)
            self.tabs.add(panel, text=kind.title())
            self.conditions.append(panel)
        general = ttk.LabelFrame(victory, text='Duration and scoring', padding=10)
        general.pack(fill='x')
        self.date_text = ttk.Label(general)
        self.date_text.grid(row=0, column=0, columnspan=4, sticky='w', pady=5)
        ttk.Label(general, text='Turns:').grid(row=1, column=0, sticky='w')
        self.turn_spin = ttk.Spinbox(general, from_=2, to=400, width=10)
        self.turn_spin.grid(row=1, column=1, sticky='w', padx=6)
        ttk.Label(general, text='Start date (YYYY-MM-DD):').grid(row=1, column=2, sticky='w', padx=(15, 5))
        self.start_date = tk.StringVar()
        ttk.Entry(general, textvariable=self.start_date, width=15).grid(row=1, column=3, sticky='w')
        ttk.Label(general, text='Casualty scoring weights (by unit class):').grid(
            row=2, column=0, columnspan=4, sticky='w', pady=(12, 4))
        weights = ttk.Frame(general)
        weights.grid(row=3, column=0, columnspan=4, sticky='w')
        self.loss_spins = []
        for i, name in enumerate(LOSS_CLASSES):
            ttk.Label(weights, text=name).grid(row=0, column=i, padx=5)
            spin = ttk.Spinbox(weights, from_=0, to=10000, width=7)
            spin.grid(row=1, column=i, padx=5)
            self.loss_spins.append(spin)
        ttk.Button(general, text='Apply Settings', command=self.apply_settings).grid(row=4, column=0, pady=10)
        ttk.Button(general, text='Revert Form', command=self.revert_form).grid(
            row=4, column=1, pady=10)
        objective_frame = ttk.LabelFrame(victory, text='Victory objectives', padding=10)
        objective_frame.pack(fill='both', expand=True, pady=12)
        columns = ('name', 'x', 'y', 'allied', 'axis', 'owner', 'radius')
        self.tree = ttk.Treeview(objective_frame, columns=columns, show='headings', height=8, selectmode='browse')
        for key, label in zip(columns, ('Name', 'X', 'Y', 'Allied value', 'Axis value', 'Initial owner', 'Radius')):
            self.tree.heading(key, text=label)
            width = 220 if key == 'name' else 55 if key in ('x', 'y') else 75 if key == 'radius' else 120
            self.tree.column(key, width=width, stretch=key == 'name')
        scroll = ttk.Scrollbar(objective_frame, orient='vertical', command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll.set)
        scroll.pack(side='right', fill='y')
        self.tree.pack(fill='both', expand=True)
        self.tree.bind('<Double-1>', lambda e: self.edit_selected())
        buttons = ttk.Frame(objective_frame)
        buttons.pack(fill='x', pady=(8, 0))
        for text, command in (('Add Objective', lambda: self.edit_selected(new=True)),
                              ('Edit Objective', self.edit_selected), ('Remove Objective', self.remove_selected)):
            ttk.Button(buttons, text=text, command=command).pack(side='left', padx=(0, 6))
        self.feedback = ttk.Label(self)
        self.feedback.pack(anchor='w', pady=5)
        fields = dict(turns=field_variable(self.turn_spin), start_date=self.start_date)
        fields.update({f'loss{i}': field_variable(spin) for i, spin in enumerate(self.loss_spins)})
        self.draft = FormDraft(self, 'Duration, date and scoring', fields, app._draft_changed,
                               self.prepare_draft)

    def prepare_draft(self, data, context, values, changes):
        roster = UnitRoster(data)
        start, end = scenario_dates(roster)
        losses = [changes.get(f'loss{i}', struct.unpack_from('<i', roster.header, 4+i*4)[0])
                  for i in range(len(self.loss_spins))]
        data = set_rules(data, changes.get('turns', end-start+1), losses)
        return set_start_date(data, changes['start_date']) if 'start_date' in changes else data

    def revert_form(self):
        self.draft.revert()
        self.load_scenario_data(self.scenario)

    def load_scenario_data(self, scenario):
        with self.draft.load('settings' if scenario else None):
            self._load_scenario_data(scenario)

    def _load_scenario_data(self, scenario):
        self.scenario = scenario
        if not scenario:
            return
        roster = UnitRoster(self.app._staged_data(include_briefings=False))
        for panel in self.conditions:
            panel.load(roster)
        start, end = scenario_dates(roster)
        from lib.scenario_rules import turns_per_day
        per_day = turns_per_day(roster)
        self.date_text.config(text=f'Start: {date_label(start, per_day)}     End: {date_label(end, per_day)}')
        self.start_date.set(date_label(start, per_day).split(' ·')[0])
        self.turn_spin.set(end-start+1)
        for i, spin in enumerate(self.loss_spins):
            spin.set(struct.unpack_from('<i', roster.header, 4+i*4)[0])
        self.tree.delete(*self.tree.get_children())
        self.objectives = objectives(roster)
        for index, obj in enumerate(self.objectives):
            self.tree.insert('', 'end', iid=str(index), values=(obj['name'], obj['x'], obj['y'],
                obj['allied'], obj['axis'], ('Allied', 'Axis')[obj['owner']] if obj['owner'] in (0, 1)
                else f"Unknown ({obj['owner']})", obj['radius']))

    def apply_settings(self):
        if not self.scenario:
            return
        try:
            data = set_rules(self.app._staged_data(include_briefings=False), self.turn_spin.get(),
                             [spin.get() for spin in self.loss_spins])
            data = set_start_date(data, self.start_date.get())
            self.app.apply_scenario_rules(data, 'Update duration, start date and scoring')
        except ValueError as exc:
            messagebox.showerror('Invalid settings', str(exc))
            return
        self.feedback.config(text='Settings applied. Use Save to write them.')
        self.draft.accept()
        return True

    def edit_selected(self, new=False):
        if not self.scenario:
            return
        selected = self.tree.selection()
        if not new and not selected:
            return
        index = None if new else int(selected[0])
        x, y = self.app.map_viewer.selected_hex or (0, 0)
        obj = dict(name='Objective', x=x, y=y, allied=100, axis=100, owner=0, radius=0) if new else self.objectives[index]
        dialog = tk.Toplevel(self)
        dialog.title('Add Objective' if new else 'Edit Objective')
        dialog.transient(self.winfo_toplevel())
        form = ttk.Frame(dialog, padding=15)
        form.pack(fill='both', expand=True)
        values = {}
        for row, (key, label) in enumerate((('name', 'Name'), ('x', 'Hex X'), ('y', 'Hex Y'),
                ('allied', 'Allied value'), ('axis', 'Axis value'), ('radius', 'Control radius (0–2 hexes)'),
                ('owner', 'Initial owner'))):
            ttk.Label(form, text=label).grid(row=row, column=0, sticky='w', pady=4)
            variable = tk.StringVar(value=('Allied', 'Axis')[obj[key]] if key == 'owner' else str(obj[key]))
            widget = (ttk.Combobox(form, textvariable=variable, values=('Allied', 'Axis'), state='readonly')
                      if key == 'owner' else ttk.Entry(form, textvariable=variable))
            widget.grid(row=row, column=1, padx=8)
            values[key] = variable
        def submit():
            v = {k: var.get() for k, var in values.items()}
            v['owner'] = ('Allied', 'Axis').index(v['owner'])
            try:
                data = edit_objective(self.app._staged_data(include_briefings=False), index, v)
                self.app.apply_scenario_rules(data, f'{"Add" if new else "Edit"} objective {v["name"]}')
            except ValueError as exc:
                messagebox.showerror('Invalid objective', str(exc), parent=dialog)
                return
            dialog.destroy()
        ttk.Button(form, text='Apply', command=submit).grid(row=7, column=1, sticky='e', pady=12)
        dialog.grab_set()

    def remove_selected(self):
        selected = self.tree.selection()
        if selected:
            data = edit_objective(self.app._staged_data(include_briefings=False), int(selected[0]))
            self.app.apply_scenario_rules(data, f'Remove objective {self.objectives[int(selected[0])]["name"]}')
