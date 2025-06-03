#!/usr/bin/env python3

from versiontracker.version import parse_version

test_cases = [
    "1.0+build.1",
    "1.0-rc.1",
    "1.2.3 (456)",
    "App v2.3.0 (build 1234)",
    "v1.0 build 1234",
]

print("Current parse_version behavior:")
for case in test_cases:
    result = parse_version(case)
    print(f"{repr(case):25} -> {result}")

print("\nExpected based on parameterized tests:")
expected = [
    ("1.0+build.1", (1, 0, 0, 1)),
    ("1.0-rc.1", (1, 0, 0, 1)),
    ("App v2.3.0 (build 1234)", (2, 3, 0)),  # from test_version.py
    ("v1.0 build 1234", (1, 0, 0, 1234)),  # from parameterized tests
]

for case, exp in expected:
    print(f"{repr(case):25} -> {exp}")
