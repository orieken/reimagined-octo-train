"""
API request and response models
"""
from datetime import datetime
from typing import Dict, List, Optional, Union

from pydantic import BaseModel, Field

from app.models.domain import BuildInfo, Feature, QueryResult, TestStatus


class ErrorResponse(BaseModel):
    """API error response"""
    detail: str
    status_code: int
    path: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# Processor API models
class CucumberReportRequest(BaseModel):
    """Request model for processing Cucumber reports"""
    build_id: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    metadata: Dict[str, str] = Field(default_factory=dict)


class CucumberReportResponse(BaseModel):
    """Response model for processed Cucumber reports"""
    test_run_id: str
    processed_features: int
    processed_scenarios: int
    success: bool = True
    message: str = "Successfully processed cucumber reports"


class BuildInfoRequest(BaseModel):
    """Request model for processing build information"""
    build_id: str
    build_number: str
    branch: str
    commit_hash: str
    build_date: datetime
    build_url: Optional[str] = None
    metadata: Dict[str, str] = Field(default_factory=dict)


class BuildInfoResponse(BaseModel):
    """Response model for processed build information"""
    build_id: str
    success: bool = True
    message: str = "Successfully processed build information"


# Query API models
class QueryRequest(BaseModel):
    """Request model for natural language queries"""
    query: str
    test_run_id: Optional[str] = None
    build_id: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    max_results: Optional[int] = None
    similarity_threshold: Optional[float] = None


class QueryResponse(BaseModel):
    """Response model for natural language queries"""
    result: QueryResult


# Stats API models
class TestTag(BaseModel):
    """Test tag with count"""
    name: str
    count: int


class TestSummary(BaseModel):
    """Test summary statistics"""
    total: int
    passed: int
    failed: int
    skipped: int = 0
    pending: int = 0
    undefined: int = 0
    success_rate: float

    @classmethod
    def from_features(cls, features: List[Feature]) -> "TestSummary":
        """Create summary from features"""
        total = 0
        passed = 0
        failed = 0
        skipped = 0
        pending = 0
        undefined = 0

        for feature in features:
            for scenario in feature.scenarios:
                total += 1

                if scenario.status == TestStatus.PASSED:
                    passed += 1
                elif scenario.status == TestStatus.FAILED:
                    failed += 1
                elif scenario.status == TestStatus.SKIPPED:
                    skipped += 1
                elif scenario.status == TestStatus.PENDING:
                    pending += 1
                elif scenario.status == TestStatus.UNDEFINED:
                    undefined += 1

        success_rate = (passed / total) * 100 if total > 0 else 0

        return cls(
            total=total,
            passed=passed,
            failed=failed,
            skipped=skipped,
            pending=pending,
            undefined=undefined,
            success_rate=success_rate,
        )


class TestStatsRequest(BaseModel):
    """Request model for test statistics"""
    test_run_id: Optional[str] = None
    build_id: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    from_date: Optional[datetime] = None
    to_date: Optional[datetime] = None


class TestStatsResponse(BaseModel):
    """Response model for test statistics"""
    summary: TestSummary
    test_run_id: Optional[str] = None
    build_info: Optional[BuildInfo] = None
    timestamp: datetime
    tags: List[TestTag] = Field(default_factory=list)


class FeatureResult(BaseModel):
    """Feature result summary"""
    name: str
    total: int
    passed: int
    failed: int
    skipped: int = 0
    pass_rate: float


class TestResultsTag(BaseModel):
    """Tag with test counts and pass rate"""
    name: str
    count: int
    pass_rate: float


class TestResultsResponse(BaseModel):
    """Response model for detailed test results"""
    total_tests: int
    passed_tests: int
    failed_tests: int
    skipped_tests: int
    pass_rate: float
    feature_results: List[FeatureResult] = Field(default_factory=list)
    tags: List[TestResultsTag] = Field(default_factory=list)
    last_updated: datetime


class DailyTrend(BaseModel):
    """Daily test trend data"""
    date: str
    total_tests: int
    passed_tests: int
    failed_tests: int
    pass_rate: float


class BuildComparison(BaseModel):
    """Build comparison data"""
    build_number: str
    pass_rate: float


class FailingTest(BaseModel):
    """Top failing test information"""
    name: str
    failure_rate: float
    occurrences: int


class TrendsResponse(BaseModel):
    """Response model for test trends"""
    daily_trends: List[DailyTrend] = Field(default_factory=list)
    build_comparison: List[BuildComparison] = Field(default_factory=list)
    top_failing_tests: List[FailingTest] = Field(default_factory=list)


class FailureCategory(BaseModel):
    """Failure category with count and percentage"""
    name: str
    value: int
    percentage: float


class FailureDetailItem(BaseModel):
    """Detail item for a specific failure"""
    element: str
    occurrences: int
    scenarios: List[str] = Field(default_factory=list)


class FeatureFailure(BaseModel):
    """Feature with failure data"""
    feature: str
    failures: int
    tests: int
    failure_rate: float


class RecentFailure(BaseModel):
    """Information about a recent test failure"""
    id: str
    scenario: str
    error: str
    date: str
    build: str


class FailureAnalysisResponse(BaseModel):
    """Response model for failure analysis"""
    failure_categories: List[FailureCategory] = Field(default_factory=list)
    failure_details: Dict[str, List[FailureDetailItem]] = Field(default_factory=dict)
    failures_by_feature: List[FeatureFailure] = Field(default_factory=list)
    recent_failures: List[RecentFailure] = Field(default_factory=list)
