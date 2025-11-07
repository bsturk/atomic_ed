#!/usr/bin/env python3
"""
D-Day Scenario Editor - FUNCTIONAL EDITOR
Allows actual editing of scenario parameters
"""

from dday_scenario_parser import DdayScenario
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import shutil

class ScenarioEditor:
    """Full-featured scenario editor with GUI"""

    def __init__(self):
        self.scenario = None
        self.scenario_file = None
        self.mission_blocks = []
        self.modified = False

        # Create main window
        self.root = tk.Tk()
        self.root.title("D-Day Scenario Editor")
        self.root.geometry("1000x800")

        self._create_menu()
        self._create_ui()

    def _create_menu(self):
        """Create menu bar"""
        menubar = tk.Menu(self.root)

        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="Open Scenario...", command=self.open_scenario, accelerator="Ctrl+O")
        file_menu.add_command(label="Save", command=self.save_scenario, accelerator="Ctrl+S")
        file_menu.add_command(label="Save As...", command=self.save_scenario_as)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit)
        menubar.add_cascade(label="File", menu=file_menu)

        # Help menu
        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(label="About", command=self.show_about)
        menubar.add_cascade(label="Help", menu=help_menu)

        self.root.config(menu=menubar)

        # Keyboard shortcuts
        self.root.bind('<Control-o>', lambda e: self.open_scenario())
        self.root.bind('<Control-s>', lambda e: self.save_scenario())

    def _create_ui(self):
        """Create main UI"""
        # Top frame - file info
        top_frame = ttk.Frame(self.root, padding="10")
        top_frame.pack(fill=tk.X)

        ttk.Label(top_frame, text="Current File:").pack(side=tk.LEFT)
        self.file_label = ttk.Label(top_frame, text="No file loaded", foreground="gray")
        self.file_label.pack(side=tk.LEFT, padx=10)

        # Notebook for tabs
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Tab 1: Mission Text
        self._create_mission_tab()

        # Tab 2: Info (placeholder for future)
        info_frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(info_frame, text="Scenario Info")
        ttk.Label(info_frame, text="Scenario information and statistics\n(Coming soon)").pack()

        # Status bar
        status_frame = ttk.Frame(self.root)
        status_frame.pack(fill=tk.X, side=tk.BOTTOM)
        self.status_label = ttk.Label(status_frame, text="Ready", relief=tk.SUNKEN, anchor=tk.W)
        self.status_label.pack(fill=tk.X, padx=5, pady=2)

    def _create_mission_tab(self):
        """Create mission text editing tab"""
        mission_frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(mission_frame, text="Mission Briefings")

        # Instructions
        inst_label = ttk.Label(mission_frame,
            text="Edit mission briefings below. Each side has multiple lines (interleaved in file).",
            wraplength=900)
        inst_label.pack(pady=(0, 10))

        # Create paned window for side-by-side editing
        paned = ttk.PanedWindow(mission_frame, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True)

        # Allied frame
        allied_frame = ttk.LabelFrame(paned, text="Allied Briefing", padding="10")
        paned.add(allied_frame, weight=1)

        ttk.Label(allied_frame, text="Edit Allied mission text:").pack(anchor=tk.W)

        allied_scroll = ttk.Scrollbar(allied_frame)
        allied_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        self.allied_text = tk.Text(allied_frame, height=20, width=45,
                                   yscrollcommand=allied_scroll.set, wrap=tk.WORD)
        self.allied_text.pack(fill=tk.BOTH, expand=True)
        allied_scroll.config(command=self.allied_text.yview)

        self.allied_text.bind('<<Modified>>', self._on_text_modified)

        # Axis frame
        axis_frame = ttk.LabelFrame(paned, text="Axis Briefing", padding="10")
        paned.add(axis_frame, weight=1)

        ttk.Label(axis_frame, text="Edit Axis mission text:").pack(anchor=tk.W)

        axis_scroll = ttk.Scrollbar(axis_frame)
        axis_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        self.axis_text = tk.Text(axis_frame, height=20, width=45,
                                 yscrollcommand=axis_scroll.set, wrap=tk.WORD)
        self.axis_text.pack(fill=tk.BOTH, expand=True)
        axis_scroll.config(command=self.axis_text.yview)

        self.axis_text.bind('<<Modified>>', self._on_text_modified)

        # Buttons
        button_frame = ttk.Frame(mission_frame)
        button_frame.pack(fill=tk.X, pady=(10, 0))

        ttk.Button(button_frame, text="Revert Changes",
                  command=self.revert_mission_text).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Apply & Save",
                  command=self.save_scenario, style='Accent.TButton').pack(side=tk.RIGHT, padx=5)

    def _on_text_modified(self, event):
        """Track modifications"""
        if self.scenario:
            self.modified = True
            self.status_label.config(text="Modified - remember to save!")

    def open_scenario(self):
        """Open a scenario file"""
        filename = filedialog.askopenfilename(
            title="Select D-Day Scenario File",
            initialdir="game/dday/game/SCENARIO",
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
            self.file_label.config(text=self.scenario_file.name, foreground="black")

            # Extract and display mission text
            self._load_mission_text()

            self.modified = False
            self.status_label.config(text=f"Loaded: {self.scenario_file.name}")

        except Exception as e:
            messagebox.showerror("Error", f"Failed to load scenario:\n{e}")

    def _load_mission_text(self):
        """Load mission text from scenario"""
        if not self.scenario:
            return

        # Extract mission text blocks
        presection_start = 0x60
        first_section = min(start for _, start, _ in self.scenario.section_order)
        presection_data = self.scenario.data[presection_start:first_section]

        # Find all text blocks
        self.mission_blocks = []
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
                    self.mission_blocks.append({
                        'offset': abs_offset,
                        'text': text,
                        'length': len(current_text)
                    })
                in_text = False
                current_text = b''

        # Separate Allied and Axis
        allied_lines = [block['text'] for i, block in enumerate(self.mission_blocks) if i % 2 == 0]
        axis_lines = [block['text'] for i, block in enumerate(self.mission_blocks) if i % 2 == 1]

        # Display in text widgets
        self.allied_text.delete('1.0', tk.END)
        self.allied_text.insert('1.0', '\n\n'.join(allied_lines))

        self.axis_text.delete('1.0', tk.END)
        self.axis_text.insert('1.0', '\n\n'.join(axis_lines))

        # Reset modified flags
        self.allied_text.edit_modified(False)
        self.axis_text.edit_modified(False)

    def revert_mission_text(self):
        """Revert changes to mission text"""
        if not self.scenario:
            return

        if messagebox.askyesno("Revert Changes", "Discard all changes to mission text?"):
            self._load_mission_text()
            self.modified = False
            self.status_label.config(text="Changes reverted")

    def save_scenario(self):
        """Save scenario with modifications"""
        if not self.scenario or not self.scenario_file:
            messagebox.showwarning("Warning", "No scenario loaded!")
            return

        try:
            # Create backup
            backup_file = self.scenario_file.with_suffix('.SCN.bak')
            shutil.copy(self.scenario_file, backup_file)

            # Apply mission text changes
            self._apply_mission_text_changes()

            # Write modified scenario
            self.scenario.write(self.scenario_file)

            self.modified = False
            self.status_label.config(text=f"Saved: {self.scenario_file.name}")
            messagebox.showinfo("Success",
                f"Scenario saved successfully!\nBackup created: {backup_file.name}")

        except Exception as e:
            messagebox.showerror("Error", f"Failed to save scenario:\n{e}")

    def save_scenario_as(self):
        """Save scenario to a new file"""
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

    def _apply_mission_text_changes(self):
        """Apply mission text edits to scenario data"""
        # Get edited text
        allied_text = self.allied_text.get('1.0', tk.END).strip()
        axis_text = self.axis_text.get('1.0', tk.END).strip()

        # Split into lines
        allied_lines = [line.strip() for line in allied_text.split('\n') if line.strip()]
        axis_lines = [line.strip() for line in axis_text.split('\n') if line.strip()]

        # Create new presection data with modified text
        # We need to rebuild the interleaved structure
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

            # Find the text block in the data and replace it
            offset = block['offset']
            old_text_bytes = block['text'].encode('ascii', errors='ignore')

            # Pad with spaces to match original length
            if len(new_bytes) < len(old_text_bytes):
                new_bytes = new_bytes + (b' ' * (len(old_text_bytes) - len(new_bytes)))

            # Replace in data
            data_array[offset:offset+len(new_bytes)] = new_bytes

        # Update scenario data
        self.scenario.data = bytes(data_array)

        # Re-parse sections since data changed
        self.scenario._parse_sections()

    def show_about(self):
        """Show about dialog"""
        messagebox.showinfo("About",
            "D-Day Scenario Editor\n\n"
            "A tool for editing World at War: D-Day scenario files\n\n"
            "Features:\n"
            "• Edit mission briefings (Allied & Axis)\n"
            "• Preserve binary format\n"
            "• Automatic backups\n\n"
            "Created: 2025-11-07")

    def run(self):
        """Run the editor"""
        self.root.mainloop()


def main():
    editor = ScenarioEditor()
    editor.run()


if __name__ == '__main__':
    main()
