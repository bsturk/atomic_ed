# Native unit logistics and plotted orders

Verified against the protected-mode code in `game/waw/dday/INVADE.EXE`.
Addresses below are offsets in its LE code object (file base `0x53654`),
not offsets in the real-mode DOS stub. `disasm/disasm_war.txt` describes that
stub; the native embedded symbols and LE code are needed for these routines.
The editor writes native SCN structures, with no new executable patch.

## HQ and unit supplies

All quantities below are signed 32-bit hundredths of a ton. Editable quantities
are constrained to nonnegative values fitting that representation. HQ auxiliary
records are 58 bytes; OB dword `+4` selects the record, and `hqlist` maps its HQ
ID back to the OB. The organization editor continues to own their hierarchy.

| Location | Meaning | Editor treatment |
|---|---|---|
| HQ `+00` | Current reserve | Editable |
| HQ `+04` | Distribution limit to subordinate HQs | Editable |
| HQ `+08` | Net received/transferred supply in the accounting period | Read-only |
| HQ `+0c` | Calculated supply request | Read-only |
| Scenario `+54 + side*b4 + HQid*4` | Consumed supply accounting | Read-only |
| HQ `+2a`, `+2c` | Cached source and entry group | Read-only |
| HQ `+38`, `+39` | In-play flag and supply connection status | Derived |
| OB `+0c` | Unit carried supplies | Editable |
| OB `+8e` | Supply level, 0–4 | Editable initial state |
| OB `+8f` | Unit supply connection status | Read-only |

The supply-level labels are the executable's `SupplyStr` table: None, Minimal,
Defense, General and Attack. DrawSupplyData (`3a4d0`) and DrawSupplyStats
(`78d65`) divide quantities by 100 for tons. CalcHQDisbPct (`55b2c`) caps
distribution by `min(HQ+04, HQ+00)`. **HQ+08 is not a supply capacity**:
ClearSupplyConsumed (`57133`) resets it, incoming supply increases it, transfers
to child HQs decrease it, and direct consumption is tracked separately.

SetHQSupplyLevel (`561bc`) follows the HQ's OB subordinate chain. It sets levels
only for units in play, with connection status other than 4 and mobility other
than 10 (Fixed). It does not recurse through HQ hierarchy. The editor can also
set an individual unit/HQ's initial level. CalcEffectiveUnitSupply (`53b55`)
can lower levels when carried supplies are insufficient. Editing a level does
not run supply distribution or manufacture stocks.

RWHQs (`2976a`) requires a positive HQ count **less than 44**. The consumption
array reserves 45 dwords per side, but that does not remove the loader's stricter
43-HQ limit. New HQ additions obey it; existing documents remain readable.

HQ transport speed comes from its existing movement class and allowance. No
unverified auxiliary byte is exposed as an invented “truck capacity.”

## Infantry riding armor

The carrier's armor auxiliary record has **three** signed 16-bit passenger OB
IDs at `+0,+2,+4`, a signed 16-bit display group color at `+6`, total passenger
size at byte `+8` and count at byte `+9`. The fourth apparent word is a color,
not a fourth passenger. A foot infantry/engineer auxiliary record has a carrier
OB ID at `+0` and matching color at `+2`. Its four bytes are zero when dismounted.
`RIDING` (`49871`) treats carrier ID zero as dismounted, so armor at OB index
zero cannot be assigned as a carrier without renumbering the OOB.

EligibleToRide (`3c86c`) accepts foot infantry/engineers, checks the passenger's
GetUnitSize against the armor size and remaining capacity `3 - load`.
Ridem (`3bc7f`) has an additional replacement policy: if a group already exists
and the new passenger is larger than 1, or current load exceeds 1, it dismounts
the first passenger. Thus ordinary game mounting produces one larger unit or
two size-1 units. The editor asks the author to explicitly dismount before
such replacement, rather than silently ejecting a unit. It can read all three
serialized slots, but does not offer a third passenger contrary to that policy.

Mounting sets both OB `+91` flags and passenger primary order 2, clears its
route count and removes its serialized orders buffer. Dismount (`3c02a`) compacts
the carrier list, subtracts size/count, clears the passenger auxiliary and flag,
and sets Defend (9). An empty carrier clears its color/flag. The editor also zeros
unused passenger IDs; native code may leave stale IDs outside the active count.
MoveRiders (`3c79c`) moves all passengers to the carrier's current hex.

