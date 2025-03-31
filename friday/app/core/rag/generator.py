"""
Generator service for the RAG pipeline
"""
from typing import Dict, List, Optional

from app.services.llm import LLMService


class GeneratorService:
    """Service for generating responses using the LLM"""

    def __init__(self, llm_service: LLMService):
        """
        Initialize the generator service

        Args:
            llm_service: LLM service for generating text
        """
        self.llm_service = llm_service

    async def generate(
            self,
            query: str,
            context: str,
            max_tokens: int = 1000,
            temperature: float = 0.7
    ) -> Dict:
        """
        Generate a response for a query using the provided context

        Args:
            query: User query
            context: Context information retrieved from the vector database
            max_tokens: Maximum number of tokens to generate
            temperature: Temperature for generation

        Returns:
            Dict with the generated answer and metadata
        """
        system_message = """
        You are an AI assistant that helps analyze Cucumber test reports.
        Use the provided context to answer the user's question specifically and concisely.
        If you don't know the answer based on the context, say so clearly.
        Do not make up information. Cite your sources when possible.
        """

        prompt = f"""
        Question: {query}

        Context:
        {context}

        Answer:
        """

        answer = await self.llm_service.generate_text(
            prompt=prompt,
            max_tokens=max_tokens,
            temperature=temperature,
            system_message=system_message
        )

        # Calculate confidence (in Phase 2, this will be more sophisticated)
        confidence = 0.8 if context else 0.4

        return {
            "answer": answer,
            "confidence": confidence
        }