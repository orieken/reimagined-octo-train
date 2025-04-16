# database.py
"""
SQLAlchemy ORM models for the test management system.

This module defines the database schema using SQLAlchemy ORM,
mapping Python classes to database tables with complex relationships
and advanced column types.
"""

from datetime import datetime, timezone
import enum
from sqlalchemy import (
    Column, Integer, String, ForeignKey, DateTime,
    Float, Enum, Boolean, Text, Table
)
from sqlalchemy.dialects.postgresql import JSONB, ARRAY, UUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()

# Helper function to always get timezone-aware UTC datetime
def utcnow():
    """Return current UTC datetime with timezone information."""
    return datetime.now(timezone.utc)

# Association Tables
test_run_tags = Table(
    "test_run_tags",
    Base.metadata,
    Column("test_run_id", Integer, ForeignKey("test_runs.id")),
    Column("tag_id", Integer, ForeignKey("test_results_tags.id"))
)

feature_tags = Table(
    "feature_tags",
    Base.metadata,
    Column("feature_id", Integer, ForeignKey("features.id")),
    Column("tag_id", Integer, ForeignKey("test_results_tags.id"))
)


# Enum Types
class TestStatus(enum.Enum):
    """Enumeration of possible test execution statuses."""
    PASSED = "PASSED"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    ERROR = "ERROR"


class ReportFormat(enum.Enum):
    """Supported report output formats."""
    HTML = "HTML"
    PDF = "PDF"
    CSV = "CSV"
    JSON = "JSON"
    XML = "XML"


class ReportStatus(enum.Enum):
    """Status of report generation."""
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class ReportType(enum.Enum):
    """Types of reports that can be generated."""
    TEST_SUMMARY = "TEST_SUMMARY"
    BUILD_HEALTH = "BUILD_HEALTH"
    FEATURE_COVERAGE = "FEATURE_COVERAGE"
    TREND_ANALYSIS = "TREND_ANALYSIS"
    CUSTOM = "CUSTOM"


class Project(Base):
    """Represents a project in the test management system."""
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False, unique=True)
    description = Column(Text, nullable=True)
    repository_url = Column(String(255), nullable=True)
    active = Column(Boolean, default=True, nullable=False)

    # Metadata
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)
    meta_data = Column(JSONB, nullable=True)

    # Relationships
    test_runs = relationship("TestRun", back_populates="project")
    features = relationship("Feature", back_populates="project")
    test_reports = relationship("TestReport", back_populates="project")
    build_infos = relationship("BuildInfo", back_populates="project")
    health_metrics = relationship("HealthMetric", back_populates="project")


class TestRun(Base):
    """Represents a single test run execution."""
    __tablename__ = "test_runs"

    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    build_id = Column(Integer, ForeignKey("build_infos.id"), nullable=True)

    # Run details
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(Enum(TestStatus), nullable=False, default=TestStatus.RUNNING)

    # Timing and performance
    start_time = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    end_time = Column(DateTime(timezone=True), nullable=True)
    duration = Column(Float, nullable=True)  # in seconds

    # Statistics
    total_tests = Column(Integer, default=0, nullable=False)
    passed_tests = Column(Integer, default=0, nullable=False)
    failed_tests = Column(Integer, default=0, nullable=False)
    skipped_tests = Column(Integer, default=0, nullable=False)
    error_tests = Column(Integer, default=0, nullable=False)
    success_rate = Column(Float, nullable=True)

    # Context
    environment = Column(String(50), nullable=True)
    branch = Column(String(100), nullable=True)
    commit_hash = Column(String(40), nullable=True)

    # Metadata
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)
    meta_data = Column(JSONB, nullable=True)

    # Relationships
    project = relationship("Project", back_populates="test_runs")
    build = relationship("BuildInfo", back_populates="test_runs")
    scenarios = relationship("Scenario", back_populates="test_run")
    tags = relationship("TestResultsTag", secondary=test_run_tags, back_populates="test_runs")


class Scenario(Base):
    """Represents a test scenario within a test run."""
    __tablename__ = "scenarios"

    id = Column(Integer, primary_key=True)
    test_run_id = Column(Integer, ForeignKey("test_runs.id"), nullable=False)
    feature_id = Column(Integer, ForeignKey("features.id"), nullable=True)

    # Scenario details
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(Enum(TestStatus), nullable=False)

    # Timing
    start_time = Column(DateTime(timezone=True), nullable=True)
    end_time = Column(DateTime(timezone=True), nullable=True)
    duration = Column(Float, nullable=True)  # in seconds

    # Error handling
    error_message = Column(Text, nullable=True)
    stack_trace = Column(Text, nullable=True)

    # Metadata
    parameters = Column(JSONB, nullable=True)
    meta_data = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

    # Relationships
    test_run = relationship("TestRun", back_populates="scenarios")
    feature = relationship("Feature", back_populates="scenarios")
    steps = relationship("Step", back_populates="scenario")
    tags = relationship("ScenarioTag", back_populates="scenario")


