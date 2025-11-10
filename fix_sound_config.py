#!/usr/bin/env python3
"""
Sound Configuration Fixer for INVADE.EXE

This tool helps diagnose and fix sound configuration issues with the
World at War: America Invades! game.

Based on analysis of INVADE.CFG and SYSTEM.SET files.
"""

import struct
import sys
from pathlib import Path

class SoundConfigFixer:
    def __init__(self, game_dir="game"):
        self.game_dir = Path(game_dir)
        self.invade_cfg = self.game_dir / "INVADE.CFG"
        self.system_set = self.game_dir / "SYSTEM.SET"

    def analyze_config(self):
        """Analyze current configuration files"""
        print("=" * 80)
        print("SOUND CONFIGURATION ANALYSIS")
        print("=" * 80)
        print()

        # Read SYSTEM.SET
        with open(self.system_set, 'rb') as f:
            system_data = f.read()

        print("SYSTEM.SET (10 bytes):")
        print(f"  Music Enabled:    {system_data[0]} {'✓ ON' if system_data[0] else '✗ OFF'}")
        print(f"  Sound FX Enabled: {system_data[1]} {'✓ ON' if system_data[1] else '✗ OFF'}")
        print()

        # Read INVADE.CFG
        with open(self.invade_cfg, 'rb') as f:
            cfg_data = f.read()

        print("INVADE.CFG (66 bytes):")
        print()
        print("  Block 1 (Sound FX - bytes 0-32):")
        print(f"    Header:   {' '.join(f'{b:02x}' for b in cfg_data[0:4])}")
        port1 = int.from_bytes(cfg_data[6:8], 'little')
        print(f"    Port:     0x{port1:04x} ({port1})")
        print(f"    IRQ:      {cfg_data[4]}")
        print(f"    DMA:      {cfg_data[5]}")
        print()
        print("  Block 2 (Music - bytes 33-65):")
        print(f"    Marker:   0x{cfg_data[34]:02x} ('{chr(cfg_data[34])}')")
        port2 = int.from_bytes(cfg_data[37:39], 'little')
        print(f"    Port:     0x{port2:04x} ({port2})")
        print(f"    IRQ:      {cfg_data[35]}")
        print(f"    DMA:      {cfg_data[36]}")
        print()

        # Analyze issues
        issues = []

        if system_data[0] == 0:
            issues.append("Music is DISABLED in SYSTEM.SET")
        if system_data[1] == 0:
            issues.append("Sound FX is DISABLED in SYSTEM.SET")

        # Check for reasonable SoundBlaster settings
        port1 = int.from_bytes(cfg_data[6:8], 'little')
        port2 = int.from_bytes(cfg_data[37:39], 'little')

        if port1 != 0x220:
            issues.append(f"Block 1 Port 0x{port1:04x} is WRONG (should be 0x0220 / 544)")
        if port2 != 0x220:
            issues.append(f"Block 2 Port 0x{port2:04x} is WRONG (should be 0x0220 / 544)")

        if cfg_data[4] not in [2, 5, 7, 10]:
            issues.append(f"Block 1 IRQ {cfg_data[4]} is unusual (typical: 5 or 7)")
        if cfg_data[5] not in [0, 1, 3]:
            issues.append(f"Block 1 DMA {cfg_data[5]} is unusual (typical: 1)")
        if cfg_data[35] not in [2, 5, 7, 10]:
            issues.append(f"Block 2 IRQ {cfg_data[35]} is unusual (typical: 5 or 7)")
        if cfg_data[36] not in [0, 1, 3]:
            issues.append(f"Block 2 DMA {cfg_data[36]} is unusual (typical: 1)")

        if issues:
            print("⚠️  POTENTIAL ISSUES:")
            for issue in issues:
                print(f"    - {issue}")
        else:
            print("✓ Configuration looks reasonable")

        print()
        return system_data, cfg_data, issues

    def enable_sound(self):
        """Enable both music and sound FX in SYSTEM.SET"""
        with open(self.system_set, 'rb') as f:
            data = bytearray(f.read())

        data[0] = 1  # Enable music
        data[1] = 1  # Enable sound FX

        with open(self.system_set, 'wb') as f:
            f.write(data)

        print("✓ Enabled music and sound FX in SYSTEM.SET")

    def set_soundblaster_defaults(self):
        """Set default SoundBlaster settings (Port 220h, IRQ 5, DMA 1)"""
        with open(self.invade_cfg, 'rb') as f:
            data = bytearray(f.read())

        # Port 220h as 16-bit little-endian
        port_220h = (0x220).to_bytes(2, 'little')

        # Block 1 (Sound FX)
        data[4] = 5   # IRQ 5
        data[5] = 1   # DMA 1
        data[6:8] = port_220h  # Port 220h

        # Block 2 (Music)
        data[35] = 5  # IRQ 5
        data[36] = 1  # DMA 1
        data[37:39] = port_220h  # Port 220h

        with open(self.invade_cfg, 'wb') as f:
            f.write(data)

        print("✓ Set SoundBlaster defaults (Port 220h, IRQ 5, DMA 1) in INVADE.CFG")

    def backup_configs(self):
        """Create backups of config files"""
        import shutil

        for cfg in [self.invade_cfg, self.system_set]:
            backup = cfg.with_suffix(cfg.suffix + '.bak')
            shutil.copy2(cfg, backup)
            print(f"✓ Backed up {cfg.name} to {backup.name}")

    def show_recommendations(self):
        """Show recommendations for fixing sound"""
        print()
        print("=" * 80)
        print("RECOMMENDATIONS")
        print("=" * 80)
        print()
        print("1. RUN THE GAME'S SETUP UTILITY:")
        print("   In DOSBox:")
        print("     - cd game")
        print("     - INVADE.EXE /SETUP")
        print("   Select:")
        print("     - Sound Card: SoundBlaster")
        print("     - Port: 220h (544)")
        print("     - IRQ: 5")
        print("     - DMA: 1")
        print()
        print("2. SET BLASTER ENVIRONMENT VARIABLE:")
        print("   In DOSBox config file [autoexec] section:")
        print("     SET BLASTER=A220 I5 D1 T4")
        print()
        print("3. USE THIS TOOL TO FIX CONFIG FILES:")
        print("   python3 fix_sound_config.py --enable")
        print("   python3 fix_sound_config.py --set-defaults")
        print()
        print("4. CHECK DOSBOX SOUND SETTINGS:")
        print("   In dosbox.conf [sblaster] section:")
        print("     sbtype=sb16")
        print("     sbbase=220")
        print("     irq=5")
        print("     dma=1")
        print()

def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Fix sound configuration for INVADE.EXE"
    )
    parser.add_argument(
        '--analyze', action='store_true',
        help='Analyze current configuration (default)'
    )
    parser.add_argument(
        '--enable', action='store_true',
        help='Enable music and sound FX in SYSTEM.SET'
    )
    parser.add_argument(
        '--set-defaults', action='store_true',
        help='Set default SoundBlaster settings (IRQ 5, DMA 1)'
    )
    parser.add_argument(
        '--backup', action='store_true',
        help='Create backups before making changes'
    )
    parser.add_argument(
        '--game-dir', default='game',
        help='Path to game directory (default: game)'
    )

    args = parser.parse_args()

    fixer = SoundConfigFixer(args.game_dir)

    # Always show analysis first
    fixer.analyze_config()

    # Make changes if requested
    if args.backup and (args.enable or args.set_defaults):
        fixer.backup_configs()
        print()

    if args.enable:
        fixer.enable_sound()
        print()

    if args.set_defaults:
        fixer.set_soundblaster_defaults()
        print()

    # Show recommendations
    fixer.show_recommendations()

if __name__ == '__main__':
    main()
