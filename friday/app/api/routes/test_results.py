"""
API routes for detailed test results
"""
from datetime import datetime
from typing import Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query

from app.models.api import ErrorResponse, TestResultsResponse, FeatureResult, TestResultsTag
from app.models.domain import TestStatus

router = APIRouter()


@router.get("/test-results")
async def get_test_results(
        test_run_id: Optional[str] = Query(None, description="Filter by test run ID"),
        build_id: Optional[str] = Query(None, description="Filter by build ID"),
        feature: Optional[str] = Query(None, description="Filter by feature name"),
        tag: Optional[str] = Query(None, description="Filter by tag"),
):
    """
    Get detailed test results for dashboard visualization

    Returns:
        dict: Test results data including total, passed, failed tests, and feature breakdown
    """
    try:
        # In Phase 1, we return a mock response
        # This will be replaced with actual data retrieval in Phase 5

        mock_data = generate_mock_test_results()

        # Apply filters if provided (simulating filtering)
        if tag:
            # Only include features that would have this tag
            tag_seed = sum(ord(c) for c in tag)
            mock_data["features"] = [
                feature for feature in mock_data["features"]
                if tag_seed % (len(mock_data["features"]) + 1) !=
                   mock_data["features"].index(feature) % (len(mock_data["features"]) + 1)
            ]

        if feature:
            # Only include the specified feature
            mock_data["features"] = [
                f for f in mock_data["features"]
                if feature.lower() in f["name"].lower()
            ]

        # Recalculate totals based on filtered features
        if tag or feature:
            total_passed = sum(f["passed"] for f in mock_data["features"])
            total_failed = sum(f["failed"] for f in mock_data["features"])
            total_skipped = sum(f.get("skipped", 0) for f in mock_data["features"])
            total = total_passed + total_failed + total_skipped

            mock_data["totalTests"] = total
            mock_data["passedTests"] = total_passed
            mock_data["failedTests"] = total_failed
            mock_data["skippedTests"] = total_skipped
            mock_data["passRate"] = round((total_passed / total) * 100, 1) if total > 0 else 0

        # Convert to direct response format expected by frontend
        result = {
            "totalTests": mock_data["totalTests"],
            "passedTests": mock_data["passedTests"],
            "failedTests": mock_data["failedTests"],
            "skippedTests": mock_data["skippedTests"],
            "passRate": mock_data["passRate"],
            "lastUpdated": mock_data["lastUpdated"],
            "featureResults": mock_data["features"],
            "tags": mock_data["tags"]
        }

        return result

    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to retrieve test results: {str(e)}",
            "timestamp": datetime.utcnow().isoformat()
        }


def generate_mock_test_results() -> Dict:
    """
    Generate mock test results data for the dashboard

    This is a temporary function for Phase 1 development
    """
    features = [
        {
            "name": "User Authentication",
            "passed": 24,
            "failed": 3,
            "skipped": 1
        },
        {
            "name": "Shopping Cart",
            "passed": 18,
            "failed": 2,
            "skipped": 0
        },
        {
            "name": "Product Catalog",
            "passed": 30,
            "failed": 5,
            "skipped": 2
        },
        {
            "name": "Checkout Process",
            "passed": 15,
            "failed": 7,
            "skipped": 3
        },
        {
            "name": "User Profile",
            "passed": 12,
            "failed": 1,
            "skipped": 0
        }
    ]

    # Calculate totals
    total_passed = sum(f["passed"] for f in features)
    total_failed = sum(f["failed"] for f in features)
    total_skipped = sum(f.get("skipped", 0) for f in features)
    total = total_passed + total_failed + total_skipped
    pass_rate = round((total_passed / total) * 100, 1) if total > 0 else 0

    # Mock tag data
    tags = [
        {"name": "@api", "count": 45, "passRate": 89.0},
        {"name": "@ui", "count": 38, "passRate": 76.0},
        {"name": "@regression", "count": 60, "passRate": 82.0},
        {"name": "@smoke", "count": 25, "passRate": 92.0},
        {"name": "@slow", "count": 20, "passRate": 85.0}
    ]

    return {
        "totalTests": total,
        "passedTests": total_passed,
        "failedTests": total_failed,
        "skippedTests": total_skipped,
        "passRate": pass_rate,
        "lastUpdated": datetime.utcnow().isoformat(),
        "features": features,
        "tags": tags
    }