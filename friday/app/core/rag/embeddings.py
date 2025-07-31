"""
Embedding service for the RAG pipeline
"""
import uuid
from typing import List

from app.models.domain import TextChunk, TextEmbedding
from app.services.llm import LLMService


class EmbeddingService:
    """Service for generating and managing embeddings"""

    def __init__(self, llm_service: LLMService, chunk_size: int, chunk_overlap: int):
        """
        Initialize the embedding service

        Args:
            llm_service: LLM service for generating embeddings
            chunk_size: Size of text chunks
            chunk_overlap: Overlap between chunks
        """
        self.llm_service = llm_service
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def chunk_text(self, text: str) -> List[str]:
        """
        Split text into chunks

        Args:
            text: Text to split

        Returns:
            List of text chunks
        """
        if len(text) <= self.chunk_size:
            return [text]

        chunks = []
        for i in range(0, len(text), self.chunk_size - self.chunk_overlap):
            chunk = text[i:i + self.chunk_size]
            if chunk:
                chunks.append(chunk)

        return chunks

    async def embed_chunk(self, chunk: TextChunk) -> TextEmbedding:
        """
        Generate embedding for a text chunk

        Args:
            chunk: Text chunk to embed

        Returns:
            Text embedding
        """
        vector = await self.llm_service.embed_text(chunk.text)

        return TextEmbedding(
            id=str(uuid.uuid4()),
            vector=vector,
            text=chunk.text,
            metadata=chunk.metadata
        )

    async def embed_chunks(self, chunks: List[TextChunk]) -> List[TextEmbedding]:
        """
        Generate embeddings for multiple text chunks

        Args:
            chunks: Text chunks to embed

        Returns:
            List of text embeddings
        """
        embeddings = []
        for chunk in chunks:
            embedding = await self.embed_chunk(chunk)
            embeddings.append(embedding)

        return embeddings