All link-changing operations validate both ends, colors, sizes and locations.
Deletion dismounts an affected group. Independent location/arrival, class,
mobility and stacking-size changes cannot strand mounted links. Formation moves
require all linked members, including passengers assigned to other HQs.
Adjusted combat strengths are left to the engine's normal recalculation.

## Saved routes

OB `+50` is a 16-bit offset in its side's runtime orders allocation; `+52` is
the fixed buffer size. Scenario dwords `+4c/+50` hold the side allocation sizes.
SaveOrders (`29331`) / RestoreOrders (`293c6`) serialize a full slot only for
ground units with nonzero OB `+86` route count and primary order below 8.
Slots appear after the main SCN blocks in side/OB order, before the preserved
trailer. Clearing a route must remove its slot from that stream, without
removing its reserved runtime allocation or shifting other slots.

`store_orders` (`69328`) writes directions in **reverse execution order**:
the next direction is `Orders[remaining]`, not `Orders[1]`. W/NW/NE/E/SE/SW
are 0/1/2/3/4/5. PlotMove (`33dda`) shifts older steps upward and inserts the
newest step at index 1. `Orders[0]` is not consistently refreshed by PlotMove,
so OB `+86` is the authoritative remaining count. ShowOrders (`344e3`) consumes
steps from that count down to 1 using CalcHexOffs (`463c8`).

The editor validates adjacent playable hexes, side allocation bounds, overlapping
runtime slots, and `min(slot size - 1, 255)` steps. It writes plotted destination
at OB `+5c/+5e`, resets automatic goal `+60/+62` to -1, sets movement state `+64`
to -1 for a route, and clears transient `+85`. Clearing returns a moving unit to
state 7, sets its target to its present hex, clears both goals and chooses Defend.
ResetUnit (`1220f`) also clears artillery mission bytes `+15..+1b` and synchronizes
an attached leader's battle ID; the editor does the same when replacing orders.
Units already linked to a battle are blocked because battle-list editing is
outside scenario authoring.

Primary orders 0/1 and 4–7 accept routes; 8–10 are defensive stances. Passenger
order 2 is managed through transport. The Orders window now selects secondary
orders explicitly. An unchanged submission preserves the native record, padding,
automatic goal and fire pattern byte for byte. Changing a defensive stance can
retain Dig in/Fortify; a movement route requires choosing secondary None.
Clear → Defend explicitly removes the previous modifier. This editor plots an exact path; it
does not reproduce the engine's terrain/combat pathfinding or guarantee a route
can be traversed. Authored Battle Plans remain separate timed/conditional HQ
instructions and can replace individual orders during play.

## Secondary ground orders and artillery missions

OB byte `+78` stores the primary order in its low nibble and the secondary order
in its high nibble. The choices are not independent flags: a unit has one
secondary order at a time. LogButton (`127bc`), BuildButton (`12895`), ArtyButton
(`12b8a`), PlotArtillery (`d0f5`) and UpdateMode (`1c1f9`) establish the following:

| High nibble | Order | Authored state |
|---|---|---|
| 1 | Replace | Primary 9, execution state `OB+64 = -1` |
| 2 | Dig in | Defensive primary 8–10, state -1 |
| 3 | Fortify | Defensive primary 8–10, state -1; engineers or descriptor 93, excluding descriptor 63 |
| 4 | Prepare | Artillery, primary 9, 1–18 preparation turns remaining |
| 5 | Target | Artillery, primary 9, optionally a plotted hex |
| 6 | On call | Artillery, primary 9, state -1, no plotted hex |
| 7 | Counter battery | Artillery, primary 9, state -1, no plotted hex |
| 8 | Shoot 'n scoot | Artillery with auxiliary `+14` capability, optionally a plotted hex |

GetRepType (`1a227`) gives ordinary HQs and supply descriptor 64 no replacement
category. Replace requests delivery; it does not immediately change strength or
deduct the scenario pool. `repsRequested` at runtime data `12a70` is a cache,
not an SCN block. ClearRepsRequested (`1a13e`) / SetRepsRequested (`1a19b`)
reconstruct it from deployed units' orders. ItNeedsReps (`1a321`) and the normal
execution phase still enforce available stock and strength limits.

CanDigOrFortify (`1e451`) rejects terrain 3, 7, 8 and 9. The editor enforces this
structural restriction. Enemy adjacency, the original theater-specific exception
and supply are evaluated during play; it does not claim that issuing the order
guarantees construction. Authored orders do not paint finished fortifications.

