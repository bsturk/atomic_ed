#!/usr/bin/env python3
"""
Analyze legacy scenario files from earlier games in the series
These files use different magic numbers than D-Day scenarios
"""

import struct
import re
from pathlib import Path

UNIQUE_SCENARIOS = [
    'CITY.SCN',
    'CLASH.SCN',
    'CRUCAMP.SCN',
    'DUCE.SCN',
    'HELLFIRE.SCN',
    'HURBERT.SCN',
    'MANSTEIN.SCN',
    'QUIET.SCN',
    'RELIEVED.SCN',
    'RESCUE.SCN',
    'RIVER.SCN',
    'TANKS.SCN',
    'TOBRUK.SCN',
    'VOLGA.SCN',
    'WINTER.SCN',
]

# Theater keywords for classification
THEATER_KEYWORDS = {
    'North Africa': ['tobruk', 'africa', 'rommel', 'desert', 'tunisia', 'tripoli', 'libya',
                     'egypt', 'crusader', 'alamein', 'kasserine', 'mareth', 'gazala'],
    'Eastern Front': ['russia', 'soviet', 'stalingrad', 'volga', 'moscow', 'kursk', 'german',
                      'winter', 'manstein', 'barbarossa', 'kharkov', 'smolensk', 'minsk',
                      'kiev', 'leningrad', 'caucasus', 'don', 'dnieper'],
    'Italy': ['italy', 'italian', 'sicily', 'salerno', 'anzio', 'cassino', 'duce',
              'mussolini', 'rome', 'naples', 'po valley'],
    'Normandy': ['normandy', 'france', 'caen', 'omaha', 'utah', 'cobra', 'bradley',
                 'cherbourg', 'falaise', 'avranches', 'mortain'],
    'Western Europe': ['belgium', 'holland', 'rhineland', 'ardennes', 'bulge', 'bastogne',
                       'arnhem', 'market garden'],
}

def extract_strings(data, min_length=4):
    """Extract ASCII strings from binary data"""
    strings = []
    current = b''
    start_pos = 0

    for i, b in enumerate(data):
        if 32 <= b < 127:  # Printable ASCII
            if len(current) == 0:
                start_pos = i
            current += bytes([b])
        else:
            if len(current) >= min_length:
                try:
                    s = current.decode('ascii')
                    strings.append((start_pos, s))
                except:
                    pass
            current = b''

    return strings

def find_mission_text(data):
    """Find and extract mission briefing text"""
    strings = extract_strings(data, min_length=20)

    # Look for long strings that look like mission text
    mission_candidates = []

    for offset, s in strings:
        # Mission text typically contains certain keywords
        if any(keyword in s.lower() for keyword in
               ['mission', 'objective', 'attack', 'defend', 'capture', 'hold',
                'enemy', 'allied', 'german', 'division', 'regiment', 'orders']):
            mission_candidates.append((offset, s))

    return mission_candidates

def identify_theater(filename, all_text):
    """Identify theater of operations from text content"""
    text_lower = all_text.lower()
    filename_lower = filename.lower()

    scores = {}
    for theater, keywords in THEATER_KEYWORDS.items():
        score = 0
        for keyword in keywords:
            if keyword in text_lower:
                score += text_lower.count(keyword) * 2
            if keyword in filename_lower:
                score += 10
        scores[theater] = score

    # Get theater with highest score
    if max(scores.values()) > 0:
        return max(scores.items(), key=lambda x: x[1])[0]
    return 'Unknown'

def extract_units(text):
    """Extract military unit designations"""
    units = set()

    # Pattern: Division numbers (e.g., 1st Division, 352nd Infantry)
    pattern1 = r'\b\d+(?:st|nd|rd|th)\s+(?:Infantry|Panzer|Armored|Airborne|Division|Regiment|Battalion|Brigade)\b'
    units.update(re.findall(pattern1, text, re.IGNORECASE))

    # Pattern: Roman numeral corps (e.g., XXI Corps, II Panzer Corps)
    pattern2 = r'\b[IVX]+\s+(?:Corps|Army|Panzer\s+Corps|SS\s+Panzer)\b'
    units.update(re.findall(pattern2, text, re.IGNORECASE))

    # Pattern: Army groups
    pattern3 = r'\bArmy\s+Group\s+[A-Z]\w*\b'
    units.update(re.findall(pattern3, text, re.IGNORECASE))

    # Pattern: Numbered armies
    pattern4 = r'\b\d+(?:st|nd|rd|th)\s+Army\b'
    units.update(re.findall(pattern4, text, re.IGNORECASE))

    return sorted(list(units))

