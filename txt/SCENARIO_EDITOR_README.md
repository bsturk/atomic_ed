# D-Day Scenario Creator/Editor

Game installations, generated scenario packs and extracted artwork are local
data, excluded from Git. See the [repository setup guide](../README.md#run-the-editor)
and [scenario pack index](SCENARIO_PACK.md) to prepare them.

A graphical editor for World at War: D-Day scenario files using Python and tkinter.
D-Day's patched `INVADE.EXE` is the target runtime, including for scenarios
imported from Operation Crusader, Stalingrad and V for Victory.

**Scenario Settings → Game Profile** selects source-game defaults and overrides
for victory ratios and winter rules. New imports preserve their original records
alongside the editable D-Day projection. Save/Save As and undo/redo retain both.
DOS export includes the required rule table in REZ; use the current library
executable. See [game profiles and remaining adaptations](GAME_PROFILES.md).

> Current editor: unit properties and arrivals are combined in **Units**.
> Choose a side, filter by status, or search by unit name/type. Select a unit to
> view its original artwork and edit its stats, availability, arrival turn, and
> entry hex. AI and orders shows the saved tactical order and provides ground and
> artillery staff-assistance checkboxes shared by the unit's HQ. Computer control
> can override these settings. Apply Changes queues edits; File → Save writes them.
> Add Unit and Delete Unit are on this page.
> HQ Organization edits assignments and the command hierarchy. Unit Definition
> edits class, descriptor, nationality, movement, stacking and artillery data.
> Add offers searchable templates from the current OOB and all staged WaW/V4V games,
> including artwork and class data. Imported ground units begin inactive;
> deploy them on Map. Add an HQ first when starting an empty side.
> Delete removes a unit from play; Show: Deleted offers Restore Unit. Unit numbers
> are retained because game scripts refer to them. Undo and Redo cover each applied
> unit edit as well as map, artwork, briefings and settings. Save commits all changes.
> See the [unit logistics and orders guide](UNIT_LOGISTICS_AND_ORDERS.md).
> Mission Briefings reads all eight fixed text slots for each side, including
> short lines and internal blank lines. Save and Save As write briefing edits.

**Save** and **Save As…** are both on the toolbar and in the File menu. Save
updates the current file atomically without creating `.bak` files. Save As lets you choose a new
name/location and continues editing that copy, preserving the source file.
An asterisk beside the scenario filename in the toolbar and window title marks
unsaved changes. It clears after saving or undoing back to the saved state.

Typing in a unit or settings form also marks the document modified, before
**Apply**. Drafts stay with their unit, side or selected range when navigating,
filtering the roster or editing the map. This covers unit properties/chits,
duration/date/scoring, weather, ground conditions, daily supply and replacements.
**Save**, **Save As** and **Export for DOS** validate and include these drafts
automatically. An invalid draft selects its form and prevents the write; other
drafts remain intact. **Revert Form** discards only the displayed form's draft.
Modal editors retain their own Apply/Cancel buttons; finish that dialog before
using a document command.

Closing the window, **File → Exit**, **New**, **Open** and **Reload** offer
**Save / Discard / Cancel** when there are unsaved changes, including form drafts.
Save must succeed before the requested action proceeds. Canceling Save As,
invalid input and write failures leave the document open. Choosing Discard does
not clear the current document until its replacement actually loads or is created.

**Open** also accepts original Stalingrad, Crusader and V4V SCNs and converts
them to unsaved D-Day documents. Save As keeps the source intact. **File →
Conversion Notes** lists the adaptations and survives Save/Save As. The 16
earlier-WaW conversions are in `scenarios/converted/stalingr` and
`scenarios/converted/crusader`; see [WaW conversion notes](WAW_CONVERSION.md).

The staged **V for Victory** scenarios can also be converted with
`python3 scenario_converter.py game/v4v -d scenarios/converted/v4v`. Open the resulting
SCNs in this editor; their terrain and unit-artwork companions survive Save and
Save As. See [conversion notes](V4V_CONVERSION.md) for experimental limitations.

## Exporting for manual play

All **43 staged Stalingrad, Crusader and V4V scenarios** are already exported in
`scenarios/dos/SCENARIO`, with current profiles and
matching artwork. Copy its `STALINGR`, `CRUSADER` and `V4V` subfolders into the
patched game's `SCENARIO` folder, and
[SELECT.BAT](../game/waw/dday/SELECT.BAT) from `game/waw/dday` into the game directory.
Run `SELECT` to stage a battle; see the [pack index](SCENARIO_PACK.md).
Native D-Day scenarios already work. No editor step is needed for this pack.

Use **File → Export for DOS** to write the current edits as a matching
`NAME.SCN`, `NAME.REZ`, and `NAME.AI` set. Export includes terrain, unit and presentation artwork,
leaves the editing document unchanged, and creates no engine, launcher,
JSON companions or backups in the export folder.

Install `game/waw/dday/INVADE-PATCHED.EXE` as `INVADE.EXE` in your playing
copy of D-Day, retaining its original `DATA/PCWATW.REZ`. Copy all three exported
files unchanged into `SCENARIO`. The existing scenario panel discovers compatible
SCNs at startup, with five entries per page and Previous/Next controls. It loads
the selected scenario's graphics/orders and remembers that filename in saves.
Exports use DOS 8.3 filenames and include titles, preview maps and banners.
Custom startup screens additionally export `DATA/PCWATW.REZ`; install that in
the playing copy's DATA folder instead of its original base REZ. Startup artwork
is global; the scenario's terrain, chits and portraits remain in its own REZ.

Only the original and latest patched executables are retained. See the short
[installation instructions](../game/waw/README.md).
The editor neither launches DOSBox nor creates a `play` directory.

## Artwork: portraits, flags and splash screens

The **Artwork** tab edits four popup busts, five nationality flags (both native
sizes), two toolbar flags, Allied/Axis emblems, turn pictures, individual leader
portraits and three startup splash screens. Select a use on
the left, choose a library image on the right, then click **Use Selected Artwork**.
The library includes the staged D-Day, Stalingrad and Operation Crusader images,
extracted under `assets/presentation`; the earlier games need not remain installed.

**Import Image…** accepts PNG, BMP, GIF, JPEG and WebP. Images are fitted without
cropping, using nearest-neighbor scaling and D-Day's palette. Flags use transparent
margins; flag alpha below 128 becomes transparent. Other pictures are opaque in
the engine, so imports blend alpha onto the native picture's background color.
The preview shows the converted artwork
before you apply it; flags include separately generated large/small images.
**Export Current Image…** writes a PNG for editing elsewhere, and **Restore
D-Day Default** removes the selected override. These changes support undo/redo.

Popup busts are shared by side/message context, not assigned to individual named
leaders. Individual portraits appear as named rows on Artwork; **Scenario Settings
→ Leaders → Portrait…** selects the appropriate row. These 37×35 images replace
the nationality flag in the leader sidebar, below its combat ratings. The chit,
name and buttons remain visible. Leaders without portraits retain their flag.
Removing a leader moves the remaining portrait assignments with their records;
undo/redo restores both. Leader chits remain in **Leaders → Choose Chit**.
Flags replace pictures for existing nationality slots; they do not change unit
nationality or engine rules. For example, use the British flag for the American
slot in a converted Crusader scenario whose Commonwealth units map to that slot.
The toolbar flags have separate controls from map nationality flags. Other menu
decorations remain native.

Save/Save As embeds these pictures in `assets/NAME.SCN.presentation.json` beside
the other editing assets. Keep that folder with the SCN. **Export for DOS** embeds
the pictures in the existing REZ companion. For startup splash overrides it also
writes **DATA/PCWATW.REZ** in the export folder. Copy that file to your playing
copy's DATA folder. Startup screens are global: the game loads them before a
scenario is selected. The game, series and publisher splashes are editable;
the animated Atomic logo and About animation remain native. Restoring defaults
and exporting to the same folder resets an existing startup pack to D-Day's art.
Use the updated `INVADE-PATCHED.EXE`, which includes the separately reversible
`presentation` patch. It selects portraits and reloads cached flags when switching
scenarios or resuming saves. Individual portraits require the additional,
separately reversible **custom-artwork** patch included in the current library
binary. The v4 fallback uses other authored pictures when the full exported REZ
is installed as `DATA/PCWATW.REZ`, but does not display individual portraits.

### Custom terrain and unit chits

Use **Map → Terrain → Import Image…** or **Terrain Reference → Import Image…**
to import a bitmap, preview it, and choose its D-Day terrain rules and one of
six artwork variants. The dialog reports how many existing hexes a replacement
will affect. It prepares 32×36 and 16×19 sprites with solid native hex masks,
plus dim and night versions. Night art is shared by all variants of the same
terrain rule in the engine; the lowest assigned variant supplies it. Terrain
imports change the pictures, while the selected native movement/combat rules
still apply. **Export Image…** exports the selected terrain as a PNG template.

On **Units**, **Import image…** below the chit preview imports a 22×23 ground/HQ
chit. The preview uses the exact DOS palette and transparency. **Use Chit**
allocates an unused slot and assigns it to this unit; it preserves all other
unit and leader chits. Identical art reuses its existing slot. A full bank reports
an error instead of overwriting used graphics. **Choose chit… → Export Selected…**
writes a PNG template. Aircraft and ships use shared support artwork and retain
their existing icon controls; they do not use this ground-chit import.

Both imports accept PNG/BMP/GIF/JPEG/WebP, fit without cropping and support
undo/redo, Save, Save As and DOS export. Images are embedded in the document's
existing terrain/counter asset files; the source image is not needed afterward.

## Creating scenarios, victory and unit icons

**File → New Scenario** (Ctrl+N), also on the toolbar, creates a blank map with
an empty roster, briefings and objective list. Choose dimensions (4–125 columns
and rows), starting terrain, start date (1939–1945), and duration (2–400 turns).
Use patch version 4 for 400-turn weather and victory history.
Save opens Save As for the first save; cancel keeps the unsaved document open.
The initial weather is clear, with 65°F temperatures. Each side has a supply
entry at the middle of its north/south edge and a 50,000-point stock.
Weather and supply are editable on Scenario Settings. Imported ground units join
the first HQ on their side; duplicating an existing unit preserves its HQ assignment.
Imported chits receive an unused destination slot automatically; native and
foreign units can coexist without replacing artwork used by another unit.

New documents use D-Day's **Cobra** engine profile: Allied attack / Axis defend,
without Bradley's coordinate-specific special objectives. With the library
executable, export under your chosen DOS filename; the game uses the exported
title and generated map previews. The internal Cobra ID still selects native
engine behavior. Only the v4 fallback requires installing new scenarios as
`SCENARIO/COBRA.SCN` and selecting **Operation Cobra**.

**Scenario Settings** now edits the actual duration, casualty scoring weights,
and objective records. The old guessed turn count, difficulty/weather controls
and free-text victory box were placeholders and have been removed. Objective
Add/Edit/Remove changes the name, hex, Allied/Axis values, initial owner and
control radius. Adding an objective defaults to the hex selected on Map.
Existing accumulated scores and unrelated record bytes remain intact.

D-Day scores held objectives over time and awards points for enemy losses.
The victory tiers use executable constants: winning/losing score ratio at least
2.0, above 1.25, otherwise draw. These are not editable SCN thresholds. The
objective values are inputs to time-weighted scoring, not one-time capture
awards. Duration changes also update calendar, daily supply, replacements and weather bounds;
move late reinforcements earlier before shortening past their scheduled arrival.

### Leaders, logistics and the calendar

On **Scenario Settings**:

- **Victory** edits an existing scenario's start date as well as its duration.
  Date changes retain the time of day and shift the calendar, unit arrivals,
  rebuild dates and authored weather together. Reinforcements and battle plans
  retain their relative turns; daily supply and replacements retain their days.
- **Leaders** adds, edits and removes leaders for either side. Set a name,
  attack/defense odds shifts, attached ground unit, home HQ, formation restriction,
  nationality and chit. A unit can have one leader; artillery cannot carry one.
  Leaders can be attached to future reinforcements. The formation restriction
  limits transfers to the home HQ and its subordinate formations.
- **Replacements** edits starting pools and daily arrivals, including ranges
  of days, for infantry, armor, engineers, anti-tank, artillery, anti-aircraft
  and airborne troops. Quantities are replacement points (0–255), not unit
  counts. The engine stores pools in bytes; avoid scheduling arrivals that
  would overflow an unused pool beyond 255. Reserved categories are preserved.
- **Garrisons** adds, edits and removes center/radius areas and assigns HQs
  from either OOB. Assigned formations use these limits for garrison behavior.
- **Supply** adds/removes stock groups as well as editing stocks, entry hexes
  and daily deliveries. Each side keeps at least one group. D-Day traces supply
  to the first group's entry hexes; extra groups are reserve pools, and each
  receives the same scheduled delivery. Removing the first group promotes the next.
- **Depots** adds/removes map depots and edits location, stock, capacity,
  land resupply versus airdrop operation, distribution to nearby HQs, and initial
  captured state. The off-map reserve entry remains and permits stock/capacity
  edits. Capture state is subsequently updated by the game's territorial control.
- **Weather** also edits initial snow, ice and wetness independently of the
  weather sequence. These are the engine's integer accumulation values, not
  inches or percentages; zero means none. The selected game profile's winter
  model applies after play begins.

Apply updates the document in memory. All these changes support **Undo Last
Edit**, **Save**, **Save As** and **Export for DOS**. Removing records repairs
their roster references. Editing leaders/garrisons disables the corresponding
Rommel/Cherbourg scenario variant that would overwrite their authored assignments.
These use native record layouts; changing dates uses the existing extended-weather
patch, and no new executable patch is needed.

Older editor/converter builds wrote only two days of replacements in new or
converted scenarios. Saving/exporting now extends a short table with zero arrivals
for missing days. Newly created and converted scenarios get complete daily tables.

On **Units**, **Choose chit…** selects a ground counter from its side's artwork
sheet. **Apply Changes**, then **Save**, persists the choice. This changes
appearance independently of class and combat stats. Aircraft and naval support
icons follow their class and cannot be changed through the ground-chit picker.

**AI and orders** edits ground/artillery staff assistance shared by an HQ.
Computer control can override those flags. The computer also reasons about
the victory objectives and uses scenario-specific executable routines.
**Scenario Settings → Battle Plans** adds timed or conditional orders for an HQ’s
assigned units: advance toward a hex, retreat, surround, idle, or stay. Each plan
has inclusive first/last turns, a goal hex, conditions and priority (0–255).
The highest-priority matching plan wins; overlapping plans for the same HQ must
have different priorities. Without a matching plan the native AI remains in charge.

Choose **Always** for timed orders, **Objective controlled by side** for capture/
recapture behavior, or **Side losses reach casualty points** for a loss threshold.
The condition side may be either side, independently of the HQ receiving orders.
Losses mean cumulative casualty points awarded to the opponent, not objective
points, a percentage or destroyed-unit count; the casualty weights on Victory
affect them. A threshold can be 1–65535 points.

For example, give an HQ an Advance plan at priority 0, Retreat while the enemy
controls a selected objective at priority 10, and Stay after its own side loses
100 casualty points at priority 20. Conditions are rechecked when the game asks
for orders, rather than immediately when a hex changes hands. By default,
objective recapture can deactivate an order.

The **Conditions** controls add up to two more checks
(three total). Choose **ALL** to require every condition, or **ANY** to accept
at least one. Each check can use either side's objective control or casualty
points. For example, retreat only after the enemy holds the bridge **and** your
side has lost 100 casualty points.

**Keep active after first matching order** keeps a plan eligible once it actually
supplies an order, even if its conditions later become false. It applies to all
assigned members of the HQ and ends at the plan's last turn. Higher priorities
still win; a plan that has always been preempted has not activated yet. This is
a persistent order, not an action that runs on only the first unit.

Activation state is stored in saves. Keep the same exported `.AI` when resuming;
a save made with these advanced rules rejects a changed rule table. Restore its
matching AI file or start a new game after editing the plans. Older saves without
activation state begin unlatched; past captures cannot be reconstructed.
An objective referenced by any condition cannot be deleted until its plan is
changed or removed. Deleting another objective keeps remaining references correct.

**Edit Nested Conditions…** opens a tree of ALL/ANY groups, with up to 16
objective/loss checks and four nested groups. For example, `(bridge held OR
crossroads held) AND losses ≥ 100`. **Action** also offers **Release HQ
reinforcements** and **Show public scenario message**. These fire once per phase;
releases can hold the selected HQ’s pending ground reinforcements until triggered.
The **Action details** tab configures hold behavior, message text, or the HQ order.
Nested conditions and new actions require the **nested-events** patch in the current
**INVADE-PATCHED.EXE**. See [event controls, timing and limits](NESTED_EVENTS.md).

Combined conditions and persistence require **INVADE-PATCHED.EXE**,
including the separately reversible **advanced-orders** patch. Export for DOS
and install the matching SCN/REZ/AI together. Earlier engines safely ignore the
entire advanced rule table, including its simple fallback orders. The unchanged
v4 executable still supports timed orders and single, nonpersistent conditions.
Plans are saved inside the SCN and participate in Undo/Redo, Save, Save As and
DOS export. Native scenario routines continue to run; authored plans override
the returned order for the selected HQ.
The game still handles pathfinding, tactical decisions and combat. Individual
saved movement paths and support missions are editable on Units.

**Weather** lists every scenario turn with temperature in Fahrenheit and weather
condition. Select one or several turns, or enter a range, then Apply. This selects
authored weather and writes explicit dates in the existing 400-turn format.

**Supply** edits each existing stock group’s initial quantity and up to 26 entry
hexes, including availability. The daily table lets you change quantities for
both sides across a day range. Supply days follow the Calendar’s supply origin.

## HQ organization and unit definitions

On **Units**, choose **HQ Organization…** to view either side as a tree of HQs
and assigned units. Select a ground unit, choose **Assigned HQ**, then **Apply
Organization**. This sets both its current and home HQ for the scenario. Staff
assistance and authored Battle Plans follow the new assigned HQ.

Select an HQ to change its **Parent HQ** and **Level** (regiment/brigade,
division, corps or army). **Independent / root** gives it no parent. The parent
must be a higher command level; circular chains are rejected. Reparenting an HQ
keeps its assigned units together. The tree displays used/available command
points using D-Day's rules; authoring can exceed the command limit, as some
shipped formations do. Add new headquarters with **Add Unit…**, using an HQ
template. Deleted HQs retain their administrative nodes and can be restored.

**Unit Definition…** edits the selected unit's class, descriptor, nationality,
movement class, base movement allowance, and stacking points. Movement allowance
uses displayed game points (for example, 10), with up to three decimal places.
Nationality and side are independent; changing nationality does not choose a
different chit. Existing combat strengths remain editable in the main form.

Ground classes can change between infantry, armor, engineer, anti-tank,
artillery and anti-aircraft. Class/mobility changes allocate independent linked
records when needed, preserving other units' IDs and data. Artillery adds base
bombardment and defensive-fire strengths, range, preparation turns and ammunition
category. Categories 0–3 select D-Day's supply-consumption table. A newly converted
artillery unit starts with minimal gun values; configure them before playing.

Changing **Side** transfers a non-HQ unit into the other OOB while preserving
its name, stats, nationality and exact chit pixels. The original roster slot
is retired, keeping other ground IDs stable. Transferred ground units start
inactive under the destination's first HQ: place them on **Map** and use
**HQ Organization** to choose another HQ. The original leader and any mounted
passengers do not transfer with it. Moving an entire HQ formation across sides
is not implemented; add a destination HQ and transfer its units individually.

HQ, aircraft and naval roles cannot be converted into other classes in place.
Aircraft and naval categories can change in **Unit Definition**. The editor
regroups support records, rebuilds their category lists and adjusts aircraft
availability without changing ground-unit IDs. Fighters/light bombers share a
category; medium bombers, transports and reconnaissance have separate groups.
Ships offer battleship, heavy cruiser, monitor, light cruiser and destroyer.
HQ/support stacking and support movement profiles remain engine/template-driven.
Class or mobility changes with saved routes or mounted transport links are
rejected until the route is cleared or the unit is dismounted. Mounted stacking
sizes are protected too. Depot configuration is on Scenario Settings → Depots.

Both dialogs apply changes in memory and support **Undo Last Edit**, **Save**,
**Save As** and **Export for DOS**. Opening a dialog applies any valid pending
main-form edits first. These are native scenario-data edits; they need no new
executable patch. The existing battle-plan patch continues to use assigned HQ IDs.

### Aircraft and naval customization

On **Units**, select a ship or squadron and choose **Unit Definition** to change
its category. Names, arrival times, aircraft counts and existing bombardment
ratings are retained. Aircraft receive the new role's native flight/cargo and
mission profile; converting a transport/recon unit to a combat aircraft creates
independent bombardment data using a D-Day template scaled to its ready aircraft.
You can edit those bombardment settings before applying the definition.
Imports, duplication and side transfers now preserve aircraft strength and
repair counts, which share record offsets with ground-unit HQ fields.

The game has room for **20 roster entries per category per side**, including
retired slots. The editor blocks additions/category changes that exceed that
limit, and regrouping while support missions are active. Ground/HQ IDs stay fixed.
New squadrons are available at all five air-superiority levels; removing one
from a category reduces its available count first and preserves other reserves.

Choose **Category artwork…** or **Import image…** on Units, or select a support
slot directly on **Artwork**. Aircraft pictures are shared by category and side;
naval pictures are shared by category across both sides. These are **71 × 34**
buttons including their text labels, not individual unit chits. The library has
D-Day, Stalingrad and Crusader aircraft pictures and D-Day's ship silhouettes.
Imported images are fitted and converted to the game palette with an export
preview. **Export Current Image…** provides a starting image for external editing.

Artwork changes participate in Undo/Redo, Save, Save As and DOS export. Install
the current **INVADE-PATCHED.EXE** for scenario-specific support artwork: its
separate reversible `support-artwork` layer loads PICT 131 from the scenario REZ,
refreshes it on scenario changes/resume, fixes the initial picture when earlier
categories are empty, and caps the optional extra-air-support bonus at the actual
roster size. The original executable and v4 fallback remain unchanged.
See [format and validation notes](AIRCRAFT_AND_NAVAL.md).

### Supply, transport and plotted orders

Select a ground unit and use **Supply…**, **Transport…** or **Orders…** under
**AI and orders**. These open the same dialog at the requested page. Apply on
each page commits one undoable edit; **File → Save**, **Save As** and
**Export for DOS** retain the changes. No additional executable patch is needed.

- **Supply:** edit unit carried supply, the initial supply level, and an HQ's
  reserve and distribution limit to subordinate HQs, in tons with two decimal
  places. Applying an HQ level to its direct eligible units excludes units
  not yet in play, fixed units and units without a supply connection. It does
  not recursively change subordinate HQs. Demand, received/transferred supply,
  consumption and connection/source caches are displayed as calculated values.
  The engine can lower a supply level when stocks are insufficient; choosing
  Attack does not create ammunition or fuel. Motorized/unmotorized HQ movement
  remains under **Unit Definition → Movement class**.
- **Transport:** mount foot infantry or engineers on same-side armor in the
  same playable hex, change their carrier, dismount one passenger, or dismount
  all passengers from a selected carrier. Both ends of the relationship, group
  colors, size totals and passenger orders are updated together. The game's
  mounting policy is one larger unit or two size-1 units; total size cannot
  exceed three, and each passenger must fit its carrier's size. Explicitly
  dismount passengers before replacing a full load. Reinforcements must be
  deployed before mounting. Armor at OB index zero cannot carry a passenger
  because zero means “not riding” in the native passenger record.
- **Orders:** inspect the current order, target, automatic goal and plotted
  route. Click neighboring hexes to draw a route on the preview; Back One Step
  removes the last step, and Clear → Defend removes the route and automatic goal
  when applied. Choose tactical/strategic movement, probe/assault orders or a
  defensive stance. The **Secondary** list also offers **Replace**, **Dig in**
  and **Fortify** for eligible ground units, and artillery **Prepare**, **Target**,
  **On call**, **Counter battery** and **Shoot 'n scoot**. Choose Target or Shoot
  'n scoot and click a hex (or enter X/Y); **Clear Target** leaves the guns ready
  without a plotted mission. On call and Counter battery select targets in play.
  Artillery preparation remaining is editable; firing requires zero remaining
  turns. Shoot 'n scoot capability is set in **Unit Definition**. Secondary
  orders need a defensive stance; choose **None** before plotting movement.
  An unchanged order preserves its native fields exactly. **Clear → Defend**
  explicitly removes the route, secondary order, target and automatic goal.
  Copying/deleting units also clears their old mission assignments. Existing movement buffers
  bound the number of steps; the editor does not truncate routes. Game movement
  costs, obstacles and enemy action still apply. Passengers take their carrier's
  route. Staff assistance, computer control and Battle Plans can replace orders
  during play; turn those off for a formation that should follow authored paths.
  Digging/fortifying and replacement delivery happen in the game, subject to its
  terrain, enemy, stock and supply checks. These controls author ground-unit and
  artillery orders; aircraft/naval mission allocation is still handled in play.

Single-unit position/arrival edits require clearing its route and dismounting
first. Formation moves and map shifts preserve routes and move complete mounted
groups together. Units linked to active battles cannot have their orders replaced
here. This remains a scenario editor, not a general saved-battle editor.

The native loader accepts at most **43 HQs per side**. Earlier editor versions
incorrectly allowed 128. Details and executable references are in
[HQ logistics, transport and orders](UNIT_LOGISTICS_AND_ORDERS.md).

## Unit and terrain libraries

`assets/units/library.zip` contains 15,401 extracted templates from all 50 staged
scenarios: D-Day, Stalingrad, Operation Crusader, and the four V4V battle sets.
Use **Units → Add Unit → Templates from**, then search name, type or source
scenario. The dialog previews the selected ground chit. You can make custom
units by choosing an existing type/template, naming it, and editing its stats
and chit. Each imported unit receives fresh roster links and class storage.

Earlier WaW templates preserve source names, classes/descriptors, combat
ratings, quality, mobility, artillery definitions and chits. HQ data and
nationality codes are translated for D-Day; its engine rules still apply.
V4V templates use the documented converter. Cross-game artwork uses
unused chit slots, and a full sheet produces an error without replacing used art.

Terrain Reference and the map’s artwork library include Crusader, Stalingrad
summer/winter, Utah Beach, Velikiye Luki, Market Garden and Gold–Juno–Sword.
The V4V catalog extracts every available base terrain in each battle set,
including types absent from an individual scenario; small/night art is derived.
Imported art uses one of D-Day’s fourteen terrain slots and six artwork variants.
Game Profile → Edit Terrain Rules customizes the slot’s movement/combat constants.

Rebuild editor data from the staged originals with:

```sh
python3 tools/build_unit_library.py
python3 tools/build_terrain_library.py
```

The extracted libraries stay usable without the earlier games installed. D-Day
remains the authoring/runtime base. `crusader_parser.py` was removed: nothing
imported it, and its fixed-offset assumptions were incorrect. The bounded
length-prefixed earlier-WaW document reader is in `lib/waw_reader.py`; the full
translator in `lib/waw_converter.py` also supplies the unit-library builder.

## Editing the map

The **Show** row independently toggles **Units**, **Terrain** (including roads,
rivers and other terrain artwork), and **Hexes** (grid lines). All three start
enabled. **Coords**, **Names**, and **Ownership** remain separate overlays.
These controls only affect the editor view; they preserve map data, zoom, scroll
position and edit history. Hidden units remain available in the Current OOB list,
and selecting a hex with Units off keeps the terrain inspector active.

In **Map**, use the panel beside the map:

- **Current OOB**: select an existing unit (with side/search filters), click
  **Place selected unit on map**, then click the destination hex. Repeating this
  moves that same unit; it never duplicates the OOB record. **Deploy at start**
  makes the unit available at the start of play; **Keep arrival turn** changes
  its entry hex while retaining its schedule. A selected reinforcement's entry
  hex has a dashed outline; its counter remains hidden until arrival.
- **Select**: clicking a hex updates the terrain name, variant and artwork
  preview on the right, including imported artwork. It remains in Select mode;
  choose **Paint on map** to paint with that terrain. **Units at selected hex** selects any
  member of a stack. **Remove from map (keep in OOB)** makes that unit inactive
  and clears its coordinates; it can be placed again later. Aircraft and naval
  support remain off map, with their artwork visible in the OOB panel.
- **Terrain**: choose a terrain name and artwork variant 0–5, then use **Paint**
  and click hexes, or **Apply to selected hex**. **Pick terrain** samples the
  selected hex. **Set selected hex to Clear** replaces its base terrain with
  Clear terrain. Existing roads, rivers, slopes and hilltops are preserved.
  **Blend edges while painting** also rebuilds cosmetic transitions on painted
  hexes and their immediate neighbors, including region painting and flood fill.
  It starts unchecked; when off, the brush preserves existing edge artwork.
  Turning it on does not change the map until you paint. Each paint/fill and its
  edge updates form one Undo/Redo step.
- **Features**: choose **Dirt road**, **Paved road**, **Railway**, **Stream**,
  **River**, **Uphill slope**, **Downhill slope**, or **Hilltop**, then choose
  **Add** or **Remove**. Click **Edit features on map**, then click near the
  desired edge of a hex. A center click uses the compass direction selected in
  the panel. The active side is highlighted in cyan. You can also stay in Select
  mode, select a hex, choose a compass direction, and use **Add/Remove on selected
  side**. The panel previews the selected hex and lists its current features.
  Roads, railways, rivers, and streams update the matching side of the neighboring
  hex automatically, including across staggered rows. **Uphill** rises toward
  that neighbor; **Downhill** falls toward it. Slopes are stored only on the low
  side. Remove erases either slope orientation. Adding a road replaces the
  road/rail type on that connection; adding water or a slope replaces the
  stream/river/slope on that edge. These two groups are independent, so a road
  can cross a river. Removing one type leaves other types alone.
- **Hilltop** uses the whole hex, without a compass direction. It adds/removes
  a hilltop marker; slopes are edited separately. D-Day supports up to 30 hilltops
  per scenario. Its ridge-like terrain uses slopes and hilltops, rather than a
  Mountain base terrain. Cosmetic terrain edge artwork remains preserved.
- **Tools → Place names**: select an existing name from the list to rename,
  move, restyle or delete it. For a new name, select a hex, click **New place
  name**, enter the text and click **Add place name**. **Use selected hex**
  moves the form's coordinates to the selected hex. Names support 25 printable
  DOS characters, with up to 50 names per scenario. The **Names** checkbox
  controls their visibility. These are map labels; victory objective names
  and scores are edited separately on Scenario Settings.
- **Tools → Ownership**: choose Allied or Axis, then paint individual hexes,
  apply to the selection, or flood fill the connected territory of the same
  owner. **Ownership** shows a blue/red overlay. Existing ZOC/stacking flags
  are preserved; objective control follows ownership. A change that conflicts
  with a deployed opposing unit is rejected as a whole.
- **Tools → Cosmetic edges**: **Blend selected hex and neighbors**, **Blend
  selected region and neighbors**, or **Blend entire map** rebuild transitions
  from adjacent terrain. Select a region with **Tools → Region / fill** first.
  Blending replaces manual edge artwork in that area and removes stale edges.
  It uses the original D-Day sprites, so imported/custom tiles and their neighbors
  keep their existing edges unless **Include imported terrain in blending** is
  checked. That option also applies while painting. Inclusion uses the tiles'
  D-Day terrain rules, not their pixels; the native fringes may not match custom,
  desert or winter artwork. Unknown terrain codes and their neighbors are preserved.
  Blending is an editor heuristic, not a reconstruction of every original map's
  hand-authored transitions. It favors water over swamp, bocage, grass, then sand;
  adjacent ground fringes soften forest/built-up edges where a dedicated fringe
  does not exist. It does not create new terrain artwork or change terrain rules.
  Region paste, resize and shift retain their existing edge-copy behavior; use
  these blend buttons afterward to adjust their boundaries.
  For manual control, choose Water, Bocage, Swamp, Clear grass or Beach,
  an edge span variant (0–2), and Add/Remove. Click **Edit cosmetic edges on map**,
  then click near a hex side. Alternatively, set a direction and apply to the
  selected hex. The preview shows the proposed result; **Pick selected side
  artwork** samples an existing sprite anchored there. Variants 0, 1 and 2 span
  one, two and three consecutive sides, ending at the chosen direction clockwise
  (W, NW, NE, E, SE, SW). These overlays draw inside the selected hex and do not
  change movement costs or add river/slope connections. Undo/Redo and normal
  Save/Save As/DOS export include both manual and automatic edge edits.
- **Tools → Region / fill**: click **Select region (two corners)**, select
  opposite corners, then **Copy selected region**. **Paste on map** previews
  the destination footprint under the pointer; click to place its upper-left
  hex. Row staggering is preserved, so alternate rows may shift a column when
  moving between odd and even rows. A paste crossing the map border is rejected
  in full. Copies include terrain variants, networks, hilltops and cosmetic
  edges. Check the additional paste options for **ownership**, **units/HQs**,
  **objectives**, and **place names**. The clipboard records the source at Copy
  time; later source edits do not change the stamp. Existing destination units,
  objectives and names remain. Roads/rivers and one-sided slopes connect at the
  paste boundary. Region painting uses the current Terrain brush or the owner
  chosen on Ownership.
  Copied units get new stable IDs, retain stats/chits/arrival times, and start
  with fresh Defend orders, no leader and no mounted passengers. Copied HQs
  reconnect to copied parents and members; references outside the stamp retain
  their existing HQ. HQ staff settings and Battle Plans are copied, with goals
  inside the stamp translated and conditions remapped to copied objectives.
  Garrison areas inside the stamp are copied for copied HQs. Supply groups,
  depots, leaders and support aircraft/ships are not duplicated by region paste.
  Limits, incompatible ownership and opposing/overfull stacks reject the whole edit.
- **Tools → Move formation**: choose an HQ, select a destination hex, and click
  **Move HQ to selected hex**. The entire formation moves by one hex-space
  translation, preserving relative positions. Choose whether to include child
  HQ formations and whether to move their authored Battle Plan goals and
  garrison areas. Future reinforcement entry positions move with the formation;
  arrival times stay the same and off-map units remain off map. Leaders stay
  attached. Saved routes and target/fallback hexes move with their units.
  A mounted group must move together. A garrison shared with an unmoved HQ
  cannot move; disable moving goals/garrisons or move the common parent formation.
  Supply entries, depots and victory objectives stay in place for formation moves.
- **Tools → Shift map**: enter column/row shifts and the resulting dimensions.
  Positive values move right/down; negative values move left/up. Increase the
  dimensions to leave room. Odd-row translations stagger columns to preserve
  hex adjacency. Terrain, ownership, edges, hills, units and reinforcement
  entries, targets, objectives, place names, supply entries, map depots,
  garrisons, naval markers, authored plans and saved AI locations move together.
  Saved movement directions remain valid and every translated route step is checked.
  Uncovered cells use the Terrain brush and selected owner. Terrain outside the
  new grid is discarded, but any stranded location or route rejects the whole
  operation. Off-map sentinel positions and reserve depot zero remain unchanged.
- **Flood fill with terrain brush**, also available on Terrain, fills the
  selected hex and its connected neighbors of the same base terrain, regardless
  of variant. It preserves roads, rivers, slopes and hilltops; cosmetic edges
  update only when **Blend edges while painting** is checked.
  Choose the starting hex, choose the Terrain brush, then fill. Tools displays
  the current brush and preserves it while selecting other hexes.
- **Tools → Resize map**: enter the new dimensions and click **Resize map**.
  The upper-left origin stays fixed. Rows/columns are added or cropped at the
  bottom/right; added cells use the current Terrain brush and chosen owner.
  Dimensions include the game's final boundary row/column. The editor offers
  4–125 rows/columns and can retain a larger dimension from an existing file.
  Before shrinking, move/remove any locations the editor reports outside the
  new bounds, including units and reinforcement entries, objectives, names,
  hills, supply/depot locations, garrisons, naval range markers and AI goals.
  Cropping saved movement routes is blocked. No unit or objective is silently
  deleted. A successful resize recenters the view.
- Drag to pan in any tool. **Undo** and **Redo** move through individual document
  edits in chronological order. **Save** or **Save As** writes the map and OOB together.

Each region paint/paste, formation move, map shift, flood fill and resize is one undoable edit. These map
tools write native SCN fields and need no additional executable patch. D-Day's
scenario-selection/overview pictures are regenerated by Export for DOS for the
library executable. Executable-specific AI coordinates are not rewritten.

Game assets are discovered under `game/waw/` (the current layout), with support
for the older `game/dday/`, `game/stalingrad/`, and `game/operation_crusader/` layout.

The map panel scrolls in smaller windows. Individual placement requires clearing
saved routes and dismounting first using the Units page. Formation moves and map
shifts update linked locations together. Unit stats remain on the Units page.

## Terrain catalog and artwork from other games

**Terrain Reference** now lists the complete D-Day palette even before opening
a scenario: fourteen terrain types, with six base artwork variants each. Usage
counts and the optional **Only show terrain used in this scenario** filter do
not restrict the painting palette. Click a variant to select it on Map.
The map's **Browse terrain from all games…** button opens this catalog.

The **Artwork** selector also offers Operation Crusader (71 base artwork
choices) and Stalingrad Summer/Winter (90 each). The editor reads the staged
artwork from its own `assets/terrain/` data library. The earlier games no
longer need to remain installed to browse or insert their terrain. The library
contains both native zoom levels, palettes, dim/night artwork, and source
resource fingerprints. `tools/build_terrain_library.py` rebuilds those data
files from the staged originals when needed. Artwork names are visual
descriptions, not claims about the source games' terrain-code tables.

To paint foreign artwork on a D-Day map:

1. Open a D-Day scenario, choose another game's artwork in Terrain Reference,
   and click a tile.
2. Paint the map. The editor automatically uses a D-Day terrain equivalent
   and reuses an existing artwork assignment or selects an unused variant.
   Each catalog row shows the D-Day rules it uses. Only when all six variants
   are already used on the map does a dialog ask which artwork to replace;
   it shows how many hexes would change appearance.
3. **Save** or **Save As** writes the scenario and its
   `assets/NAME.SCN.terrain.json` artwork document. Converted units also use
   `assets/NAME.SCN.counters.json`. Use **File → Export for DOS** to produce the matching
   SCN/REZ/AI set for manual copying.

The companions embed the artwork pixels. Keep the `assets` subfolder when moving
scenarios, and use Save As to rename them. Older artwork files directly beside an
SCN still load. Copy the three DOS exports into the library executable's SCENARIO directory. Failed multi-file saves roll back the changes;
temporary rollback files are cleaned up, with no persistent `.bak` files.

Default behavior is Clear for open/desert/scrub/rocky artwork, Forest for
woodland, Swamp for marsh, Town for towns/scattered buildings, City for city
and industrial blocks, Rubble for ruins, Water for water and Airfield for
airfields. Crusader's town variant uses Town even within another artwork row.
These are D-Day equivalents, not reproductions of the older engines' rules.

**Undo Last Edit** also undoes artwork assignments. **Restore original D-Day
artwork** restores the selected type/variant slot. Save updates the scenario and
artwork atomically without `.bak` files. DOS export writes the SCN, REZ and AI
together and rolls back failed writes.

Terrain imports use the assigned terrain slot and replace its base terrain artwork
at both native zoom levels, including dim/night copies. Unit imports can also
add their source chits through the separate counter-artwork system.
D-Day has six base variants per terrain rule and one shared
night tile per type; the lowest assigned variant supplies that night tile.
The editor normalizes imported transparency to D-Day's hex outline to prevent
white source pixels becoming holes. Roads, rivers, slopes and edge blends
continue to use D-Day artwork and are preserved by base terrain painting.

Terrain artwork import does not convert scenario structures or reproduce the
older games' terrain rules; whole-scenario conversion is a separate editor
feature. The library executable selects each scenario's exported REZ companion.
The v4 fallback instead shares `DATA/PCWATW.REZ` across its seven slots.
See the [runtime test notes](../game/waw/patches/README.md) for actual testing.
**File → New Scenario** creates an empty scenario; its defaults and runtime slot
are described above. Some authoring controls remain unavailable, as listed below.

## Briefings and scenario data

Each side has eight briefing lines, each up to 127 characters in Mac Roman.
Blank lines count; visual wrapping does not. Save rejects unsupported characters
or excess text without truncation. Scenario Settings edits the supported flags.
Tools offers scenario validation and unit-list export.

D-Day SCNs are a sequence of length-prefixed blocks; the opening `0x1230` is the
4,656-byte Scenario block length, not a 96-byte file header. Ground and support
unit records are 172 bytes. `lib/unit_roster.py` defines the verified block layout
and linked auxiliary tables. Older pointer-based analyses in this repository are
historical and should not be used as a current write specification.

## Remaining authoring gaps

These are current limitations of the editor, not fields erased on Save:

This list includes both editor work and possible engine extensions. Bulk moves,
coordinate shifts and copying regions with scenario contents use native data
and are implemented. HQ supply settings, mounted transport and individual
plotted routes are editable; calculated logistics fields remain read-only.
Nested conditions, reinforcement release and messages extend the authored-AI
engine patch; they are implemented extensions, not dormant native scenario settings. Victory
ratios and verified terrain constants are editable through Game Profile and its
independent runtime patch layers; combat/movement formulas remain native.

- **Complete unit definitions:** transferring an entire HQ formation to the other side,
  changing between ground/HQ/support roles and adding new engine classes remain
  unavailable. Aircraft/naval categories and their shared artwork are editable;
  individual support-unit pictures would require another engine extension.
- **Map authoring:** resize retains the upper-left origin; Shift map moves the
  map and scenario coordinates together. Crops that would strand references
  are blocked. Region copies can include ground units/HQs, labels, objectives
  and ownership. Automatic terrain-edge blending uses D-Day's existing fringe
  artwork; it does not synthesize fringes from imported/custom pixels.
  DOS export does regenerate selection previews, mini-maps,
  overview pictures and title banners from the edited map and title.
- **Artwork authoring:** custom terrain/ground-chit imports, individual leader
  portraits and game/series/publisher splash screens are supported. A pixel
  editor, custom banners, the animated Atomic/About screens
  and other menu decorations remain unavailable. Popup busts are still shared
  by side/message context, independently of leader portraits.
- **Scenario systems:** generated-weather parameters and supply formulas have
  no controls. Weather edits an explicit authored sequence and
  initial ground conditions. Opaque/runtime bytes in leaders and depots are
  preserved rather than exposed as guessed settings.
- **AI and victory rules:** Battle Plans provides timed and conditional HQ
  orders, nested ALL/ANY groups, persistent activation, one-time reinforcement
  releases and public messages, all saved with the game. Other actions, new
  condition types, arbitrary scripts and configurable formulas remain unavailable. Native scenario-specific
  routines still run. Victory ratios are editable on Game Profile; movement/combat
  formulas remain D-Day behavior. Game Profile also edits dry/light-mud movement
  costs, strategic road costs, and defense/bombardment terrain multipliers;
  see [terrain rules](TERRAIN_RULES.md). Patch version 4 supports up to 400
  turns in both weather and victory history.
- **Cross-game conversion:** all staged Stalingrad, Crusader and V4V scenarios
  convert to profiled documents with preserved source records. Adapted Stalingrad/
  V4V winter behavior is available; other original engine algorithms and scripts
  are not reproduced. Terrain pictures may share D-Day's limited variant slots;
  Crusader's nationality/supply models require adaptations. Stalingrad's campaign
  retains its three-turn day. See [WaW notes](WAW_CONVERSION.md) and [V4V notes](V4V_CONVERSION.md).
- **Runtime presentation:** the separate library executable discovers up to 256
  compatible SCNs in the existing panel, selects matching graphics/AI, and
  restores their identity from saves. New exports generate previews and banners.
  The presentation layer loads authored flags, portraits and side emblems;
  remaining core D-Day UI artwork stays native. The v4
  fallback retains the original seven slots. See the
  [library patch notes](../game/waw/patches/README.md#runtime-scenario-library-version-1).
- **Saved-game editing:** active battle records cannot be rewritten; individual
  relocation requires clearing routes and dismounting first;
  this is not a complete saved-game editor. Scenario authoring has session-wide
  undo, redo and a browsable edit history as described below.

## Undo, redo and edit history

**Undo** (Ctrl+Z) and **Redo** (Ctrl+Y or Ctrl+Shift+Z) are available from the
Edit menu and toolbar, with buttons on Map and Units. They share one chronological
history for the open document, including:

- Briefing text for either side, including drafts too long to save yet.
- Every applied unit-property, chit, availability and HQ-assistance change.
- Unit add/delete/restore, placement, definitions and HQ organization.
- Unit supply, mounting/dismounting and plotted movement orders.
- Terrain, counter and presentation artwork, including imported images.
- Terrain/features, place names, ownership, cosmetic edges, region painting,
  paste, flood fill and map resizing.
- Victory objectives, scoring/duration/start date, weather/ground conditions,
  supply groups and entries, battle plans, leaders, replacements, garrisons and depots.

Choose **Edit → Edit History…** or **History…** on the toolbar to see the ordered
changes, their times, the current position, undone steps and the saved step.
Select a row and **Restore Selected** (or double-click it) to move directly to
that document state. Moving back retains the later steps for redo; making a new
edit then replaces those later steps. Invalid operations and no-op applies do
not add a step or erase redo. Unit edits show their changed fields in the details.

Briefing typing is grouped into bursts separated by a one-second pause, changing
sides, leaving the field, or another document action. Other forms enter history
when **Apply** succeeds. Save/Export collect pending forms into one undoable
**Apply pending form edits** step. Undo also handles pending forms, retaining
them for Redo; invalid forms must be corrected or reverted first. Adding/deleting
units or opening organization/definition editors applies pending forms before
roster indexes can change. **Revert Form** discards the displayed unapplied draft.
Picking a brush, zooming, panning, filtering units and copying a region do not
change the document and do not enter history. Each region operation is one step.

**Save** and **Save As** retain history and mark the saved position. Undoing a
saved edit marks the document modified again; returning to the saved content
clears that flag. Save As keeps history while switching the current filename;
undo does not switch back to the old file. Failed or cancelled saves retain all
edits and the saved checkpoint; validated drafts may already be in history, but
are still unsaved. Legacy-table repairs performed by Save appear
as a separate preparation step if they change the document.

History lasts for the current editing session. **New**, **Open**, **Reload** and
closing the editor end that history; reopening a file starts a fresh history.
No history files, backup trees or additional DOS files are created. The editor
keeps compressed scenario snapshots and shares immutable artwork data between
steps; no arbitrary step-count limit is imposed. This editor feature does not
require another DOS executable patch.

## Requirements and usage

Python 3.10 or newer, Tkinter and Pillow are required. The staged D-Day resource
file is `game/waw/dday/DATA/PCWATW.REZ`; the terrain library is under
`assets/terrain`. DOSBox-X is not required by the editor. The editor does not
require `extracted_images` with these assets present. That folder
can be deleted; some historical extraction scripts and optional fixture tests
still refer to it.

```sh
python3 scenario_editor.py game/waw/dday/SCENARIO/BRADLEY.SCN
```

Shortcuts: Ctrl+N creates a scenario, Ctrl+O opens, Ctrl+S saves,
Ctrl+Shift+S saves as, F5 reloads.
Reload discards staged changes. Keep the source games as originals and use Save
As for experiments. Validate and test edited scenarios in the game.

The current GUI is `scenario_editor.py`, backed by `lib/scenario_parser.py`,
`lib/unit_roster.py`, `lib/map_editor.py` and the artwork modules. The separate
legacy `scenario_creator.py` is not the current editor.
