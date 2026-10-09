#!/usr/bin/env python3
"""Inspect or repair D-Day audio in an explicitly selected playing copy."""
import argparse
from pathlib import Path
import shutil
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lib.sound_config import (Hardware, CARD_NAMES, RESOLUTIONS, IRQS, DMAS,
    PORTS, child, effects_enabled, set_effects, missing_wavs, install_wavs,
    legacy_port_damage, repair_legacy_preferences)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--game-dir', type=Path, required=True,
                        help='Playing directory containing INVADE.EXE')
    parser.add_argument('--analyze', action='store_true', help='Inspect (the default)')
    parser.add_argument('--fix', action='store_true',
                        help='Configure Sound Blaster, enable effects, and copy missing WAVs into DATA/SOUND')
    parser.add_argument('--enable', action='store_true', help='Enable effects for both players in INVADE.CFG')
    parser.add_argument('--set-defaults', action='store_true', help='Configure Sound Blaster in SYSTEM.SET')
    parser.add_argument('--install-wavs', action='store_true', help='Copy missing SOUND/*.WAV into DATA/SOUND')
    parser.add_argument('--repair-legacy-preferences', action='store_true',
                        help='Reset display options corrupted by the old sound tool to native defaults')
    parser.add_argument('--irq', type=int, choices=IRQS, default=7)
    parser.add_argument('--dma', type=int, choices=DMAS, default=1)
    parser.add_argument('--port', type=lambda s: int(s, 16), choices=PORTS, default=0x220,
                        help='Hexadecimal base address (default: 220)')
    parser.add_argument('--backup', action='store_true', help='Opt in to .bak configuration backups')
    args = parser.parse_args(argv)
    try:
        game = args.game_dir
        if not game.is_dir():
            raise ValueError(f'Game directory does not exist: {game}')
        system_path, prefs_path = child(game, 'SYSTEM.SET'), child(game, 'INVADE.CFG')
        hardware = Hardware.read(system_path.read_bytes()) if system_path.exists() else Hardware()
        prefs = prefs_path.read_bytes() if prefs_path.exists() else None
        if prefs is not None:
            effects_enabled(prefs)  # Validate before any write.
        if args.fix or args.set_defaults:
            hardware = hardware.sound_blaster(args.irq, args.dma, args.port)
        if (args.fix or args.enable) and prefs is not None:
            prefs = set_effects(prefs, True, True)
        if args.repair_legacy_preferences and prefs is not None:
            prefs = repair_legacy_preferences(prefs)
        writes = {}
        if args.fix or args.set_defaults:
            writes[system_path] = hardware.to_bytes()
        if (args.fix or args.enable or args.repair_legacy_preferences) and prefs is not None:
            writes[prefs_path] = prefs
        writes = {p: d for p, d in writes.items() if not p.exists() or p.read_bytes() != d}
        if args.backup:
            for path in writes:
                backup = path.with_suffix(path.suffix + '.bak')
                if path.exists() and backup.exists():
                    raise ValueError(f'Backup already exists: {backup}; preserve it or omit --backup.')
        if args.fix or args.install_wavs:
            print(f'Copied {install_wavs(game)} WAV files into DATA/SOUND.')
        for path, data in writes.items():
            if args.backup and path.exists():
                shutil.copy2(path, path.with_suffix(path.suffix + '.bak'))
            path.write_bytes(data)
            print(f'Updated {path.name}.')
        print(f'Resolution: {RESOLUTIONS.get(hardware.video, hex(hardware.video))}')
        print(f'Sound card: {CARD_NAMES.get(hardware.card, hardware.card)}; '
              f'port {hardware.port:03X}, IRQ {hardware.irq}, DMA {hardware.dma}')
        if prefs is None:
            print('INVADE.CFG absent: the game creates defaults with effects enabled.')
        else:
            print('Effects (Allies, Axis): ' + ', '.join('on' if v else 'off' for v in effects_enabled(prefs)))
            if legacy_port_damage(prefs):
                print('Old sound-tool damage detected in display preferences; '
                      '--repair-legacy-preferences resets those options to native defaults.')
        missing = missing_wavs(game)
        print('DATA/SOUND: ' + (f'missing {len(missing)} of 34 WAV files' if missing else 'all 34 WAV files present'))
        print('Match SYSTEM.SET to DOSBox [sblaster] settings; restart DOSBox after file changes.')
        print('Background music requires the music patch and DATA/MUSIC/V4V.OPL; toggle it in Options.')
    except (OSError, ValueError) as exc:
        parser.exit(1, f'Error: {exc}\n')


if __name__ == '__main__':
    main()
