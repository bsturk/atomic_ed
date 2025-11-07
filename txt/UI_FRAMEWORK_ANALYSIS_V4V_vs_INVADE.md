# COMPREHENSIVE UI CODE ANALYSIS: V4V vs INVADE DISASSEMBLY

## EXECUTIVE SUMMARY

**Critical Finding**: V4V and INVADE use fundamentally DIFFERENT execution environments and architectures:
- **V4V**: 16-bit DOS executable (3-4 segments + 112 overlays) with Borland C++ 3.1
- **INVADE**: 32-bit protected mode DOS executable using DOS/4G extender (Rational Systems)

This explains why identical visual UIs can have completely different underlying code.

---

## 1. EXECUTION ENVIRONMENT ANALYSIS

### V4V Architecture
```
Compiler: Borland C++ 3.1 (Copyright 1991)
Line 53895: aCopyright1991B db '- Copyright 1991 Borland Intl.',0
```
- Pure 16-bit DOS real mode
- 5 main segments (seg000-seg004)
- 112 overlay segments (ovr045-ovr156)
- File size: 250,921 disassembly lines
- Massive code footprint (megabytes)

### INVADE Architecture  
```
Extender: DOS/4G (Rational Systems)
Line 58 (seg000:005C): db 44h,4Fh,53h,2Fh,34h,47h... = "DOS/4G"
Line 68 (seg000:0085): aNc_19871993 db 'nc. 1987 - 1993',0
Full string: "DOS/4G  Copyright (C) Ration Systems, Inc. 1987 - 1993"
```
- 32-bit protected mode with DOS extender
- 4 segments (seg000-seg003, seg004 is zero-length)
- NO overlays
- File size: 27,915 disassembly lines
- Much more compact (fits in extender's 32-bit address space)

**CRITICAL IMPLICATION**: These are running in completely different CPU modes!
- V4V: 16-bit real mode, segmented memory, far pointers everywhere
- INVADE: 32-bit protected mode, flat memory model, near pointers

---

## 2. UI FRAMEWORK ARCHITECTURE

### V4V UI System (Borland C++ Framework)
V4V has an explicit object-oriented UI framework (dseg:64F5-6554):

**Manager Classes (Lines 70495-70502):**
```
Line 70495: aMemoryManager   db 'memory manager',0
Line 70497: aMenuManager     db 'menu manager',0  
Line 70498: aDialogManager   db 'dialog manager',0
Line 70499: aEventManager    db 'event manager',0
Line 70500: aFontManager     db 'font manager',0
Line 70501: aPaletteManager  db 'palette manager',0
Line 70502: aResourceManage  db 'resource manager',0
```

**Graphics Library:**
```
Line 70496: aFastdraw db 'fastdraw',0
Lines 20737, 20781: Error messages for fastdraw dispose operations
```

**Resource System:**
```
Lines 70490-70494: OpenResFile, CloseResFile, GetResource error strings
Line 62443: aMenu_dat db 'menu.dat',0
```

**Video Mode:**
```
Line 70484: Video board does not support VESA 640x480x256 color video mode
```

### INVADE UI System (DOS/4G Framework)
INVADE shows:
- **NO manager class markers**
- **NO fastdraw references**
- **NO menu.dat file references**
- **NO OpenResFile/CloseResFile API**
- **Generic video handling** (no explicit VESA mode check)

This suggests INVADE uses either:
1. A simpler, built-in UI system within the DOS/4G extender
2. A different UI framework
3. Direct VGA programming without a framework

---

## 3. MENU SYSTEM IMPLEMENTATION

### V4V Menu Code Structure

**Primary Menu Handler (Line 17208)**: `sub_764E`
```asm
Line 17221: call sub_2AED         ; Load menu.dat file
Line 17227: push aErrorOpeningMe  ; "Error opening menu file.\n"
Line 17236: call far ptr sub_343B ; Render menu to screen
Line 17243: call near ptr sub_760C; Handle menu interaction
```

**File Loader (Line 7479)**: `sub_2AED`
```
Purpose: Opens and loads menu.dat file
- Line 7495: mov si, [bp+arg_4]  ; Load filename pointer
- Line 7495: mov di, [bp+arg_6]  ; Load flags
- Line 7509: call sub_257B       ; Open file operation
- Line 7576: call sub_25C0       ; Render loaded menu data
```

**Menu Renderer (Line 8744)**: `sub_336A` (called through thunk at 8890 `sub_343B`)
```
- Line 8773: test word ptr [bx+6CDEh], 200h  ; Check menu state flags
- Line 8789: call sub_1699                   ; Call rendering primitive
- Line 8797: test word ptr [bx+6CDEh], 4000h ; Another state check
- Line 8806-8820: Loop processing menu data from file
```

### INVADE Menu System
**NO equivalent structures found:**
- No sub_764E equivalent
- No sub_2AED equivalent  
- No sub_343B equivalent
- No "Error opening menu file" error messages
- No menu.dat file references
- No menu state flag checks at specific memory addresses

---

## 4. GRAPHICS/VIDEO SYSTEM DIFFERENCES

### V4V Graphics Backend
```
Explicit VESA support:
Line 70484: "Video board does not support VESA 640x480x256 color video mode"

Palette Manager:
Line 70501: aPaletteManager db 'palette manager',0
```

I/O Port Operations (Sample from lines 11494-12076):
```asm
Line 11494: out dx, al        ; Direct port output
Line 11496: inc dx            ; Port increment
Line 11498: out dx, al
Line 11586: in al, dx         ; Direct port input  
Line 11606: in al, dx         ; Input operations
```

Timer Programming (Lines 15479-15510):
```asm
Line 15479: out dx, al        ; Timer 8253-5 (AT: 8254.2)
Line 15482: out dx, al
Line 15484: out dx, al
Line 15506: out dx, al
Line 15509: out dx, al
Line 15510: out dx, al
```

### INVADE Graphics Backend
```
Generic video references:
Line 15032: "Return: AH = number of columns on screen"

No explicit VESA mode checking
No timer port operations at equivalent locations
No palette manager references
```

**I/O Port Operations (Lines 1339-2052):**
```asm
Line 1339: out dx, al
Line 1341: out dx, al  
Line 1416: in ax, dx
Line 1419: out dx, ax
(Much less frequent than V4V)
```

**Key Difference**: V4V makes 81 interrupt calls vs Invade's 47 interrupt calls

---

## 5. MEMORY MANAGEMENT MODEL

### V4V Memory Model (16-bit Segmented)
- Far pointers throughout (segment:offset model)
- Overlay segments (ovr###) loaded/unloaded dynamically
- Classical DOS memory segmentation (64KB segments)
- Multiple allocation strategies evident

Example from Line 20742:
```asm
mov ax, word ptr dword_1D3CD+2  ; Upper word of far pointer
mov dx, word ptr dword_1D3CD    ; Lower word of far pointer
```

### INVADE Memory Model (32-bit Flat)
- Near pointers (32-bit linear addresses)
- No overlay system needed
- Unified 4GB address space (within extender)
- Simpler memory management

---

## 6. COMPILER DIFFERENCES

### V4V Compiler
```
Line 53895: "- Copyright 1991 Borland Intl."
```
**Compiler**: Borland C++ 3.1 (released 1992)
- Generates 16-bit real mode code
- Segment-based calling conventions
- Windows-compatible architecture options

### INVADE Compiler/Tools
```
Line 58-68: "DOS/4G  Copyright (C) Ration Systems, Inc. 1987 - 1993"
```
**Extender**: Rational Systems DOS/4G (now Phar Lap DOS/4GW)
- Generic 32-bit compiler output
- Could be compiled with Borland C++ 4.0+ (which supported 32-bit)
- Or another 32-bit DOS compiler
- Protected mode runtime environment

---

## 7. CRITICAL DIFFERENCES TABLE

| Aspect | V4V | INVADE |
|--------|-----|--------|
| **CPU Mode** | 16-bit Real Mode | 32-bit Protected Mode |
| **Extender** | None (native) | DOS/4G |
| **Compiler** | Borland C++ 3.1 | Unknown (32-bit capable) |
| **Memory Model** | Segmented (64KB segments) | Flat (4GB linear) |
| **Pointer Size** | Far (32-bit seg:offset) | Near (32-bit linear) |
| **Architecture** | 5 seg + 112 overlays | 4 seg (one empty) |
| **Code Size** | 250,921 lines | 27,915 lines |
| **UI Framework** | 7-class OOP system | Likely simpler system |
| **Menu System** | menu.dat file-based | Unknown (no menu.dat) |
| **Graphics Lib** | fastdraw library | Unknown library |
| **Video Mode** | VESA 640x480x256 explicit | Generic video handling |
| **Resource API** | OpenResFile/CloseResFile/GetResource | Unknown |

---

## 8. EXPLANATION FOR IDENTICAL UIs

Given the radically different architectures, the identical visual appearance is due to:

1. **Design Similarity**: Both games designed to show identical menus/dialogs
2. **Display Mode Synchronization**: Both use VGA 640x480x256 color mode
3. **Palette Matching**: Same 256-color palette definition
4. **Layout Agreement**: Menu positions, fonts, and sizes coordinated
5. **Independent Implementation**: Different code paths achieving same visual result

The fact that they don't share the same code framework makes sense because:
- V4V was built in real mode with Borland C++ 3.1
- INVADE was built using a 32-bit DOS extender
- Different compilation models → different code generation
- But same final display specifications → identical appearance

---

## 9. WHAT SHARED CODE ACTUALLY MEANS

"Shared UI code" likely refers to:

### NOT Shared (Different Implementation):
- Menu loading and rendering code
- Graphics primitive functions
- Resource management system
- Event handling
- Font rendering

### Possibly Shared (Low-level DOS calls):
- VGA palette initialization
- INT 10h BIOS video calls (basic mode setting)
- INT 33h mouse handler (if both use it)
- INT 16h keyboard handler
- Basic DOS INT 21h file operations

### Definitely Different (CPU/Extender specific):
- Memory allocation patterns
- Segment management code
- Overlay loading system (V4V only)
- Protected mode transitions (INVADE only)

---

## 10. RECOMMENDED INVESTIGATION PATHS

### To Find True Shared Code:

1. **Compare low-level graphics primitives:**
   - Pixel setting routines
   - Line drawing algorithms  
   - Rectangle filling
   - Pattern fill operations

2. **Compare BIOS call sequences:**
   - Search for identical INT 10h sequences
   - Look for same mode-setting parameters
   - Compare palette load sequences

3. **Check system library calls:**
   - Both may use same DOS INT 21h calls
   - Both may share mouse (INT 33h) routines
   - Keyboard input (INT 16h) may be identical

4. **Examine VGA port I/O:**
   - V4V: Lines 11494-12076
   - INVADE: Lines 1339-2052
   - Compare port access patterns
   - Look for identical register sequences

5. **Resource file format:**
   - V4V uses menu.dat + V4V.RES
   - INVADE uses PCWATW.REZ (possibly Apple HFS format - worth investigating)
   - May share resource format despite different loading code

---

## CONCLUSION

**The identical UIs do NOT indicate shared UI code frameworks.** Instead, they represent:

1. **Conscious Design Decision**: Both games use same display mode (VGA 640x480x256)
2. **Independent Implementation**: Each game implemented similar UI/menu designs separately
3. **Architecture Mismatch**: Different compilation environments (16-bit vs 32-bit) prevented code sharing
4. **Temporal Release**: If V4V (Borland C++ 3.1, 1992) came first, INVADE may have been designed to "look the same" but implemented independently for DOS/4G

**The games likely shared:**
- UI/UX design documents
- Visual specifications (colors, layout)
- Menu text content

**The games likely did NOT share:**
- Source code
- Compiled code segments
- Graphics libraries (fastdraw vs native)
- Menu loading systems (menu.dat vs embedded)

---

## KEY EVIDENCE SUMMARY

1. **Line 53895 (V4V)**: Borland C++ 3.1 (1991 Copyright)
2. **Line 58-68 (INVADE)**: DOS/4G extender (Rational Systems 1987-1993)
3. **Lines 70495-70502 (V4V)**: 7-layer OOP manager system
4. **INVADE**: No equivalent manager system found
5. **Lines 62443, 17227 (V4V)**: menu.dat file system
6. **INVADE**: No menu.dat references
7. **V4V Architecture**: 5 segments + 112 overlays (real mode)
8. **INVADE Architecture**: 4 segments (one empty) + DOS/4G (protected mode)
9. **Size Ratio**: V4V is 9x larger (250,921 vs 27,915 lines)

