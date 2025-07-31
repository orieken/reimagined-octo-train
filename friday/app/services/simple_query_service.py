# app/services/simple_query_service.py
"""
Simplified Query Service that works with your current LLMService setup
"""
import logging
import json
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from app.services.llm import LLMService
from app.services.vector_db import VectorDBService
from app.services.postgres_db import PostgresDBService
from app.services import datetime_service as dt
from datetime import timedelta

logger = logging.getLogger(__name__)


@dataclass
class QueryResponse:
    """Simple query response"""
    answer: str
    confidence: float
    sources: List[Dict[str, Any]]
    related_queries: List[str]
    execution_time_ms: float = 0.0


class SimpleQueryService:
    """
    Simplified query service that works with your current setup
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
        Process a natural language query about test data
        """
        start_time = dt.now_utc()

        try:
            # 1. Get vector search results
            vector_results = await self._search_vector_data(query_text)

            # 2. Get SQL statistics
            sql_stats = await self._get_basic_stats(**kwargs)

            # 3. Generate answer using your existing query_ollama method
            answer = await self._generate_answer_simple(query_text, vector_results, sql_stats)

            # 4. Create response
            end_time = dt.now_utc()
            execution_time = (end_time - start_time).total_seconds() * 1000

            return QueryResponse(
                answer=answer,
                confidence=0.8 if vector_results or sql_stats else 0.3,
                sources=vector_results[:3],  # Top 3 sources
                related_queries=self._get_simple_related_queries(query_text),
                execution_time_ms=execution_time
            )

        except Exception as e:
            logger.error(f"Query failed: {str(e)}", exc_info=True)
            return QueryResponse(
                answer=f"I encountered an error while processing your query: {str(e)}",
                confidence=0.0,
                sources=[],
                related_queries=[],
                execution_time_ms=0.0
            )

    async def _search_vector_data(self, query_text: str) -> List[Dict[str, Any]]:
        """Search vector database using your existing setup"""
        try:
            # Generate embedding
            query_embedding = await self.llm.embed_text(query_text)

            # Search using Qdrant client directly (since your VectorDBService doesn't have search method)
            search_results = self.vector_db.client.search(
                collection_name="test_artifacts",
                query_vector=query_embedding,
                limit=5,
                score_threshold=0.3
            )

            # Convert to simple format
            results = []
            for result in search_results:
                results.append({
                    "id": str(result.id),
                    "content": result.payload,
                    "score": result.score,
                    "type": result.payload.get("type", "unknown")
                })

            return results

        except Exception as e:
            logger.error(f"Vector search failed: {e}")
            return []

    async def _get_basic_stats(self, **kwargs) -> Dict[str, Any]:
        """Get basic test statistics from PostgreSQL"""
        try:
            async with self.postgres.session() as session:
                from sqlalchemy import select, func, and_
                from app.models.database import Scenario, TestRun, TestStatus

                # Build base query for recent tests
                days = kwargs.get("days", 7)
                cutoff = dt.now_utc() - timedelta(days=days)

                query = select(
                    func.count(Scenario.id).label("total"),
                    func.sum(func.case((Scenario.status == TestStatus.PASSED, 1), else_=0)).label("passed"),
                    func.sum(func.case((Scenario.status == TestStatus.FAILED, 1), else_=0)).label("failed"),
                    func.sum(func.case((Scenario.status == TestStatus.SKIPPED, 1), else_=0)).label("skipped")
                ).select_from(Scenario).join(TestRun).where(TestRun.created_at >= cutoff)

                # Add environment filter if specified
                if kwargs.get("environment"):
                    query = query.where(TestRun.environment == kwargs["environment"])

                result = await session.execute(query)
                row = result.fetchone()

                if row and row.total:
                    return {
                        "total_tests": row.total,
                        "passed": row.passed,
                        "failed": row.failed,
                        "skipped": row.skipped,
                        "pass_rate": round((row.passed / row.total) * 100, 2),
                        "time_period": f"last {days} days"
                    }

                return {"total_tests": 0, "pass_rate": 0, "time_period": f"last {days} days"}

        except Exception as e:
            logger.error(f"SQL stats failed: {e}")
            return {}

    async def _generate_answer_simple(
            self,
            query_text: str,
            vector_results: List[Dict[str, Any]],
            sql_stats: Dict[str, Any]
    ) -> str:
        """Generate answer using your existing query_ollama method"""

        # Build context from available data
        context_parts = []

        # Add SQL statistics
        if sql_stats:
            if sql_stats.get("total_tests", 0) > 0:
                context_parts.append(
                    f"Recent Statistics ({sql_stats.get('time_period', 'recent')}): "
                    f"{sql_stats['total_tests']} total tests, "
                    f"{sql_stats['pass_rate']}% pass rate, "
                    f"{sql_stats.get('failed', 0)} failures, "
                    f"{sql_stats.get('passed', 0)} passed"
                )
            else:
                context_parts.append("No recent test data found in the specified time period.")

        # Add vector search results
        if vector_results:
            context_parts.append("\nRelevant Test Details:")
            for i, result in enumerate(vector_results[:3], 1):
                content = result["content"]
                name = content.get("name", "Unknown Test")
                test_type = content.get("type", "test")
                context_parts.append(f"{i}. {test_type.title()}: {name}")

                if content.get("status"):
                    context_parts.append(f"   Status: {content['status']}")
                if content.get("feature"):
                    context_parts.append(f"   Feature: {content['feature']}")

        # Create the full prompt
        context_text = "\n".join(context_parts) if context_parts else "No specific test data found."

        prompt = f"""You are a helpful test analysis assistant. Answer the user's question about their test results using the provided context.

QUESTION: {query_text}

AVAILABLE DATA:
{context_text}

Please provide a clear, concise answer based on the available data. If the data is limited, acknowledge that and provide what information you can. Include specific numbers when available.

ANSWER:"""

        try:
            # Use your existing query_ollama method
            answer = await self.llm.query_ollama(prompt)
            return answer.strip() if answer else "I don't have enough information to answer that question."

        except Exception as e:
            logger.error(f"Answer generation failed: {e}")
            return f"I found some relevant data but had trouble generating a complete answer: {str(e)}"

    def _get_simple_related_queries(self, query_text: str) -> List[str]:
        """Generate simple related queries based on keywords"""
        related = []

        query_lower = query_text.lower()

        if any(word in query_lower for word in ["fail", "failed", "failing", "error"]):
            related = [
                "What's the current pass rate?",
                "Show me test trends this week",
                "Which features have the most failures?"
            ]
        elif any(word in query_lower for word in ["pass", "passing", "success"]):
            related = [
                "Show me recent test failures",
                "How are tests trending over time?",
                "Which tests are most reliable?"
            ]
        elif any(word in query_lower for word in ["trend", "time", "history"]):
            related = [
                "What's the current pass rate?",
                "Show me recent failures",
                "Which environments are most stable?"
            ]
        else:
            related = [
                "What's the current pass rate?",
                "Show me recent test failures",
                "How are tests trending this week?"
            ]

        return related[:3]

    # Simple API methods
    async def ask(self, question: str, **filters) -> str:
        """Simple question-answer interface"""
        response = await self.query(question, **filters)
        return response.answer

    async def get_pass_rate(self, days: int = 7, environment: str = None) -> Dict[str, Any]:
        """Get current pass rate"""
        stats = await self._get_basic_stats(days=days, environment=environment)

        if stats.get("total_tests", 0) > 0:
            return {
                "pass_rate": stats["pass_rate"],
                "total_tests": stats["total_tests"],
                "passed": stats["passed"],
                "failed": stats["failed"],
                "time_period": stats["time_period"],
                "environment": environment or "all environments"
            }
        else:
            return {
                "pass_rate": 0,
                "total_tests": 0,
                "message": f"No test data found for the last {days} days",
                "environment": environment or "all environments"
            }
