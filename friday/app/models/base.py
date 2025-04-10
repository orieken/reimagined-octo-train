# base.py
from enum import Enum, auto
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
import uuid


# Status Enums
class TestStatus(str, Enum):
    """Enum for test execution status."""
    PASSED = "PASSED"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    ERROR = "ERROR"
    UNDEFINED = "UNDEFINED"


class ReportFormat(str, Enum):
    """Supported report output formats."""
    HTML = "HTML"
    PDF = "PDF"
    CSV = "CSV"
    JSON = "JSON"
    XML = "XML"


class ReportStatus(str, Enum):
    """Report generation status."""
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class ReportType(str, Enum):
    """Types of reports that can be generated."""
    TEST_SUMMARY = "TEST_SUMMARY"
    BUILD_HEALTH = "BUILD_HEALTH"
    FEATURE_COVERAGE = "FEATURE_COVERAGE"
    TREND_ANALYSIS = "TREND_ANALYSIS"
    CUSTOM = "CUSTOM"


class NotificationPriority(str, Enum):
    """Notification priority levels."""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class NotificationStatus(str, Enum):
    """Notification delivery status."""
    PENDING = "pending"
    SENDING = "sending"
    DELIVERED = "delivered"
    FAILED = "failed"


class NotificationChannel(str, Enum):
    """Notification delivery channels."""
    EMAIL = "email"
    IN_APP = "in_app"
    SLACK = "slack"
    TEAMS = "teams"
    WEBHOOK = "webhook"


class BuildEnvironment(str, Enum):
    """Common build environments."""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    QA = "qa"
    SANDBOX = "sandbox"


# Metadata Models
class ChunkMetadata(BaseModel):
    """Metadata for a text chunk."""
    source: Optional[str] = None
    source_id: Optional[str] = None
    chunk_index: Optional[int] = None
    document_type: Optional[str] = None
    context: Dict[str, Any] = Field(default_factory=dict)
    model_config = ConfigDict(
        json_schema_extra = {
            "example": {
                "source": "test_report.txt",
                "source_id": "TR-2023-001",
                "chunk_index": 1,
                "document_type": "test_report",
                "context": {"project": "Test Project"}
            }
        }
    )


class TextChunk(BaseModel):
    """Model representing a chunk of text with metadata."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    text: str
    metadata: ChunkMetadata = Field(default_factory=ChunkMetadata)
    chunk_size: Optional[int] = None
    model_config = ConfigDict(
        json_schema_extra = {
            "example": {
                "id": "chunk-123",
                "text": "This is a sample text chunk from a test report.",
                "metadata": {
                    "source": "test_report.txt",
                    "source_id": "TR-2023-001"
                },
                "chunk_size": 50
            }
        }
    )


class TextEmbedding(BaseModel):
    """Model representing a text embedding vector."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    vector: List[float]
    text_chunk_id: str
    model: Optional[str] = None
    model_config = ConfigDict(
        json_schema_extra = {
            "example": {
                "id": "embedding-123",
                "vector": [0.1, 0.2, 0.3],
                "text_chunk_id": "chunk-123",
                "model": "text-embedding-ada-002"
            }
        }
    )


# Tag Models
class Tag(BaseModel):
    """Generic tag model."""
    name: str
    description: Optional[str] = None
    color: Optional[str] = None
    model_config = ConfigDict(
        json_schema_extra = {
            "example": {
                "name": "performance",
                "description": "Performance-related tests",
                "color": "#FF5733"
            }
        }
    )


# Common Configuration Models
class ConfigurationItem(BaseModel):
    """Represents a configuration item with key-value pair."""
    key: str
    value: Any
    description: Optional[str] = None
    model_config = ConfigDict(
        json_schema_extra = {
            "example": {
                "key": "max_retry_attempts",
                "value": 3,
                "description": "Maximum number of retry attempts for tests"
            }
        }
    )


# Pagination Model
class PaginationParams(BaseModel):
    """Standard pagination parameters."""
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=10, ge=1, le=100)
    total_items: Optional[int] = None
    total_pages: Optional[int] = None
    model_config = ConfigDict(
        json_schema_extra = {
            "example": {
                "page": 1,
                "page_size": 20,
                "total_items": 100,
                "total_pages": 5
            }
        }
    )

class ReportFrequency(str, Enum):
    """Enum for report generation frequency."""
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    ANNUALLY = "annually"