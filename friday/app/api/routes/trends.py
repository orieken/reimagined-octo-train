# app/api/routes/trends.py
from fastapi import APIRouter, Depends, HTTPException, Query, Path
from typing import List, Dict, Any, Optional
import logging
from datetime import datetime
import uuid

from app.config import settings
from app.services.orchestrator import ServiceOrchestrator
from app.api.dependencies import get_orchestrator_service
from app.models.domain import (
    TestRun as Report, Scenario as TestCase, BuildInfo
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix=settings.API_PREFIX, tags=["trends"])


@router.get("/trends/pass-rate", response_model=Dict[str, Any])
async def get_pass_rate_trend(
        days: int = Query(30, description="Number of days to analyze"),
        environment: Optional[str] = Query(None, description="Filter by environment"),
        feature: Optional[str] = Query(None, description="Filter by feature"),
        orchestrator: ServiceOrchestrator = Depends(get_orchestrator_service)
):
    """
    Get pass rate trend over time.

    This endpoint returns the pass rate trend over the specified number of days,
    optionally filtered by environment and feature.
    """
    try:
        # Build query with filters
        query_parts = ["pass rate trend"]

        if environment:
            query_parts.append(f"environment:{environment}")

        if feature:
            query_parts.append(f"feature:{feature}")

        query = " ".join(query_parts)

        # Generate embedding for the query
        query_embedding = await orchestrator.llm.generate_embedding(query)

        # Search for reports
        filters = {"type": "report"}

        if environment:
            filters["environment"] = environment

        # Get a larger sample of reports for trend analysis
        report_results = await orchestrator.semantic_search(
            query=query,
            filters=filters,
            limit=100  # Larger limit for more comprehensive analysis
        )

        # Group reports by date
        date_groups = {}
        for report in report_results:
            timestamp = report.payload.get("timestamp", "")
            if not timestamp:
                continue

            # Extract date part only
            date = timestamp.split("T")[0]

            if date not in date_groups:
                date_groups[date] = []

            date_groups[date].append(report.payload)

        # Calculate pass rate for each date
        trend_data = []
        for date, reports in sorted(date_groups.items()):
            total_tests = 0
            passed_tests = 0

            for report in reports:
                # We would need to get test cases for each report to be accurate
                # This is a simplification for illustration
                test_cases = []

                if feature:
                    # If feature filter is applied, search for test cases with that feature
                    test_cases_results = orchestrator.vector_db.search_test_cases(
                        query_embedding=query_embedding,
                        report_id=report.get("id"),
                        limit=1000
                    )

                    test_cases = [tc.payload for tc in test_cases_results if tc.payload.get("feature") == feature]
                else:
                    # Otherwise, use report statistics if available
                    total_tests += report.get("total_tests", 0)
                    passed_tests += report.get("passed_tests", 0)

                if test_cases:
                    total_tests += len(test_cases)
                    passed_tests += len([tc for tc in test_cases if tc.get("status") == "PASSED"])

            if total_tests > 0:
                pass_rate = (passed_tests / total_tests) * 100
            else:
                pass_rate = 0

            trend_data.append({
                "date": date,
                "pass_rate": round(pass_rate, 2),
                "total_tests": total_tests,
                "passed_tests": passed_tests
            })

        # Return the trend data
        return {
            "days": days,
            "environment": environment,
            "feature": feature,
            "trend_data": trend_data,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error retrieving pass rate trend: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve pass rate trend: {str(e)}"
        )


