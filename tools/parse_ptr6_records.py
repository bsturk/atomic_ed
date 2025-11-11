#!/usr/bin/env python3
"""
Parse PTR6 as variable-length records and try to understand their meaning
"""
import struct
import sys
sys.path.insert(0, '/src/proj/mods/atomic_ed')
from lib.scenario_parser import DdayScenario

def parse_ptr6_records(data):
    """Parse PTR6 as [length_word][data...] records"""
    records = []
    i = 0

    while i + 2 <= len(data):
        # Read length
        length = struct.unpack('<H', data[i:i+2])[0]

        if length == 0:
            # Skip zeros but track them
            zero_start = i
            while i < len(data) and data[i] == 0:
                i += 1
            if i - zero_start > 4:
                records.append({
                    'type': 'padding',
                    'offset': zero_start,
                    'length': i - zero_start,
                    'data': b''
                })
            continue

        # Sanity check
        if length > 2048 or i + 2 + length > len(data):
            # Not a valid length, skip
            i += 2
            continue

        # Extract record
        record_data = data[i+2:i+2+length]

        records.append({
            'type': 'record',
            'offset': i,
            'length': length,
            'data': record_data
        })

        i += 2 + length

    return records

def analyze_record_contents(record, scenario_name):
    """Try to interpret a record's contents"""
    data = record['data']
    length = len(data)

    info = {
        'offset': record['offset'],
        'length': length,
        'interpretations': []
    }

    if length == 0:
        return info

    # Try as array of 16-bit values
    if length % 2 == 0:
        words = []
        for i in range(0, length, 2):
            w = struct.unpack('<H', data[i:i+2])[0]
            words.append(w)

        info['as_words'] = words

        # Look for patterns
        # Check if they're all small values (could be turn numbers, counts)
        if all(w < 256 for w in words):
            info['interpretations'].append('small_values')

        # Check if they look like coordinates
        if length >= 4:
            coord_pairs = []
            for i in range(0, len(words)-1, 2):
                x, y = words[i], words[i+1]
                if 0 < x <= 125 and 0 < y <= 100:
                    coord_pairs.append((x, y))
            if coord_pairs:
                info['coord_pairs'] = coord_pairs
                info['interpretations'].append('coordinates')

        # Check if they're all 1s (flags)
        if all(w == 1 for w in words):
            info['interpretations'].append('all_ones')

        # Check for common values
        if length >= 8:
            # First few values might be a header
            info['first_4_words'] = words[:4]

    # Check for ASCII strings
    ascii_chars = [chr(b) if 32 <= b < 127 else '?' for b in data]
    ascii_ratio = sum(1 for c in ascii_chars if c != '?') / len(ascii_chars)

    if ascii_ratio > 0.7:
        info['interpretations'].append('text_data')
        info['ascii'] = ''.join(ascii_chars)

    return info

def main():
    print("="*80)
    print("PTR6 RECORD PARSER")
    print("="*80)

    scn = DdayScenario('/src/proj/mods/atomic_ed/game/SCENARIO/CAMPAIGN.SCN')
    ptr6_data = scn.sections.get('PTR6', b'')

    if not ptr6_data:
        print("No PTR6 data!")
        return

    print(f"\nParsing {len(ptr6_data)} bytes of PTR6 data...\n")

    records = parse_ptr6_records(ptr6_data)

    print(f"Found {len(records)} records/segments")
    print()

    # Analyze each record
    print("="*80)
    print("RECORD ANALYSIS")
    print("="*80)

    data_records = [r for r in records if r['type'] == 'record']

    for i, record in enumerate(data_records[:30]):  # First 30 records
        info = analyze_record_contents(record, 'CAMPAIGN')

        print(f"\nRecord {i} at 0x{info['offset']:04x}:")
        print(f"  Length: {info['length']} bytes")

        if 'interpretations' in info and info['interpretations']:
            print(f"  Type: {', '.join(info['interpretations'])}")

        if 'as_words' in info:
            words = info['as_words']
            if len(words) <= 16:
                print(f"  Words: {', '.join(str(w) for w in words)}")
            else:
                print(f"  First 16 words: {', '.join(str(w) for w in words[:16])}...")

        if 'first_4_words' in info:
            print(f"  Header?: {info['first_4_words']}")

        if 'coord_pairs' in info:
            pairs = info['coord_pairs']
            if len(pairs) <= 8:
                print(f"  Coordinates: {pairs}")
            else:
                print(f"  First 8 coords: {pairs[:8]}...")

        if 'ascii' in info:
            print(f"  ASCII: \"{info['ascii'][:60]}...\"")

    # Statistics
    print(f"\n\n{'='*80}")
    print("STATISTICS")
    print("="*80)

    lengths = [r['length'] for r in data_records]
    print(f"\nRecord count: {len(data_records)}")
    print(f"Min length: {min(lengths) if lengths else 0}")
    print(f"Max length: {max(lengths) if lengths else 0}")
    print(f"Avg length: {sum(lengths)/len(lengths) if lengths else 0:.1f}")

    # Length distribution
    length_counts = {}
    for l in lengths:
        length_counts[l] = length_counts.get(l, 0) + 1

    print(f"\nMost common lengths:")
    for length, count in sorted(length_counts.items(), key=lambda x: x[1], reverse=True)[:10]:
        print(f"  {length:4d} bytes: {count:3d} records")

if __name__ == '__main__':
    main()
