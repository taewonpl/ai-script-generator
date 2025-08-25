"""
Scene Visualizer Agent - Enhances visual storytelling and scene descriptions
"""

from typing import Any

# Import Core Module components
try:
    from ai_script_core import (
        get_service_logger,
        utc_now,
    )

    CORE_AVAILABLE = True
    logger = get_service_logger("generation-service.scene_visualizer_agent")
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


class SceneVisualizerAgent(BaseSpecialAgent):
    """
    Scene Visualizer Agent - Enhances visual storytelling and cinematic descriptions

    Capabilities:
    - Analyzes visual description density and quality
    - Enhances scene setting and atmosphere
    - Improves cinematic visualization
    - Adds sensory details and immersive elements
    - Optimizes for visual media adaptation
    """

    def __init__(self, provider_factory=None, config: dict[str, Any] = None):
        default_config = {
            "detail_level": 0.7,  # How much visual detail to add
            "cinematic_style": True,  # Use cinematic language
            "sensory_enhancement": 0.8,  # Add sensory details
            "atmosphere_boost": 0.9,  # Enhance atmospheric descriptions
            "visual_metaphors": True,  # Use visual metaphors
            "color_palette": True,  # Include color descriptions
        }

        if config:
            default_config.update(config)

        super().__init__(
            agent_name="scene_visualizer",
            capabilities=[AgentCapability.VISUAL_ENHANCEMENT],
            priority=AgentPriority.MEDIUM,
            provider_factory=provider_factory,
            config=default_config,
        )

    async def analyze_content(self, state: GenerationState) -> dict[str, Any]:
        """Analyze visual description quality and identify enhancement opportunities"""

        content = state.get("styled_script") or state.get("draft_script", "")

        visual_analysis = {
            "scene_descriptions": self._extract_scene_descriptions(content),
            "visual_density": self._calculate_visual_density(content),
            "atmospheric_quality": self._assess_atmospheric_quality(content),
            "sensory_elements": self._count_sensory_elements(content),
            "cinematic_potential": self._assess_cinematic_potential(content),
            "enhancement_opportunities": self._identify_visual_opportunities(content),
        }

        should_enhance = (
            visual_analysis["visual_density"] < 0.6
            or visual_analysis["atmospheric_quality"] < 0.5
            or len(visual_analysis["enhancement_opportunities"]) > 2
        )

        visual_analysis.update(
            {
                "should_enhance": should_enhance,
                "enhancement_confidence": self._calculate_visual_confidence(
                    visual_analysis
                ),
                "context": f"Visual density {visual_analysis['visual_density']:.1f} with {len(visual_analysis['enhancement_opportunities'])} opportunities",
            }
        )

        return visual_analysis

    async def enhance_content(self, state: GenerationState) -> dict[str, Any]:
        """Enhance visual storytelling and scene descriptions"""

        content = state.get("styled_script") or state.get("draft_script", "")
        analysis = await self.analyze_content(state)

        prompt = await self._create_visual_enhancement_prompt(content, analysis)
        ai_result = await self.execute_ai_enhancement(prompt, max_tokens=4000)

        quality_improvement = self.calculate_quality_improvement(
            content, ai_result["enhanced_content"]
        )

        enhancement_result = {
            **ai_result,
            "quality_improvement": quality_improvement,
            "visual_analysis": analysis,
            "visual_elements_added": self._count_visual_improvements(
                content, ai_result["enhanced_content"]
            ),
            "enhancement_type": "visual_scene_enhancement",
        }

        return enhancement_result

    def calculate_quality_improvement(
        self, original_content: str, enhanced_content: str
    ) -> float:
        """Calculate visual quality improvement"""

        original_visual_score = self._calculate_overall_visual_quality(original_content)
        enhanced_visual_score = self._calculate_overall_visual_quality(enhanced_content)

        return max(0.0, enhanced_visual_score - original_visual_score)

    def _extract_scene_descriptions(self, content: str) -> list[dict[str, Any]]:
        """Extract scene descriptions from script"""

        scenes = []
        lines = content.split("\n")

        for i, line in enumerate(lines):
            line = line.strip()

            if line.startswith(("EXT.", "INT.")):
                scenes.append(
                    {
                        "line_number": i,
                        "header": line,
                        "type": "exterior" if line.startswith("EXT.") else "interior",
                        "description_quality": self._assess_scene_header_quality(line),
                    }
                )

        return scenes

    def _calculate_visual_density(self, content: str) -> float:
        """Calculate density of visual descriptions"""

        visual_words = [
            "bright",
            "dark",
            "colorful",
            "vivid",
            "shadowy",
            "gleaming",
            "massive",
            "tiny",
            "towering",
            "sprawling",
            "narrow",
            "wide",
            "rough",
            "smooth",
            "jagged",
            "polished",
            "weathered",
            "pristine",
        ]

        content_lower = content.lower()
        total_words = len(content.split())

        if total_words == 0:
            return 0.0

        visual_count = sum(content_lower.count(word) for word in visual_words)
        return min(visual_count / total_words * 50, 1.0)  # Normalize

    def _assess_atmospheric_quality(self, content: str) -> float:
        """Assess atmospheric description quality"""

        atmosphere_indicators = [
            "atmosphere",
            "mood",
            "feeling",
            "tension",
            "energy",
            "warmth",
            "coldness",
            "eeriness",
            "comfort",
            "unease",
        ]

        content_lower = content.lower()
        atmosphere_score = sum(
            content_lower.count(indicator) for indicator in atmosphere_indicators
        )

        return min(atmosphere_score / 10.0, 1.0)

    def _count_sensory_elements(self, content: str) -> dict[str, int]:
        """Count sensory elements in descriptions"""

        sensory_elements = {
            "visual": ["see", "look", "watch", "bright", "dark", "color"],
            "auditory": ["hear", "sound", "noise", "quiet", "loud", "whisper"],
            "tactile": ["feel", "touch", "rough", "smooth", "warm", "cold"],
            "olfactory": ["smell", "scent", "aroma", "fragrance", "odor"],
            "gustatory": ["taste", "sweet", "bitter", "sour", "salty"],
        }

        content_lower = content.lower()
        counts = {}

        for sense, words in sensory_elements.items():
            counts[sense] = sum(content_lower.count(word) for word in words)

        return counts

    def _assess_cinematic_potential(self, content: str) -> float:
        """Assess potential for cinematic adaptation"""

        cinematic_elements = [
            "camera",
            "shot",
            "angle",
            "close-up",
            "wide",
            "zoom",
            "cut",
            "fade",
            "dissolve",
            "montage",
            "sequence",
        ]

        content_lower = content.lower()
        cinematic_count = sum(
            content_lower.count(element) for element in cinematic_elements
        )

        return min(cinematic_count / 5.0, 1.0)

    def _identify_visual_opportunities(self, content: str) -> list[dict[str, Any]]:
        """Identify opportunities for visual enhancement"""

        opportunities = []
        lines = content.split("\n")

        for i, line in enumerate(lines):
            line = line.strip()

            # Scene headers that could be more descriptive
            if line.startswith(("EXT.", "INT.")) and len(line.split()) < 4:
                opportunities.append(
                    {
                        "line_number": i,
                        "type": "scene_header_expansion",
                        "current": line,
                        "potential": "Add time, weather, and atmospheric details",
                    }
                )

            # Action lines that could be more visual
            elif (
                not line.startswith(("EXT.", "INT.", "FADE"))
                and not line.isupper()
                and len(line) > 10
                and '"' not in line
            ):
                visual_words = ["bright", "dark", "large", "small", "beautiful", "ugly"]
                if not any(word in line.lower() for word in visual_words):
                    opportunities.append(
                        {
                            "line_number": i,
                            "type": "action_visualization",
                            "current": line,
                            "potential": "Add visual and sensory details",
                        }
                    )

        return opportunities

    def _calculate_visual_confidence(self, analysis: dict[str, Any]) -> float:
        """Calculate confidence for visual enhancement"""

        factors = [
            (analysis["visual_density"] < 0.5, 0.3),
            (analysis["atmospheric_quality"] < 0.4, 0.3),
            (len(analysis["enhancement_opportunities"]) > 3, 0.2),
            (sum(analysis["sensory_elements"].values()) < 5, 0.2),
        ]

        confidence = 0.0
        for condition, weight in factors:
            if condition:
                confidence += weight

        return min(confidence, 1.0)

    async def _create_visual_enhancement_prompt(
        self, content: str, analysis: dict[str, Any]
    ) -> str:
        """Create prompt for visual enhancement"""

        detail_level = self.get_config_value("detail_level", 0.7)
        opportunities_count = len(analysis["enhancement_opportunities"])

        prompt = f"""
You are a visual storytelling expert specializing in cinematic scene descriptions. Enhance the following script by adding vivid, immersive visual details that bring scenes to life and improve cinematic potential.

CURRENT SCRIPT:
{content}

VISUAL ANALYSIS:
- Visual Density: {analysis['visual_density']:.1f}/1.0
- Atmospheric Quality: {analysis['atmospheric_quality']:.1f}/1.0
- Enhancement Opportunities: {opportunities_count}
- Cinematic Potential: {analysis['cinematic_potential']:.1f}/1.0

ENHANCEMENT SETTINGS:
- Detail Level: {detail_level}/1.0
- Cinematic Style: {self.get_config_value('cinematic_style', True)}
- Sensory Enhancement: {self.get_config_value('sensory_enhancement', 0.8)}

VISUAL ENHANCEMENT GUIDELINES:
1. Enhance scene headers with time, weather, and atmospheric details
2. Add vivid visual descriptions to action lines
3. Include sensory details (sight, sound, touch, smell)
4. Create immersive atmosphere and mood
5. Use cinematic language and visual metaphors
6. Add color, lighting, and spatial descriptions
7. Enhance setting details that support story mood

TECHNIQUES:
- Expand scene headers: "EXT. COFFEE SHOP" → "EXT. COFFEE SHOP - MORNING (Golden sunlight streams through large windows)"
- Add atmospheric details: Weather, lighting, ambient sounds
- Include character visual details: Clothing, expressions, body language
- Describe environments: Architecture, furniture, objects, textures
- Use visual metaphors and symbolic elements
- Create visual rhythm and pacing through descriptions

REQUIREMENTS:
- Maintain script formatting and structure
- Keep all dialogue and character actions intact
- Enhance without overwriting the core story
- Use professional screenwriting style
- Make scenes more cinematic and visually engaging

Please provide the enhanced script with rich visual storytelling that brings every scene to vivid life.
"""

        return prompt.strip()

    def _calculate_overall_visual_quality(self, content: str) -> float:
        """Calculate overall visual quality score"""

        factors = [
            ("visual_density", self._calculate_visual_density(content), 0.3),
            ("atmospheric_quality", self._assess_atmospheric_quality(content), 0.25),
            (
                "sensory_richness",
                sum(self._count_sensory_elements(content).values()) / 20.0,
                0.25,
            ),
            ("cinematic_potential", self._assess_cinematic_potential(content), 0.2),
        ]

        total_score = 0.0
        for name, score, weight in factors:
            total_score += min(score, 1.0) * weight

        return min(total_score, 1.0)

    def _count_visual_improvements(self, original: str, enhanced: str) -> int:
        """Count visual improvements made"""

        original_visual_words = self._count_visual_descriptors(original)
        enhanced_visual_words = self._count_visual_descriptors(enhanced)

        return max(0, enhanced_visual_words - original_visual_words)

    def _count_visual_descriptors(self, content: str) -> int:
        """Count visual descriptor words"""

        descriptors = [
            "bright",
            "dark",
            "vivid",
            "colorful",
            "shadowy",
            "gleaming",
            "massive",
            "tiny",
            "beautiful",
            "ugly",
            "elegant",
            "rough",
            "smooth",
            "jagged",
            "polished",
            "weathered",
            "atmospheric",
            "moody",
            "dramatic",
            "serene",
            "chaotic",
            "peaceful",
        ]

        content_lower = content.lower()
        return sum(content_lower.count(descriptor) for descriptor in descriptors)

    def _assess_scene_header_quality(self, header: str) -> float:
        """Assess quality of a scene header"""

        # Basic scene header vs detailed one
        words = header.split()

        # More words generally means more detail
        word_score = min(len(words) / 8.0, 0.6)

        # Check for time indicators
        time_indicators = ["morning", "day", "evening", "night", "dawn", "dusk"]
        time_score = (
            0.2
            if any(indicator in header.lower() for indicator in time_indicators)
            else 0.0
        )

        # Check for weather/atmosphere
        atmosphere_indicators = ["sunny", "rainy", "stormy", "foggy", "bright", "dark"]
        atmosphere_score = (
            0.2
            if any(indicator in header.lower() for indicator in atmosphere_indicators)
            else 0.0
        )

        return word_score + time_score + atmosphere_score
