# app/models/api.py
from typing import List, Dict, Any, Optional, Union
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum


class ErrorResponse(BaseModel):
    """Standard error response."""
    detail: str
    status_code: int = 500


class SuccessResponse(BaseModel):
    """Standard success response."""
    status: str = "success"
    message: str
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())


class ReportResponse(BaseModel):
    """Response for report upload endpoint."""
    status: str
    message: str
    report_id: str
    timestamp: str


class SearchResultItem(BaseModel):
    """Single item in search results."""
    id: str
    score: float
    content: Dict[str, Any]


class SearchResponse(BaseModel):
    """Response for search endpoint."""
    query: str
    results: List[SearchResultItem] = Field(default_factory=list)
    total_hits: int = 0
    execution_time_ms: float = 0


class AnalysisResponse(BaseModel):
    """Response for analysis endpoint."""
    query: str
    timestamp: str
    recommendations: List[str] = Field(default_factory=list)
    related_items: List[Dict[str, Any]] = Field(default_factory=list)
    summary: str


class ReportSummaryResponse(BaseModel):
    """Response for report summary endpoint."""
    report_id: str
    summary: str
    timestamp: str


class TestCaseInsightsResponse(BaseModel):
    """Response for test case insights endpoint."""
    test_case_id: str
    test_case: Optional[Dict[str, Any]] = None
    analysis: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    recommendations: List[str] = Field(default_factory=list)
    timestamp: str


class BuildTrendAnalysisResponse(BaseModel):
    """Response for build trend analysis endpoint."""
    build_numbers: List[str]
    builds_analyzed: int
    trend_analysis: str
    timestamp: str


class AnswerResponse(BaseModel):
    """Response for answer generation endpoint."""
    query: str
    answer: str
    timestamp: str


class ProcessingStatusResponse(BaseModel):
    """Response for checking processing status."""
    task_id: str
    status: str  # "pending", "completed", "failed"
    progress: float = 0.0  # 0.0 to 1.0
    message: Optional[str] = None
    timestamp: str


class HealthCheckResponse(BaseModel):
    """Response for health check endpoint."""
    status: str  # "ok", "degraded", "unavailable"
    services: Dict[str, str]
    timestamp: str


# Missing models required by test_results.py
class TestResultsTag(BaseModel):
    """Tag for a test result."""
    name: str
    value: Optional[str] = None
    color: Optional[str] = None


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


class ScenarioResult(BaseModel):
    """Model representing a scenario result."""
    id: str
    name: str
    status: str
    duration: Optional[float] = None
    feature: str
    steps: List[StepResult] = Field(default_factory=list)
    error_message: Optional[str] = None
    tags: List[TestResultsTag] = Field(default_factory=list)


class FeatureResult(BaseModel):
    """Model representing a feature result."""
    id: str
    name: str
    description: Optional[str] = None
    scenarios: List[ScenarioResult] = Field(default_factory=list)
    tags: List[TestResultsTag] = Field(default_factory=list)
    status: str
    duration: Optional[float] = None
    pass_rate: Optional[float] = None


class TestResultsResponse(BaseModel):
    """Response for test results endpoint."""
    id: str
    name: str
    status: str
    timestamp: str
    duration: float
    environment: str
    features: List[FeatureResult] = Field(default_factory=list)
    tags: List[TestResultsTag] = Field(default_factory=list)
    statistics: Dict[str, Any] = Field(default_factory=dict)


class TestResultsListResponse(BaseModel):
    """Response for listing test results."""
    results: List[Dict[str, Any]] = Field(default_factory=list)
    total: int = 0
    page: int = 1
    page_size: int = 10


class TestCaseListResponse(BaseModel):
    """Response for listing test cases."""
    test_cases: List[ScenarioResult] = Field(default_factory=list)
    total: int = 0
    page: int = 1
    page_size: int = 10


class StatisticsResponse(BaseModel):
    """Response for statistics endpoint."""
    total_test_cases: int = 0
    status_counts: Dict[str, int] = Field(default_factory=dict)
    pass_rate: float = 0.0
    timestamp: str

