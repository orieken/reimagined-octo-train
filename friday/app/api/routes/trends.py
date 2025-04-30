# app/api/routes/trends.py
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Dict, Any, Optional, List
import logging
from datetime import datetime, timedelta

from app.config import settings
from app.services.orchestrator import ServiceOrchestrator
from app.api.dependencies import get_orchestrator_service
from app.services import datetime_service as dt

logger = logging.getLogger(__name__)

router = APIRouter(prefix=settings.API_PREFIX, tags=["trends"])

@router.get("/trends", response_model=Dict[str, Any])
async def get_trends(
    time_range: str = Query("week", description="Time range for trend analysis: 'week', 'month', or 'quarter'"),
    feature: Optional[str] = Query(None, description="Filter results by feature"),
    tag: Optional[str] = Query(None, description="Filter results by tag"),
    orchestrator: ServiceOrchestrator = Depends(get_orchestrator_service)
):
    try:
        # Setup time range
        end_date = dt.now_utc()
        start_date = {
            "week": end_date - timedelta(days=7),
            "month": end_date - timedelta(days=30),
            "quarter": end_date - timedelta(days=90)
        }.get(time_range, end_date - timedelta(days=7))

        client = orchestrator.vector_db.client
        collection = orchestrator.vector_db.cucumber_collection

        from qdrant_client.http import models as qdrant_models

        base_filter = qdrant_models.Filter(must=[
            qdrant_models.FieldCondition(key="type", match=qdrant_models.MatchValue(value="test_case"))
        ])
        if feature:
            base_filter.must.append(qdrant_models.FieldCondition(key="feature", match=qdrant_models.MatchValue(value=feature)))
        if tag:
            base_filter.must.append(qdrant_models.FieldCondition(key="tags", match=qdrant_models.MatchAny(any=[tag])))

        # Retrieve all matching test cases
        all_test_cases, offset = [], None
        while True:
            batch, offset = client.scroll(
                collection_name=collection,
                scroll_filter=base_filter,
                limit=1000,
                offset=offset,
                with_payload=True,
                with_vectors=False
            )
            all_test_cases.extend(batch)
            if offset is None or len(batch) < 1000:
                break

        # Filter by date range using parsed timestamps
        filtered = []
        for tc in all_test_cases:
            raw_ts = tc.payload.get("timestamp")
            if not raw_ts:
                continue
            try:
                parsed_ts = dt.parse_iso_datetime_to_utc(raw_ts)
                if start_date <= parsed_ts <= end_date:
                    filtered.append((parsed_ts, tc.payload))
            except Exception:
                continue

        # Aggregate daily
        daily = {}
        for ts, payload in filtered:
            key = ts.strftime("%Y-%m-%d")
            display = ts.strftime("%b %-d")
            entry = daily.setdefault(key, {
                "date": display,
                "total_scenarios": 0,
                "passed_scenarios": 0,
                "failed_scenarios": 0,
                "pass_rate": 0.0
            })
            entry["total_scenarios"] += 1
            status = payload.get("status", "").upper()
            if status == "PASSED":
                entry["passed_scenarios"] += 1
            elif status == "FAILED":
                entry["failed_scenarios"] += 1

        for entry in daily.values():
            total = entry["total_scenarios"]
            passed = entry["passed_scenarios"]
            if total > 0:
                entry["pass_rate"] = round(passed / total, 3)

        daily_trends = sorted(daily.values(), key=lambda x: x["date"])

        return {
            "status": "success",
            "trends": {
                "daily": daily_trends,
                "builds": [],  # Stubbed
                "top_failures": []  # Stubbed
            },
            "debug_info": {
                "total_test_cases": len(all_test_cases),
                "filtered": len(filtered),
                "time_range": time_range,
                "start": dt.isoformat_utc(start_date),
                "end": dt.isoformat_utc(end_date),
                "feature": feature,
                "tag": tag
            }
        }

    except Exception as e:
        logger.error(f"Error retrieving trends: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to retrieve trends: {str(e)}")

