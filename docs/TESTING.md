# Testing Strategy and Guidelines

This document outlines the testing strategy, best practices, and guidelines for the VersionTracker project.

## Test Organization

### Test Categories

Tests are organized using pytest markers to enable selective execution:

- `@pytest.mark.unit` - Fast, isolated unit tests
- `@pytest.mark.integration` - Tests that combine multiple components
- `@pytest.mark.network` - Tests requiring network access or external services
- `@pytest.mark.slow` - Tests that may take longer than 60 seconds
- `@pytest.mark.timeout` - Tests specifically testing timeout behavior
- `@pytest.mark.flaky` - Tests that may be unreliable and need retry logic

### Running Tests Selectively

```bash
# Run only unit tests (fast)
pytest -m "unit"

# Run all tests except slow ones
pytest -m "not slow"

# Run only network tests
pytest -m "network"

# Skip flaky tests in CI
pytest -m "not flaky"
```

## Timeout Configuration

### Global Timeout Settings

All tests have a global timeout of **5 minutes (300 seconds)** to prevent hanging:

```ini
# pytest.ini
timeout = 300
timeout_method = thread
```

### Test-Specific Timeouts

For tests requiring longer execution times, use the `@pytest.mark.timeout` decorator:

```python
@pytest.mark.timeout(600)  # 10 minutes for heavy integration tests
def test_comprehensive_app_discovery():
    """Test that may need extended time for large app collections."""
    pass
```

### Timeout Strategies by Test Type

| Test Type | Recommended Timeout | Rationale |
|-----------|-------------------|-----------|
| Unit Tests | 30 seconds | Should be fast and isolated |
| Integration Tests | 2 minutes | May involve multiple components |
| Network Tests | 5 minutes | External dependencies may be slow |
| End-to-End Tests | 10 minutes | Full workflow testing |

## Network Test Guidelines

### Mock Server Usage

Network tests use a mock Homebrew server to simulate external dependencies:

```python
@pytest.mark.network
@with_mock_homebrew_server
def test_homebrew_integration(self, mock_server, server_url):
    """Test Homebrew operations with controlled responses."""
    mock_server.add_cask("firefox", "120.0.1", "Web browser")
    # Test implementation
```

### CI Environment Handling

Some tests are skipped in CI environments to avoid external dependencies:

```python
@pytest.mark.skipif(_is_ci_environment(), reason="Skipping brew-dependent test in CI")
def test_real_homebrew_interaction():
    """Test that requires actual Homebrew installation."""
    pass
```

### Network Error Simulation

Test various network conditions:

```python
# Timeout simulation
mock_server.set_timeout(True)

# Delay simulation  
mock_server.set_delay(2.0)

# Error simulation
mock_server.set_error(500, "Internal Server Error")
```

## Performance Testing

### Benchmarking

Performance-critical functions should include benchmark tests:

```python
@pytest.mark.benchmark
def test_app_discovery_performance(benchmark):
    """Ensure app discovery remains performant."""
    result = benchmark(discover_applications)
    assert len(result) > 0
    # Benchmark automatically measures execution time
```

### Memory Usage

Monitor memory usage for operations processing large datasets:

```python
@pytest.mark.slow
def test_memory_usage_large_app_list():
    """Verify memory efficiency with large app collections."""
    import psutil
    process = psutil.Process()

    initial_memory = process.memory_info().rss
    # Process large dataset
    final_memory = process.memory_info().rss

    memory_increase = final_memory - initial_memory
    assert memory_increase < 100 * 1024 * 1024  # Less than 100MB increase
```

## Test Data Management

### Fixtures

Use fixtures for reusable test data:

```python
@pytest.fixture
def sample_app_data():
    """Provide consistent test application data."""
    return [
        {"name": "Firefox", "version": "120.0.1", "path": "/Applications/Firefox.app"},
        {"name": "Chrome", "version": "119.0.0", "path": "/Applications/Chrome.app"},
    ]
```

### Parameterized Tests

Use parameterization to test multiple scenarios efficiently:

```python
@pytest.mark.parametrize("version_string,expected", [
    ("1.2.3", (1, 2, 3)),
    ("v2.0.0", (2, 0, 0)),
    ("1.0.0-beta", (1, 0, 0, "beta")),
])
def test_version_parsing(version_string, expected):
    """Test version parsing with various formats."""
    assert parse_version(version_string) == expected
```

## Async Testing

### Async Test Configuration

Async tests require proper configuration:

```python
@pytest.mark.asyncio
async def test_async_homebrew_operation():
    """Test async Homebrew operations."""
    async with aiohttp.ClientSession() as session:
        result = await async_homebrew_query(session, "firefox")
        assert result is not None
```

### Async Timeout Handling

Async operations should have explicit timeouts:

```python
import asyncio

@pytest.mark.asyncio
@pytest.mark.timeout(30)
async def test_async_with_timeout():
    """Test async operation with timeout protection."""
    try:
        result = await asyncio.wait_for(
            slow_async_operation(),
            timeout=10.0
        )
        assert result is not None
    except asyncio.TimeoutError:
        pytest.fail("Operation timed out")
```

## Coverage Requirements

### Target Coverage

- **Overall**: 70%+ coverage maintained
- **Core modules**: 80%+ coverage required
- **Critical paths**: 95%+ coverage required

### Coverage Exclusions

Exclude specific lines from coverage when appropriate:

```python
def platform_specific_function():
    if sys.platform == "darwin":  # pragma: no cover
        # macOS-specific implementation
        pass
    else:  # pragma: no cover
        raise NotImplementedError("Platform not supported")
```

## Test Maintenance

### Flaky Test Handling

1. **Identify**: Mark flaky tests with `@pytest.mark.flaky`
2. **Investigate**: Add logging to understand failure patterns
3. **Fix**: Address root causes (timing, dependencies, etc.)
4. **Retry**: Implement retry logic for unavoidable external dependencies

### Test Performance

- Keep unit tests under 1 second each
- Limit integration tests to under 30 seconds
- Use `@pytest.mark.slow` for tests over 60 seconds
- Profile slow tests and optimize when possible

### Dependencies

- Mock external dependencies (Homebrew, network calls)
- Use dependency injection for testability
- Avoid testing third-party library functionality
- Focus on testing integration points

## Running Tests

### Local Development

```bash
# Quick unit test run
pytest -m "unit and not slow" --maxfail=5

# Full test suite
pytest

# With coverage report
pytest --cov=versiontracker --cov-report=html

# Performance tests only
pytest -m "benchmark"
```

### CI Environment

The CI pipeline runs tests with:
- Multiple Python versions (3.12, 3.13)
- Multiple platforms (Ubuntu, macOS)
- Parallel execution where appropriate
- Coverage reporting
- Performance regression detection

### Debugging Tests

```bash
# Run single test with detailed output
pytest tests/test_specific.py::test_function -vvv -s

# Drop into debugger on failure
pytest --pdb

# Run last failed tests only
pytest --lf

# Run tests matching pattern
pytest -k "test_version"
```

This testing strategy ensures reliable, maintainable, and comprehensive test coverage while preventing common issues like hanging tests and flaky behavior.
