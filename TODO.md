# VersionTracker TODO

## Current Status (June 2026)

### Project Health

- **Version**: 1.0.1 (stable)
- **Tests**: 2,477 passing, 16 skipped
- **Coverage**: 86% overall (target: 85%) ✅
- **CI/CD**: All workflows passing on master (all green)
- **Python Support**: 3.12+ (with 3.13 compatibility)
- **Security**: 0 dependabot alerts, 0 secret scanning alerts, 0 CodeQL findings
- **Linting**: ruff clean, mypy clean
- **Open Issues**: 0
- **Open PRs**: 0

### Recent Completions

- ~~PR #145~~ **Dependency hygiene** — declared `termcolor` core dep, synced all
  requirements files with `pyproject.toml`, fixed mypy type signatures in `ui.py`
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

### ✅ P4 — Exception narrowing — **done in PR #185 + PR #194**

- [x] `homebrew.py` `get_homebrew_path`: `OSError` + re-raise `HomebrewError`
- [x] `finder.py` async availability check: `AttributeError + RuntimeError`
- [x] `finder.py` `get_applications` parsing: `KeyError + IndexError + TypeError`
- [x] `outdated_handlers.py` filter fallback: `ValueError + TypeError + AttributeError`
- [x] `setup_handlers.py`: narrowed to `(OSError, ValueError, ConfigError)`,
  `(AttributeError, ValueError, ConfigError)`, `(ValueError, TypeError, OSError)`
- [x] `config_handlers.py`: narrowed to `(OSError, PermissionError, ValueError)`
- [x] `app_handlers.py`: narrowed to `(OSError, PermissionError, ValueError,
  ApplicationError, HomebrewError)`
- [x] `filter_handlers.py`: narrowed to `(OSError, ValueError, AttributeError, KeyError)`
- [x] `__main__.py` line 313: broad `except Exception` retained as justified
  top-level CLI boundary (documents all propagated errors to the user)

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
| `test_ml_module.py` | 13 | ML deps (numpy, scikit-learn) not installed in default venv | Leave as-is; install `macversiontracker[ml]` to run |
| `test_platform_compatibility.py` | 2 | macOS-only and non-macOS platform guards | Leave as-is |
| `test_ui_new.py` | 1 | Environment-specific colour handling (non-TTY) | Leave as-is |

All skip decorators already carry a `reason=` string; no additional inline comments needed.

---

## Homebrew Release (v0.9.0) — Complete

- [x] Bump version to 0.9.0 in `__init__.py` and `pyproject.toml`
- [x] Update CHANGELOG.md with v0.9.0 entry
- [x] Formula created at `docdyhr/homebrew-tap` with verified SHA256
- [x] `brew install docdyhr/tap/macversiontracker` tested and working
- [x] Legacy root `versiontracker.rb` removed (superseded by tap formula)
- [x] `release-homebrew.yml` workflow updated to push to tap repo

---

## Unmanaged Application Audit Feature (in progress)

> Goal: `versiontracker audit` — identify user-facing apps that are not
> App-Store-managed, not Homebrew-owned, have no confirmed auto-update path,
> and aren't blocklisted, with full evidence per signal. Full spec at
> `.claude/plans/versiontracker-unmanaged-apps-handoff.md` (gitignored).

- [x] **Phase 1 — Models + identity-preserving discovery** —
  `versiontracker/audit/{models,discovery}.py`, 59 new tests (94% coverage on
  `discovery.py`, 100% on `models.py`). Filesystem-walk-based discovery (not a
  `system_profiler`-JSON filter) with `Info.plist` + `_MASReceipt/receipt`
  probes; validated live against this machine's `/Applications` (140 apps, 36
  correctly classified App Store via the receipt signal alone).
- [x] **Phase 2 — Exact Homebrew ownership + blocklist identity** —
  `versiontracker/audit/{homebrew,blocklist}.py`, 46 new tests (95.89%
  coverage on `blocklist.py`, 96.84% on `homebrew.py`). Ownership joins
  discovered bundles to `brew info --json=v2 --cask --installed` app-artifact
  `target` paths (zero fuzzy matching); blocklist matches canonical
  path/bundle ID/Homebrew token/display name in that priority order. Fixed
  two real bugs found during design review before they shipped: a
  `run_command_secure` exception-handling gap that could crash the whole
  audit on a missing `brew` binary instead of degrading to `unknown`, and a
  cwd-dependent blocklist path-matching bug. Validated live against this
  machine's `/Applications`: 45 apps correctly resolved `managed` with
  correct cask tokens (e.g. `brave-browser`, `google-chrome`, `dropbox`), 94
  `not_available`, 0 `unknown`.
