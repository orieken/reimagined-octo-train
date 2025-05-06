from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Dict, Any, Optional
import logging

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
            # Start with the basic type filter
            conditions = [qdrant_models.FieldCondition(key="type", match=qdrant_models.MatchValue(value="scenario"))]

            # Add status filter if provided
            if status:
                conditions.append(
                    qdrant_models.FieldCondition(key="status", match=qdrant_models.MatchValue(value=status)))

            # We'll skip environment filter here since scenarios don't have environment field
            # We'll filter by environment later if needed

            return qdrant_models.Filter(must=conditions)

        # Log the filters being used
        logger.info(f"Using filter with type=scenario, status=None")

        # Count total scenarios
        total_count = client.count(collection_name, base_filter()).count
        logger.info(f"Found {total_count} total scenarios")

        # Count passed scenarios
        passed_count = client.count(collection_name, base_filter("PASSED")).count
        logger.info(f"Found {passed_count} passed scenarios")

        # Count failed scenarios
        failed_count = client.count(collection_name, base_filter("FAILED")).count
        logger.info(f"Found {failed_count} failed scenarios")

        # Calculate pass rate
        pass_rate = passed_count / total_count if total_count else 0

        # Scroll through scenarios
        all_test_cases, offset, limit = [], None, 1000

        while True:
            logger.info(f"Scrolling through scenarios with offset={offset}, limit={limit}")
            test_cases_batch, offset = client.scroll(
                collection_name=collection_name,
                scroll_filter=base_filter(),
                limit=limit,
                offset=offset,
                with_payload=True,
                with_vectors=False
            )

            logger.info(f"Retrieved {len(test_cases_batch)} scenarios in this batch")
            all_test_cases.extend(test_cases_batch)

            if offset is None or len(test_cases_batch) < limit:
                break

        # Process data
        logger.info(f"Processing {len(all_test_cases)} total scenarios")
        report_ids = set()
        external_report_ids = set()
        tag_counts = {}
        skipped_count = 0
        total_duration = 0

        for tc in all_test_cases:
            payload = tc.payload
            # Get test_run_id (our primary key for reports)
            test_run_id = payload.get("test_run_id")
            if test_run_id:
                report_ids.add(test_run_id)

            # Check for external report_id if present
            report_id = payload.get("report_id")
            if report_id:
                external_report_ids.add(report_id)

            # Count tags if present
            for tag in payload.get("tags", []):
                tag_counts[tag] = tag_counts.get(tag, 0) + 1

            # Count skipped tests
            if payload.get("status") == "SKIPPED":
                skipped_count += 1

            # Sum durations if present
            total_duration += payload.get("duration", 0)

        # Get top tags
        top_tags = dict(sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)[:10])

        # Calculate average duration
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
            must = [qdrant_models.FieldCondition(key="type", match=qdrant_models.MatchValue(value="scenario"))]
            if status:
                must.append(qdrant_models.FieldCondition(key="status", match=qdrant_models.MatchValue(value=status)))
            # Skip environment filter since scenarios don't have that field
            return qdrant_models.Filter(must=must)

        # Log the filters being used
        logger.info(f"Using filter with type=scenario, status=None")

        # Count scenarios
        total_count = client.count(collection_name, filter_with_status()).count
        logger.info(f"Found {total_count} total scenarios")

        passed_count = client.count(collection_name, filter_with_status("PASSED")).count
        logger.info(f"Found {passed_count} passed scenarios")

        failed_count = client.count(collection_name, filter_with_status("FAILED")).count
        logger.info(f"Found {failed_count} failed scenarios")

        pass_rate = passed_count / total_count if total_count else 0

        # Scroll through scenarios
        all_test_cases, offset, limit = [], None, 1000

        while True:
            logger.info(f"Scrolling through scenarios with offset={offset}, limit={limit}")
            test_cases_batch, offset = client.scroll(
                collection_name=collection_name,
                scroll_filter=filter_with_status(),
                limit=limit,
                offset=offset,
                with_payload=True,
                with_vectors=False
            )

            logger.info(f"Retrieved {len(test_cases_batch)} scenarios in this batch")
            all_test_cases.extend(test_cases_batch)

            if offset is None or len(test_cases_batch) < limit:
                break

        # Process data
        logger.info(f"Processing {len(all_test_cases)} total scenarios")
        report_ids = set()
        external_report_ids = set()
        tag_counts = {}

        for tc in all_test_cases:
            # Get report IDs
            test_run_id = tc.payload.get("test_run_id")
            if test_run_id:
                report_ids.add(test_run_id)

            # Get external report IDs if present
            report_id = tc.payload.get("report_id")
            if report_id:
                external_report_ids.add(report_id)

            # Count tags if present
            for tag in tc.payload.get("tags", []):
                tag_counts[tag] = tag_counts.get(tag, 0) + 1

        # Get top tags
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


