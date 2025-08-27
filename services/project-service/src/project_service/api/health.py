"""
Health Check API Router
"""

from typing import Any

from fastapi import APIRouter, Depends

# Temporary classes until shared core is properly imported
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..database import get_db


class HealthCheckDTO(BaseModel):
    service_name: str
    status: str
    version: str
    details: dict[str, Any]


class APIResponseDTO(BaseModel):
    success: bool = True
    message: str = "Success"
    data: Any = None


router = APIRouter(prefix="/health", tags=["Health"])


@router.get("/", response_model=APIResponseDTO)
async def health_check() -> APIResponseDTO:
    """기본 헬스체크"""
    health_data = HealthCheckDTO(
        service_name="project-service",
        status="healthy",
        version="1.0.0",
        details={"description": "AI Script Generator Project Service", "port": 8001},
    )

    return APIResponseDTO(
        success=True, message="Project Service is healthy", data=health_data
    )


@router.get("/database", response_model=APIResponseDTO)
async def database_health_check(db: Session = Depends(get_db)) -> APIResponseDTO:
    """데이터베이스 헬스체크"""
    try:
        # 간단한 데이터베이스 쿼리로 연결 확인
        from sqlalchemy import text

        db.execute(text("SELECT 1"))

        health_data = HealthCheckDTO(
            service_name="project-service",
            status="healthy",
            version="1.0.0",
            details={"database": "connected", "database_type": "sqlite"},
        )

        return APIResponseDTO(
            success=True, message="Database connection is healthy", data=health_data
        )
    except Exception as e:
        health_data = HealthCheckDTO(
            service_name="project-service",
            status="unhealthy",
            version="1.0.0",
            details={"database": "disconnected", "error": str(e)},
        )

        return APIResponseDTO(
            success=False, message="Database connection failed", data=health_data
        )
