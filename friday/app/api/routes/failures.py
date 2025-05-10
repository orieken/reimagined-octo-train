from fastapi import APIRouter, Depends, HTTPException, Query, Path
from typing import List, Dict, Any, Optional, Union
from datetime import datetime, timedelta
from uuid import UUID
import logging
from collections import Counter
from sqlalchemy import select, and_, or_, desc, func
from sqlalchemy.orm import selectinload
from qdrant_client.http import models as qdrant_models
import re

from app.config import settings
from app.services.orchestrator import ServiceOrchestrator
from app.api.dependencies import get_orchestrator_service
from app.services import datetime_service as dt
from app.services.failure_analysis_service import FailureAnalysisService
from app.models.database import (
    TestRun as DBTestRun,
    Scenario as DBScenario,
    Step as DBStep,
    Feature as DBFeature,
    ScenarioTag as DBScenarioTag,
    TestStatus
)
from app.models.responses import PaginatedResponse, SearchResponse

logger = logging.getLogger(__name__)

# Initialize the failure analysis service
failure_service = FailureAnalysisService()

router = APIRouter(prefix=settings.API_PREFIX, tags=["failures"])


# Helper function to extract error info from a scenario
def extract_error_info(scenario: DBScenario) -> Dict[str, Any]:
    """Extract error information from scenario steps."""
    error_info = {
        "message": None,
        "stack_trace": None,
        "step_name": None
    }

    if hasattr(scenario, "steps") and scenario.steps:
        for step in scenario.steps:
            if step.status == TestStatus.FAILED or str(
                    step.status) == 'TestStatus.FAILED' or step.status == TestStatus.ERROR or str(
                    step.status) == 'TestStatus.ERROR':
                error_info["message"] = step.error_message
                error_info["stack_trace"] = step.stack_trace
                error_info["step_name"] = step.name
                break

    return error_info


# Helper function to get historical data for a scenario
async def get_historical_failure_data(scenario_name: str, session) -> Dict[str, Any]:
    """Get historical data for a scenario by name."""
    try:
        # Query for scenarios with the same name
        query = (
            select(DBScenario)
            .where(DBScenario.name == scenario_name)
            .order_by(desc(DBScenario.created_at))
            .limit(50)  # Get last 50 runs
        )

        result = await session.execute(query)
        scenarios = result.scalars().all()

        if not scenarios:
            return {
                "total_runs": 0,
                "failure_rate": 0,
                "recent_history": []
            }

        # Calculate statistics
        total_runs = len(scenarios)
        failed_runs = sum(1 for s in scenarios if s.status == TestStatus.FAILED or str(s.status) == 'TestStatus.FAILED')
        failure_rate = failed_runs / total_runs if total_runs > 0 else 0

        # Get detailed history for last 10 runs
        recent_history = []
        for scenario in scenarios[:10]:
            # Get test run info
            test_run_query = select(DBTestRun).where(DBTestRun.id == scenario.test_run_id)
            test_run_result = await session.execute(test_run_query)
            test_run = test_run_result.scalar_one_or_none()

            # Extract error if failed
            error_message = None
            if scenario.status == TestStatus.FAILED or str(scenario.status) == 'TestStatus.FAILED':
                error_info = extract_error_info(scenario)
                error_message = error_info.get("message")

            recent_history.append({
                "id": str(scenario.id),
                "status": str(scenario.status),
                "date": dt.isoformat_utc(scenario.created_at),
                "environment": test_run.environment if test_run else None,
                "duration": scenario.duration,
                "error_message": error_message
            })

        # Check if scenario is flaky
        is_flaky = False
        last_statuses = [s.status for s in scenarios[:5]]
        if len(last_statuses) >= 3:
            # If we have both passes and failures in last 5 runs, it's flaky
            statuses_str = [str(status) for status in last_statuses]
            has_passed = any(s == str(TestStatus.PASSED) or s == 'TestStatus.PASSED' for s in statuses_str)
            has_failed = any(s == str(TestStatus.FAILED) or s == 'TestStatus.FAILED' for s in statuses_str)
            is_flaky = has_passed and has_failed

        return {
            "total_runs": total_runs,
            "failure_rate": failure_rate,
            "is_flaky": is_flaky,
            "recent_history": recent_history
        }

    except Exception as e:
        logger.error(f"Error retrieving historical data: {str(e)}", exc_info=True)
        return {
            "total_runs": 0,
            "failure_rate": 0,
            "recent_history": []
        }


