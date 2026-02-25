"""Machine Learning module for VersionTracker intelligent recommendations.

This module provides ML-powered features including intelligent app-to-cask matching,
personalized recommendations, and usage pattern analysis to improve the user experience.

Note:
    This module requires optional ML dependencies. Install them with:
        pip install homebrew-versiontracker[ml]

    Or install manually:
        pip install numpy scikit-learn
"""

import json
import logging
import pickle  # nosec B403
import time
from pathlib import Path
from typing import Any

from versiontracker.exceptions import VersionTrackerError

logger = logging.getLogger(__name__)

# Check for optional ML dependencies
_HAS_ML_DEPS = False
_ML_IMPORT_ERROR: str | None = None

try:
    import numpy as np
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import accuracy_score
    from sklearn.metrics.pairwise import cosine_similarity
    from sklearn.model_selection import train_test_split
    from sklearn.preprocessing import StandardScaler

    _HAS_ML_DEPS = True
except ImportError as e:
    _ML_IMPORT_ERROR = str(e)
    # Create placeholder types for when sklearn is not available
    np = None  # type: ignore[assignment]
    TfidfVectorizer = None  # type: ignore[assignment, misc]
    LogisticRegression = None  # type: ignore[assignment, misc]
    StandardScaler = None  # type: ignore[assignment, misc]


__all__ = [
    "MLRecommendationEngine",
    "MatchingConfidenceModel",
    "UsageAnalyzer",
    "FeatureExtractor",
    "ModelTrainer",
    "MLError",
    "is_ml_available",
]


def is_ml_available() -> bool:
    """Check if ML dependencies are available.

    Returns:
        True if numpy and scikit-learn are installed, False otherwise.
    """
    return _HAS_ML_DEPS


def _require_ml_deps() -> None:
    """Raise an error if ML dependencies are not available."""
    if not _HAS_ML_DEPS:
        raise MLError(
            f"ML features require additional dependencies. "
            f"Install with: pip install homebrew-versiontracker[ml]\n"
            f"Import error: {_ML_IMPORT_ERROR}"
        )


class MLError(VersionTrackerError):
    """Raised when ML operations fail."""

    pass


class FeatureExtractor:
    """Extract features from application and cask data for ML models."""

    def __init__(self) -> None:
        """Initialize feature extractor."""
        _require_ml_deps()
        self.vectorizer = TfidfVectorizer(
            ngram_range=(1, 3),
            max_features=10000,
            stop_words="english",
            lowercase=True,
            analyzer="char_wb",
        )
        self.fitted = False

    def extract_text_features(self, app_name: str, cask_name: str) -> dict[str, Any]:
        """Extract text-based features for matching."""
        features: dict[str, Any] = {}

        # Basic string metrics
        features["name_length_diff"] = abs(len(app_name) - len(cask_name))
        max_len = max(len(app_name), len(cask_name))
        features["name_length_ratio"] = min(len(app_name), len(cask_name)) / max_len if max_len > 0 else 0

        # Character overlap
        app_chars = set(app_name.lower())
        cask_chars = set(cask_name.lower())
        union_chars = app_chars.union(cask_chars)
        features["char_overlap"] = len(app_chars.intersection(cask_chars)) / len(union_chars) if union_chars else 0

        # Word overlap
        app_words = set(app_name.lower().split())
        cask_words = set(cask_name.lower().replace("-", " ").split())
        if app_words and cask_words:
            union_words = app_words.union(cask_words)
            features["word_overlap"] = len(app_words.intersection(cask_words)) / len(union_words)
        else:
            features["word_overlap"] = 0.0

        # First character match
        features["first_char_match"] = int(app_name[0].lower() == cask_name[0].lower()) if app_name and cask_name else 0

        # Levenshtein-like features
        features["edit_distance_normalized"] = self._normalized_edit_distance(app_name.lower(), cask_name.lower())

        # Substring matching
        features["app_in_cask"] = int(app_name.lower() in cask_name.lower())
        features["cask_in_app"] = int(cask_name.lower().replace("-", " ") in app_name.lower())

        return features

    def extract_metadata_features(self, app_data: dict[str, Any], cask_data: dict[str, Any]) -> dict[str, Any]:
        """Extract metadata-based features."""
        features: dict[str, Any] = {}

        # Developer/publisher matching
        app_developer = app_data.get("developer", "").lower()
        cask_homepage = cask_data.get("homepage", "").lower()
        features["developer_in_homepage"] = (
            int(app_developer in cask_homepage) if app_developer and cask_homepage else 0
        )

        # Category matching
        app_category = app_data.get("category", "").lower()
        cask_desc = cask_data.get("desc", "").lower()
        features["category_in_desc"] = int(app_category in cask_desc) if app_category and cask_desc else 0

        # Version similarity
        app_version = app_data.get("version", "")
        cask_version = cask_data.get("version", "")
        features["version_similarity"] = (
            self._version_similarity(app_version, cask_version) if app_version and cask_version else 0.0
        )

        # Bundle ID matching
        app_bundle_id = app_data.get("bundle_id", "").lower()
        cask_artifacts = str(cask_data.get("artifacts", "")).lower()
        features["bundle_id_in_artifacts"] = (
            int(app_bundle_id in cask_artifacts) if app_bundle_id and cask_artifacts else 0
        )

        return features

    def _normalized_edit_distance(self, s1: str, s2: str) -> float:
        """Calculate normalized edit distance between two strings."""
        if not s1 or not s2:
            return 1.0

        m, n = len(s1), len(s2)
        dp = [[0] * (n + 1) for _ in range(m + 1)]

        for i in range(m + 1):
            dp[i][0] = i
        for j in range(n + 1):
            dp[0][j] = j

        for i in range(1, m + 1):
            for j in range(1, n + 1):
                if s1[i - 1] == s2[j - 1]:
                    dp[i][j] = dp[i - 1][j - 1]
                else:
                    dp[i][j] = 1 + min(dp[i - 1][j], dp[i][j - 1], dp[i - 1][j - 1])

        return dp[m][n] / max(m, n)

    def _version_similarity(self, v1: str, v2: str) -> float:
        """Calculate version similarity score."""
        try:
            v1_parts = [int(x) for x in v1.split(".") if x.isdigit()]
            v2_parts = [int(x) for x in v2.split(".") if x.isdigit()]

            if not v1_parts or not v2_parts:
                return 0.0

            if v1_parts[0] == v2_parts[0]:
                return 1.0
            else:
                return 1.0 / (1.0 + abs(v1_parts[0] - v2_parts[0]))

        except (ValueError, IndexError):
            return 0.0


