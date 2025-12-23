# VersionTracker TODO

## Current Status (December 2025)

### Project Health

- **Version**: 0.8.1
- **Tests**: 1,230+ passing tests, 70%+ coverage
- **CI/CD**: All 11 workflows passing
- **Python Support**: 3.12+ (with 3.13 compatibility)
- **Security**: No known vulnerabilities

### Recent Completions (v0.8.1)

- Fixed 4 failing integration tests
- Resolved CI/CD pipeline stability issues (pytest-timeout)
- Updated vulnerable dependencies
- Repository cleanup and organization
- Added deprecation notice to `version_legacy.py`

## Active Development

### Code Quality

- [ ] Refactor `version_legacy.py` (1,950 lines, ~11% coverage)
  - Break into smaller, focused modules
  - Increase test coverage before migration
  - Migrate functionality to `versiontracker.version` package

### Performance Optimization

- [ ] Complete async migration for Homebrew API calls
  - Current: 893ms single cask, 2.7s batch
  - Target: Parallel batch processing for 5x+ speedup

## Homebrew Release Preparation

### Phase 1: Pre-Release Validation

- [ ] Confirm target version tag exists: `git fetch --tags && git tag -l v0.8.1`
- [ ] Ensure CHANGELOG has entry for this version
- [ ] Run full test suite locally: `pytest`
- [ ] Validate packaging: `python -m build`

### Phase 2: Formula Creation

- [ ] Download canonical GitHub tag archive
- [ ] Compute SHA256 checksum
- [ ] Update `versiontracker.rb` formula
- [ ] Run: `brew audit --new-formula --strict ./versiontracker.rb`

### Phase 3: Tap Repository

- [ ] Update `homebrew-versiontracker` repository
- [ ] Test tap: `brew tap docdyhr/versiontracker && brew install versiontracker`

## Future Enhancements

### Extended Package Manager Support

- [ ] MacPorts integration
- [ ] mas-cli for App Store applications
- [ ] Unified interface for multiple package managers

### Platform Compatibility

- [ ] Apple Silicon vs Intel Homebrew path handling
- [ ] macOS version compatibility (Monterey through Sequoia)

### GUI/Web Interface

- [ ] FastAPI-based web interface
- [ ] Real-time update monitoring dashboard
- [ ] Mobile-responsive design

### Security Features

- [ ] Vulnerability database integration (NVD, CVE)
- [ ] Security scoring for installed applications
- [ ] Alert on applications with known issues

## Contributing

### Good First Issues

- Add examples to documentation
- Improve error messages
- Add edge case tests

### Advanced Contributions

- MacPorts integration
- Performance optimization
- Web interface development

---

**Last Updated**: December 2025
**Maintainer**: @docdyhr
