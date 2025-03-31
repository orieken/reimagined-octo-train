"""
Unit tests for BaseProcessor
"""
import unittest
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from app.core.processors.base import BaseProcessor
from app.core.rag.embeddings import EmbeddingService
from app.models.domain import ChunkMetadata, TextChunk, TextEmbedding
from app.services.vector_db import VectorDBService


# Create a concrete implementation of BaseProcessor for testing
class TestableProcessor(BaseProcessor):
    """Concrete implementation of BaseProcessor for testing"""

    async def process(self, data, metadata):
        """Process implementation for testing"""
        result = await self.process_text(f"Test data: {data}", metadata)
        return {"success": True, "embedded_ids": result}


class TestBaseProcessor:
    """Test suite for BaseProcessor"""

    @pytest.fixture
    def mock_embedding_service(self):
        """Create a mock EmbeddingService"""
        mock_service = MagicMock(spec=EmbeddingService)
        mock_service.chunk_text = MagicMock(return_value=["Chunk 1", "Chunk 2"])
        mock_service.embed_chunks = AsyncMock()
        return mock_service

    @pytest.fixture
    def mock_vector_db_service(self):
        """Create a mock VectorDBService"""
        mock_service = MagicMock(spec=VectorDBService)
        mock_service.insert_embeddings = AsyncMock(return_value=["id1", "id2"])
        return mock_service

    @pytest.fixture
    def processor(self, mock_embedding_service, mock_vector_db_service):
        """Create a TestableProcessor instance for testing"""
        return TestableProcessor(
            embedding_service=mock_embedding_service,
            vector_db_service=mock_vector_db_service
        )

    @pytest.fixture
    def sample_embeddings(self):
        """Create sample embeddings for testing"""
        return [
            TextEmbedding(
                id="id1",
                vector=[0.1] * 384,
                text="Chunk 1",
                metadata=ChunkMetadata(
                    test_run_id="test1",
                    feature_id=None,
                    scenario_id=None,
                    build_id=None,
                    chunk_type="test",
                    tags=[]
                )
            ),
            TextEmbedding(
                id="id2",
                vector=[0.2] * 384,
                text="Chunk 2",
                metadata=ChunkMetadata(
                    test_run_id="test1",
                    feature_id=None,
                    scenario_id=None,
                    build_id=None,
                    chunk_type="test",
                    tags=[]
                )
            )
        ]

    @pytest.mark.asyncio
    async def test_process_text(self, processor, mock_embedding_service,
                                mock_vector_db_service, sample_embeddings):
        """Test the process_text method"""
        # Setup
        text = "Test text for embedding"
        metadata = {"test_run_id": "test1", "chunk_type": "test"}

        # Configure mocks
        mock_embedding_service.embed_chunks.return_value = sample_embeddings

        # Execute
        result = await processor.process_text(text, metadata)

        # Assert
        assert result == ["id1", "id2"]

        # Verify chunking was called
        mock_embedding_service.chunk_text.assert_called_once_with(text)

        # Verify embedding was called with TextChunk objects
        mock_embedding_service.embed_chunks.assert_called_once()
        chunks_arg = mock_embedding_service.embed_chunks.call_args[0][0]
        assert len(chunks_arg) == 2
        assert isinstance(chunks_arg[0], TextChunk)
        assert chunks_arg[0].text == "Chunk 1"
        assert chunks_arg[0].metadata.test_run_id == "test1"
        assert chunks_arg[0].metadata.chunk_type == "test"

        # Verify vector DB insertion was called
        mock_vector_db_service.insert_embeddings.assert_called_once_with(sample_embeddings)

    @pytest.mark.asyncio
    async def test_concrete_implementation(self, processor, mock_embedding_service,
                                           mock_vector_db_service):
        """Test the concrete implementation of process"""
        # Setup
        data = "sample data"
        metadata = {"test_run_id": "test1", "chunk_type": "test"}

        # Configure mock to correctly handle the text from our implementation
        mock_embedding_service.chunk_text.return_value = ["Test data: sample data"]

        # Execute
        result = await processor.process(data, metadata)

        # Assert
        assert result["success"] is True
        assert result["embedded_ids"] == ["id1", "id2"]

        # Verify process_text was called with the expected text
        mock_embedding_service.chunk_text.assert_called_once_with("Test data: sample data")