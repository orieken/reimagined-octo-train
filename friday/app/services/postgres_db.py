from typing import List, Dict, Any, Optional, Callable, TypeVar, Generic
import logging
import asyncio
import json
import uuid
import functools
from datetime import datetime, timezone

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql import text
from sqlalchemy.exc import SQLAlchemyError

from app.config import settings
from app.models.domain import (
    Scenario as TestCase, Step as TestStep, TestRun as Report,
    BuildInfo, Feature
)
from app.services import datetime_service as dt

logger = logging.getLogger(__name__)

# SQLAlchemy async engine setup
DB_URL = settings.DATABASE_URL.replace('sqlite:///', 'sqlite+aiosqlite:///')
if 'postgresql' in DB_URL and 'postgresql+asyncpg' not in DB_URL:
    DB_URL = DB_URL.replace('postgresql://', 'postgresql+asyncpg://')

engine = create_async_engine(DB_URL, echo=False)
AsyncSessionLocal = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

# Type variables for decorator
T = TypeVar('T')
R = TypeVar('R')


def with_db_session(func):
    """
    Decorator to provide a database session to a method.
    Handles session creation, cleanup, commits, and rollbacks.
    """

    @functools.wraps(func)
    async def wrapper(self, *args, **kwargs):
        session = AsyncSessionLocal()
        try:
            result = await func(self, session, *args, **kwargs)
            await session.commit()
            return result
        except Exception as e:
            await session.rollback()
            logger.error(f"Database error in {func.__name__}: {str(e)}")
            raise
        finally:
            await session.close()

    return wrapper


