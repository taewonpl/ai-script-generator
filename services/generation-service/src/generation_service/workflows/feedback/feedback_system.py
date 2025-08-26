"""
Feedback Loop System - Learns from user preferences and improves quality
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any

# Import Core Module components
try:
    from ai_script_core import (
        get_service_logger,
        utc_now,
    )

    CORE_AVAILABLE = True
    logger = get_service_logger("generation-service.feedback_system")
except (ImportError, RuntimeError):
    CORE_AVAILABLE = False
    import logging

    logger = logging.getLogger(__name__)

    # Fallback utility functions
    def utc_now():
        """Fallback UTC timestamp"""
        from datetime import datetime, timezone

        return datetime.now(timezone.utc)

    def generate_uuid():
        """Fallback UUID generation"""
        import uuid

        return str(uuid.uuid4())

    def generate_id():
        """Fallback ID generation"""
        import uuid

        return str(uuid.uuid4())[:8]

    # Fallback base classes
    class BaseDTO:
        """Fallback base DTO class"""

        pass

    class SuccessResponseDTO:
        """Fallback success response DTO"""

        pass

    class ErrorResponseDTO:
        """Fallback error response DTO"""

        pass


from generation_service.workflows.quality import QualityDimension


class FeedbackType(str, Enum):
    """Types of user feedback"""

    EXPLICIT_RATING = "explicit_rating"
    IMPLICIT_BEHAVIOR = "implicit_behavior"
    PREFERENCE_UPDATE = "preference_update"
    QUALITY_CORRECTION = "quality_correction"
    AGENT_FEEDBACK = "agent_feedback"


class FeedbackSentiment(str, Enum):
    """Sentiment of feedback"""

    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"
    MIXED = "mixed"


@dataclass
class UserFeedback:
    """Individual piece of user feedback"""

    feedback_id: str
    user_id: str | None
    generation_id: str
    feedback_type: FeedbackType
    sentiment: FeedbackSentiment
    content: dict[str, Any]  # Feedback content specific to type
    quality_scores: dict[str, float] | None  # User-provided quality scores
    timestamp: datetime
    session_id: str | None = None
    context: dict[str, Any] | None = None


@dataclass
class UserPreferenceProfile:
    """Learned user preference profile"""

    user_id: str
    quality_preferences: dict[QualityDimension, float]  # Importance weights
    agent_preferences: dict[str, float]  # Agent effectiveness for this user
    style_preferences: dict[str, Any]  # Style and content preferences
    feedback_history: list[str]  # Feedback IDs
    last_updated: datetime
    confidence_score: float  # How confident we are in these preferences
    total_feedback_count: int


class FeedbackLearningEngine:
    """
    Learning engine that processes feedback to improve future generations

    Features:
    - User preference learning from explicit and implicit feedback
    - Quality assessment calibration
    - Agent effectiveness learning
    - Content personalization
    - Continuous improvement loops
    """

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self.config = config or {}

        # Storage for feedback and preferences
        self.feedback_storage: dict[str, UserFeedback] = {}
        self.user_profiles: dict[str, UserPreferenceProfile] = {}

        # Learning parameters
        self.learning_rate = self.config.get("learning_rate", 0.1)
        self.preference_decay = self.config.get(
            "preference_decay", 0.95
        )  # How much to decay old preferences
        self.minimum_feedback_count = self.config.get("minimum_feedback_count", 5)

        # Feedback aggregation windows
        self.short_term_window = timedelta(days=7)
        self.medium_term_window = timedelta(days=30)
        self.long_term_window = timedelta(days=90)

        if CORE_AVAILABLE:
            logger.info(
                "FeedbackLearningEngine initialized",
                extra={
                    "learning_rate": self.learning_rate,
                    "minimum_feedback": self.minimum_feedback_count,
                },
            )

    async def record_feedback(self, feedback: UserFeedback) -> None:
        """Record user feedback and trigger learning"""

        # Store feedback
        self.feedback_storage[feedback.feedback_id] = feedback

        # Update user profile if user_id available
        if feedback.user_id:
            await self._update_user_profile(feedback)

        # Log feedback for monitoring
        if CORE_AVAILABLE:
            logger.info(
                "User feedback recorded",
                extra={
                    "feedback_id": feedback.feedback_id,
                    "feedback_type": feedback.feedback_type,
                    "sentiment": feedback.sentiment,
                    "user_id": feedback.user_id,
                    "generation_id": feedback.generation_id,
                },
            )

    async def process_generation_feedback(
        self,
        generation_id: str,
        user_rating: float,
        quality_feedback: dict[str, float] | None = None,
        user_id: str | None = None,
        comments: str | None = None,
    ) -> None:
        """Process feedback for a completed generation"""

        feedback = UserFeedback(
            feedback_id=f"gen_{generation_id}_{(utc_now() if CORE_AVAILABLE else datetime.now()).timestamp()}",
            user_id=user_id,
            generation_id=generation_id,
            feedback_type=FeedbackType.EXPLICIT_RATING,
            sentiment=self._determine_sentiment(user_rating),
            content={
                "overall_rating": user_rating,
                "quality_feedback": quality_feedback or {},
                "comments": comments,
            },
            quality_scores=quality_feedback,
            timestamp=utc_now() if CORE_AVAILABLE else datetime.now(),
        )

        await self.record_feedback(feedback)

    async def process_implicit_feedback(
        self,
        generation_id: str,
        user_actions: dict[str, Any],
        user_id: str | None = None,
        session_duration: float | None = None,
    ) -> None:
        """Process implicit feedback from user behavior"""

        # Analyze user actions to infer satisfaction
        satisfaction_score = self._calculate_satisfaction_from_actions(
            user_actions, session_duration
        )

        feedback = UserFeedback(
            feedback_id=f"implicit_{generation_id}_{(utc_now() if CORE_AVAILABLE else datetime.now()).timestamp()}",
            user_id=user_id,
            generation_id=generation_id,
            feedback_type=FeedbackType.IMPLICIT_BEHAVIOR,
            sentiment=self._determine_sentiment(satisfaction_score),
            content={
                "user_actions": user_actions,
                "session_duration": session_duration,
                "inferred_satisfaction": satisfaction_score,
            },
            quality_scores=None,
            timestamp=utc_now() if CORE_AVAILABLE else datetime.now(),
        )

        await self.record_feedback(feedback)

    async def get_user_preferences(self, user_id: str) -> UserPreferenceProfile | None:
        """Get learned preferences for a user"""

        if user_id not in self.user_profiles:
            return None

        profile = self.user_profiles[user_id]

        # Check if profile needs updating
        days_since_update = (
            (utc_now() - profile.last_updated).days if CORE_AVAILABLE else 0
        )

        if days_since_update > 30:  # Refresh if older than 30 days
            await self._refresh_user_profile(user_id)

        return self.user_profiles.get(user_id)

    async def personalize_generation_config(
        self, base_config: dict[str, Any], user_id: str | None = None
    ) -> dict[str, Any]:
        """Personalize generation configuration based on user preferences"""

        if not user_id:
            return base_config

        profile = await self.get_user_preferences(user_id)
        if not profile or profile.confidence_score < 0.3:
            return base_config

        personalized_config = base_config.copy()

        # Adjust quality dimension weights
        if "quality_preferences" in personalized_config:
            for dimension, weight in profile.quality_preferences.items():
                if dimension.value in personalized_config["quality_preferences"]:
                    # Blend user preference with base config
                    base_weight = personalized_config["quality_preferences"][
                        dimension.value
                    ]
                    personalized_weight = (base_weight * 0.7) + (weight * 0.3)
                    personalized_config["quality_preferences"][
                        dimension.value
                    ] = personalized_weight

        # Adjust agent configurations
        if "agent_configs" in personalized_config:
            for agent_name, effectiveness in profile.agent_preferences.items():
                if agent_name in personalized_config["agent_configs"]:
                    # Increase intensity for effective agents, decrease for ineffective ones
                    if effectiveness > 0.7:
                        personalized_config["agent_configs"][agent_name][
                            "intensity"
                        ] = (
                            personalized_config["agent_configs"][agent_name].get(
                                "intensity", 0.7
                            )
                            * 1.1
                        )
                    elif effectiveness < 0.4:
                        personalized_config["agent_configs"][agent_name][
                            "intensity"
                        ] = (
                            personalized_config["agent_configs"][agent_name].get(
                                "intensity", 0.7
                            )
                            * 0.8
                        )

        # Apply style preferences
        if profile.style_preferences:
            personalized_config["style_preferences"] = {
                **personalized_config.get("style_preferences", {}),
                **profile.style_preferences,
            }

        return personalized_config

    async def calibrate_quality_assessment(
        self, assessor_scores: dict[str, float], user_scores: dict[str, float]
    ) -> dict[str, float]:
        """Calibrate quality assessment based on user feedback"""

        calibrated_scores = assessor_scores.copy()

        # Learn calibration factors from user vs. assessor score differences
        calibration_factors = self._calculate_calibration_factors(
            assessor_scores, user_scores
        )

        # Apply calibration
        for dimension, factor in calibration_factors.items():
            if dimension in calibrated_scores:
                calibrated_scores[dimension] = min(
                    max(calibrated_scores[dimension] * factor, 0.0), 1.0
                )

        return calibrated_scores

    async def get_improvement_suggestions(
        self, user_id: str | None = None
    ) -> list[str]:
        """Get improvement suggestions based on feedback patterns"""

        suggestions = []

        if user_id:
            profile = await self.get_user_preferences(user_id)
            if profile and profile.confidence_score > 0.5:
                # User-specific suggestions
                low_satisfaction_areas = [
                    dim
                    for dim, weight in profile.quality_preferences.items()
                    if weight < 0.4
                ]

                for dimension in low_satisfaction_areas:
                    suggestions.append(
                        f"Focus on improving {dimension.value.replace('_', ' ')}"
                    )

        # General suggestions from recent feedback
        recent_feedback = self._get_recent_feedback(self.short_term_window)
        if recent_feedback:
            common_issues = self._analyze_common_feedback_patterns(recent_feedback)
            suggestions.extend(common_issues)

        return suggestions[:5]  # Limit to top 5 suggestions

    async def _update_user_profile(self, feedback: UserFeedback) -> None:
        """Update user preference profile with new feedback"""

        user_id = feedback.user_id
        if not user_id:
            return

        # Get or create profile
        if user_id not in self.user_profiles:
            self.user_profiles[user_id] = UserPreferenceProfile(
                user_id=user_id,
                quality_preferences=dict.fromkeys(QualityDimension, 0.5),
                agent_preferences={},
                style_preferences={},
                feedback_history=[],
                last_updated=utc_now() if CORE_AVAILABLE else datetime.now(),
                confidence_score=0.0,
                total_feedback_count=0,
            )

        profile = self.user_profiles[user_id]

        # Update feedback history
        profile.feedback_history.append(feedback.feedback_id)
        profile.total_feedback_count += 1
        profile.last_updated = utc_now() if CORE_AVAILABLE else datetime.now()

        # Update quality preferences if quality scores provided
        if feedback.quality_scores:
            for dimension_name, score in feedback.quality_scores.items():
                try:
                    dimension = QualityDimension(dimension_name)
                    current_pref = profile.quality_preferences.get(dimension, 0.5)

                    # Update preference using learning rate
                    normalized_score = score  # Assume score is already 0-1
                    updated_pref = current_pref + (
                        self.learning_rate * (normalized_score - current_pref)
                    )
                    profile.quality_preferences[dimension] = max(
                        0.0, min(1.0, updated_pref)
                    )

                except ValueError:
                    logger.warning(f"Unknown quality dimension: {dimension_name}")

        # Update confidence score based on feedback count
        profile.confidence_score = min(
            profile.total_feedback_count
            / 10.0,  # Full confidence at 10+ feedback items
            1.0,
        )

        # Apply preference decay to older preferences
        if profile.total_feedback_count > 5:
            for dimension in profile.quality_preferences:
                profile.quality_preferences[dimension] *= self.preference_decay

    async def _refresh_user_profile(self, user_id: str) -> None:
        """Refresh user profile based on recent feedback"""

        if user_id not in self.user_profiles:
            return

        profile = self.user_profiles[user_id]

        # Get recent feedback for this user
        recent_feedback = [
            feedback
            for feedback in self.feedback_storage.values()
            if (
                feedback.user_id == user_id
                and (utc_now() - feedback.timestamp).days <= 90
            )
        ]

        if not recent_feedback:
            return

        # Recalculate preferences from recent feedback
        quality_sum = dict.fromkeys(QualityDimension, 0.0)
        quality_count = dict.fromkeys(QualityDimension, 0)

        for feedback in recent_feedback:
            if feedback.quality_scores:
                for dimension_name, score in feedback.quality_scores.items():
                    try:
                        dimension = QualityDimension(dimension_name)
                        quality_sum[dimension] += score
                        quality_count[dimension] += 1
                    except ValueError:
                        continue

        # Update preferences with averages
        for dimension in QualityDimension:
            if quality_count[dimension] > 0:
                profile.quality_preferences[dimension] = (
                    quality_sum[dimension] / quality_count[dimension]
                )

        # Update confidence
        profile.confidence_score = min(len(recent_feedback) / 10.0, 1.0)
        profile.last_updated = utc_now() if CORE_AVAILABLE else datetime.now()

    def _determine_sentiment(self, score: float) -> FeedbackSentiment:
        """Determine sentiment from numeric score"""

        if score >= 0.7:
            return FeedbackSentiment.POSITIVE
        elif score >= 0.4:
            return FeedbackSentiment.NEUTRAL
        else:
            return FeedbackSentiment.NEGATIVE

    def _calculate_satisfaction_from_actions(
        self, user_actions: dict[str, Any], session_duration: float | None = None
    ) -> float:
        """Calculate satisfaction score from user actions"""

        satisfaction = 0.5  # Neutral baseline

        # Positive indicators
        if user_actions.get("downloaded_script", False):
            satisfaction += 0.3
        if user_actions.get("shared_script", False):
            satisfaction += 0.2
        if user_actions.get("regenerated_count", 0) == 0:
            satisfaction += 0.1
        if session_duration and session_duration > 300:  # 5+ minutes
            satisfaction += 0.1

        # Negative indicators
        if user_actions.get("regenerated_count", 0) > 2:
            satisfaction -= 0.2
        if user_actions.get("abandoned_early", False):
            satisfaction -= 0.3
        if session_duration and session_duration < 60:  # Less than 1 minute
            satisfaction -= 0.2

        return max(0.0, min(1.0, satisfaction))

    def _calculate_calibration_factors(
        self, assessor_scores: dict[str, float], user_scores: dict[str, float]
    ) -> dict[str, float]:
        """Calculate calibration factors for quality assessment"""

        calibration_factors = {}

        for dimension in assessor_scores:
            if dimension in user_scores:
                assessor_score = assessor_scores[dimension]
                user_score = user_scores[dimension]

                if assessor_score > 0:
                    # Factor to bring assessor score closer to user score
                    factor = user_score / assessor_score
                    # Limit extreme adjustments
                    calibration_factors[dimension] = max(0.5, min(2.0, factor))
                else:
                    calibration_factors[dimension] = 1.0

        return calibration_factors

    def _get_recent_feedback(self, window: timedelta) -> list[UserFeedback]:
        """Get feedback within specified time window"""

        cutoff_time = (utc_now() if CORE_AVAILABLE else datetime.now()) - window

        return [
            feedback
            for feedback in self.feedback_storage.values()
            if feedback.timestamp >= cutoff_time
        ]

    def _analyze_common_feedback_patterns(
        self, feedback_list: list[UserFeedback]
    ) -> list[str]:
        """Analyze common patterns in feedback to generate suggestions"""

        suggestions = []

        if not feedback_list:
            return suggestions

        # Count negative feedback by type
        negative_feedback = [
            f for f in feedback_list if f.sentiment == FeedbackSentiment.NEGATIVE
        ]

        if len(negative_feedback) > len(feedback_list) * 0.3:  # >30% negative
            suggestions.append("Review overall generation quality standards")

        # Analyze quality dimension issues
        quality_issues = {}
        for feedback in feedback_list:
            if feedback.quality_scores:
                for dimension, score in feedback.quality_scores.items():
                    if score < 0.5:
                        quality_issues[dimension] = quality_issues.get(dimension, 0) + 1

        # Suggest improvements for most common issues
        for dimension, count in sorted(
            quality_issues.items(), key=lambda x: x[1], reverse=True
        )[:3]:
            suggestions.append(f"Improve {dimension.replace('_', ' ')} quality")

        return suggestions

    def get_feedback_statistics(self) -> dict[str, Any]:
        """Get statistics about feedback system performance"""

        total_feedback = len(self.feedback_storage)
        if total_feedback == 0:
            return {"total_feedback": 0}

        # Calculate statistics
        recent_feedback = self._get_recent_feedback(self.short_term_window)

        sentiment_counts = {}
        for sentiment in FeedbackSentiment:
            sentiment_counts[sentiment.value] = len(
                [f for f in recent_feedback if f.sentiment == sentiment]
            )

        return {
            "total_feedback": total_feedback,
            "recent_feedback": len(recent_feedback),
            "user_profiles": len(self.user_profiles),
            "sentiment_distribution": sentiment_counts,
            "average_confidence": (
                sum(profile.confidence_score for profile in self.user_profiles.values())
                / len(self.user_profiles)
                if self.user_profiles
                else 0.0
            ),
        }
