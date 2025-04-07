import pytest
from fastapi.testclient import TestClient
from app.main import app  # Import your FastAPI application

client = TestClient(app)


def test_health_check():
    """Test the health check endpoint."""
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()

    # Check key fields exist
    assert "status" in data
    assert "services" in data
    assert "system" in data
    assert "timestamp" in data

    # Check services
    assert "vector_db" in data["services"]
    assert "llm" in data["services"]

    # Check system details
    assert "version" in data["system"]
    assert "python" in data["system"]
    assert "platform" in data["system"]


def test_query_route():
    """Test the query route."""
    query_data = {
        "query": "Find test reports about authentication",
        "filters": {"type": "report"},
        "limit": 5
    }

    response = client.post("/api/query", json=query_data)
    assert response.status_code == 200

    data = response.json()
    assert "query" in data
    assert "results" in data
    assert "total_hits" in data
    assert "execution_time_ms" in data
    assert "timestamp" in data


def test_answer_generation():
    """Test the answer generation route."""
    answer_data = {
        "query": "What are the most common test failures?",
        "max_tokens": 500
    }

    response = client.post("/api/answer", json=answer_data)
    assert response.status_code == 200

    data = response.json()
    assert "query" in data
    assert "answer" in data
    assert "timestamp" in data


def test_test_results_routes():
    """Test various test results routes."""
    # Test list test results
    response = client.get("/api/test-results?limit=10")
    assert response.status_code == 200

    data = response.json()
    assert "results" in data
    assert "total" in data
    assert "page" in data
    assert "page_size" in data

    # If you have a known test result ID, test getting specific result
    # Replace with an actual ID from your test data
    test_result_id = "sample-test-result-id"
    response = client.get(f"/api/test-results/{test_result_id}")
    assert response.status_code == 200


def test_trends_routes():
    """Test trend-related routes."""
    # Pass rate trend
    response = client.get("/api/trends/pass-rate?days=30")
    assert response.status_code == 200

    data = response.json()
    assert "trend_data" in data
    assert "timestamp" in data

    # Duration trend
    response = client.get("/api/trends/duration?days=30")
    assert response.status_code == 200

    data = response.json()
    assert "trend_data" in data
    assert "timestamp" in data


def test_analytics_routes():
    """Test analytics routes."""
    # Build health
    # You'll need to replace with an actual project ID
    response = client.get("/api/analytics/build-health?project_id=1")
    assert response.status_code == 200

    data = response.json()
    assert "project_id" in data
    assert "health_score" in data
    assert "status" in data


def test_reporting_routes():
    """Test reporting routes."""
    # List report templates
    response = client.get("/api/reports/templates")
    assert response.status_code == 200

    # You might want more specific checks based on your implementation
    assert isinstance(response.json(), list)


# Optional: Add more specific tests for edge cases and error handling
def test_query_with_invalid_data():
    """Test query route with invalid input."""
    response = client.post("/api/query", json={})
    assert response.status_code == 422  # Unprocessable Entity


def test_nonexistent_route():
    """Test a nonexistent route."""
    response = client.get("/api/nonexistent")
    assert response.status_code == 404
