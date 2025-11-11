# Scenario Editor Update - Behavior Byte Bit Field Support

**Date:** 2025-11-11
**Update Type:** Major UI/UX Enhancement
**Files Modified:** `scenario_editor.py`

---

## Overview

Updated the scenario editor to correctly interpret and edit AI behavior bytes as **bit fields** instead of discrete enumeration values. This fixes the issue where behavior bytes like 0x28, 0x1B, and 0x25 were incorrectly shown as "Idle/Ready".

---

## Changes Made

### 1. Replaced Dropdown with Checkboxes

**Old Implementation:**
- Single dropdown with 8 predefined behavior "states"
- Only recognized specific values (0x00, 0x02, 0x0B, 0x10, 0x80, 0x82, 0x92, 0xF2)
- Any unknown value defaulted to "Idle/Ready"
- Could not represent combined flags

**New Implementation:**
- 8 individual checkboxes, one for each bit flag
- Live hex and binary display showing current byte value
- Can represent any combination of flags
- Correctly interprets all 256 possible values

### 2. UI Layout Changes

**Location:** `scenario_editor.py` lines 1061-1135

Added:
- Behavior byte display with both hex and binary format
- 8 checkboxes in 2-column layout
- Description labels for each flag
- Real-time updates when checkboxes change

**Checkbox Layout:**
```
Left Column (Bits 0-3):          Right Column (Bits 4-7):
☐ Bit 0: Active/Enabled          ☐ Bit 4: Defensive Stance
☐ Bit 1: Mobile                  ☐ Bit 5: Aggressive/Attack
☐ Bit 2: Combat Capable          ☐ Bit 6: Reserved/Hold
☐ Bit 3: Scripted Orders         ☐ Bit 7: High Priority
```

### 3. Bit Flag Definitions

**Location:** `scenario_editor.py` lines 1095-1112

```python
self.behavior_flags = [
    {'bit': 0, 'mask': 0x01, 'name': 'Active/Enabled'},
    {'bit': 1, 'mask': 0x02, 'name': 'Mobile'},
    {'bit': 2, 'mask': 0x04, 'name': 'Combat Capable'},
    {'bit': 3, 'mask': 0x08, 'name': 'Scripted Orders'},
    {'bit': 4, 'mask': 0x10, 'name': 'Defensive Stance'},
    {'bit': 5, 'mask': 0x20, 'name': 'Aggressive/Attack'},
    {'bit': 6, 'mask': 0x40, 'name': 'Reserved/Hold'},
    {'bit': 7, 'mask': 0x80, 'name': 'High Priority'},
]
```

### 4. New Helper Methods

**Location:** `scenario_editor.py` lines 1301-1316

#### `_on_behavior_flag_changed()`
Called when any checkbox is toggled. Updates hex and binary displays in real-time.

#### `_get_behavior_byte_from_flags()`
Calculates the behavior byte value from checkbox states by OR-ing individual bit masks.

### 5. Updated Display Logic

**Location:** `scenario_editor.py` lines 1227-1234

```python
# Update byte display
self.behavior_byte_var.set(f"0x{behavior_byte:02X}")
self.behavior_binary_var.set(f"0b{behavior_byte:08b}")

# Set individual flag checkboxes based on behavior byte
for i, flag in enumerate(self.behavior_flags):
    is_set = bool(behavior_byte & flag['mask'])
    self.behavior_flag_vars[i].set(is_set)
```

### 6. Updated Apply Changes Logic

**Location:** `scenario_editor.py` lines 1271-1295

- Calculates behavior byte from checkboxes
- Shows active flags in success message
- Displays both hex and binary values

### 7. Completely Rewritten Help Text

**Location:** `scenario_editor.py` lines 1318-1400

Updated help dialog to explain:
- Bit field system vs enumeration
- Individual bit flag meanings
- Common flag combinations
- Special engine values (0x80, 0x92, 0xF2, 0xFF, 0xFD)
- Technical implementation details
- Reference to full analysis document

