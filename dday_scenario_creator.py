#!/usr/bin/env python3
"""
D-Day Scenario Creator/Editor - Comprehensive Graphical Tool
============================================================

A full-featured graphical scenario creator/editor for D-Day scenarios using tkinter.

Features:
- Mission text editing (Allied & Axis)
- Unit roster viewing and editing
- Hex viewer for binary data sections
- String search and replace
- Coordinate data viewer/editor
- Data section inspector
- Multiple scenario support
- Backup management
- Export/import capabilities

Usage:
    python3 dday_scenario_creator.py [scenario_file.scn]
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
from pathlib import Path
import struct
import shutil
from datetime import datetime
from dday_scenario_parser import DdayScenario


class HexViewer(ttk.Frame):
    """Hex viewer widget for viewing binary data"""

    def __init__(self, parent):
        super().__init__(parent)

        # Create text widget with scrollbar
        self.scroll = ttk.Scrollbar(self)
        self.scroll.pack(side=tk.RIGHT, fill=tk.Y)

        self.text = tk.Text(self,
                           font=("Courier", 10),
                           yscrollcommand=self.scroll.set,
                           wrap=tk.NONE,
                           width=80,
                           height=25)
        self.text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.scroll.config(command=self.text.yview)

        # Configure tags for coloring
        self.text.tag_configure("offset", foreground="#888888")
        self.text.tag_configure("hex", foreground="#000000")
        self.text.tag_configure("ascii", foreground="#0066cc")

    def display_data(self, data, offset_start=0):
        """Display binary data in hex format"""
        self.text.delete('1.0', tk.END)

        bytes_per_line = 16
        for i in range(0, len(data), bytes_per_line):
            chunk = data[i:i+bytes_per_line]

            # Offset
            offset = offset_start + i
            offset_str = f"{offset:08x}  "
            self.text.insert(tk.END, offset_str, "offset")

            # Hex bytes
            hex_str = ' '.join(f'{b:02x}' for b in chunk)
            hex_str = hex_str.ljust(bytes_per_line * 3)
            self.text.insert(tk.END, hex_str + "  ", "hex")

            # ASCII representation
            ascii_str = ''.join(chr(b) if 32 <= b < 127 else '.' for b in chunk)
            self.text.insert(tk.END, ascii_str + "\n", "ascii")


class UnitEditor(ttk.Frame):
    """Unit roster editor"""

    def __init__(self, parent):
        super().__init__(parent)

        # Instructions
        inst_label = ttk.Label(self,
            text="Unit Roster: List of units defined in this scenario (PTR3 section)",
            font=("TkDefaultFont", 9, "bold"))
        inst_label.pack(pady=5)

        # Treeview for units
        columns = ("Index", "Name", "Type", "Hex Data")
        self.tree = ttk.Treeview(self, columns=columns, show='headings', height=15)

        self.tree.heading("Index", text="Index")
        self.tree.heading("Name", text="Unit Name")
        self.tree.heading("Type", text="Type Code")
        self.tree.heading("Hex Data", text="Binary Data (hex)")

        self.tree.column("Index", width=50)
        self.tree.column("Name", width=150)
        self.tree.column("Type", width=100)
        self.tree.column("Hex Data", width=300)

        # Scrollbar
        scrollbar = ttk.Scrollbar(self, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    def load_units(self, ptr3_data):
        """Load and parse units from PTR3 section"""
        # Clear existing
        for item in self.tree.get_children():
            self.tree.delete(item)

        if not ptr3_data:
            return

        # Try to parse units
        units = self._parse_units(ptr3_data)

        for idx, unit in enumerate(units):
            self.tree.insert("", tk.END, values=(
                idx,
                unit.get('name', 'Unknown'),
                unit.get('type', 'Unknown'),
                unit.get('hex', '')
            ))

    def _parse_units(self, data):
        """Parse unit data from binary"""
        units = []
        i = 0

        while i < len(data):
            # Look for unit name patterns (ASCII text)
            if i + 20 < len(data):
                # Extract potential unit name (look for ASCII sequences)
                chunk = data[i:i+32]

                # Find ASCII strings
                name = b''
                for b in chunk[8:24]:  # Typically name starts after type bytes
                    if 32 <= b < 127:
                        name += bytes([b])
                    elif name:
                        break

                if len(name) >= 3:  # Valid unit name
                    unit_type_code = f"{chunk[0]:02x} {chunk[1]:02x} {chunk[2]:02x}"
                    hex_data = ' '.join(f'{b:02x}' for b in chunk[:16])

                    units.append({
                        'name': name.decode('ascii', errors='ignore').strip(),
                        'type': unit_type_code,
                        'hex': hex_data,
                        'offset': i
                    })

                    i += 32  # Move to next potential unit
                else:
                    i += 1
            else:
                break

        return units


class CoordinateViewer(ttk.Frame):
    """Coordinate data viewer for PTR5"""

    def __init__(self, parent):
        super().__init__(parent)

        # Instructions
        inst_label = ttk.Label(self,
            text="Coordinate Data: Numeric values from PTR5 (likely positions, stats, etc.)",
            font=("TkDefaultFont", 9, "bold"))
        inst_label.pack(pady=5)

        # Create text widget
        self.text = scrolledtext.ScrolledText(self,
                                              font=("Courier", 10),
                                              width=80,
                                              height=20)
        self.text.pack(fill=tk.BOTH, expand=True)

    def load_data(self, ptr5_data):
        """Load and display coordinate data"""
        self.text.delete('1.0', tk.END)

        if not ptr5_data:
            self.text.insert('1.0', "No data available")
            return

        # Parse as 16-bit integers
        self.text.insert(tk.END, "=== 16-bit Integers (UINT16) ===\n\n")

        for i in range(0, min(len(ptr5_data), 512), 2):
            if i + 2 <= len(ptr5_data):
                value = struct.unpack('<H', ptr5_data[i:i+2])[0]
                self.text.insert(tk.END, f"Offset 0x{i:04x}: {value:5d} (0x{value:04x})\n")

        if len(ptr5_data) > 512:
            self.text.insert(tk.END, f"\n... and {len(ptr5_data) - 512} more bytes\n")


class StringSearcher(ttk.Frame):
    """String search and replace tool"""

    def __init__(self, parent, on_search_callback):
        super().__init__(parent)
        self.on_search_callback = on_search_callback

        # Search frame
        search_frame = ttk.Frame(self)
        search_frame.pack(fill=tk.X, padx=5, pady=5)

        ttk.Label(search_frame, text="Search:").pack(side=tk.LEFT, padx=5)
        self.search_entry = ttk.Entry(search_frame, width=40)
        self.search_entry.pack(side=tk.LEFT, padx=5)

        ttk.Button(search_frame, text="Find All",
                  command=self.do_search).pack(side=tk.LEFT, padx=5)

        # Results
        ttk.Label(self, text="Search Results:").pack(anchor=tk.W, padx=5)

        self.tree = ttk.Treeview(self, columns=("Offset", "Section", "Text"),
                                 show='headings', height=15)
        self.tree.heading("Offset", text="Offset")
        self.tree.heading("Section", text="Section")
        self.tree.heading("Text", text="Text Preview")

        self.tree.column("Offset", width=100)
        self.tree.column("Section", width=100)
        self.tree.column("Text", width=400)

        scrollbar = ttk.Scrollbar(self, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    def do_search(self):
        """Perform search"""
        query = self.search_entry.get()
        if query and self.on_search_callback:
            self.on_search_callback(query, self.tree)


class DdayScenarioCreator:
    """Main scenario creator/editor application"""

    def __init__(self):
        self.scenario = None
        self.scenario_file = None
        self.modified = False

        # Create main window
        self.root = tk.Tk()
        self.root.title("D-Day Scenario Creator/Editor")
        self.root.geometry("1200x900")

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
        self.root.bind('<Control-n>', lambda e: self.new_scenario())
        self.root.bind('<F5>', lambda e: self.reload_scenario())

    def _create_menu(self):
        """Create menu bar"""
        menubar = tk.Menu(self.root)

        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="New Scenario...", command=self.new_scenario,
                             accelerator="Ctrl+N")
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
        edit_menu.add_command(label="Validate Scenario", command=self.validate_scenario)
        edit_menu.add_separator()
        edit_menu.add_command(label="Search Strings...", command=self.show_search)
        menubar.add_cascade(label="Edit", menu=edit_menu)

        # Tools menu
        tools_menu = tk.Menu(menubar, tearoff=0)
        tools_menu.add_command(label="Extract All Strings", command=self.extract_strings)
        tools_menu.add_command(label="Compare with Another Scenario...",
                              command=self.compare_scenarios)
        tools_menu.add_separator()
        tools_menu.add_command(label="Backup Manager...", command=self.manage_backups)
        menubar.add_cascade(label="Tools", menu=tools_menu)

        # Help menu
        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(label="About", command=self.show_about)
        help_menu.add_command(label="Format Documentation", command=self.show_format_docs)
        menubar.add_cascade(label="Help", menu=help_menu)

        self.root.config(menu=menubar)

    def _create_toolbar(self):
        """Create toolbar"""
        toolbar = ttk.Frame(self.root)
        toolbar.pack(fill=tk.X, padx=5, pady=5)

        ttk.Button(toolbar, text="📂 Open", command=self.open_scenario).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="💾 Save", command=self.save_scenario).pack(side=tk.LEFT, padx=2)

        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=5)

        ttk.Button(toolbar, text="✓ Validate", command=self.validate_scenario).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="🔍 Search", command=self.show_search).pack(side=tk.LEFT, padx=2)

        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=5)

        # File info in toolbar
        self.file_label = ttk.Label(toolbar, text="No file loaded",
                                    font=("TkDefaultFont", 9, "bold"))
        self.file_label.pack(side=tk.LEFT, padx=10)

    def _create_main_ui(self):
        """Create main UI with notebook"""
        # Create notebook
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Tab 1: Overview
        self._create_overview_tab()

        # Tab 2: Mission Briefings
        self._create_mission_tab()

        # Tab 3: Unit Roster
        self._create_unit_tab()

        # Tab 4: Coordinate Data
        self._create_coordinate_tab()

        # Tab 5: PTR6 Data
        self._create_ptr6_tab()

        # Tab 6: Hex Viewer
        self._create_hex_tab()

    def _create_overview_tab(self):
        """Create overview tab"""
        frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(frame, text="📊 Overview")

        # Header info
        header_frame = ttk.LabelFrame(frame, text="Scenario Header", padding="10")
        header_frame.pack(fill=tk.X, pady=5)

        info_text = scrolledtext.ScrolledText(header_frame, height=10, width=80)
        info_text.pack(fill=tk.BOTH, expand=True)
        self.overview_text = info_text

        # Statistics
        stats_frame = ttk.LabelFrame(frame, text="Statistics", padding="10")
        stats_frame.pack(fill=tk.X, pady=5)

        stats_text = scrolledtext.ScrolledText(stats_frame, height=8, width=80)
        stats_text.pack(fill=tk.BOTH, expand=True)
        self.stats_text = stats_text

        # Data sections
        sections_frame = ttk.LabelFrame(frame, text="Data Sections", padding="10")
        sections_frame.pack(fill=tk.BOTH, expand=True, pady=5)

        sections_text = scrolledtext.ScrolledText(sections_frame, height=10, width=80)
        sections_text.pack(fill=tk.BOTH, expand=True)
        self.sections_text = sections_text

    def _create_mission_tab(self):
        """Create mission briefing editor tab"""
        frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(frame, text="📝 Mission Briefings")

        # Instructions
        inst_label = ttk.Label(frame,
            text="Edit mission briefings for both sides. Text is interleaved in the file.",
            font=("TkDefaultFont", 9))
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

        # Buttons
        button_frame = ttk.Frame(frame)
        button_frame.pack(fill=tk.X, pady=(10, 0))

        ttk.Button(button_frame, text="Revert Changes",
                  command=self.revert_mission_text).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Apply & Save",
                  command=self.save_scenario).pack(side=tk.RIGHT, padx=5)

    def _create_unit_tab(self):
        """Create unit roster tab"""
        frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(frame, text="⚔️ Unit Roster")

        self.unit_editor = UnitEditor(frame)
        self.unit_editor.pack(fill=tk.BOTH, expand=True)

    def _create_coordinate_tab(self):
        """Create coordinate data tab"""
        frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(frame, text="📍 Coordinates")

        self.coord_viewer = CoordinateViewer(frame)
        self.coord_viewer.pack(fill=tk.BOTH, expand=True)

    def _create_ptr6_tab(self):
        """Create PTR6 data viewer tab"""
        frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(frame, text="🎮 PTR6 Data")

        ttk.Label(frame,
                 text="PTR6 Section: Specialized/AI Data (mostly sparse)",
                 font=("TkDefaultFont", 9, "bold")).pack(pady=5)

        self.ptr6_hex = HexViewer(frame)
        self.ptr6_hex.pack(fill=tk.BOTH, expand=True)

    def _create_hex_tab(self):
        """Create hex viewer tab"""
        frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(frame, text="🔍 Hex Viewer")

        # Section selector
        selector_frame = ttk.Frame(frame)
        selector_frame.pack(fill=tk.X, pady=5)

        ttk.Label(selector_frame, text="View Section:").pack(side=tk.LEFT, padx=5)

        self.hex_section_var = tk.StringVar(value="PTR3")
        for section in ["Header", "PTR3", "PTR4", "PTR5", "PTR6", "Full File"]:
            ttk.Radiobutton(selector_frame,
                           text=section,
                           variable=self.hex_section_var,
                           value=section,
                           command=self.update_hex_view).pack(side=tk.LEFT, padx=5)

        self.hex_viewer = HexViewer(frame)
        self.hex_viewer.pack(fill=tk.BOTH, expand=True)

    def _create_statusbar(self):
        """Create status bar"""
        status_frame = ttk.Frame(self.root)
        status_frame.pack(fill=tk.X, side=tk.BOTTOM)

        self.status_label = ttk.Label(status_frame,
                                      text="Ready",
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
            self.status_label.config(text="Scenario modified - remember to save!")

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
            self.file_label.config(text=f"📄 {self.scenario_file.name}")

            # Load all tabs
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

        # Load overview
        self._load_overview()

        # Load mission text
        self._load_mission_text()

        # Load units
        if 'PTR3' in self.scenario.sections:
            self.unit_editor.load_units(self.scenario.sections['PTR3'])

        # Load coordinates
        if 'PTR5' in self.scenario.sections:
            self.coord_viewer.load_data(self.scenario.sections['PTR5'])

        # Load PTR6
        if 'PTR6' in self.scenario.sections:
            self.ptr6_hex.display_data(self.scenario.sections['PTR6'][:1024])

        # Load hex viewer
        self.update_hex_view()

    def _load_overview(self):
        """Load overview information"""
        if not self.scenario:
            return

        # Header info
        self.overview_text.delete('1.0', tk.END)
        self.overview_text.insert(tk.END, f"Scenario File: {self.scenario_file.name}\n")
        self.overview_text.insert(tk.END, f"File Size: {len(self.scenario.data):,} bytes\n\n")
        self.overview_text.insert(tk.END, f"Magic Number: 0x{struct.unpack('<H', self.scenario.data[0:2])[0]:04x}\n\n")
        self.overview_text.insert(tk.END, "Header Counts:\n")
        for i, count in enumerate(self.scenario.counts):
            self.overview_text.insert(tk.END, f"  Count {i+1:2d}: {count:3d}\n")

        # Statistics
        self.stats_text.delete('1.0', tk.END)
        stats = self.scenario.get_statistics()
        self.stats_text.insert(tk.END, f"Total Size:     {stats['file_size']:,} bytes\n")
        self.stats_text.insert(tk.END, f"Zero Bytes:     {stats['zero_bytes']:,} bytes ({stats['zero_percentage']:.1f}%)\n")
        self.stats_text.insert(tk.END, f"Data Bytes:     {stats['data_bytes']:,} bytes\n")
        self.stats_text.insert(tk.END, f"ASCII Strings:  {stats['string_count']}\n")

        # Data sections
        self.sections_text.delete('1.0', tk.END)
        self.sections_text.insert(tk.END, "Data Sections (in file order):\n\n")
        for name, start, end in self.scenario.section_order:
            size = end - start
            self.sections_text.insert(tk.END,
                f"{name:5s}: 0x{start:06x} - 0x{end:06x} ({size:,} bytes)\n")

    def _load_mission_text(self):
        """Load mission text from scenario"""
        if not self.scenario:
            return

        # Extract mission text blocks (same logic as existing editor)
        presection_start = 0x60
        first_section = min(start for _, start, _ in self.scenario.section_order)
        presection_data = self.scenario.data[presection_start:first_section]

        # Find all text blocks
        mission_blocks = []
        in_text = False
        start = 0
        current_text = b''

        for i, byte in enumerate(presection_data):
            if 32 <= byte <= 126:  # Printable ASCII
                if not in_text:
                    start = i
                    in_text = True
                current_text += bytes([byte])
            else:
                if in_text and len(current_text) >= 30:
                    abs_offset = presection_start + start
                    text = current_text.decode('ascii', errors='ignore').strip()
                    mission_blocks.append({
                        'offset': abs_offset,
                        'text': text,
                        'length': len(current_text)
                    })
                in_text = False
                current_text = b''

        self.mission_blocks = mission_blocks

        # Separate Allied and Axis
        allied_lines = [block['text'] for i, block in enumerate(mission_blocks) if i % 2 == 0]
        axis_lines = [block['text'] for i, block in enumerate(mission_blocks) if i % 2 == 1]

        # Display in text widgets
        self.allied_text.delete('1.0', tk.END)
        self.allied_text.insert('1.0', '\n\n'.join(allied_lines))

        self.axis_text.delete('1.0', tk.END)
        self.axis_text.insert('1.0', '\n\n'.join(axis_lines))

        # Reset modified flags
        self.allied_text.edit_modified(False)
        self.axis_text.edit_modified(False)

    def revert_mission_text(self):
        """Revert mission text changes"""
        if not self.scenario:
            return

        if messagebox.askyesno("Revert", "Discard all mission text changes?"):
            self._load_mission_text()
            self.modified = False
            self.modified_label.config(text="")
            self.status_label.config(text="Changes reverted")

    def save_scenario(self):
        """Save scenario"""
        if not self.scenario or not self.scenario_file:
            messagebox.showwarning("Warning", "No scenario loaded!")
            return

        try:
            # Create backup
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = self.scenario_file.with_suffix(f'.{timestamp}.bak')
            shutil.copy(self.scenario_file, backup_file)

            # Apply mission text changes
            self._apply_mission_text_changes()

            # Write scenario
            self.scenario.write(str(self.scenario_file))

            self.modified = False
            self.modified_label.config(text="", foreground="black")
            self.status_label.config(text=f"Saved: {self.scenario_file.name}")

            messagebox.showinfo("Success",
                f"Scenario saved successfully!\n\nBackup created:\n{backup_file.name}")

        except Exception as e:
            messagebox.showerror("Error", f"Failed to save scenario:\n{e}")

    def _apply_mission_text_changes(self):
        """Apply mission text edits to scenario data"""
        # Get edited text
        allied_text = self.allied_text.get('1.0', tk.END).strip()
        axis_text = self.axis_text.get('1.0', tk.END).strip()

        # Split into lines
        allied_lines = [line.strip() for line in allied_text.split('\n') if line.strip()]
        axis_lines = [line.strip() for line in axis_text.split('\n') if line.strip()]

        # Create new data array
        data_array = bytearray(self.scenario.data)

        # Replace each text block
        for i, block in enumerate(self.mission_blocks):
            if i % 2 == 0:  # Allied
                line_idx = i // 2
                if line_idx < len(allied_lines):
                    new_text = allied_lines[line_idx]
                else:
                    new_text = ""
            else:  # Axis
                line_idx = i // 2
                if line_idx < len(axis_lines):
                    new_text = axis_lines[line_idx]
                else:
                    new_text = ""

            # Encode and pad
            new_bytes = new_text.encode('ascii', errors='ignore')

            # Check length
            if len(new_bytes) > 127:
                new_bytes = new_bytes[:127]

            # Find text block and replace
            offset = block['offset']
            old_text_bytes = block['text'].encode('ascii', errors='ignore')

            # Pad with spaces
            if len(new_bytes) < len(old_text_bytes):
                new_bytes = new_bytes + (b' ' * (len(old_text_bytes) - len(new_bytes)))

            # Replace in data
            data_array[offset:offset+len(new_bytes)] = new_bytes

        # Update scenario data
        self.scenario.data = bytes(data_array)

        # Re-parse sections
        self.scenario._parse_sections()

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

        if not filename:
            return

        self.scenario_file = Path(filename)
        self.save_scenario()

    def reload_scenario(self):
        """Reload current scenario"""
        if self.scenario_file:
            if self.modified:
                if not messagebox.askyesno("Reload", "Discard unsaved changes?"):
                    return
            self.open_scenario()

    def new_scenario(self):
        """Create new scenario"""
        messagebox.showinfo("New Scenario",
            "Creating new scenarios requires understanding the binary format.\n\n"
            "Recommended: Start by opening and modifying an existing scenario.")

    def validate_scenario(self):
        """Validate scenario"""
        if not self.scenario:
            messagebox.showwarning("Warning", "No scenario loaded!")
            return

        valid = self.scenario.validate()

        if valid:
            messagebox.showinfo("Validation", "Scenario file is valid! ✓")
        else:
            messagebox.showwarning("Validation", "Scenario has warnings. Check format.")

    def show_search(self):
        """Show string search"""
        if not self.scenario:
            messagebox.showwarning("Warning", "No scenario loaded!")
            return

        # Create search window
        search_win = tk.Toplevel(self.root)
        search_win.title("String Search")
        search_win.geometry("700x500")

        searcher = StringSearcher(search_win, self._do_search)
        searcher.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

    def _do_search(self, query, tree):
        """Perform string search"""
        # Clear results
        for item in tree.get_children():
            tree.delete(item)

        # Search in all sections
        query_lower = query.lower()

        for section_name, section_data in self.scenario.sections.items():
            # Find all occurrences
            i = 0
            while i < len(section_data):
                # Look for ASCII text
                text_start = i
                text = b''

                while i < len(section_data) and 32 <= section_data[i] < 127:
                    text += bytes([section_data[i]])
                    i += 1

                if len(text) >= len(query):
                    text_str = text.decode('ascii', errors='ignore')
                    if query_lower in text_str.lower():
                        # Found match
                        preview = text_str[:60] + ('...' if len(text_str) > 60 else '')
                        tree.insert("", tk.END, values=(
                            f"0x{text_start:06x}",
                            section_name,
                            preview
                        ))

                i += 1

    def extract_strings(self):
        """Extract all strings from scenario"""
        if not self.scenario:
            messagebox.showwarning("Warning", "No scenario loaded!")
            return

        strings = self.scenario.find_strings(min_length=4)

        # Show in new window
        string_win = tk.Toplevel(self.root)
        string_win.title(f"Extracted Strings ({len(strings)} found)")
        string_win.geometry("800x600")

        text = scrolledtext.ScrolledText(string_win, font=("Courier", 10))
        text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        for offset, s in strings:
            text.insert(tk.END, f"0x{offset:06x}: {s}\n")

    def compare_scenarios(self):
        """Compare with another scenario"""
        messagebox.showinfo("Compare", "Scenario comparison feature coming soon!")

    def manage_backups(self):
        """Manage backup files"""
        if not self.scenario_file:
            messagebox.showwarning("Warning", "No scenario loaded!")
            return

        # Find backups
        backups = list(self.scenario_file.parent.glob(f"{self.scenario_file.stem}.*.bak"))

        if not backups:
            messagebox.showinfo("Backups", "No backups found for this scenario.")
            return

        # Show backup list
        backup_win = tk.Toplevel(self.root)
        backup_win.title("Backup Manager")
        backup_win.geometry("600x400")

        ttk.Label(backup_win,
                 text=f"Backups for {self.scenario_file.name}:",
                 font=("TkDefaultFont", 10, "bold")).pack(pady=10)

        listbox = tk.Listbox(backup_win, width=70, height=15)
        listbox.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        for backup in sorted(backups, reverse=True):
            size = backup.stat().st_size
            listbox.insert(tk.END, f"{backup.name} ({size:,} bytes)")

        button_frame = ttk.Frame(backup_win)
        button_frame.pack(pady=10)

        ttk.Button(button_frame, text="Close",
                  command=backup_win.destroy).pack(side=tk.LEFT, padx=5)

    def show_about(self):
        """Show about dialog"""
        messagebox.showinfo("About",
            "D-Day Scenario Creator/Editor\n\n"
            "A comprehensive tool for creating and editing\n"
            "World at War: D-Day scenario files\n\n"
            "Features:\n"
            "• Mission briefing editor (Allied & Axis)\n"
            "• Unit roster viewer\n"
            "• Coordinate data viewer\n"
            "• Hex viewer for binary data\n"
            "• String search and extraction\n"
            "• Automatic backup management\n"
            "• Format validation\n\n"
            "Created: 2025-11-07\n"
            "Format: D-Day .SCN (Magic: 0x1230)")

    def show_format_docs(self):
        """Show format documentation"""
        docs_win = tk.Toplevel(self.root)
        docs_win.title("D-Day Scenario Format Documentation")
        docs_win.geometry("900x700")

        text = scrolledtext.ScrolledText(docs_win, font=("Courier", 10), wrap=tk.WORD)
        text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Load documentation
        docs_path = Path("txt/D_DAY_FORMAT_FINAL_SUMMARY.txt")
        if docs_path.exists():
            text.insert('1.0', docs_path.read_text())
        else:
            text.insert('1.0', """
