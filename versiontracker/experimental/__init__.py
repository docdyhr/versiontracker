"""Experimental features for VersionTracker.

This package contains modules that are implemented but not yet wired into the
main CLI or production code paths. They are available for opt-in use by
developers and advanced users, but should not be imported unconditionally from
production code.

Modules
-------
analytics
    Comprehensive analytics and monitoring system: session tracking, performance
    metrics, usage patterns, and business intelligence via SQLite. Not called by
    any CLI path; import explicitly when needed.

benchmarks
    Automated performance benchmarking: function-level timing, memory and CPU
    tracking, statistical analysis, and async benchmark orchestration. Useful
    for profiling and regression detection during development.

Usage Example
-------------
To use analytics in a custom script or future CLI command::

    from versiontracker.experimental.analytics import AnalyticsEngine

    engine = AnalyticsEngine()
    with engine.session():
        engine.record_event("app_scan_started")

To run benchmarks::

    from versiontracker.experimental.benchmarks import BenchmarkRunner

    runner = BenchmarkRunner()
    runner.run_all()
    runner.print_report()

Stability
---------
All modules in this package are subject to change without notice between minor
versions. They are NOT part of the public API and are excluded from the
standard mypy and coverage checks.

To promote a module out of experimental status:
1. Wire it into a CLI entry point or handler.
2. Add it to the standard test suite with ≥ 60 % coverage.
3. Remove it from this package and move it to the top-level ``versiontracker``
   package.
"""

__all__ = [
    "analytics",
    "benchmarks",
]
