from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, field_validator, root_validator
from datetime import datetime, timezone
from uuid import uuid4, UUID
from app.services import datetime_service as dt

from .base import (
    TestStatus, NotificationStatus, NotificationPriority, NotificationChannel,
)

def default_id() -> str:
    return str(uuid4())

def default_timestamp() -> datetime:
    return dt.now_utc()



class Step(BaseModel):
    id: str = Field(default_factory=default_id)
    external_id: Optional[str] = None
    name: str
    keyword: Optional[str] = None
    status: str
    duration: Optional[float] = 0.0
    error_message: Optional[str] = None
    stack_trace: Optional[str] = None
    embeddings: Optional[List[Dict[str, Any]]] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    metadata: Optional[Dict[str, Any]] = None
    created_at: Optional[datetime] = Field(default_factory=default_timestamp)
    updated_at: Optional[datetime] = Field(default_factory=default_timestamp)
    order: Optional[str] = None

    @root_validator(pre=True)
    def handle_external_id(cls, values):
        if "id" in values:
            values["external_id"] = values["id"]
            values["id"] = str(uuid4())
        return values

    def is_failed(self) -> bool:
        return self.status.upper() in [TestStatus.FAILED, TestStatus.ERROR]

    def get_duration(self) -> Optional[float]:
        if self.start_time and self.end_time:
            start = dt.ensure_utc_datetime(self.start_time)
            end = dt.ensure_utc_datetime(self.end_time)
            return dt.duration_in_milliseconds(start, end)
        return self.duration


class Scenario(BaseModel):
    id: str = Field(default_factory=default_id)
    external_id: Optional[str] = None
    name: str
    description: Optional[str] = ""
    status: str
    duration: Optional[float] = 0.0
    tags: Optional[List[str]] = []
    tag_metadata: Optional[Dict[str, Dict[str, Any]]] = Field(default_factory=dict)
    feature: Optional[str] = None
    feature_file: Optional[str] = None
    feature_id: Optional[str] = None
    test_run_id: Optional[str] = None
    steps: List[Step]
    embeddings: Optional[List[Dict[str, Any]]] = None
    is_flaky: Optional[bool] = False
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    metadata: Optional[Dict[str, Any]] = None
    created_at: Optional[datetime] = Field(default_factory=default_timestamp)
    updated_at: Optional[datetime] = Field(default_factory=default_timestamp)

    @root_validator(pre=True)
    def handle_external_id(cls, values):
        if "id" in values:
            values["external_id"] = values["id"]
            values["id"] = str(uuid4())
        return values

    def is_failed(self) -> bool:
        return self.status.upper() in [TestStatus.FAILED, TestStatus.ERROR]

    def get_failed_steps(self) -> List[Step]:
        return [step for step in self.steps if step.status.upper() in [TestStatus.FAILED, TestStatus.ERROR]]

    def calculate_status(self) -> str:
        if not self.steps:
            return self.status
        step_statuses = [step.status.upper() for step in self.steps]
        if any(status == TestStatus.FAILED for status in step_statuses):
            return TestStatus.FAILED
        if any(status == TestStatus.ERROR for status in step_statuses):
            return TestStatus.ERROR
        if all(status == TestStatus.PASSED for status in step_statuses):
            return TestStatus.PASSED
        return TestStatus.UNDEFINED

    def get_total_duration(self) -> Optional[float]:
        if self.start_time and self.end_time:
            start = dt.ensure_utc_datetime(self.start_time)
            end = dt.ensure_utc_datetime(self.end_time)
            return dt.duration_in_milliseconds(start, end)
        step_durations = [step.duration or 0 for step in self.steps]
        return sum(step_durations) if step_durations else self.duration