class MatchingConfidenceModel:
    """ML model to predict confidence scores for app-cask matches."""

    def __init__(self, model_path: Path | None = None) -> None:
        """Initialize the confidence model."""
        _require_ml_deps()
        self.model = LogisticRegression(random_state=42)
        self.scaler = StandardScaler()
        self.feature_extractor = FeatureExtractor()
        self.model_path = model_path or Path.home() / ".config" / "versiontracker" / "ml_models"
        self.model_path.mkdir(parents=True, exist_ok=True)
        self.trained = False

    def train(self, training_data: list[dict[str, Any]]) -> dict[str, Any]:
        """Train the model on labeled matching data."""
        if not training_data:
            raise MLError("No training data provided")

        logger.info("Training confidence model with %s examples", len(training_data))

        X, y = self._prepare_training_data(training_data)

        if len(X) == 0:
            raise MLError("No valid training examples found")

        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)

        X_train_scaled = self.scaler.fit_transform(X_train)
        X_test_scaled = self.scaler.transform(X_test)

        self.model.fit(X_train_scaled, y_train)

        y_pred = self.model.predict(X_test_scaled)
        accuracy = accuracy_score(y_test, y_pred)

        self._save_model()
        self.trained = True

        logger.info("Model trained with accuracy: %s", accuracy)

        return {
            "accuracy": accuracy,
            "training_samples": len(X_train),
            "test_samples": len(X_test),
            "feature_count": X_train.shape[1],
        }

    def predict_confidence(self, app_data: dict[str, Any], cask_data: dict[str, Any]) -> float:
        """Predict confidence score for an app-cask match."""
        if not self.trained:
            self._load_model()

        features = self._extract_match_features(app_data, cask_data)
        X = np.array([list(features.values())])

        X_scaled = self.scaler.transform(X)
        confidence = self.model.predict_proba(X_scaled)[0][1]

        return float(confidence)

    def _prepare_training_data(self, training_data: list[dict[str, Any]]) -> tuple[Any, Any]:
        """Prepare training data for model."""
        features_list = []
        labels = []

        for example in training_data:
            try:
                app_data = example["app"]
                cask_data = example["cask"]
                label = example["match"]

                features = self._extract_match_features(app_data, cask_data)
                features_list.append(list(features.values()))
                labels.append(label)

            except KeyError as e:
                logger.warning("Skipping invalid training example: missing key %s", e)
                continue

        return np.array(features_list), np.array(labels)

    def _extract_match_features(self, app_data: dict[str, Any], cask_data: dict[str, Any]) -> dict[str, Any]:
        """Extract all features for a match prediction."""
        app_name = app_data.get("name", "")
        cask_name = cask_data.get("name", "")

        text_features = self.feature_extractor.extract_text_features(app_name, cask_name)
        metadata_features = self.feature_extractor.extract_metadata_features(app_data, cask_data)

        return {**text_features, **metadata_features}

    def _save_model(self) -> None:
        """Save trained model and scaler."""
        model_file = self.model_path / "confidence_model.pkl"
        scaler_file = self.model_path / "scaler.pkl"

        with open(model_file, "wb") as f:
            pickle.dump(self.model, f)

        with open(scaler_file, "wb") as f:
            pickle.dump(self.scaler, f)

        logger.info("Model saved to %s", model_file)

    def _load_model(self) -> None:
        """Load trained model and scaler."""
        model_file = self.model_path / "confidence_model.pkl"
        scaler_file = self.model_path / "scaler.pkl"

        if not model_file.exists() or not scaler_file.exists():
            logger.warning("No trained model found, using default behavior")
            return

        try:
            with open(model_file, "rb") as f:
                self.model = pickle.load(f)  # nosec B301

            with open(scaler_file, "rb") as f:
                self.scaler = pickle.load(f)  # nosec B301

            self.trained = True
            logger.info("Model loaded successfully")

        except Exception as e:
            logger.error("Failed to load model: %s", e)


