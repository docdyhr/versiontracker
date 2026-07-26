"""Identity-preserving discovery for the unmanaged macOS application audit feature.

Discovery walks the filesystem directly under the resolved roots (default
locations, configured additional_app_dirs, and caller-supplied extra roots).
Parsed system_profiler data, if supplied, is used only to *enrich* records
already found by the walk (name/version/obtained_from) -- it is never the
source of which bundles exist, since additional_app_dirs and ~/Applications
entries are not guaranteed to already be indexed by system_profiler.

No network access, no subprocess calls.
"""

from __future__ import annotations

import logging
import plistlib
from collections.abc import Iterator, Sequence
from pathlib import Path
from typing import Any

from versiontracker.audit.models import (
    ApplicationRecord,
    AppStoreEvidence,
    AppStoreStatus,
    EvidenceConfidence,
    EvidenceSource,
)
from versiontracker.config import get_config

_APP_SUFFIX = ".app"
_APP_STORE_OBTAINED_FROM_VALUES = frozenset({"mac_app_store", "ios_app_store"})


def default_discovery_roots() -> list[Path]:
    """Built-in discovery roots: /Applications and ~/Applications.

    Computed per call (not at import time) so tests can patch Path.home().
    """
    return [Path("/Applications"), Path.home() / "Applications"]


def configured_discovery_roots() -> list[Path]:
    """Additional roots from config (additional_app_dirs).

    Reads via Config.get("additional_app_dirs", []) -- the real accessor.
    getattr(get_config(), "additional_app_dirs", default) must NOT be used
    here: Config has no such attribute or property, so getattr would always
    silently return the fallback default instead of the configured value.
    """
    raw_dirs = get_config().get("additional_app_dirs", [])
    return [Path(entry) for entry in raw_dirs]


def resolve_discovery_roots(extra_roots: Sequence[str | Path] | None = None) -> list[Path]:
    """Combine default, configured, and caller-supplied roots.

    extra_roots stands in for the future CLI --additional-dirs flag (wired
    up in a later phase); here it is just a plain, additive parameter. Roots
    are expanded (~), resolved, and de-duplicated in first-seen order.
    """
    candidates: list[Path] = [*default_discovery_roots(), *configured_discovery_roots()]
    if extra_roots:
        candidates.extend(Path(entry) for entry in extra_roots)

    resolved: list[Path] = []
    seen: set[Path] = set()
    for candidate in candidates:
        try:
            resolved_candidate = candidate.expanduser().resolve()
        except OSError as e:
            logging.debug("Could not resolve discovery root %s: %s", candidate, e)
            continue
        if resolved_candidate not in seen:
            seen.add(resolved_candidate)
            resolved.append(resolved_candidate)
    return resolved


def _log_walk_error(error: OSError) -> None:
    logging.debug("Cannot list a directory during discovery walk: %s", error)


def _walk_root(root: Path, *, include_nested: bool) -> Iterator[Path]:
    """Yield raw (not yet resolved) paths of .app bundles found under root.

    Uses Path.walk() (top-down, no symlink following) so that, when
    include_nested is False, matched bundle directories can be pruned from
    dirnames in place -- the standard os.walk/Path.walk idiom for stopping
    descent into an already-matched directory. When include_nested is True,
    no pruning happens, so the walk naturally continues into Contents/... and
    finds nested helper bundles too.
    """
    if not root.is_dir():
        return

    for dirpath, dirnames, _filenames in root.walk(top_down=True, on_error=_log_walk_error, follow_symlinks=False):
        app_dirnames = [d for d in dirnames if d.lower().endswith(_APP_SUFFIX)]
        for app_dirname in app_dirnames:
            yield dirpath / app_dirname
        if not include_nested:
            dirnames[:] = [d for d in dirnames if d not in app_dirnames]


def _nearest_parent_bundle(path: Path, root: Path) -> Path | None:
    """Nearest `.app` ancestor of `path` strictly between `root` and `path`, or None if not nested.

    Walks from root down to path (not path's own final component) so the
    last .app ancestor encountered is the nearest enclosing bundle.
    """
    try:
        relative_parts = path.relative_to(root).parts
    except ValueError:
        return None

    current = root
    nearest: Path | None = None
    for part in relative_parts[:-1]:
        current = current / part
        if current.suffix.lower() == _APP_SUFFIX:
            nearest = current
    return nearest


def _read_info_plist(bundle_path: Path) -> dict[str, Any]:
    """Read Contents/Info.plist, returning {} on any read/parse failure.

    Never raises -- same defensive pattern as
    versiontracker/plugins/example_plugins.py::_get_app_info. Deliberately
    catches Exception broadly, not a specific tuple: confirmed live on a
    real machine that a genuinely malformed plist can raise
    xml.parsers.expat.ExpatError (via plistlib's XML parser), which is
    neither OSError, ValueError, nor plistlib.InvalidFileException -- a
    narrower tuple silently fails this function's own "never raises"
    contract the moment a real Info.plist is corrupt.
    """
    plist_path = bundle_path / "Contents" / "Info.plist"
    try:
        with plist_path.open("rb") as f:
            data = plistlib.load(f)
    except Exception as e:
        logging.debug("Could not read Info.plist for %s: %s", bundle_path, e)
        return {}
    return data if isinstance(data, dict) else {}


