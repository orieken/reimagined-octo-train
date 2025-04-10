# responses.py
from typing import List, Dict, Any, Optional, Union
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime

from .base import (
    TestStatus,
    ReportFormat,
    ReportStatus,
    ReportType,
    NotificationPriority,
    NotificationStatus,
    NotificationChannel
)

from .schemas import (
    ProjectResponse,
    TestRunResponse,
    FeatureResponse,
    ScenarioResponse,
    StepResponse,
    ReportResponse, TestResultsTag
)


class ErrorResponse(BaseModel):
    """Standardized error response model."""
    error_code: str
    message: str
    details: Optional[Dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=datetime.now)

    model_config = ConfigDict(
        json_schema_extra = {
            "example": {
                "error_code": "VALIDATION_ERROR",
                "message": "Invalid input provided",
                "details": {
                    "field": "name",
                    "reason": "Name cannot be empty"
                }
            }
        }
    )


class SuccessResponse(BaseModel):
    """Standard success response model."""
    status: str = "success"
    message: str
    data: Optional[Dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=datetime.now)

    model_config = ConfigDict(
        json_schema_extra = {
            "example": {
                "status": "success",
                "message": "Operation completed successfully",
                "data": {
                    "id": "123",
                    "created_at": "2023-06-15T10:30:00Z"
                }
            }
        }
    )


class PaginatedResponse(BaseModel):
    """Generic paginated response model."""
    items: List[Any]
    total_items: int
    page: int
    page_size: int
    total_pages: int

    model_config = ConfigDict(
        json_schema_extra = {
            "example": {
                "items": [],
                "total_items": 100,
                "page": 1,
                "page_size": 10,
                "total_pages": 10
            }
        }
    )


class SearchResultItem(BaseModel):
    """Detailed search result item."""
    id: str
    type: str
    score: float
    content: Dict[str, Any]

    model_config = ConfigDict(
        json_schema_extra = {
            "example": {
                "id": "result-123",
                "type": "scenario",
                "score": 0.95,
                "content": {
                    "name": "User Login Test",
                    "status": "PASSED"
                }
            }
        }
    )


class SearchResponse(BaseModel):
    """Comprehensive search response model."""
    query: str
    results: List[SearchResultItem]
    total_hits: int
    execution_time_ms: float
    page: int = 1
    page_size: int = 10

    model_config = ConfigDict(
        json_schema_extra = {
            "example": {
                "query": "login test",
                "results": [],
                "total_hits": 5,
                "execution_time_ms": 45.5,
                "page": 1,
                "page_size": 10
            }
        }
    )


class TestRunAnalyticsResponse(BaseModel):
    """Detailed analytics for test runs."""
    test_runs: List[TestRunResponse]
    total_runs: int
    pass_rate: float
    average_duration: float
    status_distribution: Dict[TestStatus, int]

    model_config = ConfigDict(
        json_schema_extra = {
            "example": {
                "total_runs": 50,
                "pass_rate": 0.90,
                "average_duration": 1200.5,
                "status_distribution": {
                    "PASSED": 45,
                    "FAILED": 5
                }
            }
        }
    )


class FeatureAnalyticsResponse(BaseModel):
    """Comprehensive feature analytics."""
    features: List[FeatureResponse]
    total_features: int
    pass_rate: float
    most_stable_feature: Optional[str] = None
    most_problematic_feature: Optional[str] = None

    model_config = ConfigDict(
        json_schema_extra = {
            "example": {
                "total_features": 10,
                "pass_rate": 0.85,
                "most_stable_feature": "User Authentication",
                "most_problematic_feature": "Payment Processing"
            }
        }
    )


class TestTrendResponse(BaseModel):
    """Test trend analysis response."""
    trend_points: List[Dict[str, Any]]
    start_date: datetime
    end_date: datetime
    pass_rate_trend: List[float]
    failure_trend: List[float]

    model_config = ConfigDict(
        json_schema_extra = {
            "example": {
                "start_date": "2023-01-01T00:00:00",
                "end_date": "2023-06-30T23:59:59",
                "pass_rate_trend": [0.8, 0.85, 0.9],
                "failure_trend": [0.2, 0.15, 0.1]
            }
        }
    )


