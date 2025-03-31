"""
Retrieval service for the RAG pipeline
"""
from typing import Dict, List, Optional

from app.services.vector_db import VectorDBService


class RetrievalService:
    """Service for retrieving relevant text chunks for a query"""

    def __init__(
            self,
            vector_db_service: VectorDBService,
            max_results: int,
            similarity_threshold: float
    ):
        """
        Initialize the retrieval service

        Args:
            vector_db_service: Vector database service
            max_results: Maximum number of results to return
            similarity_threshold: Threshold for similarity scores
        """
        self.vector_db_service = vector_db_service
        self.max_results = max_results
        self.similarity_threshold = similarity_threshold

    async def retrieve(self, query_vector: List[float], filters: Optional[Dict] = None) -> List[Dict]:
        """
        Retrieve relevant text chunks for a query vector

        Args:
            query_vector: Query embedding vector
            filters: Optional filters to apply

        Returns:
            List of text chunks with scores
        """
        results = await self.vector_db_service.search(
            query_vector=query_vector,
            limit=self.max_results,
            filters=filters
        )

        # Filter by similarity threshold
        filtered_results = [
            result for result in results
            if result.get("score", 0) >= self.similarity_threshold
        ]

        return filtered_results

    def format_context(self, results: List[Dict]) -> str:
        """
        Format retrieved results into a context string for the generator

        Args:
            results: List of retrieval results

        Returns:
            Formatted context string
        """
        if not results:
            return ""

        context_parts = []
        for i, result in enumerate(results):
            text = result.get("text", "")
            score = result.get("score", 0)
            source = result.get("metadata", {}).get("source", "Unknown")

            context_parts.append(f"[{i + 1}] {text} (Source: {source}, Relevance: {score:.2f})")

        return "\n\n".join(context_parts)