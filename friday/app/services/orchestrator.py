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
from app.services.postgres_db import PostgresDBService
from app.models import (
    Scenario as TestCase, Step as TestStep, TestRun as Report,
    BuildInfo, Feature, TextChunk, ChunkMetadata, TestStatus
)


logger = logging.getLogger(__name__)


class TestDataRepository:
    """
    Repository that handles synchronized storage and retrieval of test data
    across both PostgreSQL and Qdrant vector database.
    """

    def __init__(self, pg_service: PostgresDBService, vector_service: VectorDBService):
        """
        Initialize with both database services.

        Args:
            pg_service: PostgreSQL database service
            vector_service: Qdrant vector database service
        """
        self.pg_service = pg_service
        self.vector_service = vector_service

    async def store_report(self, report: Report, embedding: List[float]) -> str:
        """
        Store a report in both PostgreSQL and Qdrant databases with robust error handling.

        Args:
            report: The report to store
            embedding: Vector embedding for the report

        Returns:
            report_id: The ID of the stored report
        """
        logger.info(f"Storing report {report.id} in both databases")

        try:
            # 1. Store in PostgreSQL first and get the numeric ID
            pg_report_id = await self.pg_service.store_report(report)

            # Verify the PostgreSQL report ID was created successfully
            if not pg_report_id:
                logger.error(f"Failed to store report {report.id} in PostgreSQL")
                raise ValueError("Could not store report in PostgreSQL")

            # 2. Attach PostgreSQL ID to the report's metadata for vector database reference
            report_with_ref = report.copy() if hasattr(report, 'copy') else report
            if not hasattr(report_with_ref, 'metadata'):
                report_with_ref.metadata = {}
            report_with_ref.metadata['pg_id'] = pg_report_id

            # 3. Store each test case in PostgreSQL
            for test_case in report.scenarios:
                try:
                    pg_test_case_id = await self.pg_service.store_test_case(test_case, pg_report_id)

                    # Store tags for the test case
                    if test_case.tags:
                        await self.pg_service.store_scenario_tags(pg_test_case_id, test_case.tags)

                except Exception as case_store_error:
                    logger.error(f"Error storing test case for report {report.id}: {str(case_store_error)}")
                    # Continue processing other test cases even if one fails
                    continue

            # 4. Store in Qdrant vector database
            vector_id = self.vector_service.store_report(report.id, embedding, report_with_ref)

            # 5. Update PostgreSQL with reference to vector ID
            await self.pg_service.update_vector_reference(pg_report_id, vector_id)

            logger.info(f"Successfully stored report {report.id} in both databases")
            return report.id

        except Exception as e:
            logger.error(f"Comprehensive error storing report in databases: {str(e)}", exc_info=True)
            raise

    async def store_test_case(self, test_case: TestCase, report_id: str, embedding: List[float]) -> str:
        """
        Store a test case in both PostgreSQL and Qdrant databases with enhanced error handling.

        Args:
            test_case: The test case to store
            report_id: The ID of the parent report
            embedding: Vector embedding for the test case

        Returns:
            test_case_id: The ID of the stored test case
        """
        logger.info(f"Storing test case {test_case.id} in both databases")

        try:
            # First, attempt to store the test case
            try:
                pg_test_case_id = await self.pg_service.store_test_case(test_case, report_id)
            except ValueError as ve:
                # If report not found, create a placeholder report
                logger.warning(f"Report {report_id} not found. Creating placeholder report.")

                # Create a placeholder report with a valid status
                placeholder_report = Report(
                    id=report_id,
                    name=f"Placeholder Report for {test_case.name}",
                    status=TestStatus.PENDING.value,  # Use a valid enum value
                    timestamp=datetime.now().isoformat(),
                    duration=0,
                    environment="unknown",
                    scenarios=[],
                    metadata={
                        "source": "placeholder",
                        "original_report_id": report_id
                    }
                )

                # Store the placeholder report
                pg_report_id = await self.pg_service.store_report(placeholder_report)

                # Now retry storing the test case with the new report ID
                pg_test_case_id = await self.pg_service.store_test_case(test_case, pg_report_id)

            # Store tags for the test case
            if test_case.tags:
                await self.pg_service.store_scenario_tags(pg_test_case_id, test_case.tags)

            # Create a new test case with additional metadata
            test_case_with_metadata = test_case.model_copy(
                update={
                    "metadata": {
                        'pg_id': pg_test_case_id,
                        'original_report_id': report_id,
                        'vector_storage_info': {
                            'embedding_used': len(embedding),
                            'stored_at': datetime.now().isoformat()
                        }
                    }
                }
            )

            # Store in vector database
            vector_id = self.vector_service.store_test_case(test_case.id, embedding, test_case_with_metadata, report_id)

            # Update PostgreSQL with reference to vector ID
            await self.pg_service.update_test_case_vector_reference(pg_test_case_id, vector_id)

            logger.info(f"Successfully stored test case {test_case.id}")
            return test_case.id

        except Exception as e:
            logger.error(f"Comprehensive error storing test case in databases: {str(e)}", exc_info=True)

            # Additional error context
            error_context = {
                "test_case_id": test_case.id,
                "report_id": report_id,
                "test_case_name": test_case.name,
                "test_case_feature": test_case.feature
            }
            logger.error(f"Error context: {error_context}")

            raise

    async def store_test_step(self, step: TestStep, test_case_id: str, embedding: List[float]) -> str:
        """
        Store a test step in both PostgreSQL and Qdrant databases with enhanced error handling.

        Args:
            step: The test step to store
            test_case_id: The ID of the parent test case
            embedding: Vector embedding for the step

        Returns:
            step_id: The ID of the stored step
        """
        logger.info(f"Storing test step {step.id} in both databases")

        try:
            # First, attempt to store the test step
            try:
                pg_step_id = await self.pg_service.store_test_step(step, test_case_id)
            except ValueError as ve:
                # If scenario not found, log and raise
                logger.warning(f"Scenario {test_case_id} not found: {str(ve)}")
                raise

            # Create a new step with additional metadata
            step_with_metadata = step.model_copy(
                update={
                    "metadata": {
                        'pg_id': pg_step_id,
                        'test_case_id': test_case_id,
                        'vector_storage_info': {
                            'embedding_used': len(embedding),
                            'stored_at': datetime.now().isoformat()
                        }
                    }
                }
            )

            try:
                # Store in vector database
                vector_id = self.vector_service.store_test_step(step.id, embedding, step_with_metadata, test_case_id)

                # Attempt to update vector reference, but catch and log any errors
                try:
                    await self.pg_service.update_step_vector_reference(pg_step_id, vector_id)
                except Exception as ref_error:
                    logger.warning(f"Could not update step vector reference: {str(ref_error)}")
                    # Optionally, you could add more sophisticated error handling here
                    # For now, we'll continue with the process

            except Exception as vector_error:
                logger.error(f"Error storing test step in vector database: {str(vector_error)}")
                # Decide how to handle this: re-raise, log, or take alternative action
                raise

            logger.info(f"Successfully stored test step {step.id}")
            return step.id

        except Exception as e:
            logger.error(f"Error storing test step in databases: {str(e)}", exc_info=True)

            # Additional error context
            error_context = {
                "step_id": step.id,
                "test_case_id": test_case_id,
                "step_name": step.name,
                "step_keyword": step.keyword
            }
            logger.error(f"Error context: {error_context}")

            raise

    async def store_build_info(self, build_info: BuildInfo, embedding: List[float]) -> str:
        """
        Store build info in both PostgreSQL and Qdrant databases.

        Args:
            build_info: The build info to store
            embedding: Vector embedding for the build info

        Returns:
            build_id: The ID of the stored build info
        """
        logger.info(f"Storing build info {build_info.id} in both databases")

        try:
            # First, store in PostgreSQL
            pg_build_id = await self.pg_service.store_build_info(build_info)

            # Then store in Qdrant with reference to PostgreSQL ID
            build_info_with_ref = build_info.copy() if hasattr(build_info, 'copy') else build_info
            if not hasattr(build_info_with_ref, 'metadata'):
                build_info_with_ref.metadata = {}
            build_info_with_ref.metadata['pg_id'] = pg_build_id

            # Store in vector database
            vector_id = self.vector_service.store_build_info(build_info.id, embedding, build_info_with_ref)

            # Update PostgreSQL with reference to vector ID
            await self.pg_service.update_build_vector_reference(pg_build_id, vector_id)

            return build_info.id

        except Exception as e:
            logger.error(f"Error storing build info in databases: {str(e)}", exc_info=True)
            raise

    async def store_feature(self, feature: Feature, embedding: List[float]) -> str:
        """
        Store a feature in both PostgreSQL and Qdrant databases.

        Args:
            feature: The feature to store
            embedding: Vector embedding for the feature

        Returns:
            feature_id: The ID of the stored feature
        """
        logger.info(f"Storing feature {feature.id} in both databases")

        try:
            # First, store in PostgreSQL
            pg_feature_id = await self.pg_service.store_feature(feature)

            # Then store in Qdrant with reference to PostgreSQL ID
            feature_with_ref = feature.copy() if hasattr(feature, 'copy') else feature
            if not hasattr(feature_with_ref, 'metadata'):
                feature_with_ref.metadata = {}
            feature_with_ref.metadata['pg_id'] = pg_feature_id

            # Store in vector database
            vector_id = self.vector_service.store_feature(feature.id, embedding, feature_with_ref)

            # Update PostgreSQL with reference to vector ID
            await self.pg_service.update_feature_vector_reference(pg_feature_id, vector_id)

            return feature.id

        except Exception as e:
            logger.error(f"Error storing feature in databases: {str(e)}", exc_info=True)
            raise

    async def semantic_search(self, query_embedding: List[float], filters: Dict[str, Any] = None, limit: int = None) -> \
    List[SearchResult]:
        """
        Perform semantic search using the vector database.

        Args:
            query_embedding: Vector embedding for the query
            filters: Optional filters to apply
            limit: Maximum number of results to return

        Returns:
            List of search results
        """
        if limit is None:
            limit = settings.DEFAULT_QUERY_LIMIT

        artifact_type = filters.get("type", "").lower() if filters else ""

        if artifact_type == "report":
            return self.vector_service.search_reports(query_embedding, limit=limit)
        elif artifact_type == "testcase":
            report_id = filters.get("report_id")
            return self.vector_service.search_test_cases(query_embedding, report_id=report_id, limit=limit)
        elif artifact_type == "teststep":
            test_case_id = filters.get("test_case_id")
            return self.vector_service.search_test_steps(query_embedding, test_case_id=test_case_id, limit=limit)
        elif artifact_type == "feature":
            return self.vector_service.search_features(query_embedding, limit=limit)
        elif artifact_type == "buildinfo":
            return self.vector_service.search_build_info(query_embedding, limit=limit)
        else:
            # Default to searching across multiple collections
            report_results = self.vector_service.search_reports(query_embedding, limit=limit // 3)
            test_case_results = self.vector_service.search_test_cases(query_embedding, limit=limit // 3)
            feature_results = self.vector_service.search_features(query_embedding, limit=limit // 3)

            # Combine and sort results
            results = sorted(
                report_results + test_case_results + feature_results,
                key=lambda x: x.score,
                reverse=True
            )[:limit]

            return results

class ServiceOrchestrator:
    """
    Orchestrates interactions between different services to provide high-level functionality
    to API endpoints. This service coordinates LLM, Vector DB, and PostgreSQL operations.
    """

    def __init__(self, vector_db_service: Optional[VectorDBService] = None,
                 llm_service: Optional[LLMService] = None,
                 pg_service: Optional[PostgresDBService] = None):
        """
        Initialize the orchestrator with necessary services.

        Args:
            vector_db_service: Optional VectorDBService instance (creates new one if None)
            llm_service: Optional LLMService instance (creates new one if None)
            pg_service: Optional PostgresDBService instance (creates new one if None)
        """
        self.vector_db = vector_db_service or VectorDBService()
        self.llm = llm_service or LLMService()
        self.pg_service = pg_service or PostgresDBService()

        # Create a repository that handles synchronized storage
        self.repository = TestDataRepository(self.pg_service, self.vector_db)

        # Ensure required vector DB collections exist
        self.vector_db.ensure_collections_exist()

        # Task tracking for async operations
        self.tasks = {}

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

            # Store the chunk - direct storage in vector DB is fine for simple chunks
            self.vector_db.store_chunk(chunk, embedding)
            chunk_ids.append(chunk.id)

        return chunk_ids

    async def process_report(self, report: Report, task_id: str = None) -> str:
        """
        Process and store a full report with its test cases and steps.

        Args:
            report: The report to process and store
            task_id: Optional task ID for tracking progress

        Returns:
            report_id: The ID of the processed report
        """
        logger.info("Processing report: %s with %d test cases", report.name, len(report.scenarios))
        start_time = time.time()

        # Update task status if we're tracking this task
        if task_id:
            self.tasks[task_id] = {
                "status": "processing",
                "progress": 0.0,
                "message": f"Started processing report {report.name}"
            }

        try:
            # Generate embedding for the report
            report_text = f"{report.name} {' '.join(report.tags or [])} {report.environment}"
            report_embedding = await self.llm.generate_embedding(report_text)

            # Store the report using the repository (handles both databases)
            await self.repository.store_report(report, report_embedding)

            # Update task progress
            if task_id:
                self.tasks[task_id]["progress"] = 0.2
                self.tasks[task_id]["message"] = f"Stored report, processing {len(report.scenarios)} test cases"

            # Process each test case
            for i, test_case in enumerate(report.scenarios):
                # Generate embedding for the test case
                test_case_text = f"{test_case.name} {test_case.description or ''} {' '.join(test_case.tags or [])} {test_case.feature}"
                test_case_embedding = await self.llm.generate_embedding(test_case_text)

                # Store the test case using the repository
                await self.repository.store_test_case(test_case, report.id, test_case_embedding)

                # Update task progress
                if task_id:
                    progress = 0.2 + (0.6 * ((i + 1) / len(report.scenarios)))
                    self.tasks[task_id]["progress"] = progress
                    self.tasks[task_id]["message"] = f"Processed {i + 1}/{len(report.scenarios)} test cases"

                # Process each test step
                for step in test_case.steps:
                    # Generate embedding for the step
                    step_text = f"{step.keyword} {step.name} {step.error_message or ''}"
                    step_embedding = await self.llm.generate_embedding(step_text)

                    # Store the step using the repository
                    await self.repository.store_test_step(step, test_case.id, step_embedding)

            elapsed_time = time.time() - start_time
            logger.info("Report processing completed in %.2f seconds", elapsed_time)

            # Update task status
            if task_id:
                self.tasks[task_id] = {
                    "status": "completed",
                    "progress": 1.0,
                    "message": f"Report processing completed in {elapsed_time:.2f} seconds"
                }

            return report.id

        except Exception as e:
            logger.error(f"Error processing report: {str(e)}", exc_info=True)

            # Update task status on error
            if task_id:
                self.tasks[task_id] = {
                    "status": "failed",
                    "progress": 0.0,
                    "message": f"Error processing report: {str(e)}"
                }

            raise

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

            # Store the build info using the repository
            return await self.repository.store_build_info(build_info, build_embedding)

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
            feature_text = f"{feature.name} {feature.description or ''} {' '.join(feature.tags or [])}"
            feature_embedding = await self.llm.generate_embedding(feature_text)

            # Store the feature using the repository
            return await self.repository.store_feature(feature, feature_embedding)

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

            # Use the repository to perform the search
            return await self.repository.semantic_search(query_embedding, filters, limit)

        async def get_task_status(self, task_id: str) -> Dict[str, Any]:
            """
            Get the status of an asynchronous processing task.

            Args:
                task_id: ID of the task to check

            Returns:
                Dictionary with status information
            """
            return self.tasks.get(task_id, None)

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