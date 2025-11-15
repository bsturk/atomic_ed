# D-Day Scenario File Format Analysis

## Investigation Date
2025-11-13

## File Structure Overview

### Header (0x00 - 0x5F)
All D-Day scenarios share an identical 96-byte header:

```
Offset    | Field                    | Description
----------|--------------------------|----------------------------------
0x00-0x01 | Signature                | 0x1230 (constant across all scenarios)
0x02-0x47 | Common header data       | Identical in all D-Day scenarios
0x48-0x4B | Pointer 1                | Segment:offset format (~0x17Cxx)
0x4C-0x4F | Pointer 2                | Segment:offset format (~0x17Cxx)
0x50-0x53 | PTR5                     | Points to data section
0x54-0x57 | PTR6                     | Points to another data section
0x58-0x5F | Additional pointers      | Purpose unknown
```

### Zeroed Region (0x60 - 0x7F)
- Always zeroed in D-Day format (32 bytes of 0x00)
- This region contains configuration data in older Crusader/Stalingrad formats
- D-Day uses a different configuration system (see TAG system below)

### Pre-Chunk Area (0x80 - 0x022B)
- Mostly zeros
- Purpose unknown

### Chunk-Based Structure (0x022C - EOF)

**Starting at offset 0x022C**, all D-Day scenarios use a chunk-based format:

```
Chunk Format:
  [size: 16-bit little-endian word]
  [data: 'size' bytes]
  [next chunk starts immediately after]
```

#### Parsing Algorithm:
```
pos = 0x022C
while pos < file_size:
    size = read_word(pos)

    if size == 0:
        pos += 2
        continue

    if size > 20000:
        pos += 2  # Invalid, skip
        continue

    chunk_data_start = pos + 2
    chunk_data_end = pos + 2 + size

    # Process chunk data here

    pos = chunk_data_end
```

## TAG System (First Chunk)

The FIRST chunk (typically 17-114 bytes) contains a TAG-based configuration system.

### Verified Tags:
- `0x2C` (',') - Unknown purpose
- `0x40` ('@') - Loads value into memory location 0xECA
- `0x2D` ('-') - Loads value into memory location 0xECE
- `0x3A` (':') - Loads value into memory location 0xECC
- `0x5E` ('^') - Unknown purpose (found at position +8 in BRADLEY.SCN first chunk)

### Disassembly Evidence:
Function `sub_7CF0` searches for TAG bytes in a string.
Function `sub_6193` parses values after finding a tag.

Code pattern:
```assembly
mov  ax, 3Ah        ; Tag ':'
push ax
push [buffer]
call sub_7CF0       ; Find tag in buffer
; ...
call sub_6193       ; Parse value after tag
mov  ds:0ECCh, ax   ; Store parsed value
```

## Parameter Array Structure

### Location
The parameter array containing the turn count is located in one of the **early large chunks** (size >= 256 bytes), typically the FIRST or SECOND valid chunk after 0x022C.

### Known Locations:

| Scenario     | Chunk# | Chunk Offset | Chunk Size | Array Offset | Turn Count |
|--------------|--------|--------------|------------|--------------|------------|
| BRADLEY.SCN  | 1      | 0x023F       | 512        | 0x0246       | 11         |
| COUNTER.SCN  | 1      | 0x0241       | 1536       | 0x0246       | 17         |
| COBRA.SCN    | 1      | 0x02A5       | 2048       | 0x02EA       | 29         |
| STLO.SCN     | 1      | 0x0245       | 15616      | 0x1462       | 67         |
| UTAH.SCN     | 1      | 0x0289       | 9984       | 0x1F7A       | 155        |
| OMAHA.SCN    | 6      | 0x172B       | 3328       | 0x1976       | 155        |
| CAMPAIGN.SCN | 2      | 0x02ED       | 19456      | 0x2220       | 155        |

### Array Format
The parameter array consists of **12 words (24 bytes)**:

```
Offset  | Field     | Typical Range    | Description
--------|-----------|------------------|----------------------------------
+0      | word[0]   | 21-107           | Unknown parameter
+2      | word[1]   | 1-124            | Unknown parameter
+4      | word[2]   | 28-728           | Unknown parameter
+6      | word[3]   | 1-255            | TURN COUNT ⭐
+8      | word[4]   | varies           | Unknown parameter
+10     | word[5]   | varies           | Unknown parameter
+12     | word[6]   | varies           | Unknown parameter
+14     | word[7]   | varies           | Unknown parameter
+16     | word[8]   | varies           | Unknown parameter
+18     | word[9]   | varies           | Unknown parameter
+20     | word[10]  | varies           | Unknown parameter
+22     | word[11]  | varies           | Unknown parameter (sometimes = turn count)
```

### Identifying Characteristics

