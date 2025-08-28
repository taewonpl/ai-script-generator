#!/usr/bin/env python3
"""
Script to systematically fix B904 exception chaining errors throughout the codebase.
"""

import subprocess
import re
import os
from pathlib import Path

def run_ruff_check():
    """Run ruff check for B904 errors and return the output."""
    try:
        result = subprocess.run(
            ["python3", "-m", "ruff", "check", "--select=B904"],
            capture_output=True,
            text=True,
            cwd="/Users/al02475493/Documents/ai-script-generator-v3"
        )
        return result.stderr  # ruff outputs to stderr
    except subprocess.CalledProcessError as e:
        return e.stderr

def parse_ruff_output(output):
    """Parse ruff output to extract file locations and line numbers."""
    errors = []
    lines = output.split('\n')
    
    for line in lines:
        if 'B904' in line:
            # Extract file path and line number
            match = re.match(r'^(.+):(\d+):\d+: B904', line)
            if match:
                file_path = match.group(1)
                line_num = int(match.group(2))
                errors.append((file_path, line_num))
    
    return errors

def get_except_block_context(file_path, line_num):
    """Get the context around the except block to understand the exception variable."""
    try:
        with open(file_path, 'r') as f:
            lines = f.readlines()
        
        # Find the except line that precedes the raise
        for i in range(line_num - 1, max(0, line_num - 10), -1):
            line = lines[i].strip()
            if line.startswith('except ') and ' as ' in line:
                # Extract exception variable name
                match = re.search(r'except .+ as (\w+):', line)
                if match:
                    return match.group(1)
            elif line.startswith('except ') and line.endswith(':'):
                # No exception variable captured
                return None
                
        return None
    except:
        return None

def fix_raise_statement(file_path, line_num, exception_var):
    """Fix a single raise statement by adding 'from e' or appropriate chaining."""
    try:
        with open(file_path, 'r') as f:
            lines = f.readlines()
        
        if line_num <= len(lines):
            original_line = lines[line_num - 1]
            
            # Check if already fixed
            if ' from ' in original_line:
                return False
            
            # Add appropriate exception chaining
            if exception_var:
                fixed_line = original_line.rstrip() + f' from {exception_var}\n'
            else:
                # If no exception variable, we need to add one
                # This is more complex and needs manual review
                return False
            
            lines[line_num - 1] = fixed_line
            
            with open(file_path, 'w') as f:
                f.writelines(lines)
            
            return True
        
    except Exception as e:
        print(f"Error fixing {file_path}:{line_num}: {e}")
        return False

def main():
    print("Fixing B904 exception chaining errors...")
    
    # Get initial error count
    output = run_ruff_check()
    errors = parse_ruff_output(output)
    
    print(f"Found {len(errors)} B904 errors to fix")
    
    fixed_count = 0
    for file_path, line_num in errors:
        # Get exception variable context
        exception_var = get_except_block_context(file_path, line_num)
        
        if exception_var:
            if fix_raise_statement(file_path, line_num, exception_var):
                fixed_count += 1
                print(f"Fixed {file_path}:{line_num}")
            else:
                print(f"Could not auto-fix {file_path}:{line_num}")
        else:
            print(f"Manual review needed for {file_path}:{line_num} - no exception variable")
    
    print(f"Fixed {fixed_count} errors automatically")
    
    # Check final count
    final_output = run_ruff_check()
    final_errors = parse_ruff_output(final_output)
    print(f"Remaining errors: {len(final_errors)}")

if __name__ == "__main__":
    main()