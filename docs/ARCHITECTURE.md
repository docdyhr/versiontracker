# VersionTracker Architecture Documentation

This document provides a comprehensive overview of the VersionTracker architecture for new contributors and maintainers.

## Table of Contents

- [High-Level Architecture](#high-level-architecture)
- [Module Overview](#module-overview)
- [Data Flow](#data-flow)
- [Design Patterns](#design-patterns)
- [Performance Architecture](#performance-architecture)
- [Error Handling Strategy](#error-handling-strategy)
- [Testing Architecture](#testing-architecture)
- [Extension Points](#extension-points)

## High-Level Architecture

VersionTracker follows a modular, layered architecture designed for maintainability, testability, and performance.

```
┌─────────────────────────────────────────────────────────────┐
│                    Presentation Layer                       │
├─────────────────────────────────────────────────────────────┤
│  CLI Interface (cli.py) │ UI Components (ui.py)             │
└─────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────┐
│                     Business Logic Layer                    │
├─────────────────────────────────────────────────────────────┤
│ App Discovery │ Version Analysis │ Recommendations │ Export │
│   (apps.py)   │   (utils.py)     │   (handlers/)    │(export)│
└─────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────┐
│                    Service Layer                           │
├─────────────────────────────────────────────────────────────┤
│    Homebrew Integration    │    Configuration Management    │
│  (homebrew.py, async_*)    │         (config.py)           │
└─────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────┐
│                 Infrastructure Layer                       │
├─────────────────────────────────────────────────────────────┤
│ Caching │ Network │ Profiling │ Utilities │ Exception Handling│
│(cache.*)|(*network)|profiling.py|(utils.py)|(exceptions.py) │
└─────────────────────────────────────────────────────────────┘
```

## Module Overview

### Core Modules

#### `cli.py` - Command Line Interface
- **Purpose**: Entry point for command-line interactions
- **Responsibilities**:
  - Argument parsing and validation
  - Command routing
  - Output formatting
  - Error handling for user-facing errors
- **Dependencies**: All other modules
- **Key Components**:
  - `main()`: Primary entry point
  - Command handlers for each CLI option
  - Progress bar management

#### `apps.py` - Application Discovery
- **Purpose**: Discover and analyze installed applications
- **Responsibilities**:
  - Scan `/Applications/` directory
  - Extract application metadata (name, version, bundle ID)
  - Filter App Store vs non-App Store applications
  - Apply user-defined blacklists and filters
- **Key Functions**:
  - `get_apps_not_in_app_store()`: Main discovery function
  - `extract_app_info()`: Metadata extraction
  - `is_app_store_app()`: App Store detection

#### `homebrew.py` / `async_homebrew.py` - Homebrew Integration
- **Purpose**: Interface with Homebrew package manager
- **Synchronous Module** (`homebrew.py`):
  - Command-line interface to Homebrew
  - Cask enumeration and version checking
  - Legacy compatibility
- **Asynchronous Module** (`async_homebrew.py`):
  - HTTP API integration with Homebrew formulae API
  - Concurrent request processing
  - Enhanced performance and error handling
- **Key Functions**:
  - `get_installed_casks()`: List installed casks
  - `fetch_cask_info()`: Get cask metadata from API
  - `check_cask_versions()`: Version comparison

### Infrastructure Modules

#### `cache.py` / `advanced_cache.py` - Caching System
- **Basic Cache** (`cache.py`):
  - Simple disk-based caching
  - JSON serialization
  - TTL-based expiration
- **Advanced Cache** (`advanced_cache.py`):
  - Multi-tier caching (memory, disk, compressed)
  - Automatic cleanup and size management
  - Thread-safe operations
  - Cache statistics and monitoring

#### `async_network.py` - Network Layer
- **Purpose**: Asynchronous HTTP operations
- **Features**:
  - Connection pooling
  - Retry logic with exponential backoff
  - Timeout management
  - Rate limiting
  - Batch request processing

#### `profiling.py` - Performance Monitoring
- **Purpose**: Performance analysis and optimization
- **Features**:
  - Function-level timing
  - Memory usage tracking
  - Statistical analysis (min/max/avg)
  - Integration with cProfile
  - Nested call detection

### Utility Modules

#### `config.py` - Configuration Management
- **Purpose**: Manage user preferences and settings
- **Features**:
  - YAML configuration file support
  - Environment variable integration
  - Default value management
  - Configuration validation

#### `utils.py` - Utility Functions
- **Purpose**: Shared utility functions
- **Key Functions**:
  - Version comparison and parsing
  - String similarity matching
  - System information gathering
  - Fuzzy matching algorithms

#### `exceptions.py` - Error Handling
- **Purpose**: Custom exception hierarchy
- **Exception Types**:
  - `HomebrewError`: Homebrew-related issues
  - `NetworkError`: Network communication problems
  - `TimeoutError`: Operation timeout
  - `CacheError`: Caching system issues

## Data Flow

### Application Discovery Flow

```
User Command → CLI Parser → Apps Module
                               ↓
App Directory Scan → Metadata Extraction → App Store Detection
                               ↓
Blacklist Filtering → Additional Directory Scan → Result Aggregation
                               ↓
                         Return App List
```

### Recommendation Flow

```
App List → Homebrew Cask Lookup (with caching)
             ↓
Version Comparison → Similarity Matching → Recommendation Scoring
             ↓
Result Filtering → Recommendation List → Output Formatting
```

### Async Network Flow

```
Request → Rate Limiter → Connection Pool → HTTP Request
            ↓                ↓               ↓
    Cache Check ←→ Request Batching ←→ Response Handling
            ↓                                ↓
    Cache Update ←← Result Processing ←← Error Handling
```

## Design Patterns

### Command Pattern
The project uses the Command pattern in the `handlers/` directory:

```python
# handlers/app_handlers.py
class AppDiscoveryHandler:
    def __init__(self, config: Config):
        self.config = config

    def handle(self, args: Namespace) -> List[Dict[str, Any]]:
        """Handle app discovery command."""
        return get_apps_not_in_app_store(
            blacklist=self.config.blacklist,
            additional_dirs=self.config.additional_dirs
        )
```

### Strategy Pattern
Different caching strategies are implemented using the Strategy pattern:

```python
class CacheStrategy(ABC):
    @abstractmethod
    def get(self, key: str) -> Optional[Any]: ...

    @abstractmethod
    def set(self, key: str, value: Any, ttl: int) -> None: ...

class MemoryCache(CacheStrategy): ...
class DiskCache(CacheStrategy): ...
class CompressedCache(CacheStrategy): ...
```

### Observer Pattern
The profiling system uses the Observer pattern for performance monitoring:

```python
@profile_function("homebrew_lookup")
def fetch_cask_info(cask_name: str) -> Dict[str, Any]:
    # Function implementation
    pass
```

### Decorator Pattern
Used extensively for:
- Performance profiling
- Caching
- Error handling
- Retry logic

## Performance Architecture

### Asynchronous Processing

The application uses a hybrid sync/async architecture:

1. **Synchronous Path**: For simple, fast operations and legacy compatibility
2. **Asynchronous Path**: For network I/O and batch operations

```python
# Async batch processing
async def process_casks_concurrently(cask_names: List[str]) -> List[Dict]:
    """Process multiple casks with controlled concurrency."""
    semaphore = asyncio.Semaphore(10)  # Limit concurrent requests

    async def fetch_with_semaphore(name):
        async with semaphore:
            return await fetch_cask_info(name)

    tasks = [fetch_with_semaphore(name) for name in cask_names]
    return await asyncio.gather(*tasks, return_exceptions=True)
```

### Caching Strategy

Multi-tier caching for optimal performance:

1. **L1 - Memory Cache**: Hot data, instant access
2. **L2 - Disk Cache**: Persistent storage, fast access
3. **L3 - Compressed Cache**: Large datasets, space-efficient

### Rate Limiting

Adaptive rate limiting based on:
- System load (CPU, memory)
- Network conditions
- API response times
- Error rates

## Error Handling Strategy

### Exception Hierarchy

```
VersionTrackerError (base)
├── HomebrewError
│   ├── HomebrewNotFoundError
│   ├── HomebrewCommandError
│   └── CaskNotFoundError
├── NetworkError
│   ├── TimeoutError
│   ├── ConnectionError
│   └── RateLimitError
├── CacheError
│   ├── CacheCorruptionError
│   └── CachePermissionError
└── ConfigurationError
    ├── InvalidConfigError
    └── MissingConfigError
```

### Error Recovery

1. **Network Errors**: Retry with exponential backoff
2. **Cache Errors**: Fallback to direct API calls
3. **Homebrew Errors**: Graceful degradation
4. **User Errors**: Clear error messages with suggestions

### Logging Strategy

```python
import logging

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Performance logging
performance_logger = logging.getLogger('versiontracker.performance')
network_logger = logging.getLogger('versiontracker.network')
```

## Testing Architecture

### Test Organization

```
tests/
├── unit/           # Unit tests for individual modules
├── integration/    # Integration tests for component interaction
├── performance/    # Performance and load tests
├── fixtures/       # Test data and mock objects
└── mock_servers/   # Mock HTTP servers for testing
```

### Test Patterns

1. **Unit Tests**: Test individual functions and classes
2. **Integration Tests**: Test module interactions
3. **Contract Tests**: Test API contracts
4. **Performance Tests**: Measure and track performance metrics
5. **Property-Based Tests**: Use Hypothesis for edge case discovery

### Mock Strategy

```python
# Mock external dependencies
@patch('versiontracker.homebrew.subprocess.run')
@patch('versiontracker.async_network.aiohttp.ClientSession')
async def test_cask_lookup(mock_session, mock_subprocess):
    # Test implementation
    pass
```

## Extension Points

### Adding New Package Managers

1. Create new module in `versiontracker/` (e.g., `macports.py`)
2. Implement standard interface:
   ```python
   class PackageManager(ABC):
       @abstractmethod
       def get_installed_packages(self) -> List[Package]: ...

       @abstractmethod
       def get_package_info(self, name: str) -> Optional[Package]: ...
   ```
3. Add handler in `handlers/`
4. Update CLI parser
5. Add tests

### Adding New Export Formats

1. Create exporter in `export.py`:
   ```python
   def export_xml(data: List[Dict]) -> str:
       # Implementation
       pass
   ```
2. Register in CLI parser
3. Add tests

### Adding New Cache Backends

1. Implement `CacheStrategy` interface
2. Add to cache factory
3. Update configuration options

### Custom Matching Algorithms

1. Implement in `utils.py`:
   ```python
   def custom_similarity(app_name: str, cask_name: str) -> float:
       # Implementation
       pass
   ```
2. Add configuration option
3. Update recommendation logic

## Configuration Architecture

### Configuration Hierarchy

1. **Default values** (hardcoded)
2. **Configuration file** (`~/.config/versiontracker/config.yaml`)
3. **Environment variables** (`VERSIONTRACKER_*`)
4. **Command-line arguments**

### Configuration Schema

```yaml
# Example configuration
api-rate-limit: 3
max-workers: 10
similarity-threshold: 75
cache:
  enabled: true
  ttl: 86400
  max-size: 100MB
profiling:
  enabled: false
  detailed: false
blacklist:
  - Firefox
  - Chrome
additional-app-dirs:
  - /Users/username/Applications
```

## Security Considerations

### Input Validation
- Sanitize all user inputs
- Validate file paths
- Limit resource consumption

### Command Execution
- Use subprocess with controlled arguments
- Avoid shell injection
- Validate Homebrew commands

### Network Security
- Use HTTPS for all API calls
- Validate SSL certificates
- Implement request timeouts

### Data Privacy
- No personal data collection
- Local processing only
- Secure cache storage

---

This architecture supports the current feature set while providing flexibility for future enhancements. The modular design allows for easy testing, maintenance, and extension.

For questions about the architecture or suggestions for improvements, please open an issue or discussion on GitHub.
