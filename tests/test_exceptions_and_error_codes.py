"""Tests for versiontracker.exceptions and versiontracker.error_codes modules.

Covers the structured error hierarchy, StructuredError class, create_error helper,
and get_errors_by_category / get_errors_by_severity filters.
"""

import pytest

from versiontracker.error_codes import (
    ErrorCategory,
    ErrorCode,
    ErrorSeverity,
    StructuredError,
    create_error,
    get_errors_by_category,
    get_errors_by_severity,
)
from versiontracker.exceptions import (
    ApplicationError,
    BrewPermissionError,
    BrewTimeoutError,
    CacheError,
    ConfigError,
    DataParsingError,
    ExportError,
    HandlerError,
    HomebrewError,
    NetworkError,
    TimeoutError,
    ValidationError,
    VersionError,
    VersionTrackerError,
)

# ---------------------------------------------------------------------------
# error_codes.py
# ---------------------------------------------------------------------------


class TestErrorCode:
    def test_enum_members_have_code_message_severity(self):
        ec = ErrorCode.NET001
        assert ec.code == "NET001"
        assert "Network" in ec.message
        assert ec.severity == ErrorSeverity.HIGH

    def test_category_derived_from_prefix(self):
        assert ErrorCode.NET001.category == ErrorCategory.NETWORK
        assert ErrorCode.HBW001.category == ErrorCategory.HOMEBREW
        assert ErrorCode.CFG002.category == ErrorCategory.CONFIG
        assert ErrorCode.SYS001.category == ErrorCategory.SYSTEM
        assert ErrorCode.APP001.category == ErrorCategory.APPLICATION
        assert ErrorCode.VER001.category == ErrorCategory.VERSION
        assert ErrorCode.PRM001.category == ErrorCategory.PERMISSION
        assert ErrorCode.VAL001.category == ErrorCategory.VALIDATION
        assert ErrorCode.CHE001.category == ErrorCategory.CACHE
        assert ErrorCode.EXP001.category == ErrorCategory.EXPORT

    def test_severity_values(self):
        assert ErrorSeverity.LOW.value == "low"
        assert ErrorSeverity.MEDIUM.value == "medium"
        assert ErrorSeverity.HIGH.value == "high"
        assert ErrorSeverity.CRITICAL.value == "critical"


class TestStructuredError:
    def test_basic_properties(self):
        err = StructuredError(error_code=ErrorCode.NET001)
        assert err.code == "NET001"
        assert err.message == ErrorCode.NET001.message
        assert err.severity == ErrorSeverity.HIGH
        assert err.category == ErrorCategory.NETWORK

    def test_defaults(self):
        err = StructuredError(error_code=ErrorCode.SYS001)
        assert err.details == ""
        assert err.context == {}
        assert err.suggestions == []
        assert err.original_exception is None

    def test_with_all_fields(self):
        orig = ValueError("original")
        err = StructuredError(
            error_code=ErrorCode.CFG002,
            details="bad yaml",
            context={"file": "/tmp/config.yaml"},
            suggestions=["Check syntax"],
            original_exception=orig,
        )
        assert err.details == "bad yaml"
        assert err.context == {"file": "/tmp/config.yaml"}
        assert err.suggestions == ["Check syntax"]
        assert err.original_exception is orig

    def test_to_dict_includes_all_keys(self):
        err = StructuredError(
            error_code=ErrorCode.HBW001,
            details="not found",
            context={"path": "/usr/local/bin/brew"},
            suggestions=["Install Homebrew"],
            original_exception=RuntimeError("missing"),
        )
        d = err.to_dict()
        assert d["code"] == "HBW001"
        assert d["details"] == "not found"
        assert d["context"] == {"path": "/usr/local/bin/brew"}
        assert d["suggestions"] == ["Install Homebrew"]
        assert "missing" in d["original_exception"]
        assert d["severity"] == "critical"
        assert d["category"] == "HBW"

    def test_to_dict_no_exception(self):
        err = StructuredError(error_code=ErrorCode.VAL001)
        assert err.to_dict()["original_exception"] is None

    def test_format_user_message_minimal(self):
        err = StructuredError(error_code=ErrorCode.VER001)
        msg = err.format_user_message()
        assert "VER001" in msg
        assert ErrorCode.VER001.message in msg

    def test_format_user_message_with_details(self):
        err = StructuredError(error_code=ErrorCode.VER001, details="1.2.3.4.5 is invalid")
        msg = err.format_user_message()
        assert "Details:" in msg
        assert "1.2.3.4.5 is invalid" in msg

    def test_format_user_message_with_context(self):
        err = StructuredError(error_code=ErrorCode.PRM001, context={"file": "/etc/hosts"})
        msg = err.format_user_message()
        assert "Context:" in msg
        assert "/etc/hosts" in msg

    def test_format_user_message_with_suggestions(self):
        err = StructuredError(error_code=ErrorCode.NET001, suggestions=["Check wifi", "Try VPN"])
        msg = err.format_user_message()
        assert "Suggestions:" in msg
        assert "Check wifi" in msg
        assert "Try VPN" in msg

    def test_str_representation(self):
        err = StructuredError(error_code=ErrorCode.APP001)
        assert "APP001" in str(err)

    def test_repr_representation(self):
        err = StructuredError(error_code=ErrorCode.EXP001)
        r = repr(err)
        assert "EXP001" in r
        assert "StructuredError" in r
        assert "medium" in r


