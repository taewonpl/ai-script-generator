"""
Dialogue Enhancer Agent - Improves dialogue quality, naturalness, and character voice
"""

from typing import Any, Optional

# Import Core Module components
try:
    from ai_script_core import (
        get_service_logger,
        utc_now,
    )

    CORE_AVAILABLE = True
    logger = get_service_logger("generation-service.dialogue_enhancer_agent")
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


class DialogueEnhancerAgent(BaseSpecialAgent):
    """
    Dialogue Enhancer Agent - Specializes in improving dialogue quality and naturalness

    Capabilities:
    - Analyzes dialogue patterns and quality
    - Enhances naturalness and flow
    - Improves character voice differentiation
    - Adds subtext and emotional depth
    - Fixes dialogue-related issues (exposition, unrealistic speech, etc.)
    """

    # Dialogue quality indicators
    QUALITY_INDICATORS = {
        "natural_speech": {
            "contractions": 0.15,  # Use of contractions (don't, can't, etc.)
            "interruptions": 0.1,  # Natural interruptions and overlaps
            "hesitations": 0.1,  # Um, uh, well, etc.
            "informal_words": 0.1,  # Casual language
            "repetition": 0.05,  # Natural repetition patterns
        },
        "emotional_depth": {
            "emotion_words": 0.2,  # Words expressing emotions
            "subtext": 0.15,  # Implied meanings
            "vulnerability": 0.1,  # Moments of openness
            "conflict": 0.15,  # Emotional conflicts
            "stakes": 0.1,  # Personal stakes expressed
        },
        "character_voice": {
            "unique_phrases": 0.15,  # Character-specific expressions
            "speech_patterns": 0.15,  # Consistent speech patterns
            "vocabulary_level": 0.1,  # Appropriate vocabulary
            "background_influence": 0.1,  # Background affecting speech
        },
        "dialogue_craft": {
            "subtext": 0.2,  # What's not said
            "punchlines": 0.1,  # Memorable lines
            "rhythm": 0.15,  # Speech rhythm and pacing
            "purpose": 0.15,  # Each line serves a purpose
            "advancement": 0.1,  # Advances plot or character
        },
    }

    # Dialogue problems to fix
    DIALOGUE_PROBLEMS = {
        "exposition_dump": ["as you know", "remember when", "let me explain"],
        "unnatural_speech": ["indeed", "certainly", "shall we"],
        "repetitive_patterns": ["said", "replied", "answered"],
        "lack_subtext": ["i feel", "i think", "i believe"],
        "weak_character_voice": ["generic response", "standard reply"],
    }

    def __init__(
        self,
        provider_factory: Optional[Any] = None,
        config: Optional[dict[str, Any]] = None,
    ) -> None:
        default_config = {
            "humor_level": 0.7,  # How much humor to inject (0.0-1.0)
            "naturalness_boost": 0.8,  # How much to improve naturalness
            "character_voice_strength": 0.9,  # How distinct character voices should be
            "subtext_enhancement": 0.7,  # How much subtext to add
            "fix_exposition": True,  # Fix exposition dumps
            "enhance_emotional_depth": True,  # Add emotional depth
            "minimum_dialogue_ratio": 0.3,  # Minimum dialogue vs action ratio
        }

        if config:
            default_config.update(config)

        super().__init__(
            agent_name="dialogue_enhancer",
            capabilities=[AgentCapability.DIALOGUE_IMPROVEMENT],
            priority=AgentPriority.HIGH,
            provider_factory=provider_factory,
            config=default_config,
        )

    async def analyze_content(self, state: GenerationState) -> dict[str, Any]:
        """
        Analyze dialogue quality and identify improvement opportunities
        """

        content = state.get("styled_script") or state.get("draft_script", "")

        # Extract and analyze dialogue
        dialogue_analysis = self._extract_dialogue_data(content)

        if dialogue_analysis["dialogue_ratio"] < self.get_config_value(
            "minimum_dialogue_ratio", 0.3
        ):
            return {
                "should_enhance": False,
                "skip_reason": "Insufficient dialogue content for enhancement",
                "dialogue_ratio": dialogue_analysis["dialogue_ratio"],
            }

        # Analyze dialogue quality
        quality_analysis = self._analyze_dialogue_quality(dialogue_analysis)

        # Identify specific problems
        problems = self._identify_dialogue_problems(dialogue_analysis)

        # Assess enhancement potential
        enhancement_potential = self._assess_enhancement_potential(
            quality_analysis, problems
        )

        analysis = {
            "dialogue_data": dialogue_analysis,
            "quality_scores": quality_analysis,
            "identified_problems": problems,
            "enhancement_opportunities": self._identify_enhancement_opportunities(
                quality_analysis, problems
            ),
            "character_voice_analysis": self._analyze_character_voices(
                dialogue_analysis
            ),
            "should_enhance": enhancement_potential > 0.4,
            "enhancement_potential": enhancement_potential,
            "context": f"Found {dialogue_analysis['total_dialogue_lines']} dialogue lines with {quality_analysis['overall_quality']:.1f}/1.0 quality",
        }

        return analysis

    async def enhance_content(self, state: GenerationState) -> dict[str, Any]:
        """
        Enhance dialogue quality and naturalness
        """

        content = state.get("styled_script") or state.get("draft_script", "")
        analysis = await self.analyze_content(state)

        # Create specialized dialogue enhancement prompt
        prompt = await self._create_dialogue_enhancement_prompt(content, analysis)

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
            "dialogue_analysis": analysis,
            "problems_fixed": enhancement_analysis["problems_fixed"],
            "naturalness_improvement": enhancement_analysis["naturalness_improvement"],
            "character_voice_improvement": enhancement_analysis["voice_improvement"],
            "humor_added": enhancement_analysis["humor_added"],
            "enhancement_type": "dialogue_enhancement",
        }

        return enhancement_result

    def calculate_quality_improvement(
        self, original_content: str, enhanced_content: str
    ) -> float:
        """
        Calculate quality improvement based on dialogue enhancement metrics
        """

        original_dialogue = self._extract_dialogue_data(original_content)
        enhanced_dialogue = self._extract_dialogue_data(enhanced_content)

        original_quality = self._analyze_dialogue_quality(original_dialogue)[
            "overall_quality"
        ]
        enhanced_quality = self._analyze_dialogue_quality(enhanced_dialogue)[
            "overall_quality"
        ]

        # Factor in specific improvements
        character_voice_improvement = self._calculate_voice_improvement(
            original_dialogue, enhanced_dialogue
        )
        naturalness_improvement = self._calculate_naturalness_improvement(
            original_content, enhanced_content
        )

        # Calculate total improvement with bonuses
        base_improvement = enhanced_quality - original_quality
        voice_bonus = character_voice_improvement * 0.1  # Up to 10% bonus
        naturalness_bonus = naturalness_improvement * 0.1  # Up to 10% bonus

        total_improvement = min(base_improvement + voice_bonus + naturalness_bonus, 1.0)

        return max(total_improvement, 0.0)

    def _extract_dialogue_data(self, content: str) -> dict[str, Any]:
        """Extract dialogue data from the script content"""

        lines = content.split("\n")
        dialogue_lines = []
        character_dialogue = {}
        total_lines = 0
        current_character = None

        for line in lines:
            line = line.strip()
            total_lines += 1

            # Skip empty lines and scene headers
            if not line or line.startswith(("EXT.", "INT.", "FADE")):
                continue

            # Detect character names
            if self._is_character_name(line):
                current_character = line.strip(":").strip()
                if current_character not in character_dialogue:
                    character_dialogue[current_character] = []

            # Detect dialogue
            elif current_character and ('"' in line or "'" in line):
                dialogue_lines.append(
                    {
                        "character": current_character,
                        "text": line,
                        "line_number": total_lines,
                    }
                )
                character_dialogue[current_character].append(line)

        return {
            "total_lines": total_lines,
            "total_dialogue_lines": len(dialogue_lines),
            "dialogue_ratio": (
                len(dialogue_lines) / total_lines if total_lines > 0 else 0.0
            ),
            "character_count": len(character_dialogue),
            "dialogue_lines": dialogue_lines,
            "character_dialogue": character_dialogue,
            "average_dialogue_per_character": (
                len(dialogue_lines) / len(character_dialogue)
                if character_dialogue
                else 0
            ),
        }

    def _analyze_dialogue_quality(
        self, dialogue_data: dict[str, Any]
    ) -> dict[str, Any]:
        """Analyze the quality of dialogue using multiple metrics"""

        dialogue_lines = dialogue_data["dialogue_lines"]
        all_dialogue_text = " ".join([line["text"] for line in dialogue_lines]).lower()

        quality_scores = {}

        # Analyze each quality category
        for category, indicators in self.QUALITY_INDICATORS.items():
            category_score = 0.0

            for indicator, weight in indicators.items():
                indicator_score = self._calculate_indicator_score(
                    all_dialogue_text, indicator
                )
                category_score += indicator_score * weight

            quality_scores[category] = min(category_score, 1.0)

        # Calculate overall quality
        overall_quality = sum(quality_scores.values()) / len(quality_scores)

        quality_scores["overall_quality"] = overall_quality

        return quality_scores

    def _calculate_indicator_score(self, dialogue_text: str, indicator: str) -> float:
        """Calculate score for a specific quality indicator"""

        if indicator == "contractions":
            contractions = [
                "don't",
                "can't",
                "won't",
                "isn't",
                "aren't",
                "wasn't",
                "weren't",
                "haven't",
                "hasn't",
                "hadn't",
            ]
            count = sum(
                dialogue_text.count(contraction) for contraction in contractions
            )
            return min(count / 10.0, 1.0)

        elif indicator == "interruptions":
            interruption_markers = ["--", "...", "but-", "wait-"]
            count = sum(dialogue_text.count(marker) for marker in interruption_markers)
            return min(count / 5.0, 1.0)

        elif indicator == "hesitations":
            hesitations = ["um", "uh", "well", "you know", "i mean"]
            count = sum(dialogue_text.count(hesitation) for hesitation in hesitations)
            return min(count / 5.0, 1.0)

        elif indicator == "emotion_words":
            emotions = [
                "love",
                "hate",
                "fear",
                "angry",
                "happy",
                "sad",
                "excited",
                "worried",
                "disappointed",
            ]
            count = sum(dialogue_text.count(emotion) for emotion in emotions)
            return min(count / 10.0, 1.0)

        elif indicator == "subtext":
            subtext_markers = [
                "what i mean is",
                "you know what i'm saying",
                "if you catch my drift",
                "between the lines",
            ]
            count = sum(dialogue_text.count(marker) for marker in subtext_markers)
            return min(count / 3.0, 1.0)

        elif indicator == "punchlines":
            punchline_markers = ["!", "?!", "...", "haha", "oh snap", "seriously?"]
            count = sum(dialogue_text.count(marker) for marker in punchline_markers)
            return min(count / 5.0, 1.0)

        # Default scoring for other indicators
        return 0.5

    def _identify_dialogue_problems(
        self, dialogue_data: dict[str, Any]
    ) -> dict[str, list[dict[str, Any]]]:
        """Identify specific dialogue problems"""

        problems = {problem_type: [] for problem_type in self.DIALOGUE_PROBLEMS.keys()}

        dialogue_lines = dialogue_data["dialogue_lines"]

        for line_data in dialogue_lines:
            line_text = line_data["text"].lower()

            # Check for each problem type
            for problem_type, indicators in self.DIALOGUE_PROBLEMS.items():
                for indicator in indicators:
                    if indicator in line_text:
                        problems[problem_type].append(
                            {
                                "line_number": line_data["line_number"],
                                "character": line_data["character"],
                                "text": line_data["text"],
                                "problem_indicator": indicator,
                            }
                        )

        return problems

    def _analyze_character_voices(
        self, dialogue_data: dict[str, Any]
    ) -> dict[str, Any]:
        """Analyze character voice distinctiveness"""

        character_dialogue = dialogue_data["character_dialogue"]
        voice_analysis = {}

        for character, lines in character_dialogue.items():
            combined_text = " ".join(lines).lower()

            voice_analysis[character] = {
                "total_lines": len(lines),
                "average_length": (
                    sum(len(line.split()) for line in lines) / len(lines)
                    if lines
                    else 0
                ),
                "vocabulary_complexity": self._calculate_vocabulary_complexity(
                    combined_text
                ),
                "emotional_range": self._calculate_emotional_range(combined_text),
                "speech_patterns": self._identify_speech_patterns(combined_text),
                "distinctiveness_score": self._calculate_distinctiveness_score(
                    combined_text, character_dialogue
                ),
            }

        return voice_analysis

    def _assess_enhancement_potential(
        self, quality_analysis: dict[str, Any], problems: dict[str, Any]
    ) -> float:
        """Assess potential for dialogue enhancement"""

        factors = [
            # Low overall quality
            (quality_analysis["overall_quality"] < 0.7, 0.3),
            # Specific problems exist
            (sum(len(problem_list) for problem_list in problems.values()) > 0, 0.3),
            # Natural speech could be improved
            (quality_analysis.get("natural_speech", 0) < 0.6, 0.2),
            # Character voices need work
            (quality_analysis.get("character_voice", 0) < 0.6, 0.2),
        ]

        potential = 0.0
        for condition, weight in factors:
            if condition:
                potential += weight

        return min(potential, 1.0)

    def _identify_enhancement_opportunities(
        self, quality_analysis: dict[str, Any], problems: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """Identify specific enhancement opportunities"""

        opportunities = []

        # Quality-based opportunities
        for category, score in quality_analysis.items():
            if category != "overall_quality" and score < 0.6:
                opportunities.append(
                    {
                        "type": "quality_improvement",
                        "category": category,
                        "current_score": score,
                        "improvement_potential": 1.0 - score,
                    }
                )

        # Problem-based opportunities
        for problem_type, problem_instances in problems.items():
            if problem_instances:
                opportunities.append(
                    {
                        "type": "problem_fix",
                        "problem": problem_type,
                        "instance_count": len(problem_instances),
                        "severity": "high" if len(problem_instances) > 3 else "medium",
                    }
                )

        return opportunities

    def _is_character_name(self, line: str) -> bool:
        """Determine if a line represents a character name"""

        line = line.strip(":").strip()

        # Character name heuristics
        if (
            line.isupper()
            and len(line.split()) <= 3
            and len(line) > 1
            and not line.startswith(("EXT.", "INT.", "FADE", "CUT"))
        ):
            return True

        return False

    async def _create_dialogue_enhancement_prompt(
        self, content: str, analysis: dict[str, Any]
    ) -> str:
        """Create specialized prompt for dialogue enhancement"""

        humor_level = self.get_config_value("humor_level", 0.7)
        naturalness_boost = self.get_config_value("naturalness_boost", 0.8)
        character_voice_strength = self.get_config_value(
            "character_voice_strength", 0.9
        )

        # Format identified problems
        problems_text = []
        for problem_type, instances in analysis["identified_problems"].items():
            if instances:
                problems_text.append(
                    f"- {problem_type.replace('_', ' ').title()}: {len(instances)} instances"
                )

        problems_summary = (
            "\n".join(problems_text)
            if problems_text
            else "No major problems identified"
        )

        # Format enhancement opportunities
        opportunities_text = []
        for opp in analysis["enhancement_opportunities"][:5]:  # Top 5
            if opp["type"] == "quality_improvement":
                opportunities_text.append(
                    f"- Improve {opp['category'].replace('_', ' ')}: {opp['current_score']:.1f} → target 0.8+"
                )
            else:
                opportunities_text.append(
                    f"- Fix {opp['problem'].replace('_', ' ')}: {opp['instance_count']} instances"
                )

        opportunities_summary = (
            "\n".join(opportunities_text)
            if opportunities_text
            else "Focus on general quality improvement"
        )

        prompt = f"""
You are a dialogue specialist expert at writing natural, engaging dialogue that reveals character and advances story. Enhance the following script by improving dialogue quality, naturalness, and character voice distinctiveness.

CURRENT SCRIPT:
{content}

DIALOGUE ANALYSIS:
- Total Dialogue Lines: {analysis['dialogue_data']['total_dialogue_lines']}
- Character Count: {analysis['dialogue_data']['character_count']}
- Overall Quality Score: {analysis['quality_scores']['overall_quality']:.1f}/1.0
- Dialogue Ratio: {analysis['dialogue_data']['dialogue_ratio']:.1f}

IDENTIFIED PROBLEMS:
{problems_summary}

ENHANCEMENT OPPORTUNITIES:
{opportunities_summary}

ENHANCEMENT SETTINGS:
- Humor Level: {humor_level}/1.0 (inject appropriate humor)
- Naturalness Boost: {naturalness_boost}/1.0 (make speech more natural)
- Character Voice Strength: {character_voice_strength}/1.0 (distinct character voices)

DIALOGUE ENHANCEMENT GUIDELINES:
1. Make dialogue sound more natural and conversational
2. Give each character a distinct voice and speech pattern
3. Add subtext - characters say one thing but mean another
4. Fix exposition dumps with more natural information delivery
5. Enhance emotional depth and vulnerability
6. Add appropriate humor and memorable lines
7. Ensure every line serves a purpose (plot, character, or relationship)

SPECIFIC TECHNIQUES:
- Use contractions and informal speech patterns
- Add interruptions, hesitations, and natural speech rhythms
- Create character-specific vocabulary and phrases
- Show emotion through dialogue choices, not just words
- Use subtext to create tension and depth
- Replace "as you know" exposition with natural reveals
- Add punch lines and memorable moments
- Create speech patterns that reflect character backgrounds

DIALOGUE QUALITY CHECKLIST:
- Natural speech patterns (contractions, hesitations, interruptions)
- Distinct character voices (unique vocabulary, rhythms, perspectives)
- Emotional depth (subtext, vulnerability, stakes)
- Purpose-driven (every line advances plot or character)
- Memorable moments (punch lines, reveals, emotional beats)
- Authentic to character backgrounds and personalities

REQUIREMENTS:
- Maintain script formatting and scene structure
- Keep character personalities and relationships consistent
- Preserve the story's emotional beats and plot points
- Make dialogue feel natural and believable
- Ensure each character has a unique voice
- Add depth without losing clarity

Please provide the enhanced script with dramatically improved dialogue that sounds natural, reveals character, and engages the audience.
"""

        return prompt.strip()

    def _analyze_enhancement_results(
        self, original: str, enhanced: str, analysis: dict[str, Any]
    ) -> dict[str, Any]:
        """Analyze the results of dialogue enhancement"""

        original_dialogue = self._extract_dialogue_data(original)
        enhanced_dialogue = self._extract_dialogue_data(enhanced)

        results = {
            "problems_fixed": self._count_problems_fixed(
                original_dialogue, enhanced_dialogue
            ),
            "naturalness_improvement": self._calculate_naturalness_improvement(
                original, enhanced
            ),
            "voice_improvement": self._calculate_voice_improvement(
                original_dialogue, enhanced_dialogue
            ),
            "humor_added": self._calculate_humor_added(original, enhanced),
            "dialogue_quality_improvement": self._calculate_dialogue_quality_improvement(
                original_dialogue, enhanced_dialogue
            ),
        }

        return results

    def _count_problems_fixed(
        self, original_dialogue: dict[str, Any], enhanced_dialogue: dict[str, Any]
    ) -> int:
        """Count how many dialogue problems were fixed"""

        original_problems = self._identify_dialogue_problems(original_dialogue)
        enhanced_problems = self._identify_dialogue_problems(enhanced_dialogue)

        fixed_count = 0
        for problem_type in original_problems:
            original_count = len(original_problems[problem_type])
            enhanced_count = len(enhanced_problems[problem_type])
            fixed_count += max(0, original_count - enhanced_count)

        return fixed_count

    def _calculate_naturalness_improvement(self, original: str, enhanced: str) -> float:
        """Calculate improvement in dialogue naturalness"""

        naturalness_indicators = [
            "don't",
            "can't",
            "won't",
            "um",
            "uh",
            "well",
            "you know",
            "i mean",
        ]

        original_lower = original.lower()
        enhanced_lower = enhanced.lower()

        original_score = sum(
            original_lower.count(indicator) for indicator in naturalness_indicators
        )
        enhanced_score = sum(
            enhanced_lower.count(indicator) for indicator in naturalness_indicators
        )

        # Normalize scores
        original_normalized = min(original_score / 20.0, 1.0)
        enhanced_normalized = min(enhanced_score / 20.0, 1.0)

        return max(0.0, enhanced_normalized - original_normalized)

    def _calculate_voice_improvement(
        self, original_dialogue: dict[str, Any], enhanced_dialogue: dict[str, Any]
    ) -> float:
        """Calculate improvement in character voice distinctiveness"""

        # This is a simplified calculation - in reality, would need more sophisticated analysis
        original_characters = len(original_dialogue["character_dialogue"])
        enhanced_characters = len(enhanced_dialogue["character_dialogue"])

        if original_characters == 0:
            return 0.0

        # Assume some improvement if characters are maintained
        if enhanced_characters >= original_characters:
            return 0.2  # Base improvement for voice enhancement
        else:
            return 0.0

    def _calculate_humor_added(self, original: str, enhanced: str) -> float:
        """Calculate how much humor was added"""

        humor_indicators = [
            "haha",
            "lol",
            "funny",
            "joke",
            "laugh",
            "hilarious",
            "ridiculous",
            "!",
        ]

        original_lower = original.lower()
        enhanced_lower = enhanced.lower()

        original_humor = sum(
            original_lower.count(indicator) for indicator in humor_indicators
        )
        enhanced_humor = sum(
            enhanced_lower.count(indicator) for indicator in humor_indicators
        )

        humor_added = max(0, enhanced_humor - original_humor)
        return min(humor_added / 10.0, 1.0)  # Normalize

    def _calculate_dialogue_quality_improvement(
        self, original_dialogue: dict[str, Any], enhanced_dialogue: dict[str, Any]
    ) -> float:
        """Calculate overall dialogue quality improvement"""

        original_quality = self._analyze_dialogue_quality(original_dialogue)[
            "overall_quality"
        ]
        enhanced_quality = self._analyze_dialogue_quality(enhanced_dialogue)[
            "overall_quality"
        ]

        return max(0.0, enhanced_quality - original_quality)

    def _calculate_vocabulary_complexity(self, text: str) -> float:
        """Calculate vocabulary complexity score"""

        complex_words = [
            "although",
            "however",
            "nevertheless",
            "consequently",
            "furthermore",
        ]
        word_count = len(text.split())

        if word_count == 0:
            return 0.0

        complex_count = sum(text.count(word) for word in complex_words)
        return min(complex_count / word_count * 10, 1.0)  # Normalize

    def _calculate_emotional_range(self, text: str) -> float:
        """Calculate emotional range in text"""

        emotions = [
            "happy",
            "sad",
            "angry",
            "afraid",
            "excited",
            "worried",
            "love",
            "hate",
        ]
        emotion_count = sum(1 for emotion in emotions if emotion in text)

        return emotion_count / len(emotions)

    def _identify_speech_patterns(self, text: str) -> list[str]:
        """Identify speech patterns in character dialogue"""

        patterns = []

        # Common speech patterns
        if "you know" in text:
            patterns.append("filler_phrases")
        if text.count("really") > 2:
            patterns.append("emphasis_repetition")
        if "..." in text:
            patterns.append("trailing_off")
        if "!" in text:
            patterns.append("exclamatory")

        return patterns

    def _calculate_distinctiveness_score(
        self, character_text: str, all_character_dialogue: dict[str, list[str]]
    ) -> float:
        """Calculate how distinct this character's voice is"""

        # Simplified distinctiveness calculation
        # In reality, would compare vocabulary, sentence patterns, etc.

        character_length = len(character_text)
        total_length = sum(
            len(" ".join(lines)) for lines in all_character_dialogue.values()
        )

        if total_length == 0:
            return 0.0

        # Base distinctiveness on relative presence and unique words
        presence_ratio = character_length / total_length
        uniqueness_factor = 0.5  # Simplified - would need actual uniqueness analysis

        return min(presence_ratio * 2 + uniqueness_factor, 1.0)
