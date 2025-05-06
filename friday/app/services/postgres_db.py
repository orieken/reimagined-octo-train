import logging
import json
from typing import Optional, List, Dict, Any
from uuid import UUID, uuid4

from sqlalchemy import select, text, insert
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.config import settings
from app.services import datetime_service as dt
from app.models import (
    TestRun as Report,
    Scenario as TestCase,
    Step as TestStep,
    Feature,
    BuildInfo
)
from app.models.database import (
    Base,
    TestRun as DBTestRun,
    Scenario as DBScenario,
    Step as DBStep,
    Feature as DBFeature,
    BuildInfo as DBBuildInfo,
    Project as DBProject,
    ScenarioTag as DBScenarioTag,
)
from app.services.datetime_service import make_timestamps, default_epoch, safe_utc_datetime, safe_duration, now_utc
from app.models.metadata import ReportMetadata
from app.models.domain import TestRun
from app.models.base import TestStatus

logger = logging.getLogger(__name__)

# Async DB engine
DB_URL = settings.DATABASE_URL
if "postgresql://" in DB_URL and "postgresql+asyncpg://" not in DB_URL:
    DB_URL = DB_URL.replace("postgresql://", "postgresql+asyncpg://")

engine = create_async_engine(DB_URL, echo=False, future=True)
AsyncSessionLocal = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)


class PostgresDBService:
    def session(self):
        return AsyncSessionLocal()

    async def ensure_project_id(self, name: str, session: AsyncSession) -> str:
        query = select(DBProject).where(DBProject.name == name)
        result = await session.execute(query)
        project = result.scalar_one_or_none()

        if project:
            return str(project.id)

        new_project = DBProject(
            name=name,
            description="Autocreated project",
            created_at=now_utc(),
            updated_at=now_utc(),
            meta_data={}
        )
        session.add(new_project)
        await session.flush()
        await session.refresh(new_project)
        return str(new_project.id)

    async def save_features(
        self,
        features: List[Feature],
        project_id: UUID,
        session: AsyncSession
    ) -> Dict[str, UUID]:
        feature_id_map = {}
        now = dt.now_utc()

        for feature in features:
            db_feature = DBFeature(
                id=uuid4(),
                name=feature.name,
                external_id=feature.external_id,
                description=feature.description,
                file_path=feature.uri,
                tags=feature.tags or [],
                created_at=now,
                updated_at=now,
                project_id=project_id
            )
            session.add(db_feature)
            await session.flush()
            feature_id_map[feature.uri] = db_feature.id

        return feature_id_map

    async def save_test_run(
            self,
            metadata: ReportMetadata,
            project_id: UUID,
            test_run: TestRun,
            features,
            session: AsyncSession
    ) -> str:
        now = dt.now_utc()
        feature_id_map = await self.save_features(features, project_id, session)
        logger.info(f"Feature ID map created: {feature_id_map}")
        logger.info(f"DEBUG: Feature ID map keys: {list(feature_id_map.keys())}")

        db_test_run = DBTestRun(
            id=uuid4(),
            external_id=metadata.test_run_id,
            name=metadata.test_run_id,
            description=None,
            status=TestStatus.UNKNOWN,
            environment=metadata.environment,
            branch=metadata.branch,
            commit_hash=metadata.commit,
            start_time=None,
            end_time=None,
            duration=0.0,
            total_tests=0,
            passed_tests=0,
            failed_tests=0,
            skipped_tests=0,
            error_tests=0,
            success_rate=0.0,
            created_at=now,
            updated_at=now,
            runner=metadata.runner,
            meta_data=metadata.metadata or {},
            project_id=project_id
        )
        session.add(db_test_run)

        # Choose a fallback feature_id - this is critical
        fallback_feature_id = None
        if feature_id_map:
            if None in feature_id_map:
                fallback_feature_id = feature_id_map[None]
            else:
                # Get the first feature ID from the map
                fallback_feature_id = next(iter(feature_id_map.values()))

        logger.info(f"DEBUG: Using fallback feature_id if needed: {fallback_feature_id}")

        for scenario in test_run.scenarios:
            # Debug scenario properties
            logger.info(
                f"DEBUG: Scenario {scenario.id} - Feature file: {getattr(scenario, 'feature_file', 'NOT PRESENT')}")
            logger.info(f"DEBUG: Scenario feature_id attribute: {getattr(scenario, 'feature_id', 'NOT PRESENT')}")

            # CRITICAL FIX: Always use the fallback feature_id instead of scenario.feature_id
            feature_id = fallback_feature_id

            if hasattr(scenario, 'feature_file') and scenario.feature_file and scenario.feature_file in feature_id_map:
                # Use feature_file to look up feature_id
                feature_id = feature_id_map.get(scenario.feature_file)
                logger.info(f"DEBUG: Using feature_id from feature_file lookup: {feature_id}")
            else:
                logger.info(f"DEBUG: Using fallback feature_id: {feature_id}")

            # NEVER use scenario.feature_id directly - it's causing the FK violation

            db_scenario = DBScenario(
                id=scenario.id,
                external_id=scenario.external_id,
                name=scenario.name,
                description=scenario.description,
                status=scenario.status,
                duration=scenario.duration,
                is_flaky=scenario.is_flaky,
                embeddings=scenario.embeddings,
                feature_id=feature_id,  # Always use our calculated feature_id, never scenario.feature_id
                test_run_id=db_test_run.id,
                created_at=scenario.created_at,
                updated_at=scenario.updated_at,
            )
            session.add(db_scenario)

            # Store tags with line numbers
            if hasattr(scenario, 'tags') and scenario.tags:
                logger.info(f"Storing {len(scenario.tags)} tags for scenario {scenario.id}: {scenario.tags}")

                # Get tag metadata if available
                tag_metadata = {}
                if hasattr(scenario, 'tag_metadata'):
                    tag_metadata = scenario.tag_metadata

                for tag in scenario.tags:
                    # Sometimes tags might have @ prefix, remove it
                    tag_name = tag
                    if isinstance(tag_name, str) and tag_name.startswith('@'):
                        tag_name = tag_name[1:]

                    # Get line number from metadata if available
                    line = None
                    if tag_metadata and tag in tag_metadata and 'line' in tag_metadata[tag]:
                        line = tag_metadata[tag]['line']

                    logger.info(f"Storing tag '{tag_name}' with line {line} for scenario {db_scenario.id}")

                    db_scenario_tag = DBScenarioTag(
                        scenario_id=db_scenario.id,
                        tag=tag_name,
                        line=line
                    )
                    session.add(db_scenario_tag)
            else:
                logger.info(f"No tags to store for scenario {scenario.id}")

            for step in scenario.steps:
                db_step = DBStep(
                    id=step.id,
                    external_id=step.external_id,
                    name=step.name,
                    keyword=step.keyword,
                    status=step.status,
                    duration=step.duration,
                    error_message=step.error_message,
                    stack_trace=step.stack_trace,
                    embeddings=step.embeddings,
                    order=step.order,
                    start_time=step.start_time,
                    end_time=step.end_time,
                    scenario_id=db_scenario.id,
                    created_at=step.created_at,
                    updated_at=step.updated_at,
                )
                session.add(db_step)

        await session.flush()
        return str(db_test_run.id)