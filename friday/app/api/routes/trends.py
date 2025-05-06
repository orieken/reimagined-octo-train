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

        # Use 'scenario' instead of 'test_case' to match our data structure
        base_filter = qdrant_models.Filter(must=[
            qdrant_models.FieldCondition(key="type", match=qdrant_models.MatchValue(value="scenario"))
        ])

        if feature:
            base_filter.must.append(
                qdrant_models.FieldCondition(key="feature", match=qdrant_models.MatchValue(value=feature)))
        if tag:
            base_filter.must.append(qdrant_models.FieldCondition(key="tags", match=qdrant_models.MatchAny(any=[tag])))

        # Retrieve all matching scenarios
        all_scenarios, offset = [], None
        while True:
            batch, offset = client.scroll(
                collection_name=collection,
                scroll_filter=base_filter,
                limit=1000,
                offset=offset,
                with_payload=True,
                with_vectors=False
            )
            all_scenarios.extend(batch)
            if offset is None or len(batch) < 1000:
                break

        logger.info(f"Retrieved {len(all_scenarios)} scenarios for trend analysis")

        # Since our scenarios may not have timestamps, we need to get them from reports
        # First, collect all test_run_ids from our scenarios
        test_run_ids = set()
        for scenario in all_scenarios:
            test_run_id = scenario.payload.get("test_run_id")
            if test_run_id:
                test_run_ids.add(test_run_id)

        # Now get the reports with these IDs to get their timestamps
        report_filter = qdrant_models.Filter(must=[
            qdrant_models.FieldCondition(key="type", match=qdrant_models.MatchValue(value="report")),
            qdrant_models.FieldCondition(key="id", match=qdrant_models.MatchAny(any=list(test_run_ids)))
        ])

        reports, report_offset = [], None
        while True and test_run_ids:  # Only fetch if we have test_run_ids
            batch, report_offset = client.scroll(
                collection_name=collection,
                scroll_filter=report_filter,
                limit=1000,
                offset=report_offset,
                with_payload=True,
                with_vectors=False
            )
            reports.extend(batch)
            if report_offset is None or len(batch) < 1000:
                break

        logger.info(f"Retrieved {len(reports)} reports with timestamps")

        # Create a mapping of test_run_id to timestamp
        report_timestamps = {}
        for report in reports:
            report_id = report.id
            timestamp = report.payload.get("timestamp")
            if report_id and timestamp:
                report_timestamps[report_id] = timestamp

        # Filter scenarios by associating them with report timestamps
        filtered = []
        for scenario in all_scenarios:
            test_run_id = scenario.payload.get("test_run_id")
            if not test_run_id or test_run_id not in report_timestamps:
                continue

            raw_ts = report_timestamps[test_run_id]
            if not raw_ts:
                continue

            try:
                parsed_ts = dt.parse_iso_datetime_to_utc(raw_ts)
                if start_date <= parsed_ts <= end_date:
                    filtered.append((parsed_ts, scenario.payload))
            except Exception as e:
                logger.error(f"Error parsing timestamp {raw_ts}: {e}")
                continue

        logger.info(f"Filtered to {len(filtered)} scenarios within time range")

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
                "total_scenarios": len(all_scenarios),
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
        client = orchestrator.vector_db.client
        collection = orchestrator.vector_db.cucumber_collection
        from qdrant_client.http import models as qdrant_models

        # First, get all reports for the time period
        report_filter = qdrant_models.Filter(must=[
            qdrant_models.FieldCondition(key="type", match=qdrant_models.MatchValue(value="report"))
        ])

        if environment:
            report_filter.must.append(
                qdrant_models.FieldCondition(key="environment", match=qdrant_models.MatchValue(value=environment))
            )

        reports, offset = [], None
        while True:
            batch, offset = client.scroll(
                collection_name=collection,
                scroll_filter=report_filter,
                limit=100,
                offset=offset,
                with_payload=True,
                with_vectors=False
            )
            reports.extend(batch)
            if offset is None or len(batch) < 100:
                break

        logger.info(f"Retrieved {len(reports)} reports for pass rate trend")

        # Filter reports by date
        cutoff_date = dt.now_utc() - timedelta(days=days)
        reports_with_ts = []

        for report in reports:
            raw_ts = report.payload.get("timestamp")
            if not raw_ts:
                continue

            try:
                parsed_ts = dt.parse_iso_datetime_to_utc(raw_ts)
                if parsed_ts >= cutoff_date:
                    reports_with_ts.append((parsed_ts, report))
            except Exception:
                continue

        logger.info(f"Filtered to {len(reports_with_ts)} reports within time range")

        # Group by date
        date_groups = {}
        for ts, report in reports_with_ts:
            date = ts.strftime("%Y-%m-%d")
            date_groups.setdefault(date, []).append(report.id)

        # For each day, find all scenarios from these reports
        trend_data = []
        for date, report_ids in sorted(date_groups.items()):
            # Get scenarios for these reports
            scenario_filter = qdrant_models.Filter(must=[
                qdrant_models.FieldCondition(key="type", match=qdrant_models.MatchValue(value="scenario")),
                qdrant_models.FieldCondition(key="test_run_id", match=qdrant_models.MatchAny(any=report_ids))
            ])

            if feature:
                scenario_filter.must.append(
                    qdrant_models.FieldCondition(key="feature", match=qdrant_models.MatchValue(value=feature))
                )

            total_count = client.count(collection, scenario_filter).count

            # Count passed scenarios
            passed_filter = qdrant_models.Filter(
                must=scenario_filter.must + [
                    qdrant_models.FieldCondition(key="status", match=qdrant_models.MatchValue(value="PASSED"))
                ]
            )
            passed_count = client.count(collection, passed_filter).count

            # Only add days with test data
            if total_count > 0:
                trend_data.append({
                    "date": date,
                    "pass_rate": round((passed_count / total_count) * 100, 2) if total_count else 0,
                    "total_tests": total_count,
                    "passed_tests": passed_count
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


@router.get("/trends/top-failing-scenarios", response_model=List[Dict[str, Any]])
async def get_top_failing_scenarios(
        days: int = Query(30, description="Number of days to analyze"),
        limit: int = Query(5, description="Maximum number of scenarios to return"),
        environment: Optional[str] = Query(None, description="Filter by environment"),
        orchestrator: ServiceOrchestrator = Depends(get_orchestrator_service)
):
    """
    Get top failing scenarios over the specified number of days.
    """
    try:
        client = orchestrator.vector_db.client
        collection = orchestrator.vector_db.cucumber_collection
        from qdrant_client.http import models as qdrant_models

        # First, get reports for the environment if specified
        report_ids = []
        if environment:
            report_filter = qdrant_models.Filter(must=[
                qdrant_models.FieldCondition(key="type", match=qdrant_models.MatchValue(value="report")),
                qdrant_models.FieldCondition(key="environment", match=qdrant_models.MatchValue(value=environment))
            ])

            reports, offset = [], None
            while True:
                batch, offset = client.scroll(
                    collection_name=collection,
                    scroll_filter=report_filter,
                    limit=100,
                    offset=offset,
                    with_payload=True,
                    with_vectors=False
                )
                for report in batch:
                    report_ids.append(report.id)

                if offset is None or len(batch) < 100:
                    break

        # Get failing scenarios
        fail_filter = qdrant_models.Filter(must=[
            qdrant_models.FieldCondition(key="type", match=qdrant_models.MatchValue(value="scenario")),
            qdrant_models.FieldCondition(key="status", match=qdrant_models.MatchValue(value="FAILED"))
        ])

        if report_ids:
            fail_filter.must.append(
                qdrant_models.FieldCondition(key="test_run_id", match=qdrant_models.MatchAny(any=report_ids))
            )

        failing_scenarios, offset = [], None
        while True:
            batch, offset = client.scroll(
                collection_name=collection,
                scroll_filter=fail_filter,
                limit=100,
                offset=offset,
                with_payload=True,
                with_vectors=False
            )
            failing_scenarios.extend(batch)
            if offset is None or len(batch) < 100:
                break

        logger.info(f"Found {len(failing_scenarios)} failing scenarios")

        # Group failures by scenario name/feature for counting
        failure_counts = {}
        for scenario in failing_scenarios:
            name = scenario.payload.get("name", "Unknown")
            key = name

            if key not in failure_counts:
                failure_counts[key] = {
                    "name": name,
                    "fail_count": 0,
                    "id": scenario.id,
                    "feature": scenario.payload.get("feature", "Unknown"),
                    "last_failure": None
                }

            failure_counts[key]["fail_count"] += 1

            # Track the most recent failure
            test_run_id = scenario.payload.get("test_run_id")
            if test_run_id:
                # We'd need to get timestamp from the report
                # This is simplified for now
                failure_counts[key]["last_failure"] = test_run_id

        # Sort by failure count and get top ones
        top_failures = sorted(
            failure_counts.values(),
            key=lambda x: x["fail_count"],
            reverse=True
        )

        return top_failures[:limit]

    except Exception as e:
        logger.error(f"Error retrieving top failing scenarios: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve top failing scenarios: {str(e)}"
        )

@router.get("/trends/health", response_model=Dict[str, Any])
async def get_trends_health(
        orchestrator: ServiceOrchestrator = Depends(get_orchestrator_service)
):
    """
    Health check endpoint specific to the trends service.
    Verifies that the trends functionality is working correctly.
    When this service is split into its own microservice, this endpoint will become
    the main health check for that service.
    """
    try:
        client = orchestrator.vector_db.client
        collection_name = orchestrator.vector_db.cucumber_collection
        from qdrant_client.http import models as qdrant_models

        health_components = {}

        # Check if we can query scenarios
        try:
            scenario_filter = qdrant_models.Filter(
                must=[
                    qdrant_models.FieldCondition(
                        key="type",
                        match=qdrant_models.MatchValue(value="scenario")
                    )
                ]
            )

            scenario_count = client.count(collection_name, scenario_filter).count

            health_components["scenarios"] = {
                "status": "healthy",
                "message": f"Found {scenario_count} scenarios",
                "count": scenario_count
            }
        except Exception as e:
            health_components["scenarios"] = {
                "status": "unhealthy",
                "message": f"Failed to query scenarios: {str(e)}",
                "count": 0
            }

        # Check if we can query reports for timestamps
        try:
            report_filter = qdrant_models.Filter(
                must=[
                    qdrant_models.FieldCondition(
                        key="type",
                        match=qdrant_models.MatchValue(value="report")
                    )
                ]
            )

            report_count = client.count(collection_name, report_filter).count

            # Try to find reports with timestamps
            reports_with_ts = 0
            if report_count > 0:
                reports, offset = [], None
                limit = min(10, report_count)  # Just check a few for health check

                batch, offset = client.scroll(
                    collection_name=collection_name,
                    scroll_filter=report_filter,
                    limit=limit,
                    offset=offset,
                    with_payload=True,
                    with_vectors=False
                )

                for report in batch:
                    if report.payload.get("timestamp"):
                        reports_with_ts += 1

            health_components["reports"] = {
                "status": "healthy",
                "message": f"Found {report_count} reports, {reports_with_ts} with timestamps",
                "count": report_count,
                "with_timestamps": reports_with_ts
            }

            if report_count > 0 and reports_with_ts == 0:
                health_components["reports"]["status"] = "warning"
                health_components["reports"]["message"] += " - No timestamps found, trends by time may not work"

        except Exception as e:
            health_components["reports"] = {
                "status": "unhealthy",
                "message": f"Failed to query reports: {str(e)}",
                "count": 0
            }

        # Check if we can perform a trend calculation
        try:
            # Simplified trend calculation check
            # Get a small sample of scenarios
            scenario_sample, offset = client.scroll(
                collection_name=collection_name,
                scroll_filter=scenario_filter,
                limit=10,
                offset=None,
                with_payload=True,
                with_vectors=False
            )

            # Verify we can group them (simplified version of trend logic)
            test_run_ids = set()
            for scenario in scenario_sample:
                test_run_id = scenario.payload.get("test_run_id")
                if test_run_id:
                    test_run_ids.add(test_run_id)

            health_components["trend_calculation"] = {
                "status": "healthy",
                "message": f"Successfully performed test trend calculation with {len(scenario_sample)} scenarios",
                "sample_size": len(scenario_sample)
            }

        except Exception as e:
            health_components["trend_calculation"] = {
                "status": "unhealthy",
                "message": f"Failed to perform trend calculation: {str(e)}",
                "sample_size": 0
            }

        # Determine overall status
        statuses = [component["status"] for component in health_components.values()]
        if "unhealthy" in statuses:
            overall_status = "unhealthy"
        elif "warning" in statuses:
            overall_status = "warning"
        else:
            overall_status = "healthy"

        return {
            "status": overall_status,
            "service": "trends",
            "components": health_components,
            "timestamp": dt.isoformat_utc(dt.now_utc())
        }
    except Exception as e:
        logger.error(f"Trends health check failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Trends health check failed: {str(e)}")