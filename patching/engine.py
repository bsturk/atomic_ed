"""Apply the D-Day weather/victory/AI patch to its exact supported binary."""
import hashlib
import json
from .paths import PATCHES


def patch_manifest():
    return json.loads((PATCHES / 'dday-weather-400.json').read_bytes())


def apply_engine_patch(data, *, reverse=False):
    manifest = patch_manifest()
    original, patched = manifest['source_sha256'], manifest['patched_sha256']
    source, target = (patched, original) if reverse else (original, patched)
    digest = hashlib.sha256(data).hexdigest()
    if reverse and digest not in (source, target):
        # The shared launcher customizes only these menu/footer labels. Restore
        # them before checking the exact patched hash; reject all other edits.
        normalized = bytearray(data)
        offset = manifest['title_table_offset']
        titles = bytes.fromhex(manifest['title_table'])
        normalized[offset:offset + len(titles)] = titles
        if hashlib.sha256(normalized).hexdigest() == source:
            data, digest = normalized, source
    if digest == target:
        return bytes(data)
    if digest != source:
        raise ValueError('Unsupported or modified INVADE.EXE; this patch requires the verified D-Day binary')
    patch = (PATCHES / ('dday-weather-400.undo.ips' if reverse else 'dday-weather-400.ips')).read_bytes()
    if hashlib.sha256(patch).hexdigest() != manifest['undo_sha256' if reverse else 'ips_sha256']:
        raise ValueError('Weather patch checksum mismatch')
    if not patch.startswith(b'PATCH') or not patch.endswith(b'EOF'):
        raise ValueError('Invalid IPS patch')
    result = bytearray(data)
    cursor = 5
    while cursor < len(patch) - 3:
        offset = int.from_bytes(patch[cursor:cursor + 3], 'big')
        size = int.from_bytes(patch[cursor + 3:cursor + 5], 'big')
        cursor += 5
        if not size or cursor + size > len(patch) - 3 or offset + size > len(result):
            raise ValueError('Invalid IPS record bounds')
        result[offset:offset + size] = patch[cursor:cursor + size]
        cursor += size
    if cursor != len(patch) - 3 or hashlib.sha256(result).hexdigest() != target:
        raise ValueError('Patched executable checksum mismatch')
    return bytes(result)
