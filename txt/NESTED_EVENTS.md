# Nested conditions and one-time actions

Battle Plans now supports nested ALL/ANY groups, reinforcement release, and public
scenario messages. These are extensions of the editor's authored-AI patch. They
are not an unused scripting feature in the original games. Combat and victory
algorithms remain native; verified constants remain on Game Profile.

## Editor controls

Open **Scenario Settings → Battle Plans**, add/edit a phase, and choose **Action**:

- **Issue HQ orders:** choose the HQ, turn range, priority, goal and order. The
  **Action details** tab contains the order selector. The highest-priority matching
  order wins for that HQ. **Keep active after first matching order** retains its
  eligibility through its last turn after it actually supplies an order.
- **Release HQ reinforcements:** choose the HQ and turn range. This fires once,
  rescheduling its pending ground members, including its HQ unit, for the next
  normal arrival phase. **Hold pending reinforcements until released** is on by
  default: a fresh game moves their arrival dates beyond scenario end until the
  event fires. Uncheck it to retain their original schedule until an earlier
  conditional release. Units already deployed or removed are unaffected.
- **Show public scenario message:** enter 1–119 printable CP437/DOS characters in
  **Action details**. It needs no HQ and fires once. The game displays it in its
  portrait panel, wraps words, and offers another page when needed. Click to
  dismiss. The message is visible to the current local player; there is no
  per-side inbox or separate PBEM delivery system.

Use the existing simple conditions, or select **Edit Nested Conditions…** on the
**Conditions** tab. Add checks, ALL groups or ANY groups; groups can contain other
groups. Select a check to set its side, objective or casualty threshold. **Use These
Conditions** keeps the draft in the parent phase; **Apply Phase** commits it.
**Use Simple Conditions** replaces the nested draft with the simple controls.

Example: release reserves when **ALL** of these hold:

1. **ANY:** Allies control the bridge; Allies control the crossroads.
2. Axis losses reach 100 casualty points.

Limits are 16 objective/loss checks, 32 total nodes, four nested group levels and
256 phases. The conditions are the same verified objective-control and cumulative
casualty-point tests as earlier versions. There are no new percentage-loss tests,
NOT operator, arbitrary variables or scripts. Casualty points exclude objective
scores; the Victory casualty weights affect loss thresholds.

## Timing, arrivals and references

HQ conditions are checked when the AI requests orders. One-time actions are
checked on fresh scenario start and after each turn's objective/scoring update,
within their inclusive first/last turn range. **Always** fires at the first
eligible check. All eligible one-time actions run; priority orders simultaneous
actions and chooses competing HQ orders. Ties between actions retain editor order.

Releases change native arrival dates, not map occupancy. The following native
arrival phase places eligible units using their authored locations and the game's
normal rules. Direct members of the chosen HQ are included; subordinate HQs need
separate release phases. Aircraft/naval support is excluded. A release does not
create units, restore casualties, move off-map entry locations, or release
another HQ's formation. If a held event never matches before its last turn, its
reinforcements remain unavailable. Multiple release phases for one HQ act as
alternative opportunities to release its pending troops.

A release on the final scenario turn cannot produce an in-scenario arrival phase;
leave at least one subsequent turn. Assign actual future arrival dates on Units
before using Hold; it does not withdraw units that are already in play. Normal
HQ/arrival dependency checks still run. Native scenario-specific routines also
continue to run, so converted scenarios still need playtesting.

Objective references in nested groups participate in deletion checks and region
copy/remapping. Map shifts and formation moves transform HQ order goals; release
and message actions have no map goal. Removing an HQ referenced by a release is
blocked until its release phase is changed or removed. Date changes preserve
relative phase turns. Undo/Redo, Save, Save As and DOS export include these edits.

## Installation and persistence

Use the current `game/waw/dday/INVADE-PATCHED.EXE` as `INVADE.EXE` in your playing
copy. Export for DOS and install the matching SCN, REZ and AI together. No fourth
file or per-scenario executable is needed. See [playing instructions](../game/waw/README.md).

Fired actions and persistent orders share the saved event activation state. Cold
Resume restores it; a release's changed arrival dates are ordinary saved unit
data. Keep the matching exported AI file with the save. Changing its fingerprint
causes Resume to reject the save instead of applying bits to different events.
Do not replace the AI file while the game is running. Saves from before the event
extension do not contain past action history.

