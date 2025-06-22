"""Comprehensive tests for utils module."""

import json
import subprocess
import threading
import time
from unittest.mock import MagicMock, Mock, mock_open, patch

import pytest

from versiontracker.exceptions import (
    DataParsingError,
    FileNotFoundError,
    NetworkError,
    PermissionError,
    TimeoutError,
)
from versiontracker.utils import (
    APP_CACHE_FILE,
    APP_CACHE_TTL,
    DEFAULT_API_RATE_LIMIT,
    SYSTEM_PROFILER_CMD,
    RateLimiter,
    _ensure_cache_dir,
    _read_cache_file,
    _write_cache_file,
    get_json_data,
    get_shell_json_data,
    get_user_agent,
    normalise_name,
    run_command,
    run_command_original,
    setup_logging,
)


class TestSetupLogging:
    """Test setup_logging function."""

    @patch("versiontracker.utils.Path")
    @patch("logging.basicConfig")
    @patch("sys.version_info", (3, 10, 0))
    def test_setup_logging_debug_mode_python_39_plus(self, mock_basicconfig, mock_path):
        """Test setup_logging with debug mode in Python 3.9+."""
        mock_log_dir = MagicMock()
        mock_path.home.return_value = MagicMock()
        mock_path.home.return_value.__truediv__.return_value.__truediv__.return_value.__truediv__.return_value = mock_log_dir
        mock_log_dir.mkdir = MagicMock()
        mock_log_dir.__truediv__.return_value = "/fake/path/versiontracker.log"

        setup_logging(debug=True)

        mock_log_dir.mkdir.assert_called_once_with(parents=True, exist_ok=True)
        mock_basicconfig.assert_called_once()
        call_kwargs = mock_basicconfig.call_args[1]
        assert "encoding" in call_kwargs
        assert call_kwargs["encoding"] == "utf-8"

    @patch("versiontracker.utils.Path")
    @patch("logging.basicConfig")
    @patch("sys.version_info", (3, 8, 0))
    def test_setup_logging_info_mode_python_38(self, mock_basicconfig, mock_path):
        """Test setup_logging with info mode in Python 3.8."""
        mock_log_dir = MagicMock()
        mock_path.home.return_value = MagicMock()
        mock_path.home.return_value.__truediv__.return_value.__truediv__.return_value.__truediv__.return_value = mock_log_dir
        mock_log_dir.mkdir = MagicMock()
        mock_log_dir.__truediv__.return_value = "/fake/path/versiontracker.log"

        setup_logging(debug=False)

        mock_basicconfig.assert_called_once()
        call_kwargs = mock_basicconfig.call_args[1]
        assert "encoding" not in call_kwargs

    @patch("versiontracker.utils.Path")
    @patch("logging.basicConfig")
    def test_setup_logging_directory_creation_error(self, mock_basicconfig, mock_path):
        """Test setup_logging handles directory creation errors gracefully."""
        mock_log_dir = MagicMock()
        mock_path.home.return_value = MagicMock()
        mock_path.home.return_value.__truediv__.return_value.__truediv__.return_value.__truediv__.return_value = mock_log_dir
        mock_log_dir.mkdir.side_effect = OSError("Permission denied")
        mock_log_dir.__truediv__.return_value = "/fake/path/versiontracker.log"

        # Should not raise an exception
        setup_logging(debug=True)

        mock_basicconfig.assert_called_once()


class TestNormaliseName:
    """Test normalise_name function."""

    def test_normalise_name_basic(self):
        """Test basic name normalization."""
        assert normalise_name("App Name") == "App Name"

    def test_normalise_name_with_numbers(self):
        """Test name normalization with numbers."""
        assert normalise_name("App123 Name456") == "App Name"

    def test_normalise_name_with_whitespace(self):
        """Test name normalization with leading/trailing whitespace."""
        assert normalise_name("  App Name  ") == "App Name"

    def test_normalise_name_with_non_printable(self):
        """Test name normalization with non-printable characters."""
        non_printable = "App\x00\x01Name"
        result = normalise_name(non_printable)
        assert result == "AppName"

    def test_normalise_name_empty_string(self):
        """Test name normalization with empty string."""
        assert normalise_name("") == ""

    def test_normalise_name_only_numbers(self):
        """Test name normalization with only numbers."""
        assert normalise_name("12345") == ""

    def test_normalise_name_complex_case(self):
        """Test name normalization with complex input."""
        complex_name = "  App123\x00Name456\x01Test  "
        result = normalise_name(complex_name)
        assert result == "AppNameTest"


