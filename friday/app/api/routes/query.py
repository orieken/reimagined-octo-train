from fastapi import APIRouter, Depends, HTTPException
from typing import List, Dict, Any, Optional
import logging
import re
import json

from app.config import settings
from app.services.orchestrator import ServiceOrchestrator
from app.api.dependencies import get_orchestrator_service

from app.models.search_analysis import QueryFilter, SearchQuery, QueryResult, SearchResults
from pydantic import BaseModel

from app.services import datetime_service as dt  # 🕒 Timezone-aware utility

logger = logging.getLogger(__name__)
router = APIRouter(prefix=settings.API_PREFIX, tags=["query"])


class QueryRequest(BaseModel):
    query: str
    filters: Optional[List[QueryFilter]] = None
    limit: Optional[int] = None


class SourceInfo(BaseModel):
    title: str
    confidence: float


class QueryResponse(BaseModel):
    status: str = "success"
    answer: str
    sources: List[SourceInfo] = []
    related_queries: List[str] = []
    execution_time_ms: Optional[float] = None
    start_timestamp: Optional[str] = None
    end_timestamp: Optional[str] = None


class QueryProcessor:
    def __init__(self, orchestrator: ServiceOrchestrator):
        self.orchestrator = orchestrator

    async def process_query(self, query_text: str) -> QueryResponse:
        logger.info(f"Parsing query: {query_text}")
        query_info = self._parse_query(query_text)
        logger.info(f"Extracted query info: {query_info}")

        search_results = await self._get_context(query_text, query_info)
        logger.info(f"Retrieved {len(search_results)} search results")

        answer = await self._generate_answer(query_text, search_results)
        sources = self._extract_sources(search_results)
        related_queries = await self._generate_related_queries(query_text, query_info)

        return QueryResponse(
            status="success",
            answer=answer,
            sources=sources,
            related_queries=related_queries
        )

    def _parse_query(self, query_text: str) -> Dict[str, Any]:
        query_info = {
            "intent": "unknown",
            "feature": None,
            "build": None,
            "metric": None,
            "time_range": None,
            "status": None,
        }

        pass_rate_pattern = re.compile(
            r"(?:what(?:'s| is| was)? the |show me the |)(?:pass|success) rate(?: for| of)? "
            r"([\w\s-]+?)(?:(?:in|from|during)(?: the| last)? ([\w\s#-]+))?(?:\?|$)", re.IGNORECASE
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

        failure_pattern = re.compile(
            r"(?:what|show|list|find)(?: are| me)? (?:the )?(?:most common |common |)(?:failures|errors|issues)(?: in| for| of)? "
            r"([\w\s-]+?)(?:(?:in|from|during)(?: the| last)? ([\w\s#-]+))?(?:\?|$)", re.IGNORECASE
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

        trend_pattern = re.compile(
            r"(?:how has|what is|show me)(?: the)? ([\w\s-]+?)(?: trend| changed| performance| rate)(?: over time| in the last| since| compared)? "
            r"([\w\s#-]+)?(?:\?|$)", re.IGNORECASE
        )
        match = trend_pattern.search(query_text)
        if match and query_info["intent"] == "unknown":
            query_info["intent"] = "trend_analysis"
            metric = match.group(1).strip() if match.group(1) else None
            query_info["metric"] = metric
            time_range = match.group(2).strip() if match.group(2) else "last 5 builds"
            query_info["time_range"] = time_range

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

        if query_info["intent"] == "unknown":
            query_info["intent"] = "general_query"

        return query_info

    async def _get_context(self, query_text: str, query_info: Dict[str, Any]) -> List[Dict[str, Any]]:
        query_embedding = await self.orchestrator.llm.generate_embedding(query_text)
        filters = {}

        if query_info["feature"]:
            filters["feature"] = query_info["feature"]
        if query_info["build"]:
            filters["build"] = query_info["build"]
        if query_info["status"]:
            filters["status"] = query_info["status"]

        artifact_type = "report" if query_info["intent"] == "trend_analysis" else "testcase"
        filters["type"] = artifact_type

        limit = 5
        search_results = await self.orchestrator.repository.semantic_search(
            query_embedding=query_embedding,
            filters=filters,
            limit=limit
        )

        return [
            {"id": result.id, "content": result.payload, "score": result.score}
            for result in search_results
        ]

    async def _generate_answer(self, query_text: str, context: List[Dict[str, Any]]) -> str:
        context_text = json.dumps([item["content"] for item in context], indent=2)

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

        return await self.orchestrator.llm.generate_text(
            prompt=prompt,
            system_prompt="You are a helpful test analysis assistant. Provide clear, accurate answers based on test data.",
            temperature=0.3,
            max_tokens=400
        )

    def _extract_sources(self, context: List[Dict[str, Any]]) -> List[SourceInfo]:
        sources = []
        for item in context:
            content = item["content"]
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
                title = f"Source {item['id'][:8]}"

            sources.append(SourceInfo(title=title, confidence=round(item["score"], 2)))

        sources.sort(key=lambda x: x.confidence, reverse=True)
        return sources[:3]

    async def _generate_related_queries(self, query_text: str, query_info: Dict[str, Any]) -> List[str]:
        related_queries = []

        feature = query_info.get("feature", "tests")
        metric = query_info.get("metric", "pass rate")
        status = query_info.get("status", "failed")

        if query_info["intent"] == "pass_rate":
            related_queries = [
                f"How has the {feature} pass rate changed over time?",
                f"What are the most common failures in {feature}?",
                f"Show me all failed {feature}"
            ]
        elif query_info["intent"] == "failure_analysis":
            related_queries = [
                f"Show me all failed {feature}",
                f"What's the pass rate for {feature}?",
                f"How has the failure rate for {feature} changed over time?"
            ]
        elif query_info["intent"] == "trend_analysis":
            related_queries = [
                f"What's the {metric} in the last build?",
                f"What are the most common failures related to {metric}?",
                f"Compare {metric} between last two builds"
            ]
        elif query_info["intent"] == "test_listing":
            related_queries = [
                f"Why did these {feature} {status}?",
                f"What's the pass rate for {feature}?",
                f"How has the {status} rate for {feature} changed over time?"
            ]

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
    try:
        start = dt.now_utc()
        logger.info(f"Processing query: {request.query}")

        processor = QueryProcessor(orchestrator)
        response = await processor.process_query(request.query)

        end = dt.now_utc()
        execution_time = (end - start).total_seconds() * 1000

        response.execution_time_ms = round(execution_time, 2)
        response.start_timestamp = dt.isoformat_utc(start)
        response.end_timestamp = dt.isoformat_utc(end)

        logger.info(f"Query processed successfully: {request.query} in {execution_time:.2f}ms")
        return response

    except Exception as e:
        logger.error(f"Error processing query: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process query: {str(e)}"
        )
