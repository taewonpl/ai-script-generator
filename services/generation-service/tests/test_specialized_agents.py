"""
Comprehensive tests for specialized agents system
"""

from datetime import datetime
from typing import Any
from unittest.mock import AsyncMock, Mock

import pytest

from generation_service.ai.providers.base_provider import (
    ModelInfo,
    ProviderGenerationResponse,
)
from generation_service.workflows.agents import (
    AgentCapability,
    AgentCoordinator,
    AgentExecutionPlan,
    AgentPriority,
    BaseSpecialAgent,
    DialogueEnhancerAgent,
    FlawGeneratorAgent,
    PlotTwisterAgent,
    SceneVisualizerAgent,
    TensionBuilderAgent,
)
from generation_service.workflows.feedback import (
    FeedbackLearningEngine,
    FeedbackSentiment,
    FeedbackType,
)
from generation_service.workflows.quality import QualityAssessor, QualityDimension
from generation_service.workflows.state import GenerationState


class TestBaseSpecialAgent:
    """Test base agent functionality"""

    @pytest.fixture
    def mock_provider_factory(self):
        """Mock provider factory"""
        factory = Mock()
        provider = Mock()
        provider.generate_with_retry = AsyncMock()
        factory.get_provider = AsyncMock(return_value=provider)
        return factory, provider

    @pytest.fixture
    def sample_state(self):
        """Sample generation state"""
        return {
            "generation_id": "test_123",
            "draft_script": "Sample script content for testing agents",
            "styled_script": 'EXT. COFFEE SHOP - DAY\n\nJOHN sits alone, looking thoughtful.\n\nJOHN\n"I need to make a decision."',
            "error_messages": [],
            "execution_log": [],
        }

    class TestAgent(BaseSpecialAgent):
        """Test implementation of BaseSpecialAgent"""

        async def analyze_content(self, state: GenerationState) -> dict[str, Any]:
            content = state.get("styled_script") or state.get("draft_script", "")
            return {
                "should_enhance": len(content) > 10,
                "enhancement_confidence": 0.8,
                "context": f"Content length: {len(content)}",
            }

        async def enhance_content(self, state: GenerationState) -> dict[str, Any]:
            content = state.get("styled_script") or state.get("draft_script", "")
            enhanced = f"ENHANCED: {content}"
            return {
                "enhanced_content": enhanced,
                "quality_improvement": 0.2,
                "model_used": "test_model",
                "tokens_used": 100,
            }

        def calculate_quality_improvement(self, original: str, enhanced: str) -> float:
            return 0.2

    def test_agent_initialization(self, mock_provider_factory):
        """Test agent initialization"""
        factory, _ = mock_provider_factory

        agent = self.TestAgent(
            agent_name="test_agent",
            capabilities=[AgentCapability.PLOT_ENHANCEMENT],
            priority=AgentPriority.HIGH,
            provider_factory=factory,
            config={"test_setting": 0.5},
        )

        assert agent.agent_name == "test_agent"
        assert AgentCapability.PLOT_ENHANCEMENT in agent.capabilities
        assert agent.priority == AgentPriority.HIGH
        assert agent.get_config_value("test_setting") == 0.5
        assert agent.execution_count == 0

    @pytest.mark.asyncio
    async def test_agent_execution_success(self, mock_provider_factory, sample_state):
        """Test successful agent execution"""
        factory, provider = mock_provider_factory

        # Mock AI response
        provider.generate_with_retry.return_value = ProviderGenerationResponse(
            content="Enhanced content",
            model_info=ModelInfo(name="test_model", provider="test"),
            metadata={"tokens_used": 100},
        )

        agent = self.TestAgent(
            agent_name="test_agent",
            capabilities=[AgentCapability.PLOT_ENHANCEMENT],
            provider_factory=factory,
        )

        result = await agent.execute(sample_state)

        assert "enhanced_script" in result
        assert (
            result["enhanced_script"]
            == 'ENHANCED: EXT. COFFEE SHOP - DAY\n\nJOHN sits alone, looking thoughtful.\n\nJOHN\n"I need to make a decision."'
        )
        assert "generation_metadata" in result
        assert "test_agent" in str(result["generation_metadata"])
        assert agent.execution_count == 1
        assert agent.success_count == 1

    @pytest.mark.asyncio
    async def test_agent_execution_skip(self, mock_provider_factory):
        """Test agent execution skip when enhancement not needed"""
        factory, _ = mock_provider_factory

        # State with insufficient content
        minimal_state = {
            "generation_id": "test_123",
            "draft_script": "Short",
            "error_messages": [],
            "execution_log": [],
        }

        agent = self.TestAgent(
            agent_name="test_agent",
            capabilities=[AgentCapability.PLOT_ENHANCEMENT],
            provider_factory=factory,
        )

        # Override analyze_content to return skip
        async def mock_analyze(state):
            return {"should_enhance": False, "skip_reason": "Content too short"}

        agent.analyze_content = mock_analyze

        result = await agent.execute(minimal_state)

        assert "enhanced_script" not in result
        assert any(
            "skipped" in log["status"] for log in result.get("execution_log", [])
        )

    @pytest.mark.asyncio
    async def test_agent_execution_error(self, mock_provider_factory, sample_state):
        """Test agent execution with error handling"""
        factory, provider = mock_provider_factory

        # Mock provider error
        provider.generate_with_retry.side_effect = Exception("AI provider error")

        agent = self.TestAgent(
            agent_name="test_agent",
            capabilities=[AgentCapability.PLOT_ENHANCEMENT],
            provider_factory=factory,
        )

        result = await agent.execute(sample_state)

        assert result.get("has_errors") is True
        assert any("failed" in msg for msg in result.get("error_messages", []))
        assert agent.execution_count == 1
        assert agent.success_count == 0


