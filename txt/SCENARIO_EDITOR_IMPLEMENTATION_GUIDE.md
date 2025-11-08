# Scenario Editor Implementation Guide
## Practical Development Guide for V4V and D-Day Editors

---

## Quick Start Guide

### Which Editor Should You Build First?

**Recommendation: Start with D-Day**

**Reasons:**
1. Working parser already provided (`scenario_parser.py`)
2. Smaller number of scenarios (7 vs 27) for testing
3. Pure binary format (simpler than V4V's text/binary hybrid)
4. Fewer files to test against

---

## Part 1: D-Day Scenario Editor

### Prerequisites

```bash
# Required
Python 3.8+
struct module (built-in)

# Optional but recommended
tkinter (GUI)
hexdump or od (testing)
DOSBox (game testing)
```

### Phase 1: Validate the Parser (Week 1)

**Goal:** Verify the existing parser works correctly

```python
# File: test_parser.py
from scenario_parser import parse_scenario

# Test 1: Parse all scenarios
scenarios = [
    'game/dday/game/SCENARIO/OMAHA.SCN',
    'game/dday/game/SCENARIO/UTAH.SCN',
    'game/dday/game/SCENARIO/BRADLEY.SCN',
    'game/dday/game/SCENARIO/COUNTER.SCN',
    'game/dday/game/SCENARIO/COBRA.SCN',
    'game/dday/game/SCENARIO/STLO.SCN',
    'game/dday/game/SCENARIO/CAMPAIGN.SCN',
]

for scn_file in scenarios:
    print(f"Parsing {scn_file}...")
    data = parse_scenario(scn_file)
    print(f"  Magic: {hex(data['magic'])}")
    print(f"  Counts: {data['counts']}")
    print(f"  Pointers: {data['pointers']}")
    print()
```

**Test Checklist:**
- [ ] All 7 scenarios parse without errors
- [ ] Magic number is 0x1230 for all files
- [ ] Counts array is [17,5,10,8,5,8,0,10,20,5,125,100] for all
- [ ] Pointers are within file bounds
- [ ] Can extract mission text from PTR4 section

### Phase 2: Add Write Functionality (Week 2)

**Goal:** Round-trip testing (read → write → verify)

```python
# Add to scenario_parser.py

def write_scenario(filename, data):
    """Write scenario data back to file"""
    with open(filename, 'wb') as f:
        # Header
        f.write(struct.pack('<H', data['magic']))          # 0x1230

        # Counts (12 x 4-byte integers)
        for count in data['counts']:
            f.write(struct.pack('<I', count))

        # Unknown header bytes
        f.write(data['header_unknown'])

        # Pointers (4 x 4-byte integers)
        # Order: PTR5, PTR6, PTR3, PTR4
        f.write(struct.pack('<I', data['pointers']['PTR5']))
        f.write(struct.pack('<I', data['pointers']['PTR6']))
        f.write(struct.pack('<I', data['pointers']['PTR3']))
        f.write(struct.pack('<I', data['pointers']['PTR4']))

        # Data sections (write in file order: PTR5, PTR6, PTR3, PTR4)
        f.write(data['sections']['PTR5'])
        f.write(data['sections']['PTR6'])
        f.write(data['sections']['PTR3'])
        f.write(data['sections']['PTR4'])

# Test round-trip
original = 'game/dday/game/SCENARIO/OMAHA.SCN'
test_copy = 'OMAHA_TEST.SCN'

data = parse_scenario(original)
write_scenario(test_copy, data)

# Verify files are identical
import filecmp
assert filecmp.cmp(original, test_copy), "Files don't match!"
print("Round-trip successful!")
```

**Test Checklist:**
- [ ] Read → Write produces identical file (binary diff)
- [ ] Test with all 7 scenarios
- [ ] Game loads the written scenario correctly
- [ ] No corruption or crashes

### Phase 3: Mission Text Editor (Week 3)

**Goal:** Extract and modify mission briefing text

```python
def extract_mission_text(data):
    """Extract human-readable text from PTR4 section"""
    ptr4_data = data['sections']['PTR4']

    # Mission text is typically at the end of PTR4
    # Look for printable ASCII strings
    text_blocks = []
    current_text = bytearray()

    for byte in ptr4_data:
        if 32 <= byte <= 126 or byte in [10, 13]:  # Printable ASCII
            current_text.append(byte)
        else:
            if len(current_text) > 20:  # Minimum text length
                text_blocks.append(current_text.decode('ascii', errors='ignore'))
            current_text = bytearray()

    # Last block
    if len(current_text) > 20:
        text_blocks.append(current_text.decode('ascii', errors='ignore'))

    return text_blocks

def replace_mission_text(data, old_text, new_text):
    """Replace mission text in PTR4 section"""
    ptr4_data = data['sections']['PTR4']

    # Find and replace
    old_bytes = old_text.encode('ascii')
    new_bytes = new_text.encode('ascii')

    # Ensure same length (pad with spaces if needed)
    if len(new_bytes) < len(old_bytes):
        new_bytes += b' ' * (len(old_bytes) - len(new_bytes))
    elif len(new_bytes) > len(old_bytes):
        raise ValueError("New text too long! Truncate to fit.")

    # Replace
    ptr4_data = ptr4_data.replace(old_bytes, new_bytes)
    data['sections']['PTR4'] = ptr4_data

    return data

# Example usage
data = parse_scenario('game/dday/game/SCENARIO/OMAHA.SCN')
texts = extract_mission_text(data)

print("Found mission texts:")
for i, text in enumerate(texts):
    print(f"\n--- Text Block {i+1} ---")
    print(text[:200])  # First 200 chars

# Edit text
data = replace_mission_text(
    data,
    old_text="As Commander of the VII Corps",
    new_text="As Commander of the VII Corps"  # Modified version
)

write_scenario('OMAHA_MODIFIED.SCN', data)
```

**Test Checklist:**
- [ ] Can extract all mission text blocks
- [ ] Can replace text without breaking file
- [ ] Game displays modified text correctly
- [ ] No crashes or corruption

### Phase 4: GUI Editor (Week 4)

**Goal:** User-friendly interface

```python
# File: editor_gui.py
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from scenario_parser import parse_scenario, write_scenario

class DdayEditor:
    def __init__(self, root):
        self.root = root
        self.root.title("D-Day Scenario Editor")
        self.current_file = None
        self.current_data = None

        # Menu
        menubar = tk.Menu(root)
        filemenu = tk.Menu(menubar, tearoff=0)
        filemenu.add_command(label="Open", command=self.open_file)
        filemenu.add_command(label="Save", command=self.save_file)
        filemenu.add_command(label="Save As", command=self.save_file_as)
        filemenu.add_separator()
        filemenu.add_command(label="Exit", command=root.quit)
        menubar.add_cascade(label="File", menu=filemenu)
        root.config(menu=menubar)

        # Main frame
        main_frame = ttk.Frame(root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # File info
        ttk.Label(main_frame, text="File:").grid(row=0, column=0, sticky=tk.W)
        self.file_label = ttk.Label(main_frame, text="No file loaded")
        self.file_label.grid(row=0, column=1, sticky=tk.W)

        # Notebook for tabs
        notebook = ttk.Notebook(main_frame)
        notebook.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Tab 1: Header Info
        header_frame = ttk.Frame(notebook, padding="10")
        notebook.add(header_frame, text="Header Info")

        ttk.Label(header_frame, text="Magic Number:").grid(row=0, column=0, sticky=tk.W)
        self.magic_label = ttk.Label(header_frame, text="")
        self.magic_label.grid(row=0, column=1, sticky=tk.W)

        # Tab 2: Mission Text
        text_frame = ttk.Frame(notebook, padding="10")
        notebook.add(text_frame, text="Mission Text")

        self.text_widget = tk.Text(text_frame, width=80, height=30)
        self.text_widget.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        scrollbar = ttk.Scrollbar(text_frame, command=self.text_widget.yview)
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.text_widget.config(yscrollcommand=scrollbar.set)

        # Tab 3: Unit Data (placeholder)
        unit_frame = ttk.Frame(notebook, padding="10")
        notebook.add(unit_frame, text="Unit Data")
        ttk.Label(unit_frame, text="Unit editor coming soon...").pack()

    def open_file(self):
        filename = filedialog.askopenfilename(
            title="Select D-Day Scenario File",
            filetypes=[("Scenario Files", "*.SCN"), ("All Files", "*.*")]
        )

        if filename:
            try:
                self.current_file = filename
                self.current_data = parse_scenario(filename)
                self.update_display()
                self.file_label.config(text=filename)
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load file:\n{e}")

    def update_display(self):
        if self.current_data:
            # Update header info
            self.magic_label.config(text=hex(self.current_data['magic']))

            # Update mission text
            self.text_widget.delete('1.0', tk.END)
            texts = extract_mission_text(self.current_data)
            for text in texts:
                self.text_widget.insert(tk.END, text + "\n\n---\n\n")

    def save_file(self):
        if self.current_file and self.current_data:
            try:
                # Update data from GUI
                # TODO: Implement text editing
                write_scenario(self.current_file, self.current_data)
                messagebox.showinfo("Success", "File saved successfully!")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save file:\n{e}")

    def save_file_as(self):
        if self.current_data:
            filename = filedialog.asksaveasfilename(
                title="Save Scenario As",
                filetypes=[("Scenario Files", "*.SCN"), ("All Files", "*.*")],
                defaultextension=".SCN"
            )

            if filename:
                self.current_file = filename
                self.save_file()

if __name__ == "__main__":
    root = tk.Tk()
    app = DdayEditor(root)
    root.mainloop()
```

**Features to Add:**
- [x] File open/save
- [x] Display header info
- [x] Display mission text
- [ ] Edit mission text
- [ ] Edit unit data (PTR3/PTR4)
- [ ] Validate changes
- [ ] Backup original files

---

## Part 2: V4V Scenario Editor

### Prerequisites

Same as D-Day editor.

### Phase 1: Basic Parser (Week 1)

```python
# File: v4v_scenario_parser.py
import struct

def parse_v4v_scenario(filename):
    """Parse V is for Victory scenario file"""
    with open(filename, 'rb') as f:
        data = f.read()

    # Verify magic number
    magic = struct.unpack('<H', data[0:2])[0]
    if magic != 0x0C0C:
        raise ValueError(f"Invalid magic number: {hex(magic)}")

    # Parse header (128 bytes)
    header = {
        'magic': magic,
        'unknown1': data[2:6],
        'difficulty': data[6],
        'unknown2': data[7],
        'float_constant': struct.unpack('<f', data[8:12])[0],  # Should be 2.05
        'map_width': struct.unpack('<H', data[12:14])[0],
        'map_height': struct.unpack('<H', data[14:16])[0],
        'unknown3': data[16:128],
    }

    # Parse mission text blocks (3 blocks of ~128 bytes each)
    text_blocks = []
    for i in range(3):
        offset = 0x80 + (i * 0x80)
        text_data = data[offset:offset+0x80]
        # Extract null-terminated string
        text = text_data.split(b'\x00')[0].decode('ascii', errors='ignore')
        text_blocks.append(text)

    # Binary data starts at 0x200
    binary_data = data[0x200:]

    return {
        'header': header,
        'mission_texts': text_blocks,
        'binary_data': binary_data,
        'raw_data': data,  # Keep original for safe editing
    }

def write_v4v_scenario(filename, data):
    """Write V4V scenario file"""
    # Start with original data
    output = bytearray(data['raw_data'])

    # Update mission text blocks
    for i, text in enumerate(data['mission_texts']):
        offset = 0x80 + (i * 0x80)
        text_bytes = text.encode('ascii')[:127]  # Max 127 chars + null
        text_bytes += b'\x00' * (128 - len(text_bytes))  # Pad to 128
        output[offset:offset+128] = text_bytes

    # Write file
    with open(filename, 'wb') as f:
        f.write(output)

# Test
data = parse_v4v_scenario('game/v_is_for_victory/game/UBATTACK.SCN')
print(f"Magic: {hex(data['header']['magic'])}")
print(f"Float constant: {data['header']['float_constant']}")
print(f"Map size: {data['header']['map_width']} x {data['header']['map_height']}")
print("\nMission texts:")
for i, text in enumerate(data['mission_texts']):
    print(f"\nBlock {i+1}:")
    print(text)
```

**Test Checklist:**
- [ ] All 27 scenarios parse correctly
- [ ] Magic number is 0x0C0C for all
- [ ] Float constant is 2.05 (±0.01)
- [ ] Mission texts extract correctly
- [ ] Round-trip produces identical file

### Phase 2: Mission Text Editor (Week 2)

```python
def edit_mission_text_gui():
    """Simple GUI for editing mission text"""
    import tkinter as tk
    from tkinter import ttk, filedialog, messagebox

    root = tk.Tk()
    root.title("V4V Mission Text Editor")

    current_data = None
    current_file = None

    def load_file():
        nonlocal current_data, current_file
        filename = filedialog.askopenfilename(
            title="Select V4V Scenario",
            filetypes=[("Scenario Files", "*.SCN")]
        )
        if filename:
            current_file = filename
            current_data = parse_v4v_scenario(filename)

            # Update text widgets
            for i, text in enumerate(current_data['mission_texts']):
                text_widgets[i].delete('1.0', tk.END)
                text_widgets[i].insert('1.0', text)

    def save_file():
        if current_data and current_file:
            # Get text from widgets
            for i in range(3):
                new_text = text_widgets[i].get('1.0', tk.END).strip()
                if len(new_text) > 127:
                    messagebox.showwarning("Warning", f"Text block {i+1} too long! Truncating.")
                    new_text = new_text[:127]
                current_data['mission_texts'][i] = new_text

            # Write file
            write_v4v_scenario(current_file, current_data)
            messagebox.showinfo("Success", "File saved!")

    # Menu
    menu = tk.Menu(root)
    menu.add_command(label="Open", command=load_file)
    menu.add_command(label="Save", command=save_file)
    root.config(menu=menu)

    # Text editors
    text_widgets = []
    for i in range(3):
        frame = ttk.LabelFrame(root, text=f"Mission Text Block {i+1}", padding="10")
        frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        text = tk.Text(frame, height=4, width=80)
        text.pack(fill=tk.BOTH, expand=True)
        text_widgets.append(text)

        ttk.Label(frame, text="Max 127 characters", foreground="gray").pack()

    root.mainloop()

# Run editor
edit_mission_text_gui()
```

### Phase 3: Unit/Location Editor (Weeks 3-4)

This requires deeper reverse engineering of the binary sections. Recommend:

1. Use hex editor to examine unit records
2. Modify one byte at a time in a hex editor
3. Test in game to see what changed
4. Document field meanings
5. Build editor once format is understood

---

## Part 3: Testing Strategy

### Test Suite

```python
# File: test_editors.py
import os
import shutil
import filecmp

def test_scenario_editor(parse_func, write_func, scenario_files):
    """Generic test for scenario editors"""
    results = []

    for scn_file in scenario_files:
        print(f"Testing {scn_file}...")

        # Backup original
        backup = scn_file + ".backup"
        shutil.copy(scn_file, backup)

        try:
            # Test 1: Round-trip
            data = parse_func(scn_file)
            temp_file = scn_file + ".test"
            write_func(temp_file, data)

            if filecmp.cmp(scn_file, temp_file):
                print("  ✓ Round-trip successful")
                results.append((scn_file, "PASS", "Round-trip OK"))
            else:
                print("  ✗ Round-trip failed (files differ)")
                results.append((scn_file, "FAIL", "Files differ"))

            # Cleanup
            if os.path.exists(temp_file):
                os.remove(temp_file)

        except Exception as e:
            print(f"  ✗ Error: {e}")
            results.append((scn_file, "ERROR", str(e)))

        finally:
            # Restore backup
            shutil.copy(backup, scn_file)
            os.remove(backup)

    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    passed = sum(1 for r in results if r[1] == "PASS")
    failed = sum(1 for r in results if r[1] == "FAIL")
    errors = sum(1 for r in results if r[1] == "ERROR")

    print(f"Passed: {passed}/{len(results)}")
    print(f"Failed: {failed}/{len(results)}")
    print(f"Errors: {errors}/{len(results)}")

    return results

# Test D-Day editor
from scenario_parser import parse_scenario, write_scenario
scenarios = [
    'game/dday/game/SCENARIO/OMAHA.SCN',
    'game/dday/game/SCENARIO/UTAH.SCN',
    # ... add all 7
]
test_scenario_editor(parse_scenario, write_scenario, scenarios)

# Test V4V editor
from v4v_scenario_parser import parse_v4v_scenario, write_v4v_scenario
v4v_scenarios = [
    'game/v_is_for_victory/game/UBATTACK.SCN',
    # ... add all 27
]
test_scenario_editor(parse_v4v_scenario, write_v4v_scenario, v4v_scenarios)
```

### Game Testing in DOSBox

```bash
# DOSBox testing procedure

# 1. Mount directories
mount c ~/atomic_ed/game/dday/game
c:

# 2. Run game
INVADE.EXE

# 3. Load modified scenario
# Navigate menus to load OMAHA.SCN

# 4. Verify:
# - Scenario loads without crash
# - Mission text displays correctly
# - Units appear correctly
# - Game plays normally

# 5. Test V4V
mount c ~/atomic_ed/game/v_is_for_victory/game
c:
V4V.EXE
```

---

## Part 4: Common Issues & Solutions

### Issue 1: "Game crashes when loading modified scenario"

**Possible causes:**
- Magic number corrupted
- File size changed unexpectedly
- Checksum mismatch (if exists)
- Pointer to invalid offset

**Solutions:**
1. Binary diff original vs modified
2. Verify magic number intact
3. Check file size matches original (±padding)
4. Validate all offset pointers

### Issue 2: "Text doesn't display correctly"

**Possible causes:**
- Text not null-terminated
- Text exceeds buffer size
- Non-ASCII characters

**Solutions:**
1. Always null-terminate strings
2. Pad with nulls to fixed size
3. Use ASCII only (no Unicode)
4. Test with short text first

### Issue 3: "Round-trip test fails"

**Possible causes:**
- Floating-point rounding
- Padding bytes not preserved
- Endianness issues
- Binary sections modified

**Solutions:**
1. Preserve all unknown bytes exactly
2. Use binary mode for file I/O
3. Check struct pack/unpack endianness ('<' for little-endian)
4. Don't modify binary sections you don't understand

---

## Part 5: Advanced Features

### Feature 1: Scenario Validation

```python
def validate_scenario(data, game_type='dday'):
    """Validate scenario file integrity"""
    errors = []
    warnings = []

    if game_type == 'dday':
        # Check magic
        if data['magic'] != 0x1230:
            errors.append(f"Invalid magic: {hex(data['magic'])}")

        # Check counts
        expected_counts = [17, 5, 10, 8, 5, 8, 0, 10, 20, 5, 125, 100]
        if data['counts'] != expected_counts:
            warnings.append(f"Unusual counts: {data['counts']}")

        # Check pointers in bounds
        file_size = len(data['raw'])
        for ptr_name, offset in data['pointers'].items():
            if offset > file_size:
                errors.append(f"{ptr_name} out of bounds: {offset} > {file_size}")

    elif game_type == 'v4v':
        # Check magic
        if data['header']['magic'] != 0x0C0C:
            errors.append(f"Invalid magic: {hex(data['header']['magic'])}")

        # Check float constant
        expected_float = 2.05
        actual_float = data['header']['float_constant']
        if abs(actual_float - expected_float) > 0.1:
            errors.append(f"Unusual float constant: {actual_float}")

        # Check text lengths
        for i, text in enumerate(data['mission_texts']):
            if len(text) > 127:
                errors.append(f"Text block {i+1} too long: {len(text)} chars")

    return errors, warnings
```

### Feature 2: Batch Processing

```python
def batch_modify_scenarios(scenario_files, modification_func):
    """Apply modification to multiple scenarios"""
    for scn_file in scenario_files:
        print(f"Processing {scn_file}...")

        # Backup
        backup = scn_file + ".bak"
        shutil.copy(scn_file, backup)

        try:
            # Load, modify, save
            data = parse_scenario(scn_file)
            data = modification_func(data)
            write_scenario(scn_file, data)
            print(f"  ✓ Modified successfully")
        except Exception as e:
            print(f"  ✗ Error: {e}")
            # Restore backup
            shutil.copy(backup, scn_file)

# Example: Change all difficulty levels
def set_difficulty(data, difficulty_level):
    if 'header' in data and 'difficulty' in data['header']:
        data['header']['difficulty'] = difficulty_level
    return data

v4v_files = ['game/v_is_for_victory/game/*.SCN']
batch_modify_scenarios(v4v_files, lambda d: set_difficulty(d, 2))
```

### Feature 3: Scenario Comparison

```python
def compare_scenarios(file1, file2):
    """Compare two scenario files"""
    data1 = parse_scenario(file1)
    data2 = parse_scenario(file2)

    differences = []

    # Compare headers
    for key in data1['header']:
        if data1['header'][key] != data2['header'][key]:
            differences.append(f"Header.{key}: {data1['header'][key]} vs {data2['header'][key]}")

    # Compare text
    for i in range(len(data1['mission_texts'])):
        if data1['mission_texts'][i] != data2['mission_texts'][i]:
            differences.append(f"Text block {i+1} differs")

    return differences
```

---

## Conclusion

### Development Timeline

**D-Day Editor:** 4 weeks
- Week 1: Parser validation
- Week 2: Write functionality
- Week 3: Mission text editor
- Week 4: GUI and polish

**V4V Editor:** 4-6 weeks
- Week 1: Basic parser
- Week 2: Mission text editor
- Weeks 3-4: Binary section reverse engineering
- Weeks 5-6: Full editor with unit data

### Success Criteria

- [ ] All scenarios load without modification
- [ ] Round-trip produces identical files
- [ ] Modified text displays in game
- [ ] No crashes or corruption
- [ ] User-friendly GUI
- [ ] Comprehensive documentation

### Next Steps

1. Choose which editor to build first (recommend D-Day)
2. Set up Python development environment
3. Run test suite to validate parser
4. Implement write functionality
5. Test in DOSBox
6. Build GUI
7. Release v1.0!

Good luck with your scenario editor development!
