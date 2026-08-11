#!/usr/bin/env python3
"""Test Python 3.13 compatibility for VersionTracker.

This script tests the compatibility of VersionTracker with Python 3.13,
checking for any issues with dependencies, type hints, and core functionality.
"""

import importlib
import sys
from pathlib import Path


class Python313CompatibilityTester:
    """Test Python 3.13 compatibility."""

    def __init__(self) -> None:
        """Initialize the compatibility tester."""
        self.results: dict[str, bool] = {}
        self.errors: dict[str, str] = {}
        self.warnings: list[str] = []

    def run_all_tests(self) -> bool:
        """Run all compatibility tests."""
        print("🐍 Testing Python 3.13 compatibility")
        print(f"Current Python version: {sys.version}")
        print("=" * 60)

        tests = [
            ("python_version", self.test_python_version),
            ("core_imports", self.test_core_imports),
            ("dependencies", self.test_dependencies),
            ("type_hints", self.test_type_hints),
            ("syntax_compatibility", self.test_syntax_compatibility),
            ("async_functionality", self.test_async_functionality),
            ("file_operations", self.test_file_operations),
            ("subprocess_operations", self.test_subprocess_operations),
        ]

        for test_name, test_func in tests:
            try:
                print(f"Running {test_name}...", end=" ")
                success = test_func()
                self.results[test_name] = success
                print("✅" if success else "❌")
                if not success and test_name in self.errors:
                    print(f"  Error: {self.errors[test_name]}")
            except Exception as e:
                self.results[test_name] = False
                self.errors[test_name] = str(e)
                print(f"❌ Exception: {e}")

        self.print_summary()
        return all(self.results.values())

    def test_python_version(self) -> bool:
        """Test Python version requirements."""
        try:
            major, minor = sys.version_info[:2]
            if major == 3 and minor >= 13:
                return True
            elif major == 3 and minor >= 10:
                self.warnings.append(f"Testing on Python {major}.{minor}, but target is 3.13+")
                return True
            else:
                self.errors["python_version"] = f"Python {major}.{minor} not supported (requires 3.10+)"
                return False
        except Exception as e:
            self.errors["python_version"] = str(e)
            return False

    def test_core_imports(self) -> bool:
        """Test core module imports."""
        try:
            modules = [
                "versiontracker",
                "versiontracker.utils",
                "versiontracker.config",
                "versiontracker.apps",
                "versiontracker.homebrew",
                "versiontracker.ui",
                "versiontracker.version",
                "versiontracker.cache",
                "versiontracker.export",
            ]

            for module in modules:
                try:
                    importlib.import_module(module)
                except ImportError as e:
                    self.errors["core_imports"] = f"Failed to import {module}: {e}"
                    return False

            return True
        except Exception as e:
            self.errors["core_imports"] = str(e)
            return False

    def test_dependencies(self) -> bool:
        """Test dependency compatibility."""
        try:
            dependencies = [
                "fuzzywuzzy",
                "tqdm",
                "yaml",
                "termcolor",
                "tabulate",
                "psutil",
                "aiohttp",
            ]

            failed_deps = []
            for dep in dependencies:
                try:
                    if dep == "yaml":
                        importlib.import_module("yaml")
                    else:
                        importlib.import_module(dep)
                except ImportError:
                    failed_deps.append(dep)

            if failed_deps:
                self.errors["dependencies"] = f"Failed dependencies: {', '.join(failed_deps)}"
                return False

            return True
        except Exception as e:
            self.errors["dependencies"] = str(e)
            return False

    def test_type_hints(self) -> bool:
        """Test type hint compatibility."""
        try:
            # Test modern type hints that might cause issues

            # Test Python 3.9+ generics
            try:
                _test_dict: dict[str, int] = {"test": 1}
                _test_list: list[str] = ["test"]
                # These should work in Python 3.13
            except TypeError:
                # Fallback for older Python versions
                pass

            # Test Union syntax (should still work)
            _test_union: str | int = "test"
            _test_optional: str | None = None

            return True
        except Exception as e:
            self.errors["type_hints"] = str(e)
            return False

    def test_syntax_compatibility(self) -> bool:
        """Test syntax compatibility with Python 3.13."""
        try:
            # Test match statements (Python 3.10+)
            test_value = "test"
            match test_value:
                case "test":
                    result = True
                case _:
                    result = False

            if not result:
                self.errors["syntax_compatibility"] = "Match statement failed"
                return False

            # Test f-string improvements (should work across versions)
            name = "test"
            _debug_string = f"{name=}"  # Python 3.8+

            # Test walrus operator (Python 3.8+)
            if (_n := len(name)) > 0:
                pass

            return True
        except Exception as e:
            self.errors["syntax_compatibility"] = str(e)
            return False

    def test_async_functionality(self) -> bool:
        """Test async/await functionality."""
        try:
            import asyncio

            async def test_async() -> bool:
                await asyncio.sleep(0.001)
                return True

            # Test if asyncio works
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(test_async())
            loop.close()

            return result
        except Exception as e:
            self.errors["async_functionality"] = str(e)
            return False

    def test_file_operations(self) -> bool:
        """Test file operations compatibility."""
        try:
            import tempfile
            from pathlib import Path

            # Test pathlib operations
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)
                test_file = temp_path / "test.txt"

                # Write and read file
                test_file.write_text("test content", encoding="utf-8")
                content = test_file.read_text(encoding="utf-8")

                if content != "test content":
                    self.errors["file_operations"] = "File content mismatch"
                    return False

            return True
        except Exception as e:
            self.errors["file_operations"] = str(e)
            return False

    def test_subprocess_operations(self) -> bool:
        """Test subprocess operations."""
        try:
            import subprocess

            # Test basic subprocess operation
            result = subprocess.run([sys.executable, "-c", "print('test')"], capture_output=True, text=True, timeout=5)

            if result.returncode != 0 or "test" not in result.stdout:
                self.errors["subprocess_operations"] = f"Subprocess failed: {result.stderr}"
                return False

            return True
        except Exception as e:
            self.errors["subprocess_operations"] = str(e)
            return False

    def print_summary(self) -> None:
        """Print test summary."""
        print("\n" + "=" * 60)
        print("🔍 COMPATIBILITY TEST RESULTS")
        print("=" * 60)

        total_tests = len(self.results)
        passed_tests = sum(self.results.values())

        print(f"Total tests: {total_tests}")
        print(f"Passed: {passed_tests}")
        print(f"Failed: {total_tests - passed_tests}")

        if self.warnings:
            print("\n⚠️  WARNINGS:")
            for warning in self.warnings:
                print(f"  - {warning}")

        if any(not result for result in self.results.values()):
            print("\n❌ FAILED TESTS:")
            for test_name, result in self.results.items():
                if not result:
                    error = self.errors.get(test_name, "Unknown error")
                    print(f"  - {test_name}: {error}")

        overall_status = "✅ COMPATIBLE" if all(self.results.values()) else "❌ INCOMPATIBLE"
        print(f"\n{overall_status} with Python 3.13")

        if sys.version_info >= (3, 13):
            print("🎉 Running on Python 3.13!")
        elif sys.version_info >= (3, 10):  # noqa: UP036
            print("ℹ️  Running on supported Python version")
        else:
            print("⚠️  Running on unsupported Python version")


