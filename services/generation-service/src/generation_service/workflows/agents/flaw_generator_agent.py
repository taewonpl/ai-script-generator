"""
Flaw Generator Agent - Adds realistic character flaws and weaknesses for depth
"""

from typing import Any, Dict, List, Optional

# Import Core Module components
try:
    from ai_script_core import (
        get_service_logger,
        utc_now,
    )

    CORE_AVAILABLE = True
    logger = get_service_logger("generation-service.flaw_generator_agent")
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


class FlawGeneratorAgent(BaseSpecialAgent):
    """
    Flaw Generator Agent - Specializes in adding realistic character flaws and weaknesses

    Capabilities:
    - Analyzes characters for depth and complexity
    - Identifies overly perfect or flat characters
    - Adds believable flaws that enhance relatability
    - Creates character growth opportunities
    - Maintains character consistency while adding depth
    """

    # Character flaw categories with weights
    FLAW_CATEGORIES = {
        "personality": {
            "arrogance": 0.8,
            "stubbornness": 0.7,
            "impatience": 0.6,
            "perfectionism": 0.7,
            "insecurity": 0.8,
            "cynicism": 0.6,
            "naivety": 0.7,
            "selfishness": 0.8,
        },
        "behavioral": {
            "procrastination": 0.6,
            "impulsiveness": 0.7,
            "avoidance": 0.6,
            "overthinking": 0.7,
            "people_pleasing": 0.8,
            "controlling": 0.8,
            "passive_aggressive": 0.7,
            "workaholic": 0.6,
        },
        "emotional": {
            "trust_issues": 0.8,
            "fear_of_commitment": 0.7,
            "anger_management": 0.8,
            "emotional_walls": 0.7,
            "abandonment_fear": 0.8,
            "rejection_sensitivity": 0.7,
            "guilt_prone": 0.6,
            "emotional_volatility": 0.7,
        },
        "social": {
            "social_anxiety": 0.7,
            "poor_boundaries": 0.8,
            "communication_issues": 0.7,
            "judgment_of_others": 0.6,
            "difficulty_saying_no": 0.7,
            "oversharing": 0.6,
            "isolation_tendency": 0.7,
            "conflict_avoidance": 0.6,
        },
    }

    def __init__(self, provider_factory: Optional[Any] = None, config: Optional[Dict[str, Any]] = None) -> None:
        default_config = {
            "max_flaws_per_character": 2,  # Maximum flaws to add per character
            "flaw_intensity": 0.6,  # How prominent flaws should be (0.1-1.0)
            "allow_growth_arcs": True,  # Enable character growth opportunities
            "preserve_likability": True,  # Keep characters likable despite flaws
            "minimum_characters": 2,  # Minimum characters needed to apply
            "flaw_integration_style": "subtle",  # "subtle", "moderate", "prominent"
        }

        if config:
            default_config.update(config)

        super().__init__(
            agent_name="flaw_generator",
            capabilities=[AgentCapability.CHARACTER_DEVELOPMENT],
            priority=AgentPriority.MEDIUM,
            provider_factory=provider_factory,
            config=default_config,
        )

    async def analyze_content(self, state: GenerationState) -> Dict[str, Any]:
        """
        Analyze characters to determine if flaws would enhance the story
        """

        content = state.get("styled_script") or state.get("draft_script", "")

        # Extract and analyze characters
        characters = self._extract_characters(content)

        if len(characters) < self.get_config_value("minimum_characters", 2):
            return {
                "should_enhance": False,
                "skip_reason": "Not enough characters for flaw generation",
                "character_count": len(characters),
            }

        # Analyze each character for depth and flaws
        character_analysis = {}
        for char_name, char_data in characters.items():
            character_analysis[char_name] = self._analyze_character(
                char_name, char_data
            )

        # Determine overall enhancement potential
        enhancement_needed = self._determine_enhancement_need(character_analysis)

        analysis = {
            "characters": character_analysis,
            "character_count": len(characters),
            "average_depth_score": self._calculate_average_depth(character_analysis),
            "enhancement_opportunities": self._identify_enhancement_opportunities(
                character_analysis
            ),
            "recommended_flaws": self._recommend_flaws(character_analysis),
            "should_enhance": enhancement_needed,
            "enhancement_confidence": self._calculate_enhancement_confidence(
                character_analysis
            ),
            "context": f"Found {len(characters)} characters with average depth {self._calculate_average_depth(character_analysis):.1f}/1.0",
        }

        return analysis

    async def enhance_content(self, state: GenerationState) -> Dict[str, Any]:
        """
        Add character flaws to enhance depth and relatability
        """

        content = state.get("styled_script") or state.get("draft_script", "")
        analysis = await self.analyze_content(state)

        # Create specialized flaw generation prompt
        prompt = await self._create_flaw_generation_prompt(content, analysis)

        # Execute AI enhancement
        ai_result = await self.execute_ai_enhancement(prompt, max_tokens=4000)

        # Calculate quality improvement
        quality_improvement = self.calculate_quality_improvement(
            content, ai_result["enhanced_content"]
        )

        # Analyze the enhancement results
        enhancement_analysis = self._analyze_enhancement_results(
            content, ai_result["enhanced_content"], analysis
        )

        enhancement_result = {
            **ai_result,
            "quality_improvement": quality_improvement,
            "character_analysis": analysis,
            "flaws_added": enhancement_analysis["flaws_added"],
            "character_depth_improvement": enhancement_analysis["depth_improvement"],
            "growth_opportunities_created": enhancement_analysis[
                "growth_opportunities"
            ],
            "enhancement_type": "character_flaw_enhancement",
        }

        return enhancement_result

    def calculate_quality_improvement(
        self, original_content: str, enhanced_content: str
    ) -> float:
        """
        Calculate quality improvement based on character depth enhancement
        """

        original_characters = self._extract_characters(original_content)
        enhanced_characters = self._extract_characters(enhanced_content)

        original_depth = self._calculate_overall_character_depth(original_characters)
        enhanced_depth = self._calculate_overall_character_depth(enhanced_characters)

        # Factor in flaw integration quality
        flaw_integration_quality = self._evaluate_flaw_integration(enhanced_content)

        # Calculate improvement with integration bonus
        base_improvement = enhanced_depth - original_depth
        integration_bonus = flaw_integration_quality * 0.15  # Up to 15% bonus

        total_improvement = min(base_improvement + integration_bonus, 1.0)

        return max(total_improvement, 0.0)

    def _extract_characters(self, content: str) -> Dict[str, Dict[str, Any]]:
        """Extract characters and their information from the script"""

        characters = {}
        lines = content.split("\n")
        current_character = None

        for i, line in enumerate(lines):
            line = line.strip()

            # Detect character names (usually all caps)
            if self._is_character_name(line):
                char_name = line.strip(":").strip()
                current_character = char_name

                if char_name not in characters:
                    characters[char_name] = {
                        "name": char_name,
                        "dialogue_lines": [],
                        "action_lines": [],
                        "first_appearance": i,
                        "total_lines": 0,
                    }

            # Collect dialogue
            elif (
                current_character
                and line
                and not line.startswith(("EXT.", "INT.", "FADE"))
            ):
                if line.startswith('"') or '"' in line:
                    characters[current_character]["dialogue_lines"].append(line)
                else:
                    characters[current_character]["action_lines"].append(line)

                characters[current_character]["total_lines"] += 1

        return characters

    def _is_character_name(self, line: str) -> bool:
        """Determine if a line represents a character name"""

        line = line.strip(":").strip()

        # Basic heuristics for character names
        if (
            line.isupper()
            and len(line.split()) <= 3
            and len(line) > 1
            and not line.startswith(("EXT.", "INT.", "FADE", "CUT"))
        ):
            return True

        return False

    def _analyze_character(
        self, char_name: str, char_data: dict[str, Any]
    ) -> dict[str, Any]:
        """Analyze a single character for depth and flaw potential"""

        dialogue_lines = char_data.get("dialogue_lines", [])
        action_lines = char_data.get("action_lines", [])

        analysis = {
            "name": char_name,
            "dialogue_count": len(dialogue_lines),
            "action_count": len(action_lines),
            "total_presence": char_data.get("total_lines", 0),
            "depth_score": self._calculate_character_depth(char_data),
            "existing_flaws": self._identify_existing_flaws(
                dialogue_lines + action_lines
            ),
            "personality_traits": self._extract_personality_traits(dialogue_lines),
            "behavioral_patterns": self._extract_behavioral_patterns(action_lines),
            "flaw_potential": self._assess_flaw_potential(char_data),
            "recommended_flaw_categories": self._recommend_flaw_categories(char_data),
        }

        return analysis

    def _calculate_character_depth(self, char_data: Dict[str, Any]) -> float:
        """Calculate character depth score (0.0 = flat, 1.0 = very deep)"""

        dialogue_lines = char_data.get("dialogue_lines", [])
        action_lines = char_data.get("action_lines", [])

        depth_factors = [
            # Presence factor
            min(char_data.get("total_lines", 0) / 20.0, 0.3),
            # Dialogue variety
            self._calculate_dialogue_variety(dialogue_lines) * 0.3,
            # Emotional range
            self._calculate_emotional_range(dialogue_lines + action_lines) * 0.2,
            # Complexity indicators
            self._calculate_complexity_indicators(dialogue_lines + action_lines) * 0.2,
        ]

        return min(sum(depth_factors), 1.0)

    def _identify_existing_flaws(self, character_lines: List[str]) -> List[str]:
        """Identify existing character flaws in the text"""

        existing_flaws = []
        combined_text = " ".join(character_lines).lower()

        # Check for existing flaw indicators
        flaw_indicators = {
            "arrogant": ["superior", "better than", "beneath me", "obviously"],
            "stubborn": ["won't change", "refuse", "never", "always right"],
            "impatient": ["hurry", "quickly", "can't wait", "now"],
            "insecure": ["not sure", "maybe", "probably wrong", "doubt"],
            "selfish": ["me first", "my needs", "don't care about"],
        }

        for flaw, indicators in flaw_indicators.items():
            if any(indicator in combined_text for indicator in indicators):
                existing_flaws.append(flaw)

        return existing_flaws

    def _extract_personality_traits(self, dialogue_lines: List[str]) -> List[str]:
        """Extract personality traits from dialogue"""

        traits = []
        combined_dialogue = " ".join(dialogue_lines).lower()

        trait_indicators = {
            "confident": ["know", "certain", "definitely", "sure"],
            "caring": ["help", "care", "worry", "love"],
            "humorous": ["funny", "joke", "laugh", "haha"],
            "serious": ["important", "serious", "crucial", "grave"],
            "optimistic": ["hope", "positive", "bright", "good"],
            "pessimistic": ["wrong", "bad", "terrible", "worst"],
        }

        for trait, indicators in trait_indicators.items():
            score = sum(combined_dialogue.count(indicator) for indicator in indicators)
            if score > 0:
                traits.append((trait, score))

        # Return top traits
        traits.sort(key=lambda x: x[1], reverse=True)
        return [trait[0] for trait in traits[:3]]

    def _extract_behavioral_patterns(self, action_lines: List[str]) -> List[str]:
        """Extract behavioral patterns from action descriptions"""

        patterns = []
        combined_actions = " ".join(action_lines).lower()

        behavior_indicators = {
            "aggressive": ["grabs", "shouts", "storms", "slams"],
            "cautious": ["carefully", "slowly", "hesitates", "checks"],
            "impulsive": ["suddenly", "immediately", "quickly", "rushes"],
            "withdrawn": ["alone", "quietly", "avoids", "steps back"],
        }

        for pattern, indicators in behavior_indicators.items():
            if any(indicator in combined_actions for indicator in indicators):
                patterns.append(pattern)

        return patterns

    def _assess_flaw_potential(self, char_data: Dict[str, Any]) -> float:
        """Assess how much potential there is for adding flaws"""

        factors = [
            # More presence = more potential for flaws
            min(char_data.get("total_lines", 0) / 15.0, 0.4),
            # Lower depth = higher potential for improvement
            (1.0 - self._calculate_character_depth(char_data)) * 0.4,
            # Fewer existing flaws = more potential
            max(0.2 - len(char_data.get("existing_flaws", [])) * 0.1, 0.0),
        ]

        return min(sum(factors), 1.0)

    def _recommend_flaw_categories(self, char_data: Dict[str, Any]) -> List[str]:
        """Recommend flaw categories for a character"""

        personality_traits = char_data.get("personality_traits", [])
        behavioral_patterns = char_data.get("behavioral_patterns", [])

        recommendations = []

        # Base on existing traits
        if "confident" in personality_traits:
            recommendations.append("personality")  # Could add arrogance
        if "caring" in personality_traits:
            recommendations.append("emotional")  # Could add trust issues
        if "aggressive" in behavioral_patterns:
            recommendations.append("behavioral")  # Could add anger management
        if "cautious" in behavioral_patterns:
            recommendations.append("social")  # Could add social anxiety

        # Default to personality if no specific indicators
        if not recommendations:
            recommendations.append("personality")

        return recommendations

    def _determine_enhancement_need(self, character_analysis: Dict[str, Any]) -> bool:
        """Determine if character flaw enhancement is needed"""

        # Check if any characters are too perfect or flat
        for char_name, analysis in character_analysis.items():
            if (
                analysis["depth_score"] < 0.6
                and analysis["flaw_potential"] > 0.5
                and len(analysis["existing_flaws"]) < 2
            ):
                return True

        return False

    def _calculate_average_depth(self, character_analysis: Dict[str, Any]) -> float:
        """Calculate average character depth across all characters"""

        if not character_analysis:
            return 0.0

        total_depth = sum(
            analysis["depth_score"] for analysis in character_analysis.values()
        )
        return total_depth / len(character_analysis)

    def _identify_enhancement_opportunities(
        self, character_analysis: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """Identify specific enhancement opportunities"""

        opportunities = []

        for char_name, analysis in character_analysis.items():
            if analysis["flaw_potential"] > 0.4:
                opportunities.append(
                    {
                        "character": char_name,
                        "potential": analysis["flaw_potential"],
                        "recommended_categories": analysis[
                            "recommended_flaw_categories"
                        ],
                        "current_depth": analysis["depth_score"],
                    }
                )

        # Sort by potential
        opportunities.sort(key=lambda x: x["potential"], reverse=True)
        return opportunities

    def _recommend_flaws(
        self, character_analysis: dict[str, Any]
    ) -> dict[str, list[str]]:
        """Recommend specific flaws for each character"""

        recommendations = {}

        for char_name, analysis in character_analysis.items():
            if analysis["flaw_potential"] > 0.4:
                char_flaws = []

                for category in analysis["recommended_flaw_categories"]:
                    if category in self.FLAW_CATEGORIES:
                        # Pick the most suitable flaw from the category
                        category_flaws = self.FLAW_CATEGORIES[category]
                        best_flaw = max(category_flaws.items(), key=lambda x: x[1])
                        char_flaws.append(best_flaw[0])

                recommendations[char_name] = char_flaws[
                    : self.get_config_value("max_flaws_per_character", 2)
                ]

        return recommendations

    def _calculate_enhancement_confidence(
        self, character_analysis: dict[str, Any]
    ) -> float:
        """Calculate confidence for applying character flaws"""

        factors = [
            # Multiple characters with potential
            (
                len(
                    [
                        c
                        for c in character_analysis.values()
                        if c["flaw_potential"] > 0.5
                    ]
                )
                >= 2,
                0.3,
            ),
            # Low average depth
            (self._calculate_average_depth(character_analysis) < 0.6, 0.3),
            # Room for flaws
            (
                sum(len(c["existing_flaws"]) for c in character_analysis.values())
                < len(character_analysis),
                0.2,
            ),
            # Good character presence
            (any(c["total_presence"] > 10 for c in character_analysis.values()), 0.2),
        ]

        confidence = 0.0
        for condition, weight in factors:
            if condition:
                confidence += weight

        return min(confidence, 1.0)

    async def _create_flaw_generation_prompt(
        self, content: str, analysis: dict[str, Any]
    ) -> str:
        """Create specialized prompt for character flaw generation"""

        flaw_intensity = self.get_config_value("flaw_intensity", 0.6)
        integration_style = self.get_config_value("flaw_integration_style", "subtle")
        preserve_likability = self.get_config_value("preserve_likability", True)

        # Format character recommendations
        char_recommendations = []
        for char_name, char_analysis in analysis["characters"].items():
            if char_analysis["flaw_potential"] > 0.4:
                recommended_flaws = analysis["recommended_flaws"].get(char_name, [])
                char_recommendations.append(
                    f"- {char_name}: {', '.join(recommended_flaws)}"
                )

        recommendations_text = (
            "\n".join(char_recommendations)
            if char_recommendations
            else "No specific recommendations"
        )

        prompt = f"""
You are a character development expert specializing in creating realistic, relatable character flaws. Enhance the following script by adding believable character flaws that increase depth and relatability while maintaining character likability.

CURRENT SCRIPT:
{content}

CHARACTER ANALYSIS:
- Total Characters: {analysis['character_count']}
- Average Depth Score: {analysis['average_depth_score']:.1f}/1.0
- Enhancement Opportunities: {len(analysis['enhancement_opportunities'])}

RECOMMENDED CHARACTER FLAWS:
{recommendations_text}

ENHANCEMENT SETTINGS:
- Flaw Intensity: {flaw_intensity}/1.0 (subtle to moderate flaws)
- Integration Style: {integration_style}
- Preserve Likability: {'Yes' if preserve_likability else 'No'}
- Max Flaws per Character: {self.get_config_value('max_flaws_per_character', 2)}

CHARACTER FLAW GUIDELINES:
1. Add realistic, relatable flaws that make characters more human
2. Ensure flaws create opportunities for character growth
3. Integrate flaws naturally into existing dialogue and actions
4. Maintain character consistency and core personality
5. Keep characters likable despite their flaws
6. Use flaws to create internal and external conflict

FLAW INTEGRATION TECHNIQUES:
- Subtle dialogue changes that reveal character weaknesses
- Action descriptions that show behavioral patterns
- Internal thoughts or reactions that expose insecurities
- Character decisions that demonstrate poor judgment
- Relationship dynamics that highlight social flaws

TYPES OF FLAWS TO CONSIDER:
- Personality flaws: arrogance, stubbornness, perfectionism, insecurity
- Behavioral flaws: procrastination, impulsiveness, avoidance, controlling
- Emotional flaws: trust issues, fear of commitment, anger management
- Social flaws: poor boundaries, communication issues, conflict avoidance

REQUIREMENTS:
- Maintain script formatting and character voices
- Keep the original story structure and plot
- Ensure flaws feel authentic, not forced
- Create opportunities for character development
- Preserve emotional beats and relationships
- Make characters more relatable and human

Please provide the enhanced script with realistic character flaws seamlessly integrated into the narrative.
"""

        return prompt.strip()

    def _analyze_enhancement_results(
        self, original: str, enhanced: str, analysis: dict[str, Any]
    ) -> dict[str, Any]:
        """Analyze the results of flaw enhancement"""

        original_chars = self._extract_characters(original)
        enhanced_chars = self._extract_characters(enhanced)

        results = {
            "flaws_added": self._count_added_flaws(original_chars, enhanced_chars),
            "depth_improvement": self._calculate_depth_improvement(
                original_chars, enhanced_chars
            ),
            "growth_opportunities": self._count_growth_opportunities(enhanced),
            "character_preservation": self._verify_character_preservation(
                original_chars, enhanced_chars
            ),
        }

        return results

    def _count_added_flaws(self, original_chars: Dict[str, Any], enhanced_chars: Dict[str, Any]) -> int:
        """Count how many new flaws were added"""

        original_flaw_count = 0
        enhanced_flaw_count = 0

        for char_name, char_data in original_chars.items():
            original_flaw_count += len(
                self._identify_existing_flaws(
                    char_data.get("dialogue_lines", [])
                    + char_data.get("action_lines", [])
                )
            )

        for char_name, char_data in enhanced_chars.items():
            enhanced_flaw_count += len(
                self._identify_existing_flaws(
                    char_data.get("dialogue_lines", [])
                    + char_data.get("action_lines", [])
                )
            )

        return max(0, enhanced_flaw_count - original_flaw_count)

    def _calculate_depth_improvement(
        self, original_chars: dict, enhanced_chars: dict
    ) -> float:
        """Calculate improvement in character depth"""

        original_depth = self._calculate_overall_character_depth(original_chars)
        enhanced_depth = self._calculate_overall_character_depth(enhanced_chars)

        return max(0.0, enhanced_depth - original_depth)

    def _calculate_overall_character_depth(self, characters: Dict[str, Any]) -> float:
        """Calculate overall character depth for all characters"""

        if not characters:
            return 0.0

        total_depth = sum(
            self._calculate_character_depth(char_data)
            for char_data in characters.values()
        )
        return total_depth / len(characters)

    def _count_growth_opportunities(self, content: str) -> int:
        """Count potential character growth opportunities in the enhanced content"""

        growth_indicators = [
            "learns",
            "realizes",
            "overcomes",
            "grows",
            "changes",
            "understands",
            "admits",
            "faces",
            "confronts",
            "accepts",
        ]

        content_lower = content.lower()
        return sum(content_lower.count(indicator) for indicator in growth_indicators)

    def _verify_character_preservation(
        self, original_chars: dict, enhanced_chars: dict
    ) -> bool:
        """Verify that character essences were preserved"""

        # Check that major characters are still present
        original_names = set(original_chars.keys())
        enhanced_names = set(enhanced_chars.keys())

        # Should have similar character sets
        preservation_ratio = (
            len(original_names & enhanced_names) / len(original_names)
            if original_names
            else 1.0
        )

        return preservation_ratio >= 0.8

    def _calculate_dialogue_variety(self, dialogue_lines: List[str]) -> float:
        """Calculate variety in dialogue patterns"""

        if not dialogue_lines:
            return 0.0

        # Measure sentence length variety
        sentence_lengths = [len(line.split()) for line in dialogue_lines]

        if len(set(sentence_lengths)) > 1:
            variety = len(set(sentence_lengths)) / len(sentence_lengths)
        else:
            variety = 0.0

        return min(variety, 1.0)

    def _calculate_emotional_range(self, character_lines: List[str]) -> float:
        """Calculate emotional range in character expressions"""

        emotions = [
            "happy",
            "sad",
            "angry",
            "afraid",
            "excited",
            "worried",
            "surprised",
        ]
        combined_text = " ".join(character_lines).lower()

        emotion_count = sum(1 for emotion in emotions if emotion in combined_text)
        return min(emotion_count / len(emotions), 1.0)

    def _calculate_complexity_indicators(self, character_lines: List[str]) -> float:
        """Calculate complexity indicators in character content"""

        complexity_words = [
            "because",
            "however",
            "although",
            "unless",
            "while",
            "despite",
        ]
        combined_text = " ".join(character_lines).lower()

        complexity_count = sum(combined_text.count(word) for word in complexity_words)
        return min(complexity_count / 10.0, 1.0)

    def _evaluate_flaw_integration(self, content: str) -> float:
        """Evaluate how well flaws were integrated into the content"""

        integration_indicators = [
            ("struggles with", 0.2),
            ("tends to", 0.15),
            ("has difficulty", 0.2),
            ("often", 0.1),
            ("weakness", 0.15),
            ("flaw", 0.1),
            ("problem", 0.1),
        ]

        content_lower = content.lower()
        integration_score = 0.0

        for indicator, weight in integration_indicators:
            count = content_lower.count(indicator)
            integration_score += count * weight

        return min(integration_score, 1.0)
