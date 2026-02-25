"""Tests for versiontracker.handlers.backup_handlers — coverage improvement.

Targets BackupManager methods: create_blacklist_backup, restore_blacklist_from_backup,
cleanup_backup, handle_save_failure, handle_config_error.
"""

import os
from unittest.mock import MagicMock, patch

from versiontracker.handlers.auto_update_types import BlacklistBackup
from versiontracker.handlers.backup_handlers import BackupManager


def _make_manager():
    """Create a BackupManager with mocked config and progress_bar."""
    mgr = BackupManager.__new__(BackupManager)
    mgr.config = MagicMock()
    mgr.progress_bar = MagicMock()
    mgr.progress_bar.color.return_value = lambda x: x
    return mgr


def _make_backup(**kwargs):
    """Create a BlacklistBackup with defaults."""
    defaults = {"original_blacklist": ["app1", "app2"], "timestamp": 1000.0}
    defaults.update(kwargs)
    return BlacklistBackup(**defaults)


# ---------------------------------------------------------------------------
# create_blacklist_backup
# ---------------------------------------------------------------------------


class TestCreateBlacklistBackup:
    """Tests for BackupManager.create_blacklist_backup()."""

    def test_success_creates_file(self, tmp_path):
        mgr = _make_manager()
        with patch("versiontracker.handlers.backup_handlers.tempfile") as mock_tempfile:
            mock_tempfile.gettempdir.return_value = str(tmp_path)
            backup = mgr.create_blacklist_backup(["firefox", "chrome"])
        assert backup.original_blacklist == ["firefox", "chrome"]
        assert backup.backup_file is not None
        assert os.path.exists(backup.backup_file)

    def test_os_error_continues_without_file(self):
        mgr = _make_manager()
        with patch("builtins.open", side_effect=OSError("permission denied")):
            backup = mgr.create_blacklist_backup(["app1"])
        assert backup.original_blacklist == ["app1"]
        assert backup.backup_file is None

    def test_preserves_list_copy(self):
        mgr = _make_manager()
        original = ["app1", "app2"]
        with patch("builtins.open", side_effect=OSError("skip file write")):
            backup = mgr.create_blacklist_backup(original)
        # Modifying original should not affect backup
        original.append("app3")
        assert backup.original_blacklist == ["app1", "app2"]


# ---------------------------------------------------------------------------
# restore_blacklist_from_backup
# ---------------------------------------------------------------------------


class TestRestoreBlacklistFromBackup:
    """Tests for BackupManager.restore_blacklist_from_backup()."""

    def test_success(self):
        mgr = _make_manager()
        mgr.config.save.return_value = True
        backup = _make_backup()
        assert mgr.restore_blacklist_from_backup(backup) is True
        mgr.config.set.assert_called_once_with("blacklist", ["app1", "app2"])

    def test_save_failure(self):
        mgr = _make_manager()
        mgr.config.save.return_value = False
        backup = _make_backup()
        assert mgr.restore_blacklist_from_backup(backup) is False

    def test_exception(self):
        mgr = _make_manager()
        mgr.config.set.side_effect = RuntimeError("boom")
        backup = _make_backup()
        assert mgr.restore_blacklist_from_backup(backup) is False


# ---------------------------------------------------------------------------
# cleanup_backup
# ---------------------------------------------------------------------------


class TestCleanupBackup:
    """Tests for BackupManager.cleanup_backup()."""

    def test_removes_existing_file(self, tmp_path):
        mgr = _make_manager()
        backup_file = tmp_path / "backup.json"
        backup_file.write_text("{}")
        backup = _make_backup(backup_file=str(backup_file))
        mgr.cleanup_backup(backup)
        assert not backup_file.exists()

    def test_no_file_does_nothing(self):
        mgr = _make_manager()
        backup = _make_backup(backup_file=None)
        mgr.cleanup_backup(backup)  # Should not raise

    def test_remove_error_logs_warning(self, tmp_path):
        mgr = _make_manager()
        backup = _make_backup(backup_file=str(tmp_path / "nonexistent.json"))
        mgr.cleanup_backup(backup)  # Should not raise


# ---------------------------------------------------------------------------
# handle_save_failure
# ---------------------------------------------------------------------------


class TestHandleSaveFailure:
    """Tests for BackupManager.handle_save_failure()."""

    def test_restore_succeeds(self):
        mgr = _make_manager()
        mgr.config.save.return_value = True
        backup = _make_backup()
        result = mgr.handle_save_failure(backup)
        assert result == 1

    def test_restore_fails(self):
        mgr = _make_manager()
        mgr.config.set.side_effect = RuntimeError("fail")
        backup = _make_backup(backup_file="/tmp/backup.json")
        result = mgr.handle_save_failure(backup)
        assert result == 1


# ---------------------------------------------------------------------------
# handle_config_error
# ---------------------------------------------------------------------------


class TestHandleConfigError:
    """Tests for BackupManager.handle_config_error()."""

    def test_restore_succeeds(self):
        mgr = _make_manager()
        mgr.config.save.return_value = True
        backup = _make_backup()
        result = mgr.handle_config_error(RuntimeError("test"), backup)
        assert result == 1

    def test_restore_fails_with_backup_file(self):
        mgr = _make_manager()
        mgr.config.set.side_effect = RuntimeError("fail")
        backup = _make_backup(backup_file="/tmp/backup.json")
        result = mgr.handle_config_error(RuntimeError("test"), backup)
        assert result == 1

    def test_restore_fails_no_backup_file(self):
        mgr = _make_manager()
        mgr.config.set.side_effect = RuntimeError("fail")
        backup = _make_backup(backup_file=None)
        result = mgr.handle_config_error(RuntimeError("test"), backup)
        assert result == 1
