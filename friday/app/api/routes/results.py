# app/routers/results.py
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from uuid import UUID
from fastapi import APIRouter, Depends, Query, HTTPException, BackgroundTasks
from sqlalchemy import func, and_, or_, distinct, case
from sqlalchemy.orm import Session
import logging

from app.config import settings
from app.database.session import get_db
from app.models.database import (
    Scenario, ScenarioTag, Build, TestStatus,
    Feature, TestRun, Step
)
from app.models.schemas import ResultsResponse, FeatureStats, TagStats

logger = logging.getLogger("friday.results")
router = APIRouter(prefix=settings.API_PREFIX, tags=["stats"])


@router.get("/results", response_model=ResultsResponse)
async def get_test_results(
        build_id: Optional[UUID] = Query(None, description="Filter by build ID"),
        test_run_id: Optional[int] = Query(None, description="Filter by test run ID"),
        feature_name: Optional[str] = Query(None, description="Filter by feature name"),
        start_date: Optional[datetime] = Query(None, description="Filter by start date"),
        end_date: Optional[datetime] = Query(None, description="Filter by end date"),
        limit_days: Optional[int] = Query(30, description="Limit results to last N days"),
        tag: Optional[str] = Query(None, description="Filter by specific tag"),
        status: Optional[str] = Query(None, description="Filter by status (PASSED, FAILED, SKIPPED)"),
        project_id: Optional[int] = Query(None, description="Filter by project ID"),
        environment: Optional[str] = Query(None, description="Filter by environment"),
        background_tasks: BackgroundTasks = BackgroundTasks(),
        db: Session = Depends(get_db)
):
    """
    Get detailed test results with statistics grouped by features and tags.

    Supports filtering by various parameters including build ID, test run ID,
    feature name, tag, status, project ID, or date range.
    Results include overall statistics, feature-based stats, and tag-based analysis.
    """
    logger.info(
        f"Processing results request with filters: build_id={build_id}, test_run_id={test_run_id}, feature={feature_name}, tag={tag}")

    try:
        # Set default date range if not provided
        if not end_date:
            end_date = datetime.utcnow()

        if not start_date and limit_days:
            start_date = end_date - timedelta(days=limit_days)

        # Determine if we're querying the UUID or Integer ID based tables
        # Based on your model imports, we'll use the Scenario model with the UUID primary key

        # Base query filter conditions
        filter_conditions = []

        # Time-based filters
        if start_date:
            # Check if the model has start_time or date field
            if hasattr(Scenario, 'start_time'):
                filter_conditions.append(Scenario.start_time >= start_date)
            else:
                filter_conditions.append(Scenario.created_at >= start_date)

        if end_date:
            if hasattr(Scenario, 'end_time'):
                filter_conditions.append(Scenario.end_time <= end_date)
            else:
                filter_conditions.append(Scenario.created_at <= end_date)

        # ID-based filters
        if build_id:
            filter_conditions.append(Scenario.build_id == build_id)

        if test_run_id:
            filter_conditions.append(Scenario.test_run_id == test_run_id)

        if project_id:
            # If Scenario doesn't have project_id directly, we need to join with TestRun
            if hasattr(Scenario, 'test_run_id'):
                filter_conditions.append(Scenario.test_run.has(TestRun.project_id == project_id))

        # Text-based filters
        if feature_name:
            # If we have a Feature relationship, use that
            if hasattr(Scenario, 'feature_id'):
                filter_conditions.append(Scenario.feature.has(Feature.name.ilike(f"%{feature_name}%")))
            else:
                # Otherwise, assume Scenario has a direct feature field
                filter_conditions.append(Scenario.feature.ilike(f"%{feature_name}%"))

        if status:
            # Convert to the correct Enum if using enum type
            filter_conditions.append(Scenario.status == status)

        if environment and hasattr(Scenario, 'environment'):
            filter_conditions.append(Scenario.environment == environment)
        elif environment and hasattr(Scenario, 'test_run'):
            # Try to filter through TestRun if Scenario doesn't have environment directly
            filter_conditions.append(Scenario.test_run.has(TestRun.environment == environment))

        # Store base filter conditions before adding tag filter
        # We'll need this for some queries that require different join logic
        base_filter_conditions = filter_conditions.copy()

        # Tag filter requires a join with scenario_tags table
        tag_filter = None
        if tag:
            tag_filter = ScenarioTag.tag == tag

        # Get overall statistics
        stats_query = db.query(
            func.count(Scenario.id).label("total"),
            func.sum(case(
                [(Scenario.status == TestStatus.PASSED, 1)],
                else_=0
            )).label("passed"),
            func.sum(case(
                [(Scenario.status == TestStatus.FAILED, 1)],
                else_=0
            )).label("failed"),
            func.sum(case(
                [(Scenario.status == TestStatus.SKIPPED, 1)],
                else_=0
            )).label("skipped"),
            func.max(Scenario.updated_at).label("last_updated")
        )

        # Apply filters differently based on whether we have a tag filter
        if tag_filter:
            stats_query = stats_query.join(
                ScenarioTag, Scenario.id == ScenarioTag.scenario_id
            ).filter(tag_filter)

        # Apply the base filters
        stats_query = stats_query.filter(*filter_conditions)

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

        # Get feature statistics
        # This depends on whether we have a feature relationship or just a feature field
        if hasattr(Scenario, 'feature_id'):
            # If we have a feature relationship
            feature_stats_query = db.query(
                Feature.name.label("feature_name"),
                func.count(Scenario.id).label("total"),
                func.sum(case(when=Scenario.status == TestStatus.PASSED, then=1, else_=0)).label("passed"),
                func.sum(case(when=Scenario.status == TestStatus.FAILED, then=1, else_=0)).label("failed"),
                func.sum(case(when=Scenario.status == TestStatus.SKIPPED, then=1, else_=0)).label("skipped")
            ).join(
                Feature, Scenario.feature_id == Feature.id
            )
        else:
            # If scenario has a direct feature field
            feature_stats_query = db.query(
                Scenario.feature.label("feature_name"),
                func.count(Scenario.id).label("total"),
                func.sum(case(when=Scenario.status == TestStatus.PASSED, then=1, else_=0)).label("passed"),
                func.sum(case(when=Scenario.status == TestStatus.FAILED, then=1, else_=0)).label("failed"),
                func.sum(case(when=Scenario.status == TestStatus.SKIPPED, then=1, else_=0)).label("skipped")
            )

        # Apply tag filter if necessary
        if tag_filter:
            feature_stats_query = feature_stats_query.join(
                ScenarioTag, Scenario.id == ScenarioTag.scenario_id
            ).filter(tag_filter)

        # Apply base filters and group by
        feature_stats_query = feature_stats_query.filter(*filter_conditions)

        # Group by the correct field based on which query we're using
        if hasattr(Scenario, 'feature_id'):
            feature_stats_query = feature_stats_query.group_by(Feature.name)
        else:
            feature_stats_query = feature_stats_query.group_by(Scenario.feature)

        # Order by count, descending
        feature_stats_query = feature_stats_query.order_by(func.count(Scenario.id).desc())

        # Format feature stats for response
        feature_stats = []
        for f in feature_stats_query.all():
            feature_stats.append({
                "name": f.feature_name or "Unknown",
                "passed_scenarios": f.passed or 0,
                "failed_scenarios": f.failed or 0,
                "skipped_scenarios": f.skipped or 0
            })

        # Get tag statistics - this requires a join with the scenario_tags table
        tag_stats_query = db.query(
            ScenarioTag.tag,
            func.count(distinct(Scenario.id)).label("count"),
            func.sum(case(when=Scenario.status == TestStatus.PASSED, then=1, else_=0)).label("passed"),
            func.sum(case(when=Scenario.status == TestStatus.FAILED, then=1, else_=0)).label("failed"),
            func.sum(case(when=Scenario.status == TestStatus.SKIPPED, then=1, else_=0)).label("skipped")
        ).join(
            Scenario, ScenarioTag.scenario_id == Scenario.id
        )

        # Apply filters
        if tag_filter:
            # If we're already filtering by tag, we need to adjust the query
            tag_stats_query = tag_stats_query.filter(tag_filter)

        # Apply the rest of the filters
        tag_stats_query = tag_stats_query.filter(*filter_conditions) \
            .group_by(ScenarioTag.tag) \
            .order_by(func.count(distinct(Scenario.id)).desc())  # Order by count, descending

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
        # Log the exception
        import logging
        logging.error(f"Error retrieving test results: {str(e)}", exc_info=True)

        # Return an error response
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve test results: {str(e)}"
        )
