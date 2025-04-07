# app/api/routes/stats.py
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Dict, Any, Optional
import logging
from datetime import datetime, timedelta

from app.config import settings
from app.services.orchestrator import ServiceOrchestrator
from app.api.dependencies import get_orchestrator_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix=settings.API_PREFIX, tags=["stats"])

@router.get("/stats/summary", response_model=Dict[str, Any])
async def get_stats_summary(
        days: int = Query(30, description="Number of days to analyze"),
        environment: Optional[str] = Query(None, description="Filter by environment"),
        orchestrator: ServiceOrchestrator = Depends(get_orchestrator_service)
):
    """
    Get a summary of test statistics.

    This endpoint returns a summary of test statistics over the specified time period.
    """
    try:
        # Get client
        client = orchestrator.vector_db.client
        collection_name = orchestrator.vector_db.cucumber_collection

        # Build filters for reports
        from qdrant_client.http import models as qdrant_models

        report_filter = qdrant_models.Filter(
            must=[
                qdrant_models.FieldCondition(
                    key="type",
                    match=qdrant_models.MatchValue(value="report")
                )
            ]
        )

        # Add environment filter if provided
        if environment:
            report_filter.must.append(
                qdrant_models.FieldCondition(
                    key="environment",
                    match=qdrant_models.MatchValue(value=environment)
                )
            )

        # Retrieve all reports
        all_reports = []
        offset = None
        limit = 100

        # Cutoff date for filtering
        cutoff_date = datetime.now() - timedelta(days=days)

        # Retrieve reports in batches
        while True:
            reports_batch, offset = client.scroll(
                collection_name=collection_name,
                scroll_filter=report_filter,
                limit=limit,
                offset=offset,
                with_payload=True,
                with_vectors=False
            )

            # Filter by date
            for report in reports_batch:
                try:
                    timestamp = report.payload.get("timestamp", "")
                    if timestamp:
                        report_date = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                        if report_date >= cutoff_date:
                            all_reports.append(report)
                except (ValueError, TypeError):
                    # If timestamp parsing fails, include the report
                    all_reports.append(report)

            if offset is None or len(reports_batch) < limit:
                # No more results
                break

        # Calculate summary statistics
        total_reports = len(all_reports)
        total_tests = 0
        passed_tests = 0
        failed_tests = 0
        skipped_tests = 0
        total_duration = 0

        for report in all_reports:
            metadata = report.payload.get("metadata", {})
            total_tests += metadata.get("total_tests", 0)
            passed_tests += metadata.get("total_passed", 0) if "total_passed" in metadata else metadata.get(
                "passed_tests", 0)
            failed_tests += metadata.get("total_failed", 0) if "total_failed" in metadata else metadata.get(
                "failed_tests", 0)
            skipped_tests += metadata.get("total_skipped", 0) if "total_skipped" in metadata else metadata.get(
                "skipped_tests", 0)
            total_duration += report.payload.get("duration", 0)

        # Calculate pass rate
        if total_tests > 0:
            pass_rate = (passed_tests / total_tests) * 100
        else:
            pass_rate = 0

        # Calculate average duration
        if total_reports > 0:
            avg_duration = total_duration / total_reports
        else:
            avg_duration = 0

        return {
            "time_period": f"Last {days} days",
            "environment": environment or "All",
            "unique_builds": total_reports,
            "total_scenarios": total_tests,
            "passed_scenarios": passed_tests,
            "failed_scenarios": failed_tests,
            "skipped_scenarios": skipped_tests,
            "pass_rate": round(pass_rate, 2),
            "average_duration": round(avg_duration, 2),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error retrieving stats summary: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve stats summary: {str(e)}"
        )

