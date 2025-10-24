# VersionTracker API Documentation

## Overview

VersionTracker provides a comprehensive API for managing macOS applications and their versions. This document covers the core modules, classes, and functions available for programmatic use.

## Core Modules

### `versiontracker.homebrew`

Core Homebrew integration module for managing cask information and operations.

#### Functions

##### `get_homebrew_casks(use_cache: bool = True) -> list[dict[str, Any]]`

Retrieves all available Homebrew casks.

**Parameters:**
- `use_cache` (bool): Whether to use cached results. Default: True

**Returns:**
- `list[dict[str, Any]]`: List of cask dictionaries

**Raises:**
- `HomebrewError`: When Homebrew operations fail
- `NetworkError`: When network requests fail

**Example:**
```python
from versiontracker.homebrew import get_homebrew_casks

casks = get_homebrew_casks()
print(f"Found {len(casks)} casks")
```

##### `get_cask_info(cask_name: str) -> dict[str, Any] | None`

Gets detailed information about a specific cask.

**Parameters:**
- `cask_name` (str): Name of the cask

**Returns:**
- `dict[str, Any] | None`: Cask information or None if not found

##### `has_auto_updates(cask_info: dict[str, Any]) -> bool`

Checks if a cask has auto-update capabilities.

**Parameters:**
- `cask_info` (dict): Cask information dictionary

**Returns:**
- `bool`: True if cask has auto-updates

### `versiontracker.apps`

Application discovery and management module.

#### Classes

##### `Application`

Represents a macOS application with version information.

**Attributes:**
- `name` (str): Application name
- `version` (str): Current version
- `path` (Path): Application bundle path
- `bundle_id` (str): Application bundle identifier

**Methods:**

###### `is_app_store_app() -> bool`

Checks if the application was installed via App Store.

**Returns:**
- `bool`: True if App Store app

###### `get_version_info() -> dict[str, Any]`

Gets detailed version information.

**Returns:**
- `dict[str, Any]`: Version details

#### Functions

##### `find_applications(paths: list[Path] | None = None) -> list[Application]`

Discovers applications in specified paths.

**Parameters:**
- `paths` (list[Path] | None): Search paths, defaults to standard locations

**Returns:**
- `list[Application]`: List of discovered applications

### `versiontracker.version`

Version comparison and parsing utilities.

#### Functions

##### `parse_version(version_string: str) -> tuple[int, ...]`

Parses a version string into comparable components.

**Parameters:**
- `version_string` (str): Version string to parse

**Returns:**
- `tuple[int, ...]`: Version components

**Example:**
```python
from versiontracker.version import parse_version, compare_versions

v1 = parse_version("1.2.3")
v2 = parse_version("1.2.4")
result = compare_versions(v1, v2)  # Returns -1
```

##### `compare_versions(version1: tuple[int, ...], version2: tuple[int, ...]) -> int`

Compares two version tuples.

**Parameters:**
- `version1` (tuple): First version
- `version2` (tuple): Second version

**Returns:**
- `int`: -1 if v1 < v2, 0 if equal, 1 if v1 > v2

### `versiontracker.config`

Configuration management system.

#### Classes

##### `Config`

Main configuration class for VersionTracker.

**Attributes:**
- `api_rate_limit` (int): API rate limit per minute
- `max_workers` (int): Maximum concurrent workers
- `similarity_threshold` (float): Fuzzy matching threshold
- `blacklist` (list[str]): Blacklisted applications
- `additional_app_dirs` (list[Path]): Additional search directories

**Methods:**

###### `load(config_file: Path | None = None) -> None`

Loads configuration from file.

**Parameters:**
- `config_file` (Path | None): Configuration file path

###### `save(config_file: Path | None = None) -> None`

Saves current configuration to file.

**Parameters:**
- `config_file` (Path | None): Configuration file path

#### Functions

##### `get_config() -> Config`

Gets the global configuration instance.

**Returns:**
- `Config`: Global configuration object

### `versiontracker.cache`

Caching system for improving performance.

#### Functions

##### `read_cache(cache_key: str) -> dict[str, Any] | None`

Reads cached data by key.

**Parameters:**
- `cache_key` (str): Cache key identifier

**Returns:**
- `dict[str, Any] | None`: Cached data or None if expired/missing

##### `write_cache(cache_key: str, data: dict[str, Any], ttl: int = 3600) -> None`

Writes data to cache.

**Parameters:**
- `cache_key` (str): Cache key identifier
- `data` (dict): Data to cache
- `ttl` (int): Time to live in seconds

### `versiontracker.export`

Data export functionality.

#### Functions

##### `export_to_json(data: list[dict[str, Any]], output_file: Path | None = None) -> str`

Exports data to JSON format.

**Parameters:**
- `data` (list): Data to export
- `output_file` (Path | None): Output file path

**Returns:**
- `str`: JSON string

##### `export_to_csv(data: list[dict[str, Any]], output_file: Path | None = None) -> str`

Exports data to CSV format.

**Parameters:**
- `data` (list): Data to export
- `output_file` (Path | None): Output file path

**Returns:**
- `str`: CSV string

## Exceptions

### `VersionTrackerError`

Base exception for all VersionTracker errors.

### `HomebrewError`

Raised when Homebrew operations fail.

### `NetworkError`

Raised when network operations fail.

### `TimeoutError`

Raised when operations timeout.

### `VersionError`

Raised when version parsing fails.

## Usage Examples

### Basic Application Discovery

```python
from versiontracker.apps import find_applications
from versiontracker.homebrew import get_homebrew_casks, get_cask_recommendations

# Find all applications
apps = find_applications()
print(f"Found {len(apps)} applications")

# Get Homebrew recommendations
casks = get_homebrew_casks()
recommendations = get_cask_recommendations(apps, casks)
print(f"Found {len(recommendations)} recommendations")
```

### Configuration Management

```python
from versiontracker.config import Config, get_config

# Load configuration
config = get_config()
config.api_rate_limit = 120  # Increase rate limit
config.blacklist.append("MyApp")  # Add to blacklist
config.save()  # Persist changes
```

### Async Operations

```python
import asyncio
from versiontracker.async_homebrew import async_get_homebrew_casks

async def main():
    casks = await async_get_homebrew_casks()
    print(f"Found {len(casks)} casks asynchronously")

asyncio.run(main())
```

### Export Results

```python
from versiontracker.export import export_to_json
from pathlib import Path

# Export recommendations to JSON
export_to_json(recommendations, Path("recommendations.json"))
```

## Type Hints

VersionTracker uses comprehensive type hints throughout the codebase. Import types from the main modules:

```python
from versiontracker.apps import Application
from versiontracker.config import Config
from typing import Any, Dict, List, Optional
```

## Error Handling

Always use proper error handling when using the API:

```python
from versiontracker.exceptions import HomebrewError, NetworkError

try:
    casks = get_homebrew_casks()
except HomebrewError as e:
    print(f"Homebrew error: {e}")
except NetworkError as e:
    print(f"Network error: {e}")
```

## Performance Considerations

- Use caching when available (`use_cache=True`)
- Prefer async operations for bulk operations
- Configure appropriate rate limits for your use case
- Use batch operations when processing multiple items

## Thread Safety

Most operations are thread-safe, but configuration changes should be synchronized:

```python
import threading
from versiontracker.config import get_config

config_lock = threading.Lock()

with config_lock:
    config = get_config()
    config.blacklist.append("NewApp")
    config.save()
```
