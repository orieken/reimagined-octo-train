# schemas.py
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timezone
from pydantic import BaseModel, Field, ConfigDict

from .search_analysis import TrendAnalysis
from .base import (
    TestStatus,
    ReportFormat,
    ReportStatus,
    ReportType,
    BuildEnvironment, ReportFrequency
)


# Helper function to get timezone-aware UTC datetime
def utcnow():
    """Return current UTC datetime with timezone information."""
    return datetime.now(timezone.utc)


# Helper function to get ISO formatted string with timezone info
def utcnow_iso():
    """Return current UTC datetime as ISO 8601 string with timezone information."""
    return datetime.now(timezone.utc).isoformat()


# Project-related Schemas
class ProjectBase(BaseModel):
    """Base model for project-related operations."""
    name: str
    description: Optional[str] = None
    repository_url: Optional[str] = None
    active: bool = True
    meta_data: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(
        json_schema_extra = {
            "example": {
                "name": "Test Automation Framework",
                "repository_url": "https://github.com/org/test-framework",
                "active": True
            }
        }
    )


class ProjectCreate(ProjectBase):
    """Model for creating a new project."""
    pass


class ProjectResponse(ProjectBase):
    """Response model for project details."""
    id: int
    created_at: datetime  # Will be timezone-aware
    updated_at: datetime  # Will be timezone-aware


# Test Run Schemas
class TestRunBase(BaseModel):
    """Base model for test run operations."""
    name: str
    description: Optional[str] = None
    status: TestStatus
    environment: Optional[BuildEnvironment] = None
    branch: Optional[str] = None
    commit_hash: Optional[str] = None

    model_config = ConfigDict(
        json_schema_extra = {
            "example": {
                "name": "Nightly Regression",
                "status": "COMPLETED",
                "environment": "staging",
                "branch": "main"
            }
        }
    )


class TestRunCreate(TestRunBase):
    """Model for creating a new test run."""
    project_id: int
    build_id: Optional[int] = None


class TestRunResponse(TestRunBase):
    """Response model for test run details."""
    id: int
    project_id: int
    build_id: Optional[int] = None
    start_time: datetime  # Will be timezone-aware
    end_time: Optional[datetime] = None  # Will be timezone-aware
    duration: Optional[float] = None
    total_tests: int = 0
    passed_tests: int = 0
    failed_tests: int = 0
    skipped_tests: int = 0
    error_tests: int = 0
    success_rate: Optional[float] = None
    created_at: datetime  # Will be timezone-aware
    updated_at: datetime  # Will be timezone-aware


# Feature Schemas
class Feature(BaseModel):
    """Base model for feature operations."""
    name: str
    description: Optional[str] = None
    file_path: Optional[str] = None
    priority: Optional[str] = None
    status: Optional[str] = None
    tags: Optional[List[str]] = None

    model_config = ConfigDict(
        json_schema_extra = {
            "example": {
                "name": "User Authentication",
                "priority": "high",
                "tags": ["login", "security"]
            }
        }
    )


class FeatureCreate(Feature):
    """Model for creating a new feature."""
    project_id: int


class FeatureResponse(Feature):
    """Response model for feature details."""
    id: int
    project_id: int
    created_at: datetime  # Will be timezone-aware
    updated_at: datetime  # Will be timezone-aware


# Scenario Schemas
class Scenario(BaseModel):
    """Base model for scenario operations."""
    name: str
    description: Optional[str] = None
    status: TestStatus
    error_message: Optional[str] = None
    stack_trace: Optional[str] = None
    parameters: Optional[Dict[str, Any]] = None
    meta_data: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(
        json_schema_extra = {
            "example": {
                "name": "Successful User Login",
                "status": "PASSED",
                "parameters": {
                    "username": "testuser",
                    "environment": "staging"
                }
            }
        }
    )


# Step Schemas
class StepBase(BaseModel):
    """Base model for step operations."""
    name: str
    description: Optional[str] = None
    status: TestStatus
    error_message: Optional[str] = None
    stack_trace: Optional[str] = None
    screenshot_url: Optional[str] = None
    log_output: Optional[str] = None
    order: int

    model_config = ConfigDict(
        json_schema_extra = {
            "example": {
                "name": "Enter Username",
                "status": "PASSED",
                "order": 1
            }
        }
    )


