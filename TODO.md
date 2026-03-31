# VersionTracker TODO

## Current Status (March 2026)

### Project Health

- **Version**: 0.9.0 (beta — stabilisation in progress)
- **Tests**: 2,158 passing, 15 skipped
- **Coverage**: ~78% overall
- **CI/CD**: All workflows passing on master (all green)
- **Python Support**: 3.12+ (with 3.13 compatibility)
- **Security**: 0 dependabot alerts, 0 secret scanning alerts, 0 CodeQL findings
- **Linting**: ruff clean, mypy clean
- **Open Issues**: 0
- **Open PRs**: 0

### Recent Completions

- ~~PR #118~~ **Dependency update** — `codecov/codecov-action` v5→v6
- ~~PR #117~~ **Stabilisation P0–P5** — Homebrew cmd fix, progress config canonicalisation,
  CLI/handler drift, exception narrowing, README/TODO alignment
- ~~PR #115~~ **CI badges + mypy** — test matrix badges, mypy consistency fix, CodeQL concurrency
- ~~PR #114~~ **Fuzzy matching + CI consolidation** — fallback fix, pipeline cleanup
- ~~PR #113~~ **Audit improvements** — dead code removal, plugin CLI, test coverage

### Previous Completions (v0.9.0)

- ~~P10~~ **Async Homebrew wiring** — `check_brew_install_candidates()` and
  `check_brew_update_candidates()` now route through async Homebrew API by
  default; deadlock bug in `async_check_brew_update_candidates` fixed
- ~~P17~~ **Test coverage push** — 77 new handler/utility tests; coverage
  61% → 78%; non-public modules excluded from metrics
- ~~P9~~ **Config split** — extracted `ConfigLoader` class with static methods
  for file I/O, env-var loading, brew detection, save, and generate_default_config
- ~~P15~~ **Test coverage improvement** — 122 new tests (matcher 98%, finder 78%, config 68%)
- ~~P1–P8, P11–P14~~ All completed in v0.8.2 (module migration, dead code removal, security fixes)

---

## Active Work — Stabilisation Cycle (v0.9.x → v1.0)

> Objective: make the project operationally consistent before adding features.
> All P0–P5 complete. Stabilisation cycle done — ready for v1.0.

### ✅ P0 — Homebrew command execution contract — **done in PR #117**

- [x] Replace shell-substitution command with `brew info --json=v2 --eval-all --cask`
- [x] Use `run_command_secure()` (argv list) in `get_all_homebrew_casks()`
- [x] Fix `is_homebrew_available()` to use configured brew path
- [x] Update tests to assert exact command/argv shape

---

### ✅ P1 — Progress flag canonicalisation — **done in PR #117**

- [x] `setup_handlers.py`: replace `_config["ui"]["show_progress"]` mutation with `config.set("no_progress", True)`
- [x] `setup_handlers.py`: replace other `_config[...]` mutations with `config.set()` calls
- [x] `outdated_handlers.py`: remove dead `config.set("show_progress", False)` call
- [x] Integration tests for `--no-progress` (PR #122)

---

### ✅ P2 — CLI/handler option drift — **done in PR #117**

- [x] Audit every `options.<name>` in handlers and `__main__.py`
- [x] Add `--output-file` to Export Options group in `cli.py`
- [x] `hasattr`-gated dead paths (`options.notify`) left as-is — safe, low risk
- [x] Integration test for `--export --output-file` (PR #122)

---

### ✅ P3 — Import-time side effects — **done in PR #121**

- [x] Delay expensive config initialisation until CLI startup (`get_config()` lazy init)
- [x] `Config()` singleton no longer created at import time — eliminates `brew --version` subprocess on import
- [x] `conftest.py` `reset_config` fixture now correctly resets `_config_instance`

---

### ✅ P4 — Exception narrowing — **partially done in PR #117**

- [x] `homebrew.py` `get_homebrew_path`: `OSError` + re-raise `HomebrewError`
- [x] `finder.py` async availability check: `AttributeError + RuntimeError`
- [x] `finder.py` `get_applications` parsing: `KeyError + IndexError + TypeError`
- [x] `outdated_handlers.py` filter fallback: `ValueError + TypeError + AttributeError`
- [ ] Remaining broad catches in `__main__.py` and deeper handler paths (next cycle)

---

### ✅ P5 — Documentation alignment — **done in PR #117**

- [x] Replace "Production-Ready" badge/heading with "Beta — Stabilising"
- [x] Update test count (1,885 → 2,173) and coverage claim (61% → 78%)
- [x] Rewrite TODO.md Active Work section with P0–P5 issue definitions
- [x] Update CHANGELOG.md with user-visible behaviour changes (PR #121)
- [x] Remove `PROJECT_REVIEW.md` from repo root (PR #121)

---

### 🟢 P16 — Remaining skipped tests (low priority)

| File | Count | Root Cause | Action |
|---|---|---|---|
| `test_ui.py` | 12 | Environment-specific terminal/colour | Leave as-is |
| `test_platform_compatibility.py` | 2 | macOS-only guards | Leave as-is |
| `test_ui_new.py` | 1 | Environment-specific colour | Leave as-is |
| `test_apps_extra.py` | 1 | Complex mocking requirements | Consider fixing |

---

## Homebrew Release (v0.9.0) — Complete

- [x] Bump version to 0.9.0 in `__init__.py` and `pyproject.toml`
- [x] Update CHANGELOG.md with v0.9.0 entry
- [x] Formula created at `docdyhr/homebrew-tap` with verified SHA256
- [x] `brew install docdyhr/tap/macversiontracker` tested and working
- [x] Legacy root `versiontracker.rb` removed (superseded by tap formula)
- [x] `release-homebrew.yml` workflow updated to push to tap repo

---

## Future Enhancements (post-stabilisation)

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
- [ ] Async wiring for `get_casks_with_auto_updates()` (deferred from P10)

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
- P3: Lazy config initialisation

---

**Last Updated**: March 2026
**Maintainer**: @docdyhr
