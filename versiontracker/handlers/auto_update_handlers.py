"""Handler functions for managing applications with auto-updates.

This module provides functions to blacklist or uninstall applications
that have auto-updates enabled, with user feedback and confirmation.
"""

import logging
import sys
from typing import Any, List, Tuple

from versiontracker.apps import get_homebrew_casks
from versiontracker.config import get_config
from versiontracker.homebrew import get_casks_with_auto_updates
from versiontracker.ui import create_progress_bar
from versiontracker.utils import run_command


def handle_blacklist_auto_updates(options: Any) -> int:
    """Add all applications with auto-updates to the blacklist.

    Args:
        options: Command line options

    Returns:
        int: Exit code (0 for success, non-zero for failure)
    """
    try:
        progress_bar = create_progress_bar()
        config = get_config()

        # Get all installed Homebrew casks
        print(progress_bar.color("green")("Getting installed Homebrew casks..."))
        all_casks = get_homebrew_casks()

        if not all_casks:
            print(progress_bar.color("yellow")("No Homebrew casks found."))
            return 0

        # Find casks with auto-updates
        print(progress_bar.color("green")("Checking for auto-updates..."))
        auto_update_casks = get_casks_with_auto_updates(all_casks)

        if not auto_update_casks:
            print(progress_bar.color("yellow")("No casks with auto-updates found."))
            return 0

        # Get current blacklist
        current_blacklist = config.get("blacklist", [])
        new_additions = []

        # Find which casks are not already blacklisted
        for cask in auto_update_casks:
            if cask not in current_blacklist:
                new_additions.append(cask)

        if not new_additions:
            print(progress_bar.color("yellow")("All casks with auto-updates are already blacklisted."))
            return 0

        # Show what will be added
        print(progress_bar.color("blue")(f"\nFound {len(auto_update_casks)} casks with auto-updates:"))
        for cask in auto_update_casks:
            status = " (already blacklisted)" if cask in current_blacklist else " (will be added)"
            color = "yellow" if cask in current_blacklist else "green"
            print(f"  - {progress_bar.color(color)(cask)}{status}")

        # Ask for confirmation
        print(progress_bar.color("yellow")(f"\nThis will add {len(new_additions)} casks to the blacklist."))
        response = input("Do you want to continue? [y/N]: ").strip().lower()

        if response != "y":
            print(progress_bar.color("yellow")("Operation cancelled."))
            return 0

        # Add to blacklist
        updated_blacklist = current_blacklist + new_additions
        config.set("blacklist", updated_blacklist)

        # Save the configuration
        if config.save():
            print(progress_bar.color("green")(f"\n✓ Successfully added {len(new_additions)} casks to the blacklist."))
            print(progress_bar.color("blue")(f"Total blacklisted items: {len(updated_blacklist)}"))
            return 0
        else:
            print(progress_bar.color("red")("Failed to save configuration. Please check your config file."))
            return 1

    except Exception as e:
        logging.error(f"Error blacklisting auto-update casks: {e}")
        print(create_progress_bar().color("red")(f"Error: {e}"))
        return 1


