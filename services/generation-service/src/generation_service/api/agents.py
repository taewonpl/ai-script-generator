"""
Advanced API endpoints for specialized agents and quality assessment
"""

from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel, Field

from generation_service.models.generation import GenerationRequest
from generation_service.services.generation_service import GenerationService
from generation_service.workflows.agents import (
    AgentCapability,
    AgentCoordinator,
    AgentPriority,
)
from generation_service.workflows.feedback import FeedbackLearningEngine
from generation_service.workflows.quality import QualityAssessor

router = APIRouter(prefix="/api/v1/agents", tags=["Specialized Agents"])


# Request/Response Models
class AgentAnalysisRequest(BaseModel):
    """Request for agent analysis"""

    content: str = Field(..., min_length=10, description="Script content to analyze")
    user_id: str | None = Field(None, description="User ID for personalization")
    agent_filter: list[str] | None = Field(
        None, description="Specific agents to analyze"
    )


class AgentRecommendationResponse(BaseModel):
    """Agent recommendation response"""

    suitable_agents: list[dict[str, Any]]
    analysis_confidence: float
    estimated_duration: float
    recommendations: list[str]


class AdaptiveWorkflowRequest(BaseModel):
    """Request for adaptive workflow execution"""

    generation_request: GenerationRequest
    user_id: str | None = None
    preferences: dict[str, Any] | None = None
    max_agents: int | None = Field(3, ge=1, le=5)
    min_confidence: float | None = Field(0.4, ge=0.0, le=1.0)


class AdaptiveWorkflowResponse(BaseModel):
    """Adaptive workflow execution response"""

    generation_id: str
    enhanced_script: str
    agents_applied: list[str]
    execution_summary: dict[str, Any]
    quality_assessment: dict[str, Any]
    overall_improvement: float


class QualityAssessmentRequest(BaseModel):
    """Request for quality assessment"""

    content: str = Field(..., min_length=10)
    user_id: str | None = None
    comparison_content: str | None = None


class QualityAssessmentResponse(BaseModel):
    """Quality assessment response"""

    overall_score: float
    dimension_scores: dict[str, dict[str, Any]]
    improvement_areas: list[dict[str, Any]]
    strengths: list[dict[str, Any]]
    recommendations: list[str]
    assessment_confidence: float


class FeedbackSubmissionRequest(BaseModel):
    """Request for submitting user feedback"""

    generation_id: str
    user_rating: float = Field(..., ge=0.0, le=1.0)
    quality_feedback: dict[str, float] | None = None
    comments: str | None = None
    user_id: str | None = None


class UserPreferencesResponse(BaseModel):
    """User preferences response"""

    user_id: str
    quality_preferences: dict[str, float]
    agent_preferences: dict[str, float]
    style_preferences: dict[str, Any]
    confidence_score: float
    total_feedback_count: int


# Dependency injection
async def get_generation_service() -> GenerationService:
    """Get generation service instance"""
    # In practice, this would be injected from your DI container
    from generation_service.services.generation_service import GenerationService

    return GenerationService()


async def get_agent_coordinator() -> AgentCoordinator:
    """Get agent coordinator instance"""
    # In practice, this would be configured and injected
    return AgentCoordinator()


async def get_quality_assessor() -> QualityAssessor:
    """Get quality assessor instance"""
    return QualityAssessor()


async def get_feedback_engine() -> FeedbackLearningEngine:
    """Get feedback learning engine instance"""
    return FeedbackLearningEngine()


