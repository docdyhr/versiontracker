# Release Notes - Version 0.6.5

**Release Date:** January 14, 2025  
**Type:** Bug Fix Release  

## 🎯 Overview

Version 0.6.5 is a focused bug fix release that resolves critical CI/CD pipeline issues and improves test reliability. This release ensures robust continuous integration across all supported Python versions and fixes test isolation problems that were causing intermittent failures.

## ✅ What's Fixed

### CI/CD Pipeline Improvements
- **Added Python 3.13 to CI test matrix** to match supported versions declared in `pyproject.toml`
- **Resolved failing `test_ci_python_versions`** in project consistency tests
- **Enhanced CI coverage** to test all declared Python versions (3.10, 3.11, 3.12, 3.13)

### Test Reliability Enhancements
- **Fixed UI test failures** (`test_cprint_fallback` and `test_print_functions_with_file_kwarg`)
- **Improved monkey-patching approach** to prevent module caching issues
- **Enhanced test isolation** for consistent execution in both individual and full test suite runs
- **All 988 tests now pass consistently** with 70.04% coverage

### Code Quality
- **Applied code formatting** with ruff for consistency
- **Updated project documentation** to reflect latest changes
- **Improved test robustness** across different execution environments

## 📊 Test Results

- ✅ **988 tests passing, 12 skipped**
- ✅ **70.04% test coverage** (exceeds 60% requirement)
- ✅ **Zero compilation errors**
- ✅ **All linting checks pass**

## 🔧 Technical Details

### Python Version Support
- **Confirmed support** for Python 3.10, 3.11, 3.12, and 3.13
- **CI pipeline now tests** all supported versions consistently
- **Prevented potential compatibility issues** with untested Python versions

### Test Infrastructure
- **Monkey-patching fixes** use module attribute access instead of re-importing
- **Eliminates race conditions** in test execution order
- **Improves reliability** for continuous integration environments

## 🚀 What's Next

This release sets a solid foundation for future development:
- All critical infrastructure issues resolved
- Comprehensive CI/CD coverage established
- Test suite reliability maximized
- Ready for feature development in upcoming releases

## 📝 Migration Notes

**No breaking changes** - this is a drop-in replacement for version 0.6.4.

Users can upgrade safely with:
```bash
pip install --upgrade versiontracker
```

## 🎉 Acknowledgments

This release demonstrates our commitment to code quality and reliability. The comprehensive test suite and robust CI/CD pipeline ensure that VersionTracker continues to provide reliable application management for macOS users.

---

**Full Changelog:** [View on GitHub](https://github.com/docdyhr/versiontracker/blob/master/CHANGELOG.md)  
**Issues Fixed:** Project consistency tests, UI test failures, CI coverage gaps  
**Next Release:** Focus will shift to feature enhancements and user experience improvements