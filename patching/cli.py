"""Apply/reverse independent D-Day patches with binary fingerprint checks."""
import argparse
from pathlib import Path

from .layers import apply_patch_set, COMPONENTS


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable', type=Path)
    parser.add_argument('-o', '--output', type=Path, help='Default: patch in place with a .bak backup')
    parser.add_argument('--reverse', action='store_true')
    parser.add_argument('--component', choices=COMPONENTS, default='engine',
                        help='engine (default); code-space; scenario-library; presentation; custom-artwork; advanced-orders; support-artwork; game-profiles; terrain-rules; nested-events; startup-selection; music; air-weather; library (all layers above engine); all')
    args = parser.parse_args()
    original = args.executable.read_bytes()
    try:
        data = apply_patch_set(original, args.component, reverse=args.reverse)
    except ValueError as error:
        parser.error(str(error))
    target = args.output or args.executable
    if target.resolve() == args.executable.resolve() and data != original:
        backup = target.with_name(target.name + '.bak')
        if backup.exists() and backup.read_bytes() not in (original, data):
            parser.error(f'Backup already exists with different content: {backup}')
        if not backup.exists():
            backup.write_bytes(original)
    elif target.exists() and target.read_bytes() != data:
        parser.error(f'Output already exists: {target}')
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)
    print(f'{"Restored" if args.reverse else "Patched"}: {target}')
