#!/usr/bin/env python3
"""
Final comprehensive fix for all remaining B904 errors.
"""

import subprocess
import re
import os

def run_ruff_check():
    """Get remaining B904 errors"""
    result = subprocess.run(
        ["python3", "-m", "ruff", "check", "--select=B904"],
        capture_output=True, text=True,
        cwd="/Users/al02475493/Documents/ai-script-generator-v3"
    )
    return result.stderr

def fix_file(filepath, line_num):
    """Fix a specific B904 error in a file"""
    try:
        with open(filepath, 'r') as f:
            lines = f.readlines()
        
        if line_num > len(lines):
            return False
            
        line = lines[line_num - 1].strip()
        
        # Skip if already fixed
        if ' from ' in line:
            return False
            
        # Determine if this is in a try/except block and what exception variable is used
        exception_var = None
        for i in range(max(0, line_num - 10), line_num - 1):
            prev_line = lines[i].strip()
            if prev_line.startswith('except ') and ' as ' in prev_line:
                # Extract the exception variable
                parts = prev_line.split(' as ')
                if len(parts) == 2:
                    exception_var = parts[1].rstrip(':').strip()
                    break
                    
        # Check if this is an HTTPException (API error)
        if 'HTTPException' in line and exception_var:
            # For HTTPException, use from None to suppress internal details
            lines[line_num - 1] = lines[line_num - 1].rstrip() + ' from None\n'
        elif exception_var and 'raise' in line:
            # For other exceptions, preserve the chain with from e
            lines[line_num - 1] = lines[line_num - 1].rstrip() + f' from {exception_var}\n'
        else:
            # Default case
            return False
            
        with open(filepath, 'w') as f:
            f.writelines(lines)
            
        return True
        
    except Exception as e:
        print(f"Error fixing {filepath}:{line_num}: {e}")
        return False

def main():
    print("Running final B904 fix...")
    
    # Get all B904 errors
    output = run_ruff_check()
    if not output.strip():
        print("No B904 errors found!")
        return
        
    lines = output.split('\n')
    fixes_applied = 0
    
    for line in lines:
        if 'B904' not in line:
            continue
            
        # Parse the error line to extract file path and line number
        match = re.match(r'^([^:]+):(\d+):\d+: B904', line)
        if not match:
            continue
            
        filepath = match.group(1)
        line_num = int(match.group(2))
        
        # Apply fix
        if fix_file(filepath, line_num):
            fixes_applied += 1
            print(f"Fixed {filepath}:{line_num}")
    
    print(f"Applied {fixes_applied} fixes")
    
    # Check final count
    final_output = run_ruff_check()
    final_lines = [l for l in final_output.split('\n') if 'B904' in l]
    print(f"Remaining B904 errors: {len(final_lines)}")

if __name__ == "__main__":
    main()