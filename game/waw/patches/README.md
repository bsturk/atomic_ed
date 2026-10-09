# D-Day engine and scenario-library patches

This directory publishes patch sources, forward/inverse IPS files, and checksum
manifests. Original and patched executables, validation captures, and development
tests mentioned below remain local and are excluded from Git. Apply the patches
to your own original D-Day executable using the commands below.

Updated 2026-10-09. `game/waw/dday/INVADE-PATCHED.EXE` is the original D-Day
game with all current patches: engine fixes, scenario selection, artwork,
conditional events, configurable victory/winter/terrain constants, and optional V4V FM music.
The startup-selection layer also connects SELECT.BAT's choice to the game's
initial selected battle.
`orig/INVADE.EXE` is the untouched original. These are the only two retained
executables; each patch layer remains separately reversible.

## Using it

The complete patched build is `game/waw/dday/INVADE-PATCHED.EXE`.
It includes the version-4 engine fixes plus directory discovery in the existing
scenario panel. Install it as `INVADE.EXE` in your playing copy and copy exported
`NAME.SCN`, `NAME.REZ`, and `NAME.AI` into `SCENARIO`, without renaming them to
native slots. Retain the original `DATA/PCWATW.REZ` for base resources.
For music, also copy `assets/music/V4V.OPL` to `DATA/MUSIC/V4V.OPL` in the playing copy.
See the short [installation guide](../README.md).

Earlier builds can be reconstructed from the individual patches; no fallback
executable is retained. The version-4 engine layer uses seven hardcoded slots
and manual REZ/AI swapping. Its implementation is documented below. Earlier-game
scenario formats must be converted/exported in the editor before playing.

## Patch files and reversal

Each layer has a forward `.ips`, inverse `.undo.ips`, and a `.json` manifest with
input/output and patch hashes. Apply layers in this order; undo in reverse order:

| Layer | Files | Result |
| --- | --- | --- |
| Engine fixes | `dday-weather-400.*` | Version 4: 400-turn weather/victory history and conditional HQ orders |
| Code space | `dday-code-space.*` | Adds 32 KiB of loaded LE code space; native selection still works |
| Scenario library | `dday-scenario-library.*` | Discovers SCNs, pages the existing panel, selects assets and preserves save identity |
| Presentation | `dday-presentation.*` | Selects scenario portraits, flags, emblems and turn pictures; refreshes cached flags |
| Custom artwork | `dday-custom-artwork.*` | Adds optional portraits selected by side and leader record |
| Advanced orders | `dday-advanced-orders.*` | Combines up to three conditions with ALL/ANY and saves persistent activation |
| Support artwork | `dday-support-artwork.*` | Loads scenario aircraft/naval pictures; refreshes the cached sheet; fixes initial category pictures and bounds extra air support |
| Game profiles | `dday-game-profiles.*` | Loads per-scenario victory ratios and adapted winter models from REZ |
| Terrain rules | `dday-terrain-rules.*` | Loads per-terrain movement/combat values and strategic road costs from REZ |
| Nested events | `dday-nested-events.*` | Nested ALL/ANY, one-time reinforcement releases/messages, reliable save footers; adds 20 KiB more LE code space |
| Startup selection | `dday-startup-selection.*` | Preselects SELECT.BAT's requested filename, assets and browser page |
| Background music | `dday-music.*` | Plays V4V FM music through Sound Blaster/AdLib; separate persistent Options toggle |
| Air weather repair | `dday-air-weather.*` | Fixes previous-turn weather reads in reconnaissance and air supply after the 400-turn expansion |

The engine layer retains its historical filename and bundled features. The twelve
additional layers are independent of that bundle and can be removed while preserving v4.
All earlier forward/inverse patches remain byte-identical. Undo air-weather, then music, then startup-selection, then nested-events
first, then terrain-rules, then game-profiles, then support-artwork, advanced-orders, custom-artwork and presentation to keep the scenario browser alone.
Readable sources are `dday-weather-400.asm`, `dday-victory-400.asm`,
`dday-scenario-library.asm`, `dday-advanced-orders.asm`, `dday-game-profiles.asm`,
`dday-terrain-rules.asm`, `dday-nested-events.asm`, `dday-startup-selection.asm`, `dday-music.asm`,
`lib/air_weather_patch.py`, and `lib/le_executable.py`.

```sh
# All layers, starting with the original (also accepts any verified intermediate):
python3 tools/patch_dday.py game/waw/dday/orig/INVADE.EXE --component all -o game/waw/dday/INVADE-PATCHED.EXE
# Remove the air-weather repair, retaining the previous music build:
python3 tools/patch_dday.py game/waw/dday/INVADE-PATCHED.EXE --component air-weather --reverse -o /tmp/MUSIC.EXE
# Remove music, retaining the previous startup-selection build:
python3 tools/patch_dday.py /tmp/MUSIC.EXE --component music --reverse -o /tmp/SELECT.EXE
# Remove launcher preselection, retaining the previous nested-events build:
python3 tools/patch_dday.py /tmp/SELECT.EXE --component startup-selection --reverse -o /tmp/NESTED.EXE
# Remove nested events, retaining the previous terrain-rules build:
python3 tools/patch_dday.py /tmp/NESTED.EXE --component nested-events --reverse -o /tmp/TERRAIN.EXE
# Remove terrain rules, retaining the previous game-profiles build:
python3 tools/patch_dday.py /tmp/TERRAIN.EXE --component terrain-rules --reverse -o /tmp/PROFILES.EXE
# Remove game profiles, retaining support artwork:
python3 tools/patch_dday.py /tmp/PROFILES.EXE --component game-profiles --reverse -o /tmp/SUPPORT.EXE
# Remove support artwork, retaining the previous advanced-orders build:
python3 tools/patch_dday.py /tmp/SUPPORT.EXE --component support-artwork --reverse -o /tmp/ADVANCED.EXE
# Then remove advanced orders, retaining the previous custom-artwork build:
python3 tools/patch_dday.py /tmp/ADVANCED.EXE --component advanced-orders --reverse -o /tmp/CUSTOM.EXE
# Remove individual leader portraits, retaining the previous presentation build:
python3 tools/patch_dday.py /tmp/CUSTOM.EXE --component custom-artwork --reverse -o /tmp/ARTWORK.EXE
# Then remove presentation support, retaining the original scenario browser:
python3 tools/patch_dday.py /tmp/ARTWORK.EXE --component presentation --reverse -o /tmp/BROWSER.EXE
# Remove all layers above the version-4 engine fixes:
python3 tools/patch_dday.py game/waw/dday/INVADE-PATCHED.EXE --component library --reverse -o /tmp/V4.EXE
# Restore the exact original, including original file length:
python3 tools/patch_dday.py game/waw/dday/INVADE-PATCHED.EXE --component all --reverse -o /tmp/ORIGINAL.EXE
# Apply/reverse just one layer (requires that layer's matching input):
python3 tools/patch_dday.py game/waw/dday/orig/INVADE.EXE --component engine -o /tmp/ENGINE.EXE
python3 tools/patch_dday.py /tmp/ENGINE.EXE --component code-space -o /tmp/EXPANDED.EXE
python3 tools/patch_dday.py /tmp/EXPANDED.EXE --component scenario-library -o /tmp/LIBRARY.EXE
python3 tools/patch_dday.py /tmp/LIBRARY.EXE --component presentation -o /tmp/ARTWORK.EXE
python3 tools/patch_dday.py /tmp/ARTWORK.EXE --component custom-artwork -o /tmp/CUSTOM.EXE
python3 tools/patch_dday.py /tmp/CUSTOM.EXE --component advanced-orders -o /tmp/ADVANCED.EXE
python3 tools/patch_dday.py /tmp/ADVANCED.EXE --component support-artwork -o /tmp/SUPPORT.EXE
python3 tools/patch_dday.py /tmp/SUPPORT.EXE --component game-profiles -o /tmp/PROFILES.EXE
python3 tools/patch_dday.py /tmp/PROFILES.EXE --component terrain-rules -o /tmp/TERRAIN.EXE
python3 tools/patch_dday.py /tmp/TERRAIN.EXE --component nested-events -o /tmp/NESTED.EXE
python3 tools/patch_dday.py /tmp/NESTED.EXE --component startup-selection -o /tmp/SELECT.EXE
python3 tools/patch_dday.py /tmp/SELECT.EXE --component music -o /tmp/MUSIC.EXE
python3 tools/patch_dday.py /tmp/MUSIC.EXE --component air-weather -o /tmp/FIXED.EXE
python3 tools/patch_dday.py /tmp/LIBRARY.EXE --component scenario-library --reverse -o /tmp/EXPANDED.EXE
# Rebuild IPS files and manifests from source; requires NASM:
python3 tools/build_dday_patch.py
python3 tools/build_dday_library_patch.py
```

