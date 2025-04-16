# app/services/reporting.py
import logging
import asyncio
from typing import List, Dict, Any, Optional, Union
from datetime import datetime, timedelta, timezone
import uuid
import json
import os
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt
import io
import base64
from enum import Enum

from app.config import settings
from app.services.orchestrator import ServiceOrchestrator
from app.services.analytics import AnalyticsService

from app.models import ReportStatus, ReportType, Report
from app.models.schemas import ReportTemplate, ReportSchedule

logger = logging.getLogger(__name__)


# Helper function to get timezone-aware UTC datetime
def utcnow():
    """Return current UTC datetime with timezone information."""
    return datetime.now(timezone.utc)


# Helper function to get ISO formatted string with timezone info
def utcnow_iso():
    """Return current UTC datetime as ISO 8601 string with timezone information."""
    return datetime.now(timezone.utc).isoformat()

class ReportingService:
    """
    Service for generating, scheduling, and delivering reports.
    """

    def __init__(self, orchestrator: ServiceOrchestrator):
        self.orchestrator = orchestrator
        self.analytics_service = AnalyticsService(orchestrator)

        # Create reports directory if it doesn't exist
        self.reports_dir = Path(settings.REPORTS_DIR)
        self.reports_dir.mkdir(parents=True, exist_ok=True)

        # Initialize scheduler
        self._initialize_scheduler()

    def _initialize_scheduler(self):
        """
        Initialize the scheduler for periodic reports.
        """
        # Load scheduled reports
        self.scheduled_reports = self._load_scheduled_reports()

        # Schedule background task for periodic report generation
        asyncio.create_task(self._scheduler_loop())

    async def _scheduler_loop(self):
        """
        Background task for periodic report generation.
        """
        while True:
            try:
                # Check for reports to generate
                now = utcnow()  # Use timezone-aware UTC now

                for schedule_id, schedule in self.scheduled_reports.items():
                    # Parse next_run with timezone info or add UTC timezone
                    next_run = datetime.fromisoformat(schedule.next_run)
                    if next_run.tzinfo is None:
                        next_run = next_run.replace(tzinfo=timezone.utc)

                    if now >= next_run:
                        # Generate report
                        await self.generate_report(
                            template_id=schedule.template_id,
                            parameters=schedule.parameters,
                            schedule_id=schedule_id
                        )

                        # Update next run time
                        next_run = self._calculate_next_run(schedule)
                        schedule.next_run = next_run.isoformat()

                        # Save updated schedule
                        self._save_scheduled_reports()

                # Sleep for a minute
                await asyncio.sleep(60)
            except Exception as e:
                logger.error(f"Error in scheduler loop: {str(e)}")
                await asyncio.sleep(60)  # Sleep and retry

    def _calculate_next_run(self, schedule: ReportSchedule) -> datetime:
        """
        Calculate the next run time for a scheduled report.
        """
        now = utcnow()  # Use timezone-aware UTC now

        if schedule.frequency == "daily":
            return now + timedelta(days=1)
        elif schedule.frequency == "weekly":
            return now + timedelta(days=7)
        elif schedule.frequency == "monthly":
            # Approximately a month
            return now + timedelta(days=30)
        else:
            # Default to daily
            return now + timedelta(days=1)

    def _load_scheduled_reports(self) -> Dict[str, ReportSchedule]:
        """
        Load scheduled reports from storage.
        """
        try:
            schedules_file = self.reports_dir / "schedules.json"

            if schedules_file.exists():
                with open(schedules_file, "r") as f:
                    schedules_data = json.load(f)

                # Convert to ReportSchedule objects
                schedules = {}
                for schedule_id, data in schedules_data.items():
                    schedules[schedule_id] = ReportSchedule(**data)

                return schedules

            return {}
        except Exception as e:
            logger.error(f"Error loading scheduled reports: {str(e)}")
            return {}

    def _save_scheduled_reports(self):
        """
        Save scheduled reports to storage.
        """
        try:
            schedules_file = self.reports_dir / "schedules.json"

            # Convert to serializable dict
            schedules_data = {
                schedule_id: schedule.dict()
                for schedule_id, schedule in self.scheduled_reports.items()
            }

            with open(schedules_file, "w") as f:
                json.dump(schedules_data, f)
        except Exception as e:
            logger.error(f"Error saving scheduled reports: {str(e)}")

    def _load_report_templates(self) -> Dict[str, ReportTemplate]:
        """
        Load report templates from storage.
        """
        try:
            templates_file = self.reports_dir / "templates.json"

            if templates_file.exists():
                with open(templates_file, "r") as f:
                    templates_data = json.load(f)

                # Convert to ReportTemplate objects
                templates = {}
                for template_id, data in templates_data.items():
                    templates[template_id] = ReportTemplate(**data)

                return templates

            # If no templates exist, create default templates
            return self._create_default_templates()
        except Exception as e:
            logger.error(f"Error loading report templates: {str(e)}")
            return self._create_default_templates()

    def _create_default_templates(self) -> Dict[str, ReportTemplate]:
        """
        Create default report templates.
        """
        templates = {}

        # Test Summary Report
        templates["test_summary"] = ReportTemplate(
            id="test_summary",
            name="Test Summary Report",
            description="Summary of test results for a specified time period",
            type=ReportType.TEST_SUMMARY,
            parameters=[
                {"name": "days", "type": "integer", "default": 30, "description": "Number of days to analyze"},
                {"name": "environment", "type": "string", "default": None, "description": "Environment to filter by"},
                {"name": "format", "type": "string", "default": "html", "description": "Report format (html, pdf, csv)"}
            ],
            created_at=utcnow_iso(),  # Use timezone-aware UTC ISO string
            updated_at=utcnow_iso()  # Use timezone-aware UTC ISO string
        )

        # Flaky Tests Report
        templates["flaky_tests"] = ReportTemplate(
            id="flaky_tests",
            name="Flaky Tests Report",
            description="Analysis of flaky tests with inconsistent results",
            type=ReportType.FLAKY_TESTS,
            parameters=[
                {"name": "days", "type": "integer", "default": 30, "description": "Number of days to analyze"},
                {"name": "environment", "type": "string", "default": None, "description": "Environment to filter by"},
                {"name": "threshold", "type": "float", "default": 0.1, "description": "Flakiness threshold (0.0-1.0)"},
                {"name": "limit", "type": "integer", "default": 20,
                 "description": "Maximum number of tests to include"},
                {"name": "format", "type": "string", "default": "html", "description": "Report format (html, pdf, csv)"}
            ],
            created_at=utcnow_iso(),  # Use timezone-aware UTC ISO string
            updated_at=utcnow_iso()  # Use timezone-aware UTC ISO string
        )

        # Performance Report
        templates["performance"] = ReportTemplate(
            id="performance",
            name="Test Performance Report",
            description="Analysis of test performance and duration trends",
            type=ReportType.PERFORMANCE,
            parameters=[
                {"name": "days", "type": "integer", "default": 30, "description": "Number of days to analyze"},
                {"name": "environment", "type": "string", "default": None, "description": "Environment to filter by"},
                {"name": "feature", "type": "string", "default": None, "description": "Feature to filter by"},
                {"name": "format", "type": "string", "default": "html", "description": "Report format (html, pdf, csv)"}
            ],
            created_at=utcnow_iso(),  # Use timezone-aware UTC ISO string
            updated_at=utcnow_iso()  # Use timezone-aware UTC ISO string
        )

        # Comprehensive Report
        templates["comprehensive"] = ReportTemplate(
            id="comprehensive",
            name="Comprehensive Test Analysis",
            description="Complete analysis including trends, flaky tests, and performance",
            type=ReportType.COMPREHENSIVE,
            parameters=[
                {"name": "days", "type": "integer", "default": 30, "description": "Number of days to analyze"},
                {"name": "environment", "type": "string", "default": None, "description": "Environment to filter by"},
                {"name": "format", "type": "string", "default": "html", "description": "Report format (html, pdf, csv)"}
            ],
            created_at=utcnow_iso(),  # Use timezone-aware UTC ISO string
            updated_at=utcnow_iso()  # Use timezone-aware UTC ISO string
        )

        # Save templates
        self._save_report_templates(templates)

        return templates

    def _save_report_templates(self, templates: Dict[str, ReportTemplate]):
        """
        Save report templates to storage.
        """
        try:
            templates_file = self.reports_dir / "templates.json"

            # Convert to serializable dict
            templates_data = {
                template_id: template.dict()
                for template_id, template in templates.items()
            }

            with open(templates_file, "w") as f:
                json.dump(templates_data, f)
        except Exception as e:
            logger.error(f"Error saving report templates: {str(e)}")

    def _load_reports(self) -> Dict[str, Report]:
        """
        Load generated reports from storage.
        """
        try:
            reports_file = self.reports_dir / "reports.json"

            if reports_file.exists():
                with open(reports_file, "r") as f:
                    reports_data = json.load(f)

                # Convert to Report objects
                reports = {}
                for report_id, data in reports_data.items():
                    reports[report_id] = Report(**data)

                return reports

            return {}
        except Exception as e:
            logger.error(f"Error loading reports: {str(e)}")
            return {}

    def _save_reports(self, reports: Dict[str, Report]):
        """
        Save generated reports to storage.
        """
        try:
            reports_file = self.reports_dir / "reports.json"

            # Convert to serializable dict
            reports_data = {
                report_id: report.dict()
                for report_id, report in reports.items()
            }

            with open(reports_file, "w") as f:
                json.dump(reports_data, f)
        except Exception as e:
            logger.error(f"Error saving reports: {str(e)}")

    def _save_report_file(self, report_id: str, content: Union[str, bytes], format: str):
        """
        Save the generated report file.
        """
        try:
            # Create directory for this report
            report_dir = self.reports_dir / report_id
            report_dir.mkdir(exist_ok=True)

            # Determine filename and write mode
            filename = f"report.{format.lower()}"
            mode = "wb" if isinstance(content, bytes) else "w"

            # Write report file
            with open(report_dir / filename, mode) as f:
                f.write(content)

            return str(report_dir / filename)
        except Exception as e:
            logger.error(f"Error saving report file: {str(e)}")
            return None

    async def get_report_templates(self) -> List[ReportTemplate]:
        """
        Get available report templates.
        """
        templates = self._load_report_templates()
        return list(templates.values())

    async def get_report_template(self, template_id: str) -> Optional[ReportTemplate]:
        """
        Get a specific report template.
        """
        templates = self._load_report_templates()
        return templates.get(template_id)

    async def create_report_template(self, template: ReportTemplate) -> ReportTemplate:
        """
        Create a new report template.
        """
        templates = self._load_report_templates()

        # Generate ID if not provided
        if not template.id:
            template.id = str(uuid.uuid4())

        # Set timestamps
        template.created_at = utcnow_iso()  # Use timezone-aware UTC ISO string
        template.updated_at = utcnow_iso()  # Use timezone-aware UTC ISO string

        # Save template
        templates[template.id] = template
        self._save_report_templates(templates)

        return template

    async def update_report_template(self, template_id: str, template: ReportTemplate) -> Optional[ReportTemplate]:
        """
        Update an existing report template.
        """
        templates = self._load_report_templates()

        if template_id not in templates:
            return None

        # Update template with new values
        template.id = template_id  # Ensure ID doesn't change
        template.created_at = templates[template_id].created_at  # Preserve creation time
        template.updated_at = utcnow_iso()  # Use timezone-aware UTC ISO string

        # Save template
        templates[template_id] = template
        self._save_report_templates(templates)

        return template

    async def delete_report_template(self, template_id: str) -> bool:
        """
        Delete a report template.
        """
        templates = self._load_report_templates()

        if template_id not in templates:
            return False

        # Remove template
        del templates[template_id]
        self._save_report_templates(templates)

        return True

    async def get_scheduled_reports(self) -> List[ReportSchedule]:
        """
        Get scheduled reports.
        """
        return list(self.scheduled_reports.values())

    async def get_scheduled_report(self, schedule_id: str) -> Optional[ReportSchedule]:
        """
        Get a specific scheduled report.
        """
        return self.scheduled_reports.get(schedule_id)

    async def schedule_report(self, schedule: ReportSchedule) -> ReportSchedule:
        """
        Schedule a report for periodic generation.
        """
        # Generate ID if not provided
        if not schedule.id:
            schedule.id = str(uuid.uuid4())

        # Calculate next run time
        if not schedule.next_run:
            now = utcnow()  # Use timezone-aware UTC now
            schedule.next_run = now.isoformat()

        # Save schedule
        self.scheduled_reports[schedule.id] = schedule
        self._save_scheduled_reports()

        return schedule

    async def update_schedule(self, schedule_id: str, schedule: ReportSchedule) -> Optional[ReportSchedule]:
        """
        Update an existing report schedule.
        """
        if schedule_id not in self.scheduled_reports:
            return None

        # Update schedule with new values
        schedule.id = schedule_id  # Ensure ID doesn't change

        # Save schedule
        self.scheduled_reports[schedule_id] = schedule
        self._save_scheduled_reports()

        return schedule

    async def delete_schedule(self, schedule_id: str) -> bool:
        """
        Delete a report schedule.
        """
        if schedule_id not in self.scheduled_reports:
            return False

        # Remove schedule
        del self.scheduled_reports[schedule_id]
        self._save_scheduled_reports()

        return True

    async def get_reports(self, limit: int = 50, offset: int = 0) -> List[Report]:
        """
        Get generated reports.
        """
        reports = self._load_reports()

        # Sort by creation time (descending)
        sorted_reports = sorted(
            reports.values(),
            key=lambda r: r.created_at,
            reverse=True
        )

        # Apply pagination
        paged_reports = sorted_reports[offset:offset + limit]

        return paged_reports

    async def get_report(self, report_id: str) -> Optional[Report]:
        """
        Get a specific generated report.
        """
        reports = self._load_reports()
        return reports.get(report_id)

    async def generate_report(
            self,
            template_id: str,
            parameters: Dict[str, Any],
            schedule_id: Optional[str] = None
    ) -> Report:
        """
        Generate a report based on a template.
        """
        # Load templates
        templates = self._load_report_templates()

        if template_id not in templates:
            raise ValueError(f"Template {template_id} not found")

        template = templates[template_id]

        # Create report object
        report_id = str(uuid.uuid4())
        now = utcnow()  # Use timezone-aware UTC now

        report = Report(
            id=report_id,
            name=f"{template.name} - {now.strftime('%Y-%m-%d %H:%M')}",
            template_id=template_id,
            parameters=parameters,
            schedule_id=schedule_id,
            status=ReportStatus.RUNNING,
            created_at=now.isoformat(),
            completed_at=None,
            file_path=None,
            format=parameters.get("format", "html").lower()
        )

        # Save initial report state
        reports = self._load_reports()
        reports[report_id] = report
        self._save_reports(reports)

        try:
            # Generate content based on template type
            content = await self._generate_report_content(template, parameters)

            # Save report file
            file_path = self._save_report_file(
                report_id=report_id,
                content=content,
                format=report.format
            )

            # Update report status
            report.status = ReportStatus.COMPLETED
            report.completed_at = utcnow_iso()  # Use timezone-aware UTC ISO string
            report.file_path = file_path

            # Save updated report
            reports[report_id] = report
            self._save_reports(reports)

            # TODO: Deliver report to subscribers

            return report
        except Exception as e:
            logger.error(f"Error generating report: {str(e)}")

            # Update report status
            report.status = ReportStatus.FAILED
            report.error = str(e)
            report.completed_at = utcnow_iso()  # Use timezone-aware UTC ISO string

            # Save updated report
            reports[report_id] = report
            self._save_reports(reports)

            return report