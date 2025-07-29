# Python 3.13 Support

This document outlines VersionTracker's Python 3.13 compatibility status and modernization roadmap.

## Current Status

✅ **Python 3.13 Ready** - VersionTracker is now compatible with Python 3.13

### Compatibility Testing Results

- **Core Functionality**: ✅ All modules import and function correctly
- **Dependencies**: ✅ All dependencies are Python 3.13 compatible
- **Type Hints**: ⚠️ Legacy typing imports can be modernized
- **Async Operations**: ✅ Full asyncio compatibility
- **File Operations**: ✅ pathlib and file I/O working correctly
- **Subprocess Operations**: ✅ All system integrations functional

## Python Version Support Matrix

| Python Version | Status | Test Coverage | CI/CD |
|---------------|--------|---------------|-------|
| 3.10 | ✅ Supported | Full | ✅ |
| 3.11 | ✅ Supported | Full | ✅ |
| 3.12 | ✅ Supported | Full | ✅ |
| 3.13 | ✅ Supported | Full | ✅ Experimental |

## Installation

### Standard Installation
```bash
pip install versiontracker
```

### Python 3.13 Specific Installation
```bash
# Install with Python 3.13 optimized requirements
pip install -r requirements-py313.txt
```

### Development Installation
```bash
# Clone repository
git clone https://github.com/docdyhr/versiontracker.git
cd versiontracker

# Create virtual environment with Python 3.13
python3.13 -m venv .venv313
source .venv313/bin/activate

# Install development dependencies
pip install -r requirements-dev.txt
```

## New Features in Python 3.13 Support

### Enhanced Type Hints
Python 3.13 brings improved type hint support. VersionTracker is ready to leverage:

- **Modern Built-in Generics**: `list[str]` instead of `List[str]`
- **Union Operator**: `str | int` instead of `Union[str, int]`
- **Enhanced Type Variables**: Better generic class support
- **Improved Performance**: Faster type checking and runtime performance

### Example Modern Type Hints
```python
# Modern Python 3.9+ syntax (fully supported)
def process_apps(
    apps: list[str],                    # Instead of List[str]
    config: dict[str, Any],             # Instead of Dict[str, Any]
    exclude: set[str] | None = None,    # Union with | operator
) -> dict[str, list[str]]:              # Modern return type
    """Process applications with modern type hints."""
    pass
```

### Async Improvements
Python 3.13's async improvements are fully utilized:

```python
import asyncio

async def check_updates_async():
    """Async update checking with Python 3.13 optimizations."""
    async with aiohttp.ClientSession() as session:
        # Enhanced async context manager support
        results = await gather_homebrew_data(session)
        return results
```

## Migration Guide

### For Users
No migration needed! VersionTracker works seamlessly across Python 3.10-3.13.

### For Contributors
When contributing code, consider using modern Python features:

1. **Type Hints**: Use built-in generics where possible
2. **Match Statements**: Use `match`/`case` for pattern matching
3. **Async Context Managers**: Leverage improved async support
4. **Error Handling**: Use enhanced exception groups if needed

### Modernizing Type Hints
Run the type hint modernization analyzer:

```bash
python scripts/modernize_type_hints.py
```

This will identify opportunities to update legacy `typing` imports to modern syntax.

## CI/CD Integration

### GitHub Actions Support
Python 3.13 is included in the CI matrix with experimental status:

```yaml
strategy:
  matrix:
    python-version: ["3.10", "3.11", "3.12", "3.13"]
    include:
      - python-version: "3.13"
        experimental: true
```

### Testing
All existing tests pass on Python 3.13. Run the compatibility test:

```bash
python scripts/test_python313.py
```

## Performance Improvements

Python 3.13 provides several performance benefits for VersionTracker:

1. **Faster Startup**: Improved module loading
2. **Better Async**: Enhanced asyncio performance
3. **Memory Efficiency**: Reduced memory usage for type hints
4. **Optimized I/O**: Faster file operations

## Dependency Compatibility

All major dependencies are Python 3.13 ready:

| Dependency | Python 3.13 Status | Version |
|-----------|-------------------|---------|
| fuzzywuzzy | ✅ Compatible | 0.18.0+ |
| tqdm | ✅ Compatible | 4.66.0+ |
| PyYAML | ✅ Compatible | 6.0+ |
| termcolor | ✅ Compatible | 2.3.0+ |
| tabulate | ✅ Compatible | 0.9.0+ |
| psutil | ✅ Compatible | 5.9.5+ |
| aiohttp | ✅ Compatible | 3.8.0+ |
| rapidfuzz | ✅ Compatible | 3.0.0+ |

## Known Issues

### Minor Compatibility Notes

1. **MyPy**: Uses Python 3.10 as baseline for maximum compatibility
2. **Pre-release Builds**: CI uses `allow-prereleases: true` for Python 3.13
3. **Type Hints**: Legacy `typing` imports work but modern syntax is preferred

### Workarounds
None required - all functionality works out of the box.

## Roadmap

### Completed ✅
- [x] Core compatibility testing
- [x] Dependency verification
- [x] CI/CD pipeline integration
- [x] Documentation updates
- [x] Type hint analysis

### In Progress 🚧
- [ ] Type hint modernization (optional optimization)
- [ ] Performance benchmarking
- [ ] Advanced Python 3.13 feature adoption

### Future Enhancements 🔮
- [ ] Leverage Python 3.13-specific performance features
- [ ] Enhanced error handling with exception groups
- [ ] Advanced type system features

## Support

### Getting Help
- 📖 [Documentation](https://github.com/docdyhr/versiontracker)
- 🐛 [Issue Tracker](https://github.com/docdyhr/versiontracker/issues)
- 💬 [Discussions](https://github.com/docdyhr/versiontracker/discussions)

### Reporting Python 3.13 Issues
When reporting Python 3.13-specific issues:

1. Include Python version: `python --version`
2. Include VersionTracker version: `versiontracker --version`
3. Run compatibility test: `python scripts/test_python313.py`
4. Include test results in issue report

### Contributing
We welcome contributions to improve Python 3.13 support:

1. **Type Hint Modernization**: Help update legacy type hints
2. **Performance Optimization**: Leverage Python 3.13 performance features
3. **Testing**: Add Python 3.13-specific test cases
4. **Documentation**: Improve Python 3.13 documentation

---

**Status**: Production Ready ✅  
**Last Updated**: July 2025  
**Tested With**: Python 3.13.0+  
**Compatibility**: Backward compatible with Python 3.10+
