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
        client = orchestrator.vector_db.client
        collection_name = orchestrator.vector_db.cucumber_collection

        from qdrant_client.http import models as qdrant_models

        # Use the same test case filter as in /stats
        test_case_filter = qdrant_models.Filter(
            must=[
                qdrant_models.FieldCondition(
                    key="type",
                    match=qdrant_models.MatchValue(value="test_case")
                )
            ]
        )
        if environment:
            test_case_filter.must.append(
                qdrant_models.FieldCondition(
                    key="environment",
                    match=qdrant_models.MatchValue(value=environment)
                )
            )

        # Initial counts via Qdrant count API
        total_count = client.count(
            collection_name=collection_name,
            count_filter=test_case_filter
        ).count

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

        # Calculate initial pass rate
        pass_rate = passed_count / total_count if total_count > 0 else 0

        # Retrieve test cases with manual date filtering
        all_test_cases = []
        offset = None
        limit = 1000
        cutoff_date = None
        if days > 0:
            cutoff_date = datetime.now() - timedelta(days=days)

        while True:
            test_cases_batch, offset = client.scroll(
                collection_name=collection_name,
                scroll_filter=test_case_filter,
                limit=limit,
                offset=offset,
                with_payload=True,
                with_vectors=False
            )
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
                            filtered_batch.append(tc)
                    except (ValueError, TypeError):
                        filtered_batch.append(tc)
                all_test_cases.extend(filtered_batch)
            else:
                all_test_cases.extend(test_cases_batch)

            if offset is None or len(test_cases_batch) < limit:
                break

        # Recalculate totals when date filtering is applied
        if cutoff_date:
            total_count = len(all_test_cases)
            passed_count = sum(1 for tc in all_test_cases if tc.payload.get("status") == "PASSED")
            failed_count = sum(1 for tc in all_test_cases if tc.payload.get("status") == "FAILED")
            pass_rate = passed_count / total_count if total_count > 0 else 0

        # Aggregate additional statistics: unique builds, skipped tests, top tags, and average duration
        report_ids = set()
        tag_counts = {}
        skipped_count = 0
        total_duration = 0

        for tc in all_test_cases:
            if "report_id" in tc.payload:
                report_ids.add(tc.payload["report_id"])
            tags = tc.payload.get("tags", [])
            for tag in tags:
                tag_counts[tag] = tag_counts.get(tag, 0) + 1

            if tc.payload.get("status") == "SKIPPED":
                skipped_count += 1
            total_duration += tc.payload.get("duration", 0)

        unique_builds = len(report_ids)
        top_tags = dict(sorted(tag_counts.items(), key=lambda item: item[1], reverse=True)[:10])
        avg_duration = total_duration / len(all_test_cases) if all_test_cases else 0

        return {
            "time_period": f"Last {days} days",
            "environment": environment or "All",
            "unique_builds": unique_builds,
            "total_scenarios": total_count,
            "passed_scenarios": passed_count,
            "failed_scenarios": failed_count,
            "skipped_scenarios": skipped_count,
            "pass_rate": pass_rate,
            "average_duration": round(avg_duration, 2),
            "top_tags": top_tags,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error retrieving stats summary: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve stats summary: {str(e)}"
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

