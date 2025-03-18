# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.3.0] - 2025-03-18

### Added
- Export functionality for JSON and CSV formats
- Command-line arguments for specifying export format (--export)
- Output file option for saving export data (--output-file)
- Comprehensive test suite for export functionality
- New `export.py` module with specialized data formatting functions
- YAML Configuration File Support (~/.config/versiontracker/config.yaml)
- Command-line option to generate default configuration file (--generate-config)
- Layered configuration with environment variables overriding config file
- Updated documentation with export and configuration usage examples

### Changed
- Refactored main application code to handle export options
- Updated CLI interface to include export option group
- Improved error handling for export operations
- Enhanced configuration management with YAML file support

## [0.2.0] - 2025-03-15

### Added
- Continuous Integration/Continuous Deployment setup using GitHub Actions
  - test.yml for running tests on multiple Python versions
  - lint.yml for code quality checking with flake8, black, and isort
  - release.yml for automated PyPI publishing
- Improved test coverage with focus on integration tests
- PyPI trusted publishing configuration

### Changed
- Fixed integration tests to properly mock functions in the __main__ module
- Streamlined code structure for better maintainability
- Updated documentation to reflect CI/CD capabilities

## [0.1.1] - 2022-02-21

### Added
- Initial public release
- Basic application tracking functionality
- Homebrew cask recommendation system
- Command-line interface with basic options
