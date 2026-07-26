"""Shared fixtures/builders for versiontracker.audit tests.

make_app_bundle creates a real, minimal .app bundle on disk
(Contents/Info.plist, optionally Contents/_MASReceipt/receipt) so
discovery.py's filesystem-based probes (Info.plist reads, MAS receipt checks)
exercise real code paths instead of being mocked out. make_sp_entry/sp_data
build the system_profiler JSON shape used only for enrichment-matching tests
-- obtained_from isn't derivable from the filesystem, so those tests need a
system_profiler entry too.
"""

from __future__ import annotations

import plistlib
from pathlib import Path
from typing import Any

import pytest


def make_app_bundle(
    base: Path,
    name: str,
    *,
    version: str = "1.0",
    bundle_id: str | None = "com.example.app",
    has_mas_receipt: bool = False,
    write_plist: bool = True,
    extra_plist_keys: dict[str, Any] | None = None,
) -> Path:
    """Create a minimal real .app bundle under `base`.

    Returns the bundle's own path (base/{name}.app) so callers can nest
    further make_app_bundle() calls under bundle/"Contents"/"MacOS" to build
    helper bundles for nesting tests. extra_plist_keys is merged into the
    Info.plist before writing -- e.g. {"SUEnableAutomaticChecks": False} for
    Sparkle-preference tests.
    """
    bundle_path = base / f"{name}.app"
    contents = bundle_path / "Contents"
    contents.mkdir(parents=True, exist_ok=True)

    if write_plist:
        plist_data: dict[str, Any] = {
            "CFBundleName": name,
            "CFBundleShortVersionString": version,
        }
        if bundle_id is not None:
            plist_data["CFBundleIdentifier"] = bundle_id
        if extra_plist_keys:
            plist_data.update(extra_plist_keys)
        with (contents / "Info.plist").open("wb") as f:
            plistlib.dump(plist_data, f)

    if has_mas_receipt:
        receipt_dir = contents / "_MASReceipt"
        receipt_dir.mkdir(parents=True, exist_ok=True)
        (receipt_dir / "receipt").write_bytes(b"fake-receipt")

    return bundle_path


def make_sp_entry(
    bundle_path: Path,
    *,
    obtained_from: str | None = None,
    name: str | None = None,
    version: str | None = None,
    bundle_id: str | None = None,
) -> dict[str, Any]:
    """Build one SPApplicationsDataType-shaped entry for enrichment tests.

    Only needed when a test cares about obtained_from (or wants to prove
    system_profiler values take priority over Info.plist) -- the filesystem
    alone can't provide obtained_from.
    """
    entry: dict[str, Any] = {"path": str(bundle_path)}
    if name is not None:
        entry["_name"] = name
    if version is not None:
        entry["version"] = version
    if obtained_from is not None:
        entry["obtained_from"] = obtained_from
    if bundle_id is not None:
        entry["bundle_id"] = bundle_id
    return entry


def sp_data(*entries: dict[str, Any]) -> dict[str, Any]:
    """Wrap entries in the top-level SPApplicationsDataType envelope."""
    return {"SPApplicationsDataType": list(entries)}


def make_cask(
    token: str,
    *,
    tap: str = "homebrew/cask",
    installed: str | None = "1.0",
    app_name: str | None = None,
    app_target: str | None = None,
    auto_updates: bool = False,
) -> dict[str, Any]:
    """Build one real-shaped installed-cask entry (as `brew info --json=v2
    --cask --installed` returns it).

    app_name=None omits the `app` artifact entirely -- covers the common
    real-world case (23 of 69 installed casks on a real machine) of a cask
    with no app artifact at all (fonts, CLI tools, pkg-only installers).
    """
    artifacts: list[dict[str, Any]] = []
    if app_name is not None:
        target = app_target if app_target is not None else f"/Applications/{app_name}"
        artifacts.append({"app": [app_name], "target": target})

    return {
        "token": token,
        "tap": tap,
        "name": [token.replace("-", " ").title()],
        "installed": installed,
        "auto_updates": auto_updates,
        "artifacts": artifacts,
    }


def make_installed_casks_payload(*casks: dict[str, Any]) -> dict[str, Any]:
    """Wrap casks in the real `brew info --json=v2 --cask --installed` envelope."""
    return {"formulae": [], "casks": list(casks)}


def add_sparkle_framework(bundle_path: Path) -> Path:
    """Add a minimal Contents/Frameworks/Sparkle.framework to an existing bundle.

    Returns the framework path. Combine with make_app_bundle(...,
    extra_plist_keys={"SUEnableAutomaticChecks": True/False}) to test the
    enabled/disabled/unset preference cases.
    """
    framework_path = bundle_path / "Contents" / "Frameworks" / "Sparkle.framework"
    framework_path.mkdir(parents=True, exist_ok=True)
    return framework_path


