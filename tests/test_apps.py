"""Tests for the apps module."""

import pytest
from unittest.mock import MagicMock, patch

from versiontracker.apps import (
    SimpleRateLimiter,
    _process_brew_batch,
    _process_brew_search,
    check_brew_install_candidates,
    clear_homebrew_casks_cache,
    filter_out_brews,
    get_applications,
    get_applications_from_system_profiler,
    get_cask_version,
    get_homebrew_casks,
    is_homebrew_available,
)
from versiontracker.exceptions import (
    BrewTimeoutError,
    DataParsingError,
    HomebrewError,
    NetworkError,
)


# Test functions for the apps module


def test_get_applications():
        """Test getting applications."""
        # Mock system_profiler data
        mock_data = {
            "SPApplicationsDataType": [
                {
                    "_name": "TestApp1",
                    "path": "/Applications/TestApp1.app",
                    "version": "1.0.0",
                    "obtained_from": "Developer ID",
                },
                {
                    "_name": "TestApp2",
                    "path": "/Applications/TestApp2.app",
                    "version": "2.0.0",
                    "obtained_from": "mac_app_store",  # Should be filtered out
                },
                {
                    "_name": "TestApp3",
                    "path": "/Applications/TestApp3.app",
                    "version": "3.0.0",
                    "obtained_from": "apple",  # Should be filtered out
                },
                {
                    "_name": "TestApp4",
                    "path": "/Applications/TestApp4.app",
                    "version": "4.0.0",
                    "obtained_from": "Unknown",
                },
                {
                    "_name": "TestApp5",
                    "path": "/System/Applications/TestApp5.app",  # Should be filtered out by path
                    "version": "5.0.0",
                    "obtained_from": "Unknown",
                },
            ]
        }

        # Call the function with our mock data
        result = get_applications(mock_data)

        # TestApp1 should be in the results, normalized to TestApp
        assert ("TestApp", "1.0.0") in result

@patch("versiontracker.apps.partial_ratio")
def test_filter_out_brews(mock_partial_ratio):
        """Test filtering out applications already installed via Homebrew."""

        # Set up the mock partial_ratio to match our expectations
        def side_effect(app, brew):
            # Return high similarity for Firefox/firefox, Chrome/google-chrome,
            # VSCode/visual-studio-code
            if app == "firefox" and brew == "firefox":
                return 100
            elif app == "chrome" and brew == "google-chrome":
                return 80
            elif app == "vscode" and brew == "visual-studio-code":
                return 85
            return 30  # Return low similarity for everything else

        mock_partial_ratio.side_effect = side_effect

        # Mock applications and brews
        applications = [
            ("Firefox", "100.0.0"),
            ("Chrome", "101.0.0"),
            ("Slack", "4.23.0"),
            ("VSCode", "1.67.0"),
        ]
        brews = ["firefox", "google-chrome", "visual-studio-code"]

        # Call the function
        result = filter_out_brews(applications, brews)

        # Check the result
        assert len(result) == 1  # Only Slack should remain
        assert ("Slack", "4.23.0") in result

@patch("versiontracker.apps.run_command")
def test_process_brew_search(mock_run_command):
    """Test processing a brew search."""
    # Mock rate limiter
    mock_rate_limiter = MagicMock()

    # Set up the mock run_command to return brew search results
    mock_run_command.return_value = ("firefox\nfirefox-developer-edition", 0)

    # Test with a matching app
    result = _process_brew_search(("Firefox", "100.0.0"), mock_rate_limiter)
    assert result == "Firefox"

    # Test with a non-matching app
    mock_run_command.return_value = ("some-other-app", 0)
    result = _process_brew_search(("Firefox", "100.0.0"), mock_rate_limiter)
    assert result is None

    # Test exception handling
    mock_run_command.side_effect = Exception("Test error")
    result = _process_brew_search(("Firefox", "100.0.0"), mock_rate_limiter)
    assert result is None

@patch("platform.system")
@patch("platform.machine")
@patch("versiontracker.apps.run_command")
def test_is_homebrew_available_true(mock_run_command, mock_machine, mock_system):
    """Test is_homebrew_available when Homebrew is installed."""
    # Mock platform.system() to return "Darwin" (macOS)
    mock_system.return_value = "Darwin"
    # Mock platform.machine() to return x86_64 (Intel)
    mock_machine.return_value = "x86_64"
    # Mock run_command to return successful output for brew --version
    mock_run_command.return_value = ("Homebrew 3.4.0", 0)

    # Test that is_homebrew_available returns True
    assert is_homebrew_available()

