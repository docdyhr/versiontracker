#!/usr/bin/env python3
"""Setup script for VersionTracker."""

import re
from pathlib import Path

from setuptools import find_packages, setup


# Read the version from the versiontracker/__init__.py file
def get_version():
    """Parse version number from __init__.py."""
    init_file = Path(__file__).parent / "versiontracker" / "__init__.py"
    with open(init_file, encoding="utf-8") as f:
        for line in f:
            match = re.match(r'^__version__\s*=\s*[\'"]([^\'"]*)[\'"]', line)
            if match:
                return match.group(1)
    raise RuntimeError("Version not found in __init__.py")

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

try:
    with open("requirements.txt", "r", encoding="utf-8") as fh:
        requirements = fh.read().splitlines()
except FileNotFoundError:
    requirements = ["PyYAML"]

setup(
    name="versiontracker",
    version=get_version(),
    author="docdyhr",
    author_email="thomas@dyhr.com",
    description="CLI versiontracker and update tool for macOS",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/docdyhr/versiontracker",
    packages=find_packages(),
    install_requires=requirements,
    classifiers=[
        "Development Status :: 4 - Beta",
        "Environment :: Console",
        "Intended Audience :: Developers",
        "Intended Audience :: System Administrators",
        "License :: OSI Approved :: MIT License",
        "Operating System :: MacOS :: MacOS X",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: System :: Systems Administration",
        "Topic :: Utilities",
    ],
    python_requires=">=3.8",
    entry_points={
        "console_scripts": [
            "versiontracker=versiontracker.__main__:main",
        ],
    },
)
