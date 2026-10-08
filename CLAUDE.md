# Claude Code Assistant Guidelines

This document provides guidelines for maintaining this repository when working with Claude Code.

## Repository Organization Best Practices

### Core Documentation Files (Keep these clean and focused)

- **README.md**: Project overview, installation, usage examples
- **CHANGELOG.md**: Version history and notable changes
- **TODO.md**: Future development plans and roadmap

### Files to Avoid Creating

Do NOT create temporary tracking files such as:

- CI_CD_*.md, TECHNICAL_DEBT_*.md, WORKFLOW_*.md
- STATUS_*.md, FIXES_*.md, IMPROVEMENTS_*.md  
- RELEASE_NOTES_*.md (unless for major releases)
- Any date-specific tracking files

### Repository Cleanup Practices

When performing technical debt reduction or major improvements:

1. **Document changes directly in CHANGELOG.md** - Don't create separate tracking files
2. **Update TODO.md** to reflect completed work and remove outdated items  
3. **Keep the repository root clean** - Remove temporary documentation files after completion
4. **Use git commit messages** for detailed change tracking instead of separate files

### Commit Message Standards

For significant changes, use structured commit messages:

```text
feat: brief description of new feature
fix: brief description of bug fix  
refactor: brief description of code improvement
docs: brief description of documentation changes
test: brief description of test additions/changes
```

Include detailed descriptions in the commit body, not separate markdown files.

### Testing and Quality Standards

- Maintain test coverage of at least 85% (enforced by `--cov-fail-under=85` in the Coverage Analysis workflow)
- Cyclomatic complexity must stay at or below 12 per function (ruff `C901`, `max-complexity = 12`)
- Run full test suite before major commits
- Use pre-commit hooks for code formatting and quality

### Coding Standards

**Line Length Policy**:

- **Maximum**: 120 characters per line (`line-length = 120`)
- **Rationale**: Provides good readability while being AI-friendly for code generation
- **Enforcement**: `ruff format` wraps code to 120, and ruff's `E501` rule flags any line it cannot wrap (long
  strings, comments, URLs) — split those by hand

### AI Code Assistant Best Practices

When working with AI code assistants, the following linting configurations have been optimized:

**Ruff Lint Configuration (pyproject.toml):**

- **Selected rules**: `E`, `W`, `F`, `I`, `B`, `C4`, `UP`, `C90`, `G` — nothing is ignored
- `E402`, `F401`, `F811`, `F821`, `F841` are enforced (not relaxed); the codebase passes all of them
- **Line Length**: 120, enforced by `E501` (see Line Length Policy above)

**MyPy Configuration:**

- Test files have relaxed type checking with `ignore_errors = true`
- Additional error codes disabled for tests: `type-arg`, `attr-defined`, `no-untyped-def`, `misc`
- `ignore_missing_imports = true` for the listed third-party modules (fuzzywuzzy, rapidfuzz, yaml, aiohttp, ...)
- `versiontracker.ai.*`, `versiontracker.ml.*` and `versiontracker.experimental.*` have `ignore_errors = true`

**Pre-commit Hooks:**

- MyPy includes `--ignore-missing-imports` flag
- TODO/FIXME checks skipped in CI environment
- Focused on essential quality checks while allowing AI development patterns

### Development Workflow

1. **Analysis**: Understand current state and identify issues
2. **Planning**: Update TODO.md with specific tasks if needed
3. **Implementation**: Make changes with clear commit messages
4. **Documentation**: Update CHANGELOG.md and README.md as needed
5. **Cleanup**: Remove any temporary files created during development
6. **Commit**: Commit on a feature branch, push it, and open a PR — `main` is protected by a repository ruleset
   (required status checks, which in practice rejects direct pushes; no force-pushes or deletion). By convention
   PRs are squash-merged

### File Organization Principles

- Keep the repository root minimal and organized
- Use clear, descriptive filenames
- Remove outdated documentation files regularly
- Consolidate information in core files rather than creating new ones

## Project-Specific Context

### Current Status (October 2026)

- Latest release: 1.2.0 — on PyPI as `macversiontracker`, in the Homebrew tap, and as a GitHub release with
  Sigstore-signed assets
- Test suite: 2,833 passing, 16 skipped (13 need the optional ML extras); coverage 88.20%
- Code quality: ruff, ruff format, and mypy all clean
- Focus: Feature development and user experience improvements

### Key Technical Details

- Python 3.12+ (`requires-python = ">=3.12"`; CI tests 3.12 and 3.13)
- Uses pytest for testing with coverage reporting
- Pre-commit hooks configured for code quality
- Async/await patterns for network operations
- Homebrew integration for macOS package management

### Common Tasks

- Adding test coverage for low-coverage modules
- Implementing async network operations  
- Adding new package manager integrations
- Performance optimization and benchmarking

## Future Resolutions

- Resolve any pending technical debt
- Continuously improve code quality and test coverage
- Explore new AI integration possibilities

---

**Remember**: Keep the repository clean, focused, and professional. Document important changes in
the standard files rather than creating temporary tracking files.
