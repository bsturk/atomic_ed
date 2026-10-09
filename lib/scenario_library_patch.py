"""Select independently reversible D-Day patch layers by verified fingerprint."""
import json

from lib.binary_patch import apply_component, digest
from lib.dday_patch import PATCHES, apply_engine_patch, patch_manifest

COMPONENTS = ('engine', 'code-space', 'scenario-library', 'presentation', 'custom-artwork', 'advanced-orders', 'support-artwork', 'game-profiles', 'terrain-rules', 'nested-events', 'startup-selection', 'music', 'air-weather', 'library', 'all')


def apply_patch_set(data, component='all', *, reverse=False):
    if component not in COMPONENTS:
        raise ValueError(f'Unknown patch component: {component}')
    if component in ('music', 'library', 'all'):
        # Upgrade/undo the first shipped music layer without accepting
        # unrelated executable changes or retaining a fallback executable.
        legacy = json.loads((PATCHES/'history/dday-music-v1.json').read_bytes())
        if digest(data) == legacy['patched_sha256']:
            data = apply_component(data, PATCHES/'history', 'dday-music-v1', reverse=True)
    if component == 'engine':
        return apply_engine_patch(data, reverse=reverse)
    if component in ('code-space', 'scenario-library', 'presentation', 'custom-artwork', 'advanced-orders', 'support-artwork', 'game-profiles', 'terrain-rules', 'nested-events', 'startup-selection', 'music', 'air-weather'):
        return apply_component(data, PATCHES, 'dday-'+component, reverse=reverse)
    engine = patch_manifest()
    space = json.loads((PATCHES/'dday-code-space.json').read_bytes())
    library = json.loads((PATCHES/'dday-scenario-library.json').read_bytes())
    presentation = json.loads((PATCHES/'dday-presentation.json').read_bytes())
    custom = json.loads((PATCHES/'dday-custom-artwork.json').read_bytes())
    advanced = json.loads((PATCHES/'dday-advanced-orders.json').read_bytes())
    support = json.loads((PATCHES/'dday-support-artwork.json').read_bytes())
    profiles = json.loads((PATCHES/'dday-game-profiles.json').read_bytes())
    terrain = json.loads((PATCHES/'dday-terrain-rules.json').read_bytes())
    nested = json.loads((PATCHES/'dday-nested-events.json').read_bytes())
    startup = json.loads((PATCHES/'dday-startup-selection.json').read_bytes())
    music = json.loads((PATCHES/'dday-music.json').read_bytes())
    air_weather = json.loads((PATCHES/'dday-air-weather.json').read_bytes())
    states = [engine['source_sha256'], engine['patched_sha256'],
              space['patched_sha256'], library['patched_sha256'], presentation['patched_sha256'], custom['patched_sha256'],
              advanced['patched_sha256'], support['patched_sha256'], profiles['patched_sha256'], terrain['patched_sha256'], nested['patched_sha256'], startup['patched_sha256'], music['patched_sha256'], air_weather['patched_sha256']]
    try:
        current = states.index(digest(data))
    except ValueError:
        raise ValueError('Unsupported or modified D-Day executable') from None
    target = (0 if component == 'all' else 1) if reverse else len(states)-1
    if component == 'library' and current == 0:
        raise ValueError('Apply the engine patch first, or use --component all')
    operations = (apply_engine_patch,
                  lambda b, **kw: apply_component(b, PATCHES, 'dday-code-space', **kw),
                  lambda b, **kw: apply_component(b, PATCHES, 'dday-scenario-library', **kw),
                  lambda b, **kw: apply_component(b, PATCHES, 'dday-presentation', **kw),
                  lambda b, **kw: apply_component(b, PATCHES, 'dday-custom-artwork', **kw),
                  lambda b, **kw: apply_component(b, PATCHES, 'dday-advanced-orders', **kw),
                  lambda b, **kw: apply_component(b, PATCHES, 'dday-support-artwork', **kw),
                  lambda b, **kw: apply_component(b, PATCHES, 'dday-game-profiles', **kw),
                  lambda b, **kw: apply_component(b, PATCHES, 'dday-terrain-rules', **kw),
                  lambda b, **kw: apply_component(b, PATCHES, 'dday-nested-events', **kw),
                  lambda b, **kw: apply_component(b, PATCHES, 'dday-startup-selection', **kw),
                  lambda b, **kw: apply_component(b, PATCHES, 'dday-music', **kw),
                  lambda b, **kw: apply_component(b, PATCHES, 'dday-air-weather', **kw))
    while current != target:
        if current < target:
            data = operations[current](data)
            current += 1
        else:
            current -= 1
            data = operations[current](data, reverse=True)
    return bytes(data)
