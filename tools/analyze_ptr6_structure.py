#!/usr/bin/env python3
"""
Analyze PTR6 as a structured format with records
"""
import struct
import sys
sys.path.insert(0, '/src/proj/mods/atomic_ed')
from lib.scenario_parser import DdayScenario

def parse_ptr6_as_records(data, record_size):
    """Try parsing PTR6 as fixed-size records"""
    print(f"\nParsing PTR6 as {record_size}-byte records:")
    print("-"*80)

    num_records = len(data) // record_size
    print(f"Number of complete records: {num_records}")
    print()

    # Show first 10 records
    print(f"First 10 records ({record_size} bytes each):")
    for i in range(min(10, num_records)):
        offset = i * record_size
        record = data[offset:offset+record_size]

        print(f"\nRecord {i} at 0x{offset:04x}:")

        # Show as hex
        hex_str = ' '.join(f'{b:02x}' for b in record)
        print(f"  Hex: {hex_str}")

        # Try different interpretations
        if record_size == 2:
            val = struct.unpack('<H', record)[0]
            print(f"  As uint16: {val} (0x{val:04x})")
        elif record_size == 4:
            val_i = struct.unpack('<I', record)[0]
            val_2h = struct.unpack('<HH', record)
            print(f"  As uint32: {val_i} (0x{val_i:08x})")
            print(f"  As 2×uint16: {val_2h[0]}, {val_2h[1]}")
        elif record_size >= 8:
            # Show as words
            words = []
            for j in range(0, record_size, 2):
                if j+1 < record_size:
                    w = struct.unpack('<H', record[j:j+2])[0]
                    words.append(w)
            print(f"  As words: {', '.join(str(w) for w in words)}")

def look_for_variable_records(data):
    """Try to find variable-length record structure"""
    print("\n\nLooking for variable-length records:")
    print("="*80)

    # Hypothesis: [length_word][data...]

    i = 0
    record_num = 0
    while i + 2 <= len(data) and record_num < 20:
        # Read potential length field
        length = struct.unpack('<H', data[i:i+2])[0]

        # Sanity check - length should be reasonable
        if length == 0:
            # Skip zeros
            zero_count = 0
            while i < len(data) and data[i] == 0:
                i += 1
                zero_count += 1
            if zero_count > 10:
                print(f"\n0x{i-zero_count:04x}: {zero_count} bytes of padding")
            continue

        if length > 1024:  # Too big, probably not a length
            i += 2
            continue

        if i + 2 + length > len(data):  # Would exceed data
            i += 2
            continue

        # Extract record
        record_data = data[i+2:i+2+length]

        print(f"\n0x{i:04x}: Record {record_num}, length={length}")

        # Show first 32 bytes
        hex_str = ' '.join(f'{b:02x}' for b in record_data[:min(32, len(record_data))])
        print(f"  Data: {hex_str}{'...' if len(record_data) > 32 else ''}")

        # Check for patterns
        if length >= 2:
            as_words = []
            for j in range(0, min(length, 16), 2):
                if j+1 < length:
                    w = struct.unpack('<H', record_data[j:j+2])[0]
                    as_words.append(w)
            print(f"  As words: {', '.join(str(w) for w in as_words)}")

        i += 2 + length
        record_num += 1

def check_for_coordinate_data(data):
    """Check if PTR6 contains map coordinate data"""
    print("\n\nChecking for coordinate-like data:")
    print("="*80)

    # Look for pairs of values in map range (0-125, 0-100)
    coordinate_pairs = []

    for i in range(0, min(len(data) - 4, 4096), 2):
        if i + 3 < len(data):
            x = struct.unpack('<H', data[i:i+2])[0]
            y = struct.unpack('<H', data[i+2:i+4])[0]

            # Check if these look like map coordinates
            if 0 < x <= 125 and 0 < y <= 100:
                coordinate_pairs.append((i, x, y))

    print(f"\nFound {len(coordinate_pairs)} potential coordinate pairs (x≤125, y≤100)")
    print("\nFirst 20:")
    for offset, x, y in coordinate_pairs[:20]:
        print(f"  0x{offset:04x}: ({x:3d}, {y:3d})")

def check_for_compressed_data(data):
    """Check if PTR6 might be compressed"""
    print("\n\nCompression Detection:")
    print("="*80)

    # Calculate entropy
    byte_counts = [0] * 256
    for b in data[:min(len(data), 8192)]:
        byte_counts[b] += 1

    # Shannon entropy
    import math
    total = sum(byte_counts)
    entropy = 0.0
    for count in byte_counts:
        if count > 0:
            p = count / total
            entropy -= p * math.log2(p)

    print(f"Shannon entropy: {entropy:.3f} bits/byte")
    print(f"Max entropy (random): 8.000 bits/byte")
    print(f"Typical text: ~4.5 bits/byte")
    print(f"Compressed data: ~7.5+ bits/byte")

    if entropy > 7.5:
        print("\n→ HIGH entropy suggests compressed or encrypted data")
    elif entropy > 5.5:
        print("\n→ MODERATE entropy suggests structured binary data")
    else:
        print("\n→ LOW entropy suggests repetitive or simple data")

def main():
    print("="*80)
    print("PTR6 STRUCTURE ANALYSIS")
    print("="*80)

    scn = DdayScenario('/src/proj/mods/atomic_ed/game/SCENARIO/CAMPAIGN.SCN')
    ptr6_data = scn.sections.get('PTR6', b'')

    if not ptr6_data:
        print("No PTR6 data!")
        return

    print(f"\nPTR6 size: {len(ptr6_data)} bytes\n")

    # Try different interpretations
    check_for_compressed_data(ptr6_data)
    check_for_coordinate_data(ptr6_data)
    look_for_variable_records(ptr6_data)

    # Try fixed-size records
    for size in [2, 4, 8, 16, 32]:
        parse_ptr6_as_records(ptr6_data, size)

if __name__ == '__main__':
    main()
