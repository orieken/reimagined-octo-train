from sqlalchemy import (
    Column, String, Integer, Float, DateTime, ForeignKey, Text, JSON
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from uuid import uuid4
from app.services.datetime_service import now_utc as utcnow

Base = declarative_base()


class DBSearchQuery(Base):
    __tablename__ = "search_queries"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    query_text = Column(String(255), nullable=False)
    filters = Column(JSON, nullable=True)
    result_count = Column(PG_UUID(as_uuid=True), nullable=True)
    user_id = Column(String(100), nullable=True)
    session_id = Column(String(100), nullable=True)
    timestamp = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    duration = Column(Float, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)


class DBQueryResult(Base):
    __tablename__ = "query_results"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    query_id = Column(PG_UUID(as_uuid=True), ForeignKey("search_queries.id"), nullable=False)
    data = Column(JSON, nullable=False)
    relevance_score = Column(Float, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)

    query = relationship("DBSearchQuery", backref="results")


class DBAnalysisRequest(Base):
    __tablename__ = "analysis_requests"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    request_type = Column(String(100), nullable=False)
    parameters = Column(JSON, nullable=False)
    status = Column(String(50), default="PENDING", nullable=False)
    user_id = Column(String(100), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)

    results = relationship("DBAnalysisResult", back_populates="request")


class DBAnalysisResult(Base):
    __tablename__ = "analysis_results"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    request_id = Column(PG_UUID(as_uuid=True), ForeignKey("analysis_requests.id"), nullable=False)
    result_data = Column(JSON, nullable=False)
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
    meta_data = Column(JSON, nullable=True)
    quadrant_vector_id = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