class ScenarioTag(Base):
    """Tags associated with a scenario."""
    __tablename__ = "scenario_tags"

    scenario_id = Column(Integer, ForeignKey("scenarios.id"), primary_key=True)
    tag = Column(String, primary_key=True)

    # Relationship
    scenario = relationship("Scenario", back_populates="tags")


class Step(Base):
    """Represents an individual step within a scenario."""
    __tablename__ = "steps"

    id = Column(Integer, primary_key=True)
    scenario_id = Column(Integer, ForeignKey("scenarios.id"), nullable=False)

    # Step details
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(Enum(TestStatus), nullable=False)

    # Timing
    start_time = Column(DateTime(timezone=True), nullable=True)
    end_time = Column(DateTime(timezone=True), nullable=True)
    duration = Column(Float, nullable=True)  # in seconds

    # Error handling
    error_message = Column(Text, nullable=True)
    stack_trace = Column(Text, nullable=True)

    # Additional information
    screenshot_url = Column(String(255), nullable=True)
    log_output = Column(Text, nullable=True)
    order = Column(Integer, nullable=False)

    # Metadata
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

    # Relationships
    scenario = relationship("Scenario", back_populates="steps")


class Feature(Base):
    """Represents a feature being tested."""
    __tablename__ = "features"

    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)

    # Feature details
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    file_path = Column(String(255), nullable=True)
    priority = Column(String(50), nullable=True)
    status = Column(String(50), nullable=True)

    # Metadata
    tags = Column(ARRAY(String), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

    # Relationships
    project = relationship("Project", back_populates="features")
    scenarios = relationship("Scenario", back_populates="feature")
    feature_tags = relationship("TestResultsTag", secondary=feature_tags, back_populates="features")


class BuildInfo(Base):
    """Represents information about a build."""
    __tablename__ = "build_infos"

    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)

    # Build details
    build_number = Column(String(50), nullable=False)
    name = Column(String(255), nullable=True)
    status = Column(String(50), nullable=False)

    # Timing
    start_time = Column(DateTime(timezone=True), nullable=False)
    end_time = Column(DateTime(timezone=True), nullable=True)
    duration = Column(Float, nullable=True)  # in seconds

    # SCM details
    branch = Column(String(100), nullable=True)
    commit_hash = Column(String(40), nullable=True)
    commit_message = Column(Text, nullable=True)
    author = Column(String(100), nullable=True)

    # URLs and environment
    ci_url = Column(String(255), nullable=True)
    artifacts_url = Column(String(255), nullable=True)
    environment = Column(String(50), nullable=True)

    # Metadata
    meta_data = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

    # Relationships
    project = relationship("Project", back_populates="build_infos")
    test_runs = relationship("TestRun", back_populates="build")
    metrics = relationship("BuildMetric", back_populates="build")
    health_metrics = relationship("HealthMetric", back_populates="build")


class TestReport(Base):
    """Represents a comprehensive test report."""
    __tablename__ = "test_reports"

    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)

    # Report details
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    execution_date = Column(DateTime(timezone=True), nullable=True)
    status = Column(String(50), nullable=True)

    # Metadata
    meta_data = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

    # Relationships
    project = relationship("Project", back_populates="test_reports")
    test_cases = relationship("TestCase", back_populates="test_report")


class TestCase(Base):
    """Represents a specific test case."""
    __tablename__ = "test_cases"

    id = Column(Integer, primary_key=True)
    test_report_id = Column(Integer, ForeignKey("test_reports.id"), nullable=False)

    # Test case details
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String(50), nullable=True)

    # Execution details
    execution_time = Column(DateTime(timezone=True), nullable=True)
    duration = Column(Integer, nullable=True)  # in milliseconds
    is_automated = Column(Boolean, default=True, nullable=False)

    # Metadata
    meta_data = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

    # Relationships
    test_report = relationship("TestReport", back_populates="test_cases")


class TestResultsTag(Base):
    """Represents tags used across different test entities."""
    __tablename__ = "test_results_tags"

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False, unique=True)
    description = Column(Text, nullable=True)
    color = Column(String(7), nullable=True)  # Hex color code

    # Metadata
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

    # Relationships
    test_runs = relationship("TestRun", secondary=test_run_tags, back_populates="tags")
    features = relationship("Feature", secondary=feature_tags, back_populates="feature_tags")


class HealthMetric(Base):
    """Represents health metrics for projects and builds."""
    __tablename__ = "health_metrics"

    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    build_id = Column(Integer, ForeignKey("build_infos.id"), nullable=True)

    # Metric details
    metric_name = Column(String(100), nullable=False)
    metric_value = Column(Float, nullable=False)
    threshold = Column(Float, nullable=True)
    status = Column(String(50), nullable=True)

    # Metadata
    timestamp = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    meta_data = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)

    # Relationships
    project = relationship("Project", back_populates="health_metrics")
    build = relationship("BuildInfo", back_populates="health_metrics")


