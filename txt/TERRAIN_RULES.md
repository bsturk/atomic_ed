# Scenario terrain constants

**Scenario Settings → Game Profile → Edit Terrain Rules** edits verified D-Day
constants. Each scenario owns its values. Apply creates one undoable history
entry; Cancel discards the dialog. Selecting another terrain retains pending
edits. Restore This Terrain and Restore All D-Day Defaults are available.
Save/Save As retain the rules in the existing authoring metadata; DOS export
embeds them in the matching REZ. No extra DOS companion file is introduced.

## Controls and units

- **Dry / Light mud movement:** twelve movement classes for each of fourteen
  terrain codes. The displayed MP cost is one step through uniform terrain.
  A step between different terrains averages their contributions, then native
  crossing and visibility modifiers apply. Zero means **blocked**, not free.
  Range 0–10 MP, increment 0.02 MP. Water and Fixed remain blocked.
- **Roads:** twelve movement classes × dirt road / paved road / railroad.
  These are costs per step in Strategic mode before visibility effects.
  Range 0.002–10 MP, increment 0.002 MP; Fixed stays zero. Positive mobile
  road costs also protect the native AI movement-range divisor.
- **Defense / Anti-armor defense:** percentages applied at the original
  terrain-modifier stage of `ModifyStr`. Range 0–400%; 100% is unchanged.
  Supply, passenger, fortification, fatigue and disruption calculations still
  surround that stage. Native minimum-strength behavior remains.
- **Bombardment received:** percentage applied by `ModifyBarrageForTerrain`
  before fortification protection. Lower values protect the target. Range
  0–400%. Native rounding and the nonpositive-result fallback of 10 remain;
  0% therefore does not make a hex completely immune.

The original algorithms remain in charge. Slope/river crossing penalties,
visibility, spotting, ZOC effects, swamp-specific attack reductions and special
water/beach behavior are not configurable here. Normal and muddy movement
values do not choose the weather state: the native weather-state byte does.
D-Day has two verified cost-table planes, dry (0) and light mud (1). The weather
UI retains labels for other states, but this executable contains no verified
additional COT planes. Those states keep their native behavior; this patch
neither invents deep-mud/freeze tables nor changes weather-state transitions.
All seven original D-Day scenarios and 43 staged conversions use state zero.

## Custom terrain

Assign/import artwork using the terrain palette, then edit the matching terrain
code's constants here. All six artwork variants and their rotations share the
same rules. Codes that originally shared a COT cost column can now be tuned
independently: e.g. Clear and Bunker no longer have to share movement costs.
The engine still has fourteen playable base terrain codes, not an unlimited
custom-terrain registry. Slot-specific special behavior remains attached to
that code. Terrain names and DOS terrain-information strings remain native;
this does not add custom names to the game.

Other-game artwork libraries work with these settings, but choosing a source
game profile does **not** automatically translate its original terrain rules.
Terrain defaults are verified D-Day values. The separate victory/winter profile
controls preserve any authored terrain overrides when changed.

## Runtime storage and compatibility

Install the current `game/waw/dday/INVADE-PATCHED.EXE`. Its independent
`terrain-rules` layer follows `game-profiles`. Earlier executables can silently
ignore new rules; they must be updated to play these exports correctly.

Only nondefault terrain rules add a `WAWTER01` block immediately before the final
64-byte `WAWPRO01` block in the REZ. The SCN/save library flags are then 7
(assets + profile + terrain required). The terrain block is exactly 844 bytes:

| Offset | Content |
| --- | --- |
| 0 | Eight-byte `WAWTER01` magic/version |
| 8 | Little-endian uint32 length, 844 |
| 12 | uint32 additive checksum of all 414 words |
| 16 | 336 uint16 base costs: ground state, mobility class, terrain code |
| 688 | 36 uint16 road costs: mobility class, road type |
| 760 | 14 uint16 defense percentages |
| 788 | 14 uint16 anti-armor defense percentages |
| 816 | 14 uint16 bombardment percentages |

Base costs store half-hex contributions in hundredths, multiplied by 10 by the
native consumer. Road costs store half-step thousandths, multiplied by 2 by the
native consumer. Model and runtime validate counts, checksum, ranges, blocked
Water/Fixed entries and positive road divisors before committing the selection.
Malformed or unsupported identity metadata is rejected by the new library.
Staging is separate from the active table: a failed resource/AI selection keeps
the previous rules. Selecting an ordinary scenario restores native road and AI
weights and stops using custom terrain values. Cold resume reloads the same
scenario REZ; retain that file with saves. As with winter profiles, replacing
its rules changes subsequent play in an existing save.

AI movement and passability use the common `BaseHexCost` hook. The live native
`RoadCost` table is updated so `CalcMaxQuanto` and `max_moves` use the same costs.
AI positional terrain ratings contain approximate weights that sometimes differ
from the actual combat multipliers. Unedited weights stay byte-for-byte native;
when a combat field is changed, its corresponding AI rating gets that authored
percentage. This preserves stock positional heuristics while allowing the AI to
consider an authored defense or bombardment change; it is not a new AI strategy.

## Disassembly evidence and validation

Addresses are relative to original D-Day code/data objects (file bases
`0x53654` and `0x107654`).

| Consumer/data | Address | Evidence |
| --- | --- | --- |
| `BaseHexCost` | code `0x2ba81` | COT entry ×10; terrain/mobility/state lookup |
| `cotVals` / `COT` | data `0x6f24` / `0x805e` | 14 mappings into two 12×10 short tables |
| `calcMC` | code `0x2c020` | Origin + destination contributions, crossing cost, visibility multiplier |
| `HexSideCost` / `RoadCost` | code `0x2bf4e` / data `0x824c` | Strategic road cost ×2; twelve classes ×three roads |
| `CalcMaxQuanto` / `max_moves` | code `0x501d0` / `0x76514` | AI movement estimates use paved-road cost |
| `ModifyStr` terrain stage | code `0x14e96–0x14f2f` | Defense and anti-armor multipliers; all surrounding native logic retained |
| `ModifyBarrageForTerrain` | code `0xd63f`; selector `0xd69b` | Terrain multiplier before fortifications |
| AI positional weights | data `0x83fa`, `0x8424`, `0x844e` | Bombardment, defense and anti-armor heuristic arrays |
| Weather state | weather block `+0x318` / patched `+0x4bc` | COT plane selector; UI strings at data `0x6abc` |

`tools/test_terrain_rules.py` executes assembled x86 under Unicorn: every
terrain/mobility/state default, actual combat constants and rounding, authored
movement/road/defense/bombardment effects, blocked entries, AI road estimates,
loader failure rollback, switching, cold resume, and exact independent reversal.
Tk tests cover per-terrain drafts, validation, Apply/Cancel, undo/redo and saving.
Extreme custom percentage multiplication uses a signed 64-bit intermediate and
saturates to a signed 32-bit result; unchanged terrain modifier settings take the original arithmetic
path. This guard does not repair overflow elsewhere in native combat formulas.

The targeted suite passed 76 tests with Tk under Xvfb. DOSBox-X also ran identical
16×12 scenarios with a plotted infantry route: native Clear 1 MP advanced three
hexes, while authored Clear 2 MP advanced one. The exported rules identity
survived native Save and a cold Resume; the next turn matched the uninterrupted
run's infantry position and movement balance. Campaign balance still needs
playtesting. Patch reproduction and full byte-for-byte reversal both passed.
