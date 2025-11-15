# D-Day Scenario Turn Count Storage Format (FINAL SPECIFICATION)

## Summary

The turn count in D-Day (.SCN) scenario files is stored at **word[3]** (offset +6 bytes) within a **parameter array** structure that is located inside a **chunk-based file format** starting at offset **0x022C**.

## Discovery Date
2025-11-12

## File Format: Chunk Structure

### Overview
D-Day scenario files use a chunk-based format starting at offset 0x022C. Each chunk has the structure:

```
[size: 16-bit little-endian word]
[data: 'size' bytes]
```

### Chunk Format Details

**Starting offset:** 0x022C (fixed across all scenarios)

**Chunk structure:**
```
Offset    | Field        | Description
----------|--------------|----------------------------------
+0        | size (word)  | Size of chunk data in bytes
+2        | data         | Chunk data ('size' bytes)
+2+size   | next chunk   | Next chunk starts here
```

### Reading Algorithm

To find the turn count parameter array:

1. **Start at offset 0x022C**
2. **Read chunks sequentially:**
   - Read size word at current offset
   - If size == 0 or size > 20000, skip this word and try next
   - Calculate chunk data range: [offset+2, offset+2+size)
   - Move to next chunk: offset = offset + 2 + size
3. **Search for parameter array in chunk data:**
   - Check if chunk contains a valid parameter array
   - Validation: word[0], word[1], word[2] should be < 1000
   - Validation: word[3] should be in range 1-255 (turn count)
4. **Read turn count:**
   - Turn count = word[3] of parameter array (16-bit word at array_offset + 6)

### Parameter Array Structure

Once located, the parameter array consists of 12 words (24 bytes):

```
Offset  | Field     | Description
--------|-----------|----------------------------------
+0      | word[0]   | Unknown parameter (typically 21-107)
+2      | word[1]   | Unknown parameter (typically 1-124)
+4      | word[2]   | Unknown parameter (typically 28-728)
+6      | word[3]   | **TURN COUNT** ⭐ (range: 1-255)
+8      | word[4]   | Unknown parameter
+10     | word[5]   | Unknown parameter
+12     | word[6]   | Unknown parameter
+14     | word[7]   | Unknown parameter
+16     | word[8]   | Unknown parameter
+18     | word[9]   | Unknown parameter
+20     | word[10]  | Unknown parameter
+22     | word[11]  | Unknown parameter
```

## Verified Locations

| Scenario      | Chunk# | Chunk Offset | Array in Chunk | Turn Value |
|---------------|--------|--------------|----------------|------------|
| BRADLEY.SCN   | 1      | 0x023F       | +5 (0x0005)    | 11         |
| COUNTER.SCN   | 1      | 0x0241       | +3 (0x0003)    | 17         |
| COBRA.SCN     | 1      | 0x02A5       | +67 (0x0043)   | 29         |
| STLO.SCN      | 1      | 0x0245       | +4635 (0x121B) | 67         |
| UTAH.SCN      | 1      | 0x0289       | +7407 (0x1CEF) | 155        |
| CAMPAIGN.SCN  | 2      | 0x02ED       | +7985 (0x1F31) | 155        |
| OMAHA.SCN     | 6      | 0x172B       | +585 (0x0249)  | 155        |

**Note:** The chunk number and offset within chunk vary by scenario, but the algorithm is deterministic: scan chunks from 0x022C until the parameter array is found.

## Implementation

### Reading Turn Count (Python)

