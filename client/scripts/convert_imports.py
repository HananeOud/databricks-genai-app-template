#!/usr/bin/env python3
"""Convert @/ imports to relative imports in TypeScript/TSX files."""

import os
import re
from pathlib import Path

SRC_DIR = Path(__file__).parent.parent / "src"

def get_relative_path(from_file: Path, to_path: str) -> str:
    """Calculate relative path from from_file to to_path (which starts with @/)."""
    # Remove @/ prefix
    target = to_path[2:]  # Remove "@/"

    # Get the directory of the importing file relative to src
    from_dir = from_file.parent.relative_to(SRC_DIR)

    # Calculate relative path
    # Go up from from_dir to src, then down to target
    up_count = len(from_dir.parts)

    if up_count == 0:
        rel_path = "./" + target
    else:
        rel_path = "../" * up_count + target

    return rel_path

def process_file(file_path: Path) -> bool:
    """Process a single file and convert @/ imports to relative imports."""
    content = file_path.read_text()

    # Pattern to match imports with @/
    pattern = r'''(from\s+['"])(@/[^'"]+)(['"])'''

    def replace_import(match):
        prefix = match.group(1)
        import_path = match.group(2)
        suffix = match.group(3)

        rel_path = get_relative_path(file_path, import_path)
        return f"{prefix}{rel_path}{suffix}"

    new_content = re.sub(pattern, replace_import, content)

    if new_content != content:
        file_path.write_text(new_content)
        return True
    return False

def main():
    """Main function to process all TypeScript/TSX files."""
    files_processed = 0
    files_modified = 0

    for ext in ["*.tsx", "*.ts"]:
        for file_path in SRC_DIR.rglob(ext):
            files_processed += 1
            if process_file(file_path):
                files_modified += 1
                print(f"Modified: {file_path.relative_to(SRC_DIR)}")

    print(f"\nProcessed {files_processed} files, modified {files_modified} files")

if __name__ == "__main__":
    main()
