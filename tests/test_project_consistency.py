"""Tests to ensure project configuration consistency."""

import re
import sys
from pathlib import Path

import pytest
import toml
import yaml


class TestProjectConsistency:
    """Test project configuration consistency."""

    def test_python_version_consistency(self):
        """Test that Python version is consistent across all configuration files."""
        project_root = Path(__file__).parent.parent

        # Read pyproject.toml
        pyproject_path = project_root / "pyproject.toml"
        with open(pyproject_path) as f:
            pyproject = toml.load(f)

        requires_python = pyproject["project"]["requires-python"]
        # Extract minimum version (e.g., ">=3.9" -> "3.9")
        min_version_match = re.match(r">=(\d+\.\d+)", requires_python)
        assert min_version_match, f"Invalid requires-python format: {requires_python}"
        min_version = min_version_match.group(1)

        # Check mypy.ini
        mypy_ini_path = project_root / "mypy.ini"
        if not mypy_ini_path.exists():
            pytest.skip(f"mypy.ini not found at {mypy_ini_path}")
        with open(mypy_ini_path) as f:
            content = f.read()
            mypy_version_match = re.search(r"python_version\s*=\s*(\d+\.\d+)", content)
            assert mypy_version_match, "python_version not found in mypy.ini"
            mypy_version = mypy_version_match.group(1)
            assert mypy_version == min_version, f"mypy.ini has {mypy_version}, expected {min_version}"

        # Check setup.cfg
        setup_cfg_path = project_root / "setup.cfg"
        if setup_cfg_path.exists():
            with open(setup_cfg_path) as f:
                content = f.read()
                setup_version_match = re.search(r"python_version\s*=\s*(\d+\.\d+)", content)
                if setup_version_match:
                    setup_version = setup_version_match.group(1)
                    assert setup_version == min_version, f"setup.cfg has {setup_version}, expected {min_version}"

        # Check README.md
        readme_path = project_root / "README.md"
        with open(readme_path) as f:
            content = f.read()
            # Look for "Python X.Y or later" pattern
            readme_version_match = re.search(r"Python\s+(\d+\.\d+)\s+or\s+later", content)
            assert readme_version_match, "Python version requirement not found in README.md"
            readme_version = readme_version_match.group(1)
            assert readme_version == min_version, f"README.md has {readme_version}, expected {min_version}"

        # Check Ruff target version
        ruff_target = pyproject.get("tool", {}).get("ruff", {}).get("target-version")
        expected_ruff = f"py{min_version.replace('.', '')}"
        assert ruff_target == expected_ruff, f"Ruff target is {ruff_target}, expected {expected_ruff}"

    def test_ci_python_versions(self):
        """Test that CI workflows test appropriate Python versions."""
        project_root = Path(__file__).parent.parent

        # Read pyproject.toml to get supported versions
        pyproject_path = project_root / "pyproject.toml"
        with open(pyproject_path) as f:
            pyproject = toml.load(f)

        # Extract all supported Python versions from classifiers
        classifiers = pyproject["project"]["classifiers"]
        supported_versions = []
        for classifier in classifiers:
            match = re.match(r"Programming Language :: Python :: (\d+\.\d+)", classifier)
            if match:
                supported_versions.append(match.group(1))

        # Check CI workflow
        ci_workflow_path = project_root / ".github" / "workflows" / "ci.yml"
        with open(ci_workflow_path) as f:
            ci_config = yaml.safe_load(f)

        # Extract Python versions from test matrix
        test_job = ci_config["jobs"]["test"]
        ci_versions = test_job["strategy"]["matrix"]["python-version"]

        # Ensure CI tests all supported versions
        for version in supported_versions:
            assert version in ci_versions, f"Python {version} is supported but not tested in CI"

    def test_coverage_configuration(self):
        """Test that coverage configuration is consistent."""
        project_root = Path(__file__).parent.parent

        # Check .coveragerc
        coveragerc_path = project_root / ".coveragerc"
        if coveragerc_path.exists():
            with open(coveragerc_path) as f:
                content = f.read()
                # Check fail_under setting
                fail_under_match = re.search(r"fail_under\s*=\s*(\d+)", content)
                if fail_under_match:
                    fail_under = int(fail_under_match.group(1))
                    assert fail_under <= 70, f"Coverage fail_under is {fail_under}%, which might be too high"
                    assert fail_under >= 50, f"Coverage fail_under is {fail_under}%, consider raising it"

        # Check pytest.ini settings
        pytest_ini_path = project_root / "pytest.ini"
        if pytest_ini_path.exists():
            with open(pytest_ini_path) as f:
                content = f.read()
                assert "--cov-fail-under=0" in content or "cov-fail-under" not in content, (
                    "pytest.ini should not enforce coverage threshold during development"
                )

        # Check pytest-ci.ini settings
        pytest_ci_ini_path = project_root / "pytest-ci.ini"
        if pytest_ci_ini_path.exists():
            with open(pytest_ci_ini_path) as f:
                content = f.read()
                assert "--cov-fail-under=0" in content, (
                    "pytest-ci.ini should have --cov-fail-under=0 to avoid CI failures"
                )

    def test_dependency_constraints(self):
        """Test that constraints.txt exists and is valid."""
        project_root = Path(__file__).parent.parent
        constraints_path = project_root / "constraints.txt"

        assert constraints_path.exists(), "constraints.txt file is missing"

        # Basic validation - file should not be empty and should contain version specs
        with open(constraints_path) as f:
            content = f.read()
            assert len(content) > 100, "constraints.txt seems too small"
            assert ">=" in content, "constraints.txt should contain version constraints"
            assert "<" in content, "constraints.txt should contain upper bounds"

    def test_current_python_version(self):
        """Test that tests are running on a supported Python version."""
        current_version = f"{sys.version_info.major}.{sys.version_info.minor}"

        # We support Python 3.9+
        assert sys.version_info >= (3, 9), f"Tests running on Python {current_version}, but 3.9+ is required"
