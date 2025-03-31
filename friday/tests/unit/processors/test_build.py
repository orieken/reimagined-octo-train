"""
Unit tests for BuildInfoProcessor
"""
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch, ANY
import pytest

from app.core.processors.build import BuildInfoProcessor
from app.core.rag.embeddings import EmbeddingService
from app.models.domain import BuildInfo, ChunkMetadata, TextChunk, TextEmbedding
from app.services.vector_db import VectorDBService


class TestBuildInfoProcessor:
    """Test suite for BuildInfoProcessor"""

    @pytest.fixture
    def mock_embedding_service(self):
        """Create a mock EmbeddingService"""
        mock_service = MagicMock(spec=EmbeddingService)
        # Mock the chunk_text method to return a single chunk
        mock_service.chunk_text = MagicMock(return_value=["Build info text"])
        mock_service.embed_chunks = AsyncMock()
        return mock_service

    @pytest.fixture
    def mock_vector_db_service(self):
        """Create a mock VectorDBService"""
        mock_service = MagicMock(spec=VectorDBService)
        mock_service.insert_embeddings = AsyncMock(return_value=["embedding-id-1"])
        return mock_service

    @pytest.fixture
    def processor(self, mock_embedding_service, mock_vector_db_service):
        """Create a BuildInfoProcessor instance for testing"""
        return BuildInfoProcessor(
            embedding_service=mock_embedding_service,
            vector_db_service=mock_vector_db_service
        )

    @pytest.fixture
    def sample_build_info(self):
        """Create a sample BuildInfo for testing"""
        return BuildInfo(
            build_id="build-123",
            build_number="456",
            branch="main",
            commit_hash="abc123def456",
            build_date=datetime.utcnow(),
            build_url="https://ci.example.com/builds/456",
            metadata={
                "triggered_by": "user1",
                "environment": "staging"
            }
        )

    @pytest.fixture
    def sample_embedding(self):
        """Create a sample embedding for testing"""
        return TextEmbedding(
            id="embedding-id-1",
            vector=[0.1] * 384,
            text="Build info text",
            metadata=ChunkMetadata(
                test_run_id="test-run-1",
                feature_id=None,
                scenario_id=None,
                build_id="build-123",
                chunk_type="build_info",
                tags=[]
            )
        )

    @pytest.mark.asyncio
    async def test_process_build_info(self, processor, mock_embedding_service,
                                      mock_vector_db_service, sample_build_info,
                                      sample_embedding):
        """Test processing build information"""
        # Setup
        metadata = {"test_run_id": "test-run-1"}
        mock_embedding_service.embed_chunks.return_value = [sample_embedding]

        # Execute
        result = await processor.process(sample_build_info, metadata)

        # Assert
        assert result["success"] is True
        assert result["build_id"] == sample_build_info.build_id
        assert "message" in result

        # Verify process_text was called with the correct arguments
        mock_embedding_service.chunk_text.assert_called_once()
        chunk_text_arg = mock_embedding_service.chunk_text.call_args[0][0]
        # The text should contain key build info
        assert sample_build_info.build_id in chunk_text_arg
        assert sample_build_info.build_number in chunk_text_arg
        assert sample_build_info.branch in chunk_text_arg
        assert sample_build_info.commit_hash in chunk_text_arg

        # Verify embed_chunks was called with TextChunk objects
        mock_embedding_service.embed_chunks.assert_called_once()
        chunks_arg = mock_embedding_service.embed_chunks.call_args[0][0]
        assert len(chunks_arg) == 1
        assert isinstance(chunks_arg[0], TextChunk)
        assert chunks_arg[0].text == "Build info text"
        # Metadata should be included
        assert chunks_arg[0].metadata.test_run_id == "test-run-1"
        assert chunks_arg[0].metadata.build_id == sample_build_info.build_id
        assert chunks_arg[0].metadata.chunk_type == "build_info"

        # Verify vector DB insertion was called
        mock_vector_db_service.insert_embeddings.assert_called_once_with([sample_embedding])

    @pytest.mark.asyncio
    async def test_process_build_info_with_metadata(self, processor, sample_build_info):
        """Test that build metadata is included in the text representation"""
        # Setup
        metadata = {"test_run_id": "test-run-1"}

        # Execute
        result = await processor.process(sample_build_info, metadata)

        # Assert
        assert result["success"] is True

        # Verify that the text includes metadata
        chunk_text_arg = processor.embedding_service.chunk_text.call_args[0][0]
        assert "Additional Metadata:" in chunk_text_arg
        assert "triggered_by: user1" in chunk_text_arg
        assert "environment: staging" in chunk_text_arg

    @pytest.mark.asyncio
    async def test_process_build_info_without_url(self, processor, sample_build_info):
        """Test processing build info without a build URL"""
        # Setup
        metadata = {"test_run_id": "test-run-1"}
        sample_build_info.build_url = None  # Remove the URL

        # Execute
        result = await processor.process(sample_build_info, metadata)

        # Assert
        assert result["success"] is True

        # Verify that the text doesn't include a URL
        chunk_text_arg = processor.embedding_service.chunk_text.call_args[0][0]
        assert "Build URL:" not in chunk_text_arg

    @pytest.mark.asyncio
    async def test_process_build_info_without_metadata(self, processor, sample_build_info):
        """Test processing build info without metadata"""
        # Setup
        metadata = {"test_run_id": "test-run-1"}
        sample_build_info.metadata = {}  # Empty metadata

        # Execute
        result = await processor.process(sample_build_info, metadata)

        # Assert
        assert result["success"] is True

        # Verify that the text doesn't include metadata section
        chunk_text_arg = processor.embedding_service.chunk_text.call_args[0][0]
        assert "Additional Metadata:" not in chunk_text_arg