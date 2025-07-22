# CI/CD Pipeline Guide

This document outlines the CI/CD pipeline for VersionTracker, including workflows, best practices, and troubleshooting guidelines.

## Pipeline Overview

VersionTracker uses GitHub Actions for continuous integration and deployment with the following workflows:

### 1. Main CI Pipeline (`ci.yml`)

**Triggers**: Push/PR to main/master branches, manual dispatch
**Purpose**: Comprehensive testing, linting, security checks, and package building

#### Jobs

- **Test**: Multi-platform testing (macOS, Ubuntu) across Python 3.8-3.12
- **Lint**: Code linting and formatting with Ruff, type checking with MyPy
- **Security**: Security analysis with Bandit, Safety, and pip-audit
- **Quality**: Code quality analysis with pydocstyle, radon, and vulture
- **Build**: Package building and verification
- **CI Summary**: Consolidated status reporting

#### Key Features

- Pip caching for faster builds
- Parallel execution across multiple Python versions
- Coverage reporting to Codecov
- Artifact uploads for all reports
- Smart failure handling with detailed summaries

### 2. Lint Pipeline (`lint.yml`)

**Triggers**: Push/PR to main/master branches, manual dispatch
**Purpose**: Fast linting and formatting checks

#### Checks

- Ruff linting with GitHub annotations
- Ruff format checking
- MyPy type checking with XML report generation

### 3. Security Pipeline (`security.yml`)

**Triggers**: Push/PR to main/master branches, manual dispatch, weekly schedule
**Purpose**: Comprehensive security analysis

#### Security Tools

- **Bandit**: Python security linter
- **Safety**: Dependency vulnerability scanning
- **pip-audit**: Package vulnerability detection
- **TruffleHog**: Secret detection
- **Scheduled scans**: Weekly security audits

#### Security Pipeline Features

- JSON report generation for all tools
- Security summary with issue counts
- Artifact upload for detailed analysis

### 4. CodeQL Analysis (`codeql-analysis.yml`)

**Triggers**: Push/PR to main/master branches, manual dispatch, weekly schedule  
**Purpose**: Deep static analysis using CodeQL  

#### CodeQL Analysis Features

- Initialises the CodeQL environment and builds the CodeQL database for Python.  
- Executes CodeQL queries for `security-and-quality` across the repository.  
- Publishes results automatically to the GitHub Code Scanning tab.  
- Scheduled weekly scans on Sundays at 03:00 UTC for early detection of vulnerabilities.  

### 5. Release Pipeline (`release.yml`)

**Triggers**: GitHub releases, manual workflow dispatch
**Purpose**: Automated package building, testing, and PyPI publishing

#### Release Stages

##### Validation

- Semantic version format validation
- Changelog entry verification
- Version consistency checks

##### Pre-Release Checks

- Full test suite execution
- Code quality verification
- Security scanning
- Package metadata validation

##### Build and Test

- Multi-platform package building
- Installation testing across Python versions
- CLI functionality verification

##### Publishing

- Test PyPI for pre-releases
- Production PyPI for stable releases
- Package integrity verification

##### Verification

- Post-publish installation testing
- Version verification
- CLI functionality testing

## Configuration Files

### Test Configuration

- **pytest-ci.ini**: CI-optimized pytest configuration
  - Coverage reporting with 85% minimum threshold
  - Parallel execution support
  - Comprehensive test markers
  - Performance optimizations

- **.coveragerc**: Coverage configuration
  - Source code coverage tracking
  - HTML/XML/JSON report generation
  - Exclusion patterns for non-critical code

### Type Checking

- **mypy.ini**: Strict type checking configuration
  - Gradual typing adoption
  - Module-specific settings
  - Platform-specific configurations

### Security

- **bandit.yaml**: Security linting configuration
  - Custom skip rules for false positives
  - Directory exclusions
  - Confidence and severity settings

## Badge Status

The README includes comprehensive badges for:

### Build Status

- CI Pipeline status
- Lint status
- Security status
- Release status

### Package Information

- PyPI version and downloads
- Python version compatibility
- Package status

### Quality Metrics

- Code coverage (Codecov)
- Code style (Ruff)
- Security analysis (Bandit)

### Repository Statistics

- Issues, forks, stars
- Last commit, code size
- License information

## Best Practices

### 1. Branch Protection

Configure branch protection rules for main/master:

- Require status checks to pass
- Require branches to be up to date
- Require review from code owners
- Restrict pushes to admin users

### 2. Secrets Management

Required repository secrets:

- `CODECOV_TOKEN`: For coverage reporting
- PyPI publishing uses trusted publishing (no token needed)

### 3. Dependencies

- Use pip caching for faster builds
- Pin development dependencies with version ranges
- Regular dependency updates via security scanning

### 4. Performance Optimization

- Matrix strategy for efficient testing
- Artifact caching between jobs
- Smart exclusions to reduce CI time
- Parallel test execution where possible

## Troubleshooting

### Common Issues

#### Test Failures

1. Check test logs in CI Summary
2. Download test artifacts for detailed analysis
3. Run tests locally with same Python version
4. Check for platform-specific issues (macOS vs Ubuntu)

#### Coverage Issues

1. Minimum coverage threshold: 85%
2. Check `.coveragerc` exclusions
3. Review coverage reports in artifacts
4. Add tests for uncovered code paths

#### Security Failures

1. Review Bandit report for false positives
2. Update `bandit.yaml` skip rules if needed
3. Check Safety/pip-audit for dependency vulnerabilities
4. Update requirements.txt for security patches

#### Release Failures

1. Verify version format (semantic versioning)
2. Check package metadata consistency
3. Ensure all tests pass before release
4. Verify PyPI credentials and permissions

### Debugging Steps

1. **Check Workflow Status**: GitHub Actions tab
2. **Review Logs**: Click on failed job for detailed logs
3. **Download Artifacts**: Reports and test results
4. **Local Reproduction**: Use same Python version and dependencies
5. **Check Dependencies**: Ensure requirements.txt is up to date

### Performance Monitoring

The CI pipeline includes performance monitoring:

- **Build times**: Tracked across jobs
- **Test execution**: Duration reporting
- **Artifact sizes**: Package size monitoring
- **Resource usage**: Memory and CPU tracking

## Maintenance

### Regular Tasks

- **Weekly**: Review security scan results
- **Monthly**: Update GitHub Actions versions
- **Quarterly**: Review and update Python version matrix
- **Release**: Update CHANGELOG.md and version numbers

### Updates

- Keep GitHub Actions up to date
- Monitor for new security tools
- Review and optimize CI performance
- Update Python version support as needed

## Development Workflow

### Pre-commit Checks

Before committing code:

```bash
# Run linting
ruff check .
ruff format .

# Run type checking
mypy --config-file=mypy.ini versiontracker

# Run tests with coverage
pytest -c pytest-ci.ini --cov=versiontracker
```

### Pull Request Process

1. Create feature branch
2. Implement changes with tests
3. Ensure CI passes locally
4. Create pull request
5. Address review feedback
6. Merge after CI approval

### Release Process

1. Update version in `versiontracker/__init__.py`
2. Update CHANGELOG.md
3. Create GitHub release with semantic version tag
4. CI automatically builds and publishes to PyPI
5. Verify package availability and functionality

This comprehensive CI/CD pipeline ensures code quality, security, and reliable releases while maintaining developer productivity.
