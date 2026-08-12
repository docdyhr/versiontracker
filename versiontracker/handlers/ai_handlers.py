"""Natural-language `--ask` command handler for VersionTracker.

Thin router only: interprets a query via versiontracker.ai.CommandInterpreter
and dispatches to the SAME handler functions the equivalent literal CLI flag
would use, reusing the already-parsed `options` Namespace unchanged. This
module must never reimplement audit/classification/homebrew logic -- only
intent recognition and routing to real handlers.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

from versiontracker.ai import CommandInterpreter
from versiontracker.handlers.app_handlers import handle_list_apps
from versiontracker.handlers.audit_handlers import handle_audit
from versiontracker.handlers.brew_handlers import handle_brew_recommendations
from versiontracker.handlers.outdated_handlers import handle_outdated_check

logger = logging.getLogger(__name__)

# Below this, the intent is too uncertain to act on at all.
_CLARIFY_THRESHOLD = 0.3

# Below this (but at/above _CLARIFY_THRESHOLD), show the best guess instead
# of executing it automatically.
_ACT_THRESHOLD = 0.7

# command_mapping actions in versiontracker.ai that do NOT correspond to any
# real standalone CLI flag -- must degrade to an explicit message, never a
# guess or a crash.
_NOT_SUPPORTED: dict[str, str] = {
    "install": 'Installing applications via --ask is not supported yet. Use "brew install <cask>" directly.',
    "uninstall": "Removing applications via --ask is not supported yet.",
    "blacklist": (
        "Blocklisting applications via --ask is not supported yet. Use --blocklist or --blocklist-auto-updates."
    ),
    "export": "Standalone export via --ask is not supported yet. Combine --ask with --export {json,yaml,csv} instead.",
    "analytics": "Analytics via --ask is not supported yet.",
}

_EXAMPLE_QUERIES = [
    '--ask "which apps need manual updates"   -> --audit',
    '--ask "list my applications"             -> --apps',
    '--ask "recommend homebrew casks"         -> --recom',
    '--ask "check for outdated applications"  -> --check-outdated',
]


def _print_ask_help() -> None:
    print("versiontracker --ask understands queries like:")
    for example in _EXAMPLE_QUERIES:
        print(f"  {example}")
    print("Run `versiontracker --help` for the full flag reference.")


def _print_clarification(query: str) -> None:
    print(f'I\'m not sure what you mean by "{query}".')
    print("Try things like:")
    for example in _EXAMPLE_QUERIES:
        print(f"  {example.split('->')[0].strip()}")


def handle_ask(options: Any) -> int:
    """Handle the --ask action.

    Returns:
        int: Exit code (0 for success, non-zero for failure/needs-clarification)
    """
    query = getattr(options, "ask", None)
    if not query or not query.strip():
        print('Please provide a query, e.g. --ask "which apps need manual updates"')
        return 1

    result = CommandInterpreter().interpret_command(query)

    if result.get("command") == "error":
        logger.debug("ask: interpret_command failed: %s", result.get("error"))
        print("Sorry, I couldn't understand that query. Try rephrasing it, or use a specific flag (see --help).")
        return 1

    command = result.get("command", {})
    action = command.get("action", "unknown")
    confidence = float(result.get("confidence", 0.0))

    if action == "unknown" or confidence < _CLARIFY_THRESHOLD:
        _print_clarification(query)
        return 1

    if action == "help":
        _print_ask_help()
        return 0

    if action in _NOT_SUPPORTED:
        print(_NOT_SUPPORTED[action])
        print("Run `versiontracker --help` for the full list of supported flags.")
        return 1

    # Built here (not as a module-level constant) so it resolves the
    # handle_* names from this module's current namespace at call time --
    # tests patch e.g. versiontracker.handlers.ai_handlers.handle_audit,
    # which a module-level dict literal built once at import time would not
    # observe.
    dispatch: dict[str, Callable[[Any], int]] = {
        "list_apps": handle_list_apps,
        "get_recommendations": handle_brew_recommendations,
        "check_outdated": handle_outdated_check,
        "audit": handle_audit,
    }
    handler = dispatch.get(action)
    if handler is None:
        # Defensive: a future NLP intent added without a matching dispatch
        # entry must degrade gracefully, not crash.
        print(f'Sorry, "{query}" was understood as "{action}", which --ask does not support yet.')
        return 1

    if confidence < _ACT_THRESHOLD:
        flags = command.get("flags") or [""]
        print(f"I think you mean: {command.get('description', action)} (confidence {confidence:.0%}).")
        print(f"If that's right, re-run with `versiontracker {flags[0]}` directly.")
        return 1

    return handler(options)