def _has_mas_receipt(bundle_path: Path) -> bool | None:
    """Check for Contents/_MASReceipt/receipt.

    Returns True/False when the check completed, or None if the filesystem
    probe itself failed (e.g. permission denied) -- distinct from a
    confirmed absence, so callers can tell "not App Store" apart from
    "couldn't determine."
    """
    receipt_path = bundle_path / "Contents" / "_MASReceipt" / "receipt"
    try:
        return receipt_path.exists()
    except OSError as e:
        logging.debug("Could not check Mac App Store receipt for %s: %s", bundle_path, e)
        return None


def resolve_app_store_evidence(bundle_path: Path, obtained_from: str | None) -> AppStoreEvidence:
    """Resolve App Store evidence from two independent local signals.

    Signal 1: system_profiler's obtained_from value (mac_app_store /
    ios_app_store indicate a store install; any other non-empty value does
    not). Signal 2: presence of Contents/_MASReceipt/receipt, which macOS
    requires for a genuine App Store install. When the signals conflict, the
    receipt is treated as the more mechanically authoritative one (
    obtained_from can be stale, or simply unavailable for bundles the
    filesystem walk found but system_profiler didn't index) -- but the
    conflict is always recorded in `reason`, never silently dropped. Only a
    failed filesystem probe (permission/I-O error) yields UNKNOWN.
    """
    normalized_obtained_from = obtained_from.strip().lower() if obtained_from else None
    reports_app_store = normalized_obtained_from in _APP_STORE_OBTAINED_FROM_VALUES

    has_receipt = _has_mas_receipt(bundle_path)
    if has_receipt is None:
        return AppStoreEvidence(
            status=AppStoreStatus.UNKNOWN,
            reason="Could not check for a Mac App Store receipt (filesystem probe failed)",
            source=EvidenceSource.FILESYSTEM,
            confidence=EvidenceConfidence.NONE,
            error="permission or I/O error reading Contents/_MASReceipt/receipt",
        )

    if normalized_obtained_from is None:
        if has_receipt:
            return AppStoreEvidence(
                status=AppStoreStatus.APP_STORE,
                reason="No system_profiler obtained_from was available; a Mac App Store receipt was found",
                source=EvidenceSource.FILESYSTEM,
                matched_identifier="_MASReceipt/receipt",
                confidence=EvidenceConfidence.MEDIUM,
            )
        return AppStoreEvidence(
            status=AppStoreStatus.NOT_APP_STORE,
            reason="No system_profiler obtained_from was available and no Mac App Store receipt was found",
            source=EvidenceSource.FILESYSTEM,
            confidence=EvidenceConfidence.MEDIUM,
        )

    if reports_app_store and has_receipt:
        return AppStoreEvidence(
            status=AppStoreStatus.APP_STORE,
            reason=f"system_profiler reported obtained_from='{normalized_obtained_from}', corroborated by a Mac App Store receipt",
            source=EvidenceSource.SYSTEM_PROFILER,
            matched_identifier=normalized_obtained_from,
            confidence=EvidenceConfidence.HIGH,
        )
    if reports_app_store and not has_receipt:
        return AppStoreEvidence(
            status=AppStoreStatus.APP_STORE,
            reason=(
                f"system_profiler reported obtained_from='{normalized_obtained_from}' "
                "but no Contents/_MASReceipt/receipt was found"
            ),
            source=EvidenceSource.SYSTEM_PROFILER,
            matched_identifier=normalized_obtained_from,
            confidence=EvidenceConfidence.MEDIUM,
        )
    if not reports_app_store and has_receipt:
        return AppStoreEvidence(
            status=AppStoreStatus.APP_STORE,
            reason=(
                "Contents/_MASReceipt/receipt is present, which conflicts with system_profiler's "
                f"obtained_from='{normalized_obtained_from}'; treating the receipt as authoritative"
            ),
            source=EvidenceSource.FILESYSTEM,
            matched_identifier="_MASReceipt/receipt",
            confidence=EvidenceConfidence.MEDIUM,
        )
    return AppStoreEvidence(
        status=AppStoreStatus.NOT_APP_STORE,
        reason=(
            f"system_profiler reported obtained_from='{normalized_obtained_from}', not an App Store "
            "source, and no receipt was found"
        ),
        source=EvidenceSource.SYSTEM_PROFILER,
        matched_identifier=normalized_obtained_from,
        confidence=EvidenceConfidence.HIGH,
    )


