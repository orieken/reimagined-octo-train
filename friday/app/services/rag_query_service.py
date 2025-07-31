# app/services/rag_query_service.py
"""
Retrieval-Augmented Generation (RAG) Query Service for Test Data Analysis
"""
import logging
import json
from typing import List, Dict, Any, Optional, Union
from dataclasses import dataclass
from enum import Enum

from app.services.llm import LLMService
from app.services.vector_db import VectorDBService
from app.services.postgres_db import PostgresDBService
from app.services import datetime_service as dt
from app.models.database import TestStatus

logger = logging.getLogger(__name__)


class QueryIntent(Enum):
    FAILURE_ANALYSIS = "failure_analysis"
    PASS_RATE = "pass_rate"
    TREND_ANALYSIS = "trend_analysis"
    TEST_LISTING = "test_listing"
    GENERAL_QUERY = "general_query"
    COMPARISON = "comparison"


@dataclass
class QueryContext:
    """Structured context for queries"""
    intent: QueryIntent
    entities: Dict[str, Any]  # features, environments, time_ranges, etc.
    filters: Dict[str, Any]  # status, project, tags, etc.
    metadata: Dict[str, Any]  # additional context


@dataclass
class SearchResult:
    """Standardized search result"""
    id: str
    content: Dict[str, Any]
    score: float
    source_type: str  # "scenario", "feature", "test_run", etc.


@dataclass
class QueryResponse:
    """Comprehensive query response"""
    answer: str
    confidence: float
    sources: List[SearchResult]
    related_queries: List[str]
    sql_context: Optional[Dict[str, Any]] = None
    vector_context: Optional[List[SearchResult]] = None
    execution_time_ms: float = 0.0


