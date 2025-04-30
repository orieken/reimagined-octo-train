# from fastapi import APIRouter, Depends, HTTPException, Query
# from typing import List, Dict, Any, Optional
# import logging
# from datetime import timedelta
# from collections import defaultdict, Counter
# import re
#
# from app.config import settings
# from app.services.orchestrator import ServiceOrchestrator
# from app.api.dependencies import get_orchestrator_service
# from app.services import datetime_service as dt
# from app.services.failure_analysis_service import FailureAnalysisService
#
# failure_service = FailureAnalysisService()
#
#
# logger = logging.getLogger(__name__)
#
# router = APIRouter(prefix=settings.API_PREFIX, tags=["failures"])
#
#
# @router.get("/failures", response_model=Dict[str, Any])
# async def get_failures(
#     days: int = Query(30, description="Number of days to analyze"),
#     environment: Optional[str] = Query(None, description="Filter by environment"),
#     build_id: Optional[str] = Query(None, description="Filter by build ID"),
#     feature: Optional[str] = Query(None, description="Filter by feature"),
#     limit_recent: int = Query(10, description="Limit for recent failures"),
#     orchestrator: ServiceOrchestrator = Depends(get_orchestrator_service)
# ):
#     try:
#         logger.info(f"Starting failures analysis for past {days} days")
#
#         client = orchestrator.vector_db.client
#         collection_name = orchestrator.vector_db.cucumber_collection
#
#         from qdrant_client.http import models as qdrant_models
#
#         test_case_filter = qdrant_models.Filter(must=[
#             qdrant_models.FieldCondition(key="type", match=qdrant_models.MatchValue(value="test_case"))
#         ])
#
#         if environment:
#             test_case_filter.must.append(
#                 qdrant_models.FieldCondition(key="environment", match=qdrant_models.MatchValue(value=environment))
#             )
#         if build_id:
#             test_case_filter.must.append(
#                 qdrant_models.FieldCondition(key="report_id", match=qdrant_models.MatchValue(value=build_id))
#             )
#         if feature:
#             test_case_filter.must.append(
#                 qdrant_models.FieldCondition(key="feature", match=qdrant_models.MatchValue(value=feature))
#             )
#
#         failed_filter = qdrant_models.Filter(must=[
#             qdrant_models.FieldCondition(key="type", match=qdrant_models.MatchValue(value="test_case")),
#             qdrant_models.FieldCondition(key="status", match=qdrant_models.MatchValue(value="FAILED"))
#         ])
#
#         if environment:
#             failed_filter.must.append(
#                 qdrant_models.FieldCondition(key="environment", match=qdrant_models.MatchValue(value=environment))
#             )
#         if build_id:
#             failed_filter.must.append(
#                 qdrant_models.FieldCondition(key="report_id", match=qdrant_models.MatchValue(value=build_id))
#             )
#         if feature:
#             failed_filter.must.append(
#                 qdrant_models.FieldCondition(key="feature", match=qdrant_models.MatchValue(value=feature))
#             )
#
#         total_count = client.count(collection_name=collection_name, count_filter=test_case_filter).count
#         failed_count = client.count(collection_name=collection_name, count_filter=failed_filter).count
#
#         logger.info(f"Found {failed_count} failures out of {total_count} total test cases")
#
#         # ... error_categories definition remains unchanged
#
#         all_failed_tests = []
#         offset = None
#         limit = 1000
#         cutoff_date = dt.now_utc() - timedelta(days=days) if days > 0 else None
#
#         while True:
#             failed_tests_batch, offset = client.scroll(
#                 collection_name=collection_name,
#                 scroll_filter=failed_filter,
#                 limit=limit,
#                 offset=offset,
#                 with_payload=True,
#                 with_vectors=False
#             )
#
#             if cutoff_date:
#                 filtered_batch = []
#                 for tc in failed_tests_batch:
#                     timestamp = tc.payload.get("timestamp", "")
#                     if timestamp and dt.parse_iso_datetime_to_utc(timestamp) >= cutoff_date:
#                         filtered_batch.append(tc)
#                 all_failed_tests.extend(filtered_batch)
#             else:
#                 all_failed_tests.extend(failed_tests_batch)
#
#             if offset is None or len(failed_tests_batch) < limit:
#                 break
#
#         if cutoff_date:
#             failed_count = len(all_failed_tests)
#             logger.info(f"After date filtering: {failed_count} failures in the last {days} days")
#
#         # ... categorize_error and extract_element functions go here
#
#         # -- Categorization and analysis section remains unchanged --
#
#         all_test_cases = []
#         offset = None
#         while True:
#             test_cases_batch, offset = client.scroll(
#                 collection_name=collection_name,
#                 scroll_filter=test_case_filter,
#                 limit=limit,
#                 offset=offset,
#                 with_payload=True,
#                 with_vectors=False
#             )
#
#             if cutoff_date:
#                 filtered_batch = []
#                 for tc in test_cases_batch:
#                     timestamp = tc.payload.get("timestamp", "")
#                     if timestamp and dt.parse_iso_datetime_to_utc(timestamp) >= cutoff_date:
#                         filtered_batch.append(tc)
#                 all_test_cases.extend(filtered_batch)
#             else:
#                 all_test_cases.extend(test_cases_batch)
#
#             if offset is None or len(test_cases_batch) < limit:
#                 break
#
#         # ... feature counting and failure aggregation logic remains unchanged
#
#         sorted_failures = sorted(
#             all_failed_tests,
#             key=lambda x: dt.parse_iso_datetime_to_utc(x.payload.get("timestamp", "")),
#             reverse=True
#         )
#
#         recent_failures = []
#         for failure in sorted_failures[:limit_recent]:
#             scenario_name = failure.payload.get("name", "Unknown Scenario")
#             error_message = failure.payload.get("error_message")
#             feature = failure.payload.get("feature", "")
#             if not error_message:
#                 category = failure_service.categorize_error(None, scenario_name)
#                 element = failure_service.extract_element(None, category, scenario_name, feature)
#                 if category == "UI Elements Not Found":
#                     error_message = f"Failed to locate or interact with {element}"
#                 elif category == "Timeout Errors":
#                     error_message = f"Timeout waiting for {element} to complete"
#                 elif category == "Assertion Failures":
#                     error_message = f"Verification failed: {element} did not match expected value"
#                 elif category == "API Errors":
#                     error_message = f"API response error while accessing {element}"
#                 elif category == "Form Validation Errors":
#                     error_message = f"Form validation error in {element}"
#                 else:
#                     words = scenario_name.split()
#                     error_message = f"Failed while {' '.join(words[:3]).lower()}..." if len(words) > 3 else f"Failed to complete {scenario_name.lower()}"
#
#             recent_failures.append({
#                 "id": failure.id,
#                 "scenario": scenario_name,
#                 "error": error_message or "Unknown Error",
#                 "date": dt.isoformat_utc(dt.parse_iso_datetime_to_utc(failure.payload.get("timestamp", ""))),
#                 "build": failure.payload.get("report_id", "Unknown Build")
#             })
#
#         return {
#             "status": "success",
#             "failures": {
#                 "total_failures": failed_count,
#                 "categories": categories_list,
#                 "details": details_dict,
#                 "by_feature": by_feature_list,
#                 "recent": recent_failures
#             }
#         }
#
#     except Exception as e:
#         logger.error(f"Error retrieving failures data: {str(e)}", exc_info=True)
#         raise HTTPException(status_code=500, detail=f"Failed to retrieve failures data: {str(e)}")
