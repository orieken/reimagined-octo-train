# src/models/domain.py
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from enum import Enum
from datetime import datetime
import uuid


class TestStatus(str, Enum):
    """Enum for test execution status."""
    PASSED = "PASSED"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"
    PENDING = "PENDING"
    BROKEN = "BROKEN"
    UNDEFINED = "UNDEFINED"


class ChunkMetadata(BaseModel):
    """Metadata for a text chunk."""
    source: Optional[str] = None
    source_id: Optional[str] = None
    chunk_index: Optional[int] = None
    document_type: Optional[str] = None
    context: Dict[str, Any] = Field(default_factory=dict)


class TextChunk(BaseModel):
    """Model representing a chunk of text with metadata."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    text: str
    metadata: ChunkMetadata = Field(default_factory=ChunkMetadata)
    chunk_size: Optional[int] = None


class TextEmbedding(BaseModel):
    """Model representing a text embedding vector."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    vector: List[float]
    text_chunk_id: str
    model: Optional[str] = None


class BuildInfo(BaseModel):
    """Information about a build."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    build_number: str
    build_url: Optional[str] = None
    branch: Optional[str] = None
    commit: Optional[str] = None
    date: Optional[str] = None
    duration: Optional[int] = None
    status: Optional[str] = None
    environment: Optional[str] = None
    version: Optional[str] = None
    team: Optional[str] = None
    project: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class Step(BaseModel):
    """Model representing a test step in a Cucumber scenario."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    keyword: str  # Given, When, Then, And, But
    name: str
    status: TestStatus
    error_message: Optional[str] = None
    duration: Optional[float] = None  # in milliseconds
    screenshot: Optional[str] = None  # path or URL to a screenshot if available
    logs: Optional[List[str]] = None  # relevant log entries

    class Config:
        use_enum_values = True


class Scenario(BaseModel):
    """Model representing a test case (Cucumber Scenario)."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: Optional[str] = None
    status: TestStatus
    tags: List[str] = Field(default_factory=list)
    feature: str  # The feature this test case belongs to
    duration: Optional[float] = None  # in milliseconds
    steps: List[Step] = Field(default_factory=list)
    error_message: Optional[str] = None
    retries: int = 0  # Number of retries if the test failed

    class Config:
        use_enum_values = True


class TestRun(BaseModel):
    """Model representing a test execution report."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    status: str  # Overall status (e.g., "PASSED", "FAILED")
    timestamp: str
    duration: float  # in milliseconds
    environment: str  # e.g., "production", "staging", "dev"
    tags: List[str] = Field(default_factory=list)
    scenarios: List[Scenario] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)  # Additional metadata

    def get_statistics(self) -> Dict[str, Any]:
        """Calculate statistics for the report."""
        total_tests = len(self.scenarios)

        # Initialize counters for each status
        status_counts = {status.value: 0 for status in TestStatus}

        # Count tests by status
        for test in self.scenarios:
            status_counts[test.status] = status_counts.get(test.status, 0) + 1

        # Calculate pass rate
        pass_rate = (status_counts.get(TestStatus.PASSED.value, 0) / total_tests * 100) if total_tests > 0 else 0

        # Calculate average duration
        total_duration = sum(tc.duration or 0 for tc in self.scenarios)
        avg_duration = total_duration / total_tests if total_tests > 0 else 0

        return {
            "total_tests": total_tests,
            "status_counts": status_counts,
            "pass_rate": pass_rate,
            "total_duration": total_duration,
            "average_duration": avg_duration
        }

    def get_failing_tests(self) -> List[Scenario]:
        """Return a list of failing test cases."""
        return [tc for tc in self.scenarios if tc.status == TestStatus.FAILED.value]

    def get_flaky_tests(self) -> List[Scenario]:
        """Return a list of potentially flaky test cases (tests with retries)."""
        return [tc for tc in self.scenarios if tc.retries > 0]


class Feature(BaseModel):
    """Model representing a Cucumber feature."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    scenarios: List[Scenario] = Field(default_factory=list)


# Aliases for backward compatibility
TestCase = Scenario
TestStep = Step
Report = TestRun


class QueryResult(BaseModel):
    """Result of a query against the vector database."""
    id: str
    score: float
    type: str  # report, test_case, test_step, feature, build_info
    content: Dict[str, Any]


class AnalysisRequest(BaseModel):
    """Model for requesting an analysis of a test report or test case."""
    report_id: Optional[str] = None
    test_case_id: Optional[str] = None
    query: str
    max_results: int = 10


class AnalysisResult(BaseModel):
    """Model for the result of an analysis."""
    query: str
    timestamp: datetime = Field(default_factory=datetime.now)
    recommendations: List[str] = Field(default_factory=list)
    related_items: List[Dict[str, Any]] = Field(default_factory=list)
    summary: str


class SearchQuery(BaseModel):
    """Model for a search query."""
    query: str
    filters: Dict[str, Any] = Field(default_factory=dict)
    limit: int = 10


class SearchResults(BaseModel):
    """Model for search results."""
    query: str
    results: List[Dict[str, Any]] = Field(default_factory=list)
    total_hits: int = 0
    execution_time_ms: float = 0


# Make sure the forward reference is resolved
Feature.update_forward_refs()
