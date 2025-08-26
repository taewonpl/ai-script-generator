"""
Script generation endpoints with Core Module integration
"""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status

from generation_service.models.generation import (
    CustomWorkflowRequest,
    GenerationRequest,
    GenerationResponse,
    HybridWorkflowResponse,
    ScriptGenerationRequest,
    WorkflowStatusResponse,
)
from generation_service.services.generation_service import GenerationService

from .idempotency_middleware import idempotent_endpoint

# Import Core Module components
try:
    from ai_script_core import (
        BaseServiceException,
        CommonResponseDTO,
        ErrorResponseDTO,
        GenerationServiceError,
        NotFoundError,
        SuccessResponseDTO,
        ValidationException,
        exception_handler,
        get_service_logger,
    )

    CORE_AVAILABLE = True
    logger = get_service_logger("generation-service.api")
except (ImportError, RuntimeError):
    CORE_AVAILABLE = False
    import logging

    logger = logging.getLogger(__name__)

router = APIRouter()


# Global service instance
_generation_service_instance = None


def get_generation_service() -> GenerationService:
    """Dependency to get generation service instance"""
    global _generation_service_instance
    if _generation_service_instance is None:
        _generation_service_instance = GenerationService()
    return _generation_service_instance


@router.post(
    "/generate",
    response_model=GenerationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Generate Script",
    description="Generate a script based on the provided parameters",
)
@idempotent_endpoint(ttl_seconds=24 * 3600)  # 24 hour TTL for generation requests
async def generate_script(
    request: GenerationRequest,
    http_request: Request,
    service: GenerationService = Depends(get_generation_service),
) -> GenerationResponse:
    """Generate a script based on the request parameters"""

    try:
        result = await service.generate_script(request)
        logger.info(f"Script generation started: {result.generation_id}")
        return result

    except ValidationException as e:
        logger.warning(f"Validation error: {e}")
        if CORE_AVAILABLE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail=e.to_dict()
            )
        else:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except BaseServiceException as e:
        logger.error(f"Service error: {e}")
        if CORE_AVAILABLE:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=e.to_dict()
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
            )
    except ValueError as e:
        logger.warning(f"Invalid request: {e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        if CORE_AVAILABLE:
            error = GenerationServiceError(f"Generation failed: {e!s}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=error.to_dict(),
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Generation failed: {e!s}",
            )


@router.get(
    "/generate/{generation_id}",
    response_model=GenerationResponse,
    summary="Get Generation Status",
    description="Get the status and result of a generation request",
)
async def get_generation_status(
    generation_id: str, service: GenerationService = Depends(get_generation_service)
) -> GenerationResponse:
    """Get the status of a generation request"""

    try:
        result = await service.get_generation_status(generation_id)
        if not result:
            if CORE_AVAILABLE:
                raise NotFoundError("Generation", generation_id)
            else:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Generation {generation_id} not found",
                )

        logger.debug(f"Retrieved generation status: {generation_id}")
        return result

    except NotFoundError as e:
        logger.warning(f"Generation not found: {generation_id}")
        if CORE_AVAILABLE:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=e.to_dict()
            )
        else:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except BaseServiceException as e:
        logger.error(f"Service error retrieving generation: {e}")
        if CORE_AVAILABLE:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=e.to_dict()
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        if CORE_AVAILABLE:
            error = GenerationServiceError(f"Failed to get generation status: {e!s}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=error.to_dict(),
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to get generation status: {e!s}",
            )


@router.delete(
    "/generate/{generation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Cancel Generation",
    description="Cancel a running generation request",
)
async def cancel_generation(
    generation_id: str, service: GenerationService = Depends(get_generation_service)
) -> None:
    """Cancel a generation request"""

    try:
        success = await service.cancel_generation(generation_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Generation {generation_id} not found or cannot be cancelled",
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to cancel generation: {e!s}",
        )


@router.get(
    "/generate/{generation_id}/quality",
    summary="Get Generation Quality Metrics",
    description="Get quality metrics for a specific generation",
)
async def get_generation_quality(
    generation_id: str, service: GenerationService = Depends(get_generation_service)
) -> dict[str, Any]:
    """Get quality metrics for a generation"""

    try:
        metrics = await service.get_generation_quality_metrics(generation_id)
        if not metrics:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Quality metrics for generation {generation_id} not found",
            )

        return metrics

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get quality metrics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get quality metrics: {e!s}",
        )