The default component remains `engine` for compatibility with earlier commands.
`--component library` applies/removes all twelve layers above v4; `all` also
includes the engine fixes. Omitting `-o` patches in place with a `.bak` backup.
Explicit output refuses to overwrite different content. Fingerprints reject
unrelated modifications and incorrect component order. The new IPS files include
a three-byte target-length field after EOF, needed for exact truncation on undo;
use the provided applicator or an IPS utility supporting that extension.

The editor exports SCN/REZ/AI files, with an additional DATA/PCWATW.REZ when
startup screens are customized. It exports no executables, backups, launchers
or game-tree copies. No Python is needed on the playing PC.

Source SHA-256:
`d28ef2b0e8eea2f5b6bb7eb1e002d3621c770f7d94e9add7480caf14ca8df2ba`

Current complete build SHA-256 (including music and air-weather repair):
`5aaf34f932e3387f9529c885cf4016ca46c19b8db4abf60fa8e3c30323445f69`

Previous build SHA-256 (music version 2, before air-weather repair):
`07134f78e03e1cf5767f17d1778d20a615a89323c95147a4aca5cebaf26a1d34`

Previous build SHA-256 (startup selection, without music):
`a1a18e9a020c68d44ac10f276ce87e05144d3a8a0583eb4f29668fffa8e2906b`

Canonical version-4 SHA-256:
`9a220a34598a46d3fad3dba0a6724aaa77b827ddedbed908f2c17dd55e791b8b`

Original scenario-library executable SHA-256 (without presentation):
`6522caf334bc979d4f20e4d4e231c7a133048035b3593a9a356c03d2283a87ca`

Previous library executable SHA-256 (presentation version 1):
`8b8c0a242dee0687a457fcafb909c62d8d65ac2271c3105d0219d5367196bf75`

Previous library executable SHA-256 (custom-artwork version 1):
`4e0464e7f0fab1e49468a07acd47a0d86954e32e7352a6177858caf1a672e579`

Previous library executable SHA-256 (advanced-orders version 1):
`26023e77482cacbad5d431d537609252a17c0c294822bf85653fc467c577f0c7`

The earlier launcher customized title slots, making its engine hash differ.
Manual scenario swapping leaves the canonical patched executable unchanged.

## Binary changes

### Air reconnaissance / air-supply weather repair (October 9)

