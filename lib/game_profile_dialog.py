"""Game defaults, runtime overrides, and honest conversion coverage."""
import tkinter as tk
from tkinter import ttk, messagebox
from lib.game_profiles import GameProfile, GAMES, FIELDS, DEFAULTS, LIMITS

MODELS = ('D-Day', 'Stalingrad (adapted)', 'V4V (adapted)', 'V4V Velikiye (adapted)')
LABELS = ('Winter model', 'Major victory ratio (%)', 'Minor victory ratio (%)',
          'Light snowfall', 'Heavy snowfall', 'Light rain', 'Heavy rain',
          'Snow melt per degree above 35°F', 'Drying coefficient',
          'Ice growth divisor', 'Ice crossing threshold', 'Ice crossing step')


class GameProfilePanel(ttk.Frame):
    kind = 'game_profile'
    def __init__(self, parent, app):
        super().__init__(parent, padding=16)
        self.app = app
        self.summary = ttk.Label(self, justify='left', wraplength=800)
        self.summary.pack(anchor='w', pady=8)
        ttk.Button(self, text='Edit Game Profile…', command=self.edit).pack(anchor='w', pady=8)
        ttk.Button(self, text='Edit Terrain Rules…', command=self.edit_terrain).pack(anchor='w', pady=4)
        self.coverage = ttk.Label(self, justify='left', wraplength=800)
        self.coverage.pack(anchor='w', pady=12)

    def load(self, roster):
        doc = self.app.document
        profile = doc.profile
        source = GAMES.get(doc.source_game, doc.source_game)
        preserved = ('Original scenario data retained in this document.' if doc.source_data else
                     'This document has no preserved original source records.')
        self.summary.config(text=f'Game profile: {GAMES[profile.game]}\n'
            f'Runtime winter model: {MODELS[profile.values[0]]}\n'
            f'Custom rule overrides: {len(profile.overrides)}; terrain values: {profile.terrain.changed}\n\n'
            f'Source: {source}' + (f' — {doc.source_name}' if doc.source_name else '') + f'\n{preserved}')
        self.coverage.config(text='DOS export includes victory, winter, and custom terrain rules for INVADE-PATCHED.EXE.\n'
            'Existing unit, terrain, supply and weather records remain editable on their respective pages.\n\n' +
            '\n'.join(profile.adaptations) + '\n\n'
            'Changing a profile affects subsequent weather updates; it preserves the initial ground conditions '
            'on the Weather page. Original source records are retained for future translations; current edits '
            'are stored in the scenario records.')

    def edit_terrain(self):
        if self.app.scenario:
            from lib.terrain_rules_dialog import TerrainRulesDialog
            return TerrainRulesDialog(self, self.app)

    def edit(self):
        if not self.app.scenario:
            return
        dialog = tk.Toplevel(self)
        dialog.title('Game Profile')
        dialog.transient(self.winfo_toplevel())
        body = ttk.Frame(dialog, padding=16)
        body.pack(fill='both', expand=True)
        profile = self.app.document.profile
        game = tk.StringVar(value=GAMES[profile.game])
        ttk.Label(body, text='Game defaults').grid(row=0, column=0, sticky='w')
        combo = ttk.Combobox(body, textvariable=game, values=tuple(GAMES.values()), state='readonly', width=32)
        combo.grid(row=0, column=1, padx=10, pady=6)
        values = {}
        for row, (key, label, value, limits) in enumerate(zip(FIELDS, LABELS, profile.values, LIMITS), 1):
            ttk.Label(body, text=label).grid(row=row, column=0, sticky='w', pady=3)
            variable = tk.StringVar(value=MODELS[value] if key == 'winter_model' else str(value))
            widget = (ttk.Combobox(body, textvariable=variable, values=MODELS, state='readonly', width=30)
                      if key == 'winter_model' else ttk.Spinbox(body, textvariable=variable,
                          from_=limits[0], to=limits[1], width=12))
            widget.grid(row=row, column=1, sticky='w', padx=10)
            values[key] = variable
        def selected_game():
            return next(key for key, label in GAMES.items() if label == game.get())
        def defaults(event=None):
            for key, value in zip(FIELDS, DEFAULTS[selected_game()]):
                values[key].set(MODELS[value] if key == 'winter_model' else str(value))
        combo.bind('<<ComboboxSelected>>', defaults)
        ttk.Label(body, text='Ground quantities use thousandths: 1,000 = one unit.\n'
            'D-Day and Stalingrad apply double accumulation at 3 km scale.\n'
            'Selecting another game resets the fields to its defaults.\n'
            'Crusader winter and V4V victory ratios currently use D-Day defaults.',
            wraplength=510).grid(row=13, column=0, columnspan=2, sticky='w', pady=12)
        def apply():
            try:
                settings = [MODELS.index(values[k].get()) if k == 'winter_model' else int(values[k].get()) for k in FIELDS]
                changed = profile.updated(selected_game(), settings)
                self.app.apply_game_profile(changed)
            except (ValueError, KeyError) as exc:
                messagebox.showerror('Invalid Game Profile', str(exc), parent=dialog)
                return
            dialog.destroy()
        buttons = ttk.Frame(body)
        buttons.grid(row=14, column=0, columnspan=2, sticky='e')
        ttk.Button(buttons, text='Restore Defaults', command=defaults).pack(side='left', padx=5)
        ttk.Button(buttons, text='Cancel', command=dialog.destroy).pack(side='left', padx=5)
        ttk.Button(buttons, text='Apply', command=apply).pack(side='left')
        dialog.bind('<Escape>', lambda e: dialog.destroy())
        dialog.grab_set()
