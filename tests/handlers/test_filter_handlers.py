"""Test module for the filter handlers.

This module contains tests for the filter handler functions
in the versiontracker.handlers.filter_handlers module.
"""

import json
import tempfile
from pathlib import Path
from unittest import mock


from versiontracker.handlers.filter_handlers import (
    handle_filter_management,
    handle_save_filter,
)
from versiontracker.ui import QueryFilterManager


class TestFilterHandlers:
    """Tests for the filter handlers."""

    def setup_method(self):
        """Set up test fixtures."""
        # Create a temporary directory for filter files
        self.temp_dir = tempfile.TemporaryDirectory()
        self.filter_manager = QueryFilterManager(self.temp_dir.name)

    def teardown_method(self):
        """Tear down test fixtures."""
        # Clean up the temporary directory
        self.temp_dir.cleanup()

    @mock.patch("versiontracker.handlers.filter_handlers.create_progress_bar")
    def test_handle_filter_management_list_filters_empty(self, mock_progress_bar):
        """Test listing filters when none exist."""
        # Setup
        mock_options = mock.MagicMock()
        mock_options.list_filters = True
        mock_color = mock_progress_bar.return_value.color
        mock_color.return_value.return_value = "Color message"

        # Execute
        result = handle_filter_management(mock_options, self.filter_manager)

        # Assert
        assert result == 0
        mock_color.assert_called_with("yellow")
        mock_color.return_value.assert_called_with("No saved filters found.")

    @mock.patch("versiontracker.handlers.filter_handlers.create_progress_bar")
    def test_handle_filter_management_list_filters_with_filters(self, mock_progress_bar):
        """Test listing filters when filters exist."""
        # Setup
        mock_options = mock.MagicMock()
        mock_options.list_filters = True

        # Create test filters
        filter_dir = Path(self.temp_dir.name) / "filters"
        filter_dir.mkdir(exist_ok=True)
        with open(filter_dir / "filter1.json", "w") as f:
            json.dump({"key": "value"}, f)
        with open(filter_dir / "filter2.json", "w") as f:
            json.dump({"key": "value"}, f)

        mock_color = mock_progress_bar.return_value.color
        mock_color.return_value.return_value = "Color message"

        # Execute
        result = handle_filter_management(mock_options, self.filter_manager)

        # Assert
        assert result == 0
        mock_color.assert_called_with("green")
        mock_color.return_value.assert_called_with("Available filters:")

    @mock.patch("versiontracker.handlers.filter_handlers.create_progress_bar")
    def test_handle_filter_management_delete_filter_success(self, mock_progress_bar):
        """Test deleting a filter that exists."""
        # Setup
        mock_options = mock.MagicMock()
        mock_options.list_filters = False
        mock_options.delete_filter = "test-filter"

        # Create test filter
        filter_dir = Path(self.temp_dir.name) / "filters"
        filter_dir.mkdir(exist_ok=True)
        with open(filter_dir / "test-filter.json", "w") as f:
            json.dump({"key": "value"}, f)

        mock_color = mock_progress_bar.return_value.color
        mock_color.return_value.return_value = "Color message"

        # Execute
        result = handle_filter_management(mock_options, self.filter_manager)

        # Assert
        assert result == 0
        mock_color.assert_called_with("green")
        mock_color.return_value.assert_called_with(
            "Filter 'test-filter' deleted successfully."
        )
        assert not (filter_dir / "test-filter.json").exists()

    @mock.patch("versiontracker.handlers.filter_handlers.create_progress_bar")
    def test_handle_filter_management_delete_filter_not_found(self, mock_progress_bar):
        """Test deleting a filter that doesn't exist."""
        # Setup
        mock_options = mock.MagicMock()
        mock_options.list_filters = False
        mock_options.delete_filter = "nonexistent-filter"
        mock_color = mock_progress_bar.return_value.color
        mock_color.return_value.return_value = "Color message"

        # Execute
        result = handle_filter_management(mock_options, self.filter_manager)

        # Assert
        assert result == 0
        mock_color.assert_called_with("red")
        mock_color.return_value.assert_called_with("Filter 'nonexistent-filter' not found.")

    @mock.patch("versiontracker.handlers.filter_handlers.create_progress_bar")
    @mock.patch("versiontracker.handlers.filter_handlers.get_config")
    def test_handle_filter_management_load_filter_success(self, mock_get_config, mock_progress_bar):
        """Test loading a filter that exists."""
        # Setup
        mock_options = mock.MagicMock()
        mock_options.list_filters = False
        mock_options.delete_filter = None
        mock_options.load_filter = "test-filter"

        # Setup mock config
        mock_config = mock.MagicMock()
        mock_config._config = {"test_key": "test_value"}
        mock_get_config.return_value = mock_config

        # Create test filter
        filter_dir = Path(self.temp_dir.name) / "filters"
        filter_dir.mkdir(exist_ok=True)
        filter_content = {
            "option1": "value1",
            "option2": "value2",
            "config": {"test_key": "new_value"}
        }
        with open(filter_dir / "test-filter.json", "w") as f:
            json.dump(filter_content, f)

        mock_color = mock_progress_bar.return_value.color
        mock_color.return_value.return_value = "Color message"

        # Execute
        result = handle_filter_management(mock_options, self.filter_manager)

        # Assert
        # The handler returns None when it loads a filter successfully
        assert result is None
        assert getattr(mock_options, "option1") == "value1"
        assert getattr(mock_options, "option2") == "value2"
        assert mock_config._config["test_key"] == "new_value"
        mock_color.assert_called_with("green")
        mock_color.return_value.assert_called_with("Loaded filter: test-filter")

    @mock.patch("versiontracker.handlers.filter_handlers.create_progress_bar")
    def test_handle_filter_management_load_filter_not_found(self, mock_progress_bar):
        """Test loading a filter that doesn't exist."""
        # Setup
        mock_options = mock.MagicMock()
        mock_options.list_filters = False
        mock_options.delete_filter = None
        mock_options.load_filter = "nonexistent-filter"
        mock_color = mock_progress_bar.return_value.color
        mock_color.return_value.return_value = "Color message"

        # Execute
        result = handle_filter_management(mock_options, self.filter_manager)

        # Assert
        assert result == 1
        mock_color.assert_called_with("red")
        mock_color.return_value.assert_called_with(
            "Filter 'nonexistent-filter' not found."
        )

    @mock.patch("versiontracker.handlers.filter_handlers.create_progress_bar")
    @mock.patch("versiontracker.handlers.filter_handlers.get_config")
    def test_handle_save_filter_success(self, mock_get_config, mock_progress_bar):
        """Test saving a filter successfully."""
        # Setup
        # Use a regular object instead of MagicMock to avoid serialization issues
        class Options:
            pass
        
        mock_options = Options()
        mock_options.save_filter = "test-save-filter"
        mock_options.option1 = "value1"
        mock_options.option2 = "value2"
        # Define dir method explicitly
        mock_options.__dir__ = lambda: ["save_filter", "option1", "option2"]

        # Setup mock config
        mock_config = mock.MagicMock()
        mock_config._config = {
            "ui": {"color": True},
            "rate_limit": 5,
            "max_workers": 8
        }
        mock_get_config.return_value = mock_config

        mock_color = mock_progress_bar.return_value.color
        mock_color.return_value.return_value = "Color message"

        # Use a patched filter manager to ensure save works
        patched_filter_manager = mock.MagicMock()
        patched_filter_manager.save_filter.return_value = True
        
        # Execute
        result = handle_save_filter(mock_options, patched_filter_manager)

        # Assert
        assert result == 0
        # Verify the filter manager was called with the correct parameters
        patched_filter_manager.save_filter.assert_called_once()
        args, kwargs = patched_filter_manager.save_filter.call_args
        assert args[0] == "test-save-filter"  # First argument should be the filter name
        
        # Verify the filter data content
        filter_data = args[1]  # Second argument should be the filter data
        assert filter_data["option1"] == "value1"
        assert filter_data["option2"] == "value2"
        assert "config" in filter_data
        assert "ui" in filter_data["config"]
        assert "rate_limit" in filter_data["config"]
        assert "max_workers" in filter_data["config"]
        
        mock_color.assert_called_with("green")
        mock_color.return_value.assert_called_with(
            "Filter 'test-save-filter' saved successfully."
        )

    @mock.patch("versiontracker.handlers.filter_handlers.create_progress_bar")
    @mock.patch("versiontracker.handlers.filter_handlers.get_config")
    @mock.patch("versiontracker.handlers.filter_handlers.logging")
    def test_handle_save_filter_failure(self, mock_logging, mock_get_config, mock_progress_bar):
        """Test handling a failure when saving a filter."""
        # Setup
        mock_options = mock.MagicMock()
        mock_options.save_filter = "test-save-filter"

        # Setup mock filter manager to fail
        mock_filter_manager = mock.MagicMock()
        mock_filter_manager.save_filter.return_value = False

        mock_color = mock_progress_bar.return_value.color
        mock_color.return_value.return_value = "Color message"

        # Execute
        result = handle_save_filter(mock_options, mock_filter_manager)

        # Assert
        assert result == 1
        mock_color.assert_called_with("red")
        mock_color.return_value.assert_called_with(
            "Failed to save filter 'test-save-filter'."
        )

    @mock.patch("versiontracker.handlers.filter_handlers.create_progress_bar")
    @mock.patch("versiontracker.handlers.filter_handlers.get_config")
    @mock.patch("versiontracker.handlers.filter_handlers.logging")
    def test_handle_save_filter_exception(self, mock_logging, mock_get_config, mock_progress_bar):
        """Test handling an exception when saving a filter."""
        # Setup
        mock_options = mock.MagicMock()
        mock_options.save_filter = "test-save-filter"

        # Setup mock filter manager to raise exception
        mock_filter_manager = mock.MagicMock()
        mock_filter_manager.save_filter.side_effect = Exception("Test error")

        mock_color = mock_progress_bar.return_value.color
        mock_color.return_value.return_value = "Color message"

        # Execute
        result = handle_save_filter(mock_options, mock_filter_manager)

        # Assert
        assert result == 1
        mock_logging.error.assert_called_once()
        mock_color.assert_called_with("red")