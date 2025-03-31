"""
Unit tests for GeneratorService
"""
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from app.core.rag.generator import GeneratorService
from app.services.llm import LLMService


class TestGeneratorService:
    """Test suite for GeneratorService"""

    @pytest.fixture
    def mock_llm_service(self):
        """Create a mock LLMService"""
        mock_service = MagicMock(spec=LLMService)
        mock_service.generate_text = AsyncMock(return_value="This is a mock response to the query.")
        return mock_service

    @pytest.fixture
    def service(self, mock_llm_service):
        """Create a GeneratorService instance for testing"""
        return GeneratorService(
            llm_service=mock_llm_service
        )

    @pytest.fixture
    def sample_query(self):
        """Create a sample query for testing"""
        return "What are the failing tests in the latest build?"

    @pytest.fixture
    def sample_context(self):
        """Create a sample context for testing"""
        return """
        [1] Feature: User Authentication - 3 tests failed, 24 passed (Source: cucumber_reports, Relevance: 0.92)
        [2] Scenario: User login with invalid credentials fails with proper error message (Source: cucumber_reports, Relevance: 0.87)
        [3] Error: Expected status code 401 but got 500. Internal server error occurred. (Source: error_reports, Relevance: 0.95)
        """

    @pytest.mark.asyncio
    async def test_generate_without_context(self, service, mock_llm_service, sample_query):
        """Test generation without any context"""
        # Execute
        result = await service.generate(query=sample_query, context="")

        # Assert
        assert isinstance(result, dict)
        assert "answer" in result
        assert "confidence" in result
        assert result["answer"] == "This is a mock response to the query."

        # Since no context was provided, confidence should be lower
        assert result["confidence"] < 0.5

        # Verify LLM service was called with proper prompt
        mock_llm_service.generate_text.assert_called_once()
        args = mock_llm_service.generate_text.call_args[1]
        assert sample_query in args["prompt"]
        assert args["system_message"] is not None

    @pytest.mark.asyncio
    async def test_generate_with_context(self, service, mock_llm_service, sample_query, sample_context):
        """Test generation with context"""
        # Execute
        result = await service.generate(query=sample_query, context=sample_context)

        # Assert
        assert "answer" in result
        assert "confidence" in result
        assert result["answer"] == "This is a mock response to the query."

        # With context, confidence should be higher
        assert result["confidence"] >= 0.5

        # Verify LLM service was called with both query and context
        mock_llm_service.generate_text.assert_called_once()
        args = mock_llm_service.generate_text.call_args[1]
        assert sample_query in args["prompt"]
        assert sample_context in args["prompt"]
        assert args["system_message"] is not None

    @pytest.mark.asyncio
    async def test_generate_with_custom_parameters(self, service, mock_llm_service, sample_query, sample_context):
        """Test generation with custom max_tokens and temperature"""
        # Setup
        max_tokens = 2000
        temperature = 0.5

        # Execute
        result = await service.generate(
            query=sample_query,
            context=sample_context,
            max_tokens=max_tokens,
            temperature=temperature
        )

        # Assert
        assert "answer" in result

        # Verify LLM service was called with custom parameters
        mock_llm_service.generate_text.assert_called_once()
        args = mock_llm_service.generate_text.call_args[1]
        assert args["max_tokens"] == max_tokens
        assert args["temperature"] == temperature

    @pytest.mark.asyncio
    async def test_confidence_calculation(self, service, mock_llm_service):
        """Test different confidence levels based on context"""
        # Test with empty context
        result1 = await service.generate(query="Query 1", context="")

        # Test with minimal context
        result2 = await service.generate(query="Query 2", context="Some minimal context")

        # Test with rich context
        rich_context = "\n".join([f"[{i}] Detailed context item {i}" for i in range(1, 10)])
        result3 = await service.generate(query="Query 3", context=rich_context)

        # Assert confidence levels
        assert result1["confidence"] < result2["confidence"]
        assert result2["confidence"] <= result3["confidence"]