# Ready-to-play scenarios

Prepared from all staged originals using the current converters:
**10 Stalingrad + 6 Operation Crusader + 27 V for Victory = 43 scenarios**.
The folder names match the renamed editing folders: `STALINGR`, `CRUSADER`,
and `V4V`. This pack contains DOS-ready SCN/REZ/AI sets; the separate
`scenarios/converted` documents contain editor JSON artwork and cannot be
staged directly by a DOS batch file.

This is the index of the locally generated pack. SCN/REZ/AI files are excluded
from the source repository. Build exports from your own installations with
`scenario_converter.py --dos`, or use an already prepared pack.

## Install and select

Copy this pack's `SCENARIO` folder into your playing copy of D-Day, merging
with its existing folder. Copy [SELECT.BAT](../game/waw/dday/SELECT.BAT)
from `game/waw/dday` beside the playing copy's `INVADE.EXE`. The batch file
is maintained only with the game; this scenario pack contains no launcher copy.
The resulting layout is:

```text
INVADE.EXE              (your patched binary)
SELECT.BAT
DATA\PCWATW.REZ         (D-Day's original base artwork)
SCENARIO\STALINGR\CAMPAIGN.SCN / .REZ / .AI
SCENARIO\STALINGR\CLASH.SCN / .REZ / .AI
SCENARIO\CRUSADER\CAMPAIGN.SCN / .REZ / .AI
SCENARIO\V4V\VLFORT.SCN / .REZ / .AI
...and the other scenarios listed below
```

From the game directory, run **`SELECT`**. Choose a game, then a battle;
V4V has a battleset submenu. **4. D-Day** lists the seven native scenarios,
which use the files already in the main `SCENARIO` folder and need no staging.
For a conversion, the batch copies the selected SCN/REZ/AI trio into that folder.
It then launches **`INVADE`** with that battle already selected. Choose
**Begin New Game**; the **Scenarios** panel shows the selected title and page.
Exiting the game returns to the batch menu; choose **0** there to quit.

Use the current `game/waw/dday/INVADE-PATCHED.EXE` as `INVADE.EXE`: automatic
selection needs its new `startup-selection` patch. When upgrading, replace both
`SELECT.BAT` and the executable. The batch writes a temporary `WAWSTART.TXT`
with the selected filename and removes it after the game exits. Missing or
invalid requested files stop startup, preventing an unintended fallback to
Bradley. Native Bradley itself remains unchanged and separately playable.

The menu needs MS-DOS 6.22's `CHOICE.COM` on PATH or DOSBox-X's built-in CHOICE.
No Python, editor or additional helper executable is needed. You can also
bypass the menu with uppercase directory and source names, without `.SCN`.
This argument form only stages/checks files and does not launch the game:

```dos
SELECT STALINGR CLASH
SELECT CRUSADER CAMPAIGN
SELECT V4V VLFORT
SELECT DDAY BRADLEY
```

Staging uses `ST` filenames for Stalingrad and `OC` for Crusader. Thus both
campaigns coexist with D-Day's `CAMPAIGN.SCN`. Previously staged scenarios
remain available, including their companions needed for saved games. Selecting
the same battle again replaces its staged trio with the packaged copy.
The batch file checks for all three source files before copying, retains the
subfolder sources, and leaves native scenarios, saves, and `DATA/PCWATW.REZ`
alone. If copying fails, it reports the failure; correct the problem and select
that battle again before playing it.

These remain adaptations to D-Day's engine, with current source-game profiles
and matching terrain, chits and previews. See [WaW conversion coverage](WAW_CONVERSION.md),
[V4V conversion coverage](V4V_CONVERSION.md), and
[general installation instructions](../game/waw/README.md).

## Scenario index

### D-Day (7 native scenarios)

These remain in the main `SCENARIO` folder of your game copy and use its base
artwork; no extra exports or copies are needed.

| Filename | Scenario |
| --- | --- |
| `BRADLEY.SCN` | Bradley's Nightmare |
| `COUNTER.SCN` | SS Counterattack |
| `STLO.SCN` | St Lo |
| `COBRA.SCN` | Operation Cobra |
| `UTAH.SCN` | Utah Beach |
| `OMAHA.SCN` | Omaha Beach |
| `CAMPAIGN.SCN` | America Invades! |

### Converted scenarios

Each source SCN has matching `.REZ` and `.AI` files in the same subfolder.
Some Stalingrad originals share titles; their filenames distinguish them.

### STALINGR - Stalingrad (10)

| Source filename | Staged filename | Scenario |
| --- | --- | --- |
| `CAMPAIGN.SCN` | `STCAMP.SCN` | Operation Uranus |
| `CITY.SCN` | `STCITY.SCN` | Rattenkrieg |
| `CLASH.SCN` | `STCLASH.SCN` | A River Too Far |
| `HURBERT.SCN` | `STHURBER.SCN` | To the Volga! |
| `MANSTEIN.SCN` | `STMANSTE.SCN` | Manstein's Solution |
| `QUIET.SCN` | `STQUIET.SCN` | Quiet Flows the Don |
| `RIVER.SCN` | `STRIVER.SCN` | A River Too Far |
| `TANKS.SCN` | `STTANKS.SCN` | Manstein's Solution |
| `VOLGA.SCN` | `STVOLGA.SCN` | To the Volga! |
| `WINTER.SCN` | `STWINTER.SCN` | Wintergewitter |

