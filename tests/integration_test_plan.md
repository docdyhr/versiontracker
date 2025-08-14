# Integration Test Plan

File: integration_test_plan.md  
Scope: End-to-end and high-fidelity integration testing for VersionTracker  
Last Updated: {{planned_update}} (initial draft – August 2025)

---

## 1. Purpose

This plan defines the integration testing strategy to complement the existing heavily mocked
unit test suite (≈10–11% line coverage). The integration layer will validate real multi-module
coordination, configuration precedence, caching behavior, CLI orchestration, and user-visible flows.

Goals:

1. Validate critical user workflows (CLI → handlers → domain logic → output).
2. Exercise realistic combinations of caching, network abstraction, and filesystem interactions.
3. Provide confidence for refactors (async Homebrew operations, blocklist migration,
   performance improvements).
4. Establish meaningful coverage expansion (target: raise overall to ≈25–30% with emphasis on
   branch/behavioral coverage rather than raw lines).

Non-goals:

- Network calls to live Homebrew endpoints (always mocked or served via in-process mock layer).
- GUI/menubar rendering validation (remain covered by separate focused tests).
- Load/performance stress benchmarking (handled by benchmark suite).

---

## 2. Test Environment

Component | Strategy
--------- | --------
Python Version | 3.13 (as per project baseline)
Platform | macOS primary; Linux CI compatibility subset (mocking platform-specific paths)
Isolation | Temporary directories (pytest tmp_path), ephemeral YAML config
Config Sources | Controlled layering: file → env vars → CLI args
Caching | Use real disk cache directory under tmp_path; clear between scenarios unless explicitly testing persistence
Concurrency | Real ThreadPoolExecutor usage unless test isolates fallback behavior
Async Layer | Feature-flagged when async Homebrew prototype lands (e.g. `VERSIONTRACKER_ASYNC_BREW=1`)
Randomness | None (deterministic inputs)
External Commands | `brew` fully mocked (command interceptor + fixture returns deterministic stdout/stderr)

---

## 3. Key Integration Axes

Axis | Coverage Intent
---- | ---------------
Application Discovery | System profiler JSON ingestion → parsing → filtering
Recommendation Flow | Non-brew apps matched to brew candidates (fuzzy + enhanced matching toggles)
Outdated Flow | Version comparison (stable, prerelease, malformed, build metadata)
Blocklist / Legacy Blacklist | Dual-flag behavior, conflict resolution, deprecation warnings
Auto-Update Management | Blacklist/blocklist augmentation + uninstall safety confirmations
Caching Behavior | Warm vs cold reads; invalidation & expiration pathways
Configuration Precedence | File vs env vs CLI overrides (e.g., similarity threshold, rate limit)
Export | JSON + CSV integrity (schema, ordering, encoding)
Error Handling | Simulated subprocess failure, malformed version strings, empty data, timeouts
Progress / UI Degradation | No-color + no-progress flags; fallback when dependencies disabled
Performance Flags | `--profile` basic integration (ensuring report generation path not crashing)
Adaptive Rate Limiting | Behavior bypassed vs enabled (baseline output / logs presence)
Future Async Layer | Parity tests ensuring identical observable output when async flag enabled

---

## 4. Planned Integration Test Suites

Suite ID | Title | Status | Description
-------- | ----- | ------ | -----------
INT-001 | Discovery Basic | Planned | Validate raw application enumeration + formatting
INT-002 | Discovery With Blocklist | Planned | Apply `--blocklist` and legacy `--blacklist` parity
INT-003 | Recommendation Enhanced Matching | Planned | Compare output with and without `--no-enhanced-matching`
INT-004 | Outdated Simple | Planned | Known outdated & up-to-date sample pairs
INT-005 | Outdated Edge Cases | Planned | Prerelease vs release, build metadata, malformed variants
INT-006 | Blocklist Migration Warnings | Planned | Ensure deprecation warnings emitted once per flag use
INT-007 | Auto-Update Blocklist Add | Planned | Simulate casks with/without auto-updates; confirm additions
INT-008 | Auto-Update Uninstall Safety | Planned | Multi-step confirmation logic (reject / accept / partial)
INT-009 | Export JSON/CSV | Planned | Schema correctness, file writing, stdout fallback
INT-010 | Config Precedence | Planned | YAML base overridden by env overridden by CLI
INT-011 | Caching Cold vs Warm | Planned | Measure path difference: first vs second run (simulate cached Homebrew data)
INT-012 | Failure Injection (brew) | Planned | Subprocess failure → graceful messaging & exit code
INT-013 | Failure Injection (network) | Planned | Mock timeout / network error path, verify retry/abort logging
INT-014 | Rate Limiting Toggle | Planned | With and without adaptive limiting flag (log presence)
INT-015 | Async Parity (Future) | Future | Compare output under sync vs async mode (diff must be empty)
INT-016 | Profiling Output | Planned | `--profile` run produces structured summary without exceptions
INT-017 | Dual Flag Merge | Planned | Both --blocklist and --blacklist supplied → merged unique set
INT-018 | Service Commands (Dry) | Planned | Install/uninstall/service-status with simulated launchd layer
INT-019 | Menubar CLI Guard | Planned | Ensure menubar flag path triggers entry point without side effects (headless stub)
INT-020 | Integration Regression Matrix | Future | Aggregated run of canonical flows for release gating

---

## 5. Test Data & Fixtures

