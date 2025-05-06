from datetime import datetime, timezone
import enum
from uuid import uuid4

from sqlalchemy import (
    Column, Integer, String, ForeignKey, DateTime,
    Float, Enum, Boolean, Text, Table, JSON, ARRAY
)
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

from app.services.datetime_service import now_utc as utcnow
from app.models.notification import NotificationStatus, NotificationPriority, NotificationChannel


Base = declarative_base()

# Association Tables
test_run_tags = Table(
    "test_run_tags",
    Base.metadata,
    Column("test_run_id", PG_UUID(as_uuid=True), ForeignKey("test_runs.id")),
    Column("tag_id", PG_UUID(as_uuid=True), ForeignKey("test_results_tags.id")),
)

feature_tags = Table(
    "feature_tags",
    Base.metadata,
    Column("feature_id", PG_UUID(as_uuid=True), ForeignKey("features.id")),
    Column("tag_id", PG_UUID(as_uuid=True), ForeignKey("test_results_tags.id"))
)

# Enum Types
class TestStatus(enum.Enum):
    PASSED = "PASSED"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    ERROR = "ERROR"
    UNKNOWN = "UNKNOWN"

class ReportFormat(enum.Enum):
    HTML = "HTML"
    PDF = "PDF"
    CSV = "CSV"
    JSON = "JSON"
    XML = "XML"

class ReportStatus(enum.Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

class ReportType(enum.Enum):
    TEST_SUMMARY = "TEST_SUMMARY"
    BUILD_HEALTH = "BUILD_HEALTH"
    FEATURE_COVERAGE = "FEATURE_COVERAGE"
    TREND_ANALYSIS = "TREND_ANALYSIS"
    CUSTOM = "CUSTOM"

class Project(Base):
    __tablename__ = "projects"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    name = Column(String(255), nullable=False, unique=True)
    description = Column(Text)
    repository_url = Column(String)
    active = Column(Boolean, default=True)
    meta_data = Column(JSON, default=dict)
    created_at = Column(DateTime(timezone=True), nullable=False)
    updated_at = Column(DateTime(timezone=True), nullable=False)

    features = relationship("Feature", back_populates="project")
    test_runs = relationship("TestRun", back_populates="project", cascade="all, delete-orphan")
    build_infos = relationship("BuildInfo", back_populates="project")
    health_metrics = relationship("HealthMetric", back_populates="project")

class TestRun(Base):
    __tablename__ = "test_runs"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    external_id = Column(String, nullable=True)
    name = Column(String, nullable=False)
    description = Column(Text)
    status = Column(Enum(TestStatus), nullable=False)
    environment = Column(String)
    branch = Column(String)
    commit_hash = Column(String)
    start_time = Column(DateTime(timezone=True))
    end_time = Column(DateTime(timezone=True))
    duration = Column(Float)
    total_tests = Column(Integer, nullable=True)
    passed_tests = Column(Integer, nullable=True)
    failed_tests = Column(Integer, nullable=True)
    skipped_tests = Column(Integer, nullable=True)
    error_tests = Column(Integer, nullable=True)
    success_rate = Column(Float)
    created_at = Column(DateTime(timezone=True), nullable=False)
    updated_at = Column(DateTime(timezone=True), nullable=False)
    runner = Column(String)
    meta_data = Column(JSON, default=dict)

    project_id = Column(PG_UUID(as_uuid=True), ForeignKey("projects.id"), nullable=True)
    project = relationship("Project", back_populates="test_runs")
    scenarios = relationship("Scenario", back_populates="test_run")

class Scenario(Base):
    __tablename__ = "scenarios"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    external_id = Column(String, nullable=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    status = Column(Enum(TestStatus), nullable=False)
    duration = Column(Float)
    is_flaky = Column(Boolean, default=False)
    embeddings = Column(JSON)
    created_at = Column(DateTime(timezone=True))
    updated_at = Column(DateTime(timezone=True))

    feature_id = Column(PG_UUID(as_uuid=True), ForeignKey("features.id"))
    test_run_id = Column(PG_UUID(as_uuid=True), ForeignKey("test_runs.id"))

    test_run = relationship("TestRun", back_populates="scenarios")
    steps = relationship("Step", back_populates="scenario")
    tags = relationship("ScenarioTag", back_populates="scenario", cascade="all, delete-orphan")


class ScenarioTag(Base):
    __tablename__ = "scenario_tags"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    scenario_id = Column(PG_UUID(as_uuid=True), ForeignKey("scenarios.id"), nullable=False)
    tag = Column(String, nullable=False)
    line = Column(Integer, nullable=True)  # Add line number column
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    # Add relationship if needed
    scenario = relationship("Scenario", back_populates="tags")

class Step(Base):
    __tablename__ = "steps"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    external_id = Column(String, nullable=True)
    name = Column(String(255), nullable=False)
    keyword = Column(String(64))
    status = Column(Enum(TestStatus), nullable=False)
    duration = Column(Float)
    error_message = Column(Text)
    stack_trace = Column(Text)
    embeddings = Column(JSON)
    order = Column(PG_UUID(as_uuid=True))
    start_time = Column(DateTime(timezone=True))
    end_time = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True))
    updated_at = Column(DateTime(timezone=True))

    scenario_id = Column(PG_UUID(as_uuid=True), ForeignKey("scenarios.id"))
    scenario = relationship("Scenario", back_populates="steps")

