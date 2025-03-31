# src/config/app_config.py
from typing import Optional, List
from pydantic import BaseModel, Field, validator
import os
from functools import lru_cache


class QdrantConfig(BaseModel):
    """Configuration for Qdrant vector database."""
    url: str = Field(default="http://localhost:6333")
    api_key: Optional[str] = Field(default=None)
    reports_collection: str = Field(default="friday_reports")
    testcases_collection: str = Field(default="friday_testcases")
    teststeps_collection: str = Field(default="friday_teststeps")

    @validator('url')
    def url_must_be_valid(cls, v):
        if not v.startswith(('http://', 'https://')):
            raise ValueError('URL must start with http:// or https://')
        return v


class OllamaConfig(BaseModel):
    """Configuration for Ollama LLM service."""
    url: str = Field(default="http://localhost:11434")
    embedding_model: str = Field(default="nomic-embed-text")
    generation_model: str = Field(default="llama3")
    timeout_seconds: int = Field(default=30)

    @validator('url')
    def url_must_be_valid(cls, v):
        if not v.startswith(('http://', 'https://')):
            raise ValueError('URL must start with http:// or https://')
        return v


class ServerConfig(BaseModel):
    """Configuration for the API server."""
    host: str = Field(default="0.0.0.0")
    port: int = Field(default=8000)
    debug: bool = Field(default=False)
    workers: int = Field(default=1)
    cors_origins: List[str] = Field(default=["*"])


class LoggingConfig(BaseModel):
    """Configuration for logging."""
    level: str = Field(default="INFO")
    format: str = Field(default="%(asctime)s - %(name)s - %(levelname)s - %(message)s")


class AppConfig(BaseModel):
    """Main application configuration."""
    qdrant: QdrantConfig = Field(default_factory=QdrantConfig)
    ollama: OllamaConfig = Field(default_factory=OllamaConfig)
    server: ServerConfig = Field(default_factory=ServerConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)


@lru_cache()
def get_app_config() -> AppConfig:
    """Load application configuration from environment or defaults."""
    # Load Qdrant configuration
    qdrant_config = QdrantConfig(
        url=os.getenv("QDRANT_URL", "http://localhost:6333"),
        api_key=os.getenv("QDRANT_API_KEY"),
        reports_collection=os.getenv("QDRANT_REPORTS_COLLECTION", "friday_reports"),
        testcases_collection=os.getenv("QDRANT_TESTCASES_COLLECTION", "friday_testcases"),
        teststeps_collection=os.getenv("QDRANT_TESTSTEPS_COLLECTION", "friday_teststeps")
    )

    # Load Ollama configuration
    ollama_config = OllamaConfig(
        url=os.getenv("OLLAMA_URL", "http://localhost:11434"),
        embedding_model=os.getenv("OLLAMA_EMBEDDING_MODEL", "nomic-embed-text"),
        generation_model=os.getenv("OLLAMA_GENERATION_MODEL", "llama3"),
        timeout_seconds=int(os.getenv("OLLAMA_TIMEOUT_SECONDS", "30"))
    )

    # Load server configuration
    server_config = ServerConfig(
        host=os.getenv("SERVER_HOST", "0.0.0.0"),
        port=int(os.getenv("SERVER_PORT", "8000")),
        debug=os.getenv("SERVER_DEBUG", "False").lower() in ("true", "1", "t"),
        workers=int(os.getenv("SERVER_WORKERS", "1")),
        cors_origins=os.getenv("CORS_ORIGINS", "*").split(",")
    )

    # Load logging configuration
    logging_config = LoggingConfig(
        level=os.getenv("LOG_LEVEL", "INFO"),
        format=os.getenv("LOG_FORMAT", "%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    )

    # Create and return the complete config
    return AppConfig(
        qdrant=qdrant_config,
        ollama=ollama_config,
        server=server_config,
        logging=logging_config
    )