class TestCacheHelpers:
    """Test cache helper functions."""

    @patch("os.makedirs")
    @patch("os.path.dirname")
    def test_ensure_cache_dir(self, mock_dirname, mock_makedirs):
        """Test _ensure_cache_dir creates directory."""
        mock_dirname.return_value = "/fake/cache/dir"

        _ensure_cache_dir()

        mock_makedirs.assert_called_once_with("/fake/cache/dir", exist_ok=True)

    @patch("os.makedirs")
    @patch("os.path.dirname")
    def test_ensure_cache_dir_error(self, mock_dirname, mock_makedirs):
        """Test _ensure_cache_dir handles errors gracefully."""
        mock_dirname.return_value = "/fake/cache/dir"
        mock_makedirs.side_effect = OSError("Permission denied")

        # Should not raise an exception
        _ensure_cache_dir()

    @patch("time.time")
    @patch("os.path.exists")
    @patch("builtins.open", new_callable=mock_open)
    def test_read_cache_file_valid_cache(self, mock_file, mock_exists, mock_time):
        """Test reading valid cache file."""
        mock_exists.return_value = True
        mock_time.return_value = 2000
        cache_data = {"timestamp": 1500, "data": {"apps": "test"}}
        mock_file.return_value.read.return_value = json.dumps(cache_data)

        result = _read_cache_file()

        assert result == cache_data

    @patch("time.time")
    @patch("os.path.exists")
    def test_read_cache_file_no_file(self, mock_exists, mock_time):
        """Test reading cache when file doesn't exist."""
        mock_exists.return_value = False

        result = _read_cache_file()

        assert result == {}

    @patch("time.time")
    @patch("os.path.exists")
    @patch("builtins.open", new_callable=mock_open)
    def test_read_cache_file_expired(self, mock_file, mock_exists, mock_time):
        """Test reading expired cache file."""
        mock_exists.return_value = True
        mock_time.return_value = 5000
        cache_data = {"timestamp": 1000, "data": {"apps": "test"}}
        mock_file.return_value.read.return_value = json.dumps(cache_data)

        result = _read_cache_file()

        assert result == {}

    @patch("logging.warning")
    @patch("os.path.exists")
    @patch("builtins.open", new_callable=mock_open)
    def test_read_cache_file_json_error(self, mock_file, mock_exists, mock_warning):
        """Test reading cache file with JSON error."""
        mock_exists.return_value = True
        mock_file.return_value.read.return_value = "invalid json"

        result = _read_cache_file()

        assert result == {}
        mock_warning.assert_called()

    @patch("versiontracker.utils._ensure_cache_dir")
    @patch("time.time")
    @patch("builtins.open", new_callable=mock_open)
    def test_write_cache_file_success(self, mock_file, mock_time, mock_ensure_dir):
        """Test successful cache file writing."""
        mock_time.return_value = 1500
        test_data = {"apps": "test"}

        _write_cache_file(test_data)

        mock_ensure_dir.assert_called_once()
        mock_file.assert_called_once()

    @patch("versiontracker.utils._ensure_cache_dir")
    @patch("time.time")
    @patch("logging.warning")
    @patch("builtins.open", new_callable=mock_open)
    def test_write_cache_file_error(
        self, mock_file, mock_warning, mock_time, mock_ensure_dir
    ):
        """Test cache file writing with error."""
        mock_time.return_value = 1500
        mock_file.side_effect = OSError("Permission denied")
        test_data = {"apps": "test"}

        _write_cache_file(test_data)

        mock_warning.assert_called()


