# __init__.py
"""
Import and export models for the application.

This module consolidates and exposes models from various categories:
- Base models (enums, foundational types)
- Domain models (core business logic)
- Schema models (API request/response structures)
- Database models (SQLAlchemy ORM models)
"""

# Base Models
from .base import (
    TestStatus,
    ReportFormat,
    ReportStatus,
    ReportType,
    BuildEnvironment,
    NotificationPriority,
    NotificationStatus,
    NotificationChannel,
    ChunkMetadata,
    TextChunk,
    TextEmbedding,
    Tag
)

# Domain Models
from .domain import (
    BuildInfo,
    Step,
    Scenario,
    TestRun,
    Feature,
    TestCase,
    TestStep,
    Report
)

# Schema Models
from .schemas import (
    ProjectBase,
    ProjectCreate,
    ProjectResponse,
    TestRunBase,
    TestRunCreate,
    TestRunResponse,
    FeatureBase,
    FeatureCreate,
    FeatureResponse,
    ScenarioBase,
    ScenarioCreate,
    ScenarioResponse,
    StepBase,
    StepCreate,
    StepResponse,
    ReportBase,
    ReportCreate,
    ReportResponse,
    TestStatistics,
    FeatureStatistics,
    BulkCreateRequest,
    BulkCreateResponse
)

# API Response Models
from .responses import (
    ErrorResponse,
    SuccessResponse,
    PaginatedResponse,
    SearchResponse,
    TestRunAnalyticsResponse,
    FeatureAnalyticsResponse,
    TestTrendResponse,
    NotificationResponse,
    ProcessingStatusResponse,
    HealthCheckResponse,
    BatchOperationResponse,
    ProcessReportResponse
)

# Search and Analysis Models
from .search_analysis import (
    SearchQuery,
    QueryResult,
    AnalysisRequest,
    AnalysisResult,
    TrendAnalysis,
    FlakinessSummary,
    TestImpactAnalysis
)

# Import SQLAlchemy database models
from .database import (
    Project as DBProject,
    TestReport as DBTestReport,
    TestCase as DBTestCase,
    TestRun as DBTestRun,
    Scenario as DBScenario,
    Step as DBStep,
    Feature as DBFeature,
    BuildInfo as DBBuildInfo,
    TextChunk as DBTextChunk,
    HealthMetric as DBHealthMetric,
    BuildMetric as DBBuildMetric,
    ReportTemplate as DBReportTemplate,
    ReportSchedule as DBReportSchedule,
    Report as DBReport,
    SearchQuery as DBSearchQuery,
    AnalysisRequest as DBAnalysisRequest,
    AnalysisResult as DBAnalysisResult,
    TestResultsTag as DBTestResultsTag
)

# Expose all models
__all__ = [
    # Base Models
    'TestStatus', 'ReportFormat', 'ReportStatus', 'ReportType',
    'BuildEnvironment', 'NotificationPriority', 'NotificationStatus',
    'NotificationChannel', 'ChunkMetadata', 'TextChunk', 'TextEmbedding', 'Tag',

    # Domain Models
    'BuildInfo', 'Step', 'Scenario', 'TestRun', 'Feature',
    'TestCase', 'TestStep', 'Report',

    # Schema Models
    'ProjectBase', 'ProjectCreate', 'ProjectResponse',
    'TestRunBase', 'TestRunCreate', 'TestRunResponse',
    'FeatureBase', 'FeatureCreate', 'FeatureResponse',
    'ScenarioBase', 'ScenarioCreate', 'ScenarioResponse',
    'StepBase', 'StepCreate', 'StepResponse',
    'ReportBase', 'ReportCreate', 'ReportResponse',
    'TestStatistics', 'FeatureStatistics',
    'BulkCreateRequest', 'BulkCreateResponse',

    # API Response Models
    'ErrorResponse', 'SuccessResponse', 'PaginatedResponse',
    'SearchResponse', 'TestRunAnalyticsResponse', 'FeatureAnalyticsResponse',
    'TestTrendResponse', 'NotificationResponse', 'ProcessingStatusResponse',
    'HealthCheckResponse', 'BatchOperationResponse', 'ProcessReportResponse'

    # Search and Analysis Models
    'SearchQuery', 'QueryResult', 'AnalysisRequest', 'AnalysisResult',
    'TrendAnalysis', 'FlakinessSummary', 'TestImpactAnalysis',

    # Database Models
    'DBProject', 'DBTestReport', 'DBTestCase', 'DBTestRun', 'DBScenario',
    'DBStep', 'DBFeature', 'DBBuildInfo', 'DBTextChunk', 'DBHealthMetric',
    'DBBuildMetric', 'DBReportTemplate', 'DBReportSchedule', 'DBReport',
    'DBSearchQuery', 'DBAnalysisRequest', 'DBAnalysisResult', 'DBTestResultsTag'
]
