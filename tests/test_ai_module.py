"""Tests for the AI module (NLP, CommandInterpreter, AIInsights, SmartRecommendations)."""

from __future__ import annotations

import time

import pytest

from versiontracker.ai import (
    AIError,
    AIInsight,
    AIInsights,
    CommandInterpreter,
    ConversationalInterface,
    Intent,
    NLPProcessor,
    SmartRecommendations,
    create_ai_assistant,
    load_ai_config,
)


class TestIntent:
    """Tests for Intent dataclass."""

    def test_intent_creation(self):
        intent = Intent(action="scan_apps", entities={}, confidence=0.9, parameters={})
        assert intent.action == "scan_apps"
        assert intent.confidence == 0.9
        assert intent.entities == {}
        assert intent.parameters == {}


class TestAIInsightDataclass:
    """Tests for AIInsight dataclass."""

    def test_ai_insight_creation(self):
        insight = AIInsight(
            category="security",
            title="Test Insight",
            description="A test insight",
            confidence=0.85,
            actionable=True,
            priority="high",
            metadata={"key": "value"},
        )
        assert insight.category == "security"
        assert insight.title == "Test Insight"
        assert insight.confidence == 0.85
        assert insight.actionable is True
        assert insight.priority == "high"


class TestAIError:
    """Tests for AIError exception."""

    def test_ai_error_is_versiontracker_error(self):
        from versiontracker.exceptions import VersionTrackerError

        error = AIError("test error")
        assert isinstance(error, VersionTrackerError)
        assert str(error) == "test error"


class TestNLPProcessor:
    """Tests for NLPProcessor class."""

    def setup_method(self):
        self.processor = NLPProcessor()

    def test_init(self):
        assert self.processor.intent_patterns is not None
        assert self.processor.entity_extractors is not None
        assert self.processor.conversation_context == []
        assert self.processor.max_context_length == 10

    def test_process_scan_apps(self):
        intent = self.processor.process_command("scan all my applications")
        assert intent.action == "scan_apps"
        assert intent.confidence > 0.5

    def test_process_recommendations(self):
        intent = self.processor.process_command("recommend homebrew alternatives")
        assert intent.action == "get_recommendations"
        assert intent.confidence > 0.5

    def test_process_check_updates(self):
        intent = self.processor.process_command("check for outdated applications")
        assert intent.action == "check_updates"
        assert intent.confidence > 0.5

    def test_process_export(self):
        intent = self.processor.process_command("export results to json")
        assert intent.action == "export_data"
        assert intent.confidence > 0.5

    def test_process_help(self):
        intent = self.processor.process_command("help me with commands")
        assert intent.action == "get_help"
        assert intent.confidence > 0.5

    def test_process_unknown_command(self):
        intent = self.processor.process_command("xyzzy plugh")
        assert intent.action == "unknown"
        assert intent.confidence == 0.0

    def test_entity_extraction_file_format(self):
        intent = self.processor.process_command("export data to json")
        assert "file_formats" in intent.entities or "output_format" in intent.parameters

    def test_conversation_context_maintained(self):
        self.processor.process_command("scan apps")
        self.processor.process_command("check updates")
        assert len(self.processor.conversation_context) == 2

    def test_conversation_context_max_length(self):
        for i in range(15):
            self.processor.process_command(f"test command {i}")
        assert len(self.processor.conversation_context) <= self.processor.max_context_length

    def test_extract_entities_version(self):
        entities = self.processor._extract_entities("update application version 2.3.1")
        assert "version_numbers" in entities
        assert "2.3.1" in entities["version_numbers"]

    def test_confidence_adjustment_with_context(self):
        base = self.processor._adjust_confidence_with_context("scan_apps", 0.8)
        assert base == 0.8  # No context yet

    def test_extract_parameters_with_time_period(self):
        intent = self.processor.process_command("show analytics for the last 7 days")
        # Should extract time period entities
        assert isinstance(intent.parameters, dict)

    def test_action_specific_params_scan(self):
        intent = self.processor.process_command("scan applications in /Applications")
        assert isinstance(intent.parameters, dict)

    def test_action_specific_params_export(self):
        intent = self.processor.process_command("export to report.json")
        assert isinstance(intent.parameters, dict)


