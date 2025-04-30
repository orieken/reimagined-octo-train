# app/routes/api/results.py
from typing import List, Dict, Any, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, Query, HTTPException, BackgroundTasks
from sqlalchemy import func, and_, or_, distinct, text, literal, Integer, case
from sqlalchemy.orm import Session, aliased
import logging
from datetime import timedelta, datetime

from app.database.session import get_db
from app.config import settings
from app.services.orchestrator import ServiceOrchestrator
from app.api.dependencies import get_orchestrator_service
from app.services import datetime_service as dt

from app.models import TestStatus
from app.models.schemas import Scenario, TestRun, Feature, ResultsResponse, ScenarioTag
from app.models.database import Scenario as DBScenario
from app.models.database import TestRun as DBTestRun
from app.models.database import Feature as DBFeature
from app.models.database import ScenarioTag as DBScenarioTag

logger = logging.getLogger("friday.results")
router = APIRouter(prefix=settings.API_PREFIX)


@router.get("/results", response_model=ResultsResponse)
async def get_test_results(
    build_id: Optional[int] = Query(None),
    test_run_id: Optional[int] = Query(None),
    feature_name: Optional[str] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    limit_days: Optional[int] = Query(30),
    tag: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    project_id: Optional[int] = Query(None),
    environment: Optional[str] = Query(None),
    use_vector_db: Optional[bool] = Query(True),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: Session = Depends(get_db),
    orchestrator: ServiceOrchestrator = Depends(get_orchestrator_service)
):
    try:
        parsed_start = dt.parse_iso8601_utc(start_date) if start_date else None
        parsed_end = dt.parse_iso8601_utc(end_date) if end_date else None
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid date format: {e}")

    if use_vector_db:
        try:
            return await get_results_from_qdrant(
                orchestrator,
                build_id,
                test_run_id,
                feature_name,
                parsed_start,
                parsed_end,
                limit_days,
                tag,
                status,
                project_id,
                environment,
                background_tasks
            )
        except Exception as e:
            logger.error(f"Error retrieving results from Qdrant: {str(e)}", exc_info=True)
            logger.info("Falling back to SQL database for results")

    try:
        return await get_results_from_sql(
            db,
            build_id,
            test_run_id,
            feature_name,
            parsed_start,
            parsed_end,
            limit_days,
            tag,
            status,
            project_id,
            environment,
            background_tasks
        )
    except Exception as e:
        logger.error(f"Error retrieving test results from SQL database: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to retrieve test results: {str(e)}")


