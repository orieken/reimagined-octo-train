# app/api/routes/test_results.py
from fastapi import APIRouter, Depends, HTTPException, Query, Path
from typing import List, Dict, Any, Optional
import logging
from datetime import datetime, timedelta
import uuid

from app.config import settings
from app.services.orchestrator import ServiceOrchestrator
from app.api.dependencies import get_orchestrator_service

from app.models.database import TestResultsTag
from app.models.responses import (TestResultsListResponse, TestResultsResponse, TestCaseListResponse,
                                  ScenarioResult, StatisticsResponse, StepResult
                                  )

logger = logging.getLogger(__name__)

router = APIRouter(prefix=settings.API_PREFIX, tags=["test-results"])


@router.get("/test-results", response_model=TestResultsListResponse)
async def list_test_results(
        limit: int = Query(10, description="Maximum number of results to return"),
        offset: int = Query(0, description="Number of results to skip"),
        status: Optional[str] = Query(None, description="Filter by status"),
        environment: Optional[str] = Query(None, description="Filter by environment"),
        days: int = Query(30, description="Number of days to look back"),
        tag: Optional[str] = Query(None, description="Filter by tag"),
        orchestrator: ServiceOrchestrator = Depends(get_orchestrator_service)
):
    """
    List test results with optional filtering.

    This endpoint returns a list of test results, optionally filtered by various criteria.
    """
    try:
        # Construct a search query based on filters
        query_parts = ["test report"]

        if status:
            query_parts.append(f"status:{status}")

        if environment:
            query_parts.append(f"environment:{environment}")

        if tag:
            query_parts.append(f"tag:{tag}")

        query = " ".join(query_parts)

        # Build filters
        filters = {"type": "report"}

        if environment:
            filters["environment"] = environment

        # Perform search
        search_results = await orchestrator.semantic_search(
            query=query,
            filters=filters,
            limit=limit + offset
        )

        # Apply date filter
        cutoff_date = datetime.now() - timedelta(days=days)
        filtered_results = []

        for result in search_results:
            try:
                # Parse timestamp and check if it's within the date range
                timestamp = result.payload.get("timestamp", "")
                if timestamp:
                    result_date = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                    if result_date >= cutoff_date:
                        filtered_results.append(result)
            except (ValueError, TypeError):
                # If timestamp parsing fails, include the result anyway
                filtered_results.append(result)

        # Skip the first N results if needed
        paged_results = filtered_results[offset:offset + limit]

        # Convert to response format
        formatted_results = []
        for result in paged_results:
            payload = result.payload
            formatted_results.append({
                "id": result.id,
                "name": payload.get("name", "Unnamed Report"),
                "status": payload.get("status", "UNKNOWN"),
                "timestamp": payload.get("timestamp", ""),
                "environment": payload.get("environment", ""),
                "duration": payload.get("duration", 0),
                "total_tests": payload.get("metadata", {}).get("total_tests", 0),
                "passed_tests": payload.get("metadata", {}).get("total_passed", 0),
                "failed_tests": payload.get("metadata", {}).get("total_failed", 0)
            })

        return TestResultsListResponse(
            results=formatted_results,
            total=len(filtered_results),
            page=(offset // limit) + 1 if limit > 0 else 1,
            page_size=limit
        )
    except Exception as e:
        logger.error(f"Error listing test results: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list test results: {str(e)}"
        )


@router.get("/test-results/{report_id}", response_model=TestResultsResponse)
async def get_test_result(
        report_id: str = Path(..., description="ID of the test result to retrieve"),
        include_steps: bool = Query(True, description="Include steps in the response"),
        orchestrator: ServiceOrchestrator = Depends(get_orchestrator_service)
):
    """
    Get a specific test result by ID.

    This endpoint returns the details of a specific test result.
    """
    try:
        # Generate a simple query embedding to search for the report
        query_text = "report details"
        query_embedding = await orchestrator.llm.generate_embedding(query_text)

        # Search for reports
        report_results = orchestrator.vector_db.search_reports(
            query_embedding=query_embedding,
            limit=settings.DEFAULT_QUERY_LIMIT
        )

        # Filter to match the exact ID
        matching_reports = [r for r in report_results if r.id == report_id]

        if not matching_reports:
            raise HTTPException(
                status_code=404,
                detail=f"Test result with ID {report_id} not found"
            )

        report_data = matching_reports[0].payload

        # Get test cases for this report
        test_cases = orchestrator.vector_db.search_test_cases(
            query_embedding=query_embedding,
            report_id=report_id,
            limit=1000  # Adjust based on expected number of test cases
        )

        # Group test cases by feature
        feature_map = {}
        for tc in test_cases:
            tc_data = tc.payload
            feature_name = tc_data.get("feature", "Unknown Feature")

            if feature_name not in feature_map:
                feature_map[feature_name] = {
                    "id": str(uuid.uuid4()),
                    "name": feature_name,
                    "description": "",
                    "scenarios": [],
                    "tags": [],
                    "status": "PASSED",  # Will be updated based on scenarios
                    "duration": 0
                }

            # Create scenario object
            scenario = {
                "id": tc.id,
                "name": tc_data.get("name", "Unnamed Scenario"),
                "status": tc_data.get("status", "UNKNOWN"),
                "duration": tc_data.get("duration", 0),
                "feature": feature_name,
                "tags": [{"name": tag} for tag in tc_data.get("tags", [])],
                "error_message": tc_data.get("error_message")
            }

            # Include steps if requested
            if include_steps:
                # Get steps for this test case
                steps = orchestrator.vector_db.search_test_steps(
                    query_embedding=query_embedding,
                    test_case_id=tc.id,
                    limit=100  # Adjust based on expected number of steps
                )

                scenario["steps"] = [
                    {
                        "id": step.id,
                        "name": step.payload.get("name", "Unnamed Step"),
                        "keyword": step.payload.get("keyword", ""),
                        "status": step.payload.get("status", "UNKNOWN"),
                        "duration": step.payload.get("duration", 0),
                        "error_message": step.payload.get("error_message")
                    }
                    for step in steps
                ]
            else:
                scenario["steps"] = []

            # Update feature status and duration
            feature_map[feature_name]["duration"] += scenario["duration"]
            if scenario["status"] == "FAILED" and feature_map[feature_name]["status"] != "FAILED":
                feature_map[feature_name]["status"] = "FAILED"

            feature_map[feature_name]["scenarios"].append(scenario)

        # Calculate feature statistics
        for feature_data in feature_map.values():
            total_scenarios = len(feature_data["scenarios"])
            passed_scenarios = sum(1 for s in feature_data["scenarios"] if s["status"] == "PASSED")

            if total_scenarios > 0:
                feature_data["pass_rate"] = (passed_scenarios / total_scenarios) * 100
            else:
                feature_data["pass_rate"] = 0

        # Convert feature map to list
        features = list(feature_map.values())

        # Calculate overall statistics
        total_scenarios = sum(len(f["scenarios"]) for f in features)
        passed_scenarios = sum(len([s for s in f["scenarios"] if s["status"] == "PASSED"]) for f in features)
        failed_scenarios = sum(len([s for s in f["scenarios"] if s["status"] == "FAILED"]) for f in features)

        statistics = {
            "total_tests": total_scenarios,
            "passed_tests": passed_scenarios,
            "failed_tests": failed_scenarios,
            "pass_rate": (passed_scenarios / total_scenarios * 100) if total_scenarios > 0 else 0
        }

        # Create the response
        response = {
            "id": report_id,
            "name": report_data.get("name", "Unnamed Report"),
            "status": report_data.get("status", "UNKNOWN"),
            "timestamp": report_data.get("timestamp", ""),
            "duration": report_data.get("duration", 0),
            "environment": report_data.get("environment", "unknown"),
            "features": features,
            "tags": [{"name": tag} for tag in report_data.get("tags", [])],
            "statistics": statistics
        }

        return response
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving test result {report_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve test result: {str(e)}"
        )


@router.get("/test-results/{report_id}/test-cases", response_model=TestCaseListResponse)
async def get_test_cases(
        report_id: str = Path(..., description="ID of the test result"),
        status: Optional[str] = Query(None, description="Filter by status"),
        feature: Optional[str] = Query(None, description="Filter by feature"),
        limit: int = Query(50, description="Maximum number of test cases to return"),
        offset: int = Query(0, description="Number of test cases to skip"),
        orchestrator: ServiceOrchestrator = Depends(get_orchestrator_service)
):
    """
    Get test cases for a specific test result.

    This endpoint returns the test cases of a specific test result,
    optionally filtered by status and feature.
    """
    try:
        # Build query
        query_parts = ["test case"]

        if status:
            query_parts.append(f"status:{status}")

        if feature:
            query_parts.append(f"feature:{feature}")

        query = " ".join(query_parts)

        # Generate embedding for the query
        query_embedding = await orchestrator.llm.generate_embedding(query)

        # Search for test cases
        test_cases = orchestrator.vector_db.search_test_cases(
            query_embedding=query_embedding,
            report_id=report_id,
            limit=1000  # We'll filter and paginate in memory
        )

        # Apply filters
        filtered_test_cases = []
        for tc in test_cases:
            tc_data = tc.payload

            # Apply status filter
            if status and tc_data.get("status") != status:
                continue

            # Apply feature filter
            if feature and tc_data.get("feature") != feature:
                continue

            filtered_test_cases.append(tc)

        # Apply pagination
        total_count = len(filtered_test_cases)
        paged_test_cases = filtered_test_cases[offset:offset + limit]

        # Convert to response format
        test_case_results = []
        for tc in paged_test_cases:
            tc_data = tc.payload

            scenario = ScenarioResult(
                id=tc.id,
                name=tc_data.get("name", "Unnamed Scenario"),
                status=tc_data.get("status", "UNKNOWN"),
                feature=tc_data.get("feature", "Unknown Feature"),
                duration=tc_data.get("duration", 0),
                error_message=tc_data.get("error_message"),
                tags=[TestResultsTag(name=tag) for tag in tc_data.get("tags", [])]
            )

            test_case_results.append(scenario)

        return TestCaseListResponse(
            test_cases=test_case_results,
            total=total_count,
            page=(offset // limit) + 1 if limit > 0 else 1,
            page_size=limit
        )
    except Exception as e:
        logger.error(f"Error retrieving test cases for {report_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve test cases: {str(e)}"
        )


@router.get("/test-results/stats", response_model=StatisticsResponse)
async def get_test_statistics(
        days: int = Query(30, description="Number of days to analyze"),
        environment: Optional[str] = Query(None, description="Filter by environment"),
        feature: Optional[str] = Query(None, description="Filter by feature"),
        orchestrator: ServiceOrchestrator = Depends(get_orchestrator_service)
):
    """
    Get test statistics.

    This endpoint returns statistics about test results over the specified time period.
    """
    try:
        # Build query
        query_parts = ["test statistics"]

        if environment:
            query_parts.append(f"environment:{environment}")

        if feature:
            query_parts.append(f"feature:{feature}")

        query = " ".join(query_parts)

        # Generate embedding for the query
        query_embedding = await orchestrator.llm.generate_embedding(query)

        # Build filters
        filters = {"type": "report"}

        if environment:
            filters["environment"] = environment

        # Search for reports
        report_results = await orchestrator.semantic_search(
            query=query,
            filters=filters,
            limit=100  # Adjust based on expected number of reports
        )

        # Apply date filter
        cutoff_date = datetime.now() - timedelta(days=days)
        filtered_reports = []

        for result in report_results:
            try:
                # Parse timestamp and check if it's within the date range
                timestamp = result.payload.get("timestamp", "")
                if timestamp:
                    result_date = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                    if result_date >= cutoff_date:
                        filtered_reports.append(result)
            except (ValueError, TypeError):
                # If timestamp parsing fails, include the result anyway
                filtered_reports.append(result)

        # Collect test cases for analysis
        all_test_cases = []
        for report in filtered_reports:
            # Get test cases for this report
            test_cases = orchestrator.vector_db.search_test_cases(
                query_embedding=query_embedding,
                report_id=report.id,
                limit=1000  # Adjust based on expected number of test cases
            )

            # Apply feature filter if needed
            if feature:
                test_cases = [tc for tc in test_cases if tc.payload.get("feature") == feature]

            all_test_cases.extend(test_cases)

        # Calculate statistics
        total_test_cases = len(all_test_cases)
        status_counts = {}

        for tc in all_test_cases:
            status = tc.payload.get("status", "UNKNOWN")
            status_counts[status] = status_counts.get(status, 0) + 1

        passed_tests = status_counts.get("PASSED", 0)

        if total_test_cases > 0:
            pass_rate = (passed_tests / total_test_cases) * 100
        else:
            pass_rate = 0

        return StatisticsResponse(
            total_test_cases=total_test_cases,
            status_counts=status_counts,
            pass_rate=pass_rate,
            timestamp=datetime.now().isoformat()
        )
    except Exception as e:
        logger.error(f"Error retrieving test statistics: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve test statistics: {str(e)}"
        )


@router.get("/test-cases/{test_case_id}", response_model=ScenarioResult)
async def get_test_case(
        test_case_id: str = Path(..., description="ID of the test case to retrieve"),
        include_steps: bool = Query(True, description="Include steps in the response"),
        orchestrator: ServiceOrchestrator = Depends(get_orchestrator_service)
):
    """
    Get a specific test case by ID.

    This endpoint returns the details of a specific test case.
    """
    try:
        # Generate a simple query embedding to search for the test case
        query_text = "test case details"
        query_embedding = await orchestrator.llm.generate_embedding(query_text)

        # Search for test cases
        test_case_results = orchestrator.vector_db.search_test_cases(
            query_embedding=query_embedding,
            limit=10
        )

        # Filter to match the exact ID
        matching_test_cases = [tc for tc in test_case_results if tc.id == test_case_id]

        if not matching_test_cases:
            raise HTTPException(
                status_code=404,
                detail=f"Test case with ID {test_case_id} not found"
            )

        test_case = matching_test_cases[0].payload

        steps = []
        if include_steps:
            # Get steps for this test case
            steps_results = orchestrator.vector_db.search_test_steps(
                query_embedding=query_embedding,
                test_case_id=test_case_id,
                limit=100  # Adjust based on expected number of steps
            )

            steps = [
                StepResult(
                    id=step.id,
                    name=step.payload.get("name", "Unnamed Step"),
                    keyword=step.payload.get("keyword", ""),
                    status=step.payload.get("status", "UNKNOWN"),
                    duration=step.payload.get("duration", 0),
                    error_message=step.payload.get("error_message")
                )
                for step in steps_results
            ]

        # Create the response
        return ScenarioResult(
            id=test_case_id,
            name=test_case.get("name", "Unnamed Scenario"),
            status=test_case.get("status", "UNKNOWN"),
            feature=test_case.get("feature", "Unknown Feature"),
            duration=test_case.get("duration", 0),
            steps=steps,
            error_message=test_case.get("error_message"),
            tags=[TestResultsTag(name=tag) for tag in test_case.get("tags", [])]
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving test case {test_case_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve test case: {str(e)}"
        )
