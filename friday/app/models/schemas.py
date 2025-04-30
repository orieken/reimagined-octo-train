from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, ConfigDict, field_validator
from datetime import datetime
from uuid import uuid4, UUID
from app.services import datetime_service as dt
from .base import TestStatus
from .notification import NotificationStatus, NotificationPriority, NotificationChannel

def default_uuid() -> str:
    return str(uuid4())


class TimestampedModel(BaseModel):
    """Ensures all inheriting models have UTC-aware datetime fields"""

    @field_validator("created_at", "updated_at", "start_time", "end_time", "timestamp", "date", "end_date",
                     mode="before", check_fields=False)
    def ensure_utc(cls, v):
        return dt.ensure_utc_datetime(v)


# ────────────────────────────────
# Core Models
# ────────────────────────────────

class StepSchema(TimestampedModel):
    id: str
    external_id: Optional[str] = None
    name: str
    keyword: Optional[str] = None
    status: str
    duration: Optional[float] = 0.0
    error_message: Optional[str] = None
    stack_trace: Optional[str] = None
    embeddings: Optional[List[Dict[str, Any]]] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    order: Optional[str] = None
    scenario_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class ScenarioSchema(TimestampedModel):
    id: str
    external_id: Optional[str] = None
    name: str
    description: Optional[str] = ""
    status: str
    duration: Optional[float] = 0.0
    tags: List[str] = []
    feature_id: Optional[str] = None
    test_run_id: Optional[str] = None
    steps: List[StepSchema]
    embeddings: Optional[List[Dict[str, Any]]] = None
    is_flaky: Optional[bool] = False
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    metadata: Optional[Dict[str, Any]] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class FeatureSchema(TimestampedModel):
    id: str
    external_id: Optional[str] = None
    name: str
    description: Optional[str] = ""
    uri: Optional[str] = None
    tags: List[str] = []
    scenarios: List[ScenarioSchema]
    project_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class BuildInfoSchema(TimestampedModel):
    id: str = Field(default_factory=default_uuid)
    external_id: Optional[str] = None
    name: str
    build_number: str
    status: str
    branch: Optional[str] = None
    commit_hash: Optional[str] = None
    environment: Optional[str] = None
    duration: Optional[float] = None
    date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    project_id: Optional[str] = None
    meta_data: Optional[Dict[str, Any]] = Field(default_factory=dict, alias="metadata")


class TestRunSchema(TimestampedModel):
    id: str
    external_id: Optional[str] = None
    name: str
    status: Optional[str] = None
    environment: Optional[str] = "unknown"
    timestamp: datetime
    duration: Optional[float] = 0.0
    branch: Optional[str] = None
    commit_hash: Optional[str] = None
    scenarios: List[ScenarioSchema]
    runner: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    total_tests: int = 0
    passed_tests: int = 0
    failed_tests: int = 0
    skipped_tests: int = 0
    error_tests: int = 0
    success_rate: float = 0.0
    project_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

# ────────────────────────────────
# Processor
# ────────────────────────────────

class ProjectSchema(TimestampedModel):
    id: str = Field(default_factory=default_uuid)
    external_id: Optional[str] = None
    name: str
    description: Optional[str] = None
    repository_url: Optional[str] = None
    active: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    meta_data: Optional[Dict[str, Any]] = Field(default_factory=dict, alias="metadata")

class ReportMetadata(BaseModel):
    project: str
    branch: str
    commit: str
    environment: str = "default"
    timestamp: datetime
    test_run_id: str
    project_id: Optional[str] = None

class ProcessCucumberReportRequest(BaseModel):
    metadata: ReportMetadata
    report: List[Dict[str, Any]]

class ProcessorResponse(BaseModel):
    status: str

class MetadataSchema(BaseModel):
    project: str
    branch: Optional[str] = None
    commit: Optional[str] = None
    environment: Optional[str] = None
    runner: Optional[str] = None
    timestamp: datetime
    test_run_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    project_id: Optional[str] = None


# ────────────────────────────────
# Search & Analysis
# ────────────────────────────────

class SearchQueryBase(BaseModel):
    query_text: str
    filters: Optional[Dict[str, Any]] = None
    result_count: Optional[int] = None
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    timestamp: Optional[datetime] = None
    duration: Optional[float] = None


class SearchQueryCreate(SearchQueryBase):
    pass


class SearchQueryResponse(SearchQueryBase):
    id: UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AnalysisRequestBase(BaseModel):
    request_type: str
    parameters: Dict[str, Any]
    status: Optional[str] = "PENDING"
    user_id: Optional[str] = None


class AnalysisRequestCreate(AnalysisRequestBase):
    pass


class AnalysisRequestResponse(AnalysisRequestBase):
    id: UUID
    created_at: datetime
    updated_at: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)


class AnalysisResultBase(BaseModel):
    result_data: Dict[str, Any]
    summary: Optional[str] = None


class AnalysisResultCreate(AnalysisResultBase):
    request_id: UUID


class AnalysisResultResponse(AnalysisResultBase):
    id: UUID
    request_id: UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TextChunkBase(BaseModel):
    text: str
    document_id: str
    document_type: str
    chunk_index: int
    meta_data: Optional[Dict[str, Any]] = None
    quadrant_vector_id: Optional[str] = None


class TextChunkCreate(TextChunkBase):
    pass


class TextChunkResponse(TextChunkBase):
    id: UUID
    created_at: datetime
    updated_at: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)

# ────────────────────────────────
# Notification
# ────────────────────────────────

class NotificationBase(BaseModel):
    message: str
    subject: Optional[str] = None
    status: NotificationStatus = NotificationStatus.PENDING
    priority: NotificationPriority = NotificationPriority.MEDIUM
    channel: NotificationChannel
    meta_data: Optional[Dict[str, Any]] = Field(default_factory=dict, alias="metadata")


class NotificationCreate(NotificationBase):
    pass


class NotificationUpdate(BaseModel):
    status: Optional[NotificationStatus] = None
    meta_data: Optional[Dict[str, Any]] = None
    sent_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class NotificationResponse(NotificationBase):
    id: UUID
    external_id: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    sent_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

# ────────────────────────────────
# Aliases
# ────────────────────────────────

TestStepSchema = StepSchema
TestCaseSchema = ScenarioSchema
ReportSchema = TestRunSchema
