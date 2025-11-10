#!/usr/bin/env python3
"""
Sound Configuration Editor for World at War: D-Day American Invades

A GUI tool to edit INVADE.CFG and SYSTEM.SET configuration files.
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from pathlib import Path
import shutil
from typing import Optional


class SystemSetEditor(ttk.Frame):
    """Editor for SYSTEM.SET file (10 bytes - preference flags)"""

    def __init__(self, parent, file_path: str):
        super().__init__(parent)
        self.file_path = Path(file_path)
        self.music_var = tk.BooleanVar(value=True)
        self.sound_fx_var = tk.BooleanVar(value=True)

        self.setup_ui()
        self.load_file()

    def setup_ui(self):
        """Setup the user interface"""
        # Title
        title = ttk.Label(self, text="SYSTEM.SET - System Preferences",
                         font=('Arial', 12, 'bold'))
        title.grid(row=0, column=0, columnspan=2, pady=10, sticky='w')

        # File path
        ttk.Label(self, text="File:").grid(row=1, column=0, sticky='w', padx=5)
        self.file_label = ttk.Label(self, text=str(self.file_path),
                                    foreground='blue')
        self.file_label.grid(row=1, column=1, sticky='w', padx=5)

        # Separator
        ttk.Separator(self, orient='horizontal').grid(
            row=2, column=0, columnspan=2, sticky='ew', pady=10)

        # Settings frame
        settings_frame = ttk.LabelFrame(self, text="Sound Preferences", padding=10)
        settings_frame.grid(row=3, column=0, columnspan=2, sticky='ew', padx=5, pady=5)

        # Music checkbox
        music_cb = ttk.Checkbutton(
            settings_frame,
            text="Music Enabled",
            variable=self.music_var,
            command=self.on_change
        )
        music_cb.grid(row=0, column=0, sticky='w', pady=5)

        ttk.Label(settings_frame, text="Enable/disable background music",
                 foreground='gray').grid(row=0, column=1, sticky='w', padx=20)

        # Sound FX checkbox
        sound_fx_cb = ttk.Checkbutton(
            settings_frame,
            text="Sound Effects Enabled",
            variable=self.sound_fx_var,
            command=self.on_change
        )
        sound_fx_cb.grid(row=1, column=0, sticky='w', pady=5)

        ttk.Label(settings_frame, text="Enable/disable sound effects",
                 foreground='gray').grid(row=1, column=1, sticky='w', padx=20)

        # Info frame
        info_frame = ttk.LabelFrame(self, text="File Information", padding=10)
        info_frame.grid(row=4, column=0, columnspan=2, sticky='ew', padx=5, pady=5)

        self.info_text = tk.Text(info_frame, height=6, width=60,
                                 font=('Courier', 9))
        self.info_text.grid(row=0, column=0, sticky='ew')

        # Buttons
        button_frame = ttk.Frame(self)
        button_frame.grid(row=5, column=0, columnspan=2, pady=10)

        self.save_btn = ttk.Button(button_frame, text="Save Changes",
                                   command=self.save_file, state='disabled')
        self.save_btn.grid(row=0, column=0, padx=5)

        ttk.Button(button_frame, text="Reload",
                  command=self.load_file).grid(row=0, column=1, padx=5)

        ttk.Button(button_frame, text="Browse...",
                  command=self.browse_file).grid(row=0, column=2, padx=5)

    def load_file(self):
        """Load SYSTEM.SET file"""
        # Update file label
        self.file_label.config(text=str(self.file_path))

        try:
            if not self.file_path.exists():
                messagebox.showwarning("File Not Found",
                    f"File not found: {self.file_path}\nUsing default values.")
                self.update_info("File not found - using defaults")
                return

            with open(self.file_path, 'rb') as f:
                data = f.read()

            if len(data) != 10:
                messagebox.showerror("Invalid File",
                    f"SYSTEM.SET should be 10 bytes, got {len(data)} bytes")
                return

            # Read preference flags
            self.music_var.set(data[0] != 0)
            self.sound_fx_var.set(data[1] != 0)

            # Update info display
            info = f"File size: {len(data)} bytes\n"
            info += f"Byte 0 (Music):    0x{data[0]:02x} ({data[0]}) - "
            info += "ON" if data[0] else "OFF"
            info += "\n"
            info += f"Byte 1 (Sound FX): 0x{data[1]:02x} ({data[1]}) - "
            info += "ON" if data[1] else "OFF"
            info += "\n"
            info += f"Bytes 2-9: "
            info += " ".join(f"{b:02x}" for b in data[2:10])

            self.update_info(info)
            self.save_btn.config(state='disabled')

        except Exception as e:
            messagebox.showerror("Error", f"Failed to load file: {e}")

    def save_file(self):
        """Save SYSTEM.SET file"""
        try:
            # Create backup
            if self.file_path.exists():
                backup_path = self.file_path.with_suffix('.SET.bak')
                shutil.copy2(self.file_path, backup_path)

            # Create 10-byte file
            data = bytearray(10)
            data[0] = 1 if self.music_var.get() else 0
            data[1] = 1 if self.sound_fx_var.get() else 0
            # Bytes 2-9 remain zero

            # Ensure directory exists
            self.file_path.parent.mkdir(parents=True, exist_ok=True)

            # Write file
            with open(self.file_path, 'wb') as f:
                f.write(data)

            messagebox.showinfo("Success",
                f"File saved successfully!\nBackup created as {backup_path.name}")
            self.save_btn.config(state='disabled')
            self.load_file()  # Reload to show current state

        except Exception as e:
            messagebox.showerror("Error", f"Failed to save file: {e}")

    def on_change(self):
        """Called when a setting changes"""
        self.save_btn.config(state='normal')

    def update_info(self, text: str):
        """Update info text display"""
        self.info_text.delete('1.0', tk.END)
        self.info_text.insert('1.0', text)

    def browse_file(self):
        """Browse for SYSTEM.SET file"""
        filename = filedialog.askopenfilename(
            title="Select SYSTEM.SET file",
            filetypes=[("SYSTEM.SET", "SYSTEM.SET"), ("All files", "*.*")]
        )
        if filename:
            self.file_path = Path(filename)
            self.load_file()


class InvadeCfgEditor(ttk.Frame):
    """Editor for INVADE.CFG file (66 bytes - sound card configuration)"""

    def __init__(self, parent, file_path: str):
        super().__init__(parent)
        self.file_path = Path(file_path)

        # Sound FX block variables
        self.sfx_irq = tk.IntVar(value=5)
        self.sfx_dma = tk.IntVar(value=1)
        self.sfx_port = tk.StringVar(value="220")

        # Music block variables
        self.music_irq = tk.IntVar(value=5)
        self.music_dma = tk.IntVar(value=1)
        self.music_port = tk.StringVar(value="220")

        self.setup_ui()
        self.load_file()

    def setup_ui(self):
        """Setup the user interface"""
        # Title
        title = ttk.Label(self, text="INVADE.CFG - Sound Card Configuration",
                         font=('Arial', 12, 'bold'))
        title.grid(row=0, column=0, columnspan=4, pady=10, sticky='w')

        # File path
        ttk.Label(self, text="File:").grid(row=1, column=0, sticky='w', padx=5)
        self.file_label = ttk.Label(self, text=str(self.file_path),
                                    foreground='blue')
        self.file_label.grid(row=1, column=1, columnspan=3, sticky='w', padx=5)

        # Separator
        ttk.Separator(self, orient='horizontal').grid(
            row=2, column=0, columnspan=4, sticky='ew', pady=10)

        # Sound FX Block
        sfx_frame = ttk.LabelFrame(self, text="Sound Effects Configuration", padding=10)
        sfx_frame.grid(row=3, column=0, columnspan=4, sticky='ew', padx=5, pady=5)

        self.create_config_inputs(sfx_frame, 0, self.sfx_irq, self.sfx_dma,
                                 self.sfx_port, "Sound FX")

        # Music Block
        music_frame = ttk.LabelFrame(self, text="Music Configuration", padding=10)
        music_frame.grid(row=4, column=0, columnspan=4, sticky='ew', padx=5, pady=5)

        self.create_config_inputs(music_frame, 0, self.music_irq, self.music_dma,
                                 self.music_port, "Music")

        # Presets
        preset_frame = ttk.LabelFrame(self, text="Presets", padding=10)
        preset_frame.grid(row=5, column=0, columnspan=4, sticky='ew', padx=5, pady=5)

        ttk.Button(preset_frame, text="SoundBlaster 16 Default (220/5/1)",
                  command=self.preset_sb16).grid(row=0, column=0, padx=5)
        ttk.Button(preset_frame, text="Copy Sound FX to Music",
                  command=self.copy_sfx_to_music).grid(row=0, column=1, padx=5)

        # Info frame
        info_frame = ttk.LabelFrame(self, text="File Information", padding=10)
        info_frame.grid(row=6, column=0, columnspan=4, sticky='ew', padx=5, pady=5)

        self.info_text = tk.Text(info_frame, height=8, width=70,
                                 font=('Courier', 9))
        self.info_text.grid(row=0, column=0, sticky='ew')

        # Buttons
        button_frame = ttk.Frame(self)
        button_frame.grid(row=7, column=0, columnspan=4, pady=10)

        self.save_btn = ttk.Button(button_frame, text="Save Changes",
                                   command=self.save_file, state='disabled')
        self.save_btn.grid(row=0, column=0, padx=5)

        ttk.Button(button_frame, text="Reload",
                  command=self.load_file).grid(row=0, column=1, padx=5)

        ttk.Button(button_frame, text="Browse...",
                  command=self.browse_file).grid(row=0, column=2, padx=5)

    def create_config_inputs(self, parent, start_row, irq_var, dma_var,
                            port_var, label_prefix):
        """Create configuration input fields"""
        # IRQ
        ttk.Label(parent, text="IRQ:").grid(row=start_row, column=0,
                                            sticky='w', pady=5)
        irq_spin = ttk.Spinbox(parent, from_=0, to=15, textvariable=irq_var,
                               width=10, command=self.on_change)
        irq_spin.grid(row=start_row, column=1, sticky='w', padx=5)
        irq_var.trace_add('write', lambda *args: self.on_change())

        ttk.Label(parent, text="(typically 5 or 7)",
                 foreground='gray').grid(row=start_row, column=2, sticky='w')

        # DMA
        ttk.Label(parent, text="DMA:").grid(row=start_row+1, column=0,
                                            sticky='w', pady=5)
        dma_spin = ttk.Spinbox(parent, from_=0, to=7, textvariable=dma_var,
                               width=10, command=self.on_change)
        dma_spin.grid(row=start_row+1, column=1, sticky='w', padx=5)
        dma_var.trace_add('write', lambda *args: self.on_change())

        ttk.Label(parent, text="(typically 1)",
                 foreground='gray').grid(row=start_row+1, column=2, sticky='w')

        # Port
        ttk.Label(parent, text="I/O Port:").grid(row=start_row+2, column=0,
                                                  sticky='w', pady=5)
        port_entry = ttk.Entry(parent, textvariable=port_var, width=10)
        port_entry.grid(row=start_row+2, column=1, sticky='w', padx=5)
        port_var.trace_add('write', lambda *args: self.on_change())

        ttk.Label(parent, text="(hex, e.g., 220 for 0x220)",
                 foreground='gray').grid(row=start_row+2, column=2, sticky='w')

    def load_file(self):
        """Load INVADE.CFG file"""
        # Update file label
        self.file_label.config(text=str(self.file_path))

        try:
            if not self.file_path.exists():
                messagebox.showwarning("File Not Found",
                    f"File not found: {self.file_path}\nUsing default values.")
                self.update_info("File not found - using defaults")
                return

            with open(self.file_path, 'rb') as f:
                data = f.read()

            if len(data) != 66:
                messagebox.showerror("Invalid File",
                    f"INVADE.CFG should be 66 bytes, got {len(data)} bytes")
                return

            # Read Sound FX block (bytes 4-7)
            self.sfx_irq.set(data[4])
            self.sfx_dma.set(data[5])
            sfx_port = data[6] | (data[7] << 8)
            self.sfx_port.set(f"{sfx_port:03x}")

            # Read Music block (bytes 35-38)
            self.music_irq.set(data[35])
            self.music_dma.set(data[36])
            music_port = data[37] | (data[38] << 8)
            self.music_port.set(f"{music_port:03x}")

            # Update info display
            info = f"File size: {len(data)} bytes\n\n"
            info += "Sound FX Block (bytes 4-7):\n"
            info += f"  IRQ:  {data[4]}\n"
            info += f"  DMA:  {data[5]}\n"
            info += f"  Port: 0x{sfx_port:04x} ({sfx_port})\n\n"
            info += "Music Block (bytes 35-38):\n"
            info += f"  IRQ:  {data[35]}\n"
            info += f"  DMA:  {data[36]}\n"
            info += f"  Port: 0x{music_port:04x} ({music_port})\n"

            # Check if configuration is correct
            if sfx_port != 0x220 or music_port != 0x220:
                info += "\n⚠ Warning: Port should typically be 0x0220"

            self.update_info(info)
            self.save_btn.config(state='disabled')

        except Exception as e:
            messagebox.showerror("Error", f"Failed to load file: {e}")

    def save_file(self):
        """Save INVADE.CFG file"""
        try:
            # Validate inputs
            try:
                sfx_port = int(self.sfx_port.get(), 16)
                music_port = int(self.music_port.get(), 16)
            except ValueError:
                messagebox.showerror("Invalid Input",
                    "Port values must be valid hexadecimal numbers")
                return

            if not (0 <= sfx_port <= 0xFFFF):
                messagebox.showerror("Invalid Input",
                    "Port must be between 0x0000 and 0xFFFF")
                return

            if not (0 <= music_port <= 0xFFFF):
                messagebox.showerror("Invalid Input",
                    "Port must be between 0x0000 and 0xFFFF")
                return

            # Load existing file or create new one
            if self.file_path.exists():
                with open(self.file_path, 'rb') as f:
                    data = bytearray(f.read())

                if len(data) != 66:
                    messagebox.showerror("Invalid File",
                        "Existing file has wrong size")
                    return

                # Create backup
                backup_path = self.file_path.with_suffix('.CFG.bak')
                shutil.copy2(self.file_path, backup_path)
            else:
                # Create new file with zeros
                data = bytearray(66)
                backup_path = None

            # Update Sound FX block
            data[4] = self.sfx_irq.get()
            data[5] = self.sfx_dma.get()
            data[6] = sfx_port & 0xFF
            data[7] = (sfx_port >> 8) & 0xFF

            # Update Music block
            data[35] = self.music_irq.get()
            data[36] = self.music_dma.get()
            data[37] = music_port & 0xFF
            data[38] = (music_port >> 8) & 0xFF

            # Ensure directory exists
            self.file_path.parent.mkdir(parents=True, exist_ok=True)

            # Write file
            with open(self.file_path, 'wb') as f:
                f.write(data)

            backup_msg = f"\nBackup created as {backup_path.name}" if backup_path else ""
            messagebox.showinfo("Success",
                f"File saved successfully!{backup_msg}")
            self.save_btn.config(state='disabled')
            self.load_file()  # Reload to show current state

        except Exception as e:
            messagebox.showerror("Error", f"Failed to save file: {e}")

    def on_change(self):
        """Called when a setting changes"""
        self.save_btn.config(state='normal')

    def update_info(self, text: str):
        """Update info text display"""
        self.info_text.delete('1.0', tk.END)
        self.info_text.insert('1.0', text)

    def browse_file(self):
        """Browse for INVADE.CFG file"""
        filename = filedialog.askopenfilename(
            title="Select INVADE.CFG file",
            filetypes=[("INVADE.CFG", "INVADE.CFG"), ("All files", "*.*")]
        )
        if filename:
            self.file_path = Path(filename)
            self.load_file()

    def preset_sb16(self):
        """Apply SoundBlaster 16 default preset"""
        self.sfx_irq.set(5)
        self.sfx_dma.set(1)
        self.sfx_port.set("220")

        self.music_irq.set(5)
        self.music_dma.set(1)
        self.music_port.set("220")

        self.on_change()

    def copy_sfx_to_music(self):
        """Copy Sound FX settings to Music settings"""
        self.music_irq.set(self.sfx_irq.get())
        self.music_dma.set(self.sfx_dma.get())
        self.music_port.set(self.sfx_port.get())

        self.on_change()


class SoundConfigEditor:
    """Main application window"""

    def __init__(self, root, game_dir: Optional[str] = None):
        self.root = root
        self.root.title("Sound Configuration Editor - World at War: D-Day")

        # Determine game directory
        if game_dir is None:
            # Try common locations
            possible_dirs = [
                Path.cwd() / "game",
                Path(__file__).parent / "game",
                Path.cwd(),
            ]
            game_dir = None
            for pdir in possible_dirs:
                if pdir.exists():
                    game_dir = pdir
                    break
            if game_dir is None:
                game_dir = Path.cwd()
        else:
            game_dir = Path(game_dir)

        self.game_dir = game_dir

        # Top toolbar
        toolbar = ttk.Frame(root)
        toolbar.pack(fill='x', padx=5, pady=5)

        ttk.Label(toolbar, text="Config Directory:").pack(side='left', padx=5)

        self.dir_label = ttk.Label(toolbar, text=str(game_dir),
                                   foreground='blue', relief='sunken', padding=3)
        self.dir_label.pack(side='left', padx=5, fill='x', expand=True)

        ttk.Button(toolbar, text="Change Directory...",
                  command=self.change_directory).pack(side='left', padx=5)

        # Create notebook (tabbed interface)
        notebook = ttk.Notebook(root)
        notebook.pack(fill='both', expand=True, padx=5, pady=5)
        self.notebook = notebook

        # SYSTEM.SET tab
        system_set_path = game_dir / "SYSTEM.SET"
        self.system_set_editor = SystemSetEditor(notebook, str(system_set_path))
        notebook.add(self.system_set_editor, text="SYSTEM.SET (Preferences)")

        # INVADE.CFG tab
        invade_cfg_path = game_dir / "INVADE.CFG"
        self.invade_cfg_editor = InvadeCfgEditor(notebook, str(invade_cfg_path))
        notebook.add(self.invade_cfg_editor, text="INVADE.CFG (Sound Card)")

        # Status bar
        status_frame = ttk.Frame(root)
        status_frame.pack(fill='x', side='bottom', padx=5, pady=5)

        ttk.Label(status_frame, text="Ready",
                 foreground='green').pack(side='left', padx=5)

        # Menu bar
        menubar = tk.Menu(root)
        root.config(menu=menubar)

        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Reload All", command=self.reload_all)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=root.quit)

        # Help menu
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="About", command=self.show_about)

    def change_directory(self):
        """Change the game directory"""
        new_dir = filedialog.askdirectory(
            title="Select Game Directory (containing SYSTEM.SET and INVADE.CFG)",
            initialdir=self.game_dir
        )
        if new_dir:
            self.game_dir = Path(new_dir)
            self.dir_label.config(text=str(self.game_dir))

            # Update file paths in editors
            self.system_set_editor.file_path = self.game_dir / "SYSTEM.SET"
            self.invade_cfg_editor.file_path = self.game_dir / "INVADE.CFG"

            # Reload files from new directory
            self.reload_all()

    def reload_all(self):
        """Reload all configuration files"""
        self.system_set_editor.load_file()
        self.invade_cfg_editor.load_file()

    def show_about(self):
        """Show about dialog"""
        about_text = """Sound Configuration Editor
Version 1.0

A GUI tool to edit sound configuration files for:
World at War: D-Day American Invades (1995)

Files managed:
• SYSTEM.SET - Sound preferences (10 bytes)
• INVADE.CFG - Sound card settings (66 bytes)

Created for easy configuration of SoundBlaster settings.
"""
        messagebox.showinfo("About", about_text)


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(
        description="Sound Configuration Editor for World at War: D-Day"
    )
    parser.add_argument(
        '--game-dir',
        help='Path to game directory (default: ./game)',
        default=None
    )

    args = parser.parse_args()

    root = tk.Tk()
    root.geometry("750x700")
    app = SoundConfigEditor(root, args.game_dir)
    root.mainloop()


if __name__ == '__main__':
    main()