class NotificationResponse(BaseModel):
    """Notification response model."""
    id: str
    title: str
    content: str
    priority: NotificationPriority
    status: NotificationStatus
    channel: NotificationChannel
    created_at: datetime
    is_read: bool = False

    model_config = ConfigDict(
        json_schema_extra = {
            "example": {
                "id": "notif-123",
                "title": "Test Run Completed",
                "content": "Nightly regression tests have finished",
                "priority": "medium",
                "status": "delivered",
                "channel": "email",
                "is_read": False
            }
        }
    )

class HealthCheckResponse(BaseModel):
    """System health check response."""
    overall_status: str
    services: Dict[str, str]
    timestamp: datetime = Field(default_factory=datetime.now)

    model_config = ConfigDict(
        json_schema_extra = {
            "example": {
                "overall_status": "healthy",
                "services": {
                    "database": "running",
                    "test_runner": "running",
                    "notification_service": "degraded"
                }
            }
        }
    )


class BatchOperationResponse(BaseModel):
    """Response for batch operations."""
    total_processed: int
    successful: int
    failed: int
    errors: Optional[List[Dict[str, Any]]] = None

    model_config = ConfigDict(
        json_schema_extra = {
            "example": {
                "total_processed": 100,
                "successful": 95,
                "failed": 5,
                "errors": [
                    {
                        "item_id": "test-123",
                        "error_message": "Validation failed"
                    }
                ]
            }
        }
    )

class AnalysisResponse(BaseModel):
    """Response model for analysis endpoint."""
    query: str
    timestamp: str
    recommendations: List[str] = Field(default_factory=list)
    related_items: List[Dict[str, Any]] = Field(default_factory=list)
    summary: str

    model_config = ConfigDict(
        json_schema_extra = {
            "example": {
                "query": "Login failures",
                "timestamp": "2023-06-15T10:30:00Z",
                "recommendations": [
                    "Investigate Chrome-specific authentication issues",
                    "Review server load during peak hours"
                ],
                "related_items": [
                    {
                        "type": "scenario",
                        "id": "scenario-123",
                        "details": "Failed login attempt"
                    }
                ],
                "summary": "Identified recurring login failures across multiple test runs"
            }
        }
    )

class ReportSummaryResponse(BaseModel):
    """Response for report summary endpoint."""
    report_id: str
    summary: str
    timestamp: str

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "report_id": "RPT-2023-001",
                "summary": "Comprehensive test run summary highlighting key findings and performance metrics",
                "timestamp": "2023-06-15T10:30:00Z"
            }
        }
    )

class TestCaseInsightsResponse(BaseModel):
    """Response for test case insights endpoint."""
    test_case_id: str
    test_case: Optional[Dict[str, Any]] = None
    analysis: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    recommendations: List[str] = Field(default_factory=list)
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())

    model_config = ConfigDict(
        json_schema_extra = {
            "example": {
                "test_case_id": "TC-2023-001",
                "test_case": {
                    "name": "User Login Test",
                    "status": "FAILED"
                },
                "analysis": {
                    "root_cause": "Authentication service timeout"
                },
                "error": "Connection timeout during login",
                "recommendations": [
                    "Check network connectivity",
                    "Verify authentication service status"
                ],
                "timestamp": "2023-06-15T10:30:00Z"
            }
        }
    )

class ProcessingStatusResponse(BaseModel):
    """Response for checking processing status."""
    task_id: str
    status: str
    progress: float = 0.0  # 0.0 to 1.0
    message: Optional[str] = None
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())

    model_config = ConfigDict(
        json_schema_extra = {
            "example": {
                "task_id": "task-123",
                "status": "running",
                "progress": 0.5,
                "message": "Processing test results",
                "timestamp": "2023-06-15T10:30:00Z"
            }
        }
    )

class TestResultsListResponse(BaseModel):
    """Response for listing test results."""
    results: List[Dict[str, Any]] = Field(default_factory=list)
    total: int = 0
    page: int = 1
    page_size: int = 10

    model_config = ConfigDict(
        json_schema_extra = {
            "example": {
                "results": [
                    {
                        "id": "test-result-123",
                        "name": "User Login Test",
                        "status": "PASSED",
                        "duration": 1200.5,
                        "timestamp": "2023-06-15T10:30:00Z"
                    }
                ],
                "total": 50,
                "page": 1,
                "page_size": 10
            }
        }
    )

