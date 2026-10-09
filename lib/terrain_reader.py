#!/usr/bin/env python3
"""Read D-Day terrain through the scenario's indexed map and shared hex records.

The file starts with length-prefixed Scenario, Calendar, HexMap and UHexes
blocks (32-bit little-endian byte lengths). HexMap contains row-major uint16
indexes into UHexes, whose records are four bytes each. The first record byte
contains the terrain code in its low nibble and sprite variant in its high
nibble. See txt/DDAY_MAP_FORMAT_RESEARCH.md for executable evidence.
"""

import struct
from collections import Counter
from dataclasses import dataclass, field

from lib.scenario_parser import DdayScenario


def _read_block(data, offset):
    """Return a bounded length-prefixed block and the next block's offset."""
    if offset + 4 > len(data):
        raise ValueError('Missing map block length')
    size = struct.unpack_from('<I', data, offset)[0]
    start = offset + 4
    end = start + size
    if end > len(data):
        raise ValueError('Truncated map block')
    return data[start:end], end


def extract_terrain_from_scenario(scenario, fallback_scenario_dir=None):
    """Return {(x, y): (terrain, variant)}, or {} for invalid/missing map data.

    fallback_scenario_dir is retained for caller compatibility. Terrain from
    another scenario is never substituted: small scenarios have their own maps.
    """
    terrain, _source = extract_terrain_with_source(scenario, fallback_scenario_dir)
    return terrain


def extract_terrain_with_source(scenario, fallback_scenario_dir=None):
    """Extract the scenario's own map and return (terrain, source filename)."""
    terrain = _extract_terrain_from_map_block(scenario)
    return terrain, scenario.filename.name if terrain else None


def _extract_terrain_from_map_block(scenario):
    return read_map_layers(scenario).terrain


@dataclass
class MapLayers:
    terrain: dict = field(default_factory=dict)
    records: dict = field(default_factory=dict)
    edges: dict = field(default_factory=dict)
    hilltops: set = field(default_factory=set)
    ownership: dict = field(default_factory=dict)
    places: list = field(default_factory=list)


def read_place_names(header):
    """Scenario's 50 fixed label slots; NameInHex uses count +122a."""
    count = header[0x122a]
    if count > 50:
        raise ValueError('Invalid place-name count')
    return [dict(x=struct.unpack_from('<h', header, 0xbe0+i*32)[0],
                 y=struct.unpack_from('<h', header, 0xbe2+i*32)[0],
                 name=header[0xbe4+i*32:0xbfe+i*32].split(b'\0')[0].decode('cp437'),
                 size=header[0xbfe+i*32], style=chr(header[0xbff+i*32]))
            for i in range(count)]


def read_map_layers(scenario):
    """Read base terrain, directional networks, terrain edges and hilltops.

    A missing/invalid edge block leaves the verified base map available. It
    never causes bytes from a different block to be interpreted as artwork.
    """
    layers = MapLayers()
    if not scenario.is_valid:
        return layers

    width, height = scenario.map_width, scenario.map_height
    if width <= 0 or height <= 0:
        return layers

    try:
        scenario_data, offset = _read_block(scenario.data, 0)
        if len(scenario_data) != 0x1230:
            return layers
        calendar, offset = _read_block(scenario.data, offset)
        if len(calendar) != 0x2a:
            return layers
        hex_map, offset = _read_block(scenario.data, offset)
        records, offset = _read_block(scenario.data, offset)
    except (ValueError, struct.error):
        return layers

    if len(hex_map) != width * height * 2 or not records or len(records) % 4:
        return layers

    for index, (record_id,) in enumerate(struct.iter_unpack('<H', hex_map)):
        record_offset = record_id * 4
        if record_offset >= len(records):
            return MapLayers()  # Reject partial or corrupt maps.
        byte = records[record_offset]
        # INVADE.EXE's terrVals table maps codes 0..14 directly, and 15 to 14.
        terrain_type = min(byte & 0x0f, 14)
        cell = index % width, index // width
        layers.terrain[cell] = (terrain_type, byte >> 4)
        layers.records[cell] = struct.unpack_from('<I', records, record_offset)[0]

    count = struct.unpack_from('<h', scenario_data, 0x2a2)[0]
    if 0 <= count <= 30:
        for index in range(count):
            x = struct.unpack_from('<h', scenario_data, 0x2a4 + 2 * index)[0]
            y = struct.unpack_from('<h', scenario_data, 0x2e0 + 2 * index)[0]
            if 0 <= x < width and 0 <= y < height:
                layers.hilltops.add((x, y))

    try:
        layers.places = read_place_names(scenario_data)
    except ValueError:
        pass
    try:
        zoc, offset = _read_block(scenario.data, offset)
        if len(zoc) == width * height * 4:
            layers.ownership = {(i % width, i // width): (word >> 16) & 1
                                for i, (word,) in enumerate(struct.iter_unpack('<I', zoc))}
        edge_map, offset = _read_block(scenario.data, offset)
        edge_records, offset = _read_block(scenario.data, offset)
        if len(edge_map) != width * height * 2 or len(edge_records) % 8:
            return layers
        edges = {}
        for index, (record_id,) in enumerate(struct.iter_unpack('<H', edge_map)):
            if record_id == 0xfde8:  # Game sentinel: no edge artwork.
                continue
            start = record_id * 8
            if start + 8 > len(edge_records):
                return layers
            edges[index % width, index // width] = edge_records[start:start + 8]
        layers.edges = edges
    except (ValueError, struct.error):
        pass
    return layers


def extract_terrain_from_file(scenario_path):
    """Extract the playable terrain from a .SCN file."""
    return extract_terrain_from_scenario(DdayScenario(scenario_path))


# Names from D-Day's Map A terrain key and manual §7, matched to PICT 128
# rows. INVADE.EXE's terrVals maps codes 0–14 directly to those rows.
TERRAIN_TYPES = {
    0: 'Bocage',
    1: 'Clear',
    2: 'Forest',
    3: 'Swamp',
    4: 'Town',
    5: 'Water',
    6: 'Beach',
    7: 'Bunker',
    8: 'Beach Bunker',
    9: 'Fortress',
    10: 'City',
    11: 'Rubble',
    12: 'Airfield',
    13: 'Invasion Beach',
    14: 'Special graphics',  # Not a named terrain in the manual's key.
}


def terrain_name(terrain_id):
    return TERRAIN_TYPES.get(terrain_id, f'Unknown terrain {terrain_id}')


if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1:
        terrain = extract_terrain_from_file(sys.argv[1])
        print(f'Extracted {len(terrain)} hexes from {sys.argv[1]}')
        for terrain_type, count in sorted(Counter(t for t, v in terrain.values()).items()):
            print(f'  {terrain_name(terrain_type)} (code {terrain_type}): '
                  f'{count:5,} ({100 * count / len(terrain):5.1f}%)')
