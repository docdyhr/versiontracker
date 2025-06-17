# CI/CD and Pre-commit Compatibility Guide

## Overview

This document outlines the comprehensive analysis and fixes implemented to ensure full compatibility between the CI/CD pipeline and pre-commit hooks, with specific focus on ruff version pinning and consistent tool usage across environments.

## 🔍 Analysis Results

### Initial Issues Identified

1. **Ruff Version Inconsistencies**
   - `constraints.txt`: `ruff>=0.3.0,<1.0.0` (range)
   - `requirements-dev.txt`: `ruff>=0.4.0` (range)
   - `.pre-commit-config.yaml`: `v0.11.12` (pinned)
   - Installed version: `0.11.10` (outdated)

2. **Configuration Compatibility**
   - Pre-commit and CI used different ruff command arguments
   - No validation mechanism for version consistency
   - Potential for drift between local and CI environments

## ✅ Fixes Implemented

### 1. Ruff Version Pinning

**Problem**: Inconsistent version specifications across configuration files could lead to different behavior between local development and CI environments.

**Solution**: Pinned ruff to exact version `0.11.12` across all configuration files:

#### Updated `constraints.txt`

```diff
- ruff>=0.3.0,<1.0.0
+ ruff==0.11.12
```

#### Updated `requirements-dev.txt`

```diff
- ruff>=0.4.0  # Replaces flake8, black, isort
+ ruff==0.11.12  # Replaces flake8, black, isort
```

#### Verified `.pre-commit-config.yaml`

```yaml
- repo: https://github.com/astral-sh/ruff-pre-commit
  rev: v0.11.12  # ✅ Already correctly pinned
  hooks:
    - id: ruff
      args: [--fix, --exit-non-zero-on-fix]
    - id: ruff-format
```

### 2. MyPy Version Pinning

**Problem**: Similar inconsistent version specifications for mypy across configuration files.

**Solution**: Pinned mypy to exact version `1.16.0` across all configuration files:

#### Updated `constraints.txt`

```diff
- mypy>=1.0.0,<2.0.0
+ mypy==1.16.0
```

#### Updated `requirements-dev.txt`

```diff
- mypy>=1.2.0
+ mypy==1.16.0
```

#### Verified `.pre-commit-config.yaml`

```yaml
- repo: https://github.com/pre-commit/mirrors-mypy
  rev: v1.16.0  # ✅ Already correctly pinned
  hooks:
    - id: mypy
      additional_dependencies:
        [
          types-PyYAML,
          types-tabulate,
          types-termcolor,
          types-requests,
          types-psutil,
          types-tqdm,
        ]
      args: [--config-file=mypy.ini, --platform=darwin]
      exclude: ^(tests/|docs/)
```

### 3. Type Stub Synchronization

**Problem**: Inconsistent type stub dependencies between pre-commit and requirements-dev.txt.

**Solution**: Synchronized all type stubs across both configurations:

- Added missing `types-psutil` and `types-tqdm` to pre-commit
- Added missing `types-termcolor` to requirements-dev.txt

### 4. Environment Synchronization

**Updated local installation**:

```bash
pip install ruff==0.11.12 mypy==1.16.0
```

**Result**: All environments now use identical tool versions.

### 5. Validation Script Creation

**Created**: `tools/validate_ci_precommit.py`

**Features**:

- Validates ruff version consistency across all config files
- Checks pre-commit hook configuration
- Validates CI workflow configuration
- Tests tool compatibility
- Validates configuration file syntax
- Provides comprehensive reporting

**Key validation checks**:

- Ruff version consistency across `constraints.txt`, `requirements-dev.txt`, `.pre-commit-config.yaml`, and installed version
- MyPy version consistency across the same configuration files
- Presence of required ruff hooks (`ruff`, `ruff-format`) and mypy hooks
- Type stub consistency between pre-commit and requirements files
- CI workflow existence and tool usage
- Tool availability and functionality
- Configuration file syntax validation

## 🔧 Configuration Compatibility Matrix

### Command Argument Alignment

| Environment | Ruff Check Command | Ruff Format Command | MyPy Command | Exit Behavior |
|-------------|-------------------|---------------------|--------------|---------------|
| **Pre-commit** | `ruff --fix --exit-non-zero-on-fix` | `ruff-format` | `mypy --config-file=mypy.ini --platform=darwin` | Fail on violations |
| **CI Lint Job** | `ruff check . --output-format=github` | `ruff format --check .` | `mypy --config-file=mypy.ini versiontracker` | Non-blocking (warn only) |
| **CI Main Job** | `ruff check . --output-format=github` | `ruff format --check .` | `mypy --config-file=mypy.ini versiontracker` | Non-blocking (warn only) |