class TestCreateError:
    def test_creates_structured_error(self):
        err = create_error(ErrorCode.NET001)
        assert isinstance(err, StructuredError)
        assert err.code == "NET001"

    def test_auto_populates_suggestions_for_known_codes(self):
        err = create_error(ErrorCode.HBW001)
        assert len(err.suggestions) > 0

    def test_no_suggestions_for_unknown_code(self):
        err = create_error(ErrorCode.CHE001)
        assert err.suggestions == []

    def test_forwards_details_and_context(self):
        err = create_error(ErrorCode.CFG002, details="bad format", context={"line": 5})
        assert err.details == "bad format"
        assert err.context == {"line": 5}

    def test_forwards_original_exception(self):
        orig = KeyError("missing_key")
        err = create_error(ErrorCode.SYS001, original_exception=orig)
        assert err.original_exception is orig


class TestGetErrorsByCategory:
    def test_returns_only_matching_category(self):
        net_errors = get_errors_by_category(ErrorCategory.NETWORK)
        assert all(e.category == ErrorCategory.NETWORK for e in net_errors)
        assert ErrorCode.NET001 in net_errors

    def test_homebrew_category(self):
        hbw = get_errors_by_category(ErrorCategory.HOMEBREW)
        assert ErrorCode.HBW001 in hbw
        assert ErrorCode.NET001 not in hbw

    def test_returns_list(self):
        assert isinstance(get_errors_by_category(ErrorCategory.CACHE), list)


class TestGetErrorsBySeverity:
    def test_returns_only_matching_severity(self):
        criticals = get_errors_by_severity(ErrorSeverity.CRITICAL)
        assert all(e.severity == ErrorSeverity.CRITICAL for e in criticals)

    def test_high_severity_non_empty(self):
        highs = get_errors_by_severity(ErrorSeverity.HIGH)
        assert len(highs) > 0
        assert ErrorCode.NET001 in highs

    def test_returns_list(self):
        assert isinstance(get_errors_by_severity(ErrorSeverity.LOW), list)


# ---------------------------------------------------------------------------
# exceptions.py
# ---------------------------------------------------------------------------


class TestVersionTrackerError:
    def test_plain_message(self):
        err = VersionTrackerError("something went wrong")
        assert str(err) == "something went wrong"
        assert err.structured_error is None
        assert err.get_error_code() is None
        assert err.get_context() == {}

    def test_with_error_code(self):
        err = VersionTrackerError(error_code=ErrorCode.SYS001)
        assert err.structured_error is not None
        assert err.get_error_code() == "SYS001"

    def test_with_error_code_and_details(self):
        err = VersionTrackerError(error_code=ErrorCode.NET001, details="connection refused")
        assert err.structured_error.details == "connection refused"

    def test_with_context(self):
        err = VersionTrackerError(error_code=ErrorCode.CFG001, context={"file": "cfg.yaml"})
        assert err.get_context() == {"file": "cfg.yaml"}

    def test_with_original_exception(self):
        orig = OSError("disk full")
        err = VersionTrackerError(error_code=ErrorCode.SYS004, original_exception=orig)
        assert err.structured_error.original_exception is orig

    def test_to_dict_with_structured_error(self):
        err = VersionTrackerError(error_code=ErrorCode.VER001)
        d = err.to_dict()
        assert d["code"] == "VER001"

    def test_to_dict_without_structured_error(self):
        err = VersionTrackerError("plain")
        d = err.to_dict()
        assert d["message"] == "plain"
        assert d["code"] is None

    def test_is_exception(self):
        with pytest.raises(VersionTrackerError):
            raise VersionTrackerError("test")


class TestConfigError:
    def test_default_message(self):
        err = ConfigError()
        assert err is not None

    def test_with_config_file_and_error_code(self):
        # context is only stored when error_code is also provided
        err = ConfigError("bad config", config_file="/home/user/.config.yaml", error_code=ErrorCode.CFG002)
        assert err.get_context().get("config_file") == "/home/user/.config.yaml"

    def test_with_config_file_no_error_code(self):
        # Without error_code the constructor still accepts config_file; context not retained
        err = ConfigError("bad config", config_file="/home/user/.config.yaml")
        assert isinstance(err, ConfigError)

    def test_without_config_file(self):
        err = ConfigError("missing key")
        assert "config_file" not in err.get_context()

    def test_is_versiontracker_error(self):
        assert isinstance(ConfigError(), VersionTrackerError)


