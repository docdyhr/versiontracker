# VersionTracker TODO

This document outlines planned enhancements and future development for the VersionTracker project.

## 🚀 High Priority

### Technical Debt Resolution (NEW - July 2025)

- [x] **Line Length Standards Harmonization** (Completed July 2025)
  - [x] Established consistent 120-character limit across codebase
  - [x] Updated pyproject.toml with clear documentation
  - [x] Enhanced CLAUDE.md with coding standards section
  - [x] Verified E501 rule enforcement via ruff
  - [x] Confirmed zero violations in current codebase

- [ ] **Fix Coverage Reporting Discrepancy** (Critical)
  - [ ] Investigate why HTML coverage shows 16% vs 70%+ actual
  - [ ] Update coverage configuration in pyproject.toml
  - [ ] Verify accurate reporting across all modules
  - [ ] Ensure CI/CD uses correct coverage metrics

- [ ] **Update Dependencies** (Security)
  - [ ] Update psutil from 6.1.1 to 7.0.0
  - [ ] Review and update all development dependencies
  - [ ] Test compatibility after updates
  - [ ] Update lock files for reproducible builds

### Performance and Architecture

- [ ] **Async Network Operations Enhancement**
  - [ ] Convert remaining synchronous Homebrew API calls to async/await
  - [ ] Implement request batching to reduce API calls
  - [ ] Add proper timeout handling and retry logic
  - [ ] Benchmark performance improvements

- [ ] **Test Coverage Improvement** (Current: 70.88% → Target: 85%)
  - [ ] Add more comprehensive tests for `apps.py` and `config.py`
  - [ ] Create integration tests for real-world scenarios
  - [ ] Add performance benchmarking suite
  - [ ] Improve coverage for newly added auto-update functionality

### Feature Enhancements

- [x] **Auto-Update Functionality** ✅ (Completed July 2025)
  - [x] Add option to automatically update applications via Homebrew
  - [x] Implement dry-run mode to preview updates
  - [x] Add confirmation prompts for potentially risky updates
  - [x] Added comprehensive auto-updates management system

- [ ] **Extended Package Manager Support**
  - [ ] Add support for MacPorts package manager
  - [ ] Integrate with mas-cli for App Store applications
  - [ ] Create unified interface for multiple package managers

## 🔧 Medium Priority

### Code Quality and Maintainability (NEW - July 2025)

- [ ] **Refactor Large Modules** (Maintainability)
  - [ ] Split version.py (1,911 lines) into focused modules:
    - [ ] version/parser.py - Parsing functions
    - [ ] version/comparator.py - Comparison logic  
    - [ ] version/models.py - Data classes
  - [ ] Refactor apps.py (1,413 lines) for better organization:
    - [ ] apps/finder.py - Application discovery
    - [ ] apps/matcher.py - Fuzzy matching logic
    - [ ] apps/cache.py - Caching functionality
  - [ ] Consider breaking down config.py (1,031 lines)

- [ ] **Improve Type Safety** (Quality)
  - [ ] Enable strict type checking in mypy configuration
  - [ ] Add type annotations to menubar_app.py untyped functions
  - [ ] Review and fix any new type errors
  - [ ] Enable --check-untyped-defs flag

### Developer Experience

- [x] **CI/CD Pipeline Enhancement**
  - [x] Add Python 3.13 to test matrix (already implemented)
  - [x] Implement automated dependency updates (enhanced Dependabot configuration)
  - [x] Set up automated performance regression testing (new workflow created)

- [x] **Documentation Overhaul**
  - [x] Update README.md with latest features and examples (async, caching, profiling)
  - [x] Create comprehensive contributing guidelines (CONTRIBUTING.md)
  - [x] Add architecture documentation for new contributors (docs/ARCHITECTURE.md)

### System Integration

- [x] **macOS Integration**
  - [x] Add launchd service for scheduled application checking
  - [x] Implement macOS notifications for update alerts
  - [x] Create menubar application for quick access