class StepCreate(StepBase):
    """Model for creating a new step."""
    scenario_id: int
    start_time: Optional[datetime] = None  # Will be timezone-aware if provided
    end_time: Optional[datetime] = None    # Will be timezone-aware if provided
    duration: Optional[float] = None


class StepResponse(StepBase):
    """Response model for step details."""
    id: int
    scenario_id: int
    start_time: Optional[datetime] = None  # Will be timezone-aware
    end_time: Optional[datetime] = None    # Will be timezone-aware
    duration: Optional[float] = None
    created_at: datetime  # Will be timezone-aware
    updated_at: datetime  # Will be timezone-aware


# Tag Schemas
class TagBase(BaseModel):
    """Base model for tag operations."""
    name: str
    description: Optional[str] = None
    color: Optional[str] = None

    model_config = ConfigDict(
        json_schema_extra = {
            "example": {
                "name": "performance",
                "color": "#FF5733"
            }
        }
    )


class TagCreate(TagBase):
    """Model for creating a new tag."""
    pass


class TagResponse(TagBase):
    """Response model for tag details."""
    id: int
    created_at: datetime  # Will be timezone-aware
    updated_at: datetime  # Will be timezone-aware


# Report Schemas
class ReportBase(BaseModel):
    """Base model for report operations."""
    name: str
    description: Optional[str] = None
    report_type: ReportType
    format: ReportFormat
    parameters: Dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(
        json_schema_extra = {
            "example": {
                "name": "Monthly Test Summary",
                "report_type": "TEST_SUMMARY",
                "format": "PDF",
                "parameters": {
                    "start_date": "2023-01-01",
                    "end_date": "2023-01-31"
                }
            }
        }
    )


class ReportCreate(ReportBase):
    """Model for creating a new report."""
    template_id: Optional[str] = None
    project_id: Optional[int] = None


class ReportResponse(ReportBase):
    """Response model for report details."""
    id: str
    status: ReportStatus
    generated_at: Optional[datetime] = None  # Will be timezone-aware
    file_path: Optional[str] = None
    error_message: Optional[str] = None
    created_at: datetime  # Will be timezone-aware
    updated_at: datetime  # Will be timezone-aware


# Statistics and Summary Schemas
class TestStatistics(BaseModel):
    """Comprehensive test run statistics."""
    total_scenarios: int
    passed_scenarios: int
    failed_scenarios: int
    skipped_scenarios: int
    pass_rate: float
    duration: Optional[float] = None

    model_config = ConfigDict(
        json_schema_extra = {
            "example": {
                "total_scenarios": 100,
                "passed_scenarios": 95,
                "failed_scenarios": 5,
                "skipped_scenarios": 0,
                "pass_rate": 0.95,
                "duration": 1200.5
            }
        }
    )


class FeatureStatistics(BaseModel):
    """Feature-level test statistics."""
    feature_name: str
    total_scenarios: int
    passed_scenarios: int
    failed_scenarios: int
    pass_rate: float

    model_config = ConfigDict(
        json_schema_extra = {
            "example": {
                "feature_name": "User Authentication",
                "total_scenarios": 20,
                "passed_scenarios": 18,
                "failed_scenarios": 2,
                "pass_rate": 0.9
            }
        }
    )

class ScenarioCreate(Scenario):
    """Model for creating a new scenario."""
    test_run_id: int
    feature_id: Optional[int] = None
    tags: Optional[List[str]] = None
    start_time: Optional[datetime] = None  # Will be timezone-aware if provided
    end_time: Optional[datetime] = None    # Will be timezone-aware if provided
    duration: Optional[float] = None

class BulkCreateResponse(BaseModel):
    """Response for bulk creation operations."""
    created_items: List[Dict[str, Any]]
    total_created: int
    errors: Optional[List[Dict[str, Any]]] = None

    model_config = ConfigDict(
        json_schema_extra = {
            "example": {
                "created_items": [
                    {"id": 1, "name": "Test Project"}
                ],
                "total_created": 1,
                "errors": []
            }
        }
    )

