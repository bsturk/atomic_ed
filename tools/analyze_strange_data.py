#!/usr/bin/env python3
"""
Deep analysis of the "bogus" data - what is it really?
"""
import struct
import re

def analyze_structure(data, offset, name):
    """Analyze the binary structure around a suspicious string"""

    print(f"\n{'='*80}")
    print(f"Analyzing: \"{name}\" at offset 0x{offset:04x}")
    print(f"{'='*80}\n")

    # Show 128 bytes of context
    start = max(0, offset - 64)
    end = min(len(data), offset + 64)

    print("Hexdump with context:")
    for i in range(start, end, 16):
        hex_vals = ' '.join(f'{data[j]:02x}' for j in range(i, min(i+16, end)))
        ascii_vals = ''.join(chr(data[j]) if 32 <= data[j] < 127 else '.' for j in range(i, min(i+16, end)))
        marker = ' <--' if i <= offset < i+16 else ''
        print(f'0x{i:04x}: {hex_vals:<48s}  {ascii_vals}{marker}')

    # If we have 64 bytes before, try to parse as unit structure
    if offset >= 64:
        pre = data[offset-64:offset]

        print(f"\nAttempting to parse as unit structure:")
        print(f"  Offset -64 (strength?): {struct.unpack('<H', pre[-64:-62])[0]}")
        print(f"  Offset -62: 0x{struct.unpack('<H', pre[-62:-60])[0]:04x}")
        print(f"  Offset -60: 0x{struct.unpack('<H', pre[-60:-58])[0]:04x}")
        print(f"  Offset -58 (X?): {struct.unpack('<H', pre[-58:-56])[0]}")
        print(f"  Offset -56 (Y?): {struct.unpack('<H', pre[-56:-54])[0]}")
        print(f"  Offset -54: 0x{struct.unpack('<H', pre[-54:-52])[0]:04x}")
        print(f"  Offset -52: 0x{struct.unpack('<H', pre[-52:-50])[0]:04x}")
        print(f"  Offset -50: 0x{struct.unpack('<H', pre[-50:-48])[0]:04x}")
        print(f"  Offset -48: 0x{struct.unpack('<H', pre[-48:-46])[0]:04x}")
        print(f"  Offset -46: 0x{struct.unpack('<H', pre[-46:-44])[0]:04x}")
        print(f"  Offset -40: 0x{struct.unpack('<H', pre[-40:-38])[0]:04x}")
        print(f"  Offset -30 (side?): 0x{pre[-30]:02x}")
        print(f"  Offset -29 (side?): 0x{pre[-29]:02x}")
        print(f"  Offset -27 (type?): 0x{pre[-27]:02x}")

        print(f"\nBytes -32 to -1:")
        for i in range(-32, 0, 8):
            vals = ' '.join(f'{pre[i+j]:02x}' for j in range(8))
            print(f"  {i:3d} to {i+7:3d}: {vals}")

    # Look at what comes after
    after_offset = offset + len(name) + 1  # +1 for null terminator
    if after_offset + 32 < len(data):
        print(f"\nBytes immediately after (offset 0x{after_offset:04x}):")
        after = data[after_offset:after_offset+32]
        for i in range(0, 32, 8):
            vals = ' '.join(f'{after[i+j]:02x}' for j in range(min(8, 32-i)))
            ascii_vals = ''.join(chr(after[i+j]) if 32 <= after[i+j] < 127 else '.' for j in range(min(8, 32-i)))
            print(f"  +{i:2d} to +{i+7:2d}: {vals:<24s} {ascii_vals}")

def main():
    with open('/src/proj/mods/atomic_ed/game/SCENARIO/CAMPAIGN.SCN', 'rb') as f:
        data = f.read()

    print("="*80)
    print("DEEP ANALYSIS OF SUSPICIOUS DATA PATTERNS")
    print("="*80)

    # Find the specific suspicious strings
    suspicious = [
        (rb'P! I0! I\x00', 'P! I0! I'),
        (rb'I`K"\x00', 'I`K"'),
        (rb'08`Y\x00', '08`Y'),
    ]

    for pattern, name in suspicious:
        match = re.search(pattern, data)
        if match:
            analyze_structure(data, match.start(), name)

    # Also analyze a known good unit for comparison
    vii_corps = data.find(b'VII Corps\x00')
    if vii_corps != -1:
        analyze_structure(data, vii_corps, 'VII Corps (KNOWN GOOD)')

    # Look for patterns - are these at regular intervals?
    print(f"\n\n{'='*80}")
    print("PATTERN ANALYSIS")
    print(f"{'='*80}\n")

    # Find ALL strings with special characters
    pattern = rb'[\x20-\x7e]{4,30}\x00'
    matches = list(re.finditer(pattern, data))

    special_char_strings = []
    for match in matches:
        s = match.group()[:-1].decode('ascii', errors='ignore')
        if any(c in '!`"@#$%^&*' for c in s):
            special_char_strings.append({
                'string': s,
                'offset': match.start(),
            })

    print(f"Found {len(special_char_strings)} strings with special characters\n")
    print("First 20:")
    for item in special_char_strings[:20]:
        print(f"  0x{item['offset']:04x}: \"{item['string']}\"")

    # Check if they're in a specific section
    print(f"\n\nOffset range analysis:")
    if special_char_strings:
        offsets = [x['offset'] for x in special_char_strings]
        print(f"  First occurrence: 0x{min(offsets):04x}")
        print(f"  Last occurrence: 0x{max(offsets):04x}")
        print(f"  Range: 0x{max(offsets) - min(offsets):04x} bytes")

        # Are they clustered?
        gaps = [offsets[i+1] - offsets[i] for i in range(len(offsets)-1)]
        avg_gap = sum(gaps) / len(gaps) if gaps else 0
        print(f"  Average gap between occurrences: {avg_gap:.1f} bytes")
        print(f"  Min gap: {min(gaps) if gaps else 0} bytes")
        print(f"  Max gap: {max(gaps) if gaps else 0} bytes")

if __name__ == '__main__':
    main()
