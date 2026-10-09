# Ready-to-play scenarios

The prepared collection contains **43 converted scenarios**: 10 from Stalingrad,
6 from Operation Crusader, and 27 from V for Victory. Play them with patched
D-Day or use them as starting points for editing. SELECT also offers the seven
native D-Day scenarios.

## Install and select

1. Install `INVADE-PATCHED.EXE` as `INVADE.EXE` in your playing copy of D-Day.
2. Copy `STALINGR`, `CRUSADER` and `V4V` from `scenarios/dos/SCENARIO` into its
   `SCENARIO` folder.
3. Copy [SELECT.BAT](../game/waw/dday/SELECT.BAT) beside `INVADE.EXE`.
4. Run **SELECT**, choose a game and battle, then choose **Begin New Game**.

The resulting layout looks like this:

```text
INVADE.EXE
SELECT.BAT
DATA/PCWATW.REZ
SCENARIO/BRADLEY.SCN
SCENARIO/STALINGR/CLASH.SCN
SCENARIO/STALINGR/CLASH.REZ
SCENARIO/STALINGR/CLASH.AI
SCENARIO/CRUSADER/CAMPAIGN.SCN
SCENARIO/CRUSADER/CAMPAIGN.REZ
SCENARIO/CRUSADER/CAMPAIGN.AI
SCENARIO/V4V/VLFORT.SCN
SCENARIO/V4V/VLFORT.REZ
SCENARIO/V4V/VLFORT.AI
```

SELECT copies the chosen converted scenario and its companions into the main
`SCENARIO` folder, then launches the game with that battle selected. Stalingrad
uses `ST` destination names and Crusader uses `OC`, so their campaigns coexist
with D-Day's. The tables below show the names.

**4. D-Day** offers the seven native scenarios. Exiting the game returns to the
menu; choose **0** to quit. DOSBox-X provides the menu's `CHOICE` command and
ANSI display support. On MS-DOS, use `CHOICE.COM` and load `ANSI.SYS` for color.

Keep staged SCN/REZ/AI files available when resuming saves. Selecting a battle
again restores its packaged files, so keep customized exports under their own
unique names. Use the DOS pack for SELECT; keep `scenarios/converted` and its
`assets` folders for further editing.

For direct staging, use uppercase folder and source names without `.SCN`:

```dos
SELECT STALINGR CLASH
SELECT CRUSADER CAMPAIGN
SELECT V4V VLFORT
SELECT DDAY BRADLEY
```

These argument forms prepare or check the files and return to DOS. Run
`INVADE` afterward and select the battle in its Scenarios panel.

Converted battles use D-Day's engine with their assigned game profiles. See
[WaW conversion](WAW_CONVERSION.md), [V4V conversion](V4V_CONVERSION.md), and
[installation](../game/waw/README.md) for the relevant settings and adaptations.

## Scenario index

### D-Day (7 native scenarios)

D-Day scenarios use the files in the game's main `SCENARIO` folder and its
base artwork.

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

To make a fresh set from your original game installations, run from the project
folder with the editor's Python dependencies installed:

```sh
python3 scenario_converter.py game --dos -d my-dos-scenarios
```

Choose a new output folder. The command creates a flat collection with unique
filenames, ready to copy into the game's main `SCENARIO` folder and select in
the game. To use SELECT, arrange the files into the subfolders above using the
source filenames in the index. Keep each SCN, REZ and AI under the same basename.