class BuildMetric(Base):
    """Represents specific metrics for a build."""
    __tablename__ = "build_metrics"

    id = Column(Integer, primary_key=True)
    build_id = Column(Integer, ForeignKey("build_infos.id"), nullable=False)

    # Metric details
    metric_name = Column(String(100), nullable=False)
    metric_value = Column(Float, nullable=False)

    # Metadata
    timestamp = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    meta_data = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)

    # Relationships
    build = relationship("BuildInfo", back_populates="metrics")


class ReportTemplate(Base):
    """Defines templates for generating reports."""
    __tablename__ = "report_templates"

    id = Column(Integer, primary_key=True)

    # Template details
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    report_type = Column(Enum(ReportType), nullable=False)
    format = Column(Enum(ReportFormat), nullable=False)

    # Template configuration
    template_data = Column(JSONB, nullable=False)

    # Metadata
    created_by = Column(String(100), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

    # Relationships
    reports = relationship("Report", back_populates="template")
    schedules = relationship("ReportSchedule", back_populates="template")


class ReportSchedule(Base):
    """Manages scheduled report generation."""
    __tablename__ = "report_schedules"

    id = Column(Integer, primary_key=True)
    template_id = Column(Integer, ForeignKey("report_templates.id"), nullable=False)

    # Schedule details
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    cron_expression = Column(String(100), nullable=False)

    # Schedule status
    enabled = Column(Boolean, default=True, nullable=False)

    # Parameters and recipients
    parameters = Column(JSONB, nullable=True)
    recipients = Column(ARRAY(String), nullable=True)

    # Timing
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)
    last_run = Column(DateTime(timezone=True), nullable=True)
    next_run = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    template = relationship("ReportTemplate", back_populates="schedules")


class Report(Base):
    """Represents a generated report."""
    __tablename__ = "reports"

    id = Column(Integer, primary_key=True)
    template_id = Column(Integer, ForeignKey("report_templates.id"), nullable=False)

    # Report details
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)

    # Status and format
    status = Column(Enum(ReportStatus), nullable=False, default=ReportStatus.PENDING)
    format = Column(Enum(ReportFormat), nullable=False)

    # File details
    generated_at = Column(DateTime(timezone=True), nullable=True)
    file_path = Column(String(255), nullable=True)
    file_size = Column(Integer, nullable=True)  # in bytes

    # Additional metadata
    parameters = Column(JSONB, nullable=True)
    error_message = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

    # Relationships
    template = relationship("ReportTemplate", back_populates="reports")


class SearchQuery(Base):
    """Tracks search queries for analysis and optimization."""
    __tablename__ = "search_queries"

    id = Column(Integer, primary_key=True)

    # Query details
    query_text = Column(String(255), nullable=False)
    filters = Column(JSONB, nullable=True)

    # Query results
    result_count = Column(Integer, nullable=True)

    # User context
    user_id = Column(String(100), nullable=True)
    session_id = Column(String(100), nullable=True)

    # Performance tracking
    timestamp = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    duration = Column(Float, nullable=True)  # in milliseconds

    # Metadata
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)


class AnalysisRequest(Base):
    """Tracks requests for detailed test analysis."""
    __tablename__ = "analysis_requests"

    id = Column(Integer, primary_key=True)

    # Request details
    request_type = Column(String(100), nullable=False)
    parameters = Column(JSONB, nullable=False)

    # Status tracking
    status = Column(String(50), default="PENDING", nullable=False)
    user_id = Column(String(100), nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

    # Relationships
    results = relationship("AnalysisResult", back_populates="request")


class AnalysisResult(Base):
    """Stores results of detailed test analysis."""
    __tablename__ = "analysis_results"

    id = Column(Integer, primary_key=True)
    request_id = Column(Integer, ForeignKey("analysis_requests.id"), nullable=False)

    # Result details
    result_data = Column(JSONB, nullable=False)
    summary = Column(Text, nullable=True)

    # Timestamp
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)

    # Relationships
    request = relationship("AnalysisRequest", back_populates="results")


class TextChunk(Base):
    """Stores text chunks for advanced search and analysis."""
    __tablename__ = "text_chunks"

    id = Column(Integer, primary_key=True)

    # Chunk details
    text = Column(Text, nullable=False)
    document_id = Column(String(255), nullable=False)
    document_type = Column(String(50), nullable=False)
    chunk_index = Column(Integer, nullable=False)

    # Metadata and vector references
    meta_data = Column(JSONB, nullable=True)
    quadrant_vector_id = Column(String(255), nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)