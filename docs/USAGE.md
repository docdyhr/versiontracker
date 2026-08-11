# VersionTracker Advanced Usage Guide

This document provides detailed information on the advanced features of VersionTracker.

## Configuration Options

VersionTracker provides multiple ways to configure the application:

### Command-line Arguments

```bash
# Basic usage for recommendations
versiontracker --recommend

# Find applications that can be newly installed with Homebrew (not already in cask repository)
versiontracker --strict-recommend

# With performance options
versiontracker --recommend --max-workers 8 --rate-limit 1

# Filtering applications
versiontracker --recommend --blacklist "Firefox,Chrome" --similarity 80

# Scanning additional directories
versiontracker --recommend --additional-dirs "/Users/username/Applications:/opt/Applications"

# Disabling progress bars
versiontracker --recommend --no-progress
```

### Configuration File

You can create a YAML configuration file for persistent settings:

```bash
# Default location
~/.config/versiontracker/config.yaml
```

A sample configuration file is provided in the repository as `sample_config.yaml`.

To generate a default configuration:

```bash
# Create default configuration in the default location
mkdir -p ~/.config/versiontracker
cp sample_config.yaml ~/.config/versiontracker/config.yaml
```

The configuration file supports all settings available through command-line arguments and environment variables.

### Environment Variables

Environment variables provide a convenient way to set default configuration:

```bash
# Set the API rate limit (seconds)
export VERSIONTRACKER_API_RATE_LIMIT=5

# Enable debug mode
export VERSIONTRACKER_DEBUG=true

# Set maximum worker threads
export VERSIONTRACKER_MAX_WORKERS=8

# Configure similarity threshold (0-100)
export VERSIONTRACKER_SIMILARITY_THRESHOLD=80

# Add applications to blacklist (comma-separated)
export VERSIONTRACKER_BLACKLIST=Firefox,Chrome,Safari

# Add additional application directories (colon-separated)
export VERSIONTRACKER_ADDITIONAL_APP_DIRS=/Users/username/Applications:/opt/Applications

# Disable progress bars
export VERSIONTRACKER_PROGRESS_BARS=false
```

Note: Environment variables override configuration file settings, and command-line arguments override both.

## Feature Details

### Application Blacklisting

The blacklist feature allows you to exclude specific applications from being checked or recommended:

```bash
# Via command line
versiontracker --recommend --blacklist "Slack,Zoom,Firefox"

# Via environment variable
export VERSIONTRACKER_BLACKLIST="Slack,Zoom,Firefox"
versiontracker --recommend
```

Applications in the blacklist will be completely ignored during the scan and recommendation process.

### Additional Application Directories

By default, VersionTracker scans the `/Applications` directory. You can add more directories:

```bash
# Via command line
versiontracker --recommend --additional-dirs "/Users/username/Applications:/Library/Applications"

# Via environment variable
export VERSIONTRACKER_ADDITIONAL_APP_DIRS="/Users/username/Applications:/Library/Applications"
versiontracker --recommend
```

The paths should be colon-separated. Each directory will be scanned for applications.

### Parallel Processing

VersionTracker performs multiple Homebrew searches in parallel for better performance:

```bash
# Default (10 workers)
versiontracker --recommend

# Increase for better performance on powerful machines
versiontracker --recommend --max-workers 16

# Decrease for lower resource usage
versiontracker --recommend --max-workers 4
```

The optimal number of workers depends on your CPU and network connection.

### Similarity Threshold

The similarity threshold controls how closely an application name must match a Homebrew cask:

```bash
# Default (75% similarity)
versiontracker --recommend

# Higher threshold (more exact matches)
versiontracker --recommend --similarity 90

# Lower threshold (more potential matches)
versiontracker --recommend --similarity 60
```

A higher threshold will reduce false positives but might miss some matches.

### Auditing Unmanaged Applications

`--audit` answers a narrower, more specific question than `--apps`: which
user-facing applications are not managed by the App Store, not owned by
Homebrew, have no confirmed local auto-update mechanism, and aren't
blocklisted? Each application's result carries evidence -- status, reason,
confidence, and source -- for all four signals, not just a yes/no. A signal
that can't be resolved (e.g. a failed Homebrew lookup) is reported as
`unknown`, never silently treated as a negative.

```bash
# Default view: only applications needing attention or with incomplete evidence
versiontracker --audit

# Show every audited application, including already-managed ones
versiontracker --audit --all

# Show full evidence per application instead of a compact table
versiontracker --audit --explain

# Show only one audit status
versiontracker --audit --status attention
versiontracker --audit --status unknown
versiontracker --audit --status managed
```

Results can be exported with full evidence in any of the three supported
formats, each carrying a versioned schema:

```bash
versiontracker --audit --export json
versiontracker --audit --export yaml
versiontracker --audit --export csv --output-file audit.csv
```

`--all` and `--status` are mutually exclusive (choosing a single status
already implies not showing everything). `--additional-dirs` and
`--blocklist`/`--blacklist` behave as documented above and merge with any
configured `additional_app_dirs`/blocklist entries rather than replacing them.

### Natural-Language Queries (--ask)

`--ask "<query>"` recognizes a handful of plain-English phrasings and routes
them to the same handler the equivalent literal flag would use -- it never
reimplements any classification logic itself, so the underlying semantics
(e.g. what counts as "needing attention") are exactly `--audit`'s, described
above.

```bash
# Routed to --audit
versiontracker --ask "which apps need manual updates"
versiontracker --ask "what needs my attention"
versiontracker --ask "which apps aren't managed"

# Routed to --apps / --recom / --check-outdated
versiontracker --ask "list my applications"
versiontracker --ask "recommend homebrew casks"
versiontracker --ask "check for outdated applications"
```

`--ask` sits in the same mutually-exclusive action group as `--audit`/`--apps`/
etc. (so combining it with a literal action flag is rejected), but combines
freely with modifier flags since those live in separate argparse groups:

```bash
versiontracker --ask "which apps need manual updates" --export json
```

A query that doesn't match a recognized phrasing, or matches an action with
no standalone CLI equivalent (e.g. "install firefox"), always prints a clear
message explaining why -- it never guesses or silently does nothing.

## Examples

### Daily Usage

```bash
# Quick check for recommendations
versiontracker --recommend

# Install all recommended applications at once
versiontracker --recommend | grep "brew install" | sh
```

### Customized Scan

```bash
# Scan personal applications with high accuracy
versiontracker --recommend --additional-dirs "/Users/username/Applications" --similarity 85 --blacklist "Firefox,Chrome"
```

### Performance Tuning

```bash
# For fast machines with good network
versiontracker --recommend --max-workers 20 --rate-limit 0.5

# For slower machines
versiontracker --recommend --max-workers 4 --rate-limit 2 --no-progress
```

## Troubleshooting

### Debug Mode

Enable debug mode to see detailed information:

```bash
versiontracker --recommend --debug true
```

This will show additional log information about application detection, brew searches, and more.

### Common Issues

1. **Rate limiting errors**: If you see rate limiting errors from Homebrew, increase the `--rate-limit` value.
2. **Missing applications**: Check if your application directories are correctly specified.
3. **False matches**: Increase the similarity threshold with `--similarity`.
4. **Performance issues**: Adjust the number of workers with `--max-workers`.
