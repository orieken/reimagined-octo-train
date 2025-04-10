# app/routers/results.py
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from uuid import UUID
from fastapi import APIRouter, Depends, Query, HTTPException, BackgroundTasks
from sqlalchemy import func, and_, or_, distinct, text, literal, Integer, case
from sqlalchemy.orm import Session, aliased
import logging

from app.database.session import get_db
from app.config import settings
from app.services.orchestrator import ServiceOrchestrator
from app.api.dependencies import get_orchestrator_service

from app.models import TestStatus
from app.models.schemas import Scenario, TestRun, Feature, ResultsResponse, ScenarioTag

# Import the actual SQLAlchemy models from your project
from app.models.database import Scenario as DBScenario
from app.models.database import TestRun as DBTestRun
from app.models.database import Feature as DBFeature
from app.models.database import ScenarioTag as DBScenarioTag

logger = logging.getLogger("friday.results")
router = APIRouter(prefix=settings.API_PREFIX)


@router.get("/results", response_model=ResultsResponse)
async def get_test_results(
        build_id: Optional[int] = Query(None, description="Filter by build ID"),
        test_run_id: Optional[int] = Query(None, description="Filter by test run ID"),
        feature_name: Optional[str] = Query(None, description="Filter by feature name"),
        start_date: Optional[datetime] = Query(None, description="Filter by start date"),
        end_date: Optional[datetime] = Query(None, description="Filter by end date"),
        limit_days: Optional[int] = Query(30, description="Limit results to last N days"),
        tag: Optional[str] = Query(None, description="Filter by specific tag"),
        status: Optional[str] = Query(None, description="Filter by status (PASSED, FAILED, SKIPPED)"),
        project_id: Optional[int] = Query(None, description="Filter by project ID"),
        environment: Optional[str] = Query(None, description="Filter by environment"),
        use_vector_db: Optional[bool] = Query(True, description="Use vector database for queries"),
        background_tasks: BackgroundTasks = BackgroundTasks(),
        db: Session = Depends(get_db),
        orchestrator: ServiceOrchestrator = Depends(get_orchestrator_service)
):
    """
    Get detailed test results with statistics grouped by features and tags.

    Supports filtering by various parameters including build ID, test run ID,
    feature name, tag, status, project ID, or date range.
    Results include overall statistics, feature-based stats, and tag-based analysis.
    """
    logger.info(
        f"Processing results request with filters: build_id={build_id}, test_run_id={test_run_id}, feature={feature_name}, tag={tag}, use_vector_db={use_vector_db}")

    # If vector DB use is enabled, query Qdrant for results
    if use_vector_db:
        try:
            return await get_results_from_qdrant(
                orchestrator=orchestrator,
                build_id=build_id,
                test_run_id=test_run_id,
                feature_name=feature_name,
                start_date=start_date,
                end_date=end_date,
                limit_days=limit_days,
                tag=tag,
                status=status,
                project_id=project_id,
                environment=environment,
                background_tasks=background_tasks
            )
        except Exception as e:
            logger.error(f"Error retrieving results from Qdrant: {str(e)}", exc_info=True)
            logger.info("Falling back to SQL database for results")

    # If vector DB query fails or is disabled, fall back to SQL database
    try:
        return await get_results_from_sql(
            db=db,
            build_id=build_id,
            test_run_id=test_run_id,
            feature_name=feature_name,
            start_date=start_date,
            end_date=end_date,
            limit_days=limit_days,
            tag=tag,
            status=status,
            project_id=project_id,
            environment=environment,
            background_tasks=background_tasks
        )
    except Exception as e:
        # Log the exception
        logger.error(f"Error retrieving test results from SQL database: {str(e)}", exc_info=True)

        # Return an error response
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve test results: {str(e)}"
        )


