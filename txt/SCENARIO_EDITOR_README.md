# D-Day Scenario Editor

Create and edit World at War scenarios, including converted Stalingrad,
Operation Crusader and V for Victory battles. The editor runs on the host
computer; exported scenarios run in patched D-Day.

See the [setup guide](../README.md#run-the-editor) for Python and game files,
and the [scenario index](SCENARIO_PACK.md) for the 43 prepared conversions.

## Open, create and save

**File → Open** accepts D-Day SCNs and original earlier-game scenarios. Opening
an earlier format creates an unsaved D-Day document. **File → Conversion Notes**
shows how it was adapted. Use **Save As** to keep an editable copy.

**File → New Scenario** creates a blank map and empty roster. Choose:

| Setting | Range |
| --- | --- |
| Map dimensions | 4–125 columns and rows |
| Start date | 1939–1945 |
| Duration | 2–400 turns |
| Terrain | Starting base terrain |
| Game profile | Victory and winter defaults |

New scenarios start with clear weather at 65°F. Each side has a supply entry
at its north or south map edge and a 50,000-point stock. Edit these under
Scenario Settings. Add an HQ first for each empty side, then add its units
and place them on Map.

**Save** updates the current document. **Save As** switches to a new copy and
continues editing it. An asterisk beside the filename marks unsaved changes.
Keep the document's **assets** subfolder with its SCN when moving it; that
folder holds custom artwork, game profiles and conversion information.

Unit and settings forms retain drafts as you navigate. Save, Save As and
Export for DOS validate and include pending forms. If a field is invalid, the
editor returns to that form so you can correct it. **Revert Form** discards
its draft. Finish modal dialogs with Apply or Cancel before saving.

New, Open, Reload and Exit offer **Save / Discard / Cancel** when changes are
pending. **Reload** reads the saved document again.

## Editing the map

Maps open centered at the largest zoom that fits beside the editing panel.
Resizing the window adjusts that fit until you zoom, pan or scroll manually.
**Reset View** fits the entire map again. Drag to pan.

The **Show** row controls **Units**, **Terrain**, **Hexes**, **Coords**, **Names**
and **Ownership** overlays. These are viewing preferences. The **Current OOB**
list remains available when unit chits are hidden.

### Terrain and features

**Select** a hex to inspect its terrain, artwork variant, features and units.
Choose a terrain and variant in the panel, then use **Paint on map** or
**Apply to selected hex**. **Pick terrain** samples a hex, and **Set selected
hex to Clear** replaces its base terrain. Base painting preserves roads,
rivers, slopes and hilltops.

**Terrain Reference** shows the complete terrain catalog. Select a variant to
use it on Map, or use **Browse terrain from all games…** to choose source
artwork. Each choice shows the D-Day terrain rules it uses. The editor assigns
an available artwork variant; if all six are in use, it asks which to replace
and shows how many hexes that replacement affects.

Under **Features**, choose Dirt road, Paved road, Railway, Stream, River,
Uphill slope, Downhill slope or Hilltop, then Add or Remove. Click **Edit
features on map** and click near the desired hex edge. A center click uses
the panel's selected compass direction. You can also apply to a selected
hex side with the panel buttons.

Connections update across neighboring hexes. Roads and water/slope features
are separate groups, so a road can cross a river. Uphill rises toward the
neighbor and Downhill falls toward it. Use slopes and hilltops to make ridges.
Hilltops apply to whole hexes, with up to **30 per scenario**.

### Place names, ownership and terrain edges

| Tool | Use |
| --- | --- |
| Place names | Add, rename, move, style or delete labels. Select a hex and use New place name to add one. Supports 50 labels of up to 25 printable DOS characters each. |
| Ownership | Paint Allied/Axis control, apply it to a region, or flood the connected territory. The Ownership overlay shows the result. |
| Cosmetic edges | Add or remove Water, Bocage, Swamp, Clear grass or Beach fringes on hex sides. Variants span one, two or three consecutive sides. |
| Blend edges | Rebuild cosmetic transitions for a hex and its neighbors, a selected region, or the entire map. |

**Blend edges while painting** also updates transitions during painting and
terrain flood fill. It starts off. Blending uses D-Day's fringe artwork;
**Include imported terrain in blending** applies it to imported tiles using
their assigned terrain rules. Preview those transitions when using desert,
winter or custom pictures. Blending replaces manual edges in the chosen area.

Cosmetic edges affect appearance. Base terrain and directional features supply
the movement and combat behavior. Victory objective names and values are
edited separately in Scenario Settings.

### Placing units

Choose a ground unit in **Current OOB**, click **Place selected unit on map**,
then click its destination. **Deploy at start** makes it available immediately;
**Keep arrival turn** retains its reinforcement schedule and moves its entry hex.
A selected future reinforcement shows a dashed entry marker.

**Units at selected hex** selects members of a stack. **Remove from map (keep
in OOB)** makes the unit inactive so you can place it again later. Aircraft and
ships use their support systems and appear with icons in the OOB panel.

For an individual position or arrival change, clear its saved route and
dismount it first on Units. Formation moves and map shifts move linked groups
together.

### Regions, formations and map size

- **Region / fill:** select two corners and copy the region. Paste previews the
  destination; click its upper-left hex to place it. Copies include terrain,
  features, hilltops and edges. Optional checkboxes include ownership,
  units/HQs, objectives and place names. Row staggering is preserved.
- **Copied formations:** copied HQs and members retain their organization,
  staff settings and Battle Plans. Copied units retain stats, chits and arrival
  times and start with Defend orders. Plan goals and objective references are
  adjusted for copied content. Leaders, supply groups, depots and support
  aircraft/ships remain separate scenario records.
- **Flood fill:** fill connected hexes of the same base terrain with the current
  brush, or fill connected territory of the same owner. Terrain fill preserves
  networks and hilltops; the blending option controls its cosmetic edges.
- **Move formation:** choose an HQ and destination to move it and its members
  together. Options include subordinate HQs, Battle Plan goals and garrisons.
  Arrival times stay the same; reinforcement entries, routes and targets move
  with the formation. Move a complete mounted group together.
- **Shift map:** enter column/row shifts and resulting dimensions. Positive
  values move right/down. Terrain and associated scenario locations move
  together, including units, objectives, labels, supply entries, depots,
  garrisons and order goals. Uncovered cells use the selected terrain and owner.
- **Resize map:** add or crop rows/columns at the bottom and right, keeping the
  upper-left origin fixed. Added cells use the selected terrain and owner.
  Move or remove any locations and routes outside the proposed bounds first.

Each operation is one Undo/Redo step. The editor checks borders, stack limits,
ownership and linked records before applying it. Use the edge-blending tools
to adjust transitions around pasted or shifted terrain.

## Units and organization

On **Units**, choose a side, filter by status, or search by name/type. Select a
unit to edit its stats, availability, arrival turn and entry hex. The page also
shows its artwork and saved orders.

**Add Unit…** offers templates from the current OOB and the extracted game
libraries. Choose a template, name the unit and customize its stats and chit.
Imported ground units join the side's first HQ and start inactive; deploy them
on Map. Duplicating a unit retains its HQ assignment.

**Delete Unit** retires a unit from play. Filter by **Deleted** to select and
**Restore Unit**. Retired roster entries retain their identities.

### HQ organization

**HQ Organization…** shows each side's HQ tree. Choose **Assigned HQ** for a
ground unit, or **Parent HQ** and **Level** for a headquarters, then **Apply
Organization**. Levels are regiment/brigade, division, corps and army. A parent
must be a higher level; **Independent / root** makes an HQ independent.

Reparenting keeps the HQ's assigned units together. Staff assistance and
Battle Plans follow the assigned HQ. The tree shows used/available command
points. Each side supports **43 HQs**.

### Definitions and artwork

**Unit Definition…** edits class, descriptor, nationality, movement class,
movement allowance and stacking points. Movement allowance uses game points
with up to three decimal places. Ground classes include infantry, armor,
engineers, anti-tank, artillery and anti-aircraft.

Artillery definitions also set bombardment and defensive-fire strengths,
range, deployment time, ammunition category and Shoot 'n scoot capability.
Review these values when changing a unit into artillery.

Changing **Side** transfers a non-HQ unit into the other OOB with its name,
stats, nationality and chit. Transferred ground units start inactive under the
destination's first HQ; place them on Map and adjust their HQ assignment as
needed. Dismount and clear routes before changing class or mobility.

**Choose chit…** selects a ground/HQ counter. **Import image…** creates a custom
22×23 chit, previews its palette and transparency, and assigns an available
slot. **Export Selected…** supplies a PNG template for external editing.
Appearance is independent of class, nationality and combat stats.

See [aircraft and naval customization](AIRCRAFT_AND_NAVAL.md) for support
categories, squadron counts and their shared button artwork.

### Supply, transport and orders

Under **AI and orders**, **Supply…**, **Transport…** and **Orders…** open controls
for carried stock, HQ distribution, mounted infantry, movement routes and
secondary orders. Staff-assistance checkboxes are shared by the unit's HQ.

The game can replace individual orders through computer control, staff
assistance or Battle Plans. Configure those systems for the intended behavior.
See [unit logistics and orders](UNIT_LOGISTICS_AND_ORDERS.md) for quantities,
mounting rules, artillery targeting and route controls.

## Scenario settings

| Page | Editable data |
| --- | --- |
| Victory | Start date, duration, casualty weights, and objectives with names, locations, side values, owner and control radius |
| Game Profile | Victory ratios, winter model and ground-condition coefficients; Edit Terrain Rules sets movement and combat modifiers |
| Battle Plans | Timed/conditional HQ orders, reinforcement releases and public messages |
| Leaders | Names, combat effects, attached units, home HQ, formation restrictions, nationality, chits and portraits |
| Replacements | Initial pools and daily arrivals for infantry, armor, engineers, anti-tank, artillery, anti-aircraft and airborne troops |
| Garrisons | Center/radius areas and assigned HQs |
| Supply | Stock groups, entry hexes, availability and daily deliveries |
| Depots | Locations, stock, capacity, land resupply/airdrop operation, distribution and initial capture state |
| Weather | Temperature and condition by turn, plus initial snow, ice and wetness |

Date changes retain time of day and shift the calendar, arrivals, rebuild
schedules and authored weather together. Reinforcements and Battle Plans retain
their relative turns. Move late reinforcements earlier before shortening a
scenario past their arrival.

D-Day scores held objectives over time and awards points for enemy losses.
**Game Profile** sets the winning/losing score ratios: defaults are at least
200% for major victory and greater than 125% for minor victory. Objective
values and casualty weights determine the points used in those comparisons.

A unit can have one attached leader. Choose an eligible ground unit and a home
HQ; the formation restriction limits transfers within that HQ's formation.
**Portrait…** opens its individual portrait on Artwork, and **Choose Chit**
sets its counter.

Replacement quantities are points, with pools and daily arrivals from **0–255**.
Plan deliveries so unused stock stays within the 255-point pool limit.

Each side keeps at least one supply group. Supply tracing uses the first
group's entry hexes; additional groups are reserve pools, and each receives
the scheduled delivery. A group supports up to **26 entry hexes**. The off-map
reserve depot allows stock/capacity edits alongside the map depots.

Weather temperatures use **Fahrenheit**. Select turns individually or apply
values across a range. Initial snow, ice and wetness use game accumulation
values; zero means none. The selected winter profile governs later changes.

See [game profiles](GAME_PROFILES.md), [terrain rules](TERRAIN_RULES.md) and
[Battle Plans](NESTED_EVENTS.md) for detailed controls and examples.

## Artwork and libraries

The **Artwork** tab edits popup busts, nationality and toolbar flags, side
emblems, turn pictures, individual leader portraits, aircraft/naval category
pictures and the game/series/publisher startup screens.

Choose a use on the left and a library picture on the right, then **Use Selected
Artwork**. **Import Image…** accepts PNG, BMP, GIF, JPEG and WebP. Imports fit
the target dimensions and convert to D-Day's palette; review the preview before
applying. **Export Current Image…** writes a PNG template. **Restore D-Day
Default** restores that slot's standard artwork.

Flags use transparent margins. Portraits and other opaque pictures blend
transparency onto their background. Popup busts are shared by side/message
context. Individual **37×35** leader portraits appear in the leader sidebar.
Flags occupy the selected nationality slot; unit nationality is set on Units.

Import terrain through **Map → Terrain → Import Image…** or **Terrain Reference**.
Choose its rules and one of six variants. The editor creates large, small,
dim and night versions. Each terrain type shares one night tile across its
variants. **Export Image…** provides a terrain PNG template.

The libraries cover D-Day, Stalingrad, Operation Crusader, and V4V's Utah Beach,
Velikiye Luki, Market Garden and Gold/Juno/Sword. They include unit templates
and source artwork usable across scenarios. To build them from your originals:

```sh
python3 tools/build_terrain_library.py
python3 tools/build_unit_library.py
python3 tools/build_presentation_library.py
```

The generated libraries retain the extracted artwork for later use. Keep the
editing document's assets folder with its SCN; imported pictures are stored
there when saved.

## Briefings

**Mission Briefings** edits each side's text. Each side has eight lines of up
to 127 characters using the game's Mac Roman character set. Blank lines count
toward the eight; visual wrapping follows the display width. Save identifies
unsupported characters or excess text so you can revise them.

## Export and play

**File → Export for DOS** writes the scenario with its terrain, chits,
presentation artwork, rules, orders and generated map previews:

```text
MYBATTLE.SCN
MYBATTLE.REZ
MYBATTLE.AI
```

Choose a DOS filename of up to eight characters. Copy all three files into the
playing copy's **SCENARIO** folder and use **INVADE-PATCHED.EXE** as **INVADE.EXE**.
The game's Scenarios panel lists up to 256 compatible scenarios, five per page,
with Previous/Next controls. Selection titles display up to 26 characters.

Custom startup screens also export **DATA/PCWATW.REZ**. Copy that file to the
playing copy's DATA folder; startup artwork applies to the whole installation.
Keep the editor's original game resources as its export templates.

Retain the matching REZ and AI files when resuming saved games. Keep your editing
SCN and assets folder for further changes. See [installation](../game/waw/README.md)
and the [prepared scenario pack](SCENARIO_PACK.md).

## Undo, redo and history

**Undo** and **Redo** cover applied unit, map, artwork, briefing and settings
changes in one chronological history. **Edit → Edit History…** shows the steps,
the current position and the saved position. Select a row and **Restore Selected**,
or double-click it, to return to that state.

Moving back keeps later steps available for Redo. Making a new edit replaces
those later steps. Briefing typing is grouped into short bursts; form edits
enter history when applied. Save/Export collect pending forms into an undoable
step. Undo handles pending forms too; correct or revert invalid drafts first.

Save and Save As retain history and mark the saved position. Returning to the
saved content clears the modified marker. History belongs to the current
editing session; New, Open, Reload and closing start a fresh session.

## Shortcuts

| Shortcut | Action |
| --- | --- |
| Ctrl+N | New scenario |
| Ctrl+O | Open |
| Ctrl+S | Save |
| Ctrl+Shift+S | Save As |
| Ctrl+Z | Undo |
| Ctrl+Y / Ctrl+Shift+Z | Redo |
| F5 | Reload |

**Tools** also offers scenario validation and unit-list export. Validate and
playtest an edited scenario before sharing it.
