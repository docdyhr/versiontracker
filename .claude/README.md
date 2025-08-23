# Claude Code Hooks Configuration

This directory contains Claude Code hooks configuration for the VersionTracker project, designed to improve development workflow and code quality.

## Overview

The hooks system provides automated quality checks, formatting, and validation during Claude Code sessions. These hooks follow best practices for Python development and are specifically tailored for this project.

## Configured Hooks

### 1. Pre-Code Quality Check

- **Trigger**: Before editing Python files (`*.py`)
- **Action**: Runs `ruff check` to validate code quality
- **Purpose**: Prevents introducing linting errors
- **Behavior**: Blocks editing if linting fails

### 2. Post-Python Format

- **Trigger**: After editing Python files (`*.py`)
- **Action**: Runs `ruff format` to auto-format code
- **Purpose**: Ensures consistent code formatting
- **Behavior**: Continues on error (non-blocking)

### 3. Post-Test Validation

- **Trigger**: After editing core modules (`versiontracker/*.py`)
- **Action**: Runs quick pytest suite
- **Purpose**: Validates that core changes don't break functionality
- **Behavior**: Continues on error (informational)

### 4. Pre-Commit Validation

- **Trigger**: Before Git commit commands
- **Action**: Runs pre-commit hooks
- **Purpose**: Ensures all pre-commit checks pass before committing
- **Behavior**: Blocks commit if checks fail

### 5. Session Environment Check

- **Trigger**: At session start
- **Action**: Validates development environment
- **Purpose**: Ensures all required tools are available
- **Behavior**: Continues on error (informational)

### 6. Security Scan on Dependencies

- **Trigger**: After editing requirements files (`requirements*.txt`)
- **Action**: Runs `safety check` for security vulnerabilities
- **Purpose**: Identifies security issues in dependencies
- **Behavior**: Continues on error (informational)

### 7. Type Check Critical Files

- **Trigger**: After editing critical files (`__init__.py`, `config.py`, `app_finder.py`)
- **Action**: Runs `mypy` type checking
- **Purpose**: Ensures type safety in critical modules
- **Behavior**: Continues on error (informational)

### 8. Release File Notifications

- **Trigger**: After editing release-critical files
- **Action**: Shows notification about version bump consideration
- **Purpose**: Reminds about potential version/changelog updates
- **Behavior**: Always continues (notification only)

## Setup

### Automatic Setup

Run the setup script to automatically configure hooks:

```bash
python scripts/setup-claude-hooks.py
```

### Manual Setup

1. Copy `hooks.json` to your Claude configuration directory
2. Ensure required tools are installed (see below)
3. Restart Claude Code

## Required Tools

The hooks require these development tools to be installed:

```bash
# Install via pip
pip install ruff pytest mypy safety pre-commit

# Or install from requirements-dev.txt
pip install -r requirements-dev.txt
```

## Customization

### Modifying Hooks

Edit `.claude/hooks.json` to customize hook behavior:

- **Timeouts**: Adjust `timeout` values (in milliseconds)
- **Error Handling**: Change `continueOnError` to control blocking behavior
- **Matchers**: Modify file patterns or tool patterns
- **Commands**: Update commands or add flags

### Adding New Hooks

Add new hook objects to the `hooks` array in `hooks.json`. Each hook needs:

- `name`: Unique identifier
- `matcher`: Conditions for when the hook runs
- `event`: When to trigger (PreToolUse, PostToolUse, SessionStart, etc.)
- `command`: Shell command to execute
- `description`: Human-readable description
- `continueOnError`: Whether to block on failure
- `timeout`: Maximum execution time

### Example Hook

```json
{
  "name": "custom-validation",
  "matcher": {
    "tool": "Edit",
    "args": {
      "file_path": "custom_module/*.py"
    }
  },
  "event": "PostToolUse",
  "command": ["python", "-m", "custom_validator", "${file_path}"],
  "description": "Run custom validation after editing",
  "continueOnError": true,
  "timeout": 10000
}
```

## Troubleshooting

### Hook Failures

- Check that required tools are installed and in PATH
- Verify file permissions on scripts
- Review timeout settings for slow operations
- Check Claude Code logs for detailed error messages

### Performance Issues

- Reduce hook frequency by using more specific matchers
- Increase timeout values for slow operations
- Consider making blocking hooks non-blocking (`continueOnError: true`)

### Environment Issues

Run the environment validation script:

```bash
./scripts/validate-dev-environment.sh
```

## Best Practices

1. **Use Pre-hooks for Validation**: Block operations that would introduce errors
2. **Use Post-hooks for Automation**: Auto-format and validate after changes
3. **Set Appropriate Timeouts**: Balance responsiveness with completeness
4. **Handle Errors Gracefully**: Use `continueOnError: true` for informational hooks
5. **Target Specific Files**: Use precise matchers to avoid unnecessary overhead
6. **Document Custom Hooks**: Always include clear descriptions

## Integration with Project Workflows

These hooks integrate with existing project infrastructure:

- **Pre-commit**: Leverages existing `.pre-commit-config.yaml`
- **Ruff**: Uses project's `pyproject.toml` configuration
- **Pytest**: Runs with project's test configuration
- **MyPy**: Uses project's type checking setup
- **Safety**: Scans current requirements files

## Security Considerations

- Hooks run with user permissions
- Commands are executed in the project directory
- Environment variables are available to hook commands
- No external network access is required (except for safety checks)

## Contributing

When adding new hooks:

1. Test thoroughly in development
2. Document the hook's purpose and behavior
3. Use appropriate error handling
4. Consider performance impact
5. Update this README with new hook information

## Support

For issues with Claude Code hooks:

1. Check Claude Code documentation
2. Verify tool installation and configuration
3. Review hook logs and error messages
4. Test hooks individually outside Claude Code
