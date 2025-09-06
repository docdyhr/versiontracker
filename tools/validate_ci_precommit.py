#!/usr/bin/env python3
"""Validation script for CI/CD and pre-commit hook compatibility.

This script ensures that:
1. Ruff versions are consistent across all configuration files
2. Pre-commit and CI use compatible arguments
3. All tools can run successfully
4. Configuration files are valid
"""

import subprocess
import sys
from pathlib import Path

import yaml

try:
    import tomllib  # Python 3.11+
except ImportError:
    try:
        import tomli as tomllib  # type: ignore[no-redef]
    except ImportError:
        # Fallback for older Python versions without tomli
        import toml as tomllib  # type: ignore[import-untyped,no-redef]


class ValidationError(Exception):
    """Custom exception for validation errors."""

    pass


class CIPrecommitValidator:
    """Validator for CI/CD and pre-commit compatibility."""

    def __init__(self, project_root: Path):
        """Initialize validator with project root path."""
        self.project_root = project_root
        self.errors: list[str] = []
        self.warnings: list[str] = []

    def validate_all(self) -> bool:
        """Run all validation checks."""
        print("🔍 Validating CI/CD and pre-commit compatibility...")
        print("=" * 60)

        checks = [
            ("Ruff version consistency", self.check_ruff_versions),
            ("MyPy version consistency", self.check_mypy_versions),
            ("Pre-commit configuration", self.validate_precommit_config),
            ("CI workflow configuration", self.validate_ci_config),
            ("Tool compatibility", self.check_tool_compatibility),
            ("Configuration file validity", self.validate_config_files),
        ]

        for check_name, check_func in checks:
            print(f"\n📋 {check_name}...")
            try:
                check_func()
                print(f"✅ {check_name}: PASSED")
            except ValidationError as e:
                self.errors.append(f"{check_name}: {e}")
                print(f"❌ {check_name}: FAILED - {e}")
            except Exception as e:
                self.errors.append(f"{check_name}: Unexpected error - {e}")
                print(f"💥 {check_name}: ERROR - {e}")

        self._print_summary()
        return len(self.errors) == 0

    def check_ruff_versions(self) -> None:
        """Check ruff version consistency across configuration files."""
        self._check_tool_versions("ruff", ["ruff-pre-commit"])

    def check_mypy_versions(self) -> None:
        """Check mypy version consistency across configuration files."""
        self._check_tool_versions("mypy", ["mirrors-mypy"])

    def _check_tool_versions(self, tool_name: str, repo_patterns: list[str]) -> None:
        """Generic method to check tool version consistency."""
        versions: dict[str, str] = {}

        # Collect versions from all sources
        self._check_constraints_file(tool_name, versions)
        self._check_requirements_dev_file(tool_name, versions)
        self._check_precommit_config(tool_name, repo_patterns, versions)
        self._check_installed_version(tool_name, versions)

        if not versions:
            raise ValidationError(f"No {tool_name} version specifications found")

        # Validate consistency
        self._validate_version_consistency(tool_name, versions)
        print(f"   {tool_name.title()} version: {list(versions.values())[0]}")

    def _check_constraints_file(self, tool_name: str, versions: dict[str, str]) -> None:
        """Check tool version in constraints.txt."""
        constraints_file = self.project_root / "constraints.txt"
        if not constraints_file.exists():
            return

        with open(constraints_file) as f:
            for line in f:
                if line.strip().startswith(f"{tool_name}=="):
                    versions["constraints.txt"] = line.split("==")[1].strip()
                elif line.strip().startswith(f"{tool_name}>="):
                    versions["constraints.txt"] = line.strip()

    def _check_requirements_dev_file(self, tool_name: str, versions: dict[str, str]) -> None:
        """Check tool version in requirements-dev.txt."""
        req_dev_file = self.project_root / "requirements-dev.txt"
        if not req_dev_file.exists():
            return

        with open(req_dev_file) as f:
            for line in f:
                if line.strip().startswith(f"{tool_name}=="):
                    version_part = line.split("==")[1].split("#")[0].strip()
                    versions["requirements-dev.txt"] = version_part
                elif line.strip().startswith(f"{tool_name}>="):
                    version_part = line.split(">=")[1].split("#")[0].strip()
                    versions["requirements-dev.txt"] = f"{tool_name}>={version_part}"

    def _check_precommit_config(self, tool_name: str, repo_patterns: list[str], versions: dict) -> None:
        """Check tool version in pre-commit config."""
        precommit_file = self.project_root / ".pre-commit-config.yaml"
        if not precommit_file.exists():
            return

        with open(precommit_file) as f:
            config = yaml.safe_load(f)
            for repo in config.get("repos", []):
                repo_url = repo.get("repo", "")
                if any(pattern in repo_url for pattern in repo_patterns):
                    versions[".pre-commit-config.yaml"] = repo.get("rev", "").lstrip("v")

    def _check_installed_version(self, tool_name: str, versions: dict[str, str]) -> None:
        """Check installed tool version."""
        try:
            result = subprocess.run([tool_name, "--version"], capture_output=True, text=True, check=True)
            output = result.stdout.strip()
            if tool_name == "mypy":
                # mypy output: "mypy 1.15.0 (compiled: yes)"
                installed_version = output.split()[1]
            else:
                # ruff output: "ruff 0.11.12"
                installed_version = output.split()[-1]
            versions["installed"] = installed_version
        except (subprocess.CalledProcessError, FileNotFoundError):
            self.warnings.append(f"Could not determine installed {tool_name} version")

    def _validate_version_consistency(self, tool_name: str, versions: dict[str, str]) -> None:
        """Validate that versions are consistent across all sources."""
        normalized_versions = set()
        for v in versions.values():
            # Extract just the version number, removing operators and comments
            clean_v = (
                v.replace(f"{tool_name}>=", "")
                .replace(f"{tool_name}==", "")
                .replace(">=", "")
                .replace("==", "")
                .split("#")[0]
                .strip()
            )
            normalized_versions.add(clean_v)

        if len(normalized_versions) > 1:
            version_info = "\n".join(f"  {file}: {version}" for file, version in versions.items())
            raise ValidationError(f"Inconsistent {tool_name} versions found:\n{version_info}")

    def validate_precommit_config(self) -> None:
        """Validate pre-commit configuration."""
        config_file = self.project_root / ".pre-commit-config.yaml"
        if not config_file.exists():
            raise ValidationError(".pre-commit-config.yaml not found")

        with open(config_file) as f:
            config = yaml.safe_load(f)

        # Check for ruff hooks
        ruff_hooks = []
        mypy_hooks = []
        for repo in config.get("repos", []):
            repo_url = repo.get("repo", "")
            if "ruff-pre-commit" in repo_url:
                ruff_hooks.extend(repo.get("hooks", []))
            elif "mirrors-mypy" in repo_url:
                mypy_hooks.extend(repo.get("hooks", []))

        if not ruff_hooks:
            raise ValidationError("No ruff hooks found in pre-commit configuration")

        if not mypy_hooks:
            self.warnings.append("No mypy hooks found in pre-commit configuration")

        # Check required hook IDs
        ruff_hook_ids = [hook.get("id") for hook in ruff_hooks]
        required_ruff_hooks = ["ruff", "ruff-format"]
        missing_ruff_hooks = [h for h in required_ruff_hooks if h not in ruff_hook_ids]

        if missing_ruff_hooks:
            raise ValidationError(f"Missing ruff hooks: {missing_ruff_hooks}")

        mypy_hook_ids = [hook.get("id") for hook in mypy_hooks]
        if mypy_hooks and "mypy" not in mypy_hook_ids:
            self.warnings.append("MyPy hook found but 'mypy' id missing")

        print(f"   Found ruff hooks: {ruff_hook_ids}")
        if mypy_hooks:
            print(f"   Found mypy hooks: {mypy_hook_ids}")

    def validate_ci_config(self) -> None:
        """Validate CI workflow configuration."""
        workflows_dir = self.project_root / ".github" / "workflows"
        if not workflows_dir.exists():
            raise ValidationError(".github/workflows directory not found")

        # Check for main CI workflows
        required_workflows = ["ci.yml", "lint.yml"]
        existing_workflows = [f.name for f in workflows_dir.glob("*.yml")]

        missing_workflows = [w for w in required_workflows if w not in existing_workflows]
        if missing_workflows:
            self.warnings.append(f"Missing recommended workflows: {missing_workflows}")

        # Check CI workflow for ruff usage
        ci_file = workflows_dir / "ci.yml"
        if ci_file.exists():
            with open(ci_file) as f:
                content = f.read()
                if "ruff check" not in content:
                    self.warnings.append("CI workflow doesn't use 'ruff check'")
                if "ruff format" not in content:
                    self.warnings.append("CI workflow doesn't use 'ruff format'")

        print(f"   Found workflows: {existing_workflows}")

    def check_tool_compatibility(self) -> None:
        """Check that tools can run successfully."""
        tools_to_check = [
            ("ruff", ["ruff", "--version"]),
            ("mypy", ["mypy", "--version"]),
            ("pre-commit", ["pre-commit", "--version"]),
        ]

        for tool_name, command in tools_to_check:
            try:
                subprocess.run(
                    command,
                    capture_output=True,
                    text=True,
                    check=True,
                    cwd=self.project_root,
                )
                print(f"   {tool_name}: ✓")
            except (subprocess.CalledProcessError, FileNotFoundError) as e:
                raise ValidationError(f"{tool_name} not available or failed: {e}") from e

        # Check mypy type stub consistency
        self._check_type_stub_versions()

    def _check_type_stub_versions(self) -> None:
        """Check that type stub versions are consistent with mypy requirements."""
        precommit_stubs = self._get_precommit_type_stubs()
        req_stubs = self._get_requirements_type_stubs()

        self._compare_type_stub_sets(precommit_stubs, req_stubs)
        print(f"   Type stubs: {len(precommit_stubs)} in pre-commit, {len(req_stubs)} in requirements-dev.txt")

    def _get_precommit_type_stubs(self) -> set[str]:
        """Extract type stub dependencies from pre-commit config."""
        precommit_file = self.project_root / ".pre-commit-config.yaml"
        precommit_stubs = set()

        if not precommit_file.exists():
            return precommit_stubs

        with open(precommit_file) as f:
            config = yaml.safe_load(f)

        for repo in config.get("repos", []):
            if "mirrors-mypy" not in repo.get("repo", ""):
                continue

            for hook in repo.get("hooks", []):
                if hook.get("id") == "mypy":
                    deps = hook.get("additional_dependencies", [])
                    for dep in deps:
                        if isinstance(dep, str) and dep.startswith("types-"):
                            precommit_stubs.add(dep.split(">=")[0].split("==")[0])

        return precommit_stubs

    def _get_requirements_type_stubs(self) -> set[str]:
        """Extract type stub dependencies from requirements-dev.txt."""
        req_dev_file = self.project_root / "requirements-dev.txt"
        req_stubs = set()

        if not req_dev_file.exists():
            return req_stubs

        with open(req_dev_file) as f:
            for line in f:
                line = line.strip()
                if line.startswith("types-"):
                    stub_name = line.split(">=")[0].split("==")[0]
                    req_stubs.add(stub_name)

        return req_stubs

    def _compare_type_stub_sets(self, precommit_stubs: set[str], req_stubs: set[str]) -> None:
        """Compare type stub sets and add warnings for inconsistencies."""
        if precommit_stubs == req_stubs:
            return

        missing_in_req = precommit_stubs - req_stubs
        missing_in_precommit = req_stubs - precommit_stubs

        if missing_in_req:
            self.warnings.append(f"Type stubs in pre-commit but not requirements-dev.txt: {missing_in_req}")
        if missing_in_precommit:
            self.warnings.append(f"Type stubs in requirements-dev.txt but not pre-commit: {missing_in_precommit}")

    def validate_config_files(self) -> None:
        """Validate configuration file syntax."""
        configs_to_check = [
            (".pre-commit-config.yaml", self._validate_yaml),
            ("pyproject.toml", self._validate_toml),
            (".github/workflows/ci.yml", self._validate_yaml),
            (".github/workflows/lint.yml", self._validate_yaml),
        ]

        for config_path, validator in configs_to_check:
            file_path = self.project_root / config_path
            if file_path.exists():
                try:
                    validator(file_path)
                    print(f"   {config_path}: ✓")
                except Exception as e:
                    raise ValidationError(f"Invalid {config_path}: {e}") from e

    def _validate_yaml(self, file_path: Path) -> None:
        """Validate YAML file syntax."""
        with open(file_path) as f:
            yaml.safe_load(f)

    def _validate_toml(self, file_path: Path) -> None:
        """Validate TOML file syntax."""
        with open(file_path, "rb") as f:
            tomllib.load(f)

    def _print_summary(self) -> None:
        """Print validation summary."""
        print("\n" + "=" * 60)
        print("📊 VALIDATION SUMMARY")
        print("=" * 60)

        if not self.errors and not self.warnings:
            print("🎉 All checks passed! CI/CD and pre-commit are fully compatible.")
        else:
            if self.errors:
                print(f"❌ ERRORS ({len(self.errors)}):")
                for error in self.errors:
                    print(f"   • {error}")

            if self.warnings:
                print(f"\n⚠️  WARNINGS ({len(self.warnings)}):")
                for warning in self.warnings:
                    print(f"   • {warning}")

        print("\n💡 RECOMMENDATIONS:")
        print("   • Keep ruff and mypy versions pinned to exact versions")
        print("   • Run 'pre-commit autoupdate' periodically")
        print("   • Test changes locally before pushing")
        print("   • Monitor CI performance and adjust as needed")
        print("   • Update type stubs when updating mypy version")


def main() -> int:
    """Main entry point."""
    project_root = Path(__file__).parent.parent

    validator = CIPrecommitValidator(project_root)
    success = validator.validate_all()

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
