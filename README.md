# Versiontracker Update tool for macOS
![PyPI - Python Version](https://img.shields.io/pypi/pyversions/requests) [![GitHub issues](https://img.shields.io/github/issues/docdyhr/httpcheck)](https://github.com/docdyhr/httpcheck/issues)  ![GitHub repo size](https://img.shields.io/github/repo-size/docdyhr/httpcheck) ![GitHub](https://img.shields.io/github/license/docdyhr/httpcheck)

* Name: Versiontracker
* Version: 0.1.1
* Programming language: Python 3
* Author: docdyhr
* Purpose: CLI versiontracker and update tool for macOS
* Release date: 21. Feb 2022 (Updated: March 2025)

## Overview

Versiontracker is a command-line tool for macOS that helps you manage applications installed outside of the App Store. It identifies applications that aren't managed through Apple's official channels and suggests which ones can be managed using Homebrew casks, making it easier to keep your applications up to date.

## Features

- List applications in `/Applications/` not updated by the App Store
- List all currently installed Homebrew casks
- Recommend which applications could be managed through Homebrew
- Fuzzy matching to identify applications across different naming conventions
- Parallel processing for faster operation
- Configurable blacklist to exclude specific applications
- Support for scanning additional application directories
- Secure command execution

## Requirements

- macOS (tested on 10.15 Catalina and later)
- Python 3.7 or later
- Homebrew package manager

## Installation

### Option 1: Clone the repository and install

```shell
# Clone the repository
git clone https://github.com/docdyhr/versiontracker.git
cd versiontracker

# Install requirements
python3 -m pip install -r requirements.txt --user

# Install the package (optional)
python3 -m pip install -e . --user
```

### Option 2: Set up a virtual environment

```shell
# Clone the repository
git clone https://github.com/docdyhr/versiontracker.git
cd versiontracker

# Create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install requirements
pip install -r requirements.txt

# Install the package (optional)
pip install -e .
```

## Usage

Versiontracker provides a simple command-line interface with several options:

```
usage: versiontracker [-h] [-D DEBUG] [--rate-limit RATE_LIMIT]
                     [--max-workers MAX_WORKERS] [--no-progress]
                     [--blacklist BLACKLIST] [--additional-dirs ADDITIONAL_DIRS]
                     [--similarity SIMILARITY] [-a | -b | -r | -V]

optional arguments:
  -h, --help            show this help message and exit
  -D DEBUG, --debug DEBUG
                        turn on DEBUG mode

Performance options:
  --rate-limit RATE_LIMIT
                        API rate limit in seconds (default: 3)
  --max-workers MAX_WORKERS
                        Maximum number of worker threads (default: 10)
  --no-progress         Disable progress bars

Filtering options:
  --blacklist BLACKLIST
                        Comma-separated list of applications to ignore
  --additional-dirs ADDITIONAL_DIRS
                        Colon-separated list of additional directories to scan for applications
  --similarity SIMILARITY
                        Similarity threshold for matching (0-100, default: 75)

  -a, --apps            return Apps in Applications/ that is not updated by App Store
  -b, --brews           return installable brews
  -r, --recommend       return recommendations for brew
  -V, --version         show program's version number and exit
```

## Usage Examples

### List all applications not updated by App Store

```shell
python3 versiontracker-cli.py --apps
```

Or if installed:

```shell
versiontracker --apps
```

### List all installed Homebrew casks

```shell
python3 versiontracker-cli.py --brews
```

### Get recommendations for Homebrew installations

```shell
python3 versiontracker-cli.py --recommend
```

### Run with debugging enabled

```shell
python3 versiontracker-cli.py --debug --recommend
```

## Configuration via Environment Variables

You can configure VersionTracker using environment variables:

```shell
# Set the API rate limit (seconds)
export VERSIONTRACKER_API_RATE_LIMIT=5

# Enable debug mode
export VERSIONTRACKER_DEBUG=true

# Set maximum worker threads
export VERSIONTRACKER_MAX_WORKERS=8

# Configure similarity threshold (0-100)
export VERSIONTRACKER_SIMILARITY_THRESHOLD=80

# Add applications to blacklist (comma-separated)
export VERSIONTRACKER_BLACKLIST=Firefox,Chrome,Safari

# Add additional application directories (colon-separated)
export VERSIONTRACKER_ADDITIONAL_APP_DIRS=/Users/username/Applications:/opt/Applications

# Disable progress bars
export VERSIONTRACKER_PROGRESS_BARS=false
```

## Testing

VersionTracker includes a test suite to ensure functionality. To run the tests:

```shell
# Activate your virtual environment if necessary
source .venv/bin/activate

# Install test dependencies
pip install pytest pytest-cov

# Run tests with coverage
pytest
```

This will run all tests and generate a coverage report showing which parts of the code are tested.

## Continuous Integration

VersionTracker uses GitHub Actions for continuous integration and deployment:

- **Testing**: Automatically runs the test suite on multiple Python versions
- **Linting**: Ensures code quality with flake8, black, and isort
- **Releases**: Automatically publishes new versions to PyPI when a release is created

The CI/CD pipeline helps maintain code quality and ensures that the application is always in a deployable state.

## Background

On macOS, not all apps are installed through the App Store. If you have many apps downloaded outside of Apple's App Store, it can be a hassle to keep them all updated - especially those you don't use every day. While download sites like macupdate.com or macdownload.com exist, they may not prioritize user privacy.

Package managers like Homebrew and MacPort make it possible to install and maintain many popular applications through the command line. Versiontracker helps bridge the gap between your current applications and what could be managed through Homebrew.

## Planned Improvements

- Add more package managers support (MacPorts, etc.)
- Add automatic update capabilities for Homebrew-manageable applications
- Improve performance with parallel API requests
- Add GUI interface
- Add support for application blacklisting
- Generate reports of outdated applications
- Add support for scanning custom application directories

## License

[MIT](https://github.com/docdyhr/versiontracker/blob/master/LICENSE)
