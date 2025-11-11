#!/usr/bin/env python3
"""
Examine the structure around location names vs unit names
"""
import struct

def hexdump(data, offset, length):
    """Print hexdump of data"""
    start = offset
    end = offset + length

    for i in range(start, end, 16):
        hex_vals = []
        ascii_vals = []
        for j in range(i, min(i+16, end)):
            hex_vals.append(f'{data[j]:02x}')
            ascii_vals.append(chr(data[j]) if 32 <= data[j] < 127 else '.')

        hex_str = ' '.join(hex_vals)
        ascii_str = ''.join(ascii_vals)
        print(f'0x{i:04x}: {hex_str:<48s}  {ascii_str}')

def main():
    with open('/src/proj/mods/atomic_ed/game/SCENARIO/CAMPAIGN.SCN', 'rb') as f:
        data = f.read()

    print("="*80)
    print("EXAMINING STRUCTURE AROUND 'BOGUS' ENTRIES")
    print("="*80)
    print()

    # Look at V9 -> Carentan
    print("Example 1: 'V9' at 0x0c03 -> 'Carentan'")
    print("-"*80)
    hexdump(data, 0x0c03 - 64, 128)
    print()

    # Look at V, -> Periers
    print("Example 2: 'V,' at 0x0c43 -> 'Periers'")
    print("-"*80)
    hexdump(data, 0x0c43 - 64, 128)
    print()

    # Now look at a real unit like VII Corps
    print("="*80)
    print("COMPARING WITH REAL UNIT")
    print("="*80)
    print()

    # Find VII Corps
    vii_corps_offset = data.find(b'VII Corps\x00')
    if vii_corps_offset != -1:
        print(f"Example 3: 'VII Corps' at 0x{vii_corps_offset:04x}")
        print("-"*80)
        hexdump(data, vii_corps_offset - 64, 128)
        print()

        # Show the structure
        pre = data[vii_corps_offset-64:vii_corps_offset]
        print("Structure analysis:")
        print(f"  Offset -64 (strength): {struct.unpack('<H', pre[-64:-62])[0]}")
        print(f"  Offset -58 (X): {struct.unpack('<H', pre[-58:-56])[0]}")
        print(f"  Offset -56 (Y): {struct.unpack('<H', pre[-56:-54])[0]}")
        print(f"  Offset -30 (side1): {pre[-30]}")
        print(f"  Offset -29 (side2): {pre[-29]}")
        print(f"  Offset -27 (type): 0x{pre[-27]:02x}")
        print()

    # Check the pattern: are the "bogus" entries actually part of a different structure?
    print("="*80)
    print("HYPOTHESIS: These are location/objective markers, not units")
    print("="*80)
    print()

    # Look at what comes before "V9\x00Carentan"
    offset = 0x0c03
    pre_v9 = data[offset-10:offset]
    print(f"10 bytes before 'V9': {' '.join(f'{b:02x}' for b in pre_v9)}")

    # The structure might be:
    # [some header] [marker like V9] [null] [actual name like "Carentan"] [null]
    # Let's check
    print()
    print("Looking for pattern in location entries...")
    print()

    # Find all the V-prefixed entries
    import re
    pattern = rb'V[\x20-\x7e]\x00[\x20-\x7e]{4,30}\x00'
    matches = re.finditer(pattern, data)

    count = 0
    for match in matches:
        offset = match.start()
        matched_data = match.group()

        # Split on first null
        parts = matched_data.split(b'\x00')
        marker = parts[0].decode('ascii', errors='ignore')
        name = parts[1].decode('ascii', errors='ignore') if len(parts) > 1 else ''

        if name:
            # Get data before the marker
            if offset >= 10:
                pre_data = data[offset-10:offset]
                print(f"0x{offset:04x}: Marker '{marker}' -> Name '{name}'")
                print(f"  Pre-data: {' '.join(f'{b:02x}' for b in pre_data)}")

                count += 1
                if count >= 10:
                    break

if __name__ == '__main__':
    main()
