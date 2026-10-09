"""Browse session edits and move to a previous or later document state."""
import tkinter as tk
from tkinter import ttk, scrolledtext


class HistoryWindow(tk.Toplevel):
    def __init__(self, app):
        super().__init__(app.root)
        self.app = app
        self.title('Edit History')
        self.geometry('820x480')
        self.transient(app.root)
        frame = ttk.Frame(self, padding=12)
        frame.pack(fill='both', expand=True)
        self.summary = ttk.Label(frame)
        self.summary.pack(anchor='w', pady=(0, 8))
        listing = ttk.Frame(frame)
        listing.pack(fill='both', expand=True)
        self.tree = ttk.Treeview(listing, columns=('step', 'action', 'time', 'state'),
                                 show='headings', selectmode='browse')
        for name, title, width in (('step', 'Step', 50), ('action', 'Change', 440),
                                    ('time', 'Time', 85), ('state', 'State', 160)):
            self.tree.heading(name, text=title)
            self.tree.column(name, width=width, stretch=name == 'action')
        scroll = ttk.Scrollbar(listing, orient='vertical', command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll.set)
        scroll.pack(side='right', fill='y')
        self.tree.pack(fill='both', expand=True)
        self.tree.tag_configure('future', foreground='#777777')
        self.tree.bind('<<TreeviewSelect>>', self.select)
        self.tree.bind('<Double-1>', lambda event: self.restore())
        self.details = scrolledtext.ScrolledText(frame, height=4, wrap='word', state='disabled')
        self.details.pack(fill='x', pady=8)
        buttons = ttk.Frame(frame)
        buttons.pack(fill='x')
        self.undo_button = ttk.Button(buttons, text='Undo', command=app.undo_edit)
        self.undo_button.pack(side='left')
        self.redo_button = ttk.Button(buttons, text='Redo', command=app.redo_edit)
        self.redo_button.pack(side='left', padx=6)
        self.restore_button = ttk.Button(buttons, text='Restore Selected', command=self.restore)
        self.restore_button.pack(side='left', padx=6)
        ttk.Button(buttons, text='Close', command=self.destroy).pack(side='right')
        ttk.Label(frame, text='Session history survives Save / Save As. Opening, reloading or creating a document starts a new history.').pack(
            anchor='w', pady=(10, 0))
        app._bind_history_shortcuts(self)
        self.refresh()

    def refresh(self):
        history = self.app.history
        self.summary.config(text=f'{len(history.entries)} edits · Current step {history.position}')
        self.tree.delete(*self.tree.get_children())
        if history.initial is not None:
            rows = [(history.initial_label, '')]+[(e.label, e.time) for e in history.entries]
            for index, (label, time) in enumerate(rows):
                states = (['Current'] if index == history.position else ['Undone'] if index > history.position else [])
                if index == history.saved_position:
                    states.append('Saved')
                self.tree.insert('', 'end', iid=str(index), values=(index, label, time, ' · '.join(states)),
                                  tags=('future',) if index > history.position else ())
            self.tree.selection_set(str(history.position))
            self.tree.see(str(history.position))
        self.undo_button.config(state='normal' if history.can_undo else 'disabled')
        self.redo_button.config(state='normal' if history.can_redo else 'disabled')
        self.select()

    def select(self, event=None):
        selected = self.tree.selection()
        history = self.app.history
        index = int(selected[0]) if selected else None
        text = ''
        if index is not None and index <= len(history.entries):
            text = history.initial_label if index == 0 else history.entries[index-1].details or history.entries[index-1].label
        self.details.config(state='normal')
        self.details.delete('1.0', 'end')
        self.details.insert('1.0', text)
        self.details.config(state='disabled')
        self.restore_button.config(state='normal' if index is not None and index != history.position else 'disabled')

    def restore(self):
        if self.tree.selection():
            self.app.restore_history(int(self.tree.selection()[0]))
