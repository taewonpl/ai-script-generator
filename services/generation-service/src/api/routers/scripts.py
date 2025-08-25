"""
Scripts Router - 스크립트 관리 API

생성된 스크립트 조회 및 관리 엔드포인트
"""

from fastapi import APIRouter

router = APIRouter(prefix="/scripts", tags=["scripts"])


@router.get("/health")
async def scripts_health():
    """스크립트 서비스 헬스체크"""
    return {"status": "healthy", "component": "scripts"}


@router.get("/")
async def list_scripts():
    """생성된 스크립트 목록"""
    # TODO: 실제 스크립트 목록 조회 로직 구현
    return {"scripts": [], "message": "Scripts list endpoint - implementation pending"}


@router.get("/{script_id}")
async def get_script(script_id: str):
    """스크립트 상세 조회"""
    # TODO: 실제 스크립트 조회 로직 구현
    return {
        "script_id": script_id,
        "message": "Script detail endpoint - implementation pending",
    }
