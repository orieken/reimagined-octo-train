# app/models/schemas.py
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum


class TestStatus(str, Enum):
    """Status of a test."""
    PASSED = "PASSED"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    ERROR = "ERROR"


class FeatureStats(BaseModel):
    """Statistics for a feature."""
    name: str
    passed_scenarios: int
    failed_scenarios: int
    skipped_scenarios: int


class TagStats(BaseModel):
    """Statistics for a tag."""
    count: int
    pass_rate: float
    passed: Optional[int] = 0
    failed: Optional[int] = 0
    skipped: Optional[int] = 0


class ResultsData(BaseModel):
    """Complete test results data structure."""
    total_scenarios: int
    passed_scenarios: int
    failed_scenarios: int
    skipped_scenarios: int
    pass_rate: float
    last_updated: str
    features: List[FeatureStats]
    tags: Dict[str, TagStats]


class ResultsResponse(BaseModel):
    """API response structure for test results."""
    status: str = "success"
    results: ResultsData