@router.get("/trends/pass-rate", response_model=Dict[str, Any])
async def get_pass_rate_trend(
    days: int = Query(30, description="Number of days to analyze"),
    environment: Optional[str] = Query(None, description="Filter by environment"),
    feature: Optional[str] = Query(None, description="Filter by feature"),
    orchestrator: ServiceOrchestrator = Depends(get_orchestrator_service)
):
    """
    Get pass rate trend over time.
    """
    try:
        # Build the embedding query
        query_parts = ["pass rate trend"]
        if environment:
            query_parts.append(f"environment:{environment}")
        if feature:
            query_parts.append(f"feature:{feature}")
        query = " ".join(query_parts)

        query_embedding = await orchestrator.llm.generate_embedding(query)

        filters = {"type": "report"}
        if environment:
            filters["environment"] = environment

        report_results = await orchestrator.semantic_search(
            query=query,
            filters=filters,
            limit=100
        )

        # Group by date
        date_groups = {}
        for report in report_results:
            timestamp = report.payload.get("timestamp")
            if not timestamp:
                continue
            try:
                date = timestamp.split("T")[0]
                date_groups.setdefault(date, []).append(report.payload)
            except Exception:
                continue

        trend_data = []
        for date, reports in sorted(date_groups.items()):
            total_tests = 0
            passed_tests = 0

            for report in reports:
                test_cases = []
                if feature:
                    # Search for test cases in this report
                    test_case_results = orchestrator.vector_db.search_test_cases(
                        query_embedding=query_embedding,
                        report_id=report.get("id"),
                        limit=1000
                    )
                    test_cases = [tc.payload for tc in test_case_results if tc.payload.get("feature") == feature]
                else:
                    # Fallback: use report-level stats
                    total_tests += report.get("total_tests", 0)
                    passed_tests += report.get("passed_tests", 0)

                if test_cases:
                    total_tests += len(test_cases)
                    passed_tests += sum(1 for tc in test_cases if tc.get("status") == "PASSED")

            trend_data.append({
                "date": date,
                "pass_rate": round((passed_tests / total_tests) * 100, 2) if total_tests else 0,
                "total_tests": total_tests,
                "passed_tests": passed_tests
            })

        return {
            "days": days,
            "environment": environment,
            "feature": feature,
            "trend_data": trend_data,
            "timestamp": dt.isoformat_utc(dt.now_utc())
        }

    except Exception as e:
        logger.error(f"Error retrieving pass rate trend: {str(e)}", exc_info=True)
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
    """
    try:
        # 🔍 Build query and filters
        query = "test duration trend"
        if environment:
            query += f" environment:{environment}"
        if feature:
            query += f" feature:{feature}"

        query_embedding = await orchestrator.llm.generate_embedding(query)

        filters = {"type": "report"}
        if environment:
            filters["environment"] = environment

        report_results = await orchestrator.semantic_search(
            query=query,
            filters=filters,
            limit=100
        )

        # ⏱ Group reports by date
        date_groups: Dict[str, List[Dict]] = {}
        for report in report_results:
            ts = report.payload.get("timestamp", "")
            if ts:
                date = ts.split("T")[0]
                date_groups.setdefault(date, []).append(report.payload)

        # 📊 Calculate average duration per day
        trend_data = []
        for date, reports in sorted(date_groups.items()):
            total_duration = 0
            total_test_cases = 0

            for report in reports:
                if feature:
                    test_cases_results = orchestrator.vector_db.search_test_cases(
                        query_embedding=query_embedding,
                        report_id=report.get("id"),
                        limit=1000
                    )
                    test_cases = [tc.payload for tc in test_cases_results if tc.payload.get("feature") == feature]
                    total_duration += sum(tc.get("duration", 0) for tc in test_cases)
                    total_test_cases += len(test_cases)
                else:
                    total_duration += report.get("duration", 0)
                    total_test_cases += report.get("total_tests", 0)

            avg_duration = total_duration / total_test_cases if total_test_cases else 0

            trend_data.append({
                "date": date,
                "avg_duration": round(avg_duration, 2),
                "total_duration": total_duration,
                "total_tests": total_test_cases
            })

        return {
            "days": days,
            "environment": environment,
            "feature": feature,
            "trend_data": trend_data,
            "timestamp": dt.isoformat_utc(dt.now_utc())
        }
    except Exception as e:
        logger.error(f"Error retrieving duration trend: {str(e)}", exc_info=True)
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
    Analyze trends across the specified builds.
    Includes metrics like pass rate, duration, and failure patterns.
    """
    try:
        if not build_numbers:
            raise HTTPException(status_code=400, detail="No build numbers provided")

        result = await orchestrator.analyze_build_trend(build_numbers)
        return {
            "status": "success",
            "analysis": result,
            "timestamp": dt.isoformat_utc(dt.now_utc())
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error analyzing build trend: {str(e)}", exc_info=True)
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
    Get top failing features over the specified number of days.
    """
    try:
        # 🧠 Build semantic query and filters
        query = "failing features"
        if environment:
            query += f" environment:{environment}"

        query_embedding = await orchestrator.llm.generate_embedding(query)

        filters = {"type": "test_case"}
        if environment:
            filters["environment"] = environment

        # 🔍 Fetch relevant test cases
        test_case_results = await orchestrator.semantic_search(
            query=query,
            filters=filters,
            limit=1000
        )

        # 📦 Group by feature and calculate failure metrics
        feature_stats = {}
        for tc in test_case_results:
            payload = tc.payload
            feature = payload.get("feature", "Unknown")
            status = payload.get("status", "").upper()

            if feature not in feature_stats:
                feature_stats[feature] = {
                    "feature": feature,
                    "total_tests": 0,
                    "failed_tests": 0,
                    "passed_tests": 0
                }

            feature_stats[feature]["total_tests"] += 1
            if status == "FAILED":
                feature_stats[feature]["failed_tests"] += 1
            elif status == "PASSED":
                feature_stats[feature]["passed_tests"] += 1

        # 📊 Compute failure rates
        for f in feature_stats.values():
            total = f["total_tests"]
            f["failure_rate"] = round((f["failed_tests"] / total) * 100, 2) if total else 0.0

        # 🔝 Sort and trim
        sorted_features = sorted(
            feature_stats.values(),
            key=lambda f: f["failure_rate"],
            reverse=True
        )

        return sorted_features[:limit]

    except Exception as e:
        logger.error(f"Error retrieving top failing features: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve top failing features: {str(e)}"
        )
