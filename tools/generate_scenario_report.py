#!/usr/bin/env python3
"""
Generate comprehensive report on unique scenarios
"""

import struct
import re
from pathlib import Path

def extract_strings(data, min_length=4):
    """Extract ASCII strings from binary data"""
    strings = []
    current = b''
    start_pos = 0

    for i, b in enumerate(data):
        if 32 <= b < 127:
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

def get_mission_briefing(strings):
    """Extract mission briefing from strings"""
    # Look for the longest coherent text segments that appear to be mission text
    mission_parts = []

    for offset, s in strings:
        if len(s) > 50:
            # Check if it looks like mission text
            if any(kw in s for kw in ['You', 'Your', 'must', 'objective', 'mission',
                                       'attack', 'defend', 'capture', 'General',
                                       'Division', 'Army', 'Corps']):
                mission_parts.append(s)

    return ' '.join(mission_parts[:10])  # First 10 relevant segments

def identify_game_series(magic):
    """Identify which game in the series based on magic number"""
    if magic == 0x1230:
        return "D-Day (1995)"
    elif magic == 0x0dac:
        return "Crusader in the Desert (1992)"
    elif magic == 0x0f4a:
        return "Clash of Steel (1993)"
    else:
        return f"Unknown (magic: 0x{magic:04x})"

# Scenario metadata based on filenames and analysis
SCENARIO_INFO = {
    'CITY.SCN': {
        'name': 'City Fighting',
        'battle': 'Battle of Stalingrad',
        'theater': 'Eastern Front',
        'date': 'September-November 1942'
    },
    'CLASH.SCN': {
        'name': 'Clash at the Myshkova',
        'battle': 'Operation Wintergewitter',
        'theater': 'Eastern Front',
        'date': 'December 1942'
    },
    'CRUCAMP.SCN': {
        'name': 'Crusader Campaign',
        'battle': 'Operation Crusader',
        'theater': 'North Africa',
        'date': 'November 1941 - January 1942'
    },
    'DUCE.SCN': {
        'name': 'Il Duce\'s Pride',
        'battle': 'Bir el Gubi',
        'theater': 'North Africa',
        'date': 'November 1941'
    },
    'HELLFIRE.SCN': {
        'name': 'Hellfire Pass',
        'battle': 'Halfaya Pass / Frontier Battles',
        'theater': 'North Africa',
        'date': 'November 1941'
    },
    'HURBERT.SCN': {
        'name': 'Hubert\'s Attack',
        'battle': 'Battle of Stalingrad',
        'theater': 'Eastern Front',
        'date': 'October-November 1942'
    },
    'MANSTEIN.SCN': {
        'name': 'Manstein\'s Counterattack',
        'battle': 'Operation Uranus - What If',
        'theater': 'Eastern Front',
        'date': 'November 1942 (hypothetical)'
    },
    'QUIET.SCN': {
        'name': 'Quiet Before the Storm',
        'battle': 'Operation Uranus',
        'theater': 'Eastern Front',
        'date': 'November 1942'
    },
    'RELIEVED.SCN': {
        'name': 'Tobruk Relieved',
        'battle': 'Operation Crusader - Late Phase',
        'theater': 'North Africa',
        'date': 'December 1941'
    },
    'RESCUE.SCN': {
        'name': 'Rescue of Tobruk',
        'battle': 'Operation Crusader - Sidi Rezegh',
        'theater': 'North Africa',
        'date': 'November 1941'
    },
    'RIVER.SCN': {
        'name': 'River Crossing',
        'battle': 'Operation Wintergewitter',
        'theater': 'Eastern Front',
        'date': 'December 1942'
    },
    'TANKS.SCN': {
        'name': 'Tank Battle',
        'battle': 'Operation Uranus - What If',
        'theater': 'Eastern Front',
        'date': 'November 1942 (hypothetical)'
    },
    'TOBRUK.SCN': {
        'name': 'Assault on Tobruk',
        'battle': 'Siege of Tobruk',
        'theater': 'North Africa',
        'date': '1941'
    },
    'VOLGA.SCN': {
        'name': 'Drive to the Volga',
        'battle': 'Battle of Stalingrad',
        'theater': 'Eastern Front',
        'date': 'October-November 1942'
    },
    'WINTER.SCN': {
        'name': 'Winter Storm',
        'battle': 'Operation Wintergewitter',
        'theater': 'Eastern Front',
        'date': 'December 1942'
    },
    'CAMPAIGN.SCN': {
        'name': 'Operation Uranus Campaign',
        'battle': 'Encirclement of Stalingrad',
        'theater': 'Eastern Front',
        'date': 'November 1942 - January 1943'
    }
}