Fixture Type | Purpose | Notes
------------ | ------- | -----
Sample system_profiler JSON | Core discovery baseline | Minimal + extended variants
Homebrew cask list (mock) | Recommendation & outdated | Includes aliasing & auto-update metadata
Version mapping table | Outdated edge tests | Contains prerelease/build metadata combos
Cache directory fixture | Cold vs warm | Parameterized to persist across test boundaries selectively
Brew command interceptor | Subprocess stub | Returns stdout/exit codes per scenario mapping
Network session stub | For async/mocking future | Deterministic latency + failure sequences
Deprecation capture fixture | Records stderr | Asserts one-time warning behavior

---

## 6. Execution Strategy

Phase | Description | Success Criteria
----- | ----------- | ----------------
Phase 1 | Implement INT-001 through INT-005 | Core functional confidence
Phase 2 | Add config, caching, export, blocklist migration (INT-006–INT-011) | Behavioral correctness across layers
Phase 3 | Error handling + rate limiting + profiling (INT-012–INT-016) | Robust failure pathways & diagnostics
Phase 4 | Platform/service & dual semantics (INT-017–INT-019) | Completeness for user operations
Phase 5 | Async parity & regression matrix (INT-015 + INT-020) | Safeguard major performance migration

---

## 7. Tooling & Conventions

Aspect | Standard
------ | --------
Test Naming | test_int_<suiteid>_<short_description>.py
Markers | @pytest.mark.integration for all integration tests
Skip Conditions | Skip menubar/service tests on non-macOS; mark reason
Parallelism | Prefer serial for cache-sensitive tests; param grouping for performance
Assertions | Focus on observable output, exit codes, config mutation, file presence
Golden Files | Stored under tests/fixtures/golden/ (planned) for stable CLI output diffing
Logging Validation | Capture via caplog; assert presence/absence of warnings for deprecation & failures

---

## 8. Coverage Impact Goals

Dimension | Current | Target (Post Phase 3) | Rationale
--------- | ------- | --------------------- | ---------
Line Coverage | ≈10–11% | 25–30% | Only meaningful integrated lines included
Branch Coverage | (Not emphasized yet) | +15–20 pts | Exercise decision logic paths (version comparison, filtering)
Critical Paths | Partial | ≥95% | Discovery, recommendation, outdated, blocklist, auto-update
Failure Modes | Limited | ≥80% of enumerated failure scenarios | Reliability signals
Config Precedence | Minimal | Full precedence matrix | Prevent regression in layering logic

---

## 9. Risk Mitigation

Risk | Mitigation
---- | ----------
Flaky tests (timing / concurrency) | Avoid real sleeps; deterministic mock timestamps
Platform divergence | Abstract platform-specific paths; neutralize if not macOS
Cache contamination | Dedicated temp dirs + explicit teardown; parameterized warm reuse
Async migration drift | Parity harness compares structured JSON output snapshot pre/post migration
Deprecation drift | Single fixture asserts warnings once; fails if repeated

---

## 10. Reporting & CI Integration

Element | Plan
------- | ----
Selective Runs | Default CI includes integration tier; allow `-m "not integration"` for fast loops
Duration Tracking | Use `--durations=10` already configured
Failure Surface | On failure, capture: stderr, generated export files, config snapshot
Badges / Metrics | (Future) Add integration success ratio to README
Regression Matrix Job | Dedicated workflow once INT-020 stabilized

---

## 11. Future Enhancements

Item | Description
---- | -----------
Performance Assertions | Compare timing budget for cold vs warm cache (tolerances)
Structured Output Mode | Introduce JSON summary flag to enable golden file comparisons
Mutation Testing Hook | Optional future gate for version comparator logic
Security Scenario Simulation | Simulated vulnerable cask metadata reporting (placeholder for future feature)
Async Stress Harness | High-concurrency mock requests to ensure no race conditions in cache layer

---

## 12. Open Questions

Question | Pending Decision
-------- | ----------------
Include menubar UI snapshot tests? | Possibly out-of-scope (treat separately)
Store golden outputs in repo vs generated? | Leaning repository stored for diff visibility
When to raise coverage threshold in CI? | After Phase 2 completion & stability confirmation
Adopt hypothesis-based property tests at integration level? | Potential for version parsing differentials

---

## 13. Implementation Checklist (Phase 1)

- [ ] Create fixtures: system_profiler_min.json, system_profiler_extended.json
- [ ] Implement INT-001 basic discovery test
- [ ] Implement INT-002 blocklist vs blacklist parity test
- [ ] Implement INT-003 enhanced vs basic matching differential test (assert ordering or candidate count)
- [ ] Implement INT-004 outdated simple: single outdated & up-to-date sample
- [ ] Implement INT-005 outdated edge: prerelease vs final, build metadata ignore rules

Success Gate for Advancing to Phase 2:

- All Phase 1 tests pass locally and in CI
- No added flakiness (repeat run stability x3)
- Output stability confirmed (initial golden baseline established)

---

## 14. Contribution Guidelines (Integration Layer)

Guideline | Rule
--------- | ----
Fixture Size | Keep minimal & focused; large fixture sets require justification
Mocking Scope | Only external boundaries (brew subprocess, network, filesystem outside tmp)
Assertions | Prefer explicit structured assertions over broad substring checks
Golden Output | Regenerate only when intentional functional change; require CHANGELOG note
Deprecation | Ensure tests cover both new + legacy flags until removal milestone

---

## 15. Appendix: Sample CLI Flow Pseudocode (Baseline)

1. Invoke: `versiontracker --apps --blocklist "Safari,Firefox" --export json`
2. Load config file → overlay env vars → apply CLI overrides
3. Collect system_profiler JSON (mock)
4. Extract application list
5. Apply blocklist filters
6. (Optional) Match brew candidates (if recommendation mode)
7. Format & export results (stdout or file)
8. Return exit code (0 success; non-zero on structured failure)

---

End of initial integration test plan draft.
