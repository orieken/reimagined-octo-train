# app/api/routes/reporting.py
from fastapi import APIRouter, Depends, HTTPException, Query, Path, Body, Response
from fastapi.responses import FileResponse
from typing import List, Dict, Any, Optional
import logging
from datetime import datetime
import os
from pathlib import Path

from app.config import settings
from app.services.orchestrator import ServiceOrchestrator
from app.services.reporting import ReportingService
from app.api.dependencies import get_orchestrator_service
from app.models.api import (
    ErrorResponse, ReportTemplate, ReportSchedule, Report,
    ReportFormat, ReportStatus, ReportType, CreateReportRequest,
    CreateScheduleRequest
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix=settings.API_PREFIX, tags=["reporting"])


# Dependency to get reporting service
async def get_reporting_service(
        orchestrator: ServiceOrchestrator = Depends(get_orchestrator_service)
) -> ReportingService:
    return ReportingService(orchestrator)


@router.get("/reports/templates", response_model=List[ReportTemplate])
async def list_report_templates(
        reporting: ReportingService = Depends(get_reporting_service)
):
    """
    Get a list of available report templates.
    """
    try:
        templates = await reporting.get_report_templates()
        return templates
    except Exception as e:
        logger.error(f"Error listing report templates: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list report templates: {str(e)}"
        )


@router.get("/reports/templates/{template_id}", response_model=ReportTemplate)
async def get_report_template(
        template_id: str = Path(description="ID of the template to retrieve"),
        reporting: ReportingService = Depends(get_reporting_service)
):
    """
    Get a specific report template by ID.
    """
    try:
        template = await reporting.get_report_template(template_id)

        if not template:
            raise HTTPException(
                status_code=404,
                detail=f"Report template with ID {template_id} not found"
            )

        return template
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving report template {template_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve report template: {str(e)}"
        )


@router.post("/reports/templates", response_model=ReportTemplate, status_code=201)
async def create_report_template(
        template: ReportTemplate = Body(..., description="Report template to create"),
        reporting: ReportingService = Depends(get_reporting_service)
):
    """
    Create a new report template.
    """
    try:
        created_template = await reporting.create_report_template(template)
        return created_template
    except Exception as e:
        logger.error(f"Error creating report template: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create report template: {str(e)}"
        )


@router.put("/reports/templates/{template_id}", response_model=ReportTemplate)
async def update_report_template(
        template_id: str = Path(description="ID of the template to update"),
        template: ReportTemplate = Body(description="Updated report template"),
        reporting: ReportingService = Depends(get_reporting_service)
):
    """
    Update an existing report template.
    """
    try:
        updated_template = await reporting.update_report_template(template_id, template)

        if not updated_template:
            raise HTTPException(
                status_code=404,
                detail=f"Report template with ID {template_id} not found"
            )

        return updated_template
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating report template {template_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update report template: {str(e)}"
        )


@router.delete("/reports/templates/{template_id}", status_code=204)
async def delete_report_template(
        template_id: str = Path(description="ID of the template to delete"),
        reporting: ReportingService = Depends(get_reporting_service)
):
    """
    Delete a report template.
    """
    try:
        success = await reporting.delete_report_template(template_id)

        if not success:
            raise HTTPException(
                status_code=404,
                detail=f"Report template with ID {template_id} not found"
            )

        return Response(status_code=204)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting report template {template_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete report template: {str(e)}"
        )


@router.get("/reports/schedules", response_model=List[ReportSchedule])
async def list_scheduled_reports(
        reporting: ReportingService = Depends(get_reporting_service)
):
    """
    Get a list of scheduled reports.
    """
    try:
        schedules = await reporting.get_scheduled_reports()
        return schedules
    except Exception as e:
        logger.error(f"Error listing scheduled reports: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list scheduled reports: {str(e)}"
        )


@router.get("/reports/schedules/{schedule_id}", response_model=ReportSchedule)
async def get_scheduled_report(
        schedule_id: str = Path(description="ID of the schedule to retrieve"),
        reporting: ReportingService = Depends(get_reporting_service)
):
    """
    Get a specific scheduled report by ID.
    """
    try:
        schedule = await reporting.get_scheduled_report(schedule_id)

        if not schedule:
            raise HTTPException(
                status_code=404,
                detail=f"Schedule with ID {schedule_id} not found"
            )

        return schedule
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving schedule {schedule_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve schedule: {str(e)}"
        )


