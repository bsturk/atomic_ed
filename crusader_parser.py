#!/usr/bin/env python3
"""
Crusader (0x0dac) Scenario Format Parser
==========================================

Complete parser for World at War: Crusader scenario files.
Properly handles the unique structure of the Crusader format.

Format Structure:
- 0x00-0x5F: Header (96 bytes) - mixed uint32 values
- 0x60-0x7F: Configuration (32 bytes) - 16-bit parameters
- 0x80+: Data sections at fixed offsets (128-byte aligned)
"""

import struct
import sys
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass


@dataclass
class CrusaderHeader:
    """Crusader format header (0x00-0x5F)"""
    magic: int           # 0x0dac
    reserved: int        # 0x0000
    value_04: int        # 0x88 (constant)
    value_08: int        # Usually 0x01
    value_0c: int        # Usually 0x01
    value_10: int        # ~0x16687 (not a pointer)
    value_14: int        # ~0x16697 (not a pointer)


@dataclass
class CrusaderConfig:
    """Crusader configuration data (0x60-0x7F)"""
    # 16-bit parameters (0x60-0x6F)
    param_0x60: int      # Possibly unit group count
    param_0x62: int      # Possibly player count
    param_0x64: int      # Possibly objective count
    param_0x66: int      # Possibly location/hex count
    param_0x68: int      # Possibly terrain type count
    param_0x6a: int      # Possibly weather/time parameter
    param_0x6c: int      # Possibly reinforcement count
    param_0x6e: int      # Possibly victory condition count
    
    # Bytes (0x70-0x7F)
    byte_0x74: int       # Possibly turn count (usually 0x17 = 23)
    byte_0x76: int       # Possibly another count (usually 0x13 = 19)


