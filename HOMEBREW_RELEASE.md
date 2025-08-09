# Homebrew Release Guide

This document outlines the process for releasing VersionTracker to Homebrew.

## Overview

VersionTracker is distributed through Homebrew using a custom formula (`versiontracker.rb`) that allows users to
easily install and manage the application.

## Release Process

### 1. Prerequisites

- Ensure all tests pass locally and in CI
- Version has been bumped in `pyproject.toml`
- Changes have been documented in `CHANGELOG.md`
- All code changes are committed and pushed

### 2. GitHub Release

The Homebrew release is automatically triggered when a new GitHub release is created:

1. Create a new release on GitHub with proper semantic versioning (e.g., `v1.2.3`)
2. The `release-homebrew.yml` workflow will automatically:
   - Download the release tarball
   - Calculate the SHA256 checksum
   - Update the Homebrew formula
   - Test the formula
   - Create a pull request to update the formula

### 3. Manual Release (if needed)

If automatic release fails, you can manually update the formula:

```bash
# 1. Update the version and SHA256 in versiontracker.rb
# 2. Test the formula locally
brew install --build-from-source ./versiontracker.rb
brew test versiontracker
brew uninstall versiontracker

# 3. Commit and push the changes
git add versiontracker.rb
git commit -m "Update Homebrew formula to v1.2.3"
git push origin main
```

## Formula Structure

The `versiontracker.rb` formula includes:

- **Version**: Automatically updated by CI
- **URL**: Points to GitHub release tarball
- **SHA256**: Checksum for integrity verification
- **Dependencies**: Python 3.8+ and required system libraries
- **Install Process**: Pip installation with proper prefix handling
- **Test**: Basic functionality verification

## Dependencies

The formula manages these dependencies:

- `python@3.8` - Minimum Python version
- `python-certifi` - SSL certificate handling
- `python-tabulate` - Table formatting
- Python packages installed via pip during build

## Installation Paths

- **Executable**: `/usr/local/bin/versiontracker`
- **Python packages**: Managed by Homebrew's Python framework
- **Configuration**: User's home directory (`~/.versiontracker/`)

## Testing

### Automated Testing

The CI workflow automatically tests:

- Formula syntax validation
- Installation process
- Basic command execution
- Help output verification
- Uninstallation cleanup

### Manual Testing

To manually test a formula update:

```bash
# Install from local formula
brew install --build-from-source ./versiontracker.rb

# Test basic functionality
versiontracker --help
versiontracker --version

# Test core features
versiontracker list
versiontracker recommend

# Clean up
brew uninstall versiontracker
```

## Troubleshooting

### Common Issues

1. **SHA256 Mismatch**
   - Solution: Regenerate checksum using `shasum -a 256 <tarball>`

2. **Python Dependency Conflicts**
   - Solution: Ensure formula uses correct Python version pinning

3. **Installation Path Issues**
   - Solution: Verify `bin.install` commands in formula

4. **Permission Errors**
   - Solution: Check file permissions in release tarball

### Debugging

To debug formula installation:

```bash
# Install with verbose output
brew install --verbose --build-from-source ./versiontracker.rb

# Check installation logs
brew list versiontracker
brew deps versiontracker

# Validate formula
brew audit --strict versiontracker.rb
```

## Maintenance

### Regular Updates

1. **Dependency Updates**: Monitor for updates to core dependencies
2. **Formula Improvements**: Enhance installation process and testing
3. **Compatibility**: Ensure compatibility with new Homebrew versions

### Version Management

- Use semantic versioning (MAJOR.MINOR.PATCH)
- Tag releases properly in Git
- Maintain backward compatibility when possible
- Document breaking changes clearly

## Security Considerations

- **Checksum Verification**: Always verify SHA256 checksums
- **Dependency Pinning**: Use specific versions for critical dependencies
- **Source Verification**: Ensure tarball sources are authentic
- **Permission Model**: Follow Homebrew security best practices

## Support

For Homebrew-specific issues:

1. Check the [Homebrew documentation](https://docs.brew.sh/)
2. Review formula audit results
3. Test on multiple macOS versions
4. Consult Homebrew community guidelines

## References

- [Homebrew Formula Cookbook](https://docs.brew.sh/Formula-Cookbook)
- [Python Formula Guidelines](https://docs.brew.sh/Python-for-Formula-Authors)
- [Homebrew Acceptable Formulae](https://docs.brew.sh/Acceptable-Formulae)