@router.post("/reports/schedules", response_model=ReportSchedule, status_code=201)
async def schedule_report(
        request: CreateScheduleRequest = Body(description="Schedule report request"),
        reporting: ReportingService = Depends(get_reporting_service)
):
    """
    Schedule a report for periodic generation.
    """
    try:
        # Create schedule object
        schedule = ReportSchedule(
            id=None,  # Will be generated
            name=request.name,
            template_id=request.template_id,
            parameters=request.parameters,
            frequency=request.frequency,
            next_run=request.next_run,
            created_at=datetime.now().isoformat()
        )

        # Schedule report
        created_schedule = await reporting.schedule_report(schedule)
        return created_schedule
    except Exception as e:
        logger.error(f"Error scheduling report: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to schedule report: {str(e)}"
        )


@router.put("/reports/schedules/{schedule_id}", response_model=ReportSchedule)
async def update_schedule(
        schedule_id: str = Path( description="ID of the schedule to update"),
        schedule: ReportSchedule = Body( description="Updated schedule"),
        reporting: ReportingService = Depends(get_reporting_service)
):
    """
    Update an existing report schedule.
    """
    try:
        updated_schedule = await reporting.update_schedule(schedule_id, schedule)

        if not updated_schedule:
            raise HTTPException(
                status_code=404,
                detail=f"Schedule with ID {schedule_id} not found"
            )

        return updated_schedule
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating schedule {schedule_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update schedule: {str(e)}"
        )


@router.delete("/reports/schedules/{schedule_id}", status_code=204)
async def delete_schedule(
        schedule_id: str = Path( description="ID of the schedule to delete"),
        reporting: ReportingService = Depends(get_reporting_service)
):
    """
    Delete a report schedule.
    """
    try:
        success = await reporting.delete_schedule(schedule_id)

        if not success:
            raise HTTPException(
                status_code=404,
                detail=f"Schedule with ID {schedule_id} not found"
            )

        return Response(status_code=204)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting schedule {schedule_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete schedule: {str(e)}"
        )


@router.get("/reports", response_model=List[Report])
async def list_reports(
        limit: int = Query(50, description="Maximum number of reports to return"),
        offset: int = Query(0, description="Number of reports to skip"),
        reporting: ReportingService = Depends(get_reporting_service)
):
    """
    Get a list of generated reports.
    """
    try:
        reports = await reporting.get_reports(limit, offset)
        return reports
    except Exception as e:
        logger.error(f"Error listing reports: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list reports: {str(e)}"
        )


@router.get("/reports/{report_id}", response_model=Report)
async def get_report(
        report_id: str = Path( description="ID of the report to retrieve"),
        reporting: ReportingService = Depends(get_reporting_service)
):
    """
    Get a specific report by ID.
    """
    try:
        report = await reporting.get_report(report_id)

        if not report:
            raise HTTPException(
                status_code=404,
                detail=f"Report with ID {report_id} not found"
            )

        return report
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving report {report_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve report: {str(e)}"
        )


@router.get("/reports/{report_id}/download")
async def download_report(
        report_id: str = Path( description="ID of the report to download"),
        reporting: ReportingService = Depends(get_reporting_service)
):
    """
    Download a generated report file.
    """
    try:
        report = await reporting.get_report(report_id)

        if not report:
            raise HTTPException(
                status_code=404,
                detail=f"Report with ID {report_id} not found"
            )

        if not report.file_path or not os.path.exists(report.file_path):
            raise HTTPException(
                status_code=404,
                detail=f"Report file not found"
            )

        # Determine content type based on format
        format_to_content_type = {
            "html": "text/html",
            "pdf": "application/pdf",
            "csv": "text/csv"
        }

        content_type = format_to_content_type.get(report.format.lower(), "application/octet-stream")

        # Return file response
        return FileResponse(
            path=report.file_path,
            media_type=content_type,
            filename=f"report_{report_id}.{report.format}"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error downloading report {report_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to download report: {str(e)}"
        )


@router.post("/reports", response_model=Report, status_code=201)
async def generate_report(
        request: CreateReportRequest = Body( description="Generate report request"),
        reporting: ReportingService = Depends(get_reporting_service)
):
    """
    Generate a report on demand.
    """
    try:
        report = await reporting.generate_report(
            template_id=request.template_id,
            parameters=request.parameters
        )
        return report
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error generating report: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate report: {str(e)}"
        )
