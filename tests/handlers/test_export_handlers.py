"""Tests for versiontracker.handlers.export_handlers — coverage improvement.

Targets error paths in handle_export().
"""

from unittest.mock import MagicMock, patch

from versiontracker.exceptions import ExportError
from versiontracker.handlers.export_handlers import handle_export


def _mock_progress_bar():
    pb = MagicMock()
    pb.color.return_value = lambda x: x
    return pb


class TestHandleExportErrors:
    """Tests for handle_export() error paths."""

    @patch("versiontracker.handlers.export_handlers.create_progress_bar", return_value=_mock_progress_bar())
    @patch("versiontracker.handlers.export_handlers.export_data", side_effect=ValueError("bad format"))
    def test_value_error(self, _export, _pb):
        assert handle_export({"data": 1}, "invalid") == 1

    @patch("versiontracker.handlers.export_handlers.create_progress_bar", return_value=_mock_progress_bar())
    @patch("versiontracker.handlers.export_handlers.export_data", side_effect=PermissionError("denied"))
    def test_permission_error(self, _export, _pb):
        assert handle_export({"data": 1}, "json", "/readonly/file.json") == 1

    @patch("versiontracker.handlers.export_handlers.create_progress_bar", return_value=_mock_progress_bar())
    @patch("versiontracker.handlers.export_handlers.export_data", side_effect=ExportError("export failed"))
    def test_export_error(self, _export, _pb):
        assert handle_export({"data": 1}, "json") == 1

    @patch("versiontracker.handlers.export_handlers.create_progress_bar", return_value=_mock_progress_bar())
    @patch("versiontracker.handlers.export_handlers.get_config")
    @patch("versiontracker.handlers.export_handlers.export_data", side_effect=RuntimeError("unexpected"))
    def test_generic_exception(self, _export, mock_config, _pb):
        mock_config.return_value.debug = False
        assert handle_export({"data": 1}, "json") == 1

    @patch("versiontracker.handlers.export_handlers.create_progress_bar", return_value=_mock_progress_bar())
    @patch("versiontracker.handlers.export_handlers.traceback")
    @patch("versiontracker.handlers.export_handlers.get_config")
    @patch("versiontracker.handlers.export_handlers.export_data", side_effect=RuntimeError("unexpected"))
    def test_debug_traceback(self, _export, mock_config, mock_tb, _pb):
        mock_config.return_value.debug = True
        handle_export({"data": 1}, "json")
        mock_tb.print_exc.assert_called_once()
