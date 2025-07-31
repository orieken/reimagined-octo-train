# app/services/llm.py
# Replace your entire llm.py file with this complete version

import os
import httpx
from sentence_transformers import SentenceTransformer
from app.config import settings
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class LLMService:
    def __init__(self):
        # Embedding model setup
        model_dir = os.getenv("EMBEDDING_MODEL_DIR", "./models/all-MiniLM-L6-v2")

        if not os.path.isdir(model_dir):
            raise ValueError(f"Embedding model directory not found: {model_dir}")

        logger.info(f"🔍 Loading local embedding model from: {model_dir}")
        self.model = SentenceTransformer(model_dir)

        # Ollama configuration - ADD THESE MISSING ATTRIBUTES
        self.ollama_url = getattr(settings, 'OLLAMA_API_URL', 'http://localhost:11434')
        self.ollama_model = getattr(settings, 'LLM_MODEL', 'llama3:latest')
        self.timeout = getattr(settings, 'LLM_TIMEOUT', 60)

        # Log the configuration
        logger.info(f"🦙 Ollama URL: {self.ollama_url}")
        logger.info(f"🦙 Ollama Model: {self.ollama_model}")

    async def embed_text(self, text: str) -> list[float]:
        """Generate embeddings using SentenceTransformer"""
        if isinstance(text, list):
            return self.model.encode(text).tolist()
        return self.model.encode([text])[0].tolist()

    async def query_ollama(self, prompt: str, context: str = None) -> str:
        """Query the LLM (Ollama) for a completion."""
        try:
            payload = {
                "model": self.ollama_model,
                "prompt": prompt,
                "stream": False
            }
            if context:
                payload["context"] = context

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(f"{self.ollama_url}/api/generate", json=payload)
                response.raise_for_status()

                result = response.json()
                return result.get("response", "")

        except Exception as e:
            logger.error(f"Ollama query failed: {str(e)}")
            return f"I encountered an error while generating the response: {str(e)}"

    async def generate_text(
            self,
            prompt: str,
            system_prompt: Optional[str] = None,
            temperature: float = 0.7,
            max_tokens: int = 500
    ) -> str:
        """
        Generate text using Ollama - wrapper around query_ollama to match expected interface
        """
        try:
            # Combine system prompt with user prompt if provided
            full_prompt = prompt
            if system_prompt:
                full_prompt = f"System: {system_prompt}\n\nUser: {prompt}\n\nAssistant:"

            # Use the existing query_ollama method
            response = await self.query_ollama(full_prompt)
            return response if response else "I couldn't generate a response."

        except Exception as e:
            logger.error(f"Text generation failed: {str(e)}")
            return f"I encountered an error while processing your request: {str(e)}"

    async def health_check(self) -> bool:
        """Check if Ollama server is reachable."""
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                response = await client.get(f"{self.ollama_url}/api/tags")
                response.raise_for_status()
                logger.info("✅ Ollama health check passed")
                return True
        except Exception as e:
            logger.error(f"❌ Ollama health check failed: {str(e)}")
            return False