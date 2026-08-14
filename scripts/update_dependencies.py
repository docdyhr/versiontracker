#!/usr/bin/env python3
"""Script to update and manage dependency lock files."""

import argparse
import subprocess
import sys
import tempfile
import venv
from pathlib import Path


def run_command(cmd: list[str], cwd: Path | None = None) -> tuple[str, int]:
    """Run a command and return output and return code."""
    try:
        result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, check=False)
        return result.stdout, result.returncode
    except Exception as e:
        return f"Error: {e}", 1


def _generate_lock_file(requirements_file: Path, lock_file: Path, project_root: Path, label: str) -> bool:
    """Generate a lock file from a fresh, isolated virtual environment.

    Installs requirements_file into a throwaway venv (instead of whatever happens to
    already be installed under sys.executable) and freezes it, so the result is
    structurally correct: it cannot contain anything beyond what requirements_file
    actually declares, and no post-hoc filtering/blocklist is needed or possible to
    get wrong.

    Args:
        requirements_file: The requirements file to install (e.g. requirements.txt).
        lock_file: Where to write the resulting lock file.
        project_root: Repository root, used as the subprocess working directory.
        label: Human-readable label for the lock file header (e.g. "Production").

    Returns:
        bool: True on success.
    """
    with tempfile.TemporaryDirectory(prefix="vt-lock-") as tmpdir:
        venv_dir = Path(tmpdir) / "venv"
        venv.create(venv_dir, with_pip=True)
        venv_python = venv_dir / "bin" / "python"

        output, returncode = run_command([str(venv_python), "-m", "pip", "install", "--quiet", "--upgrade", "pip"])
        if returncode != 0:
            print(f"Failed to upgrade pip in isolated environment: {output}")
            return False

        cmd = [str(venv_python), "-m", "pip", "install", "--quiet", "-r", str(requirements_file)]
        output, returncode = run_command(cmd, cwd=project_root)
        if returncode != 0:
            print(f"Failed to install {requirements_file.name} in isolated environment: {output}")
            return False

        output, returncode = run_command([str(venv_python), "-m", "pip", "freeze"])
        if returncode != 0:
            print(f"Failed to freeze isolated environment: {output}")
            return False

    with open(lock_file, "w") as f:
        f.write(f"# {label} dependency lock file\n")
        f.write("# Generated automatically by scripts/update_dependencies.py -- do not edit manually.\n")
        f.write(f"# Installed {requirements_file.name} into a fresh, isolated virtual environment and froze\n")
        f.write("# it, so this can only ever contain what that requirements file actually declares --\n")
        f.write("# never whatever else happens to be installed in the environment running this script.\n")
        f.write(f"# Python version: {sys.version_info.major}.{sys.version_info.minor}+\n\n")

        for line in sorted(output.strip().split("\n")):
            if line and not line.startswith("#"):
                f.write(f"{line}\n")

    print(f"Updated {lock_file}")
    return True


def update_production_dependencies(project_root: Path) -> bool:
    """Update production dependency lock file."""
    print("Updating production dependencies...")
    return _generate_lock_file(
        project_root / "requirements.txt",
        project_root / "requirements-prod.lock",
        project_root,
        "Production",
    )


def update_development_dependencies(project_root: Path) -> bool:
    """Update development dependency lock file."""
    print("Updating development dependencies...")
    return _generate_lock_file(
        project_root / "requirements-dev.txt",
        project_root / "requirements-dev.lock",
        project_root,
        "Development",
    )


def check_security_vulnerabilities(project_root: Path) -> bool:
    """Check the generated lock files for known vulnerabilities via pip-audit.

    Targets the lock files directly (not the ambient environment running this
    script) so this actually verifies the artifacts this script just produced.
    """
    print("Checking lock files for security vulnerabilities...")

    all_clean = True
    for lock_name in ("requirements-prod.lock", "requirements-dev.lock"):
        lock_file = project_root / lock_name
        if not lock_file.exists():
            continue

        cmd = [sys.executable, "-m", "pip_audit", "-r", str(lock_file)]
        output, returncode = run_command(cmd, cwd=project_root)

        if returncode == 0:
            print(f"✓ {lock_name}: no known vulnerabilities found")
        else:
            print(f"⚠️  {lock_name}: vulnerabilities found:")
            print(output)
            all_clean = False

    return all_clean


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


def main() -> None:
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
