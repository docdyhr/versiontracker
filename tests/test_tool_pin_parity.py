"""Test that every site pinning ruff names the version the manifest (pyproject.toml) pins.

Dependabot's dev-tools group bumps ruff in pyproject.toml, requirements-dev.txt and
requirements-py313.txt, but never the pre-commit hook's ``rev``, so local commits linted with
an older ruff than CI (0.17.0 pinned, hook still v0.16.2, until PR #335). The required
"Code Linting and Formatting" job runs this file, so a ruff bump PR cannot merge until every
site moves. ``requirements-dev.lock`` is not a site: scripts/update_dependencies.py regenerates
it as a snapshot, and nothing installs from it.
"""

import re
import tomllib
from collections.abc import Callable
from pathlib import Path

import yaml
from packaging.requirements import InvalidRequirement, Requirement
from packaging.utils import canonicalize_name
from packaging.version import InvalidVersion, Version

PROJECT_ROOT = Path(__file__).parent.parent
# The drift self-test runs on these, never on the live files, so a drifted tree fails only the gate test.
# They also use layouts the live files don't (dependency groups, a second hook repo, a .git URL, -c).
FIXTURE_SITES = {
    "pyproject.toml": (
        '[project]\nname = "example"\nversion = "0"\n\n'
        '[project.optional-dependencies]\ndev = ["pytest>=8", "ruff==1.0.0"]\n\n'
        '[dependency-groups]\nstyle = [{include-group = "docs"}, "ruff==1.0.0"]\ndocs = ["sphinx>=8"]\n'
    ),
    "requirements-dev.txt": "-r requirements.txt\n-c constraints.txt\npytest>=8\nruff==1.0.0  # exact pin\n",
    "requirements-py313.txt": "mypy>=1.10\nruff==1.0.0\n",
    ".pre-commit-config.yaml": (
        "repos:\n"
        "  - repo: https://github.com/pre-commit/pre-commit-hooks\n    rev: v5.0.0\n"
        "    hooks:\n      - id: trailing-whitespace\n"
        "  - repo: https://github.com/astral-sh/ruff-pre-commit.git\n    rev: v1.0.0\n"
        "    hooks:\n      - id: ruff\n"
    ),
}


def as_version(text: str) -> Version | None:
    """Parse ``text`` as a PEP 440 version, or return None (a wildcard, a frozen SHA, ...)."""
    try:
        return Version(text)
    except InvalidVersion:
        return None


def ruff_versions(lines: list[str]) -> list[Version | None]:
    """Return the pinned version of every ruff requirement in ``lines`` (None for one that is not ``==X``)."""
    versions: list[Version | None] = []
    for line in lines:
        # Drop an inline comment, per-requirement pip options (--hash=...) and a trailing continuation backslash
        text = re.split(r"(?:^|\s)(?:#|--)", line, maxsplit=1)[0].strip().rstrip("\\").strip()
        try:
            requirement = Requirement(text)
        except InvalidRequirement:
            continue  # blank lines, comments and pip options such as -r and -c
        if canonicalize_name(requirement.name) == "ruff":
            specs = list(requirement.specifier)
            exact = len(specs) == 1 and specs[0].operator == "=="
            versions.append(as_version(specs[0].version) if exact else None)
    return versions


def collect_ruff_pins(root: Path) -> dict[str, list[Version | None]]:
    """Map each site under ``root`` that installs or runs ruff to the ruff versions it pins."""
    with open(root / "pyproject.toml", "rb") as f:
        pyproject = tomllib.load(f)
    groups = [
        *pyproject["project"].get("optional-dependencies", {}).values(),
        *pyproject.get("dependency-groups", {}).values(),
    ]
    pins = {"pyproject.toml": ruff_versions([dep for group in groups for dep in group if isinstance(dep, str)])}
    for name in ("requirements-dev.txt", "requirements-py313.txt"):
        pins[name] = ruff_versions((root / name).read_text(encoding="utf-8").splitlines())

    with open(root / ".pre-commit-config.yaml", encoding="utf-8") as f:
        pre_commit = yaml.safe_load(f)
    pins[".pre-commit-config.yaml"] = [
        as_version(str(repo.get("rev", "")).removeprefix("v"))
        for repo in pre_commit["repos"]
        if str(repo.get("repo", "")).rstrip("/").removesuffix(".git").endswith("/ruff-pre-commit")
    ]
    return pins


