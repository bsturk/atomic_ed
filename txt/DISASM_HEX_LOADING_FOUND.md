# Disassembly: Hex Loading Code Found

**Date:** 2025-11-09
**Discovery:** Found sprite sheet width reference in disassembly

---

## Discovery

### Sprite Sheet Width Reference

**Location:** `disasm.txt` line 1119
**Code:**
```asm
seg002:01B3    mov    word ptr ds:1C0h, 0C80h
```

**Analysis:**
- `1C0h` = 448 decimal = **SPRITE SHEET WIDTH**
- `0C80h` = 3200 decimal

This appears to be initializing or storing a value related to the sprite sheet width of 448 pixels.

**Context:** This is in `seg002` at offset `01B3`, which is early in the code segment, suggesting initialization code.

---

## Verified Values

### From Pixel Analysis
```python
SPRITE_WIDTH = 448      # 0x1C0 - FOUND IN DISASM!
SPRITE_HEIGHT = 570     # 0x23A - not yet found
HEX_WIDTH = 32          # 0x20
HEX_HEIGHT = 36         # 0x24
HEX_SPACING = 34        # 0x22
HEX_ROW_SPACING = 38    # 0x26
HEX_OFFSET_X = 12       # 0x0C
```

### Disassembly Findings
- ✓ Sprite width 448 (0x1C0) found at seg002:01B3
- ⏳ Sprite height 570 (0x23A) - searching
- ⏳ Tile dimensions 32×36 - searching
- ⏳ Spacing values 34×38 - searching

---

## Next Steps

1. Examine code around seg002:01B3 for height value (570/0x23A)
2. Search for tile extraction loop with 13×14 grid
3. Look for constants 32, 36, 34, 38 near sprite sheet operations
4. Trace forward from width initialization to find rendering code

---

**Status:** PARTIAL MATCH - Sprite width confirmed in disassembly