class TestGetJsonData:
    """Test get_json_data function."""

    def setup_method(self):
        """Clear the lru_cache before each test."""
        from versiontracker.utils import _check_system_profiler_cache

        _check_system_profiler_cache.cache_clear()

    def teardown_method(self):
        """Clear the lru_cache after each test."""
        from versiontracker.utils import _check_system_profiler_cache

        _check_system_profiler_cache.cache_clear()

    @patch("versiontracker.utils._write_cache_file")
    @patch("versiontracker.utils._read_cache_file")
    @patch("versiontracker.utils.run_command")
    def test_get_json_data_cache_hit(
        self, mock_run_cmd, mock_read_cache, mock_write_cache
    ):
        """Test get_json_data with cache hit."""
        cached_data = {"data": {"apps": "cached"}}
        mock_read_cache.return_value = cached_data

        result = get_json_data(SYSTEM_PROFILER_CMD)

        assert result == cached_data["data"]
        mock_run_cmd.assert_not_called()
        mock_write_cache.assert_not_called()

    @patch("versiontracker.utils._write_cache_file")
    @patch("versiontracker.utils._read_cache_file")
    @patch("versiontracker.utils.run_command")
    def test_get_json_data_cache_miss(
        self, mock_run_cmd, mock_read_cache, mock_write_cache
    ):
        """Test get_json_data with cache miss."""
        mock_read_cache.return_value = {}
        test_data = {"apps": "fresh"}
        mock_run_cmd.return_value = (json.dumps(test_data), 0)

        result = get_json_data(SYSTEM_PROFILER_CMD)

        assert result == test_data
        mock_run_cmd.assert_called_once_with(SYSTEM_PROFILER_CMD, timeout=60)
        mock_write_cache.assert_called_once_with(test_data)

    @patch("versiontracker.utils.run_command")
    def test_get_json_data_non_system_profiler(self, mock_run_cmd):
        """Test get_json_data with non-system profiler command."""
        test_data = {"result": "test"}
        mock_run_cmd.return_value = (json.dumps(test_data), 0)

        result = get_json_data("other command")

        assert result == test_data
        mock_run_cmd.assert_called_once_with("other command", timeout=60)

    @patch("versiontracker.utils.run_command")
    def test_get_json_data_command_failure(self, mock_run_cmd):
        """Test get_json_data with command failure."""
        mock_run_cmd.return_value = ("error output", 1)

        with pytest.raises(DataParsingError):
            get_json_data("failing command")

    @patch("versiontracker.utils.run_command")
    def test_get_json_data_empty_output(self, mock_run_cmd):
        """Test get_json_data with empty output."""
        mock_run_cmd.return_value = ("", 0)

        with pytest.raises(DataParsingError, match="produced no output"):
            get_json_data("empty command")

    @patch("versiontracker.utils.run_command")
    def test_get_json_data_invalid_json(self, mock_run_cmd):
        """Test get_json_data with invalid JSON."""
        mock_run_cmd.return_value = ("invalid json", 0)

        with pytest.raises(DataParsingError, match="Failed to parse JSON"):
            get_json_data("invalid json command")

    @patch("versiontracker.utils.run_command")
    def test_get_json_data_command_not_found(self, mock_run_cmd):
        """Test get_json_data with command not found error."""
        error = subprocess.CalledProcessError(127, "cmd", "command not found")
        mock_run_cmd.side_effect = error

        with pytest.raises(FileNotFoundError):
            get_json_data("nonexistent command")

    @patch("versiontracker.utils.run_command")
    def test_get_json_data_permission_denied(self, mock_run_cmd):
        """Test get_json_data with permission denied error."""
        error = subprocess.CalledProcessError(13, "cmd", "permission denied")
        mock_run_cmd.side_effect = error

        with pytest.raises(PermissionError):
            get_json_data("restricted command")

    @patch("versiontracker.utils.run_command")
    def test_get_json_data_network_error(self, mock_run_cmd):
        """Test get_json_data with network error."""
        mock_run_cmd.side_effect = Exception("network timeout error")

        with pytest.raises(NetworkError):
            get_json_data("network command")


