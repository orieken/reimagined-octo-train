from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Dict, Any, Optional
import logging

from app.config import settings
from app.services.orchestrator import ServiceOrchestrator
from app.services import datetime_service as dt
from app.api.dependencies import get_orchestrator_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix=settings.API_PREFIX, tags=["stats"])


@router.get("/projects/lookup", response_model=Dict[str, Any])
async def lookup_project_by_name(
        name: str = Query(..., description="The human-readable project name to look up"),
        orchestrator: ServiceOrchestrator = Depends(get_orchestrator_service)
):
    """
    Look up project details by its human-readable name.

    Args:
        name: The project name to look up
        orchestrator: Service orchestrator for accessing databases

    Returns:
        Project details if found, or an error message if not found
    """
    try:
        client = orchestrator.vector_db.client
        collection_name = orchestrator.vector_db.cucumber_collection
        from qdrant_client.http import models as qdrant_models

        # Get reports to check if any match the project name
        report_filter = qdrant_models.Filter(
            must=[
                qdrant_models.FieldCondition(
                    key="type",
                    match=qdrant_models.MatchValue(value="report")
                )
            ]
        )

        # Get reports to scan for the project name
        reports, offset, limit = [], None, 100

        while True:
            reports_batch, offset = client.scroll(
                collection_name=collection_name,
                scroll_filter=report_filter,
                limit=limit,
                offset=offset,
                with_payload=True,
                with_vectors=False
            )

            reports.extend(reports_batch)

            if offset is None or len(reports_batch) < limit:
                break

        # Look for a project with matching name
        matching_reports = []
        project_id = None

        for report in reports:
            payload = report.payload
            if payload.get("project", "").lower() == name.lower():
                # Found a report with matching project name
                matching_reports.append(report)
                if not project_id and "project_id" in payload:
                    project_id = payload["project_id"]

        if not matching_reports:
            return {
                "status": "error",
                "message": f"No project found with name '{name}'",
                "timestamp": dt.isoformat_utc(dt.now_utc())
            }

        # Collect project details from matching reports
        environments = set()
        branches = set()
        build_ids = set()
        run_timestamps = []

        for report in matching_reports:
            payload = report.payload

            # Collect environment information
            if "environment" in payload:
                environments.add(payload["environment"])

            # Collect branch information
            if "branch" in payload:
                branches.add(payload["branch"])

            # Collect build IDs
            if "build_id" in payload:
                build_ids.add(payload["build_id"])

            # Collect timestamps
            if "timestamp" in payload:
                run_timestamps.append(payload["timestamp"])

        # Get statistics if project_id is found
        scenario_count = 0
        passed_count = 0
        failed_count = 0

        if project_id:
            # Get scenario counts
            scenario_filter = qdrant_models.Filter(
                must=[
                    qdrant_models.FieldCondition(
                        key="type",
                        match=qdrant_models.MatchValue(value="scenario")
                    ),
                    qdrant_models.FieldCondition(
                        key="project_id",
                        match=qdrant_models.MatchValue(value=project_id)
                    )
                ]
            )

            scenario_count = client.count(collection_name, scenario_filter).count

            # Get passed scenarios
            passed_filter = qdrant_models.Filter(
                must=scenario_filter.must + [
                    qdrant_models.FieldCondition(
                        key="status",
                        match=qdrant_models.MatchValue(value="PASSED")
                    )
                ]
            )
            passed_count = client.count(collection_name, passed_filter).count

            # Get failed scenarios
            failed_filter = qdrant_models.Filter(
                must=scenario_filter.must + [
                    qdrant_models.FieldCondition(
                        key="status",
                        match=qdrant_models.MatchValue(value="FAILED")
                    )
                ]
            )
            failed_count = client.count(collection_name, failed_filter).count

        # Sort timestamps and get the latest
        latest_run = None
        if run_timestamps:
            sorted_timestamps = sorted(run_timestamps, reverse=True)
            latest_run = sorted_timestamps[0] if sorted_timestamps else None

        return {
            "status": "success",
            "project": {
                "name": name,
                "id": project_id,
                "total_reports": len(matching_reports),
                "environments": list(environments),
                "branches": list(branches),
                "builds": list(build_ids),
                "latest_run": latest_run,
                "total_scenarios": scenario_count,
                "passed_scenarios": passed_count,
                "failed_scenarios": failed_count,
                "pass_rate": round(passed_count / scenario_count, 4) if scenario_count > 0 else 0
            },
            "timestamp": dt.isoformat_utc(dt.now_utc())
        }

    except Exception as e:
        logger.error(f"Error looking up project by name: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to look up project: {str(e)}")