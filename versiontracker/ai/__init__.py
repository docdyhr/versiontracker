"""AI-powered natural language interface for VersionTracker.

This module provides intelligent command processing, natural language understanding,
and AI-driven insights for application management tasks.
"""

import logging
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from versiontracker.config import get_config
from versiontracker.exceptions import VersionTrackerError

logger = logging.getLogger(__name__)

__all__ = [
    "NLPProcessor",
    "CommandInterpreter",
    "AIInsights",
    "SmartRecommendations",
    "ConversationalInterface",
    "AIError",
]


class AIError(VersionTrackerError):
    """Raised when AI operations fail."""

    pass


@dataclass
class Intent:
    """Represents a parsed user intent."""

    action: str
    entities: dict[str, Any]
    confidence: float
    parameters: dict[str, Any]


@dataclass
class AIInsight:
    """AI-generated insight about applications or system state."""

    category: str
    title: str
    description: str
    confidence: float
    actionable: bool
    priority: str  # "low", "medium", "high", "critical"
    metadata: dict[str, Any]


class NLPProcessor:
    """Natural language processing engine for command understanding."""

    def __init__(self):
        """Initialize NLP processor."""
        self.intent_patterns = self._load_intent_patterns()
        self.entity_extractors = self._initialize_entity_extractors()
        self.conversation_context = []
        self.max_context_length = 10

    def process_command(self, text: str) -> Intent:
        """Process natural language command and extract intent."""
        text = text.strip().lower()

        # Store in conversation context
        self.conversation_context.append({"timestamp": time.time(), "user_input": text, "type": "user"})

        # Keep context size manageable
        if len(self.conversation_context) > self.max_context_length:
            self.conversation_context.pop(0)

        # Extract intent and entities
        intent = self._extract_intent(text)
        entities = self._extract_entities(text)
        parameters = self._extract_parameters(text, intent, entities)

        return Intent(
            action=intent["action"], entities=entities, confidence=intent["confidence"], parameters=parameters
        )

    def _load_intent_patterns(self) -> dict[str, Any]:
        """Load intent recognition patterns."""
        return {
            "scan_apps": {
                "patterns": [
                    r".*scan.*applications?.*",
                    r".*find.*apps?.*",
                    r".*discover.*applications?.*",
                    r".*list.*applications?.*",
                    r".*show.*me.*apps?.*",
                    r".*what.*apps?.*installed.*",
                ],
                "confidence_base": 0.8,
            },
            "get_recommendations": {
                "patterns": [
                    r".*recommend.*homebrew.*",
                    r".*suggest.*casks?.*",
                    r".*find.*homebrew.*alternatives?.*",
                    r".*what.*can.*i.*install.*with.*brew.*",
                    r".*show.*me.*recommendations.*",
                    r".*homebrew.*options.*",
                ],
                "confidence_base": 0.85,
            },
            "check_updates": {
                "patterns": [
                    r".*check.*updates?.*",
                    r".*outdated.*applications?.*",
                    r".*apps?.*need.*updating.*",
                    r".*what.*needs.*update.*",
                    r".*show.*outdated.*",
                ],
                "confidence_base": 0.8,
            },
            "install_app": {
                "patterns": [r".*install.*", r".*brew.*install.*", r".*add.*application.*", r".*get.*app.*"],
                "confidence_base": 0.7,
            },
            "remove_app": {
                "patterns": [r".*remove.*", r".*uninstall.*", r".*delete.*application.*", r".*brew.*uninstall.*"],
                "confidence_base": 0.7,
            },
            "blacklist_app": {
                "patterns": [
                    r".*blacklist.*",
                    r".*ignore.*application.*",
                    r".*exclude.*from.*updates.*",
                    r".*don't.*track.*",
                ],
                "confidence_base": 0.75,
            },
            "export_data": {
                "patterns": [r".*export.*", r".*save.*to.*file.*", r".*generate.*report.*", r".*output.*results.*"],
                "confidence_base": 0.8,
            },
            "get_help": {
                "patterns": [r".*help.*", r".*how.*do.*i.*", r".*what.*can.*you.*do.*", r".*commands.*available.*"],
                "confidence_base": 0.9,
            },
            "analytics": {
                "patterns": [
                    r".*analytics.*",
                    r".*statistics.*",
                    r".*performance.*report.*",
                    r".*show.*me.*stats.*",
                    r".*usage.*data.*",
                ],
                "confidence_base": 0.8,
            },
        }

    def _initialize_entity_extractors(self) -> dict[str, Any]:
        """Initialize entity extraction patterns."""
        return {
            "app_names": r"(?:app|application)\s+(?:named\s+)?['\"]?([^'\"]+)['\"]?",
            "file_formats": r"(?:as|to|in)\s+(json|yaml|xml|csv|txt)",
            "time_periods": r"(?:last|past|recent)\s+(\d+)\s+(days?|weeks?|months?|years?)",
            "version_numbers": r"version\s+(\d+(?:\.\d+)*)",
            "developer_names": r"(?:by|from|developer)\s+([A-Za-z0-9\s]+)",
            "categories": r"(?:category|type)\s+([A-Za-z0-9\s]+)",
            "confidence_threshold": r"(?:confidence|threshold|accuracy)\s+(?:of\s+)?(\d+)%?",
        }

    def _extract_intent(self, text: str) -> dict[str, Any]:
        """Extract the primary intent from text."""
        best_match = {"action": "unknown", "confidence": 0.0}

        for action, config in self.intent_patterns.items():
            for pattern in config["patterns"]:
                match = re.search(pattern, text)
                if match:
                    # Calculate confidence based on pattern match quality
                    confidence = config["confidence_base"]

                    # Boost confidence for exact matches
                    if len(match.group(0)) / len(text) > 0.5:
                        confidence += 0.1

                    # Consider context from previous interactions
                    confidence = self._adjust_confidence_with_context(action, confidence)

                    if confidence > best_match["confidence"]:
                        best_match = {"action": action, "confidence": confidence}

        return best_match

    def _extract_entities(self, text: str) -> dict[str, Any]:
        """Extract entities from the text."""
        entities = {}

        for entity_type, pattern in self.entity_extractors.items():
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                if entity_type in ["app_names", "developer_names", "categories"]:
                    entities[entity_type] = [match.strip() for match in matches]
                else:
                    entities[entity_type] = matches

        return entities

    def _extract_parameters(self, text: str, intent: dict[str, Any], entities: dict[str, Any]) -> dict[str, Any]:
        """Extract command parameters based on intent and entities."""
        parameters = {}

        # Time-based parameters
        if "time_periods" in entities:
            for period in entities["time_periods"]:
                if len(period) == 2:  # (number, unit)
                    parameters["time_period"] = {
                        "value": int(period[0]),
                        "unit": period[1].rstrip("s"),  # Remove plural 's'
                    }

        # File format parameters
        if "file_formats" in entities:
            parameters["output_format"] = entities["file_formats"][0]

        # Application filtering
        if "app_names" in entities:
            parameters["filter_apps"] = entities["app_names"]

        # Developer filtering
        if "developer_names" in entities:
            parameters["filter_developers"] = entities["developer_names"]

        # Confidence threshold
        if "confidence_threshold" in entities:
            threshold = entities["confidence_threshold"][0]
            parameters["confidence_threshold"] = float(threshold) / 100 if threshold.isdigit() else 0.7

        return self._extract_action_specific_params(intent, text, parameters)

    def _extract_action_specific_params(
        self, intent: dict[str, Any], text: str, parameters: dict[str, Any]
    ) -> dict[str, Any]:
        """Extract action-specific parameters."""
        if intent["action"] == "scan_apps":
            # Check for specific directories mentioned
            dir_pattern = r"(?:in|from)\s+([/\w\s]+(?:/[/\w\s]*)*)"
            dir_matches = re.findall(dir_pattern, text)
            if dir_matches:
                parameters["scan_directories"] = [Path(d.strip()) for d in dir_matches]

        elif intent["action"] == "export_data":
            # Extract file path if mentioned
            file_pattern = r"(?:to|as)\s+([^\s]+\.[a-zA-Z]+)"
            file_matches = re.findall(file_pattern, text)
            if file_matches:
                parameters["output_file"] = file_matches[0]

        return parameters

    def _adjust_confidence_with_context(self, action: str, base_confidence: float) -> float:
        """Adjust confidence based on conversation context."""
        if not self.conversation_context:
            return base_confidence

        # Look at recent context for related actions
        recent_context = self.conversation_context[-3:]  # Last 3 interactions
        related_actions = 0

        for context_item in recent_context:
            if context_item.get("intent_action") == action:
                related_actions += 1

        # Boost confidence for repeated actions
        if related_actions > 0:
            return min(1.0, base_confidence + (related_actions * 0.05))

        return base_confidence


