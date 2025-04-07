"""
Import and export models to ensure they're registered with SQLAlchemy.
"""
# Import all model classes to register them with Base.metadata
from app.models.database import (
    Project,
    TestReport,
    TestCase,
    TestRun,
    Scenario,
    Step,
    Feature,
    BuildInfo,
    TextChunk,
    HealthMetric,
    BuildMetric,
    ReportTemplate,
    ReportSchedule,
    Report,
    SearchQuery,
    AnalysisRequest,
    AnalysisResult,
    TestResultsTag
)

# Export all model classes
__all__ = [
    'Project',
    'TestReport',
    'TestCase',
    'TestRun',
    'Scenario',
    'Step',
    'Feature',
    'BuildInfo',
    'TextChunk',
    'HealthMetric',
    'BuildMetric',
    'ReportTemplate',
    'ReportSchedule',
    'Report',
    'SearchQuery',
    'AnalysisRequest',
    'AnalysisResult',
    'TestResultsTag'
]