class CreateScheduleRequest(BaseModel):
    """Request to schedule a report."""
    name: str
    template_id: str
    parameters: Dict[str, Any] = Field(default_factory=dict)
    frequency: ReportFrequency
    next_run: Optional[str] = None

    model_config = ConfigDict(
        json_schema_extra = {
            "example": {
                "name": "Monthly Test Summary",
                "template_id": "template-123",
                "parameters": {
                    "start_date": "2023-01-01",
                    "end_date": "2023-01-31"
                },
                "frequency": "monthly",
                "next_run": "2023-02-01T00:00:00Z"  # Note the Z for UTC
            }
        }
    )

class CreateReportRequest(BaseModel):
    """Request to generate a report."""
    template_id: str
    parameters: Dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(
        json_schema_extra = {
            "example": {
                "template_id": "template-123",
                "parameters": {
                    "start_date": "2023-01-01",
                    "end_date": "2023-01-31",
                    "format": "PDF",
                    "include_details": True
                }
            }
        }
    )

class TestResultsTag(BaseModel):
    """Pydantic model for test results tags."""
    id: Optional[int] = None
    name: str
    description: Optional[str] = None
    color: Optional[str] = None
    created_at: Optional[datetime] = None  # Will be timezone-aware
    updated_at: Optional[datetime] = None  # Will be timezone-aware

    model_config = ConfigDict(
        json_schema_extra = {
            "example": {
                "id": 1,
                "name": "smoke",
                "description": "Smoke test tag",
                "color": "#FF5733"
            }
        }
    )

class TestFlakiness(BaseModel):
    """Model representing flaky test information."""
    id: str
    name: str
    feature: str
    flakiness_score: float = Field(..., description="Score from 0.0 to 1.0, higher is more flaky", ge=0, le=1)
    total_runs: int
    pass_count: int
    fail_count: int
    history: List[Dict[str, Any]] = Field(default_factory=list)

    model_config = ConfigDict(
        json_schema_extra = {
            "example": {
                "id": "test-123",
                "name": "User Login Test",
                "feature": "Authentication",
                "flakiness_score": 0.3,
                "total_runs": 100,
                "pass_count": 85,
                "fail_count": 15,
                "history": [
                    {
                        "run_id": "run-001",
                        "status": "PASSED",
                        "timestamp": "2023-06-15T10:30:00Z"  # Note the Z for UTC
                    }
                ]
            }
        }
    )

class TrendPoint(BaseModel):
    """Data point for trend analysis."""
    timestamp: str
    report_id: str
    total_tests: int = 0
    passed_tests: int = 0
    failed_tests: int = 0
    pass_rate: float = 0.0
    avg_duration: float = 0.0

    model_config = ConfigDict(
        json_schema_extra = {
            "example": {
                "timestamp": "2023-06-15T10:30:00Z",  # Note the Z for UTC
                "report_id": "report-123",
                "total_tests": 100,
                "passed_tests": 90,
                "failed_tests": 10,
                "pass_rate": 0.9,
                "avg_duration": 1200.5
            }
        }
    )

class FailureCorrelation(BaseModel):
    """Model representing correlation between test failures."""
    id: str
    test1_name: str
    test1_feature: str
    test2_name: str
    test2_feature: str
    correlation_score: float = Field(..., description="Score from 0.0 to 1.0, higher means stronger correlation", ge=0, le=1)
    co_failure_count: int = 0
    test1_failure_count: int = 0
    test2_failure_count: int = 0

    model_config = ConfigDict(
        json_schema_extra = {
            "example": {
                "id": "correlation-123",
                "test1_name": "User Login Test",
                "test1_feature": "Authentication",
                "test2_name": "Password Reset Test",
                "test2_feature": "Authentication",
                "correlation_score": 0.75,
                "co_failure_count": 5,
                "test1_failure_count": 10,
                "test2_failure_count": 8
            }
        }
    )

