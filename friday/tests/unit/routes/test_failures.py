"""
Unit tests for failures API routes
"""
import json
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.routes.failures import router


@pytest.fixture
def app():
    """Create a FastAPI app with the failures router"""
    app = FastAPI()
    # The router doesn't have a prefix in our implementation
    app.include_router(router)
    return app


@pytest.fixture
def client(app):
    """Create a test client for the app"""
    return TestClient(app)


class TestFailuresRoutes:
    """Test suite for failures API routes"""

    def test_get_failure_analysis_default(self, client):
        """Test getting failure analysis with default parameters"""
        # Execute
        response = client.get("/failures")

        # Assert
        assert response.status_code == 200
        data = response.json()

        # Check response structure
        assert "failureCategories" in data
        assert "failureDetails" in data
        assert "failuresByFeature" in data
        assert "recentFailures" in data

        # Check failure categories structure
        categories = data["failureCategories"]
        assert isinstance(categories, list)
        assert len(categories) > 0
        for category in categories:
            assert "name" in category
            assert "value" in category
            assert "percentage" in category
            assert 0 <= category["percentage"] <= 100

        # Check that percentages sum to approximately 100%
        total_percentage = sum(category["percentage"] for category in categories)
        assert 99.0 <= total_percentage <= 101.0  # Allow for rounding errors

        # Check failure details structure
        details = data["failureDetails"]
        assert isinstance(details, dict)
        assert len(details) > 0
        for category_name, category_details in details.items():
            assert isinstance(category_details, list)
            assert len(category_details) > 0
            for detail in category_details:
                assert "element" in detail
                assert "occurrences" in detail
                assert "scenarios" in detail
                assert isinstance(detail["scenarios"], list)

        # Check failures by feature structure
        feature_failures = data["failuresByFeature"]
        assert isinstance(feature_failures, list)
        assert len(feature_failures) > 0
        for feature in feature_failures:
            assert "feature" in feature
            assert "failures" in feature
            assert "tests" in feature
            assert "failureRate" in feature
            assert 0 <= feature["failureRate"] <= 100
            assert feature["failures"] <= feature["tests"]

        # Check recent failures structure
        recent = data["recentFailures"]
        assert isinstance(recent, list)
        assert len(recent) > 0
        for failure in recent:
            assert "id" in failure
            assert "scenario" in failure
            assert "error" in failure
            assert "date" in failure
            assert "build" in failure

            # Verify date format
            try:
                datetime.fromisoformat(failure["date"].replace('Z', '+00:00'))
            except ValueError:
                pytest.fail(f"Date is not in ISO format: {failure['date']}")

    def test_get_failure_analysis_with_filters(self, client):
        """Test getting failure analysis with filters"""
        # Test with test run ID filter
        response = client.get("/failures?test_run_id=test-123")
        assert response.status_code == 200
        data = response.json()
        assert "failureCategories" in data

        # Test with build ID filter
        response = client.get("/failures?build_id=build-456")
        assert response.status_code == 200
        data = response.json()
        assert "failureCategories" in data

        # Test with days filter
        response = client.get("/failures?days=14")
        assert response.status_code == 200
        data = response.json()
        assert "failureCategories" in data

        # Test with multiple filters
        response = client.get("/failures?test_run_id=test-123&build_id=build-456&days=14")
        assert response.status_code == 200
        data = response.json()
        assert "failureCategories" in data

    def test_failure_data_consistency(self, client):
        """Test that failure data is consistent between requests"""
        # Execute multiple requests
        response1 = client.get("/failures")
        assert response1.status_code == 200

        response2 = client.get("/failures")
        assert response2.status_code == 200

        # Assert
        data1 = response1.json()
        data2 = response2.json()

        # Same request should yield the same basic structure in Phase 1
        assert len(data1["failureCategories"]) == len(data2["failureCategories"])
        assert len(data1["failuresByFeature"]) == len(data2["failuresByFeature"])
        assert len(data1["recentFailures"]) == len(data2["recentFailures"])

        # Category names should be consistent
        category_names1 = [c["name"] for c in data1["failureCategories"]]
        category_names2 = [c["name"] for c in data2["failureCategories"]]
        assert category_names1 == category_names2

        # Feature names should be consistent
        feature_names1 = [f["feature"] for f in data1["failuresByFeature"]]
        feature_names2 = [f["feature"] for f in data2["failuresByFeature"]]
        assert feature_names1 == feature_names2

    def test_dates_are_recent(self, client):
        """Test that failure dates are recent"""
        # Execute
        response = client.get("/failures")
        assert response.status_code == 200
        data = response.json()

        # Check recent failures dates
        now = datetime.utcnow()
        three_days_ago = now - timedelta(days=3)

        for failure in data["recentFailures"]:
            failure_date = datetime.fromisoformat(failure["date"].replace('Z', '+00:00'))
            # Failure date should be within the last 3 days
            assert failure_date > three_days_ago
            assert failure_date <= now

    def test_value_ranges_are_valid(self, client):
        """Test that value ranges in the response are valid"""
        # Execute
        response = client.get("/failures")
        assert response.status_code == 200
        data = response.json()

        # Check failure categories
        for category in data["failureCategories"]:
            assert category["value"] >= 0
            assert 0 <= category["percentage"] <= 100

        # Check failures by feature
        for feature in data["failuresByFeature"]:
            assert feature["failures"] >= 0
            assert feature["tests"] >= feature["failures"]
            assert 0 <= feature["failureRate"] <= 100