# IMPORTANT: Fixed path routes need to be defined BEFORE path parameter routes
@router.get("/failures/summary", response_model=Dict[str, Any])
async def get_failure_summary(
        days: int = Query(7, description="Number of days to analyze"),
        environment: Optional[str] = Query(None, description="Filter by environment"),
        project_id: Optional[UUID] = Query(None, description="Filter by project ID"),
        orchestrator: ServiceOrchestrator = Depends(get_orchestrator_service)
):
    """
    Get a summary of test failures.
    """
    try:
        # Set cutoff date for filtering
        cutoff_date = dt.now_utc() - timedelta(days=days) if days > 0 else None

        async with orchestrator.pg_service.session() as session:
            # Build query to get scenarios
            base_query = (
                select(DBScenario)
                .join(DBTestRun, DBScenario.test_run_id == DBTestRun.id)
            )

            # Apply filters
            filters = []

            if cutoff_date:
                filters.append(DBTestRun.created_at >= cutoff_date)

            if project_id:
                filters.append(DBTestRun.project_id == project_id)

            if environment:
                filters.append(DBTestRun.environment == environment)

            # Apply all filters
            if filters:
                base_query = base_query.where(and_(*filters))

            # Execute query
            result = await session.execute(base_query)
            scenarios = result.scalars().all()

            if not scenarios:
                return {
                    "status": "success",
                    "summary": {
                        "total_scenarios": 0,
                        "failed_scenarios": 0,
                        "total_test_runs": 0,
                        "failure_rate": 0,
                        "most_common_failures": [],
                        "flaky_scenarios": []
                    }
                }

            # Calculate statistics
            total_scenarios = len(scenarios)
            failed_scenarios = sum(
                1 for s in scenarios
                if s.status == TestStatus.FAILED or str(s.status) == 'TestStatus.FAILED'
            )

            # Count distinct test runs
            test_run_ids = set(s.test_run_id for s in scenarios)
            total_test_runs = len(test_run_ids)

            # Calculate failure rate
            failure_rate = failed_scenarios / total_scenarios if total_scenarios > 0 else 0

            # Find most common failures
            failed_scenarios_list = [
                s for s in scenarios
                if s.status == TestStatus.FAILED or str(s.status) == 'TestStatus.FAILED'
            ]

            # Group failures by scenario name
            failure_counts = {}
            for scenario in failed_scenarios_list:
                name = scenario.name
                if name not in failure_counts:
                    failure_counts[name] = {
                        "name": name,
                        "count": 0,
                        "id": str(scenario.id),
                        "last_failed": scenario.created_at
                    }
                failure_counts[name]["count"] += 1

                # Update last failed date if this scenario is more recent
                if scenario.created_at > failure_counts[name]["last_failed"]:
                    failure_counts[name]["last_failed"] = scenario.created_at
                    failure_counts[name]["id"] = str(scenario.id)

            # Sort failures by count
            most_common_failures = sorted(
                failure_counts.values(),
                key=lambda x: x["count"],
                reverse=True
            )[:10]  # Top 10 failures

            # Format the last_failed date
            for failure in most_common_failures:
                failure["last_failed"] = dt.isoformat_utc(failure["last_failed"])

            # Find flaky scenarios
            # For this, we need to query scenarios by name and check if they have mixed statuses
            flaky_scenarios = []

            # Get distinct scenario names
            scenario_names = set(s.name for s in scenarios)

            # Check each scenario name
            for name in scenario_names:
                name_scenarios = [s for s in scenarios if s.name == name]
                if len(name_scenarios) >= 3:  # Need at least 3 runs to determine flakiness
                    statuses = [str(s.status) for s in name_scenarios]
                    # If both PASSED and FAILED statuses exist, it's flaky
                    has_passed = any(s == str(TestStatus.PASSED) or s == 'TestStatus.PASSED' for s in statuses)
                    has_failed = any(s == str(TestStatus.FAILED) or s == 'TestStatus.FAILED' for s in statuses)

                    if has_passed and has_failed:
                        # Get the most recent scenario instance
                        latest = max(name_scenarios, key=lambda s: s.created_at)

                        # Calculate flakiness rate
                        failed_count = sum(
                            1 for s in name_scenarios
                            if s.status == TestStatus.FAILED or str(s.status) == 'TestStatus.FAILED'
                        )
                        flakiness_rate = failed_count / len(name_scenarios)

                        flaky_scenarios.append({
                            "id": str(latest.id),
                            "name": name,
                            "total_runs": len(name_scenarios),
                            "failed_runs": failed_count,
                            "flakiness_rate": round(flakiness_rate, 2),
                            "last_run": dt.isoformat_utc(latest.created_at)
                        })

            # Sort flaky scenarios by flakiness rate
            flaky_scenarios.sort(key=lambda x: x["flakiness_rate"], reverse=True)

            return {
                "status": "success",
                "summary": {
                    "total_scenarios": total_scenarios,
                    "failed_scenarios": failed_scenarios,
                    "total_test_runs": total_test_runs,
                    "failure_rate": round(failure_rate, 4),
                    "most_common_failures": most_common_failures,
                    "flaky_scenarios": flaky_scenarios
                }
            }

    except Exception as e:
        logger.error(f"Error retrieving failure summary: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to retrieve failure summary: {str(e)}")


