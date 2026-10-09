# V for Victory scenarios

All **27 V for Victory scenarios** are converted for patched D-Day and prepared
in `scenarios/dos/SCENARIO/V4V`. They are available for play and as starting
points for editing.

Copy the `V4V` folder into your playing copy's `SCENARIO` directory and run
[SELECT.BAT](../game/waw/dday/SELECT.BAT) beside `INVADE.EXE`. Choose a battleset
and scenario, then **Begin New Game**. See the [scenario index](SCENARIO_PACK.md)
and [installation guide](../game/waw/README.md).

## Supported battlesets

| Battleset | Scenario prefix | Required source files | Scenarios |
| --- | --- | --- | ---: |
| Utah Beach | UB | `UTAH.BTL`, `UTAH.RES` | 6 |
| Velikiye Luki | VL | `VELIKIYE.BTL`, `VL.RES` | 7 |
| Market Garden | MG | `MARKET.BTL`, `MG.RES` | 7 |
| Gold/Juno/Sword | GJS | `GJS.BTL`, `GJS.RES` | 7 |

## Open and edit

**File → Open** accepts an original V4V SCN. Keep its battleset and resource
files beside it while importing. The editor creates an unsaved D-Day document
with a V4V game profile, using the Velikiye Luki winter variant where applicable.

Use **Save As** to keep your version. Converted editing documents store their
terrain, chits, profile and conversion notes in an `assets` subfolder. Keep that
folder with the SCN. **File → Conversion Notes** describes the scenario's
adaptations. Existing editing documents retain their saved settings.

**File → Export for DOS** writes matching **SCN, REZ and AI** files. Copy all
three into the patched game's `SCENARIO` directory and retain them when resuming
saved games.

## Conversion coverage

| Area | Result |
| --- | --- |
| Map | Active scenario area from the battleset, adjusted to D-Day hex staggering |
| Terrain | Source terrain mapped to D-Day rules, with source artwork and derived small/night variants |
| Directional features | Roads, railways, water and slope connections adapted to D-Day rendering |
| Units | Names, side, nationality, class, combat ratings, quality, fatigue, positions and arrival times |
| Chits | Source ground-unit pictures |
| Organization | D-Day HQ and support-category records built for the imported roster |
| Objectives and labels | Names, values and positions within the converted map |
| Briefings | Both sides' complete briefing text |
| Calendar and weather | Source dates and historical weather, with up to 400 scenario turns |
| Initial ground | Snow, ice and wetness accumulated using the adapted V4V profile |
| Supply | Source daily quantities and entry locations, with D-Day initial stock and depot settings |

## Rules and scenario setup

These conversions use D-Day's combat, supply and tactical AI together with the
selected [game profile](GAME_PROFILES.md). Victory ratios start at 200% for
major victory and 125% for minor victory. Objective values, casualty weights
and those ratios are editable in Scenario Settings.

Weapon and HQ details use matching D-Day templates. Conversion Notes identifies
the template choices. Check important formations in **Unit Definition** and
**HQ Organization** when adapting a battle.

Battle Plans, saved orders, leaders, garrisons and replacement schedules start
empty; HQ staff assistance starts disabled. Author them in the editor to suit
your scenario. Cosmetic edges and hilltops can be added with the map tools.
Territorial ownership follows the source map, and unit positions determine
initial occupied hexes.

Directional features use D-Day's interpretation of the imported connections.
Review important crossings and slopes on Map and during play. D-Day terrain
slots and supply rules can give source values different effects, so playtest
the battle's balance after adjusting it.

The [editor guide](SCENARIO_EDITOR_README.md) covers terrain, formations,
artwork and scenario settings; [Battle Plans](NESTED_EVENTS.md) covers events.

## Command-line conversion

Run from the project folder with the editor's Python dependencies installed:

```sh
python3 scenario_converter.py game/v4v --dry-run
python3 scenario_converter.py game/v4v/MGFIRST.SCN -o my-scenarios/MGFIRST.SCN
python3 scenario_converter.py game/v4v --dos -d my-v4v-dos-scenarios
```

`--dry-run` checks the conversions in memory. For editing output, each SCN has
artwork in the accompanying `assets` folder. `--dos` writes the matching
SCN/REZ/AI sets for installation. Choose a new output destination for each batch.