def analyze_scenario(filepath):
    """Analyze a scenario file and return detailed info"""
    with open(filepath, 'rb') as f:
        data = f.read()

    magic = struct.unpack('<H', data[0:2])[0]
    strings = extract_strings(data, min_length=4)

    # Get metadata
    info = SCENARIO_INFO.get(filepath.name, {
        'name': filepath.stem,
        'battle': 'Unknown',
        'theater': 'Unknown',
        'date': 'Unknown'
    })

    # Extract objectives (look for location names in objective area)
    objectives = []
    for offset, s in strings:
        if 0x0a00 <= offset <= 0x0c00 and 5 <= len(s) <= 30:
            objectives.append(s)

    return {
        'filename': filepath.name,
        'size': len(data),
        'size_kb': len(data) // 1024,
        'magic': magic,
        'game': identify_game_series(magic),
        'name': info['name'],
        'battle': info['battle'],
        'theater': info['theater'],
        'date': info['date'],
        'briefing': get_mission_briefing(strings),
        'objectives': objectives[:10],
        'string_count': len(strings)
    }

def main():
    base_dir = Path('/home/user/atomic_ed/game/SCENARIO-all')

    scenarios = [
        'CITY.SCN', 'CLASH.SCN', 'CRUCAMP.SCN', 'DUCE.SCN', 'HELLFIRE.SCN',
        'HURBERT.SCN', 'MANSTEIN.SCN', 'QUIET.SCN', 'RELIEVED.SCN', 'RESCUE.SCN',
        'RIVER.SCN', 'TANKS.SCN', 'TOBRUK.SCN', 'VOLGA.SCN', 'WINTER.SCN',
        'CAMPAIGN.SCN'
    ]

    results = []
    for scn in scenarios:
        filepath = base_dir / scn
        if filepath.exists():
            results.append(analyze_scenario(filepath))

    # Print report
    print("=" * 100)
    print("UNIQUE SCENARIO FILES FROM PREVIOUS GAMES - COMPREHENSIVE ANALYSIS")
    print("=" * 100)
    print()

    # Group by game
    by_game = {}
    for r in results:
        game = r['game']
        if game not in by_game:
            by_game[game] = []
        by_game[game].append(r)

    print("SUMMARY BY GAME SERIES")
    print("-" * 100)
    for game in sorted(by_game.keys()):
        scenarios = by_game[game]
        print(f"\n{game}:")
        print(f"  Files: {len(scenarios)}")
        theaters = set(s['theater'] for s in scenarios)
        print(f"  Theaters: {', '.join(sorted(theaters))}")
        files = [s['filename'] for s in scenarios]
        print(f"  Scenarios: {', '.join(files)}")
    print()

    # Detailed listing
    print("\n" + "=" * 100)
    print("DETAILED SCENARIO INFORMATION")
    print("=" * 100)

    for r in results:
        print(f"\n{'─' * 100}")
        print(f"FILE: {r['filename']}")
        print(f"{'─' * 100}")
        print(f"Scenario Name:  {r['name']}")
        print(f"Game Series:    {r['game']}")
        print(f"File Size:      {r['size_kb']}K ({r['size']:,} bytes)")
        print(f"Magic Number:   0x{r['magic']:04x}")
        print()
        print(f"Theater:        {r['theater']}")
        print(f"Battle:         {r['battle']}")
        print(f"Date:           {r['date']}")
        print()

        if r['objectives']:
            print(f"Map Objectives:")
            for obj in r['objectives']:
                print(f"  - {obj}")
            print()

        print(f"Mission Briefing (excerpt):")
        briefing = r['briefing']
        if len(briefing) > 600:
            briefing = briefing[:600] + "..."
        # Wrap text at 90 chars
        words = briefing.split()
        lines = []
        current_line = ""
        for word in words:
            if len(current_line) + len(word) + 1 <= 90:
                if current_line:
                    current_line += " " + word
                else:
                    current_line = word
            else:
                if current_line:
                    lines.append(current_line)
                current_line = word
        if current_line:
            lines.append(current_line)

        for line in lines[:15]:  # Max 15 lines
            print(f"  {line}")
        print()

if __name__ == '__main__':
    main()