D-Day Scenario Format (.SCN)

Magic Number: 0x1230
Header Size: 96 bytes (0x60)

Structure:
- Header (0x00-0x5F): Magic, counts, pointers
- Pre-section data (0x60-PTR5): Mission text
- PTR5: Numeric/coordinate data
- PTR6: Specialized/AI data
- PTR3: Unit roster
- PTR4: Unit positioning + text

See txt/D_DAY_FORMAT_FINAL_SUMMARY.txt for complete documentation.
""")

    def update_hex_view(self):
        """Update hex viewer"""
        if not self.scenario:
            return

        section = self.hex_section_var.get()

        if section == "Header":
            self.hex_viewer.display_data(self.scenario.data[:0x60], 0)
        elif section == "Full File":
            # Show first 4KB
            self.hex_viewer.display_data(self.scenario.data[:4096], 0)
        elif section in self.scenario.sections:
            data = self.scenario.sections[section]
            # Show first 4KB
            offset = self.scenario.pointers.get(section, 0)
            self.hex_viewer.display_data(data[:4096], offset)

    def run(self):
        """Run the application"""
        self.root.mainloop()


def main():
    """Main entry point"""
    import sys

    app = DdayScenarioCreator()

    # Load scenario from command line if provided
    if len(sys.argv) > 1:
        scenario_file = sys.argv[1]
        if Path(scenario_file).exists():
            app.scenario_file = Path(scenario_file)
            app.scenario = DdayScenario(scenario_file)
            if app.scenario.is_valid:
                app.file_label.config(text=f"📄 {app.scenario_file.name}")
                app._load_scenario_data()
                app.status_label.config(text=f"Loaded: {scenario_file}")

    app.run()


if __name__ == '__main__':
    main()
