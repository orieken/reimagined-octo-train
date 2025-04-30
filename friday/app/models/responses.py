from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime

from app.models.schemas import (
    TestCaseSchema, TestRunSchema, FeatureSchema,
    SearchQueryResponse, AnalysisResultResponse
)


class SuccessResponse(BaseModel):
    status: str = "success"
    message: Optional[str] = None
    data: Optional[Any] = None


class ErrorResponse(BaseModel):
    status: str = "error"
    error: str
    detail: Optional[str] = None
    code: Optional[int] = None


class PaginatedResponse(BaseModel):
    total: int
    page: int
    page_size: int
    results: List[Any]


class SearchResponse(BaseModel):
    query: str
    total_matches: int
    results: List[Dict[str, Any]]


class ProcessingStatusResponse(BaseModel):
    status: str
    processed_items: int
    failed_items: int
    errors: Optional[List[str]] = None
    timestamp: datetime


class HealthCheckResponse(BaseModel):
    status: str
    uptime_seconds: Optional[float]
    version: Optional[str]
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class TestRunAnalyticsResponse(BaseModel):
    total_runs: int
    average_duration: float
    average_pass_rate: float
    environments: List[str]


class FeatureAnalyticsResponse(BaseModel):
    feature_name: str
    total_scenarios: int
    passed: int
    failed: int
    flaky: int
    pass_rate: float


class TestTrendResponse(BaseModel):
    date: str
    pass_rate: float
    avg_duration: float
    total_tests: int


class NotificationResponse(BaseModel):
    id: UUID
    message: str
    subject: Optional[str]
    status: str
    priority: str
    channel: str
    metadata: Optional[Dict[str, Any]] = None
    created_at: datetime
    sent_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class BatchOperationResponse(BaseModel):
    success_count: int
    failure_count: int
    errors: Optional[List[str]] = None

class ProcessReportResponse(BaseModel):
    status: str
    message: str
    report_id: str
    project_id: str  # <- was UUID
    imported_scenarios: int
    imported_steps: int
    task_id: Optional[str] = None
    timestamp: str


class ReportResponse(TestRunSchema):
    report_id: UUID
    task_id: Optional[str] = None
    status: str
    timestamp: datetime

class AnalysisResponse(BaseModel):
    id: UUID
    request_type: str
    parameters: Dict[str, Any]
    status: str
    user_id: Optional[str]
    summary: Optional[str]
    result_data: Dict[str, Any]
    created_at: datetime

class SuccessResponse(BaseModel):
    success: bool = True
    message: Optional[str] = "OK"


class ReportResponse(SuccessResponse):
    report: Optional[TestRunSchema]


class TestCaseInsightsResponse(BaseModel):
    id: UUID
    name: str
    status: str
    insights: List[str]


class ReportSummaryResponse(BaseModel):
    report_id: UUID
    total: int
    passed: int
    failed: int
    skipped: int
    duration: float


class AnalysisResponse(BaseModel):
    query: SearchQueryResponse
    results: List[AnalysisResultResponse]
    metadata: Optional[Dict[str, Any]] = None