@router.get("/failures/rag", response_model=Dict[str, Any])
async def get_failures_for_rag(
        query: str = Query(..., description="Semantic search query for test failures"),
        days: int = Query(30, description="Number of days to analyze"),
        environment: Optional[str] = Query(None, description="Filter by environment"),
        project_id: Optional[UUID] = Query(None, description="Filter by project ID"),
        feature_name: Optional[str] = Query(None, description="Filter by feature name"),
        tag: Optional[str] = Query(None, description="Filter by tag"),
        limit: int = Query(5, description="Number of results to return"),
        orchestrator: ServiceOrchestrator = Depends(get_orchestrator_service)
):
    """
    Specialized endpoint for RAG (Retrieval-Augmented Generation) applications.

    Returns semantically relevant test failures with detailed context formatted
    for use in AI assistant applications.
    """
    try:
        logger.info(f"Starting RAG failures query: '{query}'")

        # Generate embedding for query
        query_embedding = await orchestrator.llm.embed_text(query)

        # First search vector DB
        scenario_ids = None
        similarity_scores = {}

        try:
            # Search vector DB for scenarios
            search_results = orchestrator.vector_db.client.search(
                collection_name=orchestrator.vector_db.cucumber_collection,
                query_vector=query_embedding,
                query_filter=qdrant_models.Filter(
                    must=[
                        qdrant_models.FieldCondition(
                            key="type",
                            match=qdrant_models.MatchValue(value="scenario")
                        ),
                        qdrant_models.FieldCondition(
                            key="status",
                            match=qdrant_models.MatchValue(value="FAILED")
                        )
                    ]
                ),
                limit=25  # Get more than needed to apply filters
            )

            # Extract scenario IDs and scores
            if search_results:
                scenario_ids = [UUID(r.id) for r in search_results]
                similarity_scores = {UUID(r.id): r.score for r in search_results}
                logger.info(f"Vector search found {len(scenario_ids)} matching scenarios")
            else:
                logger.info("Vector search returned no results")
                return {
                    "query": query,
                    "results": [],
                    "context": "No test failures found matching your query."
                }
        except Exception as e:
            logger.error(f"Vector search failed: {str(e)}", exc_info=True)
            return {
                "query": query,
                "results": [],
                "context": f"Error searching for test failures: {str(e)}"
            }

        # Now fetch full details from PostgreSQL
        async with orchestrator.pg_service.session() as session:
            # Build SQL query for scenarios
            results = []

            if scenario_ids:
                cutoff_date = dt.now_utc() - timedelta(days=days) if days > 0 else None

                # Base query
                base_query = (
                    select(DBScenario)
                    .options(
                        selectinload(DBScenario.steps),
                        selectinload(DBScenario.tags)
                    )
                    .join(DBTestRun, DBScenario.test_run_id == DBTestRun.id)
                    .outerjoin(DBFeature, DBScenario.feature_id == DBFeature.id)
                    .where(DBScenario.id.in_(scenario_ids))
                )

                # Apply additional filters
                filters = []

                if cutoff_date:
                    filters.append(DBTestRun.created_at >= cutoff_date)

                if project_id:
                    filters.append(DBTestRun.project_id == project_id)

                if environment:
                    filters.append(DBTestRun.environment == environment)

                if feature_name:
                    filters.append(DBFeature.name.ilike(f"%{feature_name}%"))

                if tag:
                    tag_subquery = (
                        select(DBScenarioTag.scenario_id)
                        .where(DBScenarioTag.tag == tag)
                        .scalar_subquery()
                    )
                    filters.append(DBScenario.id.in_(tag_subquery))

                if filters:
                    base_query = base_query.where(and_(*filters))

                # Execute query
                result = await session.execute(base_query)
                scenarios = result.scalars().all()

                # Sort by similarity score since this is a semantic query
                scenarios.sort(key=lambda s: similarity_scores.get(s.id, 0), reverse=True)

                # Process top results
                for scenario in scenarios[:limit]:
                    # Get test run info
                    test_run_query = select(DBTestRun).where(DBTestRun.id == scenario.test_run_id)
                    test_run_result = await session.execute(test_run_query)
                    test_run = test_run_result.scalar_one_or_none()

                    # Get feature info
                    feature = None
                    if scenario.feature_id:
                        feature_query = select(DBFeature).where(DBFeature.id == scenario.feature_id)
                        feature_result = await session.execute(feature_query)
                        feature = feature_result.scalar_one_or_none()

                    # Process steps
                    steps = []
                    for step in sorted(scenario.steps, key=lambda s: s.order or ""):
                        steps.append({
                            "name": step.name,
                            "keyword": step.keyword,
                            "status": str(step.status),
                            "error_message": step.error_message,
                        })

                    # Find error information
                    error_info = extract_error_info(scenario)

                    # Determine failure category
                    category = failure_service.categorize_error(
                        error_info.get("message"),
                        scenario.name
                    )

                    # Gather additional context
                    tags = [tag.tag for tag in scenario.tags] if scenario.tags else []

                    # Get historical failure data for context
                    historical_data = await get_historical_failure_data(scenario.name, session)

                    # Add to results
                    results.append({
                        "id": str(scenario.id),
                        "name": scenario.name,
                        "similarity_score": similarity_scores.get(scenario.id, 0),
                        "status": str(scenario.status),
                        "created_at": dt.isoformat_utc(scenario.created_at),
                        "test_run": {
                            "name": test_run.name if test_run else None,
                            "environment": test_run.environment if test_run else None,
                            "branch": test_run.branch if test_run else None,
                        },
                        "feature": {
                            "name": feature.name if feature else None,
                        },
                        "steps": steps,
                        "tags": tags,
                        "error": {
                            "message": error_info.get("message"),
                            "category": category,
                            "step_name": error_info.get("step_name"),
                        },
                        "history": {
                            "total_runs": historical_data.get("total_runs", 0),
                            "failure_rate": historical_data.get("failure_rate", 0),
                            "is_flaky": historical_data.get("is_flaky", False),
                        }
                    })

            # Generate summary context
            context = ""
            if results:
                context = f"Found {len(results)} test failures related to '{query}'.\n\n"

                # Add common features among results
                features = [r["feature"]["name"] for r in results if r["feature"]["name"]]
                if features:
                    feature_counts = Counter(features)
                    top_features = feature_counts.most_common(3)
                    context += "Most common affected features: " + ", ".join(
                        f"{feature} ({count})" for feature, count in top_features
                    ) + ".\n"

                # Add common error categories
                categories = [r["error"]["category"] for r in results if r["error"]["category"]]
                if categories:
                    category_counts = Counter(categories)
                    top_categories = category_counts.most_common(3)
                    context += "Common error types: " + ", ".join(
                        f"{category} ({count})" for category, count in top_categories
                    ) + ".\n"

                # Add flakiness info
                flaky_count = sum(1 for r in results if r["history"]["is_flaky"])
                if flaky_count > 0:
                    context += f"{flaky_count} of these failures appear to be flaky tests.\n"
            else:
                context = f"No test failures found matching '{query}' with the specified filters."

            return {
                "query": query,
                "results": results,
                "context": context
            }

    except Exception as e:
        logger.error(f"Error retrieving RAG failures data: {str(e)}", exc_info=True)
        return {
            "query": query,
            "results": [],
            "context": f"Error retrieving failure data: {str(e)}"
        }


