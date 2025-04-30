from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Dict, Any, Optional
import logging
from datetime import timedelta

from app.config import settings
from app.services.orchestrator import ServiceOrchestrator
from app.api.dependencies import get_orchestrator_service
from app.services import datetime_service as dt

logger = logging.getLogger(__name__)
router = APIRouter(prefix=settings.API_PREFIX, tags=["stats"])


@router.get("/stats/summary", response_model=Dict[str, Any])
async def get_stats_summary(
    days: int = Query(30),
    environment: Optional[str] = Query(None),
    orchestrator: ServiceOrchestrator = Depends(get_orchestrator_service)
):
    try:
        client = orchestrator.vector_db.client
        collection_name = orchestrator.vector_db.cucumber_collection
        from qdrant_client.http import models as qdrant_models

        def base_filter(status: Optional[str] = None):
            conditions = [qdrant_models.FieldCondition(key="type", match=qdrant_models.MatchValue(value="test_case"))]
            if status:
                conditions.append(qdrant_models.FieldCondition(key="status", match=qdrant_models.MatchValue(value=status)))
            if environment:
                conditions.append(qdrant_models.FieldCondition(key="environment", match=qdrant_models.MatchValue(value=environment)))
            return qdrant_models.Filter(must=conditions)

        total_count = client.count(collection_name, base_filter()).count
        passed_count = client.count(collection_name, base_filter("PASSED")).count
        failed_count = client.count(collection_name, base_filter("FAILED")).count
        pass_rate = passed_count / total_count if total_count else 0

        all_test_cases, offset, limit = [], None, 1000
        cutoff_date = dt.now_utc() - timedelta(days=days) if days > 0 else None

        while True:
            test_cases_batch, offset = client.scroll(
                collection_name=collection_name,
                scroll_filter=base_filter(),
                limit=limit,
                offset=offset,
                with_payload=True,
                with_vectors=False
            )
            if cutoff_date:
                for tc in test_cases_batch:
                    try:
                        ts = tc.payload.get("timestamp", "")
                        if ts and dt.parse_iso8601_utc(ts) >= cutoff_date:
                            all_test_cases.append(tc)
                    except Exception:
                        all_test_cases.append(tc)
            else:
                all_test_cases.extend(test_cases_batch)

            if offset is None or len(test_cases_batch) < limit:
                break

        if cutoff_date:
            total_count = len(all_test_cases)
            passed_count = sum(1 for tc in all_test_cases if tc.payload.get("status") == "PASSED")
            failed_count = sum(1 for tc in all_test_cases if tc.payload.get("status") == "FAILED")
            pass_rate = passed_count / total_count if total_count else 0

        report_ids = set()
        external_report_ids = set()
        tag_counts = {}
        skipped_count = 0
        total_duration = 0

        for tc in all_test_cases:
            payload = tc.payload
            report_ids.add(payload.get("pg_id"))
            external_report_ids.add(payload.get("report_id"))
            for tag in payload.get("tags", []):
                tag_counts[tag] = tag_counts.get(tag, 0) + 1
            if payload.get("status") == "SKIPPED":
                skipped_count += 1
            total_duration += payload.get("duration", 0)

        top_tags = dict(sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)[:10])
        avg_duration = total_duration / total_count if total_count else 0

        return {
            "time_period": f"Last {days} days",
            "environment": environment or "All",
            "unique_builds": len(report_ids),
            "external_reports": list(external_report_ids),
            "total_scenarios": total_count,
            "passed_scenarios": passed_count,
            "failed_scenarios": failed_count,
            "skipped_scenarios": skipped_count,
            "pass_rate": pass_rate,
            "average_duration": round(avg_duration, 2),
            "top_tags": top_tags,
            "timestamp": dt.isoformat_utc(dt.now_utc())
        }
    except Exception as e:
        logger.error(f"Error retrieving stats summary: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve stats summary: {str(e)}")

@router.get("/stats", response_model=Dict[str, Any])
async def get_stats(
    days: int = Query(30),
    environment: Optional[str] = Query(None),
    orchestrator: ServiceOrchestrator = Depends(get_orchestrator_service)
):
    try:
        client = orchestrator.vector_db.client
        collection_name = orchestrator.vector_db.cucumber_collection
        from qdrant_client.http import models as qdrant_models

        def filter_with_status(status: Optional[str] = None):
            must = [qdrant_models.FieldCondition(key="type", match=qdrant_models.MatchValue(value="test_case"))]
            if status:
                must.append(qdrant_models.FieldCondition(key="status", match=qdrant_models.MatchValue(value=status)))
            if environment:
                must.append(qdrant_models.FieldCondition(key="environment", match=qdrant_models.MatchValue(value=environment)))
            return qdrant_models.Filter(must=must)

        total_count = client.count(collection_name, filter_with_status()).count
        passed_count = client.count(collection_name, filter_with_status("PASSED")).count
        failed_count = client.count(collection_name, filter_with_status("FAILED")).count
        pass_rate = passed_count / total_count if total_count else 0

        all_test_cases, offset, limit = [], None, 1000
        cutoff_date = dt.now_utc() - timedelta(days=days) if days > 0 else None

        while True:
            test_cases_batch, offset = client.scroll(
                collection_name=collection_name,
                scroll_filter=filter_with_status(),
                limit=limit,
                offset=offset,
                with_payload=True,
                with_vectors=False
            )
            if cutoff_date:
                for tc in test_cases_batch:
                    try:
                        ts = tc.payload.get("timestamp", "")
                        if ts and dt.parse_iso8601_utc(ts) >= cutoff_date:
                            all_test_cases.append(tc)
                    except Exception:
                        all_test_cases.append(tc)
            else:
                all_test_cases.extend(test_cases_batch)

            if offset is None or len(test_cases_batch) < limit:
                break

        if cutoff_date:
            total_count = len(all_test_cases)
            passed_count = sum(1 for tc in all_test_cases if tc.payload.get("status") == "PASSED")
            failed_count = sum(1 for tc in all_test_cases if tc.payload.get("status") == "FAILED")
            pass_rate = passed_count / total_count if total_count else 0

        report_ids = set()
        external_report_ids = set()
        tag_counts = {}
        for tc in all_test_cases:
            report_ids.add(tc.payload.get("pg_id"))
            external_report_ids.add(tc.payload.get("report_id"))
            for tag in tc.payload.get("tags", []):
                tag_counts[tag] = tag_counts.get(tag, 0) + 1

        top_tags = dict(sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)[:10])

        return {
            "status": "success",
            "statistics": {
                "total_scenarios": total_count,
                "passed_scenarios": passed_count,
                "failed_scenarios": failed_count,
                "pass_rate": pass_rate,
                "unique_builds": len(report_ids),
                "external_reports": list(external_report_ids),
                "top_tags": top_tags
            }
        }
    except Exception as e:
        logger.error(f"Error retrieving stats: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve stats: {str(e)}")
