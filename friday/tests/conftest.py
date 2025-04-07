# tests/conftest.py
"""
Pytest fixtures for the Friday service tests.
"""

import json
from typing import Any, Dict
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.processors.build import BuildInfoProcessor
from app.core.processors.cucumber import CucumberProcessor
from app.core.rag.embeddings import EmbeddingService
from app.services.llm import LLMService
from app.services.vector_db import VectorDBService

import pytest
from httpx import AsyncClient
from app.main import app  # Import your FastAPI application


@pytest.fixture
async def test_client():
    """
    Async test client for making requests to the application.

    This fixture creates an async test client that can be used
    to make requests to your FastAPI routes during testing.
    """
    async with AsyncClient(app=app, base_url="http://testserver") as client:
        yield client


@pytest.fixture
def mock_data():
    """
    Fixture to provide mock test data for consistent testing.

    This can be expanded to load data from a JSON file or generate
    dynamic test data for each test run.
    """
    return {
        "projects": [
            {
                "id": "project-1",
                "name": "Test Project",
                "description": "Sample project for testing"
            }
        ],
        "test_runs": [
            {
                "id": "test-run-1",
                "project_id": "project-1",
                "name": "Sample Test Run",
                "status": "PASSED",
                "total_tests": 10,
                "passed_tests": 8,
                "failed_tests": 2
            }
        ]
    }


@pytest.fixture
def sample_cucumber_report() -> Dict[str, Any]:
    """
    Sample Cucumber report for testing.

    Returns:
        Dictionary containing a sample Cucumber report
    """
    return [
        {
            "description": "In order to load a website\nas a user\nI want cucumber to work with playwright",
            "elements": [
                {
                    "description": "",
                    "id": "setup-works;qwefsd",
                    "keyword": "Scenario",
                    "line": 9,
                    "name": "qwefsd",
                    "steps": [
                        {
                            "keyword": "Before",
                            "hidden": True,
                            "result": {"status": "passed", "duration": 172299499},
                        },
                        {
                            "arguments": [],
                            "keyword": "When ",
                            "line": 10,
                            "name": 'I navigate to the url "https://www.google.com"',
                            "match": {"location": "features/step_definitions/browser.steps.ts:9"},
                            "result": {"status": "passed", "duration": 819300125},
                        },
                        {
                            "arguments": [],
                            "keyword": "Then ",
                            "line": 11,
                            "name": 'I should see the title "Google"',
                            "match": {"location": "features/step_definitions/browser.steps.ts:15"},
                            "result": {"status": "passed", "duration": 4925416},
                        },
                    ],
                    "tags": [{"name": "@focus", "line": 1}, {"name": "@JIRA-123", "line": 8}],
                    "type": "scenario",
                },
                {
                    "description": "",
                    "id": "setup-works;qwe",
                    "keyword": "Scenario",
                    "line": 14,
                    "name": "qwe",
                    "steps": [
                        {
                            "keyword": "Before",
                            "hidden": True,
                            "result": {"status": "passed", "duration": 176922582},
                        },
                        {
                            "arguments": [],
                            "keyword": "When ",
                            "line": 15,
                            "name": 'I navigate to the url "https://www.google.com"',
                            "match": {"location": "features/step_definitions/browser.steps.ts:9"},
                            "result": {"status": "passed", "duration": 934293666},
                        },
                        {
                            "arguments": [],
                            "keyword": "Then ",
                            "line": 16,
                            "name": 'I should see the title "abc"',
                            "match": {"location": "features/step_definitions/browser.steps.ts:15"},
                            "result": {
                                "status": "failed",
                                "duration": 7411917,
                                "error_message": 'Error: expected "abc" but got "Google"',
                            },
                        },
                    ],
                    "tags": [{"name": "@focus", "line": 1}, {"name": "@JIRA-123", "line": 13}],
                    "type": "scenario",
                },
            ],
            "id": "setup-works",
            "line": 2,
            "keyword": "Feature",
            "name": "Setup Works",
            "tags": [{"name": "@focus", "line": 1}],
            "uri": "features/sample.feature",
        }
    ]


