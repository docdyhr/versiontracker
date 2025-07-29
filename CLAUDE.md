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

- Maintain test coverage above 70% (target: 85%)
- All complex functions should have cyclomatic complexity < 15
- Run full test suite before major commits
- Use pre-commit hooks for code formatting and quality

### Coding Standards

**Line Length Policy**:

- **Maximum**: 120 characters per line (enforced via ruff)
- **Rationale**: Provides good readability while being AI-friendly for code generation
- **Enforcement**: Automatic via ruff E501 rule (enabled by default)

### AI Code Assistant Best Practices

When working with AI code assistants, the following linting configurations have been optimized:

**Ruff Lint Configuration (pyproject.toml):**

- **Line Length**: Enforced at 120 characters maximum (AI-friendly but maintains readability)
- `E402`: Module import not at top - Ignored for AI-generated code patterns  
- `F401`, `F811`, `F821`, `F841`: Import and variable warnings - Relaxed for iterative development
- **E501**: Line length violations are enforced via `line-length = 120` setting

**MyPy Configuration:**

- Test files have relaxed type checking with `ignore_errors = true`
- Additional error codes disabled for tests: `type-arg`, `attr-defined`, `no-untyped-def`, `misc`
- `ignore_missing_imports = true` for external dependencies

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
6. **Commit**: Stage, commit, and push changes

### File Organization Principles

- Keep the repository root minimal and organized
- Use clear, descriptive filenames
- Remove outdated documentation files regularly
- Consolidate information in core files rather than creating new ones

## Project-Specific Context

### Current Status (June 2025)

- All major technical debt has been resolved
- Test coverage: 70.88% (962 passing tests)
- Code quality: Excellent (all complexity issues resolved)
- Focus: Feature development and user experience improvements

### Key Technical Details

- Python 3.10-3.12 compatibility
- Uses pytest for testing with coverage reporting
- Pre-commit hooks configured for code quality
- Async/await patterns for network operations
- Homebrew integration for macOS package management

### Common Tasks

- Adding test coverage for low-coverage modules
- Implementing async network operations  
- Adding new package manager integrations
- Performance optimization and benchmarking

---

**Remember**: Keep the repository clean, focused, and professional. Document important changes in
the standard files rather than creating temporary tracking files.
