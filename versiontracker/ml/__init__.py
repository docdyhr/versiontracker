"""
Machine Learning module for VersionTracker intelligent recommendations.

This module provides ML-powered features including intelligent app-to-cask matching,
personalized recommendations, and usage pattern analysis to improve the user experience.
"""

import json
import logging
import pickle
import time
from pathlib import Path
from typing import Any

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

# from versiontracker.config import get_config
from versiontracker.exceptions import VersionTrackerError

logger = logging.getLogger(__name__)

__all__ = [
    "MLRecommendationEngine",
    "MatchingConfidenceModel",
    "UsageAnalyzer",
    "FeatureExtractor",
    "ModelTrainer",
    "MLError",
]


class MLError(VersionTrackerError):
    """Raised when ML operations fail."""

    pass


class FeatureExtractor:
    """Extract features from application and cask data for ML models."""

    def __init__(self):
        """Initialize feature extractor."""
        self.vectorizer = TfidfVectorizer(
            ngram_range=(1, 3), max_features=10000, stop_words="english", lowercase=True, analyzer="char_wb"
        )
        self.fitted = False

    def extract_text_features(self, app_name: str, cask_name: str) -> dict[str, Any]:
        """Extract text-based features for matching."""
        features = {}

        # Basic string metrics
        features["name_length_diff"] = abs(len(app_name) - len(cask_name))
        features["name_length_ratio"] = min(len(app_name), len(cask_name)) / max(len(app_name), len(cask_name))

        # Character overlap
        app_chars = set(app_name.lower())
        cask_chars = set(cask_name.lower())
        features["char_overlap"] = len(app_chars.intersection(cask_chars)) / len(app_chars.union(cask_chars))

        # Word overlap
        app_words = set(app_name.lower().split())
        cask_words = set(cask_name.lower().replace("-", " ").split())
        if app_words and cask_words:
            features["word_overlap"] = len(app_words.intersection(cask_words)) / len(app_words.union(cask_words))
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
        features = {}

        # Developer/publisher matching
        app_developer = app_data.get("developer", "").lower()
        cask_homepage = cask_data.get("homepage", "").lower()

        if app_developer and cask_homepage:
            features["developer_in_homepage"] = int(app_developer in cask_homepage)
        else:
            features["developer_in_homepage"] = 0

        # Category matching
        app_category = app_data.get("category", "").lower()
        cask_desc = cask_data.get("desc", "").lower()

        if app_category and cask_desc:
            features["category_in_desc"] = int(app_category in cask_desc)
        else:
            features["category_in_desc"] = 0

        # Version similarity
        app_version = app_data.get("version", "")
        cask_version = cask_data.get("version", "")

        if app_version and cask_version:
            features["version_similarity"] = self._version_similarity(app_version, cask_version)
        else:
            features["version_similarity"] = 0.0

        # Bundle ID matching
        app_bundle_id = app_data.get("bundle_id", "").lower()
        cask_artifacts = str(cask_data.get("artifacts", "")).lower()

        if app_bundle_id and cask_artifacts:
            features["bundle_id_in_artifacts"] = int(app_bundle_id in cask_artifacts)
        else:
            features["bundle_id_in_artifacts"] = 0

        return features

    def _normalized_edit_distance(self, s1: str, s2: str) -> float:
        """Calculate normalized edit distance between two strings."""
        if not s1 or not s2:
            return 1.0

        # Simple Levenshtein distance implementation
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
            # Extract numeric parts
            v1_parts = [int(x) for x in v1.split(".") if x.isdigit()]
            v2_parts = [int(x) for x in v2.split(".") if x.isdigit()]

            if not v1_parts or not v2_parts:
                return 0.0

            # Compare major versions
            if v1_parts[0] == v2_parts[0]:
                return 1.0
            else:
                # Penalize major version differences
                return 1.0 / (1.0 + abs(v1_parts[0] - v2_parts[0]))

        except (ValueError, IndexError):
            return 0.0


