"""Scenario artwork selection with previews of the pixels exported to DOS."""
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

from PIL import Image, ImageDraw, ImageTk

from lib.presentation_artwork import SLOTS, choices, native_artwork, import_image, scenario_slots, slot_for


class ArtworkPanel(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, padding=10)
        self.app = app
        self.slots = dict(SLOTS)
        self.key = next(iter(SLOTS))
        self.candidate = None
        self.images = []
        ttk.Label(self, text='Choose aircraft, naval, portrait, flag and screen artwork.',
                  font=('TkDefaultFont', 10, 'bold')).pack(anchor='w', pady=(0, 12))
        body = ttk.Frame(self)
        body.pack(fill='both', expand=True)
        self.tree = ttk.Treeview(body, columns=('artwork',), show='tree headings', selectmode='browse', height=16)
        self.tree.heading('#0', text='Used for')
        self.tree.heading('artwork', text='Current artwork')
        self.tree.column('#0', width=225, minwidth=160)
        self.tree.column('artwork', width=260, minwidth=120)
        scroll = ttk.Scrollbar(body, orient='vertical', command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll.set)
        scroll.pack(side='left', fill='y')
        self.tree.pack(side='left', fill='both', expand=True)
        for key, slot in SLOTS.items():
            self.tree.insert('', 'end', iid=key, text=slot.label, values=('D-Day default',))
        self.tree.bind('<<TreeviewSelect>>', self.select_slot)

        right = ttk.Frame(body, padding=(20, 0, 0, 0))
        right.pack(side='left', fill='both', expand=True)
        self.heading = ttk.Label(right, font=('TkDefaultFont', 11, 'bold'))
        self.heading.pack(anchor='w')
        self.description = ttk.Label(right, wraplength=500, justify='left')
        self.description.pack(anchor='w', pady=(6, 12))
        previews = ttk.Frame(right)
        previews.pack(fill='x')
        self.preview_labels = []
        for title in ('Current', 'Selected artwork'):
            pane = ttk.Frame(previews)
            pane.pack(side='left', fill='both', expand=True)
            ttk.Label(pane, text=title).pack()
            label = ttk.Label(pane, anchor='center')
            label.pack(fill='both', expand=True, pady=8)
            self.preview_labels.append(label)
        ttk.Label(right, text='Artwork library').pack(anchor='w', pady=(16, 4))
        self.source = ttk.Combobox(right, state='readonly', width=48)
        self.source.pack(fill='x')
        self.source.bind('<<ComboboxSelected>>', self.select_source)
        self.import_button = ttk.Button(right, text='Import Image…', command=self.import_file)
        self.import_button.pack(anchor='w', pady=8)
        self.candidate_label = ttk.Label(right, wraplength=500)
        self.candidate_label.pack(anchor='w')
        ttk.Label(right, text='Images fit without cropping and use D-Day colors. Flags keep transparency; '
                  'other pictures use the native background color. Previews show the exported result.',
                  wraplength=500, justify='left').pack(anchor='w', pady=(8, 16))
        buttons = ttk.Frame(right)
        buttons.pack(fill='x')
        self.apply_button = ttk.Button(buttons, text='Use Selected Artwork', command=self.apply)
        self.apply_button.pack(side='left')
        self.restore_button = ttk.Button(buttons, text='Restore D-Day Default', command=self.restore)
        self.restore_button.pack(side='left', padx=8)
        self.export_button = ttk.Button(right, text='Export Current Image…', command=self.export_image)
        self.export_button.pack(anchor='w', pady=12)
        self.tree.selection_set(self.key)
        self.select_slot()
        self.refresh()

    def select_slot(self, event=None):
        selected = self.tree.selection()
        if not selected:
            return
        self.key = selected[0]
        slot = self.slots.get(self.key, slot_for(self.key))
        self.heading.config(text=slot.label)
        descriptions = {
            'ship': 'Shared by every ship in this category, on both sides. The 71 × 34 image includes the category label. Choose existing artwork or import a complete replacement button.',
            'air': 'Shared by every squadron in this category on the selected side. Fighters and light bombers share one picture. The 71 × 34 image includes the category label. Artwork does not change the unit’s role.',
            'portrait': 'Shared popup bust, chosen by side and message context. Individual leaders use their own small chits.',
            'flag': 'Used by units and leaders with this nationality setting, at both map sizes. This changes the picture; unit nationality and rules stay as set on Units.',
            'toolbar': 'Side flag in the top toolbar. This is separate from nationality flags on the map; the button frame and flagpole are preserved.',
            'emblem': 'Side emblem used in the game interface.',
            'turn': 'Side artwork displayed when the game changes players.',
            'leader': 'Portrait for this individual leader, shown in place of the nationality flag below the combat ratings. The leader’s chit and controls remain visible. Requires the custom-artwork engine patch.',
            'splash': 'Global startup screen, shown before a scenario is selected. Export for DOS also writes DATA/PCWATW.REZ; copy that file into the game’s DATA folder. It applies to every scenario in that installation.',
        }
        self.description.config(text=descriptions[slot.kind])
        self.options = choices(slot.kind)
        self.source.config(values=[choice.label for choice in self.options],
                           state='readonly' if self.options and self.app.scenario else 'disabled')
        if self.options:
            self.source.current(0)
            self.select_source()
        else:
            self.source.set('Import an image')
            self.candidate = None
            self.draw_previews()

    def select_source(self, event=None):
        index = self.source.current()
        if index < 0:
            return
        try:
            self.candidate = self.options[index].artwork(self.key)
            self.draw_previews()
        except (OSError, ValueError) as exc:
            messagebox.showerror('Cannot Load Artwork', str(exc), parent=self)

    def refresh(self):
        loaded = self.app.scenario is not None
        from lib.unit_roster import UnitRoster
        self.slots = scenario_slots(UnitRoster(self.app._staged_data(include_briefings=False)) if loaded else None)
        for key in self.tree.get_children():
            if key not in self.slots:
                self.tree.delete(key)
        for key, slot in self.slots.items():
            if not self.tree.exists(key):
                self.tree.insert('', 'end', iid=key)
            self.tree.item(key, text=slot.label)
            art = self.app.presentation_artwork.get(key)
            self.tree.set(key, 'artwork', art.name if art else ('No portrait' if slot.kind == 'leader' else 'D-Day default'))
        if self.key not in self.slots:
            self.key = next(iter(self.slots))
            self.tree.selection_set(self.key)
            self.select_slot()
        self.heading.config(text=self.slots[self.key].label)
        self.restore_button.config(text='Remove Portrait' if self.slots[self.key].kind == 'leader' else 'Restore D-Day Default')
        for button in (self.apply_button, self.import_button, self.export_button):
            button.config(state='normal' if loaded else 'disabled')
        self.source.config(state='readonly' if loaded and self.options else 'disabled')
        self.restore_button.config(state='normal' if loaded and self.key in self.app.presentation_artwork else 'disabled')
        self.draw_previews()

    @staticmethod
    def preview(image):
        scale = min(4, 260/image.width, 290/image.height)
        image = image.resize((max(1, round(image.width*scale)), max(1, round(image.height*scale))), Image.Resampling.NEAREST)
        canvas = Image.new('RGB', (270, 300), '#dddddd')
        draw = ImageDraw.Draw(canvas)
        for y in range(0, 300, 10):
            for x in range(0, 270, 10):
                if (x//10+y//10)%2:
                    draw.rectangle((x, y, x+9, y+9), fill='#bbbbbb')
        canvas.paste(image, ((270-image.width)//2, (300-image.height)//2), image)
        return canvas

    def draw_previews(self):
        current = self.app.presentation_artwork.get(self.key) or native_artwork(self.key)
        candidate = self.candidate or current
        self.images = [ImageTk.PhotoImage(self.preview(art.image(self.key)), master=self)
                       for art in (current, candidate)]
        for label, image in zip(self.preview_labels, self.images):
            label.config(image=image)
        self.candidate_label.config(text=f'{candidate.name} · '+
                                    ' / '.join(f'{w} × {h}' for w, h in slot_for(self.key).sizes)+' pixels')
        self.restore_button.config(text='Remove Portrait' if slot_for(self.key).kind == 'leader' else 'Restore D-Day Default')
        self.restore_button.config(state='normal' if self.app.scenario and self.key in self.app.presentation_artwork else 'disabled')
        self.apply_button.config(state='normal' if self.app.scenario and self.candidate is not None else 'disabled')

    def import_file(self):
        filename = filedialog.askopenfilename(parent=self, title='Import Artwork',
                    filetypes=[('Images', '*.png *.bmp *.gif *.jpg *.jpeg *.webp'), ('All files', '*.*')])
        if not filename:
            return
        try:
            self.candidate = import_image(self.key, filename)
            self.source.set('Imported image')
            self.draw_previews()
        except (OSError, ValueError, Image.DecompressionBombError) as exc:
            messagebox.showerror('Cannot Import Artwork', str(exc), parent=self)

    def apply(self):
        if self.candidate is not None:
            self.app.assign_presentation_artwork(self.key, self.candidate)

    def restore(self):
        self.app.assign_presentation_artwork(self.key, None)

    def export_image(self):
        filename = filedialog.asksaveasfilename(parent=self, title='Export Current Artwork',
                    initialfile=self.key+'.png', defaultextension='.png', filetypes=[('PNG image', '*.png')])
        if filename:
            try:
                artwork = self.app.presentation_artwork.get(self.key) or native_artwork(self.key)
                artwork.image(self.key).save(filename, format='PNG')
            except OSError as exc:
                messagebox.showerror('Cannot Export Artwork', str(exc), parent=self)