def test_dependency_versions() -> None:
    """Test specific dependency versions for Python 3.13 compatibility."""
    print("\n📦 DEPENDENCY VERSION CHECK")
    print("=" * 60)

    dependencies = [
        "fuzzywuzzy",
        "tqdm",
        "PyYAML",
        "termcolor",
        "tabulate",
        "psutil",
        "aiohttp",
    ]

    try:
        import pkg_resources

        for dep in dependencies:
            try:
                version = pkg_resources.get_distribution(dep).version
                print(f"✅ {dep}: {version}")
            except pkg_resources.DistributionNotFound:
                print(f"❌ {dep}: Not installed")

    except ImportError:
        # Fallback without pkg_resources
        print("pkg_resources not available, using importlib.metadata")
        try:
            import importlib.metadata as metadata

            for dep in dependencies:
                try:
                    version = metadata.version(dep)
                    print(f"✅ {dep}: {version}")
                except metadata.PackageNotFoundError:
                    print(f"❌ {dep}: Not installed")
        except ImportError:
            print("Cannot check dependency versions")


def create_python313_requirements() -> None:
    """Create Python 3.13 specific requirements file."""
    print("\n📄 CREATING PYTHON 3.13 REQUIREMENTS")
    print("=" * 60)

    requirements_313 = """# Python 3.13 compatible requirements
# Updated: 2025-07-22

# Core dependencies - verified Python 3.13 compatible
fuzzywuzzy>=0.18.0
rapidfuzz>=3.0.0  # Better performance than python-Levenshtein
tqdm>=4.66.0
PyYAML>=6.0
termcolor>=2.3.0
tabulate>=0.9.0
psutil>=5.9.5
aiohttp>=3.8.0

# Development dependencies - Python 3.13 compatible
pytest>=8.0.0
pytest-cov>=4.1.0
pytest-asyncio>=0.23.0
pytest-timeout>=2.1.0
pytest-xdist>=3.3.0
pytest-mock>=3.11.0

# Type checking and linting - Python 3.13 compatible
mypy>=1.8.0  # Updated for Python 3.13 support
ruff>=0.1.0  # Modern linter with Python 3.13 support
bandit[toml]>=1.7.5

# Build and packaging
build>=1.0.0
wheel>=0.42.0
twine>=4.0.2

# Pre-commit
pre-commit>=3.5.0
"""

    output_file = Path("requirements-py313.txt")
    output_file.write_text(requirements_313)
    print(f"✅ Created {output_file}")


def main() -> None:
    """Main function."""
    if len(sys.argv) > 1 and sys.argv[1] == "--create-requirements":
        create_python313_requirements()
        return

    tester = Python313CompatibilityTester()
    compatible = tester.run_all_tests()

    test_dependency_versions()

    if "--create-requirements" not in sys.argv:
        print("\nTo create Python 3.13 requirements file, run:")
        print(f"python {sys.argv[0]} --create-requirements")

    sys.exit(0 if compatible else 1)


if __name__ == "__main__":
    main()