class TestSpecializedAgents:
    """Test individual specialized agents"""

    @pytest.fixture
    def mock_provider_factory(self):
        """Mock provider factory for agents"""
        factory = Mock()
        provider = Mock()
        provider.generate_with_retry = AsyncMock()
        factory.get_provider = AsyncMock(return_value=provider)
        return factory, provider

    @pytest.fixture
    def sample_script(self):
        """Sample script for testing"""
        return """
EXT. COFFEE SHOP - DAY

JOHN sits alone at a table, looking thoughtful.

JOHN
"I need to make a decision about my future."

MARY enters and approaches his table.

MARY
"Mind if I sit? You look like you could use some company."

JOHN
"Sure, that would be nice."

Mary sits down. An awkward silence follows.

MARY
"So what's troubling you?"

JOHN
"I got a job offer in another city. I don't know if I should take it."

MARY
"That sounds like a big decision."

JOHN
"It is. I'd have to leave everything behind."

FADE OUT.
"""

    @pytest.mark.asyncio
    async def test_plot_twister_agent(self, mock_provider_factory, sample_script):
        """Test PlotTwisterAgent functionality"""
        factory, provider = mock_provider_factory

        # Mock enhanced response with plot twist
        provider.generate_with_retry.return_value = ProviderGenerationResponse(
            content=sample_script
            + "\n\nSuddenly, John realizes Mary is his long-lost sister.",
            model_info=ModelInfo(name="gpt-4", provider="openai"),
            metadata={"tokens_used": 150},
        )

        agent = PlotTwisterAgent(provider_factory=factory)

        state = {
            "generation_id": "test_123",
            "styled_script": sample_script,
            "error_messages": [],
            "execution_log": [],
        }

        # Test analysis
        analysis = await agent.analyze_content(state)
        assert "predictability_score" in analysis
        assert "twist_opportunities" in analysis
        assert isinstance(analysis["should_enhance"], bool)

        # Test enhancement
        if analysis["should_enhance"]:
            result = await agent.enhance_content(state)
            assert "enhanced_content" in result
            assert "twists_added" in result
            assert result["enhancement_type"] == "plot_twist_enhancement"

    @pytest.mark.asyncio
    async def test_flaw_generator_agent(self, mock_provider_factory, sample_script):
        """Test FlawGeneratorAgent functionality"""
        factory, provider = mock_provider_factory

        # Mock enhanced response with character flaws
        enhanced_script = sample_script.replace(
            'JOHN\n"I need to make a decision about my future."',
            'JOHN\n"I need to make a decision about my future. But I always overthink everything."',
        )

        provider.generate_with_retry.return_value = ProviderGenerationResponse(
            content=enhanced_script,
            model_info=ModelInfo(name="gpt-4", provider="openai"),
            metadata={"tokens_used": 120},
        )

        agent = FlawGeneratorAgent(provider_factory=factory)

        state = {
            "generation_id": "test_123",
            "styled_script": sample_script,
            "error_messages": [],
            "execution_log": [],
        }

        # Test analysis
        analysis = await agent.analyze_content(state)
        assert "characters" in analysis
        assert "character_count" in analysis
        assert "recommended_flaws" in analysis

        # Test enhancement
        if analysis["should_enhance"]:
            result = await agent.enhance_content(state)
            assert "enhanced_content" in result
            assert "flaws_added" in result
            assert result["enhancement_type"] == "character_flaw_enhancement"

    @pytest.mark.asyncio
    async def test_dialogue_enhancer_agent(self, mock_provider_factory, sample_script):
        """Test DialogueEnhancerAgent functionality"""
        factory, provider = mock_provider_factory

        # Mock enhanced response with improved dialogue
        enhanced_script = sample_script.replace(
            '"Sure, that would be nice."',
            "\"Yeah, I'd... I'd like that actually. Thanks.\"",
        )

        provider.generate_with_retry.return_value = ProviderGenerationResponse(
            content=enhanced_script,
            model_info=ModelInfo(name="gpt-4", provider="openai"),
            metadata={"tokens_used": 130},
        )

        agent = DialogueEnhancerAgent(provider_factory=factory)

        state = {
            "generation_id": "test_123",
            "styled_script": sample_script,
            "error_messages": [],
            "execution_log": [],
        }

        # Test analysis
        analysis = await agent.analyze_content(state)
        assert "dialogue_data" in analysis
        assert "quality_scores" in analysis
        assert "identified_problems" in analysis

        # Test enhancement
        if analysis["should_enhance"]:
            result = await agent.enhance_content(state)
            assert "enhanced_content" in result
            assert "naturalness_improvement" in result
            assert result["enhancement_type"] == "dialogue_enhancement"

    @pytest.mark.asyncio
    async def test_scene_visualizer_agent(self, mock_provider_factory, sample_script):
        """Test SceneVisualizerAgent functionality"""
        factory, provider = mock_provider_factory

        # Mock enhanced response with visual details
        enhanced_script = sample_script.replace(
            "EXT. COFFEE SHOP - DAY",
            "EXT. COFFEE SHOP - DAY (Golden sunlight streams through large windows)",
        )

        provider.generate_with_retry.return_value = ProviderGenerationResponse(
            content=enhanced_script,
            model_info=ModelInfo(name="gpt-4", provider="openai"),
            metadata={"tokens_used": 110},
        )

        agent = SceneVisualizerAgent(provider_factory=factory)

        state = {
            "generation_id": "test_123",
            "styled_script": sample_script,
            "error_messages": [],
            "execution_log": [],
        }

        # Test analysis
        analysis = await agent.analyze_content(state)
        assert "scene_descriptions" in analysis
        assert "visual_density" in analysis
        assert "enhancement_opportunities" in analysis

        # Test enhancement
        if analysis["should_enhance"]:
            result = await agent.enhance_content(state)
            assert "enhanced_content" in result
            assert "visual_elements_added" in result
            assert result["enhancement_type"] == "visual_scene_enhancement"

    @pytest.mark.asyncio
    async def test_tension_builder_agent(self, mock_provider_factory, sample_script):
        """Test TensionBuilderAgent functionality"""
        factory, provider = mock_provider_factory

        # Mock enhanced response with increased tension
        enhanced_script = sample_script.replace(
            "An awkward silence follows.",
            "An awkward silence follows. John's hands tremble slightly as he grips his coffee cup.",
        )

        provider.generate_with_retry.return_value = ProviderGenerationResponse(
            content=enhanced_script,
            model_info=ModelInfo(name="gpt-4", provider="openai"),
            metadata={"tokens_used": 140},
        )

        agent = TensionBuilderAgent(provider_factory=factory)

        state = {
            "generation_id": "test_123",
            "styled_script": sample_script,
            "error_messages": [],
            "execution_log": [],
        }

        # Test analysis
        analysis = await agent.analyze_content(state)
        assert "tension_structure" in analysis
        assert "pacing_analysis" in analysis
        assert "tension_effectiveness" in analysis

        # Test enhancement
        if analysis["should_enhance"]:
            result = await agent.enhance_content(state)
            assert "enhanced_content" in result
            assert "tension_increase" in result
            assert result["enhancement_type"] == "tension_building_enhancement"