class PostgresDBService:
    """
    Service for interacting with the PostgreSQL database.
    Handles storage and retrieval of test data in relational format.
    """

    @with_db_session
    async def store_report(self, session: AsyncSession, report: Report) -> str:
        """
        Store a test report in the PostgreSQL database.

        Args:
            session: Database session
            report: The report to store

        Returns:
            The ID of the stored report
        """
        try:
            # Import datetime services to ensure consistent handling

            # Use ensure_utc_datetime for consistent timestamp handling
            timestamp = dt.ensure_utc_datetime(report.timestamp)

            # Always use now_utc() for created_at and updated_at
            created_at = dt.now_utc()
            updated_at = dt.now_utc()

            # Calculate success rate
            total_scenarios = len(report.scenarios)
            passed_scenarios = sum(1 for s in report.scenarios if s.status == "PASSED")
            failed_scenarios = sum(1 for s in report.scenarios if s.status == "FAILED")
            skipped_scenarios = sum(1 for s in report.scenarios if s.status == "SKIPPED")
            error_scenarios = sum(1 for s in report.scenarios if s.status == "ERROR")
            success_rate = (passed_scenarios / total_scenarios) * 100 if total_scenarios > 0 else 0

            # Prepare metadata
            metadata = report.metadata if hasattr(report, 'metadata') else {}

            # Check if the project exists, create it if it doesn't
            project_id = metadata.get("project_id", 1)
            project_name = metadata.get("project", "Default Project")

            # Check if project exists
            project_check_query = """
            SELECT id FROM projects WHERE id = :project_id LIMIT 1
            """
            result = await session.execute(text(project_check_query), {"project_id": project_id})
            existing_project = result.scalar()

            if not existing_project:
                # Create the project
                project_insert = """
                INSERT INTO projects (
                    id, name, description, repository_url, active, meta_data, created_at, updated_at
                ) VALUES (
                    :id, :name, :description, :repository_url, :active, CAST(:meta_data AS jsonb), :created_at, :updated_at
                ) RETURNING id
                """
                project_params = {
                    "id": project_id,
                    "name": project_name,
                    "description": f"Auto-created project for {project_name}",
                    "repository_url": metadata.get("repository_url", None),
                    "active": True,
                    "meta_data": json.dumps({"auto_created": True, "source": "cucumber_processor"}),
                    "created_at": created_at,
                    "updated_at": updated_at
                }

                try:
                    result = await session.execute(text(project_insert), project_params)
                    project_id = result.scalar()
                    logger.info(f"Created project {project_id} for report {report.id}")
                except Exception as e:
                    logger.warning(f"Failed to create project, will use project_id=null: {str(e)}")
                    project_id = None

            # We need to generate a numeric ID since the database expects an integer ID
            # but our domain model uses UUID strings
            # First, check if we need to create a mapping for this UUID
            uuid_check_query = """
            SELECT meta_data->>'original_uuid' AS original_uuid
            FROM test_runs
            WHERE meta_data->>'original_uuid' = :original_uuid
            LIMIT 1
            """
            result = await session.execute(text(uuid_check_query), {"original_uuid": report.id})
            existing_uuid = result.scalar()

            if existing_uuid:
                # Get the integer ID for this UUID
                id_query = """
                SELECT id FROM test_runs 
                WHERE meta_data->>'original_uuid' = :original_uuid
                LIMIT 1
                """
                result = await session.execute(text(id_query), {"original_uuid": report.id})
                report_id = result.scalar()
            else:
                # Store the original UUID in metadata for reference
                metadata["original_uuid"] = report.id

                # Insert the report with a database-generated ID
                query = """
                INSERT INTO test_runs (
                    name, status, project_id, environment, 
                    start_time, end_time, duration, total_tests, 
                    passed_tests, failed_tests, skipped_tests, error_tests,
                    success_rate, branch, commit_hash, meta_data, 
                    created_at, updated_at
                ) VALUES (
                    :name, :status, :project_id, :environment,
                    :start_time, :end_time, :duration, :total_tests,
                    :passed_tests, :failed_tests, :skipped_tests, :error_tests,
                    :success_rate, :branch, :commit_hash, CAST(:meta_data AS jsonb),
                    :created_at, :updated_at
                ) RETURNING id
                """

                # Use consistent timezone-aware datetime objects
                params = {
                    "name": report.name,
                    "status": report.status,
                    "project_id": project_id,
                    "environment": report.environment,
                    "start_time": timestamp,
                    "end_time": None,  # Could be updated with ensure_utc_datetime if needed
                    "duration": report.duration,
                    "total_tests": total_scenarios,
                    "passed_tests": passed_scenarios,
                    "failed_tests": failed_scenarios,
                    "skipped_tests": skipped_scenarios,
                    "error_tests": error_scenarios,
                    "success_rate": success_rate,
                    "branch": metadata.get("branch", "main"),
                    "commit_hash": metadata.get("commit", None),
                    "meta_data": json.dumps(metadata),
                    "created_at": created_at,
                    "updated_at": updated_at
                }

                result = await session.execute(text(query), params)
                report_id = result.scalar()

            logger.info(f"Stored report with DB ID {report_id} (original UUID: {report.id}) in PostgreSQL")
            return report_id

        except Exception as e:
            logger.error(f"Error storing report in PostgreSQL: {str(e)}")
            raise

    @with_db_session
    async def store_test_case(self, session: AsyncSession, test_case: TestCase, report_id: str) -> int:
        """
        Store a test case in the PostgreSQL database.

        Args:
            session: Database session
            test_case: The test case to store
            report_id: The ID of the parent report (could be a UUID string or DB integer ID)

        Returns:
            The ID of the stored test case
        """
        try:
            # Convert data types if needed
            if isinstance(test_case.duration, str):
                try:
                    duration = float(test_case.duration)
                except ValueError:
                    duration = 0
            else:
                duration = test_case.duration

            # Prepare metadata
            metadata = test_case.metadata if hasattr(test_case, 'metadata') else {}
            # Add original UUID to metadata for future reference
            metadata["original_uuid"] = test_case.id

            # Determine the numeric report_id
            if not str(report_id).isdigit():
                # We have a UUID string, need to find the corresponding DB ID
                report_lookup_query = """
                SELECT id FROM test_runs
                WHERE meta_data->>'original_uuid' = :original_uuid
                LIMIT 1
                """
                result = await session.execute(text(report_lookup_query), {"original_uuid": report_id})
                numeric_report_id = result.scalar()
                if not numeric_report_id:
                    logger.warning(f"Could not find test run with original UUID {report_id}")
                    raise ValueError(f"No test run found with UUID {report_id}")
            else:
                numeric_report_id = report_id

            # Ensure all datetime fields are timezone-aware
            start_time = dt.ensure_utc_datetime(test_case.start_time if hasattr(test_case, 'start_time') else None)
            end_time = dt.ensure_utc_datetime(test_case.end_time if hasattr(test_case, 'end_time') else None)
            created_at = dt.now_utc()
            updated_at = dt.now_utc()

            # Convert test case to SQL parameters
            params = {
                "name": test_case.name,
                "description": test_case.description if hasattr(test_case, 'description') else "",
                "status": test_case.status,
                "test_run_id": numeric_report_id,
                "feature_id": None,  # Will need to look up or create feature
                "duration": duration,
                "start_time": start_time,
                "end_time": end_time,
                "error_message": test_case.error_message if hasattr(test_case, 'error_message') else None,
                "stack_trace": test_case.stack_trace if hasattr(test_case, 'stack_trace') else None,
                "parameters": json.dumps({}),  # Could populate from test case data
                "meta_data": json.dumps(metadata),
                "created_at": created_at,
                "updated_at": updated_at
            }

            # Find or create the feature
            feature_name = test_case.feature if hasattr(test_case, 'feature') else "Unknown"

            # Check if the project exists, create it if it doesn't
            project_id = 1  # Default
            if "project_id" in metadata:
                project_id = metadata["project_id"]
            elif "project" in metadata:
                project_name = metadata["project"]

                # Check if project exists by name
                project_check_query = """
                SELECT id FROM projects WHERE name = :project_name LIMIT 1
                """
                result = await session.execute(text(project_check_query), {"project_name": project_name})
                existing_project_id = result.scalar()

                if existing_project_id:
                    project_id = existing_project_id
                else:
                    # Create the project
                    project_insert = """
                    INSERT INTO projects (
                        name, description, repository_url, active, meta_data, created_at, updated_at
                    ) VALUES (
                        :name, :description, :repository_url, :active, CAST(:meta_data AS jsonb), :created_at, :updated_at
                    ) RETURNING id
                    """
                    project_params = {
                        "name": project_name,
                        "description": f"Auto-created project for {project_name}",
                        "repository_url": metadata.get("repository_url", None),
                        "active": True,
                        "meta_data": json.dumps({"auto_created": True, "source": "test_case_processor"}),
                        "created_at": created_at,
                        "updated_at": created_at
                    }

                    try:
                        result = await session.execute(text(project_insert), project_params)
                        project_id = result.scalar()
                        logger.info(f"Created project {project_id} for test case {test_case.name}")
                    except Exception as e:
                        logger.warning(f"Failed to create project, will use default: {str(e)}")

            feature_query = """
            SELECT id FROM features WHERE name = :name LIMIT 1
            """
            result = await session.execute(text(feature_query), {"name": feature_name})
            feature_id = result.scalar()

            if not feature_id:
                # Create the feature
                feature_insert = """
                INSERT INTO features (
                    name, description, project_id, created_at, updated_at
                ) VALUES (
                    :name, :description, :project_id, :created_at, :updated_at
                ) RETURNING id
                """
                feature_params = {
                    "name": feature_name,
                    "description": "",
                    "project_id": project_id,  # Use the resolved project_id
                    "created_at": created_at,
                    "updated_at": created_at
                }
                result = await session.execute(text(feature_insert), feature_params)
                feature_id = result.scalar()

            # Set the feature ID
            params["feature_id"] = feature_id

            # Insert the test case
            query = """
            INSERT INTO scenarios (
                name, description, status, test_run_id, feature_id,
                start_time, end_time, duration, error_message, stack_trace,
                parameters, meta_data, created_at, updated_at
            ) VALUES (
                :name, :description, :status, :test_run_id, :feature_id,
                :start_time, :end_time, :duration, :error_message, :stack_trace,
                CAST(:parameters AS jsonb), CAST(:meta_data AS jsonb), :created_at, :updated_at
            ) RETURNING id
            """

            result = await session.execute(text(query), params)

            # Get the test case ID
            test_case_id = result.scalar()

            logger.info(f"Stored test case {test_case_id} in PostgreSQL")
            return test_case_id

        except Exception as e:
            logger.error(f"Error storing test case in PostgreSQL: {str(e)}")
            raise

    @with_db_session
    async def store_scenario_tags(self, session: AsyncSession, scenario_id: int, tags: List[str]) -> None:
        """
        Store tags for a scenario in the PostgreSQL database.

        Args:
            session: Database session
            scenario_id: The ID of the scenario
            tags: List of tags to store
        """
        if not tags:
            return

        try:
            # Clean tags (remove @ prefix if present)
            clean_tags = [tag.lstrip('@') for tag in tags]

            # Insert tags in bulk
            values = []
            for tag in clean_tags:
                if tag:  # Skip empty tags
                    values.append(f"({scenario_id}, '{tag}')")

            if not values:
                return

            values_str = ", ".join(values)
            query = f"""
            INSERT INTO scenario_tags (scenario_id, tag)
            VALUES {values_str}
            ON CONFLICT (scenario_id, tag) DO NOTHING
            """

            await session.execute(text(query))

            logger.info(f"Stored {len(values)} tags for scenario {scenario_id}")

        except Exception as e:
            logger.error(f"Error storing scenario tags in PostgreSQL: {str(e)}")
            raise

    @with_db_session
    async def store_test_step(self, session: AsyncSession, step: TestStep, test_case_id: str) -> int:
        """
        Store a test step in the PostgreSQL database.

        Args:
            session: Database session
            step: The test step to store
            test_case_id: The ID of the parent test case

        Returns:
            The ID of the stored step
        """
        try:
            # Look up the PostgreSQL scenario ID from the Qdrant ID
            query = """
            SELECT id FROM scenarios WHERE meta_data->>'qdrant_id' = :qdrant_id LIMIT 1
            """
            result = await session.execute(text(query), {"qdrant_id": test_case_id})
            scenario_id = result.scalar()

            if not scenario_id:
                logger.warning(f"Could not find scenario with Qdrant ID {test_case_id}")
                return None

            # Convert data types if needed
            if isinstance(step.duration, str):
                try:
                    duration = float(step.duration)
                except ValueError:
                    duration = 0
            else:
                duration = step.duration

            # Prepare metadata
            metadata = step.metadata if hasattr(step, 'metadata') else {}
            # Add Qdrant ID to metadata for future reference
            metadata["qdrant_id"] = step.id

            # Get the order from the step number or generate one
            order = getattr(step, "order", 0)
            if not order:
                # Count existing steps to determine order
                count_query = """
                SELECT COUNT(*) FROM steps WHERE scenario_id = :scenario_id
                """
                result = await session.execute(text(count_query), {"scenario_id": scenario_id})
                order = result.scalar() + 1

            # Ensure all datetime fields are timezone-aware
            start_time = dt.ensure_utc_datetime(step.start_time if hasattr(step, 'start_time') else None)
            end_time = dt.ensure_utc_datetime(step.end_time if hasattr(step, 'end_time') else None)
            created_at = dt.now_utc()
            updated_at = dt.now_utc()

            # Convert step to SQL parameters
            params = {
                "scenario_id": scenario_id,
                "name": step.name if hasattr(step, 'name') else "",
                "keyword": step.keyword if hasattr(step, 'keyword') else "",
                "description": "",
                "status": step.status,
                "duration": duration,
                "error_message": step.error_message if hasattr(step, 'error_message') else None,
                "stack_trace": step.stack_trace if hasattr(step, 'stack_trace') else None,
                "start_time": start_time,
                "end_time": end_time,
                "screenshot_url": None,
                "log_output": None,
                "order": order,
                "created_at": created_at,
                "updated_at": updated_at
            }

            # Insert the step
            query = """
            INSERT INTO steps (
                scenario_id, name, description, status, start_time,
                end_time, duration, error_message, stack_trace, screenshot_url,
                log_output, "order", created_at, updated_at
            ) VALUES (
                :scenario_id, :name, :description, :status, :start_time,
                :end_time, :duration, :error_message, :stack_trace, :screenshot_url,
                :log_output, :order, :created_at, :updated_at
            ) RETURNING id
            """

            result = await session.execute(text(query), params)

            # Get the step ID
            step_id = result.scalar()

            logger.info(f"Stored step {step_id} in PostgreSQL")
            return step_id

        except Exception as e:
            logger.error(f"Error storing test step in PostgreSQL: {str(e)}")
            raise

    @with_db_session
    async def store_build_info(self, session: AsyncSession, build_info: BuildInfo) -> int:
        """
        Store build information in the PostgreSQL database.

        Args:
            session: Database session
            build_info: The build info to store

        Returns:
            The ID of the stored build info
        """
        try:
            # Prepare metadata
            metadata = build_info.metadata if hasattr(build_info, 'metadata') else {}

            # Check if we need to create a project first
            project_id = metadata.get("project_id", 1)
            project_check_query = """
            SELECT id FROM projects WHERE id = :project_id LIMIT 1
            """
            result = await session.execute(text(project_check_query), {"project_id": project_id})
            existing_project = result.scalar()

            if not existing_project:
                # Create the project
                project_name = metadata.get("project", "Default Project")
                project_insert = """
                INSERT INTO projects (
                    id, name, description, repository_url, active, meta_data, created_at, updated_at
                ) VALUES (
                    :id, :name, :description, :repository_url, :active, CAST(:meta_data AS jsonb), :created_at, :updated_at
                ) RETURNING id
                """
                project_params = {
                    "id": project_id,
                    "name": project_name,
                    "description": f"Auto-created project for {project_name}",
                    "repository_url": metadata.get("repository_url", None),
                    "active": True,
                    "meta_data": json.dumps({"auto_created": True, "source": "build_info_processor"}),
                    "created_at": dt.now_utc(),
                    "updated_at": dt.now_utc()
                }

                try:
                    result = await session.execute(text(project_insert), project_params)
                    project_id = result.scalar()
                    logger.info(f"Created project {project_id} for build {build_info.build_number}")
                except Exception as e:
                    logger.warning(f"Failed to create project, will use project_id=null: {str(e)}")
                    project_id = None

            # Ensure all datetime fields are timezone-aware
            start_time = dt.ensure_utc_datetime(build_info.date if hasattr(build_info, 'date') else None)
            end_time = dt.ensure_utc_datetime(build_info.end_date if hasattr(build_info, 'end_date') else None)
            created_at = dt.now_utc()
            updated_at = dt.now_utc()

            # Convert build info to SQL parameters
            params = {
                "project_id": project_id,
                "build_number": build_info.build_number,
                "name": build_info.name if hasattr(build_info, 'name') else build_info.build_number,
                "status": build_info.status,
                "start_time": start_time,
                "end_time": end_time,
                "duration": build_info.duration if hasattr(build_info, 'duration') else None,
                "branch": build_info.branch if hasattr(build_info, 'branch') else "main",
                "commit_hash": build_info.commit_hash if hasattr(build_info, 'commit_hash') else None,
                "environment": build_info.environment if hasattr(build_info, 'environment') else "dev",
                "meta_data": json.dumps(metadata),
                "created_at": created_at,
                "updated_at": updated_at
            }

            # Insert the build info
            query = """
            INSERT INTO build_infos (
                project_id, build_number, name, status, start_time,
                end_time, duration, branch, commit_hash, environment,
                meta_data, created_at, updated_at
            ) VALUES (
                :project_id, :build_number, :name, :status, :start_time,
                :end_time, :duration, :branch, :commit_hash, :environment,
                CAST(:meta_data AS jsonb), :created_at, :updated_at
            ) RETURNING id
            """

            result = await session.execute(text(query), params)

            # Get the build ID
            build_id = result.scalar()

            logger.info(f"Stored build info {build_id} in PostgreSQL")
            return build_id

        except Exception as e:
            logger.error(f"Error storing build info in PostgreSQL: {str(e)}")
            raise

    @with_db_session
    async def store_feature(self, session: AsyncSession, feature: Feature) -> int:
        """
        Store a feature in the PostgreSQL database.

        Args:
            session: Database session
            feature: The feature to store

        Returns:
            The ID of the stored feature
        """
        try:
            # Prepare metadata
            metadata = feature.metadata if hasattr(feature, 'metadata') else {}

            # Check if we need to create a project first
            project_id = metadata.get("project_id", 1)
            project_check_query = """
            SELECT id FROM projects WHERE id = :project_id LIMIT 1
            """
            result = await session.execute(text(project_check_query), {"project_id": project_id})
            existing_project = result.scalar()

            if not existing_project:
                # Create the project
                project_name = metadata.get("project", "Default Project")
                project_insert = """
                INSERT INTO projects (
                    id, name, description, repository_url, active, meta_data, created_at, updated_at
                ) VALUES (
                    :id, :name, :description, :repository_url, :active, CAST(:meta_data AS jsonb), :created_at, :updated_at
                ) RETURNING id
                """
                project_params = {
                    "id": project_id,
                    "name": project_name,
                    "description": f"Auto-created project for {project_name}",
                    "repository_url": metadata.get("repository_url", None),
                    "active": True,
                    "meta_data": json.dumps({"auto_created": True, "source": "feature_processor"}),
                    "created_at": dt.now_utc(),
                    "updated_at": dt.now_utc()
                }

                try:
                    result = await session.execute(text(project_insert), project_params)
                    project_id = result.scalar()
                    logger.info(f"Created project {project_id} for feature {feature.name}")
                except Exception as e:
                    logger.warning(f"Failed to create project, will use project_id=null: {str(e)}")
                    project_id = None

            # Use now_utc() for consistent timestamp handling
            created_at = dt.now_utc()
            updated_at = dt.now_utc()

            # Convert feature to SQL parameters
            params = {
                "name": feature.name,
                "description": feature.description if hasattr(feature, 'description') else "",
                "project_id": project_id,
                "file_path": feature.file_path if hasattr(feature, 'file_path') else None,
                "tags": feature.tags if hasattr(feature, 'tags') else [],
                "created_at": created_at,
                "updated_at": updated_at
            }

            # Insert the feature
            query = """
            INSERT INTO features (
                name, description, project_id, file_path, tags,
                created_at, updated_at
            ) VALUES (
                :name, :description, :project_id, :file_path, CAST(:tags AS jsonb),
                :created_at, :updated_at
            ) ON CONFLICT (name) DO UPDATE SET
                description = EXCLUDED.description,
                file_path = EXCLUDED.file_path,
                tags = EXCLUDED.tags,
                updated_at = EXCLUDED.updated_at
            RETURNING id
            """

            result = await session.execute(text(query), params)

            # Get the feature ID
            feature_id = result.scalar()

            logger.info(f"Stored feature {feature_id} in PostgreSQL")
            return feature_id

        except Exception as e:
            logger.error(f"Error storing feature in PostgreSQL: {str(e)}")
            raise

    @with_db_session
    async def update_vector_reference(self, session: AsyncSession, pg_id: int, vector_id: str) -> None:
        """
        Update a PostgreSQL record with reference to its vector database ID.

        Args:
            session: Database session
            pg_id: PostgreSQL ID
            vector_id: Vector database ID
        """
        try:
            # Get current time for update
            updated_at = dt.now_utc()

            query = """
            UPDATE test_runs 
            SET 
                meta_data = meta_data || ('{"vector_id": "' || :vector_id || '"}')::jsonb,
                updated_at = :updated_at
            WHERE id = :pg_id
            """

            await session.execute(text(query), {
                "pg_id": pg_id,
                "vector_id": vector_id,
                "updated_at": updated_at
            })

            logger.info(f"Updated test run {pg_id} with vector ID {vector_id}")

        except Exception as e:
            logger.error(f"Error updating vector reference: {str(e)}")
            raise

    @with_db_session
    async def update_test_case_vector_reference(self, session: AsyncSession, pg_id: int, vector_id: str) -> None:
        """
        Update a test case with reference to its vector database ID.

        Args:
            session: Database session
            pg_id: PostgreSQL ID
            vector_id: Vector database ID
        """
        try:
            # Get current time for update
            updated_at = dt.now_utc()

            query = """
            UPDATE scenarios 
            SET 
                meta_data = meta_data || ('{"vector_id": "' || :vector_id || '"}')::jsonb,
                updated_at = :updated_at
            WHERE id = :pg_id
            """

            await session.execute(text(query), {
                "pg_id": pg_id,
                "vector_id": vector_id,
                "updated_at": updated_at
            })

            logger.info(f"Updated scenario {pg_id} with vector ID {vector_id}")

        except Exception as e:
            logger.error(f"Error updating test case vector reference: {str(e)}")
            raise

    @with_db_session
    async def update_step_vector_reference(self, session: AsyncSession, pg_id: int, vector_id: str) -> None:
        """
        Update a test step with reference to its vector database ID.

        Args:
            session: Database session
            pg_id: PostgreSQL ID
            vector_id: Vector database ID
        """
        try:

            # Get current time for update
            updated_at = dt.now_utc()

            query = """
            UPDATE steps 
            SET 
                meta_data = meta_data || ('{"vector_id": "' || :vector_id || '"}')::jsonb,
                updated_at = :updated_at
            WHERE id = :pg_id
            """

            await session.execute(text(query), {
                "pg_id": pg_id,
                "vector_id": vector_id,
                "updated_at": updated_at
            })

            logger.info(f"Updated step {pg_id} with vector ID {vector_id}")

        except Exception as e:
            logger.error(f"Error updating step vector reference: {str(e)}")
            raise

    @with_db_session
    async def update_build_vector_reference(self, session: AsyncSession, pg_id: int, vector_id: str) -> None:
        """
        Update a build info with reference to its vector database ID.

        Args:
            session: Database session
            pg_id: PostgreSQL ID
            vector_id: Vector database ID
        """
        try:
            # Get current time for update
            updated_at = dt.now_utc()

            query = """
            UPDATE build_infos 
            SET 
                meta_data = COALESCE(meta_data, '{}'::jsonb) || ('{"vector_id": "' || :vector_id || '"}')::jsonb,
                updated_at = :updated_at
            WHERE id = :pg_id
            """

            await session.execute(text(query), {
                "pg_id": pg_id,
                "vector_id": vector_id,
                "updated_at": updated_at
            })

            logger.info(f"Updated build info {pg_id} with vector ID {vector_id}")

        except Exception as e:
            logger.error(f"Error updating build vector reference: {str(e)}")
            raise

    @with_db_session
    async def update_feature_vector_reference(self, session: AsyncSession, pg_id: int, vector_id: str) -> None:
        """
        Update a feature with reference to its vector database ID.

        Args:
            session: Database session
            pg_id: PostgreSQL ID
            vector_id: Vector database ID
        """
        try:

            # Get current time for update
            updated_at = dt.now_utc()

            query = """
            UPDATE features 
            SET 
                meta_data = COALESCE(meta_data, '{}'::jsonb) || ('{"vector_id": "' || :vector_id || '"}')::jsonb,
                updated_at = :updated_at
            WHERE id = :pg_id
            """

            await session.execute(text(query), {
                "pg_id": pg_id,
                "vector_id": vector_id,
                "updated_at": updated_at
            })

            logger.info(f"Updated feature {pg_id} with vector ID {vector_id}")

        except Exception as e:
            logger.error(f"Error updating feature vector reference: {str(e)}")
            raise