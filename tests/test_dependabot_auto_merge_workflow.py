"""Tests for the Dependabot patch auto-merge workflow and the constraints in setup-python-deps.

fetch-metadata reports requirement-range updates (constraints.txt ``>=a,<b``) as semver-major,
because it reads previous-version from the range string (``10.0.0,>=9.1.0``). The workflow's
``level`` step derives the real bump level from the PR title instead. The required checks install
with ``-c constraints.txt``, and the required lint job resolves the whole file, so a range that
doesn't resolve fails them before auto-merge can land it. The fixtures
marked "run" are the fetch-metadata outputs and titles of real runs on this repo (2026-10-26/27).
"""

import os
import shutil
import stat
import subprocess
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parent.parent
WORKFLOW = ROOT / ".github" / "workflows" / "dependabot-auto-merge.yml"
ACTION = ROOT / ".github" / "actions" / "setup-python-deps" / "action.yml"
LINT = ROOT / ".github" / "workflows" / "lint.yml"

PATCH = "version-update:semver-patch"
MINOR = "version-update:semver-minor"
MAJOR = "version-update:semver-major"
BASH = os.environ.get("VT_TEST_BASH") or shutil.which("bash") or "bash"

pytestmark = pytest.mark.skipif(shutil.which(BASH) is None, reason="bash is required to run the workflow scripts")


def _workflow_steps() -> list[dict]:
    return yaml.safe_load(WORKFLOW.read_text())["jobs"]["auto-merge"]["steps"]


def _level_script() -> str:
    for step in _workflow_steps():
        if step.get("id") == "level":
            return step["run"]
    pytest.fail("dependabot-auto-merge.yml has no step with id 'level'")


def _derive(meta_type: str, prev: str, title: str, tmp_path: Path) -> str:
    """Run the level step as GitHub does for a default-shell step (bash -e) and read its output."""
    script = tmp_path / "level.sh"
    script.write_text(_level_script())
    out = tmp_path / "github_output"
    out.write_text("")
    env = {
        "PATH": os.environ["PATH"],
        "META_TYPE": meta_type,
        "PREV": prev,
        "TITLE": title,
        "GITHUB_OUTPUT": str(out),
    }
    subprocess.run(
        [BASH, "--noprofile", "--norc", "-e", str(script)],
        env=env,
        cwd=tmp_path,
        check=True,
        capture_output=True,
        text=True,
        timeout=10,
    )
    lines = [line for line in out.read_text().splitlines() if line.startswith("update-type=")]
    assert len(lines) == 1, lines
    return lines[0].split("=", 1)[1]


@pytest.mark.parametrize(
    ("meta_type", "prev", "title", "expected"),
    [
        # run 40478242807 (#346): a true patch that fetch-metadata called major
        (
            MAJOR,
            "10.0.0,>=9.1.0",
            "deps(deps): update sphinx requirement from <10.0.0,>=9.1.0 to >=9.1.1,<10.0.0",
            PATCH,
        ),
        # run 40478270225 (#348)
        (
            MAJOR,
            "22.0.0,>=21.14.6",
            "deps(deps): update virtualenv requirement from <22.0.0,>=21.14.6 to >=21.14.13,<22.0.0",
            PATCH,
        ),
        # run 40478256456 (#347)
        (
            MAJOR,
            "5.0.0,>=4.1.1",
            "deps(deps): update filelock requirement from <5.0.0,>=4.1.1 to >=4.2.4,<5.0.0",
            MINOR,
        ),
        # run 40478285417 (#349)
        (MAJOR, "5.0.0,>=4.65.3", "deps(deps): update tox requirement from <5.0.0,>=4.65.3 to >=4.67.1,<5.0.0", MINOR),
        # run 40478297662 (#350)
        (
            MAJOR,
            "8.0.0,>=7.16.2",
            "deps(deps): update coverage requirement from <8.0.0,>=7.16.2 to >=7.17.0,<8.0.0",
            MINOR,
        ),
        # #334's title (merged before the workflow existed): a date-stamped stub release is a patch
        (
            MAJOR,
            "85.0.0,>=84.0.0.20260812",
            "deps(deps): update types-setuptools requirement from <85.0.0,>=84.0.0.20260812"
            " to >=84.0.0.20261006,<85.0.0",
            PATCH,
        ),
        # #342's title: lower bound only, no upper bound on either side
        (MAJOR, ">=4.6.2", "deps(deps): update pre-commit requirement from >=4.6.2 to >=4.7.0", MINOR),
        # a range in a subdirectory manifest carries an " in /dir" suffix
        (
            MAJOR,
            "10.0.0,>=9.1.0",
            "deps(deps): update sphinx requirement from <10.0.0,>=9.1.0 to >=9.1.1,<10.0.0 in /docs",
            PATCH,
        ),
    ],
)
def test_range_update_level_comes_from_the_title(meta_type, prev, title, expected, tmp_path):
    """A requirement-range update is classified by its bounds, not by fetch-metadata's update-type."""
    assert _derive(meta_type, prev, title, tmp_path) == expected


@pytest.mark.parametrize(
    "title",
    [
        "deps(deps): update coverage requirement from <8.0.0,>=7.16.2 to >=7.16.2,<9.0.0",
        "deps(deps): update coverage requirement from <8.0.0,>=7.16.2 to >=7.16.3,<9.0.0",
        "deps(deps): update coverage requirement from <8.0.0,>=7.16.2 to >=7.16.3",
    ],
)
def test_changed_upper_bound_is_major(title, tmp_path):
    """Moving or dropping the upper bound admits new releases wholesale, so it is never a patch."""
    assert _derive(MAJOR, "8.0.0,>=7.16.2", title, tmp_path) == MAJOR


