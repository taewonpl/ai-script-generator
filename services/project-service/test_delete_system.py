"""
Unit tests for Project Delete System
Tests idempotency, business logic guards, and error handling
"""

import pytest
import uuid
from datetime import datetime
from unittest.mock import patch, MagicMock

from fastapi.testclient import TestClient
from src.project_service.main import app

client = TestClient(app)

# Test data
VALID_PROJECT_ID = str(uuid.uuid4())
VALID_DELETE_ID = str(uuid.uuid4())

class TestProjectDeleteSystem:
    """Test suite for production-grade project deletion"""

    def setup_method(self):
        """Setup test environment"""
        pass

    @pytest.fixture
    def mock_db_session(self):
        """Mock database session"""
        with patch('src.project_service.api.projects.get_db') as mock:
            mock_session = MagicMock()
            mock.__enter__ = lambda x: mock_session
            mock.__exit__ = lambda *args: None
            mock.return_value = mock_session
            yield mock_session

    @pytest.fixture
    def mock_project_service(self, mock_db_session):
        """Mock project service"""
        with patch('src.project_service.api.projects.ProjectService') as mock_service:
            service_instance = mock_service.return_value
            
            # Mock project object
            mock_project = MagicMock()
            mock_project.id = VALID_PROJECT_ID
            mock_project.name = "Test Project"
            service_instance.get_project.return_value = mock_project
            service_instance.delete_project.return_value = True
            
            yield service_instance

    def test_successful_deletion(self, mock_db_session, mock_project_service):
        """Test successful project deletion with idempotency tracking"""
        # Mock database responses
        mock_db_session.execute.side_effect = [
            # Check existing delete_id (none found)
            MagicMock(fetchone=lambda: [0]),
            # Create table (no return)
            None,
            # No active generation jobs
            MagicMock(fetchone=lambda: [0]),
            # Record deletion
            None,
        ]

        headers = {"X-Delete-Id": VALID_DELETE_ID}
        response = client.delete(f"/api/v1/projects/{VALID_PROJECT_ID}", headers=headers)

        assert response.status_code == 204
        assert response.text == ""  # No content for 204

        # Verify database interactions
        mock_db_session.execute.assert_called()
        mock_db_session.commit.assert_called_once()
        mock_project_service.delete_project.assert_called_once_with(VALID_PROJECT_ID)

    def test_idempotent_deletion(self, mock_db_session, mock_project_service):
        """Test duplicate delete_id returns success without deletion"""
        # Mock existing delete_id found
        mock_db_session.execute.return_value = MagicMock(fetchone=lambda: [1])

        headers = {"X-Delete-Id": VALID_DELETE_ID}
        response = client.delete(f"/api/v1/projects/{VALID_PROJECT_ID}", headers=headers)

        assert response.status_code == 204

        # Should not perform actual deletion
        mock_project_service.delete_project.assert_not_called()
        # Should not commit changes
        mock_db_session.commit.assert_not_called()

    def test_project_not_found_treated_as_success(self, mock_db_session, mock_project_service):
        """Test 404 project not found is treated as successful deletion"""
        from src.project_service.services.project_service import NotFoundError
        
        # Mock no existing delete_id
        mock_db_session.execute.side_effect = [
            MagicMock(fetchone=lambda: [0]),  # No existing delete_id
            None,  # Create table
            None,  # Record deletion
        ]
        
        # Mock project not found
        mock_project_service.get_project.side_effect = NotFoundError("Project not found")

        headers = {"X-Delete-Id": VALID_DELETE_ID}
        response = client.delete(f"/api/v1/projects/{VALID_PROJECT_ID}", headers=headers)

        assert response.status_code == 204
        
        # Should still record the deletion attempt for idempotency
        mock_db_session.commit.assert_called_once()

    def test_active_generation_jobs_conflict(self, mock_db_session, mock_project_service):
        """Test 409 conflict when active generation jobs exist"""
        # Mock database responses
        mock_db_session.execute.side_effect = [
            # Check existing delete_id (none found)
            MagicMock(fetchone=lambda: [0]),
            # Create table (no return)
            None,
            # Active generation jobs found
            MagicMock(fetchone=lambda: [2]),  # 2 active jobs
        ]

        headers = {"X-Delete-Id": VALID_DELETE_ID}
        response = client.delete(f"/api/v1/projects/{VALID_PROJECT_ID}", headers=headers)

        assert response.status_code == 409
        data = response.json()
        assert data["detail"]["code"] == "ACTIVE_GENERATION_JOBS"
        assert "활성 생성 작업" in data["detail"]["message"]
        assert data["detail"]["active_jobs_count"] == 2

        # Should not perform deletion
        mock_project_service.delete_project.assert_not_called()

    def test_missing_delete_id_generates_new_one(self, mock_db_session, mock_project_service):
        """Test that missing X-Delete-Id header generates a new one"""
        # Mock database responses for successful deletion
        mock_db_session.execute.side_effect = [
            MagicMock(fetchone=lambda: [0]),  # No existing delete_id
            None,  # Create table
            MagicMock(fetchone=lambda: [0]),  # No active jobs
            None,  # Record deletion
        ]

        # No X-Delete-Id header provided
        response = client.delete(f"/api/v1/projects/{VALID_PROJECT_ID}")

        assert response.status_code == 204
        mock_project_service.delete_project.assert_called_once()

    def test_service_deletion_failure(self, mock_db_session, mock_project_service):
        """Test handling of service layer deletion failure"""
        # Mock database setup but service fails
        mock_db_session.execute.side_effect = [
            MagicMock(fetchone=lambda: [0]),  # No existing delete_id
            None,  # Create table
            MagicMock(fetchone=lambda: [0]),  # No active jobs
        ]
        
        # Mock service deletion failure
        mock_project_service.delete_project.return_value = False

        headers = {"X-Delete-Id": VALID_DELETE_ID}
        response = client.delete(f"/api/v1/projects/{VALID_PROJECT_ID}", headers=headers)

        assert response.status_code == 500
        data = response.json()
        assert data["detail"]["code"] == "DELETION_FAILED"
        assert "프로젝트 삭제에 실패했습니다" in data["detail"]["message"]

    def test_database_error_handling(self, mock_db_session, mock_project_service):
        """Test handling of database errors during deletion"""
        # Mock database error
        mock_db_session.execute.side_effect = Exception("Database connection failed")

        headers = {"X-Delete-Id": VALID_DELETE_ID}
        response = client.delete(f"/api/v1/projects/{VALID_PROJECT_ID}", headers=headers)

        assert response.status_code == 500
        data = response.json()
        assert data["detail"]["code"] == "INTERNAL_ERROR"

    def test_structured_logging_context(self, mock_db_session, mock_project_service):
        """Test that proper logging context is included"""
        # Mock successful deletion
        mock_db_session.execute.side_effect = [
            MagicMock(fetchone=lambda: [0]),  # No existing delete_id
            None,  # Create table
            MagicMock(fetchone=lambda: [0]),  # No active jobs
            None,  # Record deletion
        ]

        headers = {"X-Delete-Id": VALID_DELETE_ID}
        
        with patch('src.project_service.api.projects.logger') as mock_logger:
            response = client.delete(f"/api/v1/projects/{VALID_PROJECT_ID}", headers=headers)
            
            assert response.status_code == 204
            
            # Verify structured logging was called
            assert mock_logger.info.call_count >= 2  # At least start and success logs
            
            # Check log context structure
            first_call_args = mock_logger.info.call_args_list[0]
            log_context = first_call_args[1]['extra']  # extra keyword argument
            
            assert 'action' in log_context
            assert 'project_id' in log_context
            assert 'delete_id' in log_context
            assert 'request_id' in log_context
            assert 'trace_id' in log_context
            assert 'timestamp' in log_context

    def test_generation_jobs_table_missing_continues_deletion(self, mock_db_session, mock_project_service):
        """Test that missing generation_jobs table doesn't block deletion"""
        # Mock responses where generation jobs query fails but deletion continues
        mock_db_session.execute.side_effect = [
            MagicMock(fetchone=lambda: [0]),  # No existing delete_id
            None,  # Create table
            Exception("no such table: generation_jobs"),  # Generation jobs table missing
            None,  # Record deletion (continues despite error)
        ]

        headers = {"X-Delete-Id": VALID_DELETE_ID}
        response = client.delete(f"/api/v1/projects/{VALID_PROJECT_ID}", headers=headers)

        assert response.status_code == 204
        mock_project_service.delete_project.assert_called_once()

    @pytest.mark.parametrize("delete_id", [
        "valid-uuid-string",
        "custom-delete-id-123", 
        str(uuid.uuid4()),
    ])
    def test_various_delete_id_formats(self, delete_id, mock_db_session, mock_project_service):
        """Test handling of various delete_id formats"""
        # Mock successful deletion
        mock_db_session.execute.side_effect = [
            MagicMock(fetchone=lambda: [0]),
            None,
            MagicMock(fetchone=lambda: [0]),
            None,
        ]

        headers = {"X-Delete-Id": delete_id}
        response = client.delete(f"/api/v1/projects/{VALID_PROJECT_ID}", headers=headers)
        
        assert response.status_code == 204

    def test_concurrent_deletion_race_condition(self, mock_db_session, mock_project_service):
        """Test race condition handling when same delete_id used concurrently"""
        # First request sees no existing delete_id, second request sees existing
        call_count = [0]
        
        def mock_execute_side_effect(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                # First call - check existing (none found initially)
                return MagicMock(fetchone=lambda: [0])
            elif call_count[0] == 2:
                # Create table
                return None
            else:
                # Subsequent calls
                return MagicMock(fetchone=lambda: [0])
        
        mock_db_session.execute.side_effect = mock_execute_side_effect

        headers = {"X-Delete-Id": VALID_DELETE_ID}
        
        # First request should succeed
        response1 = client.delete(f"/api/v1/projects/{VALID_PROJECT_ID}", headers=headers)
        assert response1.status_code == 204
        
        # Reset mock for second request
        call_count[0] = 0
        mock_db_session.execute.side_effect = [
            MagicMock(fetchone=lambda: [1]),  # Found existing delete_id
        ]
        
        # Second request with same delete_id should be idempotent
        response2 = client.delete(f"/api/v1/projects/{VALID_PROJECT_ID}", headers=headers)
        assert response2.status_code == 204

if __name__ == "__main__":
    pytest.main([__file__, "-v"])