The new patch also fixes native repeated-save truncation. The original writer
can overwrite a shorter save without removing the old tail. A stale event/identity
footer at EOF could otherwise restore outdated activation bits. After writing the
new footer, the patched binary truncates the file at the current position.

## Runtime format and patch research

Authoring documents use a JSON payload inside the existing SCN trailer, followed
by its uint32 length and `WAWAI004`. Existing `WAWAI001/002/003` documents retain
their earlier encodings when they do not need nested groups or new actions.

DOS AI uses the existing 32-byte fingerprinted header, signature `WAWAI004`, and
320-byte guarded rows. Rows remain priority sorted. The compact logical row is:

| Logical bytes | Meaning |
| --- | --- |
| 0–15 | Eight uint16 fields: scenario/marker, side, HQ, first/last turn, order, X/Y |
| 16–19 | Action (0 order, 1 release, 2 message), token count, hold flag, zero |
| 20–27 | Reserved zero |
| 28–31 | Sum of all logical bytes excluding this checksum field |
| 32–159 | Up to 32 four-byte postfix condition tokens, remaining slots zero |
| 160–279 | CP437 message, NUL terminated and padded, or zero for other actions |
| 280–281 | Reserved zero |

Markers are `0x84` (ordinary) and `0x85` (persistent HQ order). Message HQ is
`0xffff`; non-order actions carry canonical Idle and dummy map-origin coordinates.
The physical row retains its first 16 bytes, then stores 19 chunks of `0xffff`
guard plus 14 logical bytes. Every aligned 16-byte legacy record has an unsupported
selector, preventing older engines from treating token/text payloads as orders.

Tokens are `<opcode:uint8, argument:uint8, value:uint16>`. Opcode 1 tests an
objective index owned by argument side. Opcode 2 tests that side's casualty
threshold. Opcodes 16/17 combine argument-count stack entries with ALL/ANY;
value must be zero. Empty token streams mean Always. The runtime validates all
tokens, guards, padding, checksums and references, including branches whose result
would already be determined. Bad files fail explicitly. No recursion runs in DOS.

The existing 80-byte `WAWEVT01` save extension retains its layout: signature,
32-byte AI identity, 32 activation bytes (256 bits), closing signature. Each sorted
row owns one bit. One-time actions set it before executing. Persistent HQ orders
set it only when selected to supply an order.

Native addresses verified from the staged binary/disassembly:

- Fresh start: wrap `StartAGame`'s `RestoreCursor` call at `0x30119`; apply holds and
  initial actions only while `NewGame` is set. Resume does not reapply holds.
- Turn tick: wrap `TabulateCities` call at `0x112b2`, before endgame checks/autosave.
- Release: OB record size 172; arrival int32 at +8; class at +0x76; assigned HQ at
  +0x81, or own HQ auxiliary index at +4. `UpdateTroops` (`0x1a760`) handles arrival
  when date equals `Calendar+12 - 1`; in-play dates are strictly less than current.
- Messages: `ShowHelp` (`0x1f0c0`), negative ID -6 bypassing optional hints;
  `WriteMsgToHelp`'s call at `0x1f627` dispatches the custom text renderer for that
  ID only. Native debug dialogs keep their original renderer. `CharWidth` measures
  wrapping; `PrintOneLine` draws within the existing portrait panel.
- Save truncation: binary `write` (`0x8f643`) with count zero invokes DOS AH=40h
  truncation at the current file position before `FSClose`.

The independent `dday-nested-events` layer follows `dday-terrain-rules`. It adds
five further 4-KiB LE code pages (13 added pages total), extends object 1 to
`0xc0000`, and moves later file pages/fixup indexes without moving the original
code/data addresses. It uses 34,172 of 53,248 added bytes. The data object starts
at `0xd0000`; original relocation targets and the DOS extender remain intact.
See [patch/reversal instructions](../game/waw/patches/README.md#patch-files-and-reversal).

## Validation

On 2026-10-08, 91 targeted tests passed, including Tk authoring/history/export,
assembled x86 truth tables and actions, malformed files, save truncation and cold
resume, linked scenario references and earlier patch regressions. Rebuilding the
patches reproduced the installed executable; independent and full reversal were
byte-exact.

DOSBox-X confirmed hold past the original arrival, conditional release, actual
native arrival, a one-time public popup, cold Resume without repetition, and a
119-character paginated message on fresh start. These checks do not establish
campaign balance or separate PBEM delivery; messages use the local game display.
