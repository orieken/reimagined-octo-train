# app/services/orchestrator.py
from typing import List, Dict, Any, Optional
import logging
import uuid
import time
import json
from datetime import datetime

from app.config import settings
from app.services.vector_db import VectorDBService, SearchResult
from app.services.llm import LLMService
from app.models.domain import (
    Scenario as TestCase, Step as TestStep, TestRun as Report,
    BuildInfo, Feature, TextChunk, ChunkMetadata
)
from qdrant_client.http import models as qdrant_models

logger = logging.getLogger(__name__)


class ServiceOrchestrator:
    """
    Orchestrates interactions between different services to provide high-level functionality
    to API endpoints. This service coordinates LLM and Vector DB operations.
    """

    def __init__(self, vector_db_service: Optional[VectorDBService] = None,
                 llm_service: Optional[LLMService] = None):
        """
        Initialize the orchestrator with necessary services.

        Args:
            vector_db_service: Optional VectorDBService instance (creates new one if None)
            llm_service: Optional LLMService instance (creates new one if None)
        """
        self.vector_db = vector_db_service or VectorDBService()
        self.llm = llm_service or LLMService()

        # Ensure required vector DB collections exist
        self.vector_db.ensure_collections_exist()

    async def process_text_chunks(self, chunks: List[TextChunk]) -> List[str]:
        """
        Process and store a list of text chunks.

        Args:
            chunks: List of text chunks to process and store

        Returns:
            List of chunk IDs that were processed
        """
        logger.info("Processing %d text chunks", len(chunks))
        chunk_ids = []

        for chunk in chunks:
            # Generate embedding for the chunk
            embedding = await self.llm.generate_embedding(chunk.text)

            # Store the chunk
            self.vector_db.store_chunk(chunk, embedding)
            chunk_ids.append(chunk.id)

        return chunk_ids

    async def process_report(self, report: Report) -> str:
        """
        Process and store a full report with its test cases and steps.

        Args:
            report: The report to process and store

        Returns:
            report_id: The ID of the processed report
        """
        logger.info("Processing report: %s with %d test cases", report.name, len(report.scenarios))
        start_time = time.time()

        # Generate embedding for the report
        report_text = f"{report.name} {' '.join(report.tags)} {report.environment}"
        report_embedding = await self.llm.generate_embedding(report_text)

        # Store the report
        self.vector_db.store_report(report.id, report_embedding, report)

        # Process each test case
        for test_case in report.scenarios:
            # Generate embedding for the test case
            test_case_text = f"{test_case.name} {test_case.description or ''} {' '.join(test_case.tags)} {test_case.feature}"
            test_case_embedding = await self.llm.generate_embedding(test_case_text)

            # Store the test case
            self.vector_db.store_test_case(test_case.id, test_case_embedding, test_case, report.id)

            # Process each test step
            for step in test_case.steps:
                # Generate embedding for the step
                step_text = f"{step.keyword} {step.name} {step.error_message or ''}"
                step_embedding = await self.llm.generate_embedding(step_text)

                # Store the step
                self.vector_db.store_test_step(step.id, step_embedding, step, test_case.id)

        elapsed_time = time.time() - start_time
        logger.info("Report processing completed in %.2f seconds", elapsed_time)

        return report.id

    async def process_build_info(self, build_info: BuildInfo) -> str:
        """
        Process and store build information.

        Args:
            build_info: The build information to process and store

        Returns:
            build_id: The ID of the processed build info
        """
        logger.info("Processing build info: %s", build_info.build_number)

        # Generate embedding for the build info
        build_text = f"{build_info.build_number} {build_info.branch or ''} {build_info.commit or ''} {build_info.environment or ''}"
        build_embedding = await self.llm.generate_embedding(build_text)

        # Store the build info
        self.vector_db.store_build_info(build_info.id, build_embedding, build_info)

        return build_info.id

    async def process_feature(self, feature: Feature) -> str:
        """
        Process and store a feature.

        Args:
            feature: The feature to process and store

        Returns:
            feature_id: The ID of the processed feature
        """
        logger.info("Processing feature: %s", feature.name)

        # Generate embedding for the feature
        feature_text = f"{feature.name} {feature.description or ''} {' '.join(feature.tags)}"
        feature_embedding = await self.llm.generate_embedding(feature_text)

        # Store the feature
        self.vector_db.store_feature(feature.id, feature_embedding, feature)

        return feature.id

    async def semantic_search(self, query: str, filters: Dict[str, Any] = None, limit: int = None) -> List[
        SearchResult]:
        """
        Perform semantic search across the vector database.

        Args:
            query: The search query text
            filters: Optional filters to apply
            limit: Maximum number of results to return

        Returns:
            List of search results
        """
        if limit is None:
            limit = settings.DEFAULT_QUERY_LIMIT

        # Generate embedding for the query
        query_embedding = await self.llm.generate_embedding(query)

        # Determine which collection to search based on filters
        if filters and "type" in filters:
            artifact_type = filters["type"].lower()

            if artifact_type == "report":
                results = self.vector_db.search_reports(query_embedding, limit=limit)
            elif artifact_type == "testcase":
                report_id = filters.get("report_id")
                results = self.vector_db.search_test_cases(
                    query_embedding,
                    report_id=report_id,
                    limit=limit
                )
            elif artifact_type == "teststep":
                test_case_id = filters.get("test_case_id")
                results = self.vector_db.search_test_steps(
                    query_embedding,
                    test_case_id=test_case_id,
                    limit=limit
                )
            elif artifact_type == "feature":
                results = self.vector_db.search_features(query_embedding, limit=limit)
            elif artifact_type == "buildinfo":
                results = self.vector_db.search_build_info(query_embedding, limit=limit)
            elif artifact_type == "chunk":
                # Define any specific filter conditions for chunks
                filter_conditions = []
                for key, value in filters.items():
                    if key != "type" and value is not None:
                        filter_conditions.append(
                            qdrant_models.FieldCondition(
                                key=f"metadata.{key}",
                                match=qdrant_models.MatchValue(value=value)
                            )
                        )
                results = self.vector_db.search_chunks(
                    query_embedding,
                    filter_conditions=filter_conditions,
                    limit=limit
                )
            else:
                # Default to searching all content
                # This implementation might vary based on your needs
                report_results = self.vector_db.search_reports(query_embedding, limit=limit // 3)
                test_case_results = self.vector_db.search_test_cases(query_embedding, limit=limit // 3)
                feature_results = self.vector_db.search_features(query_embedding, limit=limit // 3)

                # Combine and sort by score
                results = sorted(
                    report_results + test_case_results + feature_results,
                    key=lambda x: x.score,
                    reverse=True
                )[:limit]
        else:
            # Default to searching all content
            report_results = self.vector_db.search_reports(query_embedding, limit=limit // 3)
            test_case_results = self.vector_db.search_test_cases(query_embedding, limit=limit // 3)
            feature_results = self.vector_db.search_features(query_embedding, limit=limit // 3)

            # Combine and sort by score
            results = sorted(
                report_results + test_case_results + feature_results,
                key=lambda x: x.score,
                reverse=True
            )[:limit]

        return results

    async def get_test_failure_insights(self, test_case_id: str) -> Dict[str, Any]:
        """
        Get insights for a specific test failure.

        Args:
            test_case_id: ID of the test case to analyze

        Returns:
            Dictionary containing analysis and insights
        """
        # Find the test case
        query_text = "test failure analysis"
        query_embedding = await self.llm.generate_embedding(query_text)

        test_case_results = self.vector_db.search_test_cases(
            query_embedding,
            limit=settings.DEFAULT_QUERY_LIMIT
        )

        # Filter results to match the exact ID
        matching_results = [r for r in test_case_results if r.id == test_case_id]

        if not matching_results:
            logger.warning("Test case with ID %s not found", test_case_id)
            return {
                "error": "Test case not found",
                "recommendations": ["Check the test case ID and try again"]
            }

        test_case_data = matching_results[0].payload

        # Only analyze failed test cases
        if test_case_data.get("status") != "FAILED":
            return {
                "message": "Test case did not fail",
                "status": test_case_data.get("status"),
                "analysis": "No failure analysis needed for non-failing tests"
            }

        # Get related test steps
        test_steps = self.vector_db.search_test_steps(
            query_embedding,
            test_case_id=test_case_id,
            limit=20
        )

        # Find similar failed test cases for context
        similar_failures_query = f"{test_case_data.get('name', '')} {test_case_data.get('error_message', '')}"
        similar_failures_embedding = await self.llm.generate_embedding(similar_failures_query)

        similar_failures = self.vector_db.search_test_cases(
            similar_failures_embedding,
            limit=5
        )

        # Filter to include only failures and exclude the current test case
        similar_failures = [
            f for f in similar_failures
            if f.id != test_case_id and f.payload.get("status") == "FAILED"
        ]

        # Prepare data for analysis
        analysis_data = {
            "test_case": test_case_data,
            "steps": [step.payload for step in test_steps],
            "similar_failures": [f.payload for f in similar_failures],
            "error_message": test_case_data.get("error_message", "No error message available")
        }

        # Analyze with LLM
        analysis_result = await self.llm.analyze_test_failure(analysis_data)

        # Enhance the analysis with historical context if available
        if similar_failures:
            historical_prompt = f"""
            Based on the test failure analysis:
            {analysis_result.get('root_cause')}

            And considering these similar failures:
            {[f.payload.get('name') + ': ' + f.payload.get('error_message', 'No error') for f in similar_failures]}

            Provide insights about potential patterns, frequency, and whether this appears to be a recurring issue.
            Focus on whether this is likely a regression, an environment issue, a flaky test, or a new bug.
            """

            historical_analysis = await self.llm.generate_text(
                prompt=historical_prompt,
                temperature=0.3,
                max_tokens=300
            )

            analysis_result["historical_context"] = historical_analysis

        return {
            "test_case": test_case_data,
            "analysis": analysis_result,
            "timestamp": datetime.now().isoformat()
        }

    async def generate_report_summary(self, report_id: str) -> str:
        """
        Generate a human-readable summary of a test report.

        Args:
            report_id: ID of the report to summarize

        Returns:
            String with a concise yet informative summary
        """
        # Find the report
        query_text = "test report summary"
        query_embedding = await self.llm.generate_embedding(query_text)

        report_results = self.vector_db.search_reports(
            query_embedding,
            limit=settings.DEFAULT_QUERY_LIMIT
        )

        # Filter results to match the exact ID
        matching_results = [r for r in report_results if r.id == report_id]

        if not matching_results:
            logger.warning("Report with ID %s not found", report_id)
            return "Report not found. Please check the report ID and try again."

        report_data = matching_results[0].payload

        # Get related test cases for this report
        test_cases = self.vector_db.search_test_cases(
            query_embedding,
            report_id=report_id,
            limit=50  # Get a good sample of test cases
        )

        # Calculate basic statistics
        total_tests = len(test_cases)
        status_counts = {}

        for tc in test_cases:
            status = tc.payload.get("status")
            status_counts[status] = status_counts.get(status, 0) + 1

        # Prepare data for the summary
        report_details = {
            "report": report_data,
            "test_cases": [tc.payload for tc in test_cases],
            "statistics": {
                "total_tests": total_tests,
                "status_counts": status_counts,
                "pass_rate": (status_counts.get("PASSED", 0) / total_tests * 100) if total_tests > 0 else 0
            }
        }

        # Generate summary with LLM
        summary = await self.llm.summarize_report(report_details)

        return summary

    async def analyze_build_trend(self, build_numbers: List[str]) -> Dict[str, Any]:
        """
        Analyze trends across multiple builds.

        Args:
            build_numbers: List of build numbers to analyze

        Returns:
            Dictionary containing trend analysis
        """
        if not build_numbers:
            return {"error": "No build numbers provided for analysis"}

        # Generate a query embedding
        query_text = "build trend analysis " + " ".join(build_numbers)
        query_embedding = await self.llm.generate_embedding(query_text)

        # Collect build information for all specified builds
        build_results = self.vector_db.search_build_info(query_embedding, limit=len(build_numbers) * 2)

        # Filter to only include the requested build numbers
        build_data = []
        for result in build_results:
            build_number = result.payload.get("build_number")
            if build_number in build_numbers:
                build_data.append(result.payload)

        if not build_data:
            return {"error": "None of the specified builds were found"}

        # Sort builds by date if available
        build_data.sort(
            key=lambda x: x.get("date", ""),
            reverse=False
        )

        # Prepare data for LLM analysis
        trend_data = {
            "builds": build_data,
            "num_builds": len(build_data),
            "build_numbers": [b.get("build_number") for b in build_data],
            "date_range": f"{build_data[0].get('date', 'N/A')} to {build_data[-1].get('date', 'N/A')}" if len(
                build_data) > 1 else "N/A"
        }

        # Generate trend analysis with LLM
        trend_prompt = f"""
        Analyze the trend across these builds:
        {json.dumps(trend_data, indent=2)}

        Focus on:
        1. Performance trends
        2. Success/failure rate changes
        3. Notable improvements or regressions
        4. Any apparent correlations with code changes or environments

        Provide a concise but thorough analysis of the build trends.
        """

        trend_analysis = await self.llm.generate_text(
            prompt=trend_prompt,
            temperature=0.4,
            max_tokens=800
        )

        return {
            "build_numbers": build_numbers,
            "builds_analyzed": len(build_data),
            "trend_analysis": trend_analysis,
            "timestamp": datetime.now().isoformat()
        }

    async def generate_answer(self, query: str, context: List[Dict] = None, max_tokens: int = 800) -> str:
        """
        Generate an answer to a query based on provided context.

        Args:
            query: The user's query
            context: List of context documents/chunks to use for answering
            max_tokens: Maximum tokens to generate

        Returns:
            Generated answer based on context
        """
        if not context:
            # If no context provided, perform a search to get relevant context
            search_results = await self.semantic_search(query, limit=5)
            context = [result.payload for result in search_results]

        # Format context for the prompt
        context_text = json.dumps(context, indent=2)

        # Create prompt for LLM
        prompt = f"""
        Use the following context to answer the question:

        CONTEXT:
        {context_text}

        QUESTION:
        {query}

        Provide a concise and accurate answer based only on the information provided in the context.
        If the context doesn't contain enough information to answer the question, acknowledge that 
        and suggest what information would be needed.
        """

        # Generate answer
        system_prompt = """
        You are a helpful assistant specialized in test analysis and reporting.
        Answer questions accurately based on the provided context.
        """

        answer = await self.llm.generate_text(
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=0.3,
            max_tokens=max_tokens
        )

        return answer