async def get_results_from_qdrant(
        orchestrator: ServiceOrchestrator,
        build_id: Optional[int] = None,
        test_run_id: Optional[int] = None,
        feature_name: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit_days: Optional[int] = 30,
        tag: Optional[str] = None,
        status: Optional[str] = None,
        project_id: Optional[int] = None,
        environment: Optional[str] = None,
        background_tasks: BackgroundTasks = BackgroundTasks(),
) -> ResultsResponse:
    """
    Get test results from Qdrant vector database.
    Similar to the implementation in /stats endpoints.
    """
    try:
        # Get client and collection
        client = orchestrator.vector_db.client
        collection_name = orchestrator.vector_db.cucumber_collection

        from qdrant_client.http import models as qdrant_models

        # Base filter for test cases
        test_case_filter = qdrant_models.Filter(
            must=[
                qdrant_models.FieldCondition(
                    key="type",
                    match=qdrant_models.MatchValue(value="test_case")
                )
            ]
        )

        # Apply additional filters
        if environment:
            test_case_filter.must.append(
                qdrant_models.FieldCondition(
                    key="environment",
                    match=qdrant_models.MatchValue(value=environment)
                )
            )

        if build_id:
            test_case_filter.must.append(
                qdrant_models.FieldCondition(
                    key="build_id",
                    match=qdrant_models.MatchValue(value=build_id)
                )
            )

        if test_run_id:
            test_case_filter.must.append(
                qdrant_models.FieldCondition(
                    key="test_run_id",
                    match=qdrant_models.MatchValue(value=test_run_id)
                )
            )

        if project_id:
            test_case_filter.must.append(
                qdrant_models.FieldCondition(
                    key="project_id",
                    match=qdrant_models.MatchValue(value=project_id)
                )
            )

        if status:
            test_case_filter.must.append(
                qdrant_models.FieldCondition(
                    key="status",
                    match=qdrant_models.MatchValue(value=status.upper())
                )
            )

        if tag:
            test_case_filter.must.append(
                qdrant_models.FieldCondition(
                    key="tags",
                    match=qdrant_models.MatchAny(any=[tag])
                )
            )

        if feature_name:
            test_case_filter.must.append(
                qdrant_models.FieldCondition(
                    key="feature",
                    match=qdrant_models.MatchText(text=feature_name)
                )
            )

        # Retrieve all test cases for processing with manual date filtering
        all_test_cases = []
        offset = None
        limit = 1000  # Batch size

        # Determine cutoff date if limit_days is provided
        cutoff_date = None
        if not start_date and limit_days:
            cutoff_date = datetime.now() - timedelta(days=limit_days)
        elif start_date:
            cutoff_date = start_date

        # Override cutoff_date if explicit start_date is provided
        if start_date:
            cutoff_date = start_date

        # Scroll through all test cases in batches
        while True:
            test_cases_batch, offset = client.scroll(
                collection_name=collection_name,
                scroll_filter=test_case_filter,
                limit=limit,
                offset=offset,
                with_payload=True,
                with_vectors=False
            )

            # Apply date filtering if needed
            if cutoff_date or end_date:
                filtered_batch = []
                for tc in test_cases_batch:
                    try:
                        timestamp = tc.payload.get("timestamp", "")
                        if timestamp:
                            tc_date = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))

                            # Check if date is within range
                            date_in_range = True
                            if cutoff_date and tc_date < cutoff_date:
                                date_in_range = False
                            if end_date and tc_date > end_date:
                                date_in_range = False

                            if date_in_range:
                                filtered_batch.append(tc)
                        else:
                            # Include items without timestamp
                            filtered_batch.append(tc)
                    except (ValueError, TypeError) as e:
                        logger.warning(f"Error parsing timestamp: {e}")
                        # Include items with invalid timestamp
                        filtered_batch.append(tc)

                all_test_cases.extend(filtered_batch)
            else:
                all_test_cases.extend(test_cases_batch)

            # Exit loop if no more results
            if offset is None or len(test_cases_batch) < limit:
                break

        # Calculate statistics
        total_count = len(all_test_cases)
        passed_count = sum(1 for tc in all_test_cases if tc.payload.get("status") == "PASSED")
        failed_count = sum(1 for tc in all_test_cases if tc.payload.get("status") == "FAILED")
        skipped_count = sum(1 for tc in all_test_cases if tc.payload.get("status") == "SKIPPED")

        # Calculate pass rate
        pass_rate = passed_count / total_count if total_count > 0 else 0

        # Group scenarios by feature
        feature_stats = {}
        for tc in all_test_cases:
            feature = tc.payload.get("feature", "Unknown")
            if feature not in feature_stats:
                feature_stats[feature] = {
                    "name": feature,
                    "passed_scenarios": 0,
                    "failed_scenarios": 0,
                    "skipped_scenarios": 0
                }

            # Update counts based on status
            status = tc.payload.get("status", "")
            if status == "PASSED":
                feature_stats[feature]["passed_scenarios"] += 1
            elif status == "FAILED":
                feature_stats[feature]["failed_scenarios"] += 1
            elif status == "SKIPPED":
                feature_stats[feature]["skipped_scenarios"] += 1

        # Group scenarios by tag
        tag_stats = {}
        for tc in all_test_cases:
            tags = tc.payload.get("tags", [])
            status = tc.payload.get("status", "")

            for tag_name in tags:
                if tag_name not in tag_stats:
                    tag_stats[tag_name] = {
                        "count": 0,
                        "passed": 0,
                        "failed": 0,
                        "skipped": 0,
                        "pass_rate": 0
                    }

                tag_stats[tag_name]["count"] += 1

                if status == "PASSED":
                    tag_stats[tag_name]["passed"] += 1
                elif status == "FAILED":
                    tag_stats[tag_name]["failed"] += 1
                elif status == "SKIPPED":
                    tag_stats[tag_name]["skipped"] += 1

        # Calculate pass rate for each tag
        for tag_name in tag_stats:
            tag_count = tag_stats[tag_name]["count"]
            tag_passed = tag_stats[tag_name]["passed"]
            tag_stats[tag_name]["pass_rate"] = round(tag_passed / tag_count, 4) if tag_count > 0 else 0

        # Get most recent timestamp as last_updated
        last_updated = datetime.now()
        for tc in all_test_cases:
            try:
                timestamp = tc.payload.get("timestamp", "")
                if timestamp:
                    tc_date = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                    if tc_date > last_updated:
                        last_updated = tc_date
            except (ValueError, TypeError):
                pass

        # Convert feature_stats dict to list for the response
        feature_stats_list = list(feature_stats.values())

        # Sort features by total scenarios (descending)
        feature_stats_list.sort(
            key=lambda x: (x["passed_scenarios"] + x["failed_scenarios"] + x["skipped_scenarios"]),
            reverse=True
        )

        # Log performance info
        background_tasks.add_task(
            logger.info,
            f"Qdrant query completed: {total_count} scenarios, {len(feature_stats)} features, {len(tag_stats)} tags"
        )

        return ResultsResponse(
            status="success",
            results={
                "total_scenarios": total_count,
                "passed_scenarios": passed_count,
                "failed_scenarios": failed_count,
                "skipped_scenarios": skipped_count,
                "pass_rate": round(pass_rate, 6),
                "last_updated": last_updated.isoformat(),
                "features": feature_stats_list,
                "tags": tag_stats
            }
        )
    except Exception as e:
        logger.error(f"Error retrieving test results from Qdrant: {str(e)}", exc_info=True)
        raise e