class CrusaderScenario:
    """Parser for Crusader (0x0dac) scenario files"""
    
    MAGIC = 0x0dac
    HEADER_SIZE = 0x60
    CONFIG_START = 0x60
    CONFIG_SIZE = 0x20
    DATA_START = 0x80
    BLOCK_SIZE = 0x80  # 128-byte alignment
    
    def __init__(self, filepath: str):
        """Initialize parser with scenario file"""
        self.filepath = Path(filepath)
        self.data = b''
        self.filesize = 0
        
        self.header: Optional[CrusaderHeader] = None
        self.config: Optional[CrusaderConfig] = None
        self.data_blocks: Dict[int, bytes] = {}  # offset -> data
        self.text_sections: List[Tuple[int, str]] = []
        
        self.is_valid = False
        self._load_and_parse()
    
    def _load_and_parse(self):
        """Load and parse scenario file"""
        try:
            with open(self.filepath, 'rb') as f:
                self.data = f.read()
            self.filesize = len(self.data)
        except Exception as e:
            print(f"Error loading file: {e}")
            return
        
        # Validate magic
        if len(self.data) < self.HEADER_SIZE:
            print(f"File too small: {len(self.data)} bytes")
            return
        
        magic = struct.unpack('<H', self.data[0x00:0x02])[0]
        if magic != self.MAGIC:
            print(f"Invalid magic: 0x{magic:04x} (expected 0x{self.MAGIC:04x})")
            return
        
        # Parse header and config
        self._parse_header()
        self._parse_config()
        
        # Extract data blocks
        self._extract_text_sections()
        self._extract_data_blocks()
        
        self.is_valid = True
    
    def _parse_header(self):
        """Parse 96-byte header"""
        magic = struct.unpack('<H', self.data[0x00:0x02])[0]
        reserved = struct.unpack('<H', self.data[0x02:0x04])[0]
        value_04 = struct.unpack('<I', self.data[0x04:0x08])[0]
        value_08 = struct.unpack('<I', self.data[0x08:0x0C])[0]
        value_0c = struct.unpack('<I', self.data[0x0C:0x10])[0]
        value_10 = struct.unpack('<I', self.data[0x10:0x14])[0]
        value_14 = struct.unpack('<I', self.data[0x14:0x18])[0]
        
        self.header = CrusaderHeader(
            magic=magic,
            reserved=reserved,
            value_04=value_04,
            value_08=value_08,
            value_0c=value_0c,
            value_10=value_10,
            value_14=value_14
        )
    
    def _parse_config(self):
        """Parse configuration data (0x60-0x7F)"""
        param_0x60 = struct.unpack('<H', self.data[0x60:0x62])[0]
        param_0x62 = struct.unpack('<H', self.data[0x62:0x64])[0]
        param_0x64 = struct.unpack('<H', self.data[0x64:0x66])[0]
        param_0x66 = struct.unpack('<H', self.data[0x66:0x68])[0]
        param_0x68 = struct.unpack('<H', self.data[0x68:0x6A])[0]
        param_0x6a = struct.unpack('<H', self.data[0x6A:0x6C])[0]
        param_0x6c = struct.unpack('<H', self.data[0x6C:0x6E])[0]
        param_0x6e = struct.unpack('<H', self.data[0x6E:0x70])[0]
        
        byte_0x74 = self.data[0x74]
        byte_0x76 = self.data[0x76]
        
        self.config = CrusaderConfig(
            param_0x60=param_0x60,
            param_0x62=param_0x62,
            param_0x64=param_0x64,
            param_0x66=param_0x66,
            param_0x68=param_0x68,
            param_0x6a=param_0x6a,
            param_0x6c=param_0x6c,
            param_0x6e=param_0x6e,
            byte_0x74=byte_0x74,
            byte_0x76=byte_0x76
        )
    
    def _extract_text_sections(self):
        """Extract text sections from fixed offsets"""
        offset = self.DATA_START
        section_num = 1
        
        while offset < len(self.data) and offset < 0x2000:  # Limit to first 8KB
            # Look for text at this offset
            if self.data[offset] != 0x00:
                # Found text, read until null
                text_bytes = b''
                temp = offset
                while temp < len(self.data) and self.data[temp] != 0x00:
                    text_bytes += bytes([self.data[temp]])
                    temp += 1
                
                if len(text_bytes) >= 4:  # Only include meaningful text
                    try:
                        text = text_bytes.decode('ascii')
                        self.text_sections.append((offset, text))
                    except UnicodeDecodeError:
                        pass
            
            # Move to next aligned block
            offset += self.BLOCK_SIZE
    
    def _extract_data_blocks(self):
        """Extract binary data blocks"""
        # Data blocks typically start after text sections (~0x1000+)
        offset = 0x1000
        
        while offset < len(self.data):
            # Look for non-zero data
            if self.data[offset] != 0x00:
                # Find end of block
                start = offset
                end = offset
                while end < len(self.data) and self.data[end] != 0x00:
                    end += 1
                
                if end - start > 0:
                    self.data_blocks[start] = self.data[start:end]
                
                offset = end
            else:
                offset += 1
    
    def display_header(self):
        """Display header information"""
        if not self.is_valid or not self.header:
            print("File not loaded or invalid")
            return
        
        print("=" * 80)
        print(f"CRUSADER SCENARIO: {self.filepath.name}")
        print("=" * 80)
        print(f"File Size: {self.filesize:,} bytes")
        print()
        
        print("HEADER (0x00-0x5F):")
        print("-" * 80)
        print(f"  Magic         : 0x{self.header.magic:04x}")
        print(f"  Reserved      : 0x{self.header.reserved:04x}")
        print(f"  Value @ 0x04  : 0x{self.header.value_04:08x} ({self.header.value_04})")
        print(f"  Value @ 0x08  : 0x{self.header.value_08:08x} ({self.header.value_08})")
        print(f"  Value @ 0x0C  : 0x{self.header.value_0c:08x} ({self.header.value_0c})")
        print(f"  Value @ 0x10  : 0x{self.header.value_10:08x} ({self.header.value_10})")
        print(f"  Value @ 0x14  : 0x{self.header.value_14:08x} ({self.header.value_14})")
        print()
    
    def display_config(self):
        """Display configuration data"""
        if not self.is_valid or not self.config:
            print("File not loaded or invalid")
            return
        
        print("CONFIGURATION (0x60-0x7F):")
        print("-" * 80)
        print(f"  Param @ 0x60  : {self.config.param_0x60:6d}")
        print(f"  Param @ 0x62  : {self.config.param_0x62:6d}")
        print(f"  Param @ 0x64  : {self.config.param_0x64:6d}")
        print(f"  Param @ 0x66  : {self.config.param_0x66:6d}")
        print(f"  Param @ 0x68  : {self.config.param_0x68:6d}")
        print(f"  Param @ 0x6A  : {self.config.param_0x6a:6d}")
        print(f"  Param @ 0x6C  : {self.config.param_0x6c:6d}")
        print(f"  Param @ 0x6E  : {self.config.param_0x6e:6d}")
        print(f"  Byte @ 0x74   : {self.config.byte_0x74:6d}")
        print(f"  Byte @ 0x76   : {self.config.byte_0x76:6d}")
        print()
    
    def display_text_sections(self):
        """Display extracted text sections"""
        print("TEXT SECTIONS:")
        print("-" * 80)
        
        for offset, text in self.text_sections:
            truncated = text[:70] + "..." if len(text) > 70 else text
            print(f"  0x{offset:06x}: {truncated}")
        
        print()
    
    def display_data_blocks(self):
        """Display extracted data blocks"""
        print("BINARY DATA BLOCKS:")
        print("-" * 80)
        
        for offset, data in sorted(self.data_blocks.items()):
            print(f"  0x{offset:06x}: {len(data):,} bytes")
        
        print()
    
    def analyze_map_dimensions(self) -> Tuple[int, int]:
        """
        Attempt to determine map dimensions from configuration.
        
        For Crusader format, dimensions may be encoded in the 16-bit parameters.
        This is a heuristic approach.
        
        Returns:
            Tuple of (height, width) in hexes
        """
        if not self.config:
            return 125, 100
        
        # Try to infer from config parameters
        # Most Crusader scenarios appear to use 125x100 like standard
        # Some might vary based on param_0x66 or param_0x68
        
        # Default to standard size
        height, width = 125, 100
        
        return height, width


def main():
    """Command-line interface"""
    if len(sys.argv) < 2:
        print("Usage: crusader_parser.py <scenario.scn>")
        sys.exit(1)
    
    filepath = sys.argv[1]
    scenario = CrusaderScenario(filepath)
    
    if not scenario.is_valid:
        print(f"Error: {filepath} is not a valid Crusader scenario")
        sys.exit(1)
    
    scenario.display_header()
    scenario.display_config()
    scenario.display_text_sections()
    scenario.display_data_blocks()
    
    height, width = scenario.analyze_map_dimensions()
    print(f"Estimated Map Dimensions: {height} x {width}")


if __name__ == '__main__':
    main()
