"""Choose the D-Day rule and artwork slot for a tile from an earlier game."""
import tkinter as tk
from tkinter import ttk

from PIL import Image, ImageTk

from lib.terrain_catalog import terrain_catalog


class TerrainImportDialog(tk.Toplevel):
    def __init__(self, app, stamp, terrain=None):
        super().__init__(app.root)
        self.app, self.stamp = app, stamp
        self.title('Use artwork in D-Day')
        self.transient(app.root)
        self.resizable(False, False)
        body = ttk.Frame(self, padding=18)
        body.pack(fill=tk.BOTH, expand=True)
        ttk.Label(body, text=stamp.name, wraplength=460).pack(anchor=tk.W)
        self.photo = ImageTk.PhotoImage(stamp.image().resize((96, 108), Image.Resampling.NEAREST))
        ttk.Label(body, image=self.photo).pack(pady=10)
        ttk.Label(body, text='Terrain slot (rules can be customized in Game Profile):').pack(anchor=tk.W)
        self.rules = ttk.Combobox(body, state='readonly', values=[e.name for e in terrain_catalog()])
        self.rules.pack(fill=tk.X, pady=5)
        self.rules.set('Choose terrain slot')
        if terrain is not None:
            self.rules.current(terrain)
        self.rules.bind('<<ComboboxSelected>>', self.update_slots)
        ttk.Label(body, text='Artwork slot:').pack(anchor=tk.W)
        self.slots = ttk.Combobox(body, state='readonly', width=58)
        self.slots.pack(fill=tk.X, pady=5)
        self.slots.bind('<<ComboboxSelected>>', self.update_impact)
        self.impact = ttk.Label(body, wraplength=460)
        self.impact.pack(anchor=tk.W, pady=8)
        ttk.Label(body, text='D-Day allows six artwork variants per terrain type. '
                  'Choose an unused slot or replace existing artwork. '
                  'Save prepares the matching game files automatically.', wraplength=460).pack(anchor=tk.W, pady=8)
        buttons = ttk.Frame(body)
        buttons.pack(fill=tk.X, pady=(8, 0))
        ttk.Button(buttons, text='Cancel', command=self.destroy).pack(side=tk.RIGHT)
        self.use_button = ttk.Button(buttons, text='Use artwork and paint', command=self.submit)
        self.use_button.pack(side=tk.RIGHT, padx=8)
        self.update_slots()
        self.update_idletasks()
        self.geometry(f'+{app.root.winfo_rootx() + max(0, (app.root.winfo_width() - self.winfo_width()) // 2)}'
                      f'+{app.root.winfo_rooty() + max(0, (app.root.winfo_height() - self.winfo_height()) // 2)}')
        self.bind('<Escape>', lambda event: self.destroy())
        self.grab_set()

    def update_slots(self, event=None):
        code = self.rules.current()
        if code < 0:
            self.slots['values'] = ()
            self.slots.set('Choose terrain rules first')
            self.slots.config(state='disabled')
            self.use_button.config(state='disabled')
            self.impact.config(text='Choose the terrain behavior this artwork should have in D-Day.')
            return
        self.slots.config(state='readonly')
        used = self.app.map_viewer.terrain.values()
        self.counts = [sum(value == (code, variant) for value in used) for variant in range(6)]
        self.slots['values'] = [f'Variant {v} · {count} hexes' +
            (f' · {self.app.terrain_artwork[code, v].name}' if (code, v) in self.app.terrain_artwork else '')
            for v, count in enumerate(self.counts)]
        free = next((v for v, count in enumerate(self.counts)
                     if not count and (code, v) not in self.app.terrain_artwork), None)
        if free is None:
            self.slots.set('Choose a slot to replace')
        else:
            self.slots.current(free)
        self.update_impact()

    def update_impact(self, event=None):
        variant = self.slots.current()
        self.use_button.config(state='normal' if variant >= 0 else 'disabled')
        self.impact.config(text=(f'This changes the artwork on {self.counts[variant]} existing hexes. '
                                 'Their movement and combat rules stay the same.' if variant >= 0 else
                                 'All six slots are in use or have assigned artwork. Choose one to replace.'))

    def submit(self):
        code, variant = self.rules.current(), self.slots.current()
        if code < 0 or variant < 0:
            return
        self.app.assign_terrain_artwork(code, variant, self.stamp)
        self.destroy()
        self.app._choose_catalog_terrain(code, variant)
