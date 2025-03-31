"""
Configuration management for Friday Service
"""
import os
from typing import List, Optional
from functools import lru_cache

from pydantic import Field, validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings"""

    # Service configuration
    SERVICE_NAME: str = "friday"
    API_PREFIX: str = "/api/v1"
    DEBUG: bool = Field(default=False)

    # App configuration
    APP_NAME: str = "Friday Test Analysis Service"
    APP_VERSION: str = "1.0.0"
    HOST: str = "0.0.0.0"
    PORT: int = 4000

    # CORS settings
    CORS_ORIGINS: List[str] = Field(default=["*"])

    # LLM settings
    OLLAMA_API_URL: str = Field(default="http://localhost:11434")
    OLLAMA_MODEL: str = Field(default="llama2")
    OLLAMA_TIMEOUT: int = Field(default=60)
    LLM_MODEL: str = "llama3"
    LLM_TIMEOUT: int = 60

    # Vector DB settings
    QDRANT_URL: str = Field(default="http://localhost:6333")
    QDRANT_COLLECTION: str = Field(default="friday_tests")
    QDRANT_VECTOR_SIZE: int = Field(default=384)  # Depends on embedding model
    VECTOR_DB_TYPE: str = "qdrant"
    VECTOR_DIMENSION: int = 384
    CUCUMBER_COLLECTION: str = "cucumber_reports"
    BUILD_INFO_COLLECTION: str = "build_info"

    # Embedding settings
    EMBEDDING_MODEL: str = "sentence-transformers/all-MiniLM-L6-v2"

    # Processing settings
    CHUNK_SIZE: int = Field(default=1000)
    CHUNK_OVERLAP: int = Field(default=200)

    # Query settings
    MAX_RESULTS: int = Field(default=5)
    SIMILARITY_THRESHOLD: float = Field(default=0.7)
    DEFAULT_QUERY_LIMIT: int = 5

    # Storage settings
    DATA_DIR: str = "./data"

    @validator("OLLAMA_API_URL", "QDRANT_URL")
    def validate_urls(cls, v):
        """Validate URL format"""
        if not v.startswith(("http://", "https://")):
            raise ValueError("URL must start with http:// or https://")
        return v

    def __hash__(self):
        """Make Settings hashable for lru_cache"""
        return hash(f"{self.SERVICE_NAME}-{self.APP_VERSION}")

    class Config:
        """Pydantic config"""
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
        extra = "ignore"  # Allow extra fields in the environment


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings singleton"""
    return Settings()


settings = get_settings()