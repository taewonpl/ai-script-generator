"""
Tension Builder Agent - Builds dramatic tension and optimizes pacing
"""

from typing import Any

# Import Core Module components
try:
    from ai_script_core import (
        get_service_logger,
        utc_now,
    )

    CORE_AVAILABLE = True
    logger = get_service_logger("generation-service.tension_builder_agent")
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


from generation_service.workflows.state import GenerationState

from .base_agent import AgentCapability, AgentPriority, BaseSpecialAgent


class TensionBuilderAgent(BaseSpecialAgent):
    """
    Tension Builder Agent - Specializes in building dramatic tension and optimizing pacing

    Capabilities:
    - Analyzes conflict structure and intensity
    - Builds dramatic tension throughout the narrative
    - Optimizes pacing for maximum emotional impact
    - Enhances climax development and resolution
    - Manages tension release patterns
    """

    # Tension building techniques with effectiveness weights
    TENSION_TECHNIQUES = {
        "conflict_escalation": {
            "increasing_stakes": 0.9,
            "time_pressure": 0.8,
            "resource_scarcity": 0.7,
            "multiple_obstacles": 0.8,
            "personal_cost": 0.9,
        },
        "emotional_tension": {
            "internal_conflict": 0.8,
            "relationship_strain": 0.7,
            "moral_dilemma": 0.9,
            "fear_anticipation": 0.8,
            "vulnerability_exposure": 0.8,
        },
        "structural_tension": {
            "delayed_gratification": 0.7,
            "false_victory": 0.8,
            "revelation_timing": 0.9,
            "cliffhanger_moments": 0.8,
            "pacing_variation": 0.7,
        },
        "atmospheric_tension": {
            "environmental_pressure": 0.6,
            "sensory_details": 0.5,
            "foreboding_atmosphere": 0.7,
            "symbolic_elements": 0.6,
            "silence_and_space": 0.5,
        },
    }

    # Pacing patterns for different story moments
    PACING_PATTERNS = {
        "build_up": {
            "short_sentences": 0.3,
            "quick_exchanges": 0.4,
            "action_descriptions": 0.3,
            "rhythm": "accelerating",
        },
        "climax": {
            "sharp_dialogue": 0.4,
            "intense_actions": 0.5,
            "emotional_peaks": 0.1,
            "rhythm": "rapid",
        },
        "release": {
            "longer_descriptions": 0.4,
            "breathing_room": 0.3,
            "reflection_moments": 0.3,
            "rhythm": "deceleration",
        },
    }

    def __init__(self, provider_factory=None, config: dict[str, Any] = None):
        default_config = {
            "tension_intensity": 0.8,  # How intense tension should be (0.1-1.0)
            "pacing_optimization": True,  # Enable pacing optimization
            "conflict_enhancement": 0.9,  # How much to enhance conflicts
            "climax_strength": 0.9,  # How strong the climax should be
            "tension_release_balance": 0.7,  # Balance between tension and release
            "minimum_conflict_scenes": 2,  # Minimum scenes needed for tension building
            "preserve_story_beats": True,  # Preserve original emotional beats
        }

        if config:
            default_config.update(config)

        super().__init__(
            agent_name="tension_builder",
            capabilities=[
                AgentCapability.TENSION_BUILDING,
                AgentCapability.PACING_OPTIMIZATION,
            ],
            priority=AgentPriority.HIGH,
            provider_factory=provider_factory,
            config=default_config,
        )

    async def analyze_content(self, state: GenerationState) -> dict[str, Any]:
        """
        Analyze tension patterns and pacing to determine enhancement opportunities
        """

        content = state.get("styled_script") or state.get("draft_script", "")

        # Analyze tension and conflict structure
        tension_analysis = self._analyze_tension_structure(content)

        if tension_analysis["conflict_scenes"] < self.get_config_value(
            "minimum_conflict_scenes", 2
        ):
            return {
                "should_enhance": False,
                "skip_reason": "Insufficient conflict scenes for tension building",
                "conflict_scenes": tension_analysis["conflict_scenes"],
            }

        # Analyze pacing patterns
        pacing_analysis = self._analyze_pacing_patterns(content)

        # Identify tension enhancement opportunities
        enhancement_opportunities = self._identify_tension_opportunities(
            content, tension_analysis, pacing_analysis
        )

        # Calculate overall tension effectiveness
        tension_effectiveness = self._calculate_tension_effectiveness(
            tension_analysis, pacing_analysis
        )

        analysis = {
            "tension_structure": tension_analysis,
            "pacing_analysis": pacing_analysis,
            "tension_effectiveness": tension_effectiveness,
            "enhancement_opportunities": enhancement_opportunities,
            "climax_potential": self._assess_climax_potential(content),
            "should_enhance": tension_effectiveness < 0.7
            or len(enhancement_opportunities) > 2,
            "enhancement_confidence": self._calculate_enhancement_confidence(
                tension_analysis, pacing_analysis
            ),
            "context": f"Tension effectiveness {tension_effectiveness:.1f} with {len(enhancement_opportunities)} opportunities",
        }

        return analysis

    async def enhance_content(self, state: GenerationState) -> dict[str, Any]:
        """
        Enhance dramatic tension and optimize pacing
        """

        content = state.get("styled_script") or state.get("draft_script", "")
        analysis = await self.analyze_content(state)

        # Create specialized tension building prompt
        prompt = await self._create_tension_building_prompt(content, analysis)

        # Execute AI enhancement
        ai_result = await self.execute_ai_enhancement(prompt, max_tokens=4000)

        # Calculate quality improvement
        quality_improvement = self.calculate_quality_improvement(
            content, ai_result["enhanced_content"]
        )

        # Analyze enhancement results
        enhancement_analysis = self._analyze_enhancement_results(
            content, ai_result["enhanced_content"], analysis
        )

        enhancement_result = {
            **ai_result,
            "quality_improvement": quality_improvement,
            "tension_analysis": analysis,
            "tension_increase": enhancement_analysis["tension_increase"],
            "pacing_improvement": enhancement_analysis["pacing_improvement"],
            "climax_enhancement": enhancement_analysis["climax_enhancement"],
            "conflict_escalation": enhancement_analysis["conflict_escalation"],
            "enhancement_type": "tension_building_enhancement",
        }

        return enhancement_result

    def calculate_quality_improvement(
        self, original_content: str, enhanced_content: str
    ) -> float:
        """
        Calculate quality improvement based on tension and pacing metrics
        """

        original_tension = self._calculate_overall_tension_score(original_content)
        enhanced_tension = self._calculate_overall_tension_score(enhanced_content)

        original_pacing = self._calculate_pacing_score(original_content)
        enhanced_pacing = self._calculate_pacing_score(enhanced_content)

        # Calculate weighted improvement
        tension_improvement = enhanced_tension - original_tension
        pacing_improvement = enhanced_pacing - original_pacing

        # Weighted average (tension is more important)
        total_improvement = (tension_improvement * 0.7) + (pacing_improvement * 0.3)

        return max(0.0, min(total_improvement, 1.0))

    def _analyze_tension_structure(self, content: str) -> dict[str, Any]:
        """Analyze the tension and conflict structure in the content"""

        lines = content.split("\n")
        conflict_indicators = [
            "argues",
            "fights",
            "confronts",
            "threatens",
            "challenges",
            "opposes",
            "refuses",
            "denies",
            "attacks",
            "defends",
            "angry",
            "furious",
            "tension",
            "conflict",
            "struggle",
        ]

        emotional_peaks = [
            "screams",
            "shouts",
            "cries",
            "breaks down",
            "explodes",
            "devastated",
            "heartbroken",
            "terrified",
            "panicked",
        ]

        tension_points = []
        conflict_scenes = 0
        emotional_intensity = []

        for i, line in enumerate(lines):
            line_lower = line.lower()

            # Count conflict indicators
            conflict_count = sum(
                line_lower.count(indicator) for indicator in conflict_indicators
            )
            if conflict_count > 0:
                conflict_scenes += 1
                tension_points.append(
                    {
                        "line_number": i,
                        "intensity": min(conflict_count, 3),
                        "type": "conflict",
                    }
                )

            # Count emotional peaks
            emotion_count = sum(line_lower.count(peak) for peak in emotional_peaks)
            if emotion_count > 0:
                emotional_intensity.append(emotion_count)
                tension_points.append(
                    {
                        "line_number": i,
                        "intensity": min(emotion_count, 3),
                        "type": "emotional",
                    }
                )

        return {
            "conflict_scenes": conflict_scenes,
            "tension_points": tension_points,
            "emotional_intensity_average": (
                sum(emotional_intensity) / len(emotional_intensity)
                if emotional_intensity
                else 0
            ),
            "tension_distribution": self._analyze_tension_distribution(
                tension_points, len(lines)
            ),
            "escalation_pattern": self._analyze_escalation_pattern(tension_points),
        }

    def _analyze_pacing_patterns(self, content: str) -> dict[str, Any]:
        """Analyze pacing patterns in the content"""

        lines = content.split("\n")
        sentences = [
            line
            for line in lines
            if line.strip() and not line.strip().startswith(("EXT.", "INT."))
        ]

        if not sentences:
            return {
                "average_sentence_length": 0,
                "rhythm_variation": 0,
                "pacing_score": 0.0,
                "fast_paced_sections": 0,
                "slow_paced_sections": 0,
            }

        # Analyze sentence lengths for rhythm
        sentence_lengths = [len(sentence.split()) for sentence in sentences]
        avg_length = sum(sentence_lengths) / len(sentence_lengths)

        # Calculate rhythm variation
        length_variance = sum(
            (length - avg_length) ** 2 for length in sentence_lengths
        ) / len(sentence_lengths)
        rhythm_variation = min(length_variance / 100, 1.0)

        # Identify pacing sections
        fast_paced_indicators = [
            "quickly",
            "suddenly",
            "immediately",
            "rushes",
            "bursts",
        ]
        slow_paced_indicators = [
            "slowly",
            "gradually",
            "thoughtfully",
            "pauses",
            "reflects",
        ]

        fast_sections = sum(
            content.lower().count(indicator) for indicator in fast_paced_indicators
        )
        slow_sections = sum(
            content.lower().count(indicator) for indicator in slow_paced_indicators
        )

        # Calculate overall pacing score
        pacing_score = self._calculate_pacing_effectiveness(
            sentence_lengths, fast_sections, slow_sections
        )

        return {
            "average_sentence_length": avg_length,
            "rhythm_variation": rhythm_variation,
            "pacing_score": pacing_score,
            "fast_paced_sections": fast_sections,
            "slow_paced_sections": slow_sections,
            "sentence_length_distribution": self._categorize_sentence_lengths(
                sentence_lengths
            ),
        }

    def _identify_tension_opportunities(
        self, content: str, tension_analysis: dict, pacing_analysis: dict
    ) -> list[dict[str, Any]]:
        """Identify specific opportunities to build tension"""

        opportunities = []
        lines = content.split("\n")

        # Look for scenes that could use more tension
        for i, line in enumerate(lines):
            line_lower = line.strip().lower()

            # Scene headers that could be more tense
            if line_lower.startswith(("ext.", "int.")):
                if not any(
                    word in line_lower for word in ["night", "storm", "dark", "tension"]
                ):
                    opportunities.append(
                        {
                            "line_number": i,
                            "type": "atmospheric_tension",
                            "current": line,
                            "potential": "Add atmospheric tension to scene setting",
                        }
                    )

            # Dialogue that could be more confrontational
            elif '"' in line and len(line) > 20:
                if not any(
                    word in line_lower
                    for word in ["but", "however", "no", "stop", "wait"]
                ):
                    opportunities.append(
                        {
                            "line_number": i,
                            "type": "dialogue_tension",
                            "current": line,
                            "potential": "Add conflict or resistance to dialogue",
                        }
                    )

            # Action lines that could be more dramatic
            elif len(line) > 30 and not line_lower.startswith(("ext.", "int.")):
                tension_words = ["tension", "dramatic", "intense", "urgent", "crucial"]
                if not any(word in line_lower for word in tension_words):
                    opportunities.append(
                        {
                            "line_number": i,
                            "type": "action_tension",
                            "current": line,
                            "potential": "Increase dramatic intensity of action",
                        }
                    )

        return opportunities

    def _calculate_tension_effectiveness(
        self, tension_analysis: dict, pacing_analysis: dict
    ) -> float:
        """Calculate overall tension effectiveness score"""

        factors = [
            # Tension structure factors
            (min(tension_analysis["conflict_scenes"] / 5.0, 1.0), 0.3),
            (tension_analysis["emotional_intensity_average"] / 3.0, 0.2),
            (tension_analysis["tension_distribution"], 0.2),
            # Pacing factors
            (pacing_analysis["pacing_score"], 0.2),
            (pacing_analysis["rhythm_variation"], 0.1),
        ]

        effectiveness = 0.0
        for score, weight in factors:
            effectiveness += score * weight

        return min(effectiveness, 1.0)

    def _assess_climax_potential(self, content: str) -> dict[str, Any]:
        """Assess the potential for climax enhancement"""

        content_lower = content.lower()
        climax_indicators = [
            "climax",
            "confrontation",
            "showdown",
            "final",
            "ultimate",
            "decisive",
        ]
        resolution_indicators = ["resolution", "conclusion", "end", "finally", "peace"]

        climax_mentions = sum(
            content_lower.count(indicator) for indicator in climax_indicators
        )
        resolution_mentions = sum(
            content_lower.count(indicator) for indicator in resolution_indicators
        )

        # Analyze story position (climax should be towards the end)
        lines = content.split("\n")
        total_lines = len([line for line in lines if line.strip()])

        climax_potential = {
            "has_identifiable_climax": climax_mentions > 0,
            "climax_strength": min(climax_mentions / 3.0, 1.0),
            "has_resolution": resolution_mentions > 0,
            "structure_balance": min(abs(0.75 - 0.8), 0.2)
            / 0.2,  # Simplified calculation
            "enhancement_potential": max(0.0, 1.0 - min(climax_mentions / 2.0, 1.0)),
        }

        return climax_potential

    def _calculate_enhancement_confidence(
        self, tension_analysis: dict, pacing_analysis: dict
    ) -> float:
        """Calculate confidence for tension enhancement"""

        factors = [
            # Low current tension effectiveness
            (
                self._calculate_tension_effectiveness(tension_analysis, pacing_analysis)
                < 0.6,
                0.3,
            ),
            # Sufficient conflict content
            (tension_analysis["conflict_scenes"] >= 3, 0.2),
            # Poor pacing patterns
            (pacing_analysis["pacing_score"] < 0.5, 0.2),
            # Low rhythm variation
            (pacing_analysis["rhythm_variation"] < 0.3, 0.2),
            # Good escalation potential
            (len(tension_analysis["tension_points"]) > 0, 0.1),
        ]

        confidence = 0.0
        for condition, weight in factors:
            if condition:
                confidence += weight

        return min(confidence, 1.0)

    async def _create_tension_building_prompt(
        self, content: str, analysis: dict[str, Any]
    ) -> str:
        """Create specialized prompt for tension building enhancement"""

        tension_intensity = self.get_config_value("tension_intensity", 0.8)
        conflict_enhancement = self.get_config_value("conflict_enhancement", 0.9)
        climax_strength = self.get_config_value("climax_strength", 0.9)

        # Format enhancement opportunities
        opportunities_text = []
        for opp in analysis["enhancement_opportunities"][:5]:  # Top 5
            opportunities_text.append(
                f"- {opp['type'].replace('_', ' ').title()}: {opp['potential']}"
            )

        opportunities_summary = (
            "\n".join(opportunities_text)
            if opportunities_text
            else "Focus on general tension building"
        )

        prompt = f"""
You are a dramatic tension expert specializing in building suspense, conflict, and emotional intensity. Enhance the following script by increasing dramatic tension, optimizing pacing, and strengthening the climax while maintaining story coherence.

CURRENT SCRIPT:
{content}

TENSION ANALYSIS:
- Conflict Scenes: {analysis['tension_structure']['conflict_scenes']}
- Tension Effectiveness: {analysis['tension_effectiveness']:.1f}/1.0
- Pacing Score: {analysis['pacing_analysis']['pacing_score']:.1f}/1.0
- Climax Potential: {analysis['climax_potential']['enhancement_potential']:.1f}

ENHANCEMENT OPPORTUNITIES:
{opportunities_summary}

ENHANCEMENT SETTINGS:
- Tension Intensity: {tension_intensity}/1.0 (build dramatic tension)
- Conflict Enhancement: {conflict_enhancement}/1.0 (strengthen conflicts)
- Climax Strength: {climax_strength}/1.0 (powerful climax)
- Pacing Optimization: {self.get_config_value('pacing_optimization', True)}

TENSION BUILDING GUIDELINES:
1. Escalate conflicts progressively throughout the story
2. Create time pressure and increasing stakes
3. Build emotional tension through character relationships
4. Use pacing variation to control dramatic rhythm
5. Strengthen the climax with maximum emotional impact
6. Balance tension with strategic release moments

SPECIFIC TECHNIQUES:
- Conflict Escalation: Add obstacles, increase personal stakes, create time pressure
- Emotional Tension: Internal conflicts, moral dilemmas, relationship strain
- Structural Tension: Delayed gratification, false victories, well-timed revelations
- Atmospheric Tension: Environmental pressure, foreboding mood, symbolic elements
- Pacing Control: Vary sentence length, quick exchanges during intense moments

PACING OPTIMIZATION:
- Build-up sections: Gradually increase pace and tension
- Climax moments: Sharp, rapid exchanges and intense action
- Release moments: Slower pacing for emotional processing
- Rhythm variation: Mix short, punchy lines with longer descriptions

REQUIREMENTS:
- Maintain script formatting and character consistency
- Preserve original story structure and themes
- Ensure tension builds logically and believably
- Keep character motivations and relationships intact
- Make tension serve the story, not overwhelm it
- Create satisfying tension release at appropriate moments

Please provide the enhanced script with dramatically improved tension, pacing, and emotional impact.
"""

        return prompt.strip()

    def _analyze_enhancement_results(
        self, original: str, enhanced: str, analysis: dict[str, Any]
    ) -> dict[str, Any]:
        """Analyze the results of tension enhancement"""

        original_tension = self._calculate_overall_tension_score(original)
        enhanced_tension = self._calculate_overall_tension_score(enhanced)

        original_pacing = self._calculate_pacing_score(original)
        enhanced_pacing = self._calculate_pacing_score(enhanced)

        results = {
            "tension_increase": max(0.0, enhanced_tension - original_tension),
            "pacing_improvement": max(0.0, enhanced_pacing - original_pacing),
            "climax_enhancement": self._calculate_climax_improvement(
                original, enhanced
            ),
            "conflict_escalation": self._count_conflict_escalations(original, enhanced),
        }

        return results

    def _calculate_overall_tension_score(self, content: str) -> float:
        """Calculate overall tension score for content"""

        tension_analysis = self._analyze_tension_structure(content)
        pacing_analysis = self._analyze_pacing_patterns(content)

        return self._calculate_tension_effectiveness(tension_analysis, pacing_analysis)

    def _calculate_pacing_score(self, content: str) -> float:
        """Calculate pacing score for content"""

        pacing_analysis = self._analyze_pacing_patterns(content)
        return pacing_analysis["pacing_score"]

    def _calculate_climax_improvement(self, original: str, enhanced: str) -> float:
        """Calculate improvement in climax strength"""

        original_climax = self._assess_climax_potential(original)
        enhanced_climax = self._assess_climax_potential(enhanced)

        return max(
            0.0, enhanced_climax["climax_strength"] - original_climax["climax_strength"]
        )

    def _count_conflict_escalations(self, original: str, enhanced: str) -> int:
        """Count how many conflict escalations were added"""

        escalation_indicators = [
            "escalates",
            "intensifies",
            "worsens",
            "builds",
            "grows",
        ]

        original_lower = original.lower()
        enhanced_lower = enhanced.lower()

        original_escalations = sum(
            original_lower.count(indicator) for indicator in escalation_indicators
        )
        enhanced_escalations = sum(
            enhanced_lower.count(indicator) for indicator in escalation_indicators
        )

        return max(0, enhanced_escalations - original_escalations)

    def _analyze_tension_distribution(
        self, tension_points: list[dict], total_lines: int
    ) -> float:
        """Analyze how tension is distributed throughout the content"""

        if not tension_points or total_lines == 0:
            return 0.0

        # Divide content into thirds and check tension distribution
        third = total_lines // 3
        sections = [0, 0, 0]  # Beginning, middle, end

        for point in tension_points:
            line_num = point["line_number"]
            if line_num < third:
                sections[0] += point["intensity"]
            elif line_num < 2 * third:
                sections[1] += point["intensity"]
            else:
                sections[2] += point["intensity"]

        # Good distribution should have increasing tension toward the end
        if sum(sections) == 0:
            return 0.0

        # Normalize and weight toward end
        normalized = [s / sum(sections) for s in sections]

        # Ideal distribution weights more toward middle and end
        ideal_weights = [0.2, 0.4, 0.4]
        distribution_score = (
            1.0 - sum(abs(normalized[i] - ideal_weights[i]) for i in range(3)) / 2.0
        )

        return max(0.0, distribution_score)

    def _analyze_escalation_pattern(self, tension_points: list[dict]) -> dict[str, Any]:
        """Analyze the escalation pattern of tension points"""

        if len(tension_points) < 2:
            return {"has_escalation": False, "escalation_quality": 0.0}

        # Sort by line number
        sorted_points = sorted(tension_points, key=lambda x: x["line_number"])

        # Check if tension generally increases
        intensities = [point["intensity"] for point in sorted_points]

        escalation_count = 0
        for i in range(1, len(intensities)):
            if intensities[i] > intensities[i - 1]:
                escalation_count += 1

        escalation_ratio = (
            escalation_count / (len(intensities) - 1) if len(intensities) > 1 else 0.0
        )

        return {
            "has_escalation": escalation_ratio > 0.5,
            "escalation_quality": escalation_ratio,
            "tension_peaks": len([i for i in intensities if i >= 2]),
            "average_intensity": sum(intensities) / len(intensities),
        }

    def _calculate_pacing_effectiveness(
        self, sentence_lengths: list[int], fast_sections: int, slow_sections: int
    ) -> float:
        """Calculate effectiveness of pacing patterns"""

        if not sentence_lengths:
            return 0.0

        # Good pacing has variety in sentence lengths
        avg_length = sum(sentence_lengths) / len(sentence_lengths)
        length_variety = len(set(sentence_lengths)) / len(sentence_lengths)

        # Balance between fast and slow sections
        total_pacing_indicators = fast_sections + slow_sections
        pacing_balance = (
            1.0
            if total_pacing_indicators == 0
            else min(fast_sections, slow_sections) / total_pacing_indicators
        )

        # Combine factors
        variety_score = min(length_variety, 1.0)
        balance_score = pacing_balance
        presence_score = min(total_pacing_indicators / 5.0, 1.0)

        return (variety_score * 0.4) + (balance_score * 0.3) + (presence_score * 0.3)

    def _categorize_sentence_lengths(
        self, sentence_lengths: list[int]
    ) -> dict[str, int]:
        """Categorize sentences by length for rhythm analysis"""

        categories = {"short": 0, "medium": 0, "long": 0}

        for length in sentence_lengths:
            if length <= 5:
                categories["short"] += 1
            elif length <= 15:
                categories["medium"] += 1
            else:
                categories["long"] += 1

        return categories
