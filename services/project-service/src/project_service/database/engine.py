import os

from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

DATABASE_URL = os.getenv("PROJECT_SERVICE_DATABASE_URL", "sqlite:///./data/projects.db")
url = make_url(DATABASE_URL)
is_sqlite = url.get_backend_name() == "sqlite"
is_memory = is_sqlite and (url.database in (None, "", ":memory:"))

connect_args = {}
if is_sqlite:
    connect_args = {"check_same_thread": False, "timeout": 20}

engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
    poolclass=StaticPool if is_memory else None,
    echo=os.getenv("SQL_ECHO", "false").lower() in {"1", "true", "yes"},
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
