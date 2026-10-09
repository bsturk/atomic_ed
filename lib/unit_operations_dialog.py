"""Supply, transport and native plotted orders for the Units page."""
import struct
import tkinter as tk
from tkinter import ttk, messagebox

from lib.unit_roster import UnitRoster, short
from lib.unit_reader import decode_record, read_units, unit_order_label
from lib.scenario_parser import DdayScenario
from lib.map_editor import hex_neighbor
from lib.unit_operations import (SUPPLY_LEVELS, ORDER_CHOICES, ROUTE_MODES,
                                 supply_state, edit_supply, transport_groups,
                                 edit_transport, dismount_all, saved_orders, edit_orders,
                                 SECONDARY_CHOICES, secondary_choices, hex_distance)


class UnitOperationsDialog(tk.Toplevel):
    def __init__(self, app, page='Orders'):
        super().__init__(app.root)
        self.app = app
        self.unit = dict(app.unit_props_editor.current_unit)
        self.side = int(self.unit['side'] == 'Axis')
        self.index = self.unit['side_index']
        self.title(f"Supply, transport and orders — {self.unit['name']}")
        self.transient(app.root)
        self.geometry('1000x730')
        self.minsize(760, 600)
        self.book = ttk.Notebook(self)
        self.book.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        self.pages = {}
        for name in ('Supply', 'Transport', 'Orders'):
            frame = ttk.Frame(self.book, padding=10)
            self.book.add(frame, text=name)
            self.pages[name] = frame
        self.build_supply()
        self.build_transport()
        self.build_orders()
        bottom = ttk.Frame(self, padding=(10, 0, 10, 10))
        bottom.pack(side=tk.BOTTOM, fill=tk.X, before=self.book)
        self.feedback = ttk.Label(bottom)
        self.feedback.pack(side=tk.LEFT)
        ttk.Button(bottom, text='Close', command=self.destroy).pack(side=tk.RIGHT)
        self.reload()
        self.feedback.config(text='Apply each page to keep changes. Close discards unapplied edits.')
        self.book.select(self.pages[page])
        self.grab_set()

    def data(self):
        return self.app._staged_data(include_briefings=False)

    def build_supply(self):
        body = self.pages['Supply']
        body.columnconfigure(1, weight=1)
        self.supply_fields = {}
        for row, (key, title) in enumerate((('carried', 'Unit carried supply (tons)'),
                                           ('reserve', 'HQ reserve (tons)'),
                                           ('distribution', 'Limit distributed to subordinate HQs (tons)'))):
            ttk.Label(body, text=title).grid(row=row, column=0, sticky=tk.W, pady=8)
            field = ttk.Entry(body, width=18)
            field.grid(row=row, column=1, sticky=tk.W, padx=12)
            self.supply_fields[key] = field
        ttk.Label(body, text='Initial supply level').grid(row=3, column=0, sticky=tk.W, pady=8)
        self.supply_level = ttk.Combobox(body, values=SUPPLY_LEVELS, state='readonly', width=18)
        self.supply_level.grid(row=3, column=1, sticky=tk.W, padx=12)
        self.apply_members = tk.BooleanVar(self, False)
        self.member_check = ttk.Checkbutton(body, text='Apply level to eligible direct subordinate units',
                                            variable=self.apply_members)
        self.member_check.grid(row=4, column=0, columnspan=2, sticky=tk.W, pady=8)
        ttk.Label(body, text='The game recalculates supply levels from available stock and connections. '
                  'Changing the level does not create supplies.', wraplength=690).grid(
                      row=5, column=0, columnspan=2, sticky=tk.W, pady=8)
        self.supply_calculated = ttk.Label(body, wraplength=700, justify=tk.LEFT)
        self.supply_calculated.grid(row=6, column=0, columnspan=2, sticky=tk.W, pady=12)
        ttk.Button(body, text='Apply Supply', command=self.submit_supply).grid(row=7, column=0, sticky=tk.W, pady=12)

    def build_transport(self):
        body = self.pages['Transport']
        self.transport_info = ttk.Label(body, wraplength=850, justify=tk.LEFT)
        self.transport_info.pack(anchor=tk.W, pady=8)
        self.carrier = ttk.Combobox(body, state='readonly', width=64)
        self.carrier.pack(anchor=tk.W, pady=8)
        self.mount = ttk.Button(body, text='Apply Carrier / Dismount', command=self.submit_transport)
        self.mount.pack(anchor=tk.W, pady=8)
        self.unload = ttk.Button(body, text='Dismount All Passengers', command=self.submit_unload)
        self.unload.pack(anchor=tk.W, pady=8)
        ttk.Label(body, text='Foot infantry and engineers can ride armor in the same hex. '
                  'A carrier mounts one larger unit or two size-1 units, totaling at most three size points; '
                  'each passenger must be no larger than its carrier. Mounting clears the passenger’s route.',
                  wraplength=800).pack(anchor=tk.W, pady=18)
        ttk.Label(body, text='Motorized HQ movement is configured under Unit Definition → Movement class.',
                  wraplength=800).pack(anchor=tk.W)

    def build_orders(self):
        # Reuse the running application's widget, including when the script
        # was launched as __main__ (avoid importing a second application module).
        MapViewer = type(self.app.map_viewer)
        dialog = self

        class RouteMap(MapViewer):
            def redraw(self):
                super().redraw()
                points = [self.hex_to_pixel(*cell) for cell in getattr(dialog, 'path', [])
                          if cell in self.terrain]
                if len(points) > 1:
                    coords = [v for point in points for v in point]
                    self.canvas.create_line(*coords, fill='black', width=6)
                    self.canvas.create_line(*coords, fill='#ffec3d', width=3, arrow=tk.LAST)
                for i, (x, y) in enumerate(points):
                    self.canvas.create_oval(x-4, y-4, x+4, y+4, fill='#ffec3d', outline='black')
                    if i in (0, len(points)-1):
                        self.canvas.create_text(x, y-12, text='Start' if i == 0 else str(i),
                                                fill='white', font=('TkDefaultFont', 10, 'bold'))
                try:
                    target = dialog.fire_target()
                except ValueError:
                    target = None
                if target in self.terrain:
                    x, y = self.hex_to_pixel(*target)
                    self.canvas.create_oval(x-12, y-12, x+12, y+12, outline='black', width=5)
                    self.canvas.create_oval(x-12, y-12, x+12, y+12, outline='#ffdf42', width=2)
                    self.canvas.create_line(x-18, y, x+18, y, fill='#ffdf42', width=2)
                    self.canvas.create_line(x, y-18, x, y+18, fill='#ffdf42', width=2)

            def _on_map_release(self, event):
                if not hasattr(self, '_press_point'):
                    return
                dragged = self._dragged
                del self._press_point
                if not dragged:
                    dialog.map_click(self.pixel_to_hex(self.canvas.canvasx(event.x), self.canvas.canvasy(event.y)))

        body = self.pages['Orders']
        top = ttk.Frame(body)
        top.pack(fill=tk.X)
        ttk.Label(top, text='Order:').pack(side=tk.LEFT)
        self.mode = ttk.Combobox(top, values=list(ORDER_CHOICES.values()), state='readonly', width=27)
        self.mode.pack(side=tk.LEFT, padx=8)
        self.mode.bind('<<ComboboxSelected>>', lambda _: self.update_route_status())
        ttk.Button(top, text='Back One Step', command=self.back_step).pack(side=tk.LEFT, padx=4)
        ttk.Button(top, text='Clear → Defend', command=self.clear_route).pack(side=tk.LEFT, padx=4)
        self.apply_orders = ttk.Button(top, text='Apply Orders', command=self.submit_orders)
        self.apply_orders.pack(side=tk.RIGHT)
        secondary = ttk.Frame(body)
        secondary.pack(fill=tk.X, pady=(8, 0))
        ttk.Label(secondary, text='Secondary:').pack(side=tk.LEFT)
        self.secondary = ttk.Combobox(secondary, state='readonly', width=22)
        self.secondary.pack(side=tk.LEFT, padx=8)
        self.secondary.bind('<<ComboboxSelected>>', self.select_secondary)
        self.gun_controls = ttk.Frame(secondary)
        self.gun_controls.pack(side=tk.LEFT)
        ttk.Label(self.gun_controls, text='Preparation remaining:').pack(side=tk.LEFT)
        self.preparation = ttk.Spinbox(self.gun_controls, from_=0, to=18, width=4)
        self.preparation.pack(side=tk.LEFT, padx=4)
        ttk.Label(self.gun_controls, text='turns').pack(side=tk.LEFT)
        self.target_controls = ttk.Frame(body)
        self.target_controls.pack(fill=tk.X, pady=6)
        ttk.Label(self.target_controls, text='Fire target: X').pack(side=tk.LEFT)
        self.target_x, self.target_y = tk.StringVar(self), tk.StringVar(self)
        ttk.Entry(self.target_controls, textvariable=self.target_x, width=5).pack(side=tk.LEFT, padx=4)
        ttk.Label(self.target_controls, text='Y').pack(side=tk.LEFT)
        ttk.Entry(self.target_controls, textvariable=self.target_y, width=5).pack(side=tk.LEFT, padx=4)
        ttk.Button(self.target_controls, text='Clear Target', command=self.clear_target).pack(side=tk.LEFT, padx=8)
        ttk.Label(self.target_controls, text='Or click a hex on the map.').pack(side=tk.LEFT)
        self.order_info = ttk.Label(body, wraplength=880)
        self.order_info.pack(anchor=tk.W, pady=6)
        self.order_hint = ttk.Label(body, wraplength=880)
        self.order_hint.pack(anchor=tk.W)
        self.route_status = ttk.Label(body, wraplength=880)
        self.route_status.pack(anchor=tk.W, pady=6)
        self.path = []
        self.viewer = RouteMap(body)
        self.viewer.pack(fill=tk.BOTH, expand=True)
        self.viewer.hex_tile_loader.artwork = dict(self.app.terrain_artwork)
        for variable in (self.target_x, self.target_y):
            variable.trace_add('write', lambda *_: self.update_route_status())

    def reload(self):
        self.roster = UnitRoster(self.data())
        self.record = self.roster.records[self.side][self.index]
        state = supply_state(self.roster, self.side, self.index)
        for key, field in self.supply_fields.items():
            field.config(state='normal')
            field.delete(0, tk.END)
            if key in state:
                field.insert(0, f'{state[key]:.2f}')
            else:
                field.config(state='disabled')
        self.supply_level.set(SUPPLY_LEVELS[state['level']] if state['level'] < 5 else f"Unknown ({state['level']})")
        self.member_check.config(state='normal' if state['hq'] else 'disabled')
        self.apply_members.set(False)
        source = state.get('source')
        description = {-1: 'Direct supply', -2: 'Parent HQ', -4: 'Unavailable'}.get(source, f'Depot {source}')
        calculated = f"Calculated connection status: {state['path']}" + (' (no connection)' if state['path'] == 4 else '')
        if state['hq']:
            calculated += (f"\nSupply source: {description} · Entry group: {state['entry']}"
                           f"\nCalculated request: {state['request']:.2f} tons"
                           f"\nNet received/transferred: {state['received']:.2f} tons"
                           f"\nConsumed this accounting period: {state['consumed']} tons")
        self.supply_calculated.config(text=calculated)
        self.reload_transport()
        error = ''
        try:
            orders = saved_orders(self.roster, self.side, self.index)
            self.path, self.route_limit = orders['path'], orders['limit']
        except ValueError as exc:
            self.path = [struct.unpack_from('<2h', self.record, 0x58)]
            self.route_limit = max(0, min(255, struct.unpack_from('<H', self.record, 0x52)[0]-1))
            error = f' Cannot preview: {exc} Clear or replace the route to repair it.'
        mode = self.record[0x78] & 15
        self.mode.set(ORDER_CHOICES.get(mode, 'Choose an order'))
        self.secondary_options = secondary_choices(self.roster, self.side, self.index)
        self.secondary.config(values=list(self.secondary_options.values()))
        modifier = self.record[0x78] >> 4
        self.secondary.set(SECONDARY_CHOICES.get(modifier, f'Unknown ({modifier})'))
        self.set_target(orders['fire_target'] if not error else None)
        if self.record[0x76] == 4:
            aux = struct.unpack_from('<i', self.record, 4)[0]*28
            self.preparation.set(self.roster.blocks[f'arty{self.side}'][aux+0x12])
        else:
            self.preparation.set('0')
        target = struct.unpack_from('<2h', self.record, 0x5c)
        automatic = struct.unpack_from('<2h', self.record, 0x60)
        self.order_info.config(text=f'Saved: {unit_order_label(decode_record(self.record))} · Target {target} · '
                               f'Automatic goal {automatic}.'+error)
        passenger = mode == 2 or (self.record[0x91] and self.record[0x76] != 1)
        self.apply_orders.config(state='disabled' if passenger else 'normal')
        scenario = DdayScenario.from_bytes(self.data(), 'orders.SCN')
        self.viewer.load_data(read_units(scenario, self.app.counter_artwork), scenario)
        self.update_order_controls()
        self.update_route_status()

    def reload_transport(self):
        self.carrier_ids = [None]
        labels = ['Dismounted']
        selected = None
        try:
            groups = transport_groups(self.roster, self.side)
            cls, mobility = self.record[0x76], self.record[0x79]
            rider = cls in (0, 2) and mobility == 0
            for index, passengers in groups.items():
                if self.index in passengers:
                    selected = index
            if rider:
                for index, unit in enumerate(self.roster.records[self.side]):
                    if unit[0x76] != 1 or not index or decode_record(unit)['deleted']:
                        continue
                    if unit[0x58:0x5c] != self.record[0x58:0x5c] and index != selected:
                        continue
                    self.carrier_ids.append(index)
                    size = sum(self.roster.records[self.side][i][0x7e] for i in groups.get(index, []))
                    labels.append(f'{index+1}: {decode_record(unit)["name"]} · load {size}/3 · size {unit[0x7e]}')
            names = [decode_record(self.roster.records[self.side][i])['name'] for i in groups.get(self.index, [])]
            info = ('Passengers: '+(', '.join(names) or 'None') if cls == 1 else
                    'Select armor in this hex, or choose Dismounted.' if rider else
                    'This unit does not use the infantry-on-armor transport system.')
            self.mount.config(state='normal' if rider else 'disabled')
            self.unload.config(state='normal' if names else 'disabled')
            self.carrier.config(state='readonly' if rider else 'disabled')
        except ValueError as exc:
            info = f'Cannot edit this side’s transport links: {exc}'
            self.mount.config(state='disabled')
            self.unload.config(state='disabled')
            self.carrier.config(state='disabled')
        self.carrier.config(values=labels)
        self.carrier.current(self.carrier_ids.index(selected))
        self.transport_info.config(text=info)

    def apply(self, operation, label, **kwargs):
        # Applying one page must not throw away work typed on another page.
        supply_draft = {k: field.get() for k, field in self.supply_fields.items()}
        level_draft, members_draft = self.supply_level.get(), self.apply_members.get()
        route_draft, mode_draft = list(self.path), self.mode.get()
        secondary_draft = (self.secondary.get(), self.target_x.get(), self.target_y.get(), self.preparation.get())
        carrier_draft = self.carrier.get()
        try:
            before = self.data()
            data = operation(before, self.side, self.index, **kwargs)
            self.app.apply_unit_structure(data, self.side, self.index, label)
        except (ValueError, IndexError, struct.error) as exc:
            messagebox.showerror('Cannot apply changes', str(exc), parent=self)
            return False
        self.reload()
        if operation is not edit_supply:
            for key, field in self.supply_fields.items():
                if str(field.cget('state')) != 'disabled':
                    field.delete(0, tk.END)
                    field.insert(0, supply_draft[key])
            self.supply_level.set(level_draft)
            self.apply_members.set(members_draft)
        if operation is edit_supply:
            self.path = route_draft
            self.mode.set(mode_draft)
            self.secondary.set(secondary_draft[0])
            self.target_x.set(secondary_draft[1])
            self.target_y.set(secondary_draft[2])
            self.preparation.set(secondary_draft[3])
            self.update_order_controls()
            self.update_route_status()
        if operation in (edit_supply, edit_orders) and carrier_draft in self.carrier.cget('values'):
            self.carrier.set(carrier_draft)
        self.feedback.config(text=f'{label}. Use File → Save.' if before != data else 'No changes.')
        return True

    def submit_supply(self):
        fields = {k: v.get() for k, v in self.supply_fields.items() if str(v.cget('state')) != 'disabled'}
        # Unknown original levels survive edits to quantities.
        level = self.supply_level.current()
        self.apply(edit_supply, 'Updated unit supply', **fields,
                   level=level if level >= 0 else None, apply_members=self.apply_members.get())

    def submit_transport(self):
        choice = self.carrier.current()
        if choice >= 0:
            self.apply(edit_transport, 'Updated mounted transport', carrier=self.carrier_ids[choice])

    def submit_unload(self):
        self.apply(dismount_all, 'Dismounted passengers')

    def add_step(self, cell):
        if self.secondary.get() != SECONDARY_CHOICES[0]:
            self.route_status.config(text='Choose secondary order None before plotting a movement route.')
            return
        if cell == self.path[0]:
            self.path = self.path[:1]
        elif len(self.path)-1 >= self.route_limit:
            self.route_status.config(text=f'This unit can store at most {self.route_limit} steps.')
            return
        elif not (0 <= cell[0] < self.viewer.map_width-1 and 0 <= cell[1] < self.viewer.map_height-1):
            self.route_status.config(text='Choose a playable hex inside the map boundary.')
            return
        elif cell not in [hex_neighbor(self.path[-1], d) for d in range(6)]:
            self.route_status.config(text='Choose a hex adjacent to the end of the route.')
            return
        else:
            self.path.append(cell)
            if self.mode.current() < 0 or list(ORDER_CHOICES)[self.mode.current()] not in ROUTE_MODES:
                self.mode.set(ORDER_CHOICES[0])
        self.update_route_status()

    def back_step(self):
        self.path = self.path[:max(1, len(self.path)-1)]
        self.update_route_status()

    def clear_route(self):
        self.path = self.path[:1]
        self.mode.set(ORDER_CHOICES[9])
        self.secondary.set(SECONDARY_CHOICES[0])
        self.set_target(None)
        self.update_order_controls()
        self.update_route_status()

    def secondary_value(self):
        return next((i for i, label in SECONDARY_CHOICES.items() if label == self.secondary.get()), None)

    def select_secondary(self, event=None):
        modifier = self.secondary_value()
        if modifier:
            self.path = self.path[:1]
            if modifier not in (2, 3) or self.mode.get() not in [ORDER_CHOICES[i] for i in (8, 9, 10)]:
                self.mode.set(ORDER_CHOICES[9])
        if modifier not in (5, 8):
            self.set_target(None)
        if modifier == 4 and self.preparation.get() == '0':
            aux = struct.unpack_from('<i', self.record, 4)[0]*28
            self.preparation.set(max(1, self.roster.blocks[f'arty{self.side}'][aux+0x10]))
        self.update_order_controls()
        self.update_route_status()

    def update_order_controls(self):
        modifier = self.secondary_value()
        if self.record[0x76] == 4:
            self.gun_controls.pack(side=tk.LEFT)
        else:
            self.gun_controls.pack_forget()
        if modifier in (5, 8):
            self.target_controls.pack(fill=tk.X, pady=6, before=self.order_info)
        else:
            self.target_controls.pack_forget()
        hints = {
            0: 'Click adjacent hexes to plot a route; click Start to restart. Drag to pan; wheel to zoom.',
            1: 'Requests replacements during play. Available replacement stock, losses and supply determine what the unit receives.',
            2: 'Builds improved positions during play. Terrain, nearby enemies and supply can prevent progress.',
            3: 'Builds fortifications during play. Terrain, nearby enemies and supply can prevent progress.',
            4: 'Artillery deploys before firing. Set the number of preparation turns remaining (1–18).',
            5: 'Choose a bombardment hex, or leave the target blank to start ready without a plotted mission.',
            6: 'Automatically supports friendly battles within range; no target hex is needed.',
            7: 'Automatically engages enemy artillery; no target hex is needed.',
            8: 'Bombards the selected hex and then displaces. Requires Shoot ’n scoot capability in Unit Definition.',
        }
        self.order_hint.config(text=hints.get(modifier, 'Existing unknown orders are preserved until explicitly replaced.'))

    def fire_target(self):
        if self.secondary_value() not in (5, 8):
            return None
        x, y = self.target_x.get().strip(), self.target_y.get().strip()
        if not x and not y:
            return None
        try:
            return int(x), int(y)
        except ValueError as exc:
            raise ValueError('Enter both fire-target coordinates, or clear both.') from exc

    def set_target(self, target):
        self.target_x.set('' if target is None else str(target[0]))
        self.target_y.set('' if target is None else str(target[1]))

    def clear_target(self):
        self.set_target(None)

    def map_click(self, cell):
        if self.secondary_value() in (5, 8):
            if 0 <= cell[0] < self.viewer.map_width-1 and 0 <= cell[1] < self.viewer.map_height-1:
                self.set_target(cell)
            else:
                self.route_status.config(text='Choose a playable hex inside the map boundary.')
        else:
            self.add_step(cell)

    def update_route_status(self):
        if not self.path:
            return
        if self.secondary_value() in (5, 8):
            try:
                target = self.fire_target()
                aux = struct.unpack_from('<i', self.record, 4)[0]*28
                reach = self.roster.blocks[f'arty{self.side}'][aux+0x11]
                text = (f'Target {target} · Distance {hex_distance(self.path[0], target)} / {reach} hexes.'
                        if target else f'No plotted fire target · Range {reach} hexes.')
            except (ValueError, IndexError):
                text = 'Enter both target coordinates, or click a hex.'
        else:
            text = f'{len(self.path)-1} / {self.route_limit} steps · Destination {self.path[-1]}.'
        self.route_status.config(text=text+' Apply Orders to keep changes.')
        self.viewer.redraw()

    def submit_orders(self):
        choice = self.mode.current()
        if choice < 0:
            messagebox.showerror('Choose an order', 'Choose a movement order or defensive stance.', parent=self)
            return
        try:
            preparation = int(self.preparation.get()) if self.record[0x76] == 4 else None
            target = self.fire_target()
        except ValueError as exc:
            messagebox.showerror('Cannot apply orders', str(exc), parent=self)
            return
        self.apply(edit_orders, 'Updated saved orders', path=self.path, mode=list(ORDER_CHOICES)[choice],
                   modifier=self.secondary_value(), target=target, preparation=preparation)
