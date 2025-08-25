"""
AI Script Generator - Project Service

A microservice for managing projects, episodes, and metadata in the AI Script Generator platform.
"""

__version__ = "0.1.0"
__author__ = "AI Script Generator Team"
__email__ = "team@aiscriptgen.com"

from .database import SessionLocal, engine, get_db, get_session, init_db
from .models import (
    Base,
    Episode,
    EpisodeStatus,
    Project,
    ProjectMetadata,
    ProjectStatus,
    ProjectType,
    TimestampMixin,
)
from .repositories import BaseRepository, ProjectRepository

__all__ = [
    # Version info
    "__version__",
    "__author__",
    "__email__",
    # Database
    "engine",
    "SessionLocal",
    "get_db",
    "get_session",
    "init_db",
    # Models
    "Base",
    "TimestampMixin",
    "Project",
    "ProjectType",
    "ProjectStatus",
    "Episode",
    "EpisodeStatus",
    "ProjectMetadata",
    # Repositories
    "BaseRepository",
    "ProjectRepository",
]
