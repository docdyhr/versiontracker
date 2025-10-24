"""Recommendations command implementation.

This module provides the RecommendationsCommand for generating Homebrew cask
recommendations based on installed applications.
"""

import logging
from typing import Any

from versiontracker.commands import BaseCommand
from versiontracker.handlers import handle_brew_recommendations


class RecommendationsCommand(BaseCommand):
    """Command to generate Homebrew cask recommendations."""

    name = "recommendations"
    description = "Get recommendations for Homebrew installations"

    def execute(self, options: Any) -> int:
        """Execute the recommendations command.

        Args:
            options: Parsed command-line arguments

        Returns:
            int: Exit code (0 for success, non-zero for failure)
        """
        try:
            return handle_brew_recommendations(options)
        except Exception as e:
            logging.exception("Error executing recommendations command: %s", str(e))
            return 1

    def validate_options(self, options: Any) -> bool:
        """Validate command-specific options.

        Args:
            options: Parsed command-line arguments

        Returns:
            bool: True if options are valid, False otherwise
        """
        # Check if either recom or strict_recom is set
        has_recom = hasattr(options, "recom") and options.recom
        has_strict_recom = hasattr(options, "strict_recom") and options.strict_recom

        if not (has_recom or has_strict_recom):
            return False

        # Validate similarity threshold if provided
        if hasattr(options, "similarity_threshold"):
            threshold = options.similarity_threshold
            if threshold is not None and (threshold < 0.0 or threshold > 1.0):
                logging.error("Similarity threshold must be between 0.0 and 1.0")
                return False

        return True

    def get_help_text(self) -> str:
        """Get detailed help text for this command.

        Returns:
            str: Help text describing the command and its options
        """
        return """
Generate Homebrew cask recommendations based on installed applications.

This command analyzes your installed applications and suggests which ones
can be managed through Homebrew casks for easier updating and management.

Options:
  --recom                   Show fuzzy-matched recommendations
  --strict-recom           Show only exact-matched recommendations
  --similarity-threshold   Set fuzzy matching threshold (0.0-1.0)
  --exclude-auto-updates   Exclude apps with auto-update capabilities
  --export JSON_FILE       Export results to JSON file

Examples:
  versiontracker --recom
  versiontracker --strict-recom --export recommendations.json
  versiontracker --recom --similarity-threshold 0.8
        """.strip()