class TestAgentCoordinator:
    """Test agent coordination functionality"""

    @pytest.fixture
    def mock_provider_factory(self):
        """Mock provider factory"""
        factory = Mock()
        provider = Mock()
        provider.generate_with_retry = AsyncMock()
        factory.get_provider = AsyncMock(return_value=provider)
        return factory, provider

    @pytest.fixture
    def sample_state(self):
        """Sample state for coordination testing"""
        return {
            "generation_id": "test_123",
            "styled_script": "EXT. PARK - DAY\n\nTwo characters meet and have a conversation about their future.",
            "error_messages": [],
            "execution_log": [],
        }

    @pytest.mark.asyncio
    async def test_coordinator_initialization(self, mock_provider_factory):
        """Test coordinator initialization"""
        factory, _ = mock_provider_factory

        coordinator = AgentCoordinator(provider_factory=factory)

        assert len(coordinator.agents) > 0
        assert "plot_twister" in coordinator.agents
        assert "dialogue_enhancer" in coordinator.agents
        assert coordinator.total_executions == 0

    @pytest.mark.asyncio
    async def test_content_analysis(self, mock_provider_factory, sample_state):
        """Test content analysis for agent selection"""
        factory, _ = mock_provider_factory

        coordinator = AgentCoordinator(provider_factory=factory)

        analysis = await coordinator.analyze_content_needs(sample_state)

        assert "suitable_agents" in analysis
        assert "analysis_confidence" in analysis
        assert "content_length" in analysis
        assert isinstance(analysis["suitable_agents"], list)

    @pytest.mark.asyncio
    async def test_execution_plan_creation(self, mock_provider_factory, sample_state):
        """Test execution plan creation"""
        factory, _ = mock_provider_factory

        coordinator = AgentCoordinator(provider_factory=factory)

        preferences = {"max_agents": 2, "min_confidence": 0.3}

        plan = await coordinator.create_execution_plan(sample_state, preferences)

        assert isinstance(plan, AgentExecutionPlan)
        assert len(plan.agents) <= 2
        assert plan.estimated_duration > 0
        assert len(plan.execution_order) <= len(plan.agents)

    @pytest.mark.asyncio
    async def test_adaptive_workflow_execution(
        self, mock_provider_factory, sample_state
    ):
        """Test complete adaptive workflow execution"""
        factory, provider = mock_provider_factory

        # Mock all agent responses
        provider.generate_with_retry.return_value = ProviderGenerationResponse(
            content="Enhanced script content",
            model_info=ModelInfo(name="gpt-4", provider="openai"),
            metadata={"tokens_used": 100},
        )

        coordinator = AgentCoordinator(provider_factory=factory)

        # Mock agent analyses to ensure they want to enhance
        for agent in coordinator.agents.values():
            original_analyze = agent.analyze_content

            async def mock_analyze(state):
                result = await original_analyze(state)
                result["should_enhance"] = True
                result["enhancement_confidence"] = 0.8
                return result

            agent.analyze_content = mock_analyze

        preferences = {"max_agents": 1}  # Limit to 1 for testing

        result = await coordinator.execute_adaptive_workflow(sample_state, preferences)

        assert "coordination_metadata" in result
        assert result["generation_id"] == sample_state["generation_id"]


