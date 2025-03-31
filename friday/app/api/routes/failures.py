"""
API routes for failure analysis
"""
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query

router = APIRouter()


@router.get("/failures")
async def get_failure_analysis(
        test_run_id: Optional[str] = Query(None, description="Filter by test run ID"),
        build_id: Optional[str] = Query(None, description="Filter by build ID"),
        days: int = Query(7, description="Number of days to analyze")
):
    """
    Get failure analysis data

    Returns:
        dict: Failure analysis data including categories, details, and recent failures
    """
    try:
        # In Phase 1, we return a mock response
        # This will be replaced with actual data retrieval in Phase 5

        failure_data = generate_mock_failure_data()

        # Return direct format expected by frontend
        return {
            "failureCategories": failure_data["categories"],
            "failureDetails": failure_data["details"],
            "failuresByFeature": failure_data["by_feature"],
            "recentFailures": failure_data["recent"]
        }

    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to retrieve failure analysis: {str(e)}",
            "timestamp": datetime.utcnow().isoformat()
        }


def generate_mock_failure_data() -> Dict:
    """
    Generate mock failure analysis data

    Returns:
        Dict: Mock failure data
    """
    # Failure categories
    categories = [
        {"name": "UI Elements Not Found", "value": 95, "percentage": 35.7},
        {"name": "Timeout Errors", "value": 68, "percentage": 25.6},
        {"name": "Assertion Failures", "value": 45, "percentage": 16.9},
        {"name": "API Response Errors", "value": 32, "percentage": 12.0},
        {"name": "Database Connection", "value": 16, "percentage": 6.0},
        {"name": "Other", "value": 10, "percentage": 3.8}
    ]

    # Failure details
    details = {
        "UI Elements Not Found": [
            {"element": "Submit Button", "occurrences": 24, "scenarios": ["User Registration", "Checkout"]},
            {"element": "Search Results", "occurrences": 18, "scenarios": ["Product Search", "Content Search"]},
            {"element": "Navigation Menu", "occurrences": 15, "scenarios": ["Homepage", "Category Pages"]}
        ],
        "Timeout Errors": [
            {"element": "API Response", "occurrences": 28, "scenarios": ["Product Catalog", "Search Results"]},
            {"element": "Page Load", "occurrences": 22, "scenarios": ["Product Details", "Checkout"]},
            {"element": "Payment Processing", "occurrences": 18, "scenarios": ["Checkout"]}
        ],
        "Assertion Failures": [
            {"element": "Product Price", "occurrences": 15, "scenarios": ["Product Details", "Shopping Cart"]},
            {"element": "User Information", "occurrences": 12, "scenarios": ["User Profile", "Account Settings"]},
            {"element": "Order Summary", "occurrences": 10, "scenarios": ["Checkout", "Order Confirmation"]}
        ]
    }

    # Failures by feature
    by_feature = [
        {"feature": "Checkout", "failures": 64, "tests": 204, "failureRate": 31.4},
        {"feature": "Search", "failures": 43, "tests": 230, "failureRate": 18.7},
        {"feature": "User Profile", "failures": 23, "tests": 120, "failureRate": 19.2},
        {"feature": "Product Catalog", "failures": 64, "tests": 329, "failureRate": 19.5},
        {"feature": "Authentication", "failures": 12, "tests": 140, "failureRate": 8.6}
    ]

    # Recent failures
    now = datetime.utcnow()
    recent = [
        {
            "id": "F123",
            "scenario": "User cannot complete checkout with saved payment method",
            "error": "Timeout waiting for payment confirmation dialog",
            "date": now.isoformat(),
            "build": "#1045"
        },
        {
            "id": "F122",
            "scenario": "Search results do not include relevant products",
            "error": "Assertion error: Expected search results to contain 'bluetooth headphones'",
            "date": (now - timedelta(hours=1)).isoformat(),
            "build": "#1045"
        },
        {
            "id": "F121",
            "scenario": "User profile update fails with valid data",
            "error": "Element not found: Save Changes button",
            "date": (now - timedelta(hours=2)).isoformat(),
            "build": "#1044"
        },
        {
            "id": "F120",
            "scenario": "Product filtering does not work with multiple criteria",
            "error": "Assertion error: Expected filtered products count to be 3, got 12",
            "date": (now - timedelta(hours=5)).isoformat(),
            "build": "#1044"
        },
        {
            "id": "F119",
            "scenario": "Payment processing fails with valid credit card",
            "error": "Timeout waiting for payment gateway response",
            "date": (now - timedelta(hours=8)).isoformat(),
            "build": "#1043"
        }
    ]

    return {
        "categories": categories,
        "details": details,
        "by_feature": by_feature,
        "recent": recent,
        "total_failures": sum(c["value"] for c in categories)
    }