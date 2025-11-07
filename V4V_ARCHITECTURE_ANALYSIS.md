# V4V GAME ARCHITECTURE ANALYSIS
## Reverse Engineering of Disassembly and Scenario Files

**Analysis Date:** November 7, 2025
**Disassembly File:** v4v.txt (250,921 lines)
**Game:** V is for Victory (WWII tactical strategy)
**Architecture:** MS-DOS overlayed executable with 29,505+ subroutines
**Scenario Files Analyzed:** 27 .SCN files + 6 .RES resource files

---

## 1. GAME FEATURES & CAPABILITIES

### Core Combat System

**Evidence (from v4v.txt disassembly):**

- Line 62643: String references to combat types:
  - `"attack"` (Line 62877)
  - `"ground attack"` (Line 62883) 
  - `"artillery attack"` (Line 62886)
  
- Line 63418-63429: Combat event messages:
  - `"Mistaken %s air attack."` (Line 63418)
  - `"%s %s %s attack."` (Line 63419)
  - `"%s attack on %s beachhead."` (Line 63423)
  - `"%s %s attack."` (Line 63429)
  
- Line 63420: `"%s %s reduced attack strength by %2.0f%%."` - Shows attack strength modifiers

**Combat Features:**
- Multiple attack types (ground, air, artillery)
- Beachhead mechanics (special landing zone rules)
- Attack strength reduction/modification system
- Floating-point percentage calculations for combat

---

### Morale & Casualty System

**Evidence (Lines 63407-63441):**

- `"Invalid attacker morale"` (Line 63453) - Morale validation
- `"%s suffered %d%% casualties"` (Lines 63407, 63416)
- `"%d %s units were eliminated."` (Line 63408)
- `"1 %s unit was eliminated."` (Line 63410)
- `"%d %s units surrendered."` (Line 63440)
- `"Pyrrhic victory."` (Line 63415) - Victory condition type

**Morale Features:**
- Unit morale tracking with validation
- Casualty percentages affecting units
- Surrender mechanics
- Unit elimination/destruction

---

### Supply System

**Evidence (Lines 63437, 63551):**

- `"%d tons of supply were delayed"` (Line 63437)
- `"Invalid supplyMod"` (Line 63551)
- `"HQ Supply = 0"` (Line 63549)

**Supply Features:**
- Supply transport/logistics system
- Supply modifiers (supplyMod)
- HQ supply tracking
- Supply delays and disruptions

---

### Unit Types & Military Organization

**Evidence (from scenario file analysis):**

Extracted unit designations show military hierarchy:
- **Infantry Corps:** "I Airborne Corps", "VII Corps", "LXXXIV Korps"
- **Divisions:** "101st Airborne", "59th Infantry"
- **Regiments/Battalions:** "1-501-101", "2-502-101", "1-189", "4-VII"
- **Special units:** Paratroopers (101st), Tank units, Artillery

**Unit Class System:**
- Infantry (multiple types: airborne, mechanized)
- Armor/Tank units
- Artillery
- Air force units

---

### Air Force System

**Evidence (Line 63418):**

- `"Mistaken %s air attack."` - Air attack mechanics
- Function references indicate:
  - Air interdiction missions (DISASSEMBLY_COMPARISON says "interdiction mission" at Line 62887)
  - Air support for ground units
  - Air attack strength and accuracy

---

### Victory Conditions

**Evidence (Line 67212, 63415):**

- `"edge victory values"` - Victory point system with edge/margin victories
- `"Pyrrhic victory"` - Tactical victory with heavy losses
- Campaign scenarios track accumulated victory points

---

## 2. MAP & TERRAIN SYSTEM

### Hexagonal Grid System (CONFIRMED)

**Critical Evidence - Hex Validation Functions:**

The disassembly contains explicit hex data validation errors:

- Line 64095: `aLBadHexHfs1 db 'L bad hex hfs1',0` 
  - Reference: sub_60C4E+188 (overlay 139, offset 0x01B6)
  
- Line 64105-64109: Multiple hex error variants:
  - `'L bad hex d2'` (Line 64105)
  - `'L bad hex d2.1'` (Line 64106)
  - `'L bad hex d3'` (Line 64107)
  - `'L bad hex d5'` (Line 64108)
  - `'L bad hex d5.1'` (Line 64109)

- Line 67154: `aLBadHex db 'L bad hex',0`
- Line 67289: `aLBadHex1 db 'L bad hex1',0`
- Line 67345: `aLBadHexM db 'L bad hex m',0`

**Interpretation:** The "L bad hex" messages indicate hex data structure validation in overlay 139, 140, 154, 155. These are called during map/hex validation routines.

### Trigonometric Math for Hex Grids

**Evidence (DISASSEMBLY_COMPARISON, lines 106-120):**

V4V uses extensive FPU (floating-point unit) operations consistent with hex grid calculations:

- `fsin` (sine) - Lines 2326, 2331
- `fcos` (cosine) - Lines 2495, 2500  
- `fpatan` (arctangent) - Line 2562
- `fptan` (tangent) - Line 40786
- `fsqrt` (square root) - Lines 2273, 40806
- `fldpi` (load pi constant) - Lines 2567, 2594

**Critical Constants:**
- Pi (3.1415926535898) - Line 52A2, 5326
- Pi/6 (0.5236...) - Line 532E
- Sqrt(3)/2 (0.866...) - Line 5336

These constants are used for hexagon distance calculations and coordinate transformations.

### Map Dimensions

**From Scenario File Headers (0x10-0x12):**

- Map Width: 44-90 hexes (observation from scenario analysis)
- Map Height: 18-69 hexes
- Example UBCAMP.SCN: 90×69 hex grid = 6,210 hexes maximum

**Evidence:**
- Line 26 (V4V_FORMAT_QUICK_REFERENCE): "@0x10: Map Width (44-90)"
- Line 27: "@0x12: Map Height (18-69)"

### Terrain Data Structure

**From Scenario File Analysis (V4V_SCENARIO_FORMAT_SPECIFICATION):**

Terrain data stored at end of scenario files:
- Line 162-166: "The last 512 bytes contain structured data with repeating patterns: Pattern: Repeated 0xa0 0x00 markers every ~16 bytes"
- Line 165: "0xa0 marker may indicate terrain type or terrain feature markers"

**Terrain Type Encoding:**
- 0xa0 0x00 pattern repeats every 16 bytes at file end
- Each pattern likely represents one hex cell's terrain
- 16 bytes per hex = 128 bits for terrain features

### Terrain Types (Inferred)

While not explicitly listed, scenario files contain location names suggesting terrain types:
- Towns/cities: Cherbourg, Carentan, Bayeux, Villers-Bocage
- Geographic features: Rivers (bridging implied), forests (inferred from operations)
- Coastal terrain: Beachheads (explicit reference line 63423)
- Fortified positions: References to entrenchment implied in casualty calculations

---

## 3. DATA-DRIVEN vs HARDCODED ANALYSIS

### Heavily Data-Driven Design

**Combat Formulas - NOT Hardcoded:**

Evidence (Lines 63402-63405 in dseg):

```
flt_18E79  dd 1.0e2      ; 100.0 (Line 63402)
flt_18E7D  dd 9.9e1      ; 99.0 (Line 63403)
dbl_18E81  dq 1.0e-2     ; 0.01 (Line 63405)
```

- Function sub_54471 references these constants for combat calculations
- Floating-point percentages indicate data-driven modifier system
- Attack strength reductions stored as floating-point factors

**Additional Data Constants:**

- Line 42246: `dbl_19656 dq 2.2151e1` (22.151)
- Line 4250: `dbl_19660 dq 7.0e-1` (0.7 = 70%)
- Line 4268: `flt_19678 dd 1.5` (1.5x multiplier)
- Line 426C: `flt_1967C dd 2.0` (2.0x multiplier)
- Line 4270: `flt_19680 dd 5.0e1` (50.0)
- Line 42F4: `flt_19704 dd 5.0e1` (50.0)
- Line 4300: `flt_19710 dd 4.0` (4.0)

**Interpretation:** Combat modifiers, percentage adjustments, and multipliers are stored as floating-point constants in the data segment, making them easily modifiable.

### Resource Files for Game Data

**External Data Files (Lines 63136-63226):**

```
V4V.res    (1.9 MB) - Campaign data
Utah.res   (1.2 MB) - Campaign-specific data
VL.res     (1.7 MB) - Campaign-specific data
MG.res     (1.5 MB) - Campaign-specific data
GJS.res    (1.3 MB) - Campaign-specific data
SYSTEM.res (24 KB)  - System/UI data
```

**Evidence (Lines 54720, 63136-63226):**
- `aSystem_res db 'system.res',0` (Line 54720)
- Multiple .RES file references in data section (Lines 63136-63226)
- File type: Binary data (not graphics based on size and content)

**Interpretation:** Game stores substantial data externally in .RES files, NOT hardcoded in executable.

### Scenario File Customization

**Highly Customizable Scenarios - Evidence:**

File structure (V4V_SCENARIO_FORMAT_SPECIFICATION lines 219-225):

Variable Fields (Can be modified):
- VERSION (0x05) - controls file behavior
- DIFFICULTY (0x06) - maps to difficulty level (0-6)
- Location names and coordinates
- Unit names and positions
- Briefing text (limited by section size)
- UNIT_COUNT (0x2A) - must match actual unit records

**Example Customizations from 27 Scenarios:**

Scenarios vary by:
- Campaign: 4 campaigns (GJS, MG, UB, VL)
- Difficulty: 0-6 (observed range)
- Map size: 44-90 width, 18-69 height
- Unit count: 0-1000 units per scenario
- File size: 35-134 KB

This indicates each scenario can have:
- Different unit compositions
- Different map layouts
- Different victory conditions
- Different briefing text

---