class TestGetShellJsonData:
    """Test get_shell_json_data function."""

    @patch("versiontracker.utils.run_command")
    def test_get_shell_json_data_success(self, mock_run_cmd):
        """Test successful shell JSON data retrieval."""
        test_data = {"result": "success"}
        mock_run_cmd.return_value = (json.dumps(test_data), 0)

        result = get_shell_json_data("test command", timeout=60)

        assert result == test_data
        mock_run_cmd.assert_called_once_with("test command", timeout=60)

    @patch("versiontracker.utils.run_command")
    def test_get_shell_json_data_command_failure(self, mock_run_cmd):
        """Test shell JSON data with command failure."""
        mock_run_cmd.return_value = ("error", 1)

        with pytest.raises(DataParsingError):
            get_shell_json_data("failing command")

    @patch("versiontracker.utils.run_command")
    def test_get_shell_json_data_invalid_json(self, mock_run_cmd):
        """Test shell JSON data with invalid JSON."""
        mock_run_cmd.return_value = ("invalid json", 0)

        with pytest.raises(DataParsingError, match="Invalid JSON data"):
            get_shell_json_data("invalid json command")

    @patch("versiontracker.utils.run_command")
    def test_get_shell_json_data_timeout_error(self, mock_run_cmd):
        """Test shell JSON data with timeout error."""
        mock_run_cmd.side_effect = TimeoutError("Command timed out")

        with pytest.raises(TimeoutError):
            get_shell_json_data("slow command")

    @patch("versiontracker.utils.run_command")
    def test_get_shell_json_data_permission_error(self, mock_run_cmd):
        """Test shell JSON data with permission error."""
        mock_run_cmd.side_effect = PermissionError("Permission denied")

        with pytest.raises(PermissionError):
            get_shell_json_data("restricted command")

    @patch("versiontracker.utils.run_command")
    def test_get_shell_json_data_generic_exception(self, mock_run_cmd):
        """Test shell JSON data with generic exception."""
        mock_run_cmd.side_effect = Exception("Generic error")

        with pytest.raises(Exception, match="Failed to get JSON data"):
            get_shell_json_data("error command")


