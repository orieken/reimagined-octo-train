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

from app.models.database import Project, Scenario as DBScenario, Feature as DBFeature, TestRun as DBTestRun, ScenarioTag as DBScenarioTag

from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.responses import ResultsResponse

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

    async def get_latest_test_runs(self,
                                   environment: Optional[str] = None,
                                   project_id: Optional[UUID] = None) -> Dict[str, Any]:
        """Get the latest test run for each active project."""
        # Import the database models, not the domain models

        results = {
            "total_scenarios": 0,
            "passed_scenarios": 0,
            "failed_scenarios": 0,
            "skipped_scenarios": 0,
            "pass_rate": 0.0,
            "features": [],
            "tags": {},
            "projects": []
        }

        try:
            async with self.pg_service.session() as session:
                # Step 1: Get all active projects
                projects_query = select(Project).where(Project.active == True)
                if project_id:
                    projects_query = projects_query.where(Project.id == project_id)

                result = await session.execute(projects_query)
                projects = result.scalars().all()

                if not projects:
                    logger.info("No active projects found")
                    return results

                # Store project info
                results["projects"] = [
                    {"id": str(p.id), "name": p.name}
                    for p in projects
                ]

                logger.info(f"Found {len(projects)} active projects")

                # Step 2: For each project, get the latest test run
                test_run_ids = []
                for project in projects:
                    # Use DBTestRun instead of TestRun
                    latest_run_query = select(DBTestRun).where(
                        DBTestRun.project_id == project.id
                    )

                    if environment:
                        latest_run_query = latest_run_query.where(DBTestRun.environment == environment)

                    latest_run_query = latest_run_query.order_by(desc(DBTestRun.created_at)).limit(1)

                    result = await session.execute(latest_run_query)
                    latest_run = result.scalar_one_or_none()

                    if latest_run:
                        test_run_ids.append(latest_run.id)

                if not test_run_ids:
                    logger.info("No test runs found for the active projects")
                    return results

                logger.info(f"Found {len(test_run_ids)} latest test runs")

                # Step 3: Get all scenarios from these test runs
                # Use DBScenario instead of Scenario
                scenarios_query = select(DBScenario).where(
                    DBScenario.test_run_id.in_(test_run_ids)
                )
                result = await session.execute(scenarios_query)
                scenarios = result.scalars().all()

                if not scenarios:
                    logger.info("No scenarios found in the latest test runs")
                    return results

                logger.info(f"Found {len(scenarios)} scenarios")

                # Log status counts for debugging
                status_counts = {}
                for scenario in scenarios:
                    status = str(scenario.status)
                    if status not in status_counts:
                        status_counts[status] = 0
                    status_counts[status] += 1

                logger.info(f"Scenario status counts: {status_counts}")

                # Calculate statistics
                total = len(scenarios)
                # Check for both enum values and string representations
                passed = sum(
                    1 for s in scenarios if s.status == TestStatus.PASSED or str(s.status) == 'TestStatus.PASSED')
                failed = sum(
                    1 for s in scenarios if s.status == TestStatus.FAILED or str(s.status) == 'TestStatus.FAILED')
                skipped = sum(
                    1 for s in scenarios if s.status == TestStatus.SKIPPED or str(s.status) == 'TestStatus.SKIPPED')

                # Step 4: Get features statistics
                feature_stats = {}
                for scenario in scenarios:
                    if scenario.feature_id:
                        # Use DBFeature instead of Feature
                        feature_query = select(DBFeature).where(
                            DBFeature.id == scenario.feature_id
                        )
                        result = await session.execute(feature_query)
                        feature = result.scalar_one_or_none()

                        if feature:
                            feature_name = feature.name or "Unknown"
                            if feature_name not in feature_stats:
                                feature_stats[feature_name] = {
                                    "name": feature_name,
                                    "passed_scenarios": 0,
                                    "failed_scenarios": 0,
                                    "skipped_scenarios": 0
                                }

                            # Updated to check string representation
                            if scenario.status == TestStatus.PASSED or str(scenario.status) == 'TestStatus.PASSED':
                                feature_stats[feature_name]["passed_scenarios"] += 1
                            elif scenario.status == TestStatus.FAILED or str(scenario.status) == 'TestStatus.FAILED':
                                feature_stats[feature_name]["failed_scenarios"] += 1
                            elif scenario.status == TestStatus.SKIPPED or str(scenario.status) == 'TestStatus.SKIPPED':
                                feature_stats[feature_name]["skipped_scenarios"] += 1

                # Recalculate totals based on feature stats to ensure consistency
                total_passed = sum(f["passed_scenarios"] for f in feature_stats.values())
                total_failed = sum(f["failed_scenarios"] for f in feature_stats.values())
                total_skipped = sum(f["skipped_scenarios"] for f in feature_stats.values())
                total_scenarios = total_passed + total_failed + total_skipped

                results["total_scenarios"] = total_scenarios
                results["passed_scenarios"] = total_passed
                results["failed_scenarios"] = total_failed
                results["skipped_scenarios"] = total_skipped
                results["pass_rate"] = total_passed / total_scenarios if total_scenarios > 0 else 0
                results["features"] = list(feature_stats.values())

                # Step 5: Get tag statistics
                scenario_ids = [s.id for s in scenarios]

                logger.info(f"Looking for tags for scenario IDs: {scenario_ids}")

                if scenario_ids:
                    logger.info(f"Looking for tags for scenario IDs: {scenario_ids[:5]}...")

                    # Use DBScenarioTag instead of ScenarioTag
                    tags_query = select(DBScenarioTag).where(
                        DBScenarioTag.scenario_id.in_(scenario_ids)
                    )

                    # Log the SQL query
                    logger.info(f"Tags query: {tags_query}")

                    result = await session.execute(tags_query)
                    scenario_tags = result.scalars().all()

                    logger.info(f"Found {len(scenario_tags)} tags for scenarios")

                    # If no tags found, check if any tags exist at all
                    if not scenario_tags:
                        all_tags_query = select(DBScenarioTag)
                        all_tags_result = await session.execute(all_tags_query)
                        all_tags = all_tags_result.scalars().all()
                        logger.info(f"Total tags in database: {len(all_tags)}")

                    tag_stats = {}
                    for tag_obj in scenario_tags:
                        tag = tag_obj.tag
                        if tag not in tag_stats:
                            tag_stats[tag] = {
                                "count": 0,
                                "passed": 0,
                                "failed": 0,
                                "skipped": 0,
                                "pass_rate": 0.0
                            }

                        tag_stats[tag]["count"] += 1

                        # Find the scenario to get its status
                        scenario_id = tag_obj.scenario_id
                        for scenario in scenarios:
                            if scenario.id == scenario_id:
                                # Updated to check string representation
                                if scenario.status == TestStatus.PASSED or str(scenario.status) == 'TestStatus.PASSED':
                                    tag_stats[tag]["passed"] += 1
                                elif scenario.status == TestStatus.FAILED or str(
                                        scenario.status) == 'TestStatus.FAILED':
                                    tag_stats[tag]["failed"] += 1
                                elif scenario.status == TestStatus.SKIPPED or str(
                                        scenario.status) == 'TestStatus.SKIPPED':
                                    tag_stats[tag]["skipped"] += 1
                                break

                    # Calculate pass rates
                    for tag, stats in tag_stats.items():
                        stats["pass_rate"] = round(stats["passed"] / stats["count"], 4) if stats["count"] else 0

                    results["tags"] = tag_stats

                # Step 6: Get latest updated timestamp
                latest_timestamp = dt.now_utc()
                if test_run_ids:
                    # Use DBTestRun instead of TestRun
                    test_runs_query = select(DBTestRun).where(
                        DBTestRun.id.in_(test_run_ids)
                    )
                    result = await session.execute(test_runs_query)
                    test_runs = result.scalars().all()

                    if test_runs:
                        latest_timestamp = max(
                            run.updated_at or run.created_at
                            for run in test_runs
                            if run.updated_at or run.created_at
                        )

                results["last_updated"] = dt.isoformat_utc(latest_timestamp)

                return results

        except Exception as e:
            logger.error(f"Error retrieving latest test runs: {str(e)}", exc_info=True)
            raise e
