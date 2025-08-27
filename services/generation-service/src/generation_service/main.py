"""
FastAPI application for Generation Service with Core Module integration
"""

import logging

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from generation_service.api import generate, health, metrics, rag, sse_generation
from generation_service.config_loader import settings
from generation_service.middleware import setup_security_middleware

# Import Core Module utilities
try:
    from ai_script_core import (
        BaseServiceException,
        exception_handler,
        get_service_logger,
    )

    CORE_AVAILABLE = True
    # Set up core logging
    logger = get_service_logger("generation-service.main")
    logger.info("Core Module loaded successfully")
except (ImportError, RuntimeError) as e:
    CORE_AVAILABLE = False
    logger = logging.getLogger(__name__)
    logger.warning(f"Core Module not available, using fallback logging: {e}")

app = FastAPI(
    title="AI Script Generator - Generation Service",
    description="AI-powered script generation service with Core Module integration",
    version="3.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Add Core Module exception handler if available
if CORE_AVAILABLE:

    @app.exception_handler(BaseServiceException)
    async def core_exception_handler(request, exc):
        logger.error(f"Core exception: {exc}")
        return await exception_handler(request, exc)

    logger.info("Core Module exception handlers registered")

app.add_middleware(
    CORSMiddleware,
    allow_origins=getattr(settings, "cors_origins", []),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Setup security middleware
setup_security_middleware(
    app,
    enable_rate_limiting=True,
    rate_limit_calls=getattr(settings, "rate_limit_calls", 100),
    rate_limit_period=getattr(settings, "rate_limit_period", 60),
)

# Log middleware setup
logger.info(
    f"CORS middleware configured with origins: {getattr(settings, 'cors_origins', [])}"
)

app.include_router(health.router, prefix="/api/v1", tags=["health"])
app.include_router(metrics.router, prefix="/api/v1", tags=["observability"])
app.include_router(generate.router, prefix="/api/v1", tags=["generation"])
app.include_router(rag.router, prefix="/api/v1/rag", tags=["rag"])
app.include_router(sse_generation.router, prefix="/api/v1", tags=["sse-generation"])

logger.info("API routers registered")


@app.get("/")
async def root():
    """Root endpoint with service information"""
    return {
        "service": "Generation Service",
        "version": "3.0.0",
        "status": "running",
        "core_module": CORE_AVAILABLE,
        "features": [
            "Multi-AI Provider Support",
            "OpenAI GPT-4o",
            "Anthropic Claude 3.5 Sonnet",
            "Local Llama Models",
            "LangGraph Hybrid Workflows",
            "Real-time Workflow Tracking",
            "ChromaDB RAG System",
            "Semantic Document Search",
            "Quality Scoring System",
            "Core Module Integration" if CORE_AVAILABLE else "Standalone Mode",
        ],
    }


@app.on_event("startup")
async def startup_event():
    """Application startup event"""
    logger.info("Generation Service starting up...")
    logger.info(f"Port: {settings.PORT}")
    logger.info(f"Debug mode: {settings.DEBUG}")
    logger.info(f"Core Module: {'Available' if CORE_AVAILABLE else 'Not Available'}")

    # Log configuration status
    ai_configs = settings.get_ai_provider_config()
    logger.info(f"AI Providers configured: {list(ai_configs.keys())}")


@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown event"""
    logger.info("Generation Service shutting down...")


if __name__ == "__main__":
    uvicorn.run(
        "generation_service.main:app",
        host="0.0.0.0",
        port=settings.PORT,
        reload=settings.DEBUG,
    )
