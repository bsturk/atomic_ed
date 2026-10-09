# Stalingrad and Operation Crusader → D-Day

Game installations, generated scenario packs and extracted artwork are local
data, excluded from Git. See the [repository setup guide](../README.md#run-the-editor)
and [scenario pack index](SCENARIO_PACK.md) to prepare them.

Updated 2026-10-08. All **10 staged Stalingrad SCNs and 6 Operation Crusader
SCNs** are preconverted for play in
`scenarios/dos/SCENARIO`, alongside all 27 V4V
scenarios. Copy its `STALINGR`, `CRUSADER` and `V4V` subfolders into the playing
copy's `SCENARIO` folder, with [SELECT.BAT](../game/waw/dday/SELECT.BAT) from
`game/waw/dday` beside the patched `INVADE.EXE`.
Run `SELECT` to stage a battle, then select it in the game. No individual export
is needed. The [pack index](SCENARIO_PACK.md) lists source and staged
filenames: staging uses `ST` prefixes for Stalingrad and `OC` for Crusader,
preserving both campaigns without replacing D-Day's. These exports include the
current source-game profiles and artwork.

Original SCNs can also be opened directly in the editor. Opening an earlier format creates
an unsaved document with a source-game profile; Save As writes a separate file. Original game files
are preserved. These are adaptations to D-Day's engine, not ports of the older
executables and their rules. The [game profile](GAME_PROFILES.md) now applies
verified victory ratios and adapted Stalingrad winter behavior. Original source
records are retained in the existing artwork companion for future translations.

Preconverted editing documents are in `scenarios/converted/stalingr` and
`scenarios/converted/crusader`. Each folder has SCNs plus an `assets`
subfolder containing the necessary terrain/chit companions. Keep those
companions with the documents. Conversion provenance and adaptations are stored
inside the terrain companion and shown by **File → Conversion Notes**. There
are no separate report files or game-tree copies.

The older documents under `scenarios/converted` predate Game Profile support
and retain their existing rules for compatibility. The ready-to-play pack was
rebuilt from the originals with current conversion settings. For a fresh editing
document with those settings, open an original SCN directly in the editor.
Existing edited conversions are not overwritten or assigned different rules.

```sh
python3 scenario_converter.py game/waw --dry-run
python3 scenario_converter.py game/waw
python3 scenario_converter.py game/waw/operation_crusader/SCENARIO/DUCE.SCN -o /tmp/DUCE.SCN
python3 scenario_converter.py game --dos -d /tmp/waw-dos/SCENARIO
```

Directory input is recursive, skips native D-Day documents, and separates mixed
source games into folders for editing documents. `--dos` produces a single folder
of matching SCN/REZ/AI sets with distinct filenames instead. Existing outputs
are never overwritten. An optional `--report /tmp/report.json` writes diagnostics.

For subsequent edits, use **File → Export for DOS**, then copy its three files as described
in [the installation guide](../game/waw/README.md). Use the current
`INVADE-PATCHED.EXE`, including `game-profiles`, and retain the exported basenames.
The binary selects their companion files automatically.

## Converted data

| Source data | D-Day editing document |
| --- | --- |
| Map rectangle and shared hex records | Original dimensions, roads, river/terrain-edge masks, hill flags and territorial ownership; occupied-hex lists rebuilt from units |
| Terrain graphics | Source summer/winter artwork assigned to compatible D-Day terrain rules; see the six-picture limit below |
| OOB | Every ground/support unit, name, base/current ratings, quality, mobility, availability, coordinates and reinforcement date |
| Unit graphics | Every referenced ground-unit and leader chit, with identical indexed pixels; identical pictures are packed together to fit D-Day's sheets |
| HQ organization | Source parent relationships, levels, subordinate lists and ground/artillery automation; D-Day lists and command spans rebuilt |
| Artillery | Source auxiliary weapon ratings and range/flags, translating Stalingrad floats to D-Day fixed-point numbers |
| Leaders | Names, effects, attachments, home HQs and chits |
| Objectives | Locations, side-specific points, radii, names and ownership; initial accumulated scores are reset |
| Briefings and labels | Full 2,048-byte briefing region and place-name text/positions/sizes; Crusader's label color becomes D-Day style `V` |
| Calendar | Original civil dates, turn counts and reinforcement timestamps; Stalingrad's operational scenarios retain their three-turn day |
| Weather | Authored historical sequence and initial snow, ice and wetness; no generated-weather parameter translation |
| Supply | Daily quantities, source entry locations and stock; Stalingrad's depot records retained, Crusader depot model adapted |
| Replacements and garrisons | Stalingrad's schedules, initial pools and garrison records; Crusader has no serialized replacement schedule |
| Casualty scoring | Stalingrad's class values and nationality multipliers; Crusader uses D-Day class values with equal nationality weighting |

The portable unit library is rebuilt using this full translation, including the
source artillery definitions. Earlier WaW unit imports no longer borrow D-Day
artillery records or movement ratings. It contains **15,401 templates across all
50 staged scenarios**, including native D-Day and V4V. The terrain library also
includes Crusader's water/coast column 1, previously omitted from the palette.

## Engine adaptations

- D-Day retains its combat, movement, supply-consumption and victory-tier
  rules. Scenario-specific routines in the older executables are not SCN data
  and are not translated. HQ automation survives; source runtime battlegroup
  allocations, movement paths and mounted passenger links are reset for a fresh
  scenario. Authored conditional/timed orders can be added in Battle Plans.
- D-Day permits six pictures per terrain rule. When a source map uses more,
  conversion retains the six most-used distinct pictures and maps the rest to
  the closest retained picture **with the same selected D-Day rule**. Notes
  record each substitution and affected hex count. All source images remain
  individually available in the editor's terrain library. The rule mapping is
  an approximation: desert wadis, steppe, industrial ground and other source
  features use D-Day's available rules and network rendering.
- The large Stalingrad campaign retains **189 turns at three turns per day**.
  D-Day's date parser reads Calendar+28 and still supports this operational
  scale. The editor uses that scale in date displays, date rebasing, weather,
  supply and replacement schedules. MANSTEIN/TANKS and QUIET also retain their
  three-turn day; other source scenarios retain six. Version 4 also supports
  authored/converted scenarios up to 400 turns, including the long V4V campaigns,
  without overflowing victory history.
- Commonwealth and Polish nationality codes become D-Day's Allied code;
  Italian units become its Italian code. Names, stats and chits remain. D-Day
  menus retain native decorations. The Artwork page can replace side portraits,
  flags, emblems and turn-screen art with library or custom images; conversion
  alone keeps their D-Day defaults. New DOS exports generate
  scenario previews, mini-maps and banners for the library executable.
- Crusader supplies one current HQ stock value. Conversion preserves it as
  D-Day reserve and uses the same amount as the initial distribution limit.
  Net-received accounting starts at zero; HQ +8 is not a capacity field. Its distribution-depot coordinates are retained and an
  empty D-Day reserve depot is added. The stocked-depot models are not equivalent.
- Historical weather is used even where the source executable could generate
  a new climate. Source generation parameters, unused tail bytes and other
  opaque serialized data are retained as compressed source records inside the
  editing document. `ScenarioDocument.source_blocks()` reads them without the
  original installation. The conversion report also records offsets and hashes.

## Verified format details

`lib/waw_reader.py` follows each protected-mode executable's LoadGame/RW
sequence. The first uint32 is a **serialized block length**, not a magic followed
by a common 96-byte header. Older fixed-offset/pointer reports in this repository
are historical and should not guide writes.

| Object | Stalingrad | Crusader | D-Day |
| --- | --- | --- | --- |
| Scenario | `0xf4a` bytes | `0xdac` bytes | `0x1230` bytes |
| Calendar | 42 bytes | 42 bytes | 42 bytes |
| OB record | 168 bytes, float ratings | 150 bytes, fixed-point ratings | 172 bytes, fixed-point ratings |
| HQ auxiliary | 34 bytes | 12 bytes, including dummy slot 0 | 58 bytes |
| Artillery auxiliary | 28 bytes, float ratings | 28 bytes, fixed-point ratings | 28 bytes, fixed-point ratings |
| Leader | 36 bytes | 30 bytes | 36 bytes |
| Supply stock | 136 bytes per group | One 220-byte block: two 110-byte records | 136 bytes per group |
| Depot | 24 bytes | 52 bytes | 24 bytes |
| Weather | 2,146 bytes | 494 bytes | 794 native / 1,222 patched |

Crusader's HQ-list prefix counts only one of two arrays stored under it. Plane
class tables also store twice their declared prefix length. Optional leaders,
garrisons and riders depend on header counts. These details prevent subsequent
blocks from being misaligned.

Relevant **code-object offsets**, not whole-file offsets:

- Stalingrad `LoadGame`: `0x23909–0x23d15`; `RWOB`: `0x262f6`;
  `RWWeather`: `0x25fe9`; `SetCalUTs`: `0x2cdfd–0x2ced5`;
  nationality casualty multiplier: `0x5041f–0x50425`.
- Crusader `LoadGame`: `0x22377–0x22699`; `RWOB`: `0x2492d`;
  `RWWeather`: `0x24698`; `RWStock`: `0x243ee`; HQ lists: `0x2575d`;
  `GetUnitSize`: `0x41f97`; `DrawTownName`: `0x1dfb0–0x1e1a8`.
- Crusader historical weather starts at absolute timestamp **91764** (object 3
  `+0x5ba1`), not the scenario start. Stalingrad's authored temperature/cloud
  arrays are at **Weather+0xf8/+0x61c**; its live arrays at `+0x300/+0x720` can
  be empty in an SCN and must not be substituted for the historical sequence.
- D-Day `UTParser` at `0x2d38f` reads Calendar+28 as the turn scale;
  `IncrementCal` at `0x2d5c4` wraps the phase against that same value. Keeping
  scale-3 rules with a six-phase calendar is inconsistent and is not used.
- Stalingrad scenario titles come from `STALIN.EXE`'s table at file `0x10aa41`;
  Crusader's title table starts at `CRUSADER.EXE` file `0xf7e20`.

## Validation

`tools/test_waw_conversion.py` checks every staged source, complete output
roundtrips, unit counts/stats/quality, exact unit and leader pixels, HQ hierarchy,
objectives, briefings, labels, directional map data, weather dates, supply,
replacements and source preservation. GUI checks cover import, map editing,
Save As, reopen, matching SCN/REZ/AI export and source-overwrite prevention.

`tools/test_victory_patch.py` executes the actual patched x86 loader and history
writer at two relocated addresses, checking native/extended saves, both sides'
totals, heap guards and turns 260, 261, 378 and 400. It verifies that the real LE
relocation cells within the replaced routines retain their original operands.
See [patch notes](../game/waw/patches/README.md) for DOSBox-X runtime checks.
These checks do not establish identical gameplay or campaign balance.
