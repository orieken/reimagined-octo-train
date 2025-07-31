# Replace your app/api/routes/query.py with this version

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Dict, Any, Optional
import logging
from uuid import UUID

from app.config import settings
from app.services.orchestrator import ServiceOrchestrator
from app.services.simple_query_service import SimpleQueryService
from app.api.dependencies import get_orchestrator_service
from app.services import datetime_service as dt
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter(prefix=settings.API_PREFIX, tags=["query"])


# ========== REQUEST/RESPONSE MODELS ==========

class QueryRequest(BaseModel):
    query: str
    environment: Optional[str] = None
    days: Optional[int] = 7


class QuickQueryRequest(BaseModel):
    question: str
    environment: Optional[str] = None
    days: Optional[int] = 7


class QueryResponse(BaseModel):
    status: str = "success"
    answer: str
    confidence: float
    sources: Optional[list] = None
    related_queries: Optional[list] = None
    execution_time_ms: float = 0.0


# ========== DEPENDENCY INJECTION ==========

async def get_query_service(
        orchestrator: ServiceOrchestrator = Depends(get_orchestrator_service)
) -> SimpleQueryService:
    """Get the simple query service instance"""
    return SimpleQueryService(
        llm_service=orchestrator.llm,
        vector_db_service=orchestrator.vector_db,
        postgres_service=orchestrator.pg_service
    )


# ========== MAIN ENDPOINTS ==========

@router.post("/query", response_model=QueryResponse)
async def query_test_data(
        request: QueryRequest,
        query_service: SimpleQueryService = Depends(get_query_service)
):
    """
    Main query endpoint - handles natural language questions about test data.

    Examples:
    - "What's the pass rate this week?"
    - "Show me recent failures"
    - "How many tests failed today?"
    """
    try:
        logger.info(f"Processing query: {request.query}")

        # Process the query
        response = await query_service.query(
            request.query,
            environment=request.environment,
            days=request.days
        )

        # Build API response
        api_response = QueryResponse(
            answer=response.answer,
            confidence=response.confidence,
            sources=response.sources,
            related_queries=response.related_queries,
            execution_time_ms=response.execution_time_ms
        )

        logger.info(f"Query processed successfully in {response.execution_time_ms:.2f}ms")
        return api_response

    except Exception as e:
        logger.error(f"Query processing failed: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process query: {str(e)}"
        )


@router.post("/ask", response_model=Dict[str, Any])
async def ask_simple_question(
        request: QuickQueryRequest,
        query_service: SimpleQueryService = Depends(get_query_service)
):
    """
    Simple question-answer endpoint for quick queries.

    Examples:
    - "Did any tests fail today?"
    - "What's the current pass rate?"
    """
    try:
        logger.info(f"Simple question: {request.question}")

        answer = await query_service.ask(
            request.question,
            environment=request.environment,
            days=request.days
        )

        return {
            "question": request.question,
            "answer": answer,
            "timestamp": dt.isoformat_utc(dt.now_utc())
        }

    except Exception as e:
        logger.error(f"Simple query failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process question: {str(e)}"
        )


@router.get("/pass-rate", response_model=Dict[str, Any])
async def get_pass_rate(
        days: int = Query(7, description="Number of days to look back"),
        environment: Optional[str] = Query(None, description="Filter by environment"),
        query_service: SimpleQueryService = Depends(get_query_service)
):
    """Get current pass rate"""
    try:
        result = await query_service.get_pass_rate(
            days=days,
            environment=environment
        )

        return {
            "pass_rate_data": result,
            "timestamp": dt.isoformat_utc(dt.now_utc())
        }

    except Exception as e:
        logger.error(f"Pass rate query failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get pass rate: {str(e)}"
        )


@router.get("/suggestions", response_model=Dict[str, Any])
async def get_query_suggestions():
    """Get example queries users can try"""
    return {
        "common_queries": [
            "What's the current pass rate?",
            "Show me recent test failures",
            "How many tests ran today?",
            "Did any tests fail this week?",
            "What's the pass rate in staging?"
        ],
        "example_requests": {
            "simple_questions": [
                {"question": "What's the pass rate?"},
                {"question": "Show me failures today", "days": 1},
                {"question": "How are staging tests doing?", "environment": "staging"}
            ],
            "complex_queries": [
                {"query": "What's the pass rate for API tests this week?", "days": 7},
                {"query": "Show me recent failures in production", "environment": "production"}
            ]
        }
    }


@router.get("/health")
async def query_service_health(
        query_service: SimpleQueryService = Depends(get_query_service)
):
    """Health check for the query service"""
    try:
        # Test basic connectivity with a simple query
        test_response = await query_service.ask("health check test")

        return {
            "status": "healthy",
            "services": {
                "llm": "ok" if test_response else "degraded",
                "vector_db": "ok",
                "postgres": "ok"
            },
            "timestamp": dt.isoformat_utc(dt.now_utc())
        }

    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": dt.isoformat_utc(dt.now_utc())
        }