class UsageAnalyzer:
    """Analyze user behavior and preferences for personalized recommendations.

    This class does not require ML dependencies and works standalone.
    """

    def __init__(self, data_path: Path | None = None) -> None:
        """Initialize usage analyzer."""
        self.data_path = data_path or Path.home() / ".config" / "versiontracker" / "usage_data.json"
        self.usage_data = self._load_usage_data()

    def record_match_feedback(self, app_name: str, cask_name: str, accepted: bool, confidence: float) -> None:
        """Record user feedback on match recommendations."""
        timestamp = time.time()

        feedback_entry = {
            "app_name": app_name,
            "cask_name": cask_name,
            "accepted": accepted,
            "confidence": confidence,
            "timestamp": timestamp,
        }

        if "match_feedback" not in self.usage_data:
            self.usage_data["match_feedback"] = []

        self.usage_data["match_feedback"].append(feedback_entry)
        self._save_usage_data()

        logger.info("Recorded feedback: %s -> %s (%s)", app_name, cask_name, "accepted" if accepted else "rejected")

    def record_app_usage(self, app_name: str, action: str, metadata: dict[str, Any] | None = None) -> None:
        """Record application usage patterns."""
        timestamp = time.time()

        usage_entry = {
            "app_name": app_name,
            "action": action,
            "timestamp": timestamp,
            "metadata": metadata or {},
        }

        if "app_usage" not in self.usage_data:
            self.usage_data["app_usage"] = []

        self.usage_data["app_usage"].append(usage_entry)
        self._save_usage_data()

    def get_user_preferences(self) -> dict[str, Any]:
        """Analyze usage data to determine user preferences."""
        return {
            "preferred_categories": self._get_preferred_categories(),
            "update_frequency": self._analyze_update_frequency(),
            "acceptance_threshold": self._calculate_acceptance_threshold(),
            "developer_preferences": self._get_developer_preferences(),
        }

    def get_personalized_threshold(self, app_name: str) -> float:
        """Get personalized confidence threshold for recommendations."""
        base_threshold = 0.7
        feedback_history = self.usage_data.get("match_feedback", [])

        if not feedback_history:
            return base_threshold

        total_feedback = len(feedback_history)
        accepted_feedback = sum(1 for f in feedback_history if f["accepted"])
        acceptance_rate = accepted_feedback / total_feedback if total_feedback > 0 else 0.5

        if acceptance_rate > 0.8:
            return max(0.5, base_threshold - 0.2)
        elif acceptance_rate < 0.3:
            return min(0.9, base_threshold + 0.2)
        else:
            return base_threshold

    def _get_preferred_categories(self) -> list[str]:
        """Identify user's preferred application categories."""
        app_usage = self.usage_data.get("app_usage", [])
        category_counts: dict[str, int] = {}

        for usage in app_usage:
            metadata = usage.get("metadata", {})
            category = metadata.get("category")
            if category:
                category_counts[category] = category_counts.get(category, 0) + 1

        return sorted(category_counts.keys(), key=lambda x: category_counts[x], reverse=True)[:5]

    def _analyze_update_frequency(self) -> str:
        """Analyze how frequently user updates applications."""
        app_usage = self.usage_data.get("app_usage", [])
        update_actions = [u for u in app_usage if u["action"] == "updated"]

        if len(update_actions) < 2:
            return "unknown"

        update_times = sorted([u["timestamp"] for u in update_actions])
        intervals = [update_times[i] - update_times[i - 1] for i in range(1, len(update_times))]

        avg_interval = sum(intervals) / len(intervals)
        days = avg_interval / (24 * 3600)

        if days < 7:
            return "frequent"
        elif days < 30:
            return "regular"
        else:
            return "infrequent"

    def _calculate_acceptance_threshold(self) -> float:
        """Calculate user's typical acceptance threshold."""
        feedback_history = self.usage_data.get("match_feedback", [])

        if not feedback_history:
            return 0.7

        accepted_confidences = [f["confidence"] for f in feedback_history if f["accepted"]]
        rejected_confidences = [f["confidence"] for f in feedback_history if not f["accepted"]]

        if not accepted_confidences:
            return 0.9
        if not rejected_confidences:
            return 0.3

        min_accepted = min(accepted_confidences)
        max_rejected = max(rejected_confidences)

        return (min_accepted + max_rejected) / 2

    def _get_developer_preferences(self) -> list[str]:
        """Identify preferred developers based on app usage."""
        app_usage = self.usage_data.get("app_usage", [])
        developer_counts: dict[str, int] = {}

        for usage in app_usage:
            metadata = usage.get("metadata", {})
            developer = metadata.get("developer")
            if developer:
                developer_counts[developer] = developer_counts.get(developer, 0) + 1

        return sorted(developer_counts.keys(), key=lambda x: developer_counts[x], reverse=True)[:10]

    def _load_usage_data(self) -> dict[str, Any]:
        """Load usage data from file."""
        if not self.data_path.exists():
            return {}

        try:
            with open(self.data_path) as f:
                return json.load(f)
        except (OSError, json.JSONDecodeError) as e:
            logger.warning("Failed to load usage data: %s", e)
            return {}

    def _save_usage_data(self) -> None:
        """Save usage data to file."""
        try:
            self.data_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.data_path, "w") as f:
                json.dump(self.usage_data, f, indent=2)
        except OSError as e:
            logger.error("Failed to save usage data: %s", e)


