# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Implemented parameterized tests for version comparison to reduce code duplication
- Created a mock server for network operation testing with simulated failures and edge cases
- Developed an advanced caching mechanism for Homebrew queries with tiered caching (memory and disk)
- Added cache compression for large responses to reduce disk usage
- Implemented thread-safe batch operations for efficient Homebrew queries
- Created detailed cache statistics and monitoring functionality
- Added request batching to reduce network calls and improve performance
- Enhanced error handling for network operations with comprehensive test coverage

## [0.6.4] - 2025-05-16

### Added

- Added ROADMAP.md with detailed development plans for short-term, medium-term, and long-term goals
- Structured improvement tasks with clear prioritization and timeline
- Created new handlers/ directory following the command pattern for better code organization
- Implemented handler modules for different command functionalities
- Added comprehensive documentation for the handlers package structure

### Fixed

- Completed missing VersionError class in exceptions.py
- Fixed config import error by replacing direct references to config with get_config()
- Improved error handling in logging statements
- Updated global config instance name for better encapsulation
- Fixed f-string usage in logging statements to use proper string formatting
- Resolved dependency issues by ensuring all required packages were installed
- Fixed exception order issues in multiple try-except blocks (bad-except-order)
- Added missing 'from e' clauses to exception re-raising statements
- Fixed various linting warnings to improve code quality
- Migrated from black/isort/flake8 to ruff for code formatting and linting

## [0.6.3] - 2025-04-01

### Fixed (0.6.3)

- Fixed GitHub badges in README.md to correctly display master branch status
- Completed review of semantic versioning implementation
- Verified GitHub Actions workflows for unintended side effects
- Updated TODO.md to reflect completed review tasks

## [0.6.2] - 2025-03-19

### Fixed (0.6.2)

- Fixed Homebrew integration to properly detect brew paths on both Intel and M1/M2 Macs
- Improved handling of brew commands to support newer Homebrew versions
- Added fallback mechanism for brew command execution
- Enhanced error handling for Homebrew operations
- Fixed tests to properly mock Homebrew interactions
- Updated is_homebrew_available to check multiple potential Homebrew locations
- Improved error messages for common Homebrew failures

## [0.6.1] - 2025-03-19

### Fixed (0.6.1)

- Fixed dependency issue by adding PyYAML to requirements
- Fixed run_command usage in brew search functions to properly handle returned tuples
- Fixed missing HAS_VERSION_PROGRESS variable in version.py
- Fixed type errors with VersionStatus in check_outdated_apps function
- Fixed tuple handling throughout codebase to match the correct return values
- Improved type hints for better compatibility with mypy validation
- Various small fixes to ensure tests pass correctly

## [0.6.0] - 2025-03-18

### Added (0.6.0)

- Added color-coded console output for better readability
- Added smart progress indicators that monitor system resources
- Implemented adaptive rate limiting based on CPU and memory usage
- Added support for saving and loading common query filters
- Created a dedicated UI module for all user interface components
- Added new CLI options to control UI features

## [0.5.1] - 2025-03-18

### Fixed (0.5.1)

- Fixed the 'USE_RAPIDFUZZ is not defined' error by properly importing the variable in apps.py
- Fixed 'argument of type 'int' is not iterable' errors in the Homebrew search functionality
- Fixed command execution in _cached_brew_search to properly handle tuples returned by run_command
- Improved shell command escaping to handle application names with special characters
- Enhanced the Homebrew search functionality to properly handle failed searches

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