class TestQualityAssessor:
    """Test quality assessment functionality"""

    @pytest.fixture
    def sample_script(self):
        """Sample script for quality assessment"""
        return """
EXT. COFFEE SHOP - DAY

JOHN sits alone, deep in thought about his uncertain future.

JOHN
"I don't know what to do. This decision will change everything."

MARY enters, noticing John's troubled expression.

MARY
"You look worried. Want to talk about it?"

The conversation reveals John's internal conflict and fears.
"""

    @pytest.mark.asyncio
    async def test_quality_assessment(self, sample_script):
        """Test basic quality assessment"""
        assessor = QualityAssessor()

        assessment = await assessor.assess_quality(sample_script)

        assert 0.0 <= assessment.overall_score <= 1.0
        assert len(assessment.dimension_scores) == len(QualityDimension)
        assert len(assessment.improvement_areas) > 0
        assert len(assessment.recommendations) > 0
        assert 0.0 <= assessment.assessment_confidence <= 1.0

    @pytest.mark.asyncio
    async def test_quality_comparison(self, sample_script):
        """Test quality comparison between two versions"""
        assessor = QualityAssessor()

        enhanced_script = (
            sample_script + "\n\nSuddenly, John's phone rings with unexpected news."
        )

        comparison = await assessor.compare_assessments(sample_script, enhanced_script)

        assert "original_assessment" in comparison
        assert "enhanced_assessment" in comparison
        assert "overall_improvement" in comparison
        assert "dimension_improvements" in comparison

    @pytest.mark.asyncio
    async def test_dimension_assessment(self, sample_script):
        """Test individual dimension assessment"""
        assessor = QualityAssessor()

        assessment = await assessor.assess_quality(sample_script)

        # Check each dimension has proper structure
        for dimension, score_obj in assessment.dimension_scores.items():
            assert 0.0 <= score_obj.score <= 1.0
            assert 0.0 <= score_obj.confidence <= 1.0
            assert isinstance(score_obj.suggestions, list)
            assert isinstance(score_obj.details, dict)


