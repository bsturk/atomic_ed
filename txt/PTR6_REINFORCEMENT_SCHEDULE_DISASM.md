# PTR6 Reinforcement Schedule – Disassembly Notes

Date: 2025-xx-xx  
Scope: D-Day (INVADE.EXE) reinforcement timing and entry hex extraction  
Files referenced: `disasm.txt` (segment seg002), PTR6 data in `.SCN` files

## Executive Summary
- The game uses a length‑prefixed record in PTR6 that stores `(turn, wave_id)` pairs. For BRADLEY this is a 0x200‑byte (256 word) record starting at PTR6+0x180 (file abs 0x1224).
- The reinforcement entry hexes come from the 10‑word PTR6 records that end with `0xFFFF 0xFFFF` (already used by the editor for off‑map entry coordinates).
- `sub_6FB0` (seg002:53E0) is the turn/time advancement routine. It calls `sub_6EBF` / `sub_6E32` to populate `ds:11EC` (reinforcement list pointer) and uses internal turn counters (`ds:98/9A` current, `ds:9C/9E` limit).
- Evidence strongly suggests the `(turn, wave)` table in PTR6 is the schedule the engine consults in `sub_6FB0` when deciding which wave to activate on a given turn.

## Disassembly Highlights
- `sub_6FB0` (seg002:53E0):
  - Maintains turn/time counters: `ds:98/9A` (current) and `ds:9C/9E` (limit).
  - Calls `sub_6EBF` (seg002:52EF) or `sub_6E32` (seg002:5262) to set up `ds:11EC` (head pointer to reinforcement list). The earlier `loc_6F32` in `sub_6EBF` shows `cmp word ptr es:[bx], 0FFFFh` before using `ds:11EC`, matching the 0xFFFF terminators in PTR6 entry records.
  - After range checks, bumps turn/time, sets `ds:11D4` to 9 (mode flag), and calls `sub_4374` with `cl=4` and a pointer to a 0x10‑byte stack buffer – likely populated from PTR6 schedule data.

## PTR6 Structures Observed
- **Reinforcement entry records** (10 words, used for entry hex):
  ```
  [ptr_lo][ptr_hi][wave_id][script][x][y][x2][y2][0xFFFF][0xFFFF]
  ```
  Present in all scenarios; wave_id links to units whose coords are 0xFFFF.

- **Schedule record** (turn → wave):
  - In BRADLEY, the first length‑prefixed block at PTR6+0x180 has length 0x200 bytes (256 words). Interpreted as consecutive word pairs `(turn, wave_id)`.
  - Scanning PTR6 for pairs `(turn <= turn_count, wave_id in off‑map waves)` yields plausible arrivals within scenario turn limits.

## Per‑Scenario Schedule Findings (from tools/parse_ptr6_reinforcement_schedule.py)
Using turn count from `TURN_COUNT_FORMAT.md`, wave IDs from reinforcement entry records, and the `(turn, wave)` pairs in PTR6:

- **BRADLEY (11 turns)** — mapped waves:  
  28→1, 31→5, 33→2, 34→1/4/9, 35→1/4/7/10, 36→1/4, 38→7, 46→1/4/10, 47→7, 48→4, 49→4.  
  (Waves 29, 30, 32, 37, 50–52 have no small‑turn pair yet.)

- **COUNTER (17 turns)** — examples:  
  25→2/3, 27→16, 28→1, 30→1 (wave IDs from off‑map units).

- **OMAHA (93 turns)** — partial:  
  256→1/2/3/4/15, 257→1, 260→1, 284→1. Needs fuller mapping with more waves.

- **UTAH / COBRA / CAMPAIGN / STLO** — reinforcement entry records present, but wave→turn mapping needs broader parsing because wave IDs aren’t visible via PTR6 strings. COBRA/CAMPAIGN nevertheless have thousands of 10‑word entries; the same schedule pattern is expected.

## How to Reproduce / Tooling
- New script: `tools/parse_ptr6_reinforcement_schedule.py`
  - Finds turn count via TURN_COUNT search.
  - Parses PTR6 reinforcement entry records (10‑word blocks).
  - Scans PTR6 word pairs for `(turn <= turn_count, wave_id)` to build a wave→turn table.
  - Prints first few wave mappings per scenario.

Run:
```
python tools/parse_ptr6_reinforcement_schedule.py
```

## Next Validation Steps
1) Single‑step `sub_6FB0` in DOSBox/emu with BRADLEY and watch it walk the PTR6 schedule record; confirm the `(turn, wave)` table is read when `ds:98/9A` increments.  
2) Extend the parser to prefer the first length‑prefixed record of size 0x200 as the schedule table; fall back to scanning all word pairs otherwise, using wave IDs from the 10‑word entries.  
3) Map more scenarios (especially COBRA/CAMPAIGN) using reinforcement entry wave IDs and the schedule scan to produce a full wave→turn report for the editor.