- [x] **Phase 3 — Local auto-update evidence** —
  `versiontracker/audit/auto_update.py`, 65 new tests (97.49% coverage).
  Five independent local probes (Sparkle framework + `SUEnableAutomaticChecks`,
  Squirrel framework + ShipIt, electron-updater's `app-update.yml`, Mozilla's
  `updater.app`, and vendor LaunchAgents/Daemons tied to a bundle ID or a
  small curated vendor table) aggregate into one evidence result; a Homebrew
  cask `auto_updates` flag supplements only when local probes found nothing.
  Design review independently verified every claim against this machine's
  real files, installed apps, and live `launchctl`/permission behaviour, and
  found 6 real gaps before they shipped (unstable Sparkle framework version
  letters, a Logi Options+ filename/Label mismatch, a root-owned/unreadable
  Teams updater daemon, empty-stub Keystone plists `launchctl` confirms
  aren't loaded, a Dropbox bundle-ID mismatch, a missing GPGTools entry).
  The live sanity pass itself then caught a 7th, real bug — `plistlib.load()`
  can raise `xml.parsers.expat.ExpatError` on a genuinely malformed plist
  (confirmed via an actual corrupt LaunchAgent on this machine), which
  neither this module's nor Phase 1's `discovery.py::_read_info_plist`
  excepted; both fixed to catch broadly, with regression tests. Validated
  live against this machine's `/Applications`: 51 `capable`, 3 `enabled`, 85
  `none_detected` — Cyberduck's real `SUEnableAutomaticChecks=false` resolves
  exactly to the "explicitly disabled → capable, not enabled" exit
  criterion; Dash and ChatGPT Atlas correctly resolve `enabled`; Teams and
  Signal correctly aggregate multiple simultaneous mechanisms; ClamXAV's
  keyword guard correctly includes its real `.HelperToolUpdater` daemon
  while excluding non-updater siblings sharing the same bundle-id prefix;
  Zoom (no Sparkle/Squirrel, no Homebrew app artifact) resolves via its real
  `us.zoom.updater.login.check` LaunchAgent alone.
- [x] **Phase 4 — CLI wiring, terminal renderer, JSON/YAML/CSV export** —
  `versiontracker/audit/{service,rendering}.py` and
  `versiontracker/handlers/audit_handlers.py` (all 100% coverage), plus the
  `--audit`/`--all`/`--status`/`--explain` flags in `cli.py` and dispatch in
  `__main__.py`. 63 new tests across `tests/audit/{test_service,
  test_rendering}.py`, `tests/handlers/test_audit_handlers.py`, and additive
  coverage in `test_cli.py`/`test_main.py`/`test_cli_workflows.py`. This is
  the first phase with a user-visible surface — `versiontracker audit` is now
  a real, runnable command. Design review caught several bugs before they
  shipped: a classification condition that would have wrongly excluded a
  future Homebrew `available` result from the attention view, `run_audit()`
  never actually fetching real `system_profiler` data (would have silently
  degraded App Store detection to medium-confidence on every real run), the
  Homebrew-before-auto-update pipeline-order dependency, and a deprecation
  warning's console hint leaking into `--export json` stdout. The live
  sanity pass then caught a real, would-have-shipped bug of its own —
  `--status managed` returned the correct summary counts but zero rows,
  because `render_terminal()`'s "Managed" section was gated behind `--all`
  even though `filter_result()` had already scoped `result.applications`
  down to exactly the requested bucket; fixed by making section visibility
  depend only on what's actually in the (already-filtered) result, matching
  the function's own "never re-applies filtering" contract. Validated live
  against this machine's real `/Applications` (152 apps: 48 attention, 0
  unknown, 104 managed) — `--audit`, `--all --explain`, `--export json`
  (byte-clean, schema-valid), `--status managed`/`--status unknown` all
  correct, and a simulated Homebrew CLI failure correctly routes every
  application to the `unknown` bucket with a populated error rather than a
  false negative.