async def get_results_from_sql(
        db: Session,
        build_id: Optional[int] = None,
        test_run_id: Optional[int] = None,
        feature_name: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit_days: Optional[int] = 30,
        tag: Optional[str] = None,
        status: Optional[str] = None,
        project_id: Optional[int] = None,
        environment: Optional[str] = None,
        background_tasks: BackgroundTasks = BackgroundTasks(),
) -> ResultsResponse:
    """
    Get test results from SQL database.
    Original implementation with fixes.
    """
    try:
        # Set default date range if not provided
        if not end_date:
            end_date = datetime.utcnow()

        if not start_date and limit_days:
            # Extend default limit to a longer period if no results found
            start_date = end_date - timedelta(days=max(limit_days, 90))

        # Base query filter conditions
        filter_conditions = []

        # Time-based filters - Using the Scenario model fields we know exist
        if start_date:
            # Based on your model, we know start_time and created_at exist
            # Using start_time as primary, falling back to created_at
            filter_conditions.append(DBScenario.start_time >= start_date if start_date else None)

        logger.debug(f"Initial filter conditions: {filter_conditions}")

        if end_date:
            # Using end_time as primary, falling back to created_at
            filter_conditions.append(DBScenario.end_time <= end_date if end_date else None)

        logger.debug(f"After end_date filter conditions: {filter_conditions}")

        # ID-based filters
        if build_id:
            filter_conditions.append(DBTestRun.build_id == build_id)

        if test_run_id:
            filter_conditions.append(DBScenario.test_run_id == test_run_id)

        if project_id:
            # If Scenario doesn't have project_id directly, we need to join with TestRun
            filter_conditions.append(DBTestRun.project_id == project_id)

        # Text-based filters
        if feature_name:
            # If we have a Feature relationship, use that
            filter_conditions.append(DBFeature.name.ilike(f"%{feature_name}%"))

        if status:
            # Convert to the correct Enum if using enum type
            try:
                status_enum = TestStatus[status.upper()]
                filter_conditions.append(DBScenario.status == status_enum)
            except (KeyError, ValueError):
                # Handle invalid status gracefully
                logger.warning(f"Invalid status filter: {status}")
                raise HTTPException(status_code=400, detail=f"Invalid status: {status}")

        if environment:
            filter_conditions.append(DBTestRun.environment == environment)

        logger.debug(f"Final filter conditions: {filter_conditions}")

        # Base query with all necessary joins - ensure we join TestRun and Feature
        base_query = db.query(DBScenario).join(
            DBTestRun, DBScenario.test_run_id == DBTestRun.id
        ).join(
            DBFeature, DBScenario.feature_id == DBFeature.id, isouter=True
        )

        # Apply tag filter with a separate join if needed
        if tag:
            base_query = base_query.join(
                DBScenarioTag, DBScenario.id == DBScenarioTag.scenario_id
            ).filter(DBScenarioTag.tag == tag)

        # Apply all other filters
        base_query = base_query.filter(*filter_conditions)

        # Overall statistics query with conditional expressions for counting
        logger.debug(f"Stats query filter conditions: {[str(condition) for condition in filter_conditions]}")

        # We know from your model that updated_at exists
        stats_query = db.query(
            func.count(distinct(DBScenario.id)).label("total"),
            func.sum(case((DBScenario.status == TestStatus.PASSED, 1), else_=0)).label("passed"),
            func.sum(case((DBScenario.status == TestStatus.FAILED, 1), else_=0)).label("failed"),
            func.sum(case((DBScenario.status == TestStatus.SKIPPED, 1), else_=0)).label("skipped"),
            func.max(DBScenario.updated_at).label("last_updated")
        )

        # Apply filters and joins to stats_query
        stats_query = stats_query.select_from(DBScenario)
        stats_query = stats_query.join(DBTestRun, DBScenario.test_run_id == DBTestRun.id)
        stats_query = stats_query.join(DBFeature, DBScenario.feature_id == DBFeature.id, isouter=True)

        # Apply tag filter to stats query if needed
        if tag:
            stats_query = stats_query.join(
                DBScenarioTag, DBScenario.id == DBScenarioTag.scenario_id
            ).filter(DBScenarioTag.tag == tag)

        # Apply all other filters
        for filter_condition in filter_conditions:
            stats_query = stats_query.filter(filter_condition)

        # Execute the query
        stats = stats_query.first()

        if not stats or stats.total == 0:
            # Return empty results if no data found
            return ResultsResponse(
                status="success",
                results={
                    "total_scenarios": 0,
                    "passed_scenarios": 0,
                    "failed_scenarios": 0,
                    "skipped_scenarios": 0,
                    "pass_rate": 0,
                    "last_updated": datetime.utcnow().isoformat(),
                    "features": [],
                    "tags": {}
                }
            )

        # Calculate pass rate
        pass_rate = stats.passed / stats.total if stats.total > 0 else 0

        # Get feature statistics - enhanced with correct joins
        feature_stats_query = db.query(
            DBFeature.name.label("feature_name"),
            func.count(distinct(DBScenario.id)).label("total"),
            func.sum(case((DBScenario.status == TestStatus.PASSED, 1), else_=0)).label("passed"),
            func.sum(case((DBScenario.status == TestStatus.FAILED, 1), else_=0)).label("failed"),
            func.sum(case((DBScenario.status == TestStatus.SKIPPED, 1), else_=0)).label("skipped")
        ).join(
            DBScenario, DBFeature.id == DBScenario.feature_id
        ).join(
            DBTestRun, DBScenario.test_run_id == DBTestRun.id
        )

        # Apply filters to the feature stats query
        for filter_condition in filter_conditions:
            feature_stats_query = feature_stats_query.filter(filter_condition)

        # Apply tag filter to feature stats if needed
        if tag:
            feature_stats_query = feature_stats_query.join(
                DBScenarioTag, DBScenario.id == DBScenarioTag.scenario_id
            ).filter(DBScenarioTag.tag == tag)

        # Group by feature name and order by total scenarios descending
        feature_stats_query = feature_stats_query.group_by(DBFeature.name).order_by(
            func.count(distinct(DBScenario.id)).desc())

        # Format feature stats for response
        feature_stats = []
        for f in feature_stats_query.all():
            feature_stats.append({
                "name": f.feature_name or "Unknown",
                "passed_scenarios": f.passed or 0,
                "failed_scenarios": f.failed or 0,
                "skipped_scenarios": f.skipped or 0
            })

        # Debug query to count total tags in the database
        total_tags_query = db.query(func.count(DBScenarioTag.tag)).scalar()
        logger.info(f"Total tags in database: {total_tags_query}")

        # Get scenario IDs from the base query to check if they have tags
        scenario_ids_query = base_query.with_entities(DBScenario.id)
        scenario_ids = [row[0] for row in scenario_ids_query.all()]

        if scenario_ids:
            # Check if these scenarios have tags
            tag_count_for_scenarios = db.query(func.count(DBScenarioTag.tag)).filter(
                DBScenarioTag.scenario_id.in_(scenario_ids)
            ).scalar()
            logger.info(f"Found {tag_count_for_scenarios} tags for {len(scenario_ids)} filtered scenarios")

        # Get tag statistics - critical part that needs fixing
        # This query gets statistics for all tags that appear in the filtered scenarios
        tag_stats_query = db.query(
            DBScenarioTag.tag,
            func.count(distinct(DBScenario.id)).label("count"),
            func.sum(case((DBScenario.status == TestStatus.PASSED, 1), else_=0)).label("passed"),
            func.sum(case((DBScenario.status == TestStatus.FAILED, 1), else_=0)).label("failed"),
            func.sum(case((DBScenario.status == TestStatus.SKIPPED, 1), else_=0)).label("skipped")
        ).join(
            DBScenario, DBScenarioTag.scenario_id == DBScenario.id
        ).join(
            DBTestRun, DBScenario.test_run_id == DBTestRun.id
        ).join(
            DBFeature, DBScenario.feature_id == DBFeature.id, isouter=True
        )

        # Enhanced logging for tag query debugging
        logger.debug(f"Tag stats query: {str(tag_stats_query)}")

        # Apply all filters
        for filter_condition in filter_conditions:
            tag_stats_query = tag_stats_query.filter(filter_condition)

        # Group by tag and order by count descending
        tag_stats_query = tag_stats_query.group_by(DBScenarioTag.tag).order_by(
            func.count(distinct(DBScenario.id)).desc())

        # Execute query and format tag stats
        tag_stats = {}
        for t in tag_stats_query.all():
            # Calculate tag-specific pass rate
            tag_pass_rate = t.passed / t.count if t.count > 0 else 0

            tag_stats[t.tag] = {
                "count": t.count,
                "pass_rate": round(tag_pass_rate, 4),
                "passed": t.passed,
                "failed": t.failed,
                "skipped": t.skipped
            }

        # Log query performance information asynchronously
        background_tasks.add_task(
            logger.info,
            f"Query completed: {stats.total} scenarios, {len(feature_stats)} features, {len(tag_stats)} tags"
        )

        # Prepare and return the response
        last_updated = stats.last_updated
        if not last_updated and stats.total > 0:
            # If there's no updated_at but we have results, use current time
            last_updated = datetime.utcnow()

        logger.debug(
            f"Query results - Total: {stats.total}, Passed: {stats.passed}, Failed: {stats.failed}, Skipped: {stats.skipped}")
        logger.debug(f"Tags found: {list(tag_stats.keys())}")

        return ResultsResponse(
            status="success",
            results={
                "total_scenarios": stats.total or 0,
                "passed_scenarios": stats.passed or 0,
                "failed_scenarios": stats.failed or 0,
                "skipped_scenarios": stats.skipped or 0,
                "pass_rate": round(pass_rate, 6),
                "last_updated": last_updated.isoformat() if last_updated else datetime.utcnow().isoformat(),
                "features": feature_stats,
                "tags": tag_stats
            }
        )
    except Exception as e:
        logger.error(f"Error retrieving test results from SQL database: {str(e)}", exc_info=True)
        raise e