@router.get(
    "/statistics/quality",
    summary="Get Service Quality Statistics",
    description="Get overall service quality statistics",
)
async def get_quality_statistics(
    service: GenerationService = Depends(get_generation_service),
) -> dict[str, Any]:
    """Get service quality statistics"""

    try:
        stats = await service.get_service_quality_statistics()
        return stats

    except Exception as e:
        logger.error(f"Failed to get quality statistics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get quality statistics: {e!s}",
        )


@router.get(
    "/active",
    summary="List Active Generations",
    description="Get list of currently active generations",
)
async def list_active_generations(
    service: GenerationService = Depends(get_generation_service),
) -> dict[str, list[str]]:
    """List active generations"""

    try:
        active = await service.list_active_generations()
        return {"active_generations": active}

    except Exception as e:
        logger.error(f"Failed to list active generations: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list active generations: {e!s}",
        )


@router.get(
    "/templates",
    summary="List Generation Templates",
    description="Get available script generation templates",
)
async def list_templates() -> dict[str, list[dict[str, str]]]:
    """List available generation templates"""

    # TODO: Implement template management
    return {
        "templates": [
            {
                "id": "drama",
                "name": "Drama Script",
                "description": "Standard drama script format",
            },
            {
                "id": "comedy",
                "name": "Comedy Script",
                "description": "Comedy script with timing notes",
            },
            {
                "id": "documentary",
                "name": "Documentary Script",
                "description": "Documentary narration format",
            },
        ]
    }


# ========================================================================================
# Hybrid Workflow Endpoints
# ========================================================================================


@router.post(
    "/hybrid-script",
    response_model=HybridWorkflowResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Generate Script with Hybrid Workflow",
    description="Execute the complete LangGraph hybrid workflow for enhanced script generation",
)
@idempotent_endpoint(ttl_seconds=24 * 3600)  # 24 hour TTL for workflow requests
async def generate_hybrid_script(
    request: ScriptGenerationRequest,
    http_request: Request,
    service: GenerationService = Depends(get_generation_service),
) -> HybridWorkflowResponse:
    """Execute hybrid LangGraph workflow for script generation"""

    try:
        # Execute hybrid workflow
        workflow_response = await service.execute_hybrid_workflow(request)

        if CORE_AVAILABLE:
            logger.info(
                "Hybrid workflow initiated",
                extra={
                    "workflow_id": workflow_response.workflow_id,
                    "generation_id": workflow_response.generation_id,
                    "project_id": request.project_id,
                    "script_type": request.script_type.value,
                },
            )
        else:
            logger.info(f"Hybrid workflow initiated: {workflow_response.workflow_id}")

        return workflow_response

    except ValidationException as e:
        logger.warning(f"Validation error in hybrid workflow: {e}")
        if CORE_AVAILABLE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail=e.to_dict()
            )
        else:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except BaseServiceException as e:
        logger.error(f"Service error in hybrid workflow: {e}")
        if CORE_AVAILABLE:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=e.to_dict()
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
            )
    except ValueError as e:
        logger.warning(f"Invalid hybrid workflow request: {e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error in hybrid workflow: {e}")
        if CORE_AVAILABLE:
            error = GenerationServiceError(f"Hybrid workflow failed: {e!s}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=error.to_dict(),
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Hybrid workflow failed: {e!s}",
            )


@router.get(
    "/workflow/{workflow_id}/status",
    response_model=WorkflowStatusResponse,
    summary="Get Workflow Status",
    description="Get real-time status and progress of a running workflow",
)
async def get_workflow_status(
    workflow_id: str, service: GenerationService = Depends(get_generation_service)
) -> WorkflowStatusResponse:
    """Get real-time workflow status and progress"""

    try:
        status_response = await service.get_workflow_status(workflow_id)
        if not status_response:
            if CORE_AVAILABLE:
                raise NotFoundError("Workflow", workflow_id)
            else:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Workflow {workflow_id} not found",
                )

        logger.debug(f"Retrieved workflow status: {workflow_id}")
        return status_response

    except NotFoundError as e:
        logger.warning(f"Workflow not found: {workflow_id}")
        if CORE_AVAILABLE:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=e.to_dict()
            )
        else:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except BaseServiceException as e:
        logger.error(f"Service error retrieving workflow status: {e}")
        if CORE_AVAILABLE:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=e.to_dict()
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error retrieving workflow status: {e}")
        if CORE_AVAILABLE:
            error = GenerationServiceError(f"Failed to get workflow status: {e!s}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=error.to_dict(),
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to get workflow status: {e!s}",
            )