@router.get("/stats/health", response_model=Dict[str, Any])
async def get_stats_health(
        orchestrator: ServiceOrchestrator = Depends(get_orchestrator_service)
):
    """
    Health check endpoint specific to the stats service.
    This can be used to verify that the stats functionality is working correctly.
    When this service is split into its own microservice, this endpoint will become
    the main health check for that service.
    """
    try:
        client = orchestrator.vector_db.client
        collection_name = orchestrator.vector_db.cucumber_collection
        from qdrant_client.http import models as qdrant_models

        # Check if we can query the database
        try:
            # Try to count scenarios
            scenario_filter = qdrant_models.Filter(
                must=[
                    qdrant_models.FieldCondition(
                        key="type",
                        match=qdrant_models.MatchValue(value="scenario")
                    )
                ]
            )

            scenario_count = client.count(collection_name, scenario_filter).count

            # Check if we can count by status
            passed_filter = qdrant_models.Filter(
                must=[
                    qdrant_models.FieldCondition(
                        key="type",
                        match=qdrant_models.MatchValue(value="scenario")
                    ),
                    qdrant_models.FieldCondition(
                        key="status",
                        match=qdrant_models.MatchValue(value="PASSED")
                    )
                ]
            )

            passed_count = client.count(collection_name, passed_filter).count

            database_status = "healthy"
            database_message = f"Successfully queried database. Found {scenario_count} scenarios."

        except Exception as e:
            database_status = "unhealthy"
            database_message = f"Failed to query database: {str(e)}"

        # Check if we can generate the stats summary
        try:
            # Simple test of the stats summary function
            # Just get scenario counts without detailed processing
            total_count = client.count(collection_name, qdrant_models.Filter(
                must=[qdrant_models.FieldCondition(key="type", match=qdrant_models.MatchValue(value="scenario"))]
            )).count

            passed_count = client.count(collection_name, qdrant_models.Filter(
                must=[
                    qdrant_models.FieldCondition(key="type", match=qdrant_models.MatchValue(value="scenario")),
                    qdrant_models.FieldCondition(key="status", match=qdrant_models.MatchValue(value="PASSED"))
                ]
            )).count

            failed_count = client.count(collection_name, qdrant_models.Filter(
                must=[
                    qdrant_models.FieldCondition(key="type", match=qdrant_models.MatchValue(value="scenario")),
                    qdrant_models.FieldCondition(key="status", match=qdrant_models.MatchValue(value="FAILED"))
                ]
            )).count

            # Verify we can calculate metrics
            pass_rate = passed_count / total_count if total_count else 0

            processing_status = "healthy"
            processing_message = "Successfully calculated stats metrics"

        except Exception as e:
            processing_status = "unhealthy"
            processing_message = f"Failed to calculate stats metrics: {str(e)}"

        # Determine overall status
        overall_status = "healthy" if database_status == "healthy" and processing_status == "healthy" else "unhealthy"

        return {
            "status": overall_status,
            "service": "stats",
            "components": {
                "database": {
                    "status": database_status,
                    "message": database_message
                },
                "processing": {
                    "status": processing_status,
                    "message": processing_message
                }
            },
            "data_summary": {
                "total_scenarios": scenario_count if database_status == "healthy" else 0,
                "collection": collection_name
            },
            "timestamp": dt.isoformat_utc(dt.now_utc())
        }
    except Exception as e:
        logger.error(f"Stats health check failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Stats health check failed: {str(e)}")


