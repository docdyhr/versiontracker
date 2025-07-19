# Auto-Update Management Commands for VersionTracker

## Overview

VersionTracker now provides comprehensive management commands for handling applications with auto-updates enabled. These commands help you identify, blacklist, or remove applications that update themselves automatically, preventing version conflicts between Homebrew and the applications' built-in update mechanisms.

## Available Commands

### 1. Search for Apps with Auto-Updates

#### List all installed Homebrew casks with auto-updates:
```bash
versiontracker --brews --only-auto-updates
```

#### List all installed casks, marking those with auto-updates:
```bash
versiontracker --brews
```
Apps with auto-updates will be marked with `(auto-updates)` in the output.

#### Find non-Homebrew apps that could be managed by Homebrew and have auto-updates:
```bash
versiontracker --recommend --only-auto-updates
```

### 2. Filter Out Apps with Auto-Updates

#### List brews excluding those with auto-updates:
```bash
versiontracker --brews --exclude-auto-updates
```

#### Get recommendations excluding apps with auto-updates:
```bash
versiontracker --recommend --exclude-auto-updates
```

### 3. Blacklist Apps with Auto-Updates

#### Add all apps with auto-updates to the blacklist:
```bash
versiontracker --blacklist-auto-updates
```

This command will:
- Find all installed Homebrew casks with auto-updates
- Show you which ones will be blacklisted
- Ask for confirmation before making changes
- Save the updated blacklist to your configuration file

Example output:
```
Getting installed Homebrew casks...
Checking for auto-updates...

Found 4 casks with auto-updates:
  - visual-studio-code (will be added)
  - slack (will be added)
  - spotify (already blacklisted)
  - zoom (will be added)

This will add 3 casks to the blacklist.
Do you want to continue? [y/N]: y

✓ Successfully added 3 casks to the blacklist.
Total blacklisted items: 12
```

### 4. Uninstall Apps with Auto-Updates

#### Uninstall all Homebrew casks that have auto-updates:
```bash
versiontracker --uninstall-auto-updates
```

This command includes multiple safety features:
- Shows all apps that will be uninstalled
- Requires first confirmation (y/N)
- Requires typing "UNINSTALL" as second confirmation
- Shows progress for each uninstallation
- Reports success/failure for each app

Example output:
```
Getting installed Homebrew casks...
Checking for auto-updates...

Found 4 casks with auto-updates:
  1. visual-studio-code
  2. slack
  3. spotify
  4. zoom

⚠️  This will UNINSTALL 4 applications!
This action cannot be undone.
Are you sure you want to continue? [y/N]: y

Please type 'UNINSTALL' to confirm you want to remove these applications:
UNINSTALL

Uninstalling casks...
Uninstalling visual-studio-code... ✓
Uninstalling slack... ✓
Uninstalling spotify... ✗
Uninstalling zoom... ✓

============================================================
Successfully uninstalled: 3
Failed to uninstall: 1

Errors:
  - spotify: Error: Cask not installed
```

## How Auto-Updates Are Detected

VersionTracker detects auto-updates in two ways:

1. **Explicit field**: Checks if the cask has an `auto_updates` field set to `true`
2. **Caveats analysis**: Searches the cask's caveats for patterns indicating auto-updates:
   - "auto-update" or "auto update"
   - "automatically update"
   - "self-update" or "self update"
   - "sparkle" (common macOS auto-update framework)
   - "update automatically"

## Best Practices

1. **Review before action**: Always review the list of applications before blacklisting or uninstalling
2. **Backup important data**: Before uninstalling applications, ensure you have backups of any important data
3. **Consider alternatives**: Some apps with auto-updates can have this feature disabled in their preferences
4. **Regular checks**: Periodically check for new apps with auto-updates as you install new software

## Configuration

The blacklist is stored in your VersionTracker configuration file at:
```
~/.config/versiontracker/config.yaml
```

You can manually edit this file to add or remove items from the blacklist:
```yaml
blacklist:
  - visual-studio-code
  - slack
  - spotify
  - zoom
```

## Combining with Other Features

### Export list of auto-update apps:
```bash
versiontracker --brews --only-auto-updates --export json --output-file auto-update-apps.json
```

### Check for outdated apps, excluding those with auto-updates:
```bash
versiontracker --outdated --exclude-auto-updates
```

### Save filter for auto-update apps:
```bash
versiontracker --brews --only-auto-updates --save-filter "auto-updaters"
```

## Troubleshooting

### "No Homebrew casks found"
- Ensure Homebrew is installed: `brew --version`
- Check that you have casks installed: `brew list --cask`

### "Failed to uninstall" errors
- The app might already be uninstalled
- Check if the app requires admin privileges: `sudo brew uninstall --cask <app>`
- The app might be running - close it first

### Blacklist not persisting
- Check file permissions: `ls -la ~/.config/versiontracker/config.yaml`
- Ensure the directory exists: `mkdir -p ~/.config/versiontracker`

## Summary

The auto-update management features provide a comprehensive solution for handling applications that update themselves. By identifying, filtering, blacklisting, or removing these applications, you can maintain better control over your software versions and avoid conflicts between different update mechanisms.
