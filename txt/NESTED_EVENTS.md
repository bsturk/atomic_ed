# Conditional events and battle plans

Use **Scenario Settings → Battle Plans** to give formations timed or conditional
orders, release reinforcements, and display scenario messages. These events run
in the patched D-Day game and are included by **Export for DOS**.

## Choose an action

Add or edit a phase, set its inclusive first and last turns, and choose **Action**:

| Action | Setup and behavior |
| --- | --- |
| Issue HQ orders | Choose an HQ, order, goal and priority. The highest-priority matching order wins for that HQ. |
| Release HQ reinforcements | Choose an HQ. The event releases its pending ground members once, including the HQ unit, for the next normal arrival phase. |
| Show public scenario message | Enter 1–119 printable DOS characters. The event displays the message once in the portrait panel for the current local player. Click to dismiss or advance a page. |

For HQ orders, **Keep active after first matching order** keeps the phase
eligible through its last turn once it supplies an order. Higher-priority
phases take precedence. Use different priorities for overlapping
orders assigned to the same HQ.

For reinforcement releases, **Hold pending reinforcements until released**
keeps the selected units waiting for the event. Turn it off to retain their
scheduled arrival as another opportunity to enter play.

## Conditions

Use **Always** for a timed event. Conditional checks can test:

- Whether either side controls an objective.
- Whether either side's cumulative losses reach a casualty-point threshold.

Loss thresholds range from **1–65,535 casualty points**. The casualty weights
under Victory affect these totals; objective scores are counted separately.

Simple conditions combine up to three checks with **ALL** or **ANY**.
**Edit Nested Conditions…** builds a tree of checks and groups. For example:

> Release reserves when (the Allies hold the bridge OR the crossroads)
> AND Axis losses reach 100 casualty points.

Select a check to set its side, objective or threshold. **Use These Conditions**
returns the draft to the phase; **Apply Phase** commits it. **Use Simple
Conditions** switches back to the simple controls.

A phase supports up to **16 checks**, **32 total tree nodes**, and **four nested
group levels**. A scenario supports **256 phases**.

## Timing and reinforcement arrivals

HQ conditions are checked when the AI requests orders. One-time actions are
checked at scenario start and after each turn's objective/scoring update,
within the phase's turn range. Priority determines the order of simultaneous
actions; equal priorities retain their order in the editor.

Before configuring a release, give its units future arrival dates on **Units**.
The release applies to pending ground members directly assigned to the selected
HQ. Give subordinate HQs their own release phases. Units enter at their authored
locations using the game's normal arrival rules.

Leave at least one turn after a release for the arrival phase. Held units stay
unavailable if their release conditions never match. Multiple release phases
for the same HQ provide alternative release opportunities.

## Editing and saved games

Battle plans support Undo/Redo, Save and Save As. Objective and HQ references
stay linked during supported map and roster edits. Change or remove referencing
phases before deleting their objective or HQ. Changing the start date preserves
relative event turns.

Install the matching **SCN, REZ and AI** with the patched executable; see
[installation](../game/waw/README.md). Save/Resume retains fired events and
persistent orders. Keep the matching AI file with the save. After editing the
plans, start a new game or restore the save's matching AI file to resume it.

The game handles pathfinding and tactical execution. Battle plans choose HQ
orders within that system; individual routes and artillery orders are covered
in [unit logistics and orders](UNIT_LOGISTICS_AND_ORDERS.md).