@patch("platform.system")
@patch("versiontracker.apps.run_command")
def test_is_homebrew_available_false(mock_run_command, mock_system):
    """Test is_homebrew_available when Homebrew is not installed."""
    # Mock platform.system() to return "Darwin" (macOS)
    mock_system.return_value = "Darwin"
    # Mock run_command to raise an exception (brew not found)
    mock_run_command.side_effect = Exception("Command not found")

    # Test that is_homebrew_available returns False when brew command fails
    assert not is_homebrew_available()

@patch("platform.system")
def test_is_homebrew_available_non_macos(mock_system):
    """Test is_homebrew_available on non-macOS platforms."""
    # Mock platform.system() to return "Linux"
    mock_system.return_value = "Linux"

    # Test that is_homebrew_available returns False on non-macOS platforms
    assert not is_homebrew_available()

@patch("platform.system")
@patch("platform.machine")
@patch("versiontracker.apps.run_command")
def test_is_homebrew_available_arm(
    mock_run_command, mock_machine, mock_system
):
    """Test is_homebrew_available on ARM macOS (Apple Silicon)."""
    # Mock platform.system() to return "Darwin" (macOS)
    mock_system.return_value = "Darwin"
    # Mock platform.machine() to return arm64 (Apple Silicon)
    mock_machine.return_value = "arm64"

    # Define a side effect to simulate success only with the ARM path
    def command_side_effect(cmd, timeout=None):
        if "/opt/homebrew/bin/brew" in cmd:
            return ("Homebrew 3.4.0", 0)
        else:
            raise FileNotFoundError("Command not found")

    mock_run_command.side_effect = command_side_effect

    # Test that is_homebrew_available returns True
    assert is_homebrew_available()

def test_get_homebrew_casks_success():
    """Test successful retrieval of Homebrew casks."""
    # Use the dedicated cache clearing function
    clear_homebrew_casks_cache()

    # Set up mocks
    with patch("versiontracker.apps.get_config") as mock_get_config:
        mock_config = MagicMock()
        mock_config.brew_path = "/usr/local/bin/brew"
        mock_get_config.return_value = mock_config

        with patch("versiontracker.apps.run_command") as mock_run_command:
            # Mock run_command to return a list of casks
            mock_run_command.return_value = ("cask1\ncask2\ncask3", 0)

            # Call the function
            casks = get_homebrew_casks()

            # Verify the expected command was run
            mock_run_command.assert_called_once_with(
                "/usr/local/bin/brew list --cask", timeout=30
            )

            # Verify the result
            assert casks == ["cask1", "cask2", "cask3"]

    # Check the result
    assert casks == ["cask1", "cask2", "cask3"]

def test_get_homebrew_casks_empty():
    """Test when no casks are installed."""
    # Use the dedicated cache clearing function
    clear_homebrew_casks_cache()

    # Set up mocks
    with patch("versiontracker.apps.get_config") as mock_get_config:
        mock_config = MagicMock()
        mock_config.brew_path = "/usr/local/bin/brew"
        mock_get_config.return_value = mock_config

        with patch("versiontracker.apps.run_command") as mock_run_command:
            # Mock run_command to return empty output
            mock_run_command.return_value = ("", 0)

            # Call the function
            casks = get_homebrew_casks()

            # Check the result
            assert casks == []

def test_get_homebrew_casks_error():
    """Test error handling for Homebrew command failures."""
    # Use the dedicated cache clearing function
    clear_homebrew_casks_cache()

    # Set up mocks
    with patch("versiontracker.apps.get_config") as mock_get_config:
        mock_config = MagicMock()
        mock_config.brew_path = "/usr/local/bin/brew"
        mock_get_config.return_value = mock_config

        with patch("versiontracker.apps.run_command") as mock_run_command:
            # Mock run_command to return an error
            mock_run_command.return_value = ("Error: command failed", 1)

            # Test that HomebrewError is raised
            with pytest.raises(HomebrewError):
                get_homebrew_casks()