@router.get("/stats/by-feature", response_model=List[Dict[str, Any]])
async def get_stats_by_feature(
        days: int = Query(30, description="Number of days to analyze"),
        environment: Optional[str] = Query(None, description="Filter by environment"),
        orchestrator: ServiceOrchestrator = Depends(get_orchestrator_service)
):
    """
    Get test statistics by feature.

    This endpoint returns test statistics grouped by feature.
    """
    try:
        # Build query
        query_parts = ["test statistics by feature"]

        if environment:
            query_parts.append(f"environment:{environment}")

        query = " ".join(query_parts)

        # Generate embedding for the query
        query_embedding = await orchestrator.llm.generate_embedding(query)

        # Search for test cases
        test_case_results = await orchestrator.semantic_search(
            query=query,
            filters={"type": "test_case"},
            limit=1000  # Adjust based on expected number of test cases
        )

        # Apply date filter
        cutoff_date = datetime.now() - timedelta(days=days)
        filtered_test_cases = []

        for tc in test_case_results:
            try:
                # We don't have direct date on test cases, but we could filter
                # based on report date if needed
                filtered_test_cases.append(tc)
            except Exception:
                filtered_test_cases.append(tc)

        # Apply environment filter if needed
        if environment:
            filtered_test_cases = [
                tc for tc in filtered_test_cases
                if tc.payload.get("environment") == environment
            ]

        # Group by feature
        feature_stats = {}
        for tc in filtered_test_cases:
            feature = tc.payload.get("feature", "Unknown")

            if feature not in feature_stats:
                feature_stats[feature] = {
                    "feature": feature,
                    "total_tests": 0,
                    "passed_tests": 0,
                    "failed_tests": 0,
                    "skipped_tests": 0,
                    "pass_rate": 0,
                    "average_duration": 0
                }

            feature_stats[feature]["total_tests"] += 1

            status = tc.payload.get("status")
            if status == "PASSED":
                feature_stats[feature]["passed_tests"] += 1
            elif status == "FAILED":
                feature_stats[feature]["failed_tests"] += 1
            elif status == "SKIPPED":
                feature_stats[feature]["skipped_tests"] += 1

            # Add duration to calculate average later
            feature_stats[feature]["average_duration"] += tc.payload.get("duration", 0)

        # Calculate pass rate and average duration
        for feature, stats in feature_stats.items():
            if stats["total_tests"] > 0:
                stats["pass_rate"] = (stats["passed_tests"] / stats["total_tests"]) * 100
                stats["average_duration"] /= stats["total_tests"]

            # Round values
            stats["pass_rate"] = round(stats["pass_rate"], 2)
            stats["average_duration"] = round(stats["average_duration"], 2)

        # Convert to list and sort by pass rate (descending)
        result = list(feature_stats.values())
        result.sort(key=lambda x: x["pass_rate"], reverse=True)

        return result
    except Exception as e:
        logger.error(f"Error retrieving stats by feature: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve stats by feature: {str(e)}"
        )