def extract_locations(strings):
    """Extract location names"""
    locations = set()

    # Common military terms to exclude
    exclude = {'Allied', 'German', 'American', 'British', 'Soviet', 'Division',
               'Regiment', 'Battalion', 'Corps', 'Army', 'Infantry', 'Panzer',
               'General', 'Major', 'Colonel', 'Captain', 'Objective', 'Mission',
               'Command', 'Forces', 'Attack', 'Defense', 'Victory', 'Defeat',
               'January', 'February', 'March', 'April', 'May', 'June', 'July',
               'August', 'September', 'October', 'November', 'December'}

    for _, s in strings:
        # Look for capitalized words (potential place names)
        words = re.findall(r'\b[A-Z][a-z]{3,}\b', s)
        for word in words:
            if word not in exclude and len(word) >= 4:
                locations.add(word)

    return sorted(list(locations))

def analyze_scenario(filepath):
    """Analyze a scenario file"""
    with open(filepath, 'rb') as f:
        data = f.read()

    # Get magic number
    magic = struct.unpack('<H', data[0:2])[0]

    # Extract all strings
    all_strings = extract_strings(data, min_length=4)
    all_text = ' '.join(s for _, s in all_strings)

    # Find mission text
    mission_text = find_mission_text(data)

    # Identify theater
    theater = identify_theater(filepath.name, all_text)

    # Extract units and locations
    units = extract_units(all_text)
    locations = extract_locations(all_strings)

    return {
        'filename': filepath.name,
        'file_size': len(data),
        'file_size_kb': len(data) // 1024,
        'magic': magic,
        'magic_hex': f'0x{magic:04x}',
        'theater': theater,
        'all_strings': all_strings,
        'mission_text': mission_text,
        'units': units,
        'locations': locations,
    }

def main():
    base_dir = Path('/home/user/atomic_ed/game/SCENARIO-all')

    # Group by magic number
    magic_groups = {}

    print("=" * 80)
    print("LEGACY SCENARIO FILE ANALYSIS")
    print("=" * 80)
    print()

    results = []
    for scenario_name in UNIQUE_SCENARIOS:
        filepath = base_dir / scenario_name

        if not filepath.exists():
            print(f"WARNING: {scenario_name} not found")
            continue

        result = analyze_scenario(filepath)
        results.append(result)

        # Group by magic number
        magic = result['magic_hex']
        if magic not in magic_groups:
            magic_groups[magic] = []
        magic_groups[magic].append(scenario_name)

    # Show magic number grouping
    print("FILE FORMAT GROUPS (by magic number):")
    print("-" * 80)
    for magic, files in sorted(magic_groups.items()):
        print(f"\nMagic {magic}:")
        for f in files:
            print(f"  - {f}")
    print()

    # Detailed analysis for each scenario
    for result in results:
        print(f"\n{'=' * 80}")
        print(f"SCENARIO: {result['filename']}")
        print('=' * 80)
        print(f"File Size: {result['file_size_kb']}K ({result['file_size']:,} bytes)")
        print(f"Magic Number: {result['magic_hex']}")
        print(f"Theater: {result['theater']}")

        print(f"\n--- Mission Briefing Text ---")
        if result['mission_text']:
            for offset, text in result['mission_text'][:3]:  # Show first 3 mission text candidates
                print(f"\n[Offset 0x{offset:04x}]")
                # Clean up text and limit length
                cleaned = text.strip()
                if len(cleaned) > 400:
                    cleaned = cleaned[:400] + "..."
                print(cleaned)
        else:
            # Show long strings that might be mission text
            long_strings = [(off, s) for off, s in result['all_strings'] if len(s) > 50]
            if long_strings:
                print(f"\n[First long text string at 0x{long_strings[0][0]:04x}]")
                text = long_strings[0][1]
                if len(text) > 400:
                    text = text[:400] + "..."
                print(text)
            else:
                print("(No mission text found)")

        print(f"\n--- Unit Designations ---")
        if result['units']:
            for unit in result['units'][:15]:
                print(f"  - {unit}")
            if len(result['units']) > 15:
                print(f"  ... and {len(result['units']) - 15} more")
        else:
            print("  (None found)")

        print(f"\n--- Notable Locations ---")
        if result['locations']:
            for loc in result['locations'][:20]:
                print(f"  - {loc}")
            if len(result['locations']) > 20:
                print(f"  ... and {len(result['locations']) - 20} more")
        else:
            print("  (None found)")

        print(f"\n--- Sample Strings (first 20) ---")
        for offset, s in result['all_strings'][:20]:
            if len(s) > 60:
                s = s[:60] + "..."
            print(f"  0x{offset:04x}: {s}")

    print("\n" + "=" * 80)
    print("ANALYSIS COMPLETE")
    print("=" * 80)

if __name__ == '__main__':
    main()