@router.post(
    "/custom-workflow",
    response_model=HybridWorkflowResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Execute Custom Workflow",
    description="Execute a custom workflow with user-defined nodes and parameters",
)
@idempotent_endpoint(ttl_seconds=24 * 3600)  # 24 hour TTL for custom workflows
async def execute_custom_workflow(
    request: CustomWorkflowRequest,
    http_request: Request,
    service: GenerationService = Depends(get_generation_service),
) -> HybridWorkflowResponse:
    """Execute custom workflow with user-defined configuration"""

    try:
        # Execute custom workflow
        workflow_response = await service.execute_custom_workflow(request)

        if CORE_AVAILABLE:
            logger.info(
                "Custom workflow initiated",
                extra={
                    "workflow_id": workflow_response.workflow_id,
                    "generation_id": workflow_response.generation_id,
                    "project_id": request.base_request.project_id,
                    "custom_nodes": len(request.custom_nodes),
                    "workflow_path": [node.value for node in request.workflow_path],
                },
            )
        else:
            logger.info(f"Custom workflow initiated: {workflow_response.workflow_id}")

        return workflow_response

    except ValidationException as e:
        logger.warning(f"Validation error in custom workflow: {e}")
        if CORE_AVAILABLE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail=e.to_dict()
            )
        else:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except BaseServiceException as e:
        logger.error(f"Service error in custom workflow: {e}")
        if CORE_AVAILABLE:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=e.to_dict()
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
            )
    except ValueError as e:
        logger.warning(f"Invalid custom workflow request: {e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error in custom workflow: {e}")
        if CORE_AVAILABLE:
            error = GenerationServiceError(f"Custom workflow failed: {e!s}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=error.to_dict(),
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Custom workflow failed: {e!s}",
            )


@router.delete(
    "/workflow/{workflow_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Cancel Workflow",
    description="Cancel a running workflow execution",
)
async def cancel_workflow(
    workflow_id: str, service: GenerationService = Depends(get_generation_service)
) -> None:
    """Cancel a running workflow"""

    try:
        success = await service.cancel_workflow(workflow_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Workflow {workflow_id} not found or cannot be cancelled",
            )

        logger.info(f"Workflow cancelled: {workflow_id}")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to cancel workflow {workflow_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to cancel workflow: {e!s}",
        )


@router.get(
    "/workflows/active",
    summary="List Active Workflows",
    description="Get list of currently active workflow executions",
)
async def list_active_workflows(
    service: GenerationService = Depends(get_generation_service),
) -> dict[str, Any]:
    """List all active workflows"""

    try:
        active_workflows = await service.list_active_workflows()
        return {
            "active_workflows": active_workflows,
            "total_active": len(active_workflows),
        }

    except Exception as e:
        logger.error(f"Failed to list active workflows: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list active workflows: {e!s}",
        )


@router.get(
    "/workflow-info",
    summary="Get Workflow Information",
    description="Get information about the LangGraph workflow system",
)
async def get_workflow_info(
    service: GenerationService = Depends(get_generation_service),
) -> dict[str, Any]:
    """Get workflow system information"""

    try:
        workflow_info = await service.get_workflow_info()
        langgraph_available = await service.is_langgraph_available()

        return {
            "workflow_info": workflow_info,
            "langgraph_available": langgraph_available,
            "capabilities": {
                "hybrid_workflow": langgraph_available,
                "custom_workflow": langgraph_available,
                "real_time_tracking": True,
                "quality_scoring": True,
                "multi_model_support": True,
                "rag_integration": workflow_info.get("rag_service_available", False),
            },
        }

    except Exception as e:
        logger.error(f"Failed to get workflow info: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get workflow info: {e!s}",
        )
