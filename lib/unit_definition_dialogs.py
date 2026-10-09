"""Units-page organization and definition controls."""
import tkinter as tk
from tkinter import ttk, messagebox

from lib.unit_definitions import (CLASSES, MOBILITY, NATIONALITIES, HQ_LEVELS,
                                  GROUND_CLASSES, ARTILLERY_FIELDS, headquarters,
                                  definition, edit_organization, edit_definition)
from lib.unit_reader import decode_record, unit_type_name
from lib.unit_roster import UnitRoster
from lib.unit_types import TYPE_DESCRIPTIONS


class OrganizationDialog(tk.Toplevel):
    def __init__(self, app):
        super().__init__(app.root)
        self.app = app
        self.title('HQ Organization')
        self.transient(app.root)
        self.geometry('860x620')
        self.minsize(680, 480)
        body = ttk.Frame(self, padding=12)
        body.pack(fill=tk.BOTH, expand=True)
        body.columnconfigure(0, weight=1)
        body.rowconfigure(1, weight=1)
        top = ttk.Frame(body)
        top.grid(row=0, column=0, sticky=tk.EW, pady=(0, 8))
        ttk.Label(top, text='Side:').pack(side=tk.LEFT)
        current = app.unit_props_editor.current_unit
        self.side = ttk.Combobox(top, values=('Allied', 'Axis'), state='readonly', width=12)
        self.side.pack(side=tk.LEFT, padx=8)
        self.side.current(int(current is not None and current['side'] == 'Axis'))
        self.side.bind('<<ComboboxSelected>>', lambda _: self.reload())
        self.summary = ttk.Label(top)
        self.summary.pack(side=tk.LEFT, padx=8)
        frame = ttk.Frame(body)
        frame.grid(row=1, column=0, sticky=tk.NSEW)
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(0, weight=1)
        self.tree = ttk.Treeview(frame, columns=('kind', 'span'), selectmode='browse')
        self.tree.heading('#0', text='HQ and assigned units')
        self.tree.heading('kind', text='Command level / unit type')
        self.tree.heading('span', text='Used / limit')
        self.tree.column('#0', width=300)
        self.tree.column('kind', width=210)
        self.tree.column('span', width=120, stretch=False)
        self.tree.grid(row=0, column=0, sticky=tk.NSEW)
        scroll = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=self.tree.yview)
        scroll.grid(row=0, column=1, sticky=tk.NS)
        self.tree.configure(yscrollcommand=scroll.set)
        self.tree.bind('<<TreeviewSelect>>', self.select)
        controls = ttk.LabelFrame(body, text='Selected unit', padding=10)
        controls.grid(row=2, column=0, sticky=tk.EW, pady=10)
        controls.columnconfigure(1, weight=1)
        self.selected_label = ttk.Label(controls)
        self.selected_label.grid(row=0, column=0, columnspan=4, sticky=tk.W, pady=(0, 8))
        self.assignment_label = ttk.Label(controls, text='HQ:')
        self.assignment_label.grid(row=1, column=0, sticky=tk.W)
        self.assignment = ttk.Combobox(controls, state='readonly', width=26)
        self.assignment.grid(row=1, column=1, sticky=tk.EW, padx=8)
        ttk.Label(controls, text='Level:').grid(row=1, column=2)
        self.level = ttk.Combobox(controls, values=HQ_LEVELS, state='readonly', width=18)
        self.level.grid(row=1, column=3, padx=(8, 0))
        self.hint = ttk.Label(controls, wraplength=750)
        self.hint.grid(row=2, column=0, columnspan=4, sticky=tk.W, pady=(8, 0))
        buttons = ttk.Frame(body)
        buttons.grid(row=3, column=0, sticky=tk.EW)
        self.feedback = ttk.Label(buttons)
        self.feedback.pack(side=tk.LEFT)
        ttk.Button(buttons, text='Close', command=self.destroy).pack(side=tk.RIGHT)
        self.apply = ttk.Button(buttons, text='Apply Organization', command=self.submit)
        self.apply.pack(side=tk.RIGHT, padx=8)
        self.reload(current['side_index'] if current else None)
        self.grab_set()

    def reload(self, selected=None):
        self.roster = UnitRoster(self.app._staged_data(include_briefings=False))
        side = self.side.current()
        self.hqs = headquarters(self.roster, side)
        self.tree.delete(*self.tree.get_children())
        inserted = set()

        def add_hq(hq, path=()):
            if hq['id'] in inserted:
                return
            parent = hq['parent']
            if 0 <= parent < len(self.hqs) and parent not in path and parent != hq['id']:
                add_hq(self.hqs[parent], (*path, hq['id']))
            parent_key = f"u{self.hqs[parent]['index']}" if parent in inserted else ''
            key = f"u{hq['index']}"
            if self.tree.exists(key):
                return
            self.tree.insert(parent_key, tk.END, iid=key, open=True,
                             text=hq['name'] + (' (deleted)' if hq['deleted'] else ''),
                             values=(HQ_LEVELS[hq['level']] if 0 <= hq['level'] < 4 else '?',
                                     f"{hq['used']} / {hq['capacity']}"))
            inserted.add(hq['id'])

        for hq in self.hqs:
            add_hq(hq)
        count = 0
        for index, record in enumerate(self.roster.records[side]):
            unit = decode_record(record)
            if unit['unit_class'] == 7 or unit['deleted']:
                continue
            count += 1
            hq = unit['hq_index']
            parent = f"u{self.hqs[hq]['index']}" if unit['unit_class'] not in (5, 6) and hq < len(self.hqs) else ''
            self.tree.insert(parent, tk.END, iid=f'u{index}', text=unit['name'], values=(unit['type_name'], ''))
        self.summary.config(text=f'{len(self.hqs)} HQs · {count} other units')
        items = self.tree.get_children()
        key = f'u{selected}' if selected is not None else items[0] if items else ''
        if key and self.tree.exists(key):
            self.tree.selection_set(key)
            self.tree.see(key)
        self.select()

    def select(self, event=None):
        selected = self.tree.selection()
        self.index = int(selected[0][1:]) if selected else None
        if self.index is None:
            self.selected_label.config(text='Add an HQ on the Units page to begin organizing this side.')
            self.assignment.set('')
            self.assignment.config(state='disabled')
            self.level.set('')
            self.level.config(state='disabled')
            self.apply.config(state='disabled')
            return
        record = self.roster.records[self.side.current()][self.index]
        unit = decode_record(record)
        self.selected_label.config(text=unit['name'])
        is_hq = unit['unit_class'] == 7
        enabled = unit['unit_class'] not in (5, 6) and not unit['deleted']
        self.assignment_label.config(text='Parent HQ:' if is_hq else 'Assigned HQ:')
        self.choices = ([-1] if is_hq else []) + [h['id'] for h in self.hqs
                        if not h['deleted'] and (not is_hq or h['id'] != unit['hq_index'])]
        labels = [('Independent / root' if i == -1 else f"{i+1}: {self.hqs[i]['name']}") for i in self.choices]
        self.assignment.config(values=labels, state='readonly' if enabled else 'disabled')
        target = self.hqs[unit['hq_index']]['parent'] if is_hq else unit['hq_index']
        self.assignment.set('')
        if target in self.choices and enabled:
            self.assignment.current(self.choices.index(target))
        self.level.config(state='readonly' if enabled and is_hq else 'disabled')
        self.level.set(HQ_LEVELS[self.hqs[unit['hq_index']]['level']] if is_hq else '')
        self.apply.config(state='normal' if enabled else 'disabled')
        self.hint.config(text=('The parent must be a higher command level. Assigned units move with this HQ.' if is_hq else
                              'Reassignment sets the unit’s assigned and home HQ for the scenario.' if enabled else
                              'Aircraft and naval support operate outside the ground HQ hierarchy.' if not unit['deleted'] else
                              'Restore this HQ on the Units page before editing it.'))

    def submit(self):
        if self.index is None or self.assignment.current() < 0:
            return
        side = self.side.current()
        record = self.roster.records[side][self.index]
        target = self.choices[self.assignment.current()]
        values = dict(parent=target, level=self.level.current()) if record[0x76] == 7 else dict(hq=target)
        try:
            before = self.app._staged_data(include_briefings=False)
            data = edit_organization(before, side, self.index, **values)
            self.app.apply_unit_structure(data, side, self.index, 'Updated HQ organization')
        except (ValueError, IndexError) as exc:
            messagebox.showerror('Cannot change organization', str(exc), parent=self)
            return
        self.reload(self.index)
        self.feedback.config(text='Organization applied. Use File → Save.' if data != before else 'No changes.')


