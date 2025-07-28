"""Tests to ensure project configuration consistency."""

import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import pytest
import toml
import yaml


def get_project_root() -> Path:
    """Get project root directory."""
    return Path(__file__).parent.parent


def load_pyproject_toml() -> Dict[str, Any]:
    """Load pyproject.toml configuration."""
    project_root = get_project_root()
    pyproject_path = project_root / "pyproject.toml"
    with open(pyproject_path, encoding="utf-8") as f:
        return toml.load(f)


def extract_min_python_version() -> str:
    """Extract minimum Python version from pyproject.toml."""
    pyproject = load_pyproject_toml()
    requires_python = pyproject["project"]["requires-python"]
    min_version_match = re.match(r">=(\d+\.\d+)", requires_python)
    if not min_version_match:
        pytest.fail(f"Invalid requires-python format: {requires_python}")
    return min_version_match.group(1)


def check_mypy_version() -> str:
    """Check Python version in mypy.ini."""
    project_root = get_project_root()
    mypy_ini_path = project_root / "mypy.ini"
    if not mypy_ini_path.exists():
        pytest.skip(f"mypy.ini not found at {mypy_ini_path}")

    with open(mypy_ini_path, encoding="utf-8") as f:
        content = f.read()

    mypy_version_match = re.search(r"python_version\s*=\s*(\d+\.\d+)", content)
    if not mypy_version_match:
        pytest.fail("python_version not found in mypy.ini")
    return mypy_version_match.group(1)


def check_setup_cfg_version() -> Optional[str]:
    """Check Python version in setup.cfg if it exists."""
    project_root = get_project_root()
    setup_cfg_path = project_root / "setup.cfg"
    if not setup_cfg_path.exists():
        return None

    with open(setup_cfg_path, encoding="utf-8") as f:
        content = f.read()

    version_pattern = r"python_version\s*=\s*(\d+\.\d+)"
    setup_version_match = re.search(version_pattern, content)
    return setup_version_match.group(1) if setup_version_match else None


def check_readme_version() -> str:
    """Check Python version requirement in README.md."""
    project_root = get_project_root()
    readme_path = project_root / "README.md"
    with open(readme_path, encoding="utf-8") as f:
        content = f.read()

    version_pattern = r"Python\s+(\d+\.\d+)\s+or\s+later"
    readme_version_match = re.search(version_pattern, content)
    if not readme_version_match:
        pytest.fail("Python version requirement not found in README.md")
    return readme_version_match.group(1)


def check_ruff_target_version() -> str:
    """Check Ruff target version in pyproject.toml."""
    pyproject = load_pyproject_toml()
    tools = pyproject.get("tool", {})
    ruff_config = tools.get("ruff", {})
    ruff_target = ruff_config.get("target-version")
    if not ruff_target:
        pytest.fail("Ruff target-version not found in pyproject.toml")
    return ruff_target


def extract_supported_versions(classifiers: List[str]) -> List[str]:
    """Extract supported Python versions from classifiers."""
    supported_versions: List[str] = []
    python_pattern = r"Programming Language :: Python :: (\d+\.\d+)"

    for classifier in classifiers:
        match = re.match(python_pattern, classifier)
        if match:
            supported_versions.append(match.group(1))
    return supported_versions


def validate_coverage_config(content: str) -> None:
    """Validate coverage configuration content."""
    fail_under_pattern = r"fail_under\s*=\s*(\d+)"
    fail_under_match = re.search(fail_under_pattern, content)
    if fail_under_match:
        fail_under = int(fail_under_match.group(1))
        high_msg = f"Coverage fail_under is {fail_under}%, too high"
        low_msg = f"Coverage fail_under is {fail_under}%, consider raising"
        assert fail_under <= 70, high_msg
        assert fail_under >= 50, low_msg


def validate_constraints_content(content: str) -> None:
    """Validate constraints.txt content."""
    assert len(content) > 100, "constraints.txt seems too small"
    ge_msg = "constraints.txt should contain version constraints"
    assert ">=" in content, ge_msg
    lt_msg = "constraints.txt should contain upper bounds"
    assert "<" in content, lt_msg


