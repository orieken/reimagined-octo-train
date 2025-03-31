"""
Unit tests for stats API routes
"""
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import parse_obj_as

from app.api.routes.stats import router
from app.models.api import TestStatsRequest, TestStatsResponse, TestSummary, TestTag


@pytest.fixture
def app():
    """Create a FastAPI app with the stats router"""
    app = FastAPI()
    app.include_router(router, prefix="/stats")
    return app


@pytest.fixture
def client(app):
    """Create a test client for the app"""
    return TestClient(app)


class TestStatsRoutes:
    """Test suite for stats API routes"""

    def test_get_test_statistics(self, client):
        """Test getting basic test statistics"""
        # Execute
        response = client.get("/stats")

        # Assert
        assert response.status_code == 200
        data = response.json()

        # Check response structure
        assert "status" in data
        assert data["status"] == "success"
        assert "statistics" in data
        assert "timestamp" in data

        # Check statistics structure
        stats = data["statistics"]
        assert "total_scenarios" in stats
        assert "passed_scenarios" in stats
        assert "failed_scenarios" in stats
        assert "skipped_scenarios" in stats
        assert "pass_rate" in stats
        assert "top_tags" in stats

        # Check values
        assert isinstance(stats["total_scenarios"], int)
        assert isinstance(stats["pass_rate"], float)
        assert 0 <= stats["pass_rate"] <= 1.0
        assert len(stats["top_tags"]) > 0

    def test_get_test_statistics_with_filters(self, client):
        """Test getting test statistics with query parameters"""
        # Execute
        response = client.get("/stats?test_run_id=test-123&build_id=build-456")

        # Assert
        assert response.status_code == 200
        data = response.json()

        # Basic checks that filtering didn't break anything
        assert data["status"] == "success"
        assert "statistics" in data

    def test_get_test_statistics_detailed_not_implemented(self, client):
        """Test that the detailed endpoint returns 501 Not Implemented"""
        # Setup
        request_data = {
            "test_run_id": "test-123",
            "build_id": "build-456",
            "tags": ["@api", "@test"],
            "from_date": datetime.utcnow().isoformat(),
            "to_date": datetime.utcnow().isoformat()
        }

        # Execute
        response = client.post("/stats", json=request_data)

        # Assert
        assert response.status_code == 501
        data = response.json()
        assert "detail" in data
        assert "Not implemented yet" in data["detail"]

    def test_model_serialization(self):
        """Test that API models can be properly serialized/deserialized"""
        # Setup
        summary = TestSummary(
            total=100,
            passed=80,
            failed=15,
            skipped=5,
            pending=0,
            undefined=0,
            success_rate=80.0
        )

        tags = [
            TestTag(name="@api", count=45),
            TestTag(name="@ui", count=38)
        ]

        response = TestStatsResponse(
            summary=summary,
            test_run_id="test-123",
            build_info=None,
            timestamp=datetime.utcnow(),
            tags=tags
        )

        # Execute
        response_dict = response.dict()
        parsed_response = parse_obj_as(TestStatsResponse, response_dict)

        # Assert
        assert parsed_response.summary.total == 100
        assert parsed_response.summary.passed == 80
        assert parsed_response.summary.success_rate == 80.0
        assert parsed_response.test_run_id == "test-123"
        assert len(parsed_response.tags) == 2
        assert parsed_response.tags[0].name == "@api"
        assert parsed_response.tags[0].count == 45

    def test_create_summary_from_features(self):
        """Test the TestSummary.from_features static method"""
        # This would be better in a separate model test file,
        # but included here for completeness

        # This test would require actual Feature objects
        # We'll skip the implementation for Phase 1 and add it in Phase 2
        pass