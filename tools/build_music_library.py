#!/usr/bin/env python3
"""Extract V4V's original FM performances using its native 16-bit sequencer.

This runs only the verified music routines under Unicorn, recording AdLib
register writes at the sequencer's 100 Hz tick rate. No DOS files are executed
on the host, and no approximate MIDI instrument mapping is used.
"""
from pathlib import Path
import hashlib
import struct
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from lib.v4v_reader import read_resources
from unicorn import Uc, UC_ARCH_X86, UC_MODE_16, UC_HOOK_INSN
from unicorn.x86_const import (UC_X86_REG_DS, UC_X86_REG_ES, UC_X86_REG_SS,
    UC_X86_REG_CS, UC_X86_REG_IP, UC_X86_REG_SP, UC_X86_REG_AX,
    UC_X86_INS_OUT, UC_X86_INS_IN)


SOURCE_SHA256 = '9918b8011aeb5366b8b8019e9a43f0b6e66331be585b078e348a79ee60b207d1'


def trace_song(executable, song):
    if hashlib.sha256(executable).hexdigest() != SOURCE_SHA256:
        raise ValueError('Unsupported V4V executable: sequencer addresses require the verified version')
    if len(song) < 24 or struct.unpack_from('<H', song)[0] != len(song)-2:
        raise ValueError('Invalid native song resource')
    last, pages, relocations, paragraphs = struct.unpack_from('<4H', executable, 2)
    end, header = (pages-1)*512 + (last or 512), paragraphs*16
    data = bytearray(executable[header:end])
    table = struct.unpack_from('<H', executable, 24)[0]
    for index in range(relocations):
        off, seg = struct.unpack_from('<HH', executable, table+4*index)
        pos = seg*16+off
        struct.pack_into('<H', data, pos, (struct.unpack_from('<H', data, pos)[0]+0x1000)&0xffff)
    cpu = Uc(UC_ARCH_X86, UC_MODE_16)
    cpu.mem_map(0, 0x100000)
    cpu.mem_write(0x10000, bytes(data))
    cpu.mem_write(0x90000, song[2:])  # Native resource manager strips length word.
    for reg, value in ((UC_X86_REG_DS,0x2541), (UC_X86_REG_ES,0x2541), (UC_X86_REG_SS,0x8000)):
        cpu.reg_write(reg, value)
    events, tick, register, timer = [], 0, 0, False

    def output(_cpu, port, size, value, _):
        nonlocal register, timer
        if size != 1:
            raise ValueError('Unexpected wide port write')
        if port == 0x388:
            register = value
        elif port == 0x389:
            if register == 4:
                timer = value == 0x21
            # Omit detection timer programming; retain musical chip writes.
            if register in (1, 8) or 0x20 <= register <= 0xf5:
                events.append((tick, register, value))
        else:
            raise ValueError(f'Unexpected sequencer output port {port:x}')

    def input_port(_cpu, port, size, _):
        if port != 0x388 or size != 1:
            raise ValueError('Unexpected sequencer input port')
        return 0xc0 if timer else 0  # AdLib detection timer status.

    cpu.hook_add(UC_HOOK_INSN, output, None, 1, 0, UC_X86_INS_OUT)
    cpu.hook_add(UC_HOOK_INSN, input_port, None, 1, 0, UC_X86_INS_IN)

    def call(offset, args=()):
        cpu.reg_write(UC_X86_REG_CS, 0x1544)
        cpu.reg_write(UC_X86_REG_IP, offset)
        cpu.reg_write(UC_X86_REG_SP, 0xfe00)
        cpu.mem_write(0x8fe00, struct.pack('<'+'H'*(2+len(args)), 0, 0xf000, *args))
        cpu.emu_start(0x15440+offset, 0xf0000, count=1000000)
        if cpu.reg_read(UC_X86_REG_CS) != 0xf000:
            raise ValueError('Native sequencer did not return within its instruction limit')
        return cpu.reg_read(UC_X86_REG_AX)

    if call(0x573, (0, 0x9000)) != 0:
        raise ValueError('Native song initialization failed')
    for tick in range(1, 60001):
        if call(0xc95):
            return events, tick
    raise ValueError('Native song exceeded ten minutes')


def encode_performance(events, end_tick):
    if not events or not any(0xb0 <= reg <= 0xb8 and value & 0x20 for _, reg, value in events):
        raise ValueError('Song contains no melodic notes')
    result = bytearray()
    for i, (tick, register, value) in enumerate(events):
        delay = (events[i+1][0] if i+1 < len(events) else end_tick+200) - tick
        if not 0 <= delay <= 65535:
            raise ValueError('Unsupported event delay')
        result += struct.pack('<BBH', register, value, delay)
    return bytes(result)


def build():
    source = ROOT/'game/v4v/V4V.EXE'
    executable = source.read_bytes()
    resources = read_resources(ROOT/'game/v4v/V4V.RES')
    payload = bytearray()
    # 1–5 are short cues/fanfares. 6–10 are the background pieces.
    for number in range(6, 11):
        events, ticks = trace_song(executable, resources['song', number])
        payload += encode_performance(events, ticks)
        print(f'V4V song {number}: {ticks/100:.2f}s, {len(events)} register writes')
    destination = ROOT/'assets/music/V4V.OPL'
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(b'WAM1'+struct.pack('<HHI',100,0,len(payload)//4)+payload)
    print(f'{destination}: {len(payload)+12} bytes')
    print('Source EXE SHA256:', hashlib.sha256(executable).hexdigest())
    return destination


if __name__ == '__main__':
    build()
