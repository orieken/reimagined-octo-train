# app/services/analytics.py
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import numpy as np
import pandas as pd
from collections import defaultdict, Counter
from itertools import combinations
import uuid

from app.config import settings
from app.services.orchestrator import ServiceOrchestrator

from app.models import TrendAnalysis
from app.models.schemas import TestFlakiness, TrendPoint, FailureCorrelation, PerformanceMetrics, \
    PerformanceTestData, AnalyticsResponse
from app.services import datetime_service as dt

logger = logging.getLogger(__name__)


class AnalyticsService:
    """
    Service for analyzing test results and extracting insights.
    """

    def __init__(self, orchestrator: ServiceOrchestrator):
        self.orchestrator = orchestrator

    async def _get_reports_in_timeframe(
            self,
            days: int,
            environment: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Helper method to get reports within a specific timeframe.
        """
        # Build query
        query_parts = ["test report"]

        if environment:
            query_parts.append(f"environment:{environment}")

        query = " ".join(query_parts)

        # Build filters
        filters = {"type": "report"}

        if environment:
            filters["environment"] = environment

        # Perform search
        search_results = await self.orchestrator.semantic_search(
            query=query,
            filters=filters,
            limit=100  # Adjust based on expected number of reports
        )

        # Apply date filter
        cutoff_date = dt.now_utc() - timedelta(days=days)
        filtered_reports = []

        for result in search_results:
            try:
                # Parse timestamp and check if it's within the date range
                timestamp = result.payload.get("timestamp", "")
                if timestamp:
                    result_date = dt.parse_iso_datetime_to_utc(timestamp)
                    if result_date >= cutoff_date:
                        filtered_reports.append(result)
            except (ValueError, TypeError):
                # If timestamp parsing fails, include the result anyway
                filtered_reports.append(result)

        return filtered_reports

    async def _get_test_cases_for_reports(
            self,
            reports: List[Dict[str, Any]],
            feature: Optional[str] = None
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Helper method to get test cases for a list of reports.
        Return a dictionary mapping report_id to list of test cases.
        """
        # Generate a simple query embedding
        query_text = "test case details"
        query_embedding = await self.orchestrator.llm.generate_embedding(query_text)

        # Get test cases for each report
        report_test_cases = {}

        for report in reports:
            report_id = report.id

            # Get test cases for this report
            test_cases = self.orchestrator.vector_db.search_test_cases(
                query_embedding=query_embedding,
                report_id=report_id,
                limit=1000  # Adjust based on expected number of test cases
            )

            # Apply feature filter if needed
            if feature:
                test_cases = [tc for tc in test_cases if tc.payload.get("feature") == feature]

            report_test_cases[report_id] = test_cases

        return report_test_cases

    async def identify_flaky_tests(
            self,
            days: int,
            environment: Optional[str] = None,
            threshold: float = 0.1,
            limit: int = 10
    ) -> List[TestFlakiness]:
        """
        Identify flaky tests based on historical data.

        A test is considered flaky if its pass/fail status changes across runs
        without code changes. This method analyzes test results over the specified
        time period and identifies tests with inconsistent results.

        Args:
            days: Number of days to analyze
            environment: Optional environment filter
            threshold: Flakiness threshold (0.0-1.0)
            limit: Maximum number of flaky tests to return

        Returns:
            List of TestFlakiness objects representing flaky tests
        """
        # Get reports in timeframe
        reports = await self._get_reports_in_timeframe(days, environment)

        # Get test cases for each report
        report_test_cases = await self._get_test_cases_for_reports(reports)

        # Analyze test cases
        test_results = {}

        for report_id, test_cases in report_test_cases.items():
            for tc in test_cases:
                tc_data = tc.payload
                test_name = tc_data.get("name", "")
                feature = tc_data.get("feature", "")
                key = f"{feature}::{test_name}"

                if key not in test_results:
                    test_results[key] = {
                        "name": test_name,
                        "feature": feature,
                        "runs": 0,
                        "passes": 0,
                        "failures": 0,
                        "history": []
                    }

                test_results[key]["runs"] += 1

                status = tc_data.get("status", "UNKNOWN")
                is_pass = status == "PASSED"

                if is_pass:
                    test_results[key]["passes"] += 1
                else:
                    test_results[key]["failures"] += 1

                # Add to history
                test_results[key]["history"].append({
                    "report_id": report_id,
                    "status": status,
                    "timestamp": tc_data.get("timestamp", ""),
                    "duration": tc_data.get("duration", 0)
                })

        # Calculate flakiness scores
        flaky_tests = []

        for key, data in test_results.items():
            if data["runs"] < 2:
                continue  # Need at least 2 runs to calculate flakiness

            # Calculate flakiness score
            if data["runs"] == 0:
                flakiness = 0.0
            else:
                # Tests that always pass or always fail are not flaky
                if data["passes"] == 0 or data["failures"] == 0:
                    flakiness = 0.0
                else:
                    # Flakiness is highest when passes/failures are close to 50/50
                    pass_rate = data["passes"] / data["runs"]
                    flakiness = 1.0 - abs(0.5 - pass_rate) * 2.0

            # Only include tests above the threshold
            if flakiness >= threshold:
                flaky_tests.append(TestFlakiness(
                    id=str(uuid.uuid4()),
                    name=data["name"],
                    feature=data["feature"],
                    flakiness_score=flakiness,
                    total_runs=data["runs"],
                    pass_count=data["passes"],
                    fail_count=data["failures"],
                    history=data["history"]
                ))

        # Sort by flakiness score (descending)
        flaky_tests.sort(key=lambda x: x.flakiness_score, reverse=True)

        # Limit results
        return flaky_tests[:limit]

    async def analyze_trends(
            self,
            days: int,
            environment: Optional[str] = None,
            feature: Optional[str] = None
    ) -> TrendAnalysis:
        """
        Analyze test result trends over time.

        This method analyzes trends in test results, including pass rates,
        test durations, and other metrics over the specified time period.

        Args:
            days: Number of days to analyze
            environment: Optional environment filter
            feature: Optional feature filter

        Returns:
            TrendAnalysis object representing test result trends
        """
        # Get reports in timeframe
        reports = await self._get_reports_in_timeframe(days, environment)

        # Sort reports by timestamp
        reports.sort(key=lambda r: r.payload.get("timestamp", ""))

        # Get test cases for each report
        report_test_cases = await self._get_test_cases_for_reports(reports, feature)

        # Prepare data points
        data_points = []

        for report in reports:
            report_id = report.id
            timestamp = report.payload.get("timestamp", "")

            # Skip reports without timestamp
            if not timestamp:
                continue

            # Get test cases for this report
            test_cases = report_test_cases.get(report_id, [])

            # Calculate metrics
            total_tests = len(test_cases)
            passed_tests = sum(1 for tc in test_cases if tc.payload.get("status") == "PASSED")
            failed_tests = sum(1 for tc in test_cases if tc.payload.get("status") == "FAILED")

            if total_tests > 0:
                pass_rate = (passed_tests / total_tests) * 100
            else:
                pass_rate = 0

            avg_duration = 0
            if total_tests > 0:
                durations = [tc.payload.get("duration", 0) for tc in test_cases]
                avg_duration = sum(durations) / total_tests

            # Create data point
            data_point = TrendPoint(
                timestamp=timestamp,
                report_id=report_id,
                total_tests=total_tests,
                passed_tests=passed_tests,
                failed_tests=failed_tests,
                pass_rate=pass_rate,
                avg_duration=avg_duration
            )

            data_points.append(data_point)

        # Create trend analysis
        return TrendAnalysis(
            points=data_points,
            days_analyzed=days,
            environment=environment,
            feature=feature
        )

    async def analyze_failure_correlations(
            self,
            report_id: Optional[str] = None,
            days: int = 30,
            limit: int = 10
    ) -> List[FailureCorrelation]:
        """
        Analyze correlations between test failures.

        This method detects tests that tend to fail together, which may
        indicate common underlying issues or dependencies.

        Args:
            report_id: Optional specific report to analyze
            days: Number of days to analyze if no report specified
            limit: Maximum number of correlations to return

        Returns:
            List of FailureCorrelation objects
        """
        # Get failures to analyze
        if report_id:
            # Analyze specific report
            query_embedding = await self.orchestrator.llm.generate_embedding("test case")

            # Get failed test cases for this report
            test_cases = self.orchestrator.vector_db.search_test_cases(
                query_embedding=query_embedding,
                report_id=report_id,
                limit=1000
            )

            # Filter to failed tests
            failed_tests = [tc for tc in test_cases if tc.payload.get("status") == "FAILED"]

            # Analyze this single report
            reports = [{"id": report_id, "failed_tests": failed_tests}]

        else:
            # Analyze reports in timeframe
            raw_reports = await self._get_reports_in_timeframe(days)

            # Get test cases for each report
            report_test_cases = await self._get_test_cases_for_reports(raw_reports)

            # Filter to reports with failures
            reports = []

            for report in raw_reports:
                report_id = report.id
                test_cases = report_test_cases.get(report_id, [])

                # Filter to failed tests
                failed_tests = [tc for tc in test_cases if tc.payload.get("status") == "FAILED"]

                if failed_tests:
                    reports.append({
                        "id": report_id,
                        "failed_tests": failed_tests
                    })

        # Find failure correlations
        failure_counts = Counter()
        co_failure_counts = Counter()

        for report_data in reports:
            failed_tests = report_data["failed_tests"]

            # Skip if fewer than 2 failures
            if len(failed_tests) < 2:
                continue

            # Count individual failures
            for tc in failed_tests:
                test_key = f"{tc.payload.get('feature', '')}::{tc.payload.get('name', '')}"
                failure_counts[test_key] += 1

            # Count co-failures
            for tc1, tc2 in combinations(failed_tests, 2):
                test_key1 = f"{tc1.payload.get('feature', '')}::{tc1.payload.get('name', '')}"
                test_key2 = f"{tc2.payload.get('feature', '')}::{tc2.payload.get('name', '')}"

                # Ensure consistent ordering
                if test_key1 > test_key2:
                    test_key1, test_key2 = test_key2, test_key1

                co_failure_key = f"{test_key1}::{test_key2}"
                co_failure_counts[co_failure_key] += 1

        # Calculate correlation scores
        correlations = []

        for co_failure_key, count in co_failure_counts.items():
            test_keys = co_failure_key.split("::")
            test_key1 = f"{test_keys[0]}::{test_keys[1]}"
            test_key2 = f"{test_keys[2]}::{test_keys[3]}"

            # Get individual failure counts
            count1 = failure_counts[test_key1]
            count2 = failure_counts[test_key2]

            # Calculate correlation score (Jaccard index)
            union_count = count1 + count2 - count

            if union_count > 0:
                correlation_score = count / union_count
            else:
                correlation_score = 0

            # Split test keys into feature and name
            feature1, name1 = test_key1.split("::")
            feature2, name2 = test_key2.split("::")

            # Create correlation object
            correlation = FailureCorrelation(
                id=str(uuid.uuid4()),
                test1_name=name1,
                test1_feature=feature1,
                test2_name=name2,
                test2_feature=feature2,
                correlation_score=correlation_score,
                co_failure_count=count,
                test1_failure_count=count1,
                test2_failure_count=count2
            )

            correlations.append(correlation)

        # Sort by correlation score (descending)
        correlations.sort(key=lambda x: x.correlation_score, reverse=True)

        # Limit results
        return correlations[:limit]

    async def analyze_performance(
            self,
            days: int,
            environment: Optional[str] = None,
            feature: Optional[str] = None
    ) -> PerformanceMetrics:
        """
        Analyze test performance metrics.

        This method analyzes test performance metrics such as average duration,
        longest running tests, and performance trends over time.

        Args:
            days: Number of days to analyze
            environment: Optional environment filter
            feature: Optional feature filter

        Returns:
            PerformanceMetrics object representing test performance
        """
        # Get reports in timeframe
        reports = await self._get_reports_in_timeframe(days, environment)

        # Get test cases for each report
        report_test_cases = await self._get_test_cases_for_reports(reports, feature)

        # Analyze test durations
        test_durations = defaultdict(list)

        for report_id, test_cases in report_test_cases.items():
            for tc in test_cases:
                tc_data = tc.payload
                test_name = tc_data.get("name", "")
                feature_name = tc_data.get("feature", "")
                duration = tc_data.get("duration", 0)

                test_key = f"{feature_name}::{test_name}"
                test_durations[test_key].append({
                    "duration": duration,
                    "report_id": report_id,
                    "timestamp": tc_data.get("timestamp", "")
                })

        # Calculate performance metrics
        tests_data = []

        for test_key, durations in test_durations.items():
            if not durations:
                continue

            feature_name, test_name = test_key.split("::")

            # Calculate statistics
            duration_values = [d["duration"] for d in durations]
            avg_duration = sum(duration_values) / len(duration_values)
            min_duration = min(duration_values)
            max_duration = max(duration_values)

            # Calculate trend
            if len(duration_values) > 1:
                # Sort by timestamp
                sorted_durations = sorted(durations, key=lambda d: d.get("timestamp", ""))

                # Calculate linear regression
                indices = list(range(len(sorted_durations)))
                durations_array = [d["duration"] for d in sorted_durations]

                if len(indices) > 1:
                    # Simple linear regression
                    x = np.array(indices)
                    y = np.array(durations_array)

                    # Calculate slope
                    slope = np.polyfit(x, y, 1)[0]

                    # Normalize slope as percentage of average duration
                    if avg_duration > 0:
                        trend_percentage = (slope / avg_duration) * 100
                    else:
                        trend_percentage = 0
                else:
                    trend_percentage = 0
            else:
                trend_percentage = 0

            # Create test data
            test_data = PerformanceTestData(
                name=test_name,
                feature=feature_name,
                avg_duration=avg_duration,
                min_duration=min_duration,
                max_duration=max_duration,
                trend_percentage=trend_percentage,
                run_count=len(durations),
                history=durations
            )

            tests_data.append(test_data)

        # Sort by average duration (descending)
        tests_data.sort(key=lambda x: x.avg_duration, reverse=True)

        # Calculate overall metrics
        all_durations = [d["duration"] for durations in test_durations.values() for d in durations]

        if all_durations:
            overall_avg_duration = sum(all_durations) / len(all_durations)
        else:
            overall_avg_duration = 0

        # Create performance metrics
        return PerformanceMetrics(
            tests=tests_data,
            overall_avg_duration=overall_avg_duration,
            days_analyzed=days,
            environment=environment,
            feature=feature
        )

    async def generate_summary(
            self,
            days: int,
            environment: Optional[str] = None
    ) -> AnalyticsResponse:
        """
        Generate a comprehensive analytics summary.

        This method provides a comprehensive summary of test analytics,
        including trends, flaky tests, performance metrics, and correlations.

        Args:
            days: Number of days to analyze
            environment: Optional environment filter

        Returns:
            AnalyticsResponse object representing a comprehensive summary
        """
        # Get trend analysis
        trends = await self.analyze_trends(days, environment)

        # Get flaky tests
        flaky_tests = await self.identify_flaky_tests(days, environment)

        # Get performance metrics
        performance = await self.analyze_performance(days, environment)

        # Get failure correlations
        correlations = await self.analyze_failure_correlations(days=days)

        # Create summary
        return AnalyticsResponse(
            trends=trends,
            flaky_tests=flaky_tests,
            performance=performance,
            correlations=correlations,
            days_analyzed=days,
            environment=environment,
            timestamp=dt.isoformat_utc(dt.now_utc())
        )
