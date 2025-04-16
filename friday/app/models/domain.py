# domain.py
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
import uuid

from .base import (
    TestStatus,
    BuildEnvironment,
    Tag
)


class BuildInfo(BaseModel):
    """Comprehensive build information model."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    build_number: str
    project: Optional[str] = None
    repository: Optional[str] = None
    branch: Optional[str] = None
    commit: Optional[str] = None

    # Build metadata
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    duration: Optional[float] = None  # in seconds

    # Build context
    environment: Optional[BuildEnvironment] = None
    status: Optional[str] = None

    # Additional metadata
    ci_url: Optional[str] = None
    artifacts_url: Optional[str] = None
    version: Optional[str] = None

    # Extra context
    author: Optional[str] = None
    commit_message: Optional[str] = None

    # Flexible metadata
    extra_info: Dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "build_number": "1.2.3-RC1",
                "project": "test-automation",
                "branch": "main",
                "commit": "abc123def456",
                "environment": "staging",
                "status": "completed"
            }
        }
    )

    def is_successful(self) -> bool:
        """Determine if the build was successful."""
        return self.status in ['completed', 'success']

    def get_build_duration(self) -> Optional[float]:
        """Calculate build duration if start and end times are available."""
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return self.duration

class StepEmbedding(BaseModel):
    """Model representing an embedding attached to a test step."""
    data: str
    mime_type: str

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "data": "base64encodeddata",
                "mime_type": "image/png"
            }
        }
    )

class Step(BaseModel):
    """Model representing a test step."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    keyword: str
    name: str
    status: TestStatus
    error_message: Optional[str] = None
    stack_trace: Optional[str] = None
    duration: Optional[float] = None
    screenshot: Optional[str] = None
    logs: Optional[List[str]] = None
    embeddings: Optional[List[StepEmbedding]] = None  # Updated to use StepEmbedding type

    class Config:
        use_enum_values = True
        json_schema_extra = {
            "example": {
                "id": "step-123",
                "keyword": "When",
                "name": "User logs in",
                "status": "PASSED",
                "duration": 250.5,
                "embeddings": [
                    {
                        "data": "base64encodeddata",
                        "mime_type": "image/png"
                    }
                ]
            }
        }

    def is_failed(self) -> bool:
        """Check if the step failed."""
        return self.status in [TestStatus.FAILED, TestStatus.ERROR]

    def get_duration(self) -> Optional[float]:
        """Calculate step duration."""
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time).total_seconds() * 1000
        return self.duration


