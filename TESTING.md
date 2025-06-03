# VersionTracker Project: Testing Guidelines for AI Agents

This document outlines the testing strategy, current practices, and recommendations for writing and maintaining tests in the VersionTracker project. Its purpose is to guide AI agents in contributing effective and high-quality tests.

## 1. Testing Framework

* **Target Framework:** The project aims to standardize on **`pytest`** for all testing, as per the project rules (`versiontracker/.github/copilot-instructions.md`).
* **Current State:** The codebase currently has a mix of tests written using:
  * **`unittest`**: Found in files like `versiontracker/tests/test_version.py`, `versiontracker/tests/test_apps.py`, and `versiontracker/tests/handlers/test_app_handlers.py`. These typically use `unittest.TestCase` subclasses and `self.assert*` methods.
  * **`pytest` (or `pytest`-style)**: Found in files like `versiontracker/tests/handlers/test_config_handlers.py` and `versiontracker/tests/handlers/test_filter_handlers.py`, which use plain `assert` statements and `pytest` features like `setup_method`. Asynchronous tests in `versiontracker/tests/test_async_*.py` also leverage `pytest` and `pytest-asyncio`.
* **Recommendation for AI:**
  * **New Tests:** All new tests should be written using `pytest` conventions (e.g., plain `assert` statements, function-based tests, `pytest` fixtures).
  * **Refactoring:** When modifying existing `unittest`-based tests, consider refactoring them to `pytest` style if feasible.

## 2. Test Structure and Organization

* **Root Test Directory:** All tests are located under the `versiontracker/tests/` directory.
* **Subdirectories:** Handler-specific tests are further organized into `versiontracker/tests/handlers/`.
* **Naming Conventions:**
  * **Files:** Test files are named with a `test_` prefix (e.g., `test_version.py`, `test_app_handlers.py`).
  * **Test Classes (for `unittest`):** Classes are prefixed with `Test` (e.g., `TestVersionComparison`, `TestAppHandlers`).
  * **Test Functions/Methods:** Functions and methods are prefixed with `test_` (e.g., `test_parse_version`, `test_handle_list_apps_success`).
* **Test File Granularity:** The project has a significant number of test files (e.g., `test_apps.py`, `test_apps_coverage.py`, `test_apps_extra.py`, `test_apps_new.py`).
  * **AI Guidance:** When adding tests, consider if they logically fit into an existing file. If a module's tests become too large or diverse, a new, descriptively named test file might be appropriate. Aim for clarity and maintainability. If multiple `test_*.py` files seem to test very similar aspects of a single module, discuss potential consolidation.

## 3. Mocking and Test Doubles

Effective mocking is crucial for isolating units of code and ensuring tests are fast and deterministic.

