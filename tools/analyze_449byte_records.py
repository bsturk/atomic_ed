#!/usr/bin/env python3
"""
Focus on the 449-byte records which appear 86 times
"""
import struct
import sys
sys.path.insert(0, '/src/proj/mods/atomic_ed')
from lib.scenario_parser import DdayScenario

def parse_ptr6_records(data):
    """Parse PTR6 as variable-length records"""
    records = []
    i = 0

    while i + 2 <= len(data):
        length = struct.unpack('<H', data[i:i+2])[0]

        if length == 0:
            zero_start = i
            while i < len(data) and data[i] == 0:
                i += 1
            continue

        if length > 2048 or i + 2 + length > len(data):
            i += 2
            continue

        record_data = data[i+2:i+2+length]

        records.append({
            'offset': i,
            'length': length,
            'data': record_data
        })

        i += 2 + length

    return records

def analyze_449_byte_record(data):
    """Analyze structure of a 449-byte record"""
    if len(data) != 449:
        return None

    # Try to find structure
    # 449 = 0x1C1

    # Parse as 16-bit values
    words = []
    for i in range(0, min(len(data), 100), 2):  # First 50 words
        w = struct.unpack('<H', data[i:i+2])[0]
        words.append(w)

    # Look for header pattern
    info = {
        'first_32_words': words[:32],
        'patterns': []
    }

    # Check if there's a consistent header
    # Common pattern: first word is often 0xC100 (449 in different endian? or flags?)
    first_word = struct.unpack('<H', data[0:2])[0] if len(data) >= 2 else 0

    # Check for all-zero or all-one runs
    for i in range(0, len(data)-4, 2):
        w = struct.unpack('<H', data[i:i+2])[0]
        if w == 0xC100 or w == 0xC140 or w == 0xC150:
            info['patterns'].append(f'Special marker 0x{w:04x} at offset {i}')

    # Check last few bytes
    info['last_16_bytes'] = [f'{b:02x}' for b in data[-16:]]

    return info

def main():
    print("="*80)
    print("ANALYZING 449-BYTE RECORDS")
    print("="*80)

    # Load OMAHA which has many of these
    scn = DdayScenario('/src/proj/mods/atomic_ed/game/SCENARIO/OMAHA.SCN')
    ptr6_data = scn.sections.get('PTR6', b'')

    if not ptr6_data:
        print("No PTR6 data!")
        return

    records = parse_ptr6_records(ptr6_data)

    # Find all 449-byte records
    records_449 = [r for r in records if r['length'] == 449]

    print(f"\nFound {len(records_449)} records of length 449\n")

    # Analyze first 10
    for i, record in enumerate(records_449[:10]):
        print(f"\n449-byte Record #{i} at offset 0x{record['offset']:04x}:")
        print("-"*80)

        info = analyze_449_byte_record(record['data'])

        if info:
            print("First 32 words:")
            for j in range(0, 32, 8):
                words_str = ', '.join(f'{w:5d}' for w in info['first_32_words'][j:j+8])
                print(f"  [{j:2d}-{j+7:2d}]: {words_str}")

            # Show as hex too for first 32 bytes
            print("\nFirst 32 bytes as hex:")
            hex_data = record['data'][:32]
            for j in range(0, 32, 16):
                hex_str = ' '.join(f'{hex_data[k]:02x}' for k in range(j, min(j+16, 32)))
                print(f"  0x{j:02x}: {hex_str}")

            if info['patterns']:
                print("\nSpecial patterns found:")
                for p in info['patterns']:
                    print(f"  {p}")

            print(f"\nLast 16 bytes: {' '.join(info['last_16_bytes'])}")

    # Look for commonalities across all 449-byte records
    print(f"\n\n{'='*80}")
    print("COMMONALITIES ACROSS ALL 449-BYTE RECORDS")
    print("="*80)

    # Check if first word is always the same
    first_words = []
    for rec in records_449:
        if len(rec['data']) >= 2:
            w = struct.unpack('<H', rec['data'][0:2])[0]
            first_words.append(w)

    unique_first = set(first_words)
    print(f"\nFirst word values ({len(unique_first)} unique):")
    for w in sorted(unique_first):
        count = first_words.count(w)
        print(f"  0x{w:04x} ({w:5d}): {count} times")

    # Check word at offset 2
    second_words = []
    for rec in records_449:
        if len(rec['data']) >= 4:
            w = struct.unpack('<H', rec['data'][2:4])[0]
            second_words.append(w)

    unique_second = set(second_words)
    print(f"\nSecond word values ({len(unique_second)} unique):")
    for w in sorted(unique_second)[:20]:  # Show first 20
        count = second_words.count(w)
        print(f"  0x{w:04x} ({w:5d}): {count} times")

if __name__ == '__main__':
    main()
