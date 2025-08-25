"""
Architect prompts for Claude - Structural and logical script design
"""

from typing import Any

from .base_prompt import BasePromptTemplate, PromptContext, PromptType, ScriptType


class ArchitectPrompts(BasePromptTemplate):
    """
    Specialized prompts for Claude as the Architect node
    Role: 논리적, 구조적 스크립트 생성 - 구조적 완성도에만 집중
    """

    def __init__(self):
        super().__init__(PromptType.ARCHITECT)

    def create_system_prompt(self, context: PromptContext) -> str:
        """Create system prompt for Claude as script architect"""

        script_guidance = self._get_script_type_guidance(context.script_type)

        system_prompt = f"""You are a professional script architect with expertise in narrative structure and storytelling logic. Your primary responsibility is to create the structural foundation of scripts with perfect logical coherence.

CORE RESPONSIBILITIES:
1. Design three-act story structure with clear progression
2. Develop character arcs with logical motivation
3. Create scene-by-scene breakdown with narrative purpose
4. Establish plot consistency and story logic
5. Plan dramatic tension and pacing structure

CRITICAL CONSTRAINTS:
- Focus ONLY on structural completeness and narrative logic
- Do NOT apply specific writing styles or channel branding
- Do NOT write actual dialogue or scene content
- Do NOT add stylistic flourishes or tone adjustments
- Create the blueprint that others will style and enhance

SCRIPT TYPE GUIDANCE:
{script_guidance}

OUTPUT REQUIREMENTS:
Provide a comprehensive structural blueprint including:
1. Three-act breakdown with act transitions
2. Character development trajectory for each main character
3. Scene-by-scene outline with narrative purpose
4. Plot point identification and logical connections
5. Pacing and tension curve planning
6. Structural consistency recommendations

Your output will be used by specialized agents who will:
- Apply channel-specific styling (handled by Stylist)
- Add special elements and effects (handled by Special Agent)
- Refine dialogue and content (handled by downstream nodes)

Focus exclusively on creating a logically sound, structurally complete foundation."""

        return system_prompt.strip()

    def create_user_prompt(self, context: PromptContext) -> str:
        """Create user prompt with project details and RAG context"""

        self._validate_context(context)

        # Format RAG context if available
        rag_section = ""
        if context.rag_context:
            rag_section = self._format_rag_context(context.rag_context, max_length=3000)

        # Build project information section
        project_info = f"""
PROJECT INFORMATION:
- Title: {context.title}
- Description: {context.description}
- Script Type: {context.script_type.value}
- Target Audience: {context.target_audience}"""

        if context.project_id:
            project_info += f"\n- Project ID: {context.project_id}"
        if context.episode_id:
            project_info += f"\n- Episode ID: {context.episode_id}"

        # Create the main prompt
        user_prompt = f"""{project_info}

{rag_section}

ARCHITECTURAL TASK:
Create a comprehensive structural blueprint for this script. Design the narrative architecture that will serve as the foundation for all subsequent development.

REQUIRED STRUCTURAL ELEMENTS:

1. THREE-ACT STRUCTURE:
   - Act 1: Setup and inciting incident (pages/time allocation)
   - Act 2A: Rising action and complications
   - Act 2B: Climax approach and major obstacles
   - Act 3: Resolution and conclusion
   - Transition points and story beats

2. CHARACTER ARCHITECTURE:
   - Main character(s) arc progression
   - Supporting character functions
   - Character relationship dynamics
   - Motivation and goal structures
   - Character development milestones

3. SCENE BREAKDOWN:
   - Scene-by-scene structural outline
   - Each scene's narrative purpose
   - Plot advancement in each scene
   - Character development moments
   - Tension and pacing notes

4. PLOT LOGIC:
   - Cause and effect relationships
   - Story consistency checks
   - Plot hole identification and solutions
   - Logical progression validation
   - Conflict escalation structure

5. STRUCTURAL RECOMMENDATIONS:
   - Pacing optimization suggestions
   - Tension curve management
   - Story coherence enhancement
   - Narrative flow improvements

Remember: Focus exclusively on structural soundness and logical narrative architecture. Do not apply styling, write dialogue, or add creative flourishes. Create the blueprint that subsequent specialized agents will build upon."""

        return user_prompt.strip()

    def create_rag_enhanced_prompt(
        self, context: PromptContext, emphasis_areas: list = None
    ) -> str:
        """Create enhanced prompt with specific RAG emphasis areas"""

        if emphasis_areas is None:
            emphasis_areas = [
                "character_consistency",
                "plot_continuity",
                "world_building",
            ]

        base_prompt = self.create_user_prompt(context)

        if not context.rag_context:
            return base_prompt

        # Add RAG-specific instructions
        rag_enhancement = f"""

RAG CONTEXT INTEGRATION INSTRUCTIONS:
The knowledge base context provided above contains relevant information for this project. Use it to ensure:

{chr(10).join([f'- {area.replace("_", " ").title()}' for area in emphasis_areas])}

When leveraging the context:
1. Maintain consistency with established narrative elements
2. Ensure character arcs align with previously established traits
3. Respect world-building rules and constraints
4. Build upon existing plot threads logically
5. Honor the structural patterns established in the knowledge base

However, do not simply copy or repeat information. Use the context to inform your architectural decisions while creating original structural solutions for this specific project."""

        return base_prompt + rag_enhancement

    def create_character_focused_prompt(
        self, context: PromptContext, main_characters: list
    ) -> str:
        """Create prompt with specific focus on character architecture"""

        base_prompt = self.create_user_prompt(context)

        character_section = f"""

CHARACTER-FOCUSED ARCHITECTURAL REQUIREMENTS:

Main Characters for Structural Development:
{chr(10).join([f'- {char}' for char in main_characters])}

For each main character, design:
1. Character Arc Structure:
   - Starting point (who they are at the beginning)
   - Transformation points (key growth moments)
   - Ending point (who they become)
   - Arc milestones throughout the three acts

2. Character Function Analysis:
   - Role in advancing the main plot
   - Subplot responsibilities
   - Relationship dynamics with other characters
   - Conflict generation and resolution

3. Character Integration:
   - How each character serves the overall structure
   - Character interaction patterns
   - Collective character ecosystem design
   - Ensemble balance considerations

Pay special attention to creating character arcs that serve the structural integrity of the overall narrative."""

        return base_prompt + character_section

    def create_plot_consistency_prompt(
        self, context: PromptContext, plot_elements: dict[str, Any]
    ) -> str:
        """Create prompt with emphasis on plot consistency"""

        base_prompt = self.create_user_prompt(context)

        consistency_section = f"""

PLOT CONSISTENCY REQUIREMENTS:

Established Plot Elements to Maintain:
{chr(10).join([f'- {key}: {value}' for key, value in plot_elements.items()])}

Structural Consistency Checklist:
1. Timeline Logic:
   - Event sequence validation
   - Cause-and-effect chains
   - Character availability and location consistency
   - Plot progression logical flow

2. Story Rules Adherence:
   - World-building constraints
   - Character behavior consistency
   - Established conflict rules
   - Resolution method consistency

3. Narrative Coherence:
   - Theme consistency throughout acts
   - Tone progression logic
   - Character motivation consistency
   - Plot thread resolution planning

Ensure your structural blueprint maintains absolute consistency with these established elements while advancing the story logically."""

        return base_prompt + consistency_section

    def _get_architect_specific_guidance(self, script_type: ScriptType) -> str:
        """Get architect-specific guidance for script types"""

        architect_guidance = {
            ScriptType.DRAMA: {
                "structure": "Focus on emotional escalation and character transformation milestones",
                "pacing": "Build dramatic tension through careful revelation timing",
                "characters": "Design deep character arcs with internal/external conflict balance",
            },
            ScriptType.COMEDY: {
                "structure": "Create setup-punchline architecture with escalating comedic situations",
                "pacing": "Plan comedy beats and timing for maximum effect",
                "characters": "Design character flaws and quirks that drive comedic conflict",
            },
            ScriptType.THRILLER: {
                "structure": "Architect suspense escalation with strategic revelation points",
                "pacing": "Plan tension peaks and relief valleys for sustained engagement",
                "characters": "Create character secrets and motivations that drive mystery",
            },
            ScriptType.DOCUMENTARY: {
                "structure": "Design information architecture with clear learning progression",
                "pacing": "Plan content revelation for educational effectiveness",
                "characters": "Structure subject presentation and narrative voice consistency",
            },
            ScriptType.VARIETY: {
                "structure": "Create segment architecture with energy flow management",
                "pacing": "Plan variety and transition timing for audience engagement",
                "characters": "Design host and guest interaction structures",
            },
        }

        guidance = architect_guidance.get(
            script_type,
            {
                "structure": "Focus on clear narrative architecture",
                "pacing": "Plan content flow for audience engagement",
                "characters": "Design character functions and relationships",
            },
        )

        return f"""
ARCHITECT-SPECIFIC GUIDANCE FOR {script_type.value.upper()}:
- Structure: {guidance['structure']}
- Pacing: {guidance['pacing']}
- Characters: {guidance['characters']}"""
