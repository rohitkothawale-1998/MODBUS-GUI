#!/usr/bin/env python3
import re
import os

def fix_print_statements(content):
    """Convert Python 2 style print statements to Python 3 format."""
    # Fix various forms of print statements
    content = re.sub(r'print\s+"([^"]*)"', r'print("\1")', content)
    content = re.sub(r"print\s+'([^']*)'", r"print('\1')", content)
    content = re.sub(r'print\s+\(([^)]*)\)', r'print(\1)', content)
    
    # Fix print with trailing comma (becomes end=" ")
    content = re.sub(r'print\s+(.*?),\s*$', r'print(\1, end=" ")', content, flags=re.MULTILINE)
    
    # Fix print with expressions
    content = re.sub(r'print\s+([^(].*?)$', r'print(\1)', content, flags=re.MULTILINE)
    
    return content

def fix_string_literals(content):
    """Convert string literals to bytes literals where needed."""
    # Convert hex string literals used for binary communication
    content = re.sub(r'"\\\x([0-9a-fA-F]{2})', r'b"\\\x\1', content)
    content = re.sub(r'\\x([0-9a-fA-F]{2})"', r'\\x\1"', content)
    
    # Fix specific cases of string literal concatenation with bytes
    content = re.sub(r'StatusReq = "\\xFE"', r'StatusReq = b"\\xFE"', content)
    content = re.sub(r'StatusReq \+= "\\x([0-9a-fA-F]{2})"', r'StatusReq += b"\\x\1"', content)
    
    # Fix multi-byte hex literals
    content = re.sub(r'StatusReq \+= "(\\x[0-9a-fA-F]{2})+?"', r'StatusReq += b"\1"', content)
    
    return content

def fix_hex_decoding(content):
    """Fix .decode('hex') which is removed in Python 3."""
    # Replace .decode('hex') with bytes.fromhex()
    content = re.sub(r'\.decode\(\'hex\'\)', r'.hex()', content)
    
    # Fix specific patterns for epochsecs hex conversion
    content = re.sub(r'epochsecs = str\(hex\(int\(time\.time\(\)\)\)\)\[2:\]', 
                    r'epochsecs = format(int(time.time()), "x")', content)
    content = re.sub(r'epochstr = epochsecs\.decode\(\'hex\'\)',
                    r'epochstr = bytes.fromhex(epochsecs)', content)
    
    # Fix other hex conversions
    content = re.sub(r'(\w+)\.decode\(\'hex\'\)', r'bytes.fromhex(\1)', content)
    content = re.sub(r'macstr = tempstr\.decode\(\'hex\'\)',
                    r'macstr = bytes.fromhex(tempstr)', content)
    
    return content

def fix_exception_handling(content):
    """Update exception handling syntax."""
    # Change 'except Exception, e' to 'except Exception as e'
    content = re.sub(r'except\s+(\w+),\s*(\w+)', r'except \1 as \2', content)
    
    return content

def fix_dict_methods(content):
    """Update dictionary method usage."""
    # Change dict.has_key() to 'in' operator
    content = re.sub(r'\.has_key\((.*?)\)', r' in \1', content)
    
    return content

def fix_file_handling(content):
    """Update file() to open()."""
    content = re.sub(r'f = file\((.*?), \'([rwa])\'\)', r'f = open(\1, \'\2\')', content)
    
    return content

def fix_unicode_handling(content):
    """Handle unicode vs. str changes in Python 3."""
    # Change type() == unicode to isinstance() with str
    content = re.sub(r'type\((.*?)\) == unicode', r'isinstance(\1, str)', content)
    
    return content

def fix_encode_hex(content):
    """Update .encode("hex") to .hex()."""
    content = re.sub(r'\.encode\("hex"\)', r'.hex()', content)
    
    # Specially handle byte.hex() conversions for int conversions
    content = re.sub(r'int\((\w+)\.hex\(\), 16\)', r'int.from_bytes(\1, byteorder="big")', content)
    
    return content

