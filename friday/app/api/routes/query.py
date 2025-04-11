from fastapi import APIRouter, Depends, HTTPException
from typing import List, Dict, Any, Optional
import logging
from datetime import datetime
import re
import json
import time

from app.config import settings
from app.services.orchestrator import ServiceOrchestrator
from app.api.dependencies import get_orchestrator_service

from app.models.search_analysis import QueryFilter, SearchQuery, QueryResult, SearchResults
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter(prefix=settings.API_PREFIX, tags=["query"])


class QueryRequest(BaseModel):
    """Request model for natural language query."""
    query: str
    filters: Optional[List[QueryFilter]] = None
    limit: Optional[int] = None


class SourceInfo(BaseModel):
    """Information about a source used to answer a query."""
    title: str
    confidence: float


class QueryResponse(BaseModel):
    """Response model for natural language query."""
    status: str = "success"
    answer: str
    sources: List[SourceInfo] = []
    related_queries: List[str] = []
    execution_time_ms: Optional[float] = None


class QueryProcessor:
    """Processes natural language queries and generates answers."""

    def __init__(self, orchestrator: ServiceOrchestrator):
        self.orchestrator = orchestrator

    async def process_query(self, query_text: str) -> QueryResponse:
        """
        Process a natural language query and generate a response.

        Args:
            query_text: The natural language query from the user

        Returns:
            QueryResponse with answer, sources, and related queries
        """
        logger.info(f"Parsing query: {query_text}")
        # 1. Extract key entities and intent from the query
        query_info = self._parse_query(query_text)
        logger.info(f"Extracted query info: {query_info}")

        # 2. Get relevant context from vector DB through semantic search
        search_results = await self._get_context(query_text, query_info)
        logger.info(f"Retrieved {len(search_results)} search results")

        # 3. Generate answer using the LLM
        answer = await self._generate_answer(query_text, search_results)

        # 4. Extract sources from the search results
        sources = self._extract_sources(search_results)

        # 5. Generate related queries
        related_queries = await self._generate_related_queries(query_text, query_info)

        return QueryResponse(
            status="success",
            answer=answer,
            sources=sources,
            related_queries=related_queries
        )

    def _parse_query(self, query_text: str) -> Dict[str, Any]:
        """
        Parse the query to extract key entities and intent.

        This uses pattern matching to identify common query types and extract
        relevant parameters like feature names, builds, metrics, etc.

        Args:
            query_text: The natural language query

        Returns:
            Dictionary with extracted parameters and query intent
        """
        query_info = {
            "intent": "unknown",
            "feature": None,
            "build": None,
            "metric": None,
            "time_range": None,
            "status": None,
        }

        # Detect query intent and extract entities using pattern matching

        # Check for pass rate queries
        pass_rate_pattern = re.compile(
            r"(?:what(?:'s| is| was)? the |show me the |)(?:pass|success) rate(?: for| of)? "
            r"([\w\s-]+?)(?:(?:in|from|during)(?: the| last)? ([\w\s#-]+))?(?:\?|$)",
            re.IGNORECASE
        )
        match = pass_rate_pattern.search(query_text)
        if match:
            query_info["intent"] = "pass_rate"
            feature = match.group(1).strip() if match.group(1) else None
            if feature and not feature.endswith("tests"):
                feature += " tests"
            query_info["feature"] = feature

            build_or_time = match.group(2).strip() if match.group(2) else "last build"
            if re.search(r"#\d+|build \d+|last build", build_or_time, re.IGNORECASE):
                query_info["build"] = build_or_time
            else:
                query_info["time_range"] = build_or_time

        # Check for failure analysis queries
        failure_pattern = re.compile(
            r"(?:what|show|list|find)(?: are| me)? (?:the )?(?:most common |common |)(?:failures|errors|issues)(?: in| for| of)? "
            r"([\w\s-]+?)(?:(?:in|from|during)(?: the| last)? ([\w\s#-]+))?(?:\?|$)",
            re.IGNORECASE
        )
        match = failure_pattern.search(query_text)
        if match and query_info["intent"] == "unknown":
            query_info["intent"] = "failure_analysis"
            feature = match.group(1).strip() if match.group(1) else None
            if feature and not feature.endswith("tests"):
                feature += " tests"
            query_info["feature"] = feature

            build_or_time = match.group(2).strip() if match.group(2) else "last build"
            if re.search(r"#\d+|build \d+|last build", build_or_time, re.IGNORECASE):
                query_info["build"] = build_or_time
            else:
                query_info["time_range"] = build_or_time

        # Check for trend analysis queries
        trend_pattern = re.compile(
            r"(?:how has|what is|show me)(?: the)? ([\w\s-]+?)(?: trend| changed| performance| rate)(?: over time| in the last| since| compared)? "
            r"([\w\s#-]+)?(?:\?|$)",
            re.IGNORECASE
        )
        match = trend_pattern.search(query_text)
        if match and query_info["intent"] == "unknown":
            query_info["intent"] = "trend_analysis"
            metric = match.group(1).strip() if match.group(1) else None
            query_info["metric"] = metric

            time_range = match.group(2).strip() if match.group(2) else "last 5 builds"
            query_info["time_range"] = time_range

        # Check for test listing queries
        test_listing_pattern = re.compile(
            r"(?:show|list|find|get)(?: me)?(?: all)? (passed|failed|skipped|running) ([\w\s-]+?)(?:(?:in|from|during)(?: the| last)? ([\w\s#-]+))?(?:\?|$)",
            re.IGNORECASE
        )
        match = test_listing_pattern.search(query_text)
        if match and query_info["intent"] == "unknown":
            query_info["intent"] = "test_listing"
            query_info["status"] = match.group(1).lower()
            feature = match.group(2).strip() if match.group(2) else None
            if feature and not feature.endswith("tests"):
                feature += " tests"
            query_info["feature"] = feature

            build_or_time = match.group(3).strip() if match.group(3) else "last build"
            if re.search(r"#\d+|build \d+|last build", build_or_time, re.IGNORECASE):
                query_info["build"] = build_or_time
            else:
                query_info["time_range"] = build_or_time

        # If we couldn't determine the intent, use a default
        if query_info["intent"] == "unknown":
            # Default to a generic query
            query_info["intent"] = "general_query"

        return query_info

    async def _get_context(self, query_text: str, query_info: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Get relevant context for the query from the vector database.

        Args:
            query_text: The natural language query
            query_info: Extracted query information

        Returns:
            List of relevant context items
        """
        # Generate embedding for the query
        query_embedding = await self.orchestrator.llm.generate_embedding(query_text)

        # Prepare filters based on extracted entities
        filters = {}

        # Add filters based on query intent and extracted entities
        if query_info["feature"]:
            filters["feature"] = query_info["feature"]

        if query_info["build"]:
            filters["build"] = query_info["build"]

        if query_info["status"]:
            filters["status"] = query_info["status"]

        # Determine artifact type based on intent
        artifact_type = "testcase"
        if query_info["intent"] == "trend_analysis":
            artifact_type = "report"

        filters["type"] = artifact_type

        # Get search results (using the repository directly since semantic_search isn't available)
        limit = 5
        search_results = await self.orchestrator.repository.semantic_search(
            query_embedding=query_embedding,
            filters=filters,
            limit=limit
        )

        # Convert search results to context items
        context = []
        for result in search_results:
            context.append({
                "id": result.id,
                "content": result.payload,
                "score": result.score
            })

        return context

    async def _generate_answer(self, query_text: str, context: List[Dict[str, Any]]) -> str:
        """
        Generate a natural language answer using the LLM service.

        Args:
            query_text: The natural language query
            context: Relevant context items

        Returns:
            Generated answer
        """
        # Prepare context for the LLM
        context_text = json.dumps([item["content"] for item in context], indent=2)

        # Create a prompt for the LLM
        prompt = f"""
        Use the following context to answer the question:

        CONTEXT:
        {context_text}

        QUESTION:
        {query_text}

        Answer the question in a clear, concise manner. If the context doesn't contain enough
        information to fully answer the question, acknowledge that and provide the best answer
        possible with the available information. If appropriate, include specific numbers and
        metrics in your answer.
        """

        # Generate answer using the LLM service
        answer = await self.orchestrator.llm.generate_text(
            prompt=prompt,
            system_prompt="You are a helpful test analysis assistant. Provide clear, accurate answers based on test data.",
            temperature=0.3,
            max_tokens=400
        )

        return answer

    def _extract_sources(self, context: List[Dict[str, Any]]) -> List[SourceInfo]:
        """
        Extract source information from context items.

        Args:
            context: Relevant context items

        Returns:
            List of source items with title and confidence
        """
        sources = []

        for item in context:
            content = item["content"]
            title = ""

            # Extract a meaningful title based on content type
            if "type" in content:
                if content["type"] == "report":
                    title = f"Build #{content.get('build_number', 'Unknown')}"
                elif content["type"] == "test_case":
                    title = f"{content.get('feature', 'Unknown Feature')} - {content.get('name', 'Unknown Test')}"
                elif content["type"] == "feature":
                    title = f"{content.get('name', 'Unknown Feature')}"
                else:
                    title = f"{content.get('name', 'Unknown Item')}"
            else:
                # Fallback to using a generic title
                title = f"Source {item['id'][:8]}"

            sources.append(
                SourceInfo(
                    title=title,
                    confidence=round(item["score"], 2)
                )
            )

        # Sort sources by confidence score
        sources.sort(key=lambda x: x.confidence, reverse=True)

        return sources[:3]  # Limit to top 3 sources

    async def _generate_related_queries(self, query_text: str, query_info: Dict[str, Any]) -> List[str]:
        """
        Generate related queries based on the original query.

        Args:
            query_text: The natural language query
            query_info: Extracted query information

        Returns:
            List of related query suggestions
        """
        # Define related queries based on the query intent
        related_queries = []

        if query_info["intent"] == "pass_rate":
            # For pass rate queries, suggest trend analysis and failure analysis
            feature = query_info["feature"] or "tests"
            related_queries = [
                f"How has the {feature} pass rate changed over time?",
                f"What are the most common failures in {feature}?",
                f"Show me all failed {feature}"
            ]

        elif query_info["intent"] == "failure_analysis":
            # For failure analysis, suggest specific test listing and trend analysis
            feature = query_info["feature"] or "tests"
            related_queries = [
                f"Show me all failed {feature}",
                f"What's the pass rate for {feature}?",
                f"How has the failure rate for {feature} changed over time?"
            ]

        elif query_info["intent"] == "trend_analysis":
            # For trend analysis, suggest specific build analysis
            metric = query_info["metric"] or "pass rate"
            related_queries = [
                f"What's the {metric} in the last build?",
                f"What are the most common failures related to {metric}?",
                f"Compare {metric} between last two builds"
            ]

        elif query_info["intent"] == "test_listing":
            # For test listing, suggest analysis on those tests
            status = query_info["status"] or "failed"
            feature = query_info["feature"] or "tests"
            related_queries = [
                f"Why did these {feature} {status}?",
                f"What's the pass rate for {feature}?",
                f"How has the {status} rate for {feature} changed over time?"
            ]

        # If we couldn't generate related queries, use defaults
        if not related_queries:
            related_queries = [
                "What's the overall pass rate in the last build?",
                "Show me the most flaky tests",
                "What are the most common failures in the last week?"
            ]

        return related_queries


@router.post("/query", response_model=QueryResponse)
async def query_endpoint(
        request: QueryRequest,
        orchestrator: ServiceOrchestrator = Depends(get_orchestrator_service)
):
    """
    Process a natural language query about test results.

    This endpoint takes a natural language query and returns an answer based on the test data,
    along with relevant sources and suggested related queries.

    Example:
        Request: { "query": "What was the pass rate for authentication tests in the last build?" }

        Response: {
            "status": "success",
            "answer": "The pass rate for authentication tests in the last build (#1045) was 85.7%.",
            "sources": [
                { "title": "Build #1045", "confidence": 0.92 },
                { "title": "Authentication Feature", "confidence": 0.88 }
            ],
            "related_queries": [
                "What are the most common failures in authentication tests?",
                "How has the authentication pass rate changed over time?",
                "Show me all failed authentication tests"
            ],
            "execution_time_ms": 235.6
        }
    """
    try:
        start_time = time.time()
        logger.info(f"Processing query: {request.query}")

        # Process the query using the QueryProcessor
        processor = QueryProcessor(orchestrator)
        response = await processor.process_query(request.query)

        # Calculate execution time
        execution_time = (time.time() - start_time) * 1000  # Convert to milliseconds
        response.execution_time_ms = round(execution_time, 2)

        logger.info(f"Query processed successfully: {request.query} in {execution_time:.2f}ms")
        return response

    except Exception as e:
        logger.error(f"Error processing query: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process query: {str(e)}"
        )
