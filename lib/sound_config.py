"""Verified D-Day configuration; see txt/SOUND_CONFIGURATION_GUIDE.md.

SYSTEM.SET contains five little-endian words, not music/effects flags.
INVADE.CFG contains two player preference records, not hardware settings.
"""
from dataclasses import dataclass, replace
from pathlib import Path
import shutil
import struct

CARD_NAMES = {0: 'No Sound Card', 1: 'Sound Blaster', 2: 'Gravis UltraSound',
              3: 'Disney Sound Source', 4: 'Pro Audio Spectrum 16'}
RESOLUTIONS = {0x101: '640×480', 0x103: '800×600',
               0x105: '1024×768', 0x107: '1280×1024'}
IRQS = (2, 5, 7)
DMAS = (1, 3, 5, 6, 7)
PORTS = (0x210, 0x220, 0x230, 0x240, 0x250, 0x260, 0x280)
WAV_NAMES = tuple(name + '.WAV' for name in (
    'EDGE DONT EXP_S1 EXP_S2 EXP_S3 EXP_M1 EXP_M2 EXP_M3 EXP_B1 EXP_B2 '
    'EXP_B3 EXP_O1 EXP_O2 EXP_O3 BADPLOT 3SHOTS VICTORY CALENDAR AIR MORSE '
    'HQ LEADER_R LEADER_G FRAMES ASSEMBLY WEATHER MAP GOODCLCK BADCLICK '
    'IM_DONE HES_DONE AMBUSH ROAR RUBBLE').split())


@dataclass(frozen=True)
class Hardware:
    video: int = 0x101
    card: int = 0
    irq: int = 0
    dma: int = 0
    port: int = 0

    @classmethod
    def read(cls, data: bytes):
        if len(data) != 10:
            raise ValueError('SYSTEM.SET must contain exactly 10 bytes.')
        return cls(*struct.unpack('<5H', data))

    def to_bytes(self):
        return struct.pack('<5H', self.video, self.card, self.irq, self.dma, self.port)

    def sound_blaster(self, irq=7, dma=1, port=0x220):
        if irq not in IRQS or dma not in DMAS or port not in PORTS:
            raise ValueError('Use IRQ, DMA and port values supported by D-Day setup.')
        return replace(self, card=1, irq=irq, dma=dma, port=port)


def validate_preferences(data: bytes):
    if len(data) != 66 or struct.unpack_from('<I', data)[0] != 62:
        raise ValueError('Expected D-Day INVADE.CFG: a 62-byte array plus its 4-byte length.')
    if data[4] != 5 or data[35] != 5:
        raise ValueError('Unsupported INVADE.CFG preference version (expected 5).')


def effects_enabled(data: bytes):
    validate_preferences(data)
    return bool(data[13]), bool(data[44])


def set_effects(data: bytes, allies: bool, axis: bool):
    validate_preferences(data)
    result = bytearray(data)
    result[13], result[44] = int(allies), int(axis)
    return bytes(result)


def legacy_port_damage(data: bytes):
    validate_preferences(data)
    return tuple(side for side, offset in enumerate((4, 35))
                 if data[offset:offset + 4] == b'\x05\x01\x20\x02')


def repair_legacy_preferences(data: bytes):
    """Opt-in reset of the two display options corrupted by the old sound tool.

    Their former values cannot be recovered; use native InitPrefs defaults (0).
    """
    result = bytearray(data)
    for side in legacy_port_damage(data):
        offset = 4 + 31 * side
        result[offset + 2:offset + 4] = b'\0\0'
    return bytes(result)


def child(directory: Path, name: str):
    """Resolve a DOS name in a host folder without creating case duplicates."""
    matches = [p for p in directory.iterdir() if p.name.upper() == name.upper()] if directory.is_dir() else []
    if len(matches) > 1:
        raise ValueError(f'Ambiguous DOS filename {name} in {directory}')
    return matches[0] if matches else directory / name


def sound_directory(game_dir: Path):
    return child(child(game_dir, 'DATA'), 'SOUND')


def missing_wavs(game_dir: Path):
    directory = sound_directory(game_dir)
    return [name for name in WAV_NAMES if not child(directory, name).is_file()]


def install_wavs(game_dir: Path):
    """Copy missing legacy SOUND/*.WAV into DATA/SOUND; preserve existing files."""
    source = child(game_dir, 'SOUND')
    target = sound_directory(game_dir)
    copies = [(child(source, name), target / name) for name in missing_wavs(game_dir)]
    missing = [p.name for p, _ in copies if not p.is_file()]
    if missing:
        raise ValueError('Missing WAV sources: ' + ', '.join(missing))
    for src, dst in copies:
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
    return len(copies)
