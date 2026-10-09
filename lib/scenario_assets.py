"""Save portable scenario assets without making per-scenario game copies."""
from pathlib import Path
import json

from lib.terrain_artwork import artwork_path, encode_artwork, save_with_artwork
from lib.counter_artwork import counter_path, load_counters, encode_counters
from lib.presentation_artwork import (presentation_path, load_presentation,
                                      encode_presentation, patch_presentation)

GAME_SCENARIOS = {
    'BRADLEY.SCN': "Bradley's Nightmare", 'COUNTER.SCN': 'SS Counterattack',
    'STLO.SCN': 'St Lo', 'COBRA.SCN': 'Operation Cobra', 'UTAH.SCN': 'Utah Beach',
    'OMAHA.SCN': 'Omaha Beach', 'CAMPAIGN.SCN': 'America Invades!',
}
MANIFEST = '.atomic-editor-game.json'


def engine_slot(data):
    """The engine reloads the menu filename selected by Scenario+1220h."""
    if len(data) < 0x1234 or data[4+0x1220] >= len(GAME_SCENARIOS):
        raise ValueError('Unsupported D-Day scenario ID')
    return tuple(GAME_SCENARIOS)[data[4+0x1220]]


def scenario_title(path):
    path = Path(path)
    for metadata in (artwork_path(path), Path(str(path) + '.conversion.json')):
        if metadata.exists():
            title = json.loads(metadata.read_bytes()).get('title')
            if isinstance(title, str) and title.strip():
                return title.strip()
    if path.exists():
        from lib.scenario_library import library_metadata, SIZE
        with path.open('rb') as stream:
            stream.seek(max(0, path.stat().st_size-SIZE))
            metadata = library_metadata(stream.read())
        if metadata and metadata['title'].strip():
            return metadata['title'].strip()
    return GAME_SCENARIOS.get(path.name.upper(), path.stem)


def export_for_dos(data, target, assignments, *, counters, title=None, presentation=None, document=None):
    """Write the SCN, matching REZ and AI orders for manual installation."""
    from lib.battle_plans import export_plans
    from lib.game_resources import GAME_ROOT
    from lib.terrain_artwork import build_terrain_resources
    from lib.counter_artwork import patch_counters
    from lib.unit_roster import UnitRoster
    from lib.weather_reader import validate_weather
    from lib.scenario_data import normalize_replacements
    from lib.scenario_library import dos_filename, with_library_metadata, build_overviews

    from lib.game_profiles import GameProfile, encode_rules
    profile = document.profile if document is not None else GameProfile()
    from lib.terrain_rules import encode_terrain_rules
    needs_terrain = bool(profile.terrain.changed)
    needs_profile = profile.values != GameProfile().values or needs_terrain
    data = normalize_replacements(data)
    target = Path(target)
    if target.suffix.upper() != '.SCN':
        raise ValueError('Choose an .SCN filename for the DOS export')
    filename = dos_filename(target.name)
    roster = UnitRoster(data)
    engine_slot(data)
    validate_weather(roster.blocks['weather'])
    original = (GAME_ROOT / 'dday/DATA/PCWATW.REZ').read_bytes()
    resources = patch_counters(build_terrain_resources(original, assignments), counters)
    title = title or target.stem
    resources = build_overviews(resources, data, assignments, title)
    resources = patch_presentation(resources, presentation or {})
    if needs_terrain:
        resources += encode_terrain_rules(profile.terrain)
    if needs_profile:
        resources += encode_rules(profile)
    # The generated selection preview depicts this map rather than a crop of
    # Normandy. Keep its red frame in the same coordinate system as the map.
    roster.header[0x22c:0x234] = roster.header[0x224:0x22c]
    data = with_library_metadata(roster.to_bytes(), filename, title, require_profile=needs_profile, require_terrain=needs_terrain)
    target.parent.mkdir(parents=True, exist_ok=True)
    resource_target = target.with_suffix('.REZ')
    extra = {resource_target: resources, target.with_suffix('.AI'): export_plans(data)}
    startup = target.parent/'DATA'/'PCWATW.REZ'
    if startup.exists() or any(key.startswith('splash_') for key in (presentation or {})):
        from lib.presentation_artwork import startup_resources
        startup.parent.mkdir(parents=True, exist_ok=True)
        extra[startup] = startup_resources(presentation or {})
    save_with_artwork(data, target, {}, include_artwork=False,
                      extra_files=extra)
    return target, resource_target


def runtime_slot_for(target):
    """Retain the original game menu slot across Save As and future reloads."""
    target = Path(target)
    sidecar = artwork_path(target)
    if sidecar.exists():
        slot = json.loads(sidecar.read_bytes()).get('runtime_slot')
        if slot is not None:
            if slot not in GAME_SCENARIOS:
                raise ValueError('Unknown D-Day scenario menu entry in artwork file')
            return slot
    return target.name.upper() if target.name.upper() in GAME_SCENARIOS else 'BRADLEY.SCN'



def playable_folder(target=None):
    """Legacy path query; the editor no longer creates or launches this tree."""
    return Path(__file__).resolve().parents[1] / 'play/dday'


def conversion_report(path):
    """Conversion notes live inside the existing artwork companion file."""
    sidecar = artwork_path(path)
    return json.loads(sidecar.read_bytes()).get('conversion') if sidecar.exists() else None


def save_scenario_assets(data, target, assignments, runtime_slot=None, *, counters=None, title=None, conversion=None, presentation=None, document=None):
    """Save the editing document and artwork atomically; DOS export is separate."""
    target = Path(target).absolute()
    if len(data) < 0x1234 or int.from_bytes(data[:4], 'little') != 0x1230:
        raise ValueError('Only D-Day scenario files can be prepared for the D-Day engine.')
    from lib.scenario_data import normalize_replacements
    data = normalize_replacements(data)
    slot = runtime_slot or runtime_slot_for(target)
    if slot not in GAME_SCENARIOS:
        raise ValueError('Unknown D-Day scenario menu entry')
    counters = load_counters(target) if counters is None else counters
    presentation = load_presentation(target) if presentation is None else presentation
    sidecar = artwork_path(target)
    if title is None and sidecar.exists():
        title = json.loads(sidecar.read_bytes()).get('title')
    if conversion is None:
        conversion = conversion_report(target)
    from lib.game_profiles import ScenarioDocument, load_document
    conversion = dict(conversion) if conversion else None
    imported_document = conversion.pop('document', None) if conversion else None
    if document is None:
        document = ScenarioDocument.from_dict(imported_document) if imported_document else load_document(target)
    extra = {sidecar: encode_artwork(assignments, slot, title, conversion, document)}
    if counters or counter_path(target).exists():
        extra[counter_path(target)] = encode_counters(counters)
    if presentation or presentation_path(target).exists():
        extra[presentation_path(target)] = encode_presentation(presentation)
    save_with_artwork(data, target, assignments, runtime_slot=slot, extra_files=extra)
