# Agent skills

Vendored from [github/awesome-copilot](https://github.com/github/awesome-copilot) at commit
`cb64ad12e32737ae764becd6885462e9b4c7cb00` (MIT License, see [`LICENSE`](LICENSE)). Every file except this README is
byte-identical to upstream `skills/<name>/` (and `LICENSE`), with one deliberate exception: `dependabot/SKILL.md` (the
`[dependabot skip]` line under "Rebase Strategy") and `dependabot/references/pr-commands.md` (the "Force push over
extra commits" tip) are corrected locally. Upstream says the marker allows Dependabot to "rebase over" extra commits;
per [GitHub's docs](https://docs.github.com/en/code-security/dependabot/working-with-dependabot/managing-pull-requests-for-dependency-updates)
it lets Dependabot force-push over them, discarding them. Keep both corrections when refreshing until upstream fixes
the wording ([github/awesome-copilot#5858](https://github.com/github/awesome-copilot/issues/5858)). Do not edit the
files here otherwise; refresh from upstream instead.

Claude Code loads `.claude/skills/` as project skills, and GitHub Copilot (cloud agent, CLI, VS Code agent mode) reads
it too. Where a skill disagrees with `CLAUDE.md` ("Vendored Agent Skills"), `CLAUDE.md` wins.

Not vendored:

- `github-release` and `conventional-commit`: they conflict with this repo's release and commit conventions.
- `pytest-coverage`: its 100% target and loop conflict with the 85% floor and the optional-extras skips.
- `docs-sync-audit/scripts/docs_drift.py` and `test-gap-audit/scripts/coverage_map.py`: optional helpers. Both skills
  use them only "when it is available" and otherwise audit by hand.

| Skill                      | Purpose                                                             |
| -------------------------- | ------------------------------------------------------------------- |
| `dependabot`               | Configuring `dependabot.yml` and working with Dependabot PRs        |
| `docs-sync-audit`          | Read-only audit of documentation drift against the code             |
| `github-actions-hardening` | Security review of `.github/workflows/*.yml`; reports, never edits  |
| `test-gap-audit`           | Read-only audit of missing or weak tests                            |