class MatchingConfidenceModel:
    """ML model to predict confidence scores for app-cask matches."""

    def __init__(self, model_path: Path | None = None):
        """Initialize the confidence model."""
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

        logger.info(f"Training confidence model with {len(training_data)} examples")

        # Extract features and labels
        X, y = self._prepare_training_data(training_data)

        if len(X) == 0:
            raise MLError("No valid training examples found")

        # Split data
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)

        # Scale features
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_test_scaled = self.scaler.transform(X_test)

        # Train model
        self.model.fit(X_train_scaled, y_train)

        # Evaluate
        y_pred = self.model.predict(X_test_scaled)
        accuracy = accuracy_score(y_test, y_pred)

        # Save model
        self._save_model()
        self.trained = True

        logger.info(f"Model trained with accuracy: {accuracy:.3f}")

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

        # Extract features
        features = self._extract_match_features(app_data, cask_data)
        X = np.array([list(features.values())])

        # Scale features
        X_scaled = self.scaler.transform(X)

        # Predict probability of positive match
        confidence = self.model.predict_proba(X_scaled)[0][1]

        return float(confidence)

    def _prepare_training_data(self, training_data: list[dict[str, Any]]) -> tuple[np.ndarray, np.ndarray]:
        """Prepare training data for model."""
        features_list = []
        labels = []

        for example in training_data:
            try:
                app_data = example["app"]
                cask_data = example["cask"]
                label = example["match"]  # 1 for positive match, 0 for negative

                features = self._extract_match_features(app_data, cask_data)
                features_list.append(list(features.values()))
                labels.append(label)

            except KeyError as e:
                logger.warning(f"Skipping invalid training example: missing key {e}")
                continue

        return np.array(features_list), np.array(labels)

    def _extract_match_features(self, app_data: dict[str, Any], cask_data: dict[str, Any]) -> dict[str, Any]:
        """Extract all features for a match prediction."""
        app_name = app_data.get("name", "")
        cask_name = cask_data.get("name", "")

        # Combine text and metadata features
        text_features = self.feature_extractor.extract_text_features(app_name, cask_name)
        metadata_features = self.feature_extractor.extract_metadata_features(app_data, cask_data)

        return {**text_features, **metadata_features}

    def _save_model(self):
        """Save trained model and scaler."""
        model_file = self.model_path / "confidence_model.pkl"
        scaler_file = self.model_path / "scaler.pkl"

        with open(model_file, "wb") as f:
            pickle.dump(self.model, f)

        with open(scaler_file, "wb") as f:
            pickle.dump(self.scaler, f)

        logger.info(f"Model saved to {model_file}")

    def _load_model(self):
        """Load trained model and scaler."""
        model_file = self.model_path / "confidence_model.pkl"
        scaler_file = self.model_path / "scaler.pkl"

        if not model_file.exists() or not scaler_file.exists():
            logger.warning("No trained model found, using default behavior")
            return

        try:
            with open(model_file, "rb") as f:
                self.model = pickle.load(f)

            with open(scaler_file, "rb") as f:
                self.scaler = pickle.load(f)

            self.trained = True
            logger.info("Model loaded successfully")

        except Exception as e:
            logger.error(f"Failed to load model: {e}")