@router.get("/trends/duration", response_model=Dict[str, Any])
async def get_duration_trend(
        days: int = Query(30, description="Number of days to analyze"),
        environment: Optional[str] = Query(None, description="Filter by environment"),
        feature: Optional[str] = Query(None, description="Filter by feature"),
        orchestrator: ServiceOrchestrator = Depends(get_orchestrator_service)
):
    """
    Get test duration trend over time.

    This endpoint returns the test duration trend over the specified number of days,
    optionally filtered by environment and feature.
    """
    try:
        # Build query with filters
        query_parts = ["test duration trend"]

        if environment:
            query_parts.append(f"environment:{environment}")

        if feature:
            query_parts.append(f"feature:{feature}")

        query = " ".join(query_parts)

        # Generate embedding for the query
        query_embedding = await orchestrator.llm.generate_embedding(query)

        # Search for reports
        filters = {"type": "report"}

        if environment:
            filters["environment"] = environment

        # Get a larger sample of reports for trend analysis
        report_results = await orchestrator.semantic_search(
            query=query,
            filters=filters,
            limit=100  # Larger limit for more comprehensive analysis
        )

        # Group reports by date
        date_groups = {}
        for report in report_results:
            timestamp = report.payload.get("timestamp", "")
            if not timestamp:
                continue

            # Extract date part only
            date = timestamp.split("T")[0]

            if date not in date_groups:
                date_groups[date] = []

            date_groups[date].append(report.payload)

        # Calculate average duration for each date
        trend_data = []
        for date, reports in sorted(date_groups.items()):
            total_duration = 0
            total_test_cases = 0

            for report in reports:
                duration = report.get("duration", 0)
                test_cases_count = report.get("total_tests", 0)

                if feature:
                    # If feature filter is applied, search for test cases with that feature
                    test_cases_results = orchestrator.vector_db.search_test_cases(
                        query_embedding=query_embedding,
                        report_id=report.get("id"),
                        limit=1000
                    )

                    feature_test_cases = [tc.payload for tc in test_cases_results if
                                          tc.payload.get("feature") == feature]

                    if feature_test_cases:
                        feature_duration = sum(tc.get("duration", 0) for tc in feature_test_cases)
                        total_duration += feature_duration
                        total_test_cases += len(feature_test_cases)
                else:
                    total_duration += duration
                    total_test_cases += test_cases_count

            if total_test_cases > 0:
                avg_duration = total_duration / total_test_cases
            else:
                avg_duration = 0

            trend_data.append({
                "date": date,
                "avg_duration": round(avg_duration, 2),
                "total_duration": total_duration,
                "total_tests": total_test_cases
            })

        # Return the trend data
        return {
            "days": days,
            "environment": environment,
            "feature": feature,
            "trend_data": trend_data,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error retrieving duration trend: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve duration trend: {str(e)}"
        )


@router.post("/trends/builds", response_model=Dict[str, Any])
async def analyze_build_trend(
        build_numbers: List[str],
        orchestrator: ServiceOrchestrator = Depends(get_orchestrator_service)
):
    """
    Analyze trends across multiple builds.

    This endpoint analyzes trends across the specified builds,
    including pass rate, duration, and other metrics.
    """
    try:
        # Use the orchestrator method to analyze build trends
        result = await orchestrator.analyze_build_trend(build_numbers)
        return result
    except Exception as e:
        logger.error(f"Error analyzing build trend: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to analyze build trend: {str(e)}"
        )


@router.get("/trends/top-failing-features", response_model=List[Dict[str, Any]])
async def get_top_failing_features(
        days: int = Query(30, description="Number of days to analyze"),
        limit: int = Query(5, description="Maximum number of features to return"),
        environment: Optional[str] = Query(None, description="Filter by environment"),
        orchestrator: ServiceOrchestrator = Depends(get_orchestrator_service)
):
    """
    Get top failing features.

    This endpoint returns the features with the highest failure rates
    over the specified number of days.
    """
    try:
        # Build query with filters
        query_parts = ["failing features"]

        if environment:
            query_parts.append(f"environment:{environment}")

        query = " ".join(query_parts)

        # Generate embedding for the query
        query_embedding = await orchestrator.llm.generate_embedding(query)

        # Search for test cases
        filters = {"type": "test_case"}

        if environment:
            filters["environment"] = environment

        # Get a larger sample of test cases for analysis
        test_case_results = await orchestrator.semantic_search(
            query=query,
            filters=filters,
            limit=1000  # Larger limit for more comprehensive analysis
        )

        # Group test cases by feature
        feature_groups = {}
        for tc in test_case_results:
            feature = tc.payload.get("feature", "Unknown")

            if feature not in feature_groups:
                feature_groups[feature] = {
                    "name": feature,
                    "total_tests": 0,
                    "failed_tests": 0,
                    "passed_tests": 0
                }

            feature_groups[feature]["total_tests"] += 1

            status = tc.payload.get("status")
            if status == "FAILED":
                feature_groups[feature]["failed_tests"] += 1
            elif status == "PASSED":
                feature_groups[feature]["passed_tests"] += 1

        # Calculate failure rate for each feature
        for feature_data in feature_groups.values():
            if feature_data["total_tests"] > 0:
                feature_data["failure_rate"] = (feature_data["failed_tests"] / feature_data["total_tests"]) * 100
            else:
                feature_data["failure_rate"] = 0

        # Sort features by failure rate (descending)
        sorted_features = sorted(
            feature_groups.values(),
            key=lambda x: x["failure_rate"],
            reverse=True
        )

        # Apply limit
        top_features = sorted_features[:limit]

        # Return the top failing features
        return [
            {
                "feature": f["name"],
                "failure_rate": round(f["failure_rate"], 2),
                "total_tests": f["total_tests"],
                "failed_tests": f["failed_tests"],
                "passed_tests": f["passed_tests"]
            }
            for f in top_features
        ]
    except Exception as e:
        logger.error(f"Error retrieving top failing features: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve top failing features: {str(e)}"
        )