@router.get("/failures/trends", response_model=Dict[str, Any])
async def get_failure_trends(
        days: int = Query(30, description="Number of days to analyze"),
        environment: Optional[str] = Query(None, description="Filter by environment"),
        project_id: Optional[UUID] = Query(None, description="Filter by project ID"),
        feature_id: Optional[UUID] = Query(None, description="Filter by feature ID"),
        tag: Optional[str] = Query(None, description="Filter by tag"),
        orchestrator: ServiceOrchestrator = Depends(get_orchestrator_service)
):
    """
    Get failure trends over time.
    """
    try:
        # Set cutoff date for filtering
        cutoff_date = dt.now_utc() - timedelta(days=days) if days > 0 else None

        async with orchestrator.pg_service.session() as session:
            # Build base query
            base_query = (
                select(DBTestRun)
                .options(
                    selectinload(DBTestRun.scenarios)
                )
            )

            # Apply filters
            filters = []

            if cutoff_date:
                filters.append(DBTestRun.created_at >= cutoff_date)

            if project_id:
                filters.append(DBTestRun.project_id == project_id)

            if environment:
                filters.append(DBTestRun.environment == environment)

            # Apply all filters to query
            if filters:
                base_query = base_query.where(and_(*filters))

            # Sort by date
            base_query = base_query.order_by(DBTestRun.created_at)

            # Execute query
            result = await session.execute(base_query)
            test_runs = result.scalars().all()

            if not test_runs:
                return {
                    "status": "success",
                    "data": {
                        "dates": [],
                        "failure_rates": [],
                        "total_tests": [],
                        "failed_tests": []
                    }
                }

            # Feature filter - needs to be applied post-query
            if feature_id:
                for i, test_run in enumerate(test_runs):
                    filtered_scenarios = [s for s in test_run.scenarios if s.feature_id == feature_id]
                    test_runs[i].scenarios = filtered_scenarios

            # Tag filter - needs to be applied post-query
            if tag:
                # Get all scenario IDs with the specified tag
                tag_query = select(DBScenarioTag.scenario_id).where(DBScenarioTag.tag == tag)
                tag_result = await session.execute(tag_query)
                tagged_scenario_ids = set(result.scalar() for result in tag_result)

                for i, test_run in enumerate(test_runs):
                    filtered_scenarios = [s for s in test_run.scenarios if s.id in tagged_scenario_ids]
                    test_runs[i].scenarios = filtered_scenarios

            # Group by day
            daily_data = {}
            for test_run in test_runs:
                # Skip if no scenarios after filtering
                if not test_run.scenarios:
                    continue

                # Get date string for grouping
                date_str = test_run.created_at.strftime("%Y-%m-%d")

                if date_str not in daily_data:
                    daily_data[date_str] = {
                        "date": date_str,
                        "total_tests": 0,
                        "failed_tests": 0,
                        "passed_tests": 0,
                        "test_runs": 0
                    }

                # Count scenarios
                total = len(test_run.scenarios)
                failed = sum(1 for s in test_run.scenarios
                             if s.status == TestStatus.FAILED or str(s.status) == 'TestStatus.FAILED')
                passed = sum(1 for s in test_run.scenarios
                             if s.status == TestStatus.PASSED or str(s.status) == 'TestStatus.PASSED')

                # Update daily counts
                daily_data[date_str]["total_tests"] += total
                daily_data[date_str]["failed_tests"] += failed
                daily_data[date_str]["passed_tests"] += passed
                daily_data[date_str]["test_runs"] += 1

            # Sort by date
            sorted_dates = sorted(daily_data.keys())
            sorted_data = [daily_data[date] for date in sorted_dates]

            # Calculate failure rates
            dates = []
            failure_rates = []
            total_tests = []
            failed_tests = []

            for data in sorted_data:
                dates.append(data["date"])
                total = data["total_tests"]
                failed = data["failed_tests"]

                failure_rate = round(failed / total, 4) if total > 0 else 0
                failure_rates.append(failure_rate)
                total_tests.append(total)
                failed_tests.append(failed)

            return {
                "status": "success",
                "data": {
                    "dates": dates,
                    "failure_rates": failure_rates,
                    "total_tests": total_tests,
                    "failed_tests": failed_tests
                }
            }

    except Exception as e:
        logger.error(f"Error retrieving failure trends: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to retrieve failure trends: {str(e)}")


