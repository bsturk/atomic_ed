#!/usr/bin/env python3
"""Convert earlier WaW and V for Victory scenarios into documents or DOS exports."""
import argparse
import hashlib
import json
from pathlib import Path

from lib.counter_artwork import counter_path
from lib.scenario_assets import save_scenario_assets, export_for_dos
from lib.game_profiles import ScenarioDocument
from lib.scenario_library import dos_filename
from lib.terrain_artwork import artwork_path
from lib.scenario_import import convert_scenario, source_game


def destinations(target, *, dos=False):
    if dos:
        return [target, target.with_suffix('.REZ'), target.with_suffix('.AI')]
    return [target, artwork_path(target), counter_path(target)]


def dos_export_name(source, game):
    """Keep all staged games together without colliding with native D-Day slots."""
    prefix = {'stalingrad': 'ST', 'operation_crusader': 'OC'}.get(game, '')
    stem = Path(source).stem.upper()
    if prefix:
        stem = 'CAMP' if stem == 'CAMPAIGN' else stem[:6]
    return dos_filename(prefix + stem + '.SCN')


def convert_file(source, target, *, dry_run=False, dos=False):
    source, target = Path(source), Path(target)
    if source.resolve() == target.resolve():
        raise ValueError('Conversion must write a separate file, never the source scenario')
    if dos:
        dos_filename(target.name)
    if not dry_run and any(p.exists() for p in destinations(target, dos=dos)):
        raise FileExistsError(f'Output already exists: {target}; choose a new destination')
    data, terrain, counters, report = convert_scenario(source)
    if not dry_run:
        target.parent.mkdir(parents=True, exist_ok=True)
        if dos:
            document = ScenarioDocument.from_dict(report['document'])
            export_for_dos(data, target, terrain, counters=counters,
                           title=report['title'], document=document)
        else:
            save_scenario_assets(data, target, terrain, report.get('runtime_slot', 'BRADLEY.SCN'),
                                 counters=counters, title=report['title'], conversion=report)
        report.update(output=str(target))
    if hashlib.sha256(source.read_bytes()).hexdigest() != report['source_sha256']:
        raise ValueError('Source changed during conversion')
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description='Convert Stalingrad, Crusader and V4V SCNs to D-Day scenarios')
    parser.add_argument('input', type=Path, help='SCN or game directory (searched recursively); V4V needs adjacent BTL/RES files')
    outputs = parser.add_mutually_exclusive_group()
    outputs.add_argument('-o', '--output', type=Path, help='Output SCN for a single-file conversion')
    outputs.add_argument('-d', '--output-dir', type=Path, help='Output directory (default: scenarios/converted/<game>)')
    parser.add_argument('--dry-run', action='store_true', help='Convert and validate in memory without writing')
    parser.add_argument('--dos', action='store_true',
                        help='Write ready-to-play SCN/REZ/AI sets (default: scenarios/dos/SCENARIO); uses unique ST/OC filenames')
    parser.add_argument('--report', type=Path, help='Write an optional diagnostic JSON report to this file')
    args = parser.parse_args(argv)
    if args.input.is_dir():
        if args.output:
            parser.error('Use --output-dir when converting a directory')
        sources = sorted(p for p in args.input.rglob('*') if p.suffix.upper() == '.SCN' and p.is_file())
        try:
            sources = [p for p in sources if source_game(p) != 'dday']
        except (OSError, ValueError) as exc:
            parser.error(str(exc))
    elif args.input.is_file():
        sources = [args.input]
    else:
        parser.error(f'Input not found: {args.input}')
    if not sources:
        parser.error('No SCN files found')
    try:
        games = [source_game(source) for source in sources]
    except (OSError, ValueError) as exc:
        parser.error(str(exc))
    mixed = len(set(games)) > 1
    try:
        targets = [args.output or
                   ((args.output_dir or Path('scenarios/dos/SCENARIO'))/dos_export_name(source, game)
                    if args.dos else
                    ((args.output_dir/game if mixed else args.output_dir) if args.output_dir
                     else Path('scenarios/converted')/game)/source.name)
                   for source, game in zip(sources, games)]
        if args.dos:
            for target in targets:
                dos_filename(target.name)
    except ValueError as exc:
        parser.error(str(exc))
    if len({p.resolve() for p in targets}) != len(targets):
        parser.error('More than one input has the same game/filename; convert those folders separately')
    if args.report and not args.dry_run:
        reserved = sources + [path for target in targets for path in destinations(target, dos=args.dos)]
        if args.report.exists() or args.report.resolve() in {path.resolve() for path in reserved}:
            parser.error('Report destination must be a new file separate from the scenarios and artwork')
    for source, target in zip(sources, targets):
        if source.resolve() == target.resolve():
            parser.error('The output would overwrite a source scenario')
        if not args.dry_run and any(p.exists() for p in destinations(target, dos=args.dos)):
            parser.error(f'Output already exists: {target}; choose a new destination')
    reports, failures = [], []
    for source, target in zip(sources, targets):
        try:
            report = convert_file(source, target, dry_run=args.dry_run, dos=args.dos)
            reports.append(report)
            width, height = report['map_size']
            print(f'{source.name}: {width}x{height}, {sum(report["unit_counts"])} units — {report["title"]}', flush=True)
        except (OSError, ValueError, KeyError) as exc:
            failures.append({'source': str(source), 'error': str(exc)})
            print(f'{source.name}: FAILED: {exc}', flush=True)
    if not args.dry_run and args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps({'converted': len(reports), 'failed': failures,
                                      'scenarios': reports}, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    print(f'{len(reports)} {"validated" if args.dry_run else "converted"}; {len(failures)} failed. '
          + ('Copy the SCN/REZ/AI sets into the patched D-Day game’s SCENARIO folder.' if args.dos else
             'Open in the editor and use File → Export for DOS for manual installation. See Conversion Notes for adaptations.'))
    return bool(failures)


if __name__ == '__main__':
    raise SystemExit(main())