def _build_sp_index(system_profiler_data: dict[str, Any] | None) -> dict[Path, dict[str, Any]]:
    """Index system_profiler entries by canonical path for enrichment lookups."""
    index: dict[Path, dict[str, Any]] = {}
    entries = (system_profiler_data or {}).get("SPApplicationsDataType", [])
    for entry in entries:
        raw_path = entry.get("path")
        if not raw_path:
            continue
        try:
            canonical = Path(raw_path).expanduser().resolve()
        except OSError as e:
            logging.debug("Could not resolve system_profiler path %r: %s", raw_path, e)
            continue
        index[canonical] = entry
    return index


def _build_record(
    raw_path: Path,
    canonical_path: Path,
    parent_bundle_path: Path | None,
    sp_index: dict[Path, dict[str, Any]],
) -> ApplicationRecord:
    """Build one record for a discovered bundle.

    Prefers system_profiler's fields when a matching entry was found (the
    long-standing primary data source), falling back to Contents/Info.plist
    and the bundle's own filename otherwise. Missing name/version/bundle_id
    are recorded as diagnostics rather than dropping the entry -- unlike
    legacy finder.get_applications(), which silently skips on KeyError.
    """
    plist_data = _read_info_plist(canonical_path)
    sp_entry = sp_index.get(canonical_path)

    diagnostics: list[str] = []

    name = ""
    if sp_entry and sp_entry.get("_name"):
        name = str(sp_entry["_name"])
    elif plist_data.get("CFBundleName"):
        name = str(plist_data["CFBundleName"])
    else:
        name = canonical_path.stem
    if not name:
        diagnostics.append("missing name")

    version = ""
    sp_version = str(sp_entry.get("version", "")).strip() if sp_entry else ""
    if sp_version:
        version = sp_version
    elif plist_data.get("CFBundleShortVersionString"):
        version = str(plist_data["CFBundleShortVersionString"]).strip()
    elif plist_data.get("CFBundleVersion"):
        version = str(plist_data["CFBundleVersion"]).strip()
    if not version:
        diagnostics.append("missing or empty version")

    bundle_id: str | None = None
    if sp_entry and sp_entry.get("bundle_id"):
        bundle_id = str(sp_entry["bundle_id"])
    elif plist_data.get("CFBundleIdentifier"):
        bundle_id = str(plist_data["CFBundleIdentifier"])
    if bundle_id is None:
        diagnostics.append("missing bundle identifier")

    obtained_from: str | None = None
    if sp_entry and sp_entry.get("obtained_from"):
        obtained_from = str(sp_entry["obtained_from"])

    return ApplicationRecord(
        name=name,
        version=version,
        path=raw_path,
        canonical_path=canonical_path,
        bundle_id=bundle_id,
        obtained_from=obtained_from,
        parent_bundle_path=parent_bundle_path,
        app_store=resolve_app_store_evidence(canonical_path, obtained_from),
        diagnostics=tuple(diagnostics),
    )


def discover_applications(
    *,
    roots: Sequence[Path] | None = None,
    extra_roots: Sequence[str | Path] | None = None,
    system_profiler_data: dict[str, Any] | None = None,
    include_nested: bool = False,
) -> list[ApplicationRecord]:
    """Discover application bundle records under the given (or default) roots.

    `roots`, when given, fully replaces default/configured root resolution --
    the escape hatch tests use to run hermetically (e.g. `roots=[tmp_path]`),
    never touching the real machine's /Applications or ~/Applications.
    Otherwise resolve_discovery_roots(extra_roots) is used.

    `system_profiler_data`, if given, only enriches records for bundles
    already found by the filesystem walk -- it is never used to discover new
    bundles beyond what the walk found itself. Discovery does not filter by
    App Store / Homebrew / any evidence status: every in-scope bundle is
    returned with its evidence attached, so `--all`-style consumers keep
    every record. Filtering into an attention list is a later-phase concern.

    Records are de-duplicated by identity_key (canonical_path, bundle_id) --
    not name/version -- in first-seen order, so two apps sharing a display
    name but differing in bundle_id or install location both survive as
    distinct records.
    """
    active_roots = list(roots) if roots is not None else resolve_discovery_roots(extra_roots)
    sp_index = _build_sp_index(system_profiler_data)

    records: list[ApplicationRecord] = []
    seen_identities: set[tuple[Path, str | None]] = set()

    for root in active_roots:
        try:
            resolved_root = root.expanduser().resolve()
        except OSError as e:
            logging.debug("Could not resolve discovery root %s: %s", root, e)
            continue

        for raw_path in _walk_root(resolved_root, include_nested=include_nested):
            canonical_path = raw_path.resolve()
            parent_bundle_path = _nearest_parent_bundle(canonical_path, resolved_root)
            record = _build_record(raw_path, canonical_path, parent_bundle_path, sp_index)

            if record.identity_key in seen_identities:
                logging.debug("Skipping duplicate application record: %s", record.identity_key)
                continue
            seen_identities.add(record.identity_key)
            records.append(record)

    return records
