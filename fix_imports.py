"""
Script to convert relative imports to absolute imports in Python files.
"""
import os
import re
from pathlib import Path

def convert_imports_in_file(file_path: Path, project_root: Path) -> None:
    """Convert relative imports to absolute imports in a single file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Skip if already using absolute imports
        if 'from .' not in content and 'import .' not in content:
            return
            
        # Get the relative path from project root to the file's directory
        rel_path = file_path.parent.relative_to(project_root)
        
        # Convert relative imports to absolute
        lines = content.split('\n')
        modified = False
        
        for i, line in enumerate(lines):
            # Handle 'from .module import ...' and 'from ..module import ...'
            if line.strip().startswith('from .'):
                # Count the number of parent references (..)
                parts = line.split()
                if len(parts) >= 2 and parts[0] == 'from':
                    module_path = parts[1]
                    if module_path.startswith('.'):
                        # Calculate the absolute path
                        dot_count = len(module_path) - len(module_path.lstrip('.'))
                        module_path = module_path.lstrip('.')
                        
                        # Get the parent directories
                        parent_parts = list(rel_path.parts)
                        if dot_count > 1:
                            parent_parts = parent_parts[:-(dot_count - 1)]
                        
                        # Create the new import path
                        new_path = '.'.join(parent_parts + [module_path])
                        if new_path.endswith('.'):
                            new_path = new_path[:-1]
                            
                        # Update the line
                        lines[i] = line.replace(parts[1], new_path, 1)
                        modified = True
        
        # Write back if modified
        if modified:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(lines))
            print(f"Updated imports in {file_path}")
            
    except Exception as e:
        print(f"Error processing {file_path}: {str(e)}")

def main():
    project_root = Path(__file__).parent.absolute()
    
    # Find all Python files in the project, excluding the virtual environment
    python_files = []
    for root, dirs, files in os.walk(project_root):
        # Skip virtual environment directories
        if '.venv' in dirs:
            dirs.remove('.venv')
        if 'venv' in dirs:
            dirs.remove('venv')
        if '__pycache__' in dirs:
            dirs.remove('__pycache__')
            
        for file in files:
            if file.endswith('.py') and not file.startswith('__'):
                file_path = Path(root) / file
                # Only include files in the project root and its subdirectories
                if project_root in file_path.parents or file_path.parent == project_root:
                    python_files.append(file_path)
    
    print(f"Found {len(python_files)} Python files to process")
    
    # Process each file
    for file_path in python_files:
        convert_imports_in_file(file_path, project_root)

if __name__ == "__main__":
    main()
