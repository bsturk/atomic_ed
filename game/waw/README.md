# Playing exported scenarios in D-Day

Use your own playing copy of D-Day. First generate `dday/INVADE-PATCHED.EXE`
using the [patch applicator](patches/README.md#patch-files-and-reversal);
game executables and data are excluded from the source repository. Copy that file into it as
`INVADE.EXE`. Keep the staged original `game/waw/dday/orig` files intact; the editor
uses them as templates and base artwork. Keep the original `DATA/PCWATW.REZ`
in your playing copy too, unless installing an exported startup pack below.

Only the original `INVADE.EXE` and the complete `INVADE-PATCHED.EXE` are kept.
Individual forward/undo patches remain under `patches/`.

The October 9 build fixes **“= BAD WEATHER IN RECCE =”** after movement, plus
the corresponding air-supply weather reads. Update the playing `INVADE.EXE`
and restart the game. Existing SCN/REZ/AI files do not need conversion or export
again. The repair is also available separately as `patches/dday-air-weather.*`;
the full patch/rebuild commands include it automatically.

For sound effects, the playing copy needs **`DATA/SOUND/*.WAV`**. The staged
D-Day WAVs are currently in `orig/SOUND`; copy them into your playing copy's
`DATA/SOUND`. Run **`INVADE /SETUP`**, select **Sound Blaster**, and save with
port/IRQ/DMA matching DOSBox (tested: **220h / IRQ 7 / DMA 1**). The staged
`SYSTEM.SET` selects No Sound Card. Restart DOSBox after copying files from the
host. This works with both executables and needs no additional binary patch.
This restores WAV effects in the original game as well as the patched build.
See [sound repair instructions](../../txt/SOUND_CONFIGURATION_GUIDE.md), including
a corrected tool that can configure your playing copy automatically.

For background music, generate `assets/music/V4V.OPL` using the
[music extraction tool](../../assets/music/README.md#rebuilding-the-data), then copy it
to **`DATA/MUSIC/V4V.OPL`** in the playing copy and use the latest patched EXE.
**Options → Background Music** controls a repeating playlist of five V for Victory
AdLib/FM pieces, independently of Sound Effects. It defaults to on and remembers
your choice in `DATA/MUSIC/MUSIC.CFG`. Keep DOSBox's `oplmode=auto` with Sound
Blaster enabled. The same playlist is available in native and converted scenarios;
no extra per-scenario files or MIDI soundfont are needed. See the
[music notes](../../assets/music/README.md) for rebuilding and limitations.

All **43 earlier-game scenarios are already converted** in
`scenarios/dos/SCENARIO`: 10 Stalingrad,
6 Operation Crusader and 27 V for Victory. The pack has `STALINGR`, `CRUSADER`
and `V4V` subfolders matching the renamed editing folders. These are local
generated files, not part of the Git checkout; see the
[scenario index and rebuilding instructions](../../txt/SCENARIO_PACK.md).

The single [SELECT.BAT](dday/SELECT.BAT) lives with the game in `game/waw/dday`.
Copy it beside your playing copy's `INVADE.EXE`, and copy
the pack's three subfolders into its `SCENARIO` directory. Run `SELECT` from
the game directory and choose a game/battle. The interactive menu launches
`INVADE` with that battle already selected; choose **Begin New Game**.
The **Scenarios** panel shows its title and correct page. Exiting returns to the
batch menu. **4. D-Day** lists all seven native scenarios, using their existing
files without staging. For conversions, the batch stages the SCN/REZ/AI trio in
the main `SCENARIO` directory. It uses distinct `ST`/`OC` destination names,
preserving native D-Day scenarios and previously staged battles for saved games.
Selecting the same battle again replaces its staged trio with the packaged copy.
It does not replace `DATA/PCWATW.REZ`.

Automatic selection requires the current `INVADE-PATCHED.EXE` with the
`startup-selection` layer. Replace both the batch file and the playing copy's
`INVADE.EXE` when upgrading. SELECT writes a temporary `WAWSTART.TXT` containing
the selected basename and removes it when the game exits. An invalid request
or missing required companions stops startup rather than loading another battle.
Without this file, launching INVADE directly retains the usual default selection.
Bradley remains the original Bradley scenario; converted battles keep their own
names and save identities.

The launcher has self-contained ANSI color panels and CP437 box drawing, sized
for an 80-column, 25-row DOS screen. The number/letter keys and Back behavior
are unchanged. Colors reset before the game starts and when leaving the menu.
DOSBox-X displays the ANSI artwork directly; real MS-DOS needs ANSI.SYS loaded.
If editing `SELECT.BAT`, preserve its CP437 encoding, literal ESC bytes and CRLF
line endings. No separate artwork files or additional launcher are needed.

The menu uses MS-DOS 6.22 `CHOICE.COM` or DOSBox-X's built-in `CHOICE`.
For direct staging without a menu or game launch, use uppercase arguments, for
example `SELECT STALINGR CLASH`, `SELECT CRUSADER CAMPAIGN`, or
`SELECT V4V VLFORT`. `SELECT DDAY BRADLEY` checks the native scenario is present.
Use the prepared **`scenarios/dos`** files: `scenarios/converted` contains editor
documents and JSON artwork, which a DOS batch file cannot load. No editor export
is needed for an existing prepared pack. See its [layout and index](../../txt/SCENARIO_PACK.md).

For your own scenarios or subsequent edits:

1. Open or create a scenario in the editor and choose **File → Export for DOS**.
   Choose a DOS filename with at most eight characters, such as `MYBATTLE.SCN`.
   Export writes `MYBATTLE.SCN`, `MYBATTLE.REZ`, and `MYBATTLE.AI`.
2. With the game closed, copy **all three files, unchanged**, into its `SCENARIO`
   directory. Different scenarios can coexist there. Keep their basenames unique.
3. Run `INVADE.EXE` and select **Scenarios**. The existing panel lists the files
   alphabetically, five per page, with **Previous** and **Next** controls.
   Select a scenario and then **Begin New Game**.

The game scans up to 256 compatible SCNs at startup. It selects the matching REZ
and AI itself and remembers their filename in saves. Keep those companions in
`SCENARIO` when resuming a save, even if the save lives elsewhere. Native D-Day
SCNs without companions use the original base artwork. Original Stalingrad,
Crusader and V4V files use different formats; use the prepared pack above or
convert/export them with the editor or `scenario_converter.py --dos`.

New exports include display titles, map previews, mini-maps and title banners.
Re-export older exports to get these. The editor's **Artwork** tab also selects
or imports popup portraits, nationality flags, emblems and turn-screen pictures.
Those are included in the REZ; replace an older library executable with the
current `INVADE-PATCHED.EXE` to use them. Names longer than 26 characters are shortened in the selection panel.
Custom terrain, ground-unit chits and individual leader portraits are included
in the same scenario REZ. Individual portraits use the new `custom-artwork`
patch included in the current library executable.

Aircraft/naval category artwork also goes in the scenario REZ. Install the current
library executable with its `support-artwork` layer to load and refresh those
pictures. Aircraft pictures are shared by category and side; ship pictures by
category across both sides. Unit Definition can change these roster categories.

Game profiles use the `game-profiles` and `terrain-rules` layers in the current
library binary. Export includes winter rules, victory ratios, and custom terrain
movement/combat constants in the scenario REZ; no fourth
file is needed. Keep that REZ when resuming saves. Old binaries ignore these
rules, so profile exports require the current library executable.
See [profile coverage](../../txt/GAME_PROFILES.md).

Battle Plans supports nested ALL/ANY conditions, persistent HQ orders, one-time
reinforcement releases and public scenario messages. These use the current library
executable’s `nested-events` patch. The earlier three-condition/persistence controls
remain available. See [event controls and limits](../../txt/NESTED_EVENTS.md). Activation survives Save/Resume: retain the matching
exported AI file for each save. If you change the plans, start a new game or
restore the old AI before resuming the old save. Earlier binaries ignore the
entire advanced rule table; the v4 fallback only supports timed plans and single
conditions without persistence.

If you import a game/series/publisher splash on **Artwork**, DOS export also
writes **DATA/PCWATW.REZ**. Copy that file to your playing copy's **DATA** folder,
separately from the three files in SCENARIO. Startup pictures apply to every
scenario in that installation because they load before scenario selection.
Restoring the original base REZ restores the original startup screens. Never
replace the editor's staged base REZ; it remains the export template.
If you rename an export, rename all three files together; existing saves still
refer to the old basename. Restart the game after adding or renaming scenarios.

No Python, launcher, editor JSON, or extra game trees are needed on the playing PC.
Converted editing documents are under `scenarios/converted/{v4v,stalingr,crusader}`;
retain their `assets` folders for further editing.

## Rebuilding or reverting patches

Individual patch layers remain available. See the
[patch instructions](patches/README.md#patch-files-and-reversal)
for rebuilding the latest executable or reverting individual layers.