---

## Example Use Cases

### Case 1: Previously "Unknown" Value 0x28

**Old Editor:** Showed as "Idle/Ready" (incorrect default)

**New Editor:**
- Hex: 0x28
- Binary: 0b00101000
- Checkboxes:
  - ☐ Bit 0: Active/Enabled
  - ☐ Bit 1: Mobile
  - ☐ Bit 2: Combat Capable
  - ☑ Bit 3: Scripted Orders
  - ☐ Bit 4: Defensive Stance
  - ☑ Bit 5: Aggressive/Attack
  - ☐ Bit 6: Reserved/Hold
  - ☐ Bit 7: High Priority
- **Interpretation:** Unit has scripted orders and is aggressive

### Case 2: Value 0x1B

**Old Editor:** Showed as "Idle/Ready" (incorrect)

**New Editor:**
- Hex: 0x1B
- Binary: 0b00011011
- Active flags: Bits 0, 1, 3, 4
- **Interpretation:** Active, mobile unit with scripted orders taking defensive stance

### Case 3: Creating Custom Behavior

**Scenario:** Want a static artillery unit that only fires defensively

**Old Editor:** No way to create this exact combination

**New Editor:**
1. Check: Bit 0 (Active)
2. Check: Bit 2 (Combat Capable)
3. Check: Bit 4 (Defensive Stance)
4. Leave unchecked: Bit 1 (Mobile)
5. Result: 0x15 - Active, stationary, defensive combat unit

---

## Backwards Compatibility

The editor can still **read** all old scenario files correctly because it interprets the raw behavior byte value. Users can now see the actual bit flags instead of incorrect state names.

**Migration:**
- No file format changes required
- Existing scenarios load correctly
- Users may want to review and adjust behavior flags based on new understanding

---

## Testing Recommendations

1. **Load BRADLEY.SCN** and verify:
   - Units with 0x28, 0x1B, 0x25 show correct bit flags
   - Checkboxes match the hex/binary display
   - Changing checkboxes updates displays correctly

2. **Test editing:**
   - Toggle individual flags
   - Verify byte value updates in real-time
   - Apply changes and save scenario
   - Reload and verify flags persist

3. **Test edge cases:**
   - All flags off (0x00)
   - All flags on (0xFF)
   - Single flag values (0x01, 0x02, 0x04, etc.)

---

## Known Limitations

1. **Special Engine Values:** The editor doesn't prevent users from setting engine-managed values like 0x92 or 0xF2. Help text warns against this.

2. **Bit Meaning Uncertainty:** Some bit interpretations are based on frequency analysis and disassembly examination, not official documentation. Real in-game testing is needed to confirm exact behavior.

3. **GUI Only:** This update doesn't affect command-line tools or batch processing scripts.

---

## Related Files

- **`txt/AI_BEHAVIOR_BYTE_ANALYSIS.md`** - Complete technical analysis
- **`tools/analyze_behavior_bytes.py`** - Extracts behavior bytes from scenarios
- **`tools/analyze_behavior_bits.py`** - Analyzes bit patterns

---

## Future Enhancements

1. **Preset Buttons:** Add quick-set buttons for common combinations
   - "Defensive Position" → 0x15
   - "Aggressive Assault" → 0x27
   - "Mobile Reserve" → 0x47

2. **Validation:** Warn when setting combinations that might not make sense
   - Example: Combat Capable without Active flag

3. **Visual Feedback:** Color-code checkboxes by frequency or importance

4. **In-Game Testing:** Modify scenarios with known behaviors and test in game to confirm bit meanings

---

## Summary

This update transforms the scenario editor from showing misleading "Idle/Ready" defaults for most behavior values to correctly displaying and editing the sophisticated bit field system that the game actually uses. Users can now create precise AI behaviors by combining individual flags instead of being limited to 8 predefined states.
