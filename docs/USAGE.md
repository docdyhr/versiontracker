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
