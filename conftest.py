"""Pytest configuration and fixtures for VersionTracker tests."""

import sys
from collections.abc import Generator
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

# Ensure the project root is in the Python path
project_root = Path(__file__).parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))


@pytest.fixture
def mock_subprocess() -> Generator[Mock, None, None]:
    """Mock subprocess.run for testing command execution."""
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = Mock(returncode=0, stdout="", stderr="", check_returncode=Mock())
        yield mock_run


@pytest.fixture
def mock_homebrew() -> Generator[Mock, None, None]:
    """Mock Homebrew operations."""
    with patch("versiontracker.homebrew.Homebrew") as mock_brew:
        instance = Mock()
        instance.search_casks.return_value = []
        instance.get_cask_info.return_value = None
        mock_brew.return_value = instance
        yield instance


@pytest.fixture
def temp_config(tmp_path: Path) -> Path:
    """Create a temporary configuration file."""
    config_file = tmp_path / "config.yaml"
    config_file.write_text(
        """
cache:
    enabled: true
    ttl: 3600
    directory: /tmp/versiontracker_test
"""
    )
    return config_file


@pytest.fixture(autouse=True)
def reset_config() -> Generator[None, None, None]:
    """Reset configuration before each test."""
    from versiontracker.config import Config

    if hasattr(Config, "_instance"):
        Config._instance = None
    yield
    if hasattr(Config, "_instance"):
        Config._instance = None


@pytest.fixture
def sample_app() -> dict[str, object]:
    """Create a sample application dictionary for testing."""
    return {
        "name": "Test App",
        "version": "1.2.3",
        "path": "/Applications/Test App.app",
        "bundle_id": "com.example.testapp",
    }


# Configure pytest plugins
pytest_plugins = [
    "pytest_cov",
]