async def get_results_from_qdrant(
    orchestrator: ServiceOrchestrator,
    build_id: Optional[UUID],
    test_run_id: Optional[UUID],
    feature_name: Optional[str],
    start_date: Optional[datetime],
    end_date: Optional[datetime],
    limit_days: Optional[int],
    tag: Optional[str],
    status: Optional[str],
    project_id: Optional[UUID],
    environment: Optional[str],
    background_tasks: BackgroundTasks
) -> ResultsResponse:
    client = orchestrator.vector_db.client
    collection_name = orchestrator.vector_db.cucumber_collection
    from qdrant_client.http import models as qdrant_models

    test_case_filter = qdrant_models.Filter(must=[
        qdrant_models.FieldCondition(key="type", match=qdrant_models.MatchValue(value="test_case"))
    ])

    if environment:
        test_case_filter.must.append(qdrant_models.FieldCondition(key="environment", match=qdrant_models.MatchValue(value=environment)))
    if build_id:
        test_case_filter.must.append(qdrant_models.FieldCondition(key="build_id", match=qdrant_models.MatchValue(value=str(build_id))))
    if test_run_id:
        test_case_filter.must.append(qdrant_models.FieldCondition(key="test_run_id", match=qdrant_models.MatchValue(value=str(test_run_id))))
    if project_id:
        test_case_filter.must.append(qdrant_models.FieldCondition(key="project_id", match=qdrant_models.MatchValue(value=str(project_id))))
    if status:
        test_case_filter.must.append(qdrant_models.FieldCondition(key="status", match=qdrant_models.MatchValue(value=status.upper())))
    if tag:
        test_case_filter.must.append(qdrant_models.FieldCondition(key="tags", match=qdrant_models.MatchAny(any=[tag])))
    if feature_name:
        test_case_filter.must.append(qdrant_models.FieldCondition(key="feature", match=qdrant_models.MatchText(text=feature_name)))

    all_test_cases = []
    offset = None
    limit = 1000
    cutoff_date = start_date or (dt.now_utc() - timedelta(days=limit_days))

    while True:
        test_cases_batch, offset = client.scroll(
            collection_name=collection_name,
            scroll_filter=test_case_filter,
            limit=limit,
            offset=offset,
            with_payload=True,
            with_vectors=False
        )

        filtered_batch = []
        for tc in test_cases_batch:
            try:
                timestamp = tc.payload.get("timestamp", "")
                if timestamp:
                    tc_date = dt.parse_iso8601_utc(timestamp)
                    if (not start_date or tc_date >= start_date) and (not end_date or tc_date <= end_date):
                        filtered_batch.append(tc)
                else:
                    filtered_batch.append(tc)
            except Exception as e:
                logger.warning(f"Failed to parse timestamp: {e}")
                filtered_batch.append(tc)

        all_test_cases.extend(filtered_batch)

        if offset is None or len(test_cases_batch) < limit:
            break

    passed = sum(1 for tc in all_test_cases if tc.payload.get("status") == "PASSED")
    failed = sum(1 for tc in all_test_cases if tc.payload.get("status") == "FAILED")
    skipped = sum(1 for tc in all_test_cases if tc.payload.get("status") == "SKIPPED")
    total = len(all_test_cases)
    pass_rate = passed / total if total else 0

    features = {}
    for tc in all_test_cases:
        feature = tc.payload.get("feature", "Unknown")
        status = tc.payload.get("status")
        if feature not in features:
            features[feature] = {"name": feature, "passed_scenarios": 0, "failed_scenarios": 0, "skipped_scenarios": 0}
        if status == "PASSED":
            features[feature]["passed_scenarios"] += 1
        elif status == "FAILED":
            features[feature]["failed_scenarios"] += 1
        elif status == "SKIPPED":
            features[feature]["skipped_scenarios"] += 1

    tags = {}
    for tc in all_test_cases:
        status = tc.payload.get("status", "")
        for t in tc.payload.get("tags", []):
            if t not in tags:
                tags[t] = {"count": 0, "passed": 0, "failed": 0, "skipped": 0, "pass_rate": 0}
            tags[t]["count"] += 1
            if status == "PASSED":
                tags[t]["passed"] += 1
            elif status == "FAILED":
                tags[t]["failed"] += 1
            elif status == "SKIPPED":
                tags[t]["skipped"] += 1

    for t in tags:
        tags[t]["pass_rate"] = round(tags[t]["passed"] / tags[t]["count"], 4) if tags[t]["count"] else 0

    last_updated = dt.now_utc()
    for tc in all_test_cases:
        try:
            timestamp = tc.payload.get("timestamp", "")
            if timestamp:
                tc_date = dt.parse_iso8601_utc(timestamp)
                if tc_date > last_updated:
                    last_updated = tc_date
        except Exception:
            continue

    background_tasks.add_task(
        logger.info,
        f"Qdrant query complete: {total} scenarios, {len(features)} features, {len(tags)} tags"
    )

    return ResultsResponse(
        status="success",
        results={
            "total_scenarios": total,
            "passed_scenarios": passed,
            "failed_scenarios": failed,
            "skipped_scenarios": skipped,
            "pass_rate": round(pass_rate, 6),
            "last_updated": dt.isoformat_utc(last_updated),
            "features": list(features.values()),
            "tags": tags
        }
    )


