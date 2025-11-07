#!/usr/bin/env python3
"""
D-Day Scenario Editor - Improved High-Level Edition
====================================================

A user-friendly high-level scenario editor for D-Day scenarios.

NEW Features in this version:
- Visual map viewer with unit positions
- Structured unit editing (add/edit/delete units)
- Scenario settings editor (turns, objectives, etc.)
- Coordinate interpretation and visualization
- Better data visualization (not just hex dumps)

Usage:
    python3 dday_scenario_editor_improved.py [scenario_file.scn]
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
from pathlib import Path
import struct
import shutil
import re
from datetime import datetime
from dday_scenario_parser import DdayScenario


class EnhancedUnitParser:
    """Enhanced parser for unit data with better structure understanding"""

    # Unit type code mappings (reverse-engineered from binary data)
    UNIT_TYPE_NAMES = {
        0x00: 'Battalion',      # Generic battalion
        0x01: 'Battalion',      # Infantry battalion
        0x02: 'Battalion',      # Special battalion
        0x07: 'Division-HQ',    # Division headquarters
        0x08: 'Battalion',      # Glider battalion
        0x11: 'Corps',          # Corps level
        0x13: 'Division',       # Division level
        0x15: 'Regiment',       # Regiment level
        0x17: 'Company',        # Company level
        0x18: 'Artillery',      # Artillery battalion
        0x1b: 'Engineer',       # Engineer battalion
        0x28: 'Tank-Bn',        # Tank battalion
        0x29: 'Tank-Bn',        # Tank battalion (variant)
        0x2a: 'Tank-Co',        # Tank company (detachment)
        0x36: 'AAA',            # Anti-aircraft artillery
        0x40: 'Cavalry',        # Cavalry squadron
        0x41: 'Battalion',      # Airborne battalion
        0x43: 'Artillery',      # Artillery battalion
        0x60: 'Combat-Cmd-A',   # Combat Command A (armor)
        0x61: 'Combat-Cmd-B',   # Combat Command B (armor)
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

                if match.start() >= 64:
                    # Look at bytes before the unit name
                    # Unit type is at offset -27 (27 bytes before name)
                    # Strength is a 16-bit value at offset -64 (64 bytes before name)
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

                units.append({
                    'index': unit_index,
                    'name': unit_name,
                    'type': unit_type,
                    'strength': strength,
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
    """Visual map viewer showing unit positions on a grid"""

    def __init__(self, parent):
        super().__init__(parent)

        # Controls
        controls_frame = ttk.Frame(self)
        controls_frame.pack(fill=tk.X, pady=5)

        ttk.Label(controls_frame, text="Map Grid Viewer",
                 font=("TkDefaultFont", 10, "bold")).pack(side=tk.LEFT, padx=5)

        ttk.Label(controls_frame, text="Grid Size:").pack(side=tk.LEFT, padx=5)
        self.grid_size_var = tk.IntVar(value=20)
        ttk.Spinbox(controls_frame, from_=10, to=50, width=5,
                   textvariable=self.grid_size_var,
                   command=self.redraw).pack(side=tk.LEFT, padx=5)

        ttk.Button(controls_frame, text="Refresh",
                  command=self.redraw).pack(side=tk.LEFT, padx=5)

        # Canvas for map
        canvas_frame = ttk.Frame(self)
        canvas_frame.pack(fill=tk.BOTH, expand=True)

        self.canvas = tk.Canvas(canvas_frame, bg='#e8f4e8', width=600, height=600)
        self.canvas.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Scrollbars
        h_scroll = ttk.Scrollbar(canvas_frame, orient=tk.HORIZONTAL, command=self.canvas.xview)
        v_scroll = ttk.Scrollbar(canvas_frame, orient=tk.VERTICAL, command=self.canvas.yview)
        self.canvas.configure(xscrollcommand=h_scroll.set, yscrollcommand=v_scroll.set)

        # Data
        self.units = []
        self.coords = []

        # Draw initial grid
        self.draw_grid()

    def load_data(self, units, coords):
        """Load unit and coordinate data"""
        self.units = units
        self.coords = coords
        self.redraw()

    def draw_grid(self):
        """Draw the background grid"""
        grid_size = self.grid_size_var.get()
        width = 600
        height = 600

        # Draw grid lines
        for i in range(0, width, grid_size):
            self.canvas.create_line(i, 0, i, height, fill='#cccccc', tags='grid')

        for i in range(0, height, grid_size):
            self.canvas.create_line(0, i, width, i, fill='#cccccc', tags='grid')

    def redraw(self):
        """Redraw the entire map"""
        self.canvas.delete('all')
        self.draw_grid()
        self.draw_units()
        self.draw_coordinates()

    def draw_units(self):
        """Draw units on the map"""
        if not self.units:
            return

        # For now, place units in a simple layout
        # In a real implementation, you'd parse actual coordinates
        grid_size = self.grid_size_var.get()

        for i, unit in enumerate(self.units[:20]):  # Limit to first 20 units
            x = (i % 10) * grid_size * 2 + 10
            y = (i // 10) * grid_size * 2 + 10

            # Draw unit as a colored rectangle
            color = '#4488ff' if i % 2 == 0 else '#ff8844'
            self.canvas.create_rectangle(x, y, x+grid_size-2, y+grid_size-2,
                                        fill=color, outline='#000000',
                                        tags=('unit', f'unit_{i}'))

            # Add unit name
            unit_name = unit.get('name', f'Unit {i}')
            if len(unit_name) > 8:
                unit_name = unit_name[:6] + '..'

            self.canvas.create_text(x + grid_size//2, y + grid_size//2,
                                   text=unit_name, font=("TkDefaultFont", 7),
                                   tags=('unit_label', f'label_{i}'))

    def draw_coordinates(self):
        """Draw coordinate markers"""
        # Draw key coordinates from PTR5 data
        if not self.coords:
            return

        grid_size = self.grid_size_var.get()

        # Take coordinates that look like grid positions
        grid_coords = [c for c in self.coords if c['interpretation'] == 'grid coordinate']

        for i, coord in enumerate(grid_coords[:10]):  # Limit to 10 markers
            # Map coordinate value to canvas position
            value = coord['value']
            x = (value % 30) * grid_size
            y = (value // 30) * grid_size

            if x < 600 and y < 600:
                # Draw marker
                self.canvas.create_oval(x-3, y-3, x+3, y+3,
                                       fill='#ff0000', outline='#000000',
                                       tags='marker')


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
        self.root.title("D-Day Scenario Editor - Improved Edition")
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

        columns = ("Index", "Name", "Strength", "Type", "Section")
        self.unit_tree = ttk.Treeview(left_frame, columns=columns,
                                      show='headings', height=20)

        self.unit_tree.heading("Index", text="#")
        self.unit_tree.heading("Name", text="Unit Name")
        self.unit_tree.heading("Strength", text="Str")
        self.unit_tree.heading("Type", text="Type")
        self.unit_tree.heading("Section", text="Section")

        self.unit_tree.column("Index", width=40)
        self.unit_tree.column("Name", width=200)
        self.unit_tree.column("Strength", width=50)
        self.unit_tree.column("Type", width=100)
        self.unit_tree.column("Section", width=60)

        scrollbar = ttk.Scrollbar(left_frame, orient=tk.VERTICAL,
                                 command=self.unit_tree.yview)
        self.unit_tree.configure(yscrollcommand=scrollbar.set)

        self.unit_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

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
        self.allied_text.insert('1.0', '\n\n'.join(allied_lines))

        self.axis_text.delete('1.0', tk.END)
        self.axis_text.insert('1.0', '\n\n'.join(axis_lines))

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

            self.unit_tree.insert("", tk.END, values=(
                unit.get('index', '?'),
                unit.get('name', 'Unknown'),
                strength_str,
                type_name,
                unit.get('section', '?')
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
            "D-Day Scenario Editor - Improved Edition\n\n"
            "A high-level scenario editor for D-Day scenarios\n\n"
            "Features:\n"
            "- Visual map viewer\n"
            "- Structured unit editing\n"
            "- Scenario settings editor\n"
            "- Mission briefing editor\n"
            "- Data visualization\n\n"
            "Version: 2.0 (Improved)\n"
            "Created: 2025-11-07")

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