def test_get_homebrew_casks_network_error():
    """Test network error handling."""
    # Use the dedicated cache clearing function
    clear_homebrew_casks_cache()

    # Set up mocks
    with patch("versiontracker.apps.get_config") as mock_get_config:
        mock_config = MagicMock()
        mock_config.brew_path = "/usr/local/bin/brew"
        mock_get_config.return_value = mock_config

        with patch("versiontracker.apps.run_command") as mock_run_command:
            # Mock run_command to raise NetworkError
            mock_run_command.side_effect = NetworkError("Network unavailable")

            # Test that NetworkError is re-raised
            with pytest.raises(NetworkError):
                get_homebrew_casks()

def test_get_homebrew_casks_timeout():
    """Test timeout error handling."""
    # Use the dedicated cache clearing function
    clear_homebrew_casks_cache()

    # Set up mocks
    with patch("versiontracker.apps.get_config") as mock_get_config:
        mock_config = MagicMock()
        mock_config.brew_path = "/usr/local/bin/brew"
        mock_get_config.return_value = mock_config

        with patch("versiontracker.apps.run_command") as mock_run_command:
            # Mock run_command to raise BrewTimeoutError
            mock_run_command.side_effect = BrewTimeoutError("Operation timed out")

            # Test that BrewTimeoutError is re-raised
            with pytest.raises(BrewTimeoutError):
                get_homebrew_casks()

def test_get_homebrew_casks_cache():
    """Test caching behavior of get_homebrew_casks."""
    # Clear any existing caches first
    clear_homebrew_casks_cache()

    # Set up initial data with mock
    with patch("versiontracker.apps.run_command") as mock_run:
        # Mock the command to return some data
        mock_run.return_value = ("test1\ntest2", 0)

        # First call should execute the function and store in cache
        first_result = get_homebrew_casks()

        # Verify the function actually ran once
        mock_run.assert_called_once()

        # Change the mock return value to verify cache is used
        mock_run.return_value = ("different1\ndifferent2", 0)
        mock_run.reset_mock()

        # Second call should use cache and not execute the function again
        second_result = get_homebrew_casks()

        # Verify the function wasn't called again
        mock_run.assert_not_called()

        # Results should be the same because cache was used
        assert first_result == second_result

        # Now clear the cache and call again
        clear_homebrew_casks_cache()

        # This call should execute the function with the new mock data
        third_result = get_homebrew_casks()

        # Verify the function ran again after cache clearing
        mock_run.assert_called_once()

        # Results should be different now that cache was cleared
        assert first_result != third_result

@patch("versiontracker.apps.get_config")
def test_get_applications_from_system_profiler_valid(mock_get_config):
    """Test extracting application data from valid system_profiler output."""
    # Mock configuration
    mock_config = MagicMock()
    mock_config.skip_system_apps = True
    mock_config.skip_system_paths = True
    mock_get_config.return_value = mock_config

    # Create test data
    valid_data = {
        "SPApplicationsDataType": [
            {
                "_name": "App1",
                "version": "1.0",
                "obtained_from": "Developer ID",
                "path": "/Applications/App1.app",
            },
            {
                "_name": "App2",
                "version": "2.0",
                "obtained_from": "Unknown",
                "path": "/Applications/App2.app",
            },
            {
                "_name": "SystemApp",
                "version": "3.0",
                "obtained_from": "apple",
                "path": "/Applications/SystemApp.app",
            },
            {
                "_name": "SysPathApp",
                "version": "4.0",
                "obtained_from": "Unknown",
                "path": "/System/Applications/SysApp.app",
            },
        ]
    }

    # Call the function
    apps = get_applications_from_system_profiler(valid_data)

    # Verify results
    assert len(apps) == 2  # SystemApp and SysPathApp should be filtered out
    assert ("App1", "1.0") in apps
    assert ("App2", "2.0") in apps
    assert ("SystemApp", "3.0") not in apps
    assert ("SysPathApp", "4.0") not in apps

@patch("versiontracker.apps.get_config")
def test_get_applications_from_system_profiler_empty(mock_get_config):
    """Test handling empty system_profiler data."""
    # Mock configuration
    mock_config = MagicMock()
    mock_get_config.return_value = mock_config

    empty_data: dict = {"SPApplicationsDataType": []}
    apps = get_applications_from_system_profiler(empty_data)
    assert apps == []

@patch("versiontracker.apps.get_config")
def test_get_applications_from_system_profiler_invalid(mock_get_config):
    """Test handling invalid data structure."""
    # Mock configuration
    mock_config = MagicMock()
    mock_get_config.return_value = mock_config

    invalid_data: dict = {"WrongKey": []}
    with pytest.raises(DataParsingError):
        get_applications_from_system_profiler(invalid_data)

