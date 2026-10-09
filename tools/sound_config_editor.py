#!/usr/bin/env python3
"""Edit verified D-Day hardware and per-player sound-effect settings."""
import argparse
from dataclasses import replace
from pathlib import Path
import sys
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lib.sound_config import (Hardware, CARD_NAMES, RESOLUTIONS, IRQS, DMAS,
    PORTS, child, effects_enabled, set_effects, missing_wavs, install_wavs,
    legacy_port_damage, repair_legacy_preferences)


class SoundConfigEditor:
    def __init__(self, root, game_dir=None):
        self.root = root
        self.game_dir = None
        self.hardware = Hardware()
        self.prefs = None
        self.card = tk.StringVar(value=CARD_NAMES[0])
        self.irq = tk.StringVar(value='7')
        self.dma = tk.StringVar(value='1')
        self.port = tk.StringVar(value='220')
        self.effects = [tk.BooleanVar(value=True), tk.BooleanVar(value=True)]
        self.path_text = tk.StringVar(value='Choose a D-Day playing directory.')
        self.video_text = tk.StringVar()
        self.status = tk.StringVar()
        self.root.title('D-Day Sound Configuration')
        frame = ttk.Frame(root, padding=16)
        frame.pack(fill='both', expand=True)
        ttk.Label(frame, textvariable=self.path_text).pack(anchor='w')
        ttk.Button(frame, text='Choose game directory…', command=self.browse).pack(anchor='w', pady=8)
        hardware = ttk.LabelFrame(frame, text='Sound hardware — SYSTEM.SET', padding=10)
        hardware.pack(fill='x')
        for row, (label, variable, values) in enumerate((
            ('Card', self.card, (CARD_NAMES[0], CARD_NAMES[1])),
            ('IRQ', self.irq, IRQS), ('DMA', self.dma, DMAS),
            ('Port (hex)', self.port, [f'{p:03X}' for p in PORTS]))):
            ttk.Label(hardware, text=label).grid(row=row, column=0, sticky='w', padx=5, pady=3)
            ttk.Combobox(hardware, textvariable=variable, values=values,
                         state='readonly', width=28).grid(row=row, column=1, sticky='w')
        ttk.Label(hardware, textvariable=self.video_text).grid(row=4, column=0, columnspan=2, sticky='w', pady=6)
        ttk.Button(hardware, text='Sound Blaster: 220 / IRQ 7 / DMA 1',
                   command=self.defaults).grid(row=5, column=0, columnspan=2, sticky='w')
        prefs = ttk.LabelFrame(frame, text='Sound effects — INVADE.CFG', padding=10)
        prefs.pack(fill='x', pady=10)
        self.effect_buttons = []
        for name, variable in zip(('Allies', 'Axis'), self.effects):
            button = ttk.Checkbutton(prefs, text=name, variable=variable)
            button.pack(anchor='w')
            self.effect_buttons.append(button)
        ttk.Label(frame, text='Match IRQ, DMA and port to DOSBox or your sound card.\n'
                  'Background music: install the music patch and V4V.OPL, then use Options in the game.').pack(anchor='w')
        buttons = ttk.Frame(frame)
        buttons.pack(fill='x', pady=10)
        self.save_button = ttk.Button(buttons, text='Save settings', command=self.save, state='disabled')
        self.save_button.pack(side='left')
        self.wav_button = ttk.Button(buttons, text='Copy missing WAV files', command=self.copy_wavs, state='disabled')
        self.wav_button.pack(side='left', padx=8)
        self.repair_button = ttk.Button(frame, text='Reset display options damaged by the old sound tool',
                                       command=self.repair, state='disabled')
        self.repair_button.pack(anchor='w')
        ttk.Label(frame, textvariable=self.status, wraplength=520).pack(anchor='w', pady=10)
        if game_dir is not None:
            self.load(Path(game_dir))

    def browse(self):
        path = filedialog.askdirectory(title='D-Day playing directory', parent=self.root)
        if path:
            self.load(Path(path))

    def load(self, game):
        try:
            if not game.is_dir():
                raise ValueError(f'Not a directory: {game}')
            system = child(game, 'SYSTEM.SET')
            cfg = child(game, 'INVADE.CFG')
            hardware = Hardware.read(system.read_bytes()) if system.exists() else Hardware()
            prefs = cfg.read_bytes() if cfg.exists() else None
            enabled = effects_enabled(prefs) if prefs is not None else (True, True)
            missing = missing_wavs(game)
        except (OSError, ValueError) as exc:
            messagebox.showerror('Cannot load settings', str(exc), parent=self.root)
            return
        self.game_dir, self.hardware, self.prefs = game, hardware, prefs
        self.path_text.set(str(game))
        self.card.set(CARD_NAMES.get(hardware.card, f'Card {hardware.card}'))
        self.irq.set(str(hardware.irq))
        self.dma.set(str(hardware.dma))
        self.port.set(f'{hardware.port:03X}')
        self.video_text.set('Resolution: ' + RESOLUTIONS.get(hardware.video, hex(hardware.video)))
        for variable, value, button in zip(self.effects, enabled, self.effect_buttons):
            variable.set(value)
            button.configure(state='normal' if prefs is not None else 'disabled')
        self.save_button.configure(state='normal')
        self.wav_button.configure(state='normal')
        damaged = prefs is not None and legacy_port_damage(prefs)
        self.repair_button.configure(state='normal' if damaged else 'disabled')
        status = f'DATA/SOUND: {34 - len(missing)}/34 WAV files present.'
        if prefs is None:
            status += ' INVADE.CFG is absent; the game creates defaults with effects enabled.'
        if damaged:
            status += ' Old sound-tool damage detected in display options.'
        self.status.set(status)

    def defaults(self):
        self.card.set(CARD_NAMES[1])
        self.irq.set('7')
        self.dma.set('1')
        self.port.set('220')

    def save(self):
        if self.game_dir is None:
            return
        try:
            hardware = self.hardware
            if self.card.get() == CARD_NAMES[1]:
                hardware = hardware.sound_blaster(int(self.irq.get()), int(self.dma.get()), int(self.port.get(), 16))
            elif self.card.get() == CARD_NAMES[0]:
                hardware = replace(hardware, card=0)
            # Other existing cards remain intact; configure those through /SETUP.
            prefs = set_effects(self.prefs, *(v.get() for v in self.effects)) if self.prefs is not None else None
            child(self.game_dir, 'SYSTEM.SET').write_bytes(hardware.to_bytes())
            if prefs is not None:
                child(self.game_dir, 'INVADE.CFG').write_bytes(prefs)
            self.hardware, self.prefs = hardware, prefs
            self.status.set('Settings saved. Restart the game to use them.')
        except (OSError, ValueError) as exc:
            messagebox.showerror('Cannot save settings', str(exc), parent=self.root)

    def copy_wavs(self):
        if self.game_dir is None:
            return
        try:
            count = install_wavs(self.game_dir)
            self.status.set(f'Copied {count} missing WAV files into DATA/SOUND. Restart DOSBox to refresh its file cache.')
        except (OSError, ValueError) as exc:
            messagebox.showerror('Cannot copy sound files', str(exc), parent=self.root)

    def repair(self):
        if self.prefs is not None:
            self.prefs = repair_legacy_preferences(self.prefs)
            self.repair_button.configure(state='disabled')
            self.status.set('Damaged display options reset to native defaults. Click Save settings to apply.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--game-dir', type=Path)
    args = parser.parse_args()
    root = tk.Tk()
    SoundConfigEditor(root, args.game_dir)
    root.mainloop()


if __name__ == '__main__':
    main()
