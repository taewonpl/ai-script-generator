"""
FastAPI dependencies for the Generation Service
"""

from fastapi import Depends, HTTPException, status
from typing import Any, Dict, Optional

# Mock project dependency for now
class MockProject:
    """Mock project model for testing"""
    def __init__(self, project_id: str):
        self.id = project_id
        self.name = f"Project {project_id}"


async def get_current_project() -> MockProject:
    """
    Dependency to get current project context
    In production, this would validate project access from headers/auth
    """
    # For now, return a mock project
    return MockProject("default-project")


# Additional dependencies can be added here as needed