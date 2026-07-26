"""Audit command handler for VersionTracker.

Thin wrapper around versiontracker.audit.service/rendering: parses CLI
options, runs the audit, and either prints terminal sections or, when
exporting, prints *only* the rendered export string. Unlike every other
existing handler (which prints a table unconditionally and then, separately,
export output if requested), this one never prints both -- exported stdout
must contain nothing but the requested data.
"""

from __future__ import annotations

from typing import Any

from versiontracker.audit import (
    AuditBucket,
    AuditResult,
    filter_result,
    render_csv,
    render_json,
    render_terminal,
    render_yaml,
    run_audit,
)
from versiontracker.config import get_config
from versiontracker.ui import create_progress_bar

_RENDERERS = {"json": render_json, "yaml": render_yaml, "csv": render_csv}


def _parse_additional_dirs(options: Any) -> list[str] | None:
    """Parse --additional-dirs as colon-separated, per its documented help text.

    Matches discovery.py's extra_roots convention -- NOT the comma-split
    app_handlers.py's own (dead, unused) --additional-dirs handling uses.
    """
    raw = getattr(options, "additional_dirs", None)
    if not raw:
        return None
    return [entry for entry in raw.split(":") if entry]


def _merge_blocklist_entries(options: Any) -> list[str]:
    """Merge configured blocklist entries with any CLI-supplied ones.

    Deliberately merges rather than overrides, per the spec's "prefer
    merge semantics for an audit filter." A divergence from
    app_handlers.py::_apply_blocklist_filtering()'s override-via-temp-config
    behavior, which stays untouched (out of scope for this feature).
    """
    entries = list(get_config().get_blocklist())
    for option_name in ("blocklist", "blacklist"):
        raw = getattr(options, option_name, None)
        if not raw:
            continue
        for entry in raw.split(","):
            entry = entry.strip()
            if entry and entry not in entries:
                entries.append(entry)
    return entries


def _handle_export(result: AuditResult, export_format: str, output_file: str | None) -> int:
    renderer = _RENDERERS.get(export_format.lower())
    if renderer is None:
        print(f"Unsupported export format: {export_format}")
        return 1

    content = renderer(result)

    if output_file:
        try:
            with open(output_file, "w") as f:
                f.write(content)
        except OSError as e:
            print(f"Error: Failed to write to {output_file}: {e}")
            return 1
        print(
            create_progress_bar().color("green")(f"Exported {len(result.applications)} applications to {output_file}")
        )
        return 0

    # Nothing else may print to stdout in this branch -- this is the
    # concrete mechanism that keeps exported output machine-parseable.
    print(content)
    return 0


def handle_audit(options: Any) -> int:
    """Handle the --audit action.

    Returns:
        int: Exit code (0 for success, non-zero for failure)
    """
    extra_roots = _parse_additional_dirs(options)
    blocklist_entries = _merge_blocklist_entries(options)

    result = run_audit(extra_roots=extra_roots, blocklist_entries=blocklist_entries)

    status_option = getattr(options, "status", None)
    status = AuditBucket(status_option) if status_option else None
    show_all = bool(getattr(options, "all", False))
    result = filter_result(result, show_all=show_all, status=status)

    export_format = getattr(options, "export_format", None)
    if export_format:
        return _handle_export(result, export_format, getattr(options, "output_file", None))

    explain = bool(getattr(options, "explain", False))
    print(render_terminal(result, explain=explain))
    return 0