class TestCommandInterpreter:
    """Tests for CommandInterpreter class."""

    def setup_method(self):
        self.interpreter = CommandInterpreter()

    def test_init(self):
        assert self.interpreter.nlp_processor is not None

    def test_interpret_scan_command(self):
        result = self.interpreter.interpret_command("scan my applications")
        assert "command" in result
        assert "confidence" in result
        assert "natural_language" in result
        assert result["command"]["action"] == "list_apps"

    def test_interpret_recommendations_command(self):
        result = self.interpreter.interpret_command("recommend homebrew casks")
        assert result["command"]["action"] == "get_recommendations"
        assert "--recom" in result["command"]["flags"]

    def test_interpret_outdated_command(self):
        result = self.interpreter.interpret_command("check outdated applications")
        assert result["command"]["action"] == "check_outdated"

    def test_interpret_help_command(self):
        result = self.interpreter.interpret_command("help me")
        assert result["command"]["action"] == "help"

    def test_interpret_unknown_returns_unknown(self):
        result = self.interpreter.interpret_command("xyzzy gibberish nonsense")
        assert result["command"]["action"] == "unknown"

    def test_interpret_error_handling(self):
        # The interpreter should handle errors gracefully
        result = self.interpreter.interpret_command("")
        assert "command" in result or "error" in result


class TestAIInsights:
    """Tests for AIInsights class."""

    def setup_method(self):
        self.insights_engine = AIInsights()

    def test_init(self):
        assert "security" in self.insights_engine.insight_generators
        assert "performance" in self.insights_engine.insight_generators
        assert "usage" in self.insights_engine.insight_generators
        assert "maintenance" in self.insights_engine.insight_generators
        assert "optimization" in self.insights_engine.insight_generators

    def test_generate_security_insights_outdated(self):
        apps = [{"name": f"App{i}", "has_update": True} for i in range(10)]
        insights = self.insights_engine.generate_insights(apps, {})
        security_insights = [i for i in insights if i.category == "security"]
        assert len(security_insights) > 0
        assert any("Outdated" in i.title for i in security_insights)

    def test_generate_security_insights_unsigned(self):
        apps = [{"name": "UnsignedApp", "signed": False}]
        insights = self.insights_engine._generate_security_insights(apps, {})
        assert len(insights) > 0
        assert any("Unsigned" in i.title for i in insights)

    def test_generate_performance_insights_large_apps(self):
        apps = [{"name": f"BigApp{i}", "size": 5000} for i in range(6)]
        insights = self.insights_engine._generate_performance_insights(apps, {})
        assert len(insights) > 0
        assert any("Large" in i.title for i in insights)

    def test_generate_usage_insights_unused_apps(self):
        old_time = time.time() - (60 * 24 * 3600)  # 60 days ago
        apps = [{"name": f"OldApp{i}", "last_opened": old_time, "system_app": False} for i in range(15)]
        insights = self.insights_engine._generate_usage_insights(apps, {})
        assert len(insights) > 0
        assert any("Unused" in i.title for i in insights)

    def test_generate_maintenance_insights(self):
        apps = [{"name": f"ManualApp{i}", "auto_updates": False} for i in range(10)]
        insights = self.insights_engine._generate_maintenance_insights(apps, {})
        assert len(insights) > 0

    def test_generate_optimization_insights(self):
        apps = [{"name": f"Editor{i}", "category": "Code Editor"} for i in range(5)]
        insights = self.insights_engine._generate_optimization_insights(apps, {})
        assert len(insights) > 0

    def test_generate_insights_empty_apps(self):
        insights = self.insights_engine.generate_insights([], {})
        assert isinstance(insights, list)

    def test_insights_sorted_by_priority(self):
        apps = [{"name": f"App{i}", "has_update": True, "signed": False} for i in range(10)]
        insights = self.insights_engine.generate_insights(apps, {})
        if len(insights) > 1:
            priority_order = {"critical": 4, "high": 3, "medium": 2, "low": 1}
            for i in range(len(insights) - 1):
                p1 = priority_order.get(insights[i].priority, 0)
                p2 = priority_order.get(insights[i + 1].priority, 0)
                assert p1 >= p2 or (p1 == p2 and insights[i].confidence >= insights[i + 1].confidence)


