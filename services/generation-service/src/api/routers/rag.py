"""
RAG Router - 검색 증강 생성 API

문서 검색 및 RAG 기능 엔드포인트
"""

from fastapi import APIRouter

router = APIRouter(prefix="/rag", tags=["rag"])


@router.get("/health")
async def rag_health():
    """RAG 서비스 헬스체크"""
    return {"status": "healthy", "component": "rag"}


@router.post("/search")
async def search_documents():
    """문서 검색"""
    # TODO: 실제 검색 로직 구현
    return {"message": "RAG search endpoint - implementation pending"}


@router.post("/index")
async def index_document():
    """문서 인덱싱"""
    # TODO: 실제 인덱싱 로직 구현
    return {"message": "RAG indexing endpoint - implementation pending"}
