"""Scenario-specific movement and combat constants, applied as one history edit."""
from dataclasses import replace
from decimal import Decimal, InvalidOperation
import tkinter as tk
from tkinter import ttk, messagebox
from lib.terrain_reader import terrain_name
from lib.unit_definitions import MOBILITY
from lib.terrain_rules import (TerrainRules, DEFAULT, ROAD_START, COMBAT_START,
                               movement_index)


class TerrainRulesDialog(tk.Toplevel):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self.title('Terrain Rules')
        self.transient(parent.winfo_toplevel())
        self.values = list(app.document.profile.terrain.values)
        self.current = 1
        self.movement, self.combat, self.roads = [], [], []
        body = ttk.Frame(self, padding=14)
        body.pack(fill='both', expand=True)
        tabs = ttk.Notebook(body)
        tabs.pack(fill='both', expand=True)
        terrain = ttk.Frame(tabs, padding=12)
        roads = ttk.Frame(tabs, padding=12)
        tabs.add(terrain, text='Terrain')
        tabs.add(roads, text='Roads')
        self.selector = ttk.Combobox(terrain, state='readonly', width=30,
            values=[f'{i:02d} — {terrain_name(i)}' for i in range(14)])
        self.selector.grid(row=0, column=0, columnspan=3, sticky='w', pady=(0,12))
        self.selector.current(self.current)
        self.selector.bind('<<ComboboxSelected>>', self.select)
        for col, text in enumerate(('Movement class', 'Dry (MP)', 'Light mud (MP)')):
            ttk.Label(terrain, text=text).grid(row=1, column=col, sticky='w', padx=6)
        self.move_widgets = []
        for m, name in enumerate(MOBILITY):
            ttk.Label(terrain, text=name).grid(row=m+2, column=0, sticky='w', padx=6, pady=3)
            pair, widgets = [], []
            for ground in range(2):
                variable = tk.StringVar()
                field = ttk.Spinbox(terrain, textvariable=variable, from_=0, to=10,
                                    increment=0.02, width=9, format='%.2f')
                field.grid(row=m+2, column=ground+1, padx=6)
                pair.append(variable)
                widgets.append(field)
            self.movement.append(pair)
            self.move_widgets.append(widgets)
        modifiers = ttk.LabelFrame(terrain, text='Combat multipliers', padding=12)
        modifiers.grid(row=1, column=3, rowspan=13, sticky='nw', padx=(18,0))
        for row, label in enumerate(('Defense (%)', 'Anti-armor defense (%)', 'Bombardment received (%)')):
            ttk.Label(modifiers, text=label).grid(row=row*2, column=0, sticky='w', pady=(8,2))
            var = tk.StringVar()
            ttk.Spinbox(modifiers, textvariable=var, from_=0, to=400, width=9).grid(row=row*2+1, column=0, sticky='w')
            self.combat.append(var)
        ttk.Label(modifiers, text='100% leaves strength unchanged.\nLower bombardment values protect\nthe target. Fortifications, supply and\nother native modifiers still apply.',
                  justify='left').grid(row=6, column=0, sticky='w', pady=14)
        ttk.Label(terrain, text='Movement shown for one step through uniform terrain; 0 blocks movement.\n'
            'A mixed step averages the two hex costs, then adds crossing and visibility effects.\n'
            'All six artwork variants share these rules. Water and Fixed remain blocked.',
            justify='left').grid(row=14, column=0, columnspan=4, sticky='w', pady=12)
        ttk.Button(terrain, text='Restore This Terrain', command=self.restore_terrain).grid(row=15, column=0, columnspan=3, sticky='w')
        for col, label in enumerate(('Movement class', 'Dirt road (MP)', 'Paved road (MP)', 'Railroad (MP)')):
            ttk.Label(roads, text=label).grid(row=0, column=col, sticky='w', padx=6)
        for m, name in enumerate(MOBILITY):
            ttk.Label(roads, text=name).grid(row=m+1, column=0, sticky='w', padx=6, pady=5)
            row = []
            for kind in range(3):
                var = tk.StringVar(value=f'{self.values[ROAD_START+m*3+kind]/500:.3f}')
                ttk.Spinbox(roads, textvariable=var, from_=0.002, to=10, increment=0.002,
                    format='%.3f', width=11, state='disabled' if m == 10 else 'normal').grid(row=m+1, column=kind+1, padx=6)
                row.append(var)
            self.roads.append(row)
        ttk.Label(roads, text='Cost per step in Strategic mode, before visibility effects.\n'
            'Mobile classes require a positive cost; the AI uses these values too.',
            justify='left').grid(row=13, column=0, columnspan=4, sticky='w', pady=14)
        buttons = ttk.Frame(body)
        buttons.pack(fill='x', pady=(12,0))
        ttk.Button(buttons, text='Restore All D-Day Defaults', command=self.restore_all).pack(side='left')
        ttk.Button(buttons, text='Apply', command=self.apply).pack(side='right')
        ttk.Button(buttons, text='Cancel', command=self.destroy).pack(side='right', padx=8)
        self.show_terrain()
        self.bind('<Escape>', lambda e: self.destroy())
        self.grab_set()

    @staticmethod
    def parse(text, scale, maximum, label):
        try:
            value = Decimal(text)*scale
            if not value.is_finite() or value != value.to_integral_value() or not 0 <= value <= maximum:
                raise ValueError()
            return int(value)
        except (InvalidOperation, ValueError):
            raise ValueError(f'{label}: use 0–{maximum/scale:g} in steps of {1/scale:g}') from None

    def stash(self):
        changed = self.values.copy()
        for m, pair in enumerate(self.movement):
            for ground, var in enumerate(pair):
                changed[movement_index(self.current, m, ground)] = self.parse(var.get(), 50, 500, f'{MOBILITY[m]} movement')
        for field, var in enumerate(self.combat):
            changed[COMBAT_START+field*14+self.current] = self.parse(var.get(), 1, 400, 'Combat percentage')
        for m, row in enumerate(self.roads):
            for kind, var in enumerate(row):
                changed[ROAD_START+m*3+kind] = self.parse(var.get(), 500, 5000, f'{MOBILITY[m]} road cost')
        TerrainRules(tuple(changed))
        self.values = changed

    def show_terrain(self):
        for m, pair in enumerate(self.movement):
            for ground, var in enumerate(pair):
                var.set(f'{self.values[movement_index(self.current, m, ground)]/50:.2f}')
                self.move_widgets[m][ground].configure(state='disabled' if m == 10 or self.current == 5 else 'normal')
        for field, var in enumerate(self.combat):
            var.set(str(self.values[COMBAT_START+field*14+self.current]))

    def select(self, event=None):
        try:
            self.stash()
        except ValueError as exc:
            self.selector.current(self.current)
            messagebox.showerror('Invalid Terrain Rules', str(exc), parent=self)
            return
        self.current = self.selector.current()
        self.show_terrain()

    def restore_terrain(self):
        for m in range(12):
            for ground in range(2):
                i = movement_index(self.current, m, ground)
                self.values[i] = DEFAULT[i]
        for field in range(3):
            i = COMBAT_START+field*14+self.current
            self.values[i] = DEFAULT[i]
        self.show_terrain()

    def restore_all(self):
        self.values = list(DEFAULT)
        self.show_terrain()
        for m, row in enumerate(self.roads):
            for kind, var in enumerate(row):
                var.set(f'{self.values[ROAD_START+m*3+kind]/500:.3f}')

    def apply(self):
        try:
            self.stash()
            profile = replace(self.app.document.profile, terrain=TerrainRules(tuple(self.values)))
            self.app.apply_game_profile(profile)
        except ValueError as exc:
            messagebox.showerror('Invalid Terrain Rules', str(exc), parent=self)
            return
        self.destroy()