## 🔧 New High Priority Items

### Testing and Quality

- [ ] **Auto-Update Feature Testing**
  - [ ] Add comprehensive unit tests for new auto-update functionality
  - [ ] Create integration tests for update confirmation flows
  - [ ] Test rollback mechanisms for failed updates
  - [ ] Add edge case handling for partial update failures

- [ ] **CI/CD Pipeline Stabilization**
  - [ ] Fix remaining platform-specific test failures
  - [ ] Improve cross-platform test compatibility
  - [ ] Add Python 3.13 support once stable
  - [ ] Enhance dependency management with lock files

## 🔮 Long-term Goals

### Security and Monitoring

- [ ] **Vulnerability Management**
  - [ ] Integrate with vulnerability databases (NVD, CVE)
  - [ ] Alert on applications with known security issues
  - [ ] Provide update recommendations for security-critical apps
  - [ ] Add security scoring for installed applications

### GUI and Web Interface

- [ ] **Modern Interface Development**
  - [ ] Develop web-based interface using FastAPI
  - [ ] Add dark/light mode support
  - [ ] Implement interactive filtering and sorting
  - [ ] Real-time update monitoring dashboard

### Plugin System

- [ ] **Extensibility Framework**
  - [ ] Design extensible plugin architecture
  - [ ] Support user-contributed package manager plugins
  - [ ] Create plugin repository and discovery mechanism
  - [ ] Add plugin sandboxing for security

## 🐛 Known Issues

### Technical Debt Items (NEW - July 2025)

- [ ] **Clean Up Security Warnings** (Code Quality)
  - [ ] Rename "blacklist" variables throughout codebase to "blocklist" or "exclude_list"
  - [ ] Configure bandit to suppress false positive warnings
  - [ ] Review hardcoded_sql_expressions warning in advanced_cache.py:575
  - [ ] Address subprocess_without_shell_equals_true in macos_integration.py:249

### Compatibility and Edge Cases

- [ ] **Platform Compatibility**
  - [ ] Test compatibility with Apple Silicon vs Intel Homebrew paths
  - [ ] Verify compatibility with Python 3.13+ (currently testing 3.10-3.12)
  - [ ] Ensure compatibility with various macOS versions (Monterey through Sequoia)

- [ ] **Error Handling Improvements**
  - [ ] Better handling of applications with irregular version formats
  - [ ] Improved error handling for network timeouts and connectivity issues
  - [x] Enhanced fuzzy matching accuracy for similar application names

## 📊 Current Project Status

### Metrics (July 2025)

- **Test Coverage**: 70.88% (962 passing, 14 skipped, 0 failing)
- **Code Quality**: Excellent (all critical complexity issues resolved)
- **Security**: Excellent (0 high-severity vulnerabilities)
- **Performance**: Good (parallel processing, async operations, caching implemented)
- **Maintainability**: Excellent (clean architecture, comprehensive refactoring completed)

### Development Status

- **Production Ready**: ✅ Core functionality stable and reliable
- **Auto-Updates**: ✅ Comprehensive auto-update management system implemented
- **Contributor Friendly**: ✅ Clear architecture and documentation
- **CI/CD Pipeline**: ✅ Automated testing and quality checks
- **Release Process**: ✅ Semantic versioning and automated releases

## 🤝 Contributing

### Good First Issues

- Improve documentation examples
- Add edge case tests for version parsing
- Implement configuration wizard
- Fix remaining minor compatibility issues

### Advanced Contributions

- Async network operations implementation
- MacPorts integration
- Web interface development
- Security vulnerability integration

---

**Last Updated**: July 2025  
**Project Status**: Production Ready - All major technical debt resolved  
**Focus**: Feature development and user experience improvements  
**Key Recent Updates**: ✅ Auto-update functionality completed | ✅ CI/CD pipeline enhanced  
**macOS Service**: ✅ Installed and running
