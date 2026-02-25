# VersionTracker TODO

## Current Status (February 2026)

### Project Health

- **Version**: 0.8.2-dev
- **Tests**: 1,563 passing, 29 skipped (of 1,592 collected)
- **CI/CD**: All 11 workflows passing
- **Python Support**: 3.12+ (with 3.13 compatibility)
- **Security**: No known vulnerabilities; all Bandit findings suppressed with justification
- **Linting**: ruff clean, mypy clean (59 source files)

### Recent Completions (v0.8.2 audit pass)

- Fixed `FileNotFoundError`/`PermissionError` builtin-shadowing bug in `exceptions.py`
- Fixed duplicate `get_config` / `VersionTrackerError` entries in `__init__.__all__`
- Resolved all 9 mypy errors (fuzzywuzzy import-untyped, version/**init**.py misc)
- Aligned `requirements.txt` version constraints with `pyproject.toml`
- Suppressed all Bandit false-positive findings with `# nosec` + justification comments
- Removed stale `pytest.xml` artifact from source tree
- Removed redundant `print()` calls shadowing `logging.info()` in `apps/finder.py` and `apps/matcher.py`
- ~~P1~~ Deleted dead `versiontracker/version.py` (unreachable, 0% coverage)
- ~~P5~~ Removed unused `commands/` directory (215 lines, zero imports from production or tests)
- ~~P7~~ Removed all f-string-in-logging violations; `G004` ruff rule enforced
- ~~P8~~ Moved `analytics.py` and `benchmarks.py` to `versiontracker/experimental/`
- ~~P11~~ Fixed CHANGELOG dates to match actual git tag dates; moved `[Unreleased]` to top
- ~~P12~~ Wired `warn_deprecated_flag` for `--blacklist` and `--blacklist-auto-updates`
- ~~P13~~ Removed unnecessary `hasattr` guards in `__main__.py`
- Fixed `requirements.txt` / `pyproject.toml` rapidfuzz dependency discrepancy

---

## Active Work — Prioritised Fix List

> Issues are ordered by impact. Work top-to-bottom.

### 🔴 P2 — Critical: Complete the `version_legacy.py` Migration

The refactoring from `version_legacy.py` → `version/` package stalled with ~50%
complete. The `version/__init__.py` currently uses `importlib.util` to dynamically
load `version_legacy.py` at import time and manually re-exports every symbol — a
fragile pattern that breaks static analysis, IDE navigation, and test mocking.

**Remaining functions to migrate** (all still in `version_legacy.py`):

- [ ] Fuzzy matching utilities → `version/fuzzy.py`
  - `partial_ratio`, `similarity_score`, `compare_fuzzy`, `get_partial_ratio_scorer`
- [ ] Homebrew integration functions → `version/homebrew.py`
  - `get_homebrew_cask_info`, `find_matching_cask`, `check_latest_version`, `_search_homebrew_casks`
- [ ] Batch processing functions → `version/batch.py`
  - `check_outdated_apps`, `_process_app_batch`, `_create_app_batches`, `_process_single_app`
- [ ] Version info helpers → `version/utils.py`
  - `get_version_info`, `decompose_version`, `compose_version_tuple`

**Cleanup once migration is complete**:

- [ ] Replace `importlib.util` dynamic loading in `version/__init__.py` with direct imports
- [ ] Delete `version_legacy.py`
- [ ] Update all import sites that reference `version_legacy` directly
- [ ] Verify 100% of tests still pass

**Target**: v0.9.0

---

### 🔴 P3 — Critical: Complete the `app_finder.py` Migration

Mirrors the `version_legacy.py` situation. `apps/__init__.py` uses
`importlib.util` to dynamically load `app_finder.py` and wraps every function in
a thin typed shim. This is why several test mocks silently miss the real code.

- [ ] Audit remaining functions in `app_finder.py` not yet in `apps/finder.py` or `apps/matcher.py`
- [ ] Migrate `check_brew_install_candidates` and batch helpers → `apps/matcher.py`
- [ ] Migrate `get_homebrew_casks`, `get_cask_version`, `check_brew_update_candidates` → `apps/finder.py`
- [ ] Migrate rate limiter classes (duplicated in `app_finder.py` and `apps/cache.py`)
  — keep only `apps/cache.py` version
- [ ] Replace `importlib.util` dynamic loading in `apps/__init__.py` with direct imports
- [ ] Delete `app_finder.py`
- [ ] Fix the 4 skipped tests in `test_apps_new.py` whose mocks were broken by the dynamic loading pattern

**Target**: v0.9.0

---

### 🔴 P4 — Critical: Fix the 29 Skipped Tests

| File | Count | Root Cause |
|---|---|---|
| `test_apps_new.py` | 4 | Mock path targets `apps.*` but real code runs from `app_finder.py` |
| `test_end_to_end_integration.py` | 7 | Wrong import/function paths, unrealistic exit code expectations |
| `test_platform_compatibility.py` | 2 | macOS-only guards (acceptable, leave skipped) |
| `test_ui.py` | 12 | Environment-specific terminal/colour behaviour |
| `test_ui_new.py` | 1 | Environment-specific colour handling |
| `test_apps_new.py` | 3 | (counted above) |

- [ ] Fix `test_apps_new.py` skipped tests (blocked by P3 above)
- [ ] Fix `test_end_to_end_integration.py` — update mock targets to real import paths
- [ ] Fix `test_end_to_end_integration.py` — correct `SystemExit` vs return-code expectations
- [ ] Review `test_ui.py` skips — use `pytest.mark.skipif` with `isatty()` checks
- [ ] Leave the 2 non-macOS `test_platform_compatibility.py` skips as-is

---

### 🟠 P6 — High: Add Tests for Core Version Comparison

`version/comparator.py` (7.3% coverage) and `version/parser.py` (8.3% coverage)
are the heart of the tool. Any regression goes undetected.

- [ ] Add parameterised tests for `compare_versions` edge cases:
  - `1.0` vs `1.0.0` (trailing zeros)
  - `2.0-beta` vs `2.0` (prerelease < release)
  - `1.2.3+build` vs `1.2.3` (build metadata)
  - Date-based versions: `2024.1` vs `2024.2`
  - Single-component: `5` vs `6`
  - Non-numeric suffixes: `1.0a` vs `1.0b`
  - Mixed: `1.2.3` vs `(1, 2, 3)` tuple input
- [ ] Add parameterised tests for `parse_version` covering all `VERSION_PATTERNS`
- [ ] Add tests for `version/homebrew.py` (currently 9.3%)
- [ ] Reach ≥ 60% coverage on `version/comparator.py` and `version/parser.py`

---

### 🟡 P9 — Medium: Split `Config` Class

`Config` in `config.py` has 34 methods across 941 lines handling: brew path
detection, YAML file loading, 4 categories of env-var loading, validation, saving,
blocklist management, and property accessors. Single-responsibility principle is
violated.

- [ ] Extract `ConfigLoader` — handles file parsing and env-var ingestion, returns a plain dict
- [ ] Keep `Config` as a validated data container with `get`/`set` and the property accessors
- [ ] Keep `ConfigValidator` where it is (already a separate class)
- [ ] Ensure all 22 import sites still work via `from versiontracker.config import Config, get_config`

---

### 🟡 P10 — Medium: Wire Async Homebrew into the CLI

`async_homebrew.py` (401 lines) and `async_network.py` (346 lines) are implemented
and tested, but the actual CLI still uses synchronous subprocess calls. The TODO
notes a 5x+ speedup is available.

- [ ] Confirm `async_homebrew_prototype.py` feature-flag mechanism works (`VERSIONTRACKER_ASYNC_BREW=1`)
- [ ] Update `brew_handlers.py` → `_get_homebrew_casks` to call async path when flag is set
- [ ] Update `check_brew_install_candidates` in `app_finder.py` similarly
- [ ] Add integration test comparing sync vs async results for parity
- [ ] Document the flag in README and `sample_config.yaml`
- [ ] Promote to default path once parity test passes (v0.9.x)

---

### 🟢 P14 — Low: `handle_setup_logging` Should Not Return on Error

Currently `handle_setup_logging` returns exit code `1` if `logging.basicConfig`
fails — but callers in `versiontracker_main` ignore this return value entirely,
meaning a logging failure silently continues.

- [ ] Change `handle_setup_logging` to return `None` (it's a side-effect function, not an action)
- [ ] Update the call site in `versiontracker_main` to not assign the return value
- [ ] Or: make it raise on failure so the caller can decide

---

## Homebrew Release Preparation (v0.8.2 → v0.9.0)

### Phase 1: Pre-Release Validation

- [ ] Confirm version tag exists: `git fetch --tags && git tag -l v0.8.2`
- [ ] Ensure CHANGELOG has correct dated entry for this version
- [ ] Run full test suite locally: `pytest`
- [ ] Validate packaging: `python -m build && twine check dist/*`

### Phase 2: Formula Creation

- [ ] Download canonical GitHub tag archive
- [ ] Compute SHA256 checksum
- [ ] Update `versiontracker.rb` formula with new version/checksum
- [ ] Run: `brew audit --new-formula --strict ./versiontracker.rb`

### Phase 3: Tap Repository

- [ ] Update `homebrew-versiontracker` repository
- [ ] Test tap: `brew tap docdyhr/versiontracker && brew install versiontracker`

---

## Future Enhancements

### Extended Package Manager Support

- [ ] MacPorts integration
- [ ] `mas-cli` for App Store applications
- [ ] Unified interface for multiple package managers

### Platform Compatibility

- [ ] Apple Silicon vs Intel Homebrew path handling improvements
- [ ] macOS version compatibility matrix (Monterey through Sequoia)

### GUI / Web Interface (Long-term Vision)

- [ ] FastAPI-based web interface
- [ ] Real-time update monitoring dashboard
- [ ] Native SwiftUI macOS app (see `docs/future_roadmap.md`)

### Security Features

- [ ] Vulnerability database integration (NVD, CVE)
- [ ] Security scoring for installed applications
- [ ] Alert on applications with known CVEs

### Advanced ML Features (Optional — `pip install macversiontracker[ml]`)

- [ ] Enhance ML-powered recommendations with user feedback loop
- [ ] Usage pattern analysis for personalised suggestions
- [ ] Confidence scoring improvements for app-cask matching

---

## Long-term Vision

For detailed strategic planning see `docs/future_roadmap.md`.

---

## Contributing

### Good First Issues

- Fix `handle_setup_logging` return behavior (P14)
- Add parameterised tests for version comparison edge cases (P6)

### Advanced Contributions

- MacPorts integration
- Async Homebrew promotion to default path (P10)
- Complete `version_legacy.py` migration (P2)
- Complete `app_finder.py` migration (P3)

---

**Last Updated**: February 2026
**Maintainer**: @docdyhr