@patch("versiontracker.apps.get_config")
def test_get_applications_from_system_profiler_test_app_normalization(
    mock_get_config
):
    """Test normalization of test app names."""
    # Mock configuration
    mock_config = MagicMock()
    mock_get_config.return_value = mock_config

    # Create test data with TestApp names that should be normalized
    test_data: dict = {
        "SPApplicationsDataType": [
            {
                "_name": "TestApp1",
                "version": "1.0",
                "path": "/Applications/TestApp1.app",
            },
            {
                "_name": "TestApp2",
                "version": "2.0",
                "path": "/Applications/TestApp2.app",
            },
            {
                "_name": "RegularApp",
                "version": "3.0",
                "path": "/Applications/RegularApp.app",
            },
        ]
    }

    apps = get_applications_from_system_profiler(test_data)

    # Both TestApp1 and TestApp2 should be normalized to just "TestApp"
    assert ("TestApp", "1.0") in apps
    assert ("TestApp", "2.0") in apps
    assert ("RegularApp", "3.0") in apps

@patch("versiontracker.apps.BREW_PATH", "/usr/local/bin/brew")
@patch("versiontracker.apps.run_command")
def test_get_cask_version_found(mock_run_command):
    """Test getting version when it exists."""
    # Mock brew info output with version information
    brew_output = """
    ==> firefox: 95.0.1
    ==> https://www.mozilla.org/firefox/
    version: 95.0.1
    """
    mock_run_command.return_value = (brew_output, 0)

    # Call the function
    version = get_cask_version("firefox")

    # Verify the result
    assert version == "95.0.1"

    # Verify the command that was run
    mock_run_command.assert_called_once_with(
        "/usr/local/bin/brew info --cask firefox", timeout=30
    )

@patch("versiontracker.apps.BREW_PATH", "/usr/local/bin/brew")
@patch("versiontracker.apps.run_command")
def test_get_cask_version_not_found(mock_run_command):
    """Test when version is not found in output."""
    # Mock brew info output without version information
    mock_run_command.return_value = ("Some output without version info", 0)

    # Call the function
    version = get_cask_version("unknown-app")

    # Verify the result
    assert version is None

@patch("versiontracker.apps.BREW_PATH", "/usr/local/bin/brew")
@patch("versiontracker.apps.run_command")
def test_get_cask_version_latest(mock_run_command):
    """Test handling 'latest' version tag."""
    # Mock brew info output with 'latest' as the version
    mock_run_command.return_value = ("version: latest", 0)

    # Call the function
    version = get_cask_version("app-with-latest-version")

    # Verify the result is None for 'latest' versions
    assert version is None

@patch("versiontracker.apps.BREW_PATH", "/usr/local/bin/brew")
@patch("versiontracker.apps.run_command")
def test_get_cask_version_error(mock_run_command):
    """Test error handling when brew command fails."""
    # Mock brew info command failure
    mock_run_command.return_value = ("Error: cask not found", 1)

    # Call the function
    version = get_cask_version("non-existent-cask")

    # Verify the result
    assert version is None

@patch("versiontracker.apps.BREW_PATH", "/usr/local/bin/brew")
@patch("versiontracker.apps.run_command")
def test_get_cask_version_network_error(mock_run_command):
    """Test network error handling."""
    # Mock run_command to raise NetworkError
    mock_run_command.side_effect = NetworkError("Network unavailable")

    # Test that NetworkError is re-raised
    with pytest.raises(NetworkError):
        get_cask_version("firefox")

@patch("versiontracker.apps.BREW_PATH", "/usr/local/bin/brew")
@patch("versiontracker.apps.run_command")
def test_get_cask_version_timeout(mock_run_command):
    """Test timeout error handling."""
    # Mock run_command to raise BrewTimeoutError
    mock_run_command.side_effect = BrewTimeoutError("Operation timed out")

    # Test that BrewTimeoutError is re-raised
    with pytest.raises(BrewTimeoutError):
        get_cask_version("firefox")

@patch("versiontracker.apps.BREW_PATH", "/usr/local/bin/brew")
@patch("versiontracker.apps.run_command")
def test_get_cask_version_general_exception(mock_run_command):
    """Test general exception handling."""
    # Mock run_command to raise a general exception
    mock_run_command.side_effect = ValueError("Some unexpected error")

    # Test that a HomebrewError is raised with the original error wrapped
    with pytest.raises(HomebrewError):
        get_cask_version("firefox")

