"""
Bridge service for connecting PostgreSQL database with vector database
"""
import logging
from typing import Dict, List, Optional, Any, Union
from datetime import datetime
import uuid

from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.database import (
    Project, TestRun, Scenario, Step, Feature, BuildInfo,
    TextChunk as DBTextChunk, TestStatus
)
from app.models.domain import (
    TextChunk, Report, TestStep, Feature as DomainFeature,
    BuildInfo as DomainBuildInfo, TestCase
)
from app.services.vector_db import VectorDBService

logger = logging.getLogger(__name__)


class DatabaseVectorBridgeService:
    """Service to bridge between PostgreSQL and vector database"""

    def __init__(self, vector_db_service: VectorDBService):
        """
        Initialize the bridge service.

        Args:
            vector_db_service: Vector database service for storing embeddings
        """
        self.vector_db = vector_db_service
        self.db = next(get_db())  # Get a database session

    def close(self):
        """Close database session"""
        if self.db:
            self.db.close()

    async def sync_test_run(self, test_run_id: str, embedding_service: Any) -> Dict[str, Any]:
        """
        Sync a test run from the database to the vector database.

        Args:
            test_run_id: ID of the test run to sync
            embedding_service: Service for generating embeddings

        Returns:
            Summary of sync operation
        """
        try:
            # Get test run from database
            db_test_run = self.db.query(TestRun).filter(TestRun.id == test_run_id).first()
            if not db_test_run:
                return {
                    "success": False,
                    "message": f"Test run {test_run_id} not found"
                }

            # Get project for this test run
            project = self.db.query(Project).filter(Project.id == db_test_run.project_id).first()
            project_name = project.name if project else "Unknown Project"

            # Get build info if available
            build_info = None
            if db_test_run.build_id:
                db_build_info = self.db.query(BuildInfo).filter(BuildInfo.id == db_test_run.build_id).first()
                if db_build_info:
                    build_info = DomainBuildInfo(
                        build_id=str(db_build_info.id),
                        build_number=db_build_info.build_number,
                        build_date=db_build_info.start_time,
                        branch=db_build_info.branch,
                        commit_hash=db_build_info.commit_hash,
                        build_url=db_build_info.ci_url,
                        metadata={
                            "status": db_build_info.status,
                            "author": db_build_info.author,
                            "commit_message": db_build_info.commit_message,
                            "environment": db_build_info.environment
                        }
                    )

                    # Store build info in vector DB if embedding service is provided
                    if embedding_service and build_info:
                        build_text = f"""
                        Build {build_info.build_number} for {project_name}
                        Branch: {build_info.branch}
                        Commit: {build_info.commit_hash}
                        Date: {build_info.build_date}
                        Status: {db_build_info.status}
                        Environment: {db_build_info.environment or 'Unknown'}
                        """

                        # Generate embedding for the build info
                        build_embedding = await embedding_service.embed_text(build_text)

                        # Store in vector DB
                        self.vector_db.store_build_info(
                            build_id=str(db_build_info.id),
                            embedding=build_embedding,
                            build_info=build_info
                        )

            # Get scenarios for this test run
            scenarios = self.db.query(Scenario).filter(Scenario.test_run_id == test_run_id).all()

            # Create domain models and sync with vector DB
            report = Report(
                id=test_run_id,
                name=db_test_run.name,
                timestamp=db_test_run.created_at,
                scenarios=[],  # Will be populated below
                metadata={
                    "project_id": db_test_run.project_id,
                    "project_name": project_name,
                    "build_id": db_test_run.build_id,
                    "status": db_test_run.status.value if db_test_run.status else None,
                    "environment": db_test_run.environment,
                    "branch": db_test_run.branch,
                    "commit_hash": db_test_run.commit_hash,
                    "success_rate": db_test_run.success_rate,
                    "total_tests": db_test_run.total_tests,
                    "passed_tests": db_test_run.passed_tests,
                    "failed_tests": db_test_run.failed_tests,
                    "skipped_tests": db_test_run.skipped_tests
                }
            )

            # Store test run in vector DB if embedding service is provided
            if embedding_service:
                report_text = f"""
                Test Run: {db_test_run.name}
                Project: {project_name}
                Date: {db_test_run.created_at}
                Status: {db_test_run.status.value if db_test_run.status else 'Unknown'}
                Environment: {db_test_run.environment or 'Unknown'}
                Branch: {db_test_run.branch or 'Unknown'}
                Success Rate: {db_test_run.success_rate or 0}%
                Total Tests: {db_test_run.total_tests or 0}
                Passed: {db_test_run.passed_tests or 0}
                Failed: {db_test_run.failed_tests or 0}
                Skipped: {db_test_run.skipped_tests or 0}
                """

                # Generate embedding for the report
                report_embedding = await embedding_service.embed_text(report_text)

                # Store in vector DB
                self.vector_db.store_report(
                    report_id=test_run_id,
                    embedding=report_embedding,
                    report=report
                )

            # Process scenarios
            scenario_count = 0
            step_count = 0
            feature_ids = set()

            for scenario in scenarios:
                # Get feature if available
                feature = None
                if scenario.feature_id:
                    db_feature = self.db.query(Feature).filter(Feature.id == scenario.feature_id).first()
                    if db_feature:
                        feature = DomainFeature(
                            id=str(db_feature.id),
                            name=db_feature.name,
                            description=db_feature.description or "",
                            file_path=db_feature.file_path or "",
                            scenarios=[],  # Not populating to avoid circular reference
                            tags=db_feature.tags or []
                        )

                        # Store feature in vector DB if not already processed and embedding service is provided
                        if str(db_feature.id) not in feature_ids and embedding_service:
                            feature_ids.add(str(db_feature.id))
                            feature_text = f"""
                            Feature: {db_feature.name}
                            Description: {db_feature.description or 'No description'}
                            Project: {project_name}
                            File: {db_feature.file_path or 'Unknown'}
                            Tags: {', '.join(db_feature.tags) if db_feature.tags else 'None'}
                            """

                            # Generate embedding for the feature
                            feature_embedding = await embedding_service.embed_text(feature_text)

                            # Store in vector DB
                            self.vector_db.store_feature(
                                feature_id=str(db_feature.id),
                                embedding=feature_embedding,
                                feature=feature
                            )

                # Get steps for this scenario
                steps = self.db.query(Step).filter(Step.scenario_id == scenario.id).order_by(Step.order).all()

                # Create domain model steps
                domain_steps = []
                for step in steps:
                    domain_step = TestStep(
                        name=step.name,
                        status=self._convert_status(step.status),
                        duration=step.duration or 0,
                        error_message=step.error_message,
                        keyword="",  # Not available in DB model
                        location=""  # Not available in DB model
                    )
                    domain_steps.append(domain_step)

                    # Only store steps for failed scenarios to save space
                    if scenario.status == TestStatus.FAILED and embedding_service:
                        step_id = f"{scenario.id}_{step.id}"
                        step_text = f"""
                        Step: {step.name}
                        Status: {step.status.value if step.status else 'Unknown'}
                        Error: {step.error_message or 'None'}
                        """

                        # Generate embedding for the step
                        step_embedding = await embedding_service.embed_text(step_text)

                        # Store in vector DB
                        self.vector_db.store_test_step(
                            step_id=step_id,
                            embedding=step_embedding,
                            step=domain_step,
                            test_case_id=str(scenario.id)
                        )
                        step_count += 1

                # Create domain model scenario (test case)
                test_case = TestCase(
                    id=str(scenario.id),
                    name=scenario.name,
                    description=scenario.description or "",
                    status=self._convert_status(scenario.status),
                    steps=domain_steps,
                    tags=[]  # Tags not available in DB model
                )

                # Store test case in vector DB if embedding service is provided
                if embedding_service:
                    # Create text representation of steps
                    steps_text = "\n".join([
                        f"Step {i + 1}: {step.name} - {step.status.value if step.status else 'Unknown'}"
                        for i, step in enumerate(steps)
                    ])

                    scenario_text = f"""
                    Scenario: {scenario.name}
                    Description: {scenario.description or 'No description'}
                    Status: {scenario.status.value if scenario.status else 'Unknown'}
                    Feature: {feature.name if feature else 'Unknown'}
                    Error: {scenario.error_message or 'None'}

                    Steps:
                    {steps_text}
                    """

                    # Generate embedding for the scenario
                    scenario_embedding = await embedding_service.embed_text(scenario_text)

                    # Store in vector DB
                    self.vector_db.store_test_case(
                        test_case_id=str(scenario.id),
                        embedding=scenario_embedding,
                        test_case=test_case,
                        report_id=test_run_id
                    )
                    scenario_count += 1

                # Add to report
                report.scenarios.append(test_case)

            return {
                "success": True,
                "test_run_id": test_run_id,
                "synced_scenarios": scenario_count,
                "synced_steps": step_count,
                "synced_features": len(feature_ids),
                "message": f"Successfully synced test run {test_run_id} to vector database"
            }

        except Exception as e:
            logger.error(f"Failed to sync test run {test_run_id}: {str(e)}", exc_info=True)
            return {
                "success": False,
                "message": f"Failed to sync test run: {str(e)}"
            }

    async def sync_text_chunks(self, embedding_service: Any) -> Dict[str, Any]:
        """
        Sync text chunks from the database to the vector database.

        Args:
            embedding_service: Service for generating embeddings

        Returns:
            Summary of sync operation
        """
        try:
            # Get text chunks from database that don't have a vector ID yet
            chunks = self.db.query(DBTextChunk).filter(
                DBTextChunk.quadrant_vector_id.is_(None)
            ).limit(100).all()  # Process in batches

            if not chunks:
                return {
                    "success": True,
                    "message": "No new text chunks to sync",
                    "synced_chunks": 0
                }

            synced_count = 0
            for db_chunk in chunks:
                # Create domain model
                domain_chunk = TextChunk(
                    id=str(db_chunk.id),
                    text=db_chunk.text,
                    metadata=db_chunk.meta_data or {},
                    chunk_size=len(db_chunk.text)
                )

                # Generate embedding
                embedding = await embedding_service.embed_text(db_chunk.text)

                # Store in vector DB
                self.vector_db.store_chunk(
                    text_chunk=domain_chunk,
                    embedding=embedding
                )

                # Update database with vector ID
                db_chunk.quadrant_vector_id = str(db_chunk.id)
                self.db.commit()

                synced_count += 1

            return {
                "success": True,
                "message": f"Successfully synced {synced_count} text chunks",
                "synced_chunks": synced_count
            }

        except Exception as e:
            logger.error(f"Failed to sync text chunks: {str(e)}", exc_info=True)
            if self.db:
                self.db.rollback()
            return {
                "success": False,
                "message": f"Failed to sync text chunks: {str(e)}"
            }

    def _convert_status(self, db_status: TestStatus) -> str:
        """Convert DB TestStatus to domain status string"""
        if db_status is None:
            return "undefined"

        status_map = {
            TestStatus.PASSED: "passed",
            TestStatus.FAILED: "failed",
            TestStatus.SKIPPED: "skipped",
            TestStatus.PENDING: "pending",
            TestStatus.RUNNING: "running",
            TestStatus.ERROR: "failed"
        }

        return status_map.get(db_status, "undefined")
