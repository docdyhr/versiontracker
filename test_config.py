"""Test script to verify configuration loading."""

from versiontracker.config import Config

# Create a Config instance
config = Config()

# Set custom config file path
config._config["config_file"] = "tmp_test/custom_config.yaml"

# Load from file
config._load_from_file()

# Print loaded configuration
print("Custom Config Values:")
for key, value in config._config.items():
    print(f"{key}: {value}")

# Verify specific values
print("\nVerifying specific values:")
print(f"api_rate_limit: {config.get('api_rate_limit')} (Expected: 5)")
print(f"max_workers: {config.get('max_workers')} (Expected: 4)")
print(f"blacklist: {config.get_blacklist()} (Expected: ['Safari', 'Numbers', 'Pages'])")
print(
    f"additional_app_dirs: {config.get('additional_app_dirs')} "
    f"(Expected: ['/Applications/Utilities', '/Applications/Adobe'])"
)
print(f"similarity_threshold: {config.get('similarity_threshold')} (Expected: 85)")
print(f"show_progress: {config.get('show_progress')} (Expected: False)")