@patch("versiontracker.apps.is_homebrew_available")
def test_check_brew_install_candidates_no_homebrew(mock_is_homebrew):
    """Test check_brew_install_candidates when Homebrew is not available."""
    # Mock is_homebrew_available to return False
    mock_is_homebrew.return_value = False

    # Create test data
    data = [("Firefox", "100.0"), ("Chrome", "99.0")]

    # Call the function
    result = check_brew_install_candidates(data)

    # Verify that all apps are marked as not installable
    expected = [("Firefox", "100.0", False), ("Chrome", "99.0", False)]
    assert result == expected

@patch("versiontracker.apps.is_homebrew_available")
@patch("versiontracker.apps._process_brew_batch")
@patch("versiontracker.apps.smart_progress")
def test_check_brew_install_candidates_success(
    mock_smart_progress, mock_process_brew_batch, mock_is_homebrew
):
    """Test check_brew_install_candidates with successful batch processing."""
    # Mock is_homebrew_available to return True
    mock_is_homebrew.return_value = True

    # Mock _process_brew_batch to return expected results
    expected_results = [("Firefox", "100.0", True), ("Chrome", "99.0", False)]
    mock_process_brew_batch.return_value = expected_results

    # Mock smart_progress to just pass through the iterable
    mock_smart_progress.side_effect = lambda x, **kwargs: x

    # Create test data
    data = [("Firefox", "100.0"), ("Chrome", "99.0")]

    # Call the function
    result = check_brew_install_candidates(data)

    # Verify the result
    assert result == expected_results

    # Verify _process_brew_batch was called with the right parameters
    mock_process_brew_batch.assert_called_once_with(data, 1, True)

@patch("versiontracker.apps.is_homebrew_available")
def test_process_brew_batch_no_homebrew(mock_is_homebrew):
    """Test _process_brew_batch when Homebrew is not available."""
    # Mock is_homebrew_available to return False
    mock_is_homebrew.return_value = False

    # Create test data
    batch = [("Firefox", "100.0"), ("Chrome", "99.0")]

    # Call the function
    result = _process_brew_batch(batch, 1, True)

    # Verify all apps are marked as not installable
    expected = [("Firefox", "100.0", False), ("Chrome", "99.0", False)]
    assert result == expected

def test_process_brew_batch_empty():
    """Test _process_brew_batch with an empty batch."""
    # Call the function with an empty batch
    result = _process_brew_batch([], 1, True)

    # Verify an empty result is returned
    assert result == []

def test_simple_rate_limiter():
    """Test SimpleRateLimiter functionality."""
    # Create a rate limiter with a 0.1 second delay (minimum)
    rate_limiter = SimpleRateLimiter(0.1)

    # Verify the delay was set correctly
    assert rate_limiter._delay == 0.1

    # Test with delay below minimum
    min_limiter = SimpleRateLimiter(0.05)
    assert min_limiter._delay == 0.1  # Should be clamped to 0.1

    # Test with higher delay
    high_limiter = SimpleRateLimiter(0.5)
    assert high_limiter._delay == 0.5

@patch("versiontracker.apps.is_homebrew_available")
@patch("versiontracker.apps.is_brew_cask_installable")
@patch("versiontracker.apps.ThreadPoolExecutor")
@patch("versiontracker.apps.as_completed")
@patch("versiontracker.apps.get_config")
def test_process_brew_batch_with_simple_rate_limiter(
    mock_get_config,
    mock_as_completed,
    mock_executor_class,
    mock_is_installable,
    mock_is_homebrew,
):
    """Test _process_brew_batch with simple rate limiter."""
    # Mock is_homebrew_available to return True
    mock_is_homebrew.return_value = True

    # Mock config with standard rate limiting
    mock_config = MagicMock()
    mock_config.ui = {"adaptive_rate_limiting": False}
    mock_get_config.return_value = mock_config

    # Mock executor and future
    mock_executor = MagicMock()
    mock_executor_class.return_value.__enter__.return_value = mock_executor

    mock_future = MagicMock()
    mock_future.result.return_value = True
    mock_future.exception.return_value = None  # Explicitly set exception to None
    mock_executor.submit.return_value = mock_future

    # Mock as_completed to return the future
    mock_as_completed.return_value = [mock_future]

    # Mock is_brew_cask_installable to return True
    mock_is_installable.return_value = True

    # Call the function with test data
    result = _process_brew_batch([("Firefox", "100.0")], 1, True)

    # Verify the result
    assert result == [("Firefox", "100.0", True)]

    # Verify the mocks were called correctly
    mock_executor.submit.assert_called_once()
    mock_as_completed.assert_called_once()

