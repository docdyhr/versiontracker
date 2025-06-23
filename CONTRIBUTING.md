# Contributing to VersionTracker

Thank you for your interest in contributing to VersionTracker! This document provides comprehensive
guidelines for contributing to the project.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Project Architecture](#project-architecture)
- [Coding Standards](#coding-standards)
- [Testing Guidelines](#testing-guidelines)
- [Performance Considerations](#performance-considerations)
- [Pull Request Process](#pull-request-process)
- [Issue Reporting](#issue-reporting)
- [Release Process](#release-process)

## Code of Conduct

This project adheres to a code of conduct. By participating, you are expected to:

- Be respectful and inclusive in all interactions
- Provide constructive feedback and criticism
- Focus on what is best for the community
- Show empathy towards other community members

## Getting Started

### Prerequisites

- macOS (primary development platform)
- Python 3.10 or later
- Homebrew package manager
- Git for version control

### Quick Setup

```bash
# Fork and clone the repository
git clone https://github.com/your-username/versiontracker.git
cd versiontracker

# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install development dependencies
pip install -c constraints.txt -r requirements.txt
pip install -c constraints.txt -r requirements-dev.txt
pip install -e .

# Install pre-commit hooks
pre-commit install
```

## Development Setup

### Virtual Environment

Always use a virtual environment to isolate dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate  # Linux/macOS
# or
.venv\Scripts\activate     # Windows
```

### Dependencies

The project uses several categories of dependencies:

- **Core dependencies** (`requirements.txt`): Runtime dependencies
- **Development dependencies** (`requirements-dev.txt`): Testing, linting, formatting tools
- **Constraints** (`constraints.txt`): Version pinning for reproducible builds

### Development Tools

Essential tools for development:

```bash
# Code formatting and linting
ruff check .                    # Linting
ruff format .                   # Code formatting
mypy versiontracker            # Type checking

# Testing
pytest                         # Run all tests
pytest --cov                   # Run with coverage
pytest -m "not slow"          # Skip slow tests

# Security and quality
bandit -r versiontracker/      # Security analysis
safety check                   # Dependency vulnerability scan
```

## Project Architecture

### Module Organization

```text
versiontracker/
├── __init__.py              # Package initialization
├── __main__.py              # CLI entry point
├── cli.py                   # Command-line interface
├── apps.py                  # Application discovery and analysis
├── homebrew.py              # Homebrew integration (sync)
├── async_homebrew.py        # Homebrew integration (async)
├── async_network.py         # Async network utilities
├── cache.py                 # Basic caching functionality
├── advanced_cache.py        # Multi-tier caching system
├── profiling.py            # Performance monitoring
├── utils.py                # Utility functions
├── config.py               # Configuration management
├── exceptions.py           # Custom exceptions
└── version.py              # Version information
```

### Key Components

1. **CLI Layer** (`cli.py`): Handles command-line parsing and user interaction
2. **Core Logic** (`apps.py`, `homebrew.py`): Business logic for app discovery and version checking
3. **Network Layer** (`async_network.py`, `async_homebrew.py`): Handles API communication
4. **Caching Layer** (`cache.py`, `advanced_cache.py`): Performance optimization
5. **Utilities** (`utils.py`, `config.py`, `profiling.py`): Supporting functionality

### Data Flow

1. **User Input** → CLI parsing and validation
2. **Configuration** → Load user preferences and settings
3. **App Discovery** → Scan filesystem for applications
4. **Homebrew Integration** → Fetch package information (with caching)
5. **Data Analysis** → Compare versions and generate recommendations
6. **Output** → Format and display results

## Coding Standards

### Code Style

- **Formatter**: [Ruff](https://github.com/astral-sh/ruff) for code formatting
- **Linter**: Ruff for linting with aggressive rules
- **Type Checker**: MyPy for static type analysis
- **Line Length**: 100 characters maximum (enforced by Ruff)
- **Imports**: Organized with `isort` integration

### Python Style Guidelines

```python
# Good: Clear, typed function with docstring
async def fetch_cask_info(
    cask_name: str,
    timeout: int = DEFAULT_TIMEOUT,
    use_cache: bool = True
) -> Dict[str, Any]:
    """Fetch information about a Homebrew cask asynchronously.

    Args:
        cask_name: Name of the cask
        timeout: Request timeout in seconds
        use_cache: Whether to use cached results

    Returns:
        Dict containing cask information

    Raises:
        NetworkError: If there's a network issue
        TimeoutError: If the request times out
    """
    # Implementation...
```

### Type Annotations

- **Required** for all public functions and methods
- **Encouraged** for internal functions
- Use `typing` module for complex types
- Follow PEP 484 guidelines

### Documentation

- **Docstrings**: Google-style docstrings for all public functions
- **Inline comments**: For complex logic or non-obvious code
- **README updates**: For user-facing changes
- **Architecture docs**: For significant design changes

### Error Handling

```python
# Use custom exceptions for domain-specific errors
from versiontracker.exceptions import HomebrewError, NetworkError

try:
    result = await fetch_data()
except aiohttp.ClientError as e:
    raise NetworkError(f"Failed to fetch data: {e}") from e
```

## Testing Guidelines

### Test Organization

```text
tests/
├── test_apps.py              # Application discovery tests
├── test_homebrew.py          # Homebrew integration tests
├── test_async_homebrew.py    # Async homebrew tests
├── test_cache.py             # Caching functionality tests
├── test_profiling.py         # Performance profiling tests
├── test_integration.py       # End-to-end integration tests
├── mock_homebrew_server.py   # Mock server for testing
└── fixtures/                 # Test data and fixtures
```

### Test Types

1. **Unit Tests**: Test individual functions and classes
2. **Integration Tests**: Test component interactions
3. **Performance Tests**: Ensure performance requirements
4. **Regression Tests**: Prevent reintroduction of bugs

### Writing Tests

```python
import pytest
from unittest.mock import patch, MagicMock

class TestHomebrewIntegration:
    """Test cases for Homebrew integration."""

    @pytest.mark.asyncio
    async def test_fetch_cask_info_success(self):
        """Test successful cask information retrieval."""
        # Arrange
        expected_data = {"name": "test-app", "version": "1.0.0"}

        # Act
        with patch('aiohttp.ClientSession.get') as mock_get:
            mock_get.return_value.__aenter__.return_value.json.return_value = expected_data
            result = await fetch_cask_info("test-app")

        # Assert
        assert result == expected_data
        mock_get.assert_called_once()

    @pytest.mark.network
    def test_network_integration(self):
        """Test real network integration."""
        # Only runs when network tests are enabled
        pass
```

### Test Execution

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=versiontracker --cov-report=html

# Run specific test categories
pytest -m "not slow"           # Skip slow tests
pytest -m integration          # Only integration tests
pytest -m network             # Only network tests

# Run with verbose output
pytest -v --tb=short
```

### Test Coverage Requirements

- **Minimum**: 70% overall coverage
- **Target**: 85% overall coverage
- **Critical paths**: 95%+ coverage required
- **New code**: Must maintain or improve coverage

## Performance Considerations

### Asynchronous Programming

- Use `async`/`await` for I/O operations
- Implement proper timeout handling
- Use `aiohttp` for HTTP requests
- Batch operations when possible

```python
# Good: Asynchronous batch processing
async def process_casks_batch(cask_names: List[str]) -> List[Dict[str, Any]]:
    """Process multiple casks concurrently."""
    tasks = [fetch_cask_info(name) for name in cask_names]
    return await asyncio.gather(*tasks, return_exceptions=True)
```

### Caching Strategy

- Use appropriate cache levels (memory, disk, compressed)
- Implement cache invalidation
- Monitor cache hit rates
- Consider cache size limits

### Memory Management

- Use generators for large datasets
- Implement proper resource cleanup
- Monitor memory usage in tests
- Profile memory-intensive operations

## Pull Request Process

### Before Submitting

1. **Create feature branch** from `master`
2. **Make atomic commits** with clear messages
3. **Add/update tests** for your changes
4. **Run full test suite** and ensure it passes
5. **Update documentation** if needed
6. **Check performance impact** for significant changes

### PR Guidelines

1. **Title**: Clear, descriptive title following conventional commits
2. **Description**:
   - What changes were made and why
   - Any breaking changes
   - Testing instructions
   - Related issues
3. **Size**: Keep PRs focused and reasonably sized
4. **Commits**: Squash if needed for clean history

### Example PR Template

```markdown
## Summary
Brief description of changes made.

## Changes
- [ ] Feature: Add async batch processing
- [ ] Tests: Add integration tests for batch operations
- [ ] Docs: Update README with new async examples

## Testing
- All existing tests pass
- Added 5 new test cases
- Performance testing shows 40% improvement

## Breaking Changes
None.

## Related Issues
Closes #123
```

### Review Process

1. **Automated checks** must pass (CI/CD pipeline)
2. **Code review** by at least one maintainer
3. **Performance review** for performance-critical changes
4. **Documentation review** for user-facing changes

## Issue Reporting

### Bug Reports

```markdown
**Bug Description**
A clear description of the bug.

**Reproduction Steps**
1. Step one
2. Step two
3. Step three

**Expected Behavior**
What should happen.

**Actual Behavior**  
What actually happens.

**Environment**
- macOS version:
- Python version:
- VersionTracker version:
- Homebrew version:

**Additional Context**
Logs, screenshots, or other helpful information.
```

### Feature Requests

```markdown
**Feature Description**
Clear description of the proposed feature.

**Use Case**
Why is this feature needed? What problem does it solve?

**Proposed Solution**
How should this feature work?

**Alternatives Considered**
Other approaches you've considered.

**Additional Context**
Any other context or examples.
```

### Performance Issues

Include profiling data, performance benchmarks, and specific scenarios where performance is inadequate.

## Release Process

### Version Management

- **Semantic Versioning**: MAJOR.MINOR.PATCH
- **Version file**: Update `versiontracker/version.py`
- **Changelog**: Maintain `CHANGELOG.md`
- **Git tags**: Tag releases in git

### Release Checklist

1. **Update version number** in `version.py`
2. **Update CHANGELOG.md** with release notes
3. **Run full test suite** on multiple Python versions
4. **Performance testing** to ensure no regressions
5. **Create release PR** for final review
6. **Tag release** after merge
7. **GitHub Actions** handles PyPI deployment

### Release Types

- **Patch** (0.0.X): Bug fixes, no new features
- **Minor** (0.X.0): New features, backward compatible
- **Major** (X.0.0): Breaking changes, major new features

## Communication

### Getting Help

- **Issues**: GitHub issues for bugs and feature requests
- **Discussions**: GitHub discussions for questions and ideas
- **Email**: Maintainer email for security issues

### Community Guidelines

- Be respectful and constructive
- Search existing issues before creating new ones
- Provide clear, detailed information
- Be patient with response times

---

## Additional Resources

- [Project README](README.md)
- [Architecture Documentation](docs/ARCHITECTURE.md) *(coming soon)*
- [API Documentation](docs/API.md) *(coming soon)*
- [Performance Guide](docs/PERFORMANCE.md) *(coming soon)*

Thank you for contributing to VersionTracker! 🚀
