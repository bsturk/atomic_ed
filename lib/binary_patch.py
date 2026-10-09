"""Fingerprint-checked IPS patches, including file growth and exact undo size."""
import hashlib
import json
from pathlib import Path


def digest(data):
    return hashlib.sha256(data).hexdigest()


def encode_ips(source, target):
    result = bytearray(b'PATCH')
    pos = 0
    while pos < len(target):
        if pos < len(source) and source[pos] == target[pos]:
            pos += 1
            continue
        start = pos
        if start == int.from_bytes(b'EOF', 'big'):
            start -= 1
        pos += 1
        while pos < len(target) and pos-start < 65535:
            # A few equal bytes cost less than another five-byte record header.
            if pos+5 <= len(source) and source[pos:pos+5] == target[pos:pos+5]:
                break
            pos += 1
        result += start.to_bytes(3, 'big')+(pos-start).to_bytes(2, 'big')+target[start:pos]
    return bytes(result)+b'EOF'+len(target).to_bytes(3, 'big')


def write_patch(folder, name, source, target, **metadata):
    folder = Path(folder)
    patch, undo = encode_ips(source, target), encode_ips(target, source)
    manifest = dict(name=name, source_sha256=digest(source), patched_sha256=digest(target),
                    source_size=len(source), patched_size=len(target),
                    ips_sha256=digest(patch), undo_sha256=digest(undo), **metadata)
    folder.mkdir(parents=True, exist_ok=True)
    (folder/f'{name}.ips').write_bytes(patch)
    (folder/f'{name}.undo.ips').write_bytes(undo)
    (folder/f'{name}.json').write_text(json.dumps(manifest, indent=2)+'\n')
    return manifest


def apply_component(data, folder, name, *, reverse=False):
    folder = Path(folder)
    manifest = json.loads((folder/f'{name}.json').read_bytes())
    source, target = (('patched', 'source') if reverse else ('source', 'patched'))
    if digest(data) == manifest[f'{target}_sha256']:
        return bytes(data)
    if digest(data) != manifest[f'{source}_sha256'] or len(data) != manifest[f'{source}_size']:
        raise ValueError(f'{name}: unsupported input; apply components in their documented order')
    suffix, checksum = ('.undo.ips', 'undo_sha256') if reverse else ('.ips', 'ips_sha256')
    patch = (folder/f'{name}{suffix}').read_bytes()
    if digest(patch) != manifest[checksum] or not patch.startswith(b'PATCH'):
        raise ValueError(f'{name}: damaged patch')
    result, cursor = bytearray(data), 5
    size = manifest[f'{target}_size']
    while cursor+3 <= len(patch) and patch[cursor:cursor+3] != b'EOF':
        if cursor+5 > len(patch):
            raise ValueError('Truncated IPS record')
        offset = int.from_bytes(patch[cursor:cursor+3], 'big')
        count = int.from_bytes(patch[cursor+3:cursor+5], 'big')
        cursor += 5
        if not count or cursor+count > len(patch) or offset+count > size:
            raise ValueError('Invalid IPS record bounds')
        if len(result) < offset+count:
            result.extend(bytes(offset+count-len(result)))
        result[offset:offset+count] = patch[cursor:cursor+count]
        cursor += count
    if patch[cursor:cursor+3] != b'EOF' or len(patch)-cursor != 6:
        raise ValueError('Invalid IPS terminator')
    if int.from_bytes(patch[-3:], 'big') != size:
        raise ValueError('Invalid IPS target size')
    del result[size:]
    if len(result) < size:
        result.extend(bytes(size-len(result)))
    if digest(result) != manifest[f'{target}_sha256']:
        raise ValueError('Patched executable checksum mismatch')
    return bytes(result)