class Feature(Base):
    __tablename__ = "features"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    name = Column(String(255), nullable=False)
    external_id = Column(String, nullable=True)
    description = Column(Text)
    file_path = Column(String)
    tags = Column(JSON, default=list)
    created_at = Column(DateTime(timezone=True))
    updated_at = Column(DateTime(timezone=True))

    project_id = Column(PG_UUID(as_uuid=True), ForeignKey("projects.id"))
    project = relationship("Project", back_populates="features")

class BuildInfo(Base):
    __tablename__ = "build_infos"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    name = Column(String)
    build_number = Column(String)
    status = Column(String)
    environment = Column(String)
    branch = Column(String)
    commit_hash = Column(String)
    start_time = Column(DateTime(timezone=True))
    end_time = Column(DateTime(timezone=True))
    duration = Column(Float)
    meta_data = Column(JSON, default=dict)
    created_at = Column(DateTime(timezone=True))
    updated_at = Column(DateTime(timezone=True))

    project_id = Column(PG_UUID(as_uuid=True), ForeignKey("projects.id"))
    project = relationship("Project", back_populates="build_infos")
    health_metrics = relationship("HealthMetric", back_populates="build")
    metrics = relationship("BuildMetric", back_populates="build")

class TestResultsTag(Base):
    __tablename__ = "test_results_tags"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    name = Column(String(100), nullable=False, unique=True)
    description = Column(Text, nullable=True)
    color = Column(String(7), nullable=True)

    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

    test_runs = relationship("TestRun", secondary=test_run_tags, backref="tags")
    features = relationship("Feature", secondary=feature_tags, backref="feature_tags")

class HealthMetric(Base):
    __tablename__ = "health_metrics"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    project_id = Column(PG_UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False)
    build_id = Column(PG_UUID(as_uuid=True), ForeignKey("build_infos.id"), nullable=True)

    metric_name = Column(String(100), nullable=False)
    metric_value = Column(Float, nullable=False)
    threshold = Column(Float, nullable=True)
    status = Column(String(50), nullable=True)

    timestamp = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    meta_data = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)

    project = relationship("Project", back_populates="health_metrics")
    build = relationship("BuildInfo", back_populates="health_metrics")

class BuildMetric(Base):
    __tablename__ = "build_metrics"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    build_id = Column(PG_UUID(as_uuid=True), ForeignKey("build_infos.id"), nullable=False)

    metric_name = Column(String(100), nullable=False)
    metric_value = Column(Float, nullable=False)

    timestamp = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    meta_data = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)

    build = relationship("BuildInfo", back_populates="metrics")

class DBSearchQuery(Base):
    __tablename__ = "search_queries"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)

    query_text = Column(String(255), nullable=False)
    filters = Column(JSONB, nullable=True)
    result_count = Column(PG_UUID(as_uuid=True), nullable=True)

    user_id = Column(String(100), nullable=True)
    session_id = Column(String(100), nullable=True)

    timestamp = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    duration = Column(Float, nullable=True)

    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)


class DBAnalysisRequest(Base):
    __tablename__ = "analysis_requests"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)

    request_type = Column(String(100), nullable=False)
    parameters = Column(JSONB, nullable=False)
    status = Column(String(50), default="PENDING", nullable=False)
    user_id = Column(String(100), nullable=True)

    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

    results = relationship("DBAnalysisResult", back_populates="request", cascade="all, delete-orphan")


class DBAnalysisResult(Base):
    __tablename__ = "analysis_results"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    request_id = Column(PG_UUID(as_uuid=True), ForeignKey("analysis_requests.id"), nullable=False)

    result_data = Column(JSONB, nullable=False)
    summary = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)

    request = relationship("DBAnalysisRequest", back_populates="results")


class DBTextChunk(Base):
    __tablename__ = "text_chunks"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)

    text = Column(Text, nullable=False)
    document_id = Column(String(255), nullable=False)
    document_type = Column(String(50), nullable=False)
    chunk_index = Column(PG_UUID(as_uuid=True), nullable=False)

    meta_data = Column(JSONB, nullable=True)
    quadrant_vector_id = Column(String(255), nullable=True)

    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

class DBNotification(Base):
    __tablename__ = "notifications"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    external_id = Column(String, nullable=True)
    message = Column(String, nullable=False)
    subject = Column(String, nullable=True)
    status = Column(Enum(NotificationStatus), nullable=False, default=NotificationStatus.PENDING)
    priority = Column(Enum(NotificationPriority), nullable=False, default=NotificationPriority.MEDIUM)
    channel = Column(Enum(NotificationChannel), nullable=False)
    meta_data = Column(JSON, default=dict)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=True)
    sent_at = Column(DateTime(timezone=True), nullable=True)
