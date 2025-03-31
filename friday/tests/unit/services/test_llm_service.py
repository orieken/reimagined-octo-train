# tests/unit/services/test_llm_service_s.py
import pytest
import json
from unittest.mock import MagicMock, patch, AsyncMock
import httpx

from app.services.llm import LLMService, LLMServiceException
from app.config import settings


@pytest.fixture
def mock_httpx_client():
    with patch('httpx.Client') as mock_client:
        mock_instance = MagicMock()
        mock_client.return_value.__enter__.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def mock_async_httpx_client():
    with patch('httpx.AsyncClient') as mock_client:
        mock_instance = AsyncMock()
        mock_client.return_value.__aenter__.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def llm_service(mock_httpx_client):
    # Setup the mock response for connection check
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "models": [
            {"name": settings.LLM_MODEL}
        ]
    }
    mock_httpx_client.get.return_value = mock_response

    # Create and return the service
    service = LLMService()
    return service


def test_init_connection_check(mock_httpx_client):
    # Setup
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "models": [
            {"name": settings.LLM_MODEL}
        ]
    }
    mock_httpx_client.get.return_value = mock_response

    # Execute
    service = LLMService()

    # Assert
    mock_httpx_client.get.assert_called_once_with(f"{settings.OLLAMA_API_URL}/api/tags")
    assert service.base_url == settings.OLLAMA_API_URL.rstrip('/')
    assert service.model == settings.LLM_MODEL
    assert service.timeout == settings.LLM_TIMEOUT


def test_init_connection_error(mock_httpx_client):
    # Setup
    mock_httpx_client.get.side_effect = httpx.HTTPError("Connection error")

    # Execute & Assert
    with pytest.raises(LLMServiceException):
        LLMService()


def test_init_model_not_available(mock_httpx_client):
    # Setup - Model is missing
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "models": [
            {"name": "different-model"}
        ]
    }
    mock_httpx_client.get.return_value = mock_response

    # Execute (should log warning but not raise error)
    with patch('app.services.llm.logger') as mock_logger:
        service = LLMService()

        # Assert
        mock_logger.warning.assert_called_once()


@pytest.mark.asyncio
async def test_generate_embedding(llm_service, mock_async_httpx_client):
    # Setup
    text = "Test text for embedding"
    expected_embedding = [0.1, 0.2, 0.3]

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "embedding": expected_embedding
    }

    mock_async_httpx_client.post.return_value = mock_response

    # Execute
    embedding = await llm_service.generate_embedding(text)

    # Assert
    mock_async_httpx_client.post.assert_called_once_with(
        f"{settings.OLLAMA_API_URL}/api/embeddings",
        json={
            "model": settings.LLM_MODEL,
            "prompt": text
        }
    )
    assert embedding == expected_embedding


@pytest.mark.asyncio
async def test_generate_embedding_empty_text(llm_service):
    # Test with empty text
    with pytest.raises(ValueError):
        await llm_service.generate_embedding("")


@pytest.mark.asyncio
async def test_generate_embedding_http_error(llm_service, mock_async_httpx_client):
    # Setup
    mock_async_httpx_client.post.side_effect = httpx.HTTPError("HTTP error")

    # Execute & Assert
    with pytest.raises(httpx.HTTPError):
        await llm_service.generate_embedding("Test text")


@pytest.mark.asyncio
async def test_generate_text(llm_service, mock_async_httpx_client):
    # Setup
    prompt = "Generate some text"
    system_prompt = "You are a helpful assistant"
    expected_text = "This is the generated text response"

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "response": expected_text
    }

    mock_async_httpx_client.post.return_value = mock_response

    # Execute
    generated_text = await llm_service.generate_text(
        prompt=prompt,
        system_prompt=system_prompt,
        temperature=0.5,
        max_tokens=300
    )

    # Assert
    mock_async_httpx_client.post.assert_called_once_with(
        f"{settings.OLLAMA_API_URL}/api/generate",
        json={
            "model": settings.LLM_MODEL,
            "prompt": prompt,
            "system": system_prompt,
            "temperature": 0.5,
            "max_tokens": 300,
            "stream": False
        }
    )
    assert generated_text == expected_text


@pytest.mark.asyncio
async def test_analyze_test_failure(llm_service, mock_async_httpx_client):
    # Setup
    test_case_details = {
        "name": "Test Case 1",
        "status": "FAILED",
        "error": "AssertionError: expected 200 but got 404"
    }

    # Mock LLM response with JSON structure
    llm_response = """{
        "root_cause": "API endpoint not found",
        "severity": "HIGH",
        "recommendations": ["Check API endpoint URL", "Verify server is running"],
        "related_components": ["API Gateway", "Backend Service"],
        "confidence": 0.85
    }"""

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "response": llm_response
    }

    mock_async_httpx_client.post.return_value = mock_response

    # Execute
    analysis = await llm_service.analyze_test_failure(test_case_details)

    # Assert
    assert mock_async_httpx_client.post.called
    assert analysis["root_cause"] == "API endpoint not found"
    assert analysis["severity"] == "HIGH"
    assert "Check API endpoint URL" in analysis["recommendations"]
    assert "API Gateway" in analysis["related_components"]
    assert analysis["confidence"] == 0.85


@pytest.mark.asyncio
async def test_analyze_test_failure_invalid_json(llm_service, mock_async_httpx_client):
    # Setup - LLM returns non-JSON response
    test_case_details = {
        "name": "Test Case 1",
        "status": "FAILED",
        "error": "AssertionError: expected 200 but got 404"
    }

    invalid_response = "I think the problem might be related to the API endpoint not being available."

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "response": invalid_response
    }

    mock_async_httpx_client.post.return_value = mock_response

    # Execute
    analysis = await llm_service.analyze_test_failure(test_case_details)

    # Assert
    assert "parsing_error" in analysis
    assert analysis["root_cause"] == "Could not analyze (LLM response format error)"
    assert "Review the test case and error logs manually" in analysis["recommendations"]
    assert analysis["raw_response"] == invalid_response