### Tool Configuration Files

Both environments use the same configuration files:

#### Ruff Configuration (`pyproject.toml`)

```toml
[tool.ruff]
target-version = "py39"
exclude = [".venv", "build", "dist", ...]

[tool.ruff.lint]
select = ["E", "F", "I"]
ignore = ["E203", "E501", "F401", "F811", "F821", "F841"]
fixable = ["ALL"]

[tool.ruff.format]
quote-style = "double"
indent-style = "space"
```

#### MyPy Configuration (`mypy.ini`)

```ini
[mypy]
python_version = 3.9
warn_return_any = False
disallow_untyped_defs = False
ignore_missing_imports = True
platform = darwin
follow_imports = silent

# Module specific settings
[mypy-versiontracker.*]
ignore_errors = False
warn_return_any = False
```

#### Type Stub Versions

- `types-PyYAML>=6.0.0`
- `types-tabulate>=0.9.0`
- `types-termcolor>=1.1.0`
- `types-requests>=2.32.0`
- `types-psutil>=5.9.0`
- `types-tqdm>=4.67.0`

## 🚀 Workflow Integration

### Pre-commit Hooks Execution Order

1. **File formatting checks** (trailing whitespace, end-of-file, etc.)
2. **Ruff linting** (`ruff --fix --exit-non-zero-on-fix`)
3. **Ruff formatting** (`ruff-format`)
4. **Type checking** (mypy - excludes tests/ and docs/)
5. **Security scanning** (bandit)
6. **Documentation checks** (pydocstyle)
7. **Additional validations**

### CI Pipeline Integration

1. **Lint Job** (`lint.yml` + `ci.yml`):

   ```yaml
   - name: Run Ruff linting
     run: |
       ruff check . --output-format=github
       ruff format --check .

   - name: Run type checking
     run: |
       mypy --config-file=mypy.ini versiontracker --junit-xml=mypy-report.xml || echo "MyPy found issues but continuing CI"
   ```

2. **Test Job** (runs in parallel):
   - Multi-platform testing (macOS, Ubuntu)
   - Multi-version Python support (3.9-3.12)
   - Coverage reporting

3. **Security Job** (runs in parallel):
   - Bandit security scanning
   - Safety dependency checking
   - pip-audit vulnerability scanning

## 📊 Validation Results

### Successful Validation Output

```
🔍 Validating CI/CD and pre-commit compatibility...
============================================================

📋 Ruff version consistency...
   Ruff version: 0.11.12
✅ Ruff version consistency: PASSED

📋 MyPy version consistency...
   Mypy version: 1.16.0
✅ MyPy version consistency: PASSED

📋 Pre-commit configuration...
   Found ruff hooks: ['ruff', 'ruff-format']
   Found mypy hooks: ['mypy']
✅ Pre-commit configuration: PASSED

📋 CI workflow configuration...
   Found workflows: ['release.yml', 'security.yml', 'lint.yml', 'ci.yml']
✅ CI workflow configuration: PASSED

📋 Tool compatibility...
   ruff: ✓
   mypy: ✓
   pre-commit: ✓
   Type stubs: 6 in pre-commit, 6 in requirements-dev.txt
✅ Tool compatibility: PASSED

📋 Configuration file validity...
   .pre-commit-config.yaml: ✓
   pyproject.toml: ✓
   .github/workflows/ci.yml: ✓
   .github/workflows/lint.yml: ✓
✅ Configuration file validity: PASSED

🎉 All checks passed! CI/CD and pre-commit are fully compatible.
```

## 🔒 Version Management Strategy

### Current Approach: Exact Version Pinning

**Rationale**:

- Ensures identical behavior across all environments
- Prevents unexpected changes from minor version updates
- Provides predictable and reproducible builds
- Eliminates potential compatibility issues
- Maintains type checking consistency with exact mypy and type stub versions

**Trade-offs**:

- Requires manual updates for new tool versions
- May miss automatic bug fixes
- Needs coordination when updating
- Type stub updates must be synchronized across configurations

### Update Process

1. **Dependabot Integration**:
   - Automatically creates PRs for version updates
   - Configured for weekly checks
   - Includes both pip dependencies and GitHub Actions