@router.get("/stats/environments/{environment}/summary", response_model=Dict[str, Any])
async def get_environment_stats(
        environment: str,
        days: int = Query(30),
        orchestrator: ServiceOrchestrator = Depends(get_orchestrator_service)
):
    """
    Get test statistics for a specific environment.

    Args:
        environment: The environment to get stats for (e.g., "staging", "production")
        days: Number of days to look back for historical data
        orchestrator: Service orchestrator for accessing databases

    Returns:
        Summary statistics for the specified environment
    """
    try:
        client = orchestrator.vector_db.client
        collection_name = orchestrator.vector_db.cucumber_collection
        from qdrant_client.http import models as qdrant_models

        # First, we need to find reports that match the environment
        # Since environment is stored on reports, not scenarios
        report_filter = qdrant_models.Filter(
            must=[
                qdrant_models.FieldCondition(
                    key="type",
                    match=qdrant_models.MatchValue(value="report")
                ),
                qdrant_models.FieldCondition(
                    key="environment",
                    match=qdrant_models.MatchValue(value=environment)
                )
            ]
        )

        # Get all reports for this environment
        matching_reports, offset, limit = [], None, 100

        while True:
            report_batch, offset = client.scroll(
                collection_name=collection_name,
                scroll_filter=report_filter,
                limit=limit,
                offset=offset,
                with_payload=True,
                with_vectors=False
            )

            matching_reports.extend(report_batch)

            if offset is None or len(report_batch) < limit:
                break

        logger.info(f"Found {len(matching_reports)} reports for environment '{environment}'")

        if not matching_reports:
            return {
                "environment": environment,
                "time_period": f"Last {days} days",
                "total_reports": 0,
                "message": f"No test reports found for environment '{environment}'"
            }

        # Extract report IDs to query related scenarios
        report_ids = [report.id for report in matching_reports]

        # Create a filter to find all scenarios from these reports
        scenario_filter = qdrant_models.Filter(
            must=[
                qdrant_models.FieldCondition(
                    key="type",
                    match=qdrant_models.MatchValue(value="scenario")
                ),
                qdrant_models.FieldCondition(
                    key="test_run_id",
                    match=qdrant_models.MatchAny(any=report_ids)
                )
            ]
        )

        # Get stats for scenarios in these reports
        total_count = client.count(collection_name, scenario_filter).count

        # Get passed scenarios
        passed_filter = qdrant_models.Filter(
            must=[
                qdrant_models.FieldCondition(
                    key="type",
                    match=qdrant_models.MatchValue(value="scenario")
                ),
                qdrant_models.FieldCondition(
                    key="test_run_id",
                    match=qdrant_models.MatchAny(any=report_ids)
                ),
                qdrant_models.FieldCondition(
                    key="status",
                    match=qdrant_models.MatchValue(value="PASSED")
                )
            ]
        )
        passed_count = client.count(collection_name, passed_filter).count

        # Get failed scenarios
        failed_filter = qdrant_models.Filter(
            must=[
                qdrant_models.FieldCondition(
                    key="type",
                    match=qdrant_models.MatchValue(value="scenario")
                ),
                qdrant_models.FieldCondition(
                    key="test_run_id",
                    match=qdrant_models.MatchAny(any=report_ids)
                ),
                qdrant_models.FieldCondition(
                    key="status",
                    match=qdrant_models.MatchValue(value="FAILED")
                )
            ]
        )
        failed_count = client.count(collection_name, failed_filter).count

        # Calculate pass rate
        pass_rate = passed_count / total_count if total_count else 0

        # Extract metadata from reports
        build_ids = set()
        branches = set()
        projects = set()

        for report in matching_reports:
            payload = report.payload

            # Collect unique identifiers
            if "build_id" in payload:
                build_ids.add(payload["build_id"])

            if "branch" in payload:
                branches.add(payload["branch"])

            if "project" in payload:
                projects.add(payload["project"])

        # Get timestamp of last run in this environment
        latest_timestamp = max([
            payload.get("timestamp")
            for report in matching_reports
            if (payload := report.payload) and "timestamp" in payload
        ], default=None)

        return {
            "environment": environment,
            "time_period": f"Last {days} days",
            "total_reports": len(matching_reports),
            "total_scenarios": total_count,
            "passed_scenarios": passed_count,
            "failed_scenarios": failed_count,
            "pass_rate": pass_rate,
            "projects": list(projects),
            "branches": list(branches),
            "unique_builds": len(build_ids),
            "latest_run": latest_timestamp,
            "timestamp": dt.isoformat_utc(dt.now_utc())
        }
    except Exception as e:
        logger.error(f"Error retrieving environment stats: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve environment stats: {str(e)}")


