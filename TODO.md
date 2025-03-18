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

- [ ] **Additional Package Manager Support**
  - [ ] Add support for MacPorts
  - [ ] Integrate with mas-cli for App Store applications
  - [ ] Unify version checking across package managers

- [ ] **Application Profiles**
  - [ ] Create snapshots of installed applications
  - [ ] Allow comparison between profiles to track changes
  - [ ] Implement profile import/export

### Future Enhancements

- [ ] **GUI Interface**
  - [ ] Develop a web-based interface using Flask
  - [ ] Add dark/light mode support
  - [ ] Implement interactive filtering and sorting

- [ ] **Security Analysis**
  - [ ] Integrate with vulnerability databases (NVD, CVE)
  - [ ] Alert on applications with known security issues
  - [ ] Provide update recommendations for security-critical apps

- [ ] **System Integration**
  - [ ] Add launchd service for scheduled checking
  - [ ] Implement macOS notifications for update alerts
  - [ ] Create a menubar application for quick access

## Bugs to Fix

- [ ] **Performance Issues**
  - [ ] Optimize Homebrew cask search to reduce API calls
  - [ ] Fix potential race conditions in concurrent execution
  - [ ] Address memory usage with large application sets

- [ ] **Compatibility**
  - [ ] Test and fix compatibility with homebrew paths on Apple Silicon vs Intel
  - [ ] Verify compatibility with Python 3.11+ (currently tested on 3.7+)
  - [ ] Ensure compatibility with various macOS versions (Monterey, Ventura, Sonoma)

- [ ] **Error Handling**
  - [ ] Improve error messages for common failures
  - [ ] Add graceful handling of network timeouts
  - [ ] Better handling of permission errors

## Optimizations

- [ ] **Performance Improvements**
  - [ ] Implement application data caching to reduce system_profiler calls
  - [ ] Optimize fuzzy matching algorithm for better performance
  - [ ] Add parallel processing for version checking

- [x] **Code Quality**
  - [x] Increase test coverage to >90%
  - [x] Refactor for better module separation
  - [ ] Implement type checking throughout the codebase

- [ ] **User Experience**
  - [ ] Enhance progress visualization with ETA and detailed status
  - [ ] Improve formatting of console output
  - [ ] Add color coding for status indications

- [x] **Documentation**
  - [x] Create comprehensive API documentation
  - [x] Add more usage examples with screenshots
  - [ ] Improve inline code documentation

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
