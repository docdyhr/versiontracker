# VersionTracker TODO

## Current Status (February 2026)

### Project Health

- **Version**: 0.9.0
- **Tests**: 1,885 passing, 16 skipped
- **Coverage**: ~61% overall (up from 58.84%)
- **CI/CD**: All 11 workflows passing on master (all green)
- **Python Support**: 3.12+ (with 3.13 compatibility)
- **Security**: 0 dependabot alerts, 0 secret scanning alerts; CodeQL alerts resolved
- **Linting**: ruff clean, mypy clean
- **Open Issues**: 0
- **Open PRs**: 0

### Recent Completions (v0.9.0)

- ~~P9~~ **Config split** — extracted `ConfigLoader` class with static methods
  for file I/O, env-var loading, brew detection, save, and
  generate_default_config; `Config` simplified to data container + accessors
- ~~P15~~ **Test coverage improvement** — 122 new tests:
  - `apps/matcher.py`: 54% → 98%
  - `apps/finder.py`: 68% → 78%
  - `config.py`: 43% → 68%
- ~~P1–P8, P11–P14~~ All completed in v0.8.2 (module migration, dead code removal, security fixes)

---

## Active Work — Prioritised Fix List

> Issues are ordered by impact. Work top-to-bottom.

### 🟡 P10 — Medium: Wire Async Homebrew into the CLI

`async_homebrew.py` (401 lines) and `async_network.py` (346 lines) are implemented
and tested, but the actual CLI still uses synchronous subprocess calls. The TODO
notes a 5x+ speedup is available.

- [ ] Confirm `async_homebrew_prototype.py` feature-flag mechanism works (`VERSIONTRACKER_ASYNC_BREW=1`)
- [ ] Update `brew_handlers.py` → `_get_homebrew_casks` to call async path when flag is set
- [ ] Update `check_brew_install_candidates` in `apps/finder.py` similarly
- [ ] Add integration test comparing sync vs async results for parity
- [ ] Document the flag in README and `sample_config.yaml`
- [ ] Promote to default path once parity test passes (v0.10.x)

---

### 🟡 P17 — Medium: Continue Test Coverage Push to 70%

Current: ~61% overall. Target: 70%.

| Module | Coverage | Priority |
|---|---|---|
| `handlers/*.py` | 0% (most) | High — CLI handlers need integration tests |
| `utils.py` | 13% | Medium — utility functions |
| `apps/finder.py` | 78% | Low — close to target |

Key targets:

- [ ] Add handler integration tests for `brew_handlers.py` and `app_handlers.py`
- [ ] Add tests for `utils.py` core functions
- [ ] Push `apps/finder.py` from 78% to 85%

---

### 🟢 P16 — Low: Remaining 16 Skipped Tests

| File | Count | Root Cause | Action |
|---|---|---|---|
| `test_ui.py` | 12 | Environment-specific terminal/colour | Leave as-is |
| `test_platform_compatibility.py` | 2 | macOS-only / non-macOS guards | Leave as-is |
| `test_ui_new.py` | 1 | Environment-specific colour handling | Leave as-is |
| `test_apps_extra.py` | 1 | Complex mocking requirements | Consider fixing |

All skips are environment-specific or CI-specific — no action needed for most.

---

## Homebrew Release Preparation (v0.9.0)

### Phase 1: Pre-Release Validation

- [x] Bump version to 0.9.0 in `__init__.py` and `pyproject.toml`
- [x] Update CHANGELOG.md with v0.9.0 entry
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

- Add handler integration tests for `brew_handlers.py` (P17)
- Improve `test_ui.py` skip conditions with `isatty()` checks

### Advanced Contributions

- MacPorts integration
- Async Homebrew promotion to default path (P10)

---

**Last Updated**: February 2026
**Maintainer**: @docdyhr
