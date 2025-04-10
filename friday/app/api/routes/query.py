# app/api/routes/query.py
from fastapi import APIRouter, Depends, HTTPException, Query as QueryParam
from typing import List, Dict, Any, Optional
import logging
from datetime import datetime

from app.config import settings
from app.services.orchestrator import ServiceOrchestrator
from app.api.dependencies import get_orchestrator_service

from app.models import SearchQuery
from app.models.search_analysis import QueryFilter

logger = logging.getLogger(__name__)
router = APIRouter(prefix=settings.API_PREFIX, tags=["query"])


@router.post("/query", response_model=Dict[str, Any])
async def query_data(
        query: str,
        filters: List[QueryFilter] = None,
        limit: int = QueryParam(10, description="Maximum number of results to return"),
        orchestrator: ServiceOrchestrator = Depends(get_orchestrator_service)
):
    """
    Query the vector database using natural language.

    This endpoint allows querying the vector database using natural language,
    and returns the most relevant results.
    """
    try:
        logger.info(f"Query request: {query}")

        # Create a search query
        search_query = SearchQuery(
            query=query,
            filters=filters or {},
            limit=limit
        )

        # Perform the search
        search_results = await orchestrator.search(search_query)

        return {
            "query": query,
            "results": search_results.results,
            "total_hits": search_results.total_hits,
            "execution_time_ms": search_results.execution_time_ms,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Query error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Query failed: {str(e)}"
        )


@router.post("/answer", response_model=Dict[str, Any])
async def generate_answer(
        query: str,
        context: Optional[List[Dict[str, Any]]] = None,
        max_tokens: int = QueryParam(800, description="Maximum tokens to generate"),
        orchestrator: ServiceOrchestrator = Depends(get_orchestrator_service)
):
    """
    Generate an answer to a natural language query.

    This endpoint uses the LLM to generate an answer based on the provided
    query and optional context.
    """
    try:
        logger.info(f"Answer request: {query}")

        # Generate the answer
        answer = await orchestrator.generate_answer(
            query=query,
            context=context,
            max_tokens=max_tokens
        )

        return {
            "query": query,
            "answer": answer,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Answer generation error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate answer: {str(e)}"
        )