"""
Integration tests for analytics API
Tests K-anonymity protection, privacy controls, and data aggregation
"""

import json
import pytest
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from sqlalchemy import text

from project_service.main import app
from project_service.database import get_session


client = TestClient(app)


@pytest.fixture
def sample_behavior_events():
    """Create sample behavior events for testing"""
    events = []
    base_time = datetime.utcnow() - timedelta(days=3)
    
    # Create events from multiple users to meet K-anonymity threshold
    for user_idx in range(6):  # 6 users > K=5 threshold
        for event_idx in range(5):  # 5 events per user
            event = {
                "schema_version": "1.0",
                "event_id": f"test-event-{user_idx}-{event_idx}",
                "seq": event_idx + 1,
                "event": "accept_partial" if event_idx % 2 == 0 else "reject_partial",
                "project_id": "test-project-123",
                "episode_id": f"test-episode-{user_idx}",
                "commit_id": f"commit-{user_idx}-{event_idx}",
                "ts_client": (base_time + timedelta(hours=event_idx)).isoformat(),
                "ts_client_hr": 1000.0 + event_idx * 100,
                "client_ts": (base_time + timedelta(hours=event_idx)).isoformat(),
                "session_id": f"session-{user_idx}",
                "page_id": f"page-{user_idx}-{event_idx}",
                "editor_scope_id": f"scope-{user_idx}",
                "actor_id_hash": f"user-hash-{user_idx}",
                "request_id": f"req-{user_idx}-{event_idx}",
                "trace_id": f"trace-{user_idx}-{event_idx}",
                "ua_hash": f"ua-hash-{user_idx}",
                "tz_offset": -480,  # PST
                "behavior_context": {
                    "selection_length": 100 + event_idx * 10,
                    "attempt_count": event_idx + 1,
                    "time_spent": 5.5 + event_idx,
                    "ui_element": "accept_button" if event_idx % 2 == 0 else "reject_button"
                },
                "content_data": {
                    "event_type": "accept_partial" if event_idx % 2 == 0 else "reject_partial",
                    "latency_since_preview_ms": 1200 + event_idx * 100,
                    "range_start": 0,
                    "range_end": 100 + event_idx * 10,
                    "selection_length": 100 + event_idx * 10
                }
            }
            events.append(event)
    
    return events


@pytest.fixture
def setup_test_data(sample_behavior_events):
    """Insert sample events into database for testing"""
    with get_session() as db:
        # Clean up any existing test data
        db.execute(text("DELETE FROM behavior_events WHERE project_id = 'test-project-123'"))
        db.commit()
        
        # Insert sample events via API to ensure proper validation
        for event in sample_behavior_events:
            response = client.post("/api/v1/feedback", json=event)
            assert response.status_code in [200, 403]  # 403 for rate limiting is ok
    
    yield
    
    # Cleanup
    with get_session() as db:
        db.execute(text("DELETE FROM behavior_events WHERE project_id = 'test-project-123'"))
        db.commit()


