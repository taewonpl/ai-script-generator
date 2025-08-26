"""
Middleware setup for generation service
"""

from fastapi import FastAPI

from ..api.idempotency_middleware import IdempotencyMiddleware

try:
    from ai_script_core import get_service_logger

    logger = get_service_logger("generation-service.middleware")
except ImportError:
    import logging

    logger = logging.getLogger(__name__)


def setup_idempotency_middleware(app: FastAPI) -> None:
    """Setup idempotency middleware for the FastAPI app"""
    try:
        middleware = IdempotencyMiddleware(
            app=app,
            header_name="Idempotency-Key",
            ttl_seconds=24 * 3600,  # 24 hours
            methods={"POST", "PUT", "PATCH"},
            enabled_paths={
                "/api/v1/generations",
                "/generate",
                "/hybrid-script",
                "/custom-workflow",
            },
        )

        app.add_middleware(
            IdempotencyMiddleware,
            **{
                "header_name": "Idempotency-Key",
                "ttl_seconds": 24 * 3600,
                "methods": {"POST", "PUT", "PATCH"},
                "enabled_paths": {
                    "/api/v1/generations",
                    "/generate",
                    "/hybrid-script",
                    "/custom-workflow",
                },
            },
        )

        logger.info("Idempotency middleware configured successfully")

    except Exception as e:
        logger.error(f"Failed to setup idempotency middleware: {e}")
        raise


def setup_all_middleware(app: FastAPI) -> None:
    """Setup all middleware for the generation service"""
    setup_idempotency_middleware(app)
    # Add other middleware setup here as needed