class MLRecommendationEngine:
    """Main ML-powered recommendation engine."""

    def __init__(self) -> None:
        """Initialize the ML recommendation engine."""
        _require_ml_deps()
        self.confidence_model = MatchingConfidenceModel()
        self.usage_analyzer = UsageAnalyzer()
        self.vectorizer = TfidfVectorizer(
            ngram_range=(1, 2),
            max_features=5000,
            stop_words="english",
            lowercase=True,
        )
        self.app_embeddings: Any = None
        self.cask_embeddings: Any = None
        self.fitted = False

    def initialize(self, apps: list[dict[str, Any]], casks: list[dict[str, Any]]) -> None:
        """Initialize the engine with application and cask data."""
        logger.info("Initializing ML engine with %s apps and %s casks", len(apps), len(casks))

        app_texts = [self._prepare_app_text(app) for app in apps]
        cask_texts = [self._prepare_cask_text(cask) for cask in casks]

        all_texts = app_texts + cask_texts
        self.vectorizer.fit(all_texts)

        self.app_embeddings = self.vectorizer.transform(app_texts)
        self.cask_embeddings = self.vectorizer.transform(cask_texts)

        self.fitted = True
        logger.info("ML engine initialization complete")

    def get_recommendations(
        self,
        apps: list[dict[str, Any]],
        casks: list[dict[str, Any]],
        threshold: float | None = None,
    ) -> list[dict[str, Any]]:
        """Get ML-powered recommendations for apps."""
        if not self.fitted:
            self.initialize(apps, casks)

        recommendations = []

        for i, app in enumerate(apps):
            app_name = app.get("name", "")

            if threshold is None:
                personal_threshold = self.usage_analyzer.get_personalized_threshold(app_name)
            else:
                personal_threshold = threshold

            app_vector = self.app_embeddings[i : i + 1]
            similarities = cosine_similarity(app_vector, self.cask_embeddings).flatten()

            top_indices = np.argsort(similarities)[::-1][:10]

            for cask_idx in top_indices:
                cask = casks[cask_idx]
                similarity = similarities[cask_idx]

                if similarity < 0.1:
                    continue

                try:
                    confidence = self.confidence_model.predict_confidence(app, cask)
                except Exception as e:
                    logger.warning("Failed to get ML confidence: %s", e)
                    confidence = similarity

                combined_score = (similarity * 0.4) + (confidence * 0.6)

                if combined_score >= personal_threshold:
                    recommendation = {
                        "app": app,
                        "cask": cask,
                        "similarity_score": float(similarity),
                        "ml_confidence": float(confidence),
                        "combined_score": float(combined_score),
                        "threshold_used": personal_threshold,
                        "recommendation_source": "ml_engine",
                    }
                    recommendations.append(recommendation)

        recommendations.sort(key=lambda x: x["combined_score"], reverse=True)

        logger.info("Generated %s ML-powered recommendations", len(recommendations))
        return recommendations

    def record_feedback(self, app_name: str, cask_name: str, accepted: bool, confidence: float) -> None:
        """Record user feedback for continuous learning."""
        self.usage_analyzer.record_match_feedback(app_name, cask_name, accepted, confidence)

    def retrain_model(self) -> None:
        """Retrain the confidence model with new feedback data."""
        feedback_data = self.usage_analyzer.usage_data.get("match_feedback", [])

        if len(feedback_data) < 10:
            logger.info("Insufficient feedback data for retraining")
            return

        logger.info("Model retraining feature pending full implementation")

    def _prepare_app_text(self, app: dict[str, Any]) -> str:
        """Prepare application text for vectorization."""
        parts = []
        for key in ("name", "developer", "category", "description"):
            if app.get(key):
                parts.append(app[key])
        return " ".join(parts)

    def _prepare_cask_text(self, cask: dict[str, Any]) -> str:
        """Prepare cask text for vectorization."""
        import re

        parts = []

        if cask.get("name"):
            parts.append(cask["name"].replace("-", " "))
        if cask.get("desc"):
            parts.append(cask["desc"])
        if cask.get("homepage"):
            domain_match = re.search(r"https?://(?:www\.)?([^/]+)", cask["homepage"])
            if domain_match:
                parts.append(domain_match.group(1))

        return " ".join(parts)


