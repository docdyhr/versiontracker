# Setup Python Dependencies Action

This composite action ensures consistent dependency installation across all workflows in the versiontracker project.

## What it does

1. Upgrades `pip`, `setuptools` and `wheel`.
2. When `constraints.txt` exists, exports `PIP_CONSTRAINT` so every following `pip` call in the action is constrained
   by it.
3. Installs `requirements.txt` and `requirements-dev.txt` (or `requirements/dev.txt`), and `requirements-test.txt`
   (or `requirements/test.txt`) when present, then the essential test tools.
4. Installs the package in editable mode with its `dev` and `test` extras. With a `pyproject.toml` this step fails
   when the extras don't install, so a constraints conflict fails the job instead of being hidden by a fallback.

pip ignores a constraint for any package an install doesn't pull in, so this action alone does not validate the
whole of `constraints.txt`. The required "Code Linting and Formatting" job (`lint.yml`) resolves the whole file for
Python 3.12 and 3.13.

## Usage

```yaml
- name: Install dependencies
  uses: ./.github/actions/setup-python-deps
```

The action takes no inputs.