class PerformanceTestData(BaseModel):
    """Performance data for a specific test."""
    name: str
    feature: str
    avg_duration: float = 0.0
    min_duration: float = 0.0
    max_duration: float = 0.0
    trend_percentage: float = 0.0  # Positive means getting slower, negative means getting faster
    run_count: int = 0
    history: List[Dict[str, Any]] = Field(default_factory=list)

    model_config = ConfigDict(
        json_schema_extra = {
            "example": {
                "name": "User Login Test",
                "feature": "Authentication",
                "avg_duration": 250.5,
                "min_duration": 200.0,
                "max_duration": 300.0,
                "trend_percentage": 5.5,
                "run_count": 50,
                "history": [
                    {
                        "run_id": "run-001",
                        "duration": 245.3,
                        "timestamp": "2023-06-15T10:30:00Z"  # Note the Z for UTC
                    }
                ]
            }
        }
    )


class PerformanceMetrics(BaseModel):
    """Performance metrics for tests."""
    tests: List[PerformanceTestData]
    overall_avg_duration: float = 0.0
    days_analyzed: int
    environment: Optional[str] = None
    feature: Optional[str] = None

    model_config = ConfigDict(
        json_schema_extra = {
            "example": {
                "tests": [
                    {
                        "name": "User Login Test",
                        "feature": "Authentication",
                        "avg_duration": 250.5,
                        "min_duration": 200.0,
                        "max_duration": 300.0,
                        "trend_percentage": 5.5,
                        "run_count": 50
                    }
                ],
                "overall_avg_duration": 275.0,
                "days_analyzed": 30,
                "environment": "staging",
                "feature": "Authentication"
            }
        }
    )

class AnalyticsResponse(BaseModel):
    """Comprehensive analytics summary response."""
    trends: TrendAnalysis
    flaky_tests: List[TestFlakiness]
    performance: PerformanceMetrics
    correlations: List[FailureCorrelation]
    days_analyzed: int
    environment: Optional[str] = None
    timestamp: str = Field(default_factory=utcnow_iso)

    model_config = ConfigDict(
        json_schema_extra = {
            "example": {
                "trends": {
                    "start_date": "2023-01-01T00:00:00Z",  # Note the Z for UTC
                    "end_date": "2023-06-30T23:59:59Z",    # Note the Z for UTC
                    "pass_rate_trend": {
                        "January": 0.85,
                        "February": 0.90,
                        "March": 0.92
                    }
                },
                "flaky_tests": [
                    {
                        "id": "test-123",
                        "name": "User Login Test",
                        "feature": "Authentication",
                        "flakiness_score": 0.3,
                        "total_runs": 100,
                        "pass_count": 85,
                        "fail_count": 15
                    }
                ],
                "performance": {
                    "tests": [
                        {
                            "name": "User Login Test",
                            "feature": "Authentication",
                            "avg_duration": 250.5
                        }
                    ],
                    "overall_avg_duration": 275.0,
                    "days_analyzed": 30,
                    "environment": "staging"
                },
                "correlations": [
                    {
                        "id": "correlation-123",
                        "test1_name": "User Login Test",
                        "test1_feature": "Authentication",
                        "test2_name": "Password Reset Test",
                        "test2_feature": "Authentication",
                        "correlation_score": 0.75
                    }
                ],
                "days_analyzed": 30,
                "environment": "staging",
                "timestamp": "2023-07-01T00:00:00Z"  # Note the Z for UTC
            }
        }
    )

class ReportTemplate(BaseModel):
    """Pydantic model for report templates."""
    id: Optional[int] = None
    name: str
    description: Optional[str] = None
    report_type: ReportType
    format: ReportFormat
    template_data: Dict[str, Any]
    created_by: Optional[str] = None
    created_at: Optional[datetime] = None  # Will be timezone-aware
    updated_at: Optional[datetime] = None  # Will be timezone-aware

    model_config = ConfigDict(
        json_schema_extra = {
            "example": {
                "id": 1,
                "name": "Monthly Test Summary",
                "description": "Comprehensive monthly test report",
                "report_type": "TEST_SUMMARY",
                "format": "PDF",
                "template_data": {
                    "sections": ["overview", "detailed_results"],
                    "include_charts": True
                },
                "created_by": "admin",
                "created_at": "2023-06-15T10:30:00Z",  # Note the Z for UTC
                "updated_at": "2023-06-15T10:30:00Z"   # Note the Z for UTC
            }
        }
    )

