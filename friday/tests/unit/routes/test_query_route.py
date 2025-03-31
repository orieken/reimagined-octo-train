"""
Unit tests for query API routes
"""
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.routes.query import router
from app.models.api import QueryRequest, QueryResponse
from app.models.domain import QueryResult
from app.api.dependencies import get_generator_service, get_retrieval_service, get_llm_service


@pytest.fixture
def mock_generator_service():
    """Create a mock GeneratorService"""
    mock_service = MagicMock()
    mock_service.generate = AsyncMock(return_value={
        "answer": "This is a test answer",
        "confidence": 0.85
    })
    return mock_service


@pytest.fixture
def mock_retrieval_service():
    """Create a mock RetrievalService"""
    mock_service = MagicMock()
    mock_service.retrieve = AsyncMock(return_value=[])
    mock_service.format_context = MagicMock(return_value="Context text")
    return mock_service


@pytest.fixture
def mock_llm_service():
    """Create a mock LLMService"""
    mock_service = MagicMock()
    mock_service.generate_embedding = AsyncMock(return_value=[0.1] * 384)
    return mock_service


@pytest.fixture
def app(mock_generator_service, mock_retrieval_service, mock_llm_service):
    """Create a FastAPI app with the query router"""
    app = FastAPI()

    # Create a function to directly patch the dependencies
    from app.api.dependencies import get_generator_service, get_retrieval_service, get_llm_service

    # Override dependencies
    app.dependency_overrides[get_generator_service] = lambda: mock_generator_service
    app.dependency_overrides[get_retrieval_service] = lambda: mock_retrieval_service
    app.dependency_overrides[get_llm_service] = lambda: mock_llm_service

    app.include_router(router, prefix="/query")
    return app


@pytest.fixture
def client(app):
    """Create a test client for the app"""
    return TestClient(app)


def test_query_route_success(client, mock_generator_service, mock_retrieval_service, mock_llm_service):
    """Test that the query route returns a successful response"""
    # Setup
    request_data = {
        "query": "What are the failing tests?",
        "test_run_id": "test-run-123",
        "build_id": "build-456",
        "tags": ["@api", "@test"],
        "max_results": 5,
        "similarity_threshold": 0.7
    }

    # Execute
    response = client.post("/query", json=request_data)

    # Assert
    assert response.status_code == 200
    data = response.json()

    # Check response structure
    assert "result" in data
    result = data["result"]
    assert "answer" in result
    assert "confidence" in result
    assert "sources" in result
    assert "metadata" in result

    # Check values
    assert result["answer"] == "This is a test answer"
    assert result["confidence"] == 0.85

    # Verify service calls
    mock_llm_service.generate_embedding.assert_called_once()
    mock_retrieval_service.retrieve.assert_called_once()
    mock_generator_service.generate.assert_called_once()


def test_query_route_error(client, mock_generator_service, mock_retrieval_service, mock_llm_service):
    """Test that the query route handles errors properly"""
    # Setup
    request_data = {
        "query": "What are the failing tests?",
    }

    # Configure the mock to raise an exception
    mock_llm_service.generate_embedding.side_effect = Exception("Test error")

    # We need to patch app.dependency_overrides directly since the fixture
    # setup might not be properly affecting this test
    with patch('app.api.routes.query.get_llm_service', return_value=mock_llm_service):
        # Execute
        response = client.post("/query", json=request_data)

    # Assert
    assert response.status_code == 500
    data = response.json()
    assert "detail" in data
    assert "error" in data["detail"].lower()


def test_query_route_validation(client):
    """Test that the query route validates input properly"""
    # Setup - missing required field 'query'
    request_data = {
        "test_run_id": "test-run-123",
        "build_id": "build-456"
    }

    # Execute
    response = client.post("/query", json=request_data)

    # Assert
    assert response.status_code == 422  # Validation error
    data = response.json()
    assert "detail" in data
    # Check that the error mentions the missing field
    assert any("query" in error.get("loc", []) for error in data["detail"])