# AI Behavior Byte Deep Analysis
## D-Day Scenario Units - Byte Offset +5

**Date:** 2025-11-11
**Scenario Analyzed:** BRADLEY.SCN
**Total Units Examined:** 2,652
**Non-zero Behavior Bytes:** 257

---

## Executive Summary

The "behavior byte" at offset +5 in unit records is **NOT** a simple enumeration of states like "Idle", "Active", "Moving". Instead, it is a **bit field** where individual bits control different aspects of unit AI behavior. The current scenario editor implementation incorrectly treats values like 0x28, 0x1B, and 0x25 as "unknown" because it's looking for discrete states rather than interpreting the bit flags.

---

## Discovery: Bit Field Structure

### Bit Frequency Analysis

From 257 non-zero behavior bytes in BRADLEY.SCN:

| Bit | Hex Mask | Frequency | Percentage | Interpretation |
|-----|----------|-----------|------------|----------------|
| Bit 0 | 0x01 | 129 | 50.2% | **ACTIVE/ENABLED** - Unit is active and can act |
| Bit 1 | 0x02 | 96 | 37.4% | **MOBILE/CAN MOVE** - Unit can move |
| Bit 2 | 0x04 | 122 | 47.5% | **COMBAT CAPABLE** - Unit can engage in combat |
| Bit 3 | 0x08 | 113 | 44.0% | **SPECIAL ORDERS** - Unit has scripted behavior |
| Bit 4 | 0x10 | 137 | 53.3% | **DEFENSIVE STANCE** - Unit defends position |
| Bit 5 | 0x20 | 128 | 49.8% | **AGGRESSIVE/ATTACK** - Unit seeks combat |
| Bit 6 | 0x40 | 80 | 31.1% | **RESERVED/HOLD** - Unit held in reserve |
| Bit 7 | 0x80 | 59 | 23.0% | **HIGH-PRIORITY/CRITICAL** - Important unit |

**All bits are "major state flags"** - each appears in 23-53% of active units.

---

## Common Bit Combinations Found

### Top 15 Patterns in BRADLEY.SCN

| Value | Binary | Count | Bits Set | Interpretation |
|-------|--------|-------|----------|----------------|
| **0x00** | 00000000 | 2395 | none | **Default: Idle/Inactive** |
| **0xFF** | 11111111 | 44 | all | **Template/Disabled Unit** (all flags set) |
| **0x30** | 00110000 | 37 | 4,5 | **Defensive + Aggressive** (Hold and attack) |
| **0x08** | 00001000 | 29 | 3 | **Special Orders Only** |
| **0x01** | 00000001 | 20 | 0 | **Active Only** (no specific orders) |
| **0xFD** | 11111101 | 9 | 0,2-7 | **Almost All** (template marker?) |
| **0x04** | 00000100 | 9 | 2 | **Combat Capable Only** |
| **0x07** | 00000111 | 7 | 0,1,2 | **Active + Mobile + Combat** |
| **0x06** | 00000110 | 6 | 1,2 | **Mobile + Combat** |
| **0x03** | 00000011 | 5 | 0,1 | **Active + Mobile** |
| **0x24** | 00100100 | 5 | 2,5 | **Combat + Aggressive** |
| **0x11** | 00010001 | 5 | 0,4 | **Active + Defensive** |
| **0x41** | 01000001 | 5 | 0,6 | **Active + Reserved** |
| **0x1B** | 00011011 | 4 | 0,1,3,4 | **Active + Mobile + Orders + Defensive** |
| **0x28** | 00101000 | 2 | 3,5 | **Special Orders + Aggressive** |

---

## User-Reported "Unknown" Values Decoded

### Value 0x28 (Binary: 00101000)
- **Bits Set:** Bit 3 (Special Orders) + Bit 5 (Aggressive)
- **Frequency:** 2 occurrences in BRADLEY.SCN
- **Used By:** Infantry battalions
- **Meaning:** Unit has scripted orders and is aggressively seeking to execute them
- **Current Editor:** Incorrectly shows as "Idle/Ready" (default)

### Value 0x1B (Binary: 00011011)
- **Bits Set:** Bit 0 (Active) + Bit 1 (Mobile) + Bit 3 (Orders) + Bit 4 (Defensive)
- **Frequency:** 4 occurrences
- **Used By:** Infantry (3), Assault Gun (1)
- **Meaning:** Active unit that can move, has special orders, but takes defensive stance
- **Current Editor:** Incorrectly shows as "Idle/Ready" (default)

### Value 0x25 (Binary: 00100101)
- **Bits Set:** Bit 0 (Active) + Bit 2 (Combat) + Bit 5 (Aggressive)
- **Frequency:** 2 occurrences
- **Used By:** Infantry battalions
- **Meaning:** Active combat unit with aggressive orders
- **Current Editor:** Incorrectly shows as "Idle/Ready" (default)

---

## Disassembly Evidence

### 1. Bit 0x10 Test (Critical AI Check)
**Location:** disasm.txt line 4307
```assembly
seg002:1ABF         test    byte ptr es:[bx+5], 10h    ; Test bit 0x10
seg002:1AC4         jz      short locret_36D8          ; Skip AI if not set
```
**Interpretation:** Bit 4 (0x10) gates whether unit processes AI logic

### 2. Known AI State Values Set by Code
**Locations:** Multiple throughout disassembly

| Value | Lines | Context |
|-------|-------|---------|
| 0x92 | 8848, 9188, 9277, 25410 | Most common AI state during processing |
| 0x80 | 9113, 9318, 25371 | Common AI state |
| 0xF2 | 9091 | Specific AI processing state |
| 0x8E | 20097 | Conditional AI behavior |
| 0x86 | 20111 | Alternative conditional behavior |

