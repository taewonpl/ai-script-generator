"""
AI Script Generator v3.0 Shared Core Package

경량화된 서비스 간 공유 모듈
- DTO 스키마 (서비스 간 통신용)
- 공통 예외 클래스
- 유틸리티 함수
- 설정 도우미

각 서비스는 독립적인 SQLAlchemy 모델, 데이터베이스, 비즈니스 로직을 가집니다.
"""

__version__ = "3.0.0"
__author__ = "AI Script Generator Team"

# 주요 모듈 export
from .src import exceptions, schemas, utils

__all__ = ["__author__", "__version__", "exceptions", "schemas", "utils"]
