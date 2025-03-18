# VersionTracker TODO List

This document outlines planned enhancements, known bugs, and potential optimizations for the VersionTracker project.

## Features to Implement

### High Priority

- [x] **Export Capabilities**
  - [x] Add JSON export option for machine-readable output
  - [x] Add CSV export option for spreadsheet integration
  - [x] Include detailed version information in exports

- [x] **Version Comparison and Outdated Detection**
  - [x] Compare installed versions with latest available from Homebrew
  - [x] Add visual indicators for outdated applications
  - [x] Sort results by "most outdated" first

- [x] **Configuration File Support**
  - [x] Implement YAML configuration file (~/.config/versiontracker/config.yaml)
  - [x] Add config file generation command
  - [x] Allow layered configuration (env vars override config file)

### Medium Priority

- [ ] **Auto-Update Functionality**
  - [ ] Add option to automatically update supported applications
  - [ ] Implement dry-run mode to preview updates
  - [ ] Add confirmation prompts for potentially risky updates
  - [ ] Include safety checks and rollback capabilities

- [ ] **Additional Package Manager Support**
  - [ ] Add support for MacPorts
  - [ ] Integrate with mas-cli for App Store applications
  - [ ] Unify version checking across package managers
  - [ ] Create adapter interfaces for future package managers

- [ ] **Application Profiles**
  - [ ] Create snapshots of installed applications
  - [ ] Allow comparison between profiles to track changes
  - [ ] Implement profile import/export
  - [ ] Enable cloud backup and sync of profiles

### Future Enhancements

- [ ] **GUI Interface**
  - [ ] Develop a web-based interface using Flask
  - [ ] Add dark/light mode support
  - [ ] Implement interactive filtering and sorting
  - [ ] Create data visualization for update statistics

- [ ] **Security Analysis**
  - [ ] Integrate with vulnerability databases (NVD, CVE)
  - [ ] Alert on applications with known security issues
  - [ ] Provide update recommendations for security-critical apps
  - [ ] Add severity ratings for vulnerabilities

- [ ] **System Integration**
  - [ ] Add launchd service for scheduled checking
  - [ ] Implement macOS notifications for update alerts
  - [ ] Create a menubar application for quick access
  - [ ] Add Shortcuts app integration

- [ ] **Plugin System**
  - [ ] Design an extensible plugin architecture
  - [ ] Support user-contributed package manager plugins
  - [ ] Create plugin repository and discovery mechanism
  - [ ] Add plugin security verification

## Bugs to Fix

- [x] **Performance Issues**
  - [x] Optimize Homebrew cask search to reduce API calls
  - [x] Fix potential race conditions in concurrent execution
  - [x] Address memory usage with large application sets

- [x] **Type Safety**
  - [x] Implement type hints throughout the codebase
  - [x] Configure mypy for static type checking
  - [x] Fix type-related issues and errors
  - [x] Ensure backwards compatibility with existing functions

- [ ] **Compatibility**
  - [ ] Test and fix compatibility with homebrew paths on Apple Silicon vs Intel
  - [ ] Verify compatibility with Python 3.11+ (currently tested on 3.7+)
  - [ ] Ensure compatibility with various macOS versions (Monterey, Ventura, Sonoma)
  - [ ] Handle application bundles with non-standard structures

- [x] **Error Handling**
  - [x] Improve error messages for common failures
  - [x] Add graceful handling of network timeouts
  - [x] Better handling of permission errors
  - [x] Fix Homebrew search command execution and error handling
  - [x] Fix rapidfuzz import and usage issues

## Optimizations

- [x] **Performance Improvements**
  - [x] Implement application data caching to reduce system_profiler calls
  - [x] Optimize fuzzy matching algorithm for better performance
  - [x] Add parallel processing for version checking

- [x] **Code Quality**
  - [x] Increase test coverage to >90%
  - [x] Refactor for better module separation
  - [x] Fix failing version comparison tests
  - [x] Implement type checking throughout the codebase

- [x] **Testing**
  - [x] Fix failing tests in test_version.py
  - [x] Fix integration tests in test_integration.py
  - [x] Fix failing tests in test_apps.py
  - [x] Fix failing tests in test_export.py
  - [x] Ensure all tests pass with type checking enabled

- [x] **User Experience**
  - [x] Enhance progress visualization with ETA and detailed status
  - [x] Improve formatting of console output
  - [x] Add proper error handling with clear error messages
  - [x] Add color coding for status indications
  - [x] Add CLI option to toggle progress visualization (--no-progress)

- [x] **Error Handling**
  - [x] Implement custom exception classes for better error classification
  - [x] Add robust error handling for network issues and timeouts
  - [x] Improve error reporting for Homebrew operations
  - [x] Add graceful handling for missing applications and commands
  - [x] Provide clear status indicators for applications with errors

- [x] **Documentation**
  - [x] Create comprehensive API documentation
  - [x] Add more usage examples with screenshots
  - [x] Improve inline code documentation

- [ ] **User Experience Improvements**
  - [ ] Implement color-coded console output for better readability
  - [ ] Add smart progress indicators for long-running operations
  - [ ] Create adaptive rate limiting based on system resources
  - [ ] Support for saving and loading common query filters

## Project Management

- [x] **Release Planning**
  - [x] Define roadmap for v1.0 release
  - [x] Establish semantic versioning policy
  - [x] Create changelog template

- [x] **Community Engagement**
  - [x] Create contributing guidelines
  - [x] Set up issue templates
  - [x] Add community code of conduct

- [x] **CI/CD Integration**
  - [x] Set up GitHub Actions for automated testing on multiple Python versions
  - [x] Implement code quality checks (flake8, black, isort) in CI pipeline
  - [x] Configure automated release workflow with PyPI trusted publishing

---

## How to Contribute

If you'd like to work on any of these items, please:
1. Create an issue referencing the specific task
2. Fork the repository
3. Create a branch with a descriptive name
4. Submit a pull request with your changes

Please see our [CONTRIBUTING.md](CONTRIBUTING.md) for more details.