Artillery auxiliary records are 28 bytes. `+10` is the configured deployment
time, `+11` range, **`+12` current preparation remaining**, `+13` ammunition
category and **`+14` Shoot 'n scoot capability**. SetArtyState (`d4ae`) loads the
remaining time from the configured value for mobile guns, or zero for fixed guns.
UpdateMode decrements preparation when stationary and not on the arrival turn,
then changes Prepare (`49`) to ready Target (`59`) at zero. It treats values above
18 as invalid. The Orders dialog restricts remaining preparation to 0–18; existing
configured deployment values are still preserved in unit definitions.

A plotted target writes `OB+5c/+5e`, clears the automatic goal `+60/+62`, sets
`OB+86 = 1` and execution state -1. **That 1 is a mission flag, not a movement
route length**: primary order 9 prevents SaveOrders from serializing a route
buffer. A cleared/unplotted artillery target is `(-1,-1)` with mission count zero.
Ground targeting requires readiness, a playable non-water hex and sufficient
range. The even-row offset hex-distance calculation is checked against native
hex_rdir_rdist_hdist (`77eae`). The game still decides whether supply permits fire.

SetFireTarget (`34fbc`) writes **seven auxiliary mission bytes `+15..+1b`**:
W/NW/NE/E/SE/SW, then center. Adjacent occupied friendly hexes receive 2; other
adjacent hexes receive 0. The center receives 2 for friendly support or 1 for
bombardment. FRIENDinHEX (`4a028`) tests both ownership and the occupancy nibble
in ZOCMap; ownership by itself is insufficient. The editor uses that same rule,
including map-boundary checks. Existing coverage is retained when only switching
Target/Shoot 'n scoot; selecting a new target computes the native default pattern.
Clearing/changing away from a mission zeros its seven assignments. Ground-unit
copies and deletions clear mission data, so a fresh or restored unit cannot
inherit an unlinked bombardment assignment.

Preparation and targeting are ground-artillery controls. Aircraft and naval
allocation have separate native mission/availability systems and are not authored
by this dialog. Active battle links and mounted passengers remain protected.
No new executable patch or patch-file rebuild is needed for these native orders.

## Verification

`tools/test_unit_operations.py` checks preservation, reciprocal links, capacity,
sentinel IDs, route limits, artillery resets, 43-HQ enforcement, dialog actions,
save and undo/redo. Unicorn executes the original routines to compare route
encoding, mounting/dismounting, rider movement, supply-level propagation and
distribution calculations. The transport tests skip only adjusted-strength math
and preseed a color to avoid GUI stack enumeration. They execute the actual
linkage and count updates. Related roster and bulk-edit tests use complete native
transport records, including the previously missing color/load/back-reference.

`tools/test_secondary_orders.py` adds order eligibility, preparation, target range,
water/boundary rejection, preservation of unrelated buffers/trailers, mission-free
copies/deletions, real map clicks, form-draft preservation, undo/redo, saving and
DOS export. Unicorn executes original LogButton/BuildButton/PlotArtillery and
SetFireTarget against the same records, checks range across 330 point pairs,
reconstructs replacement requests, advances preparation to ready and cycles the
native artillery modes. Drawing/audio, the turn-specific supply gate and enemy
adjacency lookup are stubbed in these producer tests; the actual order writes,
terrain checks, range calculation, fire pattern and preparation consumer run
in the original code.

DOSBox-X secondary-order smoke test used an exported scenario with an Allied
engineer on Fortify, armor on Replace, artillery on Prepare (two turns), and
Axis infantry/artillery on Dig in/Target. The game loaded and executed two turns
without an order/record error. Native saves showed Allied preparation decrement
from 2 to 1 to 0 and transition from `49` to ready `59`; the engineer retained
Fortify. Replace returned to Defend through the game's execution logic. The
computer-controlled Axis issued its own orders, as expected; this test is not
evidence that AI-controlled units retain authored individual missions. The
executable was the existing library build, unchanged by this feature.

DOSBox-X smoke test: exported a small scenario with HQ reserve 321.45 tons,
distribution limit 123.45 tons, foot infantry mounted on armor and a two-step
route `(6,3) → (7,3) → (8,3)`. The initial native save preserved those quantities,
links and route. After one execution phase, both carrier and passenger were at
`(8,3)`, the carrier had exhausted its route and returned to Defend, and the
passenger was still mounted. The engine retained the 123.45-ton distribution
limit while recalculating reserve, request, receipts and consumption. Tests used
a private `/tmp` game copy and the existing library executable; shipped game
files and patch layers were not modified.
