"""Weather and supply controls for Scenario Settings."""
import struct
import tkinter as tk
from tkinter import ttk, messagebox

from lib.scenario_conditions import (WEATHER_NAMES, weather_sequence, set_weather,
    supply_groups, set_supply_group, daily_supply, set_daily_supply)
from lib.scenario_rules import scenario_dates, date_label, turns_per_day
from lib.scenario_data import (ground_conditions, set_ground_conditions,
                               add_supply_group, remove_supply_group)
from lib.form_drafts import FormDraft
from lib.unit_roster import UnitRoster


def table(parent, columns, height=10):
    frame = ttk.Frame(parent)
    frame.pack(fill='both', expand=True, pady=6)
    tree = ttk.Treeview(frame, columns=tuple(columns), show='headings', height=height)
    for key, label in columns.items():
        tree.heading(key, text=label)
        tree.column(key, width=150, stretch=True)
    scroll = ttk.Scrollbar(frame, command=tree.yview)
    tree.configure(yscrollcommand=scroll.set)
    scroll.pack(side='right', fill='y')
    tree.pack(fill='both', expand=True)
    return tree


def entry(parent, label, value, row, choices=None):
    ttk.Label(parent, text=label).grid(row=row, column=0, sticky='w', padx=5, pady=5)
    var = tk.StringVar(value=value)
    widget = (ttk.Entry(parent, textvariable=var) if choices is None else
              ttk.Combobox(parent, textvariable=var, values=choices, state='readonly'))
    widget.grid(row=row, column=1, sticky='ew', padx=5, pady=5)
    return var