class Feature(BaseModel):
    id: str = Field(default_factory=default_id)
    external_id: Optional[str] = None
    name: str
    description: Optional[str] = ""
    uri: Optional[str] = None
    tags: Optional[List[str]] = []
    scenarios: List[Scenario]
    project_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    created_at: Optional[datetime] = Field(default_factory=default_timestamp)
    updated_at: Optional[datetime] = Field(default_factory=default_timestamp)

    @root_validator(pre=True)
    def handle_external_id(cls, values):
        if "id" in values:
            values["external_id"] = values["id"]
            values["id"] = str(uuid4())
        return values

    def get_feature_statistics(self) -> Dict[str, Any]:
        total_scenarios = len(self.scenarios)
        status_counts = {}
        for status in TestStatus:
            status_counts[status.value] = sum(
                1 for scenario in self.scenarios if scenario.status == status
            )
        pass_rate = (
            status_counts.get(TestStatus.PASSED.value, 0) / total_scenarios * 100
        ) if total_scenarios > 0 else 0
        return {
            "total_scenarios": total_scenarios,
            "status_counts": status_counts,
            "pass_rate": round(pass_rate, 2)
        }

    def get_scenarios_by_tag(self, tag: str) -> List[Scenario]:
        return [scenario for scenario in self.scenarios if tag in scenario.tags]


class TestRun(BaseModel):
    id: str = Field(default_factory=default_id)
    external_id: Optional[str] = None
    name: str
    status: Optional[str] = None
    environment: Optional[str] = "unknown"
    timestamp: datetime
    duration: Optional[float] = 0.0
    branch: Optional[str] = None
    commit_hash: Optional[str] = None
    scenarios: List[Scenario]
    runner: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    total_tests: int = 0
    passed_tests: int = 0
    failed_tests: int = 0
    skipped_tests: int = 0
    error_tests: int = 0
    success_rate: float = 0.0
    project_key: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    created_at: Optional[datetime] = Field(default_factory=default_timestamp)
    updated_at: Optional[datetime] = Field(default_factory=default_timestamp)

    @root_validator(pre=True)
    def handle_external_id(cls, values):
        if "id" in values:
            values["external_id"] = values["id"]
            values["id"] = str(uuid4())
        return values


class BuildInfo(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    external_id: Optional[str] = None
    name: str
    build_number: str
    status: str
    branch: Optional[str] = None
    commit_hash: Optional[str] = None
    environment: Optional[str] = None
    duration: Optional[float] = None
    date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    project_id: Optional[str] = None

    @field_validator("created_at", "updated_at", "date", "end_date", mode="before")
    def ensure_utc(cls, value):
        return dt.ensure_utc_datetime(value)

    @root_validator(pre=True)
    def handle_external_id(cls, values):
        if "id" in values:
            values["external_id"] = values["id"]
            values["id"] = str(uuid4())
        return values

    def is_successful(self) -> bool:
        return self.status in ["completed", "success", "PASSED"]

    def get_build_duration(self) -> Optional[float]:
        if self.date and self.end_date:
            start = dt.ensure_utc_datetime(self.date)
            end = dt.ensure_utc_datetime(self.end_date)
            return (end - start).total_seconds()
        return self.duration


class Project(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    external_id: Optional[str] = None
    name: str
    description: Optional[str] = None
    repository_url: Optional[str] = None
    active: bool = True
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @field_validator("created_at", "updated_at", mode="before")
    def ensure_utc(cls, value):
        return dt.ensure_utc_datetime(value)

class Notification(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    external_id: Optional[str] = None
    message: str
    subject: Optional[str] = None
    status: NotificationStatus = NotificationStatus.PENDING
    priority: NotificationPriority = NotificationPriority.MEDIUM
    channel: NotificationChannel
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=dt.now_utc)
    updated_at: Optional[datetime] = None
    sent_at: Optional[datetime] = None

    model_config = {
        "json_schema_extra": {
            "example": {
                "message": "Build failed for commit abc123 on staging.",
                "subject": "Build Alert",
                "status": "PENDING",
                "priority": "HIGH",
                "channel": "SLACK"
            }
        }
    }
# Aliases for clarity
TestCase = Scenario
TestStep = Step
Report = TestRun
