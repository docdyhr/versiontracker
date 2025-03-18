#!/usr/bin/env python3
"""Setup script for VersionTracker."""

from setuptools import find_packages, setup

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

try:
    with open("requirements.txt", "r", encoding="utf-8") as fh:
        requirements = fh.read().splitlines()
except FileNotFoundError:
    requirements = ["PyYAML"]

setup(
    name="versiontracker",
    version="0.3.1",
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
