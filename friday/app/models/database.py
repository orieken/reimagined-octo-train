"""
SQLAlchemy models for Friday Service
"""
from datetime import datetime
import enum
from typing import List, Optional
from sqlalchemy import (
    Column, Integer, String, ForeignKey, DateTime,
    Float, Enum, JSON, Boolean, Text, Table
)
from sqlalchemy.dialects.postgresql import JSONB, ARRAY, UUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
import uuid

Base = declarative_base()

# Many-to-many relationship between TestRun and Tags
test_run_tags = Table(
    "test_run_tags",
    Base.metadata,
    Column("test_run_id", Integer, ForeignKey("test_runs.id")),
    Column("tag_id", Integer, ForeignKey("test_results_tags.id"))
)


# Enum Tables/Types
class TestStatus(str, enum.Enum):
    PASSED = "PASSED"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    ERROR = "ERROR"


class ReportFormat(str, enum.Enum):
    HTML = "HTML"
    PDF = "PDF"
    CSV = "CSV"
    JSON = "JSON"
    XML = "XML"


class ReportStatus(str, enum.Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class ReportType(str, enum.Enum):
    TEST_SUMMARY = "TEST_SUMMARY"
    BUILD_HEALTH = "BUILD_HEALTH"
    FEATURE_COVERAGE = "FEATURE_COVERAGE"
    TREND_ANALYSIS = "TREND_ANALYSIS"
    CUSTOM = "CUSTOM"


# Core Domain Models
class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False, unique=True)
    description = Column(Text, nullable=True)
    repository_url = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    active = Column(Boolean, default=True, nullable=False)
    meta_data = Column(JSONB, nullable=True)

    # Relationships
    test_runs = relationship("TestRun", back_populates="project")
    features = relationship("Feature", back_populates="project")
    build_infos = relationship("BuildInfo", back_populates="project")
    health_metrics = relationship("HealthMetric", back_populates="project")
    test_reports = relationship("TestReport", back_populates="project")


