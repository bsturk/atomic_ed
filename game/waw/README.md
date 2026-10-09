# Playing scenarios in patched D-Day

Use a separate playing copy of D-Day. Create `INVADE-PATCHED.EXE` with the
[patch applicator](patches/README.md#patch-files-and-reversal), then copy it
into the playing folder as **INVADE.EXE**. Keep the editor's original game
files as its templates.

## Play a prepared scenario

The prepared pack includes **43 earlier-game scenarios**: 10 Stalingrad,
6 Operation Crusader and 27 V for Victory. Copy `STALINGR`, `CRUSADER` and
`V4V` from `scenarios/dos/SCENARIO` into the playing copy's **SCENARIO** folder.
Copy [SELECT.BAT](dday/SELECT.BAT) beside `INVADE.EXE`.

Run **SELECT** in DOSBox and choose a game and battle. The menu launches D-Day
with that battle selected; choose **Begin New Game**. **4. D-Day** offers the
seven native scenarios. Exiting the game returns to SELECT; choose **0** to quit.

SELECT gives converted battles distinct filenames, so they coexist with native
D-Day scenarios. It copies each selected SCN and its matching REZ/AI into the
main SCENARIO directory. Keep those files available for saved games. Selecting
a battle again restores its packaged files; use unique names for custom exports.

DOSBox-X provides the required CHOICE command and ANSI color support. On MS-DOS,
use `CHOICE.COM` and load `ANSI.SYS` for the colored menu. See the
[scenario pack guide](../../txt/SCENARIO_PACK.md) for the complete index,
folder layout and command-line staging options.

## Play an edited or new scenario

1. In the editor, choose **File → Export for DOS**. Use a filename of up to
   eight characters, such as `MYBATTLE.SCN`.
2. With the game closed, copy **MYBATTLE.SCN**, **MYBATTLE.REZ** and
   **MYBATTLE.AI** into its **SCENARIO** directory.
3. Run **INVADE**, open **Scenarios**, select the battle, and choose
   **Begin New Game**.

The Scenarios panel discovers up to **256 compatible SCNs** at startup and
lists them alphabetically, five per page. **Previous** and **Next** change
pages. Each exported battle includes a title, map previews and matching artwork.
The selection panel displays up to 26 characters of the title.

Keep the original **DATA/PCWATW.REZ** as the base artwork. A custom startup-screen
export also includes **DATA/PCWATW.REZ**; install that in the playing copy's DATA
folder to use those screens throughout the installation. Restore its original
base file to restore D-Day's startup screens.

## Saved games and companion files

Keep the matching **REZ and AI** in SCENARIO when resuming a save. The game uses
them for artwork, scenario rules and Battle Plans. Changing the REZ changes
the rules used on Resume. After changing Battle Plans, start a new game or
restore the save's matching AI file.

If you rename an export, rename its SCN, REZ and AI together. Existing saves
continue to refer to the original basename. Restart the game after adding or
renaming scenarios.

Keep editing SCNs and their **assets** folders for further work in the editor.
For DOS installation, use the matching exported SCN/REZ/AI sets. Original
Stalingrad, Crusader and V4V files can be imported through the editor or
`scenario_converter.py`; the prepared pack is already converted.

## Sound and music

Place sound-effect WAV files in **DATA/SOUND**. Run **INVADE /SETUP**, select
**Sound Blaster**, and match its port, IRQ and DMA to DOSBox. A typical setup
uses **220h / IRQ 7 / DMA 1**. Enable Sound Effects for the player side.
See the [sound setup guide](../../txt/SOUND_CONFIGURATION_GUIDE.md).

For background music, copy **V4V.OPL** to **DATA/MUSIC/V4V.OPL** and use
**Options → Background Music**. The repeating five-piece playlist is shared
across scenarios, and the game remembers the setting. The
[music guide](../../assets/music/README.md) explains how to create the file.

## Patch management

The [patch guide](patches/README.md) covers applying, rebuilding and reversing
the individual executable patches.
