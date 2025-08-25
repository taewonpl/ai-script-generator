"""
Special Agent prompts for GPT - Specialized enhancement tasks
"""

from enum import Enum

from .base_prompt import BasePromptTemplate, PromptContext, PromptType, ScriptType


class SpecialAgentType(str, Enum):
    """Types of special agents"""

    PLOT_TWISTER = "plot_twister"
    FLAW_GENERATOR = "flaw_generator"
    DIALOGUE_ENHANCER = "dialogue_enhancer"
    TENSION_BUILDER = "tension_builder"
    EMOTION_AMPLIFIER = "emotion_amplifier"
    CONFLICT_INTENSIFIER = "conflict_intensifier"
    HUMOR_INJECTOR = "humor_injector"
    PACING_OPTIMIZER = "pacing_optimizer"


class SpecialAgentPrompts(BasePromptTemplate):
    """
    Specialized prompts for GPT as Special Agent nodes
    Role: 특수 목적별 스크립트 개선 - Plot Twister, Flaw Generator, Dialogue Enhancer
    """

    def __init__(
        self, agent_type: SpecialAgentType = SpecialAgentType.DIALOGUE_ENHANCER
    ):
        super().__init__(PromptType.SPECIAL_AGENT)
        self.agent_type = agent_type

        # Define agent specializations
        self.agent_configs = {
            SpecialAgentType.PLOT_TWISTER: {
                "expertise": "Plot twist creation and narrative surprise elements",
                "focus": "Adding unexpected but logical plot developments",
                "constraints": "Twists must feel surprising yet inevitable in hindsight",
            },
            SpecialAgentType.FLAW_GENERATOR: {
                "expertise": "Character flaw development and realistic imperfection creation",
                "focus": "Creating compelling character weaknesses and growth opportunities",
                "constraints": "Flaws must serve story purpose and character development",
            },
            SpecialAgentType.DIALOGUE_ENHANCER: {
                "expertise": "Dialogue quality improvement and conversational realism",
                "focus": "Making dialogue more natural, engaging, and character-specific",
                "constraints": "Maintain character voice while improving clarity and impact",
            },
            SpecialAgentType.TENSION_BUILDER: {
                "expertise": "Dramatic tension creation and suspense management",
                "focus": "Increasing emotional stakes and audience engagement",
                "constraints": "Build tension without disrupting story flow",
            },
            SpecialAgentType.EMOTION_AMPLIFIER: {
                "expertise": "Emotional impact enhancement and feeling intensification",
                "focus": "Deepening emotional resonance and audience connection",
                "constraints": "Amplify emotions authentically without melodrama",
            },
            SpecialAgentType.CONFLICT_INTENSIFIER: {
                "expertise": "Conflict escalation and dramatic opposition enhancement",
                "focus": "Strengthening character conflicts and story obstacles",
                "constraints": "Intensify conflicts while maintaining character believability",
            },
            SpecialAgentType.HUMOR_INJECTOR: {
                "expertise": "Humor integration and comedic timing optimization",
                "focus": "Adding appropriate humor and lightening serious moments",
                "constraints": "Humor must fit tone and not undermine dramatic moments",
            },
            SpecialAgentType.PACING_OPTIMIZER: {
                "expertise": "Story pacing adjustment and rhythm optimization",
                "focus": "Balancing fast and slow moments for optimal engagement",
                "constraints": "Maintain story structure while improving flow",
            },
        }

    def create_system_prompt(self, context: PromptContext) -> str:
        """Create system prompt for GPT as specialized agent"""

        agent_config = self.agent_configs[self.agent_type]

        system_prompt = f"""You are a specialized script enhancement agent with expertise in {agent_config['expertise']}. Your role is to take an already well-structured and styled script and apply your specific enhancement techniques to elevate its quality in your area of specialization.

AGENT SPECIALIZATION: {self.agent_type.value.replace('_', ' ').title()}
CORE EXPERTISE: {agent_config['expertise']}
PRIMARY FOCUS: {agent_config['focus']}
KEY CONSTRAINTS: {agent_config['constraints']}

ENHANCEMENT PRINCIPLES:
1. Preserve the existing story structure and character arcs
2. Maintain the established style and tone from the stylist
3. Apply your specialized techniques strategically, not uniformly
4. Ensure all enhancements serve the overall narrative purpose
5. Keep modifications consistent with character personalities
6. Enhance without overwhelming or disrupting the existing quality

FORBIDDEN ACTIONS:
- Do not change the fundamental plot structure
- Do not alter character relationships or main story beats
- Do not modify the established tone or style significantly
- Do not add elements that contradict existing character development
- Do not create inconsistencies with previously established facts

QUALITY STANDARDS:
Your enhancements should feel like natural improvements that make the script better without drawing attention to the fact that they were added. The audience should feel the improvement in engagement, emotion, or entertainment value without noticing the mechanical changes.

OUTPUT REQUIREMENTS:
Provide the enhanced script with clear indicators of what you've improved and why. Focus on your specialized area while maintaining harmony with all other script elements."""

        return system_prompt.strip()

    def create_user_prompt(self, context: PromptContext) -> str:
        """Create user prompt with styled script and enhancement requirements"""

        self._validate_context(context)

        # Get the styled script from previous nodes
        styled_script = context.additional_context.get("styled_script", "")
        architect_structure = context.additional_context.get("architect_structure", "")

        if not styled_script:
            styled_script = "[이전 노드에서 스타일링된 스크립트가 제공되지 않았습니다.]"

        # Format RAG context for enhancement guidance
        rag_section = ""
        if context.rag_context:
            rag_section = f"""
REFERENCE MATERIALS:
{context.rag_context[:2000]}

Use these references to understand the project's context and ensure your enhancements align with established patterns and expectations.
"""

        # Get agent-specific enhancement instructions
        enhancement_instructions = self._get_enhancement_instructions(context)

        project_info = f"""
PROJECT INFORMATION:
- Title: {context.title}
- Description: {context.description}
- Script Type: {context.script_type.value}
- Target Audience: {context.target_audience}
- Channel Style: {context.channel_style}
- Enhancement Agent: {self.agent_type.value.replace('_', ' ').title()}"""

        user_prompt = f"""{project_info}

{rag_section}

CURRENT SCRIPT TO ENHANCE:
{styled_script}

ORIGINAL STRUCTURAL FOUNDATION:
{architect_structure}

{enhancement_instructions}

ENHANCEMENT TASK:
Apply your specialized {self.agent_type.value.replace('_', ' ')} techniques to improve this script. Focus specifically on your area of expertise while maintaining all existing quality and consistency.

QUALITY CHECKPOINTS:
□ Structure preservation: Original story beats maintained
□ Character consistency: All character voices and arcs preserved
□ Style harmony: Enhancements blend seamlessly with existing style
□ Narrative flow: Improvements enhance rather than disrupt pacing
□ Audience engagement: Changes increase entertainment/emotional value
□ Technical quality: All modifications are professionally executed

Provide the enhanced script with a brief summary of the improvements made."""

        return user_prompt.strip()

    def _get_enhancement_instructions(self, context: PromptContext) -> str:
        """Get specific enhancement instructions based on agent type"""

        instructions = {
            SpecialAgentType.PLOT_TWISTER: f"""
PLOT TWIST ENHANCEMENT INSTRUCTIONS:

Your mission: Add unexpected but logical plot developments that surprise audiences while feeling inevitable.

Enhancement Strategies:
1. Identify moments where a revelation could recontextualize earlier events
2. Look for character motivations that could be more complex than they appear
3. Find opportunities for information to be revealed that changes story meaning
4. Create "aha moments" where pieces fall into place retrospectively

Twist Quality Standards:
- Surprises feel earned, not arbitrary
- Earlier scenes gain new meaning when twist is revealed
- Character behavior remains consistent with twist revelation
- Twist serves the overall story theme and message

Focus Areas for {context.script_type.value}:
{self._get_twist_focus_for_type(context.script_type)}""",
            SpecialAgentType.FLAW_GENERATOR: f"""
CHARACTER FLAW ENHANCEMENT INSTRUCTIONS:

Your mission: Develop realistic character imperfections that create growth opportunities and story conflict.

Enhancement Strategies:
1. Identify where characters seem too perfect or one-dimensional
2. Add flaws that logically connect to character backgrounds
3. Create flaws that generate natural story conflicts
4. Ensure flaws provide clear character growth arcs

Flaw Development Standards:
- Flaws feel human and relatable, not cartoon-like
- Character weaknesses create meaningful story obstacles
- Flaws have logical roots in character history/personality
- Growth opportunities are built into flaw structure

Character Types for {context.script_type.value}:
{self._get_flaw_focus_for_type(context.script_type)}""",
            SpecialAgentType.DIALOGUE_ENHANCER: f"""
DIALOGUE ENHANCEMENT INSTRUCTIONS:

Your mission: Improve conversational quality, naturalism, and character-specific voice.

Enhancement Strategies:
1. Replace exposition-heavy dialogue with natural conversation
2. Add subtext and layered meaning to important exchanges
3. Improve rhythm and flow of conversational patterns
4. Strengthen character voice distinctions

Dialogue Quality Standards:
- Conversations sound like real people talking
- Each character has a distinct speaking pattern
- Dialogue advances plot while revealing character
- Emotional beats land with proper timing and word choice

Dialogue Style for {context.script_type.value}:
{self._get_dialogue_focus_for_type(context.script_type)}""",
            SpecialAgentType.TENSION_BUILDER: f"""
TENSION BUILDING ENHANCEMENT INSTRUCTIONS:

Your mission: Increase dramatic tension and audience engagement through strategic enhancement.

Enhancement Strategies:
1. Identify moments where stakes could be raised
2. Add time pressure or urgency where appropriate
3. Create moments of uncertainty about outcomes
4. Build anticipation for key story events

Tension Standards:
- Tension feels organic to the story situation
- Audience investment increases without manipulation
- Relief and escalation are properly balanced
- Tension serves character development and plot

Tension Focus for {context.script_type.value}:
{self._get_tension_focus_for_type(context.script_type)}""",
            SpecialAgentType.EMOTION_AMPLIFIER: f"""
EMOTIONAL AMPLIFICATION INSTRUCTIONS:

Your mission: Deepen emotional resonance and strengthen audience connection.

Enhancement Strategies:
1. Identify emotionally significant moments needing amplification
2. Add emotional layers to character interactions
3. Strengthen emotional payoffs for character arcs
4. Create more visceral emotional experiences

Emotional Standards:
- Emotions feel authentic and earned
- Amplification doesn't become melodramatic
- Emotional beats connect to overall story themes
- Character emotional journeys are strengthened

Emotional Focus for {context.script_type.value}:
{self._get_emotion_focus_for_type(context.script_type)}""",
            SpecialAgentType.CONFLICT_INTENSIFIER: f"""
CONFLICT INTENSIFICATION INSTRUCTIONS:

Your mission: Strengthen character conflicts and story obstacles for maximum dramatic impact.

Enhancement Strategies:
1. Escalate existing conflicts to higher stakes
2. Add personal dimensions to abstract conflicts
3. Create opposing forces that test character resolve
4. Ensure conflicts drive character growth

Conflict Standards:
- Intensification feels natural, not forced
- Conflicts have clear personal stakes for characters
- Opposition challenges characters' core beliefs/values
- Resolution opportunities require genuine character growth

Conflict Focus for {context.script_type.value}:
{self._get_conflict_focus_for_type(context.script_type)}""",
            SpecialAgentType.HUMOR_INJECTOR: f"""
HUMOR INJECTION INSTRUCTIONS:

Your mission: Add appropriate humor that enhances entertainment value without undermining dramatic moments.

Enhancement Strategies:
1. Find natural opportunities for character-based humor
2. Add comedic relief that doesn't break tension inappropriately
3. Use humor to reveal character personality and relationships
4. Balance comedy with overall tone requirements

Humor Standards:
- Comedy fits the established tone and style
- Humor emerges from character and situation, not forced jokes
- Comedic timing enhances rather than disrupts story flow
- Humor serves character development or relationship building

Humor Style for {context.script_type.value}:
{self._get_humor_focus_for_type(context.script_type)}""",
            SpecialAgentType.PACING_OPTIMIZER: f"""
PACING OPTIMIZATION INSTRUCTIONS:

Your mission: Adjust story rhythm and flow for optimal audience engagement.

Enhancement Strategies:
1. Balance fast and slow moments for variety
2. Ensure scene transitions maintain momentum
3. Adjust information revelation timing
4. Optimize emotional beat spacing

Pacing Standards:
- Rhythm changes serve story and audience engagement
- Scene flow feels natural and purposeful
- Information is revealed at optimal moments
- Emotional peaks and valleys are well-balanced

Pacing Focus for {context.script_type.value}:
{self._get_pacing_focus_for_type(context.script_type)}""",
        }

        return instructions.get(
            self.agent_type, "Apply your specialized enhancement techniques."
        )

    def _get_twist_focus_for_type(self, script_type: ScriptType) -> str:
        """Get plot twist focus based on script type"""
        focus_map = {
            ScriptType.DRAMA: "Character secret revelations, hidden relationships, past event recontextualization",
            ScriptType.THRILLER: "Identity reveals, betrayal twists, conspiracy unveiling",
            ScriptType.COMEDY: "Misunderstanding reveals, identity mix-ups, situational reversals",
            ScriptType.DOCUMENTARY: "New evidence, expert opinion shifts, fact reinterpretation",
        }
        return focus_map.get(
            script_type, "Character motivation reveals, situation reframing"
        )

    def _get_flaw_focus_for_type(self, script_type: ScriptType) -> str:
        """Get character flaw focus based on script type"""
        focus_map = {
            ScriptType.DRAMA: "Deep psychological flaws, moral compromises, emotional wounds",
            ScriptType.COMEDY: "Quirky personality traits, social awkwardness, harmless obsessions",
            ScriptType.THRILLER: "Trust issues, paranoia, dangerous overconfidence",
            ScriptType.DOCUMENTARY: "Subject bias, expert limitations, perspective blind spots",
        }
        return focus_map.get(
            script_type, "Relatable human weaknesses, growth opportunities"
        )

    def _get_dialogue_focus_for_type(self, script_type: ScriptType) -> str:
        """Get dialogue enhancement focus based on script type"""
        focus_map = {
            ScriptType.DRAMA: "Emotional subtext, layered meanings, authentic conflict expression",
            ScriptType.COMEDY: "Comedic timing, character humor, witty exchanges",
            ScriptType.THRILLER: "Tension-building conversation, information reveals, suspenseful exchanges",
            ScriptType.DOCUMENTARY: "Clear narration, expert interview enhancement, story narration",
        }
        return focus_map.get(
            script_type, "Natural conversation flow, character voice distinction"
        )

    def _get_tension_focus_for_type(self, script_type: ScriptType) -> str:
        """Get tension building focus based on script type"""
        focus_map = {
            ScriptType.DRAMA: "Emotional stakes, relationship tension, internal conflict pressure",
            ScriptType.THRILLER: "Suspense building, danger escalation, mystery tension",
            ScriptType.COMEDY: "Anticipation building, comedic tension, awkward situation pressure",
            ScriptType.DOCUMENTARY: "Information tension, revelation anticipation, argument building",
        }
        return focus_map.get(script_type, "Audience engagement, stakes escalation")

    def _get_emotion_focus_for_type(self, script_type: ScriptType) -> str:
        """Get emotional amplification focus based on script type"""
        focus_map = {
            ScriptType.DRAMA: "Deep emotional connection, cathartic moments, heartfelt exchanges",
            ScriptType.COMEDY: "Joy amplification, heartwarming moments, positive emotions",
            ScriptType.THRILLER: "Fear and anxiety, relief moments, triumph emotions",
            ScriptType.DOCUMENTARY: "Empathy building, inspiration, educational satisfaction",
        }
        return focus_map.get(
            script_type, "Authentic emotional depth, audience connection"
        )

    def _get_conflict_focus_for_type(self, script_type: ScriptType) -> str:
        """Get conflict intensification focus based on script type"""
        focus_map = {
            ScriptType.DRAMA: "Internal conflicts, moral dilemmas, relationship struggles",
            ScriptType.THRILLER: "Life-or-death stakes, pursuit conflicts, betrayal confrontations",
            ScriptType.COMEDY: "Misunderstanding conflicts, social conflicts, comedic obstacles",
            ScriptType.DOCUMENTARY: "Ideological conflicts, fact vs. opinion, perspective clashes",
        }
        return focus_map.get(
            script_type, "Character-driven conflicts, meaningful opposition"
        )

    def _get_humor_focus_for_type(self, script_type: ScriptType) -> str:
        """Get humor injection focus based on script type"""
        focus_map = {
            ScriptType.DRAMA: "Subtle humor for relief, character quirks, lightening heavy moments",
            ScriptType.COMEDY: "Enhanced comedic moments, character-based humor, situation comedy",
            ScriptType.THRILLER: "Dark humor, tension-breaking moments, ironic observations",
            ScriptType.DOCUMENTARY: "Gentle humor, expert personality, educational entertainment",
        }
        return focus_map.get(
            script_type, "Appropriate humor that enhances rather than disrupts"
        )

    def _get_pacing_focus_for_type(self, script_type: ScriptType) -> str:
        """Get pacing optimization focus based on script type"""
        focus_map = {
            ScriptType.DRAMA: "Emotional beat timing, revelation pacing, character development flow",
            ScriptType.THRILLER: "Suspense building rhythm, action pacing, tension escalation timing",
            ScriptType.COMEDY: "Comedic timing, setup-punchline rhythm, energy management",
            ScriptType.DOCUMENTARY: "Information flow, narrative progression, educational pacing",
        }
        return focus_map.get(
            script_type, "Story rhythm optimization, audience engagement flow"
        )

    def create_multi_agent_prompt(
        self, context: PromptContext, agent_types: list[SpecialAgentType]
    ) -> str:
        """Create prompt for multiple special agent enhancements"""

        base_prompt = self.create_user_prompt(context)

        multi_agent_section = f"""
MULTI-AGENT ENHANCEMENT TASK:

Apply the following specialized enhancements in order:
{chr(10).join([f'{i+1}. {agent_type.value.replace("_", " ").title()}' for i, agent_type in enumerate(agent_types)])}

Enhancement Coordination:
- Apply each enhancement while preserving previous improvements
- Ensure all enhancements work together harmoniously
- Maintain consistency across all enhancement layers
- Prioritize overall script quality over individual technique showcasing

For each enhancement, provide:
1. Specific improvements made
2. Reasoning for enhancement choices
3. How it builds on previous enhancements
4. Quality assurance verification"""

        return base_prompt + multi_agent_section
