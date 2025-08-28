#!/usr/bin/env python3
"""
Script to fix remaining B904 exception chaining errors.
"""

import subprocess
import sys

def run_ruff_and_get_errors():
    """Get all remaining B904 errors."""
    result = subprocess.run(
        ["python3", "-m", "ruff", "check", "--select=B904"],
        capture_output=True, text=True, cwd="/Users/al02475493/Documents/ai-script-generator-v3"
    )
    return result.stderr

def apply_common_fixes():
    """Apply common exception chaining fixes."""
    
    # Common patterns for service and internal errors that should preserve the chain
    patterns_to_fix = [
        # Service errors should preserve chain
        ('raise DatabaseError(', 'raise DatabaseError(', ') from e'),
        ('raise ConcurrencyError(', 'raise ConcurrencyError(', ') from e'),
        ('raise ValidationError(', 'raise ValidationError(', ') from e'),
        ('raise NotFoundError(', 'raise NotFoundError(', ') from e'),
        ('raise ChromaStoreError(', 'raise ChromaStoreError(', ') from e'),
        ('raise ConfigurationError(', 'raise ConfigurationError(', ') from e'),
        ('raise RAGServiceError(', 'raise RAGServiceError(', ') from e'),
        ('raise RetrievalError(', 'raise RetrievalError(', ') from e'),
        ('raise EmbeddingError(', 'raise EmbeddingError(', ') from e'),
        ('raise NodeExecutionError(', 'raise NodeExecutionError(', ') from e'),
        ('raise RuntimeError(', 'raise RuntimeError(', ') from e'),
        ('raise ValueError(', 'raise ValueError(', ') from e'),
        ('raise AttributeError(', 'raise AttributeError(', ') from e'),
        ('raise TimeoutError(', 'raise TimeoutError(', ') from e'),
        ('raise asyncio.TimeoutError(', 'raise asyncio.TimeoutError(', ') from e'),
        ('raise ProviderUnavailableError(', 'raise ProviderUnavailableError(', ') from e'),
    ]
    
    # Find all Python files
    import os
    import glob
    
    python_files = []
    for root, dirs, files in os.walk("/Users/al02475493/Documents/ai-script-generator-v3"):
        # Skip certain directories
        skip_dirs = {'.git', '__pycache__', '.pytest_cache', 'node_modules', '.venv', 'venv'}
        dirs[:] = [d for d in dirs if d not in skip_dirs]
        
        for file in files:
            if file.endswith('.py'):
                python_files.append(os.path.join(root, file))
    
    print(f"Processing {len(python_files)} Python files...")
    
    total_fixes = 0
    for filepath in python_files:
        fixes_in_file = 0
        
        try:
            with open(filepath, 'r') as f:
                content = f.read()
            
            original_content = content
            
            # Apply each pattern
            for search_pattern, replace_start, replace_end in patterns_to_fix:
                # Look for the pattern and add exception chaining if not present
                lines = content.split('\n')
                new_lines = []
                
                for i, line in enumerate(lines):
                    if (search_pattern in line and 
                        'from e' not in line and 
                        'from None' not in line and 
                        line.strip().endswith(')')):
                        # This is a raise statement that needs chaining
                        # Check if we're in an except block by looking at previous lines
                        in_except_block = False
                        exception_var = None
                        for j in range(max(0, i-10), i):
                            prev_line = lines[j].strip()
                            if prev_line.startswith('except ') and ' as ' in prev_line:
                                exception_var = prev_line.split(' as ')[-1].rstrip(':').strip()
                                in_except_block = True
                                break
                            elif prev_line.startswith('except ') and prev_line.endswith(':'):
                                in_except_block = True
                                break
                        
                        if in_except_block:
                            if exception_var:
                                new_line = line.rstrip(')') + f') from {exception_var}'
                                new_lines.append(new_line)
                                fixes_in_file += 1
                            else:
                                # No exception variable captured, add 'from e' assuming standard pattern
                                new_line = line.rstrip(')') + ') from e'
                                new_lines.append(new_line)
                                fixes_in_file += 1
                        else:
                            new_lines.append(line)
                    else:
                        new_lines.append(line)
                
                content = '\n'.join(new_lines)
            
            # Write back if changes were made
            if content != original_content:
                with open(filepath, 'w') as f:
                    f.write(content)
                
                if fixes_in_file > 0:
                    print(f"Fixed {fixes_in_file} errors in {filepath}")
                    total_fixes += fixes_in_file
                    
        except Exception as e:
            print(f"Error processing {filepath}: {e}")
            continue
    
    print(f"Total fixes applied: {total_fixes}")

def main():
    print("Applying comprehensive B904 fixes...")
    
    # Get initial count
    initial_output = run_ruff_and_get_errors()
    initial_lines = [line for line in initial_output.split('\n') if 'B904' in line]
    print(f"Initial B904 errors: {len(initial_lines)}")
    
    # Apply fixes
    apply_common_fixes()
    
    # Get final count
    final_output = run_ruff_and_get_errors()
    final_lines = [line for line in final_output.split('\n') if 'B904' in line]
    print(f"Remaining B904 errors: {len(final_lines)}")
    
    if len(final_lines) > 0:
        print("\nRemaining errors to fix manually:")
        for line in final_lines[:10]:  # Show first 10
            if line.strip():
                print(line)
        
        if len(final_lines) > 10:
            print(f"... and {len(final_lines) - 10} more")

if __name__ == "__main__":
    main()