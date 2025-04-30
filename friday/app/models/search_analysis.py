from typing import Optional, List, Dict, Any
from uuid import UUID
from pydantic import BaseModel, Field
from datetime import datetime


class SearchQuery(BaseModel):
    id: UUID
    query_text: str
    filters: Optional[Dict[str, Any]] = None
    result_count: Optional[int] = 0
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    timestamp: datetime
    duration: Optional[float] = None  # in milliseconds
    created_at: datetime


class QueryResult(BaseModel):
    id: UUID
    query_id: UUID
    data: Dict[str, Any]
    relevance_score: Optional[float] = None
    created_at: datetime


class AnalysisRequest(BaseModel):
    id: UUID
    request_type: str
    parameters: Dict[str, Any]
    status: str = "PENDING"
    user_id: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None


class AnalysisResult(BaseModel):
    id: UUID
    request_id: UUID
    result_data: Dict[str, Any]
    summary: Optional[str] = None
    created_at: datetime


class TrendAnalysis(BaseModel):
    label: str
    date: datetime
    value: float
    metadata: Optional[Dict[str, Any]] = None


class FlakinessSummary(BaseModel):
    scenario_name: str
    total_runs: int
    flaky_runs: int
    flakiness_rate: float


class TestImpactAnalysis(BaseModel):
    impacted_features: List[str]
    test_cases: List[str]
    impact_score: float

class SearchQuery(BaseModel):
    id: Optional[UUID] = None
    query_text: str
    filters: Optional[Dict[str, Any]] = None
    result_count: Optional[int] = None
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    timestamp: Optional[datetime] = None
    duration: Optional[float] = None
    created_at: Optional[datetime] = None


class SearchQueryCreate(BaseModel):
    query_text: str
    filters: Optional[Dict[str, Any]] = None
    user_id: Optional[str] = None
    session_id: Optional[str] = None


class SearchQueryResponse(SearchQuery):
    pass


class QueryResult(BaseModel):
    id: Optional[UUID] = None
    query_id: UUID
    data: Dict[str, Any]
    relevance_score: Optional[float] = None
    created_at: Optional[datetime] = None


class QueryResultResponse(QueryResult):
    pass


class AnalysisRequest(BaseModel):
    id: Optional[UUID] = None
    request_type: str
    parameters: Dict[str, Any]
    status: Optional[str] = "PENDING"
    user_id: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class AnalysisRequestCreate(BaseModel):
    request_type: str
    parameters: Dict[str, Any]
    user_id: Optional[str] = None


class AnalysisRequestResponse(AnalysisRequest):
    pass


class AnalysisResult(BaseModel):
    id: Optional[UUID] = None
    request_id: UUID
    result_data: Dict[str, Any]
    summary: Optional[str] = None
    created_at: Optional[datetime] = None


class AnalysisResultResponse(AnalysisResult):
    pass


class TextChunk(BaseModel):
    id: Optional[UUID] = None
    text: str
    document_id: str
    document_type: str
    chunk_index: int
    meta_data: Optional[Dict[str, Any]] = None
    quadrant_vector_id: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class TextChunkCreate(BaseModel):
    text: str
    document_id: str
    document_type: str
    chunk_index: int
    meta_data: Optional[Dict[str, Any]] = None
    quadrant_vector_id: Optional[str] = None


class TextChunkResponse(TextChunk):
    pass
