"""Handler functions for managing applications with auto-updates.

This module provides functions to blocklist (legacy: blacklist) or uninstall applications
that have auto-updates enabled, with user feedback and confirmation.
"""

import logging
from typing import Any

from versiontracker.app_finder import get_homebrew_casks
from versiontracker.config import get_config
from versiontracker.homebrew import get_casks_with_auto_updates
from versiontracker.ui import create_progress_bar
from versiontracker.utils import run_command


def handle_blacklist_auto_updates(options: Any) -> int:
    """Add all applications with auto-updates to the blocklist (legacy: blacklist).

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

        # Get current blocklist (stored under legacy 'blacklist' key)
        current_blacklist = config.get("blacklist", [])
        new_additions = []

        # Find which casks are not already blocklisted
        for cask in auto_update_casks:
            if cask not in current_blacklist:
                new_additions.append(cask)

        if not new_additions:
            print(progress_bar.color("yellow")("All casks with auto-updates are already blocklisted."))
            return 0

        # Show what will be added
        print(progress_bar.color("blue")(f"\nFound {len(auto_update_casks)} casks with auto-updates:"))
        for cask in auto_update_casks:
            status = " (already blocklisted)" if cask in current_blacklist else " (will be added)"
            color = "yellow" if cask in current_blacklist else "green"
            print(f"  - {progress_bar.color(color)(cask)}{status}")

        # Ask for confirmation
        print(progress_bar.color("yellow")(f"\nThis will add {len(new_additions)} casks to the blocklist."))
        response = input("Do you want to continue? [y/N]: ").strip().lower()

        if response != "y":
            print(progress_bar.color("yellow")("Operation cancelled."))
            return 0

        # Add to blacklist
        updated_blacklist = current_blacklist + new_additions
        config.set("blacklist", updated_blacklist)

        # Save the configuration
        if config.save():
            print(progress_bar.color("green")(f"\n✓ Successfully added {len(new_additions)} casks to the blocklist."))
            print(progress_bar.color("blue")(f"Total blocklisted items: {len(updated_blacklist)}"))
            return 0
        else:
            print(progress_bar.color("red")("Failed to save configuration. Please check your config file."))
            return 1

    except Exception as e:
        logging.error(f"Error blocklisting (legacy: blacklisting) auto-update casks: {e}")
        print(create_progress_bar().color("red")(f"Error: {e}"))
        return 1


def _get_auto_update_casks() -> tuple[list[str], int]:
    """Get casks with auto-updates.
    
    Returns:
        tuple: (auto_update_casks, exit_code) - exit_code is 0 for success, non-zero for early exit
    """
    progress_bar = create_progress_bar()
    
    # Get all installed Homebrew casks
    print(progress_bar.color("green")("Getting installed Homebrew casks..."))
    all_casks = get_homebrew_casks()

    if not all_casks:
        print(progress_bar.color("yellow")("No Homebrew casks found."))
        return [], 0

    # Find casks with auto-updates
    print(progress_bar.color("green")("Checking for auto-updates..."))
    auto_update_casks = get_casks_with_auto_updates(all_casks)

    if not auto_update_casks:
        print(progress_bar.color("yellow")("No casks with auto-updates found."))
        return [], 0
        
    return auto_update_casks, -1  # -1 indicates continue processing


def _display_casks_and_confirm(auto_update_casks: list[str]) -> bool:
    """Display casks to be uninstalled and get user confirmation.
    
    Args:
        auto_update_casks: List of casks with auto-updates
        
    Returns:
        bool: True if user confirmed, False otherwise
    """
    progress_bar = create_progress_bar()
    
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
        return False

    # Double confirmation for safety
    print(progress_bar.color("red")("\nPlease type 'UNINSTALL' to confirm you want to remove these applications:"))
    confirmation = input().strip()

    if confirmation != "UNINSTALL":
        print(progress_bar.color("yellow")("Operation cancelled."))
        return False
        
    return True


def _uninstall_single_cask(cask: str) -> tuple[bool, str | None]:
    """Uninstall a single cask.
    
    Args:
        cask: Name of the cask to uninstall
        
    Returns:
        tuple: (success, error_message)
    """
    try:
        # Run brew uninstall command
        command = f"brew uninstall --cask {cask}"
        stdout, returncode = run_command(command, timeout=60)

        if returncode == 0:
            return True, None
        else:
            return False, stdout
    except Exception as e:
        return False, str(e)


def _perform_uninstall_operations(auto_update_casks: list[str]) -> tuple[int, int, list[tuple[str, str]]]:
    """Perform the uninstall operations for all casks.
    
    Args:
        auto_update_casks: List of casks to uninstall
        
    Returns:
        tuple: (successful_count, failed_count, errors)
    """
    progress_bar = create_progress_bar()
    successful = 0
    failed = 0
    errors = []

    print(progress_bar.color("blue")("\nUninstalling casks..."))
    for cask in auto_update_casks:
        print(f"Uninstalling {progress_bar.color('yellow')(cask)}...", end=" ")
        success, error_message = _uninstall_single_cask(cask)
        
        if success:
            print(progress_bar.color("green")("✓"))
            successful += 1
        else:
            print(progress_bar.color("red")("✗"))
            failed += 1
            errors.append((cask, error_message))
            
    return successful, failed, errors


def _display_uninstall_results(successful: int, failed: int, errors: list[tuple[str, str]]) -> int:
    """Display uninstall results.
    
    Args:
        successful: Number of successful uninstalls
        failed: Number of failed uninstalls
        errors: List of error tuples (cask, error_message)
        
    Returns:
        int: Exit code
    """
    progress_bar = create_progress_bar()
    
    # Show results
    print(progress_bar.color("blue")("\n" + "=" * 60))
    print(progress_bar.color("green")(f"Successfully uninstalled: {successful}"))
    if failed > 0:
        print(progress_bar.color("red")(f"Failed to uninstall: {failed}"))
        print(progress_bar.color("red")("\nErrors:"))
        for cask, error in errors:
            print(f"  - {cask}: {error}")

    return 0 if failed == 0 else 1


def handle_uninstall_auto_updates(options: Any) -> int:
    """Uninstall all Homebrew casks that have auto-updates enabled.

    Args:
        options: Command line options

    Returns:
        int: Exit code (0 for success, non-zero for failure)
    """
    try:
        # Get casks with auto-updates
        auto_update_casks, exit_code = _get_auto_update_casks()
        if exit_code >= 0:  # Early exit condition
            return exit_code

        # Display and get confirmation
        if not _display_casks_and_confirm(auto_update_casks):
            return 0

        # Perform uninstall operations
        successful, failed, errors = _perform_uninstall_operations(auto_update_casks)

        # Display results and return appropriate exit code
        return _display_uninstall_results(successful, failed, errors)

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
