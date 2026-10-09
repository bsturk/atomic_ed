#!/usr/bin/env python3
"""
D-Day Scenario Editor
=============================================

A comprehensive scenario editor for D-Day scenarios with both high-level editing
and advanced visualization capabilities.

Features:
- Interactive hex map viewer (125×100 grid) with zoom/pan
- Terrain visualization with 17 terrain types
- Structured unit editing (add/edit/delete units) with detailed properties
- Scenario settings editor (turns, objectives, etc.)
- Mission text editing (Allied & Axis)
- Coordinate interpretation and visualization
- Enhanced unit parsing with type names and combat stats

Usage:
    python3 scenario_editor.py [scenario_file.scn]
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext, font as tkfont
from pathlib import Path
import struct
import shutil
import re
import math
import json
import os
from collections import Counter
from datetime import datetime
from PIL import Image, ImageTk
from lib.scenario_parser import DdayScenario
from lib.terrain_reader import (
    read_map_layers,
    MapLayers,
    terrain_name,
)
from lib.hex_tile_loader import HexTileLoader
from lib.game_art import unit_counter, support_unit_icon
from lib.game_resources import GAME_ROOT
from lib.unit_reader import (
    read_units, unit_status, prepare_unit_changes, unit_arrival_label, arrival_time_from_form,
    unit_order_label, HQ_AUTOMATION_FIELDS,
)
from lib.unit_types import unit_type_name
from lib.unit_roster import UnitRoster
from lib.unit_definitions import edit_definition, transfer_unit, refresh_command_spans
from lib.unit_definition_dialogs import OrganizationDialog, UnitDefinitionDialog
from lib.briefing_reader import read_briefings, prepare_briefing_changes
from lib.map_editor import prepare_map_unit_changes, edit_map_feature
from lib.map_controls import MapEditingPanel
from lib.map_tools import (edit_place_name, paint_ownership, edit_cosmetic_edge, copy_region,
                           paste_region, flood_terrain, flood_ownership, resize_map,
                           blend_terrain_edges, paint_blended_terrain)
from lib.bulk_edit import move_formation, shift_map
from lib.terrain_catalog import terrain_catalog, artwork_catalog, ART_SOURCES
from lib.terrain_artwork import (TerrainStamp, load_artwork, automatic_artwork_slot,
                                 validate_slot, artwork_path)
from lib.scenario_assets import (save_scenario_assets, runtime_slot_for, GAME_SCENARIOS,
                                 scenario_title, export_for_dos, engine_slot, conversion_report)
from lib.scenario_import import source_game, convert_scenario
from lib.counter_artwork import load_counters, counter_path, allocate_counter
from lib.presentation_artwork import load_presentation, presentation_path, validate_artwork, slot_for
from lib.artwork_panel import ArtworkPanel
from lib.unit_library import unit_library, library_template, template_choices
from lib.terrain_dialog import TerrainImportDialog
from lib.scenario_dialogs import ScenarioSettingsEditor, NewScenarioDialog, CounterDialog
from lib.scenario_rules import synchronize_occupancy, authoring_warnings
from lib.modification_tracker import ModificationTracker, ModificationType
from lib.game_profiles import ScenarioDocument, GameProfile, load_document
from lib.edit_history import DocumentState, EditHistory
from lib.history_dialog import HistoryWindow
from lib.form_drafts import FormDraft, field_variable, ask_save_changes


def format_unit_value(value):
    """Keep stored fractional strength points without inventing effective stats."""
    return f'{value:.3f}'.rstrip('0').rstrip('.')


class EnhancedUnitParser:
    """Enhanced parser for unit data with better structure understanding"""

    @staticmethod
    def get_unit_type_name(type_code, unit_class=None):
        return unit_type_name(type_code, unit_class)

    @staticmethod
    def parse_units_from_scenario(scenario):
        """Read the game's two order-of-battle blocks, including reinforcements."""
        return read_units(scenario)

    @staticmethod
    def parse_coordinates_from_ptr5(data):
        """Parse coordinate/numeric data from PTR5 with interpretation"""
        coords = []

        if not data:
            return coords

        # Parse as 16-bit values
        for i in range(0, min(len(data), 512), 2):
            if i + 2 <= len(data):
                value = struct.unpack('<H', data[i:i+2])[0]

                # Skip runs of zeros
                if value == 0:
                    continue

                # Interpret possible coordinate ranges
                # D-Day maps are typically grid-based, values might be:
                # - Grid coordinates (0-255 range)
                # - Pixel coordinates (larger values)
                # - Strength values (0-100 range)

                interpretation = "unknown"
                if 0 < value <= 100:
                    interpretation = "strength/percentage"
                elif 100 < value <= 500:
                    interpretation = "grid coordinate"
                elif 500 < value <= 10000:
                    interpretation = "pixel coordinate"
                else:
                    interpretation = "large value/offset"

                coords.append({
                    'offset': i,
                    'value': value,
                    'hex': f'{value:04x}',
                    'interpretation': interpretation
                })

        return coords


