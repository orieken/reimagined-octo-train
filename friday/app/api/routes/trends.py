"""
API routes for test trends
"""
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query

router = APIRouter()


@router.get("/trends")
async def get_test_trends(
        time_range: str = Query("week", description="Time range for trends (week, month, year)")
):
    """
    Get test trends over time

    Returns:
        dict: Test trends data including daily trends, build comparison, etc.
    """
    try:
        # In Phase 1, we return a mock response
        # This will be replaced with actual data retrieval in Phase 5

        # Generate appropriate data based on time range
        if time_range == "week":
            data = generate_daily_trends(7)
        elif time_range == "month":
            data = generate_daily_trends(30)
        else:  # year
            data = generate_weekly_trends(12)

        # Return direct format expected by frontend
        return {
            "dailyTrends": data["dailyTrends"],
            "buildComparison": data["buildComparison"],
            "topFailingTests": data["topFailingTests"]
        }

    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to retrieve test trends: {str(e)}",
            "timestamp": datetime.utcnow().isoformat()
        }


def generate_daily_trends(days: int) -> Dict:
    """
    Generate mock daily trends data

    Args:
        days: Number of days to generate data for

    Returns:
        Dict: Mock trends data
    """
    daily_data = []
    now = datetime.utcnow()

    for i in range(days - 1, -1, -1):
        date = now - timedelta(days=i)
        date_str = date.strftime("%b %d")  # Format: "Mar 28"

        # Generate slightly varying data
        total = 100 + int((days - i) * 1.5)
        pass_rate = 75.0 + (15.0 * ((days - i) % 3) / 3)  # Varies between 75 and 90
        passed = int(total * (pass_rate / 100))
        failed = total - passed

        daily_data.append({
            "date": date_str,
            "totalTests": total,
            "passedTests": passed,
            "failedTests": failed,
            "passRate": round(pass_rate, 1)
        })

    # Build comparison data
    build_data = []
    for i in range(5):
        build_number = f"#{1045 - i}"
        pass_rate = 75.0 + (15.0 * (i % 4) / 4)  # Varies between 75 and 90

        build_data.append({
            "buildNumber": build_number,
            "passRate": round(pass_rate, 1)
        })

    # Top failing tests
    failing_tests = [
        {
            "name": "User authentication with invalid credentials",
            "failureRate": 35.0,
            "occurrences": 8
        },
        {
            "name": "Product checkout with expired credit card",
            "failureRate": 32.0,
            "occurrences": 7
        },
        {
            "name": "Search functionality with special characters",
            "failureRate": 28.0,
            "occurrences": 6
        },
        {
            "name": "User profile update with invalid data",
            "failureRate": 25.0,
            "occurrences": 5
        },
        {
            "name": "Product catalog filtering by multiple criteria",
            "failureRate": 22.0,
            "occurrences": 4
        }
    ]

    return {
        "dailyTrends": daily_data,
        "buildComparison": build_data,
        "topFailingTests": failing_tests
    }


def generate_weekly_trends(weeks: int) -> Dict:
    """
    Generate mock weekly trends data

    Args:
        weeks: Number of weeks to generate data for

    Returns:
        Dict: Mock trends data
    """
    weekly_data = []

    for i in range(weeks):
        week_num = i + 1

        # Generate slightly varying data
        total = 500 + int((weeks - i) * 10)
        pass_rate = 75.0 + (15.0 * ((weeks - i) % 3) / 3)  # Varies between 75 and 90
        passed = int(total * (pass_rate / 100))
        failed = total - passed

        weekly_data.append({
            "date": f"Week {week_num}",
            "totalTests": total,
            "passedTests": passed,
            "failedTests": failed,
            "passRate": round(pass_rate, 1)
        })

    # Same build comparison and failing tests as daily
    build_data = []
    for i in range(5):
        build_number = f"#{1045 - i}"
        pass_rate = 75.0 + (15.0 * (i % 4) / 4)  # Varies between 75 and 90

        build_data.append({
            "buildNumber": build_number,
            "passRate": round(pass_rate, 1)
        })

    failing_tests = [
        {
            "name": "User authentication with invalid credentials",
            "failureRate": 35.0,
            "occurrences": 8
        },
        {
            "name": "Product checkout with expired credit card",
            "failureRate": 32.0,
            "occurrences": 7
        },
        {
            "name": "Search functionality with special characters",
            "failureRate": 28.0,
            "occurrences": 6
        },
        {
            "name": "User profile update with invalid data",
            "failureRate": 25.0,
            "occurrences": 5
        },
        {
            "name": "Product catalog filtering by multiple criteria",
            "failureRate": 22.0,
            "occurrences": 4
        }
    ]

    return {
        "dailyTrends": weekly_data,  # Use the same key for consistency
        "buildComparison": build_data,
        "topFailingTests": failing_tests
    }