# Agent Analysis and Recommendations
@router.post("/analyze", response_model=AgentRecommendationResponse)
async def analyze_content_for_agents(
    request: AgentAnalysisRequest,
    coordinator: AgentCoordinator = Depends(get_agent_coordinator),
) -> AgentRecommendationResponse:
    """
    Analyze content to determine which specialized agents should be applied
    """
    try:
        # Create a minimal state for analysis
        state = {
            "styled_script": request.content,
            "generation_id": f"analysis_{hash(request.content)}",
            "user_id": request.user_id,
        }

        # Analyze content needs
        analysis = await coordinator.analyze_content_needs(state)

        # Filter agents if requested
        if request.agent_filter:
            filtered_agents = [
                agent
                for agent in analysis["suitable_agents"]
                if agent["agent_name"] in request.agent_filter
            ]
            analysis["suitable_agents"] = filtered_agents

        # Create execution plan for duration estimation
        plan = await coordinator.create_execution_plan(state)

        recommendations = []
        for agent_info in analysis["suitable_agents"][:3]:  # Top 3
            recommendations.append(
                f"Apply {agent_info['agent_name']} with {agent_info['confidence']:.1f} confidence"
            )

        return AgentRecommendationResponse(
            suitable_agents=analysis["suitable_agents"],
            analysis_confidence=analysis["analysis_confidence"],
            estimated_duration=plan.estimated_duration,
            recommendations=recommendations,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Agent analysis failed: {e!s}")


@router.post("/adaptive-workflow", response_model=AdaptiveWorkflowResponse)
async def execute_adaptive_workflow(
    request: AdaptiveWorkflowRequest,
    background_tasks: BackgroundTasks,
    coordinator: AgentCoordinator = Depends(get_agent_coordinator),
    quality_assessor: QualityAssessor = Depends(get_quality_assessor),
    generation_service: GenerationService = Depends(get_generation_service),
) -> AdaptiveWorkflowResponse:
    """
    Execute adaptive workflow with intelligent agent selection and coordination
    """
    try:
        # Create initial state from generation request
        state = await generation_service.create_initial_state(
            request.generation_request
        )

        # Apply preferences
        preferences = request.preferences or {}
        preferences.update(
            {"max_agents": request.max_agents, "min_confidence": request.min_confidence}
        )

        # Execute adaptive workflow
        enhanced_state = await coordinator.execute_adaptive_workflow(state, preferences)

        # Assess quality of result
        original_content = state.get("styled_script", state.get("draft_script", ""))
        enhanced_content = enhanced_state.get(
            "enhanced_script", enhanced_state.get("styled_script", "")
        )

        quality_assessment = await quality_assessor.assess_quality(enhanced_content)

        # Calculate overall improvement
        if original_content:
            original_assessment = await quality_assessor.assess_quality(
                original_content
            )
            overall_improvement = (
                quality_assessment.overall_score - original_assessment.overall_score
            )
        else:
            overall_improvement = 0.0

        # Extract execution summary
        coordination_metadata = enhanced_state.get("coordination_metadata", {})
        execution_plan = coordination_metadata.get("execution_plan", {})

        return AdaptiveWorkflowResponse(
            generation_id=enhanced_state["generation_id"],
            enhanced_script=enhanced_content,
            agents_applied=execution_plan.get("agents_executed", []),
            execution_summary={
                "total_duration": execution_plan.get("total_duration", 0.0),
                "agents_count": len(execution_plan.get("agents_executed", [])),
                "parallel_groups": execution_plan.get("parallel_groups", []),
                "overall_success": coordination_metadata.get("overall_success", False),
            },
            quality_assessment={
                "overall_score": quality_assessment.overall_score,
                "assessment_confidence": quality_assessment.assessment_confidence,
                "top_strengths": [s[1] for s in quality_assessment.strengths[:3]],
                "top_improvements": [
                    area[0].value for area in quality_assessment.improvement_areas[:3]
                ],
            },
            overall_improvement=overall_improvement,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Adaptive workflow failed: {e!s}")


# Quality Assessment Endpoints
@router.post("/quality/assess", response_model=QualityAssessmentResponse)
async def assess_content_quality(
    request: QualityAssessmentRequest,
    assessor: QualityAssessor = Depends(get_quality_assessor),
) -> QualityAssessmentResponse:
    """
    Perform comprehensive quality assessment of script content
    """
    try:
        # Assess primary content
        assessment = await assessor.assess_quality(request.content)

        # Format dimension scores
        dimension_scores = {}
        for dimension, score_obj in assessment.dimension_scores.items():
            dimension_scores[dimension.value] = {
                "score": score_obj.score,
                "confidence": score_obj.confidence,
                "details": score_obj.details,
                "suggestions": score_obj.suggestions[:3],  # Top 3 suggestions
            }

        # Format improvement areas
        improvement_areas = []
        for dimension, potential in assessment.improvement_areas:
            improvement_areas.append(
                {
                    "dimension": dimension.value,
                    "improvement_potential": potential,
                    "current_score": assessment.dimension_scores[dimension].score,
                }
            )

        # Format strengths
        strengths = []
        for dimension, description in assessment.strengths:
            strengths.append(
                {
                    "dimension": dimension.value,
                    "description": description,
                    "score": assessment.dimension_scores[dimension].score,
                }
            )

        # Handle comparison if provided
        if request.comparison_content:
            comparison = await assessor.compare_assessments(
                request.content, request.comparison_content
            )
            # Add comparison data to response (could extend response model)

        return QualityAssessmentResponse(
            overall_score=assessment.overall_score,
            dimension_scores=dimension_scores,
            improvement_areas=improvement_areas,
            strengths=strengths,
            recommendations=assessment.recommendations,
            assessment_confidence=assessment.assessment_confidence,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Quality assessment failed: {e!s}")


@router.post("/quality/compare")
async def compare_content_quality(
    original_content: str,
    enhanced_content: str,
    user_id: str | None = None,
    assessor: QualityAssessor = Depends(get_quality_assessor),
) -> dict[str, Any]:
    """
    Compare quality assessments between two pieces of content
    """
    try:
        comparison = await assessor.compare_assessments(
            original_content, enhanced_content
        )

        return {
            "overall_improvement": comparison["overall_improvement"],
            "dimension_improvements": comparison["dimension_improvements"],
            "improvement_summary": comparison["improvement_summary"],
            "regression_warnings": comparison["regression_warnings"],
            "original_score": comparison["original_assessment"].overall_score,
            "enhanced_score": comparison["enhanced_assessment"].overall_score,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Quality comparison failed: {e!s}")


# Feedback and Learning Endpoints
@router.post("/feedback/submit")
async def submit_feedback(
    request: FeedbackSubmissionRequest,
    background_tasks: BackgroundTasks,
    feedback_engine: FeedbackLearningEngine = Depends(get_feedback_engine),
) -> dict[str, str]:
    """
    Submit user feedback for continuous learning and improvement
    """
    try:
        # Process the feedback
        await feedback_engine.process_generation_feedback(
            generation_id=request.generation_id,
            user_rating=request.user_rating,
            quality_feedback=request.quality_feedback,
            user_id=request.user_id,
            comments=request.comments,
        )

        return {
            "message": "Feedback submitted successfully",
            "feedback_id": request.generation_id,
        }

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Feedback submission failed: {e!s}"
        )


@router.get("/preferences/{user_id}", response_model=UserPreferencesResponse)
async def get_user_preferences(
    user_id: str, feedback_engine: FeedbackLearningEngine = Depends(get_feedback_engine)
) -> UserPreferencesResponse:
    """
    Get learned preferences for a specific user
    """
    try:
        profile = await feedback_engine.get_user_preferences(user_id)

        if not profile:
            raise HTTPException(status_code=404, detail="User preferences not found")

        return UserPreferencesResponse(
            user_id=profile.user_id,
            quality_preferences={
                dim.value: weight for dim, weight in profile.quality_preferences.items()
            },
            agent_preferences=profile.agent_preferences,
            style_preferences=profile.style_preferences,
            confidence_score=profile.confidence_score,
            total_feedback_count=profile.total_feedback_count,
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get user preferences: {e!s}"
        )


@router.post("/preferences/{user_id}/personalize")
async def personalize_config(
    user_id: str,
    base_config: dict[str, Any],
    feedback_engine: FeedbackLearningEngine = Depends(get_feedback_engine),
) -> dict[str, Any]:
    """
    Personalize generation configuration based on user preferences
    """
    try:
        personalized_config = await feedback_engine.personalize_generation_config(
            base_config, user_id
        )

        return {
            "personalized_config": personalized_config,
            "personalization_applied": personalized_config != base_config,
        }

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Configuration personalization failed: {e!s}"
        )


# Agent and System Statistics
@router.get("/stats/agents")
async def get_agent_statistics(
    coordinator: AgentCoordinator = Depends(get_agent_coordinator),
) -> dict[str, Any]:
    """
    Get statistics about agent performance and usage
    """
    try:
        return coordinator.get_coordinator_metrics()

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get agent statistics: {e!s}"
        )


@router.get("/stats/quality")
async def get_quality_statistics(
    assessor: QualityAssessor = Depends(get_quality_assessor),
) -> dict[str, Any]:
    """
    Get statistics about quality assessment performance
    """
    try:
        return assessor.get_assessor_stats()

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get quality statistics: {e!s}"
        )


