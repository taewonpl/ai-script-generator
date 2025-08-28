"""
Unit tests for Episode Commit System
Tests idempotency, rate limiting, validation, and error handling
"""

import pytest
import uuid
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

from fastapi.testclient import TestClient
from src.project_service.main import app

client = TestClient(app)

# Test data
VALID_PROJECT_ID = str(uuid.uuid4())
VALID_EPISODE_ID = str(uuid.uuid4())
VALID_COMMIT_ID = str(uuid.uuid4())

class TestCommitSystem:
    """Test suite for episode commit system"""

    def setup_method(self):
        """Setup test environment"""
        # Clear rate limiting cache
        from src.project_service.api.feedback import _commit_timestamps
        _commit_timestamps.clear()

    @pytest.fixture
    def mock_db_session(self):
        """Mock database session"""
        with patch('src.project_service.api.feedback.get_session') as mock:
            mock_session = MagicMock()
            mock.__enter__ = lambda x: mock_session
            mock.__exit__ = lambda *args: None
            mock.return_value = mock_session
            yield mock_session

    @pytest.fixture
    def mock_project_repo(self, mock_db_session):
        """Mock project repository with valid project"""
        with patch('src.project_service.api.feedback.ProjectRepository') as mock_repo:
            repo_instance = mock_repo.return_value
            
            # Mock project object
            mock_project = MagicMock()
            mock_project.id = VALID_PROJECT_ID
            repo_instance.get.return_value = mock_project
            
            yield repo_instance

    @pytest.fixture
    def mock_episode_repo(self, mock_db_session):
        """Mock episode repository with valid episode"""
        with patch('src.project_service.api.feedback.EpisodeRepository') as mock_repo:
            repo_instance = mock_repo.return_value
            
            # Mock episode object
            mock_episode = MagicMock()
            mock_episode.id = VALID_EPISODE_ID
            mock_episode.project_id = VALID_PROJECT_ID
            repo_instance.get.return_value = mock_episode
            
            yield repo_instance

    def test_successful_commit(self, mock_db_session, mock_project_repo, mock_episode_repo):
        """Test successful commit submission"""
        # Mock database responses
        mock_db_session.execute.side_effect = [
            # Check existing commit (none found)
            MagicMock(fetchone=lambda: [0]),
            # Create table (no return)
            None,
            # Insert commit (no return)
            None,
        ]

        payload = {
            "event": "commit_positive",
            "project_id": VALID_PROJECT_ID,
            "episode_id": VALID_EPISODE_ID,
            "commit_id": VALID_COMMIT_ID,
            "client_ts": datetime.utcnow().isoformat() + "Z"
        }

        response = client.post("/api/v1/feedback", json=payload)

        assert response.status_code == 200
        data = response.json()
        
        assert data["stored"] is True
        assert data["commit_id"] == VALID_COMMIT_ID
        assert "timestamp" in data
        assert "request_id" in data
        assert "trace_id" in data

        # Verify database interactions
        mock_db_session.execute.assert_called()
        mock_db_session.commit.assert_called_once()

    def test_duplicate_commit_idempotency(self, mock_db_session, mock_project_repo, mock_episode_repo):
        """Test duplicate commit_id returns stored: false"""
        # Mock existing commit found
        mock_db_session.execute.return_value = MagicMock(fetchone=lambda: [1])

        payload = {
            "event": "commit_positive",
            "project_id": VALID_PROJECT_ID,
            "episode_id": VALID_EPISODE_ID,
            "commit_id": VALID_COMMIT_ID,
            "client_ts": datetime.utcnow().isoformat() + "Z"
        }

        response = client.post("/api/v1/feedback", json=payload)

        assert response.status_code == 200
        data = response.json()
        
        assert data["stored"] is False
        assert data["commit_id"] == VALID_COMMIT_ID

        # Should not commit to database
        mock_db_session.commit.assert_not_called()

    def test_rate_limiting(self, mock_db_session, mock_project_repo, mock_episode_repo):
        """Test rate limiting prevents rapid commits"""
        # First commit succeeds
        mock_db_session.execute.side_effect = [
            MagicMock(fetchone=lambda: [0]),  # No existing commit
            None,  # Create table
            None,  # Insert commit
        ]

        payload = {
            "event": "commit_positive",
            "project_id": VALID_PROJECT_ID,
            "episode_id": VALID_EPISODE_ID,
            "commit_id": str(uuid.uuid4()),
            "client_ts": datetime.utcnow().isoformat() + "Z"
        }

        response1 = client.post("/api/v1/feedback", json=payload)
        assert response1.status_code == 200

        # Immediate second commit should be rate limited
        payload["commit_id"] = str(uuid.uuid4())  # Different commit_id
        response2 = client.post("/api/v1/feedback", json=payload)
        
        assert response2.status_code == 429
        data = response2.json()
        assert "RATE_LIMITED" in data["detail"]["code"]
        assert "retry_after" in data["detail"]
        assert "Retry-After" in response2.headers

    def test_invalid_event_type(self):
        """Test unsupported event types are rejected"""
        payload = {
            "event": "invalid_event",
            "project_id": VALID_PROJECT_ID,
            "episode_id": VALID_EPISODE_ID,
            "commit_id": VALID_COMMIT_ID,
            "client_ts": datetime.utcnow().isoformat() + "Z"
        }

        response = client.post("/api/v1/feedback", json=payload)
        
        assert response.status_code == 400
        data = response.json()
        assert "UNSUPPORTED_EVENT" in data["detail"]["code"]

    def test_project_not_found(self, mock_db_session, mock_episode_repo):
        """Test project validation - project not found"""
        with patch('src.project_service.api.feedback.ProjectRepository') as mock_repo:
            repo_instance = mock_repo.return_value
            repo_instance.get.return_value = None  # Project not found

            payload = {
                "event": "commit_positive",
                "project_id": str(uuid.uuid4()),
                "episode_id": VALID_EPISODE_ID,
                "commit_id": VALID_COMMIT_ID,
                "client_ts": datetime.utcnow().isoformat() + "Z"
            }

            response = client.post("/api/v1/feedback", json=payload)
            
            assert response.status_code == 404
            data = response.json()
            assert "PROJECT_NOT_FOUND" in data["detail"]["code"]

    def test_episode_not_found(self, mock_db_session, mock_project_repo):
        """Test episode validation - episode not found"""
        with patch('src.project_service.api.feedback.EpisodeRepository') as mock_repo:
            repo_instance = mock_repo.return_value
            repo_instance.get.return_value = None  # Episode not found

            payload = {
                "event": "commit_positive",
                "project_id": VALID_PROJECT_ID,
                "episode_id": str(uuid.uuid4()),
                "commit_id": VALID_COMMIT_ID,
                "client_ts": datetime.utcnow().isoformat() + "Z"
            }

            response = client.post("/api/v1/feedback", json=payload)
            
            assert response.status_code == 404
            data = response.json()
            assert "EPISODE_NOT_FOUND" in data["detail"]["code"]

    def test_episode_project_mismatch(self, mock_db_session, mock_project_repo, mock_episode_repo):
        """Test episode belongs to different project"""
        # Mock episode belonging to different project
        mock_episode_repo.get.return_value.project_id = str(uuid.uuid4())

        payload = {
            "event": "commit_positive",
            "project_id": VALID_PROJECT_ID,
            "episode_id": VALID_EPISODE_ID,
            "commit_id": VALID_COMMIT_ID,
            "client_ts": datetime.utcnow().isoformat() + "Z"
        }

        response = client.post("/api/v1/feedback", json=payload)
        
        assert response.status_code == 400
        data = response.json()
        assert "PROJECT_MISMATCH" in data["detail"]["code"]

    def test_race_condition_handling(self, mock_db_session, mock_project_repo, mock_episode_repo):
        """Test race condition where commit_id is inserted between check and insert"""
        from sqlalchemy.exc import IntegrityError
        
        # Mock check shows no existing commit, but insert fails due to race condition
        mock_db_session.execute.side_effect = [
            MagicMock(fetchone=lambda: [0]),  # No existing commit initially
            None,  # Create table succeeds
            IntegrityError("UNIQUE constraint failed: episode_commits.commit_id", None, None),  # Insert fails
        ]

        payload = {
            "event": "commit_positive",
            "project_id": VALID_PROJECT_ID,
            "episode_id": VALID_EPISODE_ID,
            "commit_id": VALID_COMMIT_ID,
            "client_ts": datetime.utcnow().isoformat() + "Z"
        }

        response = client.post("/api/v1/feedback", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        assert data["stored"] is False  # Should handle race condition gracefully

    def test_get_episode_commits(self, mock_db_session):
        """Test retrieving commit history for an episode"""
        # Mock commit history data
        mock_commits = [
            ("commit-1", "commit_positive", "2024-01-01T10:00:00Z", "2024-01-01T10:00:01Z", 
             "req-1", "trace-1", datetime(2024, 1, 1, 10, 0, 1)),
            ("commit-2", "commit_positive", "2024-01-01T09:00:00Z", "2024-01-01T09:00:01Z", 
             "req-2", "trace-2", datetime(2024, 1, 1, 9, 0, 1)),
        ]
        mock_db_session.execute.return_value = mock_commits

        response = client.get(f"/api/v1/episodes/{VALID_EPISODE_ID}/commits")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["episode_id"] == VALID_EPISODE_ID
        assert len(data["commits"]) == 2
        assert data["total"] == 2
        
        # Check first commit details
        commit = data["commits"][0]
        assert commit["commit_id"] == "commit-1"
        assert commit["event_type"] == "commit_positive"

    def test_missing_required_fields(self):
        """Test validation of required fields"""
        incomplete_payload = {
            "event": "commit_positive",
            "project_id": VALID_PROJECT_ID,
            # Missing episode_id, commit_id, client_ts
        }

        response = client.post("/api/v1/feedback", json=incomplete_payload)
        assert response.status_code == 422  # Validation error

    def test_invalid_uuid_format(self):
        """Test handling of invalid UUID formats"""
        payload = {
            "event": "commit_positive",
            "project_id": "invalid-uuid",
            "episode_id": VALID_EPISODE_ID,
            "commit_id": VALID_COMMIT_ID,
            "client_ts": datetime.utcnow().isoformat() + "Z"
        }

        response = client.post("/api/v1/feedback", json=payload)
        # Should still process (UUID validation is not enforced at API level)
        # Validation happens at business logic level

    @pytest.mark.parametrize("client_ts", [
        "invalid-timestamp",
        "2024-13-40T25:70:70Z",  # Invalid date
        "",
    ])
    def test_invalid_timestamps(self, client_ts, mock_db_session, mock_project_repo, mock_episode_repo):
        """Test handling of various invalid timestamp formats"""
        payload = {
            "event": "commit_positive",
            "project_id": VALID_PROJECT_ID,
            "episode_id": VALID_EPISODE_ID,
            "commit_id": VALID_COMMIT_ID,
            "client_ts": client_ts
        }

        # API should still accept it (timestamp validation is not strict)
        # But we can log warnings for monitoring
        mock_db_session.execute.side_effect = [
            MagicMock(fetchone=lambda: [0]),
            None,
            None,
        ]

        response = client.post("/api/v1/feedback", json=payload)
        # Should process successfully regardless of timestamp format
        assert response.status_code in [200, 422]  # 422 for validation errors

if __name__ == "__main__":
    pytest.main([__file__, "-v"])