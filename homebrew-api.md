# 🛠️ Homebrew Automation & API Access Guide

This document outlines how to programmatically access and automate Homebrew package information for use in the
`versiontracker` project.

---

## 📦 1. Homebrew CLI for Automation

You can extract structured data using built-in commands:

### 🔍 Formula Info

```bash
brew info --json=v2 --formula <name>
```

### 🔍 Cask Info

```bash
brew info --json=v2 --cask <name>
```

### 📃 Installed Packages

```bash
brew list --formula
brew list --cask
```

### 🔁 Outdated Packages (JSON)

```bash
brew outdated --json=v2
```

---

## ⚙️ 2. Example: Detecting Auto-Updating Casks

Use this script to list installed casks and detect those with `(auto_updates)`:

```bash
brew list --cask | while read cask; do
  if brew info --cask "$cask" | grep -q auto_updates; then
    echo "$cask (auto_updates)"
  else
    echo "$cask"
  fi
done
```

---

## 🌐 3. Unofficial JSON API

You can use the public `formulae.brew.sh` endpoint for fetching formula and cask metadata:

### ✅ Formula

```bash
curl https://formulae.brew.sh/api/formula/<name>.json
```

### ✅ Cask

```bash
curl https://formulae.brew.sh/api/cask/<name>.json
```

Example:

```bash
curl https://formulae.brew.sh/api/cask/google-chrome.json
```

---

## 📚 4. GitHub Metadata

Homebrew formulae and casks are hosted on GitHub:

- **Formulae:** <https://github.com/Homebrew/homebrew-core>
- **Casks:** <https://github.com/Homebrew/homebrew-cask>

Use the GitHub REST or GraphQL API for metadata/history.

---

## 💡 5. Ruby API (Advanced)

Homebrew is written in Ruby. You can script it with:

```bash
brew irb
```

Example inside the REPL:

```ruby
Formula["wget"].desc
Cask::CaskLoader.load("google-chrome").version
```

---

## 🧪 Sample JSON Output

```json
{
  "name": "claude",
  "versions": { "stable": "0.12.28" },
  "auto_updates": true,
  "desc": "Claude Desktop App"
}
```

---

## 🧰 Recommended Use in Versiontracker

- Parse `brew info --json=v2` results to track version, auto-update status.
- Optionally fetch JSON from `formulae.brew.sh` for remote diffing.
- Store output in structured files (e.g. `homebrew.json`) for Claude-assisted parsing.

---

© 2025 [docdyhr/versiontracker](https://github.com/docdyhr/versiontracker)
