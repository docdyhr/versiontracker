#!/usr/bin/env python3
"""Script to update and manage dependency lock files."""

import argparse
import os
import subprocess
import sys
from pathlib import Path
from typing import List, Optional


def run_command(cmd: List[str], cwd: Optional[Path] = None) -> tuple[str, int]:
    """Run a command and return output and return code."""
    try:
        result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, check=False)
        return result.stdout, result.returncode
    except Exception as e:
        return f"Error: {e}", 1


def update_production_dependencies(project_root: Path) -> bool:
    """Update production dependency lock file."""
    print("Updating production dependencies...")

    # Install from pyproject.toml
    cmd = [sys.executable, "-m", "pip", "install", "-e", "."]
    output, returncode = run_command(cmd, cwd=project_root)

    if returncode != 0:
        print(f"Failed to install project dependencies: {output}")
        return False

    # Generate lock file
    cmd = [sys.executable, "-m", "pip", "freeze"]
    output, returncode = run_command(cmd, cwd=project_root)

    if returncode != 0:
        print(f"Failed to freeze dependencies: {output}")
        return False

    # Filter to only production dependencies
    production_deps = []
    for line in output.strip().split("\n"):
        if line and not line.startswith("#") and "==" in line:
            # Skip development-only packages
            package_name = line.split("==")[0].lower()
            if package_name not in ["pytest", "mypy", "ruff", "bandit", "coverage"]:
                production_deps.append(line)

    # Write lock file
    lock_file = project_root / "requirements-prod.lock"
    with open(lock_file, "w") as f:
        f.write("# Production dependency lock file\n")
        f.write("# Generated automatically - do not edit manually\n")
        f.write(f"# Python version: {sys.version_info.major}.{sys.version_info.minor}+\n\n")

        for dep in sorted(production_deps):
            f.write(f"{dep}\n")

    print(f"Updated {lock_file}")
    return True


def update_development_dependencies(project_root: Path) -> bool:
    """Update development dependency lock file."""
    print("Updating development dependencies...")

    # Install development dependencies
    cmd = [sys.executable, "-m", "pip", "install", "-r", "requirements-dev.txt"]
    output, returncode = run_command(cmd, cwd=project_root)

    if returncode != 0:
        print(f"Failed to install development dependencies: {output}")
        return False

    # Generate lock file
    cmd = [sys.executable, "-m", "pip", "freeze"]
    output, returncode = run_command(cmd, cwd=project_root)

    if returncode != 0:
        print(f"Failed to freeze dependencies: {output}")
        return False

    # Write lock file
    lock_file = project_root / "requirements-dev.lock"
    with open(lock_file, "w") as f:
        f.write("# Development dependency lock file\n")
        f.write("# Generated automatically - do not edit manually\n")
        f.write(f"# Python version: {sys.version_info.major}.{sys.version_info.minor}+\n\n")

        for line in sorted(output.strip().split("\n")):
            if line and not line.startswith("#"):
                f.write(f"{line}\n")

    print(f"Updated {lock_file}")
    return True


def check_security_vulnerabilities(project_root: Path) -> bool:
    """Check for security vulnerabilities in dependencies."""
    print("Checking for security vulnerabilities...")

    # Use safety to check for known vulnerabilities
    cmd = [sys.executable, "-m", "safety", "check", "--json"]
    output, returncode = run_command(cmd, cwd=project_root)

    if returncode == 0:
        print("✓ No known security vulnerabilities found")
        return True
    else:
        print("⚠️  Security vulnerabilities found:")
        print(output)
        return False


def validate_lock_files(project_root: Path) -> bool:
    """Validate that lock files are consistent and installable."""
    print("Validating lock files...")

    # Check production lock file
    prod_lock = project_root / "requirements-prod.lock"
    if not prod_lock.exists():
        print("❌ Production lock file not found")
        return False

    # Check development lock file
    dev_lock = project_root / "requirements-dev.lock"
    if not dev_lock.exists():
        print("❌ Development lock file not found")
        return False

    # Try installing from lock files in a test environment
    # This would require creating a temporary virtual environment
    # For now, just check that files are readable

    try:
        with open(prod_lock) as f:
            prod_lines = f.readlines()
        with open(dev_lock) as f:
            dev_lines = f.readlines()

        print(f"✓ Production lock file: {len(prod_lines)} lines")
        print(f"✓ Development lock file: {len(dev_lines)} lines")
        return True

    except Exception as e:
        print(f"❌ Error reading lock files: {e}")
        return False


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Manage dependency lock files")
    parser.add_argument(
        "--check-only", action="store_true", help="Only check vulnerabilities and validate, don't update"
    )
    parser.add_argument("--production-only", action="store_true", help="Only update production dependencies")
    parser.add_argument("--development-only", action="store_true", help="Only update development dependencies")

    args = parser.parse_args()

    # Find project root
    project_root = Path(__file__).parent.parent
    if not (project_root / "pyproject.toml").exists():
        print("❌ Could not find pyproject.toml - are you in the right directory?")
        sys.exit(1)

    success = True

    if not args.check_only:
        if not args.development_only:
            success &= update_production_dependencies(project_root)

        if not args.production_only:
            success &= update_development_dependencies(project_root)

    # Always check security and validate
    success &= check_security_vulnerabilities(project_root)
    success &= validate_lock_files(project_root)

    if success:
        print("\n✅ All dependency operations completed successfully")
        sys.exit(0)
    else:
        print("\n❌ Some dependency operations failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
