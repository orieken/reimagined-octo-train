"""
Base processor for Friday
"""
from abc import ABC, abstractmethod
from typing import Dict, List, Any

from app.core.rag.embeddings import EmbeddingService
from app.models.domain import TextChunk, TextEmbedding
from app.services.vector_db import VectorDBService


class BaseProcessor(ABC):
    """Base class for all processors"""

    def __init__(self, embedding_service: EmbeddingService, vector_db_service: VectorDBService):
        """
        Initialize the base processor

        Args:
            embedding_service: Service for generating embeddings
            vector_db_service: Service for storing embeddings
        """
        self.embedding_service = embedding_service
        self.vector_db_service = vector_db_service

    @abstractmethod
    async def process(self, data: Any, metadata: Dict) -> Dict:
        """
        Process input data

        Args:
            data: Input data to process
            metadata: Additional metadata for processing

        Returns:
            Processing results
        """
        pass

    async def process_text(self, text: str, metadata: Dict) -> List[str]:
        """
        Process text by chunking, embedding, and storing in the vector database

        Args:
            text: Text to process
            metadata: Metadata for the text chunks

        Returns:
            List of IDs of the stored embeddings
        """
        # Create chunk metadata
        chunk_metadata = metadata.copy()

        # Split text into chunks
        text_chunks = self.embedding_service.chunk_text(text)

        # Create TextChunk objects
        chunks = [
            TextChunk(text=chunk, metadata=chunk_metadata)
            for chunk in text_chunks
        ]

        # Generate embeddings
        embeddings = await self.embedding_service.embed_chunks(chunks)

        # Store embeddings in vector database
        ids = await self.vector_db_service.insert_embeddings(embeddings)

        return ids