# app/api/routes/failures.py
from fastapi import APIRouter, Depends, HTTPException, Query, Path
from typing import List, Dict, Any, Optional
import logging
from datetime import datetime
import uuid

from app.config import settings
from app.services.orchestrator import ServiceOrchestrator
from app.api.dependencies import get_orchestrator_service


logger = logging.getLogger(__name__)

router = APIRouter(prefix=settings.API_PREFIX, tags=["failures"])


@router.get("/failures/recent", response_model=List[Dict[str, Any]])
async def get_recent_failures(
        limit: int = Query(10, description="Maximum number of failures to return"),
        skip: int = Query(0, description="Number of failures to skip"),
        environment: Optional[str] = Query(None, description="Filter by environment"),
        feature: Optional[str] = Query(None, description="Filter by feature"),
        orchestrator: ServiceOrchestrator = Depends(get_orchestrator_service)
):
    """
    Get recent test failures.

    This endpoint returns a list of recent test failures,
    optionally filtered by environment and feature.
    """
    try:
        # Build query with filters
        query_parts = ["recent test failures"]

        if environment:
            query_parts.append(f"environment:{environment}")

        if feature:
            query_parts.append(f"feature:{feature}")

        query = " ".join(query_parts)

        # Generate embedding for the query
        query_embedding = await orchestrator.llm.generate_embedding(query)

        # Search for test cases
        filters = {
            "type": "test_case",
            "status": "FAILED"
        }

        # Perform search to get all failures
        test_case_results = await orchestrator.semantic_search(
            query=query,
            filters=filters,
            limit=limit + skip
        )

        # Apply pagination
        paged_results = test_case_results[skip:limit + skip]

        # Format the results
        formatted_failures = []
        for tc in paged_results:
            payload = tc.payload

            # Check if we need to apply environment filter
            if environment and payload.get("environment") != environment:
                continue

            # Check if we need to apply feature filter
            if feature and payload.get("feature") != feature:
                continue

            formatted_failures.append({
                "id": tc.id,
                "name": payload.get("name", "Unnamed Test Case"),
                "feature": payload.get("feature", "Unknown Feature"),
                "error_message": payload.get("error_message", "No error message"),
                "report_id": payload.get("report_id", "Unknown Report"),
                "tags": payload.get("tags", [])
            })

        return formatted_failures
    except Exception as e:
        logger.error(f"Error retrieving recent failures: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve recent failures: {str(e)}"
        )


@router.get("/failures/analysis", response_model=Dict[str, Any])
async def analyze_failure_patterns(
        time_period: str = Query("last_week", description="Time period for analysis (last_day, last_week, last_month)"),
        environment: Optional[str] = Query(None, description="Filter by environment"),
        feature: Optional[str] = Query(None, description="Filter by feature"),
        orchestrator: ServiceOrchestrator = Depends(get_orchestrator_service)
):
    """
    Analyze patterns in test failures.

    This endpoint uses the LLM to identify patterns in test failures
    over the specified time period.
    """
    try:
        # Build query with filters
        query_parts = [f"test failure patterns {time_period}"]

        if environment:
            query_parts.append(f"environment:{environment}")

        if feature:
            query_parts.append(f"feature:{feature}")

        query = " ".join(query_parts)

        # Generate embedding for the query
        query_embedding = await orchestrator.llm.generate_embedding(query)

        # Search for failed test cases
        filters = {
            "type": "test_case",
            "status": "FAILED"
        }

        # Get a larger sample of failures for analysis
        test_case_results = await orchestrator.semantic_search(
            query=query,
            filters=filters,
            limit=100  # Larger limit for more comprehensive analysis
        )

        # Filter results if needed
        if environment or feature:
            filtered_results = []
            for tc in test_case_results:
                payload = tc.payload

                # Check environment filter
                if environment and payload.get("environment") != environment:
                    continue

                # Check feature filter
                if feature and payload.get("feature") != feature:
                    continue

                filtered_results.append(tc)

            test_case_results = filtered_results

        # If we have no results, return early
        if not test_case_results:
            return {
                "message": "No failures found for the specified criteria",
                "time_period": time_period,
                "environment": environment,
                "feature": feature,
                "timestamp": datetime.now().isoformat()
            }

        # Group failures by error message pattern
        # This is a simple grouping; the LLM will do more sophisticated analysis
        error_groups = {}
        for tc in test_case_results:
            error_msg = tc.payload.get("error_message", "Unknown error")
            if error_msg not in error_groups:
                error_groups[error_msg] = []

            error_groups[error_msg].append(tc.payload)

        # Prepare data for LLM analysis
        analysis_data = {
            "time_period": time_period,
            "environment": environment,
            "feature": feature,
            "total_failures": len(test_case_results),
            "error_groups": [
                {
                    "error": error,
                    "count": len(failures),
                    "examples": failures[:3]  # Just include a few examples
                }
                for error, failures in error_groups.items()
            ]
        }

        # Generate analysis with LLM
        analysis_prompt = f"""
        Analyze the following test failure patterns:

        {analysis_data}

        Identify:
        1. Common patterns in the failures
        2. Possible root causes
        3. Recommendations for fixing or investigating these failures

        Provide a clear, concise analysis with actionable recommendations.
        """

        analysis = await orchestrator.llm.generate_text(
            prompt=analysis_prompt,
            temperature=0.3,
            max_tokens=1000
        )

        # Return the analysis
        return {
            "time_period": time_period,
            "environment": environment,
            "feature": feature,
            "total_failures": len(test_case_results),
            "failure_groups": len(error_groups),
            "analysis": analysis,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error analyzing failure patterns: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to analyze failure patterns: {str(e)}"
        )


