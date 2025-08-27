"""
Quality Assessment System - Multi-dimensional quality scoring and analysis
"""

import re
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Optional

# Import Core Module components
try:
    from ai_script_core import (
        get_service_logger,
        utc_now,
    )

    CORE_AVAILABLE = True
    logger = get_service_logger("generation-service.quality_assessor")
except (ImportError, RuntimeError):
    CORE_AVAILABLE = False
    import logging

    logger = logging.getLogger(__name__)  # type: ignore[assignment]

    # Fallback utility functions
    def utc_now():
        """Fallback UTC timestamp"""
        from datetime import datetime, timezone

        return datetime.now(timezone.utc)

    def generate_uuid() -> str:
        """Fallback UUID generation"""
        import uuid

        return str(uuid.uuid4())

    def generate_id() -> str:
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


class QualityDimension(str, Enum):
    """Quality assessment dimensions"""

    PLOT_STRUCTURE = "plot_structure"
    CHARACTER_DEVELOPMENT = "character_development"
    DIALOGUE_QUALITY = "dialogue_quality"
    VISUAL_STORYTELLING = "visual_storytelling"
    EMOTIONAL_IMPACT = "emotional_impact"
    PACING_AND_RHYTHM = "pacing_and_rhythm"
    ORIGINALITY = "originality"
    TECHNICAL_CRAFT = "technical_craft"


@dataclass
class QualityScore:
    """Individual quality score with context"""

    dimension: QualityDimension
    score: float  # 0.0 to 1.0
    confidence: float  # 0.0 to 1.0
    details: dict[str, Any]
    suggestions: list[str]
    evidence: list[str]


@dataclass
class QualityAssessment:
    """Complete quality assessment result"""

    overall_score: float
    dimension_scores: dict[QualityDimension, QualityScore]
    improvement_areas: list[
        tuple[QualityDimension, float]
    ]  # (dimension, potential_improvement)
    strengths: list[tuple[QualityDimension, str]]  # (dimension, strength_description)
    assessment_confidence: float
    content_analysis: dict[str, Any]
    recommendations: list[str]
    timestamp: datetime