**Verified pattern:**
1. **Padding byte**: A 0x00 byte ALWAYS precedes the parameter array
2. **Word alignment**: Arrays always start at EVEN offsets
3. **Value validation**:
   - word[0], word[1], word[2] are all >= 10 and < 1000
   - word[3] (turn count) is in range 1-255
   - NOT suspicious round numbers like 256, 257

### Offset Within Chunk
The array does NOT appear at a fixed offset from chunk start:

| Scenario     | Offset in Chunk |
|--------------|-----------------|
| BRADLEY.SCN  | +5              |
| COUNTER.SCN  | +3              |
| COBRA.SCN    | +67             |
| STLO.SCN     | +4635           |
| UTAH.SCN     | +7407           |
| OMAHA.SCN    | +585            |
| CAMPAIGN.SCN | +7985           |

## Comparison with Previous Games

### Crusader/Stalingrad Format Differences:
1. **0x60-0x7F region**: Contains data (not zeroed)
2. **Chunk structure**: Some scenarios don't have chunk structure at 0x022C
3. **Parameter array**: Found at different locations (often 0x01C4, 0x01CC, 0x0D84)
4. **BW chunks**: Older formats use "BW" signature chunks (code checks for 0x42='B', 0x57='W')

D-Day scenarios do NOT contain "BW" chunks according to analysis.

## Current Limitations

### What We Know:
✅ File uses chunk-based format starting at 0x022C
✅ First chunk contains TAG-based configuration
✅ Parameter array is in early large chunks
✅ Array has 0x00 padding byte before it
✅ Turn count is at word[3] (+6 bytes) in the array

### What We Don't Know:
❌ Exact algorithm game uses to locate the parameter array
❌ Purpose of most parameters in the array
❌ Meaning of data between chunk start and parameter array
❌ Whether there's additional metadata or signature we haven't found

## Recommended Approach

For reading/writing turn counts, use the **known offset table** from TURN_COUNT_FORMAT.md as the authoritative source. The chunk structure explains why offsets vary between scenarios but doesn't provide a programmatic method superior to a lookup table.

## Disassembly Findings

### Turn Count Memory Location
**Memory address: `ds:2Eh` (data segment offset 0x002E)**

The turn count is loaded from the scenario file and stored at this runtime memory location.

### Key Code Locations:
- **Write to ds:2Eh**: Line 10271, 10299 in disasm.txt
  ```assembly
  mov  ds:2Eh, al    ; Store turn count
  ```

- **Comparisons with ds:2Eh**: Found 27+ instances checking against 0x0B (11)
  ```assembly
  cmp  byte ptr ds:2Eh, 0Bh    ; Check if turn count == 11
  ```

### Call Chain (Partial):
1. Scenario file is loaded via file I/O functions (`sub_7B88`, `sub_7B9A`, `sub_7BB2`)
2. Chunk parsing occurs (checking for "MF", "MZ", "BW" signatures)
3. Parameter values are extracted and passed through registers (dx register contains turn count)
4. Function `sub_5E50` receives turn count in dx register
5. Value is stored to `ds:2Eh` for runtime use

### What We Could Not Determine:
1. The exact code that READS word[3] from the parameter array in the file
2. The precise algorithm for locating the parameter array within chunks
3. Whether there's additional metadata or offsets we haven't found

The file loading code path goes deep into protected mode operations and multiple levels of indirection, making it difficult to trace the complete path from file bytes to memory without extensive further analysis.

## Recommendations

### For Reading/Writing Turn Counts:

**Use the known offset lookup table** as documented in TURN_COUNT_FORMAT.md:

| Scenario     | Turn Count Offset |
|--------------|-------------------|
| BRADLEY.SCN  | 0x024C            |
| COUNTER.SCN  | 0x024C            |
| STLO.SCN     | 0x1468            |
| COBRA.SCN    | 0x02F0            |
| UTAH.SCN     | 0x1F80            |
| OMAHA.SCN    | 0x197C            |
| CAMPAIGN.SCN | 0x2226            |

This lookup table is the most reliable method because:
1. ✅ Verified empirically for all D-Day scenarios
2. ✅ Direct access without complex parsing
3. ✅ No risk of false positives
4. ✅ Simple to implement

### Alternative: Heuristic Search

If you need to support unknown scenarios, use a search with strict validation:

1. Parse chunk structure starting at 0x022C
2. For each large chunk (size >= 256), search for:
   - Padding byte 0x00
   - Followed by 12 words where:
     - word[0], word[1], word[2] all >= 10 and < 1000
     - word[3] in range 1-255
     - NOT suspicious values (256, 257)
3. Return word[3] as turn count

Note: This may yield false positives and requires careful validation.

## Further Investigation Needed

1. Complete disassembly trace from file read to parameter array extraction
2. Understanding the data that precedes the array within chunks (appears to be scenario-specific metadata)
3. Mapping the purpose of other parameter array words
4. Determining if there's a chunk index or type field that identifies the parameter chunk
