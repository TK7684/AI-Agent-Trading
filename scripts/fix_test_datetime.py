"""
Script to fix datetime.utcnow() usage in test files.
Replaces with datetime.now(UTC) for timezone-aware datetime usage.
"""

import os
import re
from pathlib import Path


def fix_datetime_utcnow_in_test_file(file_path: Path) -> int:
    """Fix datetime.utcnow() usage in a test file."""
    if not file_path.exists():
        return 0

    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Count occurrences before replacement
    count_before = content.count('datetime.utcnow()')

    if count_before == 0:
        return 0

    # Check if UTC is already imported
    has_utc_import = 'UTC' in content

    # Replace datetime.utcnow() with datetime.now(UTC)
    content = re.sub(r'datetime\.utcnow\(\)', 'datetime.now(UTC)', content)

    # Add UTC to imports if needed
    if not has_utc_import:
        # Find the import line and add UTC
        import_pattern = r'(from datetime import\s+([^\n]+))'
        import_match = re.search(import_pattern, content)

        if import_match:
            import_line = import_match.group(1)
            imported_items = import_match.group(2)

            # Add UTC to the import list
            if imported_items.strip() == '*':
                # If using star import, UTC is already included
                pass
            else:
                # Replace the import line to include UTC
                new_import_line = f"from datetime import {imported_items}, UTC"
                content = content.replace(import_line, new_import_line)
        else:
            # If no datetime import exists, add one
            content = "from datetime import datetime, timedelta, UTC\n" + content

    # Write the fixed content back
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)

    return count_before


def fix_all_test_datetime(base_dir: Path) -> int:
    """Fix datetime.utcnow() usage in all test files."""
    total_fixed = 0

    # Find all test files
    for py_file in base_dir.rglob('test_*.py'):
        fixed_count = fix_datetime_utcnow_in_test_file(py_file)
        if fixed_count > 0:
            print(f"Fixed {fixed_count} occurrences in {py_file}")
            total_fixed += fixed_count

    # Also check the tests/ directory
    tests_dir = base_dir / 'tests'
    if tests_dir.exists():
        for py_file in tests_dir.rglob('*.py'):
            if not py_file.name.startswith('test_'):
                continue

            fixed_count = fix_datetime_utcnow_in_test_file(py_file)
            if fixed_count > 0:
                print(f"Fixed {fixed_count} occurrences in {py_file}")
                total_fixed += fixed_count

    return total_fixed


def main():
    """Main function to fix datetime.utcnow() usage in tests."""
    base_dir = Path(__file__).parent.parent
    print(f"Searching for datetime.utcnow() in test files in {base_dir}...")

    total_fixed = fix_all_test_datetime(base_dir)
    print(f"Total fixed: {total_fixed} occurrences")


if __name__ == '__main__':
    main()