class QualityAssessor:
    """
    Advanced quality assessment system for script content

    Features:
    - Multi-dimensional quality scoring
    - Detailed analysis with evidence and suggestions
    - Comparative assessment (before/after enhancement)
    - Learning from user feedback
    - Configurable quality standards
    """

    def __init__(self, config: Optional[dict[str, Any]] = None) -> None:
        self.config = config or {}

        # Quality dimension weights (customizable)
        self.dimension_weights = self.config.get(
            "dimension_weights",
            {
                QualityDimension.PLOT_STRUCTURE: 0.2,
                QualityDimension.CHARACTER_DEVELOPMENT: 0.18,
                QualityDimension.DIALOGUE_QUALITY: 0.15,
                QualityDimension.VISUAL_STORYTELLING: 0.12,
                QualityDimension.EMOTIONAL_IMPACT: 0.15,
                QualityDimension.PACING_AND_RHYTHM: 0.1,
                QualityDimension.ORIGINALITY: 0.05,
                QualityDimension.TECHNICAL_CRAFT: 0.05,
            },
        )

        # Assessment thresholds
        self.quality_thresholds = self.config.get(
            "quality_thresholds",
            {
                "excellent": 0.85,
                "good": 0.7,
                "acceptable": 0.5,
                "needs_improvement": 0.0,
            },
        )

        # Historical assessments for learning
        self.assessment_history = []

        if CORE_AVAILABLE:
            logger.info(
                "QualityAssessor initialized",
                extra={
                    "dimensions": list(self.dimension_weights.keys()),
                    "thresholds": self.quality_thresholds,
                },
            )

    async def assess_quality(
        self, content: str, generation_metadata: dict[str, Any] = None
    ) -> QualityAssessment:
        """
        Perform comprehensive quality assessment of script content
        """

        if not content or not content.strip():
            return self._create_empty_assessment()

        # Analyze content structure and characteristics
        content_analysis = self._analyze_content_structure(content)

        # Assess each quality dimension
        dimension_scores = {}
        for dimension in QualityDimension:
            score = await self._assess_dimension(
                dimension, content, content_analysis, generation_metadata
            )
            dimension_scores[dimension] = score

        # Calculate overall score
        overall_score = self._calculate_overall_score(dimension_scores)

        # Identify improvement areas and strengths
        improvement_areas = self._identify_improvement_areas(dimension_scores)
        strengths = self._identify_strengths(dimension_scores)

        # Generate recommendations
        recommendations = self._generate_recommendations(
            dimension_scores, improvement_areas
        )

        # Calculate assessment confidence
        assessment_confidence = self._calculate_assessment_confidence(
            dimension_scores, content_analysis
        )

        assessment = QualityAssessment(
            overall_score=overall_score,
            dimension_scores=dimension_scores,
            improvement_areas=improvement_areas,
            strengths=strengths,
            assessment_confidence=assessment_confidence,
            content_analysis=content_analysis,
            recommendations=recommendations,
            timestamp=utc_now() if CORE_AVAILABLE else datetime.now(),
        )

        # Store for learning
        self.assessment_history.append(assessment)

        return assessment

    async def compare_assessments(
        self,
        original_content: str,
        enhanced_content: str,
        generation_metadata: dict[str, Any] = None,
    ) -> dict[str, Any]:
        """
        Compare quality assessments between original and enhanced content
        """

        original_assessment = await self.assess_quality(
            original_content, generation_metadata
        )
        enhanced_assessment = await self.assess_quality(
            enhanced_content, generation_metadata
        )

        comparison = {
            "original_assessment": original_assessment,
            "enhanced_assessment": enhanced_assessment,
            "overall_improvement": enhanced_assessment.overall_score
            - original_assessment.overall_score,
            "dimension_improvements": {},
            "improvement_summary": [],
            "regression_warnings": [],
        }

        # Compare each dimension
        for dimension in QualityDimension:
            original_score = original_assessment.dimension_scores[dimension].score
            enhanced_score = enhanced_assessment.dimension_scores[dimension].score
            improvement = enhanced_score - original_score

            comparison["dimension_improvements"][dimension] = {
                "original_score": original_score,
                "enhanced_score": enhanced_score,
                "improvement": improvement,
                "relative_improvement": (
                    improvement / original_score if original_score > 0 else 0
                ),
            }

            # Track significant improvements and regressions
            if improvement > 0.1:
                comparison["improvement_summary"].append(
                    f"Significant improvement in {dimension.value}: +{improvement:.2f}"
                )
            elif improvement < -0.05:
                comparison["regression_warnings"].append(
                    f"Regression in {dimension.value}: {improvement:.2f}"
                )

        return comparison

    async def _assess_dimension(
        self,
        dimension: QualityDimension,
        content: str,
        content_analysis: dict[str, Any],
        metadata: dict[str, Any] = None,
    ) -> QualityScore:
        """Assess a specific quality dimension"""

        if dimension == QualityDimension.PLOT_STRUCTURE:
            return self._assess_plot_structure(content, content_analysis)
        elif dimension == QualityDimension.CHARACTER_DEVELOPMENT:
            return self._assess_character_development(content, content_analysis)
        elif dimension == QualityDimension.DIALOGUE_QUALITY:
            return self._assess_dialogue_quality(content, content_analysis)
        elif dimension == QualityDimension.VISUAL_STORYTELLING:
            return self._assess_visual_storytelling(content, content_analysis)
        elif dimension == QualityDimension.EMOTIONAL_IMPACT:
            return self._assess_emotional_impact(content, content_analysis)
        elif dimension == QualityDimension.PACING_AND_RHYTHM:
            return self._assess_pacing_rhythm(content, content_analysis)
        elif dimension == QualityDimension.ORIGINALITY:
            return self._assess_originality(content, content_analysis)
        elif dimension == QualityDimension.TECHNICAL_CRAFT:
            return self._assess_technical_craft(content, content_analysis)
        else:
            return QualityScore(dimension, 0.5, 0.5, {}, [], [])

    def _assess_plot_structure(
        self, content: str, analysis: dict[str, Any]
    ) -> QualityScore:
        """Assess plot structure quality"""

        factors = []
        suggestions = []
        evidence = []

        # Check for clear three-act structure
        has_setup = analysis.get("has_clear_beginning", False)
        has_development = analysis.get("scene_count", 0) > 2
        has_resolution = analysis.get("has_resolution", False)

        structure_score = sum([has_setup, has_development, has_resolution]) / 3.0
        factors.append(("structure_clarity", structure_score, 0.4))

        if not has_setup:
            suggestions.append("Add clearer story setup and character introduction")
        if not has_resolution:
            suggestions.append("Strengthen story resolution and conclusion")

        # Check for conflict and tension
        conflict_score = min(analysis.get("conflict_scenes", 0) / 3.0, 1.0)
        factors.append(("conflict_presence", conflict_score, 0.3))

        if conflict_score < 0.5:
            suggestions.append("Increase dramatic conflict and tension")

        # Check for plot coherence
        coherence_indicators = ["because", "therefore", "as a result", "leads to"]
        coherence_count = sum(
            content.lower().count(indicator) for indicator in coherence_indicators
        )
        coherence_score = min(coherence_count / 5.0, 1.0)
        factors.append(("plot_coherence", coherence_score, 0.3))

        if coherence_score < 0.6:
            suggestions.append("Improve causal relationships between plot points")

        # Calculate overall score
        score = sum(score * weight for _, score, weight in factors)
        confidence = 0.8 if analysis.get("word_count", 0) > 500 else 0.6

        return QualityScore(
            dimension=QualityDimension.PLOT_STRUCTURE,
            score=score,
            confidence=confidence,
            details={factor: score for factor, score, _ in factors},
            suggestions=suggestions,
            evidence=evidence,
        )

    def _assess_character_development(
        self, content: str, analysis: dict[str, Any]
    ) -> QualityScore:
        """Assess character development quality"""

        factors = []
        suggestions = []
        evidence = []

        # Character count and depth
        character_count = analysis.get("character_count", 0)
        character_score = min(character_count / 3.0, 1.0)
        factors.append(("character_presence", character_score, 0.3))

        if character_count < 2:
            suggestions.append("Develop more distinct characters")

        # Character depth indicators
        depth_indicators = ["feels", "thinks", "believes", "wants", "needs", "fears"]
        depth_count = sum(
            content.lower().count(indicator) for indicator in depth_indicators
        )
        depth_score = min(depth_count / 8.0, 1.0)
        factors.append(("character_depth", depth_score, 0.4))

        if depth_score < 0.5:
            suggestions.append("Add more character emotions and motivations")

        # Character growth
        growth_indicators = ["learns", "changes", "realizes", "overcomes", "grows"]
        growth_count = sum(
            content.lower().count(indicator) for indicator in growth_indicators
        )
        growth_score = min(growth_count / 3.0, 1.0)
        factors.append(("character_growth", growth_score, 0.3))

        if growth_score < 0.4:
            suggestions.append("Show character growth and development")

        score = sum(score * weight for _, score, weight in factors)
        confidence = 0.7

        return QualityScore(
            dimension=QualityDimension.CHARACTER_DEVELOPMENT,
            score=score,
            confidence=confidence,
            details={factor: score for factor, score, _ in factors},
            suggestions=suggestions,
            evidence=evidence,
        )

    def _assess_dialogue_quality(
        self, content: str, analysis: dict[str, Any]
    ) -> QualityScore:
        """Assess dialogue quality"""

        factors = []
        suggestions = []
        evidence = []

        # Dialogue presence
        dialogue_ratio = analysis.get("dialogue_ratio", 0.0)
        presence_score = min(dialogue_ratio * 2, 1.0)
        factors.append(("dialogue_presence", presence_score, 0.2))

        if dialogue_ratio < 0.3:
            suggestions.append("Increase dialogue to improve character interaction")

        # Natural speech patterns
        natural_indicators = ["don't", "can't", "won't", "um", "well", "you know"]
        natural_count = sum(
            content.lower().count(indicator) for indicator in natural_indicators
        )
        natural_score = min(natural_count / 10.0, 1.0)
        factors.append(("naturalness", natural_score, 0.3))

        if natural_score < 0.4:
            suggestions.append("Make dialogue more natural and conversational")

        # Character voice distinction
        # Simplified - would need more sophisticated analysis
        voice_score = 0.6  # Placeholder
        factors.append(("character_voice", voice_score, 0.3))

        # Dialogue purpose (not just exposition)
        exposition_indicators = ["as you know", "remember when", "let me explain"]
        exposition_count = sum(
            content.lower().count(indicator) for indicator in exposition_indicators
        )
        purpose_score = max(0.0, 1.0 - exposition_count / 5.0)
        factors.append(("dialogue_purpose", purpose_score, 0.2))

        if exposition_count > 2:
            suggestions.append("Reduce exposition in dialogue, show don't tell")

        score = sum(score * weight for _, score, weight in factors)
        confidence = 0.75

        return QualityScore(
            dimension=QualityDimension.DIALOGUE_QUALITY,
            score=score,
            confidence=confidence,
            details={factor: score for factor, score, _ in factors},
            suggestions=suggestions,
            evidence=evidence,
        )

    def _assess_visual_storytelling(
        self, content: str, analysis: dict[str, Any]
    ) -> QualityScore:
        """Assess visual storytelling quality"""

        factors = []
        suggestions = []
        evidence = []

        # Visual description density
        visual_words = [
            "bright",
            "dark",
            "colorful",
            "massive",
            "tiny",
            "beautiful",
            "ugly",
        ]
        visual_count = sum(content.lower().count(word) for word in visual_words)
        visual_score = min(visual_count / 15.0, 1.0)
        factors.append(("visual_density", visual_score, 0.4))

        if visual_score < 0.5:
            suggestions.append("Add more visual descriptions to enhance imagery")

        # Scene setting quality
        scene_headers = analysis.get("scene_count", 0)
        setting_score = min(scene_headers / 3.0, 1.0)
        factors.append(("scene_setting", setting_score, 0.3))

        # Cinematic potential
        cinematic_words = ["camera", "shot", "close-up", "wide", "angle"]
        cinematic_count = sum(content.lower().count(word) for word in cinematic_words)
        cinematic_score = min(cinematic_count / 3.0, 1.0)
        factors.append(("cinematic_potential", cinematic_score, 0.3))

        if cinematic_score < 0.3:
            suggestions.append("Consider cinematic visual elements for adaptation")

        score = sum(score * weight for _, score, weight in factors)
        confidence = 0.7

        return QualityScore(
            dimension=QualityDimension.VISUAL_STORYTELLING,
            score=score,
            confidence=confidence,
            details={factor: score for factor, score, _ in factors},
            suggestions=suggestions,
            evidence=evidence,
        )

    def _assess_emotional_impact(
        self, content: str, analysis: dict[str, Any]
    ) -> QualityScore:
        """Assess emotional impact quality"""

        factors = []
        suggestions = []
        evidence = []

        # Emotional vocabulary
        emotion_words = [
            "love",
            "hate",
            "fear",
            "joy",
            "anger",
            "sadness",
            "hope",
            "despair",
        ]
        emotion_count = sum(content.lower().count(word) for word in emotion_words)
        emotion_score = min(emotion_count / 10.0, 1.0)
        factors.append(("emotional_vocabulary", emotion_score, 0.4))

        if emotion_score < 0.4:
            suggestions.append("Increase emotional vocabulary and expression")

        # Emotional range
        unique_emotions = len(
            [word for word in emotion_words if word in content.lower()]
        )
        range_score = unique_emotions / len(emotion_words)
        factors.append(("emotional_range", range_score, 0.3))

        if range_score < 0.4:
            suggestions.append("Expand emotional range of characters")

        # Stakes and consequences
        stakes_indicators = ["loses", "wins", "fails", "succeeds", "dies", "lives"]
        stakes_count = sum(
            content.lower().count(indicator) for indicator in stakes_indicators
        )
        stakes_score = min(stakes_count / 5.0, 1.0)
        factors.append(("emotional_stakes", stakes_score, 0.3))

        if stakes_score < 0.3:
            suggestions.append("Raise emotional stakes and consequences")

        score = sum(score * weight for _, score, weight in factors)
        confidence = 0.65

        return QualityScore(
            dimension=QualityDimension.EMOTIONAL_IMPACT,
            score=score,
            confidence=confidence,
            details={factor: score for factor, score, _ in factors},
            suggestions=suggestions,
            evidence=evidence,
        )

    def _assess_pacing_rhythm(
        self, content: str, analysis: dict[str, Any]
    ) -> QualityScore:
        """Assess pacing and rhythm quality"""

        factors = []
        suggestions = []
        evidence = []

        # Sentence length variety
        sentences = [line.strip() for line in content.split("\n") if line.strip()]
        if sentences:
            lengths = [len(sentence.split()) for sentence in sentences]
            avg_length = sum(lengths) / len(lengths)
            length_variety = len(set(lengths)) / len(lengths)

            variety_score = min(length_variety * 2, 1.0)
            factors.append(("rhythm_variety", variety_score, 0.4))

            if variety_score < 0.5:
                suggestions.append("Vary sentence length for better rhythm")

        # Pacing indicators
        fast_indicators = ["quickly", "suddenly", "immediately", "rushes"]
        slow_indicators = ["slowly", "gradually", "pauses", "thoughtfully"]

        fast_count = sum(
            content.lower().count(indicator) for indicator in fast_indicators
        )
        slow_count = sum(
            content.lower().count(indicator) for indicator in slow_indicators
        )

        pacing_balance = (
            1.0
            if fast_count + slow_count == 0
            else min(fast_count, slow_count) / (fast_count + slow_count)
        )
        factors.append(("pacing_balance", pacing_balance, 0.3))

        # Action density
        action_words = ["runs", "jumps", "fights", "moves", "acts"]
        action_count = sum(content.lower().count(word) for word in action_words)
        action_score = min(action_count / 8.0, 1.0)
        factors.append(("action_density", action_score, 0.3))

        if action_score < 0.3:
            suggestions.append("Add more dynamic action for pacing")

        score = sum(score * weight for _, score, weight in factors) if factors else 0.5
        confidence = 0.6

        return QualityScore(
            dimension=QualityDimension.PACING_AND_RHYTHM,
            score=score,
            confidence=confidence,
            details={factor: score for factor, score, _ in factors},
            suggestions=suggestions,
            evidence=evidence,
        )

    def _assess_originality(
        self, content: str, analysis: dict[str, Any]
    ) -> QualityScore:
        """Assess originality and creativity"""

        factors = []
        suggestions = []
        evidence = []

        # Cliché detection (simplified)
        cliches = ["once upon a time", "happily ever after", "dark and stormy night"]
        cliche_count = sum(content.lower().count(cliche) for cliche in cliches)
        originality_score = max(0.0, 1.0 - cliche_count / 3.0)
        factors.append(("cliche_avoidance", originality_score, 0.5))

        if cliche_count > 1:
            suggestions.append("Avoid common clichés and overused phrases")

        # Unique word usage
        words = content.lower().split()
        unique_ratio = len(set(words)) / len(words) if words else 0
        uniqueness_score = min(unique_ratio * 2, 1.0)
        factors.append(("vocabulary_uniqueness", uniqueness_score, 0.3))

        # Creative elements
        creative_indicators = [
            "unusual",
            "unexpected",
            "creative",
            "original",
            "unique",
        ]
        creative_count = sum(
            content.lower().count(indicator) for indicator in creative_indicators
        )
        creative_score = min(creative_count / 3.0, 1.0)
        factors.append(("creative_elements", creative_score, 0.2))

        if creative_score < 0.3:
            suggestions.append("Add more creative and unexpected elements")

        score = sum(score * weight for _, score, weight in factors)
        confidence = 0.5  # Lower confidence for originality assessment

        return QualityScore(
            dimension=QualityDimension.ORIGINALITY,
            score=score,
            confidence=confidence,
            details={factor: score for factor, score, _ in factors},
            suggestions=suggestions,
            evidence=evidence,
        )

    def _assess_technical_craft(
        self, content: str, analysis: dict[str, Any]
    ) -> QualityScore:
        """Assess technical writing craft"""

        factors = []
        suggestions = []
        evidence = []

        # Script formatting
        format_indicators = ["EXT.", "INT.", "FADE IN", "FADE OUT"]
        format_count = sum(content.count(indicator) for indicator in format_indicators)
        format_score = min(format_count / 3.0, 1.0)
        factors.append(("script_formatting", format_score, 0.4))

        if format_score < 0.5:
            suggestions.append("Improve script formatting and structure")

        # Grammar and style (simplified)
        # In practice, this would use more sophisticated analysis
        sentence_count = len([line for line in content.split("\n") if line.strip()])
        avg_sentence_length = (
            len(content.split()) / sentence_count if sentence_count > 0 else 0
        )

        # Ideal range for script writing
        length_score = 1.0 if 8 <= avg_sentence_length <= 20 else 0.7
        factors.append(("sentence_structure", length_score, 0.3))

        # Consistency
        consistency_score = 0.8  # Placeholder - would need more analysis
        factors.append(("consistency", consistency_score, 0.3))

        score = sum(score * weight for _, score, weight in factors)
        confidence = 0.7

        return QualityScore(
            dimension=QualityDimension.TECHNICAL_CRAFT,
            score=score,
            confidence=confidence,
            details={factor: score for factor, score, _ in factors},
            suggestions=suggestions,
            evidence=evidence,
        )

    def _analyze_content_structure(self, content: str) -> dict[str, Any]:
        """Analyze basic content structure"""

        lines = content.split("\n")
        words = content.split()

        # Count different elements
        scene_headers = len(
            [line for line in lines if line.strip().startswith(("EXT.", "INT."))]
        )
        dialogue_lines = len([line for line in lines if '"' in line])
        character_names = len(
            set(re.findall(r"^[A-Z][A-Z\s]{1,20}$", content, re.MULTILINE))
        )

        return {
            "total_lines": len([line for line in lines if line.strip()]),
            "word_count": len(words),
            "scene_count": scene_headers,
            "dialogue_lines": dialogue_lines,
            "dialogue_ratio": dialogue_lines / len(lines) if lines else 0,
            "character_count": character_names,
            "has_clear_beginning": any(
                indicator in content.upper()
                for indicator in ["FADE IN", "EXT.", "INT."]
            ),
            "has_resolution": any(
                indicator in content.upper()
                for indicator in ["FADE OUT", "END", "CONCLUSION"]
            ),
            "average_words_per_line": len(words) / len(lines) if lines else 0,
        }

    def _calculate_overall_score(
        self, dimension_scores: dict[QualityDimension, QualityScore]
    ) -> float:
        """Calculate weighted overall quality score"""

        total_score = 0.0
        total_weight = 0.0

        for dimension, score_obj in dimension_scores.items():
            weight = self.dimension_weights.get(dimension, 0.1)
            # Weight by confidence
            effective_weight = weight * score_obj.confidence
            total_score += score_obj.score * effective_weight
            total_weight += effective_weight

        return total_score / total_weight if total_weight > 0 else 0.0

    def _identify_improvement_areas(
        self, dimension_scores: dict[QualityDimension, QualityScore]
    ) -> list[tuple[QualityDimension, float]]:
        """Identify dimensions with most improvement potential"""

        improvement_areas = []
        for dimension, score_obj in dimension_scores.items():
            # Calculate improvement potential (lower score = higher potential)
            potential = (1.0 - score_obj.score) * score_obj.confidence
            improvement_areas.append((dimension, potential))

        # Sort by potential improvement (highest first)
        improvement_areas.sort(key=lambda x: x[1], reverse=True)

        return improvement_areas[:3]  # Top 3 improvement areas

    def _identify_strengths(
        self, dimension_scores: dict[QualityDimension, QualityScore]
    ) -> list[tuple[QualityDimension, str]]:
        """Identify dimensional strengths"""

        strengths = []
        for dimension, score_obj in dimension_scores.items():
            if score_obj.score > 0.7 and score_obj.confidence > 0.6:
                strength_desc = f"Strong {dimension.value.replace('_', ' ')} (score: {score_obj.score:.2f})"
                strengths.append((dimension, strength_desc))

        return strengths

    def _generate_recommendations(
        self,
        dimension_scores: dict[QualityDimension, QualityScore],
        improvement_areas: list[tuple[QualityDimension, float]],
    ) -> list[str]:
        """Generate actionable recommendations"""

        recommendations = []

        # Add specific suggestions from low-scoring dimensions
        for dimension, potential in improvement_areas:
            score_obj = dimension_scores[dimension]
            if score_obj.suggestions:
                recommendations.extend(
                    score_obj.suggestions[:2]
                )  # Top 2 suggestions per dimension

        # Add general recommendations based on overall patterns
        avg_score = sum(
            score_obj.score for score_obj in dimension_scores.values()
        ) / len(dimension_scores)

        if avg_score < 0.5:
            recommendations.append("Consider fundamental story structure improvements")
        elif avg_score < 0.7:
            recommendations.append("Focus on character and dialogue enhancement")
        else:
            recommendations.append("Polish details and add creative flourishes")

        return recommendations[:5]  # Limit to 5 recommendations

    def _calculate_assessment_confidence(
        self,
        dimension_scores: dict[QualityDimension, QualityScore],
        content_analysis: dict[str, Any],
    ) -> float:
        """Calculate overall assessment confidence"""

        # Average dimension confidence
        avg_dimension_confidence = sum(
            score.confidence for score in dimension_scores.values()
        ) / len(dimension_scores)

        # Content length factor (more content = higher confidence)
        word_count = content_analysis.get("word_count", 0)
        length_factor = min(word_count / 1000, 1.0)

        # Structure clarity factor
        structure_factor = 0.8 if content_analysis.get("scene_count", 0) > 1 else 0.6

        # Combine factors
        confidence = (
            (avg_dimension_confidence * 0.6)
            + (length_factor * 0.3)
            + (structure_factor * 0.1)
        )

        return min(confidence, 1.0)

    def _create_empty_assessment(self) -> QualityAssessment:
        """Create empty assessment for invalid content"""

        empty_scores = {}
        for dimension in QualityDimension:
            empty_scores[dimension] = QualityScore(
                dimension=dimension,
                score=0.0,
                confidence=0.0,
                details={},
                suggestions=["No content to assess"],
                evidence=[],
            )

        return QualityAssessment(
            overall_score=0.0,
            dimension_scores=empty_scores,
            improvement_areas=[],
            strengths=[],
            assessment_confidence=0.0,
            content_analysis={},
            recommendations=["Provide content for quality assessment"],
            timestamp=utc_now() if CORE_AVAILABLE else datetime.now(),
        )

    def get_quality_level(self, score: float) -> str:
        """Get quality level description for a score"""

        for level, threshold in sorted(
            self.quality_thresholds.items(), key=lambda x: x[1], reverse=True
        ):
            if score >= threshold:
                return level
        return "needs_improvement"

    def get_assessor_stats(self) -> dict[str, Any]:
        """Get assessor statistics"""

        if not self.assessment_history:
            return {"total_assessments": 0}

        recent_assessments = self.assessment_history[-10:]  # Last 10
        avg_score = sum(a.overall_score for a in recent_assessments) / len(
            recent_assessments
        )
        avg_confidence = sum(a.assessment_confidence for a in recent_assessments) / len(
            recent_assessments
        )

        return {
            "total_assessments": len(self.assessment_history),
            "recent_average_score": avg_score,
            "recent_average_confidence": avg_confidence,
            "dimension_weights": self.dimension_weights,
            "quality_thresholds": self.quality_thresholds,
        }
