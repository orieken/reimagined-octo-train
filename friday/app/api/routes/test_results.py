from datetime import timedelta
from typing import List, Dict, Any, Optional
import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Path

from app.config import settings
from app.services import datetime_service as dt
from app.services.orchestrator import ServiceOrchestrator
from app.api.dependencies import get_orchestrator_service

from app.models.database import TestResultsTag
from app.models.responses import (
    TestResultsListResponse, TestResultsResponse, TestCaseListResponse,
    ScenarioResult, StatisticsResponse, StepResult
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix=settings.API_PREFIX, tags=["test-results"])


@router.get("/test-results", response_model=TestResultsListResponse)
async def list_test_results(
        limit: int = Query(10),
        offset: int = Query(0),
        status: Optional[str] = Query(None),
        environment: Optional[str] = Query(None),
        days: int = Query(30),
        tag: Optional[str] = Query(None),
        orchestrator: ServiceOrchestrator = Depends(get_orchestrator_service)
):
    try:
        query_parts = ["test report"]
        if status: query_parts.append(f"status:{status}")
        if environment: query_parts.append(f"environment:{environment}")
        if tag: query_parts.append(f"tag:{tag}")
        query = " ".join(query_parts)

        filters = {"type": "report"}
        if environment: filters["environment"] = environment

        search_results = await orchestrator.semantic_search(query, filters, limit + offset)

        cutoff_date = dt.now_utc() - timedelta(days=days)
        filtered_results = []
        for result in search_results:
            try:
                timestamp = result.payload.get("timestamp", "")
                if timestamp and dt.parse_iso8601_utc(timestamp) >= cutoff_date:
                    filtered_results.append(result)
            except Exception:
                filtered_results.append(result)

        paged_results = filtered_results[offset:offset + limit]
        formatted_results = [{
            "id": result.id,
            "name": payload.get("name", "Unnamed Report"),
            "status": payload.get("status", "UNKNOWN"),
            "timestamp": payload.get("timestamp", ""),
            "environment": payload.get("environment", ""),
            "duration": payload.get("duration", 0),
            "total_tests": payload.get("metadata", {}).get("total_tests", 0),
            "passed_tests": payload.get("metadata", {}).get("total_passed", 0),
            "failed_tests": payload.get("metadata", {}).get("total_failed", 0)
        } for result in paged_results for payload in [result.payload]]

        return TestResultsListResponse(
            results=formatted_results,
            total=len(filtered_results),
            page=(offset // limit) + 1 if limit > 0 else 1,
            page_size=limit
        )
    except Exception as e:
        logger.error(f"Error listing test results: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to list test results: {str(e)}")


@router.get("/test-results/{report_id}", response_model=TestResultsResponse)
async def get_test_result(
        report_id: str,
        include_steps: bool = Query(True),
        orchestrator: ServiceOrchestrator = Depends(get_orchestrator_service)
):
    try:
        query_embedding = await orchestrator.llm.generate_embedding("report details")
        report_results = orchestrator.vector_db.search_reports(query_embedding, settings.DEFAULT_QUERY_LIMIT)
        matching_reports = [r for r in report_results if r.id == report_id]

        if not matching_reports:
            raise HTTPException(status_code=404, detail=f"Test result with ID {report_id} not found")

        report_data = matching_reports[0].payload
        test_cases = orchestrator.vector_db.search_test_cases(query_embedding, report_id, limit=1000)

        feature_map = {}
        for tc in test_cases:
            tc_data = tc.payload
            feature_name = tc_data.get("feature", "Unknown Feature")

            if feature_name not in feature_map:
                feature_map[feature_name] = {
                    "id": str(uuid.uuid4()),
                    "name": feature_name,
                    "description": "",
                    "scenarios": [],
                    "tags": [],
                    "status": "PASSED",
                    "duration": 0
                }

            scenario = {
                "id": tc.id,
                "name": tc_data.get("name", "Unnamed Scenario"),
                "status": tc_data.get("status", "UNKNOWN"),
                "duration": tc_data.get("duration", 0),
                "feature": feature_name,
                "tags": [{"name": tag} for tag in tc_data.get("tags", [])],
                "error_message": tc_data.get("error_message")
            }

            if include_steps:
                steps = orchestrator.vector_db.search_test_steps(query_embedding, tc.id, limit=100)
                scenario["steps"] = [{
                    "id": step.id,
                    "name": step.payload.get("name", "Unnamed Step"),
                    "keyword": step.payload.get("keyword", ""),
                    "status": step.payload.get("status", "UNKNOWN"),
                    "duration": step.payload.get("duration", 0),
                    "error_message": step.payload.get("error_message")
                } for step in steps]
            else:
                scenario["steps"] = []

            feature_map[feature_name]["duration"] += scenario["duration"]
            if scenario["status"] == "FAILED":
                feature_map[feature_name]["status"] = "FAILED"
            feature_map[feature_name]["scenarios"].append(scenario)

        for feature_data in feature_map.values():
            total = len(feature_data["scenarios"])
            passed = sum(1 for s in feature_data["scenarios"] if s["status"] == "PASSED")
            feature_data["pass_rate"] = (passed / total) * 100 if total else 0

        features = list(feature_map.values())
        total_scenarios = sum(len(f["scenarios"]) for f in features)
        passed_scenarios = sum(len([s for s in f["scenarios"] if s["status"] == "PASSED"]) for f in features)
        failed_scenarios = sum(len([s for s in f["scenarios"] if s["status"] == "FAILED"]) for f in features)

        statistics = {
            "total_tests": total_scenarios,
            "passed_tests": passed_scenarios,
            "failed_tests": failed_scenarios,
            "pass_rate": (passed_scenarios / total_scenarios * 100) if total_scenarios > 0 else 0
        }

        return {
            "id": report_id,
            "name": report_data.get("name", "Unnamed Report"),
            "status": report_data.get("status", "UNKNOWN"),
            "timestamp": report_data.get("timestamp", ""),
            "duration": report_data.get("duration", 0),
            "environment": report_data.get("environment", "unknown"),
            "features": features,
            "tags": [{"name": tag} for tag in report_data.get("tags", [])],
            "statistics": statistics
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving test result {report_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve test result: {str(e)}")


@router.get("/test-results/stats", response_model=StatisticsResponse)
async def get_test_statistics(
        days: int = Query(30),
        environment: Optional[str] = Query(None),
        feature: Optional[str] = Query(None),
        orchestrator: ServiceOrchestrator = Depends(get_orchestrator_service)
):
    try:
        query_parts = ["test statistics"]
        if environment: query_parts.append(f"environment:{environment}")
        if feature: query_parts.append(f"feature:{feature}")
        query = " ".join(query_parts)

        query_embedding = await orchestrator.llm.generate_embedding(query)
        filters = {"type": "report"}
        if environment: filters["environment"] = environment

        report_results = await orchestrator.semantic_search(query, filters, limit=100)
        cutoff_date = dt.now_utc() - timedelta(days=days)
        filtered_reports = []

        for result in report_results:
            try:
                timestamp = result.payload.get("timestamp", "")
                if timestamp and dt.parse_iso8601_utc(timestamp) >= cutoff_date:
                    filtered_reports.append(result)
            except Exception:
                filtered_reports.append(result)

        all_test_cases = []
        for report in filtered_reports:
            test_cases = orchestrator.vector_db.search_test_cases(
                query_embedding, report.id, limit=1000)
            if feature:
                test_cases = [tc for tc in test_cases if tc.payload.get("feature") == feature]
            all_test_cases.extend(test_cases)

        total_test_cases = len(all_test_cases)
        status_counts = {}
        for tc in all_test_cases:
            status = tc.payload.get("status", "UNKNOWN")
            status_counts[status] = status_counts.get(status, 0) + 1

        passed_tests = status_counts.get("PASSED", 0)
        pass_rate = (passed_tests / total_test_cases * 100) if total_test_cases else 0

        return StatisticsResponse(
            total_test_cases=total_test_cases,
            status_counts=status_counts,
            pass_rate=pass_rate,
            timestamp=dt.isoformat_utc(dt.now_utc())
        )
    except Exception as e:
        logger.error(f"Error retrieving test statistics: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve test statistics: {str(e)}")

