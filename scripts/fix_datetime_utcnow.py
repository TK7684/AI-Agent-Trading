"""
Script to fix all datetime.now(UTC) usage in the codebase.
Replaces with datetime.now(UTC) for timezone-aware datetime usage.
"""

import os
import re
from pathlib import Path


def fix_datetime_utcnow_in_file(file_path: Path) -> int:
    """Fix datetime.now(UTC) usage in a single file."""
    if not file_path.exists():
        return 0

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except PermissionError:
        print(f"Permission denied for {file_path}, skipping...")
        return 0

    # Count occurrences before replacement
    count_before = content.count('datetime.now(UTC)')

    if count_before == 0:
        return 0

    # Check if UTC is already imported
    needs_import = 'from datetime import' in content and 'UTC' not in content

    # Replace datetime.now(UTC) with datetime.now(UTC)
    content = re.sub(r'datetime\.utcnow\(\)', 'datetime.now(UTC)', content)

    # Add UTC to imports if needed
    if needs_import:
        # Add a separate import for UTC to avoid complex parsing
        content = re.sub(r'(from datetime import\s+[^\n]+)', r'\1\nfrom datetime import UTC', content)

    # Write the fixed content back
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)

    return count_before


def fix_all_datetime_utcnow(base_dir: Path) -> int:
    """Fix datetime.now(UTC) usage in all Python files."""
    total_fixed = 0

    # Find all Python files
    for py_file in base_dir.rglob('*.py'):
        # Skip test files for now to avoid interfering with test fixes
        if 'test_' in py_file.name or 'tests' in str(py_file) or 'test_results' in str(py_file):
            continue

        # Skip vendor/external libraries
        if 'site-packages' in str(py_file) or '__pycache__' in str(py_file):
            continue

        try:
            fixed_count = fix_datetime_utcnow_in_file(py_file)
            if fixed_count > 0:
                print(f"Fixed {fixed_count} occurrences in {py_file}")
                total_fixed += fixed_count
        except Exception as e:
            print(f"Error processing {py_file}: {str(e)}")

    return total_fixed


def main():
    """Main function to fix datetime.now(UTC) usage."""
    base_dir = Path(__file__).parent.parent
    print(f"Searching for datetime.now(UTC) in {base_dir}...")

    total_fixed = fix_all_datetime_utcnow(base_dir)
    print(f"Total fixed: {total_fixed} occurrences")


if __name__ == '__main__':
    main()
