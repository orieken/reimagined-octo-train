# app/api/dependencies.py
from functools import lru_cache

from app.services.vector_db import VectorDBService
from app.services.llm import LLMService
from app.services.orchestrator import ServiceOrchestrator
from app.config import settings

@lru_cache()
def get_vector_db_service():
    """Get a VectorDBService instance (singleton) with configuration from settings."""
    return VectorDBService()

@lru_cache()
def get_llm_service():
    """Get a LLMService instance (singleton) with configuration from settings."""
    return LLMService()

@lru_cache()
def get_orchestrator_service():
    """Get a ServiceOrchestrator instance (singleton) using the other services."""
    vector_db = get_vector_db_service()
    llm = get_llm_service()
    return ServiceOrchestrator(
        vector_db_service=vector_db,
        llm_service=llm
    )

# Aliases to match expected function names that might be in use
def get_retrieval_service():
    """Alias for get_vector_db_service."""
    return get_vector_db_service()

def get_generator_service():
    """Alias for get_llm_service."""
    return get_llm_service()