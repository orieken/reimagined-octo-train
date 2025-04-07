# app/services/reporting.py
import logging
import asyncio
from typing import List, Dict, Any, Optional, Union
from datetime import datetime, timedelta
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
from app.models.api import (
    ReportTemplate, ReportSchedule, Report, ReportFormat,
    ReportStatus, ReportType, ReportSubscription
)

logger = logging.getLogger(__name__)


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
                now = datetime.now()

                for schedule_id, schedule in self.scheduled_reports.items():
                    next_run = datetime.fromisoformat(schedule.next_run)

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
        now = datetime.now()

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
            created_at=datetime.now().isoformat(),
            updated_at=datetime.now().isoformat()
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
            created_at=datetime.now().isoformat(),
            updated_at=datetime.now().isoformat()
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
            created_at=datetime.now().isoformat(),
            updated_at=datetime.now().isoformat()
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
            created_at=datetime.now().isoformat(),
            updated_at=datetime.now().isoformat()
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
        now = datetime.now().isoformat()
        template.created_at = now
        template.updated_at = now

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
        template.updated_at = datetime.now().isoformat()

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
            now = datetime.now()
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
        report = Report(
            id=report_id,
            name=f"{template.name} - {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            template_id=template_id,
            parameters=parameters,
            schedule_id=schedule_id,
            status=ReportStatus.RUNNING,
            created_at=datetime.now().isoformat(),
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
            report.completed_at = datetime.now().isoformat()
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
            report.completed_at = datetime.now().isoformat()

            # Save updated report
            reports[report_id] = report
            self._save_reports(reports)

            return report

    async def _generate_report_content(
            self,
            template: ReportTemplate,
            parameters: Dict[str, Any]
    ) -> Union[str, bytes]:
        """
        Generate report content based on template type.
        """
        # Extract common parameters
        days = parameters.get("days", 30)
        environment = parameters.get("environment")
        format = parameters.get("format", "html").lower()

        # Generate content based on template type
        if template.type == ReportType.TEST_SUMMARY:
            return await self._generate_test_summary(days, environment, format)
        elif template.type == ReportType.FLAKY_TESTS:
            threshold = parameters.get("threshold", 0.1)
            limit = parameters.get("limit", 20)
            return await self._generate_flaky_tests_report(days, environment, threshold, limit, format)
        elif template.type == ReportType.PERFORMANCE:
            feature = parameters.get("feature")
            return await self._generate_performance_report(days, environment, feature, format)
        elif template.type == ReportType.COMPREHENSIVE:
            return await self._generate_comprehensive_report(days, environment, format)
        else:
            raise ValueError(f"Unsupported report type: {template.type}")

    async def _generate_test_summary(
            self,
            days: int,
            environment: Optional[str],
            format: str
    ) -> Union[str, bytes]:
        """
        Generate a test summary report.
        """
        # Get trends data
        trends = await self.analytics_service.analyze_trends(days, environment)

        # Generate report based on format
        if format == "html":
            return self._generate_html_test_summary(trends)
        elif format == "pdf":
            return self._generate_pdf_test_summary(trends)
        elif format == "csv":
            return self._generate_csv_test_summary(trends)
        else:
            raise ValueError(f"Unsupported format: {format}")

    def _generate_html_test_summary(self, trends) -> str:
        """
        Generate HTML test summary report.
        """
        # Create dataframe from trends data
        df = pd.DataFrame([{
            "Date": point.timestamp.split("T")[0],
            "Total Tests": point.total_tests,
            "Passed Tests": point.passed_tests,
            "Failed Tests": point.failed_tests,
            "Pass Rate (%)": round(point.pass_rate, 2),
            "Avg. Duration (ms)": round(point.avg_duration, 2)
        } for point in trends.points])

        # Generate trends chart
        if not df.empty:
            fig, ax = plt.subplots(figsize=(10, 6))
            ax.plot(df["Date"], df["Pass Rate (%)"], marker="o", label="Pass Rate (%)")
            ax.set_xlabel("Date")
            ax.set_ylabel("Pass Rate (%)")
            ax.set_title(f"Test Pass Rate Trend (Last {trends.days_analyzed} Days)")
            ax.grid(True)

            # Set y-axis range to emphasize changes
            y_min = max(0, df["Pass Rate (%)"].min() - 5)
            y_max = min(100, df["Pass Rate (%)"].max() + 5)
            ax.set_ylim(y_min, y_max)

            # Rotate x-axis labels
            plt.xticks(rotation=45)

            # Convert plot to base64 image
            buffer = io.BytesIO()
            plt.savefig(buffer, format="png")
            buffer.seek(0)
            plot_data = base64.b64encode(buffer.getvalue()).decode()
            plt.close()

            # Generate HTML
            html = f"""
            <html>
            <head>
                <title>Test Summary Report</title>
                <style>
                    body {{ font-family: Arial, sans-serif; margin: 20px; }}
                    h1 {{ color: #333; }}
                    table {{ border-collapse: collapse; width: 100%; margin-top: 20px; }}
                    th, td {{ padding: 8px; text-align: left; border-bottom: 1px solid #ddd; }}
                    th {{ background-color: #f2f2f2; }}
                    .chart {{ margin-top: 30px; }}
                    .summary {{ margin-top: 30px; }}
                </style>
            </head>
            <body>
                <h1>Test Summary Report</h1>
                <p>Environment: {trends.environment or "All"}</p>
                <p>Period: Last {trends.days_analyzed} days</p>

                <div class="summary">
                    <h2>Summary</h2>
                    <p>Total Reports: {len(trends.points)}</p>
                    <p>Average Pass Rate: {df["Pass Rate (%)"].mean():.2f}%</p>
                    <p>Average Test Count: {df["Total Tests"].mean():.2f}</p>
                </div>

                <div class="chart">
                    <h2>Pass Rate Trend</h2>
                    <img src="data:image/png;base64,{plot_data}" width="100%">
                </div>

                <h2>Detailed Results</h2>
                <table>
                    <tr>
                        <th>Date</th>
                        <th>Total Tests</th>
                        <th>Passed Tests</th>
                        <th>Failed Tests</th>
                        <th>Pass Rate (%)</th>
                        <th>Avg. Duration (ms)</th>
                    </tr>
                    {"".join(f"<tr><td>{row['Date']}</td><td>{row['Total Tests']}</td><td>{row['Passed Tests']}</td><td>{row['Failed Tests']}</td><td>{row['Pass Rate (%)']:.2f}</td><td>{row['Avg. Duration (ms)']:.2f}</td></tr>" for _, row in df.iterrows())}
                </table>
            </body>
            </html>
            """
        else:
            html = f"""
            <html>
            <head>
                <title>Test Summary Report</title>
                <style>
                    body {{ font-family: Arial, sans-serif; margin: 20px; }}
                    h1 {{ color: #333; }}
                </style>
            </head>
            <body>
                <h1>Test Summary Report</h1>
                <p>Environment: {trends.environment or "All"}</p>
                <p>Period: Last {trends.days_analyzed} days</p>
                <p>No test data available for the specified period.</p>
            </body>
            </html>
            """

        return html

    def _generate_pdf_test_summary(self, trends) -> bytes:
        """
        Generate PDF test summary report.
        """
        # For simplicity, we'll convert HTML to PDF
        # In a real implementation, you would use a library like WeasyPrint or ReportLab
        # This placeholder just returns the HTML as bytes
        html = self._generate_html_test_summary(trends)
        return html.encode("utf-8")

    def _generate_csv_test_summary(self, trends) -> str:
        """
        Generate CSV test summary report.
        """
        # Create dataframe from trends data
        df = pd.DataFrame([{
            "Date": point.timestamp.split("T")[0],
            "Total Tests": point.total_tests,
            "Passed Tests": point.passed_tests,
            "Failed Tests": point.failed_tests,
            "Pass Rate (%)": round(point.pass_rate, 2),
            "Avg. Duration (ms)": round(point.avg_duration, 2)
        } for point in trends.points])

        # Convert to CSV
        return df.to_csv(index=False)

    async def _generate_flaky_tests_report(
            self,
            days: int,
            environment: Optional[str],
            threshold: float,
            limit: int,
            format: str
    ) -> Union[str, bytes]:
        """
        Generate a flaky tests report.
        """
        # Get flaky tests data
        flaky_tests = await self.analytics_service.identify_flaky_tests(
            days=days,
            environment=environment,
            threshold=threshold,
            limit=limit
        )

        # Generate report based on format
        if format == "html":
            return self._generate_html_flaky_tests(flaky_tests, days, environment)
        elif format == "pdf":
            return self._generate_pdf_flaky_tests(flaky_tests, days, environment)
        elif format == "csv":
            return self._generate_csv_flaky_tests(flaky_tests)
        else:
            raise ValueError(f"Unsupported format: {format}")

    def _generate_html_flaky_tests(self, flaky_tests, days, environment) -> str:
        """
        Generate HTML flaky tests report.
        """
        # Create dataframe from flaky tests data
        df = pd.DataFrame([{
            "Test Name": test.name,
            "Feature": test.feature,
            "Flakiness Score": round(test.flakiness_score, 2),
            "Total Runs": test.total_runs,
            "Pass Count": test.pass_count,
            "Fail Count": test.fail_count,
            "Pass Rate (%)": round((test.pass_count / test.total_runs) * 100, 2) if test.total_runs > 0 else 0
        } for test in flaky_tests])

        # Generate HTML
        if not df.empty:
            html = f"""
            <html>
            <head>
                <title>Flaky Tests Report</title>
                <style>
                    body {{ font-family: Arial, sans-serif; margin: 20px; }}
                    h1 {{ color: #333; }}
                    table {{ border-collapse: collapse; width: 100%; margin-top: 20px; }}
                    th, td {{ padding: 8px; text-align: left; border-bottom: 1px solid #ddd; }}
                    th {{ background-color: #f2f2f2; }}
                    .summary {{ margin-top: 30px; }}
                    .high {{ background-color: #ffcccc; }}
                    .medium {{ background-color: #ffffcc; }}
                    .low {{ background-color: #e6ffe6; }}
                </style>
            </head>
            <body>
                <h1>Flaky Tests Report</h1>
                <p>Environment: {environment or "All"}</p>
                <p>Period: Last {days} days</p>

                <div class="summary">
                    <h2>Summary</h2>
                    <p>Total Flaky Tests: {len(flaky_tests)}</p>
                    <p>Average Flakiness Score: {df["Flakiness Score"].mean():.2f}</p>
                </div>

                <h2>Flaky Tests</h2>
                <table>
                    <tr>
                        <th>Test Name</th>
                        <th>Feature</th>
                        <th>Flakiness Score</th>
                        <th>Total Runs</th>
                        <th>Passes</th>
                        <th>Failures</th>
                        <th>Pass Rate (%)</th>
                    </tr>
                    {"".join(f"<tr class=\"{'high' if row['Flakiness Score'] > 0.7 else 'medium' if row['Flakiness Score'] > 0.4 else 'low'}\"><td>{row['Test Name']}</td><td>{row['Feature']}</td><td>{row['Flakiness Score']:.2f}</td><td>{row['Total Runs']}</td><td>{row['Pass Count']}</td><td>{row['Fail Count']}</td><td>{row['Pass Rate (%)']:.2f}</td></tr>" for _, row in df.iterrows())}
                </table>
            </body>
            </html>
            """
        else:
            html = f"""
            <html>
            <head>
                <title>Flaky Tests Report</title>
                <style>
                    body {{ font-family: Arial, sans-serif; margin: 20px; }}
                    h1 {{ color: #333; }}
                </style>
            </head>
            <body>
                <h1>Flaky Tests Report</h1>
                <p>Environment: {environment or "All"}</p>
                <p>Period: Last {days} days</p>
                <p>No flaky tests detected for the specified period.</p>
            </body>
            </html>
            """

        return html

    def _generate_pdf_flaky_tests(self, flaky_tests, days, environment) -> bytes:
        """
        Generate PDF flaky tests report.
        """
        # For simplicity, we'll convert HTML to PDF
        html = self._generate_html_flaky_tests(flaky_tests, days, environment)
        return html.encode("utf-8")

    def _generate_csv_flaky_tests(self, flaky_tests) -> str:
        """
        Generate CSV flaky tests report.
        """
        # Create dataframe from flaky tests data
        df = pd.DataFrame([{
            "Test Name": test.name,
            "Feature": test.feature,
            "Flakiness Score": round(test.flakiness_score, 2),
            "Total Runs": test.total_runs,
            "Pass Count": test.pass_count,
            "Fail Count": test.fail_count,
            "Pass Rate (%)": round((test.pass_count / test.total_runs) * 100, 2) if test.total_runs > 0 else 0
        } for test in flaky_tests])

        # Convert to CSV
        return df.to_csv(index=False)

    async def _generate_performance_report(
            self,
            days: int,
            environment: Optional[str],
            feature: Optional[str],
            format: str
    ) -> Union[str, bytes]:
        """
        Generate a performance report.
        """
        # Get performance metrics
        performance = await self.analytics_service.analyze_performance(days, environment, feature)

        # Generate report based on format
        if format == "html":
            return self._generate_html_performance(performance)
        elif format == "pdf":
            return self._generate_pdf_performance(performance)
        elif format == "csv":
            return self._generate_csv_performance(performance)
        else:
            raise ValueError(f"Unsupported format: {format}")

    def _generate_html_performance(self, performance) -> str:
        """
        Generate HTML performance report.
        """
        # Create dataframe from performance data
        df = pd.DataFrame([{
            "Test Name": test.name,
            "Feature": test.feature,
            "Avg. Duration (ms)": round(test.avg_duration, 2),
            "Min Duration (ms)": round(test.min_duration, 2),
            "Max Duration (ms)": round(test.max_duration, 2),
            "Trend (%)": round(test.trend_percentage, 2),
            "Run Count": test.run_count
        } for test in performance.tests])

        # Generate top 10 slowest tests chart
        if len(df) > 0:
            top_10 = df.nlargest(min(10, len(df)), "Avg. Duration (ms)")

            fig, ax = plt.subplots(figsize=(10, 6))
            ax.bar(top_10["Test Name"], top_10["Avg. Duration (ms)"])
            ax.set_xlabel("Test Name")
            ax.set_ylabel("Avg. Duration (ms)")
            ax.set_title("Top 10 Slowest Tests")
            plt.xticks(rotation=45, ha="right")
            plt.tight_layout()

            # Convert plot to base64 image
            buffer = io.BytesIO()
            plt.savefig(buffer, format="png")
            buffer.seek(0)
            plot_data = base64.b64encode(buffer.getvalue()).decode()
            plt.close()

            # Generate HTML
            html = f"""
            <html>
            <head>
                <title>Test Performance Report</title>
                <style>
                    body {{ font-family: Arial, sans-serif; margin: 20px; }}
                    h1 {{ color: #333; }}
                    table {{ border-collapse: collapse; width: 100%; margin-top: 20px; }}
                    th, td {{ padding: 8px; text-align: left; border-bottom: 1px solid #ddd; }}
                    th {{ background-color: #f2f2f2; }}
                    .chart {{ margin-top: 30px; }}
                    .summary {{ margin-top: 30px; }}
                    .trend-positive {{ color: red; }}
                    .trend-negative {{ color: green; }}
                    .trend-neutral {{ color: gray; }}
                </style>
            </head>
            <body>
                <h1>Test Performance Report</h1>
                <p>Environment: {performance.environment or "All"}</p>
                <p>Feature: {performance.feature or "All"}</p>
                <p>Period: Last {performance.days_analyzed} days</p>

                <div class="summary">
                    <h2>Summary</h2>
                    <p>Total Tests: {len(performance.tests)}</p>
                    <p>Overall Avg. Duration: {performance.overall_avg_duration:.2f} ms</p>
                </div>

                <div class="chart">
                    <h2>Top 10 Slowest Tests</h2>
                    <img src="data:image/png;base64,{plot_data}" width="100%">
                </div>

                <h2>Test Performance Details</h2>
                <table>
                    <tr>
                        <th>Test Name</th>
                        <th>Feature</th>
                        <th>Avg. Duration (ms)</th>
                        <th>Min Duration (ms)</th>
                        <th>Max Duration (ms)</th>
                        <th>Trend</th>
                        <th>Run Count</th>
                    </tr>
                    {"".join(f"<tr><td>{row['Test Name']}</td><td>{row['Feature']}</td><td>{row['Avg. Duration (ms)']:.2f}</td><td>{row['Min Duration (ms)']:.2f}</td><td>{row['Max Duration (ms)']:.2f}</td><td class=\"{'trend-positive' if row['Trend (%)'] > 1 else 'trend-negative' if row['Trend (%)'] < -1 else 'trend-neutral'}\">{row['Trend (%)']:.2f}%</td><td>{row['Run Count']}</td></tr>" for _, row in df.iterrows())}
                </table>
            </body>
            </html>
            """
        else:
            html = f"""
            <html>
            <head>
                <title>Test Performance Report</title>
                <style>
                    body {{ font-family: Arial, sans-serif; margin: 20px; }}
                    h1 {{ color: #333; }}
                </style>
            </head>
            <body>
                <h1>Test Performance Report</h1>
                <p>Environment: {performance.environment or "All"}</p>
                <p>Feature: {performance.feature or "All"}</p>
                <p>Period: Last {performance.days_analyzed} days</p>
                <p>No performance data available for the specified period.</p>
            </body>
            </html>
            """

        return html

    def _generate_pdf_performance(self, performance) -> bytes:
        """
        Generate PDF performance report.
        """
        # For simplicity, we'll convert HTML to PDF
        html = self._generate_html_performance(performance)
        return html.encode("utf-8")

    def _generate_csv_performance(self, performance) -> str:
        """
        Generate CSV performance report.
        """
        # Create dataframe from performance data
        df = pd.DataFrame([{
            "Test Name": test.name,
            "Feature": test.feature,
            "Avg. Duration (ms)": round(test.avg_duration, 2),
            "Min Duration (ms)": round(test.min_duration, 2),
            "Max Duration (ms)": round(test.max_duration, 2),
            "Trend (%)": round(test.trend_percentage, 2),
            "Run Count": test.run_count
        } for test in performance.tests])

        # Convert to CSV
        return df.to_csv(index=False)

    async def _generate_comprehensive_report(
            self,
            days: int,
            environment: Optional[str],
            format: str
    ) -> Union[str, bytes]:
        """
        Generate a comprehensive report including trends, flaky tests, and performance.
        """
        # Get all required data
        summary = await self.analytics_service.generate_summary(days, environment)

        # Generate report based on format
        if format == "html":
            return self._generate_html_comprehensive(summary)
        elif format == "pdf":
            return self._generate_pdf_comprehensive(summary)
        elif format == "csv":
            return self._generate_csv_comprehensive(summary)
        else:
            raise ValueError(f"Unsupported format: {format}")

    def _generate_html_comprehensive(self, summary) -> str:
        """
        Generate HTML comprehensive report.
        """
        # Generate trends chart
        if len(summary.trends.points) > 0:
            trends_df = pd.DataFrame([{
                "Date": point.timestamp.split("T")[0],
                "Pass Rate (%)": round(point.pass_rate, 2)
            } for point in summary.trends.points])

            fig, ax = plt.subplots(figsize=(10, 4))
            ax.plot(trends_df["Date"], trends_df["Pass Rate (%)"], marker="o")
            ax.set_xlabel("Date")
            ax.set_ylabel("Pass Rate (%)")
            ax.set_title("Test Pass Rate Trend")
            plt.xticks(rotation=45, ha="right")
            plt.tight_layout()

            # Convert plot to base64 image
            buffer = io.BytesIO()
            plt.savefig(buffer, format="png")
            buffer.seek(0)
            trends_plot = base64.b64encode(buffer.getvalue()).decode()
            plt.close()
        else:
            trends_plot = None

        # Generate top flaky tests chart
        if len(summary.flaky_tests) > 0:
            flaky_df = pd.DataFrame([{
                "Test Name": test.name,
                "Flakiness Score": round(test.flakiness_score, 2)
            } for test in summary.flaky_tests[:5]])  # Top 5

            fig, ax = plt.subplots(figsize=(10, 4))
            ax.bar(flaky_df["Test Name"], flaky_df["Flakiness Score"])
            ax.set_xlabel("Test Name")
            ax.set_ylabel("Flakiness Score")
            ax.set_title("Top 5 Flaky Tests")
            plt.xticks(rotation=45, ha="right")
            plt.tight_layout()

            # Convert plot to base64 image
            buffer = io.BytesIO()
            plt.savefig(buffer, format="png")
            buffer.seek(0)
            flaky_plot = base64.b64encode(buffer.getvalue()).decode()
            plt.close()
        else:
            flaky_plot = None

        # Generate top slowest tests chart
        if len(summary.performance.tests) > 0:
            perf_df = pd.DataFrame([{
                "Test Name": test.name,
                "Avg. Duration (ms)": round(test.avg_duration, 2)
            } for test in summary.performance.tests[:5]])  # Top 5

            fig, ax = plt.subplots(figsize=(10, 4))
            ax.bar(perf_df["Test Name"], perf_df["Avg. Duration (ms)"])
            ax.set_xlabel("Test Name")
            ax.set_ylabel("Avg. Duration (ms)")
            ax.set_title("Top 5 Slowest Tests")
            plt.xticks(rotation=45, ha="right")
            plt.tight_layout()

            # Convert plot to base64 image
            buffer = io.BytesIO()
            plt.savefig(buffer, format="png")
            buffer.seek(0)
            perf_plot = base64.b64encode(buffer.getvalue()).decode()
            plt.close()
        else:
            perf_plot = None

        # Generate correlations table
        correlations_table = ""
        if len(summary.correlations) > 0:
            correlations_table = """
            <h2>Top Failure Correlations</h2>
            <table>
                <tr>
                    <th>Test 1</th>
                    <th>Test 2</th>
                    <th>Correlation Score</th>
                    <th>Co-Failure Count</th>
                </tr>
            """

            for corr in summary.correlations[:5]:  # Top 5
                correlations_table += f"""
                <tr>
                    <td>{corr.test1_name} ({corr.test1_feature})</td>
                    <td>{corr.test2_name} ({corr.test2_feature})</td>
                    <td>{corr.correlation_score:.2f}</td>
                    <td>{corr.co_failure_count}</td>
                </tr>
                """

            correlations_table += "</table>"

        # Generate HTML
        html = f"""
        <html>
        <head>
            <title>Comprehensive Test Analysis</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                h1 {{ color: #333; }}
                h2 {{ color: #555; margin-top: 30px; }}
                table {{ border-collapse: collapse; width: 100%; margin-top: 10px; }}
                th, td {{ padding: 8px; text-align: left; border-bottom: 1px solid #ddd; }}
                th {{ background-color: #f2f2f2; }}
                .section {{ margin-top: 40px; }}
                .chart {{ margin-top: 20px; }}
                .trend-positive {{ color: red; }}
                .trend-negative {{ color: green; }}
                .trend-neutral {{ color: gray; }}
            </style>
        </head>
        <body>
            <h1>Comprehensive Test Analysis</h1>
            <p>Environment: {summary.environment or "All"}</p>
            <p>Period: Last {summary.days_analyzed} days</p>
            <p>Generated: {summary.timestamp}</p>

            <div class="section">
                <h2>Test Result Trends</h2>
                {f'<div class="chart"><img src="data:image/png;base64,{trends_plot}" width="100%"></div>' if trends_plot else '<p>No trend data available.</p>'}

                <h3>Recent Results</h3>
                <table>
                    <tr>
                        <th>Date</th>
                        <th>Total Tests</th>
                        <th>Passed</th>
                        <th>Failed</th>
                        <th>Pass Rate (%)</th>
                    </tr>
                    {"".join(f"<tr><td>{point.timestamp.split('T')[0]}</td><td>{point.total_tests}</td><td>{point.passed_tests}</td><td>{point.failed_tests}</td><td>{point.pass_rate:.2f}</td></tr>" for point in summary.trends.points[:5])}
                </table>
            </div>

            <div class="section">
                <h2>Flaky Tests</h2>
                {f'<div class="chart"><img src="data:image/png;base64,{flaky_plot}" width="100%"></div>' if flaky_plot else '<p>No flaky tests detected.</p>'}

                {f'''
                <table>
                    <tr>
                        <th>Test Name</th>
                        <th>Feature</th>
                        <th>Flakiness Score</th>
                        <th>Pass/Fail Ratio</th>
                    </tr>
                    {"".join(f"<tr><td>{test.name}</td><td>{test.feature}</td><td>{test.flakiness_score:.2f}</td><td>{test.pass_count}/{test.fail_count}</td></tr>" for test in summary.flaky_tests[:5])}
                </table>
                ''' if len(summary.flaky_tests) > 0 else ''}
            </div>

            <div class="section">
                <h2>Performance Analysis</h2>
                {f'<div class="chart"><img src="data:image/png;base64,{perf_plot}" width="100%"></div>' if perf_plot else '<p>No performance data available.</p>'}

                {f'''
                <table>
                    <tr>
                        <th>Test Name</th>
                        <th>Feature</th>
                        <th>Avg. Duration (ms)</th>
                        <th>Trend</th>
                    </tr>
                    {"".join(f"<tr><td>{test.name}</td><td>{test.feature}</td><td>{test.avg_duration:.2f}</td><td class=\"{'trend-positive' if test.trend_percentage > 1 else 'trend-negative' if test.trend_percentage < -1 else 'trend-neutral'}\">{test.trend_percentage:.2f}%</td></tr>" for test in summary.performance.tests[:5])}
                </table>
                ''' if len(summary.performance.tests) > 0 else ''}
            </div>

            <div class="section">
                {correlations_table if correlations_table else '<h2>Failure Correlations</h2><p>No significant failure correlations detected.</p>'}
            </div>
        </body>
        </html>
        """

        return html

    def _generate_pdf_comprehensive(self, summary) -> bytes:
        """
        Generate PDF comprehensive report.
        """
        # For simplicity, we'll convert HTML to PDF
        html = self._generate_html_comprehensive(summary)
        return html.encode("utf-8")

    def _generate_csv_comprehensive(self, summary) -> str:
        """
        Generate CSV comprehensive report.
        """
        # Since a comprehensive report contains multiple sections,
        # we'll create a combined CSV with sections separated by headers

        # Trends section
        trends_df = pd.DataFrame([{
            "Date": point.timestamp.split("T")[0],
            "Total Tests": point.total_tests,
            "Passed Tests": point.passed_tests,
            "Failed Tests": point.failed_tests,
            "Pass Rate (%)": round(point.pass_rate, 2),
            "Avg. Duration (ms)": round(point.avg_duration, 2)
        } for point in summary.trends.points])

        # Flaky tests section
        flaky_df = pd.DataFrame([{
            "Test Name": test.name,
            "Feature": test.feature,
            "Flakiness Score": round(test.flakiness_score, 2),
            "Total Runs": test.total_runs,
            "Pass Count": test.pass_count,
            "Fail Count": test.fail_count
        } for test in summary.flaky_tests])

        # Performance section
        perf_df = pd.DataFrame([{
            "Test Name": test.name,
            "Feature": test.feature,
            "Avg. Duration (ms)": round(test.avg_duration, 2),
            "Min Duration (ms)": round(test.min_duration, 2),
            "Max Duration (ms)": round(test.max_duration, 2),
            "Trend (%)": round(test.trend_percentage, 2),
            "Run Count": test.run_count
        } for test in summary.performance.tests])

        # Correlations section
        corr_df = pd.DataFrame([{
            "Test 1": f"{corr.test1_name} ({corr.test1_feature})",
            "Test 2": f"{corr.test2_name} ({corr.test2_feature})",
            "Correlation Score": round(corr.correlation_score, 2),
            "Co-Failure Count": corr.co_failure_count,
            "Test 1 Failures": corr.test1_failure_count,
            "Test 2 Failures": corr.test2_failure_count
        } for corr in summary.correlations])

        # Combine all sections
        csv_parts = []

        # Metadata
        csv_parts.append(
            f"Comprehensive Test Analysis\nEnvironment: {summary.environment or 'All'}\nPeriod: Last {summary.days_analyzed} days\nGenerated: {summary.timestamp}\n\n")

        # Trends section
        csv_parts.append("SECTION: Test Result Trends\n")
        csv_parts.append(trends_df.to_csv(index=False))
        csv_parts.append("\n\n")

        # Flaky tests section
        csv_parts.append("SECTION: Flaky Tests\n")
        csv_parts.append(flaky_df.to_csv(index=False))
        csv_parts.append("\n\n")

        # Performance section
        csv_parts.append("SECTION: Performance Analysis\n")
        csv_parts.append(perf_df.to_csv(index=False))
        csv_parts.append("\n\n")

        # Correlations section
        csv_parts.append("SECTION: Failure Correlations\n")
        csv_parts.append(corr_df.to_csv(index=False))

        return "".join(csv_parts)