class TestResultsResponse(BaseModel):
    """Comprehensive response for test results endpoint."""
    id: str
    name: str
    status: TestStatus
    timestamp: str
    duration: float
    environment: str
    features: List[Dict[str, Any]] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)
    statistics: Dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(
        json_schema_extra = {
            "example": {
                "id": "test-run-123",
                "name": "Nightly Regression Test",
                "status": "COMPLETED",
                "timestamp": "2023-06-15T10:30:00Z",
                "duration": 3600.5,
                "environment": "staging",
                "features": [
                    {
                        "name": "User Authentication",
                        "total_scenarios": 10,
                        "passed_scenarios": 8,
                        "failed_scenarios": 2
                    }
                ],
                "tags": ["regression", "nightly"],
                "statistics": {
                    "total_scenarios": 50,
                    "passed_scenarios": 45,
                    "failed_scenarios": 5,
                    "pass_rate": 0.9
                }
            }
        }
    )

class TestCaseListResponse(BaseModel):
    """Response for listing test cases."""
    test_cases: List[ScenarioResponse] = Field(default_factory=list)
    total: int = 0
    page: int = 1
    page_size: int = 10

    model_config = ConfigDict(
        json_schema_extra = {
            "example": {
                "test_cases": [
                    {
                        "id": "scenario-123",
                        "name": "User Login Scenario",
                        "status": "PASSED",
                        "feature": "Authentication",
                        "duration": 1200.5,
                        "tags": ["smoke", "login"]
                    }
                ],
                "total": 50,
                "page": 1,
                "page_size": 10
            }
        }
    )

class ScenarioResult(BaseModel):
    """Model representing a scenario result."""
    id: str
    name: str
    status: str
    feature: str
    duration: float = 0
    error_message: Optional[str] = None
    tags: List[TestResultsTag] = Field(default_factory=list)

    model_config = ConfigDict(
        json_schema_extra = {
            "example": {
                "id": "scenario-123",
                "name": "User Login Scenario",
                "status": "PASSED",
                "feature": "Authentication",
                "duration": 1200.5,
                "error_message": None,
                "tags": [
                    {"name": "smoke"},
                    {"name": "login"}
                ]
            }
        }
    )

class StatisticsResponse(BaseModel):
    """Response for statistics endpoint."""
    total_test_cases: int = 0
    status_counts: Dict[str, int] = Field(default_factory=dict)
    pass_rate: float = 0.0
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())

    model_config = ConfigDict(
        json_schema_extra = {
            "example": {
                "total_test_cases": 100,
                "status_counts": {
                    "PASSED": 90,
                    "FAILED": 5,
                    "SKIPPED": 5
                },
                "pass_rate": 0.90,
                "timestamp": "2023-06-15T10:30:00Z"
            }
        }
    )

class StepResult(BaseModel):
    """Model representing a test step result."""
    id: str
    name: str
    keyword: str
    status: str
    duration: Optional[float] = None
    error_message: Optional[str] = None
    screenshot: Optional[str] = None
    logs: Optional[List[str]] = None

    model_config = ConfigDict(
        json_schema_extra = {
            "example": {
                "id": "step-123",
                "name": "Enter username",
                "keyword": "When",
                "status": "PASSED",
                "duration": 250.5,
                "error_message": None,
                "screenshot": "/path/to/screenshot.png",
                "logs": [
                    "Entered username successfully",
                    "Validated input field"
                ]
            }
        }
    )

class ProcessReportResponse(BaseModel):
    """Response model for cucumber report processing."""
    status: str  # Using a string instead of ReportStatus enum
    message: str
    report_id: Optional[str] = None
    task_id: Optional[str] = None
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())

    model_config = ConfigDict(
        json_schema_extra = {
            "example": {
                "status": "accepted",
                "message": "Report processing started for project-name (main)",
                "report_id": "report-123",
                "task_id": "task-123",
                "timestamp": "2023-06-15T10:30:00Z"
            }
        }
    )