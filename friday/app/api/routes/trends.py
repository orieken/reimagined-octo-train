# app/api/routes/trends.py
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Dict, Any, Optional, List
import logging
from datetime import datetime, timedelta

from app.config import settings
from app.services.orchestrator import ServiceOrchestrator
from app.api.dependencies import get_orchestrator_service
from app.services import datetime_service as dt
from qdrant_client.http import models as qdrant_models
from app.models.database import Scenario as DBScenario, Feature as DBFeature, ScenarioTag as DBScenarioTag, TestRun as DBTestRun, BuildInfo as DBBuildInfo
from sqlalchemy import select, between, UUID, and_

logger = logging.getLogger(__name__)

router = APIRouter(prefix=settings.API_PREFIX, tags=["trends"])


@router.get("/trends", response_model=Dict[str, Any])
async def get_trends(
        time_range: str = Query("week", description="Time range for trend analysis: 'week', 'month', or 'quarter'"),
        feature: Optional[str] = Query(None, description="Filter results by feature"),
        tag: Optional[str] = Query(None, description="Filter results by tag"),
        query: Optional[str] = Query(None, description="Semantic search query"),
        orchestrator: ServiceOrchestrator = Depends(get_orchestrator_service)
):
    try:
        # Set time range
        end_date = dt.now_utc()
        start_date = {
            "week": end_date - timedelta(days=7),
            "month": end_date - timedelta(days=30),
            "quarter": end_date - timedelta(days=90)
        }.get(time_range, end_date - timedelta(days=7))

        # STEP 1: Get test runs within the time range from PostgreSQL
        async with orchestrator.pg_service.session() as session:
            # Query test runs within the date range
            test_runs_query = select(DBTestRun).where(
                between(DBTestRun.created_at, start_date, end_date)
            )
            result = await session.execute(test_runs_query)
            test_runs = result.scalars().all()

            if not test_runs:
                logger.info(f"No test runs found in time range {time_range}")
                return {
                    "status": "success",
                    "trends": {"daily": [], "builds": [], "top_failures": []},
                    "debug_info": {
                        "total_scenarios": 0,
                        "filtered": 0,
                        "time_range": time_range,
                        "start": dt.isoformat_utc(start_date),
                        "end": dt.isoformat_utc(end_date),
                        "feature": feature,
                        "tag": tag,
                        "query": query
                    }
                }

            test_run_ids = [str(tr.id) for tr in test_runs]
            logger.info(f"Found {len(test_run_ids)} test runs in time range")

            # STEP 2A: If semantic query is provided, use vector DB to get relevant scenarios
            scenario_ids = []
            if query:
                try:
                    # Generate embedding for the query
                    query_embedding = await orchestrator.llm.embed_text(query)

                    client = orchestrator.vector_db.client
                    collection = orchestrator.vector_db.cucumber_collection

                    from qdrant_client.http import models as qdrant_models

                    # Create filter for scenarios from our test runs
                    vector_db_filter = qdrant_models.Filter(
                        must=[
                            qdrant_models.FieldCondition(
                                key="type",
                                match=qdrant_models.MatchValue(value="scenario")
                            ),
                            qdrant_models.FieldCondition(
                                key="test_run_id",
                                match=qdrant_models.MatchAny(any=test_run_ids)
                            )
                        ]
                    )

                    # Search for similar scenarios
                    search_results = client.search(
                        collection_name=collection,
                        query_vector=query_embedding,
                        query_filter=vector_db_filter,
                        limit=100
                    )

                    # Extract scenario IDs from search results
                    for result in search_results:
                        if 'id' in result.payload:
                            scenario_ids.append(result.payload['id'])

                    logger.info(f"Vector search found {len(scenario_ids)} relevant scenarios")

                    # If no results from vector search, return empty
                    if not scenario_ids:
                        return {
                            "status": "success",
                            "trends": {"daily": [], "builds": [], "top_failures": []},
                            "debug_info": {
                                "total_scenarios": 0,
                                "filtered": 0,
                                "time_range": time_range,
                                "start": dt.isoformat_utc(start_date),
                                "end": dt.isoformat_utc(end_date),
                                "feature": feature,
                                "tag": tag,
                                "query": query
                            }
                        }

                except Exception as e:
                    logger.error(f"Vector search error: {str(e)}")
                    # Fall back to regular filtering if vector search fails
                    scenario_ids = []

            # STEP 2B: Get scenarios based on filters
            if scenario_ids:
                # Use scenario IDs from vector search
                scenarios_query = select(DBScenario).where(
                    DBScenario.id.in_([UUID(id) for id in scenario_ids if id])
                )
            else:
                # No semantic query, use regular filtering
                scenarios_query = select(DBScenario).where(
                    DBScenario.test_run_id.in_([tr.id for tr in test_runs])
                )

            # Add feature filter if specified
            if feature:
                scenarios_query = scenarios_query.join(
                    DBFeature,
                    DBScenario.feature_id == DBFeature.id
                ).where(DBFeature.name == feature)

            # Execute query to get matching scenarios
            result = await session.execute(scenarios_query)
            scenarios = result.scalars().all()

            if not scenarios:
                logger.info(f"No scenarios found matching criteria")
                return {
                    "status": "success",
                    "trends": {"daily": [], "builds": [], "top_failures": []},
                    "debug_info": {
                        "total_scenarios": 0,
                        "filtered": 0,
                        "time_range": time_range,
                        "start": dt.isoformat_utc(start_date),
                        "end": dt.isoformat_utc(end_date),
                        "feature": feature,
                        "tag": tag,
                        "query": query
                    }
                }

            # Get scenario IDs for further filtering
            db_scenario_ids = [s.id for s in scenarios]
            scenario_count = len(db_scenario_ids)
            logger.info(f"Found {scenario_count} scenarios before tag filtering")

            # STEP 3: Apply tag filter if specified
            if tag:
                tag_query = select(DBScenarioTag.scenario_id).where(
                    and_(
                        DBScenarioTag.scenario_id.in_(db_scenario_ids),
                        DBScenarioTag.tag == tag
                    )
                )
                result = await session.execute(tag_query)
                tagged_scenario_ids = [id[0] for id in result.all()]

                # Filter scenarios to only those with the tag
                scenarios = [s for s in scenarios if s.id in tagged_scenario_ids]
                logger.info(f"Filtered to {len(scenarios)} scenarios after tag filter")

            # STEP 4: Get feature info for each scenario
            feature_ids = [s.feature_id for s in scenarios if s.feature_id]
            feature_info = {}

            if feature_ids:
                feature_query = select(DBFeature).where(
                    DBFeature.id.in_(feature_ids)
                )
                result = await session.execute(feature_query)
                features = result.scalars().all()

                for f in features:
                    feature_info[str(f.id)] = f.name

            # STEP 5: Group scenarios by day for trend analysis
            scenario_data = []

            # Get test run timestamps to associate with scenarios
            test_run_dates = {str(tr.id): tr.created_at for tr in test_runs}

            for scenario in scenarios:
                test_run_id = str(scenario.test_run_id)

                if test_run_id in test_run_dates:
                    timestamp = test_run_dates[test_run_id]
                    feature_name = feature_info.get(str(scenario.feature_id), "Unknown")

                    scenario_data.append({
                        "id": str(scenario.id),
                        "name": scenario.name,
                        "status": str(scenario.status),
                        "timestamp": timestamp,
                        "feature": feature_name,
                        "test_run_id": test_run_id
                    })

            # Rest of the implementation remains the same...

            # STEP 6: Generate daily trend data
            daily = {}
            for scenario in scenario_data:
                ts = scenario["timestamp"]
                date_key = ts.strftime("%Y-%m-%d")
                display = ts.strftime("%b %-d")

                entry = daily.setdefault(date_key, {
                    "date": display,
                    "total_scenarios": 0,
                    "passed_scenarios": 0,
                    "failed_scenarios": 0,
                    "pass_rate": 0.0
                })

                entry["total_scenarios"] += 1

                status = scenario["status"]
                if "PASSED" in status:
                    entry["passed_scenarios"] += 1
                elif "FAILED" in status:
                    entry["failed_scenarios"] += 1

            # Calculate pass rates
            for entry in daily.values():
                total = entry["total_scenarios"]
                passed = entry["passed_scenarios"]
                if total > 0:
                    entry["pass_rate"] = round(passed / total, 3)

            daily_trends = sorted(daily.values(), key=lambda x: x["date"])

            # STEP 7: Generate failure data
            failure_counts = {}
            for scenario in scenario_data:
                if "FAILED" not in scenario["status"]:
                    continue

                name = scenario["name"]
                feature = scenario["feature"]
                key = f"{feature}|{name}"

                if key not in failure_counts:
                    failure_counts[key] = {
                        "name": name,
                        "feature": feature,
                        "fail_count": 0,
                        "id": scenario["id"],
                        "last_failure": None
                    }

                failure_counts[key]["fail_count"] += 1

                # Track the most recent failure
                if not failure_counts[key]["last_failure"] or scenario["timestamp"] > failure_counts[key][
                    "last_failure"]:
                    failure_counts[key]["last_failure"] = scenario["timestamp"]

            # Sort and get top failures
            top_failures = sorted(
                failure_counts.values(),
                key=lambda x: x["fail_count"],
                reverse=True
            )[:5]  # Top 5 failures

            # Format timestamps
            for failure in top_failures:
                if failure["last_failure"]:
                    failure["last_failure"] = dt.isoformat_utc(failure["last_failure"])

            return {
                "status": "success",
                "trends": {
                    "daily": daily_trends,
                    "builds": [],  # You can implement this separately
                    "top_failures": top_failures
                },
                "debug_info": {
                    "total_scenarios": scenario_count,
                    "filtered": len(scenarios),
                    "time_range": time_range,
                    "start": dt.isoformat_utc(start_date),
                    "end": dt.isoformat_utc(end_date),
                    "feature": feature,
                    "tag": tag,
                    "query": query
                }
            }

    except Exception as e:
        logger.error(f"Error retrieving trends: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to retrieve trends: {str(e)}")