class TestAnalyticsAPI:
    """Test analytics API endpoints"""

    def test_behavior_patterns_with_sufficient_data(self, setup_test_data):
        """Test analytics patterns endpoint with sufficient data for K-anonymity"""
        response = client.get(
            "/api/v1/analytics/patterns", 
            params={
                "project_id": "test-project-123",
                "time_window": "7d"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert "project_id" in data
        assert "total_events" in data
        assert "unique_users" in data
        assert "regeneration_patterns" in data
        assert "satisfaction_metrics" in data
        assert "k_anonymity_compliant" in data
        
        # Verify privacy compliance
        assert data["k_anonymity_compliant"] is True
        assert data["unique_users"] >= 5  # Meets K-anonymity threshold
        
        # Verify no text content in response
        def check_no_text_content(obj, path=""):
            if isinstance(obj, dict):
                for key, value in obj.items():
                    assert "content" not in key.lower() or isinstance(value, (int, float, bool))
                    assert "text" not in key.lower() or isinstance(value, (int, float, bool))
                    assert "body" not in key.lower() or isinstance(value, (int, float, bool))
                    if isinstance(value, dict):
                        check_no_text_content(value, f"{path}.{key}")
            elif isinstance(obj, list):
                for i, item in enumerate(obj):
                    check_no_text_content(item, f"{path}[{i}]")
        
        check_no_text_content(data)

    def test_behavior_patterns_insufficient_data(self):
        """Test analytics patterns endpoint with insufficient data for K-anonymity"""
        # Create minimal test data (less than K=5 users)
        with get_session() as db:
            db.execute(text("DELETE FROM behavior_events WHERE project_id = 'test-project-minimal'"))
            
            # Insert events from only 3 users (< K=5)
            for user_idx in range(3):
                db.execute(text("""
                    INSERT INTO behavior_events 
                    (event_id, schema_version, seq, event_type, project_id, episode_id,
                     ts_client, ts_client_hr, session_id, page_id, editor_scope_id,
                     actor_id_hash, tz_offset, behavior_context, content_data)
                    VALUES (:event_id, '1.0', 1, 'accept_partial', 'test-project-minimal', 'ep1',
                            :ts_client, 1000.0, 'session1', 'page1', 'scope1',
                            :actor_id_hash, -480, '{}', '{}')
                """), {
                    "event_id": f"minimal-event-{user_idx}",
                    "ts_client": datetime.utcnow().isoformat(),
                    "actor_id_hash": f"user-hash-minimal-{user_idx}"
                })
            db.commit()
        
        response = client.get(
            "/api/v1/analytics/patterns", 
            params={
                "project_id": "test-project-minimal",
                "time_window": "7d"
            }
        )
        
        # Should return 403 due to insufficient data for K-anonymity
        assert response.status_code == 403
        error_data = response.json()
        assert error_data["detail"]["code"] == "INSUFFICIENT_DATA"

    def test_event_metrics_endpoint(self, setup_test_data):
        """Test event metrics endpoint"""
        response = client.get(
            "/api/v1/analytics/events",
            params={
                "project_id": "test-project-123",
                "time_window": "7d"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert isinstance(data, list)
        
        # Verify each metric entry
        for metric in data:
            assert "event_type" in metric
            assert "count" in metric
            assert "time_period" in metric
            assert isinstance(metric["count"], int)
            assert metric["count"] > 0

    def test_analytics_stats_endpoint(self):
        """Test general analytics statistics endpoint"""
        response = client.get("/api/v1/analytics/stats")
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        required_fields = [
            "total_sessions", "total_events", "active_projects",
            "data_quality_score", "k_anonymity_compliance_rate", "last_updated"
        ]
        
        for field in required_fields:
            assert field in data
        
        # Verify data types
        assert isinstance(data["total_sessions"], int)
        assert isinstance(data["total_events"], int)
        assert isinstance(data["active_projects"], int)
        assert isinstance(data["data_quality_score"], (int, float))
        assert isinstance(data["k_anonymity_compliance_rate"], (int, float))
        
        # Verify ranges
        assert 0 <= data["data_quality_score"] <= 1
        assert 0 <= data["k_anonymity_compliance_rate"] <= 1

    def test_invalid_time_window(self):
        """Test analytics endpoints with invalid time window"""
        response = client.get(
            "/api/v1/analytics/patterns",
            params={
                "project_id": "test-project-123",
                "time_window": "invalid"
            }
        )
        
        assert response.status_code == 400
        error_data = response.json()
        assert error_data["detail"]["code"] == "INVALID_TIME_WINDOW"

    def test_text_free_validation_in_feedback_api(self):
        """Test that feedback API rejects events with text content"""
        event_with_text = {
            "schema_version": "1.0",
            "event_id": "test-text-validation",
            "seq": 1,
            "event": "accept_partial",
            "project_id": "test-project-123",
            "episode_id": "test-episode-text",
            "commit_id": "test-commit-text",
            "ts_client": datetime.utcnow().isoformat(),
            "ts_client_hr": 1000.0,
            "client_ts": datetime.utcnow().isoformat(),
            "session_id": "session-text-test",
            "page_id": "page-text-test",
            "editor_scope_id": "scope-text-test",
            "tz_offset": -480,
            "behavior_context": {
                "selection_length": 100,
                "content": "This is forbidden text content that should be rejected"
            }
        }
        
        response = client.post("/api/v1/feedback", json=event_with_text)
        
        # Should be rejected due to text content
        assert response.status_code == 400
        error_data = response.json()
        assert error_data["detail"]["code"] == "FORBIDDEN_TEXT_CONTENT"

    def test_valid_behavior_event_acceptance(self):
        """Test that valid behavior events are accepted"""
        valid_event = {
            "schema_version": "1.0",
            "event_id": "test-valid-behavior",
            "seq": 1,
            "event": "accept_partial",
            "project_id": "test-project-valid",
            "episode_id": "test-episode-valid",
            "commit_id": "test-commit-valid",
            "ts_client": datetime.utcnow().isoformat(),
            "ts_client_hr": 1000.0,
            "client_ts": datetime.utcnow().isoformat(),
            "session_id": "session-valid",
            "page_id": "page-valid",
            "editor_scope_id": "scope-valid",
            "tz_offset": -480,
            "behavior_context": {
                "selection_length": 100,
                "attempt_count": 1,
                "time_spent": 5.5,
                "ui_element": "accept_btn"
            },
            "content_data": {
                "event_type": "accept_partial",
                "latency_since_preview_ms": 1250,
                "range_start": 0,
                "range_end": 100,
                "delta_chars": 5
            }
        }
        
        response = client.post("/api/v1/feedback", json=valid_event)
        
        # Should be accepted
        assert response.status_code == 200
        data = response.json()
        assert data["stored"] is True

    def test_unsupported_event_type(self):
        """Test that unsupported event types are rejected"""
        invalid_event = {
            "schema_version": "1.0",
            "event_id": "test-invalid-event-type",
            "seq": 1,
            "event": "unsupported_event_type",
            "project_id": "test-project-123",
            "episode_id": "test-episode-123",
            "commit_id": "test-commit-123",
            "ts_client": datetime.utcnow().isoformat(),
            "ts_client_hr": 1000.0,
            "client_ts": datetime.utcnow().isoformat(),
            "session_id": "session-test",
            "page_id": "page-test",
            "editor_scope_id": "scope-test",
            "tz_offset": -480,
        }
        
        response = client.post("/api/v1/feedback", json=invalid_event)
        
        assert response.status_code == 400
        error_data = response.json()
        assert error_data["detail"]["code"] == "UNSUPPORTED_EVENT"


if __name__ == "__main__":
    pytest.main([__file__])