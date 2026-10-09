"""Additional map tools, kept in one sidebar tab."""
import struct
import tkinter as tk
from tkinter import ttk

from PIL import Image, ImageTk

from lib.map_editor import DIRECTIONS
from lib.map_tools import EDGE_FAMILIES, rectangle, translate_cell
from lib.terrain_reader import terrain_name


class MapToolsPanel(ttk.Frame):
    def __init__(self, parent, panel, on_tool):
        super().__init__(parent, padding=8)
        self.panel, self.viewer, self.on_tool = panel, panel.viewer, on_tool
        self.first = self.last = self.clipboard = self.place_index = None
        self.hover = None
        self.loaded_places = []
        self.edge_image = None
        self.section = tk.StringVar(value='Place names')
        chooser = ttk.Combobox(self, state='readonly', textvariable=self.section,
                              values=('Place names', 'Ownership', 'Cosmetic edges', 'Region / fill', 'Move formation', 'Resize map', 'Shift map'))
        chooser.pack(fill=tk.X, pady=(0, 8))
        chooser.bind('<<ComboboxSelected>>', self._section_changed)
        self.brush_label = ttk.Label(self, wraplength=300)
        self.brush_label.pack(anchor=tk.W, pady=(0, 8))
        self.frames = {name: ttk.Frame(self) for name in chooser['values']}
        self._places(self.frames['Place names'])
        self._ownership(self.frames['Ownership'])
        self._edges(self.frames['Cosmetic edges'])
        self._region(self.frames['Region / fill'])
        self._resize(self.frames['Resize map'])
        self._formation(self.frames['Move formation'])
        self._shift(self.frames['Shift map'])
        self.frames[self.section.get()].pack(fill=tk.BOTH, expand=True)

    def _button(self, parent, text, command):
        button = ttk.Button(parent, text=text, command=command)
        button.pack(fill=tk.X, pady=3)
        return button

    def _field(self, parent, text, value='', values=None):
        ttk.Label(parent, text=text).pack(anchor=tk.W, pady=(5, 0))
        var = tk.StringVar(value=str(value))
        widget = (ttk.Combobox(parent, textvariable=var, values=values, state='readonly')
                  if values is not None else ttk.Entry(parent, textvariable=var))
        widget.pack(fill=tk.X)
        return var

    def _section_changed(self, event=None):
        for frame in self.frames.values():
            frame.pack_forget()
        self.frames[self.section.get()].pack(fill=tk.BOTH, expand=True)
        self.panel.set_mode('Select')
        if self.section.get() == 'Ownership':
            self.viewer.ownership_var.set(True)
        self.refresh()
        self.viewer.redraw()

    def _places(self, frame):
        ttk.Label(frame, text='Place names · up to 50').pack(anchor=tk.W)
        box = ttk.Frame(frame)
        box.pack(fill=tk.X, pady=5)
        self.place_list = tk.Listbox(box, height=6, exportselection=False, width=24)
        scroll = ttk.Scrollbar(box, command=self.place_list.yview)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.place_list.configure(yscrollcommand=scroll.set)
        self.place_list.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.place_list.bind('<<ListboxSelect>>', self._select_place)
        self.place_name = self._field(frame, 'Name')
        row = ttk.Frame(frame)
        row.pack(fill=tk.X, pady=5)
        self.place_x, self.place_y = tk.StringVar(value='0'), tk.StringVar(value='0')
        for text, var in (('X', self.place_x), ('Y', self.place_y)):
            ttk.Label(row, text=text).pack(side=tk.LEFT, padx=(0, 4))
            ttk.Entry(row, width=5, textvariable=var).pack(side=tk.LEFT, padx=(0, 10))
        self._button(frame, 'Use selected hex', self._place_at_hex)
        self.place_size = self._field(frame, 'Text size', 18, tuple(range(10, 25)))
        self.place_style = self._field(frame, 'Style', 'Place (V)', ('Place (V)', 'Water (R)', 'Alternate (I)'))
        self._button(frame, 'New place name', self.new_place)
        self.save_place_button = self._button(frame, 'Add place name', self.save_place)
        self._button(frame, 'Delete selected name', self.delete_place)

    def _select_place(self, event=None):
        selected = self.place_list.curselection()
        if not selected:
            return
        self.place_index = selected[0]
        item = self.viewer.map_layers.places[self.place_index]
        self._load_place_fields(item)
        self.viewer.selected_hex = item['x'], item['y']
        self.panel.refresh_hex()
        self.viewer.redraw()

    def _load_place_fields(self, item):
        for var, key in ((self.place_name, 'name'), (self.place_x, 'x'),
                         (self.place_y, 'y'), (self.place_size, 'size')):
            var.set(item[key])
        self.place_style.set({'V': 'Place (V)', 'R': 'Water (R)', 'I': 'Alternate (I)'}.get(item['style'], 'Place (V)'))
        self.save_place_button.config(text='Update place name')

    def _place_at_hex(self):
        if self.viewer.selected_hex in self.viewer.terrain:
            self.place_x.set(self.viewer.selected_hex[0])
            self.place_y.set(self.viewer.selected_hex[1])

    def new_place(self):
        self.place_index = None
        self.place_list.selection_clear(0, tk.END)
        self.place_name.set('')
        self._place_at_hex()
        self.save_place_button.config(text='Add place name')

    def save_place(self):
        index = self.place_index
        count = len(self.viewer.map_layers.places)
        values = dict(name=self.place_name.get(), x=self.place_x.get(), y=self.place_y.get(),
                      size=self.place_size.get(), style=self.place_style.get()[-2:-1])
        if self.on_tool and self.on_tool('place', index=index, values=values):
            self.place_index = count if index is None else index
            self.refresh()
            self.save_place_button.config(text='Update place name')

    def delete_place(self):
        if self.place_index is not None and self.on_tool:
            if self.on_tool('place', index=self.place_index):
                self.new_place()

    def _ownership(self, frame):
        self.owner = self._field(frame, 'Territorial owner', 'Allied', ('Allied', 'Axis'))
        self.owner_at_hex = ttk.Label(frame, wraplength=255)
        self.owner_at_hex.pack(anchor=tk.W, pady=8)
        self._button(frame, 'Paint ownership on map', lambda: self.panel.set_mode('Ownership'))
        self._button(frame, 'Apply to selected hex', self.apply_owner)
        self._button(frame, 'Flood fill owner from selected hex',
                     lambda: self._at_hex('fill_owner', owner=self.owner_value()))
        ttk.Label(frame, text='Fill follows adjacent hexes with the same owner. '
                  'Objective control changes with ownership.', wraplength=255).pack(anchor=tk.W, pady=8)

    def owner_value(self):
        return int(self.owner.get() == 'Axis')

    def apply_owner(self):
        cell = self.viewer.selected_hex
        if cell is not None and self.on_tool:
            self.on_tool('ownership', cells=[cell], owner=self.owner_value())

    def _edges(self, frame):
        ttk.Checkbutton(frame, text='Blend edges while painting', variable=self.panel.auto_blend).pack(anchor=tk.W, pady=3)
        ttk.Checkbutton(frame, text='Include imported terrain in blending', variable=self.panel.blend_imported).pack(anchor=tk.W, pady=3)
        self._button(frame, 'Blend selected hex and neighbors', self.blend_hex)
        self.blend_region_button = self._button(frame, 'Blend selected region and neighbors', self.blend_region)
        self._button(frame, 'Blend entire map', lambda: self.on_tool and self.on_tool('blend'))
        ttk.Label(frame, text='Rebuilds edge artwork in that area, replacing manual edges. '
                  'Imported tiles and their neighbors keep their edges unless included above. '
                  'Use Region / fill to select a region. Undo restores the previous artwork.',
                  wraplength=265).pack(anchor=tk.W, pady=6)
        ttk.Separator(frame).pack(fill=tk.X, pady=8)
        self.edge_family = self._field(frame, 'Edge artwork', EDGE_FAMILIES[0], EDGE_FAMILIES)
        self.edge_variant = self._field(frame, 'Edge span variant (0–2)', 0, (0, 1, 2))
        self.edge_direction = self._field(frame, 'Direction', 'E', DIRECTIONS)
        self.edge_action = self._field(frame, 'Action', 'Add', ('Add', 'Remove'))
        self.edge_preview = ttk.Label(frame, anchor=tk.CENTER)
        self.edge_preview.pack(fill=tk.X, pady=8)
        self.edge_stored = ttk.Label(frame, wraplength=255)
        self.edge_stored.pack(anchor=tk.W, pady=5)
        for var in (self.edge_family, self.edge_variant, self.edge_direction, self.edge_action):
            var.trace_add('write', lambda *_: self.refresh_edge())
        self._button(frame, 'Edit cosmetic edges on map', lambda: self.panel.set_mode('Edges'))
        self._button(frame, 'Apply to selected side', self.apply_edge)
        self._button(frame, 'Pick selected side artwork', self.pick_edge)
        ttk.Label(frame, text='Variants 0, 1 and 2 cover one, two or three sides, ending at the '
                  'chosen direction clockwise (W, NW, NE, E, SE, SW). Draws inside this hex. '
                  'Crossing costs come from the terrain and Features tools.', wraplength=255).pack(anchor=tk.W, pady=8)

    def blend_hex(self):
        if self.viewer.selected_hex in self.viewer.terrain and self.on_tool:
            self.on_tool('blend', cells=[self.viewer.selected_hex])
        else:
            self.panel.hint.config(text='Select a hex on the map first.')

    def blend_region(self):
        if self.region_cells() and self.on_tool:
            self.on_tool('blend', cells=self.region_cells())

    def refresh_edge(self):
        cell = self.viewer.selected_hex
        layers = self.viewer.map_layers
        old = layers.edges.get(cell, bytes(8))
        direction = DIRECTIONS.index(self.edge_direction.get())
        mask = struct.unpack_from('<H', old)[0]
        names = [f'{DIRECTIONS[d]}: {EDGE_FAMILIES[old[d+2] >> 4] if old[d+2] >> 4 < 5 else "Unknown"}'
                 f' {old[d+2] & 15}' for d in range(6) if mask & 1 << d]
        self.edge_stored.config(text='Stored: '+(', '.join(names) or 'None'))
        preview = bytearray(old)
        remove = self.edge_action.get() == 'Remove'
        struct.pack_into('<H', preview, 0, mask & ~(1 << direction) if remove else mask | 1 << direction)
        preview[2+direction] = EDGE_FAMILIES.index(self.edge_family.get())*16+int(self.edge_variant.get())
        code, variant = layers.terrain.get(cell, (1, 0))
        try:
            art = self.viewer.hex_tile_loader.compose_tile(code, variant, layers.records.get(cell, 0),
                                                           preview, cell in layers.hilltops)
        except ValueError:
            art = self.viewer.hex_tile_loader.get_tile_with_variant(code, variant)
        self.edge_image = ImageTk.PhotoImage(art.resize((96, 108), Image.Resampling.NEAREST))
        self.edge_preview.config(image=self.edge_image)
        if self.panel.mode.get() == 'Edges':
            self.viewer.redraw()

    def apply_edge(self):
        self._at_hex('edge', direction=DIRECTIONS.index(self.edge_direction.get()),
                     family=EDGE_FAMILIES.index(self.edge_family.get()), variant=int(self.edge_variant.get()),
                     remove=self.edge_action.get() == 'Remove')

    def pick_edge(self):
        record = self.viewer.map_layers.edges.get(self.viewer.selected_hex, bytes(8))
        d = DIRECTIONS.index(self.edge_direction.get())
        if struct.unpack_from('<H', record)[0] & 1 << d and record[2+d] >> 4 < 5 and record[2+d] & 15 < 3:
            self.edge_family.set(EDGE_FAMILIES[record[2+d] >> 4])
            self.edge_variant.set(record[2+d] & 15)

    def _region(self, frame):
        self.region_label = ttk.Label(frame, text='No region selected.', wraplength=255)
        self.region_label.pack(anchor=tk.W, pady=5)
        self._button(frame, 'Select region (two corners)', self.select_region)
        self._button(frame, 'Copy selected region', self.copy)
        self.copy_owner = tk.BooleanVar(value=False)
        ttk.Checkbutton(frame, text='Also paste ownership', variable=self.copy_owner).pack(anchor=tk.W, pady=4)
        self.copy_units = tk.BooleanVar(value=False)
        self.copy_objectives = tk.BooleanVar(value=False)
        self.copy_places = tk.BooleanVar(value=False)
        for text, var in (('Also copy units / HQs', self.copy_units),
                          ('Also copy objectives', self.copy_objectives), ('Also copy place names', self.copy_places)):
            ttk.Checkbutton(frame, text=text, variable=var).pack(anchor=tk.W, pady=3)
        self._button(frame, 'Paste on map', lambda: self.panel.set_mode('Paste'))
        self._button(frame, 'Paste at selected hex', self.paste)
        self.clipboard_label = ttk.Label(frame, text='Clipboard empty.', wraplength=255)
        self.clipboard_label.pack(anchor=tk.W, pady=5)
        self._button(frame, 'Paint region with terrain brush', self.paint_region)
        self._button(frame, 'Paint region with chosen owner', self.own_region)
        self._button(frame, 'Clear region selection', self.clear_region)
        ttk.Separator(frame).pack(fill=tk.X, pady=8)
        self._button(frame, 'Flood fill with terrain brush', self.fill_terrain)
        ttk.Label(frame, text='Choose the brush on Terrain. Fill matches base terrain, across all variants. '
                  'Paste always includes terrain, connections, hilltops and edge artwork. Checked items are added '
                  'from the copied snapshot; existing units, objectives and names remain. Copied units keep their '
                  'arrival times and chits, with fresh orders and no leader or mounted passengers.',
                  wraplength=255).pack(anchor=tk.W, pady=8)

    def brush(self):
        return dict(terrain=self.panel.terrain_choices[self.panel.terrain_combo.current()],
                    variant=int(self.panel.variant_combo.get()))

    def select_region(self):
        self.first = self.last = None
        self.hover = None
        self.panel.set_mode('Region')
        self.refresh()

    def clear_region(self):
        self.first = self.last = None
        self.hover = None
        self.panel.set_mode('Select')
        self.refresh()

    def region_cells(self):
        return rectangle(self.first, self.last) if self.first is not None and self.last is not None else []

    def copy(self):
        if self.region_cells() and self.on_tool:
            self.clipboard = self.on_tool('copy', first=self.first, last=self.last)
            self.refresh()

    def paste(self):
        if self.clipboard:
            self._at_hex('paste', region=self.clipboard, ownership=self.copy_owner.get(),
                         units=self.copy_units.get(), objectives=self.copy_objectives.get(), places=self.copy_places.get())
        else:
            self.panel.hint.config(text='Select two corners and copy a region first.')

    def paint_region(self):
        if self.region_cells() and self.on_tool:
            self.on_tool('terrain_region', cells=self.region_cells(), **self.brush())

    def own_region(self):
        if self.region_cells() and self.on_tool:
            self.on_tool('ownership', cells=self.region_cells(), owner=self.owner_value())

    def fill_terrain(self):
        self._at_hex('fill_terrain', **self.brush())

    def _resize(self, frame):
        self.resize_current = ttk.Label(frame, wraplength=255)
        self.resize_current.pack(anchor=tk.W, pady=4)
        self.width = self._field(frame, 'Columns', self.viewer.map_width)
        self.height = self._field(frame, 'Rows', self.viewer.map_height)
        self.new_owner = self._field(frame, 'New hex ownership', 'Allied', ('Allied', 'Axis'))
        self._button(frame, 'Use current dimensions', self.current_dimensions)
        self._button(frame, 'Resize map', self.resize)
        ttk.Label(frame, text='Keeps the upper-left origin and existing coordinates. Adds or removes rows at the bottom '
                  'and columns at the right. New hexes use the Terrain brush. Dimensions include one boundary row '
                  'and column. Move units, objectives, names and other marked locations out of a crop first.',
                  wraplength=255).pack(anchor=tk.W, pady=8)

    def current_dimensions(self):
        self.width.set(self.viewer.map_width)
        self.height.set(self.viewer.map_height)

    def resize(self):
        if self.on_tool:
            self.on_tool('resize', width=self.width.get(), height=self.height.get(),
                         owner=int(self.new_owner.get() == 'Axis'), **self.brush())

    def _formation(self, frame):
        self.formation = self._field(frame, 'HQ formation', values=())
        self.formation_choices = {}
        self.formation_children = tk.BooleanVar(value=True)
        self.formation_goals = tk.BooleanVar(value=True)
        ttk.Checkbutton(frame, text='Include subordinate HQ formations', variable=self.formation_children).pack(anchor=tk.W, pady=7)
        ttk.Checkbutton(frame, text='Move Battle Plan goals and garrisons', variable=self.formation_goals).pack(anchor=tk.W, pady=7)
        self.formation_target = ttk.Label(frame, wraplength=270)
        self.formation_target.pack(anchor=tk.W, pady=8)
        self._button(frame, 'Move HQ to selected hex', self.move_formation)
        ttk.Label(frame, text='Select a destination on the map. Moves the HQ and its assigned ground units '
                  'by the same hex offset, including scheduled entry locations. Arrival times, leaders and '
                  'valid movement routes stay attached. Off-map units stay off map. Supply locations stay fixed.',
                  wraplength=270).pack(anchor=tk.W, pady=8)

    def move_formation(self):
        choice = self.formation_choices.get(self.formation.get())
        if choice and self.viewer.selected_hex is not None and self.on_tool:
            self.on_tool('formation', side=choice[0], hq=choice[1], destination=self.viewer.selected_hex,
                         descendants=self.formation_children.get(), move_goals=self.formation_goals.get())
        else:
            self.panel.hint.config(text='Choose an HQ and select a destination hex first.')

    def _shift(self, frame):
        self.shift_x = self._field(frame, 'Shift columns (+ right, − left)', 0)
        self.shift_y = self._field(frame, 'Shift rows (+ down, − up)', 0)
        self.shift_width = self._field(frame, 'Resulting columns', self.viewer.map_width)
        self.shift_height = self._field(frame, 'Resulting rows', self.viewer.map_height)
        self.shift_owner = self._field(frame, 'New hex ownership', 'Allied', ('Allied', 'Axis'))
        self._button(frame, 'Use current dimensions', self.current_shift_dimensions)
        self._button(frame, 'Shift map and all locations', self.shift_map)
        ttk.Label(frame, text='Moves terrain, units and entry locations, objectives, names, supply, garrisons, '
                  'naval markers and AI goals together. Increase dimensions to make room. Uncovered hexes use '
                  'the Terrain brush. Terrain outside the new grid is discarded; an operation that strands a '
                  'scenario location or route is rejected. Odd-row shifts stagger columns to preserve hex connections.',
                  wraplength=270).pack(anchor=tk.W, pady=8)

    def current_shift_dimensions(self):
        self.shift_width.set(self.viewer.map_width)
        self.shift_height.set(self.viewer.map_height)

    def shift_map(self):
        if self.on_tool:
            self.on_tool('shift', dx=self.shift_x.get(), dy=self.shift_y.get(),
                         width=self.shift_width.get(), height=self.shift_height.get(),
                         owner=int(self.shift_owner.get() == 'Axis'), **self.brush())

    def _at_hex(self, operation, **kwargs):
        if self.viewer.selected_hex in self.viewer.terrain and self.on_tool:
            return self.on_tool(operation, cell=self.viewer.selected_hex, **kwargs)
        self.panel.hint.config(text='Select a hex on the map first.')

    def click_hex(self, cell, direction):
        mode = self.panel.mode.get()
        if mode == 'Ownership':
            self.apply_owner()
        elif mode == 'Edges':
            if direction is not None:
                self.edge_direction.set(DIRECTIONS[direction])
            self.apply_edge()
        elif mode == 'Region':
            if self.first is None or self.last is not None:
                self.first, self.last = cell, None
            else:
                self.last = cell
        elif mode == 'Paste':
            self.paste()
        self.refresh()

    def preview_cells(self):
        target = self.hover or self.viewer.selected_hex
        if self.panel.mode.get() == 'Paste' and self.clipboard and target:
            return [translate_cell(c, self.clipboard['origin'], target) for c in self.clipboard['cells']]
        if self.panel.mode.get() == 'Region' and self.first and self.last is None and self.hover:
            return rectangle(self.first, self.hover)
        return self.region_cells() or ([self.first] if self.first else [])

    def refresh(self):
        places = self.viewer.map_layers.places
        changed = places != self.loaded_places
        self.loaded_places = [dict(p) for p in places]
        rows = [f"{p['name']} ({p['x']}, {p['y']})" for p in places]
        if list(self.place_list.get(0, tk.END)) != rows:
            self.place_list.delete(0, tk.END)
            for row in rows:
                self.place_list.insert(tk.END, row)
        if self.place_index is not None:
            if self.place_index < len(places):
                self.place_list.selection_set(self.place_index)
                if changed:
                    self._load_place_fields(places[self.place_index])
            else:
                self.new_place()
        cell = self.viewer.selected_hex
        owner = self.viewer.map_layers.ownership.get(cell)
        self.owner_at_hex.config(text='Selected hex: '+(('Allied', 'Axis')[owner] if owner is not None else '—'))
        count = len(self.region_cells())
        self.blend_region_button.config(state='normal' if count else 'disabled')
        self.region_label.config(text=(f'{self.first} to {self.last} · {count} hexes' if count else
                                      f'First corner: {self.first}. Choose the second.' if self.first else 'No region selected.'))
        counts = self.clipboard.get('counts', {}) if self.clipboard else {}
        self.clipboard_label.config(text=(f"Copied {len(self.clipboard['cells'])} hexes · "
            f"{counts.get('units', 0)} ground units · {counts.get('objectives', 0)} objectives · "
            f"{counts.get('places', 0)} place names." if self.clipboard else 'Clipboard empty.'))
        self.resize_current.config(text=f'Current grid: {self.viewer.map_width} × {self.viewer.map_height}')
        self.formation_choices = {
            f"{u['side']} · {u['hq_index']+1}: {u['name']}": (int(u['side'] == 'Axis'), u['hq_index'])
            for u in self.viewer.units if u['unit_class'] == 7 and not u['deleted']}
        combo = next(w for w in self.frames['Move formation'].winfo_children() if isinstance(w, ttk.Combobox))
        combo.config(values=tuple(self.formation_choices))
        if self.formation.get() not in self.formation_choices:
            self.formation.set(next(iter(self.formation_choices), ''))
        self.formation_target.config(text=f'Chosen HQ destination: {cell}' if cell is not None else 'Select a destination hex on the map.')
        brush = self.brush()
        self.brush_label.config(text=f"Terrain brush: {terrain_name(brush['terrain'])} · variant {brush['variant']}")
        self.refresh_edge()

    def reset(self):
        self.first = self.last = self.clipboard = self.place_index = None
        self.hover = None
        self.loaded_places = []
        self.new_place()
        self.current_dimensions()
        self.current_shift_dimensions()
        self.shift_x.set(0)
        self.shift_y.set(0)
