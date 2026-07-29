# Repository Guidelines

## Project Structure & Module Organization

The core package is `versiontracker/`: CLI entry (`__main__.py`, `cli.py`), discovery in `apps/`, integrations in
`homebrew*.py`, caching via `cache.py` and `advanced_cache.py`, and shared handlers under `handlers/`. Tests live in
`tests/`. Assets, docs, and automation map to `assets/`, `docs/`, and `scripts/`, with config samples in `examples/` and
`sample_config.yaml`. `pyproject.toml` plus the `requirements*.txt` files manage builds and dependency pins.

## Build, Test, and Development Commands

Create a venv (`python3 -m venv .venv && source .venv/bin/activate`), install dependencies with `pip install -c
constraints.txt -r requirements.txt -r requirements-dev.txt`, then `pip install -e .`. Run `ruff check .`, `ruff format
.`, `mypy versiontracker`, and `pytest`; add `-m "not slow"` or `--maxfail=1` as needed. `python -m build` assembles
distributions, and release helpers in `scripts/` keep taps and requirement snapshots current.

## Coding Style & Naming Conventions

Use 4-space indentation, full type hints, and concise docstrings. Ruff enforces 120-character lines, sorted imports, and
strict lint rules—accept its autofixes before manual tweaks. Keep code and test files in `snake_case`, classes in
`PascalCase`, and constants in `UPPER_CASE`. Route CLI adjustments through `versiontracker.cli` to preserve the
registered entry point.

## Testing Guidelines

`pytest.ini` enables branch coverage and exports to `htmlcov/` and `coverage.xml`; sustain coverage near the present 70%
baseline. Add unit tests next to the code they exercise (e.g., `tests/test_cache.py`) and gate heavier flows behind
`slow`, `integration`, `network`, or `asyncio` markers. Stub Homebrew access with fixtures or helpers from
`tests/test_apps*.py` instead of hitting the network.

## Commit & Pull Request Guidelines

Commits follow Conventional Commits (`type(scope): summary (#issue)`), e.g., `fix(cache): cap stale entries (#123)`.
Bundle related changes, update `CHANGELOG.md` or docs when behaviour shifts, and attach CLI output diffs if they clarify
the impact. Before opening a PR, run `ruff check .`, `ruff format --check .`, `mypy versiontracker`, and `pytest`; flag
blockers and link to tracking issues in the description.

## Security & Tooling

For security-sensitive work, add `bandit -r versiontracker`, `pip-audit`, and `check-security-status.sh` to your local
checklist. Never commit secrets—use `sample_config.yaml` as a template and store live credentials in environment
variables or the macOS keychain.
