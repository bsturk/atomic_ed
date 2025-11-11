#!/usr/bin/env python3
"""
Deep analysis of PTR6 AI/game parameter structure
"""
import struct
import sys
import glob
sys.path.insert(0, '/src/proj/mods/atomic_ed')
from lib.scenario_parser import DdayScenario

def analyze_ptr6_header(data):
    """Analyze the first part of PTR6 which might be header/metadata"""
    print("PTR6 Header Analysis (first 256 bytes)")
    print("="*80)

    if len(data) < 256:
        print(f"PTR6 too small: {len(data)} bytes")
        return

    # Show as 16-bit values
    print("\nAs 16-bit little-endian values:")
    print("-"*80)
    for i in range(0, 256, 16):
        offset = f"0x{i:04x}:"
        values = []
        for j in range(i, min(i+16, 256), 2):
            if j+1 < len(data):
                val = struct.unpack('<H', data[j:j+2])[0]
                values.append(f"{val:5d}")
        print(f"{offset:8s} {' '.join(values)}")

    # Look for patterns
    print("\n\nPattern Detection:")
    print("-"*80)

    # Check for counts/sizes
    val_0 = struct.unpack('<H', data[0:2])[0] if len(data) >= 2 else 0
    val_2 = struct.unpack('<H', data[2:4])[0] if len(data) >= 4 else 0
    val_4 = struct.unpack('<H', data[4:6])[0] if len(data) >= 6 else 0
    val_6 = struct.unpack('<H', data[6:8])[0] if len(data) >= 8 else 0

    print(f"Word at 0x00: {val_0:5d} (0x{val_0:04x})")
    print(f"Word at 0x02: {val_2:5d} (0x{val_2:04x})")
    print(f"Word at 0x04: {val_4:5d} (0x{val_4:04x})")
    print(f"Word at 0x06: {val_6:5d} (0x{val_6:04x})")

    # Look for repeating byte patterns
    print("\n\nRepeating Patterns:")
    print("-"*80)

    # Find runs of 0x01 0x00 (little-endian 1)
    i = 0
    while i < 256:
        if i+1 < len(data) and data[i:i+2] == b'\x01\x00':
            run_start = i
            run_count = 0
            while i+1 < len(data) and data[i:i+2] == b'\x01\x00':
                run_count += 1
                i += 2
            if run_count > 3:
                print(f"  0x{run_start:04x}: Run of {run_count} × 0x0001 (value 1)")
        else:
            i += 1

def find_command_structures(data):
    """Try to identify command/parameter structures"""
    print("\n\nCommand Structure Analysis")
    print("="*80)

    # Hypothesis: Commands might be byte-aligned with parameters following
    # Look for patterns where a byte value is followed by consistent structure

    command_patterns = {}

    i = 0
    while i < min(len(data), 4096):  # Analyze first 4KB
        if i + 4 >= len(data):
            break

        # Try treating as [cmd_byte][2-byte param][...]
        cmd = data[i]

        if cmd in command_patterns:
            command_patterns[cmd] += 1
        else:
            command_patterns[cmd] = 1

        # Try to determine parameter size
        # Skip ahead based on common patterns
        if cmd == 0x00:
            # Skip zeros
            while i < len(data) and data[i] == 0x00:
                i += 1
        elif cmd < 0x10:
            # Small commands might have fixed size params
            i += 3  # cmd + 2 byte param
        else:
            i += 1

    print(f"\nCommand byte frequency (first 4KB):")
    print("-"*80)

    # Sort by frequency
    sorted_cmds = sorted(command_patterns.items(), key=lambda x: x[1], reverse=True)

    for cmd, count in sorted_cmds[:20]:
        print(f"  0x{cmd:02x}: {count:4d} occurrences")