class MapViewer(ttk.Frame):
    """Interactive hex map viewer for D-Day scenarios"""

    # Default map constants (will be overridden by scenario data)
    DEFAULT_MAP_WIDTH = 125   # hexes (columns/X axis)
    DEFAULT_MAP_HEIGHT = 100  # hexes (rows/Y axis)
    HEX_SIZE = 12     # initial hex radius in pixels

    def __init__(self, parent, on_terrain_edit=None, on_unit_place=None, on_undo=None, on_feature_edit=None,
                 on_map_tool=None):
        super().__init__(parent)

        # Map state
        self.hex_size = self.HEX_SIZE
        self.offset_x = 50
        self.offset_y = 50
        self._scroll_geometry = None
        self._center_pending = True
        self._center_on_resize = True
        self._redraw_timers = set()
        self.show_grid = True
        self.show_coords = False
        self.units = []  # Includes reinforcements; visibility is checked when drawing.
        self.map_layers = MapLayers()
        self.terrain_raster = None
        self.terrain_view_image = None
        self.coord_font = tkfont.Font(family='Arial', size=9, weight='bold')
        self.unit_images = {}
        self.terrain = {}  # Dict of (x,y): terrain_type
        self.terrain_source_name = None
        self.terrain_source_is_fallback = False
        self.scenario = None  # Store scenario for accessing dynamic dimensions
        self.selected_hex = None
        self.edit_controls = None
        self.edit_callbacks = (on_terrain_edit, on_unit_place, on_undo, on_feature_edit, on_map_tool)

        # Map dimensions (will be set from scenario, defaults used as fallback)
        self.map_width = self.DEFAULT_MAP_WIDTH
        self.map_height = self.DEFAULT_MAP_HEIGHT

        # Fallback swatches follow the same sprite rows as the game.
        self.terrain_colors = {
            0: '#90AE40', 1: '#B4CC60', 2: '#487F35', 3: '#619A88',
            4: '#918954', 5: '#245FC4', 6: '#D5C286', 7: '#698448',
            8: '#B9A469', 9: '#686338', 10: '#738444', 11: '#77863D',
            12: '#97AB74', 13: '#A98C77', 14: '#202020',
        }

        # Load hex tile images - CRITICAL, will raise RuntimeError if it fails
        self.hex_tile_images = {}  # Composited terrain images for the current zoom.
        self.hex_tile_base_images = {}  # Cache of base terrain images (without variants)
        self.hex_tile_loader = None  # HexTileLoader instance for variant support

        try:
            self.use_images = self._load_hex_tiles()
        except (RuntimeError, OSError, ValueError, struct.error) as e:
            messagebox.showerror(
                "Critical Error: Hex Tiles Not Available",
                f"{e}\n\nThe scenario editor cannot function without hex tile images.\n"
                f"Please ensure game/waw/dday/DATA/PCWATW.REZ is available.\n\n"
                f"The application will now exit."
            )
            # Force exit
            import sys
            sys.exit(1)

        self._create_ui()
        self._bind_events()

    def _create_ui(self):
        """Create map viewer UI"""
        # Control panel
        control_frame = ttk.Frame(self)
        control_frame.pack(fill=tk.X, padx=5, pady=5)

        self.map_title_label = ttk.Label(control_frame, text="Map",
                 font=("TkDefaultFont", 9, "bold"))
        self.map_title_label.pack(side=tk.LEFT, padx=5)

        ttk.Button(control_frame, text="+ Zoom In",
                  command=self.zoom_in).pack(side=tk.LEFT, padx=2)
        ttk.Button(control_frame, text="- Zoom Out",
                  command=self.zoom_out).pack(side=tk.LEFT, padx=2)
        ttk.Button(control_frame, text="Reset View",
                  command=self.reset_view).pack(side=tk.LEFT, padx=2)

        ttk.Separator(control_frame, orient=tk.VERTICAL).pack(side=tk.LEFT,
                                                              fill=tk.Y, padx=5)

        # Keep view layers on their own row so they remain accessible in a
        # narrower window. These are display preferences, not scenario edits.
        layers = ttk.Frame(self)
        layers.pack(fill=tk.X, padx=10, pady=(0, 5))
        ttk.Label(layers, text='Show:').pack(side=tk.LEFT, padx=(0, 5))
        self.units_var = tk.BooleanVar(value=True)
        self.terrain_var = tk.BooleanVar(value=True)
        self.grid_var = tk.BooleanVar(value=True)
        self.coords_var = tk.BooleanVar(value=False)
        self.names_var = tk.BooleanVar(value=True)
        self.ownership_var = tk.BooleanVar(value=False)
        self.layer_toggles = {}
        for label, variable in (('Units', self.units_var), ('Terrain', self.terrain_var),
                                ('Hexes', self.grid_var), ('Coords', self.coords_var),
                                ('Names', self.names_var), ('Ownership', self.ownership_var)):
            button = ttk.Checkbutton(layers, text=label, variable=variable, command=self.redraw)
            button.pack(side=tk.LEFT, padx=4)
            self.layer_toggles[label] = button

        # Info label
        self.info_label = ttk.Label(control_frame, text="Zoom: 100%")
        self.info_label.pack(side=tk.LEFT, padx=10)

        # Canvas with scrollbars
        body = ttk.Frame(self)
        body.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        canvas_frame = ttk.Frame(body)

        # Scrollbars
        h_scroll = ttk.Scrollbar(canvas_frame, orient=tk.HORIZONTAL)
        h_scroll.pack(side=tk.BOTTOM, fill=tk.X)

        v_scroll = ttk.Scrollbar(canvas_frame, orient=tk.VERTICAL)
        v_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        # Canvas
        self.canvas = tk.Canvas(canvas_frame,
                               bg='#E8E8E8',
                               highlightthickness=0,
                               borderwidth=0,
                               xscrollcommand=h_scroll.set,
                               yscrollcommand=v_scroll.set,
                               width=800,
                               height=600)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.canvas.bind('<Destroy>', self._cancel_redraws, add='+')

        h_scroll.config(command=self._on_xscroll)
        v_scroll.config(command=self._on_yscroll)
        if self.edit_callbacks[0] is not None:
            sidebar = ttk.Frame(body)
            sidebar.pack(side=tk.RIGHT, fill=tk.Y)
            self.edit_canvas = tk.Canvas(sidebar, width=350, height=500, highlightthickness=0)
            edit_scroll = ttk.Scrollbar(sidebar, orient=tk.VERTICAL, command=self.edit_canvas.yview)
            self.edit_canvas.config(yscrollcommand=edit_scroll.set)
            edit_scroll.pack(side=tk.RIGHT, fill=tk.Y)
            self.edit_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            self.edit_controls = MapEditingPanel(self.edit_canvas, self, *self.edit_callbacks)
            editor_window = self.edit_canvas.create_window((0, 0), window=self.edit_controls, anchor=tk.NW)
            self.edit_canvas.bind('<Configure>', lambda event:
                                  self.edit_canvas.itemconfigure(editor_window, width=event.width))
            self.edit_controls.bind('<Configure>', lambda event:
                                    self.edit_canvas.configure(scrollregion=self.edit_canvas.bbox('all')))

            def scroll_editor(event):
                step = (-1 if getattr(event, 'num', None) == 4 else
                        1 if getattr(event, 'num', None) == 5 else -int(event.delta / 120))
                self.edit_canvas.yview_scroll(step, 'units')
                return 'break'

            def bind_editor_scroll(widget):
                if widget.winfo_class() not in ('Treeview', 'TCombobox', 'Listbox', 'TSpinbox'):
                    for sequence in ('<MouseWheel>', '<Button-4>', '<Button-5>'):
                        widget.bind(sequence, scroll_editor)
                for child in widget.winfo_children():
                    bind_editor_scroll(child)
            bind_editor_scroll(self.edit_controls)
        canvas_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Status bar
        status_frame = ttk.Frame(self)
        status_frame.pack(fill=tk.X, padx=5, pady=2)

        self.status_label = ttk.Label(status_frame, text="Ready")
        self.status_label.pack(side=tk.LEFT)

    def _bind_events(self):
        """Bind mouse events for panning"""
        self.canvas.bind('<ButtonPress-1>', self._on_map_press)
        self.canvas.bind('<B1-Motion>', self._on_map_drag)
        self.canvas.bind('<ButtonRelease-1>', self._on_map_release)
        self.canvas.bind('<ButtonPress-3>', self._on_pan_start)
        self.canvas.bind('<B3-Motion>', self._on_pan_move)
        self.canvas.bind('<Escape>', lambda event: self.edit_controls.set_mode('Select') if self.edit_controls else None)
        self.canvas.bind('<Motion>', self._on_mouse_move)
        self.canvas.bind('<MouseWheel>', self._on_mousewheel)
        self.canvas.bind('<Configure>', self._on_canvas_configure)

        self._configure_pending = False

    def _on_xscroll(self, *args):
        """Handle horizontal scroll and redraw"""
        self._center_on_resize = False
        self._center_pending = False
        self.canvas.xview(*args)
        if self.units or self.terrain:
            self.redraw()

    def _on_yscroll(self, *args):
        """Handle vertical scroll and redraw"""
        self._center_on_resize = False
        self._center_pending = False
        self.canvas.yview(*args)
        if self.units or self.terrain:
            self.redraw()

    def _load_hex_tiles(self):
        """
        Load hex tile images by extracting from sprite sheet IN MEMORY.

        Raises RuntimeError if sprite sheet unavailable or extraction fails.
        This is a CRITICAL operation - the editor cannot function without hex tiles.
        """
        # Create HexTileLoader instance for variant support
        self.hex_tile_loader = HexTileLoader()

        # Load base tiles (default variants) - will raise RuntimeError if it fails
        tiles = self.hex_tile_loader.load_tiles()

        # Store the loaded tiles (already in RGBA format with transparency)
        self.hex_tile_base_images = tiles

        print(f"Successfully loaded {len(self.hex_tile_base_images)} hex tile images")
        print("✓ Variant support enabled - can render specific hex variants from map data")
        return True

    def _get_hex_tile_image(self, terrain_type, size, variant=0, record=0, edges=b'', hilltop=False):
        """
        Get a scaled hex tile image for the given terrain type, size, and variant.

        Args:
            terrain_type: Terrain type ID (0-14)
            size: Hex size in pixels
            variant: Variant column (0-12), defaults to 0

        Returns:
            PhotoImage ready for canvas use, or None if unavailable
        """
        if not self.use_images:
            return None

        # Create a cache key including variant
        cache_key = (terrain_type, variant, size, record, edges, hilltop)

        # Check cache
        if cache_key in self.hex_tile_images:
            return self.hex_tile_images[cache_key]

        # Get base image with specific variant
        try:
            if self.hex_tile_loader:
                # Use the exact variant column stored in the scenario byte.
                base_img = self.hex_tile_loader.compose_tile(
                    terrain_type, variant, record, edges, hilltop)
            else:
                # Use default variant (variant 0) from base images
                base_img = self.hex_tile_base_images.get(terrain_type)

            if base_img is None:
                return None

        except Exception as e:
            print(f"Error loading hex tile variant: {e}")
            # Fall back to default variant
            base_img = self.hex_tile_base_images.get(terrain_type)
            if base_img is None:
                return None

        # Match the same pointy-top bounds as centers and grid outlines.
        new_width = max(1, round(size * math.sqrt(3)))
        new_height = max(1, round(size * 2))

        # Scale the image
        try:
            scaled_img = base_img.resize((new_width, new_height), Image.Resampling.NEAREST)
            photo_img = ImageTk.PhotoImage(scaled_img)

            # Cache it (keep a reference to prevent garbage collection)
            self.hex_tile_images[cache_key] = photo_img

            return photo_img
        except Exception as e:
            print(f"Error scaling hex tile image: {e}")
            return None

    def _on_pan_start(self, event):
        """Start panning"""
        self._center_on_resize = False
        self._center_pending = False
        self.canvas.scan_mark(event.x, event.y)

    def _on_map_press(self, event):
        self.canvas.focus_set()
        self._press_point = event.x, event.y
        self._dragged = False
        self._on_pan_start(event)

    def _on_map_drag(self, event):
        if not hasattr(self, '_press_point'):
            return
        if math.hypot(event.x - self._press_point[0], event.y - self._press_point[1]) > 4:
            self._dragged = True
        if self._dragged:
            self._on_pan_move(event)

    def _on_map_release(self, event):
        if not hasattr(self, '_press_point'):
            return
        dragged = self._dragged
        del self._press_point
        if dragged or self.edit_controls is None:
            return
        px, py = self.canvas.canvasx(event.x), self.canvas.canvasy(event.y)
        cell = self.pixel_to_hex(px, py)
        if cell in self.terrain:
            self.edit_controls.click_hex(cell, self.pixel_to_hex_direction(cell, px, py))

    def _on_pan_move(self, event):
        """Pan the same viewport used by the scrollbars."""
        self.canvas.scan_dragto(event.x, event.y, gain=1)
        self.redraw()

    def _on_mouse_move(self, event):
        """Show hex coordinates under mouse"""
        # Convert widget coordinates to canvas coordinates (accounts for scroll)
        canvas_x = self.canvas.canvasx(event.x)
        canvas_y = self.canvas.canvasy(event.y)

        # Convert canvas coordinates to hex coordinates
        hex_x, hex_y = self.pixel_to_hex(canvas_x, canvas_y)
        if self.edit_controls and self.edit_controls.mode.get() in ('Region', 'Paste'):
            tools = self.edit_controls.tools
            if tools.hover != (hex_x, hex_y):
                tools.hover = hex_x, hex_y
                self.redraw()

        if 0 <= hex_x < self.map_width and 0 <= hex_y < self.map_height:
            terrain_data = self.terrain.get((hex_x, hex_y))
            if terrain_data is None:
                self.status_label.config(text=f"Hex: ({hex_x}, {hex_y}) | Terrain unavailable")
                return

            if isinstance(terrain_data, tuple):
                terrain_type, variant = terrain_data
            else:
                terrain_type, variant = terrain_data, None
            text = (f"Hex: ({hex_x}, {hex_y}) | Terrain: {terrain_name(terrain_type)} "
                    f"(code {terrain_type})")
            if variant is not None:
                text += f" | Variant: {variant}"
            names = [unit['name'] for unit in self.units
                     if self.units_var.get() and self._unit_is_visible(unit)
                     and (unit['x'], unit['y']) == (hex_x, hex_y)]
            if names:
                text += f" | {len(names)} unit(s): " + ', '.join(names)
            self.status_label.config(text=text)
        else:
            self.status_label.config(text="Outside map bounds")

    def _on_mousewheel(self, event):
        """Zoom with mouse wheel, centered on cursor position"""
        self._zoom_at_point(event.x, event.y, zoom_in=event.delta > 0)

    def _on_canvas_configure(self, event):
        """Handle canvas resize/configure event"""
        if self._center_on_resize:
            self._center_pending = True
        # Redraw when canvas is configured (prevents initial blank display)
        # Use a flag to avoid multiple redraws during rapid resizing
        if not self._configure_pending:
            self._configure_pending = True
            self._schedule_redraw(50, self._do_configure_redraw)

    def _schedule_redraw(self, delay, callback):
        def run():
            self._redraw_timers.discard(timer)
            callback()
        timer = self.canvas.after(delay, run)
        self._redraw_timers.add(timer)

    def _cancel_redraws(self, event):
        for timer in self._redraw_timers:
            self.canvas.after_cancel(timer)
        self._redraw_timers.clear()

    def _do_configure_redraw(self):
        """Perform the actual redraw after configure event"""
        self._configure_pending = False
        if self.units or self.terrain:
            self.redraw()

    def hex_to_pixel(self, hex_x, hex_y):
        """Convert hex coordinates to pixel coordinates"""
        # INVADE.EXE's CalcScr shifts even rows half a column to the right.
        x = self.hex_size * math.sqrt(3) * (hex_x + 0.5 * (1 - hex_y % 2))
        y = self.hex_size * 1.5 * hex_y

        return x + self.offset_x, y + self.offset_y

    def pixel_to_hex(self, pixel_x, pixel_y):
        """Find the containing pointy-top hex, including its sloping edges."""
        x = (pixel_x - self.offset_x) / self.hex_size - math.sqrt(3) / 2
        y = (pixel_y - self.offset_y) / self.hex_size
        # Convert to axial/cube coordinates and round to the closest hex center.
        q = x / math.sqrt(3) - y / 3
        r = 2 * y / 3
        cube_s = -q - r
        rq, rr, rs = round(q), round(r), round(cube_s)
        dq, dr, ds = abs(rq - q), abs(rr - r), abs(rs - cube_s)
        if dq > dr and dq > ds:
            rq = -rr - rs
        elif dr > ds:
            rr = -rq - rs
        return rq + (rr + (rr & 1)) // 2, rr

    def pixel_to_hex_direction(self, cell, pixel_x, pixel_y):
        """Nearest side in W/NW/NE/E/SE/SW order; center clicks keep the brush direction."""
        cx, cy = self.hex_to_pixel(*cell)
        dx, dy = pixel_x - cx, pixel_y - cy
        if math.hypot(dx, dy) < self.hex_size * 0.3:
            return None
        return (int(math.floor(math.atan2(dy, dx) / (math.pi / 3) + 0.5)) + 3) % 6

    def draw_hexagon(self, center_x, center_y, size, fill='white', outline='black'):
        """Draw a pointy-top hex matching the tile image and center spacing."""
        points = []
        for i in range(6):
            angle = math.pi / 3 * i - math.pi / 6
            px = center_x + size * math.cos(angle)
            py = center_y + size * math.sin(angle)
            points.extend([px, py])

        return self.canvas.create_polygon(points, fill=fill, outline=outline, width=1)

    def load_data(self, units, scenario=None):
        """Load map data - units is list of unit dicts from EnhancedUnitParser"""
        self.units = units if units else []
        self.scenario = scenario
        self.selected_hex = None
        if self.edit_controls:
            self.edit_controls.unit_key = None
            self.edit_controls.set_mode('Select')
        self._center_pending = True
        self._center_on_resize = True

        # Get map dimensions from scenario (or use defaults)
        if scenario and scenario.is_valid:
            self.map_width = scenario.map_width
            self.map_height = scenario.map_height
            self.map_title_label.config(text=f"Map ({self.map_width}×{self.map_height} hex grid)")
        else:
            self.map_width = self.DEFAULT_MAP_WIDTH
            self.map_height = self.DEFAULT_MAP_HEIGHT
            self.map_title_label.config(text=f"Map ({self.map_width}×{self.map_height} hex grid)")

        self.terrain = {}
        self.map_layers = MapLayers()
        self.terrain_raster = None
        self.terrain_view_image = None
        self.hex_tile_images.clear()
        self.unit_images.clear()
        self.terrain_source_name = None
        self.terrain_source_is_fallback = False
        if scenario and scenario.is_valid:
            self.map_layers = read_map_layers(scenario)
            self.terrain = self.map_layers.terrain
            self.terrain_source_name = scenario.filename.name if self.terrain else None
        self.update_unit_summary()
        if self.edit_controls:
            self.edit_controls.tools.reset()
            self.edit_controls.refresh()

        # Force initial redraw after a short delay to ensure canvas is ready
        self._schedule_redraw(100, self.redraw)

    def update_unit_summary(self):
        terrain_source = (f"Terrain from {self.terrain_source_name}" if self.terrain else
                          "Terrain unavailable (invalid or incomplete map data)")
        units_with_pos = sum(self._unit_is_visible(u) for u in self.units)
        count = sum(not u.get('deleted') for u in self.units)
        self.status_label.config(
            text=f"Loaded {count} units ({units_with_pos} on map) | {terrain_source}")

    def redraw(self):
        """Redraw the entire map"""
        if self._center_pending and self.canvas.winfo_width() > 1 and self.canvas.winfo_height() > 1:
            self._center_view()
        # Establish bounds before culling tiles, without resetting the viewport.
        self._update_scroll_region()
        self.canvas.delete('all')
        if getattr(self, '_image_scale', None) != self.hex_size:
            self.hex_tile_images.clear()
            self.unit_images.clear()
            self._image_scale = self.hex_size

        self.show_grid = self.grid_var.get()
        self.show_coords = self.coords_var.get()

        # Update info - show zoom and hex dimensions
        zoom_pct = int(self.hex_size / self.HEX_SIZE * 100)
        self.info_label.config(text=f"Zoom: {zoom_pct}%")

        # Draw only visible hexes for performance
        visible_hexes = self._get_visible_hexes()

        # Scale one continuous terrain surface; grid/labels are separate layers.
        show_terrain = self.terrain_var.get()
        if show_terrain and self.use_images and self.terrain:
            self._draw_terrain_raster()
        for hex_y in range(visible_hexes['min_y'], visible_hexes['max_y']):
            for hex_x in range(visible_hexes['min_x'], visible_hexes['max_x']):
                if (hex_x, hex_y) in self.terrain:
                    px, py = self.hex_to_pixel(hex_x, hex_y)
                    if show_terrain and not self.use_images:
                        terrain = self.terrain[(hex_x, hex_y)]
                        code = terrain[0] if isinstance(terrain, tuple) else terrain
                        color = self.terrain_colors.get(code, '#FFFFFF')
                        item = self.draw_hexagon(px, py, self.hex_size, fill=color, outline=color)
                        self.canvas.itemconfigure(item, tags=('terrain',))
                    if self.show_grid:
                        item = self.draw_hexagon(px, py, self.hex_size, fill='', outline='#888888')
                        self.canvas.itemconfigure(item, tags=('hex_grid',))
                    if self.ownership_var.get():
                        owner = self.map_layers.ownership.get((hex_x, hex_y))
                        if owner is not None:
                            item = self.draw_hexagon(px, py, self.hex_size,
                                                    fill=('#2779da', '#dc4949')[owner], outline='')
                            self.canvas.itemconfigure(item, stipple='gray25', tags=('ownership',))

        if self.names_var.get():
            self._draw_place_names()

        # Preserve stacks while keeping future arrivals off the map.
        stacks = {}
        for unit in self.units if self.units_var.get() else ():
            if self._unit_is_visible(unit):
                stacks.setdefault((unit['x'], unit['y']), []).append(unit)
        for (x, y), stack in stacks.items():
            if (visible_hexes['min_x'] <= x < visible_hexes['max_x']
                    and visible_hexes['min_y'] <= y < visible_hexes['max_y']):
                self._draw_unit_stack(x, y, stack)

        if self.show_coords:
            self._draw_coordinate_labels(visible_hexes)
        self._draw_edit_selection()

    def _draw_edit_selection(self):
        if self.edit_controls is None:
            return
        for cell in self.edit_controls.tools.preview_cells():
            px, py = self.hex_to_pixel(*cell)
            item = self.draw_hexagon(px, py, self.hex_size * 0.92, fill='',
                                    outline='#ffb300' if cell in self.terrain else '#dd2222')
            self.canvas.itemconfigure(item, width=2, tags=('region',))
        unit = self.edit_controls.selected_unit()
        targets = []
        if self.selected_hex in self.terrain:
            targets.append((self.selected_hex, '#ffd43b', False))
        if self.units_var.get() and unit and (unit['x'], unit['y']) in self.terrain:
            targets.append(((unit['x'], unit['y']), '#208cff', not unit['in_play']))
        for cell, color, pending in targets:
            px, py = self.hex_to_pixel(*cell)
            item = self.draw_hexagon(px, py, self.hex_size * 0.9, fill='', outline=color)
            self.canvas.itemconfigure(item, width=3, tags=('selection',), dash=(4, 3) if pending else ())
            if pending:
                self.canvas.create_text(px, py - self.hex_size - 7, text='Arrival hex',
                                        fill='#114477', font=('TkDefaultFont', 9, 'bold'), tags=('selection',))
        mode = self.edit_controls.mode.get()
        if (self.selected_hex in self.terrain and (mode == 'Edges' or (mode == 'Features'
                and self.edit_controls.feature_var.get() != 'Hilltop'))):
            px, py = self.hex_to_pixel(*self.selected_hex)
            direction = (('W', 'NW', 'NE', 'E', 'SE', 'SW').index(self.edit_controls.tools.edge_direction.get())
                         if mode == 'Edges' else self.edit_controls.feature_direction.get())
            angle = (direction - 3) * math.pi / 3
            points = [coordinate for a in (angle - math.pi / 6, angle + math.pi / 6)
                      for coordinate in (px + self.hex_size * math.cos(a), py + self.hex_size * math.sin(a))]
            self.canvas.create_line(*points, fill='#00b8ef', width=4, tags=('selection', 'feature_edge'))

    def _draw_place_names(self):
        for place in self.map_layers.places:
            cell = place['x'], place['y']
            if cell not in self.terrain or not place['name']:
                continue
            px, py = self.hex_to_pixel(*cell)
            py -= self.hex_size * 0.75
            size = max(8, min(18, round(place['size'] * self.hex_size / 32)))
            color = {'V': '#fff9dc', 'R': '#b2e4ff', 'I': '#eeeeee'}.get(place['style'], 'white')
            text = self.canvas.create_text(px, py, text=place['name'], anchor=tk.SW,
                                          font=('Arial', size, 'bold'), fill=color, tags=('place_name',))
            x0, y0, x1, y1 = self.canvas.bbox(text)
            bg = self.canvas.create_rectangle(x0-2, y0-1, x1+2, y1+1, fill='#18232a',
                                              outline='', tags=('place_name',))
            self.canvas.tag_lower(bg, text)

    def _unit_is_visible(self, unit):
        return (not unit.get('deleted') and unit.get('in_play', True)
                and 0 <= unit.get('x', -1) < self.map_width
                and 0 <= unit.get('y', -1) < self.map_height)

    def _get_visible_hexes(self):
        """Get range of visible hexes based on canvas viewport"""
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()

        # Add padding for partially visible hexes
        padding = 5

        # Convert widget corners to canvas coordinates (accounts for scroll)
        # canvasx/canvasy converts widget position to canvas coordinate space
        visible_x1 = self.canvas.canvasx(0)
        visible_y1 = self.canvas.canvasy(0)
        visible_x2 = self.canvas.canvasx(canvas_width)
        visible_y2 = self.canvas.canvasy(canvas_height)

        # pixel_to_hex expects canvas coordinates
        min_x, min_y = self.pixel_to_hex(visible_x1, visible_y1)
        max_x, max_y = self.pixel_to_hex(visible_x2, visible_y2)

        return {
            'min_x': max(0, min_x - padding),
            'max_x': min(self.map_width, max_x + padding),
            'min_y': max(0, min_y - padding),
            'max_y': min(self.map_height, max_y + padding)
        }

    def _draw_terrain_raster(self):
        """Sample the native map into the viewport with one shared transform."""
        if self.terrain_raster is None:
            self.terrain_raster = self.hex_tile_loader.compose_map(
                self.map_width, self.map_height, self.map_layers)
        view_x, view_y = self.canvas.canvasx(0), self.canvas.canvasy(0)
        width, height = self.canvas.winfo_width(), self.canvas.winfo_height()
        scale_x = self.hex_size * math.sqrt(3) / 32
        scale_y = self.hex_size / 18
        left = self.offset_x - self.hex_size * math.sqrt(3) / 2
        top = self.offset_y - self.hex_size
        # Render only the viewport: zooming a large map must not allocate an
        # enormous scaled copy of the complete map.
        image = self.terrain_raster.transform(
            (width, height), Image.Transform.AFFINE,
            (1 / scale_x, 0, (view_x - left) / scale_x,
             0, 1 / scale_y, (view_y - top) / scale_y),
            resample=Image.Resampling.NEAREST)
        self.terrain_view_image = ImageTk.PhotoImage(image)
        self.canvas.create_image(view_x, view_y, image=self.terrain_view_image,
                                 anchor=tk.NW, tags=('terrain',))

    def _draw_coordinate_labels(self, visible):
        """High-contrast coordinates, with fewer labels when zoomed out."""
        self.coord_font.configure(size=max(9, min(12, int(self.hex_size / 4))))
        label_width = self.coord_font.measure(f'{self.map_width - 1},{self.map_height - 1}') + 6
        label_height = self.coord_font.metrics('linespace') + 4
        step_x = max(1, math.ceil(label_width / (self.hex_size * math.sqrt(3))))
        step_y = max(1, math.ceil(label_height / (self.hex_size * 1.5)))
        for y in range(visible['min_y'], visible['max_y']):
            if y % step_y:
                continue
            for x in range(visible['min_x'], visible['max_x']):
                if x % step_x or (x, y) not in self.terrain:
                    continue
                px, py = self.hex_to_pixel(x, y)
                # Put coordinates toward the bottom of the cell; render after
                # units so a counter cannot hide the label.
                label = self.canvas.create_text(
                    px, py + self.hex_size * 0.85, text=f'{x},{y}',
                    font=self.coord_font, fill='white', tags=('coords', 'coord_text'))
                left, top, right, bottom = self.canvas.bbox(label)
                plate = self.canvas.create_rectangle(
                    left - 2, top - 1, right + 2, bottom + 1,
                    fill='#17212b', outline='', tags=('coords', 'coord_background'))
                self.canvas.tag_lower(plate, label)

    def _draw_unit_stack(self, hex_x, hex_y, stack):
        """Draw the game's printed counter artwork, with a small stack offset."""
        px, py = self.hex_to_pixel(hex_x, hex_y)
        scale = self.hex_size / 18
        width, height = max(1, round(22 * scale)), max(1, round(23 * scale))
        step = max(1, round(2 * scale))
        if self.edit_controls:
            selected = self.edit_controls.selected_unit()
            if selected in stack:
                stack = [selected] + [u for u in stack if u is not selected]
        # The first roster unit is the top counter. Hover lists the entire stack.
        for depth, unit in reversed(list(enumerate(stack[:3]))):
            key = (unit.get('counter_resource'), unit.get('counter_index'), width, height)
            if key not in self.unit_images:
                try:
                    art = unit_counter(key[0], key[1], unit.get('counter_bitmap'))
                    self.unit_images[key] = ImageTk.PhotoImage(
                        art.resize((width, height), Image.Resampling.NEAREST))
                except (ValueError, TypeError, RuntimeError, OSError) as exc:
                    print(f"Counter unavailable for {unit.get('name')}: {exc}")
                    self.unit_images[key] = None
            image = self.unit_images[key]
            if image is not None:
                self.canvas.create_image(px + depth * step, py - depth * step,
                                         image=image, tags=('unit',))
            else:
                color = '#237032' if unit.get('side') == 'Allied' else '#666666'
                self.canvas.create_rectangle(px - width / 2, py - height / 2,
                                             px + width / 2, py + height / 2,
                                             fill=color, outline='white', tags=('unit',))

    def _map_pixel_bounds(self):
        """Bounds of the complete hex grid, including staggered rows and tips."""
        width = self.hex_size * math.sqrt(3)
        return (
            self.offset_x - (width / 2 if self.map_height > 1 else 0),
            self.offset_y - self.hex_size,
            self.offset_x + self.map_width * width,
            self.offset_y + max(0, self.map_height - 1) * self.hex_size * 1.5 + self.hex_size,
        )

    def _update_scroll_region(self, view_origin=None):
        """Keep the whole map reachable while preserving the current viewport.

        Zoom can request a new viewport origin. Include that viewport in the
        bounds so Tk cannot clamp it and move the zoom anchor, even on a map
        smaller than the window. Ordinary redraws never reposition the view.
        """
        canvas_width, canvas_height = self.canvas.winfo_width(), self.canvas.winfo_height()
        geometry = (self.map_width, self.map_height, self.hex_size,
                    self.offset_x, self.offset_y, canvas_width, canvas_height)
        if view_origin is None and geometry == self._scroll_geometry:
            return  # Keep the scrollbar range stable while scrolling or dragging.
        if view_origin is None:
            view_x, view_y = self.canvas.canvasx(0), self.canvas.canvasy(0)
        else:
            view_x, view_y = view_origin
        left, top, right, bottom = self._map_pixel_bounds()
        padding = 30
        left = math.floor(min(0, left - padding, view_x))
        top = math.floor(min(0, top - padding, view_y))
        right = math.ceil(max(right + padding, view_x + canvas_width))
        bottom = math.ceil(max(bottom + padding, view_y + canvas_height))
        self.canvas.config(scrollregion=(left, top, right, bottom))
        self._scroll_geometry = geometry

        if view_origin is not None:
            self.canvas.xview_moveto((view_x - left) / (right - left))
            self.canvas.yview_moveto((view_y - top) / (bottom - top))

    def _zoom_at_point(self, screen_x, screen_y, zoom_in=True):
        """Zoom about a widget point, preserving its location on the map."""
        self._center_on_resize = False
        self._center_pending = False
        world_x = self.canvas.canvasx(screen_x) - self.offset_x
        world_y = self.canvas.canvasy(screen_y) - self.offset_y

        # Calculate new hex size
        old_size = self.hex_size
        zoom_factor = 1.25 if zoom_in else 0.8

        new_size = self.hex_size * zoom_factor
        new_size = max(3, min(60, new_size))

        if abs(new_size - old_size) < 0.1:
            return

        # Calculate scale ratio
        scale = new_size / old_size
        self.hex_size = new_size

        # Move the viewport, keeping the map origin fixed in canvas space.
        self._update_scroll_region((
            self.offset_x + world_x * scale - screen_x,
            self.offset_y + world_y * scale - screen_y,
        ))
        self.redraw()

    def _visible_map_center(self):
        """Widget position for button zooms; avoid centering on empty space."""
        left, top, right, bottom = self._map_pixel_bounds()
        view_x, view_y = self.canvas.canvasx(0), self.canvas.canvasy(0)
        width, height = self.canvas.winfo_width(), self.canvas.winfo_height()
        left, right = max(0, left - view_x), min(width, right - view_x)
        top, bottom = max(0, top - view_y), min(height, bottom - view_y)
        # Tk's canvas coordinates are integral pixels, including zoom anchors.
        return (
            round((left + right) / 2 if left < right else width / 2),
            round((top + bottom) / 2 if top < bottom else height / 2),
        )

    def zoom_in(self):
        """Zoom in centered on the visible map."""
        self._zoom_at_point(*self._visible_map_center(), zoom_in=True)

    def zoom_out(self):
        """Zoom out centered on the visible map."""
        self._zoom_at_point(*self._visible_map_center(), zoom_in=False)

    def reset_view(self):
        """Restore the default zoom and center the map in the viewport."""
        self.hex_size = self.HEX_SIZE
        self.offset_x = 50
        self.offset_y = 50
        self._center_pending = True
        self._center_on_resize = True
        self.redraw()

    def _center_view(self):
        left, top, right, bottom = self._map_pixel_bounds()
        self._update_scroll_region((
            (left + right - self.canvas.winfo_width()) / 2,
            (top + bottom - self.canvas.winfo_height()) / 2,
        ))
        self._center_pending = False


