# Aircraft and naval customization

Use **Units** to add, duplicate or edit ships and squadrons. Their icons appear
in the roster and current OOB panel. Aircraft and naval support operate through
the game's support systems.

## Categories and unit data

Select a support unit and open **Unit Definition** to change its category.

| Unit | Categories |
| --- | --- |
| Aircraft | Fighters/light bombers, medium bombers, transports, reconnaissance |
| Ships | Battleships, heavy cruisers, monitors, light cruisers, destroyers |

Category changes retain names, arrival times, nationality and aircraft counts.
Aircraft receive the selected role's flight, cargo and default mission settings.
Moving a transport or reconnaissance squadron into a combat role creates
bombardment settings from a suitable D-Day template. Review those settings
before applying the definition.

Aircraft have separate full-strength, ready and under-repair counts. Combat
squadron bombardment during play depends on per-aircraft strength and the
number ready. The editor preserves these counts when importing, duplicating
or transferring a squadron.

Each side supports **20 roster entries per category**, including deleted
entries. Category changes require support records that are free of active
mission or leader references; the editor identifies conflicts before applying.

## Availability

Aircraft availability is tracked for five air-superiority levels. Adding a
squadron makes it available at each level. Removing one reduces availability
in that category while preserving its other reservations. The patched game's
extra-air-support option is bounded by the available roster.

## Category artwork

Choose **Category artwork…** or **Import image…** on Units, or select the
corresponding slot on **Artwork**.

- Aircraft artwork is shared by category and side.
- Ship artwork is shared by category across both sides.
- Each image is a **71 × 34 pixel** button, including its text label.

The library includes D-Day, Stalingrad and Crusader aircraft pictures and D-Day
ship silhouettes. Imported images are fitted to the button and converted to
the game palette. Review the preview before applying. **Export Current Image…**
provides a PNG to use as a template in an image editor.

## Saving and playing

Category and artwork changes support Undo/Redo, Save and Save As. Keep the
editing document's `assets` folder with its SCN. **Export for DOS** includes
the artwork in the matching REZ; install the **SCN, REZ and AI** together and
use `INVADE-PATCHED.EXE` as `INVADE.EXE`.

See the [editor guide](SCENARIO_EDITOR_README.md) for adding units and the
[installation guide](../game/waw/README.md) for playing exports.
