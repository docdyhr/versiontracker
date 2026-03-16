"""Tests for the ML module (UsageAnalyzer, FeatureExtractor, etc.).

UsageAnalyzer tests run without ML dependencies.
Other tests are skipped if numpy/scikit-learn are not installed.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from versiontracker.ml import MLError, UsageAnalyzer, is_ml_available


class TestIsMLAvailable:
    """Tests for is_ml_available function."""

    def test_returns_bool(self):
        result = is_ml_available()
        assert isinstance(result, bool)


class TestMLError:
    """Tests for MLError exception."""

    def test_ml_error_is_versiontracker_error(self):
        from versiontracker.exceptions import VersionTrackerError

        error = MLError("test error")
        assert isinstance(error, VersionTrackerError)
        assert str(error) == "test error"


class TestUsageAnalyzer:
    """Tests for UsageAnalyzer (no ML deps required)."""

    def setup_method(self, tmp_path_factory=None):
        self.tmp_path = Path("/tmp/vt_test_usage")
        self.tmp_path.mkdir(parents=True, exist_ok=True)
        self.data_file = self.tmp_path / "usage_data.json"
        # Clean state
        if self.data_file.exists():
            self.data_file.unlink()
        self.analyzer = UsageAnalyzer(data_path=self.data_file)

    def teardown_method(self):
        if self.data_file.exists():
            self.data_file.unlink()

    def test_init_empty(self):
        assert self.analyzer.usage_data == {}
        assert self.analyzer.data_path == self.data_file

    def test_record_match_feedback(self):
        self.analyzer.record_match_feedback("Firefox", "firefox", True, 0.9)
        assert len(self.analyzer.usage_data["match_feedback"]) == 1
        entry = self.analyzer.usage_data["match_feedback"][0]
        assert entry["app_name"] == "Firefox"
        assert entry["cask_name"] == "firefox"
        assert entry["accepted"] is True
        assert entry["confidence"] == 0.9

    def test_record_app_usage(self):
        self.analyzer.record_app_usage("Firefox", "launched", {"category": "Browser"})
        assert len(self.analyzer.usage_data["app_usage"]) == 1
        entry = self.analyzer.usage_data["app_usage"][0]
        assert entry["app_name"] == "Firefox"
        assert entry["action"] == "launched"

    def test_get_user_preferences_empty(self):
        prefs = self.analyzer.get_user_preferences()
        assert "preferred_categories" in prefs
        assert "update_frequency" in prefs
        assert "acceptance_threshold" in prefs
        assert "developer_preferences" in prefs

    def test_get_personalized_threshold_no_feedback(self):
        threshold = self.analyzer.get_personalized_threshold("Firefox")
        assert threshold == 0.7  # Base threshold

    def test_get_personalized_threshold_high_acceptance(self):
        for _ in range(10):
            self.analyzer.record_match_feedback("App", "cask", True, 0.8)
        threshold = self.analyzer.get_personalized_threshold("App")
        assert threshold < 0.7  # Should lower threshold for accepting users

    def test_get_personalized_threshold_low_acceptance(self):
        for _ in range(10):
            self.analyzer.record_match_feedback("App", "cask", False, 0.5)
        threshold = self.analyzer.get_personalized_threshold("App")
        assert threshold > 0.7  # Should raise threshold for rejecting users

    def test_preferred_categories(self):
        self.analyzer.record_app_usage("VSCode", "launched", {"category": "Editor"})
        self.analyzer.record_app_usage("Sublime", "launched", {"category": "Editor"})
        self.analyzer.record_app_usage("Firefox", "launched", {"category": "Browser"})
        prefs = self.analyzer._get_preferred_categories()
        assert "Editor" in prefs

    def test_update_frequency_unknown(self):
        freq = self.analyzer._analyze_update_frequency()
        assert freq == "unknown"

    def test_acceptance_threshold_no_feedback(self):
        threshold = self.analyzer._calculate_acceptance_threshold()
        assert threshold == 0.7

    def test_acceptance_threshold_all_accepted(self):
        self.analyzer.usage_data["match_feedback"] = [{"accepted": True, "confidence": 0.8} for _ in range(5)]
        threshold = self.analyzer._calculate_acceptance_threshold()
        assert threshold == 0.3  # No rejected → return 0.3

    def test_acceptance_threshold_all_rejected(self):
        self.analyzer.usage_data["match_feedback"] = [{"accepted": False, "confidence": 0.5} for _ in range(5)]
        threshold = self.analyzer._calculate_acceptance_threshold()
        assert threshold == 0.9  # No accepted → return 0.9

    def test_developer_preferences(self):
        self.analyzer.record_app_usage("VSCode", "launched", {"developer": "Microsoft"})
        self.analyzer.record_app_usage("Edge", "launched", {"developer": "Microsoft"})
        devs = self.analyzer._get_developer_preferences()
        assert "Microsoft" in devs

    def test_persistence(self):
        self.analyzer.record_match_feedback("Firefox", "firefox", True, 0.9)

        # Create new analyzer from same file
        new_analyzer = UsageAnalyzer(data_path=self.data_file)
        assert len(new_analyzer.usage_data.get("match_feedback", [])) == 1

    def test_load_corrupted_data(self):
        self.data_file.write_text("not valid json{{{")
        analyzer = UsageAnalyzer(data_path=self.data_file)
        assert analyzer.usage_data == {}

    def test_save_creates_parent_dirs(self):
        deep_path = self.tmp_path / "deep" / "nested" / "usage.json"
        analyzer = UsageAnalyzer(data_path=deep_path)
        analyzer.record_app_usage("test", "launched")
        assert deep_path.exists()


# Tests that require ML dependencies
requires_ml = pytest.mark.skipif(not is_ml_available(), reason="ML dependencies (numpy, scikit-learn) not installed")


@requires_ml
class TestFeatureExtractor:
    """Tests for FeatureExtractor (requires ML deps)."""

    def setup_method(self):
        from versiontracker.ml import FeatureExtractor

        self.extractor = FeatureExtractor()

    def test_extract_text_features(self):
        features = self.extractor.extract_text_features("Firefox", "firefox")
        assert "name_length_diff" in features
        assert "char_overlap" in features
        assert "word_overlap" in features
        assert "first_char_match" in features
        assert features["name_length_diff"] == 0
        assert features["first_char_match"] == 1

    def test_extract_text_features_different_names(self):
        features = self.extractor.extract_text_features("Visual Studio Code", "vscode")
        assert features["name_length_diff"] > 0
        assert 0.0 <= features["char_overlap"] <= 1.0

    def test_extract_metadata_features(self):
        app_data = {"developer": "Mozilla", "category": "Browser", "version": "120.0", "bundle_id": "org.mozilla"}
        cask_data = {
            "homepage": "https://mozilla.org",
            "desc": "Web browser",
            "version": "120.0",
            "artifacts": "org.mozilla.firefox",
        }
        features = self.extractor.extract_metadata_features(app_data, cask_data)
        assert "developer_in_homepage" in features
        assert "category_in_desc" in features
        assert "version_similarity" in features
        assert features["developer_in_homepage"] == 1

    def test_normalized_edit_distance_identical(self):
        dist = self.extractor._normalized_edit_distance("firefox", "firefox")
        assert dist == 0.0

    def test_normalized_edit_distance_empty(self):
        dist = self.extractor._normalized_edit_distance("", "test")
        assert dist == 1.0

    def test_version_similarity_same_major(self):
        sim = self.extractor._version_similarity("3.2.1", "3.5.0")
        assert sim == 1.0

    def test_version_similarity_different_major(self):
        sim = self.extractor._version_similarity("1.0", "5.0")
        assert 0.0 < sim < 1.0

    def test_version_similarity_invalid(self):
        sim = self.extractor._version_similarity("abc", "def")
        assert sim == 0.0


@requires_ml
class TestMatchingConfidenceModel:
    """Tests for MatchingConfidenceModel (requires ML deps)."""

    def test_init(self):
        from versiontracker.ml import MatchingConfidenceModel

        model = MatchingConfidenceModel(model_path=Path("/tmp/vt_test_models"))
        assert model.trained is False

    def test_train_empty_raises(self):
        from versiontracker.ml import MatchingConfidenceModel

        model = MatchingConfidenceModel(model_path=Path("/tmp/vt_test_models"))
        with pytest.raises(MLError, match="No training data"):
            model.train([])


@requires_ml
class TestModelTrainer:
    """Tests for ModelTrainer (requires ML deps)."""

    def test_generate_synthetic_data(self):
        from versiontracker.ml import ModelTrainer

        trainer = ModelTrainer()
        apps = [
            {"name": "Firefox"},
            {"name": "Chrome"},
            {"name": "VSCode"},
        ]
        casks = [
            {"name": "firefox"},
            {"name": "google-chrome"},
            {"name": "visual-studio-code"},
            {"name": "slack"},
        ]
        data = trainer.generate_synthetic_training_data(apps, casks)
        assert isinstance(data, list)
        if data:
            assert "app" in data[0]
            assert "cask" in data[0]
            assert "match" in data[0]

    def test_fuzzy_match_identical(self):
        from versiontracker.ml import ModelTrainer

        trainer = ModelTrainer()
        assert trainer._fuzzy_match("firefox", "firefox") == 1.0

    def test_fuzzy_match_empty(self):
        from versiontracker.ml import ModelTrainer

        trainer = ModelTrainer()
        assert trainer._fuzzy_match("", "test") == 0.0


class TestRequireMLDeps:
    """Tests for _require_ml_deps guard."""

    def test_require_ml_deps_when_unavailable(self):
        from versiontracker import ml

        original = ml._HAS_ML_DEPS
        try:
            ml._HAS_ML_DEPS = False
            with pytest.raises(MLError, match="ML features require"):
                ml._require_ml_deps()
        finally:
            ml._HAS_ML_DEPS = original

    def test_feature_extractor_raises_without_deps(self):
        from versiontracker import ml

        original = ml._HAS_ML_DEPS
        try:
            ml._HAS_ML_DEPS = False
            with pytest.raises(MLError):
                ml.FeatureExtractor()
        finally:
            ml._HAS_ML_DEPS = original
