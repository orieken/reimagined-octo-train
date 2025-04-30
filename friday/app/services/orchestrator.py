import logging
import json
from typing import List, Optional, Any, Dict
from uuid import uuid4, UUID

from app.models.domain import Feature, Scenario, Step, TestRun, TestStatus
from app.models.metadata import ReportMetadata
from app.services import datetime_service as dt
from app.services.llm import LLMService
from app.services.vector_db import VectorDBService
from app.services.postgres_db import PostgresDBService
from app.services.cucumber_transformer import transform_cucumber_json_to_internal_model, calculate_overall_status

from app.models.database import Project
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class TestDataRepository:
    def __init__(self, pg_service: Optional[PostgresDBService] = None, vector_db: Optional[VectorDBService] = None):
        self.pg_service = pg_service or PostgresDBService()
        self.vector_db = vector_db or VectorDBService()

    async def store_report(
        self,
        metadata: ReportMetadata,
        report: TestRun,
        features: List[Feature],
        report_embedding: List[float],
        session: AsyncSession,
    ) -> str:
        logger.info(f"Storing report for project={metadata.project} with {len(report.scenarios)} scenarios")

        test_run_id = await self.pg_service.save_test_run(metadata, metadata.project_id, report, features, session=session)
        # Convert the Pydantic model to a dictionary
        metadata_dict = metadata.model_dump() if hasattr(metadata, 'model_dump') else metadata.dict()

        self.vector_db.store_test_run_embedding(test_run_id, report_embedding, metadata_dict)

        return test_run_id


class ServiceOrchestrator:
    def __init__(
        self,
        llm_service: Optional[LLMService] = None,
        vector_db_service: Optional[VectorDBService] = None,
        pg_service: Optional[PostgresDBService] = None,
    ):
        self.llm = llm_service or LLMService()
        self.vector_db = vector_db_service or VectorDBService()
        self.pg_service = pg_service or PostgresDBService()
        self.repository = TestDataRepository(pg_service=self.pg_service, vector_db=self.vector_db)

    async def ensure_project(self, session: AsyncSession, project_name: str) -> UUID:
        result = await session.execute(select(Project).where(Project.name == project_name))
        project = result.scalar_one_or_none()

        if project:
            return project.id
        else:
            new_project = Project(
                id=uuid4(),
                name=project_name,
                created_at=dt.now_utc(),
                updated_at=dt.now_utc(),
                active=True,
                meta_data={}
            )
            session.add(new_project)
            await session.flush()
            return new_project.id

    async def process_report(self, metadata: ReportMetadata, raw_features: List[dict]) -> None:
        logger.debug("[DEBUG] Metadata received:\n%s", json.dumps(metadata.model_dump(), indent=2, default=str))

        async with self.pg_service.session() as session:
            async with session.begin():
                project_id = await self.ensure_project(session, metadata.project)
                metadata.project_id = project_id

                logger.debug("[DEBUG] Raw features incoming: %d", len(raw_features))

                features = transform_cucumber_json_to_internal_model(raw_features, project_id=project_id)
                logger.debug("[DEBUG] Parsed features: %d", len(features))

                test_run = self._create_test_run_from_metadata(metadata, features)
                logger.debug("[DEBUG] TestRun created with %d scenarios", len(test_run.scenarios))

                embedding = await self.llm.embed_text(test_run.name or metadata.test_run_id)

                # Convert metadata to dict
                metadata_dict = metadata.model_dump() if hasattr(metadata, 'model_dump') else metadata.dict()

                test_run_id = await self.pg_service.save_test_run(
                    metadata=metadata,
                    project_id=project_id,
                    test_run=test_run,
                    features=features,
                    session=session,
                )

                # No await here - synchronous call
                self.vector_db.store_test_run_embedding(test_run_id, embedding, metadata_dict)

                for scenario in test_run.scenarios:
                    # Create appropriate metadata for scenario
                    scenario_metadata = {
                        "project_id": str(project_id),
                        "test_run_id": str(test_run_id),
                        "name": scenario.name,
                        "status": scenario.status
                    }

                    # Get embedding for scenario
                    scenario_embedding = await self.llm.embed_text(scenario.name or "")

                    # Store in vector DB - no await
                    self.vector_db.store_scenario_embedding(
                        scenario.id,
                        scenario_embedding,
                        scenario_metadata
                    )

                    for step in scenario.steps:
                        # Create appropriate metadata for step
                        step_metadata = {
                            "project_id": str(project_id),
                            "scenario_id": str(scenario.id),
                            "name": step.name,
                            "status": step.status
                        }

                        # Get embedding for step
                        step_embedding = await self.llm.embed_text(step.name or "")

                        # Store in vector DB - no await
                        self.vector_db.store_step_embedding(
                            step.id,
                            step_embedding,
                            step_metadata
                        )

            logger.info(f"Processed report for project={metadata.project}")

    def _create_test_run_from_metadata(self, metadata: ReportMetadata, features: List[Feature]) -> TestRun:
        all_scenarios = [scenario for feature in features for scenario in feature.scenarios]
        passed = sum(1 for s in all_scenarios if s.status == TestStatus.PASSED)
        failed = sum(1 for s in all_scenarios if s.status == TestStatus.FAILED)
        skipped = sum(1 for s in all_scenarios if s.status == TestStatus.SKIPPED)
        total = len(all_scenarios) or 1
        success_rate = passed / total

        return TestRun(
            name=metadata.test_run_id,
            external_id=str(uuid4()),
            status=calculate_overall_status(all_scenarios),
            environment=metadata.environment or "unknown",
            timestamp=dt.parse_iso_datetime_to_utc(metadata.timestamp),
            branch=metadata.branch,
            commit_hash=metadata.commit,
            scenarios=all_scenarios,
            meta_data=metadata.model_dump(exclude_unset=True),
            success_rate=success_rate,
            total_tests=total,
            passed_tests=passed,
            failed_tests=failed,
            skipped_tests=skipped,
            error_tests=failed + skipped,
        )

    async def ping_services(self) -> bool:
        logger.info("🔎 Pinging dependent services...")

        if not await self.vector_db.ping():
            raise RuntimeError("VectorDBService is not reachable.")

        if not await self.pg_service.ping():
            raise RuntimeError("PostgresDBService is not reachable.")

        try:
            dummy_text = "healthcheck"
            embedding = await self.llm.embed_text(dummy_text)
            if not embedding or not isinstance(embedding, list):
                raise RuntimeError("Embedding model returned invalid response.")
        except Exception as e:
            raise RuntimeError(f"LLMService failed: {e}")

        logger.info("✅ All dependent services healthy.")
        return True