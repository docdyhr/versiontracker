# CLAUDE.md - VersionTracker Project Guide

## Commands
- Run all tests: `pytest -v`
- Run single test: `pytest tests/test_file.py::TestClass::test_method -v`
- Run specific test file: `pytest tests/test_file.py -v`
- Type checking: `mypy versiontracker`
- Lint code: `flake8 versiontracker`
- Format code: `black versiontracker && isort versiontracker`

## Code Style Guidelines
- Imports: stdlib → external → internal, alphabetized within groups
- Naming: snake_case for functions/variables, PascalCase for classes, CAPS for constants
- Line length: 100 characters max (black, flake8 configured for this)
- Types: Use type hints consistently; Optional for nullable values
- Error handling: Use custom exceptions from versiontracker.exceptions
- Docstrings: Google-style with Args, Returns, Raises sections
- Testing: Unit tests with unittest TestCase style, use mocks appropriately
- Dependencies: Always provide fallbacks for optional dependencies
- Logging: Use logger.debug/info/warning/error with descriptive messages