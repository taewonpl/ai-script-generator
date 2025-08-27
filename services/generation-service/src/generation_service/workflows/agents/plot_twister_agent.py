"""
Plot Twister Agent - Adds unexpected plot twists and narrative surprises
"""

import re
from typing import Any, Optional

# Import Core Module components
try:
    from ai_script_core import (
        get_service_logger,
        utc_now,
    )

    CORE_AVAILABLE = True
    logger = get_service_logger("generation-service.plot_twister_agent")
except (ImportError, RuntimeError):
    CORE_AVAILABLE = False
    import logging

    logger = logging.getLogger(__name__)

    # Fallback utility functions
    def utc_now() -> datetime:
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


from generation_service.workflows.state import GenerationState

from .base_agent import AgentCapability, AgentPriority, BaseSpecialAgent


class PlotTwisterAgent(BaseSpecialAgent):
    """
    Plot Twister Agent - Specializes in adding unexpected plot twists and narrative surprises

    Capabilities:
    - Analyzes existing plot structure for predictability
    - Identifies optimal twist insertion points
    - Generates compelling plot revelations
    - Maintains story coherence while adding surprises
    - Enhances audience engagement through unexpected developments
    """

    def __init__(
        self,
        provider_factory: Optional[Any] = None,
        config: Optional[dict[str, Any]] = None,
    ) -> None:
        default_config = {
            "twist_intensity": 0.7,  # How dramatic the twists should be (0.1-1.0)
            "max_twists": 2,  # Maximum number of twists to add
            "preserve_ending": True,  # Whether to preserve the original ending
            "character_revelation": True,  # Allow character-based revelations
            "plot_revelation": True,  # Allow plot-based revelations
            "minimum_content_length": 500,  # Minimum content length to apply twists
        }

        if config:
            default_config.update(config)

        super().__init__(
            agent_name="plot_twister",
            capabilities=[AgentCapability.PLOT_ENHANCEMENT],
            priority=AgentPriority.HIGH,
            provider_factory=provider_factory,
            config=default_config,
        )

    async def analyze_content(self, state: GenerationState) -> dict[str, Any]:
        """
        Analyze script content to determine if plot twists would enhance the story
        """

        content = state.get("styled_script") or state.get("draft_script", "")

        if len(content) < self.get_config_value("minimum_content_length", 500):
            return {
                "should_enhance": False,
                "skip_reason": "Content too short for plot twists",
                "content_length": len(content),
            }

        # Analyze plot structure and predictability
        analysis = {
            "predictability_score": self._calculate_predictability(content),
            "character_count": self._count_characters(content),
            "plot_points": self._identify_plot_points(content),
            "current_twists": self._count_existing_twists(content),
            "twist_opportunities": self._find_twist_opportunities(content),
            "story_structure": self._analyze_story_structure(content),
        }

        # Determine if enhancement is needed
        should_enhance = (
            analysis["predictability_score"] > 0.6  # Story is too predictable
            and analysis["character_count"] >= 2  # Enough characters for twists
            and len(analysis["twist_opportunities"]) > 0  # Valid insertion points exist
            and analysis["current_twists"]
            < self.get_config_value("max_twists", 2)  # Room for more twists
        )

        analysis.update(
            {
                "should_enhance": should_enhance,
                "enhancement_confidence": self._calculate_enhancement_confidence(
                    analysis
                ),
                "recommended_twist_types": self._recommend_twist_types(analysis),
                "context": f"Story has {analysis['predictability_score']:.1f} predictability with {len(analysis['twist_opportunities'])} twist opportunities",
            }
        )

        return analysis

    async def enhance_content(self, state: GenerationState) -> dict[str, Any]:
        """
        Apply plot twists to enhance the narrative
        """

        content = state.get("styled_script") or state.get("draft_script", "")
        analysis = await self.analyze_content(state)

        # Create specialized plot twist prompt
        prompt = await self._create_plot_twist_prompt(content, analysis)

        # Execute AI enhancement
        ai_result = await self.execute_ai_enhancement(prompt, max_tokens=4000)

        # Calculate quality improvement
        quality_improvement = self.calculate_quality_improvement(
            content, ai_result["enhanced_content"]
        )

        # Add plot twist specific metadata
        enhancement_result = {
            **ai_result,
            "quality_improvement": quality_improvement,
            "twist_analysis": analysis,
            "twists_added": self._count_added_twists(
                content, ai_result["enhanced_content"]
            ),
            "plot_structure_preserved": self._verify_structure_preservation(
                content, ai_result["enhanced_content"]
            ),
            "enhancement_type": "plot_twist_enhancement",
        }

        return enhancement_result

    def calculate_quality_improvement(
        self, original_content: str, enhanced_content: str
    ) -> float:
        """
        Calculate quality improvement based on plot enhancement metrics
        """

        original_score = self._calculate_plot_quality(original_content)
        enhanced_score = self._calculate_plot_quality(enhanced_content)

        # Factor in twist effectiveness
        twist_effectiveness = self._evaluate_twist_effectiveness(enhanced_content)

        # Calculate improvement with twist bonus
        base_improvement = enhanced_score - original_score
        twist_bonus = twist_effectiveness * 0.2  # Up to 20% bonus for great twists

        total_improvement = min(base_improvement + twist_bonus, 1.0)

        return max(total_improvement, 0.0)

    def _calculate_predictability(self, content: str) -> float:
        """Calculate how predictable the current plot is (0.0 = unpredictable, 1.0 = very predictable)"""

        predictability_indicators = [
            ("then", 0.1),  # Linear progression
            ("obviously", 0.15),  # Obvious outcomes
            ("as expected", 0.2),  # Expected developments
            ("predictably", 0.25),  # Explicit predictability
            ("of course", 0.1),  # Obvious statements
        ]

        surprise_indicators = [
            ("suddenly", -0.1),  # Sudden changes
            ("unexpectedly", -0.2),  # Unexpected events
            ("shocking", -0.15),  # Shocking revelations
            ("twist", -0.2),  # Existing twists
            ("revelation", -0.15),  # Revelations
            ("surprise", -0.1),  # Surprises
        ]

        content_lower = content.lower()
        predictability_score = 0.5  # Base score

        # Count predictability indicators
        for indicator, weight in predictability_indicators:
            count = content_lower.count(indicator)
            predictability_score += count * weight

        # Count surprise indicators (reduce predictability)
        for indicator, weight in surprise_indicators:
            count = content_lower.count(indicator)
            predictability_score += count * weight  # weight is negative

        # Normalize to 0-1 range
        return max(0.0, min(1.0, predictability_score))

    def _count_characters(self, content: str) -> int:
        """Count distinct character names in the script"""

        # Look for character names (all caps lines with short text)
        character_pattern = r"^[A-Z][A-Z\s]{1,20}$"
        lines = content.split("\n")

        characters = set()
        for line in lines:
            line = line.strip()
            if re.match(character_pattern, line) and len(line.split()) <= 3:
                characters.add(line)

        return len(characters)

    def _identify_plot_points(self, content: str) -> list[dict[str, Any]]:
        """Identify major plot points in the script"""

        plot_indicators = [
            "arrives",
            "discovers",
            "reveals",
            "confronts",
            "decides",
            "attacks",
            "escapes",
            "meets",
            "learns",
            "realizes",
            "finds",
            "loses",
            "wins",
            "fails",
            "dies",
            "returns",
        ]

        plot_points = []
        lines = content.split("\n")

        for i, line in enumerate(lines):
            line_lower = line.lower()
            for indicator in plot_indicators:
                if indicator in line_lower:
                    plot_points.append(
                        {
                            "line_number": i,
                            "type": indicator,
                            "content": line.strip(),
                            "context": self._get_line_context(lines, i),
                        }
                    )

        return plot_points

    def _count_existing_twists(self, content: str) -> int:
        """Count existing plot twists in the content"""

        twist_indicators = [
            "suddenly",
            "unexpectedly",
            "shocking",
            "revelation",
            "twist",
            "surprise",
            "but actually",
            "little did",
            "however",
            "plot twist",
            "it turns out",
        ]

        content_lower = content.lower()
        twist_count = 0

        for indicator in twist_indicators:
            twist_count += content_lower.count(indicator)

        return twist_count

    def _find_twist_opportunities(self, content: str) -> list[dict[str, Any]]:
        """Find potential insertion points for plot twists"""

        lines = content.split("\n")
        opportunities = []

        # Look for scenes that could be enhanced with twists
        for i, line in enumerate(lines):
            line_lower = line.strip().lower()

            # Scene transitions
            if line_lower.startswith(("ext.", "int.", "fade")):
                opportunities.append(
                    {
                        "line_number": i,
                        "type": "scene_transition",
                        "opportunity": "New scene allows for revelation",
                        "confidence": 0.7,
                    }
                )

            # Dialogue that could hide revelations
            elif '"' in line and len(line) > 20:
                opportunities.append(
                    {
                        "line_number": i,
                        "type": "dialogue_twist",
                        "opportunity": "Character could reveal unexpected information",
                        "confidence": 0.6,
                    }
                )

            # Action descriptions
            elif not line_lower.startswith(("ext.", "int.")) and len(line) > 30:
                if any(
                    word in line_lower for word in ["enters", "opens", "looks", "finds"]
                ):
                    opportunities.append(
                        {
                            "line_number": i,
                            "type": "action_twist",
                            "opportunity": "Action could lead to unexpected discovery",
                            "confidence": 0.5,
                        }
                    )

        return opportunities

    def _analyze_story_structure(self, content: str) -> dict[str, Any]:
        """Analyze the overall story structure"""

        lines = content.split("\n")
        total_lines = len([line for line in lines if line.strip()])

        # Divide into acts (rough estimation)
        act1_end = int(total_lines * 0.25)
        act2_end = int(total_lines * 0.75)

        structure = {
            "total_lines": total_lines,
            "estimated_acts": {
                "act1": {"start": 0, "end": act1_end},
                "act2": {"start": act1_end, "end": act2_end},
                "act3": {"start": act2_end, "end": total_lines},
            },
            "has_clear_beginning": self._has_clear_beginning(content),
            "has_climax_buildup": self._has_climax_buildup(content),
            "has_resolution": self._has_resolution(content),
        }

        return structure

    def _calculate_enhancement_confidence(self, analysis: dict[str, Any]) -> float:
        """Calculate confidence level for applying plot twists"""

        factors = [
            (analysis["predictability_score"] > 0.7, 0.3),  # High predictability
            (len(analysis["twist_opportunities"]) > 2, 0.2),  # Multiple opportunities
            (analysis["character_count"] >= 3, 0.2),  # Enough characters
            (analysis["current_twists"] == 0, 0.2),  # No existing twists
            (
                analysis["story_structure"]["has_clear_beginning"],
                0.1,
            ),  # Clear structure
        ]

        confidence = 0.0
        for condition, weight in factors:
            if condition:
                confidence += weight

        return min(confidence, 1.0)

    def _recommend_twist_types(self, analysis: dict[str, Any]) -> list[str]:
        """Recommend types of twists based on analysis"""

        recommendations = []

        # Character-based twists
        if analysis["character_count"] >= 3 and self.get_config_value(
            "character_revelation", True
        ):
            recommendations.append("character_revelation")
            recommendations.append("hidden_relationship")

        # Plot-based twists
        if self.get_config_value("plot_revelation", True):
            recommendations.append("false_assumption")
            recommendations.append("hidden_motive")

        # Structure-based twists
        if len(analysis["twist_opportunities"]) > 3:
            recommendations.append("perspective_shift")
            recommendations.append("timeline_reveal")

        return recommendations

    async def _create_plot_twist_prompt(
        self, content: str, analysis: dict[str, Any]
    ) -> str:
        """Create specialized prompt for plot twist enhancement"""

        twist_intensity = self.get_config_value("twist_intensity", 0.7)
        recommended_twists = ", ".join(analysis.get("recommended_twist_types", []))

        prompt = f"""
You are a master storyteller specializing in plot twists. Enhance the following script by adding compelling, unexpected plot twists that increase audience engagement while maintaining story coherence.

CURRENT SCRIPT:
{content}

ANALYSIS CONTEXT:
- Predictability Score: {analysis['predictability_score']:.1f}/1.0 (higher = more predictable)
- Character Count: {analysis['character_count']}
- Existing Twists: {analysis['current_twists']}
- Twist Opportunities: {len(analysis['twist_opportunities'])}
- Recommended Twist Types: {recommended_twists}

ENHANCEMENT INSTRUCTIONS:
1. Intensity Level: {twist_intensity}/1.0 (moderate to strong twists)
2. Maximum Twists: {self.get_config_value('max_twists', 2)}
3. Preserve Ending: {'Yes' if self.get_config_value('preserve_ending', True) else 'No'}

PLOT TWIST GUIDELINES:
- Add unexpected revelations that recontextualize earlier events
- Ensure twists are surprising but believable in hindsight
- Maintain character consistency and motivations
- Use foreshadowing to make twists feel earned, not random
- Integrate twists naturally into the existing narrative flow
- Preserve the original story's core themes and message

TWIST TECHNIQUES TO CONSIDER:
- Character revelations (hidden identities, relationships, motives)
- False assumptions (what seemed true is actually false)
- Perspective shifts (events seen from new angle)
- Timeline revelations (events happened differently than shown)
- Hidden connections (seemingly unrelated elements are connected)

REQUIREMENTS:
- Maintain script formatting and style
- Keep character voices consistent
- Ensure twists serve the story, not just shock value
- Preserve emotional beats and character arcs
- Make sure the enhanced version is more engaging than the original

Please provide the enhanced script with compelling plot twists integrated seamlessly into the narrative.
"""

        return prompt.strip()

    def _count_added_twists(self, original: str, enhanced: str) -> int:
        """Count how many new twists were added"""

        original_twists = self._count_existing_twists(original)
        enhanced_twists = self._count_existing_twists(enhanced)

        return max(0, enhanced_twists - original_twists)

    def _verify_structure_preservation(self, original: str, enhanced: str) -> bool:
        """Verify that the basic story structure was preserved"""

        # Check that key structural elements are maintained
        original_scenes = len(
            [
                line
                for line in original.split("\n")
                if line.strip().startswith(("EXT.", "INT."))
            ]
        )
        enhanced_scenes = len(
            [
                line
                for line in enhanced.split("\n")
                if line.strip().startswith(("EXT.", "INT."))
            ]
        )

        # Allow for some variation but not drastic changes
        scene_preservation = abs(enhanced_scenes - original_scenes) <= 2

        # Check length preservation (should be roughly similar)
        length_preservation = 0.7 <= len(enhanced) / len(original) <= 1.5

        return scene_preservation and length_preservation

    def _calculate_plot_quality(self, content: str) -> float:
        """Calculate overall plot quality score"""

        factors = [
            ("engagement", self._calculate_engagement_score(content), 0.3),
            ("structure", self._calculate_structure_score(content), 0.2),
            ("character_development", self._calculate_character_score(content), 0.2),
            ("originality", self._calculate_originality_score(content), 0.2),
            ("emotional_impact", self._calculate_emotional_score(content), 0.1),
        ]

        total_score = 0.0
        for name, score, weight in factors:
            total_score += score * weight

        return min(total_score, 1.0)

    def _calculate_engagement_score(self, content: str) -> float:
        """Calculate engagement/interest score"""

        engagement_indicators = [
            "conflict",
            "tension",
            "mystery",
            "surprise",
            "revelation",
        ]
        content_lower = content.lower()

        score = 0.3  # Base score
        for indicator in engagement_indicators:
            if indicator in content_lower:
                score += 0.1

        return min(score, 1.0)

    def _calculate_structure_score(self, content: str) -> float:
        """Calculate story structure score"""

        structure = self._analyze_story_structure(content)

        score = 0.0
        if structure["has_clear_beginning"]:
            score += 0.3
        if structure["has_climax_buildup"]:
            score += 0.4
        if structure["has_resolution"]:
            score += 0.3

        return score

    def _calculate_character_score(self, content: str) -> float:
        """Calculate character development score"""

        character_count = self._count_characters(content)

        # More characters generally means more development opportunities
        if character_count >= 3:
            return 0.8
        elif character_count == 2:
            return 0.6
        elif character_count == 1:
            return 0.4
        else:
            return 0.2

    def _calculate_originality_score(self, content: str) -> float:
        """Calculate originality/unpredictability score"""

        predictability = self._calculate_predictability(content)
        return 1.0 - predictability  # Invert predictability for originality

    def _calculate_emotional_score(self, content: str) -> float:
        """Calculate emotional impact score"""

        emotion_words = [
            "love",
            "fear",
            "anger",
            "joy",
            "sadness",
            "hope",
            "despair",
            "passion",
        ]
        content_lower = content.lower()

        emotion_count = sum(content_lower.count(word) for word in emotion_words)
        return min(emotion_count / 10.0, 1.0)  # Normalize to 0-1

    def _evaluate_twist_effectiveness(self, content: str) -> float:
        """Evaluate how effective the added twists are"""

        twist_quality_indicators = [
            ("revelation", 0.2),
            ("realizes", 0.15),
            ("discovers", 0.15),
            ("truth", 0.1),
            ("secret", 0.1),
            ("hidden", 0.1),
            ("actually", 0.1),
        ]

        content_lower = content.lower()
        effectiveness = 0.0

        for indicator, weight in twist_quality_indicators:
            count = content_lower.count(indicator)
            effectiveness += count * weight

        return min(effectiveness, 1.0)

    def _has_clear_beginning(self, content: str) -> bool:
        """Check if the script has a clear beginning"""

        beginning_indicators = ["fade in", "ext.", "int.", "opens"]
        first_quarter = content[: len(content) // 4].lower()

        return any(indicator in first_quarter for indicator in beginning_indicators)

    def _has_climax_buildup(self, content: str) -> bool:
        """Check if the script builds to a climax"""

        climax_indicators = ["confrontation", "climax", "showdown", "final", "ultimate"]
        content_lower = content.lower()

        return any(indicator in content_lower for indicator in climax_indicators)

    def _has_resolution(self, content: str) -> bool:
        """Check if the script has a resolution"""

        resolution_indicators = [
            "fade out",
            "end",
            "conclusion",
            "finally",
            "resolution",
        ]
        last_quarter = content[3 * len(content) // 4 :].lower()

        return any(indicator in last_quarter for indicator in resolution_indicators)

    def _get_line_context(
        self, lines: list[str], line_index: int, context_size: int = 2
    ) -> str:
        """Get context around a specific line"""

        start = max(0, line_index - context_size)
        end = min(len(lines), line_index + context_size + 1)

        context_lines = lines[start:end]
        return "\n".join(context_lines)
