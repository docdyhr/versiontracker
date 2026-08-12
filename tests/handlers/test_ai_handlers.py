"""Tests for versiontracker.handlers.ai_handlers."""

from __future__ import annotations

from unittest.mock import Mock, patch

from versiontracker.handlers.ai_handlers import handle_ask


def _make_options(**overrides: object) -> Mock:
    options = Mock()
    options.ask = None
    options.all = False
    options.status = None
    options.explain = False
    options.export_format = None
    options.output_file = None
    options.additional_dirs = None
    options.blocklist = None
    options.blacklist = None
    for key, value in overrides.items():
        setattr(options, key, value)
    return options


class TestHandleAsk:
    """Tests for handle_ask()."""

    def test_no_query_returns_1(self, capsys):
        result = handle_ask(_make_options(ask=None))
        assert result == 1
        assert "provide a query" in capsys.readouterr().out.lower()

    def test_empty_query_returns_1(self, capsys):
        result = handle_ask(_make_options(ask="   "))
        assert result == 1
        assert "provide a query" in capsys.readouterr().out.lower()

    def test_audit_query_routes_to_handle_audit(self):
        with patch("versiontracker.handlers.ai_handlers.handle_audit", return_value=0) as mocked:
            options = _make_options(ask="which apps need manual updates")
            result = handle_ask(options)
        assert result == 0
        mocked.assert_called_once_with(options)

    def test_audit_query_preserves_export_format_on_options(self):
        # The same options object (with all its other fields, e.g.
        # export_format set by --export) must be forwarded unchanged.
        with patch("versiontracker.handlers.ai_handlers.handle_audit", return_value=0) as mocked:
            options = _make_options(ask="which apps need manual updates", export_format="json")
            handle_ask(options)
        called_options = mocked.call_args.args[0]
        assert called_options.export_format == "json"

    def test_list_apps_query_routes_to_handle_list_apps(self):
        with patch("versiontracker.handlers.ai_handlers.handle_list_apps", return_value=0) as mocked:
            options = _make_options(ask="list my applications")
            result = handle_ask(options)
        assert result == 0
        mocked.assert_called_once_with(options)

    def test_recommendations_query_routes_to_handle_brew_recommendations(self):
        with patch("versiontracker.handlers.ai_handlers.handle_brew_recommendations", return_value=0) as mocked:
            options = _make_options(ask="recommend homebrew casks")
            result = handle_ask(options)
        assert result == 0
        mocked.assert_called_once_with(options)

    def test_check_outdated_query_routes_to_handle_outdated_check(self):
        with patch("versiontracker.handlers.ai_handlers.handle_outdated_check", return_value=0) as mocked:
            options = _make_options(ask="check for outdated applications")
            result = handle_ask(options)
        assert result == 0
        mocked.assert_called_once_with(options)

    def test_unsupported_intent_prints_message_not_crash(self, capsys):
        result = handle_ask(_make_options(ask="install app named firefox"))
        assert result == 1
        assert "not supported" in capsys.readouterr().out.lower()

    def test_gibberish_query_asks_for_clarification(self, capsys):
        result = handle_ask(_make_options(ask="xyzzy plugh nonsense"))
        assert result == 1
        assert "not sure" in capsys.readouterr().out.lower()

    def test_help_query_prints_examples_and_returns_0(self, capsys):
        result = handle_ask(_make_options(ask="help me"))
        assert result == 0
        assert "--audit" in capsys.readouterr().out

    def test_interpreter_error_result_prints_message_not_crash(self, capsys):
        # CommandInterpreter.interpret_command() itself catches exceptions
        # and returns {"command": "error", ...} -- handle_ask must degrade
        # gracefully rather than propagate or crash on that shape.
        fake_interpreter = Mock()
        fake_interpreter.interpret_command.return_value = {
            "command": "error",
            "error": "boom",
            "natural_language": "x",
            "confidence": 0.0,
        }
        with patch("versiontracker.handlers.ai_handlers.CommandInterpreter", return_value=fake_interpreter):
            result = handle_ask(_make_options(ask="x"))
        assert result == 1
        assert "couldn't understand" in capsys.readouterr().out.lower()

    def test_action_with_no_dispatch_entry_prints_message_not_crash(self, capsys):
        # Defensive branch: a future NLP intent added to CommandInterpreter's
        # command_mapping without a matching _DISPATCH/_NOT_SUPPORTED entry
        # must degrade gracefully, not raise or silently no-op.
        fake_interpreter = Mock()
        fake_interpreter.interpret_command.return_value = {
            "command": {"action": "mystery_action", "flags": [], "description": "mystery"},
            "confidence": 0.9,
            "natural_language": "x",
        }
        with patch("versiontracker.handlers.ai_handlers.CommandInterpreter", return_value=fake_interpreter):
            result = handle_ask(_make_options(ask="x"))
        assert result == 1
        assert "does not support" in capsys.readouterr().out.lower()

    def test_moderate_confidence_shows_best_guess_without_executing(self, capsys):
        # Above the clarify floor but below the act threshold: a real,
        # dispatchable action must be described, not silently executed.
        fake_interpreter = Mock()
        fake_interpreter.interpret_command.return_value = {
            "command": {"action": "list_apps", "flags": ["--apps"], "description": "Scan and list applications"},
            "confidence": 0.5,
            "natural_language": "x",
        }
        with (
            patch("versiontracker.handlers.ai_handlers.CommandInterpreter", return_value=fake_interpreter),
            patch("versiontracker.handlers.ai_handlers.handle_list_apps") as mocked,
        ):
            result = handle_ask(_make_options(ask="x"))
        assert result == 1
        mocked.assert_not_called()
        out = capsys.readouterr().out.lower()
        assert "i think you mean" in out
        assert "--apps" in out