`dday-air-weather` fixes **“= BAD WEATHER IN RECCE =”** during movement
resolution. The original engine's `RepairFromMoveOut` calls `UpdateCalendar`
before resolving air supply and reconnaissance, so these routines intentionally
read the previous turn's cloud cover. Four instructions used `Weather + index
+ 0x213`, whereas the main weather expansion moved the cloud array from `+0x214`
to `+0x32c`. These biased reads were missed and could read temperature bytes as
cloud codes. Hell's Highway reproduces the error on its first movement phase:
the old read returns 53 (a temperature byte) instead of cloud code 1.

The repair changes the displacement to `0x32b` at code-object instructions
`0x220b`, `0x2247`, `0x78629`, and `0x78730`. These are the reconnaissance storm
gate and visibility penalty, supply-drop amount calculation, and air-resupply
storm gate. Only eight executable bytes change. Original night/storm restrictions,
weather penalties, and invalid-weather diagnostics remain in place. An audit of
all 71 LE relocations referring to the Weather pointer found no remaining reads
using the old cloud/flag offsets near those loads.

Rebuild this layer with `python3 tools/build_dday_air_weather_patch.py`, or use
the full library builder. Both preserve every earlier IPS/undo/manifest exactly.
The format of scenarios, assets and saves is unchanged; replace the playing EXE
and restart. There is no new data file and no need to re-export conversions.

`tools/test_air_weather_patch.py` reproduces the old error using MGHELL's actual
weather/calendar and native calendar increment. It checks both sides, all five
cloud codes, night/disabled-recon gates, supply amounts, negative temperatures,
late turns through the 400-entry boundary, and exact patch reversal. It also runs
native air-mission gates/calculations over every authored weather entry in all
43 packaged conversions and seven native D-Day scenarios, loading their weather
through the real patched loader.

DOSBox-X reproduced the original dialog after MGHELL's first execution phase.
With the repaired executable, the same scenario completed two execution phases
and reached turn 3 (2:00 PM) without the dialog. The six air-weather tests and
25 targeted engine/library/music/startup checks passed. A broader editor-format
test attempt hit two unrelated missing-template errors because those tests and
the New-scenario template lookup still expect `dday/SCENARIO`, while the staged
originals now live under `dday/orig/SCENARIO`; that lookup was not changed here.

### Original engine expansion

The code cave occupies 1,120 of the 1,120 zero bytes after code-object virtual end
`0xb2ba0`, file offset `0x1061f4`. The LE header's object size is extended within
its already loaded final page. No new pages, external loader or LE relocations
are needed. Global addresses are taken from existing relocated instructions.
The AWE sound-state zero region at `0xaca10` is not free code space and is untouched.

Four original routines are hooked: `RWWeather` (`0x27e1a`), `SetCalUTs`
(`0x2f834`), `ValidateWeather` (`0x2a35d`), and `SwapWeather` (`0x27dac`).
There are 47 verified weather-field operand edits, plus four hooks, the cave and
the LE object-size edit. Versions 2/3 add a fifth hook at the `bg_stuff` epilogue
(`0x67b55`). Version 4 adds 40 verified victory-field/size operand changes and
replaces the old SwapVictory/RWVictory region, for **95 edits total**. The cave
remains 1,120 bytes. Unrelated matching bytes are untouched.

| Weather data | Original offset/size | Extended offset/size |
| --- | --- | --- |
| Snow, ice, wetness | `0x000`, three int32 | same |
| Fahrenheit temperatures | `0x00c`, 260 int16 | `0x00c`, 400 int16 |
| Weather codes | `0x214`, 260 bytes | `0x32c`, 400 bytes |
| Ground/ice state flags | `0x318`, two bytes | `0x4bc`, two bytes |
| Absolute start/end timestamps | selected from seven executable cases | `0x4be`, two int32 |
| Total | 794 bytes | 1,222 bytes |

Native 794-byte blocks are expanded on load, preserving their original dates and
conditions. Saves always use the extended layout, so **new saves require the
patched engine**. The loader rejects unknown block sizes and date spans exceeding
400 entries. Existing native scenarios remain supported.

V4V conversions now contain their authored temperature/weather intervals and
original dates. Full VLCAMP retains all 393 inclusive timestamps. Dry initial
ground and D-Day's accumulation rules are an adaptation: V4V snow/ice seeds and
pre-scenario winter simulation have not been translated.

## Validation

`tools/test_dday_patch.py` executes the actual patched x86 with Unicorn at two
relocated load addresses. It covers every native scenario's load/save/reload,
original and extended weather validation, callee registers/stack, guarded
allocations, invalid block sizes/date ranges, and original weather arithmetic at
indexes 260 (rain) and 392 (snow). Patch hashes, idempotence and exact reversal
are also checked. Unicorn is optional for normal editor use, required for these
machine tests.

The Python/Tk suite includes authoring, condition, library, and machine-code
regressions. Four optional tests depend on removed `extracted_images` fixtures. Run with:

```sh
xvfb-run -a python3 -m unittest discover -s tools -p 'test_*.py' -q
```

Actual DOSBox-X results are recorded below. They are targeted loading, weather
and save checks, not a full campaign playthrough or a claim of gameplay balance.

DOSBox-X 2025.02.01 (SDL2), `core=normal`, `cycles=fixed 50000`, 32 MB RAM,
SVGA S3, surface output, IRQ 5 and audio muted for headless testing:

- **Native Bradley:** loaded, saved, and resumed successfully. Its game-written
  `PATCHNAT.SAV` contains a 1,222-byte weather block and native dates
  97392–97409. Reloaded map (local `validation/native-reloaded.png`).
- **Converted VLCAMP:** loads to the full 393-turn map and saves successfully with
  **Local Human Opp.** selected. `VLSTART.SAV` retains dates 93950–94342 and all
  authored weather entries. Initial map (local `validation/vl-start.png`).
- **Late-weather fixture:** advanced the calendar in a copy of VLSTART.SAV to
  weather index 260 (December 28, turn 261), preserving the original weather.
  DOSBox-X loaded it and displayed late weather in the calendar. Committed both
  human sides, executed one turn, and saved at index **261**, displayed turn 262.
  Weather display (local `validation/vl-weather-260.png`),
  game after execution (local `validation/vl-turn-262.png`).
- **Final weather entry:** loaded a second calendar-advanced fixture at index
  **392**, displayed turn **393 of 393**, opened its January 19 calendar, and saved.
  Final-entry display (local `validation/vl-weather-392.png`). The game-written save still
  contains all 400 slots and the correct end timestamp.

These calendar-advanced fixtures test addressing and save behavior; they do not
represent a played campaign. Units and combat state remain from the initial save.
New-game testing also found and fixed the converter's empty terrain-edge table,
HQ parent/active state and supply-table offsets (see the conversion notes).

**Resolved conversion error:** the earlier VLCAMP computer-planning failure
(historical capture (local `validation/vl-ai-odds-error.png`)) comes from
`attack_odds_into_hex` (`0x802e`). It rejects a target whose hex owner equals the
attacking side; the executable's literal message is `Latt odds error`.
The converter had zeroed all territorial ownership and stacking bits, and
`InitUnitMap` (`0x31420`) consequently loaded no unit stacks. Version 4 conversions
retain source ownership (bit 16) and rebuild stacking (bits 17–20) from the active
ground roster. Zone-of-control influence is then recalculated by D-Day.
Unit stacking sizes also now follow V4V `1845:0432`: one point when source
`+0x5e == 1`, otherwise three. The earlier universal 255 value was an HQ sentinel
that D-Day interpreted literally for non-HQs. All 27 documents were regenerated.
The combat-odds check remains intact; no additional executable patch was needed.

**Retest with the corrected conversion:** selected the computer opponent in
VLCAMP, allowed Axis planning to finish, executed the first turn, and saved
`VLAIFIX.SAV` at displayed turn 2 (timestamp 93951). Resumed that save and executed
another turn. The game reached turn 3 with Axis planning committed and no odds
error. The save contains 129 occupied hexes, rather than the earlier empty map.
Resumed turn 2 (local `validation/vl-ai-fixed-reloaded.png`),
turn 3 after execution (local `validation/vl-ai-fixed-turn3.png`).
This checks opening AI planning, turn execution and save/reload, not a full campaign.

Earlier `VLSTART`, `VL260` and `VL392` saves contain the old empty occupancy data;
they remain weather-test fixtures, not suitable starting points for playing.
Start a new game from the refreshed conversion to get the corrected state.
Other scenarios have
structural tests, not comprehensive DOS playtests. Winter accumulation, AI,
victory thresholds and balance still differ from V4V. These historical checks used native D-Day flags, mini-maps and banners.
The new library exports generate map previews and banners; flags remain native.

The current editor can run without `extracted_images` using the staged D-Day
resource and `assets/terrain`; that old folder can be deleted. Legacy research
scripts and the four optional image-fixture tests still reference it.

Session hashes and saved weather values (local `validation/session.json`) record the
produced saves. These validation saves were removed during runtime cleanup;
their hashes, recorded values and screenshots remain as test evidence.

The earlier `scenario_player.py` launch path was tested through the DOS menu;
a concurrent prepare was refused while its game session held the runtime lock.
That temporary runtime was subsequently deleted. The editor now exports files
for manual installation instead of offering a Play menu.


## Victory history extension (version 4)

The weather extension alone was insufficient for long converted campaigns.
`UpdateVicHistory` (`0x52fe5`) indexes the score history by elapsed turn without
bounds checks. Native history has 260 int16 entries per side; turn 261 would
write into the other side's totals and beyond the allocation. This affects
long V4V conversions and newly authored scenarios beyond 260 turns. Stalingrad's
campaign retains its native 189-turn, three-turn-per-day calendar.

Version 4 expands each side from 544 bytes to **824 bytes**: six int32 totals
followed by 400 int16 history entries. The complete Victory block becomes
**1,648 bytes**. All verified runtime references to the side stride, Axis history
offset and reset lengths are updated, including casualty-based AI conditions.
Scoring formulas and victory-tier thresholds are unchanged.

`dday-victory-400.asm` occupies code `0x27770–0x27928`, formerly SwapVictory and
RWVictory. DOS never invoked the old endian-swap path. The replacement keeps
the callable RWVictory entry at `0x27808` and all five LE-relocated operand cells
at their exact original locations. It accepts native 1,088-byte or extended
1,648-byte blocks, moves the native Axis record safely, and zeroes new history.
Saves always write the extended block. Native scenarios and older saves remain
loadable; **saves made by v4 require v4**. The editor reads both layouts.

`tools/test_victory_patch.py` executes the real replacement at two code/data load
addresses, verifies the actual LE fixup cells, load/save/reload compatibility,
invalid-size rejection, separate side totals, heap guards, and history writes
through turns 260, 261, 378 and 400. The native casualty-scoring/conditional-AI
regression also runs against the expanded layout.

## Authored HQ battle plans and conditions (introduced in version 3)

This section describes the unchanged v3/v4 single-condition format. The current
library also supports [combined conditions and persistent activation](#combined-conditions-and-persistent-orders).

Scenario Settings → Battle Plans edits inclusive turn phases for an HQ’s assigned
units, optionally conditioned on objective control or cumulative casualty points.
Plans have priorities; the highest matching priority wins. Overlaps at the same
priority for the same HQ are rejected. Conditions follow current saved game
state and are rechecked whenever the AI asks for orders; they are not one-shot
events. An objective-based order can stop applying after recapture.

The `.SCN` stores plans in an ignored trailer. Timed-only plans retain the old
16-byte `WAWAI001` records. Conditions/priorities use 24-byte `WAWAI002` records.
`.AI` exports always contain 16-byte rows ordered by decreasing priority. Low
bytes of scenario, side and HQ preserve their original selectors. The high
scenario byte is 0 for timed, 1/2 for Allied/Axis objective control, or 3/4 for
Allied/Axis losses. The side/HQ high bytes store a little-endian 16-bit argument:
objective index or casualty-point threshold (1–65535). Remaining fields are
first turn, last turn, order, X and Y as before. Version 2 compares the full
scenario word and skips conditional rows instead of applying them unconditionally.
The cave reads `WAWAI.DAT` from the game root, with a 256-row limit. It preserves
native behavior when the file is absent, empty, mismatched, or out of range.
Copy an empty exported AI file when returning to an unscripted scenario.

The engine reassigns dynamic battlegroups around objectives in ForceAllocation2;
the authored selector is therefore OB+0x81 (assigned HQ), not +0x82 (dynamic BG).
The hook runs at the end of bg_stuff, replacing its returned order and destination
for a matching phase. Existing pathfinding, fatigue, tactical decisions and combat
continue to apply. Supported orders are advance, retreat, surround, idle and stay.
It is not an arbitrary event or executable-code scripting system.

Objective tests read VicLoc+17 (current owner) after checking the index against
Scenario+0x1222. Losses suffered by side S read Victory[(1-S)*824+20] in v4
(the native/v3 stride was 544), the
opponent's accumulated casualty score in thousandths; this is the field updated
by `KIAVicPen` (+0x52d49). The threshold is multiplied by 1000. Total victory
and objective points do not enter this test. Zero casualty weights consequently
do not advance the associated casualty score. Native scoring/combat formulas
and victory-tier constants remain unchanged.

`tools/test_scenario_conditions.py` executes the hook at two relocated addresses,
checking dates, sides, HQ assignment, coordinates, missing files, output fields,
stack restoration and volume restoration. The DOSBox-X smoke scenario reached
turn 2 with storm/42°F weather and edited supply, and its Axis units kept their
starting hexes under a Stay phase despite receiving a different dynamic BG ID.
After switching to an Advance phase, infantry moved toward its goal by turn 4.
Those initial timed-order DOSBox checks were made with version 2.

`tools/test_conditional_ai.py` checks both sides, capture/recapture, exact loss
boundaries, priority fallback, missing/malformed conditions, live score selection,
and output/register/volume preservation. It executes native `KIAVicPen` to verify
that combat casualty points drive the loss condition. Editor tests cover both
trailer formats, protected/remapped objective references, Apply/Undo/Save/reload,
date/duration changes and matching SCN/AI exports.

DOSBox-X conditional-order smoke check (2026-10-06): an authored 16×12 scenario
used an Axis Stay order while Axis controlled Crossroads, with a lower-priority
Advance fallback. At turn 2 (97400), all four Axis units remained at their
starting hexes. The game saved and resumed successfully. For a controlled
recapture test, the saved objective owner and corresponding map ownership were
changed to Allied, then the save was resumed. At turn 3 (97401), Axis infantry
and armor moved from (5,9)/(6,9) to (5,6)/(6,6) under the Advance fallback.
The final canonical build also resumed that save and advanced to turn 4.
This tests live condition selection and Save/Resume, not a full campaign or
natural capture sequence. Loss-condition validation executes native casualty
scoring and the actual patched hook in Unicorn.

These engine fixes are included in the current complete `INVADE-PATCHED.EXE`.
The original `INVADE.EXE` remains byte-identical. The patch utility rejects the
older patched hashes; use the original as input or copy the new build.

## Earlier WaW conversion checks (version 4)

The editor/converter regression run on 2026-10-06 completed **222 tests: 218
passed, 4 skipped**. All 16 staged earlier-WaW documents and their saved terrain/
chit companions match the final converter; original source hashes are unchanged.
The unit library contains 15,401 templates across the 50 staged game scenarios.

DOSBox-X checks used a temporary playing copy outside the repository:

- Crusader **Il Duce's Finest** loaded, executed combat/movement and reached
  turn 2. It exposed numeric place-name styles incompatible with D-Day; the
  converter now translates them to its equivalent `V` color before export.
- Stalingrad **Rattenkrieg** loaded with 459 units, reached turn 2, wrote a
  1,648-byte victory block, and resumed that saved game successfully using v4.
- Stalingrad **Operation Uranus** loaded all 1,106 units, including the packed
  counter sheets, executed combat/movement to turn 2, saved, and resumed in
  planning. Its three-turn daily calendar and original 189-turn duration are
  retained: the saved timestamp advanced from 46986 to 46987 (November 19,
  1942, noon), with a 1,648-byte victory block. The native D-Day date routine
  is also executed in regression tests for both three-turn and six-turn scales.

These are smoke checks, not complete campaign playthroughs or balance tests.
All source-unit/leader chits are pixel-checked; terrain substitutions and other
engine adaptations are listed in [WaW conversion notes](../../../txt/WAW_CONVERSION.md).

## Runtime scenario library (version 1)

The optional startup-selection layer reads `WAWSTART.TXT` in the game directory
after discovery. SELECT.BAT writes one DOS SCN basename (with CRLF). The reader
accepts a bounded 8.3 name with optional LF/CRLF, compares it case-insensitively
against discovered filenames, activates its matching REZ/AI/profile and opens
the correct five-row page. No file means the existing first-playable default.
An explicit malformed, missing or unloadable request displays an error and
exits instead of silently choosing another battle. Saved-game identity takes
precedence when resuming; the startup request does not rewrite saves or slots.
The batch deletes the hint after the game exits. If DOSBox was forcibly closed,
the next SELECT launch replaces it; deleting it restores the direct-launch default.
This layer adds no LE pages and uses 376 more bytes of the reserved code area.
Earlier patch artifacts are unchanged and its inverse restores the exact prior
build. `tools/test_startup_selection.py` executes these cases at relocated x86
addresses, including companion failures, paging, profiles and cold save resume.
DOSBox-X also verified VLFORT's selected title, briefing and playable Velikiye
Luki map, followed by return to the batch menu and hint cleanup. Selecting native
Cobra next restored its title, briefing and artwork. The combined library,
profile, terrain, event, support-unit and startup-selection checks passed 82 tests.

The library patch reuses the existing **Scenarios** panel. Its code contains
seven fixed controls, not a variable-length list. The patch supplies **Previous**,
five scenario rows, and **Next**, retaining the native selection, briefing,
preview and Begin New Game controls. There is no popup scenario picker.

It enumerates `SCENARIO\*.SCN` once per process with the existing Watcom
`_dos_findfirst`/`_dos_findnext` calls, checks the D-Day header/version/native ID,
and sorts by DOS filename. Capacity is 256; reaching it displays a notice.
Missing required companions prevent selection without changing the current
scenario. Restart after changing the directory. A readable header is not full
scenario validation: export valid editor documents, not arbitrary binary files.

Native scenario IDs 0–6 still control engine rules and compatibility tables.
The file-list index is separate. Selecting a row changes the selected ID's entry
in the native filename table, so both ReadScenarioData and StartNewGame open the
chosen filename, even when many exports share the same ID. Fixed original names
and titles are retained separately for legacy fallbacks.

A scenario REZ is opened as a resource overlay. Terrain, counters and scenario
preview/title PICTs come from it; core fonts, dialogs, menus and other UI resources
stay in the original base resource map. Replacement overlays are opened before
the previous map is freed. Native bitmap initialization rebuilds terrain/counter
caches for new games and resumed games. Authored AI opens `SCENARIO\NAME.AI`
instead of the root `WAWAI.DAT`, preventing orders from another installed scenario
with the same native ID from being reused. All three exported companions should
remain together, including an empty AI file for an unscripted scenario.

### Export and saved identity

Export appends a 64-byte `WAWLIB01` footer to the SCN. New library saves append
the same footer after native game data. Fields are: magic (8), DOS filename (13),
display title (27), flags (uint32), reserved zero (uint32), repeated magic (8).
Flag 1 requires REZ and AI companions. Strings are terminated; titles use CP437
and at most 26 bytes. Battle-plan trailers precede this footer and remain editable.
The old v4 engine ignores the footer, retaining binary compatibility.

Discovery uses the actual filesystem filename when an export is renamed; rename
its companions too. Saves retain the selected basename and reopen its assets in
a fresh process. Existing saves without a footer fall back to the original
filename corresponding to their native ID. Older converted saves are ambiguous;
use the v4/manual-swap workflow or supply their correct companions under that
native basename. A library save with missing required assets refuses to resume
and exits the game rather than loading incorrect artwork/orders.

Exports generate PICT 144, 145+ID, 4500+ID and 4600+ID from the map/title: selection
preview, mini-map, overview and banner. The presentation layer additionally routes
PICT 251 (toolbar flags), 560/561 (nationality flags), 730/731 (emblems), 780/781 (turn pictures) and
1100–1103 (popup busts) to the scenario REZ. Other D-Day UI artwork is unchanged.
Older SCNs without metadata show their filename
stem (or original D-Day title); native files without REZ companions use base art.

### LE expansion

The code object formerly ended at relative `0xb3000`, preferred base `0x10000`.
The next object begins at `0xd0000`, leaving a 52-KiB address gap. We insert eight
4-KiB pages within that gap: code now ends at `0xbb000`, leaving 20 KiB spare.
The existing 328 bytes of header-table padding accommodates the larger page map
and fixup-page table. Module pages increase from 196 to 204; subsequent object
page indexes increase by eight. New fixup-page entries are empty. Existing fixup
records, object numbers, in-object offsets and original code/data bytes survive
unchanged. The code object becomes writable because the new pages include state.
File data after old code shifts 32 KiB, including the unchanged trailing debug data.

The library uses position-independent calls and reads an existing LE-relocated
operand to find the data object. No new relocations are required. Eight verified
hooks cover initial preview, selection, panel initialization, labels, resource
routing, save/resume identity and the authored-order file open. The builder checks
prologues/calls and bounds; tests ensure no hook overlaps an existing fixup cell.
The final implementation occupies about 25 KiB of the 32-KiB extension.

The LE field definitions are in Open Watcom's
[exeflat.h](https://github.com/open-watcom/open-watcom-v2/blob/master/bld/watcom/h/exeflat.h).

### Library validation

`tools/test_scenario_library.py` applies the actual LE fixups and executes the
new machine code at two code/data load addresses. It checks discovery, invalid
headers, sort/paging, 256-entry bounds, selection with shared native IDs, renamed
files, companion failures, resource-map rollback, font/terrain routing, per-file
AI, filename persistence and cold resume. It also checks metadata/plan coexistence,
generated artwork, IPS growth/exact reversal and all existing relocation records.

DOSBox-X smoke checks use a temporary playing copy outside the repository:
21 installed SCNs were paged in the existing panel; native Bradley, Crusader
Il Duce's Finest and Stalingrad Rattenkrieg previews were selected in one session.
Crusader started with its exported terrain/chits/banner, saved, and resumed in
a fresh process after selecting Stalingrad in the menu. The final build also
started Rattenkrieg, executed combat/movement to turn 2, and wrote both manual
and automatic saves identifying `BCITY.SCN`, with a 1,648-byte victory block.
Resuming the Crusader save directly from that Stalingrad session restored its
desert terrain and chits. These checks supplement the machine-code tests;
they are not full campaign playthroughs.

Final library regression run (2026-10-06): **233 tests, 229 passed and 4 optional
image-fixture tests skipped**. Both builders are reproducible. Full reversal
returns the original executable byte for byte and removes the extra 32 KiB;
removing only the library/expansion layers returns the unchanged v4 executable.
The shipped `INVADE-PATCHED.EXE` matches the final DOSBox-tested binary.

### Presentation artwork (version 1)

The Artwork page's portraits, nationality flags, side emblems and turn-screen
pictures are included in the scenario's existing REZ export. The optional
`dday-presentation` layer extends resource routing without replacing fonts,
dialogs, menu decorations or startup logos. Four popup portraits are selected
by side/message context, not by a named leader record.

`InitGameBits` caches PICT 560/561 in buffers 16/17. Successful scenario
activation reloads those two buffers and toolbar buffer 11 (PICT 251) with `LoadAPict`, including when switching
back to an original SCN with base artwork or resuming a saved game. Missing
companions leave the previous artwork/cache intact; early startup skips buffers
that have not been allocated yet. Other supported pictures load on demand.
All exported resource headers, strides and dimensions remain native.

The original presentation build assembles `dday-scenario-library.asm` twice:
the original build is unchanged, and `PRESENTATION=1` adds artwork support. The
builder writes a separate forward/inverse presentation patch between those
two binaries. The augmented library occupies 25,632 of the reserved 32,768
bytes; it needs no further executable expansion or relocations.

Tests in `tools/test_presentation_artwork.py` cover palette/alpha conversion,
resource isolation, both flag sizes, portable saves and rollback, Tk history and
Save As, DOS exports, x86 resource routing, cached-flag refresh, failed selection,
base-art restoration and cold resume. Portraits/emblems/turn pictures use opaque
DrawPicture rendering; imported alpha is composited onto their native background.
Flags retain index-zero transparency. Native portrait white pixels stay opaque.
`InitTBarButts` rebases the cached toolbar to screen coordinates; the presentation
refresh temporarily resets its origin before loading the sheet, then restores
both the original origin and the caller's port. This is covered by the machine
test so resuming cannot paste the sheet at the wrong offset into its own cache.

DOSBox-X smoke check (2026-10-06): an exported Bradley scenario displayed the
Crusader Allied popup bust, British territorial and toolbar flags, and the Crusader
Allied emblem. The scenario was saved, then resumed in a fresh DOSBox process
after selecting original Bradley; its custom pictures and both flag caches were
restored, with the rest of the toolbar correctly aligned. The original and
exported scenarios were selectable in the same session.
Testing used a temporary playing copy outside the repository. The original
engine, v4 fallback, code-space IPS and original scenario-library IPS are unchanged;
reversing only presentation restores the browser-only hash above exactly.

Final presentation regression run: **252 tests, 248 passed and 4 optional
image-fixture tests skipped**. The rebuilt executable matches the DOSBox-tested
copy. Full reversal restores the original bytes; presentation-only reversal
restores the unchanged scenario-browser executable.

### Individual leader portraits (custom-artwork version 1)

The builder now makes a third assembly with `PRESENTATION=1` and
`CUSTOM_ARTWORK=1`, producing a separate `dday-custom-artwork` forward/undo
patch on top of the unchanged presentation build. It occupies 26,060 of the
reserved 32,768 bytes, without additional LE pages or relocations.

The editor adds PICT **12000 + side×128 + leader index**, only for assigned
portraits. Each is a 37×35 palette bitmap. The resource writer preserves
existing payloads, names and attributes while rebuilding the type/reference
map; it does not repurpose opaque leader fields. Leader removal reindexes
portrait assignments with the remaining records, including through undo/redo.

The hook at code **0x2ee34**, the final ResetPenColor call in DrawLeaderSideBar,
selects the displayed side (PMode) and CurrentLeader. It probes map 1 before
GetResource so an absent portrait does not trigger a resource error. The
portrait replaces the nationality flag at SBRect+(4,123), retaining the name,
chit, buttons and combat ratings. When a previous portrait is present, the hook
clears its rectangle and restores the current leader's flag before looking up
the next portrait; native transparent flag blits alone leave stale pixels.
The caller's resource-map selection and saved registers are restored.

Terrain and ground-chit imports use the existing resource routes and need no
additional engine code. Startup splashes (PICT 132, 141, 740) are global and
export in a separate DATA/PCWATW.REZ: they load before scenario selection.
The animated Atomic logo and About animation remain unchanged. Individual
portraits are the only feature requiring this additional patch layer.

Validation (2026-10-07): **275 tests, 271 passed and 4 optional image-fixture
tests skipped**, plus a targeted startup-default restoration check. The machine
tests exercise side/index lookup, absent portraits, stale-image clearing,
resource routing and relocated code/data bases. DOSBox-X displayed an exported
startup image and a custom leader portrait with the original controls and
combat ratings intact; stepping to a leader without a portrait restored the
flag. Testing used a temporary playing copy outside the repository.

The custom-artwork build matches that DOSBox-tested binary. The builder
reproduces it, and custom-artwork-only reversal returns the previous presentation
hash exactly; full reversal returns the original executable. Original game files,
the v4 fallback, and all earlier IPS/undo layers remain unchanged.

## Combined conditions and persistent orders

`dday-advanced-orders` version 1 extends the authored HQ order patch with up to
three objective/loss checks per plan, combined using ALL (AND) or ANY (OR).
The optional **Keep active after first matching order** setting remembers when
a plan actually supplies an order. Thereafter it remains eligible for every
assigned unit of that HQ until its last turn, even if the trigger clears.
Higher priorities still win. An order preempted by another plan has not
activated yet. Conditions are evaluated on native AI order requests, not by
an immediate capture callback. This extension does not introduce arbitrary
event actions, nested expressions, or an original-game scripting facility.

The builder assembles `dday-scenario-library.asm` with `ADVANCED_ORDERS=1`,
including `dday-advanced-orders.asm`. Earlier layer builds omit the define and
remain byte-identical. The new layer hooks `bg_stuff` at `0x67b55`, retains native
tactical mode, and delegates legacy files to the unchanged v4 AuthoredAI cave.
It also extends the existing load/save identity hooks. The complete extension
uses 27,680 of the 32,768 added code bytes; no further LE growth is needed.

The editor stores advanced plans in a `WAWAI003` trailer: normalized compact
JSON, its little-endian uint32 byte length, then the eight-byte signature.
Unknown trailer data and the library identity are preserved. Documents without
advanced plans keep their previous binary `WAWAI001`/`WAWAI002` representation.

DOS export switches the entire `.AI` to this format when any plan is advanced:

- 32-byte header: `WAWAI003`, uint16 row count (1–256), uint16 stride (32),
  a 128-bit BLAKE2s fingerprint of the exported rows, a `0xffff` guard and
  reserved zero word. Fingerprint bytes 0–3 occupy header offsets 12–15;
  bytes 4–15 occupy offsets 18–29; the guard is at 16 and reserved word at 30.
- Rows are sorted by descending priority. Each starts with the original eight
  uint16 order fields, with scenario high byte `0x80` or `0x81` (persistent).
  Offset 16 is `0xffff`; offsets 18/19 are mode (0 ALL, 1 ANY) and condition
  count (0–3). Three four-byte slots follow: kind byte, side byte, uint16
  argument (objective index or casualty threshold). Unused slots are zero.
- The engine checks the header, exact file size, every condition, turn/goal
  bounds and allowed orders. It compares the exported header with the one
  loaded for the active game. The fingerprint is generated by the exporter;
  the engine does not recompute BLAKE2s on each order request.

The guards make every old 16-byte interpretation unmatchable or unsupported.
Older engines therefore ignore the entire advanced file, including simple
fallback rows. Use the current library executable for these exports.

SaveGame appends an 80-byte `WAWEVT01` state block immediately before the
existing 64-byte `WAWLIB01` identity: eight-byte signature, the 32-byte AI
header, 32 activation bytes (one bit per sorted row), and an eight-byte closing
signature. Fresh games clear the flags. Resume restores them only when the
installed AI header matches; a mismatch rejects the load with an explanation.
Keep the matching `.AI` with saves, or start a new game after changing plans.
Older saves without this state start unlatched. Native SCN/SAV block formats
remain unchanged; the extra bytes are ignored by older engines.

`tools/test_advanced_orders.py` covers document round trips, undo/redo, Save As,
DOS export, objective references, ALL/ANY, priority preemption, all HQ members,
expiry, both relocated memory layouts, 256-plan capacity and the final activation bit, fresh starts,
cold Save/Resume, changed rules and malformed data. It executes the actual
assembled x86 hooks under Unicorn, mocking DOS and resource services. The
full regression run completed 285 tests, with four optional-fixture skips.

DOSBox-X smoke check (2026-10-07), in a temporary playing copy: a 16×12 scenario
gave the Axis HQ a persistent Stay order requiring Axis control of both
Crossroads and Bridge, above an Advance fallback. At turn 2 (97400), all four
Axis units stayed in their starting hexes and the native save contained flag 0
set in `WAWEVT01`. A controlled fixture changed Crossroads ownership and its map
hex to Allied in that save, leaving the activation bit intact. After a cold
restart and Resume, turn 3 (97401) retained all four positions and saved the
flag again. An otherwise identical fixture with the activation bit cleared
took the fallback: infantry/armor advanced from (5,9)/(6,9) to (5,6)/(6,6),
and the flag remained clear. This checks combined-condition rejection and
persistence through the real game loop, native save writer and cold resume.

Before the support-artwork extension below, `INVADE-PATCHED.EXE` was that tested advanced-orders binary. A source
rebuild reproduced every existing forward/undo patch and manifest exactly.
Removing advanced-orders restores the previous custom-artwork hash; full undo
restores the original file. The original executable, v4 fallback and staged
game assets remain unchanged.

## Aircraft and naval support artwork

`dday-support-artwork.ips`, `.undo.ips` and `.json` form a separate layer after
advanced orders. The current `INVADE-PATCHED.EXE` includes it. This layer:

- Routes PICT 131 to the selected scenario's REZ and reloads cached buffer 13
  on selection/resume, including a return to the default graphics.
- Corrects the first displayed category picture when empty categories are
  skipped on opening the aircraft/naval panel.
- Caps the optional extra-air-support bonus at the category's actual roster
  count. Custom rosters with a single squadron no longer trip the old assertion.

The final source rebuild occupies 27,904 of the 32,768 added code bytes. No
additional binary growth or native record-format change is needed. Its SHA-256 is
`b5bc1230f810246d70c8a1cbbe1e22fff9d36561347a1081191073cfcd5812ea`.
Reversing only this layer restores advanced orders exactly:
`26023e77482cacbad5d431d537609252a17c0c294822bf85653fc467c577f0c7`.
Earlier patch layers and the original INVADE.EXE remain unchanged.

Validation: 102 targeted unit/support/artwork/library/advanced-order tests pass,
including native x86 category consumers and the assembled cache-refresh and
selection hooks. DOSBox-X loaded edited COUNTER aircraft/naval categories,
displayed their scenario artwork, saved them and restored the custom cruiser
picture correctly on a cold resume with the final executable. This is a
load/UI/save/resume smoke test, not a complete campaign test.
See [aircraft/naval format notes](../../../txt/AIRCRAFT_AND_NAVAL.md).

## Game profiles

`dday-game-profiles.ips`, `.undo.ips` and `.json` are an independent layer after
support artwork. The current `INVADE-PATCHED.EXE` includes it. It loads per-scenario
victory ratios and winter coefficients from the matching REZ and replaces
`GetVicLevel` and `CalcSnowIceWetness`. D-Day defaults preserve native results;
Stalingrad and V4V winter models use adapted thousandth arithmetic. Older
unported combat, movement, supply and scripted behavior remains D-Day's.
See [profile formats, source evidence and limitations](../../../txt/GAME_PROFILES.md).

The game-profiles build before terrain rules uses 28,988 of 32,768 added bytes, with SHA-256
`db42792cec90d4dd7e1b1190040e907ada04062717b65941018bb68a943f8029`.
Reversing only `game-profiles` restores the support-artwork binary exactly:
`b5bc1230f810246d70c8a1cbbe1e22fff9d36561347a1081191073cfcd5812ea`.
Earlier layers and the v4 fallback remain unchanged. For example:

```sh
python3 tools/patch_dday.py game/waw/dday/orig/INVADE.EXE --component all -o /tmp/INVADE.EXE
python3 tools/patch_dday.py /tmp/INVADE.EXE --component nested-events --reverse -o /tmp/TERRAIN.EXE
python3 tools/patch_dday.py /tmp/TERRAIN.EXE --component terrain-rules --reverse -o /tmp/PROFILES.EXE
python3 tools/patch_dday.py /tmp/PROFILES.EXE --component game-profiles --reverse -o /tmp/SUPPORT.EXE
```

Validation (2026-10-07): 92 targeted profile/history/authoring/conversion/assets/
weather/library/advanced-order/support tests passed. Runtime tests execute actual
assembled code under Unicorn; the Stalingrad winter comparison also runs the
original Stalingrad machine code. Rebuilding reproduced every forward/undo patch
and manifest exactly, and full reversal restored the original executable.

DOSBox-X, in a temporary playing copy, loaded a 16×12 scenario with the Stalingrad
profile and heavy snow at 20°F, advanced to turn 2, and wrote a native save with
snow 800, ice 1067, wetness 0 and the profile-required identity flag. Native
D-Day would leave ice unchanged. This confirms profile loading, gameplay updates
and the native save writer. After a cold restart and Resume, advancing to turn 3
produced snow 1200, ice 1390, wetness 0 in both manual and automatic saves.
This is a load/play/save/resume smoke check, not a campaign balance test.

## Terrain rules

`dday-terrain-rules.ips`, `.undo.ips` and `.json` form an independent layer after
`game-profiles`. The current `INVADE-PATCHED.EXE` includes it. The editor's
**Game Profile → Edit Terrain Rules** controls dry/light-mud costs for each
terrain/movement class, strategic road costs, defense/anti-armor multipliers,
and bombardment received. Original movement/combat algorithms, crossing costs,
fortifications and supply calculations remain. See [format, controls, native
addresses and limits](../../../txt/TERRAIN_RULES.md).

The terrain-rules build, before nested events, uses **31,788 of 32,768** added code bytes. Its SHA-256 is
`5fcdad3599a7ad9c865e83906adce1dc5ed9b021dc87fd915fad681dd516faf5`.
Reversing only `terrain-rules` restores the previous game-profiles binary exactly:
`db42792cec90d4dd7e1b1190040e907ada04062717b65941018bb68a943f8029`.
Every earlier patch remains byte-identical; original `INVADE.EXE` is unchanged.

Validation (2026-10-07): **76 targeted tests passed**, including actual native
x86 arithmetic/AI consumers, per-scenario switching and cold resume, malformed
rule rejection, editor drafts/history/save/export, and earlier profiles,
secondary orders and supply/transport regressions. Rebuilding reproduced all
patch files/manifests and the installed library binary exactly. Full reversal
restored the original executable byte-for-byte.

DOSBox-X tested identical 16×12 scenarios with the same plotted infantry route:
with native Clear cost 1 MP the unit moved from `(6,3)` to `(9,3)` in the first
turn; with authored Clear cost 2 MP it moved to `(7,3)`. Native saves preserved
the terrain-required scenario identity. A cold Resume followed by another turn
and save matched the uninterrupted run's infantry position and movement balance.
These are runtime smoke checks, not campaign balance testing.

## Nested conditions and one-time event actions

`dday-nested-events.ips`, `.undo.ips` and `.json` are an independent layer after
`terrain-rules`. The current `INVADE-PATCHED.EXE` includes this layer. It supports
nested ALL/ANY objective/loss conditions, persistent HQ orders, one-time release
of pending HQ reinforcements, and public messages. Optional holds keep those
reinforcements unavailable until release. Native arrival routines still place
them at their existing entry locations. Combat/victory algorithms are unchanged.

The builder defines `NESTED_EVENTS` only for the new layer and includes
`dday-nested-events.asm`. Earlier layers continue to reproduce exactly. This layer
adds five more LE pages (20,480 bytes), for 53,248 added bytes total, and consumes
34,172 of them. The new code-object size is `0xc0000`; the next object's address
and all original relocation targets remain unchanged. Three new call hooks handle
fresh-start actions, turn-end actions and scenario-message drawing. The save hook
also truncates overwritten saves at their new EOF, preventing stale event-state
footers after orders/other variable data shrink.

The authoring/runtime format is `WAWAI004`. Runtime rows use bounded postfix
expressions and guarded 320-byte records; older AI parsers cannot interpret their
payload as orders. Activation uses the existing fingerprinted `WAWEVT01` save
extension. The same SCN/REZ/AI export/install workflow applies. See
[controls, formats, native addresses and limits](../../../txt/NESTED_EVENTS.md).

Current library SHA-256 (`nested-events` version 1):
`38b70bd385954baf8d308a2ddea029d1ed5ab2c4bd94c5ac5362982e706285b5`.
Undoing only this layer restores the previous terrain-rules binary exactly:
`5fcdad3599a7ad9c865e83906adce1dc5ed9b021dc87fd915fad681dd516faf5`.
Original `INVADE.EXE` and the v4 engine patch remain unchanged.

Validation (2026-10-08): **91 targeted tests passed** across nested/advanced
orders, library loading, terrain/game profiles, map/formation copies, scenario
conditions/data and unit roster operations. Tests execute assembled x86 at two
relocated bases, check nested truth tables, activation priority, one-time release,
held dates, message pagination, malformed files, save overwrite/cold resume,
editor drafts/history/save/export, and native hook/fixup boundaries. Source rebuild
reproduced all patch files/manifests and the installed binary. Independent undo
restored the terrain-rules hash; full undo restored the original executable.

DOSBox-X checks used a temporary playing copy and actual native saves. Two ground
reinforcements scheduled for turn 2 were held beyond scenario end, released by a
nested objective condition on turn 3, and appeared via native arrival processing
on turn 4. The message fired once. A cold Resume advanced to turn 5 without
repeating either action; changed arrival dates and both activation bits persisted,
with exactly one current save footer. A separate 119-character startup message
wrapped across pages and retained its fired bit in a native turn-1 save. These are
runtime smoke checks, not a full campaign or PBEM playtest.

## Background music layer

The original D-Day `SongLogic` is empty. `dday-music` adds a separate FM player;
it does not reinterpret existing player preferences. In particular, preference
+8 means Center Map on Battles in D-Day and remains unchanged. Sound Effects
continues to use preference +9. Music is controlled by Options → Background Music
and `DATA/MUSIC/MUSIC.CFG`, with missing configuration defaulting to on.

The patch wraps SongLogic, Options-menu creation/dispatch, and the two native
sound-shutdown calls. After native InsertMenu clears its enabled flags, SongLogic
restores the extra item's availability. Music version 2 uses the native 140 Hz TSM service with an explicit 100 Hz divider
and bounded OPL writes, without DOS calls in interrupt context. Missing/bad music
data or unavailable audio/timer resources disable music without aborting startup.

Rebuild this layer alone with `python3 tools/build_dday_music_patch.py`; the full
library builder includes it too. Recreate the music asset with
`python3 tools/build_music_library.py` (Unicorn/Pillow plus the staged V4V game).
See [music asset and format documentation](../../../assets/music/README.md).

### Music timing correction (version 2)

The first music release did not return zero from its timer callback. Native
`TimerISR` (0x8a2e4) interprets EAX as a scheduling status; nonzero leaves the
old deadline in place, and 2 reprograms the PIT. Restoring the incoming EAX
therefore made the music callback repeatedly due. The fixed callback explicitly
returns zero on every path. It also requests rate 0 (native 140 Hz) and uses a
phase accumulator to produce 100 stream ticks per 140 interrupts, avoiding the
native scheduler's inexact fractional-rate calculation.

`tools/test_music_patch.py` now executes the original NewService, ResumeService,
PauseService and TimerISR code, including a second periodic service. The first
release fails the deadline regression; version 2 advances the deadline and
produces exactly 100 music ticks per second. Earlier tests mocked those services
and missed the callback contract.

Forward/inverse files for the superseded music version are retained under
`history/dday-music-v1.*` to recognize and upgrade or remove that verified build.
`--component music`, `library`, or `all` automatically upgrades it; `--reverse`
continues to work. No fallback executable is installed. Earlier non-music patch
files remain byte-identical.