- [x] **Phase 5 — Regression tests and documentation** —
  `tests/audit/test_golden_fixture.py` (new): one `run_audit()` call over 7
  synthetic apps proving the resolvers compose correctly (App Store,
  Homebrew, auto-update, blocklist, and multiple simultaneous signals each
  independently reaching `managed`), plus an isolated test proving a
  Homebrew CLI failure produces `unknown`, never a silently-flipped
  negative. CLI-level flag-output tests added to
  `tests/integration/test_cli_workflows.py` proving `--all`/`--status`/
  `--explain`/`--export json` each change observable `versiontracker_main()`
  stdout. Targeted failure-injection tests added for two confirmed gaps: a
  real `PermissionError` (not the existing malformed-content case) on a
  blocklist path entry (`test_blocklist.py`) and on both LaunchAgent-plist
  reads and directory listing (`test_auto_update.py`), the latter isolated
  from the existing blanket-failure test so a *single* failing probe can't
  be silently absorbed into `none_detected`. 12 new tests total, full suite
  2715→2727 passed, 16 skipped.

  Also opportunistic fixes found along the way: replaced
  `tests/test_matcher_coverage.py::test_strict_mode_skips_matched`, which
  mocked `partial_ratio` to always match — making it structurally
  impossible to ever observe a `strict_mode`-specific effect — with a test
  that honestly pins the real current behavior (see the known-bug note
  below). Fixed a real, live, silently-shipping bug found during design
  review: `versiontracker/menubar_app.py` and
  `versiontracker/handlers/macos_handlers.py` both hard-coded the
  nonexistent `--outdated` flag (the real flag is `--check-outdated`) —
  every menubar "Check for Updates"/"Show Outdated Apps" click and every
  `--install-service` scheduled background check has been failing silently
  since introduction. Fixed both, added `tests/test_menubar_app.py` (zero
  prior coverage) validating every menu command against the real argparse
  parser so a future flag rename can't reintroduce this silently. Also
  corrected the same stale `--outdated` in README.md (5 lines) and
  `docs/AUTO_UPDATE_MANAGEMENT.md`, and added the missing audit-feature
  documentation to `docs/USAGE.md` and `docs/ARCHITECTURE.md` (Phase 4 only
  updated README/CHANGELOG/TODO).
- [x] Phase 6 (NLP portion) — `versiontracker --ask "<query>"` wires
  `versiontracker.ai`'s previously-unused `CommandInterpreter` into a real CLI
  command (`versiontracker/handlers/ai_handlers.py::handle_ask()`), routing
  recognized intents to the existing `handle_audit`/`handle_list_apps`/
  `handle_brew_recommendations`/`handle_outdated_check` handlers -- never
  reimplementing classification logic itself, per the spec's guardrail. Added
  a new `audit_apps` NLP intent distinct from `check_updates` (materially
  different evidence: no-confirmed-auto-update-path vs. Homebrew-known-outdated).
  Out-of-scope/low-confidence queries always print a clear message rather than
  guessing. 20 new tests (`tests/test_ai_module.py`, new
  `tests/handlers/test_ai_handlers.py`, `tests/integration/test_cli_workflows.py`);
  full suite 2727→2747 passed, 16 skipped.
- [ ] Phase 6 (Swift GUI portion) — Swift bridge consumes versioned JSON,
  "Needs attention" view, menubar/service command updates (deferred; no
  Xcode project exists yet in this repo, see "GUI / Web Interface" below)

### Known, confirmed, separate bugs found during audit-feature work (not fixed — out of scope)

- **`--strict-recommend` is non-functional as documented.**
  `versiontracker/apps/matcher.py:filter_out_brews()`'s `candidates` list is
  built but never returned or used, and both the `strict_mode=True` and
  `False` branches `break` out of the match loop identically — so
  `strict_mode` currently has zero effect on the function's return value.
  README's own description ("find applications that can be newly installed
  with Homebrew, not already in cask repository") does not match reality.
  Fixing the actual logic needs a product decision this audit work doesn't
  make (`candidates` is dead in *both* modes, so there's no "restore
  intended behavior" to fall back to) — tracked here, not fixed.
- **`HomebrewStatus.AVAILABLE` is a phantom status.** No resolver in
  `versiontracker/audit/homebrew.py` ever produces it — cask availability
  (a matching cask exists but doesn't own this installed bundle) was
  deliberately deferred as a later enrichment per the Phase 2 spec. The
  enum member, and `classify_record()`'s defensive handling of it, exist
  for when this enrichment is eventually implemented.

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
- Coverage push toward 85% (currently ~83.5%)

---

**Last Updated**: May 2026
**Maintainer**: @docdyhr
