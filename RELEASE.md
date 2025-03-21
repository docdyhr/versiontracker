# Release Process

This document outlines the release process for VersionTracker.

## Versioning

VersionTracker follows [Semantic Versioning](https://semver.org/):

- **MAJOR** version when you make incompatible API changes
- **MINOR** version when you add functionality in a backwards compatible manner
- **PATCH** version when you make backwards compatible bug fixes

## Release Checklist

1. **Update Version**

   Run the version bump script, specifying the type of version increment:

   ```bash
   # For a patch release:
   python bump_version.py patch

   # For a minor release:
   python bump_version.py minor

   # For a major release:
   python bump_version.py major
   ```

2. **Update CHANGELOG.md**

   The version bump script will add a section to the CHANGELOG.md. Make sure to:
   - Add detail about what changed in this release
   - Follow the standard format: Added, Changed, Fixed, Removed

3. **Verify Documentation**

   Ensure that the documentation is up-to-date with any new features or changes.

4. **Run Tests and Lint**

   ```bash
   # Run tests
   pytest -v

   # Run type checks
   mypy versiontracker

   # Run linters
   flake8 versiontracker
   black versiontracker
   isort versiontracker
   ```

5. **Commit and Tag**

   ```bash
   # Commit the changes
   git add versiontracker/__init__.py CHANGELOG.md README.md
   git commit -m "Bump version to X.Y.Z"

   # Create a tag for the new version
   git tag -a vX.Y.Z -m "Version X.Y.Z"

   # Push the changes
   git push origin master
   git push origin vX.Y.Z
   ```

6. **Create GitHub Release**

   On GitHub, create a new release:
   - Use the tag you just pushed
   - Title the release "Version X.Y.Z"
   - Copy the relevant section from CHANGELOG.md into the description
   - Add any additional notes or instructions

7. **PyPI Publication**

   When a new tag is pushed, the GitHub Action workflow will:
   - Build the package
   - Upload to PyPI
   - Verify the release

## Post-Release

1. Verify that the package is available on PyPI: https://pypi.org/project/versiontracker/
2. Verify that the GitHub release page is correct
3. Test the installation from PyPI: `pip install versiontracker`

## Hotfix Process

For critical issues that need immediate attention:

1. Create a hotfix branch from the release tag:
   ```bash
   git checkout -b hotfix/vX.Y.Z vX.Y.Z
   ```

2. Make the necessary fixes and commit them
3. Run the version bump script: `python bump_version.py patch`
4. Follow the release process from step 3 onwards