class UnitPropertiesEditor(ttk.Frame):
    """Edit verified OB fields and preview the unit's original game artwork."""

    def __init__(self, parent, on_unit_update_callback, on_select_callback=None, action_parent=None,
                 on_draft_changed=lambda: None, get_counter_artwork=lambda: {}, on_import_chit=lambda: None,
                 on_operations=lambda page: None, on_support_artwork=lambda: None,
                 get_presentation_artwork=lambda: {}):
        super().__init__(parent)
        self.on_unit_update_callback = on_unit_update_callback
        self.on_select_callback = on_select_callback
        self.get_counter_artwork = get_counter_artwork
        self.on_support_artwork = on_support_artwork
        self.get_presentation_artwork = get_presentation_artwork
        self.current_unit = None
        self.counter_var = tk.IntVar(self, value=0)
        self.units = []
        self.chit_image = None
        self.columnconfigure(0, weight=1)

        ttk.Label(self, text="Unit Properties", font=("TkDefaultFont", 10, "bold")).grid(
            row=0, column=0, sticky=tk.W, padx=8, pady=8)
        self.unit_combo = ttk.Combobox(self, state='readonly', width=42)
        self.unit_combo.grid(row=1, column=0, sticky=tk.EW, padx=8, pady=4)
        self.unit_combo.bind('<<ComboboxSelected>>', self.on_unit_selected)

        form = ttk.Frame(self, padding=8)
        form.grid(row=2, column=0, sticky=tk.NSEW)
        form.columnconfigure(1, weight=1)
        ttk.Label(form, text="Name:").grid(row=0, column=0, sticky=tk.W, pady=4)
        self.name_entry = ttk.Entry(form, width=28)
        self.name_entry.grid(row=0, column=1, sticky=tk.EW, padx=6)
        self.chit_label = ttk.Label(form, anchor=tk.CENTER)
        self.chit_label.grid(row=0, column=2, rowspan=4, padx=12, sticky=tk.N)
        chit_buttons = ttk.Frame(form)
        chit_buttons.grid(row=3, column=2, sticky=tk.S)
        self.chit_button = ttk.Button(chit_buttons, text='Choose chit…', command=self.choose_chit)
        self.chit_button.pack()
        self.import_chit_button = ttk.Button(chit_buttons, text='Import image…', command=on_import_chit)
        self.import_chit_button.pack(pady=3)
        self.type_label = ttk.Label(form, wraplength=265)
        self.side_label = ttk.Label(form)
        self.unit_status_label = ttk.Label(form)
        for row, title, label in ((1, 'Type:', self.type_label), (2, 'Side:', self.side_label),
                                  (3, 'Status:', self.unit_status_label)):
            ttk.Label(form, text=title).grid(row=row, column=0, sticky=tk.W, pady=4)
            label.grid(row=row, column=1, sticky=tk.W, padx=6)

        position = ttk.LabelFrame(form, text='Arrival and deployment', padding=8)
        position.grid(row=4, column=0, columnspan=3, sticky=tk.W, pady=6)
        self.availability_var = tk.StringVar(value='At start')
        ttk.Label(position, text='Availability:').grid(row=0, column=0, sticky=tk.W)
        self.availability_combo = ttk.Combobox(position, textvariable=self.availability_var,
                                             values=('At start', 'Scheduled', 'Inactive'),
                                             state='readonly', width=10)
        self.availability_combo.grid(row=0, column=1, padx=6, sticky=tk.W)
        self.availability_combo.bind('<<ComboboxSelected>>', self._update_arrival_controls)
        ttk.Label(position, text='Arrival turn:').grid(row=0, column=2, sticky=tk.W)
        self.arrival_turn_spin = ttk.Spinbox(position, from_=1, to=255, width=6)
        self.arrival_turn_spin.grid(row=0, column=3, padx=6)
        self.arrival_hint = ttk.Label(position, wraplength=460)
        self.arrival_hint.grid(row=1, column=0, columnspan=5, sticky=tk.W, pady=5)
        self.position_label = ttk.Label(position, text='Hex X:')
        self.position_label.grid(row=2, column=0, sticky=tk.W)
        self.pos_x_spin = ttk.Spinbox(position, from_=-1, to=0, width=6)
        self.pos_x_spin.grid(row=2, column=1, sticky=tk.W, padx=6)
        ttk.Label(position, text="Y:").grid(row=2, column=2, sticky=tk.W)
        self.pos_y_spin = ttk.Spinbox(position, from_=-1, to=0, width=6)
        self.pos_y_spin.grid(row=2, column=3, padx=6)
        ttk.Label(position, text="−1 = off map").grid(row=2, column=4, sticky=tk.W, padx=6)

        stats = ttk.LabelFrame(form, text="Combat strengths", padding=8)
        stats.grid(row=5, column=0, columnspan=3, sticky=tk.EW, pady=5)
        ttk.Label(stats, text="Base").grid(row=0, column=1)
        ttk.Label(stats, text="Adjusted (saved)").grid(row=0, column=2, padx=12)
        self.stat_spins = {}
        self.saved_stats = {}
        for row, (key, title) in enumerate((('attack', 'Attack'), ('defense', 'Defense'),
                                           ('armor', 'Armor'), ('antitank', 'Antitank')), 1):
            ttk.Label(stats, text=title + ':').grid(row=row, column=0, sticky=tk.W, pady=3)
            spin = ttk.Spinbox(stats, from_=0, to=2147483.647, increment=1, width=9)
            spin.grid(row=row, column=1, padx=6)
            self.stat_spins[key + '_base'] = spin
            label = ttk.Label(stats, width=10, anchor=tk.CENTER)
            label.grid(row=row, column=2, padx=12)
            self.saved_stats[key + '_current'] = label
        ttk.Label(stats, text="The game recalculates adjusted strengths during play.",
                  wraplength=520).grid(row=5, column=0, columnspan=3, sticky=tk.W, pady=(6, 0))

        condition = ttk.LabelFrame(form, text="Quality and condition", padding=8)
        condition.grid(row=6, column=0, columnspan=3, sticky=tk.EW, pady=5)
        for row, (key, title) in enumerate((('quality', 'Base quality'), ('disruption', 'Disruption'),
                                           ('fatigue', 'Fatigue'))):
            ttk.Label(condition, text=title + ':').grid(row=row, column=0, sticky=tk.W, pady=3)
            spin = ttk.Spinbox(condition, from_=0, to=15, width=6)
            spin.grid(row=row, column=1, padx=6, sticky=tk.W)
            self.stat_spins[key] = spin
        self.quality_state_label = ttk.Label(condition, wraplength=200)
        self.quality_state_label.grid(row=0, column=2, rowspan=3, padx=12, sticky=tk.NW)

        ai = ttk.LabelFrame(form, text='AI and orders', padding=8)
        ai.grid(row=7, column=0, columnspan=3, sticky=tk.EW, pady=5)
        ttk.Label(ai, text='Saved order:').grid(row=0, column=0, sticky=tk.NW, pady=3)
        self.order_label = ttk.Label(ai, wraplength=330)
        self.order_label.grid(row=0, column=1, columnspan=2, sticky=tk.W, padx=6)
        ttk.Label(ai, text='Controlling HQ:').grid(row=1, column=0, sticky=tk.NW, pady=3)
        self.hq_label = ttk.Label(ai, wraplength=330)
        self.hq_label.grid(row=1, column=1, columnspan=2, sticky=tk.W, padx=6)
        ttk.Label(ai, text='Staff assistance:').grid(row=2, column=0, sticky=tk.W, pady=3)
        self.ai_vars = {}
        self.ai_checks = {}
        for column, (key, title) in enumerate((('hq_auto_ground', 'Ground orders'),
                                              ('hq_auto_artillery', 'Artillery orders')), 1):
            variable = tk.BooleanVar()
            check = ttk.Checkbutton(ai, text=title, variable=variable)
            check.grid(row=2, column=column, sticky=tk.W, padx=6)
            self.ai_vars[key] = variable
            self.ai_checks[key] = check
        self.ai_hint = ttk.Label(ai, wraplength=460)
        self.ai_hint.grid(row=3, column=0, columnspan=3, sticky=tk.W, pady=(6, 0))
        operations = ttk.Frame(ai)
        operations.grid(row=4, column=0, columnspan=3, sticky=tk.W, pady=(8, 0))
        self.operation_buttons = {}
        for page in ('Supply', 'Transport', 'Orders'):
            button = ttk.Button(operations, text=page+'…', command=lambda p=page: on_operations(p), state='disabled')
            button.pack(side=tk.LEFT, padx=(0, 8))
            self.operation_buttons[page] = button

        buttons = ttk.Frame(action_parent if action_parent is not None else self)
        if action_parent is None:
            buttons.grid(row=3, column=0, sticky=tk.W, padx=8, pady=5)
        else:
            buttons.pack(side=tk.LEFT, padx=8, pady=5)
        self.apply_button = ttk.Button(buttons, text="Apply Changes", command=self.apply_changes)
        self.apply_button.pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(buttons, text="Revert Form", command=self.revert_changes).pack(side=tk.LEFT)
        self.feedback = ttk.Label(self, wraplength=420)
        self.feedback.grid(row=4, column=0, sticky=tk.W, padx=8, pady=3)

        fields = {key: field_variable(spin) for key, spin in self.stat_spins.items()}
        fields.update(name=field_variable(self.name_entry), x=field_variable(self.pos_x_spin),
                      y=field_variable(self.pos_y_spin), availability=self.availability_var,
                      arrival_turn=field_variable(self.arrival_turn_spin), counter_index=self.counter_var,
                      **self.ai_vars)
        self.draft = FormDraft(self, 'Unit properties', fields, on_draft_changed, self.prepare_draft)
        self.load_units([])

    @property
    def counter_index(self):
        return self.counter_var.get()

    @counter_index.setter
    def counter_index(self, value):
        self.counter_var.set(value)

    def prepare_draft(self, data, context, values, changes):
        scenario = DdayScenario.from_bytes(data, 'draft.SCN')
        unit = next((u for u in read_units(scenario, self.get_counter_artwork(), self.get_presentation_artwork())
                     if (u['side'], u['side_index']) == context), None)
        if unit is None or unit.get('deleted'):
            raise ValueError('The unit for this draft is no longer available.')
        edited = dict(changes)
        if 'availability' in edited or 'arrival_turn' in edited:
            availability = ('Inactive' if unit['arrival_time'] == -1 else
                            'At start' if unit['arrival_time'] < unit['start_time'] else 'Scheduled')
            edited['arrival_time'] = arrival_time_from_form(unit,
                edited.get('availability', availability),
                edited.get('arrival_turn', max(1, unit['arrival_time'] - unit['start_time'] + 1)))
        edited.pop('availability', None)
        edited.pop('arrival_turn', None)
        updated, patches = prepare_unit_changes(unit, edited)
        result = bytearray(data)
        for offset, value, _ in patches:
            result[offset:offset+len(value)] = value
        return bytes(result)

    def _update_arrival_controls(self, event=None):
        scheduled = self.availability_var.get() == 'Scheduled'
        self.arrival_turn_spin.config(state='normal' if scheduled else 'disabled')
        self.position_label.config(text='Entry hex X:' if scheduled else 'Hex X:')

    def load_units(self, units, selected_index=None):
        self.units = units
        self.unit_combo['values'] = [f"{u['side']} · {u['side_index']}: {u['name']}" for u in units]
        if units:
            index = next((i for i, u in enumerate(units) if u['index'] == selected_index), 0)
            self.unit_combo.current(index)
            self.on_unit_selected(None)
        else:
            self.draft.deactivate()
            self.current_unit = None
            self.unit_combo.set('')
            self.name_entry.delete(0, tk.END)
            self.chit_image = None
            self.chit_label.config(image='', text='')
            self.chit_button.config(state='disabled')
            self.import_chit_button.config(state='disabled')
            for button in self.operation_buttons.values():
                button.config(state='disabled')
            for label in (self.type_label, self.side_label, self.unit_status_label,
                          self.quality_state_label, self.feedback, self.arrival_hint,
                          self.order_label, self.hq_label, self.ai_hint,
                          *self.saved_stats.values()):
                label.config(text='')
            for spin in (self.pos_x_spin, self.pos_y_spin, *self.stat_spins.values()):
                spin.set('')
            for key, check in self.ai_checks.items():
                self.ai_vars[key].set(False)
                check.config(state='disabled')
            self.apply_button.config(state='disabled')
            self.availability_var.set('')
            self.availability_combo.config(state='disabled')
            self.arrival_turn_spin.config(state='normal')
            self.arrival_turn_spin.set('')
            self.arrival_turn_spin.config(state='disabled')

    def on_unit_selected(self, event):
        index = self.unit_combo.current()
        if 0 <= index < len(self.units):
            self.current_unit = self.units[index]
            self.display_unit()
            if self.on_select_callback:
                self.on_select_callback(self.current_unit)

    def display_unit(self):
        unit = self.current_unit
        if unit is None:
            return
        with self.draft.load((unit['side'], unit['side_index'])):
            self._display_unit()
        self._update_arrival_controls()
        if self.counter_index != unit['counter_index']:
            self.preview_chit(self.counter_index)
        if self.draft.context in self.draft.pending():
            self.feedback.config(text='Unapplied edits retained. Apply Changes or Save keeps them.')

    def _display_unit(self):
        unit = self.current_unit
        if unit is None:
            return
        self.apply_button.config(state='disabled' if unit.get('deleted') else 'normal')
        self.feedback.config(text='')
        self.name_entry.delete(0, tk.END)
        self.name_entry.insert(0, unit['name'])
        self.type_label.config(text=unit['type_name'])
        self.side_label.config(text=unit['side'])
        self.unit_status_label.config(text=unit_status(unit))
        self.availability_combo.config(state='readonly')
        availability = ('Inactive' if unit['arrival_time'] == -1 else
                        'At start' if unit['arrival_time'] < unit['start_time'] else 'Scheduled')
        self.availability_var.set(availability)
        self.arrival_turn_spin.config(state='normal', to=max(1, unit['end_time'] - unit['start_time'] + 1))
        self.arrival_turn_spin.set(max(1, unit['arrival_time'] - unit['start_time'] + 1))
        self.arrival_hint.config(text=f"Current turn: {unit['current_time'] - unit['start_time'] + 1}. "
                                'Scheduled units enter during their arrival turn.')
        self._update_arrival_controls()
        self.pos_x_spin.config(to=unit['map_width'] - (1 if unit['unit_class'] in (5, 6) else 2))
        self.pos_y_spin.config(to=unit['map_height'] - (1 if unit['unit_class'] in (5, 6) else 2))
        self.pos_x_spin.set(unit['x'])
        self.pos_y_spin.set(unit['y'])
        for key, spin in self.stat_spins.items():
            spin.set(format_unit_value(unit[key]))
        for key, label in self.saved_stats.items():
            label.config(text=format_unit_value(unit[key]))
        self.quality_state_label.config(
            text=f"Saved quality\nAttack: {unit['attack_quality']}\nDefense: {unit['defense_quality']}")
        self.order_label.config(text=unit_order_label(unit))
        has_automation = any(key in unit for key in self.ai_vars)
        self.hq_label.config(text=unit.get('hq_name', 'Not applicable') if has_automation else 'Unavailable')
        for key, check in self.ai_checks.items():
            self.ai_vars[key].set(bool(unit.get(key, False)))
            check.config(state='normal' if key in unit and not unit.get('deleted') else 'disabled')
        self.ai_hint.config(text=(
            'Staff assistance is shared by all units assigned to this HQ. '
            'Computer control and Battle Plans can replace plotted orders during play.'
            if has_automation else
            'HQ staff assistance does not apply to aircraft or ships.' if unit['unit_class'] in (5, 6) else
            'HQ staff assistance is unavailable for this unit.'))
        is_support = unit['unit_class'] in (5, 6)
        for button in self.operation_buttons.values():
            button.config(state='disabled' if is_support or unit.get('deleted') else 'normal')
        self.counter_index = unit['counter_index']
        self.chit_button.config(text='Category artwork…' if is_support else 'Choose chit…',
                                state='disabled' if unit.get('deleted') else 'normal')
        self.import_chit_button.config(state='disabled' if unit.get('deleted') else 'normal')
        try:
            if is_support:
                art = support_unit_icon(unit['unit_class'], unit['type'], unit['side'], unit.get('support_artwork'))
                scale = 2
            else:
                art = unit_counter(unit['counter_resource'], unit['counter_index'], unit.get('counter_bitmap'))
                scale = 3
            self.chit_image = ImageTk.PhotoImage(art.resize(
                (art.width * scale, art.height * scale), Image.Resampling.NEAREST))
            self.chit_label.config(image=self.chit_image, text='')
        except (OSError, RuntimeError, ValueError):
            self.chit_image = None
            self.chit_label.config(image='', text='Artwork unavailable')

        if unit.get('deleted'):
            self.feedback.config(text='Use Restore Unit to return this unit to the scenario.')

    def choose_chit(self):
        if self.current_unit:
            if self.current_unit['unit_class'] in (5, 6):
                self.on_support_artwork()
            else:
                CounterDialog(self, self.current_unit, self.counter_index, self.preview_chit)

    def preview_chit(self, index):
        self.counter_index = index
        unit = self.current_unit
        art = unit_counter(unit['counter_resource'], index, unit.get('counter_bitmap'))
        self.chit_image = ImageTk.PhotoImage(art.resize((66, 69), Image.Resampling.NEAREST))
        self.chit_label.config(image=self.chit_image, text='')
        self.feedback.config(text='Chit selected. Use Apply Changes to keep it.')

    def apply_changes(self):
        if self.current_unit is None or self.current_unit.get('deleted'):
            return False
        values = {key: spin.get() for key, spin in self.stat_spins.items()}
        values.update(name=self.name_entry.get(), x=self.pos_x_spin.get(), y=self.pos_y_spin.get())
        if self.current_unit['unit_class'] not in (5, 6):
            values['counter_index'] = self.counter_index
        values.update({key: variable.get() for key, variable in self.ai_vars.items() if key in self.current_unit})
        try:
            values['arrival_time'] = arrival_time_from_form(
                self.current_unit, self.availability_var.get(), self.arrival_turn_spin.get())
            updated, patches = prepare_unit_changes(self.current_unit, values)
            if patches and self.on_unit_update_callback:
                self.on_unit_update_callback(self.current_unit, updated, patches)
        except ValueError as exc:
            messagebox.showerror('Invalid unit value', str(exc))
            return False
        self.current_unit.update(updated)
        self.draft.accept()
        self.unit_combo['values'] = [f"{u['side']} · {u['side_index']}: {u['name']}" for u in self.units]
        self.unit_combo.current(self.units.index(self.current_unit))
        self.display_unit()
        self.feedback.config(text='Changes applied. Use File → Save to write them.' if patches else 'No changes.')
        return True

    def revert_changes(self):
        self.draft.revert()
        self.display_unit()