class ModelTrainer:
    """Utility class for training ML models with labeled data."""

    def __init__(self) -> None:
        """Initialize model trainer."""
        _require_ml_deps()
        self.confidence_model = MatchingConfidenceModel()

    def generate_synthetic_training_data(
        self,
        apps: list[dict[str, Any]],
        casks: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Generate synthetic training data for bootstrapping."""
        training_data = []

        positive_pairs = self._generate_positive_pairs(apps, casks)
        for app, cask in positive_pairs:
            training_data.append({"app": app, "cask": cask, "match": 1})

        negative_pairs = self._generate_negative_pairs(apps, casks, len(positive_pairs))
        for app, cask in negative_pairs:
            training_data.append({"app": app, "cask": cask, "match": 0})

        logger.info("Generated %s synthetic training examples", len(training_data))
        return training_data

    def _generate_positive_pairs(
        self,
        apps: list[dict[str, Any]],
        casks: list[dict[str, Any]],
    ) -> list[tuple[dict[str, Any], dict[str, Any]]]:
        """Generate positive training pairs based on name similarity."""
        pairs = []

        for app in apps:
            app_name = app.get("name", "").lower()

            for cask in casks:
                cask_name = cask.get("name", "").lower().replace("-", " ")

                if app_name in cask_name or cask_name in app_name or self._fuzzy_match(app_name, cask_name) > 0.8:
                    pairs.append((app, cask))
                    break

        return pairs[:50]

    def _generate_negative_pairs(
        self,
        apps: list[dict[str, Any]],
        casks: list[dict[str, Any]],
        count: int,
    ) -> list[tuple[dict[str, Any], dict[str, Any]]]:
        """Generate negative training pairs."""
        import random

        pairs = []
        attempts = 0
        max_attempts = count * 10

        while len(pairs) < count and attempts < max_attempts:
            app = random.choice(apps)  # nosec B311
            cask = random.choice(casks)  # nosec B311

            app_name = app.get("name", "").lower()
            cask_name = cask.get("name", "").lower().replace("-", " ")

            if self._fuzzy_match(app_name, cask_name) < 0.3:
                pairs.append((app, cask))

            attempts += 1

        return pairs

    def _fuzzy_match(self, s1: str, s2: str) -> float:
        """Simple fuzzy string matching."""
        if not s1 or not s2:
            return 0.0

        tokens1 = set(s1.split())
        tokens2 = set(s2.split())

        if not tokens1 or not tokens2:
            return 0.0

        intersection = len(tokens1.intersection(tokens2))
        union = len(tokens1.union(tokens2))

        return intersection / union if union > 0 else 0.0