2. **Manual Update Process**:

   ```bash
   # 1. Update pre-commit hooks
   pre-commit autoupdate

   # 2. Update requirements files
   # Edit constraints.txt and requirements-dev.txt
   # Ensure ruff and mypy versions match pre-commit
   # Synchronize type stub versions

   # 3. Install updated versions
   pip install -r requirements-dev.txt

   # 4. Validate compatibility
   python tools/validate_ci_precommit.py

   # 5. Test changes
   pre-commit run --all-files
   ```

## 🛡️ Quality Assurance

### Continuous Validation

1. **Pre-commit Hook**: Runs on every commit
2. **CI Pipeline**: Runs on every push/PR
3. **Validation Script**: Can be run manually anytime
4. **Dependabot**: Monitors for updates weekly

### Testing Strategy

```bash
# Local testing workflow
git add .
pre-commit run --all-files
python tools/validate_ci_precommit.py
pytest

# Individual tool testing
ruff check . --output-format=github
ruff format --check .
mypy --config-file=mypy.ini versiontracker
```

### CI Testing Matrix

- **Operating Systems**: macOS (primary), Ubuntu (compatibility)
- **Python Versions**: 3.9, 3.10, 3.11, 3.12
- **Tool Versions**: Pinned for consistency
  - Ruff: 0.11.12
  - MyPy: 1.16.0
  - Type Stubs: Synchronized across environments

## 📋 Maintenance Checklist

### Weekly Tasks

- [ ] Review Dependabot PRs for tool updates
- [ ] Check CI performance metrics
- [ ] Monitor for new ruff features/changes

### Monthly Tasks

- [ ] Run full validation suite
- [ ] Review and update version pins if needed
- [ ] Check for deprecated configurations

### Before Releases

- [ ] Run `python tools/validate_ci_precommit.py`
- [ ] Verify all CI jobs pass
- [ ] Confirm pre-commit hooks work correctly
- [ ] Test on clean environment

## 🚨 Troubleshooting

### Common Issues

1. **Tool Version Mismatch Error**:

   ```bash
   # Solution: Update all version specifications
   pip install ruff==0.11.12 mypy==1.16.0
   # Update constraints.txt and requirements-dev.txt
   python tools/validate_ci_precommit.py
   ```

2. **Type Stub Inconsistency**:

   ```bash
   # Solution: Synchronize type stubs
   # Update .pre-commit-config.yaml additional_dependencies
   # Update requirements-dev.txt type stub versions
   python tools/validate_ci_precommit.py
   ```

3. **Pre-commit Hook Failures**:

   ```bash
   # Solution: Update hooks and retry
   pre-commit autoupdate
   pre-commit run --all-files
   ```

4. **CI Failures**:

   ```bash
   # Solution: Check for configuration drift
   python tools/validate_ci_precommit.py
   # Compare local and CI environments
   ```

### Emergency Recovery

If compatibility breaks:

1. Revert to known good versions: `ruff==0.11.12`, `mypy==1.16.0`
2. Restore synchronized type stub versions
3. Run validation script to confirm fix
4. Update all configuration files to match
5. Test thoroughly before pushing

## 🔮 Future Enhancements

### Planned Improvements

1. **Automated Version Synchronization**:
   - Script to update all files simultaneously
   - Integration with version management tools
   - Automatic type stub version updates

2. **Enhanced Validation**:
   - Performance benchmarking
   - Configuration drift detection
   - Cross-platform validation
   - Type coverage reporting

3. **Developer Experience**:
   - VS Code integration
   - Development container configuration
   - Quick setup scripts
   - MyPy error suppression strategies

### Configuration Evolution

- Monitor ruff and mypy development for breaking changes
- Evaluate new linting rules, formatters, and type checking features
- Consider integration with additional tools (e.g., pyright)
- Maintain backwards compatibility when possible
- Track type stub updates and new type checking capabilities

## 📚 References

- [Ruff Configuration Documentation](https://docs.astral.sh/ruff/configuration/)
- [Pre-commit Hooks Documentation](https://pre-commit.com/)
- [GitHub Actions Workflow Syntax](https://docs.github.com/en/actions/using-workflows/workflow-syntax-for-github-actions)
- [Project CI/CD Guide](.github/CI_CD_GUIDE.md)

---

**Last Updated**: December 2024  
**Ruff Version**: 0.11.12  
**MyPy Version**: 1.16.0  
**Type Stubs**: 6 synchronized stubs  
**Validation Status**: ✅ All Compatible