class AddUnitDialog(tk.Toplevel):
    """Choose a complete unit template, including its artwork and class data."""

    def __init__(self, app):
        super().__init__(app.root)
        self.app = app
        self.title('Add Unit')
        self.transient(app.root)
        self.resizable(False, False)
        body = ttk.Frame(self, padding=16)
        body.pack(fill=tk.BOTH, expand=True)
        ttk.Label(body, text='Choose a template for the new unit’s type, artwork, and strengths.',
                  wraplength=460).grid(row=0, column=0, columnspan=2, sticky=tk.W, pady=(0, 12))
        self.side = tk.StringVar(value=(app.unit_props_editor.current_unit or {}).get('side', 'Allied'))
        ttk.Label(body, text='Side:').grid(row=1, column=0, sticky=tk.W)
        side_combo = ttk.Combobox(body, values=('Allied', 'Axis'), textvariable=self.side, state='readonly')
        side_combo.grid(row=1, column=1, sticky=tk.W, padx=8, pady=4)
        side_combo.bind('<<ComboboxSelected>>', self.load_templates)
        ttk.Label(body, text='Template:').grid(row=2, column=0, sticky=tk.W)
        self.template_combo = ttk.Combobox(body, state='readonly', width=48)
        self.template_combo.grid(row=2, column=1, padx=8, pady=4)
        self.template_combo.bind('<<ComboboxSelected>>', self.select_template)
        ttk.Label(body, text='New name:').grid(row=3, column=0, sticky=tk.W)
        self.name_var = tk.StringVar()
        self.name_entry = ttk.Entry(body, textvariable=self.name_var, width=35)
        self.name_entry.grid(row=3, column=1, sticky=tk.W, padx=8, pady=4)
        self.template_hint = ttk.Label(body, wraplength=460)
        self.template_hint.grid(
                      row=4, column=0, columnspan=2, sticky=tk.W, pady=12)
        buttons = ttk.Frame(body)
        buttons.grid(row=5, column=0, columnspan=2, sticky=tk.E)
        ttk.Button(buttons, text='Cancel', command=self.destroy).pack(side=tk.LEFT, padx=6)
        self.add_button = ttk.Button(buttons, text='Add Unit', command=self.submit)
        self.add_button.pack(side=tk.LEFT)
        self.source_paths = [None, *dict.fromkeys(item['game'] for item in unit_library())]
        names = {'dday':'D-Day', 'stalingrad':'Stalingrad', 'operation_crusader':'Operation Crusader',
                 'v4v_utah':'V4V · Utah Beach', 'v4v_vl':'V4V · Velikiye Luki',
                 'v4v_mg':'V4V · Market Garden', 'v4v_gjs':'V4V · Gold–Juno–Sword'}
        ttk.Label(body, text='Templates from:').grid(row=6, column=0, sticky=tk.W, pady=(12, 4))
        self.source_combo = ttk.Combobox(body, state='readonly', width=48,
            values=['Current scenario', *[names[k] for k in self.source_paths[1:]]])
        self.source_combo.grid(row=6, column=1, padx=8, pady=(12, 4))
        self.source_combo.current(0 if app.units else min(1, len(self.source_paths)-1))
        self.source_combo.bind('<<ComboboxSelected>>', self.load_templates)
        ttk.Label(body, text='Search name / type / scenario:').grid(row=7, column=0, sticky='w')
        self.search = tk.StringVar()
        ttk.Entry(body, textvariable=self.search, width=48).grid(row=7, column=1, padx=8, pady=5)
        self.search.trace_add('write', lambda *a: self.load_templates())
        self.preview = ttk.Label(body)
        self.preview.grid(row=8, column=0, columnspan=2, pady=8)
        self.load_templates()
        self.update_idletasks()
        self.geometry(f'+{app.root.winfo_rootx() + max(0, (app.root.winfo_width() - self.winfo_width()) // 2)}'
                      f'+{app.root.winfo_rooty() + max(0, (app.root.winfo_height() - self.winfo_height()) // 2)}')
        self.bind('<Escape>', lambda event: self.destroy())
        self.bind('<Return>', lambda event: self.submit())
        self.grab_set()
        self.name_entry.focus_set()

    def load_templates(self, event=None):
        path = self.source_paths[self.source_combo.current()]
        side = ('Allied', 'Axis').index(self.side.get())
        available = template_choices(path, side) if path else self.app.units
        query = self.search.get().casefold()
        self.templates = [dict(u) for u in available if u['side'] == self.side.get()
                          and query in (u['name']+' '+u['type_name']+' '+u.get('provenance','')).casefold()]
        self.template_combo['values'] = [f"{u['name']} — {u['type_name']}" +
            (f" · {u['provenance']}" if u.get('provenance') else '') for u in self.templates]
        current = self.app.unit_props_editor.current_unit
        if self.templates:
            preferred = next((i for i, u in enumerate(self.templates)
                              if not path and current and u['index'] == current['index']), 0)
            if path and not any(u['side'] == self.side.get() for u in self.app.units):
                preferred = next((i for i, u in enumerate(self.templates) if u['unit_class'] == 7), 0)
            self.template_combo.current(preferred)
            self.add_button.config(state='normal')
            self.select_template()
        else:
            self.template_combo.set('No matching unit templates')
            self.preview.config(image='')
            self.add_button.config(state='disabled')
        self.template_hint.config(text=(
            'Imported ground units start inactive. Deploy them on Map when ready.\n'
            'New ground units join the first HQ; add an HQ for this side first.' if path else
            'The new unit starts with the template’s position and arrival.\n'
            'You can edit these on the Units page.'))

    def select_template(self, event=None):
        if not self.templates or self.template_combo.current() < 0:
            return
        unit = self.templates[self.template_combo.current()]
        if 'library_id' in unit:
            pixels = unit_library()[unit['library_id']]['chit']
            if pixels:
                from lib.game_art import load_bitmap
                image = Image.frombytes('P', (22,23), pixels)
                image.putpalette(load_bitmap(128).getpalette())
                self.preview_image = ImageTk.PhotoImage(image.resize((66,69), Image.Resampling.NEAREST))
                self.preview.config(image=self.preview_image)
            else:
                self.preview.config(image='')
        else:
            self.preview.config(image='')
        existing = {u['name'].casefold() for u in self.app.units}
        name = ('New ' + unit['name'])[:25]
        number = 2
        while name.casefold() in existing:
            suffix = f' {number}'
            name = ('New ' + unit['name'])[:25 - len(suffix)] + suffix
            number += 1
        self.name_var.set(name)
        self.name_entry.selection_range(0, tk.END)

    def submit(self):
        if self.templates and self.app.create_unit(self.templates[self.template_combo.current()], self.name_var.get()):
            self.destroy()