@router.get("/failures/flaky-tests", response_model=List[Dict[str, Any]])
async def get_flaky_tests(
        threshold: int = Query(2, description="Minimum number of failures required to be considered flaky"),
        limit: int = Query(10, description="Maximum number of tests to return"),
        orchestrator: ServiceOrchestrator = Depends(get_orchestrator_service)
):
    """
    Get potentially flaky tests.

    This endpoint identifies tests that have both passed and failed
    recently, indicating they might be flaky.
    """
    try:
        # Build query to find flaky tests
        query = "flaky tests inconsistent results"

        # Generate embedding for the query
        query_embedding = await orchestrator.llm.generate_embedding(query)

        # Get all test cases
        test_case_results = orchestrator.vector_db.search_test_cases(
            query_embedding=query_embedding,
            limit=1000  # We need a large sample to find patterns
        )

        # Group test cases by name to find ones that have failed and passed
        test_groups = {}
        for tc in test_case_results:
            name = tc.payload.get("name")
            feature = tc.payload.get("feature")
            key = f"{feature}::{name}"

            if key not in test_groups:
                test_groups[key] = {
                    "name": name,
                    "feature": feature,
                    "statuses": {},
                    "instances": []
                }

            status = tc.payload.get("status")
            test_groups[key]["statuses"][status] = test_groups[key]["statuses"].get(status, 0) + 1
            test_groups[key]["instances"].append(tc.payload)

        # Find tests that have both passed and failed
        flaky_tests = []
        for key, data in test_groups.items():
            if "PASSED" in data["statuses"] and "FAILED" in data["statuses"]:
                if data["statuses"].get("FAILED", 0) >= threshold:
                    flaky_tests.append({
                        "name": data["name"],
                        "feature": data["feature"],
                        "pass_count": data["statuses"].get("PASSED", 0),
                        "fail_count": data["statuses"].get("FAILED", 0),
                        "flakiness_score": min(
                            10,
                            10 * data["statuses"].get("FAILED", 0) / (
                                        data["statuses"].get("PASSED", 0) + data["statuses"].get("FAILED", 0))
                        ),
                        "latest_examples": data["instances"][:3]
                    })

        # Sort by flakiness score (descending)
        flaky_tests.sort(key=lambda x: x["flakiness_score"], reverse=True)

        # Apply limit
        return flaky_tests[:limit]
    except Exception as e:
        logger.error(f"Error identifying flaky tests: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to identify flaky tests: {str(e)}"
        )


@router.get("/failures/{test_case_id}/similar", response_model=List[Dict[str, Any]])
async def find_similar_failures(
        test_case_id: str = Path(..., description="ID of the test case to find similar failures for"),
        limit: int = Query(5, description="Maximum number of similar failures to return"),
        orchestrator: ServiceOrchestrator = Depends(get_orchestrator_service)
):
    """
    Find test failures similar to the specified test case.

    This endpoint uses semantic search to find failures with similar
    characteristics to the specified test case.
    """
    try:
        # First, get the test case
        query_text = "test case details"
        query_embedding = await orchestrator.llm.generate_embedding(query_text)

        test_case_results = orchestrator.vector_db.search_test_cases(
            query_embedding=query_embedding,
            limit=10
        )

        # Find the exact test case
        matching_test_cases = [tc for tc in test_case_results if tc.id == test_case_id]

        if not matching_test_cases:
            raise HTTPException(
                status_code=404,
                detail=f"Test case with ID {test_case_id} not found"
            )

        test_case = matching_test_cases[0].payload

        # Create a query based on the test case details
        search_query = f"{test_case.get('name', '')} {test_case.get('error_message', '')}"

        # Generate embedding for the search query
        search_embedding = await orchestrator.llm.generate_embedding(search_query)

        # Search for similar test cases
        similar_test_cases = orchestrator.vector_db.search_test_cases(
            query_embedding=search_embedding,
            limit=limit + 1  # +1 because the original might be included
        )

        # Filter out the original test case
        similar_test_cases = [tc for tc in similar_test_cases if tc.id != test_case_id]

        # Limit the results
        similar_test_cases = similar_test_cases[:limit]

        # Format the results
        return [
            {
                "id": tc.id,
                "name": tc.payload.get("name", "Unnamed Test Case"),
                "feature": tc.payload.get("feature", "Unknown Feature"),
                "error_message": tc.payload.get("error_message", "No error message"),
                "report_id": tc.payload.get("report_id", "Unknown Report"),
                "similarity_score": tc.score
            }
            for tc in similar_test_cases
        ]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error finding similar failures: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to find similar failures: {str(e)}"
        )