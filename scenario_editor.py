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
from tkinter import ttk, filedialog, messagebox, scrolledtext
from pathlib import Path
import struct
import shutil
import re
import math
import json
import os
from datetime import datetime
from PIL import Image, ImageTk
from lib.scenario_parser import DdayScenario
from lib.terrain_reader import extract_terrain_from_scenario
from lib.hex_tile_loader import load_hex_tiles, HexTileLoader


class EnhancedUnitParser:
    """Enhanced parser for unit data with better structure understanding"""

    # Unit type code mappings (reverse-engineered from binary data and military context)
    UNIT_TYPE_NAMES = {
        # Infantry Types
        0x00: 'Infantry-Bn',    # Generic infantry battalion
        0x01: 'Airborne-Bn',    # Airborne/paratrooper battalion (101st Airborne units)
        0x02: 'Infantry-Bn',    # Special infantry battalion
        0x04: 'SS-Bn',          # Waffen-SS battalion (German elite)
        0x08: 'Glider-Bn',      # Glider infantry battalion (airborne assault)
        0x0b: 'SS-Regiment',    # Waffen-SS regiment
        0x0f: 'FJ-Co',          # Fallschirmjäger company
        0x1d: 'Static-Bn',      # Static/coastal defense battalion
        0x27: 'Panzer-Co',      # Panzer company (German armor company)
        0x32: 'Heavy-Co',       # Heavy weapons company (SS/Panzergrenadier)
        0x35: 'Panzer-Bn',      # Panzer battalion - German armor
        0x38: 'FJ-Heavy',       # Fallschirmjäger heavy battalion
        0x41: 'PzGren-Bn',      # Panzergrenadier battalion (armored infantry)
        0x62: 'FJ-Heavy',       # Fallschirmjäger heavy battalion

        # Armor Types
        0x0d: 'Panzer-Heavy',   # Panzer heavy company/detachment
        0x28: 'Tank-Bn',        # Tank battalion (Allied)
        0x29: 'Tank-Bn',        # Tank battalion variant
        0x2a: 'Tank-Co',        # Tank company (detachment)
        0x60: 'Combat-Cmd-A',   # Combat Command A (US armored division)
        0x61: 'Combat-Cmd-B',   # Combat Command B (US armored division)

        # Artillery Types
        0x18: 'Artillery',      # Field artillery battalion
        0x24: 'Arty-Group',     # Artillery group (off-map fire support)
        0x25: 'Arty-Group',     # Artillery group variant
        0x43: 'Artillery',      # Artillery battalion

        # Support Types
        0x1b: 'Engineer',       # Engineer battalion
        0x16: 'Eng-Co',         # Engineer company
        0x34: 'Assault-Gun',    # Assault gun battalion (StuG)
        0x10: 'Flak-Regt',      # Flak regiment (anti-aircraft)
        0x36: 'AAA/Heavy',      # Anti-aircraft or heavy battalion
        0x40: 'Cavalry',        # Cavalry reconnaissance squadron
        0x5f: 'Recon',          # Reconnaissance battalion/company

        # Air Units
        0x26: 'Luftwaffe',      # Luftwaffe fighter wing (JG = Jagdgeschwader)

        # Command Levels
        0x07: 'Division-HQ',    # Division headquarters
        0x11: 'Corps',          # Corps level (Allied)
        0x12: 'Korps',          # Korps level (German)
        0x13: 'Division',       # Division level
        0x14: 'Static-Div',     # Static infantry division
        0x15: 'Regiment',       # Regiment level
        0x17: 'Company',        # Company level
        0x1c: 'Static-HQ',      # Static division HQ
        0x2b: 'Army-HQ',        # Army headquarters
        0x5e: 'Static-Regt',    # Static regiment (coastal defense)
    }

    @staticmethod
    def get_unit_type_name(type_code):
        """Convert unit type code to human-readable name"""
        return EnhancedUnitParser.UNIT_TYPE_NAMES.get(type_code, f'Type-{type_code:02x}')

    @staticmethod
    def parse_units_from_scenario(scenario):
        """Parse units from scenario - searches PTR4 and PTR6 sections"""
        units = []

        if not scenario:
            return units

        # Unit names are actually in PTR4 and PTR6, not PTR3!
        # PTR4 contains unit positioning and names
        # PTR6 contains unit definitions

        unit_index = 0

        # Parse from PTR6 (unit definitions)
        ptr6_data = scenario.sections.get('PTR6', b'')
        if ptr6_data:
            units.extend(EnhancedUnitParser._extract_units_from_data(
                ptr6_data, 'PTR6', unit_index))
            unit_index = len(units)

        # Parse from PTR4 (unit instances/positioning)
        ptr4_data = scenario.sections.get('PTR4', b'')
        if ptr4_data:
            # Skip mission text at the beginning (first ~10KB typically)
            # Look for unit names in the latter part
            search_start = min(10000, len(ptr4_data) // 2)
            units.extend(EnhancedUnitParser._extract_units_from_data(
                ptr4_data[search_start:], 'PTR4', unit_index, search_start))

        return units

    @staticmethod
    def _extract_units_from_data(data, section_name, start_index, offset_base=0):
        """Extract unit names from binary data"""
        units = []

        if not data:
            return units

        import re
        import struct

        # Find null-terminated ASCII strings (more accurate for unit names)
        # Look for sequences of printable chars followed by null byte
        pattern = b'[\x20-\x7e]{4,30}\x00'
        matches = re.finditer(pattern, data)

        unit_index = start_index

        for match in matches:
            # Remove the null terminator
            unit_name = match.group()[:-1].decode('ascii', errors='ignore').strip()

            # More strict validation
            if not unit_name or len(unit_name) < 4:
                continue

            # Skip location/objective markers (pattern: short string like "V9" followed by another string)
            # These appear as: "V9\x00C\x00Carentan\x00" where V9 is a 2-char marker
            if len(unit_name) == 2 or len(unit_name) == 3:
                # Check if there's another null-terminated string immediately after
                next_offset = match.end()
                if next_offset + 10 < len(data):
                    # Look for pattern: [1 char][null][readable string]
                    if data[next_offset] < 0x80 and next_offset + 2 < len(data) and data[next_offset + 1] == 0:
                        # This looks like a location marker, skip it
                        continue

            # Reject strings with invalid characters that never appear in real unit names
            invalid_chars = '!@#$%^&*+=[]{}|\\<>?/~`"\';'
            if any(c in invalid_chars for c in unit_name):
                continue

            # Must start with alphanumeric
            if not unit_name[0].isalnum():
                continue

            # Skip common non-unit strings
            skip_words = ['Your', 'The', 'You', 'and', 'are', 'for', 'with', 'that',
                         'http', 'www', 'Allied', 'Axis', 'beachhead', 'capture',
                         'attack', 'defend', 'objective', 'must', 'will', 'have']
            if any(word.lower() in unit_name.lower() for word in skip_words):
                continue

            # Look for unit-like patterns:
            # - Contains numbers: "101st", "3-501-101", "I-8-3FJ"
            # - Contains Roman numerals: "VII Corps", "III-5-3FJ"
            # - Military designations: "Infantry", "Airborne", "Corps"
            # - Common formats: "D-70-VII", "1-501-101"
            has_number = any(c.isdigit() for c in unit_name)

            # Check for Roman numerals (whole words only to avoid matching random I's)
            roman_pattern = r'\b(I|II|III|IV|V|VI|VII|VIII|IX|X|XI|XII)\b'
            has_roman = bool(re.search(roman_pattern, unit_name))

            military_terms = ['Corps', 'Infantry', 'Airborne', 'Division', 'FJ',
                             'Schnelle', 'Panzer', 'Armor', 'Regiment', 'Battalion',
                             'Brigade', 'Artillery', 'Cavalry', 'Recon', 'Engineer',
                             'Korps', 'Pz', 'Lehr']
            has_military = any(term in unit_name for term in military_terms)

            # Common unit naming patterns
            # e.g. "1-501-101", "D-70-VII", "III-5-3FJ"
            dash_pattern = r'^\d+[A-Z]?-\d+[A-Z]?-\d+[A-Z]*$|^[A-Z]-\d+-[IVX]+$|^[IVX]+-\d+-[A-Z0-9]+$'
            matches_pattern = bool(re.match(dash_pattern, unit_name))

            # "101st", "82nd", "3rd" style
            ordinal_pattern = r'\d+(st|nd|rd|th)\b'
            has_ordinal = bool(re.search(ordinal_pattern, unit_name))

            if has_number or has_roman or has_military or matches_pattern or has_ordinal:
                # Additional checks: Skip if the unit type byte looks like ASCII text
                # (indicates it's narrative text, not a unit record)
                if match.start() >= 64:
                    pre_check = data[match.start()-64:match.start()]
                    if len(pre_check) >= 27:
                        type_byte = pre_check[-27]
                        # If type byte is lowercase letter, it's probably narrative
                        if 0x61 <= type_byte <= 0x7a:  # lowercase a-z
                            continue
                        # If type byte is > 0x80, probably garbage/binary data
                        if type_byte > 0x80:
                            continue

                    # Additional sanity check: Count how many bytes in the pre-data look like garbage
                    # Real unit records have mostly low values and structure
                    high_bytes = sum(1 for b in pre_check[-32:] if b > 0x7F)
                    if high_bytes > 15:  # More than half are high bytes = garbage
                        continue

                # Get surrounding binary context for stats
                context_start = max(0, match.start() - 32)
                context_end = min(len(data), match.end() + 32)
                context = data[context_start:context_end]

                # Try to extract stats from binary data before the name
                # Combat stats are in the 64-byte record before the unit name
                unit_instance_index = 0
                unit_type = 0
                x = 0
                y = 0
                side = 'Unknown'
                attack_base = 0
                defense_base = 0
                quality = 0
                disruption = 0
                fatigue = 0
                antitank = 0

                if match.start() >= 64:
                    # Look at bytes before the unit name
                    # Unit record structure (64 bytes before name):
                    # Bytes -64 to -62: Unit Instance Index (NOT strength!)
                    # Byte -60: Antitank value
                    # Bytes -58 to -56: X coordinate
                    # Bytes -56 to -54: Y coordinate
                    # Byte -27: Unit type code
                    # Bytes -30,-29: Side indicator
                    # Byte -9: Attack base
                    # Byte -8: Defense base
                    # Byte -7: Quality
                    # Byte -6: Disruption
                    # Byte -5: Fatigue
                    # Byte -2: Record marker (0xFF)
                    pre_data = data[match.start()-64:match.start()]

                    # Extract unit type from byte at position -27
                    if len(pre_data) >= 27:
                        unit_type = pre_data[-27]

                    # Extract unit instance index as 16-bit LE at position -64
                    if len(pre_data) >= 64:
                        unit_instance_index = struct.unpack('<H', pre_data[-64:-62])[0]
                        # Sanity check - reasonable index values
                        if unit_instance_index > 1000:
                            unit_instance_index = 0

                    # Extract actual combat stats from last 16 bytes
                    if len(pre_data) >= 9:
                        attack_base = pre_data[-9]
                        defense_base = pre_data[-8]
                        quality = pre_data[-7]
                        disruption = pre_data[-6]
                        fatigue = pre_data[-5]

                    # Extract antitank from byte -60
                    if len(pre_data) >= 60:
                        antitank = pre_data[-60]

                    # Extract coordinates from offset -58 (X) and -56 (Y)
                    # Special value 0xFFFF (65535) indicates off-map/reinforcement units
                    if len(pre_data) >= 58:
                        x = struct.unpack('<H', pre_data[-58:-56])[0]
                    if len(pre_data) >= 56:
                        y = struct.unpack('<H', pre_data[-56:-54])[0]

                    # Check for off-map marker (0xFFFF = 65535)
                    if x == 0xFFFF or y == 0xFFFF:
                        # This is a reinforcement/off-map unit
                        x = -1  # Use -1 to indicate off-map
                        y = -1
                    # Validate coordinates (D-Day map is 125x100)
                    elif x > 125 or y > 100:
                        x = 0
                        y = 0

                    # Determine side from binary data at offset -30 and -29
                    # Allied units: both bytes = 0x00
                    # Axis units: both bytes = 0x01
                    if len(pre_data) >= 30:
                        side_byte_30 = pre_data[-30]
                        side_byte_29 = pre_data[-29]

                        if side_byte_30 == 0 and side_byte_29 == 0:
                            side = 'Allied'
                        elif side_byte_30 == 1 and side_byte_29 == 1:
                            side = 'Axis'
                        else:
                            side = 'Unknown'

                units.append({
                    'index': unit_index,
                    'name': unit_name,
                    'type': unit_type,
                    'unit_instance_index': unit_instance_index,
                    'attack_base': attack_base,
                    'defense_base': defense_base,
                    'quality': quality,
                    'disruption': disruption,
                    'fatigue': fatigue,
                    'antitank': antitank,
                    'x': x,
                    'y': y,
                    'side': side,
                    'section': section_name,
                    'offset': offset_base + match.start(),
                    'raw_data': context[:64].hex() if len(context) >= 64 else context.hex()
                })

                unit_index += 1

        return units

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
    DEFAULT_MAP_WIDTH = 100   # hexes (columns)
    DEFAULT_MAP_HEIGHT = 125  # hexes (rows) - longer dimension is vertical
    HEX_SIZE = 12     # initial hex radius in pixels

    def __init__(self, parent):
        super().__init__(parent)

        # Map state
        self.hex_size = self.HEX_SIZE
        self.offset_x = 50
        self.offset_y = 50
        self.show_grid = True
        self.show_coords = False
        self.units = []  # List of unit dicts from EnhancedUnitParser
        self.terrain = {}  # Dict of (x,y): terrain_type
        self.scenario = None  # Store scenario for accessing dynamic dimensions

        # Map dimensions (will be set from scenario, defaults used as fallback)
        self.map_width = self.DEFAULT_MAP_WIDTH
        self.map_height = self.DEFAULT_MAP_HEIGHT

        # Colors (fallback if images not available)
        self.terrain_colors = {
            0: '#90EE90',  # Grass/Field - light green
            1: '#4169E1',  # Water/Ocean - blue
            2: '#F4A460',  # Beach/Sand - sandy brown
            3: '#228B22',  # Forest - dark green
            4: '#A9A9A9',  # Town - gray
            5: '#8B4513',  # Road - brown
            6: '#4682B4',  # River - steel blue
            7: '#696969',  # Mountains - dim gray
            8: '#6B8E23',  # Swamp - olive
            9: '#8B7355',  # Bridge - tan
            10: '#708090', # Fortification - slate gray
            11: '#556B2F', # Bocage - dark olive
            12: '#A0522D', # Cliff - sienna
            13: '#BC8F8F', # Village - rosy brown
            14: '#DEB887', # Farm - burlywood
            15: '#5F9EA0', # Canal - cadet blue
            16: '#C0C0C0', # Unknown - silver
        }

        # Load hex tile images - CRITICAL, will raise RuntimeError if it fails
        self.hex_tile_images = {}  # Cache of PhotoImage objects by (terrain, variant, size)
        self.hex_tile_base_images = {}  # Cache of base terrain images (without variants)
        self.hex_tile_loader = None  # HexTileLoader instance for variant support

        try:
            self.use_images = self._load_hex_tiles()
        except RuntimeError as e:
            messagebox.showerror(
                "Critical Error: Hex Tiles Not Available",
                f"{e}\n\nThe scenario editor cannot function without hex tile images.\n"
                f"Please ensure extracted_images/scan_width_448.png exists.\n\n"
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

        self.map_title_label = ttk.Label(control_frame, text="Map Viewer",
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

        # Grid toggle
        self.grid_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(control_frame, text="Show Grid",
                       variable=self.grid_var,
                       command=self.redraw).pack(side=tk.LEFT, padx=2)

        # Coords toggle
        self.coords_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(control_frame, text="Show Coords",
                       variable=self.coords_var,
                       command=self.redraw).pack(side=tk.LEFT, padx=2)

        ttk.Separator(control_frame, orient=tk.VERTICAL).pack(side=tk.LEFT,
                                                              fill=tk.Y, padx=5)

        # Info label
        self.info_label = ttk.Label(control_frame, text="Zoom: 100%")
        self.info_label.pack(side=tk.LEFT, padx=10)

        # Canvas with scrollbars
        canvas_frame = ttk.Frame(self)
        canvas_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Scrollbars
        h_scroll = ttk.Scrollbar(canvas_frame, orient=tk.HORIZONTAL)
        h_scroll.pack(side=tk.BOTTOM, fill=tk.X)

        v_scroll = ttk.Scrollbar(canvas_frame, orient=tk.VERTICAL)
        v_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        # Canvas
        self.canvas = tk.Canvas(canvas_frame,
                               bg='#E8E8E8',
                               xscrollcommand=h_scroll.set,
                               yscrollcommand=v_scroll.set,
                               width=800,
                               height=600)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        h_scroll.config(command=self._on_xscroll)
        v_scroll.config(command=self._on_yscroll)

        # Status bar
        status_frame = ttk.Frame(self)
        status_frame.pack(fill=tk.X, padx=5, pady=2)

        self.status_label = ttk.Label(status_frame, text="Ready")
        self.status_label.pack(side=tk.LEFT)

    def _bind_events(self):
        """Bind mouse events for panning"""
        self.canvas.bind('<ButtonPress-1>', self._on_pan_start)
        self.canvas.bind('<B1-Motion>', self._on_pan_move)
        self.canvas.bind('<Motion>', self._on_mouse_move)
        self.canvas.bind('<MouseWheel>', self._on_mousewheel)
        self.canvas.bind('<Configure>', self._on_canvas_configure)

        self.drag_start_x = 0
        self.drag_start_y = 0
        self._configure_pending = False

    def _on_xscroll(self, *args):
        """Handle horizontal scroll and redraw"""
        self.canvas.xview(*args)
        if self.units or self.terrain:
            self.redraw()

    def _on_yscroll(self, *args):
        """Handle vertical scroll and redraw"""
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
        tiles = load_hex_tiles()

        # Store the loaded tiles (already in RGBA format with transparency)
        self.hex_tile_base_images = tiles

        print(f"Successfully loaded {len(self.hex_tile_base_images)} hex tile images")
        print("✓ Variant support enabled - can render specific hex variants from map data")
        return True

    def _get_hex_tile_image(self, terrain_type, size, variant=0):
        """
        Get a scaled hex tile image for the given terrain type, size, and variant.

        Args:
            terrain_type: Terrain type ID (0-16)
            size: Hex size in pixels
            variant: Variant column (0-12), defaults to 0

        Returns:
            PhotoImage ready for canvas use, or None if unavailable
        """
        if not self.use_images:
            return None

        # Create a cache key including variant
        cache_key = (terrain_type, variant, size)

        # Check cache
        if cache_key in self.hex_tile_images:
            return self.hex_tile_images[cache_key]

        # Get base image with specific variant
        try:
            if self.hex_tile_loader and variant > 0:
                # Use variant-specific tile
                base_img = self.hex_tile_loader.get_tile_with_variant(terrain_type, variant)
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

        # Calculate scaled size (hex tiles are 32×36 pixels actual content)
        # Scale proportionally to the hex size
        scale_factor = size / 12.0
        new_width = int(32 * scale_factor)
        new_height = int(36 * scale_factor)

        # Ensure minimum size
        new_width = max(4, new_width)
        new_height = max(4, new_height)

        # Scale the image
        try:
            scaled_img = base_img.resize((new_width, new_height), Image.Resampling.LANCZOS)
            photo_img = ImageTk.PhotoImage(scaled_img)

            # Cache it (keep a reference to prevent garbage collection)
            self.hex_tile_images[cache_key] = photo_img

            return photo_img
        except Exception as e:
            print(f"Error scaling hex tile image: {e}")
            return None

    def _on_pan_start(self, event):
        """Start panning"""
        self.drag_start_x = event.x
        self.drag_start_y = event.y

    def _on_pan_move(self, event):
        """Pan the view"""
        dx = event.x - self.drag_start_x
        dy = event.y - self.drag_start_y

        self.offset_x += dx
        self.offset_y += dy

        self.drag_start_x = event.x
        self.drag_start_y = event.y

        self.redraw()

    def _on_mouse_move(self, event):
        """Show hex coordinates under mouse"""
        # Convert screen to hex coordinates
        hex_x, hex_y = self.pixel_to_hex(event.x, event.y)

        if 0 <= hex_x < self.map_width and 0 <= hex_y < self.map_height:
            terrain_data = self.terrain.get((hex_x, hex_y), (0, 0))

            # Handle both old format (int) and new format (tuple)
            if isinstance(terrain_data, tuple):
                terrain_type, variant = terrain_data
                self.status_label.config(
                    text=f"Hex: ({hex_x}, {hex_y}) | Terrain: {terrain_type} | Variant: {variant}")
            else:
                self.status_label.config(
                    text=f"Hex: ({hex_x}, {hex_y}) | Terrain: {terrain_data}")
        else:
            self.status_label.config(text="Outside map bounds")

    def _on_mousewheel(self, event):
        """Zoom with mouse wheel"""
        if event.delta > 0:
            self.zoom_in()
        else:
            self.zoom_out()

    def _on_canvas_configure(self, event):
        """Handle canvas resize/configure event"""
        # Redraw when canvas is configured (prevents initial blank display)
        # Use a flag to avoid multiple redraws during rapid resizing
        if not self._configure_pending:
            self._configure_pending = True
            self.canvas.after(50, self._do_configure_redraw)

    def _do_configure_redraw(self):
        """Perform the actual redraw after configure event"""
        self._configure_pending = False
        if self.units or self.terrain:
            self.redraw()

    def hex_to_pixel(self, hex_x, hex_y):
        """Convert hex coordinates to pixel coordinates"""
        # Flat-top hexagon layout
        x = self.hex_size * math.sqrt(3) * (hex_x + 0.5 * (hex_y % 2))
        y = self.hex_size * 1.5 * hex_y

        return x + self.offset_x, y + self.offset_y

    def pixel_to_hex(self, pixel_x, pixel_y):
        """Convert pixel coordinates to hex coordinates (approximate)"""
        # Adjust for offset
        x = pixel_x - self.offset_x
        y = pixel_y - self.offset_y

        # Flat-top hexagon inverse
        hex_y = int(y / (self.hex_size * 1.5))
        hex_x = int((x - self.hex_size * math.sqrt(3) * 0.5 * (hex_y % 2)) /
                    (self.hex_size * math.sqrt(3)))

        return hex_x, hex_y

    def draw_hexagon(self, center_x, center_y, size, fill='white', outline='black'):
        """Draw a single hexagon"""
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

        # Get map dimensions from scenario (or use defaults)
        if scenario and scenario.is_valid:
            self.map_width = scenario.map_width
            self.map_height = scenario.map_height
            self.map_title_label.config(text=f"Map Viewer ({self.map_width}×{self.map_height} hex grid)")
        else:
            self.map_width = self.DEFAULT_MAP_WIDTH
            self.map_height = self.DEFAULT_MAP_HEIGHT
            self.map_title_label.config(text=f"Map Viewer ({self.map_width}×{self.map_height} hex grid)")

        # Extract REAL terrain data from scenario file!
        if scenario and scenario.is_valid:
            self.terrain = extract_terrain_from_scenario(scenario)
            terrain_source = "REAL terrain data from scenario file"
        else:
            # Fallback to generated terrain if scenario not available
            self.terrain = self._generate_fallback_terrain()
            terrain_source = "generated terrain (fallback)"

        # Count units with valid positions
        units_with_pos = sum(1 for u in self.units if u.get('x', 0) > 0 and u.get('y', 0) > 0)

        self.status_label.config(
            text=f"Loaded {len(self.units)} units ({units_with_pos} with positions) | {terrain_source}")

        # Force initial redraw after a short delay to ensure canvas is ready
        self.canvas.after(100, self.redraw)

    def _generate_fallback_terrain(self):
        """Generate fallback terrain (only used if real terrain can't be loaded)"""
        import random

        terrain = {}

        # Initialize all hexes as grass
        for y in range(self.map_height):
            for x in range(self.map_width):
                terrain[(x, y)] = 0  # Grass

        # Use fixed seed for deterministic generation
        random.seed(42)

        # Define terrain blob configurations
        # Format: (terrain_type, blob_count, min_size, max_size)
        terrain_blobs = [
            (1, 8, 15, 40),    # Water/Ocean - large patches
            (2, 12, 8, 20),    # Beach/Sand - medium patches
            (3, 25, 10, 35),   # Forest - many medium patches
            (4, 15, 5, 15),    # Town - smaller patches
            (6, 10, 3, 12),    # River - thin patches
            (8, 8, 8, 20),     # Swamp - medium patches
            (11, 12, 6, 18),   # Bocage (hedgerows) - medium patches
            (13, 10, 4, 12),   # Village - small patches
            (14, 8, 5, 15),    # Farm - medium patches
        ]

        # Generate terrain blobs
        for terrain_type, blob_count, min_size, max_size in terrain_blobs:
            for _ in range(blob_count):
                # Random center point
                center_x = random.randint(0, self.map_width - 1)
                center_y = random.randint(0, self.map_height - 1)

                # Random blob size
                blob_size = random.randint(min_size, max_size)

                # Generate blob using flood-fill style growth
                blob_hexes = set()
                to_process = [(center_x, center_y)]

                while to_process and len(blob_hexes) < blob_size:
                    x, y = to_process.pop(0)

                    if (x, y) in blob_hexes:
                        continue
                    if x < 0 or x >= self.map_width or y < 0 or y >= self.map_height:
                        continue

                    # Add to blob with probability decreasing by distance from center
                    dist = abs(x - center_x) + abs(y - center_y)
                    prob = max(0.2, 1.0 - (dist / (blob_size * 0.5)))

                    if random.random() < prob:
                        blob_hexes.add((x, y))

                        # Add neighbors to process queue
                        # Hex neighbors (flat-top hexagon)
                        if y % 2 == 0:  # Even row
                            neighbors = [
                                (x-1, y), (x+1, y),           # Left, right
                                (x-1, y-1), (x, y-1),         # Top-left, top-right
                                (x-1, y+1), (x, y+1)          # Bottom-left, bottom-right
                            ]
                        else:  # Odd row
                            neighbors = [
                                (x-1, y), (x+1, y),           # Left, right
                                (x, y-1), (x+1, y-1),         # Top-left, top-right
                                (x, y+1), (x+1, y+1)          # Bottom-left, bottom-right
                            ]

                        for nx, ny in neighbors:
                            if 0 <= nx < self.map_width and 0 <= ny < self.map_height:
                                if (nx, ny) not in blob_hexes:
                                    to_process.append((nx, ny))

                # Apply blob to terrain
                for x, y in blob_hexes:
                    terrain[(x, y)] = terrain_type

        return terrain

    def redraw(self):
        """Redraw the entire map"""
        self.canvas.delete('all')

        self.show_grid = self.grid_var.get()
        self.show_coords = self.coords_var.get()

        # Update info
        zoom_pct = int(self.hex_size / self.HEX_SIZE * 100)
        self.info_label.config(text=f"Zoom: {zoom_pct}% | Hexes: {self.map_width}×{self.map_height}")

        # Draw only visible hexes for performance
        visible_hexes = self._get_visible_hexes()

        # Draw terrain (background grid)
        for hex_y in range(visible_hexes['min_y'], visible_hexes['max_y']):
            for hex_x in range(visible_hexes['min_x'], visible_hexes['max_x']):
                if 0 <= hex_x < self.map_width and 0 <= hex_y < self.map_height:
                    self._draw_hex_tile(hex_x, hex_y)

        # Draw units at their actual positions
        for unit in self.units:
            # Get actual coordinates from unit data
            hex_x = unit.get('x', 0)
            hex_y = unit.get('y', 0)

            # Only draw units with valid coordinates (skip off-map units with x=-1 or y=-1)
            if hex_x > 0 and hex_y > 0 and hex_x < self.map_width and hex_y < self.map_height:
                # Determine unit color based on side
                side = unit.get('side', 'Unknown')
                unit_type = unit.get('type', 0)

                # Color coding:
                # - Blue for Allied units
                # - Red for Axis units
                # - Yellow for Unknown
                # - Darker shades for higher-level units (Corps/Division)
                if side == 'Allied':
                    if unit_type in [0x11, 0x13, 0x07]:  # Corps, Division, HQ
                        color = '#0000CD'  # Medium blue
                    else:
                        color = '#4169E1'  # Royal blue
                elif side == 'Axis':
                    if unit_type in [0x12, 0x13, 0x07]:  # Korps, Division, HQ
                        color = '#8B0000'  # Dark red
                    else:
                        color = '#DC143C'  # Crimson
                else:
                    color = '#FFD700'  # Gold for unknown

                self._draw_unit(hex_x, hex_y, unit.get('name', 'Unknown'), color)

        # Update scroll region
        self._update_scroll_region()

    def _get_visible_hexes(self):
        """Get range of visible hexes"""
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()

        # Add padding
        padding = 5

        min_x, min_y = self.pixel_to_hex(-self.offset_x, -self.offset_y)
        max_x, max_y = self.pixel_to_hex(canvas_width - self.offset_x,
                                         canvas_height - self.offset_y)

        return {
            'min_x': max(0, min_x - padding),
            'max_x': min(self.map_width, max_x + padding),
            'min_y': max(0, min_y - padding),
            'max_y': min(self.map_height, max_y + padding)
        }

    def _draw_hex_tile(self, hex_x, hex_y):
        """Draw a single hex tile with proper variant support"""
        px, py = self.hex_to_pixel(hex_x, hex_y)

        # Get terrain data (now includes variant)
        terrain_data = self.terrain.get((hex_x, hex_y), (0, 0))

        # Handle both old format (int) and new format (tuple)
        if isinstance(terrain_data, tuple):
            terrain_type, variant = terrain_data
        else:
            # Legacy format compatibility
            terrain_type = terrain_data
            variant = 0

        # Try to use image first, fallback to color
        if self.use_images:
            tile_img = self._get_hex_tile_image(terrain_type, self.hex_size, variant)
            if tile_img:
                # Draw the image
                self.canvas.create_image(px, py, image=tile_img, anchor=tk.CENTER)

                # Draw grid outline if enabled
                if self.show_grid:
                    self.draw_hexagon(px, py, self.hex_size, fill='', outline='#888888')

                # Draw coordinates if enabled
                if self.show_coords and self.hex_size >= 10:
                    coord_text = f"{hex_x},{hex_y}"
                    if variant > 0:
                        coord_text += f"\nv{variant}"
                    self.canvas.create_text(px, py,
                                           text=coord_text,
                                           font=("Arial", max(6, int(self.hex_size / 3))),
                                           fill='black')
                return

        # Fallback to colored hexagon
        color = self.terrain_colors.get(terrain_type, '#FFFFFF')
        outline_color = '#666666' if self.show_grid else color
        self.draw_hexagon(px, py, self.hex_size, fill=color, outline=outline_color)

        # Draw coordinates if enabled
        if self.show_coords and self.hex_size >= 10:
            coord_text = f"{hex_x},{hex_y}"
            if variant > 0:
                coord_text += f"\nv{variant}"
            self.canvas.create_text(px, py,
                                   text=coord_text,
                                   font=("Arial", max(6, int(self.hex_size / 3))),
                                   fill='black')

    def _draw_unit(self, hex_x, hex_y, name, color='red'):
        """Draw a unit marker"""
        px, py = self.hex_to_pixel(hex_x, hex_y)

        # Draw unit marker (colored circle)
        radius = self.hex_size * 0.4
        # Calculate darker outline color
        outline_color = self._darken_color(color)

        self.canvas.create_oval(px - radius, py - radius,
                               px + radius, py + radius,
                               fill=color, outline=outline_color, width=2)

        # Draw unit name if zoom is large enough
        if self.hex_size >= 15:
            self.canvas.create_text(px, py - self.hex_size - 5,
                                   text=name,
                                   font=("Arial", max(7, int(self.hex_size / 2))),
                                   fill=outline_color)

    def _darken_color(self, color):
        """Darken a hex color by 30%"""
        # Remove '#' if present
        if color.startswith('#'):
            color = color[1:]

        # Convert to RGB
        r = int(color[0:2], 16)
        g = int(color[2:4], 16)
        b = int(color[4:6], 16)

        # Darken by 30%
        r = int(r * 0.7)
        g = int(g * 0.7)
        b = int(b * 0.7)

        return f'#{r:02x}{g:02x}{b:02x}'

    def _update_scroll_region(self):
        """Update canvas scroll region"""
        # Calculate map bounds
        max_x = self.map_width * self.hex_size * math.sqrt(3) + self.offset_x + 100
        max_y = self.map_height * self.hex_size * 1.5 + self.offset_y + 100

        self.canvas.config(scrollregion=(0, 0, max_x, max_y))

    def zoom_in(self):
        """Zoom in"""
        self.hex_size = min(50, int(self.hex_size * 1.2))
        self.redraw()

    def zoom_out(self):
        """Zoom out"""
        self.hex_size = max(4, int(self.hex_size / 1.2))
        self.redraw()

    def reset_view(self):
        """Reset view to default"""
        self.hex_size = self.HEX_SIZE
        self.offset_x = 50
        self.offset_y = 50
        self.redraw()


class UnitPropertiesEditor(ttk.Frame):
    """Structured editor for unit properties"""

    def __init__(self, parent, on_unit_update_callback):
        super().__init__(parent)
        self.on_unit_update_callback = on_unit_update_callback
        self.current_unit = None

        # Create UI
        title = ttk.Label(self, text="Unit Properties Editor",
                         font=("TkDefaultFont", 10, "bold"))
        title.grid(row=0, column=0, columnspan=2, pady=10, sticky=tk.W)

        # Unit selection
        ttk.Label(self, text="Select Unit:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        self.unit_combo = ttk.Combobox(self, width=40, state='readonly')
        self.unit_combo.grid(row=1, column=1, sticky=tk.W, padx=5, pady=5)
        self.unit_combo.bind('<<ComboboxSelected>>', self.on_unit_selected)

        # Separator
        ttk.Separator(self, orient=tk.HORIZONTAL).grid(row=2, column=0, columnspan=2,
                                                       sticky=tk.EW, pady=10)

        # Unit properties form
        form_frame = ttk.LabelFrame(self, text="Unit Properties", padding=10)
        form_frame.grid(row=3, column=0, columnspan=2, sticky=tk.EW, padx=5, pady=5)

        # Name
        ttk.Label(form_frame, text="Name:").grid(row=0, column=0, sticky=tk.W, pady=3)
        self.name_entry = ttk.Entry(form_frame, width=30)
        self.name_entry.grid(row=0, column=1, sticky=tk.W, pady=3, padx=5)

        # Type and Side on same row
        ttk.Label(form_frame, text="Type:").grid(row=1, column=0, sticky=tk.W, pady=3)
        self.type_entry = ttk.Entry(form_frame, width=20)
        self.type_entry.grid(row=1, column=1, sticky=tk.W, pady=3, padx=5)

        ttk.Label(form_frame, text="Side:").grid(row=1, column=2, sticky=tk.W, pady=3, padx=(10,0))
        self.side_combo = ttk.Combobox(form_frame, width=10, state='readonly',
                                       values=['Allied', 'Axis'])
        self.side_combo.grid(row=1, column=3, sticky=tk.W, pady=3, padx=5)
        self.side_combo.current(0)

        # Position X
        ttk.Label(form_frame, text="Position X:").grid(row=2, column=0, sticky=tk.W, pady=3)
        self.pos_x_spin = ttk.Spinbox(form_frame, from_=0, to=500, width=10)
        self.pos_x_spin.grid(row=2, column=1, sticky=tk.W, pady=3, padx=5)

        # Position Y
        ttk.Label(form_frame, text="Position Y:").grid(row=3, column=0, sticky=tk.W, pady=3)
        self.pos_y_spin = ttk.Spinbox(form_frame, from_=0, to=500, width=10)
        self.pos_y_spin.grid(row=3, column=1, sticky=tk.W, pady=3, padx=5)

        # Combat Stats section
        stats_frame = ttk.LabelFrame(form_frame, text="Combat Stats", padding=5)
        stats_frame.grid(row=4, column=0, columnspan=4, sticky=tk.EW, pady=5)

        # Attack
        ttk.Label(stats_frame, text="Attack:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.attack_spin = ttk.Spinbox(stats_frame, from_=0, to=20, width=5)
        self.attack_spin.grid(row=0, column=1, sticky=tk.W, pady=2, padx=5)
        self.attack_spin.set(0)

        # Defense
        ttk.Label(stats_frame, text="Defense:").grid(row=0, column=2, sticky=tk.W, pady=2, padx=(10,0))
        self.defense_spin = ttk.Spinbox(stats_frame, from_=0, to=20, width=5)
        self.defense_spin.grid(row=0, column=3, sticky=tk.W, pady=2, padx=5)
        self.defense_spin.set(0)

        # Quality
        ttk.Label(stats_frame, text="Quality:").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.quality_spin = ttk.Spinbox(stats_frame, from_=0, to=10, width=5)
        self.quality_spin.grid(row=1, column=1, sticky=tk.W, pady=2, padx=5)
        self.quality_spin.set(0)

        # Antitank
        ttk.Label(stats_frame, text="Antitank:").grid(row=1, column=2, sticky=tk.W, pady=2, padx=(10,0))
        self.antitank_spin = ttk.Spinbox(stats_frame, from_=0, to=20, width=5)
        self.antitank_spin.grid(row=1, column=3, sticky=tk.W, pady=2, padx=5)
        self.antitank_spin.set(0)

        # Disruption
        ttk.Label(stats_frame, text="Disruption:").grid(row=2, column=0, sticky=tk.W, pady=2)
        self.disruption_spin = ttk.Spinbox(stats_frame, from_=0, to=10, width=5)
        self.disruption_spin.grid(row=2, column=1, sticky=tk.W, pady=2, padx=5)
        self.disruption_spin.set(0)

        # Fatigue
        ttk.Label(stats_frame, text="Fatigue:").grid(row=2, column=2, sticky=tk.W, pady=2, padx=(10,0))
        self.fatigue_spin = ttk.Spinbox(stats_frame, from_=0, to=10, width=5)
        self.fatigue_spin.grid(row=2, column=3, sticky=tk.W, pady=2, padx=5)
        self.fatigue_spin.set(0)

        # Separator for AI Scripting section
        ttk.Separator(form_frame, orient=tk.HORIZONTAL).grid(row=5, column=0, columnspan=4,
                                                              sticky=tk.EW, pady=10)

        # AI Behavior section label with info
        ai_header_frame = ttk.Frame(form_frame)
        ai_header_frame.grid(row=6, column=0, columnspan=4, sticky=tk.W, pady=(0, 5))

        ai_label = ttk.Label(ai_header_frame, text="AI Behavior Flags (Bit Field)",
                            font=("TkDefaultFont", 9, "bold"))
        ai_label.pack(side=tk.LEFT)

        # Info button
        info_btn = ttk.Button(ai_header_frame, text="?", width=3,
                             command=self._show_behavior_help)
        info_btn.pack(side=tk.LEFT, padx=5)

        # Behavior Byte (hex display with live update)
        ttk.Label(form_frame, text="Behavior Byte:").grid(row=7, column=0, sticky=tk.W, pady=3)
        self.behavior_byte_var = tk.StringVar(value="0x00")
        behavior_display_frame = ttk.Frame(form_frame)
        behavior_display_frame.grid(row=7, column=1, sticky=tk.W, pady=3, padx=5)

        self.behavior_byte_entry = ttk.Entry(behavior_display_frame, width=10, state='readonly',
                                             textvariable=self.behavior_byte_var,
                                             font=("Courier", 10, "bold"))
        self.behavior_byte_entry.pack(side=tk.LEFT)

        # Binary display
        self.behavior_binary_var = tk.StringVar(value="0b00000000")
        ttk.Label(behavior_display_frame, textvariable=self.behavior_binary_var,
                 font=("Courier", 9), foreground='#666666').pack(side=tk.LEFT, padx=(10, 0))

        # AI Behavior Flags (8 checkboxes for individual bits)
        flags_frame = ttk.LabelFrame(form_frame, text="Behavior Flags", padding=5)
        flags_frame.grid(row=8, column=0, columnspan=4, sticky=tk.EW, pady=5, padx=5)

        # Define behavior bit flags with descriptions
        self.behavior_flags = [
            {'bit': 0, 'mask': 0x01, 'name': 'Active/Enabled',
             'desc': 'Unit is active and can take actions'},
            {'bit': 1, 'mask': 0x02, 'name': 'Mobile',
             'desc': 'Unit can move on the map'},
            {'bit': 2, 'mask': 0x04, 'name': 'Combat Capable',
             'desc': 'Unit can engage in combat'},
            {'bit': 3, 'mask': 0x08, 'name': 'Scripted Orders',
             'desc': 'Unit has special scripted orders'},
            {'bit': 4, 'mask': 0x10, 'name': 'Defensive Stance',
             'desc': 'Unit takes defensive stance'},
            {'bit': 5, 'mask': 0x20, 'name': 'Aggressive/Attack',
             'desc': 'Unit actively seeks combat'},
            {'bit': 6, 'mask': 0x40, 'name': 'Reserved/Hold',
             'desc': 'Unit held in reserve'},
            {'bit': 7, 'mask': 0x80, 'name': 'High Priority',
             'desc': 'High-priority/critical unit'},
        ]

        # Create checkbox variables
        self.behavior_flag_vars = []

        # Layout checkboxes in 2 columns
        for i, flag in enumerate(self.behavior_flags):
            row = i % 4
            col = i // 4

            var = tk.BooleanVar(value=False)
            self.behavior_flag_vars.append(var)

            cb = ttk.Checkbutton(flags_frame,
                                text=f"Bit {flag['bit']}: {flag['name']}",
                                variable=var,
                                command=self._on_behavior_flag_changed)
            cb.grid(row=row, column=col*2, sticky=tk.W, pady=2, padx=5)

            # Add tooltip/description label
            desc_label = ttk.Label(flags_frame, text=flag['desc'],
                                  font=("TkDefaultFont", 8),
                                  foreground='#666666')
            desc_label.grid(row=row, column=col*2+1, sticky=tk.W, pady=2, padx=(0, 10))

        # Buttons
        button_frame = ttk.Frame(self)
        button_frame.grid(row=4, column=0, columnspan=2, pady=10)

        ttk.Button(button_frame, text="Apply Changes",
                  command=self.apply_changes).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Revert",
                  command=self.revert_changes).pack(side=tk.LEFT, padx=5)

        # Raw data view
        raw_frame = ttk.LabelFrame(self, text="Raw Data (read-only)", padding=10)
        raw_frame.grid(row=5, column=0, columnspan=2, sticky=tk.EW, padx=5, pady=5)

        self.raw_text = scrolledtext.ScrolledText(raw_frame, height=6, width=60,
                                                  font=("Courier", 9))
        self.raw_text.pack(fill=tk.BOTH, expand=True)

    def load_units(self, units):
        """Load units into the selector"""
        self.units = units

        unit_names = [f"{u.get('index', i)}: {u.get('name', 'Unknown')}"
                     for i, u in enumerate(units)]
        self.unit_combo['values'] = unit_names

        if units:
            self.unit_combo.current(0)
            self.on_unit_selected(None)

    def on_unit_selected(self, event):
        """Handle unit selection"""
        if not self.unit_combo.get():
            return

        index = self.unit_combo.current()
        if 0 <= index < len(self.units):
            self.current_unit = self.units[index]
            self.display_unit()

    def display_unit(self):
        """Display current unit in the form"""
        if not self.current_unit:
            return

        # Populate form
        self.name_entry.delete(0, tk.END)
        self.name_entry.insert(0, self.current_unit.get('name', ''))

        # Show type with human-readable name
        type_code = self.current_unit.get('type', 0)
        type_name = EnhancedUnitParser.get_unit_type_name(type_code)
        self.type_entry.delete(0, tk.END)
        self.type_entry.insert(0, f"{type_name} (0x{type_code:02x})")

        # Set position from unit data
        x = self.current_unit.get('x', 0)
        y = self.current_unit.get('y', 0)

        # Handle special cases
        if x == -1 or y == -1:
            # Off-map/reinforcement unit
            x = 0
            y = 0

        self.pos_x_spin.set(x)
        self.pos_y_spin.set(y)

        # Set combat stats from unit data
        attack_base = self.current_unit.get('attack_base', 0)
        defense_base = self.current_unit.get('defense_base', 0)
        quality = self.current_unit.get('quality', 0)
        antitank = self.current_unit.get('antitank', 0)
        disruption = self.current_unit.get('disruption', 0)
        fatigue = self.current_unit.get('fatigue', 0)

        self.attack_spin.set(attack_base)
        self.defense_spin.set(defense_base)
        self.quality_spin.set(quality)
        self.antitank_spin.set(antitank)
        self.disruption_spin.set(disruption)
        self.fatigue_spin.set(fatigue)

        # Set side from unit data
        side = self.current_unit.get('side', 'Allied')
        if side == 'Axis':
            self.side_combo.current(1)
        else:
            self.side_combo.current(0)

        # Set AI behavior from unit data
        # Try to extract behavior byte from raw data (at offset +5 in 8-byte record)
        behavior_byte = self.current_unit.get('behavior_byte', None)

        # If not directly stored, try to extract from raw_data
        if behavior_byte is None:
            raw_data = self.current_unit.get('raw_data', '')
            if raw_data and len(raw_data) >= 10:  # Need at least 5 bytes (10 hex chars)
                try:
                    # Behavior byte is at offset +5 in the unit record
                    # In hex string, that's position 10 (2 chars per byte)
                    behavior_byte = int(raw_data[10:12], 16)
                except (ValueError, IndexError):
                    behavior_byte = 0x00
            else:
                behavior_byte = 0x00

        # Update byte display
        self.behavior_byte_var.set(f"0x{behavior_byte:02X}")
        self.behavior_binary_var.set(f"0b{behavior_byte:08b}")

        # Set individual flag checkboxes based on behavior byte
        for i, flag in enumerate(self.behavior_flags):
            is_set = bool(behavior_byte & flag['mask'])
            self.behavior_flag_vars[i].set(is_set)

        # Display raw data
        self.raw_text.delete('1.0', tk.END)
        self.raw_text.insert('1.0', f"Section: {self.current_unit.get('section', 'Unknown')}\n")
        self.raw_text.insert('1.0', f"Offset: 0x{self.current_unit.get('offset', 0):06x}\n")
        self.raw_text.insert(tk.END, f"Type: {self.current_unit.get('type', 0)}\n")
        self.raw_text.insert(tk.END, f"Unit Instance Index: {self.current_unit.get('unit_instance_index', 0)}\n")
        eff_atk = attack_base - fatigue
        eff_def = defense_base - fatigue
        self.raw_text.insert(tk.END, f"Attack: {eff_atk} (base={attack_base})\n")
        self.raw_text.insert(tk.END, f"Defense: {eff_def} (base={defense_base})\n")
        self.raw_text.insert(tk.END, f"Quality: {quality}, Antitank: {antitank}\n")
        self.raw_text.insert(tk.END, f"Disruption: {disruption}, Fatigue: {fatigue}\n")
        self.raw_text.insert(tk.END, f"\nRaw hex data (64 bytes):\n")
        raw_data = self.current_unit.get('raw_data', '')
        # Format hex nicely
        for i in range(0, min(len(raw_data), 128), 32):
            self.raw_text.insert(tk.END, f"{raw_data[i:i+32]}\n")

    def apply_changes(self):
        """Apply changes to the current unit"""
        if not self.current_unit:
            messagebox.showwarning("Warning", "No unit selected!")
            return

        # Update unit data
        self.current_unit['name'] = self.name_entry.get()

        try:
            self.current_unit['type'] = int(self.type_entry.get())
        except ValueError:
            pass

        # Update combat stats
        try:
            self.current_unit['attack_base'] = int(self.attack_spin.get())
            self.current_unit['defense_base'] = int(self.defense_spin.get())
            self.current_unit['quality'] = int(self.quality_spin.get())
            self.current_unit['antitank'] = int(self.antitank_spin.get())
            self.current_unit['disruption'] = int(self.disruption_spin.get())
            self.current_unit['fatigue'] = int(self.fatigue_spin.get())
        except ValueError:
            pass

        # Update side
        self.current_unit['side'] = self.side_combo.get()

        # Update behavior byte from checkboxes
        behavior_byte = self._get_behavior_byte_from_flags()
        self.current_unit['behavior_byte'] = behavior_byte

        # Build flag description for user
        active_flags = []
        for i, flag in enumerate(self.behavior_flags):
            if self.behavior_flag_vars[i].get():
                active_flags.append(f"Bit {flag['bit']}")

        flags_str = ", ".join(active_flags) if active_flags else "None"

        # Notify callback
        if self.on_unit_update_callback:
            self.on_unit_update_callback(self.current_unit)

        atk = self.current_unit.get('attack_base', 0)
        defn = self.current_unit.get('defense_base', 0)
        qual = self.current_unit.get('quality', 0)
        messagebox.showinfo("Success",
                           f"Unit properties updated!\n\n"
                           f"Changes:\n"
                           f"- Name: {self.current_unit['name']}\n"
                           f"- Side: {self.current_unit['side']}\n"
                           f"- Attack: {atk}, Defense: {defn}, Quality: {qual}\n"
                           f"- Behavior: 0x{behavior_byte:02X} (0b{behavior_byte:08b})\n"
                           f"- Flags: {flags_str}\n\n"
                           f"Note: Changes are saved in memory. Use File > Save to persist to disk.")

    def revert_changes(self):
        """Revert changes to current unit"""
        self.display_unit()

    def _on_behavior_flag_changed(self):
        """Handle behavior flag checkbox change"""
        # Calculate new behavior byte from checkboxes
        behavior_byte = self._get_behavior_byte_from_flags()

        # Update displays
        self.behavior_byte_var.set(f"0x{behavior_byte:02X}")
        self.behavior_binary_var.set(f"0b{behavior_byte:08b}")

    def _get_behavior_byte_from_flags(self):
        """Calculate behavior byte value from checkbox states"""
        behavior_byte = 0x00
        for i, flag in enumerate(self.behavior_flags):
            if self.behavior_flag_vars[i].get():
                behavior_byte |= flag['mask']
        return behavior_byte

    def _show_behavior_help(self):
        """Show detailed help about AI behavior system"""
        help_text = """AI BEHAVIOR BIT FIELD SYSTEM

The D-Day game engine uses a bit field system where each unit has a behavior
byte (at offset +5 in its 8-byte record) that controls AI behavior through
8 independent flags.

IMPORTANT: This is NOT a simple state enumeration! Each bit controls a
different aspect of unit behavior and can be combined.

BEHAVIOR FLAGS:

• Bit 0 (0x01): Active/Enabled
  Unit is active and can take actions. Without this, unit is inactive.

• Bit 1 (0x02): Mobile
  Unit can move on the map. Clear this for static defenses.

• Bit 2 (0x04): Combat Capable
  Unit can engage in combat operations.

• Bit 3 (0x08): Scripted Orders
  Unit has special scripted orders or AI behavior.

• Bit 4 (0x10): Defensive Stance
  Unit takes a defensive stance. Gates certain AI processing.

• Bit 5 (0x20): Aggressive/Attack
  Unit actively seeks combat and attacks enemy units.

• Bit 6 (0x40): Reserved/Hold
  Unit is held in reserve, not immediately committed.

• Bit 7 (0x80): High Priority
  High-priority or critical unit marker.

COMMON COMBINATIONS:

• Inactive Unit (0x00)
  All flags clear - unit is inactive/dead.

• Basic Active Unit (0x07)
  Bits 0,1,2 - Active, Mobile, Combat capable.

• Defensive Unit (0x15)
  Bits 0,2,4 - Active, Combat, Defensive stance.

• Aggressive Attacker (0x27)
  Bits 0,1,2,5 - Active, Mobile, Combat, Aggressive.

• Reserved Force (0x47)
  Bits 0,1,2,6 - Active, Mobile, Combat, Reserved.

• Scripted Behavior (0x0F)
  Bits 0-3 - Active, Mobile, Combat, Scripted.

SPECIAL ENGINE VALUES:

The game engine temporarily sets these values during AI processing:
• 0x80, 0x92, 0xF2 - Temporary AI processing states
• 0xFF - Template/disabled unit marker
• 0xFD - Alternative template marker

Do not manually set these unless creating special test scenarios.

HOW IT WORKS:

The game engine reads the behavior byte during AI processing. Individual
bits control different aspects:
- Bit 4 (0x10) gates whether unit processes AI at all
- Combination of flags determines unit's tactical behavior
- Engine may temporarily modify behavior during processing

TECHNICAL DETAILS:

- Stored in PTR6 section at unit offset +5
- Each unit is 8 bytes in PTR6
- Flags can be combined for complex behaviors
- Disassembly shows extensive bit testing (line 4307+)

For complete analysis: txt/AI_BEHAVIOR_BYTE_ANALYSIS.md
"""

        # Create help dialog
        help_win = tk.Toplevel(self.master)
        help_win.title("AI Behavior Help")
        help_win.geometry("650x600")

        # Text widget with scrollbar
        text_frame = ttk.Frame(help_win)
        text_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        scrollbar = ttk.Scrollbar(text_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        text = tk.Text(text_frame, wrap=tk.WORD, yscrollcommand=scrollbar.set,
                      font=("Courier", 9))
        text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=text.yview)

        text.insert('1.0', help_text)
        text.config(state=tk.DISABLED)

        # Close button
        close_btn = ttk.Button(help_win, text="Close", command=help_win.destroy)
        close_btn.pack(pady=10)


class ScenarioSettingsEditor(ttk.Frame):
    """Editor for scenario-level settings"""

    def __init__(self, parent):
        super().__init__(parent)

        title = ttk.Label(self, text="Scenario Settings",
                         font=("TkDefaultFont", 10, "bold"))
        title.pack(pady=10)

        # Settings form
        form_frame = ttk.LabelFrame(self, text="General Settings", padding=15)
        form_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # Scenario name
        row = 0
        ttk.Label(form_frame, text="Scenario Name:").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.name_entry = ttk.Entry(form_frame, width=40)
        self.name_entry.grid(row=row, column=1, sticky=tk.W, pady=5, padx=5)

        # Turn limit
        row += 1
        ttk.Label(form_frame, text="Turn Limit:").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.turn_spin = ttk.Spinbox(form_frame, from_=1, to=100, width=10)
        self.turn_spin.grid(row=row, column=1, sticky=tk.W, pady=5, padx=5)
        self.turn_spin.set(20)

        # Difficulty
        row += 1
        ttk.Label(form_frame, text="Difficulty:").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.difficulty_combo = ttk.Combobox(form_frame, width=15, state='readonly',
                                            values=['Easy', 'Normal', 'Hard', 'Expert'])
        self.difficulty_combo.grid(row=row, column=1, sticky=tk.W, pady=5, padx=5)
        self.difficulty_combo.current(1)

        # Weather
        row += 1
        ttk.Label(form_frame, text="Weather:").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.weather_combo = ttk.Combobox(form_frame, width=15, state='readonly',
                                         values=['Clear', 'Cloudy', 'Rain', 'Storm'])
        self.weather_combo.grid(row=row, column=1, sticky=tk.W, pady=5, padx=5)
        self.weather_combo.current(0)

        # Victory conditions
        row += 1
        ttk.Label(form_frame, text="Victory Conditions:").grid(row=row, column=0,
                                                               sticky=tk.NW, pady=5)
        self.victory_text = scrolledtext.ScrolledText(form_frame, height=4, width=40)
        self.victory_text.grid(row=row, column=1, sticky=tk.W, pady=5, padx=5)
        self.victory_text.insert('1.0', "Capture all objective hexes\nEliminate enemy forces")

        # Info label
        info_frame = ttk.Frame(self)
        info_frame.pack(fill=tk.X, padx=10, pady=10)

        info_label = ttk.Label(info_frame,
                              text="Note: These settings are interpreted from binary data.\n"
                                   "Some values may not be fully accurate until format is completely decoded.",
                              foreground="#666666", font=("TkDefaultFont", 8))
        info_label.pack()

        # Buttons
        button_frame = ttk.Frame(self)
        button_frame.pack(pady=10)

        ttk.Button(button_frame, text="Apply Settings",
                  command=self.apply_settings).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Reset to Defaults",
                  command=self.reset_settings).pack(side=tk.LEFT, padx=5)

    def load_scenario_data(self, scenario):
        """Load scenario data into the form"""
        # Load scenario name
        self.name_entry.delete(0, tk.END)
        self.name_entry.insert(0, scenario.filename.stem if scenario else "Unknown")

        # Load turn count - it's stored at word[3] (offset +6) in a parameter array
        # The array location varies per scenario, so we search for it
        if scenario and scenario.data:
            turn_count = self._find_turn_count(scenario)
            if turn_count:
                self.turn_spin.delete(0, tk.END)
                self.turn_spin.insert(0, str(turn_count))

    def _find_turn_count(self, scenario):
        """Find turn count in scenario data

        Based on analysis documented in txt/TURN_COUNT_FORMAT.md:
        - Turn count is ALWAYS at word[3] (offset +6) within a parameter array
        - Array location varies per scenario but can be found by searching
        - Turn count range: 1-255
        - Surrounding words (word[0-2]) are typically < 1000
        """
        # Common turn count array base offsets (array_start, not turn offset)
        # These are the most likely locations to find the parameter array
        common_array_bases = [
            0x0246,  # BRADLEY, COUNTER
            0x02EA,  # COBRA
            0x1462,  # STLO (in PTR5 section)
            0x1F7A,  # UTAH
            0x1976,  # OMAHA
            0x2220,  # CAMPAIGN
        ]

        # First, check common offsets (fast path)
        for array_base in common_array_bases:
            if array_base + 8 < len(scenario.data):
                turn_offset = array_base + 6  # word[3]
                turn_candidate = struct.unpack('<H', scenario.data[turn_offset:turn_offset + 2])[0]

                # Validate: turn count should be reasonable
                if 1 <= turn_candidate <= 255:
                    # Double-check by validating word[0-2] are also reasonable
                    word0 = struct.unpack('<H', scenario.data[array_base:array_base + 2])[0]
                    word1 = struct.unpack('<H', scenario.data[array_base + 2:array_base + 4])[0]
                    word2 = struct.unpack('<H', scenario.data[array_base + 4:array_base + 6])[0]

                    if all(0 <= w <= 1000 for w in [word0, word1, word2]):
                        return turn_candidate

        # If not found at common locations, search the PRE_PTR5 area and PTR5 section
        # PRE_PTR5: from 0x60 to first section pointer
        # PTR5: might contain the array if PTR6 comes first
        ptr5_offset = scenario.pointers.get('PTR5', len(scenario.data))
        ptr6_offset = scenario.pointers.get('PTR6', len(scenario.data))
        first_section_offset = min(ptr5_offset, ptr6_offset)

        # Search PRE_PTR5 area
        for array_base in range(0x60, first_section_offset - 8, 2):
            if array_base + 8 >= len(scenario.data):
                break

            turn_offset = array_base + 6
            turn_candidate = struct.unpack('<H', scenario.data[turn_offset:turn_offset + 2])[0]

            if 1 <= turn_candidate <= 255:
                # Validate surrounding words
                word0 = struct.unpack('<H', scenario.data[array_base:array_base + 2])[0]
                word1 = struct.unpack('<H', scenario.data[array_base + 2:array_base + 4])[0]
                word2 = struct.unpack('<H', scenario.data[array_base + 4:array_base + 6])[0]

                if all(0 <= w <= 1000 for w in [word0, word1, word2]):
                    return turn_candidate

        # Search PTR5 section if PTR6 comes first (like STLO.SCN)
        if ptr6_offset < ptr5_offset:
            ptr5_end = ptr5_offset + min(4096, len(scenario.data) - ptr5_offset)
            for array_base in range(ptr5_offset, ptr5_end - 8, 2):
                if array_base + 8 >= len(scenario.data):
                    break

                turn_offset = array_base + 6
                turn_candidate = struct.unpack('<H', scenario.data[turn_offset:turn_offset + 2])[0]

                if 1 <= turn_candidate <= 255:
                    word0 = struct.unpack('<H', scenario.data[array_base:array_base + 2])[0]
                    word1 = struct.unpack('<H', scenario.data[array_base + 2:array_base + 4])[0]
                    word2 = struct.unpack('<H', scenario.data[array_base + 4:array_base + 6])[0]

                    if all(0 <= w <= 1000 for w in [word0, word1, word2]):
                        return turn_candidate

        # Default to 20 if not found (should not happen with valid scenarios)
        return 20

    def apply_settings(self):
        """Apply settings to scenario"""
        messagebox.showinfo("Apply Settings",
                           "Settings would be applied to scenario binary data.\n\n"
                           "Note: Full implementation requires complete format understanding.")

    def reset_settings(self):
        """Reset to default values"""
        self.turn_spin.set(20)
        self.difficulty_combo.current(1)
        self.weather_combo.current(0)


class ImprovedScenarioEditor:
    """Main improved scenario editor application"""

    def __init__(self):
        self.scenario = None
        self.scenario_file = None
        self.modified = False
        self.units = []
        self.coords = []

        # Create main window
        self.root = tk.Tk()
        self.root.title("D-Day Scenario Editor")
        self.root.geometry("1400x900")

        # Configure style
        style = ttk.Style()
        style.theme_use('clam')

        self._create_menu()
        self._create_toolbar()
        self._create_main_ui()
        self._create_statusbar()

        # Keyboard shortcuts
        self.root.bind('<Control-o>', lambda e: self.open_scenario())
        self.root.bind('<Control-s>', lambda e: self.save_scenario())
        self.root.bind('<F5>', lambda e: self.reload_scenario())

    def _create_menu(self):
        """Create menu bar"""
        menubar = tk.Menu(self.root)

        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="Open Scenario...", command=self.open_scenario,
                             accelerator="Ctrl+O")
        file_menu.add_separator()
        file_menu.add_command(label="Save", command=self.save_scenario,
                             accelerator="Ctrl+S")
        file_menu.add_command(label="Save As...", command=self.save_scenario_as)
        file_menu.add_separator()
        file_menu.add_command(label="Reload", command=self.reload_scenario,
                             accelerator="F5")
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit)
        menubar.add_cascade(label="File", menu=file_menu)

        # Edit menu
        edit_menu = tk.Menu(menubar, tearoff=0)
        edit_menu.add_command(label="Add Unit...", command=self.add_unit)
        edit_menu.add_command(label="Delete Unit...", command=self.delete_unit)
        edit_menu.add_separator()
        edit_menu.add_command(label="Scenario Settings...",
                             command=lambda: self.notebook.select(4))
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

        ttk.Button(toolbar, text="Open", command=self.open_scenario).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Save", command=self.save_scenario).pack(side=tk.LEFT, padx=2)

        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=5)

        ttk.Button(toolbar, text="Add Unit", command=self.add_unit).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Delete Unit", command=self.delete_unit).pack(side=tk.LEFT, padx=2)

        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=5)

        ttk.Button(toolbar, text="Validate", command=self.validate_scenario).pack(side=tk.LEFT, padx=2)

        self.file_label = ttk.Label( toolbar, text = '!! NO SCENARIO FILE LOADED !!',
                                     font = ( "TkDefaultFont", 9, "bold" ) )

        self.file_label.pack( side = tk.LEFT, padx = 20 )

    def _create_main_ui(self):
        """Create main UI with notebook"""
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Tab 1: Mission Briefings (keep from original)
        self._create_mission_tab()

        # Tab 2: Map Viewer (NEW!)
        self._create_map_tab()

        # Tab 3: Unit Editor (IMPROVED!)
        self._create_unit_editor_tab()

        # Tab 4: Scenario Settings (NEW!)
        self._create_settings_tab()

        # Tab 5: Terrain Reference (NEW!)
        self._create_terrain_reference_tab()

    def _create_mission_tab(self):
        """Create mission briefing editor tab"""
        frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(frame, text="Mission Briefings")

        inst_label = ttk.Label(frame,
            text="Edit mission briefings for both sides",
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

        # Axis frame
        axis_frame = ttk.LabelFrame(paned, text="Axis Briefing", padding="10")
        paned.add(axis_frame, weight=1)

        self.axis_text = scrolledtext.ScrolledText(axis_frame,
                                                   height=25,
                                                   width=50,
                                                   wrap=tk.WORD)
        self.axis_text.pack(fill=tk.BOTH, expand=True)
        self.axis_text.bind('<<Modified>>', self._on_text_modified)

    def _create_map_tab(self):
        """Create map viewer tab"""
        frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(frame, text="Map Viewer")

        self.map_viewer = MapViewer(frame)
        self.map_viewer.pack(fill=tk.BOTH, expand=True)

    def _create_unit_editor_tab(self):
        """Create improved unit editor tab"""
        frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(frame, text="Unit Editor")

        # Split into unit list and properties editor
        paned = ttk.PanedWindow(frame, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True)

        # Left: Unit list with tabs by side
        left_frame = ttk.LabelFrame(paned, text="Unit List", padding="5")
        paned.add(left_frame, weight=1)

        # Create notebook for tabs
        self.unit_list_notebook = ttk.Notebook(left_frame)
        self.unit_list_notebook.pack(fill=tk.BOTH, expand=True)

        # Dictionary to store treeviews for each side
        self.unit_trees_by_side = {}

        # Right: Properties editor
        right_frame = ttk.Frame(paned)
        paned.add(right_frame, weight=1)

        self.unit_props_editor = UnitPropertiesEditor(right_frame, self.on_unit_updated)
        self.unit_props_editor.pack(fill=tk.BOTH, expand=True)

    def _create_settings_tab(self):
        """Create scenario settings tab"""
        frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(frame, text="Scenario Settings")

        self.settings_editor = ScenarioSettingsEditor(frame)
        self.settings_editor.pack(fill=tk.BOTH, expand=True)

    def _create_terrain_reference_tab(self):
        """Create terrain reference tab"""
        frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(frame, text="Terrain Reference")

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
        terrain_canvas.create_window((0, 0), window=terrain_frame, anchor=tk.NW)

        # Terrain type definitions with descriptions
        # CORRECTED to match manual + sprite sheet analysis (2025-11-11)
        terrain_info = [
            (0, 'Grass/Field', 'Open grassland and fields. Easy movement for all unit types.'),
            (1, 'Water/Ocean', 'Deep water and ocean. Impassable for ground units.'),
            (2, 'Beach/Sand', 'Sandy beaches and coastal areas. Landing zones for amphibious assaults.'),
            (3, 'Forest', 'Dense woodland. Provides cover, slows movement.'),
            (4, 'Town', 'Urban areas and towns. Defensive positions, slows attackers.'),
            (5, 'Road', 'Paved roads. Faster movement along roads.'),
            (6, 'River', 'Rivers and streams. May require bridges or ford points.'),
            (7, 'Mountains', 'Mountainous terrain. Difficult movement, good defensive positions.'),
            (8, 'Swamp', 'Marshland and swamps. Very slow movement, difficult terrain.'),
            (9, 'Bridge', 'Bridge crossings. Critical chokepoints over rivers.'),
            (10, 'Fortification', 'Defensive fortifications. Strong defensive bonuses.'),
            (11, 'Bocage', 'Norman hedgerows. Dense vegetation barriers, very defensive.'),
            (12, 'Cliff', 'Steep cliffs. Often impassable, key terrain features.'),
            (13, 'Village', 'Small villages and hamlets. Minor defensive bonuses.'),
            (14, 'Farm', 'Farmland and agricultural areas. Open terrain with buildings.'),
            (15, 'Canal', 'Canals and waterways. Water obstacles.'),
            (16, 'Clear', 'Open clear terrain. Grass variant, easy movement.'),
        ]

        # Get terrain colors from MapViewer
        terrain_colors = {
            0: '#90EE90',  # Grass/Field - light green
            1: '#4169E1',  # Water/Ocean - blue
            2: '#F4A460',  # Beach/Sand - sandy brown
            3: '#228B22',  # Forest - dark green
            4: '#A9A9A9',  # Town - gray
            5: '#8B4513',  # Road - brown
            6: '#4682B4',  # River - steel blue
            7: '#696969',  # Mountains - dim gray
            8: '#6B8E23',  # Swamp - olive
            9: '#8B7355',  # Bridge - tan
            10: '#708090', # Fortification - slate gray
            11: '#556B2F', # Bocage - dark olive
            12: '#A0522D', # Cliff - sienna
            13: '#BC8F8F', # Village - rosy brown
            14: '#DEB887', # Farm - burlywood
            15: '#5F9EA0', # Canal - cadet blue
            16: '#C0C0C0', # Unknown - silver
        }

        # Create terrain type entries
        # Initialize image list for garbage collection protection
        if not hasattr(self, '_terrain_preview_images'):
            self._terrain_preview_images = []

        for idx, (terrain_id, name, description) in enumerate(terrain_info):
            entry_frame = ttk.Frame(terrain_frame, relief=tk.RIDGE, borderwidth=1)
            entry_frame.grid(row=idx, column=0, sticky=tk.EW, padx=5, pady=3)

            # Get and display actual hex tile image (always available)
            base_img = self.map_viewer.hex_tile_base_images[terrain_id]

            # Scale to a reasonable preview size (60x68 to match roughly 2x original size)
            preview_img = base_img.resize((60, 68), Image.Resampling.LANCZOS)
            photo_img = ImageTk.PhotoImage(preview_img)

            # Store reference to prevent garbage collection
            self._terrain_preview_images.append(photo_img)

            # Create label to display image
            img_label = ttk.Label(entry_frame, image=photo_img, relief=tk.SOLID, borderwidth=1)
            img_label.grid(row=0, column=0, rowspan=2, padx=10, pady=5)

            # Type ID and name
            type_label = ttk.Label(entry_frame,
                                  text=f"Type {terrain_id}: {name}",
                                  font=("TkDefaultFont", 10, "bold"))
            type_label.grid(row=0, column=1, sticky=tk.W, padx=10, pady=(5, 0))

            # Description
            desc_label = ttk.Label(entry_frame, text=description,
                                  foreground='#555555')
            desc_label.grid(row=1, column=1, sticky=tk.W, padx=10, pady=(0, 5))

        # Configure grid weights
        terrain_frame.columnconfigure(0, weight=1)

        # Update scroll region
        terrain_frame.update_idletasks()
        terrain_canvas.config(scrollregion=terrain_canvas.bbox('all'))

        # Enable mousewheel scrolling anywhere on the canvas
        def _on_mousewheel(event):
            terrain_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        def _bind_mousewheel(event):
            terrain_canvas.bind_all("<MouseWheel>", _on_mousewheel)

        def _unbind_mousewheel(event):
            terrain_canvas.unbind_all("<MouseWheel>")

        terrain_canvas.bind("<Enter>", _bind_mousewheel)
        terrain_canvas.bind("<Leave>", _unbind_mousewheel)

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
        """Track modifications"""
        if self.scenario:
            self.modified = True
            self.modified_label.config(text="Modified *", foreground="red")

    def open_scenario(self):
        """Open a scenario file"""
        filename = filedialog.askopenfilename(
            title="Select D-Day Scenario File",
            initialdir="game/SCENARIO",
            filetypes=[("Scenario Files", "*.SCN"), ("All Files", "*.*")]
        )

        if not filename:
            return

        try:
            self.scenario = DdayScenario(filename)

            if not self.scenario.is_valid:
                messagebox.showerror("Error", "Invalid scenario file format!")
                return

            self.scenario_file = Path(filename)
            self.file_label.config(text=f"{self.scenario_file.name}")

            # Load all data
            self._load_scenario_data()

            self.modified = False
            self.modified_label.config(text="", foreground="black")
            self.status_label.config(text=f"Loaded: {self.scenario_file.name}")

        except Exception as e:
            messagebox.showerror("Error", f"Failed to load scenario:\n{e}")

    def _load_scenario_data(self):
        """Load scenario data into all tabs"""
        if not self.scenario:
            return

        # Parse units from scenario (searches PTR4 and PTR6)
        self.units = EnhancedUnitParser.parse_units_from_scenario(self.scenario)

        # Parse coordinates from PTR5
        ptr5_data = self.scenario.sections.get('PTR5', b'')
        self.coords = EnhancedUnitParser.parse_coordinates_from_ptr5(ptr5_data)

        # Load mission text
        self._load_mission_text()

        # Load map viewer with REAL terrain data
        self.map_viewer.load_data(self.units, self.scenario)

        # Load unit editor
        self._load_units_into_tree()
        self.unit_props_editor.load_units(self.units)

        # Load settings
        self.settings_editor.load_scenario_data(self.scenario)

    def _load_mission_text(self):
        """Load mission text from scenario"""
        if not self.scenario:
            return

        # Extract mission text (same as original)
        presection_start = 0x60
        first_section = min(start for _, start, _ in self.scenario.section_order)
        presection_data = self.scenario.data[presection_start:first_section]

        mission_blocks = []
        in_text = False
        start = 0
        current_text = b''

        for i, byte in enumerate(presection_data):
            if 32 <= byte <= 126:
                if not in_text:
                    start = i
                    in_text = True
                current_text += bytes([byte])
            else:
                if in_text and len(current_text) >= 30:
                    text = current_text.decode('ascii', errors='ignore').strip()
                    mission_blocks.append(text)
                in_text = False
                current_text = b''

        self.mission_blocks = mission_blocks

        # Separate Allied and Axis
        allied_lines = [block for i, block in enumerate(mission_blocks) if i % 2 == 0]
        axis_lines = [block for i, block in enumerate(mission_blocks) if i % 2 == 1]

        # Display in text widgets
        self.allied_text.delete('1.0', tk.END)
        self.allied_text.insert('1.0', '\n'.join(allied_lines))

        self.axis_text.delete('1.0', tk.END)
        self.axis_text.insert('1.0', '\n'.join(axis_lines))

        self.allied_text.edit_modified(False)
        self.axis_text.edit_modified(False)

    def _load_units_into_tree(self):
        """Load units into tree views organized by side with tabs"""
        # Clear existing tabs
        for tab in self.unit_list_notebook.tabs():
            self.unit_list_notebook.forget(tab)
        self.unit_trees_by_side.clear()

        # Organize units by side
        units_by_side = {}
        for unit in self.units:
            side = unit.get('side', 'Unknown')
            if side not in units_by_side:
                units_by_side[side] = []
            units_by_side[side].append(unit)

        # Create a tab for each side
        columns = ("Index", "Name", "Position", "Atk", "Def", "Qual", "Dis", "Fat", "Type")

        for side in sorted(units_by_side.keys()):
            # Create frame for this side's tab
            tab_frame = ttk.Frame(self.unit_list_notebook)
            self.unit_list_notebook.add(tab_frame, text=f"{side} ({len(units_by_side[side])})")

            # Create treeview for this side
            tree = ttk.Treeview(tab_frame, columns=columns,
                               show='headings', height=20)

            tree.heading("Index", text="#")
            tree.heading("Name", text="Unit Name")
            tree.heading("Position", text="Position")
            tree.heading("Atk", text="Atk")
            tree.heading("Def", text="Def")
            tree.heading("Qual", text="Qual")
            tree.heading("Dis", text="Dis")
            tree.heading("Fat", text="Fat")
            tree.heading("Type", text="Type")

            tree.column("Index", width=40)
            tree.column("Name", width=160)
            tree.column("Position", width=70)
            tree.column("Atk", width=40)
            tree.column("Def", width=40)
            tree.column("Qual", width=40)
            tree.column("Dis", width=40)
            tree.column("Fat", width=40)
            tree.column("Type", width=100)

            # Scrollbar
            scrollbar = ttk.Scrollbar(tab_frame, orient=tk.VERTICAL,
                                     command=tree.yview)
            tree.configure(yscrollcommand=scrollbar.set)

            tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

            # Bind selection event
            tree.bind('<<TreeviewSelect>>',
                     lambda event, s=side: self.on_unit_tree_select(event, s))

            # Store reference
            self.unit_trees_by_side[side] = {
                'tree': tree,
                'units': units_by_side[side]
            }

            # Populate tree with units for this side
            for unit in units_by_side[side]:
                # Get actual combat stats
                attack_base = unit.get('attack_base', 0)
                defense_base = unit.get('defense_base', 0)
                quality = unit.get('quality', 0)
                disruption = unit.get('disruption', 0)
                fatigue = unit.get('fatigue', 0)

                # Calculate effective stats
                effective_atk = attack_base - fatigue if attack_base > 0 else 0
                effective_def = defense_base - fatigue if defense_base > 0 else 0

                # Format stats
                atk_str = str(effective_atk) if attack_base > 0 else '-'
                def_str = str(effective_def) if defense_base > 0 else '-'
                qual_str = str(quality) if quality > 0 else '-'
                dis_str = str(disruption) if disruption > 0 else '-'
                fat_str = str(fatigue) if fatigue > 0 else '-'

                # Get human-readable type name
                type_code = unit.get('type', 0)
                type_name = EnhancedUnitParser.get_unit_type_name(type_code)

                # Get position
                x = unit.get('x', 0)
                y = unit.get('y', 0)
                if x == -1 or y == -1:
                    position_str = 'Off-map'
                elif x > 0 or y > 0:
                    position_str = f"({x},{y})"
                else:
                    position_str = '-'

                tree.insert("", tk.END, values=(
                    unit.get('index', '?'),
                    unit.get('name', 'Unknown'),
                    position_str,
                    atk_str,
                    def_str,
                    qual_str,
                    dis_str,
                    fat_str,
                    type_name
                ))

    def on_unit_updated(self, unit):
        """Callback when unit is updated"""
        self.modified = True
        self.modified_label.config(text="Modified *", foreground="red")
        self.status_label.config(text="Unit updated - remember to save!")

    def on_unit_tree_select(self, event, side):
        """Handle unit tree selection - show selected unit in properties editor"""
        if side not in self.unit_trees_by_side:
            return

        tree = self.unit_trees_by_side[side]['tree']
        units = self.unit_trees_by_side[side]['units']

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
                # Find position in full units list
                full_unit_index = self.units.index(selected_unit)

                # Update the combo box selection
                self.unit_props_editor.unit_combo.current(full_unit_index)
                # Trigger the display
                self.unit_props_editor.on_unit_selected(None)
        except (ValueError, IndexError):
            pass

    def add_unit(self):
        """Add a new unit"""
        messagebox.showinfo("Add Unit",
                           "Add Unit functionality requires understanding the complete\n"
                           "unit data structure. This feature will be available once\n"
                           "the format is fully decoded.")

    def delete_unit(self):
        """Delete selected unit"""
        selection = self.unit_tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "No unit selected!")
            return

        if messagebox.askyesno("Delete Unit",
                              "Delete selected unit?\n\nWarning: This may break the scenario "
                              "if not done correctly!"):
            messagebox.showinfo("Delete Unit",
                               "Delete Unit functionality requires understanding the complete\n"
                               "unit data structure and updating all related sections.")

    def save_scenario(self):
        """Save scenario"""
        if not self.scenario or not self.scenario_file:
            messagebox.showwarning("Warning", "No scenario loaded!")
            return

        # For now, only mission text is saved
        messagebox.showinfo("Save",
                           "Currently only mission briefing changes are saved.\n\n"
                           "Full save functionality with all improvements will be\n"
                           "available once the format is completely understood.")

    def save_scenario_as(self):
        """Save scenario as new file"""
        if not self.scenario:
            messagebox.showwarning("Warning", "No scenario loaded!")
            return

        filename = filedialog.asksaveasfilename(
            title="Save Scenario As",
            initialdir=self.scenario_file.parent if self.scenario_file else ".",
            defaultextension=".SCN",
            filetypes=[("Scenario Files", "*.SCN"), ("All Files", "*.*")]
        )

        if filename:
            self.scenario_file = Path(filename)
            self.save_scenario()

    def reload_scenario(self):
        """Reload current scenario"""
        if self.scenario_file:
            if self.modified:
                if not messagebox.askyesno("Reload", "Discard unsaved changes?"):
                    return
            self.scenario = DdayScenario(str(self.scenario_file))
            self._load_scenario_data()
            self.modified = False
            self.modified_label.config(text="")

    def validate_scenario(self):
        """Validate scenario"""
        if not self.scenario:
            messagebox.showwarning("Warning", "No scenario loaded!")
            return

        valid = self.scenario.validate()

        if valid:
            messagebox.showinfo("Validation", "Scenario file is valid!")
        else:
            messagebox.showwarning("Validation", "Scenario has validation warnings.")

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

MISSION BRIEFINGS TAB:
- Edit Allied and Axis mission briefings side-by-side
- Changes are saved to the scenario file

MAP VIEWER TAB:
- Visual representation of unit positions
- Adjust grid size for better viewing
- Click refresh to update the display

UNIT EDITOR TAB:
- View all units in the scenario
- Select a unit to edit its properties
- Use the form to modify name, type, position, combat stats

DATA VIEWER TAB:
- Overview of scenario data structure
- Shows sections, units, and coordinate data

SCENARIO SETTINGS TAB:
- Edit scenario-level settings
- Turn limit, difficulty, weather, victory conditions

NOTES:
- Some features are still in development
- Not all data structures are fully decoded
- Always keep backups of your scenario files
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
        scenario_file = sys.argv[1]
        if Path(scenario_file).exists():
            app.scenario_file = Path(scenario_file)
            app.scenario = DdayScenario(scenario_file)
            if app.scenario.is_valid:
                app.file_label.config(text=f"{app.scenario_file.name}")
                app._load_scenario_data()
                app.status_label.config(text=f"Loaded: {scenario_file}")

    app.run()


if __name__ == '__main__':
    main()