class CommandInterpreter:
    """Interprets NLP results and generates executable commands."""

    def __init__(self):
        """Initialize command interpreter."""
        self.nlp_processor = NLPProcessor()

    def interpret_command(self, natural_language_input: str) -> dict[str, Any]:
        """Interpret natural language and return executable command structure."""
        try:
            intent = self.nlp_processor.process_command(natural_language_input)

            command_structure = {
                "command": self._map_intent_to_command(intent),
                "parameters": intent.parameters,
                "confidence": intent.confidence,
                "natural_language": natural_language_input,
                "timestamp": time.time(),
            }

            return command_structure

        except Exception as e:
            logger.error("Error interpreting command: %s", e)
            return {"command": "error", "error": str(e), "natural_language": natural_language_input, "confidence": 0.0}

    def _map_intent_to_command(self, intent: Intent) -> dict[str, Any]:
        """Map parsed intent to executable command structure."""
        command_mapping = {
            "scan_apps": {"action": "list_apps", "flags": ["--apps"], "description": "Scan and list applications"},
            "get_recommendations": {
                "action": "get_recommendations",
                "flags": ["--recom"],
                "description": "Generate Homebrew recommendations",
            },
            "check_updates": {
                "action": "check_outdated",
                "flags": ["--check-outdated"],
                "description": "Check for outdated applications",
            },
            "install_app": {"action": "install", "flags": [], "description": "Install application via Homebrew"},
            "remove_app": {"action": "uninstall", "flags": [], "description": "Uninstall application"},
            "blacklist_app": {
                "action": "blacklist",
                "flags": ["--blacklist-auto-updates"],
                "description": "Add applications to blacklist",
            },
            "export_data": {"action": "export", "flags": ["--export"], "description": "Export data to file"},
            "analytics": {
                "action": "analytics",
                "flags": ["--analytics"],
                "description": "Show analytics and statistics",
            },
            "get_help": {"action": "help", "flags": ["--help"], "description": "Show help information"},
        }

        base_command = command_mapping.get(
            intent.action, {"action": "unknown", "flags": [], "description": "Unknown command"}
        )

        # Add parameters as command line arguments
        if intent.parameters:
            base_command["parameters"] = intent.parameters

        return base_command


