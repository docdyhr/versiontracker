# PyPI Publishing Guide

This document describes how to publish **macversiontracker** to PyPI using GitHub's Trusted Publisher workflow.

## Package Information

- **PyPI Project Name**: `macversiontracker`
- **Repository**: `docdyhr/versiontracker`
- **Publishing Method**: GitHub Actions with Trusted Publishers (OIDC)

## Prerequisites

### 1. Configure PyPI Trusted Publisher

Before you can publish, you must configure the Trusted Publisher on PyPI:

1. Go to <https://pypi.org/manage/account/publishing/>
2. Click "Add a new pending publisher"
3. Fill in the form with these exact values:

   ```text
   PyPI Project Name: macversiontracker
   Owner: docdyhr
   Repository name: versiontracker
   Workflow name: publish-pypi.yml
   Environment name: pypi
   ```

4. Click "Add"

### 2. Configure TestPyPI Trusted Publisher (Optional but Recommended)

For testing before production releases:

1. Go to <https://test.pypi.org/manage/account/publishing/>
2. Click "Add a new pending publisher"
3. Fill in the form with these exact values:

   ```text
   PyPI Project Name: macversiontracker
   Owner: docdyhr
   Repository name: versiontracker
   Workflow name: publish-pypi.yml
   Environment name: testpypi
   ```

4. Click "Add"

## Publishing Methods

### Method 1: Publish via GitHub Release (Recommended)

This is the primary method for production releases:

1. **Update version in `pyproject.toml`**:

   ```toml
   version = "0.9.0"  # Increment version
   ```

2. **Update CHANGELOG.md** with release notes

3. **Commit and push changes**:

   ```bash
   git add pyproject.toml CHANGELOG.md
   git commit -m "chore: Bump version to 0.9.0"
   git push
   ```

4. **Create a git tag**:

   ```bash
   git tag v0.9.0
   git push origin v0.9.0
   ```

5. **Create GitHub Release**:

   ```bash
   gh release create v0.9.0 \
     --title "v0.9.0 - Release Title" \
     --notes "Release notes here"
   ```

6. **Automated Process**:
   - GitHub Actions workflow triggers automatically
   - Builds the package (wheel + sdist)
   - Publishes to PyPI using Trusted Publisher
   - Signs distributions with Sigstore
   - Uploads artifacts to GitHub Release

### Method 2: Manual Publish via Workflow Dispatch

For testing or special releases:

1. Go to: <https://github.com/docdyhr/versiontracker/actions/workflows/publish-pypi.yml>
2. Click "Run workflow"
3. Select:
   - **Branch**: `master` (or your target branch)
   - **Environment**: `testpypi` or `pypi`
4. Click "Run workflow"

**For TestPyPI**:

- URL: <https://test.pypi.org/project/macversiontracker/>
- Test installation: `pip install --index-url https://test.pypi.org/simple/ macversiontracker`

**For Production PyPI**:

- URL: <https://pypi.org/project/macversiontracker/>
- Installation: `pip install macversiontracker`

## Workflow Details

The publishing workflow (`.github/workflows/publish-pypi.yml`) performs these steps:

### Build Job

1. Checkout code
2. Set up Python 3.12
3. Install build tools (`build`, `twine`)
4. Build package distributions
5. Check distributions with `twine check`
6. Upload as artifacts

### Publish Jobs

**publish-to-testpypi**:

- Triggered by: Manual workflow dispatch with `environment=testpypi`
- Downloads build artifacts
- Publishes to test.pypi.org
- Uses OIDC authentication (no API tokens needed)

**publish-to-pypi**:

- Triggered by: GitHub Release OR manual workflow dispatch with `environment=pypi`
- Downloads build artifacts
- Publishes to pypi.org
- Uses OIDC authentication (no API tokens needed)

**github-release** (GitHub Releases only):

- Downloads build artifacts
- Signs with Sigstore for provenance
- Uploads signed artifacts to GitHub Release

## Version Numbering

Follow [Semantic Versioning](https://semver.org/):

- **MAJOR.MINOR.PATCH** (e.g., `1.0.0`)
  - **MAJOR**: Breaking changes
  - **MINOR**: New features (backwards compatible)
  - **PATCH**: Bug fixes (backwards compatible)

Examples:

- `0.8.1` → `0.8.2` (bug fix)
- `0.8.1` → `0.9.0` (new feature)
- `0.9.0` → `1.0.0` (first stable release)

## Pre-Release Testing

Before publishing to production PyPI:

1. **Test locally**:

   ```bash
   python -m build
   twine check dist/*
   pip install dist/macversiontracker-*.whl
   versiontracker --version
   ```

2. **Publish to TestPyPI**:
   - Use workflow dispatch with `environment=testpypi`
   - Test installation from TestPyPI

3. **Create GitHub Release** when ready for production

## Troubleshooting

### Issue: "Trusted publisher configuration mismatch"

**Solution**: Verify that:

- PyPI project name is exactly `macversiontracker`
- Repository is `docdyhr/versiontracker`
- Workflow file is `.github/workflows/publish-pypi.yml`
- Environment name matches (`pypi` or `testpypi`)

### Issue: "Project already exists but you don't have permissions"

**Solution**:

- The package name may be taken
- Contact PyPI support if you own the project
- Consider a different package name

### Issue: "Build artifacts not found"

**Solution**:

- Ensure the `build` job completed successfully
- Check that `python-package-distributions` artifact exists
- Re-run the workflow

### Issue: "Version already exists on PyPI"

**Solution**:

- You cannot re-upload the same version
- Increment the version number in `pyproject.toml`
- PyPI versions are immutable

## Security Notes

### Trusted Publishers (OIDC)

This project uses PyPI's Trusted Publisher feature which:

- **No API tokens required**: Authentication via GitHub OIDC
- **Automatic credential management**: GitHub generates short-lived tokens
- **Enhanced security**: No long-lived secrets in repository
- **Audit trail**: All publishes logged with GitHub identity

### Sigstore Signing

Production releases are automatically signed with Sigstore, providing:

- **Cryptographic proof** of artifact authenticity
- **Transparency log** entries for verification
- **Signature files** (`.sigstore`) uploaded to GitHub Releases

## Monitoring

After publishing:

1. **Verify on PyPI**: <https://pypi.org/project/macversiontracker/>
2. **Check installation**: `pip install macversiontracker`
3. **Monitor downloads**: <https://pepy.tech/project/macversiontracker> (if available)
4. **GitHub Release**: <https://github.com/docdyhr/versiontracker/releases>

## Additional Resources

- [PyPI Trusted Publishers Guide](https://docs.pypi.org/trusted-publishers/)
- [GitHub Actions PyPI Publish Action](https://github.com/pypa/gh-action-pypi-publish)
- [Python Packaging User Guide](https://packaging.python.org/)
- [Semantic Versioning](https://semver.org/)

---

**Last Updated**: 2026-01-09
**Current Version**: 0.8.1
**Status**: Ready for first publication
