# Stalingrad and Operation Crusader scenarios

All **10 Stalingrad** and **6 Operation Crusader** scenarios are converted for
patched D-Day. Use them for play or as starting points for editing. The prepared
DOS files are in `scenarios/dos/SCENARIO/STALINGR` and
`scenarios/dos/SCENARIO/CRUSADER`.

Copy those folders into your playing copy's `SCENARIO` directory and run
[SELECT.BAT](../game/waw/dday/SELECT.BAT) beside `INVADE.EXE`. Choose the game
and battle, then **Begin New Game**. See the [scenario index](SCENARIO_PACK.md)
for titles and filenames, and [installation](../game/waw/README.md) for setup.

## Open and edit

**File → Open** accepts an original Stalingrad or Crusader SCN and creates an
unsaved D-Day editing document with the appropriate game profile. Use **Save As**
to keep your edited version. **File → Conversion Notes** lists the adaptations
for that scenario.

Prepared editing documents are also available under
`scenarios/converted/stalingr` and `scenarios/converted/crusader`. Keep each
folder's `assets` subfolder with its SCNs. Existing documents retain their saved
profiles; opening an original creates a document with the source-game defaults.

After editing, use **File → Export for DOS** and copy the matching **SCN, REZ
and AI** into the patched game's `SCENARIO` directory.

## Conversion coverage

| Area | Result |
| --- | --- |
| Map | Dimensions, terrain, directional features, hilltops and ownership |
| Artwork | Source terrain plus ground-unit and leader chits, assigned to D-Day artwork slots |
| Units | Names, ratings, quality, mobility, positions, availability and reinforcement dates |
| Organization | HQ hierarchy, assignments and staff-assistance settings |
| Artillery | Weapon ratings, range and related settings |
| Leaders | Names, effects, attachments, home HQs and chits |
| Objectives | Locations, names, values, radii and ownership, with scoring starting at zero |
| Text | Briefings and place names |
| Calendar | Dates, duration and the source scenario's turns per day |
| Weather | Historical weather and initial snow, ice and wetness |
| Supply | Daily deliveries, entry locations and stocks, adapted to D-Day supply groups and depots |
| Replacements and garrisons | Stalingrad's schedules, pools and garrison records |

## Rules and adaptations

Converted scenarios run with D-Day's combat, movement and supply systems. Their
[game profiles](GAME_PROFILES.md) set victory ratios and winter behavior;
Stalingrad uses an adapted Stalingrad winter model, while Crusader uses D-Day's.
Review conversion notes and playtest balance after making changes.

D-Day provides six artwork variants per terrain rule. If a source uses more,
conversion keeps the six most-used pictures and assigns the others to the
closest retained picture with the same rule. Conversion Notes lists affected
hexes. The complete source artwork remains available in the terrain library.
Use [terrain rules](TERRAIN_RULES.md) to tune the assigned slots.

The Stalingrad campaign retains **189 turns at three turns per day**. The
MANSTEIN, TANKS and QUIET scenarios also retain their three-turn day. Other
source scenarios use six turns per day. Date, weather and supply controls use
the imported scenario's time scale.

Commonwealth and Polish units use D-Day's Allied nationality slot; Italian
units use its Italian slot. Names, stats and chits retain their source identity.
Use **Artwork** to select flags, portraits and side emblems for the scenario.

Crusader HQ stock becomes the initial HQ reserve and distribution limit.
Its depot locations are retained with D-Day stock settings. Crusader uses
D-Day casualty class values with equal nationality weighting; its replacement
schedule starts empty and can be authored in Scenario Settings.

Ground units start with fresh orders and transport state. Configure individual
[orders](UNIT_LOGISTICS_AND_ORDERS.md) and formation-wide
[Battle Plans](NESTED_EVENTS.md) in the editor.

## Command-line conversion

Run from the project folder with your original games in `game/waw`:

```sh
python3 scenario_converter.py game/waw --dry-run
python3 scenario_converter.py game/waw/operation_crusader/SCENARIO/DUCE.SCN -o my-scenarios/DUCE.SCN
python3 scenario_converter.py game/waw --dos -d my-dos-scenarios
```

`--dry-run` checks conversion in memory. Directory input searches recursively
for earlier-game scenarios. Editing output includes an `assets` folder;
`--dos` writes matching SCN/REZ/AI sets with distinct `ST` and `OC` filenames.
Choose a new output destination for each batch.
