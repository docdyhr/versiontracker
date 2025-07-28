"""
Python 3.13 Type Hints Examples

This file demonstrates modern type hint syntax available in Python 3.13
while maintaining compatibility with older versions through conditional imports.
"""

import sys

# Import identity function based on Python version
if sys.version_info >= (3, 12):
    from .identity_py312 import identity
else:
    from .identity_legacy import identity

# Example usage
def example_usage():
    """Demonstrate identity function usage."""
    print("String identity:", identity("hello"))
    print("Integer identity:", identity(42))
    print("List identity:", identity([1, 2, 3]))

# Additional Python 3.13 features
if sys.version_info >= (3, 13):
    # Python 3.13+ specific features can be added here
    pass

if __name__ == "__main__":
    example_usage()
