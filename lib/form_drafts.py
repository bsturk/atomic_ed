"""Keep unapplied form fields across record selection and model refreshes."""
from contextlib import contextmanager
import tkinter as tk
from tkinter import ttk


def ask_save_changes(parent, action, name):
    """Use explicit action labels; closing the prompt is always Cancel."""
    dialog = tk.Toplevel(parent)
    dialog.title('Unsaved changes')
    dialog.transient(parent)
    dialog.resizable(False, False)
    result = None
    def choose(value):
        nonlocal result
        result = value
        dialog.destroy()
    body = ttk.Frame(dialog, padding=18)
    body.pack(fill='both', expand=True)
    ttk.Label(body, text=f'Save changes to {name} before {action}?', wraplength=420).pack(anchor='w')
    buttons = ttk.Frame(body)
    buttons.pack(anchor='e', pady=(18, 0))
    for title, value in (('Save', 'save'), ('Discard', 'discard'), ('Cancel', None)):
        button = ttk.Button(buttons, text=title, command=lambda v=value: choose(v))
        button.pack(side='left', padx=4)
        if value == 'save':
            button.focus_set()
    dialog.bind('<Escape>', lambda e: choose(None))
    dialog.protocol('WM_DELETE_WINDOW', lambda: choose(None))
    dialog.grab_set()
    parent.wait_window(dialog)
    return result


def field_variable(widget):
    """Give an existing entry/spinbox a retained, observable text variable."""
    variable = tk.StringVar(master=widget, value=widget.get())
    widget.configure(textvariable=variable)
    return variable


class FormDraft:
    def __init__(self, owner, label, fields, changed, prepare):
        self.owner, self.label, self.fields = owner, label, fields
        self.changed, self.prepare = changed, prepare
        self.context = None
        self.baseline = {}
        self.drafts = {}
        self.edit_order = {}
        self.revision = 0
        self.loading = False
        for variable in fields.values():
            variable.trace_add('write', self._changed)

    def _changed(self, *args):
        if not self.loading and self.context is not None:
            self.revision += 1
            self.edit_order[self.context] = self.revision
            self.changed()

    def values(self):
        return {key: variable.get() for key, variable in self.fields.items()}

    def pending(self):
        pending = dict(self.drafts)
        if self.context is not None and not self.loading:
            values = self.values()
            changes = {k: v for k, v in values.items() if v != self.baseline[k]}
            if changes:
                pending[self.context] = (values, changes)
            else:
                pending.pop(self.context, None)
        return dict(sorted(pending.items(), key=lambda item: self.edit_order.get(item[0], 0)))

    @contextmanager
    def load(self, context):
        self.drafts = self.pending()
        self.context = context
        self.loading = True
        try:
            yield
            self.baseline = self.values()
            if context in self.drafts:
                for key, value in self.drafts[context][1].items():
                    self.fields[key].set(value)
        finally:
            self.loading = False
        self.changed()

    def deactivate(self):
        self.drafts = self.pending()
        self.context = None

    def accept(self):
        self.drafts.pop(self.context, None)
        self.edit_order.pop(self.context, None)
        self.baseline = self.values()
        self.changed()

    def revert(self):
        self.loading = True
        try:
            for key, value in self.baseline.items():
                self.fields[key].set(value)
            self.drafts.pop(self.context, None)
            self.edit_order.pop(self.context, None)
        finally:
            self.loading = False
        self.changed()

    def clear(self):
        """A document replacement ends its drafts, including hidden records."""
        self.drafts.clear()
        self.edit_order.clear()
        self.context = None
        self.baseline = {}
