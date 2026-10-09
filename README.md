# Atomic Editor

A scenario editor for Atomic Games’ **World at War** and **V for Victory**
games. Tweak a favorite battle, create your own, or bring scenarios from the
earlier games into **D-Day — America Invades!**

Use the desktop editor to make your changes, then play them in DOSBox-X with
the patched D-Day game.

![Bradley’s Nightmare in the map editor, with original terrain, unit chits, and terrain painting controls](www/image/editor-map.png)

*Bradley’s Nightmare on the Map page. Terrain, roads, rivers, place names, and
unit counters use the game’s artwork.*

## What the editor can do

- **Make your own battles.** Start with a blank map or edit an existing scenario,
  with undo, redo, and edit history along the way.
- **Shape the battlefield.** Paint terrain, roads, rivers, and other map features.
  Add place names, change ownership, resize maps, and copy whole regions.
- **Build an army.** Add and place units, change their stats and chits, organize
  HQs, schedule reinforcements, and move formations together.
- **Plan the fighting.** Set movement routes, artillery orders, supply levels,
  and transport arrangements. Create AI orders and events triggered by captured
  objectives or losses.
- **Set the conditions.** Edit briefings, objectives, leaders, replacements,
  depots, dates, weather, and starting snow, ice, or mud.
- **Give it your own look.** Use artwork from the supported games or import
  custom terrain, unit chits, portraits, flags, and startup screens.
- **Adjust the rules.** Customize victory thresholds, winter behavior, and
  terrain movement and combat values.

<details>
<summary>More screenshots: units and artwork</summary>

![Units page showing the Allied roster, reinforcement arrivals, a tank’s stats, and its original chit](www/image/editor-units.png)

*Units and reinforcements share one roster, with editable properties and a chit preview.*

![Artwork page comparing a D-Day popup portrait with a portrait from the Stalingrad library](www/image/editor-artwork.png)

*The Artwork page previews library images or custom imports before applying them.*

</details>

## Games and scenarios

The collection includes **50 battles**: seven original D-Day scenarios and
**43 earlier-game scenarios already converted for D-Day**.

| Game / battleset | Scenarios | Examples |
| --- | ---: | --- |
| World at War: D-Day — America Invades! | 7 native | Bradley’s Nightmare, SS Counterattack, Operation Cobra, Omaha Beach |
| World at War: Stalingrad | 10 converted | Operation Uranus, Rattenkrieg, Wintergewitter |
| World at War: Operation Crusader | 6 converted | Operation Crusader, Hell Fire Pass, Fortress Tobruk |
| V for Victory: Utah Beach | 6 converted | Objective Carentan, Race for Carteret, Final Assault |
| V for Victory: Velikiye Luki | 7 converted | Fortress in the Snow, Into the City, Red Storm |
| V for Victory: Market Garden | 7 converted | A Bridge Too Far, Screaming Eagles, Hell’s Highway |
| V for Victory: Gold–Juno–Sword | 7 converted | Off the Beaches, To Caen!, Attack of the 12th SS |

The converted scenarios are ready to play with the patched game, or you can use
them as a starting point for your own battles. Open one in the editor, make your
changes, and use **Export for DOS** when you're ready to play. You can also
import original earlier-game `.SCN` files for editing. See the
[full scenario list](txt/SCENARIO_PACK.md) for every battle.

Converted scenarios run under D-Day's rules, so their behavior and balance can
differ from the original games. The [conversion guides](#more-help) explain the
remaining differences.

## Run the editor

You'll need your own copy of D-Day, **Python 3.10 or newer with Tkinter**, and
**DOSBox-X** to play. The editor itself runs outside DOSBox.

Copy D-Day's `DATA` and `SCENARIO` folders into `game/waw/dday`. Keep a copy of
the original executable at `game/waw/dday/orig/INVADE.EXE` for patching. The
important files should look like this:

```text
game/waw/dday/DATA/PCWATW.REZ
game/waw/dday/SCENARIO/BRADLEY.SCN   (and the other scenarios)
game/waw/dday/orig/INVADE.EXE
```

Then, from the project folder:

```sh
python3 -m venv .venv
# Linux / macOS:
source .venv/bin/activate
# Windows: .venv\Scripts\activate
python -m pip install -r requirements.txt
python scenario_editor.py
```

On Debian/Ubuntu, you may also need to install `python3-tk`.

Choose **Open** to load a scenario or **New** to start from scratch. Save your
work with **Save** or **Save As**. If you move an editable scenario elsewhere,
keep its accompanying `assets` folder with it.

For the earlier games, put their installations in `game/waw/stalingrad`,
`game/waw/operation_crusader`, or `game/v4v`. Keep their original data files
together. The [artwork library guide](txt/SCENARIO_EDITOR_README.md#unit-and-terrain-libraries)
explains how to make their terrain and units available for your own scenarios.

## What the D-Day patches add

The patched game lets you:

- Select custom and converted scenarios from the game's familiar scenario menu.
- Play longer battles, with weather and score history for up to 400 turns.
- Use each scenario's own terrain, unit artwork, flags, and portraits.
- Play with custom AI plans, triggered events, victory settings, and terrain rules.
- Enjoy optional V for Victory background music.

It also includes fixes for weather-related errors during reconnaissance and
air supply. The patches can be applied or reversed individually if needed;
see the [patch guide](game/waw/patches/README.md) for those options.

## Playing your scenario

First, create the patched executable:

```sh
python tools/patch_dday.py game/waw/dday/orig/INVADE.EXE --component all -o game/waw/dday/INVADE-PATCHED.EXE
```

1. Make a separate playing copy of D-Day. Copy `INVADE-PATCHED.EXE` into it
   and rename it **`INVADE.EXE`**, keeping the game's original data files.
2. In the editor, choose **File → Export for DOS** and give your scenario a
   name of up to eight characters.
3. Copy the exported **`.SCN`**, **`.REZ`**, and **`.AI`** files into the playing
   copy's `SCENARIO` folder. Keep all three together, including when resuming saves.
4. Launch the game in DOSBox-X, choose your battle under **Scenarios**, and
   select **Begin New Game**.

For the prepared scenario collection, the colorful
[SELECT.BAT](game/waw/dday/SELECT.BAT) menu can select and launch battles for you.
The [playing guide](game/waw/README.md) explains how to set it up, including
installing custom startup screens.

For audio, follow the [sound setup guide](txt/SOUND_CONFIGURATION_GUIDE.md).
The optional [V4V music setup](assets/music/README.md) adds five background
pieces, controlled by **Options → Background Music** in the game.

## More help

- [Editor guide](txt/SCENARIO_EDITOR_README.md)
- [Complete scenario list](txt/SCENARIO_PACK.md)
- [Stalingrad and Operation Crusader conversion](txt/WAW_CONVERSION.md)
- [V for Victory conversion](txt/V4V_CONVERSION.md)
- [Playing and installing scenarios](game/waw/README.md)
- [Applying or reverting individual patches](game/waw/patches/README.md)