class AIInsights:
    """Generate AI-powered insights about applications and system state."""

    def __init__(self):
        """Initialize AI insights engine."""
        self.insight_generators = {
            "security": self._generate_security_insights,
            "performance": self._generate_performance_insights,
            "usage": self._generate_usage_insights,
            "maintenance": self._generate_maintenance_insights,
            "optimization": self._generate_optimization_insights,
        }

    def generate_insights(self, apps: list[dict[str, Any]], system_data: dict[str, Any]) -> list[AIInsight]:
        """Generate comprehensive insights about the application ecosystem."""
        insights = []

        for category, generator in self.insight_generators.items():
            try:
                category_insights = generator(apps, system_data)
                insights.extend(category_insights)
            except Exception as e:
                logger.warning("Failed to generate %s insights: %s", category, e)

        # Sort by priority and confidence
        priority_order = {"critical": 4, "high": 3, "medium": 2, "low": 1}
        insights.sort(key=lambda x: (priority_order.get(x.priority, 0), x.confidence), reverse=True)

        return insights

    def _generate_security_insights(self, apps: list[dict[str, Any]], system_data: dict[str, Any]) -> list[AIInsight]:
        """Generate security-related insights."""
        insights = []

        # Check for outdated applications
        outdated_apps = [app for app in apps if app.get("has_update", False)]
        if len(outdated_apps) > 5:
            insights.append(
                AIInsight(
                    category="security",
                    title="Multiple Outdated Applications Detected",
                    description=f"{len(outdated_apps)} applications have available updates. "
                    "Outdated software may contain security vulnerabilities.",
                    confidence=0.9,
                    actionable=True,
                    priority="high",
                    metadata={"outdated_count": len(outdated_apps), "apps": [app["name"] for app in outdated_apps[:5]]},
                )
            )

        # Check for unsigned applications
        unsigned_apps = [app for app in apps if not app.get("signed", True)]
        if unsigned_apps:
            insights.append(
                AIInsight(
                    category="security",
                    title="Unsigned Applications Found",
                    description=f"{len(unsigned_apps)} applications are not digitally signed, "
                    "which may pose security risks.",
                    confidence=0.8,
                    actionable=True,
                    priority="medium",
                    metadata={"unsigned_apps": [app["name"] for app in unsigned_apps]},
                )
            )

        return insights

    def _generate_performance_insights(
        self, apps: list[dict[str, Any]], system_data: dict[str, Any]
    ) -> list[AIInsight]:
        """Generate performance-related insights."""
        insights = []

        # Large applications taking up space
        large_apps = sorted(
            [app for app in apps if app.get("size", 0) > 1000], key=lambda x: x.get("size", 0), reverse=True
        )[:5]

        if large_apps:
            total_size = sum(app.get("size", 0) for app in large_apps)
            insights.append(
                AIInsight(
                    category="performance",
                    title="Large Applications Using Disk Space",
                    description=f"Top 5 largest applications are using {total_size:.1f} GB of disk space. "
                    "Consider reviewing if all are necessary.",
                    confidence=0.7,
                    actionable=True,
                    priority="low",
                    metadata={"large_apps": [(app["name"], app.get("size", 0)) for app in large_apps]},
                )
            )

        return insights

    def _generate_usage_insights(self, apps: list[dict[str, Any]], system_data: dict[str, Any]) -> list[AIInsight]:
        """Generate usage pattern insights."""
        insights = []

        # Apps not launched recently
        import time

        current_time = time.time()
        thirty_days_ago = current_time - (30 * 24 * 3600)

        unused_apps = [
            app
            for app in apps
            if app.get("last_opened", current_time) < thirty_days_ago and not app.get("system_app", False)
        ]

        if len(unused_apps) > 10:
            insights.append(
                AIInsight(
                    category="usage",
                    title="Many Unused Applications",
                    description=f"{len(unused_apps)} applications haven't been used in the last 30 days. "
                    "Consider removing unused applications to free up space.",
                    confidence=0.6,
                    actionable=True,
                    priority="low",
                    metadata={"unused_apps": [app["name"] for app in unused_apps[:10]]},
                )
            )

        return insights

    def _generate_maintenance_insights(
        self, apps: list[dict[str, Any]], system_data: dict[str, Any]
    ) -> list[AIInsight]:
        """Generate maintenance-related insights."""
        insights = []

        # Applications with auto-updates disabled
        manual_update_apps = [app for app in apps if not app.get("auto_updates", True)]
        if len(manual_update_apps) > 5:
            insights.append(
                AIInsight(
                    category="maintenance",
                    title="Many Applications Require Manual Updates",
                    description=f"{len(manual_update_apps)} applications don't have auto-updates enabled. "
                    "Consider using Homebrew for easier update management.",
                    confidence=0.8,
                    actionable=True,
                    priority="medium",
                    metadata={"manual_apps": [app["name"] for app in manual_update_apps[:5]]},
                )
            )

        return insights

    def _generate_optimization_insights(
        self, apps: list[dict[str, Any]], system_data: dict[str, Any]
    ) -> list[AIInsight]:
        """Generate optimization insights."""
        insights = []

        # Duplicate functionality apps
        duplicate_categories = {}
        for app in apps:
            category = app.get("category", "Unknown")
            if category not in duplicate_categories:
                duplicate_categories[category] = []
            duplicate_categories[category].append(app["name"])

        # Find categories with many apps
        crowded_categories = {
            cat: apps_list for cat, apps_list in duplicate_categories.items() if len(apps_list) > 3 and cat != "Unknown"
        }

        if crowded_categories:
            top_category = max(crowded_categories.keys(), key=lambda x: len(duplicate_categories[x]))
            insights.append(
                AIInsight(
                    category="optimization",
                    title="Multiple Apps in Same Category",
                    description=f"You have {len(duplicate_categories[top_category])} applications "
                    f"in the {top_category} category. Consider consolidating to reduce bloat.",
                    confidence=0.5,
                    actionable=False,
                    priority="low",
                    metadata={"category": top_category, "apps": duplicate_categories[top_category]},
                )
            )

        return insights


