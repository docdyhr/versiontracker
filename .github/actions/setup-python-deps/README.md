# Setup Python Dependencies Action

This composite action ensures consistent dependency installation across all workflows in the versiontracker project.

## Features

- Installs dependencies using `constraints.txt` to ensure version consistency
- Configurable options for different workflow needs
- Reduces duplication across workflow files

## Usage

```yaml
- name: Install dependencies
  uses: ./.github/actions/setup-python-deps
```

## Inputs

| Input | Description | Required | Default |
|-------|-------------|----------|---------|
| `requirements` | Install base requirements.txt | No | `true` |
| `dev-requirements` | Install requirements-dev.txt | No | `true` |
| `install-package` | Install package in editable mode | No | `true` |

## Examples

### Full installation (default)

```yaml
- uses: ./.github/actions/setup-python-deps
```

### Only dev requirements

```yaml
- uses: ./.github/actions/setup-python-deps
  with:
    requirements: 'false'
    dev-requirements: 'true'
    install-package: 'false'
```

### Only base requirements without package

```yaml
- uses: ./.github/actions/setup-python-deps
  with:
    requirements: 'true'
    dev-requirements: 'false'
    install-package: 'false'
```