# Main failures endpoint with the format specified in the story
@router.get("/failures", response_model=Dict[str, Any])
async def get_failures(
        days: int = Query(30, description="Number of days to analyze"),
        environment: Optional[str] = Query(None, description="Filter by environment"),
        project_id: Optional[UUID] = Query(None, description="Filter by project ID"),
        feature_id: Optional[UUID] = Query(None, description="Filter by feature ID"),
        feature_name: Optional[str] = Query(None, description="Filter by feature name"),
        tag: Optional[str] = Query(None, description="Filter by tag"),
        build_id: Optional[str] = Query(None, description="Filter by build ID"),
        recent_limit: int = Query(10, description="Number of recent failures to return"),
        query: Optional[str] = Query(None, description="Semantic search query"),
        orchestrator: ServiceOrchestrator = Depends(get_orchestrator_service)
):
    """
    Get analysis of test failures with categorization and trends.

    This endpoint provides a comprehensive analysis of test failures including
    categorization, common failure patterns, feature-level analysis, and recent failures.
    """
    try:
        logger.info(f"Starting failures analysis with params: days={days}")

        # Set cutoff date for filtering
        cutoff_date = dt.now_utc() - timedelta(days=days) if days > 0 else None

        # If semantic query provided, first search vector DB
        scenario_ids = None

        if query and query.strip():
            logger.info(f"Performing semantic search for: '{query}'")
            try:
                # Generate embedding for query
                query_embedding = await orchestrator.llm.embed_text(query)

                # Search vector DB for scenarios
                search_results = orchestrator.vector_db.client.search(
                    collection_name=orchestrator.vector_db.cucumber_collection,
                    query_vector=query_embedding,
                    query_filter=qdrant_models.Filter(
                        must=[
                            qdrant_models.FieldCondition(
                                key="type",
                                match=qdrant_models.MatchValue(value="scenario")
                            ),
                            qdrant_models.FieldCondition(
                                key="status",
                                match=qdrant_models.MatchValue(value="FAILED")
                            )
                        ]
                    ),
                    limit=100  # Get more results than needed to apply additional filters
                )

                # Extract scenario IDs
                if search_results:
                    scenario_ids = [UUID(r.id) for r in search_results]
                    logger.info(f"Vector search found {len(scenario_ids)} matching scenarios")
                else:
                    logger.info("Vector search returned no results")
                    return {
                        "status": "success",
                        "failures": {
                            "total_failures": 0,
                            "categories": [],
                            "details": {},
                            "by_feature": [],
                            "recent": []
                        }
                    }
            except Exception as e:
                logger.error(f"Vector search failed: {str(e)}", exc_info=True)
                logger.warning("Falling back to SQL-only search")
                # Continue with SQL-only approach

        async with orchestrator.pg_service.session() as session:
            # Build SQL query for failed scenarios
            base_query = (
                select(DBScenario)
                .options(
                    selectinload(DBScenario.steps),
                    selectinload(DBScenario.tags)
                )
                .join(DBTestRun, DBScenario.test_run_id == DBTestRun.id)
                .outerjoin(DBFeature, DBScenario.feature_id == DBFeature.id)
                .where(DBScenario.status == TestStatus.FAILED)
            )

            # Apply filters
            filters = []

            # Date filter
            if cutoff_date:
                filters.append(DBTestRun.created_at >= cutoff_date)

            # Vector search ID filter
            if scenario_ids:
                filters.append(DBScenario.id.in_(scenario_ids))

            # Project filter
            if project_id:
                filters.append(DBTestRun.project_id == project_id)

            # Environment filter
            if environment:
                filters.append(DBTestRun.environment == environment)

            # Feature filters
            if feature_id:
                filters.append(DBScenario.feature_id == feature_id)
            if feature_name:
                filters.append(DBFeature.name.ilike(f"%{feature_name}%"))

            # Tag filter
            if tag:
                tag_subquery = (
                    select(DBScenarioTag.scenario_id)
                    .where(DBScenarioTag.tag == tag)
                    .scalar_subquery()
                )
                filters.append(DBScenario.id.in_(tag_subquery))

            # Build filter
            if build_id:
                filters.append(DBTestRun.external_id == build_id)

            # Apply all filters to query
            if filters:
                base_query = base_query.where(and_(*filters))

            # Execute query for failed scenarios
            result = await session.execute(base_query)
            scenarios = result.scalars().all()

            # Get total test count (including passes) for calculating rates
            total_query = (
                select(DBScenario)
                .join(DBTestRun, DBScenario.test_run_id == DBTestRun.id)
                .outerjoin(DBFeature, DBScenario.feature_id == DBFeature.id)
            )

            # Apply the same filters except status
            if filters:
                total_query = total_query.where(and_(*filters))

            total_result = await session.execute(total_query)
            all_scenarios = total_result.scalars().all()

            logger.info(f"Found {len(scenarios)} failed scenarios out of {len(all_scenarios)} total scenarios")

            if not scenarios:
                return {
                    "status": "success",
                    "failures": {
                        "total_failures": 0,
                        "categories": [],
                        "details": {},
                        "by_feature": [],
                        "recent": []
                    }
                }

            # 1. Calculate failure categories
            categories = {}
            details = {}

            for scenario in scenarios:
                # Get error info from failed steps
                error_info = extract_error_info(scenario)
                error_message = error_info.get("message")

                # Get feature info
                feature_name = None
                if scenario.feature_id:
                    feature_query = select(DBFeature).where(DBFeature.id == scenario.feature_id)
                    feature_result = await session.execute(feature_query)
                    feature = feature_result.scalar_one_or_none()
                    if feature:
                        feature_name = feature.name

                # Determine failure category
                category = failure_service.categorize_error(error_message, scenario.name)
                if not category:
                    category = "Unknown"

                # Increment category count
                if category not in categories:
                    categories[category] = 0
                categories[category] += 1

                # Extract failing element based on error message and category
                element = failure_service.extract_element(error_message, category, scenario.name, feature_name)

                # Add to details
                if category not in details:
                    details[category] = {}

                if element not in details[category]:
                    details[category][element] = {
                        "element": element,
                        "occurrences": 0,
                        "scenarios": set()
                    }

                details[category][element]["occurrences"] += 1
                details[category][element]["scenarios"].add(scenario.name)

            # Format categories
            total_failures = len(scenarios)
            category_list = []

            for category, count in sorted(categories.items(), key=lambda x: x[1], reverse=True):
                percentage = round(count / total_failures * 100, 1) if total_failures > 0 else 0
                category_list.append({
                    "name": category,
                    "count": count,
                    "percentage": percentage
                })

            # Format details
            details_dict = {}
            for category, elements in details.items():
                details_dict[category] = []
                for element, data in sorted(elements.items(), key=lambda x: x[1]["occurrences"], reverse=True):
                    details_dict[category].append({
                        "element": element,
                        "occurrences": data["occurrences"],
                        "scenarios": list(data["scenarios"])[:5]  # Limit to 5 examples
                    })

            # 2. Analyze failures by feature
            feature_stats = {}

            # Get all feature IDs
            feature_ids = set(s.feature_id for s in all_scenarios if s.feature_id)

            # Fetch feature info
            for feature_id in feature_ids:
                feature_query = select(DBFeature).where(DBFeature.id == feature_id)
                feature_result = await session.execute(feature_query)
                feature = feature_result.scalar_one_or_none()

                if feature:
                    # Count tests and failures for this feature
                    feature_tests = [s for s in all_scenarios if s.feature_id == feature_id]
                    feature_failures = [s for s in scenarios if s.feature_id == feature_id]

                    if feature_tests:
                        feature_stats[feature.name] = {
                            "feature": feature.name,
                            "failures": len(feature_failures),
                            "tests": len(feature_tests),
                            "failure_rate": round(len(feature_failures) / len(feature_tests), 3)
                        }

            # Sort features by failure count
            by_feature = sorted(
                feature_stats.values(),
                key=lambda x: x["failures"],
                reverse=True
            )

            # 3. Get recent failures
            recent_query = (
                select(DBScenario)
                .options(
                    selectinload(DBScenario.steps)
                )
                .join(DBTestRun, DBScenario.test_run_id == DBTestRun.id)
                .where(DBScenario.status == TestStatus.FAILED)
                .order_by(desc(DBScenario.created_at))
                .limit(recent_limit)
            )

            # Apply the same filters
            if filters:
                recent_query = recent_query.where(and_(*filters))

            recent_result = await session.execute(recent_query)
            recent_scenarios = recent_result.scalars().all()

            recent_failures = []
            for scenario in recent_scenarios:
                # Get test run info
                test_run_query = select(DBTestRun).where(DBTestRun.id == scenario.test_run_id)
                test_run_result = await session.execute(test_run_query)
                test_run = test_run_result.scalar_one_or_none()

                error_info = extract_error_info(scenario)

                recent_failures.append({
                    "id": str(scenario.id),
                    "scenario": scenario.name,
                    "error": error_info.get("message") or "Unknown error",
                    "date": dt.isoformat_utc(scenario.created_at),
                    "build": test_run.external_id if test_run else "Unknown"
                })

            return {
                "status": "success",
                "failures": {
                    "total_failures": total_failures,
                    "categories": category_list,
                    "details": details_dict,
                    "by_feature": by_feature,
                    "recent": recent_failures
                }
            }

    except Exception as e:
        logger.error(f"Error retrieving failures data: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to retrieve failures data: {str(e)}")