class TestRunCommand:
    """Test run_command function."""

    @patch("subprocess.Popen")
    def test_run_command_success(self, mock_popen):
        """Test successful command execution."""
        mock_process = Mock()
        mock_process.communicate.return_value = ("output", "")
        mock_process.returncode = 0
        mock_popen.return_value = mock_process

        stdout, returncode = run_command("test command")

        assert stdout == "output"
        assert returncode == 0

    @patch("subprocess.Popen")
    def test_run_command_with_timeout(self, mock_popen):
        """Test command execution with timeout."""
        mock_process = Mock()
        mock_process.communicate.return_value = ("output", "")
        mock_process.returncode = 0
        mock_popen.return_value = mock_process

        stdout, returncode = run_command("test command", timeout=30)

        mock_process.communicate.assert_called_once_with(timeout=30)

    @patch("subprocess.Popen")
    def test_run_command_failure_with_stderr(self, mock_popen):
        """Test command execution failure with stderr."""
        mock_process = Mock()
        mock_process.communicate.return_value = ("", "error message")
        mock_process.returncode = 1
        mock_popen.return_value = mock_process

        stdout, returncode = run_command("failing command")

        assert stdout == "error message"
        assert returncode == 1

    @patch("subprocess.Popen")
    def test_run_command_homebrew_not_found(self, mock_popen):
        """Test command execution with Homebrew not found (expected case)."""
        mock_process = Mock()
        mock_process.communicate.return_value = (
            "",
            "Error: No formulae or casks found",
        )
        mock_process.returncode = 1
        mock_popen.return_value = mock_process

        stdout, returncode = run_command("brew search nonexistent")

        assert "No formulae or casks found" in stdout
        assert returncode == 1

    @patch("subprocess.Popen")
    def test_run_command_command_not_found(self, mock_popen):
        """Test command execution with command not found."""
        mock_process = Mock()
        mock_process.communicate.return_value = ("", "command not found")
        mock_process.returncode = 127
        mock_popen.return_value = mock_process

        with pytest.raises(FileNotFoundError):
            run_command("nonexistent_command")

    @patch("subprocess.Popen")
    def test_run_command_permission_denied(self, mock_popen):
        """Test command execution with permission denied."""
        mock_process = Mock()
        mock_process.communicate.return_value = ("", "permission denied")
        mock_process.returncode = 13
        mock_popen.return_value = mock_process

        with pytest.raises(PermissionError):
            run_command("restricted_command")

    @patch("subprocess.Popen")
    def test_run_command_network_error(self, mock_popen):
        """Test command execution with network error."""
        mock_process = Mock()
        mock_process.communicate.return_value = ("", "network is unreachable")
        mock_process.returncode = 1
        mock_popen.return_value = mock_process

        with pytest.raises(NetworkError):
            run_command("network_command")

    @patch("subprocess.Popen")
    def test_run_command_timeout_expired(self, mock_popen):
        """Test command execution with timeout expired."""
        mock_process = Mock()
        mock_process.communicate.side_effect = subprocess.TimeoutExpired("cmd", 30)
        mock_process.kill = Mock()
        mock_popen.return_value = mock_process

        with pytest.raises(TimeoutError):
            run_command("slow_command", timeout=30)

        mock_process.kill.assert_called_once()

    @patch("subprocess.Popen")
    def test_run_command_timeout_kill_error(self, mock_popen):
        """Test command execution with timeout and kill error."""
        mock_process = Mock()
        mock_process.communicate.side_effect = subprocess.TimeoutExpired("cmd", 30)
        mock_process.kill.side_effect = Exception("Kill failed")
        mock_popen.return_value = mock_process

        with pytest.raises(TimeoutError):
            run_command("slow_command", timeout=30)

    @patch("subprocess.Popen")
    def test_run_command_file_not_found_exception(self, mock_popen):
        """Test command execution with FileNotFoundError exception."""
        mock_popen.side_effect = FileNotFoundError("Command not found")

        with pytest.raises(FileNotFoundError):
            run_command("nonexistent_command")

    @patch("subprocess.Popen")
    def test_run_command_permission_error_exception(self, mock_popen):
        """Test command execution with PermissionError exception."""
        mock_popen.side_effect = PermissionError("Permission denied")

        with pytest.raises(PermissionError):
            run_command("restricted_command")

    @patch("subprocess.Popen")
    def test_run_command_subprocess_error(self, mock_popen):
        """Test command execution with subprocess error."""
        mock_popen.side_effect = subprocess.SubprocessError("Subprocess error")

        with pytest.raises(subprocess.SubprocessError):
            run_command("error_command")

    @patch("subprocess.Popen")
    def test_run_command_generic_network_exception(self, mock_popen):
        """Test command execution with generic network exception."""
        mock_popen.side_effect = Exception("network connection failed")

        with pytest.raises(NetworkError):
            run_command("network_command")

    @patch("subprocess.Popen")
    def test_run_command_generic_exception(self, mock_popen):
        """Test command execution with generic exception."""
        mock_popen.side_effect = Exception("Generic error")

        with pytest.raises(Exception, match="Error executing command"):
            run_command("error_command")


