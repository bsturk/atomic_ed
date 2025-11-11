#!/usr/bin/env python3
"""
Search for patterns in disassembly that might relate to PTR6 usage
"""
import re

def search_patterns():
    """Search for interesting patterns"""

    with open('/src/proj/mods/atomic_ed/disasm.txt', 'rb') as f:
        content = f.read().decode('latin-1', errors='ignore')

    lines = content.split('\n')

    # Look for functions that call multiple times (likely processing loops)
    print("Looking for functions with many calls (likely data processing):")
    print("="*80)

    func_calls = {}
    current_func = None

    for line in lines:
        # Detect function start
        if 'proc near' in line or 'proc far' in line:
            match = re.search(r'(sub_[0-9A-F]+|[a-zA-Z_][a-zA-Z0-9_]*)\s+proc', line)
            if match:
                current_func = match.group(1)
                func_calls[current_func] = {'calls': 0, 'loops': 0, 'compares': 0}

        if current_func and current_func in func_calls:
            if 'call' in line.lower():
                func_calls[current_func]['calls'] += 1
            if 'loop' in line.lower():
                func_calls[current_func]['loops'] += 1
            if 'cmp' in line.lower():
                func_calls[current_func]['compares'] += 1

    # Show functions with many calls and loops
    interesting = [(name, stats) for name, stats in func_calls.items()
                  if stats['loops'] > 0 and stats['calls'] > 5]

    interesting.sort(key=lambda x: x[1]['calls'], reverse=True)

    print("\nFunctions with loops and many calls (data processors):")
    for name, stats in interesting[:20]:
        print(f"  {name:20s}: {stats['calls']:3d} calls, {stats['loops']:2d} loops, {stats['compares']:3d} cmps")

    # Look for comparisons with small values (might be record types)
    print("\n\nLooking for comparisons with small constants (record types?):")
    print("="*80)

    small_val_cmps = {}
    for line in lines:
        # Look for cmp with small immediate values
        match = re.search(r'cmp\s+.*,\s*([0-9]+)h?\s*(?:;|$)', line, re.IGNORECASE)
        if match:
            val_str = match.group(1)
            try:
                val = int(val_str, 16) if 'h' in line else int(val_str)
                if 1 <= val <= 100:  # Small values
                    small_val_cmps[val] = small_val_cmps.get(val, 0) + 1
            except:
                pass

    print("\nMost common small value comparisons:")
    for val, count in sorted(small_val_cmps.items(), key=lambda x: x[1], reverse=True)[:30]:
        print(f"  {val:3d}: {count:3d} times")

    # Look for structure offsets (things like [bx+N])
    print("\n\nLooking for structure field accesses [reg+offset]:")
    print("="*80)

    struct_offsets = {}
    for line in lines:
        matches = re.findall(r'\[(?:bx|si|di|bp)\+([0-9A-Fa-f]+)h?\]', line)
        for match in matches:
            try:
                offset = int(match, 16) if len(match) > 2 else int(match)
                if offset < 200:  # Structure field offsets
                    struct_offsets[offset] = struct_offsets.get(offset, 0) + 1
            except:
                pass

    print("\nMost common structure offsets (likely data structure fields):")
    for offset, count in sorted(struct_offsets.items(), key=lambda x: x[1], reverse=True)[:30]:
        print(f"  +0x{offset:02x}: {count:4d} times")

if __name__ == '__main__':
    search_patterns()
