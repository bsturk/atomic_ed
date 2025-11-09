#!/usr/bin/env python3
"""
Analyze unique scenario files from SCENARIO-all directory
Extract mission briefings, locations, units, and other metadata
"""

import sys
import struct
from pathlib import Path
from scenario_parser import DdayScenario

# Scenarios unique to SCENARIO-all (not in SCENARIO)
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
    'North Africa': ['tobruk', 'africa', 'rommel', 'desert', 'tunisia', 'tripoli', 'libya', 'egypt', 'crusader'],
    'Eastern Front': ['russia', 'soviet', 'stalingrad', 'volga', 'moscow', 'kursk', 'german', 'winter', 'manstein', 'barbarossa'],
    'Italy': ['italy', 'italian', 'sicily', 'salerno', 'anzio', 'cassino', 'duce'],
    'Normandy': ['normandy', 'france', 'caen', 'omaha', 'utah', 'cobra', 'bradley', 'cherbourg'],
    'Western Europe': ['belgium', 'holland', 'rhineland', 'ardennes', 'bulge'],
}

def extract_text_region(data, start_offset, max_length=2000):
    """Extract printable ASCII text from a region"""
    text_segments = []
    current = b''

    end = min(start_offset + max_length, len(data))
    for i in range(start_offset, end):
        b = data[i]
        if 32 <= b < 127 or b in [9, 10, 13]:  # Printable + tab/newline
            current += bytes([b])
        else:
            if len(current) >= 10:  # Min string length
                try:
                    s = current.decode('ascii', errors='ignore')
                    text_segments.append(s)
                except:
                    pass
            current = b''

    return '\n'.join(text_segments)

def find_unit_designations(text):
    """Find military unit designations in text"""
    import re

    units = []

    # Pattern: Letter-Number-Roman numerals (e.g., B-801-VII)
    pattern1 = r'\b[A-Z]-\d+-[IVX]+\b'
    units.extend(re.findall(pattern1, text))

    # Pattern: Division numbers (e.g., 1st Division, 352nd)
    pattern2 = r'\b\d+(?:st|nd|rd|th)\s+(?:Division|Regiment|Battalion|Corps|Army)\b'
    units.extend(re.findall(pattern2, text, re.IGNORECASE))

    # Pattern: Unit codes (e.g., XXI Corps)
    pattern3 = r'\b[IVX]+\s+(?:Corps|Army|Panzer|Infantry)\b'
    units.extend(re.findall(pattern3, text, re.IGNORECASE))

    return list(set(units))

def identify_theater(filename, text):
    """Identify theater of operations from text content"""
    text_lower = text.lower()
    filename_lower = filename.lower()

    scores = {}
    for theater, keywords in THEATER_KEYWORDS.items():
        score = 0
        for keyword in keywords:
            if keyword in text_lower:
                score += text_lower.count(keyword) * 2
            if keyword in filename_lower:
                score += 5
        scores[theater] = score

    # Get theater with highest score
    if max(scores.values()) > 0:
        return max(scores.items(), key=lambda x: x[1])[0]
    return 'Unknown'

def extract_locations(text):
    """Extract potential location names from text"""
    import re

    locations = []

    # Capitalize words (potential place names)
    # Match words that start with capital and are 4+ chars
    pattern = r'\b[A-Z][a-z]{3,}(?:\s+[A-Z][a-z]+)*\b'
    candidates = re.findall(pattern, text)

    # Filter out common words
    common_words = {'Allied', 'German', 'American', 'British', 'Soviet', 'Division',
                    'Regiment', 'Battalion', 'Corps', 'Army', 'Infantry', 'Panzer',
                    'General', 'Major', 'Colonel', 'Captain', 'June', 'July', 'August',
                    'September', 'October', 'November', 'December', 'January', 'February',
                    'March', 'April', 'Commander', 'Command', 'Forces', 'Force', 'Line',
                    'Attack', 'Defense', 'Objective', 'Mission', 'Enemy', 'Friendly'}

    for candidate in candidates:
        if candidate not in common_words and len(candidate) >= 4:
            locations.append(candidate)

    return list(set(locations))

def analyze_scenario(filepath):
    """Analyze a single scenario file"""
    scenario = DdayScenario(filepath)

    if not scenario.is_valid:
        return None

    # Extract text from various regions
    text_regions = []

    # Region 1: Around 0x3E4 (mission briefing area)
    text_regions.append(extract_text_region(scenario.data, 0x3E4, 1500))

    # Region 2: PTR4 section (Unit positioning + Text)
    if 'PTR4' in scenario.sections:
        ptr4_data = scenario.sections['PTR4']
        text_regions.append(extract_text_region(ptr4_data, 0, 2000))

    # Combine all text
    full_text = '\n'.join(text_regions)

    # Find all strings for locations
    all_strings = scenario.find_strings(min_length=4)
    string_text = ' '.join(s for _, s in all_strings)

    return {
        'filename': filepath.name,
        'file_size': len(scenario.data),
        'file_size_kb': len(scenario.data) // 1024,
        'map_height': scenario.map_height,
        'map_width': scenario.map_width,
        'pointers': scenario.pointers,
        'text': full_text,
        'all_strings': string_text,
        'theater': identify_theater(filepath.name, full_text + ' ' + string_text),
        'units': find_unit_designations(full_text),
        'locations': extract_locations(full_text + ' ' + string_text),
    }

def main():
    base_dir = Path('/home/user/atomic_ed/game/SCENARIO-all')

    print("=" * 80)
    print("UNIQUE SCENARIO FILE ANALYSIS")
    print("=" * 80)
    print()

    for scenario_name in UNIQUE_SCENARIOS:
        filepath = base_dir / scenario_name

        if not filepath.exists():
            print(f"WARNING: {scenario_name} not found")
            continue

        print(f"\n{'=' * 80}")
        print(f"SCENARIO: {scenario_name}")
        print('=' * 80)

        result = analyze_scenario(filepath)

        if not result:
            print("ERROR: Failed to parse scenario file")
            continue

        print(f"\nFile Size: {result['file_size_kb']}K ({result['file_size']:,} bytes)")
        print(f"Map Dimensions: {result['map_width']} x {result['map_height']} hexes")
        print(f"Theater: {result['theater']}")

        print(f"\n--- Offset Pointers ---")
        for name, ptr in sorted(result['pointers'].items()):
            if ptr > 0:
                print(f"  {name}: 0x{ptr:06x} ({ptr:,})")

        print(f"\n--- Mission Text ---")
        if result['text'].strip():
            # Show first 500 chars of mission text
            mission_text = result['text'].strip()[:800]
            print(mission_text)
            if len(result['text']) > 800:
                print("...")
        else:
            print("(No mission text found)")

        print(f"\n--- Unit Designations ---")
        if result['units']:
            for unit in sorted(result['units'])[:10]:
                print(f"  - {unit}")
            if len(result['units']) > 10:
                print(f"  ... and {len(result['units']) - 10} more")
        else:
            print("  (None found)")

        print(f"\n--- Notable Locations ---")
        if result['locations']:
            for loc in sorted(result['locations'])[:15]:
                print(f"  - {loc}")
            if len(result['locations']) > 15:
                print(f"  ... and {len(result['locations']) - 15} more")
        else:
            print("  (None found)")

    print("\n" + "=" * 80)
    print("ANALYSIS COMPLETE")
    print("=" * 80)

if __name__ == '__main__':
    main()
