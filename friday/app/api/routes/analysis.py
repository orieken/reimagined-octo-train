# # app/api/routes/analysis.py
# from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query, Path
# from typing import List, Dict, Any, Optional
# import logging
# from datetime import datetime, timezone
# import uuid
#
# from app.config import settings
# from app.services.orchestrator import ServiceOrchestrator
# from app.api.dependencies import get_orchestrator_service
#
#
# from app.models import ReportResponse, Report, SearchResponse, SearchQuery, AnalysisRequest
# from app.models.responses import AnalysisResponse, ReportSummaryResponse, TestCaseInsightsResponse
#
# logger = logging.getLogger(__name__)
#
# router = APIRouter(prefix=settings.API_PREFIX, tags=["analysis"])

#
# # Helper function to get timezone-aware UTC datetime
# def utcnow():
#     """Return current UTC datetime with timezone information."""
#     return datetime.now(timezone.utc)
#
#
# # Helper function to get ISO formatted string with timezone info
# def utcnow_iso():
#     """Return current UTC datetime as ISO 8601 string with timezone information."""
#     return datetime.now(timezone.utc).isoformat()
#
#
# @router.post("/reports", response_model=ReportResponse)
# async def upload_report(
#         report: Report,
#         background_tasks: BackgroundTasks,
#         process_async: bool = Query(True, description="Process the report asynchronously"),
#         orchestrator: ServiceOrchestrator = Depends(get_orchestrator_service)
# ):
#     """
#     Upload and process a test report.
#
#     This endpoint accepts a full test report with test cases and steps,
#     generates embeddings, and stores it in the vector database.
#     """
#     try:
#         logger.info(f"Received report upload: {report.name}")
#
#         # Process the report in the background or synchronously
#         if process_async:
#             background_tasks.add_task(orchestrator.process_report, report)
#             return ReportResponse(
#                 status="accepted",
#                 message="Report processing started",
#                 report_id=report.id,
#                 timestamp=utcnow_iso()  # Use timezone-aware UTC ISO string
#             )
#         else:
#             report_id = await orchestrator.process_report(report)
#             return ReportResponse(
#                 status="success",
#                 message="Report processed successfully",
#                 report_id=report_id,
#                 timestamp=utcnow_iso()  # Use timezone-aware UTC ISO string
#             )
#     except Exception as e:
#         logger.error(f"Error processing report: {str(e)}")
#         raise HTTPException(
#             status_code=500,
#             detail=f"Failed to process report: {str(e)}"
#         )
#
#
# @router.post("/search", response_model=SearchResponse)
# async def semantic_search(
#         query: SearchQuery,
#         orchestrator: ServiceOrchestrator = Depends(get_orchestrator_service)
# ):
#     """
#     Search for test artifacts using semantic search.
#
#     This endpoint performs a semantic search across test artifacts
#     based on the provided query and filters.
#     """
#     try:
#         logger.info(f"Search request: {query.query}")
#         search_results = await orchestrator.semantic_search(
#             query=query.query,
#             filters=query.filters,
#             limit=query.limit
#         )
#
#         return SearchResponse(
#             query=query.query,
#             results=[{
#                 "id": result.id,
#                 "score": result.score,
#                 "content": result.payload
#             } for result in search_results],
#             total_hits=len(search_results),
#             execution_time_ms=0  # Placeholder, actual time is measured by orchestrator
#         )
#     except Exception as e:
#         logger.error(f"Search error: {str(e)}")
#         raise HTTPException(
#             status_code=500,
#             detail=f"Search failed: {str(e)}"
#         )
#
#
# @router.post("/analyze", response_model=AnalysisResponse)
# async def analyze(
#         request: AnalysisRequest,
#         orchestrator: ServiceOrchestrator = Depends(get_orchestrator_service)
# ):
#     """
#     Analyze test reports or test cases.
#
#     This endpoint provides analysis, insights, and recommendations
#     for test reports or specific test cases.
#     """
#     try:
#         logger.info(f"Analysis request: {request.query}")
#         result = await orchestrator.analyze(request)
#
#         # Ensure result timestamp is timezone-aware
#         if hasattr(result, 'timestamp') and isinstance(result.timestamp, datetime):
#             timestamp_iso = result.timestamp.isoformat()
#         else:
#             # If timestamp is not a datetime object, use current UTC time
#             timestamp_iso = utcnow_iso()
#
#         return AnalysisResponse(
#             query=result.query,
#             timestamp=timestamp_iso,
#             recommendations=result.recommendations,
#             related_items=result.related_items,
#             summary=result.summary
#         )
#     except Exception as e:
#         logger.error(f"Analysis error: {str(e)}")
#         raise HTTPException(
#             status_code=500,
#             detail=f"Analysis failed: {str(e)}"
#         )
#
#
# @router.get("/reports/{report_id}/summary", response_model=ReportSummaryResponse)
# async def get_report_summary(
#         report_id: str = Path(..., description="ID of the report to summarize"),
#         orchestrator: ServiceOrchestrator = Depends(get_orchestrator_service)
# ):
#     """
#     Get a human-readable summary of a test report.
#
#     This endpoint generates a concise summary of a test report
#     highlighting key metrics and insights.
#     """
#     try:
#         logger.info(f"Summary request for report: {report_id}")
#         summary = await orchestrator.generate_report_summary(report_id)
#
#         return ReportSummaryResponse(
#             report_id=report_id,
#             summary=summary,
#             timestamp=utcnow_iso()  # Use timezone-aware UTC ISO string
#         )
#     except Exception as e:
#         logger.error(f"Summary generation error: {str(e)}")
#         raise HTTPException(
#             status_code=500,
#             detail=f"Failed to generate summary: {str(e)}"
#         )
#
#
# @router.get("/test-cases/{test_case_id}/insights", response_model=TestCaseInsightsResponse)
# async def get_test_failure_insights(
#         test_case_id: str = Path(..., description="ID of the test case to analyze"),
#         orchestrator: ServiceOrchestrator = Depends(get_orchestrator_service)
# ):
#     """
#     Get insights for a test failure.
#
#     This endpoint analyzes a specific test failure and provides
#     root cause analysis and recommendations.
#     """
#     try:
#         logger.info(f"Insights request for test case: {test_case_id}")
#         insights = await orchestrator.get_test_failure_insights(test_case_id)
#
#         # Check if there was an error
#         if "error" in insights:
#             return TestCaseInsightsResponse(
#                 test_case_id=test_case_id,
#                 error=insights["error"],
#                 recommendations=insights.get("recommendations", []),
#                 timestamp=utcnow_iso()  # Use timezone-aware UTC ISO string
#             )
#
#         # Use provided timestamp if it exists, or current UTC time
#         timestamp = insights.get("timestamp", utcnow_iso())
#
#         return TestCaseInsightsResponse(
#             test_case_id=test_case_id,
#             test_case=insights.get("test_case"),
#             analysis=insights.get("analysis"),
#             timestamp=timestamp
#         )
#     except Exception as e:
#         logger.error(f"Insights generation error: {str(e)}")
#         raise HTTPException(
#             status_code=500,
#             detail=f"Failed to generate insights: {str(e)}"
#         )
#
#
# @router.post("/answer", response_model=Dict[str, Any])
# async def generate_answer(
#         query: str,
#         context: Optional[List[Dict[str, Any]]] = None,
#         max_tokens: int = Query(800, description="Maximum tokens to generate"),
#         orchestrator: ServiceOrchestrator = Depends(get_orchestrator_service)
# ):
#     """
#     Generate an answer to a natural language query.
#
#     This endpoint uses the LLM to generate an answer based on the provided
#     context or searches for relevant context automatically.
#     """
#     try:
#         logger.info(f"Answer request: {query}")
#         answer = await orchestrator.generate_answer(
#             query=query,
#             context=context,
#             max_tokens=max_tokens
#         )
#
#         return {
#             "query": query,
#             "answer": answer,
#             "timestamp": utcnow_iso()  # Use timezone-aware UTC ISO string
#         }
#     except Exception as e:
#         logger.error(f"Answer generation error: {str(e)}")
#         raise HTTPException(
#             status_code=500,
#             detail=f"Failed to generate answer: {str(e)}"
#         )
#
#
# @router.get("/health", response_model=Dict[str, Any])
# async def health_check(
#         orchestrator: ServiceOrchestrator = Depends(get_orchestrator_service)
# ):
#     """
#     Health check endpoint for the analysis service.
#
#     This endpoint checks the health of the vector database and LLM services.
#     """
#     health_status = {
#         "status": "ok",
#         "services": {
#             "vector_db": "unknown",
#             "llm": "unknown"
#         },
#         "timestamp": utcnow_iso()  # Use timezone-aware UTC ISO string
#     }
#
#     # Check Vector DB
#     try:
#         # Simple check to see if we can access collections
#         orchestrator.vector_db.client.get_collections()
#         health_status["services"]["vector_db"] = "ok"
#     except Exception as e:
#         health_status["services"]["vector_db"] = f"error: {str(e)}"
#         health_status["status"] = "degraded"
#
#     # Check LLM Service
#     try:
#         # Generate a simple embedding to test connection
#         test_text = "health check"
#         test_embedding = await orchestrator.llm.generate_embedding(test_text)
#
#         if test_embedding and len(test_embedding) > 0:
#             health_status["services"]["llm"] = "ok"
#         else:
#             health_status["services"]["llm"] = "error: empty embedding returned"
#             health_status["status"] = "degraded"
#     except Exception as e:
#         health_status["services"]["llm"] = f"error: {str(e)}"
#         health_status["status"] = "degraded"
#
#     return health_status