@router.post("/search", response_model=Dict[str, Any])
async def semantic_search(
        query: str,
        filters: Optional[Dict[str, Any]] = None,
        orchestrator: ServiceOrchestrator = Depends(get_orchestrator_service)
):
    """
    Perform a semantic search against your test data and return comprehensive information.
    This endpoint supports RAG use cases where you want to query and analyze test data
    using natural language.
    """
    try:
        # Generate embedding for the query
        query_embedding = await orchestrator.llm.embed_text(query)

        # Set up vector DB search
        client = orchestrator.vector_db.client
        collection = orchestrator.vector_db.cucumber_collection
        from qdrant_client.http import models as qdrant_models

        # Build filter based on provided filters
        vector_filter = qdrant_models.Filter(must=[])

        if filters:
            # Add type filter if specified
            if "type" in filters:
                vector_filter.must.append(
                    qdrant_models.FieldCondition(
                        key="type",
                        match=qdrant_models.MatchValue(value=filters["type"])
                    )
                )

            # Add date range if specified
            if "start_date" in filters and "end_date" in filters:
                # Implementation depends on how dates are stored in vector DB
                pass

            # Other filters as needed

        # Perform vector search
        search_results = client.search(
            collection_name=collection,
            query_vector=query_embedding,
            query_filter=vector_filter,
            limit=20
        )

        # Collect relevant IDs
        scenario_ids = []
        test_run_ids = []
        for result in search_results:
            payload = result.payload
            result_type = payload.get("type")

            if result_type == "scenario":
                scenario_ids.append(payload.get("id"))
            elif result_type == "report":
                test_run_ids.append(payload.get("id"))

        # Get detailed information from PostgreSQL
        async with orchestrator.pg_service.session() as session:
            from app.models.database import (
                TestRun as DBTestRun,
                Scenario as DBScenario,
                Feature as DBFeature,
                ScenarioTag as DBScenarioTag,
                Step as DBStep
            )
            from sqlalchemy import select

            # Get scenarios
            scenarios_data = []
            if scenario_ids:
                scenario_query = select(DBScenario).where(
                    DBScenario.id.in_([UUID(id) for id in scenario_ids if id])
                )
                result = await session.execute(scenario_query)
                scenarios = result.scalars().all()

                # Get related features
                feature_ids = [s.feature_id for s in scenarios if s.feature_id]
                feature_map = {}

                if feature_ids:
                    features_query = select(DBFeature).where(
                        DBFeature.id.in_(feature_ids)
                    )
                    result = await session.execute(features_query)
                    features = result.scalars().all()

                    for f in features:
                        feature_map[f.id] = {
                            "id": str(f.id),
                            "name": f.name,
                            "description": f.description,
                            "tags": f.tags
                        }

                # Get tags for scenarios
                scenario_tag_map = {}
                if scenarios:
                    scenario_ids_for_tags = [s.id for s in scenarios]
                    tags_query = select(DBScenarioTag).where(
                        DBScenarioTag.scenario_id.in_(scenario_ids_for_tags)
                    )
                    result = await session.execute(tags_query)
                    tags = result.scalars().all()

                    for tag in tags:
                        if tag.scenario_id not in scenario_tag_map:
                            scenario_tag_map[tag.scenario_id] = []
                        scenario_tag_map[tag.scenario_id].append(tag.tag)

                # Get steps for scenarios
                steps_query = select(DBStep).where(
                    DBStep.scenario_id.in_([s.id for s in scenarios])
                )
                result = await session.execute(steps_query)
                steps = result.scalars().all()

                # Group steps by scenario_id
                steps_by_scenario = {}
                for step in steps:
                    if step.scenario_id not in steps_by_scenario:
                        steps_by_scenario[step.scenario_id] = []
                    steps_by_scenario[step.scenario_id].append({
                        "id": str(step.id),
                        "name": step.name,
                        "keyword": step.keyword,
                        "status": str(step.status),
                        "duration": step.duration,
                        "error_message": step.error_message
                    })

                # Build comprehensive scenario data
                for scenario in scenarios:
                    scenario_data = {
                        "id": str(scenario.id),
                        "name": scenario.name,
                        "description": scenario.description,
                        "status": str(scenario.status),
                        "duration": scenario.duration,
                        "feature": feature_map.get(scenario.feature_id, {"name": "Unknown"}),
                        "tags": scenario_tag_map.get(scenario.id, []),
                        "steps": steps_by_scenario.get(scenario.id, []),
                        "test_run_id": str(scenario.test_run_id) if scenario.test_run_id else None
                    }
                    scenarios_data.append(scenario_data)

            # Get test runs
            test_runs_data = []
            if test_run_ids:
                test_run_query = select(DBTestRun).where(
                    DBTestRun.id.in_([UUID(id) for id in test_run_ids if id])
                )
                result = await session.execute(test_run_query)
                test_runs = result.scalars().all()

                for test_run in test_runs:
                    test_run_data = {
                        "id": str(test_run.id),
                        "name": test_run.name,
                        "status": str(test_run.status),
                        "environment": test_run.environment,
                        "branch": test_run.branch,
                        "commit_hash": test_run.commit_hash,
                        "created_at": dt.isoformat_utc(test_run.created_at),
                        "total_tests": test_run.total_tests,
                        "passed_tests": test_run.passed_tests,
                        "failed_tests": test_run.failed_tests,
                        "skipped_tests": test_run.skipped_tests,
                        "success_rate": test_run.success_rate
                    }
                    test_runs_data.append(test_run_data)

        # Return comprehensive results
        return {
            "status": "success",
            "query": query,
            "results": {
                "scenarios": scenarios_data,
                "test_runs": test_runs_data
            },
            "meta": {
                "total_results": len(scenarios_data) + len(test_runs_data),
                "filters_applied": filters
            }
        }

    except Exception as e:
        logger.error(f"Error performing semantic search: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")



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