class ReportSchedule(BaseModel):
    """Pydantic model for report schedules."""
    id: Optional[int] = None
    template_id: int
    name: str
    description: Optional[str] = None
    cron_expression: str
    enabled: bool = True
    parameters: Optional[Dict[str, Any]] = None
    recipients: Optional[List[str]] = None
    created_at: Optional[datetime] = None  # Will be timezone-aware
    updated_at: Optional[datetime] = None  # Will be timezone-aware
    last_run: Optional[datetime] = None    # Will be timezone-aware
    next_run: Optional[datetime] = None    # Will be timezone-aware

    model_config = ConfigDict(
        json_schema_extra = {
            "example": {
                "id": 1,
                "template_id": 123,
                "name": "Monthly Performance Report",
                "description": "Automated monthly performance test report",
                "cron_expression": "0 0 1 * *",
                "enabled": True,
                "parameters": {
                    "environment": "production",
                    "report_type": "performance"
                },
                "recipients": ["admin@company.com", "qa@company.com"],
                "created_at": "2023-06-15T10:30:00Z",   # Note the Z for UTC
                "updated_at": "2023-06-15T10:30:00Z",   # Note the Z for UTC
                "last_run": "2023-06-30T00:00:00Z",     # Note the Z for UTC
                "next_run": "2023-07-01T00:00:00Z"      # Note the Z for UTC
            }
        }
    )

class ResultsData(BaseModel):
    """Detailed results data structure."""
    total_scenarios: int = 0
    passed_scenarios: int = 0
    failed_scenarios: int = 0
    skipped_scenarios: int = 0
    pass_rate: float = 0.0
    last_updated: str
    features: List[Dict[str, Any]] = Field(default_factory=list)
    tags: Dict[str, Dict[str, Any]] = Field(default_factory=dict)

    model_config = ConfigDict(
        json_schema_extra = {
            "example": {
                "total_scenarios": 100,
                "passed_scenarios": 85,
                "failed_scenarios": 10,
                "skipped_scenarios": 5,
                "pass_rate": 0.85,
                "last_updated": "2023-06-15T10:30:00Z",  # Note the Z for UTC
                "features": [
                    {
                        "name": "User Authentication",
                        "total_scenarios": 20,
                        "passed_scenarios": 18,
                        "failed_scenarios": 2
                    }
                ],
                "tags": {
                    "smoke": {
                        "total": 10,
                        "passed": 9,
                        "failed": 1
                    }
                }
            }
        }
    )


class ResultsResponse(BaseModel):
    """Response structure for test results."""
    status: str
    results: ResultsData

    model_config = ConfigDict(
        json_schema_extra = {
            "example": {
                "status": "success",
                "results": {
                    "total_scenarios": 100,
                    "passed_scenarios": 85,
                    "failed_scenarios": 10,
                    "skipped_scenarios": 5,
                    "pass_rate": 0.85,
                    "last_updated": "2023-06-15T10:30:00Z",  # Note the Z for UTC
                    "features": [
                        {
                            "name": "User Authentication",
                            "total_scenarios": 20,
                            "passed_scenarios": 18,
                            "failed_scenarios": 2
                        }
                    ],
                    "tags": {
                        "smoke": {
                            "total": 10,
                            "passed": 9,
                            "failed": 1
                        }
                    }
                }
            }
        }
    )

class ScenarioTag(BaseModel):
    """Model representing a tag for a scenario."""
    scenario_id: int
    tag: str

    model_config = ConfigDict(
        json_schema_extra = {
            "example": {
                "scenario_id": 123,
                "tag": "smoke"
            }
        }
    )

# Feature Models
class FeatureBase(BaseModel):
    """Base model for feature operations."""
    name: str
    description: Optional[str] = None
    file_path: Optional[str] = None
    priority: Optional[str] = None
    status: Optional[str] = None
    tags: Optional[List[str]] = None

    model_config = ConfigDict(
        json_schema_extra = {
            "example": {
                "name": "User Authentication",
                "description": "Feature handling user login and authentication",
                "file_path": "/features/authentication.feature",
                "priority": "high",
                "status": "active",
                "tags": ["authentication", "security"]
            }
        }
    )


