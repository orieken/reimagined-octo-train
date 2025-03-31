"""
API routes for querying test data
"""
from typing import Dict, Optional
from fastapi import APIRouter, Depends, HTTPException, Query as QueryParam

from app.models.api import QueryRequest, QueryResponse
from app.models.domain import QueryResult
from app.config import get_settings, Settings
from app.services.llm import LLMService
from app.api.dependencies import get_llm_service, get_generator_service, get_retrieval_service
from app.core.rag.retrieval import RetrievalService
from app.core.rag.generator import GeneratorService

router = APIRouter()


@router.post("", response_model=QueryResponse)
async def query_test_data(
        request_data: QueryRequest,
        llm_service: LLMService = Depends(get_llm_service),
        retrieval_service: RetrievalService = Depends(get_retrieval_service),
        generator_service: GeneratorService = Depends(get_generator_service),
        settings: Settings = Depends(get_settings)
):
    """
    Query test data using natural language

    Uses RAG pipeline to generate a response based on test data
    """
    try:
        # In Phase 1, we return a mock response
        # This will be replaced with actual RAG pipeline in Phase 3

        # Mock embedding generation
        query_embedding = await llm_service.generate_embedding(request_data.query)

        # Mock retrieval (empty in Phase 1)
        filters = {}
        if request_data.test_run_id:
            filters["test_run_id"] = request_data.test_run_id
        if request_data.build_id:
            filters["build_id"] = request_data.build_id
        if request_data.tags:
            filters["tags"] = request_data.tags

        results = await retrieval_service.retrieve(query_embedding, filters)

        # Format context from results (empty in Phase 1)
        context = retrieval_service.format_context(results)

        # Generate response
        generation_result = await generator_service.generate(
            query=request_data.query,
            context=context
        )

        # Create response
        query_result = QueryResult(
            answer=generation_result["answer"],
            confidence=generation_result["confidence"],
            sources=[],  # Empty in Phase 1
            metadata={}
        )

        return {"result": query_result}

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process query: {str(e)}"
        )