class TestFeedbackSystem:
    """Test feedback learning system"""

    @pytest.fixture
    def feedback_engine(self):
        """Feedback learning engine instance"""
        return FeedbackLearningEngine()

    @pytest.mark.asyncio
    async def test_feedback_recording(self, feedback_engine):
        """Test feedback recording and processing"""
        from generation_service.workflows.feedback import UserFeedback

        feedback = UserFeedback(
            feedback_id="test_feedback_1",
            user_id="user_123",
            generation_id="gen_456",
            feedback_type=FeedbackType.EXPLICIT_RATING,
            sentiment=FeedbackSentiment.POSITIVE,
            content={"overall_rating": 0.8},
            quality_scores={"plot_structure": 0.9, "dialogue_quality": 0.7},
            timestamp=datetime.now(),
        )

        await feedback_engine.record_feedback(feedback)

        assert feedback.feedback_id in feedback_engine.feedback_storage
        assert "user_123" in feedback_engine.user_profiles

    @pytest.mark.asyncio
    async def test_user_preference_learning(self, feedback_engine):
        """Test user preference learning from feedback"""

        # Submit multiple feedback items
        await feedback_engine.process_generation_feedback(
            generation_id="gen_1",
            user_rating=0.8,
            quality_feedback={"plot_structure": 0.9, "dialogue_quality": 0.7},
            user_id="user_123",
        )

        await feedback_engine.process_generation_feedback(
            generation_id="gen_2",
            user_rating=0.6,
            quality_feedback={"plot_structure": 0.5, "dialogue_quality": 0.8},
            user_id="user_123",
        )

        # Get learned preferences
        profile = await feedback_engine.get_user_preferences("user_123")

        assert profile is not None
        assert profile.user_id == "user_123"
        assert profile.total_feedback_count == 2
        assert profile.confidence_score > 0.0

    @pytest.mark.asyncio
    async def test_config_personalization(self, feedback_engine):
        """Test configuration personalization based on preferences"""

        # Create user profile with preferences
        await feedback_engine.process_generation_feedback(
            generation_id="gen_1",
            user_rating=0.9,
            quality_feedback={"dialogue_quality": 0.95, "plot_structure": 0.8},
            user_id="user_123",
        )

        base_config = {
            "quality_preferences": {"dialogue_quality": 0.5, "plot_structure": 0.6},
            "agent_configs": {"dialogue_enhancer": {"intensity": 0.7}},
        }

        personalized = await feedback_engine.personalize_generation_config(
            base_config, "user_123"
        )

        # Should have some personalization applied
        assert personalized != base_config

    @pytest.mark.asyncio
    async def test_implicit_feedback(self, feedback_engine):
        """Test implicit feedback processing"""

        user_actions = {
            "downloaded_script": True,
            "session_duration": 350,
            "regenerated_count": 0,
            "shared_script": True,
        }

        await feedback_engine.process_implicit_feedback(
            generation_id="gen_1",
            user_actions=user_actions,
            user_id="user_123",
            session_duration=350,
        )

        # Check feedback was recorded
        implicit_feedback = [
            f
            for f in feedback_engine.feedback_storage.values()
            if f.feedback_type == FeedbackType.IMPLICIT_BEHAVIOR
        ]

        assert len(implicit_feedback) > 0
        assert implicit_feedback[0].sentiment == FeedbackSentiment.POSITIVE