@router.get("/failures/{scenario_id}", response_model=Dict[str, Any])
async def get_failure_details(
        scenario_id: UUID = Path(..., description="Scenario ID"),
        orchestrator: ServiceOrchestrator = Depends(get_orchestrator_service)
):
    """
    Get detailed information about a specific test failure.
    """
    try:
        async with orchestrator.pg_service.session() as session:
            # Query scenario with related steps
            query = (
                select(DBScenario)
                .options(
                    selectinload(DBScenario.steps),
                    selectinload(DBScenario.tags)
                )
                .where(DBScenario.id == scenario_id)
            )

            result = await session.execute(query)
            scenario = result.scalar_one_or_none()

            if not scenario:
                raise HTTPException(status_code=404, detail="Scenario not found")

            # Get test run info
            test_run_query = select(DBTestRun).where(DBTestRun.id == scenario.test_run_id)
            test_run_result = await session.execute(test_run_query)
            test_run = test_run_result.scalar_one_or_none()

            # Get feature info
            feature = None
            if scenario.feature_id:
                feature_query = select(DBFeature).where(DBFeature.id == scenario.feature_id)
                feature_result = await session.execute(feature_query)
                feature = feature_result.scalar_one_or_none()

            # Process steps
            steps = []
            for step in sorted(scenario.steps, key=lambda s: s.order or ""):
                steps.append({
                    "id": str(step.id),
                    "name": step.name,
                    "keyword": step.keyword,
                    "status": str(step.status),
                    "duration": step.duration,
                    "error_message": step.error_message,
                    "stack_trace": step.stack_trace,
                    "order": step.order
                })

            # Check for semantic similarity to other failures
            similar_failures = []
            if orchestrator.vector_db:
                try:
                    # Generate embedding for this scenario
                    scenario_text = f"{scenario.name} {' '.join([s.name for s in scenario.steps if s.name])}"
                    embedding = await orchestrator.llm.embed_text(scenario_text)

                    # Find similar failures
                    search_results = orchestrator.vector_db.client.search(
                        collection_name=orchestrator.vector_db.cucumber_collection,
                        query_vector=embedding,
                        query_filter=qdrant_models.Filter(
                            must=[
                                qdrant_models.FieldCondition(
                                    key="type",
                                    match=qdrant_models.MatchValue(value="scenario")
                                ),
                                qdrant_models.FieldCondition(
                                    key="status",
                                    match=qdrant_models.MatchValue(value="FAILED")
                                )
                            ],
                            must_not=[
                                qdrant_models.FieldCondition(
                                    key="id",
                                    match=qdrant_models.MatchValue(value=str(scenario_id))
                                )
                            ]
                        ),
                        limit=5  # Get top 5 similar failures
                    )

                    # Get basic info for similar failures
                    for result in search_results:
                        similar_id = UUID(result.id)
                        similar_query = select(DBScenario).where(DBScenario.id == similar_id)
                        similar_result = await session.execute(similar_query)
                        similar_scenario = similar_result.scalar_one_or_none()

                        if similar_scenario:
                            similar_failures.append({
                                "id": str(similar_scenario.id),
                                "name": similar_scenario.name,
                                "similarity_score": result.score,
                                "created_at": dt.isoformat_utc(similar_scenario.created_at)
                            })
                except Exception as e:
                    logger.error(f"Error finding similar failures: {str(e)}", exc_info=True)
                    # Continue without similar failures

            # Get historical failure data
            historical_data = await get_historical_failure_data(scenario.name, session)

            # Determine failure category
            error_info = extract_error_info(scenario)
            category = failure_service.categorize_error(
                error_info.get("message"),
                scenario.name
            )

            return {
                "id": str(scenario.id),
                "name": scenario.name,
                "description": scenario.description,
                "status": str(scenario.status),
                "duration": scenario.duration,
                "is_flaky": scenario.is_flaky,
                "created_at": dt.isoformat_utc(scenario.created_at),
                "updated_at": dt.isoformat_utc(scenario.updated_at) if scenario.updated_at else None,
                "test_run": {
                    "id": str(test_run.id) if test_run else None,
                    "name": test_run.name if test_run else None,
                    "environment": test_run.environment if test_run else None,
                    "branch": test_run.branch if test_run else None,
                    "commit_hash": test_run.commit_hash if test_run else None,
                },
                "feature": {
                    "id": str(feature.id) if feature else None,
                    "name": feature.name if feature else None,
                    "description": feature.description if feature else None,
                },
                "steps": steps,
                "tags": [tag.tag for tag in scenario.tags] if scenario.tags else [],
                "error": {
                    "message": error_info.get("message"),
                    "stack_trace": error_info.get("stack_trace"),
                    "category": category,
                    "step_name": error_info.get("step_name"),
                },
                "similar_failures": similar_failures,
                "history": historical_data
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving failure details: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to retrieve failure details: {str(e)}")