class FeatureCreate(FeatureBase):
    """Model for creating a new feature."""
    project_id: int


class FeatureResponse(FeatureBase):
    """Response model for feature details."""
    id: int
    project_id: int
    created_at: datetime  # Will be timezone-aware
    updated_at: datetime  # Will be timezone-aware


# Test Run Models
class TestRun(BaseModel):
    """Base model for test run operations."""
    name: str
    description: Optional[str] = None
    status: TestStatus
    environment: Optional[str] = None
    branch: Optional[str] = None
    commit_hash: Optional[str] = None

    model_config = ConfigDict(
        json_schema_extra = {
            "example": {
                "name": "Nightly Regression",
                "description": "Automated nightly regression test run",
                "status": "COMPLETED",
                "environment": "staging",
                "branch": "main",
                "commit_hash": "abc123def456"
            }
        }
    )


class TestRunCreate(TestRun):
    """Model for creating a new test run."""
    project_id: int
    build_id: Optional[int] = None


class TestRunResponse(TestRun):
    """Response model for test run details."""
    id: int
    project_id: int
    build_id: Optional[int] = None
    start_time: datetime  # Will be timezone-aware
    end_time: Optional[datetime] = None  # Will be timezone-aware
    duration: Optional[float] = None
    total_tests: int = 0
    passed_tests: int = 0
    failed_tests: int = 0
    skipped_tests: int = 0
    error_tests: int = 0
    success_rate: Optional[float] = None
    created_at: datetime  # Will be timezone-aware
    updated_at: datetime  # Will be timezone-aware


# Scenario Models
class ScenarioBase(BaseModel):
    """Base model for scenario operations."""
    name: str
    description: Optional[str] = None
    status: TestStatus
    error_message: Optional[str] = None
    stack_trace: Optional[str] = None
    parameters: Optional[Dict[str, Any]] = None
    meta_data: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(
        json_schema_extra = {
            "example": {
                "name": "Successful User Login",
                "description": "Validate user can log in with valid credentials",
                "status": "PASSED",
                "error_message": None,
                "parameters": {
                    "username": "testuser",
                    "environment": "staging"
                }
            }
        }
    )


class ScenarioCreate(ScenarioBase):
    """Model for creating a new scenario."""
    test_run_id: int
    feature_id: Optional[int] = None
    tags: Optional[List[str]] = None
    start_time: Optional[datetime] = None  # Will be timezone-aware if provided
    end_time: Optional[datetime] = None    # Will be timezone-aware if provided
    duration: Optional[float] = None


class ScenarioResponse(ScenarioBase):
    """Response model for scenario details."""
    id: int
    test_run_id: int
    feature_id: Optional[int] = None
    start_time: Optional[datetime] = None  # Will be timezone-aware
    end_time: Optional[datetime] = None    # Will be timezone-aware
    duration: Optional[float] = None
    created_at: datetime  # Will be timezone-aware
    updated_at: datetime  # Will be timezone-aware
    tags: List[str] = []

    model_config = ConfigDict(
        json_schema_extra = {
            "example": {
                "id": 1,
                "test_run_id": 100,
                "feature_id": 50,
                "name": "User Login Scenario",
                "status": "PASSED",
                "start_time": "2023-06-15T10:25:00Z",  # Note the Z for UTC
                "end_time": "2023-06-15T10:30:00Z",    # Note the Z for UTC
                "duration": 300.5,
                "created_at": "2023-06-15T10:20:00Z",  # Note the Z for UTC
                "updated_at": "2023-06-15T10:30:00Z",  # Note the Z for UTC
                "tags": ["smoke", "login"]
            }
        }
    )

# Bulk Operation Schemas
class BulkCreateRequest(BaseModel):
    """Schema for bulk creation of entities."""
    items: List[Union[
        ProjectCreate,
        TestRunCreate,
        FeatureCreate,
        ScenarioCreate,
        StepCreate
    ]]

    model_config = ConfigDict(
        json_schema_extra = {
            "example": {
                "items": [
                    {
                        "name": "Test Project",
                        "repository_url": "https://github.com/example/repo"
                    }
                ]
            }
        }
    )