def find_ruff_pin_problems(pins: dict[str, list[Version | None]]) -> list[str]:
    """Describe every site that does not pin exactly the manifest's ruff version (empty when all agree)."""
    problems = [f"{site}: no ruff pin" for site, versions in pins.items() if not versions]
    problems += [f"{site}: a ruff entry is not an exact version" for site, versions in pins.items() if None in versions]
    manifest = {version for version in pins["pyproject.toml"] if version is not None}
    if len(manifest) > 1:
        problems.append(f"pyproject.toml pins ruff at several versions: {sorted(map(str, manifest))}")
    elif manifest:
        (truth,) = manifest
        problems += [
            f"{site}: pins {version}, pyproject.toml pins {truth}"
            for site, versions in pins.items()
            for version in versions
            if version is not None and version != truth
        ]
    return problems


def test_ruff_pinned_to_the_manifest_version_everywhere():
    """Every ruff pin site names the version pyproject.toml pins."""
    problems = find_ruff_pin_problems(collect_ruff_pins(PROJECT_ROOT))
    assert not problems, f"ruff pins disagree with the manifest: {problems}"


def test_ruff_pin_check_reports_drift(tmp_path):
    """The check reports a stale site on either side, an extra or non-exact requirement, and a removed pin."""

    def problems_after(name: str, edit: Callable[[str], str]) -> list[str]:
        for site, text in FIXTURE_SITES.items():
            (tmp_path / site).write_text(edit(text) if site == name else text, encoding="utf-8")
        return find_ruff_pin_problems(collect_ruff_pins(tmp_path))

    assert problems_after("requirements-dev.txt", lambda text: text) == []

    stale_hook = problems_after(".pre-commit-config.yaml", lambda text: text.replace("rev: v1.0.0", "rev: v0.0.1"))
    assert stale_hook == [".pre-commit-config.yaml: pins 0.0.1, pyproject.toml pins 1.0.0"], stale_hook

    manifest_moved = problems_after("pyproject.toml", lambda text: text.replace("ruff==1.0.0", "ruff==0.0.1"))
    for site in FIXTURE_SITES.keys() - {"pyproject.toml"}:
        assert f"{site}: pins 1.0.0, pyproject.toml pins 0.0.1" in manifest_moved, manifest_moved

    stale_group = problems_after(
        "pyproject.toml", lambda text: text.replace('"docs"}, "ruff==1.0.0"', '"docs"}, "ruff==0.0.1"')
    )
    assert any("several versions" in problem for problem in stale_group), stale_group

    second_extra = problems_after(
        "pyproject.toml",
        lambda text: text.replace(
            "[project.optional-dependencies]\n", '[project.optional-dependencies]\nlint = ["ruff==0.0.1"]\n'
        ),
    )
    assert any("several versions" in problem for problem in second_extra), second_extra

    tab_comment = problems_after("requirements-dev.txt", lambda text: text + "ruff==0.0.1\t# a second, stale pin\n")
    assert tab_comment == ["requirements-dev.txt: pins 0.0.1, pyproject.toml pins 1.0.0"], tab_comment

    extra = problems_after("requirements-dev.txt", lambda text: text + "ruff>=0.0.1\n")
    assert extra == ["requirements-dev.txt: a ruff entry is not an exact version"], extra

    removed = problems_after("requirements-py313.txt", lambda text: text.replace("ruff==1.0.0\n", ""))
    assert removed == ["requirements-py313.txt: no ruff pin"], removed


def test_requirement_lines_with_comments_options_and_continuations():
    """Inline comments, per-requirement pip options and hash continuation lines do not hide a pin."""
    lines = [
        "ruff==1.0.0 \\",
        "    --hash=sha256:00",
        "ruff==1.0.0 --hash=sha256:00",
        "ruff==1.0.0\t# note",
        "-c c.txt",
    ]
    assert ruff_versions(lines) == [Version("1.0.0")] * 3


def test_pep440_equal_spellings_agree():
    """``ruff==0.17`` and hook ``rev: v0.17.0`` are the same version, not drift."""
    pins = {"pyproject.toml": [Version("0.17")], ".pre-commit-config.yaml": [as_version("0.17.0")]}
    assert find_ruff_pin_problems(pins) == []