class TestRun(Base):
    __tablename__ = "test_runs"

    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    build_id = Column(Integer, ForeignKey("build_infos.id"), nullable=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(Enum(TestStatus), nullable=False, default=TestStatus.RUNNING)
    start_time = Column(DateTime, default=datetime.utcnow, nullable=False)
    end_time = Column(DateTime, nullable=True)
    duration = Column(Float, nullable=True)  # in seconds
    total_tests = Column(Integer, default=0, nullable=False)
    passed_tests = Column(Integer, default=0, nullable=False)
    failed_tests = Column(Integer, default=0, nullable=False)
    skipped_tests = Column(Integer, default=0, nullable=False)
    error_tests = Column(Integer, default=0, nullable=False)
    success_rate = Column(Float, nullable=True)  # Percentage
    environment = Column(String(50), nullable=True)
    branch = Column(String(100), nullable=True)
    commit_hash = Column(String(40), nullable=True)
    meta_data = Column(JSONB, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    project = relationship("Project", back_populates="test_runs")
    build = relationship("BuildInfo", back_populates="test_runs")
    scenarios = relationship("Scenario", back_populates="test_run")
    tags = relationship("TestResultsTag", secondary=test_run_tags, back_populates="test_runs")


class Scenario(Base):
    __tablename__ = "scenarios"

    id = Column(Integer, primary_key=True)
    test_run_id = Column(Integer, ForeignKey("test_runs.id"), nullable=False)
    feature_id = Column(Integer, ForeignKey("features.id"), nullable=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(Enum(TestStatus), nullable=False)
    start_time = Column(DateTime, nullable=True)
    end_time = Column(DateTime, nullable=True)
    duration = Column(Float, nullable=True)  # in seconds
    error_message = Column(Text, nullable=True)
    stack_trace = Column(Text, nullable=True)
    parameters = Column(JSONB, nullable=True)
    meta_data = Column(JSONB, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    test_run = relationship("TestRun", back_populates="scenarios")
    feature = relationship("Feature", back_populates="scenarios")
    steps = relationship("Step", back_populates="scenario")


class Step(Base):
    __tablename__ = "steps"

    id = Column(Integer, primary_key=True)
    scenario_id = Column(Integer, ForeignKey("scenarios.id"), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(Enum(TestStatus), nullable=False)
    start_time = Column(DateTime, nullable=True)
    end_time = Column(DateTime, nullable=True)
    duration = Column(Float, nullable=True)  # in seconds
    error_message = Column(Text, nullable=True)
    stack_trace = Column(Text, nullable=True)
    screenshot_url = Column(String(255), nullable=True)
    log_output = Column(Text, nullable=True)
    order = Column(Integer, nullable=False)  # To maintain step sequence
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    scenario = relationship("Scenario", back_populates="steps")


class Feature(Base):
    __tablename__ = "features"

    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    file_path = Column(String(255), nullable=True)
    tags = Column(ARRAY(String), nullable=True)
    priority = Column(String(50), nullable=True)
    status = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    project = relationship("Project", back_populates="features")
    scenarios = relationship("Scenario", back_populates="feature")


class BuildInfo(Base):
    __tablename__ = "build_infos"

    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    build_number = Column(String(50), nullable=False)
    name = Column(String(255), nullable=True)
    status = Column(String(50), nullable=False)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=True)
    duration = Column(Float, nullable=True)  # in seconds
    branch = Column(String(100), nullable=True)
    commit_hash = Column(String(40), nullable=True)
    commit_message = Column(Text, nullable=True)
    author = Column(String(100), nullable=True)
    ci_url = Column(String(255), nullable=True)
    artifacts_url = Column(String(255), nullable=True)
    environment = Column(String(50), nullable=True)
    meta_data = Column(JSONB, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    project = relationship("Project", back_populates="build_infos")
    test_runs = relationship("TestRun", back_populates="build")
    metrics = relationship("BuildMetric", back_populates="build")
    health_metrics = relationship("HealthMetric", back_populates="build")


class TextChunk(Base):
    __tablename__ = "text_chunks"

    id = Column(Integer, primary_key=True)
    text = Column(Text, nullable=False)
    document_id = Column(String(255), nullable=False)
    document_type = Column(String(50), nullable=False)
    chunk_index = Column(Integer, nullable=False)
    meta_data = Column(JSONB, nullable=True)
    # Replace vector embedding with a reference ID to Quadrant
    quadrant_vector_id = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class HealthMetric(Base):
    __tablename__ = "health_metrics"

    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    build_id = Column(Integer, ForeignKey("build_infos.id"), nullable=True)
    metric_name = Column(String(100), nullable=False)
    metric_value = Column(Float, nullable=False)
    threshold = Column(Float, nullable=True)
    status = Column(String(50), nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    meta_data = Column(JSONB, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    project = relationship("Project", back_populates="health_metrics")
    build = relationship("BuildInfo", back_populates="health_metrics")


# Supporting Models
class BuildMetric(Base):
    __tablename__ = "build_metrics"

    id = Column(Integer, primary_key=True)
    build_id = Column(Integer, ForeignKey("build_infos.id"), nullable=False)
    metric_name = Column(String(100), nullable=False)
    metric_value = Column(Float, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    meta_data = Column(JSONB, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    build = relationship("BuildInfo", back_populates="metrics")


class ReportTemplate(Base):
    __tablename__ = "report_templates"

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    report_type = Column(Enum(ReportType), nullable=False)
    format = Column(Enum(ReportFormat), nullable=False)
    template_data = Column(JSONB, nullable=False)  # Template configuration
    created_by = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    reports = relationship("Report", back_populates="template")
    schedules = relationship("ReportSchedule", back_populates="template")


class ReportSchedule(Base):
    __tablename__ = "report_schedules"

    id = Column(Integer, primary_key=True)
    template_id = Column(Integer, ForeignKey("report_templates.id"), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    cron_expression = Column(String(100), nullable=False)
    enabled = Column(Boolean, default=True, nullable=False)
    parameters = Column(JSONB, nullable=True)
    recipients = Column(ARRAY(String), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    last_run = Column(DateTime, nullable=True)
    next_run = Column(DateTime, nullable=True)

    # Relationships
    template = relationship("ReportTemplate", back_populates="schedules")


class Report(Base):
    __tablename__ = "reports"

    id = Column(Integer, primary_key=True)
    template_id = Column(Integer, ForeignKey("report_templates.id"), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(Enum(ReportStatus), nullable=False, default=ReportStatus.PENDING)
    format = Column(Enum(ReportFormat), nullable=False)
    generated_at = Column(DateTime, nullable=True)
    file_path = Column(String(255), nullable=True)
    file_size = Column(Integer, nullable=True)  # in bytes
    parameters = Column(JSONB, nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    template = relationship("ReportTemplate", back_populates="reports")


class SearchQuery(Base):
    __tablename__ = "search_queries"

    id = Column(Integer, primary_key=True)
    query_text = Column(String(255), nullable=False)
    filters = Column(JSONB, nullable=True)
    result_count = Column(Integer, nullable=True)
    user_id = Column(String(100), nullable=True)
    session_id = Column(String(100), nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    duration = Column(Float, nullable=True)  # in milliseconds
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class AnalysisRequest(Base):
    __tablename__ = "analysis_requests"

    id = Column(Integer, primary_key=True)
    request_type = Column(String(100), nullable=False)
    parameters = Column(JSONB, nullable=False)
    status = Column(String(50), default="PENDING", nullable=False)
    user_id = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    results = relationship("AnalysisResult", back_populates="request")


class AnalysisResult(Base):
    __tablename__ = "analysis_results"

    id = Column(Integer, primary_key=True)
    request_id = Column(Integer, ForeignKey("analysis_requests.id"), nullable=False)
    result_data = Column(JSONB, nullable=False)
    summary = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    request = relationship("AnalysisRequest", back_populates="results")


class TestResultsTag(Base):
    __tablename__ = "test_results_tags"

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False, unique=True)
    description = Column(Text, nullable=True)
    color = Column(String(7), nullable=True)  # Hex color code
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    test_runs = relationship("TestRun", secondary=test_run_tags, back_populates="tags")



# Add this class if TestReport is expected
class TestReport(Base):
    """
    Placeholder for existing TestReport model.
    This model serves as a base for the TestRun model.
    """
    __tablename__ = "test_reports"

    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    execution_date = Column(DateTime, nullable=True)
    status = Column(String(50), nullable=True)
    meta_data = Column(JSONB,
                       nullable=True)  # Note: using meta_data instead of metadata to avoid SQLAlchemy name conflicts
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    project = relationship("Project", back_populates="test_reports")
    test_cases = relationship("TestCase", back_populates="test_report")


class TestCase(Base):
    """
    Placeholder for existing TestCase model.
    This model serves as a base for the Scenario model.
    """
    __tablename__ = "test_cases"

    id = Column(Integer, primary_key=True)
    test_report_id = Column(Integer, ForeignKey("test_reports.id"), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String(50), nullable=True)
    execution_time = Column(DateTime, nullable=True)
    duration = Column(Integer, nullable=True)  # in milliseconds
    is_automated = Column(Boolean, default=True, nullable=False)
    meta_data = Column(JSONB, nullable=True)  # Using meta_data instead of metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    test_report = relationship("TestReport", back_populates="test_cases")


class ScenarioTag(Base):
    """Scenario tags table."""
    __tablename__ = "scenario_tags"

    scenario_id = Column(UUID(as_uuid=True), ForeignKey("scenarios.id"), primary_key=True)
    tag = Column(String, primary_key=True)

    # Add relationship
    scenario = relationship("Scenario", back_populates="tags")


class Build(Base):
    """Build information table."""
    __tablename__ = "builds"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    build_number = Column(String, nullable=False)
    date = Column(DateTime, nullable=False)

    # Add relationships as needed
    scenarios = relationship("Scenario", back_populates="build")