class TestRunCommandOriginal:
    """Test run_command_original function."""

    @patch("subprocess.run")
    def test_run_command_original_success(self, mock_run):
        """Test successful command execution."""
        mock_result = Mock()
        mock_result.stdout = "line1\nline2\n\nline3\n"
        mock_run.return_value = mock_result

        result = run_command_original("test command")

        assert result == ["line1", "line2", "line3"]
        mock_run.assert_called_once_with(
            "test command",
            shell=True,
            capture_output=True,
            text=True,
            check=True,
            timeout=30,
        )

    @patch("subprocess.run")
    def test_run_command_original_with_timeout(self, mock_run):
        """Test command execution with custom timeout."""
        mock_result = Mock()
        mock_result.stdout = "output\n"
        mock_run.return_value = mock_result

        result = run_command_original("test command", timeout=60)

        assert result == ["output"]
        mock_run.assert_called_once_with(
            "test command",
            shell=True,
            capture_output=True,
            text=True,
            check=True,
            timeout=60,
        )

    @patch("subprocess.run")
    def test_run_command_original_timeout_expired(self, mock_run):
        """Test command execution with timeout expired."""
        mock_run.side_effect = subprocess.TimeoutExpired("cmd", 30)

        with pytest.raises(TimeoutError):
            run_command_original("slow command")

    @patch("subprocess.run")
    def test_run_command_original_permission_denied(self, mock_run):
        """Test command execution with permission denied."""
        error = subprocess.CalledProcessError(13, "cmd")
        error.stderr = "permission denied"
        mock_run.side_effect = error

        with pytest.raises(PermissionError):
            run_command_original("restricted command")

    @patch("subprocess.run")
    def test_run_command_original_command_not_found(self, mock_run):
        """Test command execution with command not found."""
        error = subprocess.CalledProcessError(127, "cmd")
        error.stderr = "command not found"
        mock_run.side_effect = error

        with pytest.raises(FileNotFoundError):
            run_command_original("nonexistent command")

    @patch("subprocess.run")
    def test_run_command_original_file_not_found(self, mock_run):
        """Test command execution with file not found."""
        error = subprocess.CalledProcessError(2, "cmd")
        error.stderr = "no such file or directory"
        mock_run.side_effect = error

        with pytest.raises(FileNotFoundError):
            run_command_original("missing file command")

    @patch("subprocess.run")
    def test_run_command_original_network_error(self, mock_run):
        """Test command execution with network error."""
        error = subprocess.CalledProcessError(1, "cmd")
        error.stderr = "network is unreachable"
        mock_run.side_effect = error

        with pytest.raises(NetworkError):
            run_command_original("network command")

    @patch("subprocess.run")
    def test_run_command_original_generic_error(self, mock_run):
        """Test command execution with generic error."""
        error = subprocess.CalledProcessError(1, "cmd")
        error.stderr = "generic error"
        mock_run.side_effect = error

        with pytest.raises(RuntimeError):
            run_command_original("error command")

    @patch("subprocess.run")
    def test_run_command_original_exception(self, mock_run):
        """Test command execution with generic exception."""
        mock_run.side_effect = Exception("Unexpected error")

        with pytest.raises(RuntimeError):
            run_command_original("error command")


class TestGetUserAgent:
    """Test get_user_agent function."""

    @patch("platform.python_version")
    @patch("platform.system")
    @patch("versiontracker.utils.__version__", "0.6.4")
    def test_get_user_agent(self, mock_system, mock_python_version):
        """Test user agent string generation."""
        mock_python_version.return_value = "3.11.0"
        mock_system.return_value = "Darwin"

        result = get_user_agent()

        assert result == "VersionTracker/0.6.4 (Python/3.11.0; Darwin)"