class TestSmartRecommendations:
    """Tests for SmartRecommendations class."""

    def setup_method(self):
        self.recommender = SmartRecommendations()

    def test_init(self):
        assert "name_similarity" in self.recommender.recommendation_weights
        assert sum(self.recommender.recommendation_weights.values()) == pytest.approx(1.0)

    def test_text_similarity_identical(self):
        score = self.recommender._text_similarity("firefox", "firefox")
        assert score == 1.0

    def test_text_similarity_empty(self):
        assert self.recommender._text_similarity("", "test") == 0.0
        assert self.recommender._text_similarity("test", "") == 0.0

    def test_text_similarity_partial(self):
        score = self.recommender._text_similarity("visual studio code", "visual studio")
        assert 0.0 < score < 1.0

    def test_generate_smart_recommendations(self):
        apps = [{"name": "Firefox", "category": "browser", "developer": "Mozilla"}]
        casks = [{"name": "firefox", "description": "web browser", "homepage": "https://mozilla.org"}]
        recs = self.recommender.generate_smart_recommendations(apps, casks, {})
        assert isinstance(recs, list)

    def test_skip_app_store_apps(self):
        apps = [{"name": "TestApp", "is_app_store_app": True}]
        casks = [{"name": "testapp", "description": "test"}]
        recs = self.recommender.generate_smart_recommendations(apps, casks, {})
        assert len(recs) == 0

    def test_generate_reasoning(self):
        match = {
            "cask": {"name": "firefox", "auto_updates": True},
            "score": 0.9,
            "factors": {"name_similarity": 0.3, "category_match": 0.1},
        }
        app = {"name": "Firefox"}
        reasoning = self.recommender._generate_reasoning(app, match)
        assert "Recommended because of:" in reasoning


class TestConversationalInterface:
    """Tests for ConversationalInterface class."""

    def setup_method(self):
        self.interface = ConversationalInterface()

    def test_init(self):
        assert self.interface.command_interpreter is not None
        assert self.interface.conversation_history == []
        assert self.interface.context_memory == {}

    def test_process_message(self):
        result = self.interface.process_message("scan my applications")
        assert "response" in result
        assert "command" in result
        assert "confidence" in result
        assert isinstance(result["response"], str)

    def test_process_unclear_message(self):
        result = self.interface.process_message("xyzzy nonsense gibberish")
        assert "response" in result
        # Low confidence should trigger clarification
        assert isinstance(result["response"], str)

    def test_conversation_history_maintained(self):
        self.interface.process_message("scan apps")
        self.interface.process_message("check updates")
        assert len(self.interface.conversation_history) == 2

    def test_conversation_history_max_length(self):
        for i in range(25):
            self.interface.process_message(f"test message {i}")
        assert len(self.interface.conversation_history) <= 20

    def test_get_conversation_summary_empty(self):
        summary = self.interface.get_conversation_summary()
        assert "message" in summary

    def test_get_conversation_summary_with_history(self):
        self.interface.process_message("scan my applications")
        self.interface.process_message("check for updates")
        summary = self.interface.get_conversation_summary()
        assert summary["total_interactions"] == 2
        assert "success_rate" in summary
        assert "recent_topics" in summary

    def test_format_parameters_output_format(self):
        result = self.interface._format_parameters({"output_format": "json"})
        assert "JSON" in result

    def test_format_parameters_filter_apps_single(self):
        result = self.interface._format_parameters({"filter_apps": ["Firefox"]})
        assert "Firefox" in result

    def test_format_parameters_filter_apps_multiple(self):
        result = self.interface._format_parameters({"filter_apps": ["Firefox", "Chrome"]})
        assert "2 specific applications" in result

    def test_format_parameters_empty(self):
        result = self.interface._format_parameters({})
        assert result == ""


class TestUtilityFunctions:
    """Tests for module-level utility functions."""

    def test_load_ai_config(self):
        config = load_ai_config()
        assert "nlp_enabled" in config
        assert "insights_enabled" in config
        assert "conversation_enabled" in config
        assert "confidence_threshold" in config

    def test_create_ai_assistant(self):
        assistant = create_ai_assistant()
        assert isinstance(assistant, ConversationalInterface)