@router.get("/stats/by-environment", response_model=List[Dict[str, Any]])
async def get_stats_by_environment(
        days: int = Query(30, description="Number of days to analyze"),
        orchestrator: ServiceOrchestrator = Depends(get_orchestrator_service)
):
    """
    Get test statistics by environment.

    This endpoint returns test statistics grouped by environment.
    """
    try:
        # Build query
        query = "test statistics by environment"

        # Generate embedding for the query
        query_embedding = await orchestrator.llm.generate_embedding(query)

        # Search for reports
        report_results = await orchestrator.semantic_search(
            query=query,
            filters={"type": "report"},
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

        # Group by environment
        env_stats = {}
        for report in filtered_reports:
            environment = report.payload.get("environment", "Unknown")

            if environment not in env_stats:
                env_stats[environment] = {
                    "environment": environment,
                    "total_reports": 0,
                    "total_tests": 0,
                    "passed_tests": 0,
                    "failed_tests": 0,
                    "pass_rate": 0,
                    "average_duration": 0
                }

            env_stats[environment]["total_reports"] += 1

            metadata = report.payload.get("metadata", {})
            env_stats[environment]["total_tests"] += metadata.get("total_tests", 0)
            env_stats[environment]["passed_tests"] += metadata.get("total_passed", 0)
            env_stats[environment]["failed_tests"] += metadata.get("total_failed", 0)

            # Add duration to calculate average later
            env_stats[environment]["average_duration"] += report.payload.get("duration", 0)

        # Calculate pass rate and average duration
        for env, stats in env_stats.items():
            if stats["total_tests"] > 0:
                stats["pass_rate"] = (stats["passed_tests"] / stats["total_tests"]) * 100

            if stats["total_reports"] > 0:
                stats["average_duration"] /= stats["total_reports"]

            # Round values
            stats["pass_rate"] = round(stats["pass_rate"], 2)
            stats["average_duration"] = round(stats["average_duration"], 2)

        # Convert to list and sort by pass rate (descending)
        result = list(env_stats.values())
        result.sort(key=lambda x: x["pass_rate"], reverse=True)

        return result
    except Exception as e:
        logger.error(f"Error retrieving stats by environment: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve stats by environment: {str(e)}"
        )


@router.get("/stats", response_model=Dict[str, Any])
async def get_stats(
        days: int = Query(30, description="Number of days to analyze"),
        environment: Optional[str] = Query(None, description="Filter by environment"),
        orchestrator: ServiceOrchestrator = Depends(get_orchestrator_service)
):
    """
    Get test statistics for the dashboard.
    """
    try:
        # Get client
        client = orchestrator.vector_db.client
        collection_name = orchestrator.vector_db.cucumber_collection

        # Build filters for test cases
        from qdrant_client.http import models as qdrant_models

        test_case_filter = qdrant_models.Filter(
            must=[
                qdrant_models.FieldCondition(
                    key="type",
                    match=qdrant_models.MatchValue(value="test_case")
                )
            ]
        )

        # Add environment filter if provided
        if environment:
            test_case_filter.must.append(
                qdrant_models.FieldCondition(
                    key="environment",
                    match=qdrant_models.MatchValue(value=environment)
                )
            )

        # Count total scenarios
        total_count = client.count(
            collection_name=collection_name,
            count_filter=test_case_filter
        ).count

        # Count passed scenarios
        passed_filter = qdrant_models.Filter(
            must=[
                qdrant_models.FieldCondition(
                    key="type",
                    match=qdrant_models.MatchValue(value="test_case")
                ),
                qdrant_models.FieldCondition(
                    key="status",
                    match=qdrant_models.MatchValue(value="PASSED")
                )
            ]
        )

        if environment:
            passed_filter.must.append(
                qdrant_models.FieldCondition(
                    key="environment",
                    match=qdrant_models.MatchValue(value=environment)
                )
            )

        passed_count = client.count(
            collection_name=collection_name,
            count_filter=passed_filter
        ).count

        # Count failed scenarios
        failed_filter = qdrant_models.Filter(
            must=[
                qdrant_models.FieldCondition(
                    key="type",
                    match=qdrant_models.MatchValue(value="test_case")
                ),
                qdrant_models.FieldCondition(
                    key="status",
                    match=qdrant_models.MatchValue(value="FAILED")
                )
            ]
        )

        if environment:
            failed_filter.must.append(
                qdrant_models.FieldCondition(
                    key="environment",
                    match=qdrant_models.MatchValue(value=environment)
                )
            )

        failed_count = client.count(
            collection_name=collection_name,
            count_filter=failed_filter
        ).count

        # Calculate pass rate
        pass_rate = passed_count / total_count if total_count > 0 else 0

        # Retrieve all test cases for date filtering and tag counting
        all_test_cases = []
        offset = None
        limit = 1000

        # Cutoff date for manual filtering
        cutoff_date = None
        if days > 0:
            cutoff_date = datetime.now() - timedelta(days=days)

        # Retrieve all test cases in batches
        while True:
            test_cases_batch, offset = client.scroll(
                collection_name=collection_name,
                scroll_filter=test_case_filter,
                limit=limit,
                offset=offset,
                with_payload=True,
                with_vectors=False
            )

            # Apply manual date filtering if needed
            if cutoff_date:
                filtered_batch = []
                for tc in test_cases_batch:
                    try:
                        timestamp = tc.payload.get("timestamp", "")
                        if timestamp:
                            tc_date = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                            if tc_date >= cutoff_date:
                                filtered_batch.append(tc)
                        else:
                            filtered_batch.append(tc)  # Include if no timestamp
                    except (ValueError, TypeError):
                        filtered_batch.append(tc)  # Include if parsing fails

                all_test_cases.extend(filtered_batch)
            else:
                all_test_cases.extend(test_cases_batch)

            if offset is None or len(test_cases_batch) < limit:
                # No more results
                break

        # Recalculate counts if date filtering was applied
        if cutoff_date:
            total_count = len(all_test_cases)
            passed_count = sum(1 for tc in all_test_cases if tc.payload.get("status") == "PASSED")
            failed_count = sum(1 for tc in all_test_cases if tc.payload.get("status") == "FAILED")
            pass_rate = passed_count / total_count if total_count > 0 else 0

        # Count unique report IDs and tags
        report_ids = set()
        tag_counts = {}

        for tc in all_test_cases:
            # Add report ID
            if "report_id" in tc.payload:
                report_ids.add(tc.payload["report_id"])

            # Count tags
            tags = tc.payload.get("tags", [])
            for tag in tags:
                tag_counts[tag] = tag_counts.get(tag, 0) + 1

        unique_builds = len(report_ids)

        # Get top 10 tags
        top_tags = dict(sorted(tag_counts.items(), key=lambda item: item[1], reverse=True)[:10])

        # Construct response
        return {
            "status": "success",
            "statistics": {
                "total_scenarios": total_count,
                "passed_scenarios": passed_count,
                "failed_scenarios": failed_count,
                "pass_rate": pass_rate,
                "unique_builds": unique_builds,
                "top_tags": top_tags
            }
        }
    except Exception as e:
        logger.error(f"Error retrieving stats: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve stats: {str(e)}"
        )

# @router.get("/stats-fixed", response_model=Dict[str, Any])
# async def get_stats_fixed(
#         days: int = Query(30, description="Number of days to analyze"),
#         environment: Optional[str] = Query(None, description="Filter by environment"),
#         orchestrator: ServiceOrchestrator = Depends(get_orchestrator_service)
# ):
#     """
#     Get test statistics for the dashboard.
#
#     This is a fixed version of the stats endpoint that works with the
#     data structure in your database.
#     """
#     try:
#         # We'll use direct queries to the vector db instead of semantic search
#         # to avoid any embedding-related issues
#
#         # Get client
#         client = orchestrator.vector_db.client
#         collection_name = orchestrator.vector_db.cucumber_collection
#
#         # Build filters for test cases
#         from qdrant_client.http import models as qdrant_models
#
#         filter_conditions = [
#             qdrant_models.FieldCondition(
#                 key="type",
#                 match=qdrant_models.MatchValue(value="test_case")
#             )
#         ]
#
#         # Add date filter if needed
#         if days > 0:
#             cutoff_date = datetime.now() - timedelta(days=days)
#             cutoff_iso = cutoff_date.isoformat()
#
#             filter_conditions.append(
#                 qdrant_models.FieldCondition(
#                     key="timestamp",
#                     match=qdrant_models.MatchText(text=cutoff_iso),
#                     range=qdrant_models.Range(
#                         gt=None  # We'll handle this later with manual filtering
#                     )
#                 )
#             )
#
#         # Add environment filter if provided
#         if environment:
#             filter_conditions.append(
#                 qdrant_models.FieldCondition(
#                     key="environment",
#                     match=qdrant_models.MatchValue(value=environment)
#                 )
#             )
#
#         # Create filter
#         search_filter = qdrant_models.Filter(
#             must=filter_conditions
#         )
#
#         # Count total scenarios matching our filter
#         total_count = client.count(
#             collection_name=collection_name,
#             count_filter=search_filter
#         ).count
#
#         # Add status filter for passed scenarios
#         passed_filter = qdrant_models.Filter(
#             must=filter_conditions + [
#                 qdrant_models.FieldCondition(
#                     key="status",
#                     match=qdrant_models.MatchValue(value="PASSED")
#                 )
#             ]
#         )
#
#         passed_count = client.count(
#             collection_name=collection_name,
#             count_filter=passed_filter
#         ).count
#
#         # Add status filter for failed scenarios
#         failed_filter = qdrant_models.Filter(
#             must=filter_conditions + [
#                 qdrant_models.FieldCondition(
#                     key="status",
#                     match=qdrant_models.MatchValue(value="FAILED")
#                 )
#             ]
#         )
#
#         failed_count = client.count(
#             collection_name=collection_name,
#             count_filter=failed_filter
#         ).count
#
#         # Calculate pass rate
#         pass_rate = passed_count / total_count if total_count > 0 else 0
#
#         # Count unique builds (reports)
#         # This is more complex - first get all test cases with their report_ids
#         limit = 1000  # Adjust based on expected volume
#         offset = None
#         all_test_cases = []
#
#         # We need to retrieve all test cases in batches
#         while True:
#             test_cases_batch, offset = client.scroll(
#                 collection_name=collection_name,
#                 scroll_filter=search_filter,
#                 limit=limit,
#                 offset=offset,
#                 with_payload=True,
#                 with_vectors=False
#             )
#
#             # Manual date filtering if we have a cutoff date
#             if days > 0:
#                 filtered_batch = []
#                 for tc in test_cases_batch:
#                     try:
#                         tc_date = datetime.fromisoformat(tc.payload.get("timestamp", "").replace("Z", "+00:00"))
#                         if tc_date >= cutoff_date:
#                             filtered_batch.append(tc)
#                     except (ValueError, TypeError):
#                         # If date parsing fails, include the test case
#                         filtered_batch.append(tc)
#
#                 all_test_cases.extend(filtered_batch)
#             else:
#                 all_test_cases.extend(test_cases_batch)
#
#             if offset is None or len(test_cases_batch) < limit:
#                 # No more results or end of results
#                 break
#
#         # Extract unique report_ids
#         report_ids = set()
#         tag_counts = {}
#
#         for tc in all_test_cases:
#             # Count report IDs
#             if "report_id" in tc.payload:
#                 report_ids.add(tc.payload["report_id"])
#
#             # Count tags
#             tags = tc.payload.get("tags", [])
#             for tag in tags:
#                 tag_counts[tag] = tag_counts.get(tag, 0) + 1
#
#         unique_builds = len(report_ids)
#
#         # Recalculate counts based on filtered test cases if manual filtering was applied
#         if days > 0:
#             total_count = len(all_test_cases)
#             passed_count = sum(1 for tc in all_test_cases if tc.payload.get("status") == "PASSED")
#             failed_count = sum(1 for tc in all_test_cases if tc.payload.get("status") == "FAILED")
#             pass_rate = passed_count / total_count if total_count > 0 else 0
#
#         # Get top 10 tags
#         top_tags = dict(sorted(tag_counts.items(), key=lambda item: item[1], reverse=True)[:10])
#
#         # Construct response
#         return {
#             "status": "success",
#             "statistics": {
#                 "total_scenarios": total_count,
#                 "passed_scenarios": passed_count,
#                 "failed_scenarios": failed_count,
#                 "pass_rate": pass_rate,
#                 "unique_builds": unique_builds,
#                 "top_tags": top_tags
#             }
#         }
#     except Exception as e:
#         logger.error(f"Error retrieving stats: {str(e)}")
#         raise HTTPException(
#             status_code=500,
#             detail=f"Failed to retrieve stats: {str(e)}"
#         )


# @router.get("/stats-fixed-simple", response_model=Dict[str, Any])
# async def get_stats_fixed_simple(
#         orchestrator: ServiceOrchestrator = Depends(get_orchestrator_service)
# ):
#     """
#     Get test statistics for the dashboard.
#
#     This is a simplified version that ignores time filtering to test the basic query.
#     """
#     try:
#         # Get client
#         client = orchestrator.vector_db.client
#         collection_name = orchestrator.vector_db.cucumber_collection
#
#         print(f"Using collection: {collection_name}")
#
#         # Build the simplest possible filter for test cases
#         from qdrant_client.http import models as qdrant_models
#
#         test_case_filter = qdrant_models.Filter(
#             must=[
#                 qdrant_models.FieldCondition(
#                     key="type",
#                     match=qdrant_models.MatchValue(value="test_case")
#                 )
#             ]
#         )
#
#         # Count total test cases
#         total_count = client.count(
#             collection_name=collection_name,
#             count_filter=test_case_filter
#         ).count
#
#         print(f"Total test cases found: {total_count}")
#
#         # Add status filter for passed scenarios
#         passed_filter = qdrant_models.Filter(
#             must=[
#                 qdrant_models.FieldCondition(
#                     key="type",
#                     match=qdrant_models.MatchValue(value="test_case")
#                 ),
#                 qdrant_models.FieldCondition(
#                     key="status",
#                     match=qdrant_models.MatchValue(value="PASSED")
#                 )
#             ]
#         )
#
#         passed_count = client.count(
#             collection_name=collection_name,
#             count_filter=passed_filter
#         ).count
#
#         print(f"Passed test cases found: {passed_count}")
#
#         # Add status filter for failed scenarios
#         failed_filter = qdrant_models.Filter(
#             must=[
#                 qdrant_models.FieldCondition(
#                     key="type",
#                     match=qdrant_models.MatchValue(value="test_case")
#                 ),
#                 qdrant_models.FieldCondition(
#                     key="status",
#                     match=qdrant_models.MatchValue(value="FAILED")
#                 )
#             ]
#         )
#
#         failed_count = client.count(
#             collection_name=collection_name,
#             count_filter=failed_filter
#         ).count
#
#         print(f"Failed test cases found: {failed_count}")
#
#         # Calculate pass rate
#         pass_rate = passed_count / total_count if total_count > 0 else 0
#
#         # Get all test cases
#         all_test_cases = []
#         offset = None
#         limit = 1000
#
#         # Retrieve all test cases in batches
#         while True:
#             print(f"Fetching batch with offset: {offset}")
#             test_cases_batch, offset = client.scroll(
#                 collection_name=collection_name,
#                 scroll_filter=test_case_filter,
#                 limit=limit,
#                 offset=offset,
#                 with_payload=True,
#                 with_vectors=False
#             )
#
#             print(f"Fetched {len(test_cases_batch)} test cases")
#             all_test_cases.extend(test_cases_batch)
#
#             if offset is None or len(test_cases_batch) < limit:
#                 # No more results
#                 break
#
#         print(f"Total test cases retrieved: {len(all_test_cases)}")
#
#         # Count unique report IDs and tags
#         report_ids = set()
#         tag_counts = {}
#
#         for tc in all_test_cases:
#             # Add report ID
#             if "report_id" in tc.payload:
#                 report_ids.add(tc.payload["report_id"])
#
#             # Count tags
#             tags = tc.payload.get("tags", [])
#             for tag in tags:
#                 tag_counts[tag] = tag_counts.get(tag, 0) + 1
#
#         unique_builds = len(report_ids)
#         print(f"Unique builds (reports) found: {unique_builds}")
#
#         # Get top 10 tags
#         top_tags = dict(sorted(tag_counts.items(), key=lambda item: item[1], reverse=True)[:10])
#
#         # Construct response
#         return {
#             "status": "success",
#             "collection": collection_name,
#             "statistics": {
#                 "total_scenarios": total_count,
#                 "passed_scenarios": passed_count,
#                 "failed_scenarios": failed_count,
#                 "pass_rate": pass_rate,
#                 "unique_builds": unique_builds,
#                 "top_tags": top_tags
#             }
#         }
#     except Exception as e:
#         logger.error(f"Error retrieving stats: {str(e)}")
#         print(f"Error details: {str(e)}")
#         raise HTTPException(
#             status_code=500,
#             detail=f"Failed to retrieve stats: {str(e)}"
#         )