### CRUSADER - Operation Crusader (6)

| Source filename | Staged filename | Scenario |
| --- | --- | --- |
| `CAMPAIGN.SCN` | `OCCAMP.SCN` | Operation Crusader |
| `DUCE.SCN` | `OCDUCE.SCN` | Il Duce's Finest |
| `HELLFIRE.SCN` | `OCHELLFI.SCN` | Hell Fire Pass |
| `RELIEVED.SCN` | `OCRELIEV.SCN` | Tobruk Relieved |
| `RESCUE.SCN` | `OCRESCUE.SCN` | To The Rescue! |
| `TOBRUK.SCN` | `OCTOBRUK.SCN` | Fortress Tobruk |

### V4V - Gold/Juno/Sword (7)

| Source filename | Staged filename | Scenario |
| --- | --- | --- |
| `GJSBEACH.SCN` | `GJSBEACH.SCN` | Off the Beaches |
| `GJSBULL.SCN` | `GJSBULL.SCN` | Charge of the Bull |
| `GJSCAMP.SCN` | `GJSCAMP.SCN` | To Caen! |
| `GJSORNE.SCN` | `GJSORNE.SCN` | The Orne Bridges |
| `GJSRUN.SCN` | `GJSRUN.SCN` | The End Run |
| `GJSSEA.SCN` | `GJSSEA.SCN` | To the Sea |
| `GJSYOUTH.SCN` | `GJSYOUTH.SCN` | Attack of the 12th SS |

### V4V - Market Garden (7)

| Source filename | Staged filename | Scenario |
| --- | --- | --- |
| `MGBREAK.SCN` | `MGBREAK.SCN` | Breakout of 30th Corps |
| `MGCAMP.SCN` | `MGCAMP.SCN` | "A Bridge Too Far" |
| `MGDEST.SCN` | `MGDEST.SCN` | Destruction of the 1st |
| `MGEAGLES.SCN` | `MGEAGLES.SCN` | Screaming Eagles |
| `MGFIRST.SCN` | `MGFIRST.SCN` | The First Bridge |
| `MGHEIGHT.SCN` | `MGHEIGHT.SCN` | Groesbeeck Heights |
| `MGHELL.SCN` | `MGHELL.SCN` | Hell's Highway |

### V4V - Utah Beach (6)

| Source filename | Staged filename | Scenario |
| --- | --- | --- |
| `UBATTACK.SCN` | `UBATTACK.SCN` | SS Counter Attack |
| `UBCAMP.SCN` | `UBCAMP.SCN` | Campaign |
| `UBCARENT.SCN` | `UBCARENT.SCN` | Objective Carentan |
| `UBCARTER.SCN` | `UBCARTER.SCN` | Race for Carteret |
| `UBFINAL.SCN` | `UBFINAL.SCN` | Final Assault |
| `UBMOP.SCN` | `UBMOP.SCN` | Mopping Up |

### V4V - Velikiye Luki (7)

| Source filename | Staged filename | Scenario |
| --- | --- | --- |
| `VLCAMP.SCN` | `VLCAMP.SCN` | Campaign |
| `VLCITY.SCN` | `VLCITY.SCN` | Into the City |
| `VLEIGHT.SCN` | `VLEIGHT.SCN` | Eight More Kilometers |
| `VLFORT.SCN` | `VLFORT.SCN` | Fortress in the Snow |
| `VLLAST.SCN` | `VLLAST.SCN` | Last Chance |
| `VLRESCUE.SCN` | `VLRESCUE.SCN` | To the Rescue |
| `VLSTORM.SCN` | `VLSTORM.SCN` | Red Storm |

## Rebuilding exports (optional)

The converter can recreate the exported sets in a new, flat output folder:

```sh
python3 scenario_converter.py game --dos -d /tmp/waw-dos/SCENARIO
```

Run from the repository root with the editor's Python dependencies installed.
Existing output files are never overwritten. The flat CLI output can be copied
directly to the game's main SCENARIO folder and selected in the game without
using the batch file. To use SELECT, arrange the rebuilt files into the three
subfolders above using the source names in the index. Keep all three companion
basenames together. The prepared pack already has this layout.

## Validation

All 43 exported sets passed map/roster/weather, resource, profile, metadata and
orders checks. The actual patched x86 scenario-selector code selected all 50
entries (43 conversions plus seven native D-Day scenarios) with matching
resources, orders and rule values in the test harness. These checks do not
replace gameplay playtesting of every scenario.

`SELECT.BAT` was tested in DOSBox-X: all 43 selections copied byte-identical
SCN/REZ/AI sets (including empty AI files), both campaigns coexisted, and the
seven native scenarios, base artwork and existing save remained unchanged.
Repeat selection, missing-companion rejection, invalid input, interactive
Stalingrad/V4V selection, back/quit, and temporary-file cleanup were checked.

The D-Day submenu was checked for all seven entries, launch/return behavior,
missing-native-file handling, and preservation of installed scenarios. A DOS
test executable recorded launches for those checks; a separate DOSBox-X run
confirmed that selecting D-Day starts the actual patched game's splash screen.
Argument-based checks still return without launching the game. The startup
selection patch was then checked in DOSBox-X using the actual game: choosing
VLFORT selected **Fortress in the Snow**, and Begin New Game loaded Velikiye Luki
on December 20, 1942. Exiting returned to SELECT and removed its temporary hint.