class ImprovedScenarioEditor:
    """Main improved scenario editor application"""

    def __init__(self):
        self.scenario = None
        self.scenario_file = None
        self.modified = False
        self.units = []
        self.coords = []
        self.mod_tracker = ModificationTracker()  # Track modifications for patch-in-place saving
        self.saved_data = b''
        self.history = EditHistory()
        self.history_window = None
        self._pending_edit = None
        self._history_briefings = None
        self._restoring_history = False
        self.terrain_artwork = {}
        self.saved_artwork = {}
        self.counter_artwork = {}
        self.saved_counters = {}
        self.presentation_artwork = {}
        self.saved_presentation = {}
        self.document = self.saved_document = ScenarioDocument()
        self.runtime_slot = None
        self.is_new = False
        self.import_name = None
        self._draft_refresh = None
        self._closing = False

        # Create main window
        self.root = tk.Tk()
        self.root.title("D-Day Scenario Editor")
        self.root.geometry("1400x900")
        self._set_application_icon()

        # Configure style
        style = ttk.Style()
        style.theme_use('clam')

        self._create_menu()
        self._create_toolbar()
        self._create_main_ui()
        self._create_statusbar()
        self.root.protocol('WM_DELETE_WINDOW', self.close_editor)

        # Keyboard shortcuts
        self.root.bind('<Control-n>', lambda e: self.new_scenario())
        self.root.bind('<Control-o>', lambda e: self.open_scenario())
        self.root.bind('<Control-s>', lambda e: self.save_scenario())
        self.root.bind('<Control-Shift-S>', lambda e: self.save_scenario_as())
        self.root.bind('<F5>', lambda e: self.reload_scenario())
        self._bind_history_shortcuts(self.root)
        self._update_history_actions()

    def _set_application_icon(self):
        """Set the window/task-switcher icon, including subsequently opened dialogs."""
        icon_path = Path(__file__).resolve().parent / 'assets' / 'app' / 'icon.png'
        self._icon_images = []
        try:
            with Image.open(icon_path) as source:
                self._icon_images = [
                    ImageTk.PhotoImage(source.resize((size, size), Image.Resampling.LANCZOS),
                                       master=self.root)
                    for size in (16, 24, 32, 48, 64, 128, 256)
                ]
            self.root.iconphoto(True, *self._icon_images)
        except (OSError, tk.TclError) as exc:
            print(f"Could not load application icon: {exc}")

    def _create_menu(self):
        """Create menu bar"""
        menubar = tk.Menu(self.root)

        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label='New Scenario...', command=self.new_scenario, accelerator='Ctrl+N')
        file_menu.add_command(label="Open Scenario...", command=self.open_scenario,
                             accelerator="Ctrl+O")
        file_menu.add_separator()
        file_menu.add_command(label="Save", command=self.save_scenario,
                             accelerator="Ctrl+S")
        file_menu.add_command(label="Save As...", command=self.save_scenario_as,
                             accelerator="Ctrl+Shift+S")
        file_menu.add_separator()
        file_menu.add_command(label="Reload", command=self.reload_scenario,
                             accelerator="F5")
        file_menu.add_command(label="Export for DOS...", command=self.export_scenario_for_dos)
        file_menu.add_command(label='Conversion Notes...', command=self.show_conversion_notes)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.close_editor)
        menubar.add_cascade(label="File", menu=file_menu)

        # Edit menu
        edit_menu = self.edit_menu = tk.Menu(menubar, tearoff=0)
        edit_menu.add_command(label='Undo', command=self.undo_edit, accelerator='Ctrl+Z', state='disabled')
        edit_menu.add_command(label='Redo', command=self.redo_edit, accelerator='Ctrl+Y', state='disabled')
        edit_menu.add_command(label='Edit History...', command=self.show_edit_history, state='disabled')
        edit_menu.add_separator()
        edit_menu.add_command(label="Scenario Settings...",
                             command=lambda: self.notebook.select(self.settings_frame))
        menubar.add_cascade(label="Edit", menu=edit_menu)

        # Tools menu
        tools_menu = tk.Menu(menubar, tearoff=0)
        tools_menu.add_command(label="Validate Scenario", command=self.validate_scenario)
        tools_menu.add_command(label="Export Unit List...", command=self.export_units)
        menubar.add_cascade(label="Tools", menu=tools_menu)

        # Help menu
        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(label="User Guide", command=self.show_help)
        help_menu.add_command(label="About", command=self.show_about)
        menubar.add_cascade(label="Help", menu=help_menu)

        self.root.config(menu=menubar)

    def _create_toolbar(self):
        """Create toolbar"""
        toolbar = ttk.Frame(self.root, relief=tk.RAISED)
        toolbar.pack(fill=tk.X, padx=5, pady=5)

        ttk.Button(toolbar, text='New', command=self.new_scenario).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Open", command=self.open_scenario).pack(side=tk.LEFT, padx=2)
        self.save_button = ttk.Button(toolbar, text="Save", command=self.save_scenario)
        self.save_button.pack(side=tk.LEFT, padx=2)
        self.save_as_button = ttk.Button(toolbar, text="Save As...", command=self.save_scenario_as)
        self.save_as_button.pack(side=tk.LEFT, padx=2)

        self.undo_button = ttk.Button(toolbar, text='Undo', command=self.undo_edit, state='disabled')
        self.undo_button.pack(side=tk.LEFT, padx=(12, 2))
        self.redo_button = ttk.Button(toolbar, text='Redo', command=self.redo_edit, state='disabled')
        self.redo_button.pack(side=tk.LEFT, padx=2)
        self.history_button = ttk.Button(toolbar, text='History...', command=self.show_edit_history, state='disabled')
        self.history_button.pack(side=tk.LEFT, padx=2)

        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=5)

        ttk.Button(toolbar, text="Validate", command=self.validate_scenario).pack(side=tk.LEFT, padx=2)

        self.file_label = ttk.Label( toolbar, text = '!! NO SCENARIO FILE LOADED !!',
                                     font = ( "TkDefaultFont", 9, "bold" ) )

        self.file_label.pack( side = tk.LEFT, padx = 20 )

    def _create_main_ui(self):
        """Create main UI with notebook"""
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        self._create_mission_tab()
        self._create_map_tab()

        # Units and their arrivals share one roster and property form.
        self._create_unit_editor_tab()

        self._create_settings_tab()
        self.artwork_panel = ArtworkPanel(self.notebook, self)
        self.notebook.add(self.artwork_panel, text='Artwork')
        self._create_terrain_reference_tab()

    def _create_mission_tab(self):
        """Create mission briefing editor tab"""
        frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(frame, text="Mission Briefings")

        inst_label = ttk.Label(frame,
            text="Edit mission briefings · Up to 8 lines per side, 127 characters per line · Save writes changes",
            font=("TkDefaultFont", 9, "bold"))
        inst_label.pack(pady=5)

        # Paned window for side-by-side editing
        paned = ttk.PanedWindow(frame, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True)

        # Allied frame
        allied_frame = ttk.LabelFrame(paned, text="Allied Briefing", padding="10")
        paned.add(allied_frame, weight=1)

        self.allied_text = scrolledtext.ScrolledText(allied_frame,
                                                     height=25,
                                                     width=50,
                                                     wrap=tk.WORD)
        self.allied_text.pack(fill=tk.BOTH, expand=True)
        self.allied_text.bind('<<Modified>>', self._on_text_modified)
        self.allied_text.bind('<FocusOut>', lambda e: self._end_briefing_group())

        # Axis frame
        axis_frame = ttk.LabelFrame(paned, text="Axis Briefing", padding="10")
        paned.add(axis_frame, weight=1)

        self.axis_text = scrolledtext.ScrolledText(axis_frame,
                                                   height=25,
                                                   width=50,
                                                   wrap=tk.WORD)
        self.axis_text.pack(fill=tk.BOTH, expand=True)
        self.axis_text.bind('<<Modified>>', self._on_text_modified)
        self.axis_text.bind('<FocusOut>', lambda e: self._end_briefing_group())

    def _create_map_tab(self):
        """Create the Map tab."""
        frame = ttk.Frame(self.notebook, padding="10")
        self.map_frame = frame
        self.notebook.add(frame, text="Map")

        self.map_viewer = MapViewer(frame, self.edit_map_terrain, self.place_map_unit,
                                    self.undo_roster_change, self.edit_map_feature, self.edit_map_tool)
        self.map_viewer.pack(fill=tk.BOTH, expand=True)
        self.map_viewer.edit_controls.browse_terrain_button.config(
            command=lambda: self.notebook.select(self.terrain_reference_tab))
        self.map_viewer.edit_controls.restore_artwork_button.config(command=self.restore_terrain_artwork)
        self.map_viewer.edit_controls.import_image_button.config(command=self.import_terrain_image)
        self.map_viewer.edit_controls.export_image_button.config(command=self.export_terrain_image)
        self.map_redo_button = ttk.Button(self.map_viewer.edit_controls, text='Redo',
                                          command=self.redo_edit, state='disabled')
        self.map_redo_button.pack(fill=tk.X, after=self.map_viewer.edit_controls.undo_button, pady=(0, 6))

    def _create_unit_editor_tab(self):
        """One roster for deployed units, reinforcements, and off-map support."""
        frame = ttk.Frame(self.notebook, padding="10")
        self.units_frame = frame
        self.notebook.add(frame, text="Units")

        actions = ttk.Frame(frame)
        actions.pack(fill=tk.X, pady=(0, 8))
        self.add_unit_button = ttk.Button(actions, text='Add Unit…', command=self.add_unit, state='disabled')
        self.add_unit_button.pack(side=tk.LEFT, padx=(0, 6))
        self.delete_unit_button = ttk.Button(actions, text='Delete Unit', command=self.delete_unit, state='disabled')
        self.delete_unit_button.pack(side=tk.LEFT, padx=(0, 6))
        self.organization_button = ttk.Button(actions, text='HQ Organization…',
            command=self.edit_unit_organization, state='disabled')
        self.organization_button.pack(side=tk.LEFT, padx=(0, 6))
        self.definition_button = ttk.Button(actions, text='Unit Definition…',
            command=self.edit_unit_definition, state='disabled')
        self.definition_button.pack(side=tk.LEFT, padx=(0, 6))
        self.undo_roster_button = ttk.Button(actions, text='Undo Last Edit', command=self.undo_roster_change,
                                             state='disabled')
        self.undo_roster_button.pack(side=tk.LEFT)
        self.redo_roster_button = ttk.Button(actions, text='Redo', command=self.redo_edit, state='disabled')
        self.redo_roster_button.pack(side=tk.LEFT, padx=6)

        filters = ttk.Frame(frame)
        filters.pack(fill=tk.X, pady=(0, 8))
        ttk.Label(filters, text='Show:').pack(side=tk.LEFT)
        self.unit_filter_var = tk.StringVar(value='All units')
        self.unit_filter = ttk.Combobox(filters, textvariable=self.unit_filter_var, state='readonly',
                                      values=('All units', 'In play', 'Reinforcements', 'Off map',
                                              'Inactive', 'Outside map', 'Deleted'), width=16)
        self.unit_filter.pack(side=tk.LEFT, padx=(6, 16))
        ttk.Label(filters, text='Find unit:').pack(side=tk.LEFT)
        self.unit_search_var = tk.StringVar()
        ttk.Entry(filters, textvariable=self.unit_search_var, width=24).pack(side=tk.LEFT, padx=6)
        self.unit_roster_summary = ttk.Label(filters)
        self.unit_roster_summary.pack(side=tk.RIGHT, padx=6)

        # Split into unit list and properties editor
        paned = ttk.PanedWindow(frame, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True)

        # Left: Unit list with tabs by side
        left_frame = ttk.LabelFrame(paned, text="Unit List (base strengths)", padding="5")
        paned.add(left_frame, weight=1)

        # Create notebook for tabs
        self.unit_list_notebook = ttk.Notebook(left_frame)
        self.unit_list_notebook.pack(fill=tk.BOTH, expand=True)

        # Dictionary to store treeviews for each side
        self.unit_trees_by_side = {}

        # Right: Properties editor
        right_frame = ttk.Frame(paned)
        paned.add(right_frame, weight=1)

        properties_actions = ttk.Frame(right_frame)
        properties_actions.pack(side=tk.BOTTOM, fill=tk.X)

        self.unit_details_canvas = tk.Canvas(right_frame, highlightthickness=0)
        details_scroll = ttk.Scrollbar(right_frame, orient=tk.VERTICAL,
                                       command=self.unit_details_canvas.yview)
        self.unit_details_canvas.config(yscrollcommand=details_scroll.set)
        details_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.unit_details_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.unit_props_editor = UnitPropertiesEditor(
            self.unit_details_canvas, self.on_unit_updated, self._sync_unit_selection,
            action_parent=properties_actions, on_draft_changed=self._draft_changed,
            get_counter_artwork=lambda: self.counter_artwork, on_import_chit=self.import_unit_image,
            on_operations=self.edit_unit_operations, on_support_artwork=self.edit_support_artwork,
            get_presentation_artwork=lambda: self.presentation_artwork)
        details_window = self.unit_details_canvas.create_window(
            (0, 0), window=self.unit_props_editor, anchor=tk.NW)
        self.unit_details_canvas.bind('<Configure>', lambda event:
            self.unit_details_canvas.itemconfigure(details_window, width=event.width))
        self.unit_props_editor.bind('<Configure>', lambda event:
            self.unit_details_canvas.configure(scrollregion=self.unit_details_canvas.bbox('all')))

        def bind_scroll(widget):
            # Text boxes and value controls keep their own wheel behavior.
            if widget.winfo_class() not in ('Text', 'TSpinbox', 'TCombobox'):
                for sequence in ('<MouseWheel>', '<Button-4>', '<Button-5>'):
                    widget.bind(sequence, self._scroll_unit_properties)
            for child in widget.winfo_children():
                bind_scroll(child)

        bind_scroll(self.unit_details_canvas)
        self.unit_filter_var.trace_add('write', lambda *_: self._refresh_unit_roster())
        self.unit_search_var.trace_add('write', lambda *_: self._refresh_unit_roster())
        self.unit_list_notebook.bind('<<NotebookTabChanged>>',
                                    lambda event: self._refresh_unit_roster(preserve_form=True))

        def initialize_split(event):
            if event.width > 1:
                paned.sashpos(0, event.width // 2)
                paned.unbind('<Configure>')

        paned.bind('<Configure>', initialize_split)

    def _scroll_unit_properties(self, event):
        steps = (-1 if getattr(event, 'num', None) == 4 else
                 1 if getattr(event, 'num', None) == 5 else -int(event.delta / 120))
        self.unit_details_canvas.yview_scroll(steps, 'units')
        return 'break'

    def _create_settings_tab(self):
        """Create scenario settings tab"""
        frame = ttk.Frame(self.notebook, padding="10")
        self.settings_frame = frame
        self.notebook.add(frame, text="Scenario Settings")

        self.settings_editor = ScenarioSettingsEditor(frame, self)
        self.settings_editor.pack(fill=tk.BOTH, expand=True)

    def _create_terrain_reference_tab(self):
        """Create terrain reference tab"""
        frame = ttk.Frame(self.notebook, padding="10")
        self.terrain_reference_tab = frame
        self.notebook.add(frame, text="Terrain Reference")

        controls = ttk.Frame(frame)
        controls.pack(fill=tk.X, padx=10, pady=5)
        ttk.Label(controls, text='Artwork:', font=('TkDefaultFont', 10, 'bold')).pack(side=tk.LEFT)
        self.terrain_source_combo = ttk.Combobox(controls, state='readonly', width=24,
                                               values=list(ART_SOURCES.values()))
        self.terrain_source_combo.current(0)
        self.terrain_source_combo.pack(side=tk.LEFT, padx=8)
        self.terrain_source_combo.bind('<<ComboboxSelected>>', self._refresh_terrain_reference_tab)
        ttk.Button(controls, text='Import Image…', command=self.import_terrain_image).pack(side=tk.LEFT, padx=8)
        self.terrain_used_only = tk.BooleanVar(value=False)
        self.terrain_usage_filter = ttk.Checkbutton(controls, text='Only show terrain used in this scenario',
                        variable=self.terrain_used_only,
                        command=self._refresh_terrain_reference_tab)
        self.terrain_usage_filter.pack(side=tk.RIGHT)
        self.terrain_catalog_hint = ttk.Label(frame, wraplength=900)
        self.terrain_catalog_hint.pack(anchor=tk.W, padx=10)

        # Scrollable frame for terrain types
        canvas_container = ttk.Frame(frame)
        canvas_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        terrain_canvas = tk.Canvas(canvas_container, bg='white')
        scrollbar = ttk.Scrollbar(canvas_container, orient=tk.VERTICAL,
                                  command=terrain_canvas.yview)
        terrain_canvas.config(yscrollcommand=scrollbar.set)

        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        terrain_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Container frame inside canvas
        terrain_frame = ttk.Frame(terrain_canvas)
        reference_window = terrain_canvas.create_window((0, 0), window=terrain_frame, anchor=tk.NW)
        terrain_canvas.bind('<Configure>', lambda event:
                            terrain_canvas.itemconfigure(reference_window, width=event.width))

        self.terrain_reference_canvas = terrain_canvas
        self.terrain_reference_frame = terrain_frame
        self._terrain_preview_images = []
        self._refresh_terrain_reference_tab()

        # Configure grid weights
        terrain_frame.columnconfigure(0, weight=1)

        # Update scroll region
        terrain_frame.update_idletasks()
        terrain_canvas.config(scrollregion=terrain_canvas.bbox('all'))

        self._bind_terrain_reference_scroll(terrain_canvas)

    def _bind_terrain_reference_scroll(self, widget):
        def scroll(event):
            step = (-1 if getattr(event, 'num', None) == 4 else
                    1 if getattr(event, 'num', None) == 5 else -int(event.delta / 120))
            self.terrain_reference_canvas.yview_scroll(step, 'units')
            return 'break'
        for sequence in ('<MouseWheel>', '<Button-4>', '<Button-5>'):
            widget.bind(sequence, scroll)
        for child in widget.winfo_children():
            self._bind_terrain_reference_scroll(child)

    def _refresh_terrain_reference_tab(self, event=None):
        """Show the complete catalog; scenario usage is optional metadata/filtering."""
        if not hasattr(self, 'terrain_reference_frame'):
            return

        for child in self.terrain_reference_frame.winfo_children():
            child.destroy()

        self._terrain_preview_images = []
        self.terrain_reference_buttons = {}
        self.terrain_reference_usage = {}
        source = list(ART_SOURCES)[self.terrain_source_combo.current()]
        self.terrain_usage_filter.config(state='normal' if source == 'dday' else 'disabled')
        if source != 'dday':
            self._show_import_artwork(source)
            return
        self.terrain_catalog_hint.config(text='All 14 D-Day terrain types and their six base variants. '
            'Click a variant to paint it. Other games’ terrain is available in the Artwork menu.')
        terrain = getattr(self.map_viewer, 'terrain', {})
        type_counts = Counter()
        for terrain_data in terrain.values():
            terrain_id = terrain_data[0] if isinstance(terrain_data, tuple) else terrain_data
            type_counts[terrain_id] += 1
        total_hexes = sum(type_counts.values())
        entries = [entry for entry in terrain_catalog()
                   if not self.terrain_used_only.get() or type_counts[entry.code]]
        for row, entry in enumerate(entries):
            terrain_id = entry.code
            count = type_counts[terrain_id]
            pct = (count / total_hexes) * 100 if total_hexes else 0
            entry_frame = ttk.Frame(self.terrain_reference_frame, relief=tk.RIDGE, borderwidth=1)
            entry_frame.grid(row=row, column=0, sticky=tk.EW, padx=5, pady=3)
            type_label = ttk.Label(
                entry_frame,
                text=entry.name,
                font=("TkDefaultFont", 10, "bold")
            )
            type_label.grid(row=0, column=0, sticky=tk.W, padx=10, pady=(10, 0))
            usage = (f"{count:,} {'hex' if count == 1 else 'hexes'} ({pct:.1f}%)" if count else
                     'Not used in this scenario' if terrain else 'Available without a scenario')
            count_label = ttk.Label(entry_frame, text=usage, width=28)
            count_label.grid(row=1, column=0, sticky=tk.NW, padx=10, pady=5)
            self.terrain_reference_usage[terrain_id] = count_label
            for column, variant in enumerate(entry.variants, 1):
                photo_img = self._create_terrain_reference_preview(terrain_id, variant)
                button = ttk.Button(entry_frame, text=f'Variant {variant}', image=photo_img or '',
                                    compound=tk.TOP, command=lambda code=terrain_id, value=variant:
                                    self._choose_catalog_terrain(code, value))
                button.grid(row=0, column=column, rowspan=2, padx=5, pady=5)
                self.terrain_reference_buttons[terrain_id, variant] = button
        if not entries:
            ttk.Label(self.terrain_reference_frame, text='No terrain usage to show. Turn off the usage filter to browse the full catalog.').grid(
                row=0, column=0, sticky=tk.W, padx=10, pady=10)
        self.terrain_reference_frame.columnconfigure(0, weight=1)
        self._bind_terrain_reference_scroll(self.terrain_reference_frame)
        self._update_terrain_reference_scrollregion()

    def _show_import_artwork(self, source):
        self.terrain_catalog_hint.config(text='Click terrain to paint it. The editor inserts its artwork automatically. '
            'Export for DOS includes the matching graphics. Each row shows its D-Day terrain rules.')
        try:
            entries = artwork_catalog(source)
            for row, entry in enumerate(entries):
                frame = ttk.LabelFrame(self.terrain_reference_frame,
                    text=f'{entry.name} · D-Day rules: {terrain_name(entry.dday_terrain)}', padding=6)
                frame.grid(row=row, column=0, sticky=tk.EW, padx=5, pady=4)
                for ordinal, column in enumerate(entry.columns):
                    art = entry.tile(column).convert('RGBA').resize((60, 68), Image.Resampling.NEAREST)
                    photo = ImageTk.PhotoImage(art)
                    self._terrain_preview_images.append(photo)
                    caption = (f'Artwork {ordinal + 1}' if entry.terrain_for_column(column) == entry.dday_terrain else
                               f'Artwork {ordinal + 1} · {terrain_name(entry.terrain_for_column(column))}')
                    button = ttk.Button(frame, text=caption, image=photo, compound=tk.TOP,
                        command=lambda entry=entry, column=column: self._import_catalog_artwork(source, entry, column))
                    button.grid(row=ordinal // 6, column=ordinal % 6, padx=5, pady=5)
                    self.terrain_reference_buttons[source, entry.row, column] = button
        except (OSError, ValueError, RuntimeError) as exc:
            ttk.Label(self.terrain_reference_frame, text=f'Cannot load this artwork: {exc}', wraplength=700).grid(
                row=0, column=0, sticky=tk.W, padx=10, pady=10)
        self._bind_terrain_reference_scroll(self.terrain_reference_frame)
        self._update_terrain_reference_scrollregion()

    def _import_catalog_artwork(self, source, entry, column):
        if not self.scenario:
            messagebox.showinfo('Import Terrain Artwork', 'Open a D-Day scenario to assign artwork and paint its map.')
            return
        try:
            stamp = TerrainStamp.from_artwork(entry, column, ART_SOURCES[source])
        except (OSError, ValueError) as exc:
            messagebox.showerror('Cannot Import Artwork', str(exc))
            return
        code = entry.terrain_for_column(column)
        variant = automatic_artwork_slot(code, stamp, self.map_viewer.terrain, self.terrain_artwork)
        if variant is None:
            self.terrain_import_dialog = TerrainImportDialog(self, stamp, code)
            return
        self.assign_terrain_artwork(code, variant, stamp)
        self._choose_catalog_terrain(code, variant)

    def _choose_catalog_terrain(self, terrain_id, variant):
        self.map_viewer.edit_controls.choose_terrain(terrain_id, variant)
        self.notebook.select(self.map_frame)

    def import_terrain_image(self):
        if not self.scenario:
            messagebox.showinfo('Import Terrain', 'Open or create a scenario first.')
            return
        from lib.custom_images import import_terrain
        filename = filedialog.askopenfilename(parent=self.root, title='Import Terrain Image',
            filetypes=[('Images', '*.png *.bmp *.gif *.jpg *.jpeg *.webp'), ('All files', '*.*')])
        if filename:
            try:
                stamp = import_terrain(filename)
                panel = self.map_viewer.edit_controls
                code = panel.terrain_choices[panel.terrain_combo.current()]
                self.terrain_import_dialog = TerrainImportDialog(self, stamp, code)
            except (OSError, ValueError, Image.DecompressionBombError) as exc:
                messagebox.showerror('Cannot Import Terrain', str(exc), parent=self.root)

    def import_unit_image(self):
        if not self.scenario or not self._apply_form_drafts():
            return
        unit = self.unit_props_editor.current_unit
        if not unit or unit.get('deleted'):
            return
        if unit['unit_class'] in (5, 6):
            self.edit_support_artwork(import_image=True)
            return
        from lib.custom_images import import_counter
        from lib.custom_image_dialog import ChitImportDialog
        filename = filedialog.askopenfilename(parent=self.root, title='Import Unit Chit',
            filetypes=[('Images', '*.png *.bmp *.gif *.jpg *.jpeg *.webp'), ('All files', '*.*')])
        if filename:
            try:
                self.chit_import_dialog = ChitImportDialog(self, import_counter(filename), Path(filename).name,
                    ('Allied', 'Axis').index(unit['side']), unit['side_index'])
            except (OSError, ValueError, Image.DecompressionBombError) as exc:
                messagebox.showerror('Cannot Import Chit', str(exc), parent=self.root)

    def edit_support_artwork(self, import_image=False):
        if not self.scenario or not self._apply_form_drafts():
            return
        unit = self.unit_props_editor.current_unit
        if unit and unit['unit_class'] in (5, 6):
            from lib.support_units import artwork_key
            key = artwork_key(unit['unit_class'], unit['type'], int(unit['side'] == 'Axis'))
            panel = self.artwork_panel
            self.notebook.select(panel)
            panel.tree.selection_set(key)
            panel.tree.see(key)
            panel.select_slot()
            if import_image:
                panel.import_file()

    def export_terrain_image(self):
        panel = self.map_viewer.edit_controls
        code = panel.terrain_choices[panel.terrain_combo.current()]
        variant = int(panel.variant_combo.get())
        filename = filedialog.asksaveasfilename(parent=self.root, title='Export Terrain Image',
            initialfile=f'terrain_{code}_{variant}.png', defaultextension='.png', filetypes=[('PNG image', '*.png')])
        if filename:
            try:
                self.map_viewer.hex_tile_loader.get_tile_with_variant(code, variant).save(filename, format='PNG')
            except (OSError, ValueError) as exc:
                messagebox.showerror('Cannot Export Terrain', str(exc), parent=self.root)

    def assign_custom_counter(self, side, index, pixels):
        from lib.counter_artwork import allocate_counter
        roster = UnitRoster(self._staged_data(include_briefings=False))
        record = roster.records[side][index]
        if record[0x76] in (5, 6):
            raise ValueError('Choose a ground unit for this chit')
        number, counters = allocate_counter(roster, self.counter_artwork, side, pixels)
        struct.pack_into('<h', record, 0x56, number)
        self.apply_unit_structure(roster.to_bytes(), side, index, 'Import custom unit chit', counters)

    def _renderable_variant(self, variant):
        """Return the variant column the current sprite sheet can render."""
        loader = getattr(self.map_viewer, 'hex_tile_loader', None)
        max_variant = getattr(loader, 'VARIANTS_PER_ROW', 13) - 1
        return min(max(0, variant), max_variant)

    def _create_terrain_reference_preview(self, terrain_id, variant):
        """Create a Tk image for the observed terrain code/variant preview."""
        try:
            rendered_variant = self._renderable_variant(variant)
            if self.map_viewer.hex_tile_loader:
                base_img = self.map_viewer.hex_tile_loader.get_tile_with_variant(
                    terrain_id, rendered_variant
                )
            else:
                base_img = self.map_viewer.hex_tile_base_images.get(terrain_id)

            if base_img is None:
                return None

            preview_img = base_img.resize((60, 68), Image.Resampling.LANCZOS)
            photo_img = ImageTk.PhotoImage(preview_img)
            self._terrain_preview_images.append(photo_img)
            return photo_img
        except Exception as e:
            print(f"Error creating terrain reference preview: {e}")
            return None

    def _update_terrain_reference_scrollregion(self):
        """Update terrain reference scroll bounds after rebuilding entries."""
        self.terrain_reference_frame.update_idletasks()
        self.terrain_reference_canvas.config(
            scrollregion=self.terrain_reference_canvas.bbox('all')
        )

    def _draw_mini_hex(self, canvas, center_x, center_y, size, color):
        """Draw a small hexagon for terrain swatch"""
        points = []
        for i in range(6):
            angle = math.pi / 3 * i - math.pi / 6
            px = center_x + size * math.cos(angle)
            py = center_y + size * math.sin(angle) * 0.8  # Slightly flatter
            points.extend([px, py])

        canvas.create_polygon(points, fill=color, outline='#333333', width=2)

    def _create_statusbar(self):
        """Create status bar"""
        status_frame = ttk.Frame(self.root)
        status_frame.pack(fill=tk.X, side=tk.BOTTOM)

        self.status_label = ttk.Label(status_frame,
                                      text="Ready - Load a scenario to begin",
                                      relief=tk.SUNKEN,
                                      anchor=tk.W)
        self.status_label.pack(fill=tk.X, side=tk.LEFT, padx=5, pady=2)

        self.modified_label = ttk.Label(status_frame,
                                       text="",
                                       relief=tk.SUNKEN,
                                       anchor=tk.E,
                                       width=15)
        self.modified_label.pack(side=tk.RIGHT, padx=5, pady=2)

    def _on_text_modified(self, event):
        """Track briefing drafts, including edits reverted back to their original text."""
        if event.widget.edit_modified():
            event.widget.edit_modified(False)
            if not self.scenario or self._restoring_history:
                return
            self._sync_briefing_history()
            self._update_modified_state()

    def _briefing_texts(self):
        return tuple(widget.get('1.0', 'end-1c') for widget in (self.allied_text, self.axis_text))

    def _draft_forms(self):
        forms = [self.unit_props_editor.draft, self.settings_editor.draft]
        for panel in self.settings_editor.conditions:
            forms.extend(getattr(panel, 'draft_forms', ()))
        return forms

    def _draft_changed(self):
        if self._draft_refresh is None and not self._closing:
            self._draft_refresh = self.root.after_idle(self._refresh_draft_state)

    def _refresh_draft_state(self):
        self._draft_refresh = None
        self._update_modified_state()
        self._update_history_actions()

    def _clear_form_drafts(self):
        for form in self._draft_forms():
            form.clear()

    def _focus_draft(self, form, context):
        if form is self.unit_props_editor.draft:
            self.notebook.select(self.units_frame)
            self.unit_filter_var.set('All units')
            self.unit_search_var.set('')
            unit = next((u for u in self.units if (u['side'], u['side_index']) == context), None)
            if unit:
                group = self.unit_trees_by_side[unit['side']]
                self.unit_list_notebook.select(group['frame'])
                self.unit_props_editor.load_units(group['units'], unit['index'])
        else:
            self.notebook.select(self.settings_frame)
            panel = form.owner
            self.settings_editor.tabs.select(0 if panel is self.settings_editor else panel)
            if hasattr(panel, 'days_draft'):
                panel.side.set(('Allied', 'Axis')[context if form is panel.pool_draft else context[0]])
                panel.load(panel.roster)
                if form is panel.days_draft:
                    panel.load_days(context)
            elif hasattr(panel, 'range_draft') and form is panel.range_draft:
                panel.load_range(context)

    def _apply_form_drafts(self):
        """Validate all drafts before staging any of them, using freshly parsed offsets."""
        pending = [(form, context, values, changes) for form in self._draft_forms()
                   for context, (values, changes) in form.pending().items()]
        if not pending:
            return True
        before = self._staged_data(include_briefings=False)
        data = before
        try:
            for form, context, values, changes in pending:
                data = form.prepare(data, context, values, changes)
            data = synchronize_occupancy(data)
        except (ValueError, IndexError, KeyError, struct.error) as exc:
            self._focus_draft(form, context)
            messagebox.showerror('Cannot Apply Pending Edits', f'{form.label}: {exc}', parent=self.root)
            self._update_modified_state()
            return False
        current = self.unit_props_editor.current_unit
        side, index = (current['side'], current['index']) if current else ('Allied', 0)
        if data != before:
            self._remember_edit(before, side, index, 'Apply pending form edits',
                                '\n'.join(dict.fromkeys(form.label for form, *_ in pending)))
        self._clear_form_drafts()
        self._replace_roster(data, side, index)
        self._update_modified_state()
        return True

    def _modal_is_open(self):
        dialog = self.root.grab_current()
        if dialog is not None:
            dialog.winfo_toplevel().lift()
            dialog.bell()
            return True
        return False

    def _confirm_document_replacement(self, action):
        self._end_briefing_group()
        self._update_modified_state()
        if not self.modified:
            return True
        name = (self.import_name or 'Untitled.SCN') if self.is_new else self.scenario_file.name
        answer = ask_save_changes(self.root, action, name)
        if answer == 'save':
            return self.save_scenario(confirm=False, notify=False)
        return answer == 'discard'

    def close_editor(self):
        if self._closing or self._modal_is_open():
            return False
        if not self._confirm_document_replacement('closing the editor'):
            return False
        self._closing = True
        if self._draft_refresh is not None:
            self.root.after_cancel(self._draft_refresh)
            self._draft_refresh = None
        # Child widgets own some timer commands; let their destroy methods
        # release those commands after cancelling the timers in Tcl.
        for timer in self.root.tk.call('after', 'info'):
            self.root.tk.call('after', 'cancel', timer)
        self.root.destroy()
        return True

    def _update_modified_state(self):
        self.modified = False
        if self.scenario:
            try:
                data = self._snapshot().data
                self.modified = (self.is_new or data != self.saved_data
                                 or self.terrain_artwork != self.saved_artwork
                                 or self.counter_artwork != self.saved_counters
                                 or self.presentation_artwork != self.saved_presentation
                                 or self.document != self.saved_document
                                 or self._briefing_texts() != read_briefings(data))
            except ValueError:
                self.modified = True
            self.modified = self.modified or any(form.pending() for form in self._draft_forms())
        self.modified_label.config(text='Modified *' if self.modified else '', foreground='red')
        self._update_document_title()

    def _update_document_title(self):
        """Keep the filename and unsaved marker consistent in the toolbar and title bar."""
        title = 'D-Day Scenario Editor'
        if not self.scenario:
            self.file_label.config(text='!! NO SCENARIO FILE LOADED !!')
            self.root.title(title)
            return
        name = (self.import_name or 'Untitled.SCN') if self.is_new else self.scenario_file.name
        name += ' *' if self.modified else ''
        if self.is_new and self.import_name:
            name += ' (imported)'
        self.file_label.config(text=name)
        self.root.title(f'{name} — {title}')

    def new_scenario(self):
        if self._modal_is_open() or not self._confirm_document_replacement('creating a new scenario'):
            return
        self.new_dialog = NewScenarioDialog(self)

    def create_scenario(self, data, profile=None):
        import tempfile
        import uuid
        # A unique, unwritten path keeps artwork lookup independent of any
        # existing document named UNTITLED.SCN. Save opens Save As first.
        self.scenario_file = Path(tempfile.gettempdir()) / f'atomic-untitled-{uuid.uuid4().hex}.SCN'
        self.scenario = DdayScenario.from_bytes(data, self.scenario_file)
        self.is_new = True
        self._load_scenario_data()
        if profile is not None:
            self.document = self.document.with_profile(profile)
            self.settings_editor.profiles.load(None)
            self._reset_history(label='New scenario')
        self.runtime_slot = 'COBRA.SCN'
        self._update_modified_state()
        self.notebook.select(self.map_frame)
        self.status_label.config(text='New scenario. Add units and objectives, then Save As.')

    def apply_scenario_rules(self, data, description='Update scenario settings', presentation=None):
        before = self._staged_data(include_briefings=False)
        if before == data and (presentation is None or presentation == self.presentation_artwork):
            return
        unit = self.unit_props_editor.current_unit
        side, index = (unit['side'], unit['index']) if unit else ('Allied', 0)
        self._remember_edit(before, side, index, description)
        if presentation is not None:
            self.presentation_artwork = presentation
        self._replace_roster(data, side, index)
        self.artwork_panel.refresh()
        self.status_label.config(text='Scenario settings updated — use Save to write changes.')

    def apply_game_profile(self, profile):
        if self.document.profile == profile:
            return
        before = self._staged_data(include_briefings=False)
        unit = self.unit_props_editor.current_unit
        side, index = (unit['side'], unit['index']) if unit else ('Allied', 0)
        self._remember_edit(before, side, index, 'Change game profile')
        self.document = self.document.with_profile(profile)
        self._replace_roster(before, side, index)

    def open_scenario(self, filename=None):
        """Open a scenario file"""
        if self._modal_is_open():
            return
        if filename is None:
            filename = filedialog.askopenfilename(
                title="Open Scenario — D-Day, Stalingrad, Crusader or V for Victory",
                initialdir=str(GAME_ROOT / 'dday/SCENARIO' if (GAME_ROOT / 'dday/SCENARIO').is_dir()
                               else GAME_ROOT / 'SCENARIO'),
                filetypes=[("Scenario Files", "*.SCN"), ("All Files", "*.*")]
            )

        if not filename:
            return
        if not self._confirm_document_replacement('opening another scenario'):
            return

        try:
            if source_game(filename) != 'dday':
                self.import_scenario(filename)
                return
            scenario = DdayScenario(filename)

            if not scenario.is_valid:
                messagebox.showerror("Error", "Invalid scenario file format!")
                return

            # Validate companion artwork before replacing the working document.
            load_artwork(Path(filename))
            load_counters(Path(filename))
            load_presentation(Path(filename))
            runtime_slot_for(Path(filename))
            load_document(Path(filename))
            self.scenario = scenario
            self.is_new = False
            self.scenario_file = Path(filename)

            # Load all data
            self._load_scenario_data()

            self.modified = False
            self.modified_label.config(text="", foreground="black")
            self._update_document_title()
            self.status_label.config(text=f"Loaded: {self.scenario_file.name}")

        except Exception as e:
            messagebox.showerror("Error", f"Failed to load scenario:\n{e}")

    def import_scenario(self, filename):
        """Open an older scenario as an unsaved D-Day editing document."""
        data, artwork, counters, report = convert_scenario(filename)
        self.create_scenario(data)
        self.document = ScenarioDocument.from_dict(report.pop('document'))
        self.conversion = report
        self.import_name = Path(filename).name
        self.terrain_artwork, self.counter_artwork = artwork, counters
        self.runtime_slot = report.get('runtime_slot', 'BRADLEY.SCN')
        self.map_viewer.hex_tile_loader.artwork = dict(artwork)
        self.map_viewer.terrain_raster = None
        self.map_viewer.hex_tile_images.clear()
        self._replace_roster(data, 'Allied', 0)
        self._refresh_terrain_reference_tab()
        self._update_document_title()
        self._reset_history(label=f'Imported {self.import_name}')
        self.status_label.config(text=f'Imported {report["title"]}. Save As preserves source data and the game profile; File → Conversion Notes lists adaptations.')

    def show_conversion_notes(self):
        report = getattr(self, 'conversion', None)
        if not report:
            messagebox.showinfo('Conversion Notes', 'This document has no conversion notes.')
            return
        window = tk.Toplevel(self.root)
        window.title('Conversion Notes')
        window.geometry('780x520')
        text = scrolledtext.ScrolledText(window, wrap=tk.WORD, padx=12, pady=12)
        text.pack(fill=tk.BOTH, expand=True)
        lines = [report['title'], f'Source: {report["source"]}',
                 f'Map: {report["map_size"][0]} × {report["map_size"][1]}',
                 f'Units: {report["unit_counts"][0]} Allied, {report["unit_counts"][1]} Axis',
                 '', 'Adaptations at import:', '']
        lines.extend('• '+item+'\n' for item in report.get('adaptations', report.get('limitations', [])))
        text.insert('1.0', '\n'.join(lines))
        text.config(state=tk.DISABLED)
        ttk.Button(window, text='Close', command=window.destroy).pack(pady=8)

    def _load_scenario_data(self):
        """Load scenario data into all tabs"""
        if not self.scenario:
            return

        self._clear_form_drafts()
        artwork = load_artwork(self.scenario_file) if self.scenario_file else {}
        runtime_slot = runtime_slot_for(self.scenario_file) if self.scenario_file else None
        # Clear modification tracker for new scenario
        self.mod_tracker.clear()
        self.mod_tracker.set_scenario_size(len(self.scenario.data))
        self.saved_data = self.scenario.data
        self.conversion = conversion_report(self.scenario_file) if self.scenario_file else None
        self.document = self.saved_document = load_document(self.scenario_file)
        self.import_name = None
        self._pending_edit = None
        self._history_briefings = None
        self.history.reset(None)
        self.terrain_artwork = artwork
        self.counter_artwork = load_counters(self.scenario_file)
        self.saved_counters = dict(self.counter_artwork)
        self.presentation_artwork = load_presentation(self.scenario_file)
        self.saved_presentation = dict(self.presentation_artwork)
        self.artwork_panel.refresh()
        self.saved_artwork = dict(artwork)
        self.runtime_slot = runtime_slot
        self.map_viewer.hex_tile_loader.artwork = dict(artwork)

        # Parse the fixed-size records in both order-of-battle blocks.
        self.units = EnhancedUnitParser.parse_units_from_scenario(self.scenario)

        # Parse coordinates from PTR5
        ptr5_data = self.scenario.sections.get('PTR5', b'')
        self.coords = EnhancedUnitParser.parse_coordinates_from_ptr5(ptr5_data)

        # Load mission text
        self._load_mission_text()

        # Load map viewer with REAL terrain data
        self.map_viewer.load_data(self.units, self.scenario)
        self._refresh_terrain_reference_tab()

        # Load unit editor
        self._load_units_into_tree()

        # Load settings
        self.settings_editor.load_scenario_data(self.scenario)
        self._reset_history(label='New scenario' if self.is_new else 'Opened scenario')

    def _load_mission_text(self):
        """Load the game's fixed briefing slots, independently for each side."""
        if not self.scenario:
            return

        self._set_briefing_texts(read_briefings(self.scenario.data))

    def _set_briefing_texts(self, texts, cursors=('1.0', '1.0')):
        for widget, text, cursor in zip((self.allied_text, self.axis_text), texts, cursors):
            widget.delete('1.0', tk.END)
            widget.insert('1.0', text)
            widget.mark_set('insert', cursor)
            widget.edit_modified(False)
        self._history_briefings = tuple(texts)

    @staticmethod
    def _unit_tree_values(unit):
        position = 'Off map' if unit['x'] < 0 or unit['y'] < 0 else f"({unit['x']},{unit['y']})"
        return (unit['index'], unit['name'], unit_status(unit), unit_arrival_label(unit), position,
                *(format_unit_value(unit[key]) for key in
                  ('attack_base', 'defense_base', 'armor_base', 'antitank_base',
                   'quality', 'disruption', 'fatigue')),
                unit['type_name'])

    def _load_units_into_tree(self):
        """Show verified roster data, including zero strengths and entry hexes."""
        self.unit_props_editor.load_units([])
        for tab in self.unit_list_notebook.tabs():
            self.unit_list_notebook.nametowidget(tab).destroy()
        self.unit_trees_by_side.clear()
        units_by_side = {'Allied': [], 'Axis': []}
        for unit in self.units:
            units_by_side.setdefault(unit['side'], []).append(unit)
        columns = ('Index', 'Name', 'Status', 'Arrival', 'Position', 'Atk', 'Def', 'Armor', 'AT',
                   'Qual', 'Dis', 'Fat', 'Type')
        titles = ('#', 'Unit name', 'Status', 'Arrival', 'Hex / entry', 'Atk', 'Def', 'Armor', 'AT',
                  'Qual', 'Dis', 'Fat', 'Type')
        widths = (35, 135, 110, 75, 80, 40, 40, 55, 40, 40, 40, 40, 160)
        for side, units in sorted(units_by_side.items()):
            frame = ttk.Frame(self.unit_list_notebook)
            self.unit_list_notebook.add(frame, text=f'{side} ({len(units)})')
            frame.rowconfigure(0, weight=1)
            frame.columnconfigure(0, weight=1)
            tree = ttk.Treeview(frame, columns=columns, show='headings', height=20, selectmode='browse')
            for column, title, width in zip(columns, titles, widths):
                tree.heading(column, text=title)
                tree.column(column, width=width, minwidth=width, stretch=False)
            vs = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=tree.yview)
            hs = ttk.Scrollbar(frame, orient=tk.HORIZONTAL, command=tree.xview)
            tree.configure(yscrollcommand=vs.set, xscrollcommand=hs.set)
            tree.grid(row=0, column=0, sticky=tk.NSEW)
            vs.grid(row=0, column=1, sticky=tk.NS)
            hs.grid(row=1, column=0, sticky=tk.EW)
            tree.bind('<<TreeviewSelect>>', lambda event, s=side: self.on_unit_tree_select(event, s))
            self.unit_trees_by_side[side] = {'tree': tree, 'units': units, 'frame': frame, 'visible': []}
        self._refresh_unit_roster()

    def _refresh_unit_roster(self, preserve_form=False):
        """Filter both sides and keep the selected unit, list, and form in sync."""
        if not self.unit_trees_by_side:
            self.unit_props_editor.load_units([])
            self.unit_roster_summary.config(text='No units loaded')
            return
        status = self.unit_filter_var.get()
        if status == 'Reinforcements':
            status = 'Reinforcement'
        query = self.unit_search_var.get().strip().casefold()
        shown = 0
        for side, group in self.unit_trees_by_side.items():
            visible = [u for u in group['units']
                       if ((status == 'All units' and not u.get('deleted')) or unit_status(u) == status)
                       and (not query or query in f"{u['name']} {u['type_name']}".casefold())]
            if status == 'Reinforcement':
                visible.sort(key=lambda u: (u['arrival_time'], u['index']))
            group['visible'] = visible
            tree = group['tree']
            children = tree.get_children()
            if children:
                tree.delete(*children)
            for unit in visible:
                tree.insert('', tk.END, iid=str(unit['index']), values=self._unit_tree_values(unit))
            self.unit_list_notebook.tab(group['frame'], text=f'{side} ({len(visible)}/{len(group["units"])})')
            shown += len(visible)
        reinforcements = sum(unit_status(u) == 'Reinforcement' for u in self.units)
        deleted = sum(u.get('deleted', False) for u in self.units)
        self.unit_roster_summary.config(text=(
            f'{shown} shown · {len(self.units) - deleted} units · {reinforcements} reinforcements'
            + (f' · {deleted} deleted' if deleted else '')))
        active = self.unit_list_notebook.select()
        group = next((g for g in self.unit_trees_by_side.values() if str(g['frame']) == active), None)
        if group is None:
            return
        visible = group['visible']
        current = self.unit_props_editor.current_unit
        selected_index = current['index'] if current else None
        if preserve_form and current is not None and current in visible:
            self.unit_props_editor.units = visible
            self.unit_props_editor.unit_combo['values'] = [
                f"{u['side']} · {u['side_index']}: {u['name']}" for u in visible]
            self.unit_props_editor.unit_combo.current(visible.index(current))
            self._sync_unit_selection(current)
        else:
            self.unit_props_editor.load_units(visible, selected_index)
        self._update_unit_actions()

    def _sync_unit_selection(self, unit):
        group = self.unit_trees_by_side.get(unit['side'])
        if not group or not group['tree'].exists(str(unit['index'])):
            return
        if self.unit_list_notebook.select() != str(group['frame']):
            self.unit_list_notebook.select(group['frame'])
        tree = group['tree']
        item = str(unit['index'])
        if tree.selection() != (item,):
            tree.selection_set(item)
        tree.focus(item)
        tree.see(item)
        self._update_unit_actions()

    def on_unit_updated(self, unit, updated, patches):
        """Track OB and shared HQ patches so Apply also survives saving/reload."""
        if any(key in ('x', 'y', 'arrival_time') for _, _, key in patches):
            from lib.terrain_reader import _read_block
            candidate = bytearray(self._staged_data(include_briefings=False))
            for offset, value, _ in patches:
                candidate[offset:offset+len(value)] = value
            synchronized = synchronize_occupancy(bytes(candidate))
            offset = 0
            for _ in range(4):
                _, offset = _read_block(candidate, offset)
            block, _ = _read_block(synchronized, offset)
            patches = [*patches, (offset+4, block, 'map_occupancy')]
            # HQ supply tracing also keeps an active flag outside the OB.
            before_roster, after_roster = UnitRoster(candidate), UnitRoster(synchronized)
            block_offset = 0
            for name, multiple in before_roster._layout():
                if multiple:
                    block_offset += 4
                if name in ('hqs0', 'hqs1'):
                    for i in range(0, len(before_roster.blocks[name]), 58):
                        if before_roster.blocks[name][i+0x38] != after_roster.blocks[name][i+0x38]:
                            patches.append((block_offset+i+0x38,
                                bytes((after_roster.blocks[name][i+0x38],)), 'hq_active'))
                block_offset += len(before_roster.blocks[name])
        fields = list(dict.fromkeys(key for _, _, key in patches if key not in ('map_occupancy', 'hq_active')))
        details = '\n'.join(f"{key.replace('_', ' ').title()}: {unit.get(key, '')} → {updated.get(key, '')}"
                            for key in fields)
        self._remember_edit(self._staged_data(include_briefings=False), unit['side'], unit['index'],
                            f"Edit unit {unit['name']}", details)
        for offset, new_bytes, key in patches:
            original = self.scenario.data[offset:offset + len(new_bytes)]
            if new_bytes == original:
                self.mod_tracker.remove_modification(offset)
            else:
                mod_type = (ModificationType.UNIT_POSITION if key in ('x', 'y')
                            else ModificationType.UNIT_NAME if key == 'name'
                            else ModificationType.REINFORCEMENT_TURN if key == 'arrival_time'
                            else ModificationType.UNIT_STATS)
                self.mod_tracker.add_modification(offset, original, new_bytes, mod_type,
                                                  f"{unit['name']}: {key.replace('_', ' ')}")
            if key in HQ_AUTOMATION_FIELDS:
                for member in self.units:
                    if member.get(key + '_offset') == offset:
                        member[key] = updated[key]
        unit.update(updated)
        if unit['unit_class'] == 7:
            for member in self.units:
                if member['side'] == unit['side'] and member['hq_index'] == unit['hq_index']:
                    member['hq_name'] = unit['name']
        side_tree = self.unit_trees_by_side.get(unit['side'])
        if side_tree and side_tree['tree'].exists(str(unit['index'])):
            side_tree['tree'].item(str(unit['index']), values=self._unit_tree_values(unit))
        self.map_viewer.redraw()
        self.map_viewer.update_unit_summary()
        self.map_viewer.edit_controls.refresh()
        self._update_modified_state()
        self._finish_edit()
        self.status_label.config(text='Unit updated — use File → Save to write changes.')
        self.root.after_idle(lambda: self._refresh_unit_roster(preserve_form=True))

    def edit_map_terrain(self, cell, terrain, variant):
        if not self.scenario:
            return
        try:
            before = self._staged_data(include_briefings=False)
            panel = self.map_viewer.edit_controls
            data = paint_blended_terrain(before, (cell,), terrain, variant,
                blend=panel.auto_blend.get(),
                exclude_slots=() if panel.blend_imported.get() else self.terrain_artwork)
        except (ValueError, struct.error) as exc:
            messagebox.showerror('Cannot Edit Terrain', str(exc))
            return
        if data == before:
            return
        current = self.unit_props_editor.current_unit
        side, index = (current['side'], current['index']) if current else ('Allied', 0)
        self._remember_edit(before, side, index, f'Paint {terrain_name(terrain)} at {cell}',
                            f'Terrain: {terrain_name(terrain)} · Variant: {variant} · Hex: {cell}')
        self._replace_roster(data, side, index)
        self.status_label.config(text=f'Changed terrain at {cell} to {terrain_name(terrain)}. Save writes the map.')

    def edit_map_feature(self, cell, feature, direction, remove=False):
        if not self.scenario:
            return
        try:
            before = self._staged_data(include_briefings=False)
            data = edit_map_feature(before, cell, feature, direction, remove)
        except (ValueError, struct.error) as exc:
            messagebox.showerror('Cannot Edit Map Feature', str(exc))
            return
        if data == before:
            self.status_label.config(text=f'No change: {feature.lower()} is already absent.' if remove else
                                     f'No change: {feature.lower()} is already present.')
            return
        current = self.unit_props_editor.current_unit
        side, index = (current['side'], current['index']) if current else ('Allied', 0)
        self._remember_edit(before, side, index, f'{"Remove" if remove else "Add"} {feature.lower()} at {cell}',
                            f'{feature} · Hex: {cell} · Direction: {direction}')
        self._replace_roster(data, side, index)
        self.status_label.config(text=f'{"Removed" if remove else "Added"} {feature.lower()} at {cell}. Save writes the map.')

    def edit_map_tool(self, operation, **values):
        """Stage each map tool as one undoable edit, including multi-hex operations."""
        if not self.scenario:
            return False
        try:
            before = self._staged_data(include_briefings=False)
            if operation == 'copy':
                return copy_region(before, **values)
            panel = self.map_viewer.edit_controls
            if operation in ('blend', 'terrain_region', 'fill_terrain'):
                values['exclude_slots'] = () if panel.blend_imported.get() else self.terrain_artwork
                if operation != 'blend':
                    values['blend'] = panel.auto_blend.get()
            operations = {
                'place': edit_place_name, 'ownership': paint_ownership,
                'edge': edit_cosmetic_edge, 'terrain_region': paint_blended_terrain,
                'blend': blend_terrain_edges,
                'fill_terrain': lambda data, cell, **kw: flood_terrain(data, cell, **kw),
                'fill_owner': lambda data, cell, **kw: flood_ownership(data, cell, **kw),
                'paste': lambda data, cell, **kw: paste_region(data, destination=cell, **kw),
                'resize': resize_map,
                'shift': shift_map,
                'formation': move_formation,
            }
            data = operations[operation](before, **values)
        except (ValueError, struct.error, OverflowError) as exc:
            messagebox.showerror('Cannot Edit Map', str(exc))
            return False
        if data == before:
            self.status_label.config(text='No map changes needed.')
            return True
        current = self.unit_props_editor.current_unit
        side, index = (current['side'], current['index']) if current else ('Allied', 0)
        descriptions = {'place': 'Updated place names', 'ownership': 'Painted ownership',
                        'blend': 'Blended terrain edges',
                        'edge': 'Updated cosmetic edge', 'terrain_region': 'Painted terrain region',
                        'fill_terrain': 'Filled terrain', 'fill_owner': 'Filled ownership',
                        'paste': 'Pasted map region', 'resize': 'Resized map',
                        'shift': 'Shifted map and scenario locations', 'formation': 'Moved HQ formation'}
        self._remember_edit(before, side, index, descriptions[operation])
        self._replace_roster(data, side, index)
        self.status_label.config(text=descriptions[operation]+'. Use Save to write changes.')
        return True

    def place_map_unit(self, unit, cell, deployment):
        if not self.scenario:
            return
        try:
            updated, patches = prepare_map_unit_changes(unit, cell, deployment)
            if not patches:
                return
            before = self._staged_data(include_briefings=False)
            data = bytearray(before)
            for offset, value, _ in patches:
                data[offset:offset + len(value)] = value
            data = synchronize_occupancy(bytes(data))
        except (ValueError, struct.error) as exc:
            messagebox.showerror('Cannot Place Unit', str(exc))
            return
        self._remember_edit(before, unit['side'], unit['index'],
                            f"Remove {unit['name']} from map" if cell is None else f"Place {unit['name']} at {cell}")
        self._replace_roster(bytes(data), unit['side'], unit['index'])
        action = (f"Removed {unit['name']} from the map; it remains inactive in the OOB." if cell is None else
                  f"Placed {unit['name']} at {cell}. " +
                  ('Available at start.' if deployment == 'Deploy at start' else 'Arrival turn preserved.'))
        self.status_label.config(text=action + ' Save writes the changes.')

    def on_unit_tree_select(self, event, side):
        """Handle unit tree selection - show selected unit in properties editor"""
        if side not in self.unit_trees_by_side:
            return

        tree = self.unit_trees_by_side[side]['tree']
        units = self.unit_trees_by_side[side]['visible']
        if self.unit_list_notebook.select() != str(self.unit_trees_by_side[side]['frame']):
            return

        selection = tree.selection()
        if not selection:
            return

        # Get the selected item
        item = selection[0]
        values = tree.item(item, 'values')

        if not values:
            return

        # Extract unit index from the first column
        try:
            unit_index = int(values[0])  # Index is in the first column

            # Find this unit in the units list by index
            selected_unit = None
            for unit in units:
                if unit.get('index') == unit_index:
                    selected_unit = unit
                    break

            if selected_unit:
                if self.unit_props_editor.current_unit is not selected_unit:
                    self.unit_props_editor.unit_combo.current(units.index(selected_unit))
                    self.unit_props_editor.on_unit_selected(None)
        except (ValueError, IndexError):
            pass

    def add_unit(self):
        if self.scenario and self._apply_form_drafts():
            self.add_unit_dialog = AddUnitDialog(self)

    def _update_unit_actions(self):
        current = self.unit_props_editor.current_unit
        self.add_unit_button.config(state='normal' if self.scenario else 'disabled')
        self.delete_unit_button.config(state='normal' if current else 'disabled',
                                       text='Restore Unit' if current and current.get('deleted') else 'Delete Unit')
        self.organization_button.config(state='normal' if self.scenario else 'disabled')
        self.definition_button.config(state='normal' if current and not current.get('deleted') else 'disabled')
        self._update_history_actions()
        if current and current.get('deleted'):
            self.unit_props_editor.apply_button.config(state='disabled')
            self.unit_props_editor.feedback.config(text='Use Restore Unit to return this unit to the scenario.')

    def _staged_data(self, include_briefings=True):
        data = bytearray(self.scenario.data)
        for offset, value in self.mod_tracker.get_patches():
            data[offset:offset + len(value)] = value
        if include_briefings:
            for offset, value, _ in prepare_briefing_changes(data, self._briefing_texts()):
                data[offset:offset + len(value)] = value
            from lib.scenario_data import normalize_replacements
            data = normalize_replacements(data)
        return bytes(data)

    @property
    def roster_history(self):
        """Compatibility for older callers; the history now covers the document."""
        return self.history.entries[:self.history.position]

    def _snapshot(self, data=None, briefings=None, selection=None):
        data = bytearray(self._staged_data(include_briefings=False) if data is None else data)
        briefings = self._briefing_texts() if briefings is None else briefings
        try:
            patches = prepare_briefing_changes(data, briefings)
        except ValueError:
            patches = []  # Invalid drafts still belong in undo/redo; Save validates them.
        for offset, value, _ in patches:
            data[offset:offset+len(value)] = value
        current = self.unit_props_editor.current_unit
        selection = selection or ((current['side'], current['index']) if current else ('Allied', 0))
        return DocumentState.capture(bytes(data), briefings, self.terrain_artwork, self.counter_artwork,
                                     selection, tuple(w.index('insert') for w in (self.allied_text, self.axis_text)),
                                     self.presentation_artwork, self.document)

    def _reset_history(self, label='Opened scenario'):
        self._pending_edit = None
        self._history_briefings = self._briefing_texts()
        self.history.reset(self._snapshot(), saved=not self.is_new, label=label)
        self._update_history_actions()

    def _sync_briefing_history(self):
        if self._restoring_history or self.history.initial is None or self._history_briefings is None:
            return
        texts = self._briefing_texts()
        changed = tuple(i for i in range(2) if texts[i] != self._history_briefings[i])
        if not changed:
            return
        before = self._snapshot(briefings=self._history_briefings)
        after = self._snapshot()
        label = 'Edit '+('Allied briefing' if changed == (0,) else 'Axis briefing' if changed == (1,) else 'briefings')
        self.history.record(before, after, label, merge_key=('briefing', changed))
        self._history_briefings = texts
        self._update_history_actions()

    def _end_briefing_group(self):
        self._sync_briefing_history()
        self.history.break_group()

    def _remember_edit(self, data, side, index, label='Edit scenario', details=''):
        self._sync_briefing_history()
        self.history.break_group()
        self._pending_edit = (self._snapshot(data, selection=(side, index)), label, details)

    def _finish_edit(self):
        if self._pending_edit is not None:
            before, label, details = self._pending_edit
            self._pending_edit = None
            self.history.record(before, self._snapshot(), label, details)
            self._update_history_actions()

    def _bind_history_shortcuts(self, parent):
        # Run before Tk's Text class bindings, which otherwise consume Ctrl+Z.
        tag = f'DocumentHistory{id(self)}'
        for sequence, command in (('<Control-z>', self.undo_edit), ('<Control-y>', self.redo_edit),
                                   ('<Control-Shift-Z>', self.redo_edit)):
            self.root.bind_class(tag, sequence, lambda event, fn=command: fn() or 'break')
        def visit(widget):
            widget.bindtags((tag, *[t for t in widget.bindtags() if t != tag]))
            for child in widget.winfo_children():
                if not isinstance(child, tk.Toplevel):
                    visit(child)
        visit(parent)

    def _update_history_actions(self):
        drafts = any(form.pending() for form in self._draft_forms())
        undo = 'normal' if self.history.can_undo or drafts else 'disabled'
        redo = 'normal' if self.history.can_redo and not drafts else 'disabled'
        for name in ('undo_button', 'undo_roster_button'):
            if hasattr(self, name):
                getattr(self, name).config(state=undo)
        for name in ('redo_button', 'redo_roster_button', 'map_redo_button'):
            if hasattr(self, name):
                getattr(self, name).config(state=redo)
        if hasattr(self, 'map_viewer'):
            self.map_viewer.edit_controls.undo_button.config(state=undo)
        loaded = 'normal' if self.scenario else 'disabled'
        self.history_button.config(state=loaded)
        label = 'Undo '+self.history.entries[self.history.position-1].label if self.history.can_undo else 'Undo'
        if drafts:
            label = 'Undo pending form edits'
        self.edit_menu.entryconfig(0, label=label, state=undo)
        label = 'Redo '+self.history.entries[self.history.position].label if self.history.can_redo else 'Redo'
        self.edit_menu.entryconfig(1, label=label, state=redo)
        self.edit_menu.entryconfig(2, state=loaded)
        if self.history_window is not None and self.history_window.winfo_exists():
            self.history_window.refresh()

    def show_edit_history(self):
        if not self.scenario:
            return
        self._end_briefing_group()
        if self.history_window is not None and self.history_window.winfo_exists():
            self.history_window.lift()
        else:
            self.history_window = HistoryWindow(self)

    def restore_history(self, position):
        if not self.scenario or self.root.grab_current() is not None:
            return 'break'
        if not self._apply_form_drafts():
            return 'break'
        self._end_briefing_group()
        if position == self.history.position:
            return 'break'
        state = self.history.move(position)
        self._restoring_history = True
        try:
            self._set_briefing_texts(state.briefings, state.cursors)
            self.terrain_artwork, self.counter_artwork = dict(state.artwork), dict(state.counters)
            self.presentation_artwork = dict(state.presentation)
            self.document = state.document or ScenarioDocument()
            self.artwork_panel.refresh()
            self.map_viewer.hex_tile_loader.artwork = dict(self.terrain_artwork)
            self.map_viewer.terrain_raster = None
            self.map_viewer.hex_tile_images.clear()
            self.unit_filter_var.set('All units')
            self.unit_search_var.set('')
            self._replace_roster(state.data, *state.selection)
            self._refresh_artwork()
        finally:
            self._restoring_history = False
        self._update_modified_state()
        self._update_history_actions()
        self.status_label.config(text=f'History: step {position} of {len(self.history.entries)}. Save writes this state.')
        return 'break'

    def undo_edit(self):
        if self._modal_is_open() or not self._apply_form_drafts():
            return 'break'
        self._sync_briefing_history()
        if self.history.can_undo:
            return self.restore_history(self.history.position-1)
        return 'break'

    def redo_edit(self):
        if self._modal_is_open() or any(form.pending() for form in self._draft_forms()):
            return 'break'
        self._sync_briefing_history()
        if self.history.can_redo:
            return self.restore_history(self.history.position+1)
        return 'break'

    def edit_unit_organization(self):
        if not self.scenario:
            return
        if not self._apply_form_drafts():
            return
        current = self.unit_props_editor.current_unit
        if current and not current.get('deleted') and not self.unit_props_editor.apply_changes():
            return
        OrganizationDialog(self)

    def edit_unit_definition(self):
        if not self._apply_form_drafts():
            return
        if self.unit_props_editor.current_unit and self.unit_props_editor.apply_changes():
            UnitDefinitionDialog(self)

    def edit_unit_operations(self, page='Orders'):
        if not self._apply_form_drafts():
            return
        current = self.unit_props_editor.current_unit
        if current and not current.get('deleted') and current['unit_class'] not in (5, 6):
            from lib.unit_operations_dialog import UnitOperationsDialog
            self.unit_operations_dialog = UnitOperationsDialog(self, page)

    def apply_unit_structure(self, data, side, index, description, counters=None):
        before = self._staged_data(include_briefings=False)
        if data == before and (counters is None or counters == self.counter_artwork):
            return
        current = self.unit_props_editor.current_unit
        selected = current['index'] if current else index
        selected_side = current['side'] if current else ('Allied', 'Axis')[side]
        self._remember_edit(before, selected_side, selected, description)
        if counters is not None:
            self.counter_artwork = counters
        self.unit_filter_var.set('All units')
        self.unit_search_var.set('')
        roster = UnitRoster(data)
        selected = index + (roster.count(0x244, 0) if side else 0)
        self._replace_roster(data, ('Allied', 'Axis')[side], selected)
        self.status_label.config(text=f'{description} — use File → Save to write changes.')

    def change_unit_definition(self, unit, values, destination):
        """Commit definition, roster links and any transferred chit atomically."""
        try:
            side = int(unit['side'] == 'Axis')
            index = unit['side_index']
            data, index = edit_definition(self._staged_data(include_briefings=False), side, index,
                                           values, return_index=True)
            counters = self.counter_artwork
            if destination != side:
                counter = None
                if unit['unit_class'] not in (5, 6):
                    from lib.game_art import _counter_sheet, load_bitmap
                    sheet = (_counter_sheet(unit['counter_bitmap']) if unit.get('counter_bitmap')
                             else load_bitmap(unit['counter_resource']))
                    number = unit['counter_index']
                    x, y = number % 22 * 22, number // 22 * 23
                    pixels = sheet.crop((x, y, x+22, y+23)).tobytes()
                    counter, counters = allocate_counter(UnitRoster(data), counters, destination, pixels)
                data, index = transfer_unit(data, side, index, destination, counter=counter)
                side = destination
            self.apply_unit_structure(data, side, index, 'Updated unit definition', counters)
        except (ValueError, IndexError, struct.error, OSError) as exc:
            messagebox.showerror('Cannot Change Unit Definition', str(exc))
            return False
        return True

    def assign_presentation_artwork(self, key, artwork):
        if not self.scenario or self.presentation_artwork.get(key) == artwork:
            return
        if not self._apply_form_drafts():
            return
        if artwork is not None:
            validate_artwork({key: artwork})
        slot = slot_for(key)
        current = self.unit_props_editor.current_unit
        side, index = (current['side'], current['index']) if current else ('Allied', 0)
        self._remember_edit(self._staged_data(include_briefings=False), side, index,
                            f'{"Restore" if artwork is None else "Change"} {slot.label.lower()}')
        if artwork is None:
            self.presentation_artwork.pop(key, None)
        else:
            self.presentation_artwork[key] = artwork
        if slot.kind in ('air', 'ship'):
            from lib.support_units import artwork_key
            for unit in self.units:
                if unit['unit_class'] in (5, 6):
                    try:
                        unit['support_artwork'] = self.presentation_artwork.get(artwork_key(
                            unit['unit_class'], unit['type'], int(unit['side'] == 'Axis')))
                    except ValueError:
                        pass
            if current:
                self.unit_props_editor.display_unit()
            self.map_viewer.edit_controls._preview_unit()
        self.artwork_panel.refresh()
        self._update_modified_state()
        self._finish_edit()
        self.status_label.config(text=f'Updated {slot.label.lower()}. Save keeps the artwork; Export for DOS includes it in the game graphics.')

    def _refresh_artwork(self):
        viewer = self.map_viewer
        viewer.hex_tile_loader.artwork = dict(self.terrain_artwork)
        viewer.terrain_raster = None
        viewer.hex_tile_images.clear()
        viewer.hex_tile_base_images = {code: viewer.hex_tile_loader.get_tile_with_variant(code, 0)
                                      for code in range(15)}
        viewer.edit_controls._preview_terrain()
        viewer.redraw()
        self._refresh_terrain_reference_tab()

    def assign_terrain_artwork(self, code, variant, stamp):
        if not self.scenario:
            return
        validate_slot(code, variant)
        key = (code, variant)
        if self.terrain_artwork.get(key) == stamp:
            return
        current = self.unit_props_editor.current_unit
        side, index = (current['side'], current['index']) if current else ('Allied', 0)
        self._remember_edit(self._staged_data(include_briefings=False), side, index,
                            f'{"Restore" if stamp is None else "Change"} {terrain_name(code)} artwork, variant {variant}')
        if stamp is None:
            self.terrain_artwork.pop(key, None)
        else:
            self.terrain_artwork[key] = stamp
        self._refresh_artwork()
        self._update_modified_state()
        self._finish_edit()
        self._update_unit_actions()
        self.status_label.config(text=f'Updated {terrain_name(code)}, variant {variant}. '
            'Export for DOS includes the scenario and matching game graphics.')

    def restore_terrain_artwork(self):
        panel = self.map_viewer.edit_controls
        self.assign_terrain_artwork(panel.terrain_choices[panel.terrain_combo.current()],
                                    int(panel.variant_combo.get()), None)

    def _replace_roster(self, data, side, index):
        """Reparse a map/roster edit; shifted file offsets must never be reused."""
        self.scenario = DdayScenario.from_bytes(data, self.scenario_file)
        self.mod_tracker.clear()
        self.mod_tracker.set_scenario_size(len(data))
        self.units = read_units(self.scenario, self.counter_artwork, self.presentation_artwork)
        self.map_viewer.units = self.units
        self.map_viewer.scenario = self.scenario
        size_changed = ((self.map_viewer.map_width, self.map_viewer.map_height) !=
                        (self.scenario.map_width, self.scenario.map_height))
        self.map_viewer.map_width, self.map_viewer.map_height = self.scenario.map_width, self.scenario.map_height
        if size_changed:
            self.map_viewer.map_title_label.config(
                text=f'Map ({self.scenario.map_width}×{self.scenario.map_height} hex grid)')
            self.map_viewer._scroll_geometry = None
            self.map_viewer._center_pending = self.map_viewer._center_on_resize = True
            self.map_viewer.edit_controls.tools.first = self.map_viewer.edit_controls.tools.last = None
            self.map_viewer.edit_controls.tools.hover = None
            self.map_viewer.edit_controls.tools.current_dimensions()
            self.map_viewer.edit_controls.tools.current_shift_dimensions()
        layers = read_map_layers(self.scenario)
        previous = self.map_viewer.map_layers
        self.map_viewer.map_layers = layers
        if (layers.terrain != previous.terrain or layers.records != previous.records
                or layers.edges != previous.edges or layers.hilltops != previous.hilltops or size_changed):
            self.map_viewer.terrain = layers.terrain
            self.map_viewer.terrain_raster = None
            self.map_viewer.hex_tile_images.clear()
            self._refresh_terrain_reference_tab()
        if self.map_viewer.selected_hex not in layers.terrain:
            self.map_viewer.selected_hex = None
        self.map_viewer.edit_controls.refresh()
        self.map_viewer.redraw()
        self.map_viewer.update_unit_summary()
        self._load_units_into_tree()
        group = self.unit_trees_by_side[side]
        self.unit_list_notebook.select(group['frame'])
        self._refresh_unit_roster()
        self.unit_props_editor.load_units(group['visible'], index)
        self._update_modified_state()
        self._update_unit_actions()

        self.settings_editor.load_scenario_data(self.scenario)
        self.artwork_panel.refresh()
        self._finish_edit()

    def create_unit(self, template, name):
        """Add a complete unit and stage the updated blocks until Save."""
        if not self._apply_form_drafts():
            return False
        try:
            # Briefings remain independent drafts when adding/deleting/undoing units.
            before = self._staged_data(include_briefings=False)
            roster = UnitRoster(before)
            side = 0 if template['side'] == 'Allied' else 1
            source_path = template.get('template_file')
            source = UnitRoster(Path(source_path).read_bytes()) if source_path else None
            counters = self.counter_artwork
            if 'library_id' in template:
                item = unit_library()[template['library_id']]
                source = library_template(item, side)
                if item['chit']:
                    counter, counters = allocate_counter(roster, counters, side, item['chit'])
                    struct.pack_into('<h', source.records[side][0], 0x56, counter)
            elif source_path and template['unit_class'] not in (5, 6):
                from lib.game_art import load_bitmap
                src = source.records[side][template['side_index']]
                number = struct.unpack_from('<h', src, 0x56)[0]
                sheet = load_bitmap(struct.unpack_from('<h', source.header, 0x238)[0]+side)
                x, y = number%22*22, number//22*23
                counter, counters = allocate_counter(roster, counters, side, sheet.crop((x,y,x+22,y+23)).tobytes())
                struct.pack_into('<h', src, 0x56, counter)
            added = roster.add(side, template['side_index'], name, source=source)
            refresh_command_spans(roster, side)
            data = synchronize_occupancy(roster.to_bytes())
        except (ValueError, IndexError, struct.error) as exc:
            messagebox.showerror('Cannot Add Unit', str(exc))
            return False
        self._remember_edit(before, template['side'], template['index'], f'Add unit {name}')
        self.counter_artwork = counters
        self.unit_filter_var.set('All units')
        self.unit_search_var.set('')
        index = added + (roster.count(0x244, 0) if side else 0)
        self._replace_roster(data, template['side'], index)
        self.unit_details_canvas.yview_moveto(0)
        self.status_label.config(text=f'Added {name}. Edit its properties, then Save the scenario.')
        return True

    def delete_unit(self):
        if not self._apply_form_drafts():
            return
        unit = self.unit_props_editor.current_unit
        if unit is None:
            return
        restore = unit.get('deleted')
        if not restore and not messagebox.askyesno('Delete Unit',
                f"Delete {unit['name']} from the scenario?\n\n"
                'You can restore it using Show: Deleted.'):
            return
        try:
            before = self._staged_data(include_briefings=False)
            roster = UnitRoster(before)
            side = 0 if unit['side'] == 'Allied' else 1
            if restore:
                roster.restore(side, unit['side_index'])
            else:
                roster.remove(side, unit['side_index'])
            refresh_command_spans(roster, side)
            data = synchronize_occupancy(roster.to_bytes())
        except (ValueError, IndexError, struct.error) as exc:
            messagebox.showerror('Cannot Change Unit Roster', str(exc))
            return
        self._remember_edit(before, unit['side'], unit['index'], f"{'Restore' if restore else 'Delete'} unit {unit['name']}")
        if restore:
            self.unit_filter_var.set('All units')
            self.unit_search_var.set('')
        self._replace_roster(data, unit['side'], unit['index'])
        self.status_label.config(text=f"{'Restored' if restore else 'Deleted'} {unit['name']} — use Save to write changes.")

    def undo_roster_change(self):
        return self.undo_edit()

    def save_scenario(self, output_file=None, *, confirm=True, notify=True):
        """Save both field patches and changes to variable-sized roster blocks."""
        if self._modal_is_open():
            return False
        if not self.scenario or not self.scenario_file:
            messagebox.showwarning("Warning", "No scenario loaded!")
            return False

        self._end_briefing_group()
        if self.is_new and output_file is None:
            return self.save_scenario_as(confirm=confirm, notify=notify)

        # Check if there are any modifications to save
        target = Path(output_file) if output_file else self.scenario_file
        if target.exists():
            try:
                foreign = source_game(target) != 'dday'
            except ValueError:
                foreign = False
            if foreign:
                messagebox.showerror('Save Scenario', 'Choose a separate D-Day document filename. The original source scenario must remain in its own game format.')
                return False
        if not self._apply_form_drafts():
            return False
        before_save = self._snapshot()
        artwork_changed = (self.document != self.saved_document or self.terrain_artwork != self.saved_artwork
                           or self.counter_artwork != self.saved_counters
                           or self.presentation_artwork != self.saved_presentation)
        try:
            data = self._staged_data()
        except ValueError as exc:
            messagebox.showerror('Invalid briefing', str(exc))
            return False
        automatic_assets = bool(self.document != ScenarioDocument() or self.terrain_artwork or self.counter_artwork or self.presentation_artwork or artwork_path(target).exists()
                                or counter_path(self.scenario_file).exists()
                                or presentation_path(self.scenario_file).exists() or presentation_path(target).exists()
                                or target.name.upper() not in GAME_SCENARIOS)
        if data == self.saved_data and target == self.scenario_file and not self.modified and not automatic_assets:
            self.history.mark_saved()
            self._update_history_actions()
            if notify:
                messagebox.showinfo("Save", "No changes to save.")
            return True

        # Show summary of pending changes
        summary = self.mod_tracker.get_summary()
        if self._briefing_texts() != read_briefings(self.scenario.data):
            summary = 'Mission briefing changes.\n' + summary
        if self.scenario.data != self.saved_data:
            summary = 'Scenario, map, or OOB changes.\n' + summary
        if artwork_changed:
            summary = 'Artwork changes.\n' + summary
        if confirm and (data != self.saved_data or target != self.scenario_file or artwork_changed):
            accepted = messagebox.askyesno(
                "Confirm Save",
                f"Save changes to {target.name}?\n\n{summary}"
            )
            if not accepted:
                return False

        try:
            if data != self.saved_data or target != self.scenario_file or artwork_changed or automatic_assets:
                if automatic_assets:
                    slot = self.runtime_slot or runtime_slot_for(self.scenario_file)
                    save_scenario_assets(data, target, self.terrain_artwork, slot,
                                         counters=self.counter_artwork,
                                         presentation=self.presentation_artwork,
                                         title=(self.conversion['title'] if self.conversion else
                                                target.stem if self.is_new else scenario_title(self.scenario_file)),
                                         conversion=self.conversion, document=self.document)
                    self.runtime_slot = slot
                else:
                    self.scenario.save_bytes(data, target)
                self.scenario_file = target
                self.is_new = False
                self.scenario = DdayScenario(target)
                self.saved_data = data
                self.saved_artwork = dict(self.terrain_artwork)
                self.saved_counters = dict(self.counter_artwork)
                self.saved_presentation = dict(self.presentation_artwork)
                self.saved_document = self.document
                self.mod_tracker.clear()
                self.modified = False
                self.modified_label.config(text="", foreground="black")
                self._load_mission_text()
                self.history.record(before_save, self._snapshot(), 'Prepare scenario for Save',
                                    'Normalize legacy scenario tables and briefing formatting for saving.')
                self.history.mark_saved()
                self._update_document_title()
                self._update_unit_actions()
                result = f'Saved changes to {target.name}'
                self.status_label.config(text=f'Saved {target.name}')
                if notify:
                    messagebox.showinfo('Saved', result)
            else:
                # No patches but modified flag set - just clear the flag
                self.modified = False
                self.modified_label.config(text="", foreground="black")
                self._load_mission_text()
                self.history.record(before_save, self._snapshot(), 'Normalize briefing formatting')
                self.history.mark_saved()
                self._update_document_title()
                self._update_history_actions()
                if notify:
                    messagebox.showinfo("Save", "No binary changes to write.")
            return True

        except Exception as e:
            messagebox.showerror("Save Error", f"Failed to save scenario:\n{e}")
            return False

    def export_scenario_for_dos(self):
        """Export current edits, artwork and AI orders for manual copying."""
        if self._modal_is_open():
            return
        if not self.scenario:
            messagebox.showwarning('Export for DOS', 'No scenario loaded!')
            return
        filename = filedialog.asksaveasfilename(
            title='Export for DOS — SCN, REZ and AI files',
            initialfile=(self.import_name or 'UNTITLED.SCN') if self.is_new else self.scenario_file.name, defaultextension='.SCN',
            filetypes=[('Scenario files', '*.SCN')])
        if not filename:
            return
        if not self._apply_form_drafts():
            return
        if Path(filename).resolve() == self.scenario_file.resolve():
            messagebox.showerror('Export for DOS', 'Choose a different folder or filename from your editing document.')
            return
        if Path(filename).exists():
            try:
                foreign = source_game(filename) != 'dday'
            except ValueError:
                foreign = False
            if foreign:
                messagebox.showerror('Export for DOS', 'Choose a separate export filename. The original source scenario must remain in its own game format.')
                return
        try:
            data = self._staged_data()
            from lib.battle_plans import advanced_plan, battle_plans
            from lib.event_rules import extended_plan
            plans = battle_plans(UnitRoster(data))
            advanced = any(advanced_plan(p) for p in plans)
            nested = any(extended_plan(p) for p in plans)
            slot = engine_slot(data)
            scenario, resources = export_for_dos(data, filename, self.terrain_artwork,
                                                counters=self.counter_artwork,
                                                presentation=self.presentation_artwork, document=self.document,
                                                title=(self.conversion['title'] if self.conversion else
                                                       Path(filename).stem if self.is_new else scenario_title(self.scenario_file)))
        except (OSError, ValueError) as exc:
            messagebox.showerror('Export for DOS', str(exc))
            return
        messagebox.showinfo('Export for DOS',
            f'Exported {scenario.name}, {resources.name}, and {scenario.with_suffix(".AI").name}.\n\n'
            + ('Also exported DATA/PCWATW.REZ for the custom startup screens. Copy it to the game’s DATA folder; it applies to all scenarios.\n\n'
               if (Path(filename).parent/'DATA'/'PCWATW.REZ').exists() else '') +
            'With the scenario-library engine, copy all three files together into SCENARIO, '
            'keeping their names. Select the scenario in the game’s Scenarios panel.\n\n' +
            ('Nested conditions and event actions require the current INVADE-PATCHED.EXE '
             '(nested-events patch). Keep the matching REZ and AI files when resuming saves. ' if nested else
             'Game profiles require the current INVADE-PATCHED.EXE (game-profiles patch). '
             'Keep the matching REZ and AI files when resuming saves. ' if self.document.profile.values != GameProfile().values else
             'Combined conditions and persistent orders require the current INVADE-PATCHED.EXE '
             '(advanced-orders patch). Keep the matching AI file when resuming saves. '
             'Earlier binaries cannot run this exported rule table. ' if advanced else
            f'With the older engine patch, use SCENARIO/{slot}, DATA/PCWATW.REZ '
            f'and WAWAI.DAT, then select {GAME_SCENARIOS[slot]}. '
            ) +
            'Keep editing the original document.')

    def save_scenario_as(self, *, confirm=True, notify=True):
        """Save scenario as new file"""
        if self._modal_is_open():
            return False
        if not self.scenario:
            messagebox.showwarning("Warning", "No scenario loaded!")
            return False

        filename = filedialog.asksaveasfilename(
            title="Save Scenario As",
            initialdir=self.scenario_file.parent if self.scenario_file and not self.is_new else '.',
            initialfile=self.scenario_file.name if self.scenario_file and not self.is_new else (self.import_name or 'UNTITLED.SCN'),
            defaultextension=".SCN",
            filetypes=[("Scenario Files", "*.SCN"), ("All Files", "*.*")]
        )

        if filename:
            return self.save_scenario(output_file=filename, confirm=confirm, notify=notify)
        return False

    def reload_scenario(self):
        """Reload current scenario"""
        if self._modal_is_open():
            return
        if self.is_new:
            messagebox.showinfo('Reload', 'Save this new scenario before reloading it.')
            return
        if self.scenario_file:
            if not self._confirm_document_replacement('reloading the scenario'):
                return
            try:
                scenario = DdayScenario(str(self.scenario_file))
                if not scenario.is_valid:
                    raise ValueError('Invalid scenario file format')
                load_artwork(self.scenario_file)
                load_counters(self.scenario_file)
                load_presentation(self.scenario_file)
                runtime_slot_for(self.scenario_file)
                load_document(self.scenario_file)
            except (OSError, ValueError) as exc:
                messagebox.showerror('Reload Error', str(exc))
                return
            self.scenario = scenario
            self._load_scenario_data()
            self.modified = False
            self.modified_label.config(text="")
            self._update_document_title()

    def validate_scenario(self):
        """Validate scenario"""
        if not self.scenario:
            messagebox.showwarning("Warning", "No scenario loaded!")
            return

        try:
            notes = authoring_warnings(self._staged_data())
        except ValueError as exc:
            messagebox.showerror('Validation', str(exc))
            return
        if notes:
            messagebox.showwarning('Validation', '\n'.join(notes))
        else:
            messagebox.showinfo('Validation', 'Scenario blocks, weather, and unit deployment checks passed.')

    def export_units(self):
        """Export unit list to text file"""
        if not self.units:
            messagebox.showwarning("Warning", "No units loaded!")
            return

        filename = filedialog.asksaveasfilename(
            title="Export Unit List",
            defaultextension=".txt",
            filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")]
        )

        if filename:
            with open(filename, 'w') as f:
                f.write(f"Unit List for {self.scenario_file.name}\n")
                f.write("=" * 60 + "\n\n")
                for unit in self.units:
                    f.write(f"Unit {unit.get('index', '?')}: {unit.get('name', 'Unknown')}\n")
                    f.write(f"  Type: {unit.get('type', 0)}\n")
                    f.write(f"  Offset: 0x{unit.get('offset', 0):04x}\n")
                    f.write("\n")

            messagebox.showinfo("Export", f"Unit list exported to:\n{filename}")

    def show_help(self):
        """Show help dialog"""
        help_text = """
D-Day Scenario Editor - User Guide

NEW SCENARIOS:
- New (Ctrl+N) creates a blank map and empty OOB, briefings and objectives
- Choose map size, starting terrain, date and duration
- Add an HQ for each side, then import units using Add Unit → Templates from
- The library executable lists exported scenarios in its Scenarios panel

SAVING:
- Save (Ctrl+S) updates the current file
- Save As (Ctrl+Shift+S) chooses a new name/location and switches to that copy
- Both commands are on the toolbar and in the File menu
- File → Export for DOS writes matching .SCN/.REZ/.AI files for manual installation
- Custom startup screens also export DATA/PCWATW.REZ for the game’s DATA folder
- The filename's asterisk includes unapplied unit/settings drafts
- Save and Export include valid drafts, even for units hidden by filters
- Drafts survive switching units and settings rows; Revert Form discards the visible draft
- Exit, New, Open and Reload offer Save / Discard / Cancel for unsaved changes

EDIT HISTORY:
- Undo (Ctrl+Z) and Redo (Ctrl+Y or Ctrl+Shift+Z) work across all scenario edits
- Edit → Edit History, or History on the toolbar, lists each change
- Select a step and Restore Selected to move backward or forward
- Unit/settings forms enter history when applied; briefing typing is grouped into bursts
- Save and Save As retain history and mark the saved step
- New, Open and Reload start a new session history
- Making a new edit after undo replaces the remaining redo steps

MISSION BRIEFINGS TAB:
- Edit Allied and Axis mission briefings side-by-side
- Each side has 8 lines with up to 127 characters per line
- Use Save to write changes; text beyond these limits is rejected, never truncated

MAP TAB:
- View terrain and units currently on the map
- Zoom and scroll to inspect the map
- Toggle the hex grid and coordinates
- Select: click a hex or unit stack; use Units at selected hex to choose a stacked unit
- Paint: choose terrain and artwork variant, then click a hex
- Blend edges while painting also updates transitions around painted or filled hexes
- Tools → Cosmetic edges blends a selected hex/region or the entire map, and supports
  manual edge artwork. Imported terrain is skipped unless explicitly included
- Features: choose dirt/paved road, railway, stream, river, uphill/downhill slope or hilltop
- Choose Add or Remove, click Edit features on map, then click near the desired hex edge
- Center clicks use the chosen compass direction; hilltops use the whole hex
- Or select a hex and use the compass and Add/Remove button in Features
- Connections update both hexes; slopes rise/fall toward the neighbor and use one side only
- Hilltops are separate markers (up to 30); adding one does not automatically create slopes
- Set selected hex to Clear replaces its base terrain; existing roads/rivers/hilltops stay
- Current OOB: choose a unit, click Place selected unit on map, then click its destination
- Deploy at start makes it available immediately; Keep arrival turn edits its arrival hex
- Remove from map keeps the unit inactive in the OOB for later placement
- Tools → Move formation moves an HQ and its ground units to the selected hex,
  optionally including subordinate HQs, Battle Plan goals and garrisons
- Tools → Region / fill copies terrain with optional units/HQs, objectives and names
- Tools → Shift map translates the map and all scenario locations; enlarge dimensions
  to make room, or reject shifts that would strand a location or saved movement route
- Drag to pan in any tool; dragging never paints or places a unit
- Undo / Redo reverse individual edits across the document; Save writes all changes

UNITS TAB:
- Browse Allied or Axis units in one shared roster
- Add Unit creates a custom unit from the current OOB or any game’s extracted library
- Delete Unit removes the selected unit from play; Save writes the deletion
- Choose Show: Deleted, then Restore Unit to bring a removed unit back
- Each Apply Changes, add/delete, organization and definition change has its own undo step
- Filter by status or search by name and unit type
- Select a unit to see its artwork and properties
- Choose chit changes a ground unit's artwork; Apply Changes keeps the choice
- Import image previews a custom ground/HQ chit; Use Chit adds it without replacing used chits
- Choose chit → Export Selected writes a PNG template for editing elsewhere
- Edit its name, position, combat strengths, and condition
- Set availability to At start, Scheduled, or Inactive
- For scheduled reinforcements, set the arrival turn and entry hex
- Click Apply Changes, then Save to write the scenario
- AI and orders shows saved orders and lets you edit shared HQ staff assistance
- Supply edits carried supplies and HQ reserves/distribution; calculated totals are read-only
- Transport mounts foot infantry/engineers on armor or dismounts linked passengers
- Orders previews and plots adjacent route steps, or clears the route with a defensive stance
- Apply in each dialog commits one edit; Save writes it to the scenario

TERRAIN REFERENCE TAB:
- Import Image adds a custom bitmap with both zoom levels and dim/night versions
- Choose its native terrain rules and artwork slot; the dialog shows affected hexes
- See terrain names, codes, artwork, and usage in the scenario

ARTWORK TAB:
- Import or select popup busts, flags, emblems and turn pictures
- Individual leader portraits appear under their names; Leaders → Portrait selects one
- Portraits replace the leader sidebar flag; the current library executable is required
- Game, series and publisher splashes export as a global DATA/PCWATW.REZ
- Use Selected Artwork applies the preview; Save keeps the pixels with the scenario

SCENARIO SETTINGS TAB:
- Set the actual duration and casualty scoring weights, then Apply Settings
- Add, edit and remove victory objectives: position, side values, owner and radius
- The executable sets victory-level score ratios; they are not SCN fields
- Weather edits conditions and temperature for a range of turns
- Supply edits initial stocks, entry hexes, and daily quantities
- Battle Plans adds timed HQ orders, up to three conditions combined with ALL/ANY,
  and orders that stay active after first matching; included in the exported AI file

        """

        win = tk.Toplevel(self.root)
        win.title("User Guide")
        win.geometry("600x500")

        text = scrolledtext.ScrolledText(win, wrap=tk.WORD)
        text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        text.insert('1.0', help_text)
        text.config(state=tk.DISABLED)

    def show_about(self):
        """Show about dialog"""
        messagebox.showinfo("About",
            "D-Day Scenario Editor - Consolidated Edition\n\n"
            "A comprehensive scenario editor combining the best features\n"
            "from the creator and editor tools.\n\n"
            "Features:\n"
            "- Interactive hex map viewer (125×100 grid)\n"
            "- Terrain visualization with zoom/pan\n"
            "- Enhanced unit editing with properties\n"
            "- Scenario settings editor\n"
            "- Mission briefing editor\n"
            "- Data visualization and analysis\n\n"
            "Version: 3.0 (Consolidated)\n"
            "Created: 2025-11-08")

    def run(self):
        """Run the application"""
        self.root.mainloop()


def main():
    """Main entry point"""
    import sys

    app = ImprovedScenarioEditor()

    # Load scenario from command line if provided
    if len(sys.argv) > 1:
        app.open_scenario(sys.argv[1])

    app.run()


if __name__ == '__main__':
    main()