def add_squirrel_framework(bundle_path: Path, *, include_shipit: bool = True) -> Path:
    """Add a minimal Contents/Frameworks/Squirrel.framework to an existing
    bundle, with ShipIt nested inside Resources/ (matching real layout)."""
    framework_path = bundle_path / "Contents" / "Frameworks" / "Squirrel.framework"
    resources_path = framework_path / "Resources"
    resources_path.mkdir(parents=True, exist_ok=True)
    if include_shipit:
        (resources_path / "ShipIt").write_bytes(b"")
    return framework_path


def add_electron_update_yml(
    bundle_path: Path,
    *,
    provider: str | None = "generic",
    url: str = "https://example.com/updates",
    malformed: bool = False,
) -> Path:
    """Add a Contents/Resources/app-update.yml to an existing bundle."""
    resources_path = bundle_path / "Contents" / "Resources"
    resources_path.mkdir(parents=True, exist_ok=True)
    yml_path = resources_path / "app-update.yml"
    if malformed:
        yml_path.write_text("not: valid: yaml: [", encoding="utf-8")
    else:
        lines = []
        if provider is not None:
            lines.append(f"provider: {provider}")
        lines.append(f"url: {url}")
        yml_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return yml_path


def add_mozilla_updater(
    bundle_path: Path,
    *,
    include_ini: bool = True,
    include_launch_services_entry: bool = True,
) -> Path:
    """Add a Contents/MacOS/updater.app (+ corroborating files) to an
    existing bundle, matching Firefox's real layout."""
    updater_app = bundle_path / "Contents" / "MacOS" / "updater.app"
    updater_app.mkdir(parents=True, exist_ok=True)

    if include_ini:
        ini_path = bundle_path / "Contents" / "Resources" / "updater.ini"
        ini_path.parent.mkdir(parents=True, exist_ok=True)
        ini_path.write_text("[Strings]\nTitle=Update\n", encoding="utf-8")

    if include_launch_services_entry:
        ls_path = bundle_path / "Contents" / "Library" / "LaunchServices" / "org.mozilla.updater"
        ls_path.parent.mkdir(parents=True, exist_ok=True)
        ls_path.write_bytes(b"")

    return updater_app


def make_launch_agent_plist(
    directory: Path,
    filename: str,
    *,
    label: str | None = "auto",
    unreadable: bool = False,
) -> Path:
    """Create one *.plist file in `directory` (a fake LaunchAgents/Daemons dir).

    filename should include the .plist suffix. label="auto" derives the
    Label key from the filename stem (the common case); label=None omits
    the Label key entirely (reproduces the real Google Keystone empty-stub
    plist); an explicit different string reproduces the real Logi Options+
    filename/Label mismatch. unreadable=True writes garbage bytes instead of
    a valid plist, simulating an unreadable/corrupt file (content-level
    failure, distinct from a permission error, which tests simulate via
    monkeypatching per the project's established pattern).
    """
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / filename
    if unreadable:
        path.write_bytes(b"not a plist")
        return path

    stem = filename[: -len(".plist")] if filename.endswith(".plist") else filename
    data: dict[str, Any] = {}
    if label == "auto":
        data["Label"] = stem
    elif label is not None:
        data["Label"] = label
    with path.open("wb") as f:
        plistlib.dump(data, f)
    return path


@pytest.fixture
def app_bundle_factory():
    """Factory fixture wrapping make_app_bundle."""
    return make_app_bundle


@pytest.fixture
def sp_entry_factory():
    """Factory fixture wrapping make_sp_entry."""
    return make_sp_entry


@pytest.fixture
def sp_data_factory():
    """Factory fixture wrapping sp_data."""
    return sp_data


@pytest.fixture
def hermetic_roots(tmp_path: Path) -> list[Path]:
    """A roots list confined to tmp_path, for discover_applications(roots=...).

    Never touches the real machine's /Applications or ~/Applications.
    """
    return [tmp_path]


@pytest.fixture
def cask_factory():
    """Factory fixture wrapping make_cask."""
    return make_cask


@pytest.fixture
def installed_casks_payload_factory():
    """Factory fixture wrapping make_installed_casks_payload."""
    return make_installed_casks_payload


@pytest.fixture
def sparkle_framework_factory():
    """Factory fixture wrapping add_sparkle_framework."""
    return add_sparkle_framework


@pytest.fixture
def squirrel_framework_factory():
    """Factory fixture wrapping add_squirrel_framework."""
    return add_squirrel_framework


@pytest.fixture
def electron_update_yml_factory():
    """Factory fixture wrapping add_electron_update_yml."""
    return add_electron_update_yml


@pytest.fixture
def mozilla_updater_factory():
    """Factory fixture wrapping add_mozilla_updater."""
    return add_mozilla_updater


@pytest.fixture
def launch_agent_plist_factory():
    """Factory fixture wrapping make_launch_agent_plist."""
    return make_launch_agent_plist