@pytest.mark.parametrize(
    ("meta_type", "prev", "title"),
    [
        # run 40478271548 (#339's group, before its rebase to 0.17.2)
        (PATCH, "0.17.0", "deps(deps): bump ruff from 0.17.0 to 0.17.1 in the dev-tools group across 1 directory"),
        # run 40297274855 (#345)
        (PATCH, "3.99.2", "ci(deps): bump trufflesecurity/trufflehog from 3.99.2 to 3.99.7"),
        (MAJOR, "6", "ci(deps): bump actions/setup-python from 6 to 7 in the actions-all group"),
        (MINOR, "1.2.3", "deps(deps): bump example from 1.2.3 to 1.3.0"),
    ],
)
def test_plain_version_keeps_fetch_metadata_type(meta_type, prev, title, tmp_path):
    """Exact pins and Actions bumps already classify correctly; their type passes through unchanged."""
    assert _derive(meta_type, prev, title, tmp_path) == meta_type


@pytest.mark.parametrize(
    "title",
    [
        "deps(deps): something Dependabot never titles a range update",
        "deps(deps): update sphinx requirement from <10.0.0,>=9.1.0 to <10.0.0,>=9.1.0",
        "deps(deps): update odd requirement from >=1.2. to >=1.2",
    ],
)
def test_unclassifiable_range_update_is_skipped(title, tmp_path):
    """Anything the step can't read yields an empty type, which the merge steps treat as 'skip'."""
    assert _derive(MAJOR, "10.0.0,>=9.1.0", title, tmp_path) == ""


def test_title_is_data_not_code(tmp_path):
    """The PR title reaches the script through env, so shell syntax in it never executes."""
    title = 'deps(deps): update x requirement from $(touch pwned) to `touch pwned2`; touch "pwned3"'
    assert _derive(MAJOR, "1.0,>=0.9", title, tmp_path) == ""
    assert not list(tmp_path.glob("pwned*"))
    assert "${{" not in _level_script()


def test_merge_steps_gate_on_the_derived_level():
    """Approve, auto-merge and the skip report all read the derived level, not fetch-metadata's."""
    gated = {s["name"]: s["if"] for s in _workflow_steps() if "if" in s}
    assert set(gated) == {"Approve patch bump", "Enable auto-merge for patch bump", "Report skipped PR"}
    for name, condition in gated.items():
        assert "steps.level.outputs.update-type" in condition, name
        assert "steps.meta.outputs.update-type" not in condition, name
        assert "contains(steps.meta.outputs.dependency-names, 'ruff')" in condition, name


def _run_action_steps(tmp_path: Path, with_constraints: bool) -> list[str]:
    """Run setup-python-deps' install steps (shell: bash) against a recording fake pip."""
    bindir = tmp_path / "bin"
    bindir.mkdir()
    log = tmp_path / "pip.log"
    fake = bindir / "pip"
    fake.write_text(f'#!/bin/sh\necho "$*" >> "{log}"\n')
    fake.chmod(fake.stat().st_mode | stat.S_IEXEC)
    work = tmp_path / "repo"
    work.mkdir()
    for name in ("requirements.txt", "requirements-dev.txt", "pyproject.toml"):
        (work / name).write_text("")
    if with_constraints:
        (work / "constraints.txt").write_text("")
    steps = yaml.safe_load(ACTION.read_text())["runs"]["steps"]
    install = [s for s in steps if s["name"] in ("Install project dependencies", "Install package in editable mode")]
    assert len(install) == 2
    env = {"PATH": f"{bindir}{os.pathsep}{os.environ['PATH']}"}
    for step in install:
        assert step["shell"] == "bash"
        subprocess.run(
            [BASH, "--noprofile", "--norc", "-eo", "pipefail", "-c", step["run"]],
            env=env,
            cwd=work,
            check=True,
            capture_output=True,
            text=True,
            timeout=10,
        )
    return log.read_text().splitlines()


def test_action_installs_requirements_with_constraints(tmp_path):
    """Every requirements and package install is constrained, so CI resolves constraints.txt."""
    calls = _run_action_steps(tmp_path, with_constraints=True)
    constrained = [
        c for c in calls if c.startswith("install -r requirements") or c.startswith("install -e .[dev,test]")
    ]
    assert [c.split()[2] for c in constrained] == ["requirements.txt", "requirements-dev.txt", ".[dev,test]"]
    for call in constrained:
        assert call.endswith("-c constraints.txt"), call


def test_required_lint_check_resolves_the_whole_constraints_file():
    """The required lint job resolves constraints.txt on its own.

    pip ignores a constraint for any package the install doesn't pull in, so without this step a
    constraints-only PR for sphinx, tox, virtualenv or pre-commit is never resolved by CI at all.
    """
    job = yaml.safe_load(LINT.read_text())["jobs"]["lint"]
    assert job["name"] == "Code Linting and Formatting"  # a required status check on main
    runs = [s.get("run", "") for s in job["steps"]]
    names = [s.get("name", "") for s in job["steps"]]
    check = [i for i, r in enumerate(runs) if "--dry-run" in r and "-r constraints.txt" in r]
    assert len(check) == 1, runs
    assert "--ignore-installed" in runs[check[0]]
    assert check[0] > names.index("Install dependencies")
    assert "continue-on-error" not in job["steps"][check[0]]


def test_action_without_constraints_file_still_installs(tmp_path):
    """A checkout without constraints.txt (the action is generic) installs unconstrained."""
    calls = _run_action_steps(tmp_path, with_constraints=False)
    assert "install -r requirements.txt" in calls
    assert "install -r requirements-dev.txt" in calls
    assert not any("constraints.txt" in c for c in calls)