@pytest.fixture
def sample_build_info() -> Dict[str, Any]:
    """
    Sample build information for testing.

    Returns:
        Dictionary containing sample build information
    """
    return {
        "build_id": "build-123",
        "build_number": "45",
        "timestamp": "2025-03-13T03:07:07Z",
        "branch": "main",
        "commit_hash": "abc123def456",
        "additional_info": {"triggered_by": "user123", "environment": "staging"},
    }


@pytest.fixture
def mock_vector_db_service() -> VectorDBService:
    """
    Mock vector database service.

    Returns:
        Mock vector database service
    """
    mock = MagicMock(spec=VectorDBService)
    mock.upsert_many = AsyncMock(return_value={"operation_id": "123", "status": "success"})
    mock.search = AsyncMock(
        return_value=[
            {
                "id": "1",
                "score": 0.95,
                "payload": {
                    "feature_name": "Setup Works",
                    "scenario_name": "qwefsd",
                    "status": "passed",
                    "tags": ["@focus", "@JIRA-123"],
                    "build_id": "build-123",
                },
            }
        ]
    )
    mock.get_all = AsyncMock(
        return_value=[
            {
                "id": "1",
                "payload": {
                    "feature_name": "Setup Works",
                    "scenario_name": "qwefsd",
                    "status": "passed",
                    "tags": ["@focus", "@JIRA-123"],
                    "build_id": "build-123",
                },
            },
            {
                "id": "2",
                "payload": {
                    "feature_name": "Setup Works",
                    "scenario_name": "qwe",
                    "status": "failed",
                    "tags": ["@focus", "@JIRA-123"],
                    "build_id": "build-123",
                },
            },
        ]
    )
    return mock


@pytest.fixture
def mock_embedding_service() -> EmbeddingService:
    """
    Mock embedding service.

    Returns:
        Mock embedding service
    """
    mock = MagicMock(spec=EmbeddingService)
    mock.get_embeddings = AsyncMock(return_value=[[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]])
    mock.get_embedding = AsyncMock(return_value=[0.1, 0.2, 0.3])
    return mock


@pytest.fixture
def mock_llm_service() -> LLMService:
    """
    Mock LLM service.

    Returns:
        Mock LLM service
    """
    mock = MagicMock(spec=LLMService)
    mock.generate = AsyncMock(
        return_value={
            "status": "success",
            "response": "This is a test response from the LLM.",
            "model": "test-model",
        }
    )
    return mock


@pytest.fixture
def cucumber_processor(
    mock_vector_db_service: VectorDBService,
    mock_embedding_service: EmbeddingService,
    mock_llm_service: LLMService,
) -> CucumberProcessor:
    """
    Cucumber processor with mock dependencies.

    Args:
        mock_vector_db_service: Mock vector database service
        mock_embedding_service: Mock embedding service
        mock_llm_service: Mock LLM service

    Returns:
        Cucumber processor with mock dependencies
    """
    return CucumberProcessor(
        vector_db_service=mock_vector_db_service,
        embedding_service=mock_embedding_service,
        llm_service=mock_llm_service,
    )


@pytest.fixture
def build_processor(
    mock_vector_db_service: VectorDBService,
    mock_embedding_service: EmbeddingService,
    mock_llm_service: LLMService,
) -> BuildInfoProcessor:
    """
    Build info processor with mock dependencies.

    Args:
        mock_vector_db_service: Mock vector database service
        mock_embedding_service: Mock embedding service
        mock_llm_service: Mock LLM service

    Returns:
        Build info processor with mock dependencies
    """
    return BuildInfoProcessor(
        vector_db_service=mock_vector_db_service,
        embedding_service=mock_embedding_service,
        llm_service=mock_llm_service,
    )
