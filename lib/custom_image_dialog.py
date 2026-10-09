"""Preview the actual palette-converted chit before committing an import."""
import tkinter as tk
from tkinter import ttk, messagebox

from PIL import Image, ImageTk

from lib.custom_images import counter_image


class ChitImportDialog(tk.Toplevel):
    def __init__(self, app, pixels, name, side, index):
        super().__init__(app.root)
        self.title('Import Unit Chit')
        self.transient(app.root)
        body = ttk.Frame(self, padding=18)
        body.pack()
        ttk.Label(body, text=name).pack()
        self.photo = ImageTk.PhotoImage(counter_image(pixels).resize((132, 138), Image.Resampling.NEAREST))
        ttk.Label(body, image=self.photo).pack(pady=12)
        ttk.Label(body, text='22 × 23 pixels · D-Day palette\nTransparent pixels remain transparent.\nAn unused chit slot will be assigned to this unit.', justify='center').pack()
        def apply():
            try:
                app.assign_custom_counter(side, index, pixels)
            except ValueError as exc:
                messagebox.showerror('Cannot Import Chit', str(exc), parent=self)
                return
            self.destroy()
        buttons = ttk.Frame(body)
        buttons.pack(pady=(16, 0))
        ttk.Button(buttons, text='Use Chit', command=apply).pack(side='left', padx=5)
        ttk.Button(buttons, text='Cancel', command=self.destroy).pack(side='left', padx=5)
        self.bind('<Escape>', lambda e: self.destroy())
        self.grab_set()
