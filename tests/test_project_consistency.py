"""Tests to ensure project configuration consistency."""

import re
import sys
import tomllib
from pathlib import Path
from typing import Any

import pytest
import yaml


def get_project_root() -> Path:
    """Get project root directory."""
    return Path(__file__).parent.parent


def load_pyproject_toml() -> dict[str, Any]:
    """Load pyproject.toml configuration."""
    project_root = get_project_root()
    pyproject_path = project_root / "pyproject.toml"
    with open(pyproject_path, "rb") as f:
        return tomllib.load(f)


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


def check_setup_cfg_version() -> str | None:
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


def extract_supported_versions(classifiers: list[str]) -> list[str]:
    """Extract supported Python versions from classifiers."""
    supported_versions: list[str] = []
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

    def _assert_setup_cfg_version(self, setup_version: str | None, min_version: str) -> None:
        """Assert setup.cfg version matches expected if it exists."""
        if setup_version is not None:
            msg = f"setup.cfg has {setup_version}, expected {min_version}"
            assert setup_version == min_version, msg

    def test_setup_cfg_python_version_consistency(self):
        """Test setup.cfg Python version matches pyproject.toml."""
        min_version = extract_min_python_version()
        setup_version = check_setup_cfg_version()
        self._assert_setup_cfg_version(setup_version, min_version)

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

        # Extract Python versions from test matrix (supports both "test" and "test-matrix" job names)
        test_job = ci_config["jobs"].get("test") or ci_config["jobs"].get("test-matrix")
        assert test_job is not None, "No 'test' or 'test-matrix' job found in ci.yml"
        ci_versions = test_job["strategy"]["matrix"]["python-version"]

        # Validate all supported versions are tested
        self._validate_ci_versions(supported_versions, ci_versions)

    def test_performance_baseline_promoted_only_on_success(self):
        """Test that a run failing the regression check never becomes the next baseline.

        With ``always()``, each failing run's slower numbers were cached as the
        next baseline, so every regression lowered the bar for the following run.
        """
        perf_path = get_project_root() / ".github" / "workflows" / "performance.yml"
        with open(perf_path, encoding="utf-8") as f:
            perf_config = yaml.safe_load(f)

        step_names = [step.get("name") for step in perf_config["jobs"]["performance-test"]["steps"]]
        steps = dict(zip(step_names, perf_config["jobs"]["performance-test"]["steps"], strict=True))
        compare_index = step_names.index("Compare with baseline (fail on >20% regression)")

        for name in ("Save new baseline", "Cache updated baseline for next run"):
            condition = steps[name]["if"]
            assert step_names.index(name) > compare_index, f"'{name}' must run after the regression check"
            assert "always()" not in condition, f"'{name}' must not run when the regression check fails"
            assert condition.startswith("success()"), f"'{name}' should be gated on success()"

    def test_steps_piping_into_tee_keep_exit_code(self):
        """Test that workflow steps piping into ``tee`` enable pipefail.

        ``pytest ... | tee log; EC=$?`` captures tee's exit code (always 0), so
        failing tests left CI and Coverage Analysis green until pipefail was set.
        """
        workflows_dir = get_project_root() / ".github" / "workflows"
        offenders = []
        for workflow_path in sorted(workflows_dir.glob("*.yml")):
            with open(workflow_path, encoding="utf-8") as f:
                workflow = yaml.safe_load(f)
            for job_name, job in workflow.get("jobs", {}).items():
                for step in job.get("steps", []):
                    script = step.get("run", "")
                    if re.search(r"\|\s*tee\b", script) and "pipefail" not in script:
                        offenders.append(f"{workflow_path.name}: {job_name} / {step.get('name', '<unnamed>')}")
        assert not offenders, f"Steps pipe into tee without pipefail, masking failures: {offenders}"

    def test_homebrew_release_regenerates_and_verifies_formula_resources(self):
        """Test that the Homebrew release re-resolves the formula's resources and tests what it pushes.

        Only url/sha256 were bumped, so the resource blocks stayed at v0.9.0's
        dependency set (no termcolor/idna/propcache, aiohttp below its CVE floor).
        The install test tapped a local clone, which copies committed state only,
        so it built the previous release — and ``--help``/``--version`` never import
        aiohttp, so a broken dependency tree passed anyway.
        """
        workflow_path = get_project_root() / ".github" / "workflows" / "release-homebrew.yml"
        with open(workflow_path, encoding="utf-8") as f:
            workflow = yaml.safe_load(f)
        scripts = [step.get("run", "") for step in workflow["jobs"]["update-homebrew"]["steps"]]

        def step_running(command: str) -> int:
            matches = [i for i, script in enumerate(scripts) if command in script]
            assert matches, f"No step runs '{command}'"
            return matches[0]

        install = step_running("brew install")
        assert step_running("brew update-python-resources") < install, (
            "Resources must be re-resolved before the install test"
        )
        install_script = scripts[install]
        assert "versiontracker --version" in install_script and "VERSION_NUMBER" in install_script, (
            "Install test must check that it built the release being pushed"
        )
        assert "--no-index" in install_script, "Install test must resolve the declared dependencies from the venv alone"

    def test_release_workflow_runs_once_per_release(self):
        """Test that publishing a release starts one Release run, not two.

        ``types: [created, published]`` fires twice for a non-draft release, so every
        release since v0.8.0 ran the whole pipeline twice; on v1.0.1 the second run's
        asset upload failed until ``--clobber`` was added to hide it.
        """
        workflow_path = get_project_root() / ".github" / "workflows" / "release.yml"
        with open(workflow_path, encoding="utf-8") as f:
            workflow = yaml.safe_load(f)
        assert workflow["on"]["release"]["types"] == ["published"], (
            "'published' alone covers stable releases, pre-releases and drafts being published"
        )

    def test_release_signs_published_files_and_follows_the_published_index(self):
        """Test that manual PyPI publishes attach signed assets and post-publish steps query the right index.

        Sign-and-attach only ran on release events, so re-publishing 1.2.0 via
        workflow_dispatch (after its tag-triggered run failed the test gate) left the
        GitHub release with no assets. The availability poll and the smoke test always
        queried PyPI, so a ``target=testpypi`` run failed after a successful upload.
        """
        workflow_path = get_project_root() / ".github" / "workflows" / "release.yml"
        with open(workflow_path, encoding="utf-8") as f:
            workflow = yaml.safe_load(f)
        jobs = workflow["jobs"]

        sign = jobs["sign-and-attach"]
        assert "index_host == 'pypi.org'" in sign["if"], "Manual PyPI publishes must sign and attach too"
        assert not any("download-artifact" in step.get("uses", "") for step in sign["steps"]), (
            "Sign the files the index serves, not this run's possibly non-identical rebuild"
        )
        assert any("sha256sum --check" in step.get("run", "") for step in sign["steps"]), (
            "Downloaded distributions must be checked against the index's digests"
        )
        sigstore = next(step for step in sign["steps"] if "gh-action-sigstore-python" in step.get("uses", ""))
        assert sigstore["with"]["release-signing-artifacts"] is False, (
            "The action attaches only on release events; the upload step must handle every event type"
        )
        upload = next(step for step in sign["steps"] if "gh release upload" in step.get("run", ""))
        assert "github.ref_name" not in upload["run"], "On workflow_dispatch, ref_name is the branch, not the tag"

        wait = next(
            step for step in jobs["publish-package"]["steps"] if step.get("name") == "Wait for package availability"
        )
        verify = next(step for step in jobs["verify-release"]["steps"] if "pip install" in step.get("run", ""))
        for step in (wait, verify):
            assert "index_host" in step["run"], f"'{step['name']}' must query the index the release was published to"

    def _assert_version_in_ci(self, version: str, ci_versions: list[str]) -> None:
        """Assert that a specific version is tested in CI."""
        error_msg = f"Python {version} is supported but not tested in CI"
        assert version in ci_versions, error_msg

    def _get_missing_versions(self, supported: list[str], ci_versions: list[str]) -> list[str]:
        """Get list of supported versions missing from CI."""
        return [version for version in supported if version not in ci_versions]

    def _validate_ci_versions(self, supported: list[str], ci_versions: list[str]) -> None:
        """Validate that all supported versions are tested in CI."""
        missing_versions = self._get_missing_versions(supported, ci_versions)
        msg = f"Python versions not tested in CI: {missing_versions}"
        assert not missing_versions, msg

    def _check_coveragerc_file(self, project_root: Path) -> None:
        """Check .coveragerc file if it exists."""
        coveragerc_path = project_root / ".coveragerc"
        if coveragerc_path.exists():
            with open(coveragerc_path, encoding="utf-8") as f:
                content = f.read()
                validate_coverage_config(content)

    def _check_pytest_ini_file(self, project_root: Path) -> None:
        """Check pytest.ini file if it exists."""
        pytest_ini_path = project_root / "pytest.ini"
        if pytest_ini_path.exists():
            with open(pytest_ini_path, encoding="utf-8") as f:
                content = f.read()
                has_cov_flag = "--cov-fail-under=0" in content
                no_cov_flag = "cov-fail-under" not in content
                dev_msg = "pytest.ini should not enforce coverage threshold"
                assert has_cov_flag or no_cov_flag, dev_msg

    def _check_pytest_ci_file(self, project_root: Path) -> None:
        """Check pytest-ci.ini file if it exists."""
        pytest_ci_path = project_root / "pytest-ci.ini"
        if pytest_ci_path.exists():
            with open(pytest_ci_path, encoding="utf-8") as f:
                content = f.read()
                ci_msg = "pytest-ci.ini should have --cov-fail-under=0"
                assert "--cov-fail-under=0" in content, ci_msg

    def test_coverage_configuration(self):
        """Test that coverage configuration is consistent."""
        project_root = get_project_root()

        # Check configuration files
        self._check_coveragerc_file(project_root)
        self._check_pytest_ini_file(project_root)
        self._check_pytest_ci_file(project_root)

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