def analyze_repeating_sequences(data):
    """Find commonly repeating byte sequences"""
    print("\n\nRepeating Byte Sequence Analysis")
    print("="*80)

    # Look for 2-byte, 4-byte, and 8-byte sequences that repeat
    for seq_len in [2, 4, 8]:
        print(f"\n{seq_len}-byte sequences:")
        print("-"*80)

        sequences = {}
        i = 0
        while i + seq_len <= min(len(data), 4096):
            seq = data[i:i+seq_len]

            # Skip all-zero sequences
            if seq == b'\x00' * seq_len:
                i += seq_len
                continue

            if seq in sequences:
                sequences[seq] += 1
            else:
                sequences[seq] = 1

            i += seq_len

        # Show top repeating sequences
        sorted_seqs = sorted(sequences.items(), key=lambda x: x[1], reverse=True)

        for seq, count in sorted_seqs[:10]:
            if count > 2:  # Only show if repeats at least 3 times
                hex_str = ' '.join(f'{b:02x}' for b in seq)

                # Try to interpret as values
                if seq_len == 2:
                    val = struct.unpack('<H', seq)[0]
                    print(f"  [{hex_str}] = {val:5d} decimal, appears {count} times")
                elif seq_len == 4:
                    val = struct.unpack('<I', seq)[0]
                    print(f"  [{hex_str}] = {val:10d} decimal, appears {count} times")
                else:
                    print(f"  [{hex_str}] appears {count} times")

def compare_ptr6_across_scenarios():
    """Compare PTR6 structure across all scenarios"""
    print("\n\nCross-Scenario PTR6 Comparison")
    print("="*80)

    scenarios = sorted(glob.glob('/src/proj/mods/atomic_ed/game/SCENARIO/*.SCN'))

    all_ptr6 = {}

    for scn_file in scenarios:
        name = scn_file.split('/')[-1]
        scn = DdayScenario(scn_file)
        ptr6_data = scn.sections.get('PTR6', b'')
        all_ptr6[name] = ptr6_data

    # Compare first 64 bytes across scenarios
    print("\nFirst 32 16-bit words across scenarios:")
    print("-"*80)
    print(f"{'Offset':<10s}", end='')
    for name in sorted(all_ptr6.keys()):
        print(f"{name:<15s}", end='')
    print()
    print("-"*80)

    for i in range(0, 64, 2):
        print(f"0x{i:04x}    ", end='')
        for name in sorted(all_ptr6.keys()):
            data = all_ptr6[name]
            if i+1 < len(data):
                val = struct.unpack('<H', data[i:i+2])[0]
                print(f"{val:<15d}", end='')
            else:
                print(f"{'---':<15s}", end='')
        print()

    # Look for common header structure
    print("\n\nLooking for common patterns in PTR6 start:")
    print("-"*80)

    # Check if first word is a count or size
    for name in sorted(all_ptr6.keys()):
        data = all_ptr6[name]
        if len(data) >= 8:
            w0 = struct.unpack('<H', data[0:2])[0]
            w1 = struct.unpack('<H', data[2:4])[0]
            w2 = struct.unpack('<H', data[4:6])[0]
            w3 = struct.unpack('<H', data[6:8])[0]

            print(f"{name:<15s} words: {w0:5d} {w1:5d} {w2:5d} {w3:5d}")

def main():
    # Analyze CAMPAIGN.SCN as primary example (largest PTR6)
    print("="*80)
    print("PTR6 AI/GAME PARAMETER DEEP ANALYSIS")
    print("="*80)
    print()

    scn = DdayScenario('/src/proj/mods/atomic_ed/game/SCENARIO/CAMPAIGN.SCN')
    ptr6_data = scn.sections.get('PTR6', b'')

    if not ptr6_data:
        print("No PTR6 data found!")
        return

    print(f"Total PTR6 size: {len(ptr6_data)} bytes\n")

    analyze_ptr6_header(ptr6_data)
    find_command_structures(ptr6_data)
    analyze_repeating_sequences(ptr6_data)
    compare_ptr6_across_scenarios()

if __name__ == '__main__':
    main()
