"""
Database Connection - 데이터베이스 연결 관리

SQLAlchemy 기반 데이터베이스 연결 및 초기화
"""

import os

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# 데이터베이스 URL (환경 변수에서 읽기)
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./data/scripts.db")

# SQLAlchemy 엔진 생성
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {},
)

# 세션 팩토리 생성
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base 클래스 생성
Base = declarative_base()


def get_db():
    """데이터베이스 세션 의존성"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """데이터베이스 초기화"""
    # 데이터베이스 테이블 생성
    Base.metadata.create_all(bind=engine)
    print("✅ Database tables created")