class ConditionsEditor(ttk.Frame):
    def __init__(self, parent, app, kind):
        super().__init__(parent, padding=10)
        self.app, self.kind, self.roster = app, kind, None
        if kind == 'weather':
            ground = ttk.LabelFrame(self, text='Initial ground conditions (game units)', padding=8)
            ground.pack(fill='x', pady=(0, 8))
            self.ground = {}
            for column, name in enumerate(('Snow', 'Ice', 'Wetness')):
                ttk.Label(ground, text=name).grid(row=0, column=column*2, padx=5)
                var = tk.StringVar(value='0')
                ttk.Entry(ground, textvariable=var, width=10).grid(row=0, column=column*2+1, padx=5)
                self.ground[name] = var
            ttk.Button(ground, text='Apply Ground Conditions', command=self.apply_ground).grid(row=0, column=6, padx=8)
            ttk.Button(ground, text='Revert', command=lambda: self.ground_draft.revert()).grid(row=0, column=7)
            self.mode = ttk.Label(self)
            self.mode.pack(anchor='w')
            self.tree = table(self, dict(turn='Turn', date='Date', temperature='Temperature (°F)', weather='Weather'))
            form = ttk.Frame(self)
            form.pack(anchor='w')
            self.first = entry(form, 'First turn', '1', 0)
            self.last = entry(form, 'Last turn', '1', 1)
            self.temperature = entry(form, 'Temperature (°F)', '65', 2)
            self.code = entry(form, 'Weather', WEATHER_NAMES[0], 3, WEATHER_NAMES)
            ttk.Button(form, text='Apply Weather to Turns', command=self.apply_weather).grid(
                row=4, column=0, columnspan=2, pady=8)
            self.tree.bind('<<TreeviewSelect>>', self.select_weather)
        else:
            groups = ttk.LabelFrame(self, text='Supply stocks and entry hexes', padding=8)
            groups.pack(fill='both', expand=True)
            self.tree = table(groups, dict(side='Side', group='Group', stock='Initial stock', hexes='Entry hexes'), 5)
            self.tree.bind('<Double-1>', lambda e: self.edit_stock())
            controls = ttk.Frame(groups)
            controls.pack(fill='x')
            self.group_side = tk.StringVar(value='Allied')
            ttk.Combobox(controls, textvariable=self.group_side, values=('Allied', 'Axis'),
                         state='readonly', width=10).pack(side='left', padx=(0, 5))
            for label, command in (('Add Group', self.add_group), ('Edit Stock / Entry Hexes', self.edit_stock),
                                    ('Remove Group', self.remove_group)):
                ttk.Button(controls, text=label, command=command).pack(side='left', padx=3)
            ttk.Label(groups, text='The first group provides entry hexes. Additional groups are reserve stock pools; '
                      'daily delivery is added to each group.', wraplength=950).pack(anchor='w', pady=6)
            days = ttk.LabelFrame(self, text='Daily supplies', padding=8)
            days.pack(fill='both', expand=True, pady=(10, 0))
            self.daily = table(days, dict(day='Day', date='Date', allied='Allied', axis='Axis'), 5)
            self.daily.bind('<<TreeviewSelect>>', self.select_day)
            form = ttk.Frame(days)
            form.pack(anchor='w')
            self.first = entry(form, 'First day', '1', 0)
            self.last = entry(form, 'Last day', '1', 1)
            self.allied = entry(form, 'Allied daily supply', '1250', 2)
            self.axis = entry(form, 'Axis daily supply', '1250', 3)
            ttk.Button(form, text='Apply Daily Supply', command=self.apply_daily).grid(row=4, column=0, columnspan=2, pady=8)
        fields = dict(first=self.first, last=self.last)
        if kind == 'weather':
            fields.update(temperature=self.temperature, code=self.code)
            self.ground_draft = FormDraft(self, 'Initial ground conditions', self.ground,
                app._draft_changed, self.prepare_ground)
        else:
            fields.update(allied=self.allied, axis=self.axis)
        self.range_draft = FormDraft(self, 'Weather' if kind == 'weather' else 'Daily supply',
            fields, app._draft_changed, self.prepare_range)
        self.draft_forms = ([self.ground_draft] if kind == 'weather' else []) + [self.range_draft]
        ttk.Button(form, text='Revert Form', command=self.range_draft.revert).grid(row=4, column=2, padx=8)

    def prepare_ground(self, data, context, values, changes):
        values = dict(zip(self.ground, ground_conditions(UnitRoster(data)))) | changes
        return set_ground_conditions(data, *(values[k] for k in self.ground))

    def prepare_range(self, data, context, values, changes):
        if self.kind == 'weather':
            if values['code'] not in WEATHER_NAMES:
                raise ValueError('Choose a weather condition.')
            return set_weather(data, values['first'], values['last'], values['temperature'],
                               WEATHER_NAMES.index(values['code']))
        return set_daily_supply(data, values['first'], values['last'], values['allied'], values['axis'])

    def load_range(self, context):
        first, last = context
        with self.range_draft.load(context):
            self.first.set(first)
            self.last.set(last)
            if self.kind == 'weather':
                temp, code = self.sequence[min(max(first-1, 0), len(self.sequence)-1)]
                self.temperature.set(temp)
                self.code.set(WEATHER_NAMES[code] if code < len(WEATHER_NAMES) else '')
            else:
                days = daily_supply(self.roster)
                allied, axis = days[min(max(first-1, 0), len(days)-1)]
                self.allied.set(allied)
                self.axis.set(axis)

    def load(self, roster):
        self.roster = roster
        per_day = turns_per_day(roster)
        self.tree.delete(*self.tree.get_children())
        if self.kind == 'weather':
            with self.ground_draft.load('ground'):
                for var, value in zip(self.ground.values(), ground_conditions(roster)):
                    var.set(value)
            self.sequence = weather_sequence(roster)
            start, _ = scenario_dates(roster)
            self.mode.config(text='Authored weather' if roster.header[0x1227] == 0 else
                             'Generated weather — applying turns switches to authored weather')
            for i, (temp, code) in enumerate(self.sequence):
                self.tree.insert('', 'end', iid=str(i+1), values=(i+1, date_label(start+i, per_day), temp,
                    WEATHER_NAMES[code] if code < len(WEATHER_NAMES) else f'Code {code}'))
        else:
            for side in (0, 1):
                for group, item in enumerate(supply_groups(roster, side)):
                    self.tree.insert('', 'end', iid=f'{side}:{group}', values=(('Allied','Axis')[side], group+1,
                        item['stock'], ', '.join(f'({x}, {y})' for x,y,_ in item['entries'])))
            self.daily.delete(*self.daily.get_children())
            start = struct.unpack_from('<i', roster.blocks['calendar'], 4)[0]
            for i, (allied, axis) in enumerate(daily_supply(roster)):
                self.daily.insert('', 'end', iid=str(i+1), values=(i+1, date_label(start+i*per_day, per_day).split(' ·')[0], allied, axis))
        count = len(self.sequence) if self.kind == 'weather' else len(daily_supply(roster))
        context = self.range_draft.context or (1, 1)
        self.load_range(context if 1 <= context[0] <= context[1] <= count else (1, 1))

    def select_weather(self, event=None):
        selected = self.tree.selection()
        if selected:
            turns = sorted(map(int, selected))
            self.load_range((turns[0], turns[-1]))

    def select_day(self, event=None):
        selected = self.daily.selection()
        if selected:
            days = sorted(map(int, selected))
            self.load_range((days[0], days[-1]))

    def apply(self, function, *args, description=None):
        if not self.roster:
            return False
        try:
            result = function(self.app._staged_data(include_briefings=False), *args)
            labels = {set_weather: 'Edit weather sequence', set_ground_conditions: 'Edit initial snow, ice and wetness',
                      set_daily_supply: 'Edit daily supply', set_supply_group: 'Edit supply stocks and entry hexes',
                      add_supply_group: 'Add supply group', remove_supply_group: 'Remove supply group'}
            self.app.apply_scenario_rules(result, description or labels.get(function, 'Edit supply groups'))
            return True
        except (ValueError, IndexError) as exc:
            messagebox.showerror('Cannot Apply Settings', str(exc), parent=self)
            return False

    def apply_weather(self):
        if self.code.get() not in WEATHER_NAMES:
            messagebox.showerror('Cannot Apply Weather', 'Choose a weather condition.', parent=self)
            return False
        if self.apply(set_weather, self.first.get(), self.last.get(), self.temperature.get(), WEATHER_NAMES.index(self.code.get())):
            self.range_draft.accept()
            return True
        return False

    def apply_ground(self):
        if self.apply(set_ground_conditions, *(var.get() for var in self.ground.values())):
            self.ground_draft.accept()
            return True
        return False

    def add_group(self):
        side = ('Allied', 'Axis').index(self.group_side.get())
        self.edit_stock(new=True, side=side)

    def remove_group(self):
        if self.tree.selection():
            side, group = map(int, self.tree.selection()[0].split(':'))
            self.apply(remove_supply_group, side, group)

    def apply_daily(self):
        if self.apply(set_daily_supply, self.first.get(), self.last.get(), self.allied.get(), self.axis.get()):
            self.range_draft.accept()
            return True
        return False

    def edit_stock(self, new=False, side=None):
        if not self.roster or (not new and not self.tree.selection()):
            return
        if new:
            group = self.roster.count(0x25c, side)
            item = dict(stock=0, entries=[])
        else:
            side, group = map(int, self.tree.selection()[0].split(':'))
            item = supply_groups(self.roster, side)[group]
        rows = list(item['entries'])
        dialog = tk.Toplevel(self)
        dialog.title(f'{("Allied", "Axis")[side]} supply group {group+1}')
        dialog.transient(self.winfo_toplevel())
        body = ttk.Frame(dialog, padding=12)
        body.pack(fill='both', expand=True)
        form = ttk.Frame(body); form.pack(anchor='w')
        stock = entry(form, 'Initial stock', item['stock'], 0)
        listing = table(body, dict(x='Hex X', y='Hex Y', state='State'), 8)
        controls = ttk.Frame(body); controls.pack(anchor='w')
        point = self.app.map_viewer.selected_hex or (0, 0)
        x = entry(controls, 'Hex X', point[0], 0)
        y = entry(controls, 'Hex Y', point[1], 1)
        enabled = tk.BooleanVar(value=True)
        ttk.Checkbutton(controls, text='Entry available', variable=enabled).grid(row=2, column=0, columnspan=2, sticky='w')
        def refresh():
            listing.delete(*listing.get_children())
            for i, (hx,hy,flag) in enumerate(rows):
                listing.insert('', 'end', iid=str(i), values=(hx,hy,'Unavailable' if flag else 'Available'))
        def select(event=None):
            if listing.selection():
                hx,hy,flag = rows[int(listing.selection()[0])]
                x.set(hx); y.set(hy); enabled.set(not flag)
        def update(add):
            try:
                row = (int(x.get()), int(y.get()), int(not enabled.get()))
                if add: rows.append(row)
                elif listing.selection(): rows[int(listing.selection()[0])] = row
                refresh()
            except ValueError:
                messagebox.showerror('Invalid Hex', 'Coordinates must be integers', parent=dialog)
        def remove():
            for i in sorted(map(int, listing.selection()), reverse=True): rows.pop(i)
            refresh()
        listing.bind('<<TreeviewSelect>>', select)
        buttons = ttk.Frame(body); buttons.pack(fill='x', pady=8)
        for title, command in (('Add Entry', lambda: update(True)), ('Update Entry', lambda: update(False)), ('Remove Entry', remove)):
            ttk.Button(buttons, text=title, command=command).pack(side='left', padx=3)
        def save():
            def change(data):
                if new:
                    data = add_supply_group(data, side)
                return set_supply_group(data, side, group, stock.get(), rows)
            if self.apply(change, description=f'{"Add" if new else "Edit"} {("Allied", "Axis")[side]} supply group {group+1}'):
                dialog.destroy()
        ttk.Button(body, text='Apply Stock and Entries', command=save).pack(side='right', pady=8)
        ttk.Button(body, text='Cancel', command=dialog.destroy).pack(side='right', padx=8)
        refresh()
        dialog.grab_set()