class Scenario(BaseModel):
    """Model representing a test scenario."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: Optional[str] = None
    status: TestStatus
    feature: str
    feature_file: Optional[str] = None  # Added feature_file
    tags: List[str] = Field(default_factory=list)
    duration: Optional[float] = None
    steps: List[Step] = Field(default_factory=list)
    error_message: Optional[str] = None
    retries: int = 0
    is_flaky: bool = False  # Added is_flaky
    embeddings: Optional[List[StepEmbedding]] = None  # Updated to use StepEmbedding type

    class Config:
        use_enum_values = True
        json_schema_extra = {
            "example": {
                "id": "scenario-123",
                "name": "User Login Scenario",
                "status": "PASSED",
                "feature": "Authentication",
                "feature_file": "/path/to/login.feature",
                "tags": ["smoke", "login"],
                "duration": 1500.5,
                "is_flaky": False,
                "embeddings": [
                    {
                        "data": "base64encodeddata",
                        "mime_type": "image/png"
                    }
                ]
            }
        }

    def is_failed(self) -> bool:
        """Check if the scenario failed."""
        return self.status in [TestStatus.FAILED, TestStatus.ERROR]

    def get_failed_steps(self) -> List[Step]:
        """Retrieve all failed steps in the scenario."""
        return [step for step in self.steps if step.status in [TestStatus.FAILED, TestStatus.ERROR]]

    def calculate_status(self) -> TestStatus:
        """Calculate overall scenario status based on steps."""
        if not self.steps:
            return self.status

        step_statuses = [step.status for step in self.steps]

        if any(status == TestStatus.FAILED for status in step_statuses):
            return TestStatus.FAILED
        if any(status == TestStatus.ERROR for status in step_statuses):
            return TestStatus.ERROR
        if all(status == TestStatus.PASSED for status in step_statuses):
            return TestStatus.PASSED

        return TestStatus.UNDEFINED

    def get_total_duration(self) -> Optional[float]:
        """Calculate total duration of steps."""
        step_durations = [step.duration or 0 for step in self.steps]
        return sum(step_durations) if step_durations else self.duration


class TestRun(BaseModel):
    """Comprehensive test run model."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))

    # Run identification
    name: str
    description: Optional[str] = None

    # Execution context
    timestamp: datetime = Field(default_factory=datetime.now)
    environment: str

    # Run details
    status: TestStatus
    duration: float  # Total run duration in milliseconds

    # Scenarios
    scenarios: List[Scenario] = Field(default_factory=list)

    # Metadata
    tags: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "Nightly Regression Test",
                "environment": "staging",
                "status": "COMPLETED",
                "scenarios": []
            }
        }
    )

    def get_statistics(self) -> Dict[str, Any]:
        """Generate comprehensive test run statistics."""
        total_scenarios = len(self.scenarios)

        # Count scenarios by status
        status_counts = {}
        for status in TestStatus:
            status_counts[status.value] = sum(
                1 for scenario in self.scenarios if scenario.status == status
            )

        # Calculate pass rate
        pass_rate = (
                    status_counts.get(TestStatus.PASSED.value, 0) / total_scenarios * 100) if total_scenarios > 0 else 0

        return {
            "total_scenarios": total_scenarios,
            "status_counts": status_counts,
            "pass_rate": round(pass_rate, 2),
            "total_duration": sum(scenario.duration or 0 for scenario in self.scenarios),
            "average_scenario_duration": sum(
                scenario.duration or 0 for scenario in self.scenarios) / total_scenarios if total_scenarios > 0 else 0
        }

    def get_failing_scenarios(self) -> List[Scenario]:
        """Retrieve scenarios that failed."""
        return [
            scenario for scenario in self.scenarios
            if scenario.status in [TestStatus.FAILED, TestStatus.ERROR]
        ]

    def get_flaky_scenarios(self) -> List[Scenario]:
        """Retrieve scenarios with retries."""
        return [scenario for scenario in self.scenarios if scenario.retries > 0]


class Feature(BaseModel):
    """Detailed feature model."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))

    # Feature identification
    name: str
    description: Optional[str] = None

    # Feature context
    file_path: Optional[str] = None
    priority: Optional[str] = None
    status: Optional[str] = None

    # Scenarios and relationships
    scenarios: List[Scenario] = Field(default_factory=list)

    # Metadata
    tags: List[str] = Field(default_factory=list)

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "User Authentication",
                "file_path": "features/auth.feature",
                "priority": "high",
                "scenarios": []
            }
        }
    )

    def get_feature_statistics(self) -> Dict[str, Any]:
        """Generate comprehensive feature statistics."""
        total_scenarios = len(self.scenarios)

        # Count scenarios by status
        status_counts = {}
        for status in TestStatus:
            status_counts[status.value] = sum(
                1 for scenario in self.scenarios if scenario.status == status
            )

        # Calculate pass rate
        pass_rate = (
                    status_counts.get(TestStatus.PASSED.value, 0) / total_scenarios * 100) if total_scenarios > 0 else 0

        return {
            "total_scenarios": total_scenarios,
            "status_counts": status_counts,
            "pass_rate": round(pass_rate, 2)
        }

    def get_scenarios_by_tag(self, tag: str) -> List[Scenario]:
        """Retrieve scenarios with a specific tag."""
        return [scenario for scenario in self.scenarios if tag in scenario.tags]


# Aliases for backward compatibility
TestCase = Scenario
TestStep = Step
Report = TestRun