* **Mocking Library:** The project primarily uses `unittest.mock` (accessible via `mock` or `unittest.mock` depending on the test file's style). This includes:
  * `@patch` decorator (and `patch` context manager).
  * `Mock`, `MagicMock` objects.
  * Seen in `versiontracker/tests/handlers/test_app_handlers.py`, `versiontracker/tests/handlers/test_config_handlers.py`.
* **Custom Mocks:**
  * **`versiontracker/tests/mock_homebrew_server.py`**: Provides a `MockHomebrewServer` to simulate Homebrew API responses for network operations. This is vital for testing Homebrew interactions without actual network calls. It's used in integration tests like `versiontracker/tests/test_async_integration.py` and `versiontracker/tests/test_network_operations.py`.
  * **`versiontracker/tests/mock_adaptive_rate_limiter.py`**: Provides a `MockAdaptiveRateLimiter` for testing functionalities that involve adaptive rate limiting.
* **What to Mock:**
  * External system calls (e.g., `subprocess.run`).
  * Network requests (e.g., to Homebrew API).
  * Filesystem operations (if not core to the test's purpose).
  * Time-dependent functions (`time.sleep`, `time.time`).
* **AI Guidance:**
  * Always mock external dependencies.
  * Utilize the existing `MockHomebrewServer` for tests involving Homebrew API interactions.
  * When mocking, ensure the mock behaves consistently with the real object's interface.

## 4. Code Coverage

* **Goal:** The project aims for at least 90% test coverage for core functionality.
* **Focus Areas:**
  * Improving test coverage for the `versiontracker/apps.py` module is a stated priority.
  * Pay special attention to version parsing and comparison edge cases (`versiontracker/version.py`).
* **Tools & Integration:**
  * **Recommendation:** Integrate `pytest-cov` for measuring coverage with `pytest`.
  * Generate HTML reports locally for visualizing coverage gaps.
  * Integrate with a CI service (e.g., Codecov, Coveralls) to track coverage over time.
* **AI Guidance:** When adding or modifying code, ensure corresponding tests are added or updated to maintain/improve coverage. Use coverage reports to identify untested code paths.

## 5. Key Test File Examples and Their Focus

* **`versiontracker/tests/test_version.py`**:
  * Focus: `versiontracker.version.py` module. Tests version string parsing (`parse_version`), version comparison (`compare_versions`), difference calculation (`get_version_difference`), and the `VersionInfo` data class.
  * Style: `unittest`.
* **`versiontracker/tests/test_apps.py`**:
  * Focus: Core logic in `versiontracker/apps.py`. Covers application discovery, Homebrew interactions (availability, cask info, caching), system profiler data processing, and batch operations.
  * Style: `unittest`. Extensive use of mocking.
* **`versiontracker/tests/handlers/test_app_handlers.py`**:
  * Focus: Functions within `versiontracker.handlers.app_handlers.py`.
  * Style: `unittest`. Demonstrates mocking of dependencies like `get_applications`, `get_config`.
* **`versiontracker/tests/handlers/test_config_handlers.py`**:
  * Focus: Functions within `versiontracker.handlers.config_handlers.py`.
  * Style: `pytest`-like (class-based but uses plain `assert` and `mock.patch`).
* **`versiontracker/tests/test_async_homebrew.py` & `test_async_network.py`**:
  * Focus: Asynchronous operations related to Homebrew API and general network calls.
  * Style: `pytest` with `pytest-asyncio` (e.g., `@pytest.mark.asyncio`).
* **`versiontracker/tests/test_async_integration.py`**:
  * Focus: Integration of asynchronous features with the `MockHomebrewServer`.
  * Style: `pytest` with `pytest-asyncio`.
* **`versiontracker/tests/test_parameterized_edge_cases.py` & `test_parameterized_version.py`**:
  * Focus: Testing version parsing and comparison with a wide range of edge cases using parameterized tests.
  * Style: `pytest` (likely using `@pytest.mark.parametrize`).

## 6. Best Practices for AI Agents

* **Write Pytest-Style Tests:** For new tests or when refactoring, use `pytest` idioms:
  * Plain `assert` statements.
  * Function-based tests where appropriate.
  * `pytest` fixtures for setup/teardown.
  * `@pytest.mark.parametrize` for data-driven tests.
* **Isolate Tests with Mocking:**
  * Aggressively mock external dependencies (network, filesystem, subprocesses) to ensure tests are fast, reliable, and deterministic.
  * Use the provided `MockHomebrewServer` for Homebrew API interactions.
* **Comprehensive Coverage:**
  * Test critical paths, edge cases (e.g., empty inputs, `None` values, invalid formats), boundary conditions, and error handling.
  * Refer to `test_parameterized_edge_cases.py` for examples of thorough edge case testing for version utilities.
* **Clarity and Readability:**
  * Use descriptive names for test functions and variables.
  * Ensure assertions are clear and directly test the intended behavior.
  * Add comments to explain complex mock setups or non-obvious test logic.
* **Determinism:**
  * Avoid tests that depend on external state, current time (unless mocked), or random data.
  * Ensure proper setup and teardown for tests that modify shared resources (e.g., caches - see `test_apps.py` for `clear_homebrew_casks_cache`).
* **Focus on `apps.py` and `version.py`:** These are critical modules. Contributions that improve their test coverage, especially around edge cases and error handling, are valuable.
* **Follow Project Structure:** Place new tests in the appropriate directory and file, adhering to existing naming conventions.

## 7. Running Tests

* Tests can likely be run using `pytest` from the project root directory:

    ```bash
    pytest
    ```

* To run tests for a specific file:

    ```bash
    pytest versiontracker/tests/test_version.py
    ```

* To run a specific test function:

    ```bash
    pytest versiontracker/tests/test_version.py::TestVersionComparison::test_parse_version
    ```

## 8. CI/CD Integration

* The project's CI/CD pipeline executes these tests automatically.
* Code coverage is (or should be) tracked as part of this pipeline. Aim to maintain or increase coverage with your contributions.

By following these guidelines, AI agents can contribute robust and maintainable tests that enhance the quality and reliability of the VersionTracker project.