class BattlePlanEditor(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, padding=10)
        self.app, self.roster = app, None
        self.tree = table(self, dict(side='Side', group='HQ battlegroup', first='First turn', last='Last turn',
                                    order='Action / orders', goal='Goal', condition='Condition', priority='Priority'))
        for key, width in dict(side=80, group=160, first=65, last=65, order=150,
                               goal=80, condition=285, priority=65).items():
            self.tree.column(key, width=width, minwidth=40)
        self.tree.bind('<Double-1>', lambda e:self.edit())
        buttons=ttk.Frame(self);buttons.pack(fill='x')
        self.buttons=[]
        for label, command in (('Add Phase',lambda:self.edit(True)),('Edit Phase',self.edit),('Remove Phase',self.remove)):
            button=ttk.Button(buttons,text=label,command=command,state='disabled')
            button.pack(side='left',padx=4)
            self.buttons.append(button)
        self.empty=ttk.Label(self)
        self.empty.pack(anchor='w',pady=8)
        ttk.Label(self, text='For HQ orders, the highest-priority matching plan wins. Releases and public messages each fire once. '
                  'Conditions test objective control or casualty points lost.',
                  wraplength=1000).pack(anchor='w', pady=4)

    def load(self, roster):
        from lib.battle_plans import battle_plans, ORDERS, condition_label
        from lib.scenario_rules import objectives
        self.roster=roster
        self.plans=battle_plans(roster)
        self.hqs={}
        for side in (0,1):
            for record in roster.records[side]:
                if record[0x76]==7:
                    group=struct.unpack_from('<i',record,4)[0]
                    self.hqs[side,group]=record[0x92:].split(b'\0')[0].decode('cp437')
        self.buttons[0].config(state='normal')
        for button in self.buttons[1:]:
            button.config(state='normal' if self.plans else 'disabled')
        self.empty.config(text='' if self.hqs else 'Add an HQ on Units to issue orders or release reinforcements; public messages need no HQ.')
        self.tree.delete(*self.tree.get_children())
        for i,p in enumerate(self.plans):
            self.tree.insert('','end',iid=str(i),values=(('Allied','Axis')[p['side']],
                self.hqs.get((p['side'],p['group']),'' if p.get('action')=='message' else f"HQ {p['group']}"),p['first'],p['last'],
                (ORDERS.get(p['order'],p['order']) if p.get('action','order')=='order' else
                 'Release reinforcements' if p['action']=='release' else 'Public message'),
                f"({p['x']}, {p['y']})" if p.get('action','order')=='order' else '',
                condition_label(p, objectives(roster)), p.get('priority', 0)))

    def apply(self, plans):
        from lib.battle_plans import set_battle_plans
        try:
            self.app.apply_scenario_rules(set_battle_plans(self.app._staged_data(include_briefings=False),plans),
                                          'Edit battle plans and conditions')
            return True
        except ValueError as exc:
            messagebox.showerror('Cannot Apply Battle Plan',str(exc),parent=self)
            return False

    def remove(self):
        rows=[p for i,p in enumerate(self.plans) if str(i) not in self.tree.selection()]
        if self.tree.selection():self.apply(rows)

    def edit(self, new=False):
        from lib.battle_plans import ORDERS, CONDITIONS, DEFAULT_EVENT
        from lib.scenario_rules import objectives
        if not self.roster:return
        if not new and not self.tree.selection():return
        index=None if new else int(self.tree.selection()[0])
        side,group=next(iter(self.hqs),(0,-1))
        x,y=self.app.map_viewer.selected_hex or (0,0)
        p=dict(side=side,group=group,first=1,last=1,order=1,x=x,y=y) if new else self.plans[index]
        p = {**DEFAULT_EVENT, **p}
        if new and not self.hqs:p['action']='message'
        from lib.event_rules import ACTIONS
        from lib.event_dialog import ExpressionDialog
        from lib.battle_plans import condition_label
        expression = [p.get('expression')]
        dialog=tk.Toplevel(self);dialog.title('Battle Plan / Event');dialog.transient(self.winfo_toplevel())
        form=ttk.Frame(dialog,padding=15);form.pack(fill='both',expand=True)
        form.columnconfigure(1, weight=1, minsize=310)
        choices={f'{("Allied","Axis")[s]} · {g+1}: {name}':(s,g) for (s,g),name in self.hqs.items()}
        if not choices:choices={'No HQ':(0,-1)}
        selected=next((k for k,v in choices.items() if v==(p['side'],p['group'])),next(iter(choices)))
        hq=entry(form,'HQ battlegroup',selected,0,tuple(choices))
        action=entry(form,'Action',ACTIONS[p.get('action','order')],1,tuple(ACTIONS.values()))
        values={}
        for row,(key,label) in enumerate((('first','First turn'),('last','Last turn'),('x','Goal X'),('y','Goal Y')),2):
            values[key]=entry(form,label,p[key],row)
        trigger = entry(form, 'Condition', CONDITIONS[p['trigger']], 6, tuple(CONDITIONS.values()))
        trigger_side = entry(form, 'Condition side', ('Allied', 'Axis')[p['trigger_side']], 7, ('Allied', 'Axis'))
        objective_choices = {f"{i+1}: {o['name']} ({o['x']}, {o['y']})": i
                             for i, o in enumerate(objectives(self.roster))}
        selected_objective = next((k for k, v in objective_choices.items() if v == p['objective']),
                                  next(iter(objective_choices), ''))
        objective = entry(form, 'Objective', selected_objective, 8, tuple(objective_choices))
        values['threshold'] = entry(form, 'Casualty points lost (at least)', p['threshold'] or 1, 9)
        values['priority'] = entry(form, 'Priority (0–255; higher wins)', p['priority'], 10)
        explanation = ttk.Label(form, wraplength=450)
        explanation.grid(row=11, column=0, columnspan=2, sticky='w', pady=10)

        def condition_changed(*_):
            kind = next(k for k, label in CONDITIONS.items() if label == trigger.get())
            for row, enabled, state in ((7, kind != 0, 'readonly'), (8, kind == 1, 'readonly'),
                                         (9, kind == 2, 'normal')):
                form.grid_slaves(row=row, column=1)[0].configure(state=state if enabled else 'disabled')
            explanation.config(text={0: 'Timed fallback: applies whenever this is the highest matching priority.',
                1: 'Tests whether the selected side controls this objective. Recapture can deactivate an order unless Keep active is enabled.',
                2: 'Uses the game’s cumulative casualty score for losses suffered by the selected side. '
                   'Objective points are excluded; casualty scoring weights affect this threshold.'}[kind])
            if action.get()!=ACTIONS['order']:
                explanation.config(text='Fires once during the turn range, when the conditions match. '
                                   'With Always, it fires at the first eligible check. Priority sets the order of simultaneous actions.')
            if kind and values['priority'].get() == '0':
                values['priority'].set('10')

        condition_changed()
        values['priority'].set(p['priority'])
        trigger.trace_add('write', condition_changed)
        details=ttk.Notebook(form)
        details.grid(row=0,column=2,rowspan=13,sticky='n',padx=(20,0))
        advanced=ttk.Frame(details,padding=12);details.add(advanced,text='Conditions')
        action_page=ttk.Frame(details,padding=12);details.add(action_page,text='Action details')
        order=entry(action_page,'HQ orders',ORDERS[p['order']],0,tuple(ORDERS.values()))
        message=entry(action_page,'Public message',p.get('message',''),1)
        hold=tk.BooleanVar(value=p.get('hold',True))
        hold_button=ttk.Checkbutton(action_page,text='Hold pending reinforcements until released',variable=hold)
        hold_button.grid(row=2,column=0,columnspan=2,sticky='w',pady=10)
        ttk.Label(action_page,text='Release affects pending ground members directly assigned to the HQ, including its HQ unit. '
                  'Arrival locations are preserved; units enter at the next normal arrival phase. Held units stay unavailable if '
                  'the condition never matches. Deployed units and aircraft/naval support are unaffected.\n\n'
                  'Public messages use 1–119 DOS characters and are shown once to the current player. '
                  'Actions are checked at scenario start and after each turn’s objective update.',wraplength=390).grid(
                      row=3,column=0,columnspan=2,sticky='w',pady=12)
        match_labels = {'all': 'ALL conditions (AND)', 'any': 'ANY condition (OR)'}
        match = entry(advanced, 'Match', match_labels[p.get('match', 'all')], 0, tuple(match_labels.values()))
        latch = tk.BooleanVar(value=p.get('latch', False))
        latch_button=ttk.Checkbutton(advanced, text='Keep active after first matching order', variable=latch)
        latch_button.grid(row=1, column=0, columnspan=2, sticky='w', pady=8)
        ttk.Label(advanced, text='Once this plan supplies an order, it stays eligible through its last turn, '
                  'even if the conditions change. Higher priorities still win. Activation survives Save/Resume.',
                  wraplength=380).grid(row=2, column=0, columnspan=2, sticky='w', pady=(0, 10))
        extra_fields = []
        extra_labels = {0: 'None', 1: CONDITIONS[1], 2: CONDITIONS[2]}
        for i in range(2):
            box = ttk.LabelFrame(advanced, text=f'Condition {i+2} (optional)', padding=8)
            box.grid(row=i+3, column=0, columnspan=2, sticky='ew', pady=6)
            c = {**DEFAULT_EVENT, **(p.get('extra_conditions', [])[i] if i < len(p.get('extra_conditions', [])) else {})}
            c_kind = entry(box, 'Condition', extra_labels[c['trigger']], 0, tuple(extra_labels.values()))
            c_side = entry(box, 'Side', ('Allied', 'Axis')[c['trigger_side']], 1, ('Allied', 'Axis'))
            c_objective = entry(box, 'Objective', next((k for k, v in objective_choices.items() if v == c['objective']),
                                next(iter(objective_choices), '')), 2, tuple(objective_choices))
            c_threshold = entry(box, 'Casualty points lost', c['threshold'] or 1, 3)
            def refresh_extra(*_, box=box, kind=c_kind):
                value = next(k for k, label in extra_labels.items() if label == kind.get())
                for row, enabled, state in ((1, bool(value), 'readonly'), (2, value == 1, 'readonly'), (3, value == 2, 'normal')):
                    box.grid_slaves(row=row, column=1)[0].configure(state=state if enabled else 'disabled')
            c_kind.trace_add('write', refresh_extra)
            refresh_extra()
            extra_fields.append((c_kind, c_side, c_objective, c_threshold))
        nested_summary=ttk.Label(advanced,wraplength=380)
        nested_summary.grid(row=6,column=0,columnspan=2,sticky='w',pady=8)
        def refresh_expression():
            active=expression[0] is not None
            summary=condition_label(dict(expression=expression[0]),objectives(self.roster)) if active else 'Using the simple conditions above.'
            if len(summary)>250:summary=summary[:247]+'…'
            nested_summary.config(text=summary)
            if active:explanation.config(text='Nested conditions: '+summary)
            for row in (6,7,8,9):
                for w in form.grid_slaves(row=row,column=1):
                    w.configure(state='disabled' if active else 'normal' if row==9 else 'readonly')
            for w in advanced.grid_slaves(row=0,column=1):w.configure(state='disabled' if active else 'readonly')
            for box in [w for w in advanced.winfo_children() if isinstance(w,ttk.LabelFrame)]:
                for w in box.winfo_children():
                    if isinstance(w,(ttk.Entry,ttk.Combobox)):w.configure(state='disabled' if active else 'normal' if isinstance(w,ttk.Entry) and not isinstance(w,ttk.Combobox) else 'readonly')
            if not active:condition_changed()
        def accept_expression(tree):
            expression[0]=tree;refresh_expression()
        def nested_edit():
            tree=expression[0]
            if tree is None:
                current=dict(trigger=next(k for k,v in CONDITIONS.items() if v==trigger.get()),
                    trigger_side=('Allied','Axis').index(trigger_side.get()),objective=objective_choices.get(objective.get(),-1),
                    threshold=values['threshold'].get())
                checks=([current] if current['trigger'] else [])
                for kind,side_var,obj_var,threshold_var in extra_fields:
                    value=next(k for k,label in extra_labels.items() if label==kind.get())
                    if value:checks.append(dict(trigger=value,trigger_side=('Allied','Axis').index(side_var.get()),
                        objective=objective_choices.get(obj_var.get(),-1),threshold=threshold_var.get()))
                tree=dict(operator=next(k for k,label in match_labels.items() if label==match.get()),children=checks) if checks else None
            self.expression_dialog=ExpressionDialog(dialog,self.roster,tree,accept_expression)
        nested_buttons=ttk.Frame(advanced);nested_buttons.grid(row=5,column=0,columnspan=2,sticky='w',pady=8)
        ttk.Button(nested_buttons,text='Edit Nested Conditions…',command=nested_edit).pack(side='left')
        ttk.Button(nested_buttons,text='Use Simple Conditions',command=lambda:accept_expression(None)).pack(side='left',padx=5)
        def action_changed(*_):
            key=next(k for k,v in ACTIONS.items() if v==action.get())
            for row in (4,5):form.grid_slaves(row=row,column=1)[0].configure(state='normal' if key=='order' else 'disabled')
            form.grid_slaves(row=0,column=1)[0].configure(state='disabled' if key=='message' else 'readonly')
            action_page.grid_slaves(row=0,column=1)[0].configure(state='readonly' if key=='order' else 'disabled')
            action_page.grid_slaves(row=1,column=1)[0].configure(state='normal' if key=='message' else 'disabled')
            hold_button.configure(state='normal' if key=='release' else 'disabled')
            latch_button.configure(state='normal' if key=='order' else 'disabled')
            if key!='order':latch.set(False)
            refresh_expression()
        action.trace_add('write',action_changed)
        action_changed()
        values['priority'].set(p['priority'])
        if p.get('action','order')!='order':details.select(action_page)
        self.edit_fields = dict(match=match,latch=latch,extras=extra_fields,expression=expression,
                                nested=nested_edit,action=action,message=message,hold=hold,order=order)
        def save():
            plan={k:v.get() for k,v in values.items()}
            plan['side'],plan['group']=choices[hq.get()]
            plan['order']=next(k for k,v in ORDERS.items() if v==order.get())
            plan['action']=next(k for k,v in ACTIONS.items() if v==action.get())
            plan['hold']=hold.get();plan['message']=message.get()
            if expression[0] is not None:plan['expression']=expression[0]
            if plan['action']!='order':
                plan['x']=struct.unpack_from('<h',self.roster.header,0x226)[0]
                plan['y']=struct.unpack_from('<h',self.roster.header,0x224)[0]
            plan['trigger'] = next(k for k, v in CONDITIONS.items() if v == trigger.get())
            plan['trigger_side'] = ('Allied', 'Axis').index(trigger_side.get())
            plan['objective'] = objective_choices.get(objective.get(), -1)
            if plan['trigger'] != 2:
                plan['threshold'] = 0
            plan['match'] = next(k for k, label in match_labels.items() if label == match.get())
            plan['latch'] = latch.get()
            plan['extra_conditions'] = []
            for kind, side_var, objective_var, threshold_var in extra_fields:
                value = next(k for k, label in extra_labels.items() if label == kind.get())
                if value:
                    plan['extra_conditions'].append(dict(trigger=value, trigger_side=('Allied', 'Axis').index(side_var.get()),
                        objective=objective_choices.get(objective_var.get(), -1),
                        threshold=threshold_var.get() if value == 2 else 0))
            rows=list(self.plans)
            if index is None:rows.append(plan)
            else:rows[index]=plan
            if self.apply(rows):dialog.destroy()
        ttk.Button(form,text='Apply Phase',command=save).grid(row=12,column=1,pady=10)
        ttk.Button(form,text='Cancel',command=dialog.destroy).grid(row=12,column=0,pady=10)
        dialog.grab_set()