class TestProjectConsistency:
    """Test project configuration consistency."""

    def test_mypy_python_version_consistency(self):
        """Test that mypy.ini Python version matches pyproject.toml."""
        min_version = extract_min_python_version()
        mypy_version = check_mypy_version()
        error_msg = f"mypy.ini has {mypy_version}, expected {min_version}"
        assert mypy_version == min_version, error_msg

    def test_setup_cfg_python_version_consistency(self):
        """Test setup.cfg Python version matches pyproject.toml."""
        min_version = extract_min_python_version()
        setup_version = check_setup_cfg_version()

        if setup_version is not None:
            msg = f"setup.cfg has {setup_version}, expected {min_version}"
            assert setup_version == min_version, msg

    def test_readme_python_version_consistency(self):
        """Test that README.md Python version matches pyproject.toml."""
        min_version = extract_min_python_version()
        readme_version = check_readme_version()
        error_msg = f"README.md has {readme_version}, expected {min_version}"
        assert readme_version == min_version, error_msg

    def test_ruff_target_version_consistency(self):
        """Test that Ruff target version matches minimum Python version."""
        min_version = extract_min_python_version()
        ruff_target = check_ruff_target_version()
        expected_ruff = f"py{min_version.replace('.', '')}"
        error_msg = f"Ruff target is {ruff_target}, expected {expected_ruff}"
        assert ruff_target == expected_ruff, error_msg

    def test_ci_python_versions(self):
        """Test that CI workflows test appropriate Python versions."""
        project_root = get_project_root()

        # Read supported versions from pyproject.toml
        pyproject = load_pyproject_toml()
        classifiers = pyproject["project"]["classifiers"]
        supported_versions = extract_supported_versions(classifiers)

        # Check CI workflow
        ci_path = project_root / ".github" / "workflows" / "ci.yml"
        with open(ci_path, encoding="utf-8") as f:
            ci_config = yaml.safe_load(f)

        # Extract Python versions from test matrix
        test_job = ci_config["jobs"]["test"]
        ci_versions = test_job["strategy"]["matrix"]["python-version"]

        # Validate all supported versions are tested
        self._validate_ci_versions(supported_versions, ci_versions)

    def _validate_ci_versions(self, supported: List[str], ci_versions: List[str]) -> None:
        """Validate that all supported versions are tested in CI."""
        for version in supported:
            error_msg = f"Python {version} is supported but not tested in CI"
            assert version in ci_versions, error_msg

    def test_coverage_configuration(self):
        """Test that coverage configuration is consistent."""
        project_root = get_project_root()

        # Check .coveragerc
        coveragerc_path = project_root / ".coveragerc"
        if coveragerc_path.exists():
            with open(coveragerc_path, encoding="utf-8") as f:
                content = f.read()
                validate_coverage_config(content)

        # Check pytest.ini settings
        pytest_ini_path = project_root / "pytest.ini"
        if pytest_ini_path.exists():
            with open(pytest_ini_path, encoding="utf-8") as f:
                content = f.read()
                has_cov_flag = "--cov-fail-under=0" in content
                no_cov_flag = "cov-fail-under" not in content
                dev_msg = "pytest.ini should not enforce coverage threshold"
                assert has_cov_flag or no_cov_flag, dev_msg

        # Check pytest-ci.ini settings
        pytest_ci_path = project_root / "pytest-ci.ini"
        if pytest_ci_path.exists():
            with open(pytest_ci_path, encoding="utf-8") as f:
                content = f.read()
                ci_msg = "pytest-ci.ini should have --cov-fail-under=0"
                assert "--cov-fail-under=0" in content, ci_msg

    def test_dependency_constraints(self):
        """Test that constraints.txt exists and is valid."""
        project_root = get_project_root()
        constraints_path = project_root / "constraints.txt"

        assert constraints_path.exists(), "constraints.txt file is missing"

        # Basic validation - file should not be empty and contain specs
        with open(constraints_path, encoding="utf-8") as f:
            content = f.read()
            validate_constraints_content(content)

    def test_current_python_version(self):
        """Test that tests are running on a supported Python version."""
        current_version = f"{sys.version_info.major}.{sys.version_info.minor}"

        # We support Python 3.9+
        req_msg = f"Tests on Python {current_version}, but 3.9+ required"
        assert sys.version_info >= (3, 9), req_msg