@router.get("/stats/projects/{project_id}/summary", response_model=Dict[str, Any])
async def get_project_stats(
        project_id: str,
        days: int = Query(30),
        orchestrator: ServiceOrchestrator = Depends(get_orchestrator_service)
):
    """
    Get test statistics for a specific project.

    Args:
        project_id: The project ID to get stats for
        days: Number of days to look back for historical data
        orchestrator: Service orchestrator for accessing databases

    Returns:
        Summary statistics for the specified project
    """
    try:
        client = orchestrator.vector_db.client
        collection_name = orchestrator.vector_db.cucumber_collection
        from qdrant_client.http import models as qdrant_models

        # Create filter for scenarios with this project_id
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

        # Get total count of scenarios for this project
        total_count = client.count(collection_name, scenario_filter).count

        if total_count == 0:
            return {
                "project_id": project_id,
                "time_period": f"Last {days} days",
                "total_scenarios": 0,
                "message": f"No scenarios found for project '{project_id}'"
            }

        # Get passed scenarios count
        passed_filter = qdrant_models.Filter(
            must=[
                qdrant_models.FieldCondition(
                    key="type",
                    match=qdrant_models.MatchValue(value="scenario")
                ),
                qdrant_models.FieldCondition(
                    key="project_id",
                    match=qdrant_models.MatchValue(value=project_id)
                ),
                qdrant_models.FieldCondition(
                    key="status",
                    match=qdrant_models.MatchValue(value="PASSED")
                )
            ]
        )
        passed_count = client.count(collection_name, passed_filter).count

        # Get failed scenarios count
        failed_filter = qdrant_models.Filter(
            must=[
                qdrant_models.FieldCondition(
                    key="type",
                    match=qdrant_models.MatchValue(value="scenario")
                ),
                qdrant_models.FieldCondition(
                    key="project_id",
                    match=qdrant_models.MatchValue(value=project_id)
                ),
                qdrant_models.FieldCondition(
                    key="status",
                    match=qdrant_models.MatchValue(value="FAILED")
                )
            ]
        )
        failed_count = client.count(collection_name, failed_filter).count

        # Calculate pass rate
        pass_rate = passed_count / total_count if total_count else 0

        # Get all scenarios to extract metadata
        all_scenarios, offset, limit = [], None, 100

        while True:
            scenarios_batch, offset = client.scroll(
                collection_name=collection_name,
                scroll_filter=scenario_filter,
                limit=limit,
                offset=offset,
                with_payload=True,
                with_vectors=False
            )

            all_scenarios.extend(scenarios_batch)

            if offset is None or len(scenarios_batch) < limit:
                break

        # Extract metadata from scenarios
        test_run_ids = set()
        report_ids = set()
        tag_counts = {}

        for scenario in all_scenarios:
            payload = scenario.payload

            # Collect test run IDs
            if "test_run_id" in payload:
                test_run_ids.add(payload["test_run_id"])

            # Collect report IDs
            if "report_id" in payload:
                report_ids.add(payload["report_id"])

            # Count tags
            for tag in payload.get("tags", []):
                tag_counts[tag] = tag_counts.get(tag, 0) + 1

        # Get top tags
        top_tags = dict(sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)[:10])

        # Also get data from reports for this project
        report_filter = qdrant_models.Filter(
            must=[
                qdrant_models.FieldCondition(
                    key="type",
                    match=qdrant_models.MatchValue(value="report")
                ),
                qdrant_models.FieldCondition(
                    key="project_id",
                    match=qdrant_models.MatchValue(value=project_id)
                )
            ]
        )

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

        # Extract additional metadata from reports
        environments = set()
        branches = set()

        for report in reports:
            payload = report.payload

            # Collect environment information
            if "environment" in payload:
                environments.add(payload["environment"])

            # Collect branch information
            if "branch" in payload:
                branches.add(payload["branch"])

        # Get project name
        project_name = "Unknown"
        if reports:
            project_name = reports[0].payload.get("project", "Unknown")

        return {
            "project_id": project_id,
            "project_name": project_name,
            "time_period": f"Last {days} days",
            "total_scenarios": total_count,
            "passed_scenarios": passed_count,
            "failed_scenarios": failed_count,
            "pass_rate": pass_rate,
            "unique_test_runs": len(test_run_ids),
            "environments": list(environments),
            "branches": list(branches),
            "top_tags": top_tags,
            "timestamp": dt.isoformat_utc(dt.now_utc())
        }
    except Exception as e:
        logger.error(f"Error retrieving project stats: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve project stats: {str(e)}")