class TestDataQueryService:
    """
    Centralized service for querying test data using RAG approach.
    Combines SQL queries for structured data with vector search for semantic queries.
    """

    def __init__(
            self,
            llm_service: LLMService,
            vector_db_service: VectorDBService,
            postgres_service: PostgresDBService
    ):
        self.llm = llm_service
        self.vector_db = vector_db_service
        self.postgres = postgres_service

    async def query(self, query_text: str, **kwargs) -> QueryResponse:
        """
        Main query interface - handles any natural language query about test data.

        Args:
            query_text: Natural language query
            **kwargs: Additional filters (project_id, environment, days, etc.)

        Returns:
            QueryResponse with answer and supporting data
        """
        start_time = dt.now_utc()

        try:
            # 1. Parse and understand the query
            context = await self._parse_query(query_text, **kwargs)
            logger.info(f"Query context: {context}")

            # 2. Get relevant data from both sources
            vector_results = await self._get_vector_context(query_text, context)
            sql_data = await self._get_sql_context(context)

            # 3. Generate comprehensive answer
            answer = await self._generate_answer(query_text, vector_results, sql_data)

            # 4. Calculate confidence and generate related queries
            confidence = self._calculate_confidence(vector_results, sql_data)
            related_queries = self._generate_related_queries(context)

            end_time = dt.now_utc()
            execution_time = (end_time - start_time).total_seconds() * 1000

            return QueryResponse(
                answer=answer,
                confidence=confidence,
                sources=vector_results,
                related_queries=related_queries,
                sql_context=sql_data,
                vector_context=vector_results,
                execution_time_ms=execution_time
            )

        except Exception as e:
            logger.error(f"Query failed: {str(e)}", exc_info=True)
            return QueryResponse(
                answer=f"I encountered an error while processing your query: {str(e)}",
                confidence=0.0,
                sources=[],
                related_queries=[]
            )

    # ========== QUERY PARSING ==========

    async def _parse_query(self, query_text: str, **kwargs) -> QueryContext:
        """Parse natural language query into structured context"""

        # Use LLM to extract intent and entities
        parsing_prompt = f"""
        Analyze this test-related query and extract:
        1. Intent (failure_analysis, pass_rate, trend_analysis, test_listing, comparison, general_query)
        2. Entities (features, environments, time periods, test statuses)
        3. Filters needed for data retrieval

        Query: "{query_text}"

        Respond in JSON format:
        {{
            "intent": "intent_name",
            "entities": {{
                "features": ["feature1", "feature2"],
                "environments": ["env1"],
                "time_range": "last week",
                "status": "failed"
            }},
            "filters": {{
                "status": "FAILED",
                "days": 7,
                "environment": "staging"
            }}
        }}
        """

        try:
            llm_response = await self.llm.generate_text(
                prompt=parsing_prompt,
                temperature=0.1,
                max_tokens=300
            )

            parsed = json.loads(llm_response)

            return QueryContext(
                intent=QueryIntent(parsed.get("intent", "general_query")),
                entities=parsed.get("entities", {}),
                filters={**parsed.get("filters", {}), **kwargs},
                metadata={"original_query": query_text}
            )

        except Exception as e:
            logger.warning(f"LLM parsing failed, using fallback: {e}")
            return self._fallback_parse(query_text, **kwargs)

    def _fallback_parse(self, query_text: str, **kwargs) -> QueryContext:
        """Regex-based fallback parsing"""
        import re

        context = QueryContext(
            intent=QueryIntent.GENERAL_QUERY,
            entities={},
            filters=kwargs,
            metadata={"original_query": query_text}
        )

        # Simple regex patterns for common queries
        if re.search(r'\b(fail|failed|failing|error)\b', query_text, re.IGNORECASE):
            context.intent = QueryIntent.FAILURE_ANALYSIS
            context.filters["status"] = "FAILED"

        elif re.search(r'\b(pass rate|success rate|passing)\b', query_text, re.IGNORECASE):
            context.intent = QueryIntent.PASS_RATE

        elif re.search(r'\b(trend|over time|history|compare)\b', query_text, re.IGNORECASE):
            context.intent = QueryIntent.TREND_ANALYSIS

        # Extract time references
        if re.search(r'\b(today|this week|last week|yesterday)\b', query_text, re.IGNORECASE):
            context.filters["days"] = 7

        return context

    # ========== DATA RETRIEVAL ==========

    async def _get_vector_context(self, query_text: str, context: QueryContext) -> List[SearchResult]:
        """Get relevant context from vector database"""
        try:
            # Generate query embedding
            query_embedding = await self.llm.embed_text(query_text)

            # Search vector database
            search_results = self.vector_db.client.search(
                collection_name="test_artifacts",
                query_vector=query_embedding,
                limit=10,
                score_threshold=0.5
            )

            # Convert to standardized format
            results = []
            for result in search_results:
                results.append(SearchResult(
                    id=str(result.id),
                    content=result.payload,
                    score=result.score,
                    source_type=result.payload.get("type", "unknown")
                ))

            return results

        except Exception as e:
            logger.error(f"Vector search failed: {e}")
            return []

    async def _get_sql_context(self, context: QueryContext) -> Dict[str, Any]:
        """Get structured data from PostgreSQL based on query context"""
        try:
            sql_data = {}

            # Get recent statistics
            if context.intent in [QueryIntent.PASS_RATE, QueryIntent.FAILURE_ANALYSIS]:
                sql_data["statistics"] = await self._get_test_statistics(context)

            # Get trend data
            if context.intent == QueryIntent.TREND_ANALYSIS:
                sql_data["trends"] = await self._get_trend_data(context)

            # Get failure details
            if context.intent == QueryIntent.FAILURE_ANALYSIS:
                sql_data["failures"] = await self._get_failure_details(context)

            return sql_data

        except Exception as e:
            logger.error(f"SQL context retrieval failed: {e}")
            return {}

    async def _get_test_statistics(self, context: QueryContext) -> Dict[str, Any]:
        """Get current test statistics"""
        async with self.postgres.session() as session:
            from sqlalchemy import select, func, and_
            from app.models.database import Scenario, TestRun, Feature

            # Build base query
            query = select(
                func.count(Scenario.id).label("total"),
                func.sum(func.case((Scenario.status == TestStatus.PASSED, 1), else_=0)).label("passed"),
                func.sum(func.case((Scenario.status == TestStatus.FAILED, 1), else_=0)).label("failed"),
                func.sum(func.case((Scenario.status == TestStatus.SKIPPED, 1), else_=0)).label("skipped")
            ).select_from(Scenario).join(TestRun)

            # Apply filters
            filters = []
            if context.filters.get("days"):
                cutoff = dt.now_utc() - dt.timedelta(days=context.filters["days"])
                filters.append(TestRun.created_at >= cutoff)

            if context.filters.get("environment"):
                filters.append(TestRun.environment == context.filters["environment"])

            if filters:
                query = query.where(and_(*filters))

            result = await session.execute(query)
            row = result.fetchone()

            if row and row.total:
                return {
                    "total_tests": row.total,
                    "passed": row.passed,
                    "failed": row.failed,
                    "skipped": row.skipped,
                    "pass_rate": round((row.passed / row.total) * 100, 2)
                }

            return {"total_tests": 0, "pass_rate": 0}

    async def _get_trend_data(self, context: QueryContext) -> List[Dict[str, Any]]:
        """Get trend data over time"""
        # Implementation for getting daily/weekly trends
        return []

    async def _get_failure_details(self, context: QueryContext) -> List[Dict[str, Any]]:
        """Get details about recent failures"""
        async with self.postgres.session() as session:
            from sqlalchemy import select, desc
            from app.models.database import Scenario, TestRun, Feature, Step

            query = (
                select(Scenario, TestRun.environment, Feature.name.label("feature_name"))
                .join(TestRun)
                .outerjoin(Feature)
                .where(Scenario.status == TestStatus.FAILED)
                .order_by(desc(TestRun.created_at))
                .limit(20)
            )

            result = await session.execute(query)
            failures = []

            for row in result:
                failures.append({
                    "scenario_name": row.Scenario.name,
                    "feature": row.feature_name,
                    "environment": row.environment,
                    "created_at": row.Scenario.created_at.isoformat() if row.Scenario.created_at else None
                })

            return failures

    # ========== ANSWER GENERATION ==========

    async def _generate_answer(
            self,
            query_text: str,
            vector_results: List[SearchResult],
            sql_data: Dict[str, Any]
    ) -> str:
        """Generate comprehensive answer using both vector and SQL context"""

        # Prepare context from vector results
        vector_context = ""
        if vector_results:
            vector_context = "\n".join([
                f"- {result.content.get('name', 'Unknown')}: {result.content.get('description', '')}"
                for result in vector_results[:5]
            ])

        # Prepare context from SQL data
        sql_context = ""
        if sql_data.get("statistics"):
            stats = sql_data["statistics"]
            sql_context += f"Current Statistics: {stats['total_tests']} total tests, {stats['pass_rate']}% pass rate\n"

        if sql_data.get("failures"):
            sql_context += f"Recent Failures: {len(sql_data['failures'])} failed tests found\n"

        # Generate answer
        prompt = f"""
        You are a helpful test analysis assistant. Answer the user's question using the provided context.
        Be specific, include numbers when available, and acknowledge if information is limited.

        QUESTION: {query_text}

        RECENT DATA:
        {sql_context}

        RELATED TEST DETAILS:
        {vector_context}

        ANSWER:
        """

        answer = await self.llm.generate_text(
            prompt=prompt,
            temperature=0.3,
            max_tokens=500,
            system_prompt="Provide clear, data-driven answers about test results. Be concise but informative."
        )

        return answer

    # ========== UTILITY METHODS ==========

    def _calculate_confidence(self, vector_results: List[SearchResult], sql_data: Dict[str, Any]) -> float:
        """Calculate confidence score for the answer"""
        confidence = 0.0

        # Boost confidence based on vector search results
        if vector_results:
            avg_score = sum(r.score for r in vector_results) / len(vector_results)
            confidence += min(avg_score * 0.5, 0.4)

        # Boost confidence based on SQL data availability
        if sql_data:
            confidence += 0.3

        # Additional context boosts confidence
        if len(vector_results) >= 3:
            confidence += 0.2

        return min(confidence, 1.0)

    def _generate_related_queries(self, context: QueryContext) -> List[str]:
        """Generate related queries based on context"""
        related = []

        if context.intent == QueryIntent.FAILURE_ANALYSIS:
            related = [
                "What's the overall pass rate this week?",
                "Show me trend analysis for failed tests",
                "Which features have the most failures?"
            ]
        elif context.intent == QueryIntent.PASS_RATE:
            related = [
                "Show me recent test failures",
                "How has the pass rate changed over time?",
                "Which environments have the lowest pass rate?"
            ]
        else:
            related = [
                "What's the current pass rate?",
                "Show me recent failures",
                "How are tests trending this week?"
            ]

        return related[:3]


