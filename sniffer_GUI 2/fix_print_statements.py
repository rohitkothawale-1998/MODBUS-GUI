#!/usr/bin/env python3
import os
import re
import sys

def fix_print_statements(filename):
    """Convert Python 2 style print(statements to Python 3 format.""")
    with open(filename, 'r', errors='ignore') as f:
        content = f.read()
    
    # First, handle simple print(statements with strings)
    content = re.sub(r'print\s+"([^"]*)"', r'print("\1")', content)
    content = re.sub(r"print\s+'([^']*)'", r"print('\1')", content)
    
    # Handle more complex print(statements with variables)
    content = re.sub(r'print\s+([^(].*?)$', r'print(\1)', content, flags=re.MULTILINE)
    
    # Handle trailing commas in print(statements)
    content = re.sub(r'print\(([^)]*),\)', r'print(\1, end=" ")', content)
    
    # Fix string encoding for hex() method
    content = re.sub(r'\.encode\("hex"\)', r'.hex()', content)
    
    with open(filename, 'w') as f:
        f.write(content)
    
    print(f"Fixed print(statements in {filename}"))

def find_python_files(directory):
    """Find all Python files in the given directory."""
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith('.py'):
                yield os.path.join(root, file)

def main():
    """Main function."""
    for filename in find_python_files('.'):
        try:
            fix_print_statements(filename)
        except Exception as e:
            print(f"Error fixing {filename}: {e}")

if __name__ == '__main__':
    main() 