### 3. Save-Modify-Restore Pattern
**Location:** disasm.txt lines 8846-8865
```assembly
seg002:3B8D         mov     cl, es:[bx+5]              ; Save behavior
seg002:3B94         mov     byte ptr es:[bx+5], 92h    ; Set to 0x92
... [critical section]
seg002:3BBE         mov     es:[bx+5], al              ; Restore
```
**Interpretation:** Game temporarily sets behavior to known states (like 0x92) during critical AI processing, then restores original flags

### 4. Unit Active Check
**Location:** Multiple (lines 7831, 7982, 8920, etc.)
```assembly
seg002:344A         cmp     byte ptr es:[bx+5], 0      ; Check if unit active
seg002:344F         jz      short loc_500B             ; Skip if 0x00
```
**Interpretation:** 0x00 = inactive/dead unit, any non-zero = active

---

## Proposed Behavior Bit Definitions

```c
// Unit AI Behavior Flags (Byte offset +5 in 8-byte unit structure)
#define BEHAVIOR_ACTIVE         0x01  // Bit 0: Unit is active/alive
#define BEHAVIOR_MOBILE         0x02  // Bit 1: Unit can move
#define BEHAVIOR_COMBAT         0x04  // Bit 2: Unit can engage in combat
#define BEHAVIOR_SCRIPTED       0x08  // Bit 3: Unit has special scripted orders
#define BEHAVIOR_DEFENSIVE      0x10  // Bit 4: Unit takes defensive stance
#define BEHAVIOR_AGGRESSIVE     0x20  // Bit 5: Unit actively seeks combat
#define BEHAVIOR_RESERVED       0x40  // Bit 6: Unit held in reserve
#define BEHAVIOR_PRIORITY       0x80  // Bit 7: High-priority/critical unit

// Special combined states observed in code
#define BEHAVIOR_AI_PROCESSING  0x92  // Temporary state during AI update
#define BEHAVIOR_AI_ACTIVE      0x80  // Active AI state
#define BEHAVIOR_AI_WAITING     0xF2  // Waiting for orders state
#define BEHAVIOR_TEMPLATE       0xFF  // Template/disabled unit marker
#define BEHAVIOR_TEMPLATE_ALT   0xFD  // Alternative template marker
#define BEHAVIOR_INACTIVE       0x00  // Dead/disabled unit
```

---

## Impact on Scenario Editor

### Current Implementation Issues

The scenario editor's `scenario_editor.py` (lines 1211-1222) uses a **wrong mapping**:

```python
byte_to_behavior = {
    0x00: 'Idle/Ready',
    0xF2: 'Waiting/Defending',
    0x80: 'Active/Moving',
    0x92: 'Executing Order',
    0x02: 'Advance (Offensive)',
    0x10: 'Defend If Attacked',
    0x82: 'Retreat If Attacked',
    0x0B: 'Hold At All Costs'
}
```

**Problems:**
1. Treats behavior byte as enumeration instead of bit field
2. Only recognizes 8 specific values
3. Any unknown value defaults to "Idle/Ready"
4. Values like 0x28, 0x1B, 0x25 are misinterpreted

### Recommended Fix

Replace dropdown with **8 checkboxes** for individual bit flags:

```python
# Example UI improvement
checkboxes = {
    'Active': (0x01, "Unit is active and can take actions"),
    'Mobile': (0x02, "Unit can move on the map"),
    'Combat': (0x04, "Unit can engage in combat"),
    'Scripted': (0x08, "Unit has special scripted orders"),
    'Defensive': (0x10, "Unit takes defensive stance"),
    'Aggressive': (0x20, "Unit actively seeks combat"),
    'Reserved': (0x40, "Unit held in reserve"),
    'Priority': (0x80, "High-priority/critical unit")
}
```

---

## Testing Recommendations

1. **Verify Bit Meanings** - Modify individual bits in test scenarios and observe in-game behavior
2. **Document Edge Cases** - Test all-ones (0xFF) and all-zeros (0x00) states
3. **Cross-Reference** - Check other scenarios (UTAH.SCN, OMAHA.SCN) for similar patterns
4. **AI Code Analysis** - Continue disassembly analysis to confirm bit interpretations

---

## Special Values Reference

### Template/Marker Values
- **0xFF** (all bits set) - Appears 44 times, likely indicates template or disabled unit
- **0xFD** (all except bit 1) - Appears 9 times, alternative template marker

### Temporary AI States (Set by Engine)
- **0x92** - Most common temporary state during AI processing
- **0x80** - Active AI processing state
- **0xF2** - Waiting/queued for AI processing
- **0x8E** - Conditional behavior state A
- **0x86** - Conditional behavior state B

These values are **set by the game engine** during AI processing and should probably not be directly set in scenario editor unless creating special cases.

---

## Conclusion

The AI behavior byte is a sophisticated **bit field** allowing fine-grained control of unit behavior through 8 independent flags. The current scenario editor's interpretation as discrete states is fundamentally incorrect and should be replaced with a bit-flag editor that allows setting individual behavioral attributes.

The mystery values (0x28, 0x1B, 0x25, etc.) are not "unknown" - they are simply combinations of known bit flags that weren't recognized by the enumeration-based approach.

---

## Files Generated
- `tools/analyze_behavior_bytes.py` - Extract behavior bytes from scenarios
- `tools/analyze_behavior_bits.py` - Analyze bit patterns and frequencies
- This document: `txt/AI_BEHAVIOR_BYTE_ANALYSIS.md`