class TestVersionError:
    def test_with_version_string_and_error_code(self):
        err = VersionError("parse failed", version_string="1.2.3.bad", error_code=ErrorCode.VER001)
        assert err.get_context().get("version_string") == "1.2.3.bad"

    def test_with_version_string_no_error_code(self):
        # Constructor accepts version_string even without error_code
        err = VersionError("parse failed", version_string="1.2.3.bad")
        assert isinstance(err, VersionError)

    def test_without_version_string(self):
        err = VersionError("generic version error")
        assert "version_string" not in err.get_context()


class TestNetworkError:
    def test_with_url_and_status_and_error_code(self):
        err = NetworkError("request failed", url="https://example.com", status_code=503, error_code=ErrorCode.NET001)
        ctx = err.get_context()
        assert ctx.get("url") == "https://example.com"
        assert ctx.get("status_code") == 503

    def test_with_url_no_error_code(self):
        # Constructor accepts url without error_code
        err = NetworkError("timeout", url="https://api.example.com")
        assert isinstance(err, NetworkError)

    def test_without_url(self):
        err = NetworkError("network down")
        assert "url" not in err.get_context()


class TestTimeoutError:
    def test_with_timeout_and_operation_and_error_code(self):
        err = TimeoutError("timed out", timeout_seconds=30.0, operation="brew update", error_code=ErrorCode.SYS005)
        ctx = err.get_context()
        assert ctx.get("timeout_seconds") == 30.0
        assert ctx.get("operation") == "brew update"

    def test_without_optional_fields(self):
        err = TimeoutError("timed out")
        assert "timeout_seconds" not in err.get_context()
        assert "operation" not in err.get_context()


class TestHomebrewError:
    def test_with_command_and_cask_and_error_code(self):
        err = HomebrewError(
            "install failed",
            command="brew install --cask firefox",
            cask_name="firefox",
            error_code=ErrorCode.HBW002,
        )
        ctx = err.get_context()
        assert ctx.get("command") == "brew install --cask firefox"
        assert ctx.get("cask_name") == "firefox"

    def test_without_optional_fields(self):
        err = HomebrewError("brew broken")
        assert "command" not in err.get_context()
        assert "cask_name" not in err.get_context()


class TestApplicationError:
    def test_with_app_name_and_path_and_error_code(self):
        err = ApplicationError(
            "detection failed",
            app_name="MyApp",
            app_path="/Applications/MyApp.app",
            error_code=ErrorCode.APP001,
        )
        ctx = err.get_context()
        assert ctx.get("app_name") == "MyApp"
        assert ctx.get("app_path") == "/Applications/MyApp.app"

    def test_without_optional_fields(self):
        err = ApplicationError()
        assert "app_name" not in err.get_context()


class TestCacheError:
    def test_with_cache_key_and_file_and_error_code(self):
        err = CacheError(
            "read failed", cache_key="brew_casks", cache_file="/tmp/cache.pkl", error_code=ErrorCode.CHE001
        )
        ctx = err.get_context()
        assert ctx.get("cache_key") == "brew_casks"
        assert ctx.get("cache_file") == "/tmp/cache.pkl"

    def test_without_optional_fields(self):
        err = CacheError()
        assert "cache_key" not in err.get_context()


class TestHandlerError:
    def test_with_handler_name_and_error_code(self):
        err = HandlerError("handler crashed", handler_name="handle_list_apps", error_code=ErrorCode.SYS001)
        assert err.get_context().get("handler_name") == "handle_list_apps"

    def test_without_handler_name(self):
        err = HandlerError()
        assert "handler_name" not in err.get_context()


class TestSimpleSubclasses:
    def test_data_parsing_error(self):
        err = DataParsingError("json decode error")
        assert isinstance(err, VersionTrackerError)
        assert str(err) == "json decode error"

    def test_brew_permission_error(self):
        err = BrewPermissionError("no access")
        assert isinstance(err, HomebrewError)
        assert isinstance(err, VersionTrackerError)

    def test_brew_timeout_error(self):
        err = BrewTimeoutError("timed out")
        assert isinstance(err, NetworkError)

    def test_export_error(self):
        err = ExportError("export failed")
        assert isinstance(err, VersionTrackerError)

    def test_validation_error(self):
        err = ValidationError("invalid arg")
        assert isinstance(err, VersionTrackerError)

    def test_file_not_found_error(self):
        import builtins

        from versiontracker.exceptions import FileNotFoundError as VTFileNotFoundError

        err = VTFileNotFoundError("missing file")
        assert isinstance(err, VersionTrackerError)
        assert isinstance(err, builtins.FileNotFoundError)

    def test_permission_error(self):
        import builtins

        from versiontracker.exceptions import PermissionError as VTPermissionError

        err = VTPermissionError("no permission")
        assert isinstance(err, VersionTrackerError)
        assert isinstance(err, builtins.PermissionError)
