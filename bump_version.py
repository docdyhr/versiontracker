#!/usr/bin/env python3
"""
Version bumping script for VersionTracker.

Usage:
    python bump_version.py [major|minor|patch]
"""

import argparse
import re
import sys
from datetime import datetime
from pathlib import Path


def parse_version(version_str):
    """Parse version string into components."""
    match = re.match(r"(\d+)\.(\d+)\.(\d+)", version_str)
    if not match:
        return None
    return tuple(map(int, match.groups()))


def bump_version(version_tuple, bump_type):
    """Bump version based on type."""
    major, minor, patch = version_tuple
    if bump_type == "major":
        return (major + 1, 0, 0)
    elif bump_type == "minor":
        return (major, minor + 1, 0)
    elif bump_type == "patch":
        return (major, minor, patch + 1)
    return version_tuple


def get_current_version():
    """Get current version from __init__.py file."""
    init_file = Path(__file__).parent / "versiontracker" / "__init__.py"
    with open(init_file, encoding="utf-8") as f:
        content = f.read()
        match = re.search(r'__version__\s*=\s*["\']([^"\']+)["\']', content)
        if match:
            return match.group(1)
    return None


def update_version_in_file(file_path, pattern, version_str, template=None):
    """Update version in a file."""
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    if template:
        replacement = template.format(version=version_str)
    else:
        replacement = version_str

    new_content = re.sub(pattern, replacement, content)

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(new_content)


def update_changelog(version_str):
    """Update the CHANGELOG.md file with a new version entry."""
    today = datetime.now().strftime("%Y-%m-%d")
    changelog_path = Path(__file__).parent / "CHANGELOG.md"

    with open(changelog_path, "r", encoding="utf-8") as f:
        content = f.readlines()

    # Find the position to insert the new version
    insert_pos = None
    for i, line in enumerate(content):
        if line.startswith("## ["):
            insert_pos = i
            break

    if insert_pos is None:
        print("Error: Could not find where to insert the new version in CHANGELOG.md")
        return False

    # Create the new version entry
    new_entry = [
        f"## [{version_str}] - {today}\n",
        "\n",
        f"### Added ({version_str})\n",
        "\n",
        "- \n",
        "\n",
    ]

    # Insert the new version entry
    content = content[:insert_pos] + new_entry + content[insert_pos:]

    with open(changelog_path, "w", encoding="utf-8") as f:
        f.writelines(content)

    return True


def main():
    """Main function to bump version."""
    parser = argparse.ArgumentParser(description="Bump version numbers")
    parser.add_argument(
        "bump_type",
        choices=["major", "minor", "patch"],
        help="Type of version bump",
    )
    parser.add_argument(
        "--no-changelog",
        action="store_true",
        help="Skip updating the changelog",
    )
    args = parser.parse_args()

    current_version = get_current_version()
    if not current_version:
        print("Error: Could not determine current version.")
        return 1

    print(f"Current version: {current_version}")
    version_tuple = parse_version(current_version)
    new_version_tuple = bump_version(version_tuple, args.bump_type)
    new_version = ".".join(map(str, new_version_tuple))
    print(f"New version: {new_version}")

    # Update version in __init__.py
    init_file = Path(__file__).parent / "versiontracker" / "__init__.py"
    update_version_in_file(
        init_file,
        r'__version__\s*=\s*["\']([^"\']+)["\']',
        f'__version__ = "{new_version}"',
    )
    print(f"Updated version in {init_file}")

    # Update version in README.md
    readme_file = Path(__file__).parent / "README.md"
    update_version_in_file(
        readme_file,
        r"(\* Version: )[^\n]*",
        f"\\1{new_version}",
    )
    print(f"Updated version in {readme_file}")

    # Update changelog if requested
    if not args.no_changelog:
        if update_changelog(new_version):
            print("Updated CHANGELOG.md with new version")
        else:
            print("Failed to update CHANGELOG.md")

    print("\nRemember to commit these changes with:")
    print(f'  git commit -m "Bump version to {new_version}"')

    return 0


if __name__ == "__main__":
    sys.exit(main())
