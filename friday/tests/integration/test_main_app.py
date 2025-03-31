"""
Integration tests for the main FastAPI application
"""
import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.main import app


@pytest.fixture
def client():
    """Create a test client for the app"""
    return TestClient(app)


def test_root_endpoint(client):
    """Test the root endpoint"""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["service"] == settings.APP_NAME


def test_health_endpoint(client):
    """Test the health check endpoint"""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "timestamp" in data


def test_cors_headers(client):
    """Test that CORS headers are correctly set"""
    # Use OPTIONS method on the root endpoint to test CORS preflight
    response = client.options("/", headers={
        "Origin": "http://localhost:3000",
        "Access-Control-Request-Method": "GET",
        "Access-Control-Request-Headers": "Content-Type"
    })

    assert response.status_code in (200, 204)
    assert "access-control-allow-origin" in response.headers
    assert "access-control-allow-methods" in response.headers
    assert "access-control-allow-headers" in response.headers


def test_global_exception_handler(client):
    """Test that exceptions are properly handled"""
    # We need to use an endpoint that actually raises an exception
    # Let's use the processor endpoint since it's not fully implemented
    # and should return a 501 error
    response = client.post("/processor/cucumber-reports",
                           files={"file": ("test.json", b"{}", "application/json")})

    # Should return 501 Not Implemented or some error code
    assert response.status_code != 200  # Any non-success code is acceptable
    data = response.json()
    assert "detail" in data  # Should have a detail field explaining the error


def test_not_found_handler(client):
    """Test that 404 Not Found is properly handled"""
    response = client.get("/nonexistent-endpoint")

    assert response.status_code == 404
    data = response.json()
    assert "detail" in data
    assert "Not Found" in data["detail"]


def test_openapi_schema(client):
    """Test that the OpenAPI schema is properly generated"""
    response = client.get("/openapi.json")

    assert response.status_code == 200
    schema = response.json()
    assert "openapi" in schema
    assert "info" in schema
    assert "paths" in schema

    # Check that our core endpoints are in the schema
    assert "/stats" in schema["paths"]
    assert "/query" in schema["paths"]
    assert "/processor/cucumber-reports" in schema["paths"]
    assert "/trends" in schema["paths"]
    assert "/health" in schema["paths"]
    assert "/failures" in schema["paths"]