class UsageAnalyzer:
    """Analyze user behavior and preferences for personalized recommendations."""

    def __init__(self, data_path: Path | None = None):
        """Initialize usage analyzer."""
        self.data_path = data_path or Path.home() / ".config" / "versiontracker" / "usage_data.json"
        self.usage_data = self._load_usage_data()

    def record_match_feedback(self, app_name: str, cask_name: str, accepted: bool, confidence: float):
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

        logger.info(f"Recorded feedback: {app_name} -> {cask_name} ({'accepted' if accepted else 'rejected'})")

    def record_app_usage(self, app_name: str, action: str, metadata: dict[str, Any] | None = None):
        """Record application usage patterns."""
        timestamp = time.time()

        usage_entry = {
            "app_name": app_name,
            "action": action,  # "launched", "updated", "installed", "removed"
            "timestamp": timestamp,
            "metadata": metadata or {},
        }

        if "app_usage" not in self.usage_data:
            self.usage_data["app_usage"] = []

        self.usage_data["app_usage"].append(usage_entry)
        self._save_usage_data()

    def get_user_preferences(self) -> dict[str, Any]:
        """Analyze usage data to determine user preferences."""
        preferences = {
            "preferred_categories": self._get_preferred_categories(),
            "update_frequency": self._analyze_update_frequency(),
            "acceptance_threshold": self._calculate_acceptance_threshold(),
            "developer_preferences": self._get_developer_preferences(),
        }

        return preferences

    def get_personalized_threshold(self, app_name: str) -> float:
        """Get personalized confidence threshold for recommendations."""
        base_threshold = 0.7

        # Analyze historical feedback for similar apps
        feedback_history = self.usage_data.get("match_feedback", [])

        if not feedback_history:
            return base_threshold

        # Calculate acceptance rate for this user
        total_feedback = len(feedback_history)
        accepted_feedback = sum(1 for f in feedback_history if f["accepted"])
        acceptance_rate = accepted_feedback / total_feedback if total_feedback > 0 else 0.5

        # Adjust threshold based on user's acceptance pattern
        if acceptance_rate > 0.8:
            # User accepts most recommendations - lower threshold
            return max(0.5, base_threshold - 0.2)
        elif acceptance_rate < 0.3:
            # User is selective - higher threshold
            return min(0.9, base_threshold + 0.2)
        else:
            return base_threshold

    def _get_preferred_categories(self) -> list[str]:
        """Identify user's preferred application categories."""
        app_usage = self.usage_data.get("app_usage", [])
        category_counts = {}

        for usage in app_usage:
            metadata = usage.get("metadata", {})
            category = metadata.get("category")
            if category:
                category_counts[category] = category_counts.get(category, 0) + 1

        # Return top 5 categories
        return sorted(category_counts.keys(), key=category_counts.get, reverse=True)[:5]

    def _analyze_update_frequency(self) -> str:
        """Analyze how frequently user updates applications."""
        app_usage = self.usage_data.get("app_usage", [])
        update_actions = [u for u in app_usage if u["action"] == "updated"]

        if len(update_actions) < 2:
            return "unknown"

        # Calculate average time between updates
        update_times = [u["timestamp"] for u in update_actions]
        update_times.sort()

        intervals = []
        for i in range(1, len(update_times)):
            intervals.append(update_times[i] - update_times[i - 1])

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

        # Find the confidence level that best separates accepted from rejected
        min_accepted = min(accepted_confidences)
        max_rejected = max(rejected_confidences)

        return (min_accepted + max_rejected) / 2

    def _get_developer_preferences(self) -> list[str]:
        """Identify preferred developers based on app usage."""
        app_usage = self.usage_data.get("app_usage", [])
        developer_counts = {}

        for usage in app_usage:
            metadata = usage.get("metadata", {})
            developer = metadata.get("developer")
            if developer:
                developer_counts[developer] = developer_counts.get(developer, 0) + 1

        # Return top 10 developers
        return sorted(developer_counts.keys(), key=developer_counts.get, reverse=True)[:10]

    def _load_usage_data(self) -> dict[str, Any]:
        """Load usage data from file."""
        if not self.data_path.exists():
            return {}

        try:
            with open(self.data_path) as f:
                return json.load(f)
        except (OSError, json.JSONDecodeError) as e:
            logger.warning(f"Failed to load usage data: {e}")
            return {}

    def _save_usage_data(self):
        """Save usage data to file."""
        try:
            self.data_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.data_path, "w") as f:
                json.dump(self.usage_data, f, indent=2)
        except OSError as e:
            logger.error(f"Failed to save usage data: {e}")


class MLRecommendationEngine:
    """Main ML-powered recommendation engine."""

    def __init__(self):
        """Initialize the ML recommendation engine."""
        self.confidence_model = MatchingConfidenceModel()
        self.usage_analyzer = UsageAnalyzer()
        self.vectorizer = TfidfVectorizer(ngram_range=(1, 2), max_features=5000, stop_words="english", lowercase=True)
        self.app_embeddings = None
        self.cask_embeddings = None
        self.fitted = False

    def initialize(self, apps: list[dict[str, Any]], casks: list[dict[str, Any]]):
        """Initialize the engine with application and cask data."""
        logger.info(f"Initializing ML engine with {len(apps)} apps and {len(casks)} casks")

        # Prepare text data for vectorization
        app_texts = [self._prepare_app_text(app) for app in apps]
        cask_texts = [self._prepare_cask_text(cask) for cask in casks]

        # Fit vectorizer on combined corpus
        all_texts = app_texts + cask_texts
        self.vectorizer.fit(all_texts)

        # Generate embeddings
        self.app_embeddings = self.vectorizer.transform(app_texts)
        self.cask_embeddings = self.vectorizer.transform(cask_texts)

        self.fitted = True
        logger.info("ML engine initialization complete")

    def get_recommendations(
        self, apps: list[dict[str, Any]], casks: list[dict[str, Any]], threshold: float | None = None
    ) -> list[dict[str, Any]]:
        """Get ML-powered recommendations for apps."""
        if not self.fitted:
            self.initialize(apps, casks)

        recommendations = []

        for i, app in enumerate(apps):
            app_name = app.get("name", "")

            # Get personalized threshold if not provided
            if threshold is None:
                personal_threshold = self.usage_analyzer.get_personalized_threshold(app_name)
            else:
                personal_threshold = threshold

            # Calculate similarities using TF-IDF vectors
            app_vector = self.app_embeddings[i : i + 1]
            similarities = cosine_similarity(app_vector, self.cask_embeddings).flatten()

            # Get top candidates based on similarity
            top_indices = np.argsort(similarities)[::-1][:10]

            for cask_idx in top_indices:
                cask = casks[cask_idx]
                similarity = similarities[cask_idx]

                # Skip low similarity matches
                if similarity < 0.1:
                    continue

                # Get ML confidence score
                try:
                    confidence = self.confidence_model.predict_confidence(app, cask)
                except Exception as e:
                    logger.warning(f"Failed to get ML confidence: {e}")
                    confidence = similarity  # Fallback to similarity

                # Combine similarity and ML confidence
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

        # Sort by combined score
        recommendations.sort(key=lambda x: x["combined_score"], reverse=True)

        logger.info(f"Generated {len(recommendations)} ML-powered recommendations")
        return recommendations

    def record_feedback(self, app_name: str, cask_name: str, accepted: bool, confidence: float):
        """Record user feedback for continuous learning."""
        self.usage_analyzer.record_match_feedback(app_name, cask_name, accepted, confidence)

    def retrain_model(self):
        """Retrain the confidence model with new feedback data."""
        feedback_data = self.usage_analyzer.usage_data.get("match_feedback", [])

        if len(feedback_data) < 10:
            logger.info("Insufficient feedback data for retraining")
            return

        # Convert feedback to training format
        for _feedback in feedback_data:
            # This would need actual app and cask data
            # For now, we'll skip retraining until we have proper data structure
            pass

        logger.info("Model retraining feature pending full implementation")

    def _prepare_app_text(self, app: dict[str, Any]) -> str:
        """Prepare application text for vectorization."""
        parts = []

        if app.get("name"):
            parts.append(app["name"])
        if app.get("developer"):
            parts.append(app["developer"])
        if app.get("category"):
            parts.append(app["category"])
        if app.get("description"):
            parts.append(app["description"])

        return " ".join(parts)

    def _prepare_cask_text(self, cask: dict[str, Any]) -> str:
        """Prepare cask text for vectorization."""
        parts = []

        if cask.get("name"):
            parts.append(cask["name"].replace("-", " "))
        if cask.get("desc"):
            parts.append(cask["desc"])
        if cask.get("homepage"):
            # Extract domain name from URL
            import re

            domain_match = re.search(r"https?://(?:www\.)?([^/]+)", cask["homepage"])
            if domain_match:
                parts.append(domain_match.group(1))

        return " ".join(parts)