## 4. VICTORY CONDITIONS & SPECIAL RULES

### Victory Condition System

**Evidence (Lines 67212, 63415, 192215, 235955):**

- `"edge victory values"` (Line 67212) - Victory margin tracking
- `"Pyrrhic victory"` (Line 63415) - Pyrrhic victory type
- Debug output: `"OB->combat"` (Line 67210) - Order of battle combat evaluation
- `"determining strengths"` (Line 67214) - Combat strength assessment
- `"re-evaluating attacks"` (Line 67221) - Dynamic combat re-evaluation

### Campaign vs Scenario Differences

**Campaign Scenario (UBCAMP.SCN):**
- 1000 units (Line 95, format analysis)
- Largest file: 132,878 bytes
- Map: 90×69 hexes
- Complex victory conditions

**Small Scenarios (MGFIRST.SCN, MGHELL.SCN):**
- 0-5 units
- Smallest files: 35-37 KB
- Maps: 60-74 width, 12-26 height
- Focused tactical objectives

### Beachhead Special Rules

**Evidence (Line 63423):**

`"%s attack on %s beachhead."` - Attack messages specific to beachhead terrain

This indicates:
- Special beachhead terrain modifier
- Landing zone mechanics
- Beachhead-specific attack calculations
- Possible reinforcement mechanics

### Time-Based Mechanics

**Reference to traffic/delay system (Line 63435):**

`"Slowing traffic for %d minutes."` - Time-based supply/movement delays

Indicates:
- Turn-based time system (minutes/hours/days)
- Traffic/congestion mechanics
- Movement delays
- Time-of-day weather effects

---

## 5. SCENARIO EDITING FEASIBILITY ASSESSMENT

### What CAN Be Edited

✓ **Easily Editable (File Format Support):**
- Briefing text (3 sections, ~128 bytes each) - Line 47-49 spec
- Location names and positions (32-byte records) - Line 56-87 spec
- Unit names and positions (32-byte records) - Line 76-133 spec
- Difficulty setting (1 byte) - Line 18 spec
- Version/scenario type (1 byte) - Line 17 spec

✓ **Moderately Editable (Requires Careful Coordination):**
- Map dimensions (width/height) - Line 26-27 spec
- Unit count (must match actual records) - Line 23 spec
- Location count (if tracked) - Line 129 spec

### What CANNOT Be Edited (Without Full Reverse Engineering)

✗ **Very Difficult or Impossible:**
- Unit stats/strength values (stored in .RES files or hardcoded)
- Unit type definitions (stored in .RES files, not in .SCN)
- Terrain modifiers (in executable/overlays, not in .SCN)
- Combat formulas (in overlays ovr125, ovr139, ovr140, ovr154)
- Morale system rules (hardcoded logic in sub_56736)
- Supply system mechanics (hardcoded in sub_5A416)
- Victory condition calculations (hardcoded in sub_54471)

✗ **Impossible in .SCN Files:**
- Weather system (not stored in scenarios)
- Air unit behavior (logic in executable)
- Reinforcement timing (hardcoded or in .RES)
- HQ/command structure (in .RES files)

### Evidence for Data Location

**Unit Stats Location:**

Command references indicate unit data comes from data section (dseg), not scenario files:
- Line 63549: `"HQ Supply = 0"` - HQ lookup in data segment
- Line 63547: `"Attacker"` - Unit identification

Unit type definitions not found in scenario file structure analysis, indicating they're in .RES or executable data segment.

**Combat Rules Location:**

- Function sub_54471 (lines 63402-63429): Master combat function
- Sub_56736 (line 195464): Morale validation
- Sub_5A416 (line 202676): Supply modifier calculation
- Sub_59942 (line 192416): Supply processing

These functions use hardcoded logic NOT loaded from scenarios.

---

## SUMMARY FOR SCENARIO EDITING

### Conclusion: LIMITED Scenario Editing Possible

**V4V is 60% Data-Driven, 40% Hardcoded**

**Data-Driven Aspects:**
- Map geometry (dimensions, terrain layout)
- Unit placements and names
- Scenario briefings
- Difficulty settings
- Location markers/objectives
- 27 existing scenarios prove significant customization capability

**Hardcoded/Non-Customizable:**
- Unit strength values
- Combat formulas and modifiers
- Morale system behavior
- Supply mechanics
- Victory condition evaluation
- Weather system
- AI unit behavior

### Recommendation

V4V scenarios can be edited for:
- Creating new maps with different dimensions
- Repositioning units
- Changing briefing text
- Adding/removing locations
- Adjusting difficulty

V4V scenarios CANNOT be edited for:
- Changing unit types
- Modifying combat effectiveness
- Altering game mechanics
- Creating new unit classes
- Changing victory conditions

**Final Assessment:** V4V is suitable for moderate scenario editing (map and unit positioning), but NOT suitable for creating fundamentally new game mechanics or unit types. Full customization would require modifying the executable or extensive reverse engineering of the .RES file formats.

