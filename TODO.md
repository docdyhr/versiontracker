# VersionTracker TODO

## Current Status (March 2026)

### Project Health

- **Version**: 0.9.0
- **Tests**: 1,993 collected, 16 skipped
- **Coverage**: ~78% overall
- **CI/CD**: All workflows passing on master (all green)
- **Python Support**: 3.12+ (with 3.13 compatibility)
- **Security**: 0 dependabot alerts, 0 secret scanning alerts, 0 CodeQL findings
- **Linting**: ruff clean, mypy clean
- **Open Issues**: 0
- **Open PRs**: 0

### Recent Completions

- ~~PR #108~~ **CodeQL security fixes** — 3 high-severity URL sanitization
  alerts resolved in `verify_badges.py` (strict scheme+hostname allowlist);
  12 medium-severity missing-workflow-permissions alerts resolved across
  `ci.yml`, `lint.yml`, `performance.yml`, `release.yml`, `security.yml`
  (job-level `permissions:` blocks added to all jobs)
- ~~PR #106~~ **Dependency update** — `actions/upload-artifact` v6→v7,
  `actions/download-artifact` v7→v8 across all workflows

### Previous Completions (v0.9.0)

- ~~P10~~ **Async Homebrew wiring** — `check_brew_install_candidates()` and
  `check_brew_update_candidates()` now route through async Homebrew API by
  default; deadlock bug in `async_check_brew_update_candidates` fixed;
  automatic sync fallback on error; `get_casks_with_auto_updates()` deferred
  to v0.10.x (no async equivalent yet)
- ~~P17~~ **Test coverage push** — 77 new handler/utility tests; coverage
  61% → 78%; non-public modules excluded from metrics
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

### 🟢 P16 — Low: Remaining 16 Skipped Tests

| File | Count | Root Cause | Action |
|---|---|---|---|
| `test_ui.py` | 12 | Environment-specific terminal/colour | Leave as-is |
| `test_platform_compatibility.py` | 2 | macOS-only / non-macOS guards | Leave as-is |
| `test_ui_new.py` | 1 | Environment-specific colour handling | Leave as-is |
| `test_apps_extra.py` | 1 | Complex mocking requirements | Consider fixing |

All skips are environment-specific or CI-specific — no action needed for most.

---

## Homebrew Release (v0.9.0) — Complete

- [x] Bump version to 0.9.0 in `__init__.py` and `pyproject.toml`
- [x] Update CHANGELOG.md with v0.9.0 entry
- [x] Formula created at `docdyhr/homebrew-tap` with verified SHA256
- [x] `brew install docdyhr/tap/macversiontracker` tested and working
- [x] Legacy root `versiontracker.rb` removed (superseded by tap formula)
- [x] `release-homebrew.yml` workflow updated to push to tap repo

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

- Improve `test_ui.py` skip conditions with `isatty()` checks
- Add integration tests for `app_handlers.py`

### Advanced Contributions

- MacPorts integration
- Async wiring for `get_casks_with_auto_updates()` (deferred from P10)

---

**Last Updated**: March 2026
**Maintainer**: @docdyhr