class ModelTrainer:
    """Utility class for training ML models with labeled data."""

    def __init__(self):
        """Initialize model trainer."""
        self.confidence_model = MatchingConfidenceModel()

    def generate_synthetic_training_data(
        self, apps: list[dict[str, Any]], casks: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Generate synthetic training data for bootstrapping."""
        training_data = []

        # Generate positive examples (known good matches)
        positive_pairs = self._generate_positive_pairs(apps, casks)
        for app, cask in positive_pairs:
            training_data.append({"app": app, "cask": cask, "match": 1})

        # Generate negative examples
        negative_pairs = self._generate_negative_pairs(apps, casks, len(positive_pairs))
        for app, cask in negative_pairs:
            training_data.append({"app": app, "cask": cask, "match": 0})

        logger.info(f"Generated {len(training_data)} synthetic training examples")
        return training_data

    def _generate_positive_pairs(
        self, apps: list[dict[str, Any]], casks: list[dict[str, Any]]
    ) -> list[tuple[dict[str, Any], dict[str, Any]]]:
        """Generate positive training pairs based on name similarity."""
        pairs = []

        for app in apps:
            app_name = app.get("name", "").lower()

            for cask in casks:
                cask_name = cask.get("name", "").lower().replace("-", " ")

                # Simple heuristics for positive matches
                if app_name in cask_name or cask_name in app_name or self._fuzzy_match(app_name, cask_name) > 0.8:
                    pairs.append((app, cask))
                    break  # One match per app

        return pairs[:50]  # Limit to avoid overfitting

    def _generate_negative_pairs(
        self, apps: list[dict[str, Any]], casks: list[dict[str, Any]], count: int
    ) -> list[tuple[dict[str, Any], dict[str, Any]]]:
        """Generate negative training pairs."""
        import random

        pairs = []
        attempts = 0
        max_attempts = count * 10

        while len(pairs) < count and attempts < max_attempts:
            app = random.choice(apps)
            cask = random.choice(casks)

            app_name = app.get("name", "").lower()
            cask_name = cask.get("name", "").lower().replace("-", " ")

            # Ensure it's actually a negative example
            if self._fuzzy_match(app_name, cask_name) < 0.3:
                pairs.append((app, cask))

            attempts += 1

        return pairs

    def _fuzzy_match(self, s1: str, s2: str) -> float:
        """Simple fuzzy string matching."""
        if not s1 or not s2:
            return 0.0

        # Simple token-based matching
        tokens1 = set(s1.split())
        tokens2 = set(s2.split())

        if not tokens1 or not tokens2:
            return 0.0

        intersection = len(tokens1.intersection(tokens2))
        union = len(tokens1.union(tokens2))

        return intersection / union if union > 0 else 0.0