class TestRateLimiter:
    """Test RateLimiter class."""

    def test_rate_limiter_initialization(self):
        """Test rate limiter initialization."""
        limiter = RateLimiter(calls_per_period=5, period=2.0)

        assert limiter.calls_per_period == 5
        assert limiter.period == 2.0
        assert limiter.timestamps == []

    def test_rate_limiter_single_call(self):
        """Test rate limiter with single call."""
        limiter = RateLimiter(calls_per_period=1, period=1.0)

        start_time = time.time()
        limiter.wait()
        end_time = time.time()

        # Should not wait for the first call
        assert (end_time - start_time) < 0.1

    @patch("time.time")
    @patch("time.sleep")
    def test_rate_limiter_rate_limiting(self, mock_sleep, mock_time):
        """Test rate limiter actually limits calls."""
        mock_time.side_effect = [100.0, 100.5, 101.0, 101.5]
        limiter = RateLimiter(calls_per_period=1, period=1.0)

        # First call should not wait
        limiter.wait()
        mock_sleep.assert_not_called()

        # Second call should wait
        limiter.wait()
        mock_sleep.assert_called_once()

    @patch("time.time")
    def test_rate_limiter_timestamp_cleanup(self, mock_time):
        """Test rate limiter cleans up old timestamps."""
        mock_time.side_effect = [100.0, 101.0, 103.0]
        limiter = RateLimiter(calls_per_period=2, period=2.0)

        # Add timestamps
        limiter.wait()  # t=100
        limiter.wait()  # t=101

        # After period, old timestamps should be cleaned
        limiter.wait()  # t=103, should clean t=100

        assert len(limiter.timestamps) == 2

    def test_rate_limiter_thread_safety(self):
        """Test rate limiter thread safety."""
        limiter = RateLimiter(calls_per_period=5, period=1.0)
        results = []

        def worker():
            start_time = time.time()
            limiter.wait()
            end_time = time.time()
            results.append(end_time - start_time)

        # Create multiple threads
        threads = [threading.Thread(target=worker) for _ in range(3)]

        # Start all threads
        for thread in threads:
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # All threads should complete without errors
        assert len(results) == 3

    @patch("time.time")
    @patch("time.sleep")
    def test_rate_limiter_multiple_calls_within_limit(self, mock_sleep, mock_time):
        """Test multiple calls within the limit."""
        mock_time.side_effect = [100.0, 100.1, 100.2]
        limiter = RateLimiter(calls_per_period=3, period=1.0)

        # Three calls within limit should not wait
        limiter.wait()
        limiter.wait()
        limiter.wait()

        mock_sleep.assert_not_called()

    @patch("time.time")
    @patch("time.sleep")
    def test_rate_limiter_lock_release_during_sleep(self, mock_sleep, mock_time):
        """Test that lock is released during sleep."""
        mock_time.side_effect = [100.0, 100.1, 100.2]
        limiter = RateLimiter(calls_per_period=1, period=1.0)

        # First call
        limiter.wait()

        # Second call should wait and release lock during sleep
        limiter.wait()

        # Verify sleep was called
        assert mock_sleep.called


class TestConstants:
    """Test module constants."""

    def test_constants_exist(self):
        """Test that required constants are defined."""
        assert APP_CACHE_FILE is not None
        assert APP_CACHE_TTL > 0
        assert SYSTEM_PROFILER_CMD is not None
        assert DEFAULT_API_RATE_LIMIT > 0

    def test_cache_file_path(self):
        """Test cache file path format."""
        assert "versiontracker" in APP_CACHE_FILE
        assert APP_CACHE_FILE.endswith(".json")

    def test_system_profiler_command(self):
        """Test system profiler command format."""
        assert "system_profiler" in SYSTEM_PROFILER_CMD
        assert "-json" in SYSTEM_PROFILER_CMD
        assert "SPApplicationsDataType" in SYSTEM_PROFILER_CMD


class TestEdgeCases:
    """Test edge cases and error conditions."""

    @patch("versiontracker.utils.run_command")
    def test_get_json_data_none_output(self, mock_run_cmd):
        """Test get_json_data with None output."""
        mock_run_cmd.return_value = (None, 0)

        with pytest.raises(DataParsingError):
            get_json_data("null command")

    def test_normalise_name_unicode(self):
        """Test name normalization with unicode characters."""
        unicode_name = "App üñíçødé Name"
        result = normalise_name(unicode_name)
        assert "üñíçødé" in result

    def test_rate_limiter_zero_period(self):
        """Test rate limiter with zero period."""
        limiter = RateLimiter(calls_per_period=1, period=0.0)

        # Should not cause issues
        limiter.wait()
        limiter.wait()

    def test_rate_limiter_negative_period(self):
        """Test rate limiter with negative period."""
        limiter = RateLimiter(calls_per_period=1, period=-1.0)

        # Should handle gracefully
        limiter.wait()

    @patch("time.time")
    def test_read_cache_file_missing_timestamp(self, mock_time):
        """Test reading cache file with missing timestamp."""
        mock_time.return_value = 2000

        with patch("os.path.exists", return_value=True):
            with patch("builtins.open", mock_open(read_data='{"data": "test"}')):
                result = _read_cache_file()
                assert result == {}

    @patch("versiontracker.utils.run_command")
    def test_get_json_data_whitespace_only_output(self, mock_run_cmd):
        """Test get_json_data with whitespace-only output."""
        mock_run_cmd.return_value = ("   \n\t  ", 0)

        with pytest.raises(DataParsingError):
            get_json_data("whitespace command")