class TestHistory(BaseModel):
    """Test history entry"""
    report_id: str
    status: str
    timestamp: str
    duration: float = 0.0

class TestFlakiness(BaseModel):
    """Flaky test information"""
    id: str
    name: str
    feature: str
    flakiness_score: float = Field(..., description="Score from 0.0 to 1.0, higher is more flaky")
    total_runs: int
    pass_count: int
    fail_count: int
    history: List[Dict[str, Any]] = []

class TrendPoint(BaseModel):
    """Data point for trend analysis"""
    timestamp: str
    report_id: str
    total_tests: int = 0
    passed_tests: int = 0
    failed_tests: int = 0
    pass_rate: float = 0.0
    avg_duration: float = 0.0

class TrendAnalysis(BaseModel):
    """Trend analysis results"""
    points: List[TrendPoint]
    days_analyzed: int
    environment: Optional[str] = None
    feature: Optional[str] = None

class FailureCorrelation(BaseModel):
    """Correlation between test failures"""
    id: str
    test1_name: str
    test1_feature: str
    test2_name: str
    test2_feature: str
    correlation_score: float = Field(..., description="Score from 0.0 to 1.0, higher means stronger correlation")
    co_failure_count: int = 0
    test1_failure_count: int = 0
    test2_failure_count: int = 0

class PerformanceTestData(BaseModel):
    """Performance data for a specific test"""
    name: str
    feature: str
    avg_duration: float = 0.0
    min_duration: float = 0.0
    max_duration: float = 0.0
    trend_percentage: float = 0.0  # Positive means getting slower, negative means getting faster
    run_count: int = 0
    history: List[Dict[str, Any]] = []

class PerformanceMetrics(BaseModel):
    """Performance metrics for tests"""
    tests: List[PerformanceTestData]
    overall_avg_duration: float = 0.0
    days_analyzed: int
    environment: Optional[str] = None
    feature: Optional[str] = None

class AnalyticsResponse(BaseModel):
    """Comprehensive analytics summary"""
    trends: TrendAnalysis
    flaky_tests: List[TestFlakiness]
    performance: PerformanceMetrics
    correlations: List[FailureCorrelation]
    days_analyzed: int
    environment: Optional[str] = None
    timestamp: str


# Enums
class ReportFormat(str, Enum):
    """Report output format"""
    HTML = "html"
    PDF = "pdf"
    CSV = "csv"

class ReportStatus(str, Enum):
    """Report generation status"""
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

class ReportType(str, Enum):
    """Report template type"""
    TEST_SUMMARY = "test_summary"
    FLAKY_TESTS = "flaky_tests"
    PERFORMANCE = "performance"
    COMPREHENSIVE = "comprehensive"
    CUSTOM = "custom"

class ReportFrequency(str, Enum):
    """Report schedule frequency"""
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"

# Parameter Schema
class ParameterSchema(BaseModel):
    """Definition of a report parameter"""
    name: str
    type: str
    default: Any = None
    description: Optional[str] = None

# Template
class ReportTemplate(BaseModel):
    """Report template definition"""
    id: Optional[str] = None
    name: str
    description: Optional[str] = None
    type: ReportType
    parameters: List[Dict[str, Any]] = []
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

# Schedule
class ReportSchedule(BaseModel):
    """Schedule for periodic report generation"""
    id: Optional[str] = None
    name: str
    template_id: str
    parameters: Dict[str, Any] = {}
    frequency: ReportFrequency
    next_run: Optional[str] = None
    created_at: Optional[str] = None

# Report
class Report(BaseModel):
    """Generated report"""
    id: str
    name: str
    template_id: str
    parameters: Dict[str, Any] = {}
    schedule_id: Optional[str] = None
    status: ReportStatus
    created_at: str
    completed_at: Optional[str] = None
    file_path: Optional[str] = None
    format: str
    error: Optional[str] = None