def handle_uninstall_auto_updates(options: Any) -> int:
    """Uninstall all Homebrew casks that have auto-updates enabled.

    Args:
        options: Command line options

    Returns:
        int: Exit code (0 for success, non-zero for failure)
    """
    try:
        progress_bar = create_progress_bar()

        # Get all installed Homebrew casks
        print(progress_bar.color("green")("Getting installed Homebrew casks..."))
        all_casks = get_homebrew_casks()

        if not all_casks:
            print(progress_bar.color("yellow")("No Homebrew casks found."))
            return 0

        # Find casks with auto-updates
        print(progress_bar.color("green")("Checking for auto-updates..."))
        auto_update_casks = get_casks_with_auto_updates(all_casks)

        if not auto_update_casks:
            print(progress_bar.color("yellow")("No casks with auto-updates found."))
            return 0

        # Show what will be uninstalled
        print(progress_bar.color("blue")(f"\nFound {len(auto_update_casks)} casks with auto-updates:"))
        for i, cask in enumerate(auto_update_casks, 1):
            print(f"{i:3d}. {progress_bar.color('yellow')(cask)}")

        # Ask for confirmation
        print(progress_bar.color("red")(f"\n⚠️  This will UNINSTALL {len(auto_update_casks)} applications!"))
        print(progress_bar.color("yellow")("This action cannot be undone."))
        response = input("Are you sure you want to continue? [y/N]: ").strip().lower()

        if response != "y":
            print(progress_bar.color("yellow")("Operation cancelled."))
            return 0

        # Double confirmation for safety
        print(progress_bar.color("red")("\nPlease type 'UNINSTALL' to confirm you want to remove these applications:"))
        confirmation = input().strip()

        if confirmation != "UNINSTALL":
            print(progress_bar.color("yellow")("Operation cancelled."))
            return 0

        # Uninstall each cask
        successful = 0
        failed = 0
        errors = []

        print(progress_bar.color("blue")("\nUninstalling casks..."))
        for cask in auto_update_casks:
            print(f"Uninstalling {progress_bar.color('yellow')(cask)}...", end=" ")
            try:
                # Run brew uninstall command
                command = f"brew uninstall --cask {cask}"
                stdout, returncode = run_command(command, timeout=60)

                if returncode == 0:
                    print(progress_bar.color("green")("✓"))
                    successful += 1
                else:
                    print(progress_bar.color("red")("✗"))
                    failed += 1
                    errors.append((cask, stdout))
            except Exception as e:
                print(progress_bar.color("red")("✗"))
                failed += 1
                errors.append((cask, str(e)))

        # Show results
        print(progress_bar.color("blue")("\n" + "=" * 60))
        print(progress_bar.color("green")(f"Successfully uninstalled: {successful}"))
        if failed > 0:
            print(progress_bar.color("red")(f"Failed to uninstall: {failed}"))
            print(progress_bar.color("red")("\nErrors:"))
            for cask, error in errors:
                print(f"  - {cask}: {error}")

        return 0 if failed == 0 else 1

    except Exception as e:
        logging.error(f"Error uninstalling auto-update casks: {e}")
        print(create_progress_bar().color("red")(f"Error: {e}"))
        return 1


def handle_list_auto_updates(options: Any) -> int:
    """List all applications with auto-updates with detailed information.

    Args:
        options: Command line options

    Returns:
        int: Exit code (0 for success, non-zero for failure)
    """
    try:
        progress_bar = create_progress_bar()
        config = get_config()

        # Get all installed Homebrew casks
        print(progress_bar.color("green")("Getting installed Homebrew casks..."))
        all_casks = get_homebrew_casks()

        if not all_casks:
            print(progress_bar.color("yellow")("No Homebrew casks found."))
            return 0

        # Find casks with auto-updates
        print(progress_bar.color("green")("Checking for auto-updates..."))
        auto_update_casks = get_casks_with_auto_updates(all_casks)

        if not auto_update_casks:
            print(progress_bar.color("yellow")("No casks with auto-updates found."))
            return 0

        # Get current blacklist
        blacklist = config.get("blacklist", [])

        # Display results
        print(progress_bar.color("blue")(f"\nFound {len(auto_update_casks)} casks with auto-updates:"))
        print(progress_bar.color("blue")("=" * 60))

        blacklisted_count = 0
        for i, cask in enumerate(auto_update_casks, 1):
            is_blacklisted = cask in blacklist
            if is_blacklisted:
                blacklisted_count += 1

            status = " (blacklisted)" if is_blacklisted else ""
            color = "yellow" if is_blacklisted else "green"
            print(f"{i:3d}. {progress_bar.color(color)(cask)}{status}")

        print(progress_bar.color("blue")("=" * 60))
        print(progress_bar.color("blue")(f"Total: {len(auto_update_casks)} casks"))
        if blacklisted_count > 0:
            print(progress_bar.color("yellow")(f"Blacklisted: {blacklisted_count} casks"))

        # Show available actions
        print(progress_bar.color("blue")("\nAvailable actions:"))
        print("  - Add to blacklist: versiontracker --blacklist-auto-updates")
        print("  - Uninstall: versiontracker --uninstall-auto-updates")

        return 0

    except Exception as e:
        logging.error(f"Error listing auto-update casks: {e}")
        print(create_progress_bar().color("red")(f"Error: {e}"))
        return 1
