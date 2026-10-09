# Scenario authoring model and game profiles

The first part of the cross-game superset is implemented. **Scenario Settings →
Game Profile → Edit Game Profile** selects defaults and overrides. New Scenario
also offers a profile. New imports automatically choose their source game,
including the Velikiye Luki winter variant.

This is an incremental authoring model, not yet a fully game-independent map
and OOB. Common editable records still use the D-Day projection. The document
now separately owns a versioned profile and retains the exact original SCN,
plus the V4V battleset payload, so untranslated source fields are not lost.
Retained originals are immutable provenance, not another copy of the current
editable roster. Additional source-only controls and broader terrain/nationality
models remain future work.

## Available runtime settings

- Major and minor victory score ratios, expressed as percentages: defaults
  200 and 125. Major victory is **at least** the major ratio; minor victory is
  **greater than** the minor ratio. The existing treatment of zero scores remains.
- D-Day, Stalingrad, V4V and V4V Velikiye winter models.
- Snowfall, rainfall, snow-melt and drying coefficients, plus ice growth divisor,
  crossing threshold and crossing adjustment. Ground quantities are thousandths.
- **Edit Terrain Rules**: dry/light-mud movement by terrain and movement class,
  strategic dirt/paved/railroad costs, defense and anti-armor defense multipliers,
  and bombardment received. See [terrain rules](TERRAIN_RULES.md) for units and limits.
- Restore Defaults and per-field overrides, with undo/redo and modified-state
  tracking. Changing a profile does not reset current initial ground conditions.

D-Day's default winter arithmetic is unchanged. Stalingrad and V4V's floating
point arithmetic is adapted to D-Day's integer ground storage: ice increments
round to the nearest thousandth each turn. Accumulated rounding and behavior
at threshold boundaries can differ from the original games. These profiles
are not a claim of identical campaigns.

Crusader's winter calculation has not been verified and explicitly defaults to
D-Day's winter model. V4V victory ratios also use D-Day defaults pending research.
D-Day, Stalingrad and Crusader's 2.0/1.25 victory constants are verified.
Combat/movement formulas, supply algorithms, generated-weather parameters and
original executable scenario scripts remain D-Day behavior. Verified terrain
constants can be overridden; source-game terrain rule tables are not automatically
imported.
The profile panel lists these limitations.

New V4V imports advance the original snow/ice/wetness seeds through the historical
weather before scenario start using the selected adapted model. For example,
VLLAST imports initial ground values `(32740, 26477, 30)`, rather than dry ground.
Stalingrad's serialized initial ground values are retained. Existing converted
editing documents keep their prior D-Day profile on open; select a new profile
explicitly, or reimport the original to obtain source provenance and updated
initial conditions. Reimport creates a separate document, so it does not replace
existing edits.

## Saving and playing

The profile and compressed source records live under `document` in the existing
`assets/<scenario>.terrain.json`. No new companion type, backup files or game
copies are introduced. Keep the assets directory for editing. Both Save and
Save As preserve the model, including after map/unit edits. Source blocks can
also be inspected with `ScenarioDocument.source_blocks()` without installed
source games. Loading future unknown model versions fails instead of discarding
unrecognized metadata.

DOS export still writes **SCN + REZ + AI**. When rules differ from native D-Day,
the exporter appends a bounded 64-byte `WAWPRO01` rule table to the scenario REZ
(with an 844-byte `WAWTER01` table immediately before it for custom terrain rules)
and marks the library identity as requiring it. The resource manager ignores the
extra bytes after the resource map. Source archives and editor metadata are not
exported. Opening such a DOS export in the editor recovers its runtime rules
from the matching REZ, although it cannot recover the omitted source archive.

Use the current `game/waw/dday/INVADE-PATCHED.EXE`, including the independent
`game-profiles` and `terrain-rules` patch layers. Earlier binaries do not apply
all these rules and can silently use D-Day defaults; update the executable.
Selection checks the profile signature, version, size, checksum, field ranges
and threshold ordering before committing a new scenario. Missing/bad profiles
reject selection. Selecting an ordinary D-Day export restores native defaults.
Save/Resume loads the profile from the saved scenario's matching REZ. Keep that
REZ with the save; modifying it changes the rules on resume. There is no saved
profile fingerprint lock in this layer.

## Verified sources and patch layout

Addresses below refer to the original executables, not the patched image.

| Game | Evidence |
| --- | --- |
| D-Day | Code object file base `0x53654`; `GetVicLevel` `0x52133`, comparisons at `0x52234/0x5224a`, double constants data `+0x25c6/+0x25ce`; `CalcSnowIceWetness` `0x43a12–0x43b80` |
| Stalingrad | Code file base `0x50054`, data base `0x105054`; victory float comparisons `0x4f9e4/0x4f9fa` to data `+0x1b46/+0x1b4a`; winter routine `0x7477f–0x749a1` |
| Stalingrad winter constants | Light/heavy snow 0.1/0.4, rain 0.015/0.045; data `+0x2588`: melt 0.08, then -0.1, drying -0.05, divisor 18, ice threshold 12, adjustments +0.2/-0.2 |
| Crusader | Code base `0x4e254`, data base `0xf2254`; victory float comparisons `0x49605/0x4961b` to data `+0x19aa/+0x19ae` |
| V4V | `253d:0370–05dc`, file `0x768f0–0x76b5c`; data base `0x16810`, constants `+0x53a8…+0x53c8`; light/heavy snow 0.15/0.45. Velikiye prevents an ice update from crossing down through 12. Startup warmup `24d1:04de–0543` |

`dday-game-profiles.asm` is included conditionally by the library assembler.
The independent forward/undo patch follows `dday-support-artwork`; rebuilding
retains every previous layer byte-for-byte. Two function hooks replace the
victory classifier and ground update. Added loader code stages rules before
asset selection commits. The game-profiles layer alone uses 28,988 of its 32,768 added bytes; terrain
rules are a subsequent independent layer.

Tests execute the assembled code under Unicorn, including relocated addresses,
stock D-Day parity, freeze/thaw boundaries, scale multipliers, victory threshold
boundaries, large scores, rejection of broken companions, scenario switching,
and cold resume. The Stalingrad comparison executes its original winter routine
against the new profile, allowing the documented thousandth rounding. Editor
checks cover profile edits, history, saving and reloading; conversion checks
cover all 27 staged V4V scenarios. DOSBox-X also loaded an exported winter
scenario, advanced turns, saved, cold-resumed and advanced again with the expected
snow/ice values. Campaign balance still requires playtesting.
