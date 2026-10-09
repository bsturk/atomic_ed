# Aircraft and naval customization

Verified against the protected-mode D-Day executable and staged scenarios,
2026-10-07. `disasm/disasm_war.txt` describes the DOS loader, so native function
addresses below refer to the executable's embedded symbols and LE code object.

## Native records and category changes

OB records are 172 bytes. Class +0x76 is 5 for ships, 6 for aircraft. Descriptor
+0x77 selects ships 30–34, and aircraft 37/38 (category 0), 36 (1), 94 (2),
95 (3). Descriptor 35 has partial native bomber handling but no staged D-Day
template; the editor does not offer it as a new category.

`RWShipClassData` 0x29a23 stores ten int16 counts followed by ten int16 heads.
`RWPlaneClassData` 0x29bf8 stores eight of each. Each half belongs to one side.
Heads are indices into that side's OB. Groups are contiguous, but their physical
order is not always ascending: CAMPAIGN places monitors before heavy cruisers.
`SetupCurrentShipClass` 0x57cb7 and `SetupCurrentPlaneClass` 0x5c7a8 enumerate
these ranges directly. Their `sScreenUnitID`/`ScreenUnitID` arrays are 20 int16s
at data offsets 0x10068/0x131b0, immediately preceding ShipRect/PlaneRect.
The editor therefore enforces 20 records per category, including retired records.

Category edits rebuild only the support tail and its OB+0x54 identities and
category tables. Ground OB indices, HQ chains, artillery indices belonging to
other units, and ground movement-order buffers remain stable. OB+0x70 is a
runtime display index and is rebuilt by the game. Changes are blocked when
support missions or leader attachments would leave external references behind.

Ships and combat aircraft use 28-byte artillery records; transports/recon do
not. An edit into a combat role allocates a fresh auxiliary slot, scaling the
template's strengths by ready aircraft. Leaving a combat role reserves the old
slot rather than renumbering unrelated artillery. Combat-to-combat changes
retain the existing bombardment settings. Aircraft receive the target template's
flight/cargo profile; name, side, nationality, arrival, quality and aircraft
counts survive. Default missions from `GetDefaultAirMission` 0x5cf02 are
1 for combat, 2 for transport and 3 for recon. Mission 4 reserves a squadron for
air superiority; it must not be read as a ground-unit activity value.

Aircraft OB+0x40 is full squadron strength, +0x80 ready aircraft, +0x81 aircraft
under repair, and +0x84 a related saved repair value. These overlap ground-unit
rebuild/HQ fields. `RepairOneSquadron` 0x5cfbc confirms these meanings. Import,
duplication, transfer and deletion/restoration now preserve them. Ordinary
category changes preserve them too. The engine subsequently recalculates combat
aircraft bombardment from its per-aircraft strength and ready aircraft.

## Availability

The 80-byte `planecounts` block is `AirAvail`: int16[side][category][5 levels],
not a disposable cached total. `SwapPlaneCounts` 0x29917, `SetCurrentPP` 0x5c8cd
and `SetAirSuperioritySquadrons` 0x5d295 confirm its use. The current level is
Scenario+0x1229. Native code reserves `category count - AirAvail` squadrons and
skips categories with zero availability.

When counts change, the editor adjusts only affected categories:
`new_available = clamp(old_available + new_count - old_count, 0, new_count)`.
This adds new squadrons to every level, reduces availability first when removing
one, and leaves other reservations intact. Some stock files have out-of-range
values in unused levels; untouched categories retain their original bytes.

`MoreAirSupport` 0x514c6 doubles Allied combat-category availability and asserts
the result fits the roster. New categories can have only one squadron. The
support-artwork patch replaces this routine with a bounded double; unchanged
valid native counts produce the same result.

## Artwork and engine patch

`InitPSButtons` 0x3882 lays out PICT 131 category buttons, 71 × 34 pixels with a
35-pixel row pitch. D-Day's naval column begins at x=36; aircraft columns at
x=108 (Allied) and x=180 (Axis). Five ship categories share artwork across sides;
four air categories have separate side artwork. These buttons include their
labels. Individual aircraft/ships do not have independently selectable pictures.

Stalingrad has aircraft columns x=36/108, rows 0–3, and no naval column. Crusader
has one x=36 column: Allied fighter/bomber rows 0/1 and Axis rows 2/3. Its sheet
does not supply transport/recon pictures. Portable PICT 131 extracts are under
`assets/presentation`; the earlier games need not stay installed to use them.

Existing presentation sidecars store button crops. DOS export replaces only
their rectangles in PICT 131, preserving mission icons and adjacent buttons.
Previews copy index zero opaquely, matching the game's button drawing.

The independent `dday-support-artwork` layer follows `dday-advanced-orders`.
It routes PICT 131 to the scenario resource overlay and reloads cached buffer 13
with `LoadAPict` after selection/resume, including returns to base artwork.
`OpenPSBox` 0x5ce2d originally chose a button before skipping empty categories;
new wrappers select the actual first category before setting the button index.
The layer also bounds the optional air-support bonus described above.
Earlier patches and the original executable stay unchanged.

## Validation

`tools/test_support_units.py` checks all supported category transitions on both
sides, native unsorted groups, independent auxiliary allocation, imported and
transferred aircraft counts, category limits, availability, isolated exported
pixels and editor selection/import/Undo/Redo/Save As/reopen. Unicorn tests run
the native category-list and default-mission functions, and the assembled
resource-routing, reload, initial-picture and air-bonus hooks. Existing unit,
artwork, runtime-library and advanced-event regressions also pass.

DOSBox-X loaded an edited COUNTER export with a transport changed into a medium
bomber and a battleship changed into a heavy cruiser. The game listed both
units in their new categories, displayed an imported Stalingrad aircraft button
and custom cruiser button, and wrote both categories and aircraft counts to its
native save. A cold resume with the final binary retained the custom cruiser
picture and displayed the correct initial category without an extra click.
This is a load/UI/save/resume smoke test, not a complete campaign test.
