#!/usr/bin/env python3
"""
D-Day Scenario Editor - Consolidated Edition
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
- Enhanced unit parsing with type names and strengths

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
from datetime import datetime
from scenario_parser import DdayScenario


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

            # Reject strings with too many special characters
            special_count = sum(1 for c in unit_name if c in '!@#$%^&*()+=[]{}|\\<>?/~`')
            if special_count > 2:  # Allow some dashes/spaces but not garbage
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
                             'Brigade', 'Artillery', 'Cavalry', 'Recon', 'Engineer']
            has_military = any(term in unit_name for term in military_terms)

            # Common unit naming patterns
            # e.g. "1-501-101", "D-70-VII", "III-5-3FJ"
            dash_pattern = r'^\d+[A-Z]?-\d+[A-Z]?-\d+[A-Z]*$|^[A-Z]-\d+-[IVX]+$|^[IVX]+-\d+-[A-Z0-9]+$'
            matches_pattern = bool(re.match(dash_pattern, unit_name))

            # "101st", "82nd", "3rd" style
            ordinal_pattern = r'\d+(st|nd|rd|th)\b'
            has_ordinal = bool(re.search(ordinal_pattern, unit_name))

            if has_number or has_roman or has_military or matches_pattern or has_ordinal:
                # Get surrounding binary context for stats
                context_start = max(0, match.start() - 32)
                context_end = min(len(data), match.end() + 32)
                context = data[context_start:context_end]

                # Try to extract stats from binary data before the name
                # Common pattern: bytes at offset -16 to -1 before name
                strength = 0
                unit_type = 0
                x = 0
                y = 0
                side = 'Unknown'

                if match.start() >= 64:
                    # Look at bytes before the unit name
                    # Unit type is at offset -27 (27 bytes before name)
                    # Strength is a 16-bit value at offset -64 (64 bytes before name)
                    # Coordinates are at offset -58 (X) and -56 (Y)
                    pre_data = data[match.start()-64:match.start()]

                    # Extract unit type from byte at position -27
                    if len(pre_data) >= 27:
                        unit_type = pre_data[-27]

                    # Extract strength as 16-bit little-endian value at position -64
                    if len(pre_data) >= 64:
                        strength = struct.unpack('<H', pre_data[-64:-62])[0]
                        # Sanity check - reasonable strength values are 1-500
                        if strength > 500:
                            strength = 0

                    # Extract coordinates from offset -58 (X) and -56 (Y)
                    if len(pre_data) >= 58:
                        x = struct.unpack('<H', pre_data[-58:-56])[0]
                    if len(pre_data) >= 56:
                        y = struct.unpack('<H', pre_data[-56:-54])[0]

                    # Validate coordinates (D-Day map is 125x100)
                    if x > 125 or y > 100:
                        x = 0
                        y = 0

                # Determine side based on naming patterns
                german_terms = ['Panzer', 'Grenadier', 'Ost', 'FJ', 'Flak', 'Sturm',
                               'Jager', 'Kampf', 'Schnelle', 'Korps', 'Luftwaffe', 'Festung']
                is_german = any(term in unit_name for term in german_terms)

                # Check for numbered US divisions/corps
                us_pattern = r'\d+(st|nd|rd|th)\s+(Infantry|Airborne|Armored|Cavalry)'
                is_us = bool(re.search(us_pattern, unit_name))

                # VII Corps, VIII Corps style
                us_corps = bool(re.search(r'(VII|VIII|V|XIX)\s+Corps', unit_name))

                if is_german:
                    side = 'Axis'
                elif is_us or us_corps:
                    side = 'Allied'
                elif has_military:
                    # Most military terms without German identifiers are Allied in D-Day scenarios
                    side = 'Allied'

                units.append({
                    'index': unit_index,
                    'name': unit_name,
                    'type': unit_type,
                    'strength': strength,
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

    # Map constants
    MAP_WIDTH = 125  # hexes
    MAP_HEIGHT = 100  # hexes
    HEX_SIZE = 12    # initial hex radius in pixels

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

        # Colors
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

        self._create_ui()
        self._bind_events()

    def _create_ui(self):
        """Create map viewer UI"""
        # Control panel
        control_frame = ttk.Frame(self)
        control_frame.pack(fill=tk.X, padx=5, pady=5)

        ttk.Label(control_frame, text="Map Viewer (125×100 hex grid)",
                 font=("TkDefaultFont", 9, "bold")).pack(side=tk.LEFT, padx=5)

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

        h_scroll.config(command=self.canvas.xview)
        v_scroll.config(command=self.canvas.yview)

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

        self.drag_start_x = 0
        self.drag_start_y = 0

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

        if 0 <= hex_x < self.MAP_WIDTH and 0 <= hex_y < self.MAP_HEIGHT:
            terrain = self.terrain.get((hex_x, hex_y), 0)
            self.status_label.config(
                text=f"Hex: ({hex_x}, {hex_y}) | Terrain: {terrain}")
        else:
            self.status_label.config(text="Outside map bounds")

    def _on_mousewheel(self, event):
        """Zoom with mouse wheel"""
        if event.delta > 0:
            self.zoom_in()
        else:
            self.zoom_out()

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

    def load_data(self, units, coords):
        """Load map data - units is list of unit dicts from EnhancedUnitParser"""
        self.units = units if units else []

        # Note: Terrain data is not currently available in scenario files
        # The map shows a neutral background with unit positions marked
        self.terrain = {}

        # Count units with valid positions
        units_with_pos = sum(1 for u in self.units if u.get('x', 0) > 0 and u.get('y', 0) > 0)

        self.status_label.config(
            text=f"Loaded {len(self.units)} units ({units_with_pos} with positions)")
        self.redraw()

    def redraw(self):
        """Redraw the entire map"""
        self.canvas.delete('all')

        self.show_grid = self.grid_var.get()
        self.show_coords = self.coords_var.get()

        # Update info
        zoom_pct = int(self.hex_size / self.HEX_SIZE * 100)
        self.info_label.config(text=f"Zoom: {zoom_pct}% | Hexes: {self.MAP_WIDTH}×{self.MAP_HEIGHT}")

        # Draw only visible hexes for performance
        visible_hexes = self._get_visible_hexes()

        # Draw terrain (background grid)
        for hex_y in range(visible_hexes['min_y'], visible_hexes['max_y']):
            for hex_x in range(visible_hexes['min_x'], visible_hexes['max_x']):
                if 0 <= hex_x < self.MAP_WIDTH and 0 <= hex_y < self.MAP_HEIGHT:
                    self._draw_hex_tile(hex_x, hex_y)

        # Draw units at their actual positions
        for unit in self.units:
            # Get actual coordinates from unit data
            hex_x = unit.get('x', 0)
            hex_y = unit.get('y', 0)

            # Only draw units with valid coordinates
            if hex_x > 0 and hex_y > 0 and hex_x < self.MAP_WIDTH and hex_y < self.MAP_HEIGHT:
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
            'max_x': min(self.MAP_WIDTH, max_x + padding),
            'min_y': max(0, min_y - padding),
            'max_y': min(self.MAP_HEIGHT, max_y + padding)
        }

    def _draw_hex_tile(self, hex_x, hex_y):
        """Draw a single hex tile"""
        px, py = self.hex_to_pixel(hex_x, hex_y)

        # Get terrain color
        terrain_type = self.terrain.get((hex_x, hex_y), 0)
        color = self.terrain_colors.get(terrain_type, '#FFFFFF')

        # Draw hexagon
        outline_color = '#666666' if self.show_grid else color
        self.draw_hexagon(px, py, self.hex_size, fill=color, outline=outline_color)

        # Draw coordinates if enabled
        if self.show_coords and self.hex_size >= 10:
            self.canvas.create_text(px, py,
                                   text=f"{hex_x},{hex_y}",
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
        max_x = self.MAP_WIDTH * self.hex_size * math.sqrt(3) + self.offset_x + 100
        max_y = self.MAP_HEIGHT * self.hex_size * 1.5 + self.offset_y + 100

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

        # Type
        ttk.Label(form_frame, text="Type:").grid(row=1, column=0, sticky=tk.W, pady=3)
        self.type_entry = ttk.Entry(form_frame, width=30)
        self.type_entry.grid(row=1, column=1, sticky=tk.W, pady=3, padx=5)

        # Position X
        ttk.Label(form_frame, text="Position X:").grid(row=2, column=0, sticky=tk.W, pady=3)
        self.pos_x_spin = ttk.Spinbox(form_frame, from_=0, to=500, width=10)
        self.pos_x_spin.grid(row=2, column=1, sticky=tk.W, pady=3, padx=5)

        # Position Y
        ttk.Label(form_frame, text="Position Y:").grid(row=3, column=0, sticky=tk.W, pady=3)
        self.pos_y_spin = ttk.Spinbox(form_frame, from_=0, to=500, width=10)
        self.pos_y_spin.grid(row=3, column=1, sticky=tk.W, pady=3, padx=5)

        # Strength
        ttk.Label(form_frame, text="Strength:").grid(row=4, column=0, sticky=tk.W, pady=3)
        self.strength_spin = ttk.Spinbox(form_frame, from_=0, to=100, width=10)
        self.strength_spin.grid(row=4, column=1, sticky=tk.W, pady=3, padx=5)
        self.strength_spin.set(100)

        # Side (Allied/Axis)
        ttk.Label(form_frame, text="Side:").grid(row=5, column=0, sticky=tk.W, pady=3)
        self.side_combo = ttk.Combobox(form_frame, width=15, state='readonly',
                                       values=['Allied', 'Axis'])
        self.side_combo.grid(row=5, column=1, sticky=tk.W, pady=3, padx=5)
        self.side_combo.current(0)

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

        # For now, use placeholder positions
        # In real implementation, parse from PTR4/PTR5
        self.pos_x_spin.set(0)
        self.pos_y_spin.set(0)

        # Set strength from unit data
        strength = self.current_unit.get('strength', 0)
        if strength > 0:
            self.strength_spin.set(strength)
        else:
            self.strength_spin.set(100)  # Default

        # Display raw data
        self.raw_text.delete('1.0', tk.END)
        self.raw_text.insert('1.0', f"Section: {self.current_unit.get('section', 'Unknown')}\n")
        self.raw_text.insert('1.0', f"Offset: 0x{self.current_unit.get('offset', 0):06x}\n")
        self.raw_text.insert(tk.END, f"Type: {self.current_unit.get('type', 0)}\n")
        self.raw_text.insert(tk.END, f"Strength (parsed): {strength}\n")
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

        # Notify callback
        if self.on_unit_update_callback:
            self.on_unit_update_callback(self.current_unit)

        messagebox.showinfo("Success", "Unit properties updated!\n\n"
                           "Note: Some changes may require scenario reload to take effect.")

    def revert_changes(self):
        """Revert changes to current unit"""
        self.display_unit()


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
        # Placeholder - would parse from scenario data
        self.name_entry.delete(0, tk.END)
        self.name_entry.insert(0, scenario.filename.stem if scenario else "Unknown")

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
        self.root.title("D-Day Scenario Editor - Consolidated Edition")
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

        # File info
        self.file_label = ttk.Label(toolbar, text="No file loaded",
                                    font=("TkDefaultFont", 9, "bold"))
        self.file_label.pack(side=tk.LEFT, padx=20)

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

        # Tab 4: Data Viewer (simplified)
        self._create_data_tab()

        # Tab 5: Scenario Settings (NEW!)
        self._create_settings_tab()

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

        # Left: Unit list
        left_frame = ttk.LabelFrame(paned, text="Unit List", padding="5")
        paned.add(left_frame, weight=1)

        columns = ("Index", "Name", "Side", "Position", "Strength", "Type")
        self.unit_tree = ttk.Treeview(left_frame, columns=columns,
                                      show='headings', height=20)

        self.unit_tree.heading("Index", text="#")
        self.unit_tree.heading("Name", text="Unit Name")
        self.unit_tree.heading("Side", text="Side")
        self.unit_tree.heading("Position", text="Position")
        self.unit_tree.heading("Strength", text="Str")
        self.unit_tree.heading("Type", text="Type")

        self.unit_tree.column("Index", width=40)
        self.unit_tree.column("Name", width=180)
        self.unit_tree.column("Side", width=60)
        self.unit_tree.column("Position", width=70)
        self.unit_tree.column("Strength", width=50)
        self.unit_tree.column("Type", width=100)

        scrollbar = ttk.Scrollbar(left_frame, orient=tk.VERTICAL,
                                 command=self.unit_tree.yview)
        self.unit_tree.configure(yscrollcommand=scrollbar.set)

        self.unit_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Bind selection event to show unit stats
        self.unit_tree.bind('<<TreeviewSelect>>', self.on_unit_tree_select)

        # Right: Properties editor
        right_frame = ttk.Frame(paned)
        paned.add(right_frame, weight=1)

        self.unit_props_editor = UnitPropertiesEditor(right_frame, self.on_unit_updated)
        self.unit_props_editor.pack(fill=tk.BOTH, expand=True)

    def _create_data_tab(self):
        """Create data viewer tab"""
        frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(frame, text="Data Viewer")

        ttk.Label(frame, text="Scenario Data Overview",
                 font=("TkDefaultFont", 10, "bold")).pack(pady=5)

        self.data_text = scrolledtext.ScrolledText(frame, font=("Courier", 10),
                                                   width=80, height=30)
        self.data_text.pack(fill=tk.BOTH, expand=True)

    def _create_settings_tab(self):
        """Create scenario settings tab"""
        frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(frame, text="Scenario Settings")

        self.settings_editor = ScenarioSettingsEditor(frame)
        self.settings_editor.pack(fill=tk.BOTH, expand=True)

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

        # Load map viewer
        self.map_viewer.load_data(self.units, self.coords)

        # Load unit editor
        self._load_units_into_tree()
        self.unit_props_editor.load_units(self.units)

        # Load data viewer
        self._load_data_overview()

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
        """Load units into the tree view"""
        # Clear existing
        for item in self.unit_tree.get_children():
            self.unit_tree.delete(item)

        # Add units
        for unit in self.units:
            strength = unit.get('strength', 0)
            strength_str = str(strength) if strength > 0 else '-'

            # Get human-readable type name
            type_code = unit.get('type', 0)
            type_name = EnhancedUnitParser.get_unit_type_name(type_code)

            # Get position
            x = unit.get('x', 0)
            y = unit.get('y', 0)
            position_str = f"({x},{y})" if x > 0 and y > 0 else '-'

            # Get side
            side = unit.get('side', 'Unknown')

            self.unit_tree.insert("", tk.END, values=(
                unit.get('index', '?'),
                unit.get('name', 'Unknown'),
                side,
                position_str,
                strength_str,
                type_name
            ))

    def _load_data_overview(self):
        """Load data overview"""
        if not self.scenario:
            return

        self.data_text.delete('1.0', tk.END)

        # Basic info
        self.data_text.insert(tk.END, f"=== Scenario: {self.scenario_file.name} ===\n\n")
        self.data_text.insert(tk.END, f"File Size: {len(self.scenario.data):,} bytes\n")
        self.data_text.insert(tk.END, f"Valid: {self.scenario.is_valid}\n\n")

        # Sections
        self.data_text.insert(tk.END, "Data Sections:\n")
        for name, start, end in self.scenario.section_order:
            size = end - start
            self.data_text.insert(tk.END,
                f"  {name}: 0x{start:06x}-0x{end:06x} ({size:,} bytes)\n")

        self.data_text.insert(tk.END, f"\nUnits Found: {len(self.units)}\n")
        self.data_text.insert(tk.END, f"Coordinates: {len(self.coords)}\n")

        # Coordinate summary
        if self.coords:
            self.data_text.insert(tk.END, "\n=== Coordinate Data Sample ===\n")
            for coord in self.coords[:20]:
                self.data_text.insert(tk.END,
                    f"  Offset 0x{coord['offset']:04x}: {coord['value']:5d} "
                    f"({coord['interpretation']})\n")

    def on_unit_updated(self, unit):
        """Callback when unit is updated"""
        self.modified = True
        self.modified_label.config(text="Modified *", foreground="red")
        self.status_label.config(text="Unit updated - remember to save!")

    def on_unit_tree_select(self, event):
        """Handle unit tree selection - show selected unit in properties editor"""
        selection = self.unit_tree.selection()
        if not selection:
            return

        # Get the selected item
        item = selection[0]
        values = self.unit_tree.item(item, 'values')

        if not values:
            return

        # Extract unit index from the first column
        try:
            unit_index = int(values[0])  # Index is in the first column

            # Update the unit properties editor to show this unit
            if 0 <= unit_index < len(self.units):
                # Update the combo box selection
                self.unit_props_editor.unit_combo.current(unit_index)
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
- Use the form to modify name, type, position, strength

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
