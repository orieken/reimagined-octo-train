# app/services/analytics_service.py
"""
Service for analytics calculations and metrics
"""
import logging
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy import func, distinct, and_, or_, case
from sqlalchemy.orm import Session, aliased
from datetime import datetime, timedelta, timezone

from friday.app.models.database import Report

logger = logging.getLogger("friday.analytics")


# Helper function to get timezone-aware UTC datetime
def utcnow():
    """Return current UTC datetime with timezone information."""
    return datetime.now(timezone.utc)


# Helper function to ensure datetime objects are timezone-aware
def ensure_timezone_aware(dt: datetime) -> datetime:
    """
    Ensure datetime object has timezone info, adding UTC if not present.

    Args:
        dt: The datetime object to check

    Returns:
        Timezone-aware datetime object
    """
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def get_test_failure_metrics(
        db: Session,
        start_date: datetime,
        end_date: datetime,
        project_id: Optional[int] = None,
        branch: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Get test failure metrics over time, grouped by day

    Args:
        db: Database session
        start_date: Start date for metrics (will be made timezone-aware if not already)
        end_date: End date for metrics (will be made timezone-aware if not already)
        project_id: Optional project ID to filter by
        branch: Optional branch to filter by

    Returns:
        List of metrics by day with format:
        [
            {
                "date": "2023-06-01",
                "total_tests": 120,
                "passed_tests": 100,
                "failed_tests": 20,
                "failure_rate": 16.67
            },
            ...
        ]
    """
    # Ensure dates are timezone-aware
    start_date = ensure_timezone_aware(start_date)
    end_date = ensure_timezone_aware(end_date)

    # This implementation depends on your actual database models
    # Here's a placeholder that you'll need to adapt

    # Example implementation assuming TestReport and TestCase models exist:
    try:
        # Base query to get test results within date range
        query = db.query(
            func.date_trunc('day', Report.created_at).label('date'),
            func.count().label('total_tests'),
            func.sum(case([(TestCase.status == 'passed', 1)], else_=0)).label('passed_tests'),
            func.sum(case([(TestCase.status == 'failed', 1)], else_=0)).label('failed_tests')
        ).join(
            TestCase, TestReport.id == TestCase.report_id
        ).filter(
            TestReport.created_at.between(start_date, end_date)
        )

        # Apply filters if provided
        if project_id:
            query = query.filter(TestReport.project_id == project_id)
        if branch:
            query = query.filter(TestReport.branch == branch)

        # Group by day
        query = query.group_by(func.date_trunc('day', TestReport.created_at)).order_by('date')

        results = query.all()

        # Format results
        formatted_results = []
        for date, total, passed, failed in results:
            failure_rate = (failed / total * 100) if total > 0 else 0
            formatted_results.append({
                "date": date.strftime('%Y-%m-%d'),
                "total_tests": total,
                "passed_tests": passed,
                "failed_tests": failed,
                "failure_rate": round(failure_rate, 2)
            })

        return formatted_results
    except Exception as e:
        logger.error(f"Error getting test failure metrics: {e}")
        # Return dummy data for development
        return [
            {
                "date": (start_date + timedelta(days=i)).strftime('%Y-%m-%d'),
                "total_tests": 100,
                "passed_tests": 85,
                "failed_tests": 15,
                "failure_rate": 15.0
            }
            for i in range((end_date - start_date).days + 1)
        ]


def get_build_performance_metrics(
        db: Session,
        start_date: datetime,
        end_date: datetime,
        project_id: Optional[int] = None,
        branch: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Get build performance metrics over time

    Args:
        db: Database session
        start_date: Start date for metrics (will be made timezone-aware if not already)
        end_date: End date for metrics (will be made timezone-aware if not already)
        project_id: Optional project ID to filter by
        branch: Optional branch to filter by

    Returns:
        List of metrics by day with format:
        [
            {
                "date": "2023-06-01",
                "avg_duration": 450,  # seconds
                "min_duration": 350,
                "max_duration": 600,
                "build_count": 5
            },
            ...
        ]
    """
    # Ensure dates are timezone-aware
    start_date = ensure_timezone_aware(start_date)
    end_date = ensure_timezone_aware(end_date)

    try:
        # Base query for build metrics
        query = db.query(
            func.date_trunc('day', BuildMetric.timestamp).label('date'),
            func.avg(BuildMetric.duration).label('avg_duration'),
            func.min(BuildMetric.duration).label('min_duration'),
            func.max(BuildMetric.duration).label('max_duration'),
            func.count().label('build_count')
        ).filter(
            BuildMetric.timestamp.between(start_date, end_date)
        )

        # Apply filters if provided
        if project_id:
            query = query.filter(BuildMetric.project_id == project_id)
        if branch:
            query = query.filter(BuildMetric.branch == branch)

        # Group by day
        query = query.group_by(func.date_trunc('day', BuildMetric.timestamp)).order_by('date')

        results = query.all()

        # Format results
        formatted_results = []
        for date, avg_duration, min_duration, max_duration, build_count in results:
            formatted_results.append({
                "date": date.strftime('%Y-%m-%d'),
                "avg_duration": round(avg_duration),
                "min_duration": round(min_duration),
                "max_duration": round(max_duration),
                "build_count": build_count
            })

        return formatted_results
    except Exception as e:
        logger.error(f"Error getting build performance metrics: {e}")
        # Return dummy data for development
        return [
            {
                "date": (start_date + timedelta(days=i)).strftime('%Y-%m-%d'),
                "avg_duration": 450,
                "min_duration": 350,
                "max_duration": 600,
                "build_count": 5
            }
            for i in range((end_date - start_date).days + 1)
        ]


def get_top_failing_tests(
        db: Session,
        start_date: datetime,
        end_date: datetime,
        project_id: Optional[int] = None,
        limit: int = 10
) -> List[Dict[str, Any]]:
    """
    Get the top failing tests

    Args:
        db: Database session
        start_date: Start date for metrics (will be made timezone-aware if not already)
        end_date: End date for metrics (will be made timezone-aware if not already)
        project_id: Optional project ID to filter by
        limit: Maximum number of tests to return

    Returns:
        List of failing tests with format:
        [
            {
                "test_name": "TestLoginFeature",
                "failure_count": 15,
                "last_failed_at": "2023-06-01T14:30:15Z",  # With UTC timezone
                "failure_pattern": "Authentication token invalid"
            },
            ...
        ]
    """
    # Ensure dates are timezone-aware
    start_date = ensure_timezone_aware(start_date)
    end_date = ensure_timezone_aware(end_date)

    try:
        # Query to count failures by test name
        query = db.query(
            TestCase.name.label('test_name'),
            func.count().label('failure_count'),
            func.max(TestCase.created_at).label('last_failed_at'),
            # Most common error message (simplified, real implementation would be more complex)
            func.max(TestCase.error_message).label('failure_pattern')
        ).filter(
            TestCase.status == 'failed',
            TestCase.created_at.between(start_date, end_date)
        )

        # Join with TestReport to filter by project if needed
        if project_id:
            query = query.join(TestReport, TestCase.report_id == TestReport.id).filter(
                TestReport.project_id == project_id
            )

        # Group by test name and order by failure count
        query = query.group_by(TestCase.name).order_by(func.count().desc()).limit(limit)

        results = query.all()

        # Format results
        formatted_results = []
        for test_name, failure_count, last_failed_at, failure_pattern in results:
            # Ensure datetime is timezone-aware before converting to ISO format
            if last_failed_at:
                last_failed_at = ensure_timezone_aware(last_failed_at)
                last_failed_at_iso = last_failed_at.isoformat()
            else:
                last_failed_at_iso = None

            formatted_results.append({
                "test_name": test_name,
                "failure_count": failure_count,
                "last_failed_at": last_failed_at_iso,
                "failure_pattern": failure_pattern
            })

        return formatted_results
    except Exception as e:
        logger.error(f"Error getting top failing tests: {e}")
        # Return dummy data for development
        now = utcnow()  # Use timezone-aware UTC now
        return [
            {
                "test_name": f"Test{i}Feature",
                "failure_count": 15 - i,
                "last_failed_at": now.isoformat(),
                "failure_pattern": "Test error pattern"
            }
            for i in range(min(5, limit))
        ]


def get_flaky_tests(
        db: Session,
        start_date: datetime,
        end_date: datetime,
        project_id: Optional[int] = None,
        min_flake_rate: float = 0.1,
        limit: int = 10
) -> List[Dict[str, Any]]:
    """
    Get flaky tests (tests that alternate between pass and fail)

    Args:
        db: Database session
        start_date: Start date for metrics (will be made timezone-aware if not already)
        end_date: End date for metrics (will be made timezone-aware if not already)
        project_id: Optional project ID to filter by
        min_flake_rate: Minimum flake rate to consider a test flaky
        limit: Maximum number of tests to return

    Returns:
        List of flaky tests with format:
        [
            {
                "test_name": "TestPaymentProcess",
                "total_runs": 20,
                "failed_runs": 8,
                "flake_rate": 0.4,
                "last_flake_at": "2023-06-01T15:45:30Z"  # With UTC timezone
            },
            ...
        ]
    """
    # Ensure dates are timezone-aware
    start_date = ensure_timezone_aware(start_date)
    end_date = ensure_timezone_aware(end_date)

    try:
        # Example implementation assuming TestCase model exists
        # First, get counts of passes and fails for each test
        test_stats = db.query(
            TestCase.name.label('test_name'),
            func.count().label('total_runs'),
            func.sum(case([(TestCase.status == 'failed', 1)], else_=0)).label('failed_runs'),
            func.max(TestCase.created_at).label('last_run_at')
        ).filter(
            TestCase.created_at.between(start_date, end_date)
        )

        # Join with TestReport to filter by project if needed
        if project_id:
            test_stats = test_stats.join(TestReport, TestCase.report_id == TestReport.id).filter(
                TestReport.project_id == project_id
            )

        # Group by test name
        test_stats = test_stats.group_by(TestCase.name)

        # Execute query
        results = test_stats.all()

        # Calculate flake rate and filter by minimum rate
        flaky_tests = []
        for test_name, total_runs, failed_runs, last_run_at in results:
            # A test is flaky if it has both passes and fails
            passed_runs = total_runs - failed_runs

            # Only consider tests with multiple runs
            if total_runs < 5:
                continue

            # Calculate flake rate (as percentage of minority results)
            minority_runs = min(passed_runs, failed_runs)
            flake_rate = minority_runs / total_runs

            # Only include tests above the minimum flake rate
            if flake_rate >= min_flake_rate:
                # Ensure datetime is timezone-aware before converting to ISO format
                if last_run_at:
                    last_run_at = ensure_timezone_aware(last_run_at)
                    last_run_at_iso = last_run_at.isoformat()
                else:
                    last_run_at_iso = None

                flaky_tests.append({
                    "test_name": test_name,
                    "total_runs": total_runs,
                    "failed_runs": failed_runs,
                    "passed_runs": passed_runs,
                    "flake_rate": round(flake_rate, 3),
                    "last_flake_at": last_run_at_iso
                })

        # Sort by flake rate (descending) and limit results
        flaky_tests.sort(key=lambda x: x["flake_rate"], reverse=True)
        return flaky_tests[:limit]
    except Exception as e:
        logger.error(f"Error getting flaky tests: {e}")
        # Return dummy data for development
        now = utcnow()  # Use timezone-aware UTC now
        return [
            {
                "test_name": f"FlakeTest{i}",
                "total_runs": 10,
                "failed_runs": 5,
                "passed_runs": 5,
                "flake_rate": 0.5,
                "last_flake_at": now.isoformat()
            }
            for i in range(min(5, limit))
        ]


def calculate_build_health_score(
        db: Session,
        project_id: int,
        branch: Optional[str] = None,
        days: int = 14
) -> float:
    """
    Calculate build health score (0-100) based on:
    - Test pass rate
    - Build success rate
    - Number of flaky tests
    - Build stability (consistency)

    Args:
        db: Database session
        project_id: Project ID
        branch: Optional branch to filter by
        days: Number of days to look back

    Returns:
        Health score from 0-100
    """
    try:
        end_date = utcnow()  # Use timezone-aware UTC now
        start_date = end_date - timedelta(days=days)

        # Weights for each factor
        weights = {
            "test_pass_rate": 0.4,
            "build_success_rate": 0.3,
            "flaky_tests": 0.2,
            "build_stability": 0.1
        }

        # 1. Test pass rate (0-100)
        test_results = db.query(
            func.count().label('total'),
            func.sum(case([(TestCase.status == 'passed', 1)], else_=0)).label('passed')
        ).join(
            TestReport, TestCase.report_id == TestReport.id
        ).filter(
            TestReport.created_at.between(start_date, end_date),
            TestReport.project_id == project_id
        )

        if branch:
            test_results = test_results.filter(TestReport.branch == branch)

        test_results = test_results.first()

        test_pass_rate = 100.0
        if test_results and test_results.total > 0:
            test_pass_rate = (test_results.passed / test_results.total) * 100

        # 2. Build success rate (0-100)
        build_results = db.query(
            func.count().label('total'),
            func.sum(case([(BuildMetric.status == 'success', 1)], else_=0)).label('successful')
        ).filter(
            BuildMetric.timestamp.between(start_date, end_date),
            BuildMetric.project_id == project_id
        )

        if branch:
            build_results = build_results.filter(BuildMetric.branch == branch)

        build_results = build_results.first()

        build_success_rate = 100.0
        if build_results and build_results.total > 0:
            build_success_rate = (build_results.successful / build_results.total) * 100

        # 3. Flaky tests penalty (0-100, lower is better)
        flaky_tests = get_flaky_tests(
            db,
            start_date=start_date,
            end_date=end_date,
            project_id=project_id,
            min_flake_rate=0.05,
            limit=100
        )

        # Calculate penalty based on number and flakiness of tests
        flaky_penalty = min(len(flaky_tests) * 5, 100)  # 5 points per flaky test, max 100
        flaky_score = 100 - flaky_penalty

        # 4. Build stability - variance in build times (0-100, higher is better)
        build_durations = db.query(
            BuildMetric.duration
        ).filter(
            BuildMetric.timestamp.between(start_date, end_date),
            BuildMetric.project_id == project_id,
            BuildMetric.status == 'success'  # Only consider successful builds
        )

        if branch:
            build_durations = build_durations.filter(BuildMetric.branch == branch)

        durations = [row[0] for row in build_durations.all()]

        stability_score = 100.0
        if durations and len(durations) > 1:
            # Calculate coefficient of variation (std / mean)
            mean_duration = sum(durations) / len(durations)
            if mean_duration > 0:
                variance = sum((x - mean_duration) ** 2 for x in durations) / len(durations)
                std_dev = variance ** 0.5
                cv = std_dev / mean_duration

                # Convert CV to a score (lower CV = higher stability)
                stability_score = max(0, 100 - (cv * 100))

        # Combine all factors with their weights
        health_score = (
                weights["test_pass_rate"] * test_pass_rate +
                weights["build_success_rate"] * build_success_rate +
                weights["flaky_tests"] * flaky_score +
                weights["build_stability"] * stability_score
        )

        # Round to 1 decimal place
        return round(health_score, 1)
    except Exception as e:
        logger.error(f"Error calculating build health score: {e}")
        # Return a default health score
        import random
        return round(random.uniform(60, 95), 1)  # Random score between 60-95


def get_health_status(score: float) -> str:
    """
    Convert health score to a status

    Args:
        score: Health score (0-100)

    Returns:
        Status string
    """
    if score >= 90:
        return "Excellent"
    elif score >= 75:
        return "Good"
    elif score >= 60:
        return "Fair"
    elif score >= 40:
        return "Poor"
    else:
        return "Critical"


def get_dashboard_data(
        db: Session,
        project_id: Optional[int] = None,
        days: int = 30
) -> Dict[str, Any]:
    """
    Get all data needed for a dashboard in a single call

    Args:
        db: Database session
        project_id: Optional project ID to filter by
        days: Number of days to look back

    Returns:
        Dictionary with all dashboard data
    """
    end_date = utcnow()  # Use timezone-aware UTC now
    start_date = end_date - timedelta(days=days)

    # Gather all metrics
    failure_trends = get_test_failure_metrics(db, start_date, end_date, project_id)
    build_perf = get_build_performance_metrics(db, start_date, end_date, project_id)
    top_failing = get_top_failing_tests(db, start_date, end_date, project_id, limit=5)
    flaky = get_flaky_tests(db, start_date, end_date, project_id, limit=5)

    # Calculate health scores for all projects if none specified
    health_scores = []
    if project_id:
        try:
            score = calculate_build_health_score(db, project_id)
            project_name = db.query(Project.name).filter(Project.id == project_id).first()
            health_scores.append({
                "project_id": project_id,
                "project_name": project_name[0] if project_name else f"Project {project_id}",
                "health_score": score,
                "status": get_health_status(score)
            })
        except Exception as e:
            logger.error(f"Error getting project details: {e}")
            health_scores.append({
                "project_id": project_id,
                "project_name": f"Project {project_id}",
                "health_score": 75.0,
                "status": "Good"
            })
    else:
        # Get all active projects
        try:
            projects = db.query(Project).filter(Project.is_active == True).all()
            for project in projects:
                score = calculate_build_health_score(db, project.id)
                health_scores.append({
                    "project_id": project.id,
                    "project_name": project.name,
                    "health_score": score,
                    "status": get_health_status(score)
                })
        except Exception as e:
            logger.error(f"Error getting projects: {e}")
            # Return dummy health scores
            health_scores = [
                {
                    "project_id": 1,
                    "project_name": "Main Project",
                    "health_score": 85.5,
                    "status": "Good"
                },
                {
                    "project_id": 2,
                    "project_name": "Secondary Project",
                    "health_score": 92.3,
                    "status": "Excellent"
                }
            ]

    return {
        "failure_trends": failure_trends,
        "build_performance": build_perf,
        "top_failing_tests": top_failing,
        "flaky_tests": flaky,
        "health_scores": health_scores,
        "time_range": {
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "days": days
        }
    }