# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.5.0] - 2025-03-18

### Added (0.5.0)

- Comprehensive error handling system with custom exception classes
- Custom exception hierarchy with domain-specific error types
- Improved error reporting for network operations, Homebrew commands, and file operations
- Graceful handling for network timeouts and connection issues
- Better error messages for common failures with suggested solutions
- User-friendly error feedback with color-coded messages
- Enhanced error classification for better troubleshooting
- Exception chaining to preserve error context

### Changed (0.5.0)

- Refactored command execution to provide more detailed error information
- Improved error handling in export functions
- Enhanced error recovery mechanisms with conditional retries
- Updated documentation with error handling information
- Completed all error handling tasks from the project roadmap

## [0.4.0] - 2025-03-18

### Added (0.4.0)

- Version comparison functionality to check for outdated applications
- New command-line option (`--outdated`) to identify applications that need updating
- Intelligent version parsing and comparison for various version formats
- Configuration options for version comparison behavior and preferences
- Status indicators for applications (up-to-date, outdated, newer, unknown)
- Sorting of results by outdated status
- Unit tests for version comparison functionality
- Enhanced configuration with version comparison settings

### Changed (0.4.0)

- Improved application version detection
- Updated documentation with version comparison examples
- Enhanced compatibility with different version number formats

## [0.3.1] - 2025-03-19

### Added (0.3.1)

- Support for specifying custom configuration file paths with `--config-path`
- Ability to use custom configuration file locations when running the application
- New tests for custom configuration file handling

### Changed (0.3.1)

- Improved configuration handling with global config instance management
- Enhanced documentation for configuration file usage
- Updated CLI help text to better describe configuration options

## [0.3.0] - 2025-03-18

### Added (0.3.0)

- Export functionality for JSON and CSV formats
- Command-line arguments for specifying export format (--export)
- Output file option for saving export data (--output-file)
- Comprehensive test suite for export functionality
- New `export.py` module with specialized data formatting functions
- YAML Configuration File Support (~/.config/versiontracker/config.yaml)
- Command-line option to generate default configuration file (--generate-config)
- Layered configuration with environment variables overriding config file
- Updated documentation with export and configuration usage examples

### Changed (0.3.0)

- Refactored main application code to handle export options
- Updated CLI interface to include export option group
- Improved error handling for export operations
- Enhanced configuration management with YAML file support

## [0.2.0] - 2025-03-15

### Added (0.2.0)

- Continuous Integration/Continuous Deployment setup using GitHub Actions
  - test.yml for running tests on multiple Python versions
  - lint.yml for code quality checking with flake8, black, and isort
  - release.yml for automated PyPI publishing
- Improved test coverage with focus on integration tests
- PyPI trusted publishing configuration

### Changed (0.2.0)

- Fixed integration tests to properly mock functions in the __main__ module
- Streamlined code structure for better maintainability
- Updated documentation to reflect CI/CD capabilities

## [0.1.1] - 2022-02-21

### Added (0.1.1)

- Initial public release
- Basic application tracking functionality
- Homebrew cask recommendation system
- Command-line interface with basic options
