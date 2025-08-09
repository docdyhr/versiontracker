#!/usr/bin/env python3
"""Example script demonstrating the auto-updates detection feature in VersionTracker.

This script shows how to use the new auto-updates functionality to:
1. List all Homebrew casks with auto-updates enabled
2. Get recommendations excluding apps with auto-updates
3. Check specific casks for auto-updates
"""

import sys
from pathlib import Path

# Add the parent directory to the path so we can import versiontracker
sys.path.insert(0, str(Path(__file__).parent.parent))

from versiontracker.app_finder import get_homebrew_casks
from versiontracker.homebrew import (
    get_cask_info,
    get_casks_with_auto_updates,
    has_auto_updates,
)
from versiontracker.ui import create_progress_bar


def main():
    """Run the auto-updates detection examples."""
    progress_bar = create_progress_bar()

    print(progress_bar.color("blue")("=" * 60))
    print(progress_bar.color("blue")("VersionTracker Auto-Updates Detection Example"))
    print(progress_bar.color("blue")("=" * 60))
    print()

    # Example 1: Get all installed Homebrew casks
    print(progress_bar.color("green")("1. Getting all installed Homebrew casks..."))
    try:
        all_casks = get_homebrew_casks()
        print(f"   Found {len(all_casks)} installed casks")
        print()
    except Exception as e:
        print(progress_bar.color("red")(f"   Error: {e}"))
        return 1

    # Example 2: Find which casks have auto-updates enabled
    print(progress_bar.color("green")("2. Checking which casks have auto-updates enabled..."))
    auto_update_casks = get_casks_with_auto_updates(all_casks[:10])  # Check first 10 for demo

    if auto_update_casks:
        print(f"   Found {len(auto_update_casks)} casks with auto-updates:")
        for cask in auto_update_casks:
            print(f"   - {progress_bar.color('yellow')(cask)}")
    else:
        print("   No casks with auto-updates found in the sample")
    print()

    # Example 3: Check specific popular casks for auto-updates
    print(progress_bar.color("green")("3. Checking specific casks for auto-updates..."))
    test_casks = ["visual-studio-code", "slack", "firefox", "google-chrome", "spotify"]

    for cask_name in test_casks:
        if cask_name in all_casks:
            has_updates = has_auto_updates(cask_name)
            status = "Yes" if has_updates else "No"
            color = "yellow" if has_updates else "blue"
            print(f"   {cask_name}: {progress_bar.color(color)(status)}")
    print()

    # Example 4: Show detailed info for a cask with auto-updates
    print(progress_bar.color("green")("4. Detailed info for a cask..."))
    sample_cask = "visual-studio-code" if "visual-studio-code" in all_casks else all_casks[0] if all_casks else None

    if sample_cask:
        try:
            info = get_cask_info(sample_cask)
            print(f"   Cask: {progress_bar.color('blue')(sample_cask)}")
            print(f"   Version: {info.get('version', 'Unknown')}")
            print(f"   Auto-updates field: {info.get('auto_updates', False)}")

            caveats = info.get("caveats", "")
            if caveats:
                print(f"   Caveats preview: {caveats[:100]}...")
        except Exception as e:
            print(f"   Could not get info for {sample_cask}: {e}")
    print()

    # Example 5: Statistics
    print(progress_bar.color("green")("5. Auto-updates statistics..."))
    if len(all_casks) > 0:
        # Check a larger sample for statistics
        sample_size = min(50, len(all_casks))
        sample_casks = all_casks[:sample_size]
        auto_update_sample = get_casks_with_auto_updates(sample_casks)

        percentage = (len(auto_update_sample) / sample_size) * 100
        print(f"   Sample size: {sample_size} casks")
        print(f"   With auto-updates: {len(auto_update_sample)} ({percentage:.1f}%)")
        print(f"   Without auto-updates: {sample_size - len(auto_update_sample)} ({100 - percentage:.1f}%)")
    print()

    print(progress_bar.color("blue")("=" * 60))
    print(progress_bar.color("green")("Done! You can now use these features with:"))
    print("  versiontracker --brews --exclude-auto-updates")
    print("  versiontracker --brews --only-auto-updates")
    print("  versiontracker --recommend --exclude-auto-updates")
    print(progress_bar.color("blue")("=" * 60))

    return 0


if __name__ == "__main__":
    sys.exit(main())