def fix_bytes_handling(content):
    """Handle bytes/string compatibility."""
    # Add proper bytes handling for string operations
    content = re.sub(r'text\.replace\(\'\\r\', \'\\n\'\)', r'text.replace(b\'\\r\', b\'\\n\')', content)
    content = re.sub(r'text\.replace\(\'\\r\\n\', \'\\n\'\)', r'text.replace(b\'\\r\\n\', b\'\\n\')', content)
    
    # Fix serial.write() calls with string literals
    content = re.sub(r'self\.serial\.write\("(.*?)"\)', r'self.serial.write(b"\1")', content)
    
    return content

def fix_map_filter(content):
    """Convert map() and filter() to explicit list comprehensions."""
    # Make map() return a list for Python 3 compatibility
    content = re.sub(r'hex_chars = map\(hex, map\(ord, s\)\)', r'hex_chars = list(map(hex, map(ord, s)))', content)
    
    return content

def fix_inspect_function(content):
    """Fix the inspect function that handles binary data."""
    old_inspect = r'''def inspect\(s\):
    hex_chars = map\(hex, map\(ord, s\)\)
    counter = 0
    print\(hex_chars\)
    for c in hex_chars:
        print\("\{ "\), counter, ", ", c, " \}"  
\tcounter\+=1'''
    
    new_inspect = '''def inspect(s):
    hex_chars = list(map(hex, [b if isinstance(b, int) else ord(b) for b in s]))
    counter = 0
    print(hex_chars)
    for c in hex_chars:
        print("{ ", counter, ", ", c, " }")
        counter += 1'''
    
    content = re.sub(old_inspect, new_inspect, content)
    return content

def fix_empty_string_comparison(content):
    """Fix empty string comparison for file read operations."""
    content = re.sub(r"record == ''", r"record == b''", content)
    content = re.sub(r"filename == ''", r"filename == ''", content)  # Keep string comparisons as strings
    
    return content

def fix_checksum_function(content):
    """Fix the checksum function for bytes handling."""
    old_checksum = r'''def checksum\(self, s\):
      return pack\('B', sum\(unpack\(str\(str\(len\(s\)\)\+"B"\), s\)\)%256\)'''
    
    new_checksum = '''def checksum(self, s):
      return pack('B', sum(unpack(str(len(s))+"B", s))%256)'''
    
    content = re.sub(old_checksum, new_checksum, content)
    return content

def fix_imageinfo_function(content):
    """Fix the imageInfo function for bytes handling."""
    old_imageinfo = r'''def imageInfo\(filename\):
    input = open\(filename, 'rb'\)
    record = input.read\(calcsize\(imageInfo_format\)\)
    if record == '':
        input.close\(\)
    result_list = unpack\(imageInfo_format, record\)
    return result_list'''
    
    new_imageinfo = '''def imageInfo(filename):
    input = open(filename, 'rb')
    record = input.read(calcsize(imageInfo_format))
    if record == b'':
        input.close()
    result_list = unpack(imageInfo_format, record)
    return result_list'''
    
    content = re.sub(old_imageinfo, new_imageinfo, content)
    return content

def convert_file(filename):
    """Apply all fixes to the specified file."""
    print(f"Converting {filename} to Python 3...")
    
    with open(filename, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
    
    # Create backup
    backup_file = filename + '.py2bak'
    with open(backup_file, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"Created backup: {backup_file}")
    
    # Apply fixes
    content = fix_print_statements(content)
    content = fix_string_literals(content)
    content = fix_hex_decoding(content)
    content = fix_exception_handling(content)
    content = fix_dict_methods(content)
    content = fix_file_handling(content)
    content = fix_unicode_handling(content)
    content = fix_encode_hex(content)
    content = fix_bytes_handling(content)
    content = fix_map_filter(content)
    content = fix_empty_string_comparison(content)
    content = fix_checksum_function(content)
    content = fix_imageinfo_function(content)
    content = fix_inspect_function(content)
    
    # Write converted file
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"Conversion complete: {filename}")

if __name__ == "__main__":
    convert_file("seWSNView.py") 