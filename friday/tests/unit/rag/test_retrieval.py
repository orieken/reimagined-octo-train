"""
Unit tests for RetrievalService
"""
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from app.core.rag.retrieval import RetrievalService
from app.services.vector_db import VectorDBService


class TestRetrievalService:
    """Test suite for RetrievalService"""

    @pytest.fixture
    def mock_vector_db_service(self):
        """Create a mock VectorDBService"""
        mock_service = MagicMock(spec=VectorDBService)
        mock_service.search = AsyncMock()
        return mock_service

    @pytest.fixture
    def service(self, mock_vector_db_service):
        """Create a RetrievalService instance for testing"""
        return RetrievalService(
            vector_db_service=mock_vector_db_service,
            max_results=5,
            similarity_threshold=0.7
        )

    @pytest.fixture
    def sample_query_vector(self):
        """Create a sample query vector for testing"""
        return [0.1] * 384

    @pytest.fixture
    def sample_search_results(self):
        """Create sample search results for testing"""
        return [
            {
                "id": "1",
                "score": 0.95,
                "text": "Feature: User Authentication",
                "metadata": {
                    "test_run_id": "test-run-1",
                    "feature_id": "feature-1",
                    "chunk_type": "feature",
                    "source": "feature-1.feature"
                }
            },
            {
                "id": "2",
                "score": 0.85,
                "text": "Scenario: Failed login shows error message",
                "metadata": {
                    "test_run_id": "test-run-1",
                    "feature_id": "feature-1",
                    "scenario_id": "scenario-2",
                    "chunk_type": "scenario",
                    "source": "feature-1.feature"
                }
            },
            {
                "id": "3",
                "score": 0.65,
                "text": "Error: Expected error message not displayed",
                "metadata": {
                    "test_run_id": "test-run-1",
                    "feature_id": "feature-1",
                    "scenario_id": "scenario-2",
                    "chunk_type": "error",
                    "source": "feature-1.feature"
                }
            }
        ]

    @pytest.mark.asyncio
    async def test_retrieve(self, service, mock_vector_db_service, sample_query_vector, sample_search_results):
        """Test retrieving relevant text chunks"""
        # Setup
        # Only return the first two results to match the filtering behavior
        filtered_results = sample_search_results[:2]  # Only results with score >= 0.7
        mock_vector_db_service.search.return_value = sample_search_results
        filters = {"test_run_id": "test-run-1", "tags": ["@test"]}

        # Execute
        results = await service.retrieve(sample_query_vector, filters)

        # Assert - we expect only the first two results since the third has score < 0.7
        assert results == filtered_results

        # Verify vector DB service was called with correct parameters
        mock_vector_db_service.search.assert_called_once()
        args = mock_vector_db_service.search.call_args[1]
        assert args["query_vector"] == sample_query_vector
        assert args["limit"] == service.max_results
        assert args["filters"] == filters

    @pytest.mark.asyncio
    async def test_retrieve_with_threshold_filtering(self, service, mock_vector_db_service, sample_query_vector):
        """Test filtering results by similarity threshold"""
        # Setup - create results with varying scores
        mixed_results = [
            {"id": "1", "score": 0.9, "text": "High relevance", "metadata": {}},
            {"id": "2", "score": 0.6, "text": "Medium relevance", "metadata": {}},
            {"id": "3", "score": 0.4, "text": "Low relevance", "metadata": {}}
        ]
        mock_vector_db_service.search.return_value = mixed_results

        # Set a higher threshold in the service
        service.similarity_threshold = 0.8

        # Execute
        results = await service.retrieve(sample_query_vector)

        # Assert - only results above threshold should be returned
        assert len(results) == 1
        assert results[0]["id"] == "1"
        assert results[0]["score"] == 0.9

    def test_format_context(self, service, sample_search_results):
        """Test formatting search results into context string"""
        # Execute
        context = service.format_context(sample_search_results)

        # Assert
        assert isinstance(context, str)

        # Check that context includes all result texts with proper formatting
        for i, result in enumerate(sample_search_results):
            # Context should include the result number
            assert f"[{i + 1}]" in context
            # Context should include the result text
            assert result["text"] in context
            # Context should include source and relevance
            assert "Source:" in context
            assert "Relevance:" in context

    def test_format_context_empty(self, service):
        """Test formatting empty search results"""
        # Execute
        context = service.format_context([])

        # Assert
        assert context == ""