# ========== SIMPLE API INTERFACE ==========

class SimpleTestQueryAPI:
    """Simplified interface for common test queries"""

    def __init__(self, query_service: TestDataQueryService):
        self.query_service = query_service

    async def ask(self, question: str, **filters) -> str:
        """Simple question-answer interface"""
        response = await self.query_service.query(question, **filters)
        return response.answer

    async def get_pass_rate(self, feature: str = None, environment: str = None, days: int = 7) -> Dict[str, Any]:
        """Get pass rate with optional filters"""
        query = f"What's the pass rate"
        if feature:
            query += f" for {feature}"
        if environment:
            query += f" in {environment}"
        query += f" in the last {days} days?"

        response = await self.query_service.query(query, environment=environment, days=days)
        return {
            "answer": response.answer,
            "confidence": response.confidence,
            "sql_data": response.sql_context
        }

    async def analyze_failures(self, feature: str = None, days: int = 7) -> Dict[str, Any]:
        """Analyze recent failures"""
        query = f"Analyze recent test failures"
        if feature:
            query += f" in {feature}"
        query += f" from the last {days} days"

        response = await self.query_service.query(query, days=days)
        return {
            "answer": response.answer,
            "failures": response.sql_context.get("failures", []),
            "related_queries": response.related_queries
        }