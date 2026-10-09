"""Terrain palette and OOB placement controls for the map page."""
import tkinter as tk
from tkinter import ttk

from PIL import Image, ImageTk

from lib.game_art import unit_counter, support_unit_icon
from lib.terrain_reader import terrain_name
from lib.terrain_catalog import terrain_catalog
from lib.map_editor import DIRECTIONS, MAP_FEATURES, hex_feature_labels
from lib.unit_reader import unit_status, unit_arrival_label
from lib.map_tool_controls import MapToolsPanel


class MapEditingPanel(ttk.Frame):
    def __init__(self, parent, viewer, on_terrain, on_unit, on_undo, on_feature=None, on_tool=None):
        super().__init__(parent, padding=8)
        self.viewer = viewer
        self.on_terrain, self.on_unit = on_terrain, on_unit
        self.on_feature = on_feature
        self.unit_key = None
        self.chit_image = self.terrain_image = self.feature_image = None
        self.mode = tk.StringVar(value='Select')
        self.auto_blend = tk.BooleanVar(value=False)
        self.blend_imported = tk.BooleanVar(value=False)
        ttk.Label(self, text='Map editing', font=('TkDefaultFont', 10, 'bold')).pack(anchor=tk.W)
        tools = ttk.Frame(self)
        tools.pack(fill=tk.X, pady=6)
        for index, title in enumerate(('Select', 'Paint', 'Features', 'Place unit')):
            ttk.Radiobutton(tools, text=title, value=title, variable=self.mode,
                            command=self._mode_changed).grid(row=index // 2, column=index % 2, sticky=tk.W, padx=(0, 20))
        self.hex_label = ttk.Label(self, text='Select a hex on the map.', wraplength=285)
        self.hex_label.pack(anchor=tk.W, pady=4)
        self.tabs = ttk.Notebook(self)
        self.tabs.pack(fill=tk.BOTH, expand=True)
        terrain = ttk.Frame(self.tabs, padding=8)
        oob = ttk.Frame(self.tabs, padding=8)
        self.tabs.add(terrain, text='Terrain')
        self.tabs.add(oob, text='Current OOB')
        features = ttk.Frame(self.tabs, padding=8)
        self.tabs.add(features, text='Features')

        self.catalog = terrain_catalog()
        self.terrain_choices = [entry.code for entry in self.catalog]
        ttk.Label(terrain, text='D-Day · full terrain palette').pack(anchor=tk.W)
        self.terrain_combo = ttk.Combobox(terrain, state='readonly', width=25,
            values=[entry.name for entry in self.catalog])
        self.terrain_combo.current(0)
        self.terrain_combo.pack(fill=tk.X, pady=5)
        self.terrain_combo.bind('<<ComboboxSelected>>', self._preview_terrain)
        variants = ttk.Frame(terrain)
        variants.pack(fill=tk.X, pady=5)
        ttk.Label(variants, text='Artwork variant:').pack(side=tk.LEFT)
        self.variant_combo = ttk.Combobox(variants, state='readonly', values=self.catalog[0].variants, width=4)
        self.variant_combo.current(0)
        self.variant_combo.pack(side=tk.LEFT, padx=6)
        self.variant_combo.bind('<<ComboboxSelected>>', self._preview_terrain)
        ttk.Checkbutton(terrain, text='Blend edges while painting', variable=self.auto_blend).pack(anchor=tk.W, pady=5)
        self.terrain_preview = ttk.Label(terrain, anchor=tk.CENTER)
        self.terrain_preview.pack(fill=tk.X, pady=8)
        self.artwork_label = ttk.Label(terrain, wraplength=265)
        self.artwork_label.pack(anchor=tk.W, pady=3)
        self.browse_terrain_button = ttk.Button(terrain, text='Browse terrain from all games…')
        self.browse_terrain_button.pack(fill=tk.X, pady=3)
        images = ttk.Frame(terrain)
        images.pack(fill=tk.X, pady=3)
        self.import_image_button = ttk.Button(images, text='Import Image…')
        self.import_image_button.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.export_image_button = ttk.Button(images, text='Export Image…')
        self.export_image_button.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.restore_artwork_button = ttk.Button(terrain, text='Restore original D-Day artwork')
        self.restore_artwork_button.pack(fill=tk.X, pady=3)
        ttk.Button(terrain, text='Paint on map', command=lambda: self.set_mode('Paint')).pack(fill=tk.X, pady=3)
        self.apply_terrain_button = ttk.Button(terrain, text='Apply to selected hex', command=self.paint_selected)
        self.apply_terrain_button.pack(fill=tk.X, pady=3)
        self.pick_terrain_button = ttk.Button(terrain, text='Pick terrain from selected hex', command=self.pick_terrain)
        self.pick_terrain_button.pack(fill=tk.X, pady=3)
        self.clear_terrain_button = ttk.Button(terrain, text='Set selected hex to Clear', command=self.clear_terrain)
        self.clear_terrain_button.pack(fill=tk.X, pady=3)
        ttk.Button(terrain, text='Flood fill from selected hex',
                   command=lambda: self.tools.fill_terrain()).pack(fill=tk.X, pady=3)
        ttk.Label(terrain, text='Blending updates cosmetic edges around painted or filled hexes. '
                  'Roads, rivers and hills stay in place. Tools → Cosmetic edges has manual editing '
                  'and blending for existing maps.', wraplength=265).pack(anchor=tk.W, pady=10)

        ttk.Label(features, text='Roads, water and hills').pack(anchor=tk.W)
        self.feature_var = tk.StringVar(value='Dirt road')
        self.feature_combo = ttk.Combobox(features, state='readonly', textvariable=self.feature_var,
                                         values=MAP_FEATURES, width=25)
        self.feature_combo.pack(fill=tk.X, pady=5)
        self.feature_combo.bind('<<ComboboxSelected>>', self._feature_changed)
        self.feature_action = tk.StringVar(value='Add')
        actions = ttk.Frame(features)
        actions.pack(fill=tk.X, pady=5)
        for action in ('Add', 'Remove'):
            ttk.Radiobutton(actions, text=action, value=action, variable=self.feature_action,
                            command=self._feature_changed).pack(side=tk.LEFT, padx=(0, 15))
        ttk.Label(features, text='Direction · selected hex').pack(anchor=tk.W, pady=(5, 0))
        compass = ttk.Frame(features)
        compass.pack(fill=tk.X, pady=5)
        compass.columnconfigure(1, weight=1)
        self.feature_direction = tk.IntVar(value=3)
        self.direction_buttons = []
        for direction, (row, col) in enumerate(((1, 0), (0, 0), (0, 2), (1, 2), (2, 2), (2, 0))):
            button = ttk.Radiobutton(compass, text=DIRECTIONS[direction], value=direction,
                                     variable=self.feature_direction, command=self._feature_changed)
            button.grid(row=row, column=col, sticky=tk.W)
            self.direction_buttons.append(button)
        self.feature_preview = ttk.Label(compass, anchor=tk.CENTER)
        self.feature_preview.grid(row=0, column=1, rowspan=3, padx=2)
        self.feature_help = ttk.Label(features, wraplength=265)
        self.feature_help.pack(anchor=tk.W, pady=6)
        self.feature_mode_button = ttk.Button(features, text='Edit features on map',
                                              command=lambda: self.set_mode('Features'))
        self.feature_mode_button.pack(fill=tk.X, pady=3)
        self.apply_feature_button = ttk.Button(features, text='Apply to selected side', command=self.apply_feature)
        self.apply_feature_button.pack(fill=tk.X, pady=3)
        ttk.Separator(features).pack(fill=tk.X, pady=8)
        ttk.Label(features, text='Features at selected hex:', font=('TkDefaultFont', 9, 'bold')).pack(anchor=tk.W)
        self.features_label = ttk.Label(features, wraplength=265, justify=tk.LEFT)
        self.features_label.pack(anchor=tk.W, pady=5)

        self.side_var = tk.StringVar(value='Both sides')
        side = ttk.Combobox(oob, textvariable=self.side_var, state='readonly', width=24,
                            values=('Both sides', 'Allied', 'Axis'))
        side.pack(fill=tk.X)
        side.bind('<<ComboboxSelected>>', self.refresh_units)
        ttk.Label(oob, text='Find unit:').pack(anchor=tk.W, pady=(5, 0))
        self.search_var = tk.StringVar()
        ttk.Entry(oob, textvariable=self.search_var, width=24).pack(fill=tk.X, pady=(0, 5))
        self.search_var.trace_add('write', self.refresh_units)
        roster = ttk.Frame(oob)
        roster.pack(fill=tk.BOTH, expand=True)
        self.unit_tree = ttk.Treeview(roster, columns=('name', 'status'), show='headings',
                                      selectmode='browse', height=5)
        self.unit_tree.heading('name', text='Unit')
        self.unit_tree.heading('status', text='Status')
        self.unit_tree.column('name', width=142, stretch=True)
        self.unit_tree.column('status', width=96, stretch=False)
        scroll = ttk.Scrollbar(roster, orient=tk.VERTICAL, command=self.unit_tree.yview)
        self.unit_tree.config(yscrollcommand=scroll.set)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.unit_tree.pack(fill=tk.BOTH, expand=True)
        self.unit_tree.bind('<<TreeviewSelect>>', self._select_oob_unit)
        self.unit_preview = ttk.Label(oob, anchor=tk.CENTER)
        self.unit_preview.pack(fill=tk.X, pady=4)
        self.unit_label = ttk.Label(oob, wraplength=265)
        self.unit_label.pack(anchor=tk.W, pady=3)
        self.deployment_var = tk.StringVar(value='Deploy at start')
        self.deployment_combo = ttk.Combobox(oob, textvariable=self.deployment_var, state='readonly',
                                            values=('Deploy at start', 'Keep arrival turn'), width=24)
        self.deployment_combo.pack(fill=tk.X, pady=3)
        self.deployment_combo.bind('<<ComboboxSelected>>', lambda event: self._mode_changed())
        self.place_button = ttk.Button(oob, text='Place selected unit on map',
                                       command=lambda: self.set_mode('Place unit'))
        self.place_button.pack(fill=tk.X, pady=3)
        self.remove_button = ttk.Button(oob, text='Remove from map (keep in OOB)', command=self.remove_unit)
        self.remove_button.pack(fill=tk.X, pady=3)
        ttk.Label(oob, text='Units at selected hex:').pack(anchor=tk.W, pady=(5, 0))
        self.stack_combo = ttk.Combobox(oob, state='readonly', width=24)
        self.stack_combo.pack(fill=tk.X, pady=3)
        self.stack_combo.bind('<<ComboboxSelected>>', self._select_stack_unit)
        self.stack = []

        self.undo_button = ttk.Button(self, text='Undo Last Edit', command=on_undo, state='disabled')
        self.undo_button.pack(fill=tk.X, pady=6)
        self.hint = ttk.Label(self, wraplength=285)
        self.hint.pack(anchor=tk.W)
        self.tools = MapToolsPanel(self.tabs, self, on_tool)
        self.tabs.add(self.tools, text='Tools')
        self.tabs.bind('<<NotebookTabChanged>>', self._tab_changed)
        self._preview_terrain()
        self.refresh()

    def _key(self, unit):
        return unit['side'], unit['side_index']

    def _tab_changed(self, event=None):
        if self.tabs.index(self.tabs.select()) == 3:
            if self.mode.get() in ('Paint', 'Features', 'Place unit'):
                self.set_mode('Select')
            self.tools.refresh()

    def selected_unit(self):
        return next((u for u in self.viewer.units if self._key(u) == self.unit_key and not u.get('deleted')), None)

    def set_mode(self, mode):
        self.mode.set(mode)
        self._mode_changed()

    def _mode_changed(self):
        mode = self.mode.get()
        if mode == 'Paint':
            self.tabs.select(0)
            hint = 'Click a hex to paint it. Drag to pan. Save writes your edits.'
        elif mode == 'Place unit':
            self.tabs.select(1)
            hint = ('Choose an OOB unit, then click its destination. '
                    + ('Placement makes it available at the start.' if self.deployment_var.get() == 'Deploy at start'
                       else 'Placement keeps its arrival turn; future units remain hidden until arrival.'))
        elif mode == 'Features':
            self.tabs.select(2)
            hint = ('Click a hex to add/remove its hilltop.' if self.feature_var.get() == 'Hilltop' else
                    'Click near a hex edge to edit that side. A center click uses the chosen direction.')
            hint += ' Drag to pan. Esc returns to Select.'
        elif mode in ('Ownership', 'Edges', 'Region', 'Paste'):
            self.tabs.select(3)
            hint = {'Ownership': 'Click a hex to paint its owner.',
                    'Edges': 'Click near a hex edge to add/remove cosmetic artwork.',
                    'Region': 'Click two opposite corners to select a region.',
                    'Paste': 'Click the destination for the copied region’s upper-left hex.'}[mode]
            hint += ' Drag to pan. Esc returns to Select.'
            if mode == 'Ownership':
                self.viewer.ownership_var.set(True)
        else:
            hint = 'Click to select a hex or unit stack. Drag to pan. Save writes your edits.'
            self.refresh_hex()
        self.hint.config(text=hint)
        self.viewer.canvas.config(cursor='crosshair' if mode != 'Select' else '')
        self.viewer.redraw()

    def _feature_changed(self, event=None):
        self.refresh_features()
        self.tools.refresh()
        self._mode_changed()

    def refresh_features(self):
        feature = self.feature_var.get()
        hilltop = feature == 'Hilltop'
        valid = self.viewer.selected_hex in self.viewer.terrain
        for button in self.direction_buttons:
            button.config(state='disabled' if hilltop else 'normal')
        self.apply_feature_button.config(text=self.feature_action.get() + (' hilltop' if hilltop else ' on selected side'),
                                        state='normal' if valid and self.on_feature else 'disabled')
        self.feature_mode_button.config(state='normal' if self.viewer.terrain and self.on_feature else 'disabled')
        if hilltop:
            help_text = 'Hilltops are separate markers. Add slopes around higher ground as needed. The game supports 30 hilltops.'
        elif feature in ('Uphill slope', 'Downhill slope'):
            help_text = ('Uphill rises from this hex toward its neighbor. Downhill falls toward its neighbor. '
                         'Adding a slope replaces a river/stream on that edge. Remove erases either slope direction.')
        elif feature in ('Stream', 'River'):
            help_text = 'Both sides of the edge update together. Adding replaces any stream, river or slope there; roads stay in place.'
        else:
            help_text = 'Connects this hex to its neighbor. Adding replaces the road/rail type on that connection; rivers and slopes stay in place.'
        self.feature_help.config(text=help_text)
        if valid:
            cell = self.viewer.selected_hex
            layers = self.viewer.map_layers
            code, variant = self.viewer.terrain[cell]
            try:
                art = self.viewer.hex_tile_loader.compose_tile(code, variant, layers.records.get(cell, 0),
                                                               layers.edges.get(cell, b''), cell in layers.hilltops)
            except ValueError:
                art = self.viewer.hex_tile_loader.get_tile_with_variant(code, variant)
            self.feature_image = ImageTk.PhotoImage(art.resize((96, 108), Image.Resampling.NEAREST))
            self.feature_preview.config(image=self.feature_image, text='')
            self.features_label.config(text='\n'.join(hex_feature_labels(layers, cell)) or 'None')
        else:
            self.feature_image = None
            self.feature_preview.config(image='', text='Select a hex')
            self.features_label.config(text='Select a hex on the map.')

    def apply_feature(self):
        cell = self.viewer.selected_hex
        if cell in self.viewer.terrain and self.on_feature:
            self.on_feature(cell, self.feature_var.get(), self.feature_direction.get(),
                            self.feature_action.get() == 'Remove')

    def _preview_terrain(self, event=None):
        entry = self.catalog[self.terrain_combo.current()]
        code = entry.code
        self.variant_combo['values'] = entry.variants
        if int(self.variant_combo.get()) not in entry.variants:
            self.variant_combo.set(entry.variants[0])
        variant = int(self.variant_combo.get())
        art = self.viewer.hex_tile_loader.get_tile_with_variant(code, variant)
        self.terrain_image = ImageTk.PhotoImage(art.resize((96, 108), Image.Resampling.NEAREST))
        self.terrain_preview.config(image=self.terrain_image)
        stamp = self.viewer.hex_tile_loader.artwork.get((code, variant))
        self.artwork_label.config(text=(stamp.name + f'\nD-Day rules: {entry.name}') if stamp else '')
        self.restore_artwork_button.config(state='normal' if stamp else 'disabled')

    def choose_terrain(self, code, variant=0, *, paint=True):
        """Use the same full catalog from the reference page and map palette."""
        index = self.terrain_choices.index(code)
        if variant not in self.catalog[index].variants:
            raise ValueError('Unsupported artwork variant')
        self.terrain_combo.current(index)
        self.variant_combo.set(variant)
        self._preview_terrain()
        if paint:
            self.set_mode('Paint')

    def refresh(self):
        self._preview_terrain()
        self.refresh_units()
        self.refresh_hex()
        self._mode_changed()

    def refresh_units(self, *_):
        search = self.search_var.get().strip().casefold()
        side = self.side_var.get()
        self.unit_tree.delete(*self.unit_tree.get_children())
        for unit in self.viewer.units:
            if unit.get('deleted') or side != 'Both sides' and side != unit['side']:
                continue
            if search and search not in f"{unit['name']} {unit['type_name']}".casefold():
                continue
            label = f"{'AL' if unit['side'] == 'Allied' else 'AX'} {unit['side_index']}: {unit['name']}"
            status = unit_status(unit)
            if status == 'Reinforcement':
                status = unit_arrival_label(unit)
            self.unit_tree.insert('', tk.END, iid=str(unit['index']), values=(label, status))
        unit = self.selected_unit()
        if unit and self.unit_tree.exists(str(unit['index'])):
            self.unit_tree.selection_set(str(unit['index']))
            self.unit_tree.focus(str(unit['index']))
            self.unit_tree.see(str(unit['index']))
        else:
            self.unit_key = None
        self._preview_unit()

    def _select_oob_unit(self, event=None):
        selection = self.unit_tree.selection()
        if not selection:
            return
        unit = next((u for u in self.viewer.units if str(u['index']) == selection[0]), None)
        if unit:
            self.unit_key = self._key(unit)
            self._preview_unit()
            self.viewer.redraw()

    def select_unit(self, unit):
        # Selecting a map counter reveals it even when the OOB was filtered.
        self.unit_key = self._key(unit)
        self.side_var.set('Both sides')
        if self.search_var.get():
            self.search_var.set('')
        self.refresh_units()
        self.tabs.select(1)

    def _preview_unit(self):
        unit = self.selected_unit()
        self.chit_image = None
        self.unit_preview.config(image='', text='')
        if unit:
            support = unit['unit_class'] in (5, 6)
            try:
                art = (support_unit_icon(unit['unit_class'], unit['type'], unit['side'], unit.get('support_artwork')) if support else
                       unit_counter(unit['counter_resource'], unit['counter_index'], unit.get('counter_bitmap')))
                self.chit_image = ImageTk.PhotoImage(art.resize((art.width * 2, art.height * 2), Image.Resampling.NEAREST))
                self.unit_preview.config(image=self.chit_image)
            except (OSError, ValueError, RuntimeError):
                self.unit_preview.config(text='Artwork unavailable')
            self.unit_label.config(text=f"{unit['name']} · {unit['side']}\n{unit['type_name']}\n"
                                  + ('Aircraft/naval support stays off map.' if support else
                                     f"{unit_status(unit)} · {unit_arrival_label(unit)} · Hex ({unit['x']}, {unit['y']})"))
        else:
            self.unit_label.config(text='Select a unit from the current OOB.')
        can_place = bool(unit and unit['unit_class'] not in (5, 6))
        self.place_button.config(state='normal' if can_place else 'disabled')
        self.remove_button.config(state='normal' if can_place and (unit['x'] >= 0 or unit['y'] >= 0) else 'disabled')

    def refresh_hex(self):
        cell = self.viewer.selected_hex
        valid = cell in self.viewer.terrain if cell is not None else False
        for button in (self.apply_terrain_button, self.pick_terrain_button, self.clear_terrain_button):
            button.config(state='normal' if valid else 'disabled')
        if valid:
            code, variant = self.viewer.terrain[cell]
            self.hex_label.config(text=f'Hex {cell[0]}, {cell[1]} · {terrain_name(code)} · Variant {variant}')
            if (self.mode.get() == 'Select' and self.tabs.index(self.tabs.select()) != 3
                    and code in self.terrain_choices
                    and variant in self.catalog[self.terrain_choices.index(code)].variants):
                self.choose_terrain(code, variant, paint=False)
        else:
            self.hex_label.config(text='Select a hex on the map.')
        self.stack = [u for u in self.viewer.units if valid and self.viewer._unit_is_visible(u)
                      and (u['x'], u['y']) == cell]
        self.stack_combo['values'] = [f"{u['side']} {u['side_index']}: {u['name']}" for u in self.stack]
        self.stack_combo.set('')
        if self.stack:
            self.stack_combo.current(next((i for i, u in enumerate(self.stack) if self._key(u) == self.unit_key), 0))
        self.refresh_features()
        self.tools.refresh()

    def _select_stack_unit(self, event=None):
        index = self.stack_combo.current()
        if 0 <= index < len(self.stack):
            self.select_unit(self.stack[index])
            self.viewer.redraw()

    def click_hex(self, cell, direction=None):
        self.viewer.selected_hex = cell
        mode = self.mode.get()
        if mode == 'Paint':
            self.paint_selected()
        elif mode == 'Features':
            if direction is not None:
                self.feature_direction.set(direction)
            self.apply_feature()
        elif mode == 'Place unit':
            unit = self.selected_unit()
            if unit:
                self.on_unit(unit, cell, self.deployment_var.get())
            else:
                self.hint.config(text='Select a unit from the Current OOB list first.')
        elif mode in ('Ownership', 'Edges', 'Region', 'Paste'):
            self.tools.click_hex(cell, direction)
        else:
            self.refresh_hex()
            if self.tabs.index(self.tabs.select()) >= 2:
                pass  # Keep the feature inspector visible while selecting other hexes.
            elif self.stack and self.viewer.units_var.get():
                self.select_unit(self.stack[0])
            else:
                self.tabs.select(0)
        self.refresh_hex()
        self.viewer.redraw()

    def paint_selected(self):
        if self.viewer.selected_hex is not None:
            code = self.terrain_choices[self.terrain_combo.current()]
            self.on_terrain(self.viewer.selected_hex, code, int(self.variant_combo.get()))

    def pick_terrain(self):
        cell = self.viewer.selected_hex
        if cell in self.viewer.terrain:
            code, variant = self.viewer.terrain[cell]
            if code in self.terrain_choices and variant < 6:
                self.choose_terrain(code, variant)

    def clear_terrain(self):
        if self.viewer.selected_hex is not None:
            self.on_terrain(self.viewer.selected_hex, 1, 0)

    def remove_unit(self):
        unit = self.selected_unit()
        if unit:
            self.on_unit(unit, None, self.deployment_var.get())