@router.get("/stats/feedback")
async def get_feedback_statistics(
    feedback_engine: FeedbackLearningEngine = Depends(get_feedback_engine),
) -> dict[str, Any]:
    """
    Get statistics about feedback system performance
    """
    try:
        return feedback_engine.get_feedback_statistics()

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get feedback statistics: {e!s}"
        )


# Configuration and Management
@router.get("/capabilities")
async def get_agent_capabilities() -> dict[str, dict[str, Any]]:
    """
    Get available agent capabilities and their descriptions
    """
    return {
        "capabilities": {
            capability.value: {
                "name": capability.value.replace("_", " ").title(),
                "description": f"Specialized capability for {capability.value.replace('_', ' ')}",
            }
            for capability in AgentCapability
        },
        "priorities": {priority.name: priority.value for priority in AgentPriority},
    }


@router.get("/health")
async def agent_system_health(
    coordinator: AgentCoordinator = Depends(get_agent_coordinator),
    assessor: QualityAssessor = Depends(get_quality_assessor),
    feedback_engine: FeedbackLearningEngine = Depends(get_feedback_engine),
) -> dict[str, Any]:
    """
    Check health status of the agent system
    """
    try:
        coordinator_metrics = coordinator.get_coordinator_metrics()
        assessor_stats = assessor.get_assessor_stats()
        feedback_stats = feedback_engine.get_feedback_statistics()

        return {
            "status": "healthy",
            "coordinator": {
                "available_agents": len(
                    coordinator_metrics.get("available_agents", [])
                ),
                "success_rate": coordinator_metrics.get("success_rate", 0.0),
            },
            "quality_assessor": {
                "total_assessments": assessor_stats.get("total_assessments", 0)
            },
            "feedback_system": {
                "total_feedback": feedback_stats.get("total_feedback", 0),
                "user_profiles": feedback_stats.get("user_profiles", 0),
            },
        }

    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}