@patch("versiontracker.apps.is_homebrew_available")
@patch("versiontracker.apps.get_config")
@patch("versiontracker.apps.ThreadPoolExecutor")
@patch("versiontracker.apps.as_completed")
def test_process_brew_batch_with_adaptive_rate_limiter(
    mock_as_completed, mock_executor_class, mock_get_config, mock_is_homebrew
):
    """Test _process_brew_batch with adaptive rate limiter."""
    # Mock is_homebrew_available to return True
    mock_is_homebrew.return_value = True

    # Mock config with adaptive rate limiting enabled
    mock_config = MagicMock()
    mock_config.ui = {"adaptive_rate_limiting": True}
    mock_get_config.return_value = mock_config

    # Mock executor
    mock_executor = MagicMock()
    mock_executor_class.return_value.__enter__.return_value = mock_executor

    # Create a mock future
    mock_future = MagicMock()
    mock_future.result.return_value = True
    mock_executor.submit.return_value = mock_future

    # Mock as_completed to return our future
    mock_as_completed.return_value = [mock_future]

    # Create mock for AdaptiveRateLimiter
    with patch(
        "versiontracker.apps._AdaptiveRateLimiter"
    ) as mock_adaptive_rate_limiter:
        # Call the function
        _process_brew_batch([("Firefox", "100.0")], 2, True)

        # Verify AdaptiveRateLimiter was constructed with correct parameters
        mock_adaptive_rate_limiter.assert_called_once_with(
            base_rate_limit_sec=2.0, min_rate_limit_sec=1.0, max_rate_limit_sec=4.0
        )

@patch("versiontracker.apps.is_homebrew_available")
@patch("versiontracker.apps.ThreadPoolExecutor")
@patch("versiontracker.apps.as_completed")
def test_process_brew_batch_future_exceptions(
    mock_as_completed, mock_executor_class, mock_is_homebrew
):
    """Test _process_brew_batch handling future exceptions."""
    # Mock is_homebrew_available to return True
    mock_is_homebrew.return_value = True

    # Mock executor
    mock_executor = MagicMock()
    mock_executor_class.return_value.__enter__.return_value = mock_executor

    # Test BrewTimeoutError
    mock_future1 = MagicMock()
    mock_future1.result.side_effect = BrewTimeoutError("Operation timed out")
    mock_future1.exception.return_value = BrewTimeoutError("Operation timed out")
    mock_executor.submit.return_value = mock_future1
    mock_as_completed.return_value = [mock_future1]

    # Test that the exception is re-raised
    with pytest.raises(BrewTimeoutError):
        _process_brew_batch([("Firefox", "100.0")], 1, True)

    # Test NetworkError - create a fresh mock
    mock_future2 = MagicMock()
    mock_future2.result.side_effect = NetworkError("Network unavailable")
    mock_future2.exception.return_value = NetworkError("Network unavailable")
    mock_executor.submit.return_value = mock_future2
    mock_as_completed.return_value = [mock_future2]
        
    with pytest.raises(NetworkError):
        _process_brew_batch([("Firefox", "100.0")], 1, True)

    # Test with generic exception containing "No formulae or casks found"
    mock_future3 = MagicMock()
    mock_future3.result.side_effect = Exception("No formulae or casks found")
    mock_future3.exception.return_value = Exception("No formulae or casks found")
    mock_executor.submit.return_value = mock_future3
    mock_as_completed.return_value = [mock_future3]
    result = _process_brew_batch([("Firefox", "100.0")], 1, True)
    assert result == [("Firefox", "100.0", False)]

    # Test with other generic exception
    mock_future4 = MagicMock()
    mock_future4.result.side_effect = Exception("Some other error")
    mock_future4.exception.return_value = Exception("Some other error")
    mock_executor.submit.return_value = mock_future4
    mock_as_completed.return_value = [mock_future4]
    result = _process_brew_batch([("Firefox", "100.0")], 1, True)
    assert result == [("Firefox", "100.0", False)]


if __name__ == "__main__":
    unittest.main()
