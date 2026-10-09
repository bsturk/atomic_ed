# Unit supply, transport and orders

On **Units**, select a ground unit and choose **Supply…**, **Transport…** or
**Orders…** under **AI and orders**. Each opens the corresponding page of the
unit operations dialog. Apply commits one undoable edit; Save, Save As and
Export for DOS include it.

## Supply

Quantities are displayed in tons with two decimal places.

| Setting | Use |
| --- | --- |
| Carried supply | Supplies held by the unit |
| Initial supply level | None, Minimal, Defense, General or Attack |
| HQ reserve | Stock held by the headquarters |
| HQ distribution limit | Maximum stock the HQ can distribute to subordinate HQs |

An HQ's distribution is limited by both its reserve and distribution limit.
Received/transferred supply, demand, consumption and connection status are
shown as calculated values. The game updates them during play and can reduce
a unit's supply level when stocks are insufficient.

Applying an HQ's supply level to its direct units affects eligible deployed,
connected, mobile units. Apply levels to subordinate HQs separately. Set an
HQ's movement class and allowance in **Unit Definition**.

Daily deliveries, supply-entry hexes, stock groups and depots are under
**Scenario Settings → Supply** and **Depots**. Each side supports up to **43 HQs**.

## Mounted transport

Foot infantry and engineers can ride same-side armor in the same playable hex.
Select a passenger to choose its carrier, or select armor to manage its load.
Use **Dismount** for one passenger or dismount the carrier's whole group.

The game's mounting rules allow one larger passenger or two size-1 passengers,
with a total size of at most three. Each passenger must fit its carrier's size.
Deploy reinforcements before mounting them, and dismount an existing load before
replacing it. The dialog offers eligible carriers and checks capacity and links.

Passengers move with their carrier. Dismounting puts a passenger on Defend.
Use **Move formation** or **Shift map** to move a mounted group together. For
individual position, arrival, class or mobility changes, dismount first.

## Movement routes

The Orders page shows the current order, target, automatic goal and plotted
route. Choose a movement order and click neighboring hexes in the preview to
plot a path. **Back One Step** removes its last step. **Clear → Defend** clears
the route, secondary order and targets and returns the unit to Defend.

Routes are limited by the unit's available route capacity, up to 255 steps.
Every step must be adjacent and within the playable map. Actual progress uses
the game's terrain costs, obstacles and enemy activity.

Choose **Secondary: None** before plotting movement. Passengers use their
carrier's route. Staff assistance, computer control and Battle Plans can replace
individual orders during play; configure these for the behavior you want.

## Secondary orders

A unit can have one secondary order at a time. The dialog offers choices
appropriate to its class and primary stance.

| Order | Behavior |
| --- | --- |
| Replace | Requests replacements during normal execution, subject to available stock and strength limits |
| Dig in | Orders eligible troops to dig in from a defensive stance |
| Fortify | Orders eligible engineers or fortification-capable units to build fortifications |
| Prepare | Sets artillery preparation time remaining |
| Target | Assigns a ground artillery target |
| On call | Lets artillery respond to support requests during play |
| Counter battery | Assigns artillery to counter-battery work during play |
| Shoot 'n scoot | Uses this mission for artillery with the capability enabled in Unit Definition |

Construction proceeds according to terrain, supply and enemy conditions.
Replacement delivery and construction are resolved by the game after the order
is issued.

## Artillery targeting

Choose **Target** or **Shoot 'n scoot**, then click a hex or enter its X/Y
coordinates. **Clear Target** leaves the guns ready for a subsequent assignment.
On call and Counter battery acquire targets during play.

Preparation remaining ranges from **0–18 turns**. A plotted ground target
requires ready guns, a playable land hex and sufficient range. Supply also
affects whether the guns can fire. The editor sets the target's bombardment or
friendly-support pattern from the units at and around that hex.

Base bombardment strength, defensive fire, range, deployment time, ammunition
category and Shoot 'n scoot capability are under **Unit Definition**. Aircraft
and naval mission allocation takes place in the game.

For formation-wide timed or conditional instructions, see
[Battle Plans](NESTED_EVENTS.md).