@pytest.mark.asyncio
async def test_integration_workflow():
    """Test complete integration workflow"""

    # Mock dependencies
    provider_factory = Mock()
    provider = Mock()
    provider.generate_with_retry = AsyncMock()
    provider_factory.get_provider = AsyncMock(return_value=provider)

    # Mock enhanced content
    provider.generate_with_retry.return_value = ProviderGenerationResponse(
        content="Enhanced script with improvements",
        model_info=ModelInfo(name="gpt-4", provider="openai"),
        metadata={"tokens_used": 150},
    )

    # Create system components
    coordinator = AgentCoordinator(provider_factory=provider_factory)
    assessor = QualityAssessor()
    feedback_engine = FeedbackLearningEngine()

    # Initial state
    state = {
        "generation_id": "integration_test",
        "styled_script": "EXT. PARK - DAY\n\nTwo people meet and discuss their dreams.",
        "error_messages": [],
        "execution_log": [],
    }

    # 1. Execute adaptive workflow
    enhanced_state = await coordinator.execute_adaptive_workflow(state)

    # 2. Assess quality
    original_content = state["styled_script"]
    enhanced_content = enhanced_state.get(
        "enhanced_script", enhanced_state.get("styled_script")
    )

    assessment = await assessor.assess_quality(enhanced_content)
    comparison = await assessor.compare_assessments(original_content, enhanced_content)

    # 3. Process feedback
    await feedback_engine.process_generation_feedback(
        generation_id=enhanced_state["generation_id"],
        user_rating=0.8,
        quality_feedback={"overall": 0.8},
        user_id="integration_user",
    )

    # Verify integration
    assert enhanced_state["generation_id"] == "integration_test"
    assert assessment.overall_score >= 0.0
    assert len(feedback_engine.feedback_storage) > 0

    # Verify coordinator recorded execution
    metrics = coordinator.get_coordinator_metrics()
    assert metrics["total_executions"] > 0
