# D-Day executable patches

The complete patched executable runs native D-Day scenarios and scenarios
exported by the editor. It adds file-based scenario selection, custom artwork,
conditional events, game profiles, terrain rules and optional background music.
Weather and victory history support scenarios up to **400 turns**.

Use **INVADE-PATCHED.EXE** as **INVADE.EXE** in your playing copy. Follow the
[installation guide](../README.md) to add scenarios, sound and music.

## Patch files and reversal

Run the applicator from the project folder. Place your original D-Day executable
at `game/waw/dday/orig/INVADE.EXE` and apply the complete set:

```sh
python3 tools/patch_dday.py game/waw/dday/orig/INVADE.EXE --component all -o game/waw/dday/INVADE-PATCHED.EXE
```

**Use `--component all` for the complete build.** The command's default component
is `engine`.

Each layer has a forward `.ips`, an inverse `.undo.ips`, and a `.json` manifest
identifying the supported input and output. The applicator checks these before
writing. An explicit output path can contain an identical result; different
existing content is protected. Without `-o`, the tool updates the input file
and creates a `.bak` backup when changing it.

To restore the exact original executable from the complete build:

```sh
python3 tools/patch_dday.py game/waw/dday/INVADE-PATCHED.EXE --component all --reverse -o ORIGINAL.EXE
```

### Individual layers

Layers apply in the order below and reverse in the opposite order. Each
individual component requires its matching input build. `--component library`
applies or removes all layers above `engine`; `--component all` includes engine.

| Component | Patch filename stem | Function |
| --- | --- | --- |
| `engine` | `dday-weather-400` | 400-turn weather/victory history and timed or single-condition HQ orders |
| `code-space` | `dday-code-space` | Executable space used by the additional features |
| `scenario-library` | `dday-scenario-library` | Scenario discovery, companion selection and saved scenario identity |
| `presentation` | `dday-presentation` | Scenario portraits, flags, emblems and turn pictures |
| `custom-artwork` | `dday-custom-artwork` | Individual leader portraits |
| `advanced-orders` | `dday-advanced-orders` | Combined conditions and persistent HQ orders |
| `support-artwork` | `dday-support-artwork` | Aircraft/naval category artwork and support roster handling |
| `game-profiles` | `dday-game-profiles` | Per-scenario victory ratios and winter models |
| `terrain-rules` | `dday-terrain-rules` | Terrain movement costs and combat modifiers |
| `nested-events` | `dday-nested-events` | Nested conditions, reinforcement releases and public messages |
| `startup-selection` | `dday-startup-selection` | SELECT.BAT's requested battle selected at startup |
| `music` | `dday-music` | V4V FM playlist with its own Options toggle |
| `air-weather` | `dday-air-weather` | Weather lookup for reconnaissance and air-supply missions |

For example, build the engine and then its code-space layer:

```sh
python3 tools/patch_dday.py game/waw/dday/orig/INVADE.EXE --component engine -o ENGINE.EXE
python3 tools/patch_dday.py ENGINE.EXE --component code-space -o EXPANDED.EXE
```

To remove music from the complete build, first reverse the layer above it:

```sh
python3 tools/patch_dday.py game/waw/dday/INVADE-PATCHED.EXE --component air-weather --reverse -o MUSIC.EXE
python3 tools/patch_dday.py MUSIC.EXE --component music --reverse -o SELECT.EXE
```

That result also omits the air-weather layer. For normal play, use the complete
build. Partial builds are useful when isolating or testing an individual feature.

Use the supplied applicator for patching and reversal; it handles executable
size changes as well as byte replacements.

## Scenario files and saved games

**Export for DOS** produces a matching **SCN, REZ and AI** set. Copy it into the
playing copy's SCENARIO folder. The Scenarios panel lists up to 256 compatible
files, five per page, and loads the selected scenario's companions.

The REZ carries artwork and custom game/terrain rules. The AI carries Battle
Plans. Keep both with saved games. Persistent orders and one-time events retain
their activation through Save/Resume; keep the save's matching AI file.

Custom startup screens additionally export **DATA/PCWATW.REZ**, which applies
to the playing installation. Background music uses **DATA/MUSIC/V4V.OPL**;
see the [music guide](../../../assets/music/README.md).

Use the complete patched executable to resume saves made with these extensions.
The [editor guide](../../../txt/SCENARIO_EDITOR_README.md) covers authoring,
and the [conversion guides](../../../txt/SCENARIO_PACK.md) describe the
prepared battles and their source-game adaptations.

## Rebuild from source

Rebuilding requires Python, NASM and the supported original D-Day executable.
From the project folder:

```sh
python3 tools/build_dday_patch.py
python3 tools/build_dday_library_patch.py
```

These commands regenerate the forward/inverse IPS files and manifests for the
complete set. Run the applicator afterward to create `INVADE-PATCHED.EXE`.

The Python implementation lives in [`patching/`](../../../patching/); the
assembly sources and generated patch files are in this directory. The commands
under `tools/` are entry points for those builders and the applicator.

## Executable checksums

SHA-256 identifies the supported original and the complete patched result.

Original D-Day executable:

```text
d28ef2b0e8eea2f5b6bb7eb1e002d3621c770f7d94e9add7480caf14ca8df2ba
```

Complete `INVADE-PATCHED.EXE`:

```text
5aaf34f932e3387f9529c885cf4016ca46c19b8db4abf60fa8e3c30323445f69
```

Each layer's manifest supplies the corresponding intermediate checksums.
