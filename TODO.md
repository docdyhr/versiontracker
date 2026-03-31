# VersionTracker TODO

## Current Status (March 2026)

### Project Health

- **Version**: 0.9.0 (beta — stabilisation in progress)
- **Tests**: 2,173 collected, 16 skipped
- **Coverage**: ~78% overall
- **CI/CD**: All workflows passing on master (all green)
- **Python Support**: 3.12+ (with 3.13 compatibility)
- **Security**: 0 dependabot alerts, 0 secret scanning alerts, 0 CodeQL findings
- **Linting**: ruff clean, mypy clean
- **Open Issues**: 0
- **Open PRs**: 0

### Recent Completions

- ~~PR #115~~ **CI badges + mypy** — test matrix badges, mypy consistency fix, CodeQL concurrency
- ~~PR #114~~ **Fuzzy matching + CI consolidation** — fallback fix, pipeline cleanup
- ~~PR #113~~ **Audit improvements** — dead code removal, plugin CLI, test coverage
- ~~PR #108~~ **CodeQL security fixes** — 3 high-severity URL sanitization alerts resolved;
  12 medium-severity missing-workflow-permissions alerts resolved
- ~~PR #106~~ **Dependency update** — `actions/upload-artifact` v6→v7, `actions/download-artifact` v7→v8

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
> Work P0→P5 in order. Do not start P3/P4 before P0/P1 are stable.

### 🔴 P0 — Homebrew command execution contract

**Problem**: `get_all_homebrew_casks()` builds a command using shell substitution
(`$(ls $(brew --repository)/...)`), but `run_command` executes with `shell=False` via
`shlex.split`. The substitution is never evaluated.
Also: `is_homebrew_available()` uses bare `"brew"` instead of the configured path.

**Files**: `versiontracker/homebrew.py`, `tests/test_homebrew_advanced.py`

- [ ] Replace shell-substitution command with `brew info --json=v2 --eval-all --cask`
- [ ] Use `run_command_secure()` (argv list) in `get_all_homebrew_casks()`
- [ ] Fix `is_homebrew_available()` to use configured brew path
- [ ] Update tests to assert exact command/argv shape

**Verify**: `pytest -q tests/test_homebrew_advanced.py tests/test_homebrew.py`

---

### 🔴 P1 — Progress flag canonicalisation

**Problem**: `--no-progress` is stored in inconsistent config locations.
`setup_handlers.py` writes to `_config["ui"]["show_progress"]` but
`Config.show_progress` is derived from `_config["no_progress"]` — the write
has no effect. `outdated_handlers.py` calls `config.set("show_progress", False)`
which is also a dead key.

**Files**: `versiontracker/handlers/setup_handlers.py`,
`versiontracker/handlers/outdated_handlers.py`

- [ ] `setup_handlers.py`: replace `_config["ui"]["show_progress"]` mutation with `config.set("no_progress", True)`
- [ ] `setup_handlers.py`: replace other `_config[...]` mutations with `config.set()` calls
- [ ] `outdated_handlers.py`: remove dead `config.set("show_progress", False)` call
- [ ] Regression tests for `--no-progress` across `--apps` and `--outdated`

**Verify**: `pytest -q tests/handlers/test_setup_handlers.py tests/test_outdated_handlers.py tests/test_cli.py`

---

### 🟡 P2 — CLI/handler option drift

**Problem**: Some handler branches access `options` attributes not backed by the
parser (e.g., `options.output_file`, `options.notify`). Currently guarded by
`hasattr`, so they don't crash, but are dead paths.

**Files**: `versiontracker/cli.py`, `versiontracker/handlers/outdated_handlers.py`

- [ ] Audit every `options.<name>` in handlers and `__main__.py`
- [ ] For each ungated access: add parser argument or remove the branch
- [ ] For each `hasattr`-gated dead path: evaluate adding to CLI or removing
- [ ] Update help text to reflect actual CLI surface

**Verify**: `pytest -q tests/test_cli.py tests/test_main.py tests/test_outdated_handlers.py`

---

### 🟡 P3 — Import-time side effects (defer until P0/P1 stable)

**Problem**: Config singleton creation at import time triggers Homebrew detection
and env inspection before CLI args are parsed.

**Files**: `versiontracker/config.py`, `versiontracker/__main__.py`

- [ ] Delay expensive config initialisation until CLI startup
- [ ] Minimise subprocess/filesystem work at import time

**Verify**: `pytest -q tests/test_config.py tests/test_main.py tests/test_integration.py`

---

### 🟡 P4 — Exception narrowing

**Problem**: Broad `except Exception` blocks in core modules mask root causes.

**Files** (start here): `versiontracker/homebrew.py`, `versiontracker/apps/finder.py`,
`versiontracker/__main__.py`, `versiontracker/handlers/setup_handlers.py`,
`versiontracker/handlers/outdated_handlers.py`

- [ ] Replace broad `except Exception` with specific exception types where feasible
- [ ] Preserve diagnostic detail in logs
- [ ] Cover expected failure classes in tests

**Verify**: `pytest -q tests/test_homebrew_advanced.py tests/test_outdated_handlers.py tests/test_integration.py`

---

### 🟢 P5 — Documentation alignment

**Problem**: README presents project as more mature than current code supports.

- [ ] Replace inflated maturity language with accurate beta/stabilisation wording
- [ ] Ensure CHANGELOG reflects any user-visible behaviour changes from P0–P4
- [ ] Remove `PROJECT_REVIEW.md` from repo root after stabilisation completes

---

### 🟢 P16 — Remaining 16 skipped tests (low priority)

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