class UnitDefinitionDialog(tk.Toplevel):
    def __init__(self, app):
        super().__init__(app.root)
        self.app = app
        self.unit = dict(app.unit_props_editor.current_unit)
        self.title(f"Unit Definition — {self.unit['name']}")
        self.transient(app.root)
        self.resizable(False, False)
        self.roster = UnitRoster(app._staged_data(include_briefings=False))
        self.source_side = int(self.unit['side'] == 'Axis')
        self.original = definition(self.roster, self.source_side, self.unit['side_index'])
        self.fields, self.options = {}, {}
        body = ttk.Frame(self, padding=16)
        body.pack(fill=tk.BOTH, expand=True)
        body.columnconfigure(1, weight=1)
        self.side = self.combo(body, 0, 'Side', 'side', {i: s for i, s in enumerate(('Allied', 'Axis'))}, self.source_side)
        self.side.bind('<<ComboboxSelected>>', self.update_side)
        cls = self.original['unit_class']
        classes = GROUND_CLASSES if cls in GROUND_CLASSES else (cls,)
        self.class_combo = self.combo(body, 1, 'Class', 'unit_class', {i: CLASSES[i] for i in classes}, cls)
        self.class_combo.bind('<<ComboboxSelected>>', self.update_artillery)
        descriptors = (range(30, 35) if cls == 5 else
                       (36, 37, 38, 94, 95) if cls == 6 else
                       [i for i in range(len(TYPE_DESCRIPTIONS)) if i not in (*range(30, 39), 94, 95)])
        # Keep an unusual preexisting descriptor available without inventing a replacement.
        descriptors = sorted(set(descriptors) | {self.original['type']})
        self.combo(body, 2, 'Category' if cls in (5, 6) else 'Descriptor', 'type',
                   {i: f'{TYPE_DESCRIPTIONS[i] or "None"} ({i})'
                   for i in descriptors}, self.original['type']).bind('<<ComboboxSelected>>', self.update_artillery)
        self.combo(body, 3, 'Nationality', 'nationality', dict(enumerate(NATIONALITIES)), self.original['nationality'])
        self.combo(body, 4, 'Movement class', 'mobility', dict(enumerate(MOBILITY)) if cls not in (5, 6)
                   else {self.original['mobility']: f"Support profile {self.original['mobility']}"}, self.original['mobility'])
        self.spin(body, 5, 'Base movement allowance', 'movement_allowance', self.original['movement_allowance'], 0, 32.767)
        self.spin(body, 6, 'Stacking points', 'stacking_size', self.original['stacking_size'], 1, 15)
        if cls in (5, 6, 7):
            self.fields['stacking_size'].config(state='disabled')
        if cls == 7:
            self.side.config(state='disabled')
        self.transfer_hint = ttk.Label(body, wraplength=480)
        self.transfer_hint.grid(row=7, column=0, columnspan=2, sticky=tk.W, pady=8)
        self.guns = ttk.LabelFrame(body, text='Artillery and bombardment', padding=10)
        self.guns.grid(row=8, column=0, columnspan=2, sticky=tk.EW, pady=8)
        labels = {'bombardment': 'Base bombardment strength', 'defensive_fire': 'Base defensive fire strength',
                  'range': 'Range (hexes)', 'preparation_turns': 'Preparation turns', 'ammo_category': 'Ammunition category',
                  'shoot_scoot': 'Shoot ’n scoot capable (0/1)'}
        for row, (key, (_, _, scale, low, high)) in enumerate(ARTILLERY_FIELDS.items()):
            self.spin(self.guns, row, labels[key], key, self.original.get(key, 1 if key in ('range', 'ammo_category') else 0), low/scale, high/scale)
        self.gun_hint = ttk.Label(self.guns, wraplength=460,
            text='Strengths use up to three decimal places. Ammunition categories 0–3 select the game’s supply-consumption table.')
        self.gun_hint.grid(row=len(ARTILLERY_FIELDS), column=0, columnspan=2, sticky=tk.W, pady=(8, 0))
        self.update_artillery()
        self.update_side()
        buttons = ttk.Frame(body)
        buttons.grid(row=9, column=0, columnspan=2, sticky=tk.E, pady=(10, 0))
        ttk.Button(buttons, text='Cancel', command=self.destroy).pack(side=tk.LEFT, padx=8)
        ttk.Button(buttons, text='Apply Definition', command=self.submit).pack(side=tk.LEFT)
        self.grab_set()

    def combo(self, parent, row, label, key, choices, value):
        ttk.Label(parent, text=label + ':').grid(row=row, column=0, sticky=tk.W, pady=4)
        combo = ttk.Combobox(parent, state='readonly', values=list(choices.values()), width=32)
        combo.grid(row=row, column=1, sticky=tk.EW, padx=(12, 0), pady=4)
        self.fields[key], self.options[key] = combo, list(choices)
        if value in choices:
            combo.current(self.options[key].index(value))
        return combo

    def spin(self, parent, row, label, key, value, low, high):
        ttk.Label(parent, text=label + ':').grid(row=row, column=0, sticky=tk.W, pady=4)
        spin = ttk.Spinbox(parent, from_=low, to=high, width=15)
        spin.grid(row=row, column=1, sticky=tk.EW, padx=(12, 0), pady=4)
        spin.set(f'{value:g}')
        self.fields[key] = spin

    def chosen(self, key):
        current = self.fields[key].current()
        if current < 0:
            raise ValueError(f'Choose {key.replace("_", " ")}')
        return self.options[key][current]

    def update_artillery(self, event=None):
        cls = self.chosen('unit_class')
        self.has_guns = cls in (4, 5) or cls == 6 and self.chosen('type') in (36, 37, 38)
        if event and cls == 6 and self.has_guns and 'bombardment' not in self.original:
            try:
                data, index = edit_definition(self.roster.to_bytes(), self.source_side,
                    self.unit['side_index'], {'type': self.chosen('type')}, return_index=True)
                defaults = definition(UnitRoster(data), self.source_side, index)
                for key in ARTILLERY_FIELDS:
                    self.fields[key].set(f'{defaults[key]:g}')
            except ValueError as exc:
                self.gun_hint.config(text=str(exc))
        if self.has_guns:
            self.guns.grid()
        else:
            self.guns.grid_remove()

    def update_side(self, event=None):
        changed = self.chosen('side') != self.source_side
        if self.original['unit_class'] in (5, 6):
            self.transfer_hint.config(text='Category changes keep the name, arrival, aircraft counts and existing bombardment ratings. '
                'Flight/mission profiles follow the new role. New combat squadrons receive native bombardment defaults. '
                'Pictures are shared by category; choose them under Category artwork on Units.')
            return
        self.transfer_hint.config(text=(
            'Transferred ground units start inactive. Place them on Map, then assign their HQ in HQ Organization.'
            if changed else 'Nationality controls game rules; side controls allegiance. The selected chit is kept.'))

    def submit(self):
        try:
            values = {key: self.chosen(key) for key in self.options if key != 'side'}
            values.update({key: self.fields[key].get() for key in ('movement_allowance', 'stacking_size')})
            if self.has_guns:
                values.update({key: self.fields[key].get() for key in ARTILLERY_FIELDS})
            if not self.app.change_unit_definition(self.unit, values, self.chosen('side')):
                return
        except ValueError as exc:
            messagebox.showerror('Cannot change definition', str(exc), parent=self)
            return
        self.destroy()