# Subscription
class ReportSubscription(BaseModel):
    """Subscription to report deliveries"""
    id: Optional[str] = None
    user_id: str
    template_id: Optional[str] = None
    schedule_id: Optional[str] = None
    delivery_method: str  # "email", "slack", etc.
    delivery_config: Dict[str, Any] = {}
    created_at: Optional[str] = None

# Request bodies
class CreateReportRequest(BaseModel):
    """Request to generate a report"""
    template_id: str
    parameters: Dict[str, Any] = {}

class CreateScheduleRequest(BaseModel):
    """Request to schedule a report"""
    name: str
    template_id: str
    parameters: Dict[str, Any] = {}
    frequency: ReportFrequency
    next_run: Optional[str] = None

class CreateSubscriptionRequest(BaseModel):
    """Request to subscribe to report deliveries"""
    user_id: str
    template_id: Optional[str] = None
    schedule_id: Optional[str] = None
    delivery_method: str
    delivery_config: Dict[str, Any] = {}


# Enums
class NotificationPriority(str, Enum):
    """Notification priority"""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

class NotificationStatus(str, Enum):
    """Notification status"""
    PENDING = "pending"
    SENDING = "sending"
    DELIVERED = "delivered"
    FAILED = "failed"

class NotificationChannel(str, Enum):
    """Notification delivery channel"""
    EMAIL = "email"
    IN_APP = "in_app"
    SLACK = "slack"
    TEAMS = "teams"
    WEBHOOK = "webhook"

# Models
class NotificationDelivery(BaseModel):
    """Notification delivery configuration"""
    channel: NotificationChannel
    recipient: str
    config: Dict[str, Any] = {}

class Notification(BaseModel):
    """Notification message"""
    id: str
    title: str
    content: str
    user_id: str
    priority: NotificationPriority = NotificationPriority.MEDIUM
    status: NotificationStatus
    created_at: str
    updated_at: str
    is_read: bool = False
    delivery: NotificationDelivery
    metadata: Dict[str, Any] = {}
    error: Optional[str] = None

class NotificationRule(BaseModel):
    """Rule for generating notifications from events"""
    id: Optional[str] = None
    name: str
    description: Optional[str] = None
    event_type: str
    conditions: List[Dict[str, Any]] = []
    priority: NotificationPriority = NotificationPriority.MEDIUM
    template: Dict[str, str]
    enabled: bool = True

class NotificationSubscription(BaseModel):
    """Subscription to notifications for a specific rule"""
    id: Optional[str] = None
    user_id: str
    rule_id: str
    channel: NotificationChannel = NotificationChannel.IN_APP
    config: Dict[str, Any] = {}
    created_at: Optional[str] = None

# Request and response models
class CreateNotificationRequest(BaseModel):
    """Request to create a notification"""
    title: str
    content: str
    user_id: str
    priority: NotificationPriority = NotificationPriority.MEDIUM
    channel: NotificationChannel = NotificationChannel.IN_APP
    metadata: Optional[Dict[str, Any]] = None

class ProcessEventRequest(BaseModel):
    """Request to process an event and generate notifications"""
    event_type: str
    event_data: Dict[str, Any]

class NotificationResponse(BaseModel):
    """Response containing a list of notifications"""
    notifications: List[Notification]
    total: int
    unread: int

class CreateRuleRequest(BaseModel):
    """Request to create a notification rule"""
    name: str
    description: Optional[str] = None
    event_type: str
    conditions: List[Dict[str, Any]] = []
    priority: NotificationPriority = NotificationPriority.MEDIUM
    template: Dict[str, str]
    enabled: bool = True

class CreateSubscriptionRequest(BaseModel):
    """Request to create a notification subscription"""
    user_id: str
    rule_id: str
    channel: NotificationChannel = NotificationChannel.IN_APP
    config: Dict[str, Any] = {}

class MarkAsReadRequest(BaseModel):
    """Request to mark notifications as read"""
    notification_ids: List[str] = []
    all: bool = False
