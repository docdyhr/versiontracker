#!/usr/bin/env python3

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from versiontracker.version import get_version_difference, parse_version

# Test the specific case that's failing
version1 = "1.0.0-alpha"
version2 = "1.0.0-beta"

print(f"Parsing '{version1}': {parse_version(version1)}")
print(f"Parsing '{version2}': {parse_version(version2)}")

result = get_version_difference(version1, version2)
print(f"Version difference: {result}")
print("Expected: (0, 0, 0)")
print(f"Actual length: {len(result) if result else 'None'}")
