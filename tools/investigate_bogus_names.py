#!/usr/bin/env python3
"""
Investigate bogus unit names in CAMPAIGN.SCN
"""
import struct
import re

def find_all_strings(data):
    """Find all null-terminated ASCII strings"""
    pattern = rb'[\x20-\x7e]{2,30}\x00'
    matches = re.finditer(pattern, data)

    results = []
    for match in matches:
        string = match.group()[:-1].decode('ascii', errors='ignore')
        offset = match.start()

        # Get pre-data if available
        pre_data = None
        if offset >= 64:
            pre_data = data[offset-64:offset]

        results.append({
            'string': string,
            'offset': offset,
            'pre_data': pre_data,
        })

    return results

def analyze_unit_patterns(data):
    """Analyze what makes a real unit vs garbage"""

    # First, let's see the first 50 strings that look military
    strings = find_all_strings(data)

    print(f"Found {len(strings)} total null-terminated strings\n")
    print(f"{'='*80}")
    print("First 50 strings with military-like patterns:")
    print(f"{'='*80}\n")

    military_terms = [
        'Corps', 'Infantry', 'Airborne', 'Division', 'FJ',
        'Schnelle', 'Panzer', 'Armor', 'Regiment', 'Battalion',
        'Brigade', 'Artillery', 'Cavalry', 'Recon', 'Engineer',
        'Korps', 'Pz', 'Lehr'
    ]

    # Also check for strings with numbers or roman numerals
    count = 0
    for item in strings:
        s = item['string']

        has_military = any(term in s for term in military_terms)
        has_number = any(c.isdigit() for c in s)
        has_roman = bool(re.search(r'\b(I|II|III|IV|V|VI|VII|VIII|IX|X|XI|XII)\b', s))

        if has_military or has_number or has_roman:
            # Check the pre-data
            type_byte = None
            strength = None
            x = None
            y = None
            side_30 = None
            side_29 = None

            if item['pre_data'] is not None and len(item['pre_data']) >= 64:
                pre = item['pre_data']
                type_byte = pre[-27]
                strength = struct.unpack('<H', pre[-64:-62])[0]
                x = struct.unpack('<H', pre[-58:-56])[0]
                y = struct.unpack('<H', pre[-56:-54])[0]
                side_30 = pre[-30]
                side_29 = pre[-29]

            # Determine if this looks like a real unit
            is_ascii_type = type_byte and (0x61 <= type_byte <= 0x7a or 0x41 <= type_byte <= 0x5a)
            is_valid_coords = (x is not None and y is not None and
                             ((0 <= x <= 125 and 0 <= y <= 100) or (x == 0xFFFF and y == 0xFFFF)))
            is_valid_side = (side_30 is not None and side_29 is not None and
                           ((side_30 == 0 and side_29 == 0) or (side_30 == 1 and side_29 == 1)))
            is_valid_strength = strength is not None and 0 < strength <= 500

            status = "REAL" if (not is_ascii_type and is_valid_coords and is_valid_side) else "JUNK"

            print(f"[{status}] 0x{item['offset']:04x}: {s:<35s}", end="")
            if type_byte is not None:
                print(f" | Type: 0x{type_byte:02x}", end="")
                if is_ascii_type:
                    print(f" ('{chr(type_byte)}'!)", end="")
            if x is not None and y is not None:
                if x == 0xFFFF:
                    print(f" | Pos: OFF-MAP", end="")
                else:
                    print(f" | Pos: ({x},{y})", end="")
            if side_30 is not None:
                print(f" | Side: ({side_30},{side_29})", end="")
            if strength is not None:
                print(f" | Str: {strength}", end="")
            print()

            count += 1
            if count >= 50:
                break

    # Now let's look specifically at the bogus ones
    print(f"\n{'='*80}")
    print("Analyzing 'JUNK' entries in detail:")
    print(f"{'='*80}\n")

    count = 0
    for item in strings:
        s = item['string']

        has_military = any(term in s for term in military_terms)
        has_number = any(c.isdigit() for c in s)
        has_roman = bool(re.search(r'\b(I|II|III|IV|V|VI|VII|VIII|IX|X|XI|XII)\b', s))

        if has_military or has_number or has_roman:
            if item['pre_data'] is not None and len(item['pre_data']) >= 64:
                pre = item['pre_data']
                type_byte = pre[-27]

                # Check if type byte is ASCII
                if 0x61 <= type_byte <= 0x7a or 0x41 <= type_byte <= 0x5a:
                    print(f"0x{item['offset']:04x}: \"{s}\"")
                    print(f"  Type byte -27: 0x{type_byte:02x} = '{chr(type_byte)}' (ASCII!)")

                    # Show more context
                    print(f"  Bytes -32 to -25: {' '.join(f'{pre[i]:02x}' for i in range(-32, -25))}")

                    # Show what comes after the string
                    next_offset = item['offset'] + len(s) + 1
                    if next_offset + 10 < len(data):
                        next_bytes = data[next_offset:next_offset+10]
                        print(f"  Next 10 bytes: {' '.join(f'{b:02x}' for b in next_bytes)}")
                        # Try to decode as ASCII
                        try:
                            next_ascii = next_bytes.decode('ascii', errors='ignore')
                            if next_ascii.isprintable():
                                print(f"  Next as ASCII: \"{next_ascii}\"")
                        except:
                            pass

                    print()

                    count += 1
                    if count >= 10:
                        break

def main():
    filename = '/src/proj/mods/atomic_ed/game/SCENARIO/CAMPAIGN.SCN'

    print(f"Analyzing: {filename}")
    print(f"{'='*80}\n")

    with open(filename, 'rb') as f:
        data = f.read()

    analyze_unit_patterns(data)

if __name__ == '__main__':
    main()
