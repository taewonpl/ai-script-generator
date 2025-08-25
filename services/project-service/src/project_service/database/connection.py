import os
from collections.abc import Generator

from sqlalchemy.orm import Session

from ..models.base import Base
from .engine import SessionLocal, engine


def get_session() -> Session:
    return SessionLocal()


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _ensure_sqlite_dir() -> None:
    url = engine.url
    if url.get_backend_name() == "sqlite":
        db_path = url.database
        if db_path and db_path != ":memory:":
            abs_db_path = os.path.abspath(db_path)
            os.makedirs(os.path.dirname(abs_db_path), exist_ok=True)


def init_db() -> None:
    _ensure_sqlite_dir()
    Base.metadata.create_all(bind=engine)
    print("✅ Project Service database initialized")


def drop_all_tables() -> None:
    Base.metadata.drop_all(bind=engine)
    print("🗑️ All tables dropped")


def reset_db() -> None:
    drop_all_tables()
    init_db()
    print("🔄 Database reset completed")