async def get_results_from_sql(
    db: Session,
    build_id: Optional[UUID] = None,
    test_run_id: Optional[UUID] = None,
    feature_name: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    limit_days: Optional[int] = 30,
    tag: Optional[str] = None,
    status: Optional[str] = None,
    project_id: Optional[UUID] = None,
    environment: Optional[str] = None,
    background_tasks: BackgroundTasks = BackgroundTasks()
) -> ResultsResponse:
    try:
        if not end_date:
            end_date = dt.now_utc()
        if not start_date and limit_days:
            start_date = end_date - timedelta(days=max(limit_days, 90))

        filter_conditions = []

        if start_date:
            filter_conditions.append(DBScenario.start_time >= start_date)
        if end_date:
            filter_conditions.append(DBScenario.end_time <= end_date)
        if build_id:
            filter_conditions.append(DBTestRun.uuid == str(build_id))
        if test_run_id:
            filter_conditions.append(DBScenario.test_run_id == str(test_run_id))
        if project_id:
            filter_conditions.append(DBTestRun.project_id == str(project_id))
        if feature_name:
            filter_conditions.append(DBFeature.name.ilike(f"%{feature_name}%"))
        if status:
            try:
                status_enum = TestStatus[status.upper()]
                filter_conditions.append(DBScenario.status == status_enum)
            except (KeyError, ValueError):
                raise HTTPException(status_code=400, detail=f"Invalid status: {status}")
        if environment:
            filter_conditions.append(DBTestRun.environment == environment)

        base_query = db.query(DBScenario).join(
            DBTestRun, DBScenario.test_run_id == DBTestRun.uuid
        ).join(
            DBFeature, DBScenario.feature_id == DBFeature.id, isouter=True
        )

        if tag:
            base_query = base_query.join(DBScenarioTag, DBScenario.id == DBScenarioTag.scenario_id)
            base_query = base_query.filter(DBScenarioTag.tag == tag)

        base_query = base_query.filter(*filter_conditions)

        stats_query = db.query(
            func.count(distinct(DBScenario.id)).label("total"),
            func.sum(case((DBScenario.status == TestStatus.PASSED, 1), else_=0)).label("passed"),
            func.sum(case((DBScenario.status == TestStatus.FAILED, 1), else_=0)).label("failed"),
            func.sum(case((DBScenario.status == TestStatus.SKIPPED, 1), else_=0)).label("skipped"),
            func.max(DBScenario.updated_at).label("last_updated")
        ).select_from(DBScenario).join(
            DBTestRun, DBScenario.test_run_id == DBTestRun.uuid
        ).join(
            DBFeature, DBScenario.feature_id == DBFeature.id, isouter=True
        )

        if tag:
            stats_query = stats_query.join(DBScenarioTag, DBScenario.id == DBScenarioTag.scenario_id).filter(DBScenarioTag.tag == tag)

        stats_query = stats_query.filter(*filter_conditions)

        stats = stats_query.first()

        if not stats or stats.total == 0:
            return ResultsResponse(
                status="success",
                results={
                    "total_scenarios": 0,
                    "passed_scenarios": 0,
                    "failed_scenarios": 0,
                    "skipped_scenarios": 0,
                    "pass_rate": 0,
                    "last_updated": dt.isoformat_utc(dt.now_utc()),
                    "features": [],
                    "tags": {}
                }
            )

        pass_rate = stats.passed / stats.total if stats.total > 0 else 0

        feature_stats_query = db.query(
            DBFeature.name.label("feature_name"),
            func.count(distinct(DBScenario.id)).label("total"),
            func.sum(case((DBScenario.status == TestStatus.PASSED, 1), else_=0)).label("passed"),
            func.sum(case((DBScenario.status == TestStatus.FAILED, 1), else_=0)).label("failed"),
            func.sum(case((DBScenario.status == TestStatus.SKIPPED, 1), else_=0)).label("skipped")
        ).join(
            DBScenario, DBFeature.id == DBScenario.feature_id
        ).join(
            DBTestRun, DBScenario.test_run_id == DBTestRun.uuid
        )

        for condition in filter_conditions:
            feature_stats_query = feature_stats_query.filter(condition)

        if tag:
            feature_stats_query = feature_stats_query.join(DBScenarioTag, DBScenario.id == DBScenarioTag.scenario_id).filter(DBScenarioTag.tag == tag)

        feature_stats_query = feature_stats_query.group_by(DBFeature.name).order_by(func.count(distinct(DBScenario.id)).desc())

        feature_stats = []
        for f in feature_stats_query.all():
            feature_stats.append({
                "name": f.feature_name or "Unknown",
                "passed_scenarios": f.passed or 0,
                "failed_scenarios": f.failed or 0,
                "skipped_scenarios": f.skipped or 0
            })

        scenario_ids = [row[0] for row in base_query.with_entities(DBScenario.id).all()]
        if scenario_ids:
            tag_count_for_scenarios = db.query(func.count(DBScenarioTag.tag)).filter(
                DBScenarioTag.scenario_id.in_(scenario_ids)
            ).scalar()
            logger.info(f"Found {tag_count_for_scenarios} tags for {len(scenario_ids)} filtered scenarios")

        tag_stats_query = db.query(
            DBScenarioTag.tag,
            func.count(distinct(DBScenario.id)).label("count"),
            func.sum(case((DBScenario.status == TestStatus.PASSED, 1), else_=0)).label("passed"),
            func.sum(case((DBScenario.status == TestStatus.FAILED, 1), else_=0)).label("failed"),
            func.sum(case((DBScenario.status == TestStatus.SKIPPED, 1), else_=0)).label("skipped")
        ).join(
            DBScenario, DBScenarioTag.scenario_id == DBScenario.id
        ).join(
            DBTestRun, DBScenario.test_run_id == DBTestRun.uuid
        ).join(
            DBFeature, DBScenario.feature_id == DBFeature.id, isouter=True
        )

        for condition in filter_conditions:
            tag_stats_query = tag_stats_query.filter(condition)

        tag_stats_query = tag_stats_query.group_by(DBScenarioTag.tag).order_by(func.count(distinct(DBScenario.id)).desc())

        tag_stats = {}
        for t in tag_stats_query.all():
            tag_pass_rate = t.passed / t.count if t.count > 0 else 0
            tag_stats[t.tag] = {
                "count": t.count,
                "pass_rate": round(tag_pass_rate, 4),
                "passed": t.passed,
                "failed": t.failed,
                "skipped": t.skipped
            }

        background_tasks.add_task(
            logger.info,
            f"SQL query complete: {stats.total} scenarios, {len(feature_stats)} features, {len(tag_stats)} tags"
        )

        last_updated = stats.last_updated or dt.now_utc()

        return ResultsResponse(
            status="success",
            results={
                "total_scenarios": stats.total or 0,
                "passed_scenarios": stats.passed or 0,
                "failed_scenarios": stats.failed or 0,
                "skipped_scenarios": stats.skipped or 0,
                "pass_rate": round(pass_rate, 6),
                "last_updated": dt.isoformat_utc(last_updated),
                "features": feature_stats,
                "tags": tag_stats
            }
        )
    except Exception as e:
        logger.error(f"Error retrieving test results from SQL database: {str(e)}", exc_info=True)
        raise e