```python
import struct

def find_turn_count(scenario_data):
    """Find and return turn count from scenario file data."""
    pos = 0x022C

    while pos < len(scenario_data) - 24:
        # Read chunk size
        size = struct.unpack('<H', scenario_data[pos:pos+2])[0]

        # Skip invalid sizes
        if size == 0 or size > 20000:
            pos += 2
            continue

        chunk_data_start = pos + 2
        chunk_data_end = chunk_data_start + size

        # Search for parameter array in this chunk
        # Array must be word-aligned and have space for 12 words
        for array_offset in range(chunk_data_start, chunk_data_end - 24, 2):
            # Read potential parameter array
            words = struct.unpack('<12H', scenario_data[array_offset:array_offset+24])

            # Validate: word[0-2] < 1000, word[3] in range 1-255
            if (words[0] < 1000 and words[1] < 1000 and words[2] < 1000 and
                1 <= words[3] <= 255):
                # Found it! Return turn count
                return words[3], array_offset

        # Move to next chunk
        pos = chunk_data_end

    return None, None

def read_turn_count(scenario_file):
    """Read turn count from a scenario file."""
    with open(scenario_file, 'rb') as f:
        data = f.read()

    turn_count, offset = find_turn_count(data)
    if turn_count:
        print(f"Turn count: {turn_count} at offset 0x{offset+6:04X}")
        return turn_count
    else:
        print("Turn count not found")
        return None
```

### Writing Turn Count (Python)

```python
def write_turn_count(scenario_file, new_turn_count):
    """Write a new turn count to a scenario file."""
    if not (1 <= new_turn_count <= 255):
        raise ValueError("Turn count must be between 1 and 255")

    with open(scenario_file, 'rb') as f:
        data = bytearray(f.read())

    # Find the parameter array
    turn_count, array_offset = find_turn_count(data)
    if array_offset is None:
        raise ValueError("Could not locate parameter array")

    # Calculate turn count offset (word[3] = array_offset + 6)
    turn_offset = array_offset + 6

    # Write new turn count
    struct.pack_into('<H', data, turn_offset, new_turn_count)

    # Write back to file
    with open(scenario_file, 'wb') as f:
        f.write(data)

    print(f"Updated turn count from {turn_count} to {new_turn_count}")
    return True
```

## Key Differences from Previous Understanding

### What We Thought:
- Turn count was at "random" offsets varying by scenario
- No clear pattern between scenarios
- Required hardcoded offset table for each scenario

### What It Actually Is:
- Turn count is inside a **deterministic chunk-based file format**
- All scenarios use the same format starting at **0x022C**
- The parameter array is **searched for** within chunks, not at a fixed offset
- The game likely uses the same search algorithm we discovered

## File Format Context

### Header (0x00 - 0x5F)
- **0x00-0x47:** Common header (identical across all scenarios)
- **0x48-0x5F:** Section pointers (PTR3-PTR6)
  - 0x48: Pointer 1 (segment:offset format, ~0x17Cxx)
  - 0x4C: Pointer 2 (segment:offset format, ~0x17Cxx)
  - 0x50: PTR5 - Points to a data section
  - 0x54: PTR6 - Points to another data section

### Zeroed Region (0x60 - 0x7F)
- Always zeroed in D-Day format
- This was used in earlier Crusader formats but not in D-Day

### Chunk Data (0x80 - 0x022B)
- Unknown data/padding
- Appears to be mostly zeros

### Chunk Structure (0x022C - EOF)
- **Starts at 0x022C** with size-prefixed chunks
- Parameter array containing turn count is in one of these chunks
- Additional game data follows in subsequent chunks

## Notes

- The offset of the parameter array within its chunk varies significantly (from +3 to +7985 bytes)
- Some scenarios (like OMAHA) have many small chunks before the one containing the array
- Other scenarios (like BRADLEY/COUNTER) have the array in the first or second chunk
- The chunk-based format suggests the file is dynamically structured based on scenario content
- Larger/more complex scenarios tend to have more chunks and later array positions

## Testing

All seven included D-Day scenarios have been verified:
- ✓ BRADLEY.SCN
- ✓ COUNTER.SCN
- ✓ STLO.SCN
- ✓ COBRA.SCN
- ✓ UTAH.SCN
- ✓ OMAHA.SCN
- ✓ CAMPAIGN.SCN

The search algorithm successfully locates the turn count in all scenarios.
