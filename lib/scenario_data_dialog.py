"""Scenario Settings controls for native leaders, garrisons and logistics."""
import struct
import tkinter as tk
from tkinter import ttk, messagebox

from lib.conditions_dialog import entry, table
from lib.scenario_data import (leaders, edit_leader, garrisons, edit_garrison,
    depots, edit_depot, REPLACEMENT_TYPES, replacement_schedule,
    replacement_pool, set_replacements)
from lib.scenario_rules import date_label, turns_per_day
from lib.unit_roster import UnitRoster, short
from lib.unit_reader import decode_record
from lib.unit_definitions import headquarters, NATIONALITIES
from lib.form_drafts import FormDraft

SIDES = ('Allied', 'Axis')


class DataEditor(ttk.Frame):
    def __init__(self, parent, app, kind):
        super().__init__(parent, padding=10)
        self.app, self.kind, self.roster = app, kind, None
        self.side = tk.StringVar(value=SIDES[0])
        if kind != 'garrisons':
            line = ttk.Frame(self)
            line.pack(fill='x')
            ttk.Label(line, text='Side').pack(side='left', padx=(0, 8))
            combo = ttk.Combobox(line, textvariable=self.side, values=SIDES, state='readonly', width=12)
            combo.pack(side='left')
            combo.bind('<<ComboboxSelected>>', lambda e: self.load(self.roster))
        if kind == 'replacements':
            self.build_replacements()
            self.pool_draft = FormDraft(self, 'Replacement pool', self.pool, app._draft_changed,
                                       self.prepare_pool)
            self.days_draft = FormDraft(self, 'Replacement arrivals',
                dict(first=self.first, last=self.last, **{str(k): v for k, v in self.quantities.items()}),
                app._draft_changed, self.prepare_days)
            self.draft_forms = [self.pool_draft, self.days_draft]
            return
        columns = {
            'leaders': dict(name='Leader', unit='Attached unit', home='Home HQ', attack='Attack shifts', defense='Defense shifts'),
            'garrisons': dict(number='Garrison', x='Hex X', y='Hex Y', radius='Radius', hqs='Assigned HQs'),
            'depots': dict(number='Depot', hex='Hex', stock='Stock', capacity='Capacity', type='Resupply', distribute='Supplies nearby HQs'),
        }[kind]
        self.tree = table(self, columns)
        self.tree.configure(selectmode='browse')
        self.tree.bind('<Double-1>', lambda e: self.edit())
        buttons = ttk.Frame(self)
        buttons.pack(fill='x')
        noun = {'leaders': 'Leader', 'garrisons': 'Garrison', 'depots': 'Depot'}[kind]
        for title, callback in ((f'Add {noun}', lambda: self.edit(True)),
                                (f'Edit {noun}', self.edit), (f'Remove {noun}', self.remove)):
            ttk.Button(buttons, text=title, command=callback).pack(side='left', padx=(0, 6))
        if kind == 'leaders':
            ttk.Button(buttons, text='Portrait…', command=self.choose_portrait).pack(side='left', padx=6)
        text = {'leaders': 'Leaders attach to one ground unit. A formation restriction limits transfers to the home HQ and its subordinates.',
                'garrisons': 'Assign HQs to a center hex and radius. Their units use this area for garrison orders.',
                'depots': 'The reserve entry stays off map. Map depots can receive land supply or airdrops and supply nearby HQs.'}[kind]
        ttk.Label(self, text=text, wraplength=950).pack(anchor='w', pady=10)

    @property
    def side_index(self):
        return SIDES.index(self.side.get())

    def prepare_pool(self, data, context, values, changes):
        pool = replacement_pool(UnitRoster(data), context)
        quantities = {key: changes.get(key, pool[key]) for key in self.pool}
        return set_replacements(data, context, quantities)

    def prepare_days(self, data, context, values, changes):
        return set_replacements(data, context[0], {k: values[str(k)] for k in REPLACEMENT_TYPES},
                                values['first'], values['last'])

    def load_days(self, context):
        side, first, last = context
        with self.days_draft.load(context):
            self.first.set(first)
            self.last.set(last)
            rows = replacement_schedule(self.roster, side)
            row = rows[min(max(first-1, 0), len(rows)-1)]
            for key, var in self.quantities.items():
                var.set(row[key])

    def apply(self, function, *args):
        if not self.roster:
            return False
        try:
            data = function(self.app._staged_data(include_briefings=False), *args)
            label = {'leaders': 'Edit leaders', 'replacements': 'Edit replacements',
                     'garrisons': 'Edit garrisons', 'depots': 'Edit depots'}[self.kind]
            presentation = None
            if function is edit_leader and len(args) == 2:
                from lib.presentation_artwork import remove_leader_portrait
                presentation = remove_leader_portrait(self.app.presentation_artwork, *args)
            self.app.apply_scenario_rules(data, label, presentation=presentation)
            return True
        except (ValueError, IndexError) as exc:
            messagebox.showerror('Cannot Apply Settings', str(exc), parent=self)
            return False

    def load(self, roster):
        self.roster = roster
        if roster is None:
            return
        self.tree.delete(*self.tree.get_children())
        side = self.side_index
        if self.kind == 'replacements':
            rows = replacement_schedule(roster, side)
            start = struct.unpack_from('<i', roster.blocks['calendar'], 4)[0]
            per_day = turns_per_day(roster)
            for i, row in enumerate(rows):
                self.tree.insert('', 'end', iid=str(i+1), values=(i+1,
                    date_label(start+i*per_day, per_day).split(' ·')[0], *(row[k] for k in REPLACEMENT_TYPES)))
            with self.pool_draft.load(side):
                for key, var in self.pool.items():
                    var.set(replacement_pool(roster, side)[key])
            context = self.days_draft.context
            if not context or context[0] != side or not 1 <= context[1] <= context[2] <= len(rows):
                context = (side, 1, 1)
            self.load_days(context)
            return
        hqs = {(s, hq['id']): hq['name'] for s in (0, 1) for hq in headquarters(roster, s)}
        if self.kind == 'leaders':
            self.rows = leaders(roster, side)
            for i, item in enumerate(self.rows):
                unit = item['unit']
                name = (decode_record(roster.records[side][unit])['name']
                        if 0 <= unit < len(roster.records[side]) else f'Missing unit {unit}')
                self.tree.insert('', 'end', iid=str(i), values=(item['name'], name,
                    hqs.get((side, item['home']), f"HQ {item['home']}"), item['attack'], item['defense']))
        elif self.kind == 'garrisons':
            self.rows = garrisons(roster)
            for i, item in enumerate(self.rows):
                self.tree.insert('', 'end', iid=str(i), values=(i+1, item['x'], item['y'], item['radius'],
                    ', '.join(f'{SIDES[s]}: {hqs[s,h]}' for s, h in item['hqs'])))
        else:
            self.rows = depots(roster, side)
            for i, item in enumerate(self.rows):
                self.tree.insert('', 'end', iid=str(i), values=(i if i else 'Reserve',
                    f"({item['x']}, {item['y']})" if i else 'Off map', item['stock'], item['capacity'],
                    ('Land' if item['land'] else 'Airdrop') + (' · Captured' if item['captured'] else ''),
                    'Yes' if item['distribute'] else 'No'))

    def remove(self):
        if self.tree.selection():
            index = int(self.tree.selection()[0])
            if self.kind == 'garrisons':
                self.apply(edit_garrison, index)
            else:
                self.apply(edit_leader if self.kind == 'leaders' else edit_depot, self.side_index, index)

    def choose_portrait(self):
        if self.tree.selection():
            key = f'leader_{self.side_index}_{self.tree.selection()[0]}'
            panel = self.app.artwork_panel
            panel.refresh()
            panel.tree.selection_set(key)
            panel.tree.see(key)
            panel.select_slot()
            self.app.notebook.select(panel)

    def edit(self, new=False):
        if self.roster is None or (not new and not self.tree.selection()):
            return
        index = None if new else int(self.tree.selection()[0])
        side = self.side_index
        x, y = self.app.map_viewer.selected_hex or (0, 0)
        item = {} if new else self.rows[index]
        hqs = [h for h in headquarters(self.roster, side) if not h['deleted']]
        if self.kind == 'leaders' and not hqs:
            messagebox.showerror('Leader Needs an HQ', 'Add an HQ on Units first.', parent=self)
            return
        dialog = tk.Toplevel(self)
        dialog.title(('Add ' if new else 'Edit ') + {'leaders': 'Leader', 'garrisons': 'Garrison', 'depots': 'Depot'}[self.kind])
        dialog.transient(self.winfo_toplevel())
        form = ttk.Frame(dialog, padding=15)
        form.pack(fill='both', expand=True)
        form.columnconfigure(1, weight=1)
        values, selections = {}, {}

        def field(key, label, default, choices=None):
            values[key] = entry(form, label, item.get(key, default), len(values), choices)

        def check(key, label, default):
            var = tk.IntVar(value=int(item.get(key, default)))
            ttk.Checkbutton(form, text=label, variable=var).grid(row=len(values), column=0, columnspan=2, sticky='w', pady=5)
            values[key] = var

        if self.kind == 'leaders':
            field('name', 'Name', 'New leader')
            units = {i: decode_record(u) for i, u in enumerate(self.roster.records[side][:self.roster.count(0x240, side)])
                     if u[0x76] != 4 and not decode_record(u)['deleted']}
            unit_choices = {f"{i}: {u['name']}": i for i, u in units.items()}
            home_choices = {f"{h['id']}: {h['name']}": h['id'] for h in hqs}
            for key, label, choices, default in (('unit', 'Attached unit', unit_choices, hqs[0]['index']),
                                                ('home', 'Home HQ', home_choices, hqs[0]['id'])):
                chosen = next((k for k, v in choices.items() if v == item.get(key, default)), '')
                values[key] = entry(form, label, chosen, len(values), tuple(choices))
                selections[key] = choices
            field('attack', 'Attack odds shifts', 0)
            field('defense', 'Defense odds shifts', 0)
            check('restricted', 'Restrict transfers to home HQ’s formation', True)
            field('counter', 'Leader chit number', short(self.roster.records[side][hqs[0]['index']], 0x56))
            values['nationality'] = entry(form, 'Nationality', NATIONALITIES[item.get('nationality', side)],
                                          len(values), NATIONALITIES)
            selections['nationality'] = {v: k for k, v in enumerate(NATIONALITIES)}

            def choose_chit():
                from lib.scenario_dialogs import CounterDialog
                try:
                    selected = int(values['counter'].get())
                except ValueError:
                    selected = 0
                resource = short(self.roster.header, 0x238) + side
                unit = dict(side=SIDES[side], counter_resource=resource,
                            counter_bitmap=self.app.counter_artwork.get(resource))
                CounterDialog(dialog, unit, selected, values['counter'].set)
            ttk.Button(form, text='Choose Chit…', command=choose_chit).grid(row=len(values), column=1, sticky='e', pady=6)
            next_row = len(values)+1
        elif self.kind == 'garrisons':
            field('x', 'Center X', x)
            field('y', 'Center Y', y)
            field('radius', 'Radius (hexes)', 5)
            ttk.Label(form, text='Assigned HQs (select any number)').grid(row=3, column=0, columnspan=2, sticky='w', pady=6)
            listing = tk.Listbox(form, selectmode='multiple', exportselection=False, width=58, height=12)
            listing.grid(row=4, column=0, columnspan=2, sticky='nsew')
            bar = ttk.Scrollbar(form, command=listing.yview)
            bar.grid(row=4, column=2, sticky='ns')
            listing.configure(yscrollcommand=bar.set)
            choices = []
            for s in (0, 1):
                for h in headquarters(self.roster, s):
                    if h['deleted']:
                        continue
                    choices.append((s, h['id']))
                    listing.insert('end', f"{SIDES[s]} · {h['id']}: {h['name']}")
                    if choices[-1] in item.get('hqs', []):
                        listing.selection_set(len(choices)-1)
            next_row = 5
        else:
            field('stock', 'Current stock', 0)
            field('capacity', 'Stock capacity', 10000)
            if index != 0:
                field('x', 'Hex X', x)
                field('y', 'Hex Y', y)
                check('land', 'Receives land supply (off = airdrop depot)', True)
                check('distribute', 'Supplies nearby HQs', True)
                check('captured', 'Initially captured', False)
            next_row = len(values)

        def save():
            record = {k: v.get() for k, v in values.items()}
            for key, choices_by_name in selections.items():
                if record[key] not in choices_by_name:
                    messagebox.showerror('Choose an Assignment', f'Choose {key} from the list.', parent=dialog)
                    return
                record[key] = choices_by_name[record[key]]
            if self.kind == 'garrisons':
                record['hqs'] = [choices[i] for i in listing.curselection()]
                saved = self.apply(edit_garrison, index, record)
            else:
                if self.kind == 'leaders':
                    resource = short(self.roster.header, 0x238) + side
                    saved = self.apply(edit_leader, side, index, record, self.app.counter_artwork.get(resource))
                else:
                    saved = self.apply(edit_depot, side, index, record)
            if saved:
                dialog.destroy()

        ttk.Button(form, text='Cancel', command=dialog.destroy).grid(row=next_row, column=0, pady=(12, 0))
        ttk.Button(form, text='Apply', command=save).grid(row=next_row, column=1, pady=(12, 0))
        dialog.bind('<Escape>', lambda e: dialog.destroy())
        dialog.grab_set()

    def build_replacements(self):
        pool = ttk.LabelFrame(self, text='Starting replacement pool', padding=8)
        pool.pack(fill='x', pady=8)
        self.pool, self.quantities = {}, {}
        for column, (key, name) in enumerate(REPLACEMENT_TYPES.items()):
            ttk.Label(pool, text=name).grid(row=0, column=column, padx=4)
            var = tk.StringVar(value='0')
            ttk.Spinbox(pool, from_=0, to=255, textvariable=var, width=8).grid(row=1, column=column, padx=4)
            self.pool[key] = var
        ttk.Button(pool, text='Apply Pool', command=self.apply_pool).grid(row=2, column=0, columnspan=2, sticky='w', pady=6)
        ttk.Button(pool, text='Revert Pool', command=lambda: self.pool_draft.revert()).grid(
            row=2, column=2, columnspan=2, sticky='w', pady=6)
        self.tree = table(self, dict(day='Day', date='Date', **{str(k): v for k, v in REPLACEMENT_TYPES.items()}))
        for key in self.tree['columns']:
            self.tree.column(key, width=90 if key != 'date' else 130, minwidth=45)
        self.tree.bind('<<TreeviewSelect>>', self.select_day)
        form = ttk.LabelFrame(self, text='Daily arrivals', padding=8)
        form.pack(fill='x')
        self.first, self.last = tk.StringVar(value='1'), tk.StringVar(value='1')
        line = ttk.Frame(form)
        line.pack(fill='x', pady=5)
        for label, var in (('First day', self.first), ('Last day', self.last)):
            ttk.Label(line, text=label).pack(side='left', padx=4)
            ttk.Entry(line, textvariable=var, width=6).pack(side='left', padx=4)
        grid = ttk.Frame(form)
        grid.pack(anchor='w')
        for column, (key, name) in enumerate(REPLACEMENT_TYPES.items()):
            ttk.Label(grid, text=name).grid(row=0, column=column, padx=4)
            var = tk.StringVar(value='0')
            ttk.Spinbox(grid, from_=0, to=255, textvariable=var, width=8).grid(row=1, column=column, padx=4)
            self.quantities[key] = var
        ttk.Button(form, text='Apply to Days', command=self.apply_days).pack(anchor='w', pady=8)
        ttk.Button(form, text='Revert Form', command=lambda: self.days_draft.revert()).pack(anchor='w')

    def select_day(self, event=None):
        if self.tree.selection():
            days = sorted(map(int, self.tree.selection()))
            self.load_days((self.side_index, days[0], days[-1]))

    def apply_pool(self):
        if self.apply(set_replacements, self.side_index, {k: v.get() for k, v in self.pool.items()}):
            self.pool_draft.accept()
            return True
        return False

    def apply_days(self):
        if self.apply(set_replacements, self.side_index, {k: v.get() for k, v in self.quantities.items()},
                      self.first.get(), self.last.get()):
            self.days_draft.accept()
            return True
        return False
