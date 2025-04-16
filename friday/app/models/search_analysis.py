# search_analysis.py
from typing import List, Dict, Any, Optional, Union
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime, timezone
import uuid


# Helper function to get timezone-aware UTC datetime
def utcnow():
    """Return current UTC datetime with timezone information."""
    return datetime.now(timezone.utc)


class QueryFilter(BaseModel):
    """Structured query filter for advanced searching."""
    field: str
    operator: str  # e.g., 'eq', 'gt', 'lt', 'contains', 'in'
    value: Any

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "field": "status",
                "operator": "eq",
                "value": "PASSED"
            }
        }
    )


class SearchQuery(BaseModel):
    """Comprehensive search query model."""
    query: Optional[str] = None
    filters: List[QueryFilter] = Field(default_factory=list)
    sort_by: Optional[str] = None
    sort_order: Optional[str] = Field(default=None, pattern='^(asc|desc)$')
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=10, ge=1, le=100)
    limit: int = Field(default=10, ge=1, le=100)

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "query": "login feature",
                "filters": [
                    {
                        "field": "status",
                        "operator": "eq",
                        "value": "PASSED"
                    }
                ],
                "sort_by": "duration",
                "sort_order": "desc",
                "limit": 20
            }
        }
    )


class QueryResult(BaseModel):
    """Structured query result with flexible content."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    type: str  # 'test_run', 'scenario', 'feature', 'step', 'build'
    score: float = Field(default=1.0, ge=0, le=1.0)
    content: Dict[str, Any]

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "result-123",
                "type": "scenario",
                "score": 0.95,
                "content": {
                    "name": "User Login Scenario",
                    "status": "PASSED",
                    "duration": 250.5
                }
            }
        }
    )


class SearchResults(BaseModel):
    """Comprehensive search results model."""
    query: str
    results: List[QueryResult] = Field(default_factory=list)
    total_hits: int = 0
    total_pages: int = 0
    current_page: int = 1
    page_size: int = 10
    execution_time_ms: float = 0

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "query": "login feature",
                "total_hits": 5,
                "total_pages": 1,
                "current_page": 1,
                "page_size": 10,
                "execution_time_ms": 45.5,
                "results": []
            }
        }
    )


class AnalysisRequest(BaseModel):
    """Detailed analysis request model."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    query_text: str
    context_type: Optional[str] = None  # 'test_run', 'feature', 'scenario'
    context_id: Optional[str] = None
    analysis_type: str = Field(default="comprehensive")
    max_results: int = Field(default=10, ge=1, le=100)
    additional_params: Dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "query_text": "Investigate login failures",
                "context_type": "feature",
                "context_id": "feature-123",
                "analysis_type": "root_cause",
                "max_results": 5
            }
        }
    )


class AnalysisResult(BaseModel):
    """Comprehensive analysis result model."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    request_id: str
    timestamp: datetime = Field(default_factory=utcnow)  # Updated to use timezone-aware utcnow

    # Analysis findings
    summary: str
    key_insights: List[str] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)

    # Related items
    related_items: List[QueryResult] = Field(default_factory=list)

    # Detailed metrics
    metrics: Dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "summary": "Identified recurring login failures",
                "key_insights": [
                    "80% of login failures occur on Chrome browser",
                    "Peak failure times are between 9-10 AM"
                ],
                "recommendations": [
                    "Investigate Chrome-specific authentication issues",
                    "Review server load during peak hours"
                ]
            }
        }
    )


class TrendAnalysis(BaseModel):
    """Trend analysis for test runs and features."""
    start_date: datetime  # Will be timezone-aware
    end_date: datetime    # Will be timezone-aware

    # Trend metrics
    pass_rate_trend: Dict[str, float] = Field(default_factory=dict)
    duration_trend: Dict[str, float] = Field(default_factory=dict)
    failure_trend: Dict[str, int] = Field(default_factory=dict)

    # Comparative analysis
    comparisons: Dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "start_date": "2023-01-01T00:00:00Z",  # Note the Z for UTC
                "end_date": "2023-06-30T23:59:59Z",    # Note the Z for UTC
                "pass_rate_trend": {
                    "January": 0.85,
                    "February": 0.90,
                    "March": 0.92
                },
                "failure_trend": {
                    "January": 10,
                    "February": 7,
                    "March": 5
                }
            }
        }
    )


class FlakinessSummary(BaseModel):
    """Summary of test flakiness."""
    test_id: str
    name: str
    total_runs: int
    total_failures: int
    flakiness_score: float = Field(ge=0, le=1)

    # Detailed flakiness information
    failure_patterns: List[Dict[str, Any]] = Field(default_factory=list)

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "test_id": "test-123",
                "name": "User Login Test",
                "total_runs": 100,
                "total_failures": 15,
                "flakiness_score": 0.15,
                "failure_patterns": [
                    {
                        "condition": "High server load",
                        "failure_rate": 0.1
                    }
                ]
            }
        }
    )


class TestImpactAnalysis(BaseModel):
    """Analysis of test impact on system quality."""
    feature_id: str
    feature_name: str

    # Impact metrics
    total_scenarios: int
    failed_scenarios: int
    impact_score: float = Field(ge=0, le=1)

    # Detailed breakdown
    failure_details: Dict[str, Any] = Field(default_factory=dict)
    recommended_actions: List[str] = Field(default_factory=list)

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "feature_id": "feature-123",
                "feature_name": "User Authentication",
                "total_scenarios": 20,
                "failed_scenarios": 3,
                "impact_score": 0.15,
                "recommended_actions": [
                    "Review authentication flow",
                    "Add more robust error handling"
                ]
            }
        }
    )