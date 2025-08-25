"""
Generation Router - AI 콘텐츠 생성 API

AI 모델을 사용한 콘텐츠 생성 엔드포인트
"""

from fastapi import APIRouter

router = APIRouter(prefix="/generation", tags=["generation"])


@router.get("/health")
async def generation_health():
    """생성 서비스 헬스체크"""
    return {"status": "healthy", "component": "generation"}


@router.get("/models")
async def list_models():
    """사용 가능한 AI 모델 목록"""
    return {
        "models": [
            {"name": "openai", "status": "available"},
            {"name": "anthropic", "status": "available"},
        ]
    }


@router.post("/generate")
async def generate_content():
    """AI 콘텐츠 생성"""
    # TODO: 실제 생성 로직 구현
    return {"message": "Generation endpoint - implementation pending"}
