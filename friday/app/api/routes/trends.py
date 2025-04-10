# app/api/routes/trends.py
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Dict, Any, Optional, List
import logging
from datetime import datetime, timedelta

from app.config import settings
from app.services.orchestrator import ServiceOrchestrator
from app.api.dependencies import get_orchestrator_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix=settings.API_PREFIX, tags=["trends"])


@router.get("/trends", response_model=Dict[str, Any])
async def get_trends(
        time_range: str = Query("week", description="Time range for trend analysis: 'week', 'month', or 'quarter'"),
        feature: Optional[str] = Query(None, description="Filter results by feature"),
        tag: Optional[str] = Query(None, description="Filter results by tag"),
        orchestrator: ServiceOrchestrator = Depends(get_orchestrator_service)
):
    """
    Get trends data for the dashboard.

    This endpoint returns historical test trend data for daily trends, build trends,
    and top failures.
    """
    try:
        # Determine date range based on time_range parameter
        end_date = datetime.now()
        if time_range == "week":
            start_date = end_date - timedelta(days=7)
        elif time_range == "month":
            start_date = end_date - timedelta(days=30)
        elif time_range == "quarter":
            start_date = end_date - timedelta(days=90)
        else:  # Default to week
            start_date = end_date - timedelta(days=7)

        # Log the date range for debugging
        logger.info(f"Fetching trends from {start_date.isoformat()} to {end_date.isoformat()}")

        # Get client and verify connection
        client = orchestrator.vector_db.client
        collection_name = orchestrator.vector_db.cucumber_collection

        # Log the collection info
        try:
            collection_info = client.get_collection(collection_name)
            logger.info(f"Connected to collection: {collection_name}, points: {collection_info.points_count}")
        except Exception as e:
            logger.error(f"Error getting collection info: {str(e)}")

        from qdrant_client.http import models as qdrant_models

        # Create a minimal filter to get all test cases first, then manually filter later
        # This helps us debug if the issue is with the filtering
        base_filter = qdrant_models.Filter(
            must=[
                qdrant_models.FieldCondition(
                    key="type",
                    match=qdrant_models.MatchValue(value="test_case")
                )
            ]
        )

        # Add feature filter if provided
        if feature:
            base_filter.must.append(
                qdrant_models.FieldCondition(
                    key="feature",
                    match=qdrant_models.MatchValue(value=feature)
                )
            )

        # Add tag filter if provided
        if tag:
            base_filter.must.append(
                qdrant_models.FieldCondition(
                    key="tags",
                    match=qdrant_models.MatchAny(any=[tag])
                )
            )

        # First, check if we have any test_case documents at all and get total document count
        total_count = client.count(
            collection_name=collection_name,
            count_filter=base_filter
        ).count

        # Count all documents regardless of type
        all_docs_count = client.count(
            collection_name=collection_name,
            count_filter=None
        ).count

        logger.info(f"Total test case documents in collection: {total_count}")
        logger.info(f"Total documents of any type in collection: {all_docs_count}")

        if total_count == 0:
            # If there are documents but none match our filter, sample what's in the collection
            if all_docs_count > 0:
                sample_docs, _ = client.scroll(
                    collection_name=collection_name,
                    limit=5,
                    with_payload=True
                )

                for i, doc in enumerate(sample_docs):
                    logger.info(f"Sample document {i}: Type={doc.payload.get('type')}, Keys={list(doc.payload.keys())}")

            return {
                "status": "success",
                "trends": {
                    "daily": [],
                    "builds": [],
                    "top_failures": []
                },
                "debug_info": {
                    "total_documents": all_docs_count,
                    "test_cases_found": total_count,
                    "time_range": time_range,
                    "applied_filters": {
                        "feature": feature,
                        "tag": tag
                    }
                }
            }

        # If we have test cases, retrieve them in batches
        all_test_cases = []
        offset = None
        limit = 1000

        while True:
            test_cases_batch, offset = client.scroll(
                collection_name=collection_name,
                scroll_filter=base_filter,
                limit=limit,
                offset=offset,
                with_payload=True,
                with_vectors=False
            )

            logger.info(f"Retrieved batch of {len(test_cases_batch)} test cases")

            # If we got some test cases, log a few examples to understand their structure
            if len(test_cases_batch) > 0 and len(all_test_cases) == 0:
                for i, tc in enumerate(test_cases_batch[:3]):
                    logger.info(f"Example test case {i}: Keys={list(tc.payload.keys())}")
                    logger.info(f"Example test case {i}: timestamp={tc.payload.get('timestamp', 'MISSING')}")
                    logger.info(f"Example test case {i}: status={tc.payload.get('status', 'MISSING')}")
                    logger.info(f"Example test case {i}: build_number={tc.payload.get('build_number', 'MISSING')}")

            # Apply date filtering if we can find timestamps
            date_filtered_batch = []
            for tc in test_cases_batch:
                # Try multiple possible timestamp field names
                timestamp = None
                for field in ['timestamp', 'createdAt', 'created_at', 'date', 'run_date', 'test_date']:
                    if field in tc.payload:
                        timestamp = tc.payload[field]
                        break

                if timestamp:
                    try:
                        # Handle different timestamp formats
                        if isinstance(timestamp, str):
                            if 'Z' in timestamp:
                                tc_date = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                            else:
                                tc_date = datetime.fromisoformat(timestamp)
                        elif isinstance(timestamp, int) or isinstance(timestamp, float):
                            # Handle epoch timestamps
                            tc_date = datetime.fromtimestamp(timestamp)
                        else:
                            continue

                        # For debugging, accept all timestamps initially
                        date_filtered_batch.append(tc)
                    except (ValueError, TypeError) as e:
                        logger.warning(f"Error parsing timestamp {timestamp}: {str(e)}")
                else:
                    # Include records without timestamps for debugging
                    date_filtered_batch.append(tc)

            all_test_cases.extend(date_filtered_batch)

            if offset is None or len(test_cases_batch) < limit:
                # No more results
                break

        logger.info(f"Total test cases after date filtering: {len(all_test_cases)}")

        # If we have no test cases after filtering, return empty results
        if len(all_test_cases) == 0:
            return {
                "status": "success",
                "trends": {
                    "daily": [],
                    "builds": [],
                    "top_failures": []
                },
                "debug_info": {
                    "total_documents": all_docs_count,
                    "test_cases_found": total_count,
                    "test_cases_after_date_filter": 0,
                    "time_range": time_range,
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat()
                }
            }

        # Log sample test cases to understand their structure better
        if len(all_test_cases) > 0:
            for i, tc in enumerate(all_test_cases[:5]):
                logger.info(f"Test case {i} has no timestamp field. Available fields: {list(tc.payload.keys())}")

        # First, collect all the unique report_ids from test cases
        report_ids = set()
        for tc in all_test_cases:
            if 'report_id' in tc.payload:
                report_ids.add(tc.payload['report_id'])

        logger.info(f"Found {len(report_ids)} unique report IDs from test cases")

        # Now get the reports with their timestamps
        reports_data = {}
        if report_ids:
            # Create a filter for reports
            report_filter = qdrant_models.Filter(
                must=[
                    qdrant_models.FieldCondition(
                        key="type",
                        match=qdrant_models.MatchValue(value="report")
                    ),
                    qdrant_models.FieldCondition(
                        key="id",
                        match=qdrant_models.MatchAny(any=list(report_ids))
                    )
                ]
            )

            # Get reports
            reports_batch, _ = client.scroll(
                collection_name=collection_name,
                scroll_filter=report_filter,
                limit=len(report_ids) + 10,  # Add some buffer
                with_payload=True,
                with_vectors=False
            )

            logger.info(f"Retrieved {len(reports_batch)} reports")

            # If we got reports, log a sample to see their structure
            if len(reports_batch) > 0:
                for i, report in enumerate(reports_batch[:3]):
                    logger.info(f"Example report {i}: Keys={list(report.payload.keys())}")
                    logger.info(f"Example report {i}: timestamp={report.payload.get('timestamp', 'MISSING')}")

            # Create a map of report_id to timestamp
            for report in reports_batch:
                if 'id' in report.payload and 'timestamp' in report.payload:
                    reports_data[report.payload['id']] = {
                        'timestamp': report.payload['timestamp']
                    }

        # Now, group test cases by day using the report timestamps
        daily_data = {}
        for tc in all_test_cases:
            # Get the report_id and look up its timestamp
            report_id = tc.payload.get('report_id')
            if not report_id or report_id not in reports_data:
                continue

            timestamp = reports_data[report_id].get('timestamp')
            if not timestamp:
                continue

            try:
                # Parse timestamp with flexible format handling
                if isinstance(timestamp, str):
                    if 'Z' in timestamp:
                        tc_datetime = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                    else:
                        tc_datetime = datetime.fromisoformat(timestamp)
                elif isinstance(timestamp, int) or isinstance(timestamp, float):
                    tc_datetime = datetime.fromtimestamp(timestamp)
                else:
                    continue

                # Use a date key that includes year for proper uniqueness
                date_key = tc_datetime.strftime("%Y-%m-%d")

                # Format display date as "Apr 10" for the response
                date_str = tc_datetime.strftime("%b %-d")  # Format: "Apr 10"

                if date_key not in daily_data:
                    daily_data[date_key] = {
                        "date": date_str,  # Use the formatted string for display
                        "total_scenarios": 0,
                        "passed_scenarios": 0,
                        "failed_scenarios": 0,
                        "pass_rate": 0.0
                    }

                # Process status as before
                status = tc.payload.get('status', 'UNKNOWN')
                if status:
                    # Normalize status values
                    status = status.upper() if isinstance(status, str) else status

                daily_data[date_key]["total_scenarios"] += 1

                if status in ["PASSED", "PASS", "SUCCESS", "SUCCESSFUL", True, 1]:
                    daily_data[date_key]["passed_scenarios"] += 1
                elif status in ["FAILED", "FAIL", "FAILURE", "ERROR", False, 0]:
                    daily_data[date_key]["failed_scenarios"] += 1
            except (ValueError, TypeError) as e:
                logger.warning(f"Error processing test case for daily trends: {str(e)}")

        # Calculate pass rates for daily data
        for date_key, data in daily_data.items():
            if data["total_scenarios"] > 0:
                data["pass_rate"] = round(data["passed_scenarios"] / data["total_scenarios"], 3)

        # Sort daily trends by date key (which includes year)
        daily_trends = [data for _, data in sorted(daily_data.items(), key=lambda x: x[0])]

        logger.info(f"Generated {len(daily_trends)} daily trend data points")

        # Build trends - Group test cases by build with flexible field mapping
        build_data = {}
        for tc in all_test_cases:
            # Try multiple field names for build identification
            build_number = None
            for field in ['build_number', 'build', 'buildNumber', 'build_id', 'buildId']:
                if field in tc.payload:
                    build_number = tc.payload[field]
                    break

            if not build_number:
                # Try report_id as fallback
                for field in ['report_id', 'reportId', 'run_id', 'runId']:
                    if field in tc.payload:
                        build_number = tc.payload[field]
                        break

            if not build_number:
                continue

            # Ensure build number has # prefix
            if isinstance(build_number, str) and not build_number.startswith('#'):
                build_number = f"#{build_number}"
            else:
                build_number = f"#{build_number}"

            if build_number not in build_data:
                build_data[build_number] = {
                    "build_number": build_number,
                    "total_scenarios": 0,
                    "passed_scenarios": 0,
                    "pass_rate": 0.0
                }

            # Try multiple status field names and normalize values
            status = None
            for field in ['status', 'test_status', 'result']:
                if field in tc.payload:
                    status = tc.payload[field]
                    break

            if status:
                # Normalize status values
                status = status.upper() if isinstance(status, str) else status
            else:
                status = "UNKNOWN"

            build_data[build_number]["total_scenarios"] += 1

            if status in ["PASSED", "PASS", "SUCCESS", "SUCCESSFUL", True, 1]:
                build_data[build_number]["passed_scenarios"] += 1

        # Calculate pass rates for builds
        for build, data in build_data.items():
            if data["total_scenarios"] > 0:
                data["pass_rate"] = round(data["passed_scenarios"] / data["total_scenarios"], 3)

        # Sort build trends by build number (assuming build numbers have a numerical component)
        build_trends = sorted(
            build_data.values(),
            key=lambda x: x["build_number"],
            reverse=True
        )

        # Remove the total_scenarios and passed_scenarios fields to match required response format
        for build in build_trends:
            build.pop("total_scenarios", None)
            build.pop("passed_scenarios", None)

        logger.info(f"Generated {len(build_trends)} build trend data points")

        # Top failures - Group failed test cases by scenario name
        failure_data = {}
        total_failures = 0

        for tc in all_test_cases:
            # Try multiple status field names and normalize values
            status = None
            for field in ['status', 'test_status', 'result']:
                if field in tc.payload:
                    status = tc.payload[field]
                    break

            if status:
                # Normalize status values
                status = status.upper() if isinstance(status, str) else status
            else:
                status = "UNKNOWN"

            if status not in ["FAILED", "FAIL", "FAILURE", "ERROR", False, 0]:
                continue

            total_failures += 1

            # Try multiple field names for the test name
            name = None
            for field in ['name', 'test_name', 'scenario_name', 'title', 'description']:
                if field in tc.payload:
                    name = tc.payload[field]
                    break

            if not name:
                continue

            if name not in failure_data:
                failure_data[name] = {
                    "name": name,
                    "occurrences": 0,
                    "failure_rate": 0.0
                }

            failure_data[name]["occurrences"] += 1

        # Calculate failure rates
        for name, data in failure_data.items():
            if total_failures > 0:
                data["failure_rate"] = round(data["occurrences"] / total_failures, 2)

        # Sort top failures by occurrences (descending)
        top_failures = sorted(
            failure_data.values(),
            key=lambda x: x["occurrences"],
            reverse=True
        )[:5]  # Limit to top 5

        logger.info(f"Generated {len(top_failures)} top failures data points")

        # Return the complete trends data
        return {
            "status": "success",
            "trends": {
                "daily": daily_trends,
                "builds": build_trends,
                "top_failures": top_failures
            }
        }
    except Exception as e:
        logger.error(f"Error retrieving trends: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve trends: {str(e)}"
        )


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