class SmartRecommendations:
    """AI-enhanced recommendation system."""

    def __init__(self):
        """Initialize smart recommendations engine."""
        self.recommendation_weights = {
            "name_similarity": 0.3,
            "category_match": 0.2,
            "developer_match": 0.2,
            "usage_pattern": 0.15,
            "user_preference": 0.15,
        }

    def generate_smart_recommendations(
        self, apps: list[dict[str, Any]], casks: list[dict[str, Any]], user_preferences: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """Generate AI-enhanced recommendations."""
        recommendations = []

        for app in apps:
            if app.get("is_app_store_app", False):
                continue  # Skip App Store apps

            best_matches = self._find_best_matches(app, casks, user_preferences)

            for match in best_matches:
                recommendation = {
                    "app": app,
                    "cask": match["cask"],
                    "confidence": match["score"],
                    "reasoning": self._generate_reasoning(app, match),
                    "ai_enhanced": True,
                    "factors": match["factors"],
                }
                recommendations.append(recommendation)

        return sorted(recommendations, key=lambda x: x["confidence"], reverse=True)

    def _find_best_matches(
        self, app: dict[str, Any], casks: list[dict[str, Any]], user_preferences: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """Find best cask matches for an application."""
        matches = []
        # Removed unused variable app_name

        for cask in casks:
            factors = self._calculate_match_factors(app, cask, user_preferences)
            total_score = sum(factors.values())

            if total_score > 0.5:  # Minimum threshold
                matches.append({"cask": cask, "score": total_score, "factors": factors})

        # Return top 3 matches
        return sorted(matches, key=lambda x: x["score"], reverse=True)[:3]

    def _calculate_match_factors(
        self, app: dict[str, Any], cask: dict[str, Any], user_preferences: dict[str, Any]
    ) -> dict[str, float]:
        """Calculate individual matching factors."""
        factors = {}

        # Name similarity
        app_name = app.get("name", "").lower()
        cask_name = cask.get("name", "").lower().replace("-", " ")
        factors["name_similarity"] = (
            self._text_similarity(app_name, cask_name) * self.recommendation_weights["name_similarity"]
        )

        # Category matching
        app_category = app.get("category", "").lower()
        cask_desc = cask.get("description", "").lower()
        factors["category_match"] = (1.0 if app_category in cask_desc else 0.0) * self.recommendation_weights[
            "category_match"
        ]

        # Developer matching
        app_developer = app.get("developer", "").lower()
        cask_homepage = cask.get("homepage", "").lower()
        factors["developer_match"] = (1.0 if app_developer in cask_homepage else 0.0) * self.recommendation_weights[
            "developer_match"
        ]

        # User preferences
        preferred_categories = user_preferences.get("preferred_categories", [])
        factors["user_preference"] = (
            0.5 if app_category in preferred_categories else 0.0
        ) * self.recommendation_weights["user_preference"]

        # Usage pattern (placeholder)
        factors["usage_pattern"] = 0.3 * self.recommendation_weights["usage_pattern"]

        return factors

    def _text_similarity(self, text1: str, text2: str) -> float:
        """Calculate simple text similarity."""
        if not text1 or not text2:
            return 0.0

        # Simple token-based similarity
        tokens1 = set(text1.split())
        tokens2 = set(text2.split())

        if not tokens1 or not tokens2:
            return 0.0

        intersection = len(tokens1.intersection(tokens2))
        union = len(tokens1.union(tokens2))

        return intersection / union if union > 0 else 0.0

    def _generate_reasoning(self, app: dict[str, Any], match: dict[str, Any]) -> str:
        """Generate human-readable reasoning for recommendation."""
        factors = match["factors"]
        cask = match["cask"]

        reasons = []

        if factors.get("name_similarity", 0) > 0.2:
            reasons.append("similar names")

        if factors.get("category_match", 0) > 0:
            reasons.append("matching category")

        if factors.get("developer_match", 0) > 0:
            reasons.append("same developer")

        if factors.get("user_preference", 0) > 0:
            reasons.append("matches your preferences")

        if cask.get("auto_updates", False):
            reasons.append("supports auto-updates")

        if not reasons:
            reasons = ["potential alternative"]

        return f"Recommended because of: {', '.join(reasons)}"


class ConversationalInterface:
    """Conversational AI interface for VersionTracker."""

    def __init__(self):
        """Initialize conversational interface."""
        self.command_interpreter = CommandInterpreter()
        self.conversation_history = []
        self.context_memory = {}

    def process_message(self, message: str) -> dict[str, Any]:
        """Process conversational message and return response."""
        # Interpret the command
        command_result = self.command_interpreter.interpret_command(message)

        # Generate conversational response
        response = self._generate_response(command_result, message)

        # Store in conversation history
        self.conversation_history.append(
            {
                "user_message": message,
                "command_result": command_result,
                "bot_response": response,
                "timestamp": time.time(),
            }
        )

        # Keep conversation history manageable
        if len(self.conversation_history) > 20:
            self.conversation_history.pop(0)

        return {"response": response, "command": command_result, "confidence": command_result.get("confidence", 0.0)}

    def _generate_response(self, command_result: dict[str, Any], original_message: str) -> str:
        """Generate conversational response based on command interpretation."""
        action = command_result.get("command", {}).get("action", "unknown")
        confidence = command_result.get("confidence", 0.0)

        if confidence < 0.3:
            return self._generate_clarification_response(original_message)

        response_templates = {
            "list_apps": [
                "I'll scan your applications and show you what's installed.",
                "Let me find all your applications for you.",
                "Scanning your applications now...",
            ],
            "get_recommendations": [
                "I'll generate Homebrew recommendations for your applications.",
                "Let me find which of your apps can be managed with Homebrew.",
                "Analyzing your apps for Homebrew alternatives...",
            ],
            "check_outdated": [
                "I'll check which of your applications need updates.",
                "Let me see what apps are outdated.",
                "Checking for available updates...",
            ],
            "install": [
                "I can help you install applications via Homebrew.",
                "Let me help you install that application.",
                "I'll set up the installation for you.",
            ],
            "export": [
                "I'll export your data to the specified format.",
                "Preparing your export file...",
                "Generating the export now...",
            ],
            "help": [
                "Here's what I can help you with:",
                "I can assist you with several tasks:",
                "Let me show you what I can do:",
            ],
            "analytics": [
                "I'll generate analytics about your applications.",
                "Let me analyze your application data.",
                "Preparing your analytics report...",
            ],
        }

        templates = response_templates.get(action, ["I understand you want to " + action])

        import random

        base_response = random.choice(templates)  # nosec B311

        # Add parameter information if available
        parameters = command_result.get("parameters", {})
        if parameters:
            param_info = self._format_parameters(parameters)
            if param_info:
                base_response += f" {param_info}"

        return base_response

    def _generate_clarification_response(self, message: str) -> str:
        """Generate response when command isn't clear."""
        clarification_responses = [
            "I'm not sure what you want to do. Could you rephrase that?",
            "I didn't quite understand. Can you be more specific?",
            "Could you clarify what you'd like me to help you with?",
            "I'm having trouble understanding your request. Could you try again?",
        ]

        import random

        base_response = random.choice(clarification_responses)  # nosec B311

        # Add helpful suggestions
        suggestions = [
            "You can ask me to scan applications, get recommendations, check for updates, or export data.",
            "Try asking something like 'scan my applications' or 'find homebrew recommendations'.",
            "I can help with tasks like finding outdated apps, generating reports, or managing your applications.",
        ]

        return base_response + " " + random.choice(suggestions)  # nosec B311

    def _format_parameters(self, parameters: dict[str, Any]) -> str:
        """Format parameters for conversational response."""
        info_parts = []

        if "output_format" in parameters:
            info_parts.append(f"in {parameters['output_format'].upper()} format")

        if "filter_apps" in parameters:
            apps = parameters["filter_apps"]
            if len(apps) == 1:
                info_parts.append(f"for {apps[0]}")
            else:
                info_parts.append(f"for {len(apps)} specific applications")

        if "time_period" in parameters:
            period = parameters["time_period"]
            info_parts.append(f"for the last {period['value']} {period['unit']}{'s' if period['value'] > 1 else ''}")

        if "confidence_threshold" in parameters:
            threshold = int(parameters["confidence_threshold"] * 100)
            info_parts.append(f"with {threshold}% confidence threshold")

        return " ".join(info_parts)

    def get_conversation_summary(self) -> dict[str, Any]:
        """Get a summary of the conversation."""
        if not self.conversation_history:
            return {"message": "No conversation history yet."}

        total_interactions = len(self.conversation_history)
        successful_commands = sum(
            1 for item in self.conversation_history if item["command_result"].get("confidence", 0) > 0.5
        )

        recent_topics = []
        for item in self.conversation_history[-5:]:  # Last 5 interactions
            action = item["command_result"].get("command", {}).get("action")
            if action and action not in recent_topics:
                recent_topics.append(action)

        return {
            "total_interactions": total_interactions,
            "successful_commands": successful_commands,
            "success_rate": successful_commands / total_interactions if total_interactions > 0 else 0,
            "recent_topics": recent_topics,
            "conversation_length": len(self.conversation_history),
        }


# Utility functions for AI features
def load_ai_config() -> dict[str, Any]:
    """Load AI-specific configuration."""
    config = get_config()
    return {
        "nlp_enabled": getattr(config, "ai_nlp_enabled", True),
        "insights_enabled": getattr(config, "ai_insights_enabled", True),
        "conversation_enabled": getattr(config, "ai_conversation_enabled", True),
        "confidence_threshold": getattr(config, "ai_confidence_threshold", 0.7),
        "max_conversation_history": getattr(config, "ai_max_conversation_history", 20),
    }


def create_ai_assistant() -> ConversationalInterface:
    """Create and configure AI assistant."""
    return ConversationalInterface()


# Example usage and testing functions
def demo_natural_language_processing():
    """Demonstrate natural language processing capabilities."""
    processor = NLPProcessor()

    test_commands = [
        "scan all my applications",
        "find homebrew recommendations for my apps",
        "check which apps need updates",
        "export results to json",
        "show me analytics for the last 7 days",
        "install firefox with homebrew",
        "help me with app management",
    ]

    print("Natural Language Processing Demo:")
    print("=" * 50)

    for command in test_commands:
        intent = processor.process_command(command)
        print(f"Input: '{command}'")
        print(f"Action: {intent.action}")
        print(f"Confidence: {intent.confidence:.2f}")
        print(f"Parameters: {intent.parameters}")
        print("-" * 30)


if __name__ == "__main__":
    demo_natural_language_processing()
