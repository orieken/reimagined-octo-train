# # app/models/api/reporting.py
# from pydantic import BaseModel, Field
# from typing import List, Dict, Any, Optional
# from enum import Enum
# from datetime import datetime
#
# # Enums
# class ReportFormat(str, Enum):
#     """Report output format"""
#     HTML = "html"
#     PDF = "pdf"
#     CSV = "csv"
#
# class ReportStatus(str, Enum):
#     """Report generation status"""
#     RUNNING = "RUNNING"
#     COMPLETED = "COMPLETED"
#     FAILED = "FAILED"
#
# class ReportType(str, Enum):
#     """Report template type"""
#     TEST_SUMMARY = "test_summary"
#     FLAKY_TESTS = "flaky_tests"
#     PERFORMANCE = "performance"
#     COMPREHENSIVE = "comprehensive"
#     CUSTOM = "custom"
#
# class ReportFrequency(str, Enum):
#     """Report schedule frequency"""
#     DAILY = "daily"
#     WEEKLY = "weekly"
#     MONTHLY = "monthly"
#
# # Parameter Schema
# class ParameterSchema(BaseModel):
#     """Definition of a report parameter"""
#     name: str
#     type: str
#     default: Any = None
#     description: Optional[str] = None
#
# # Template
# class ReportTemplate(BaseModel):
#     """Report template definition"""
#     id: Optional[str] = None
#     name: str
#     description: Optional[str] = None
#     type: ReportType
#     parameters: List[Dict[str, Any]] = []
#     created_at: Optional[str] = None
#     updated_at: Optional[str] = None
#
# # Schedule
# class ReportSchedule(BaseModel):
#     """Schedule for periodic report generation"""
#     id: Optional[str] = None
#     name: str
#     template_id: str
#     parameters: Dict[str, Any] = {}
#     frequency: ReportFrequency
#     next_run: Optional[str] = None
#     created_at: Optional[str] = None
#
# # Report
# class Report(BaseModel):
#     """Generated report"""
#     id: str
#     name: str
#     template_id: str
#     parameters: Dict[str, Any] = {}
#     schedule_id: Optional[str] = None
#     status: ReportStatus
#     created_at: str
#     completed_at: Optional[str] = None
#     file_path: Optional[str] = None
#     format: str
#     error: Optional[str] = None
#
# # Subscription
# class ReportSubscription(BaseModel):
#     """Subscription to report deliveries"""
#     id: Optional[str] = None
#     user_id: str
#     template_id: Optional[str] = None
#     schedule_id: Optional[str] = None
#     delivery_method: str  # "email", "slack", etc.
#     delivery_config: Dict[str, Any] = {}
#     created_at: Optional[str] = None
#
# # Request bodies
# class CreateReportRequest(BaseModel):
#     """Request to generate a report"""
#     template_id: str
#     parameters: Dict[str, Any] = {}
#
# class CreateScheduleRequest(BaseModel):
#     """Request to schedule a report"""
#     name: str
#     template_id: str
#     parameters: Dict[str, Any] = {}
#     frequency: ReportFrequency
#     next_run: Optional[str] = None
#
# class CreateSubscriptionRequest(BaseModel):
#     """Request to subscribe to report deliveries"""
#     user_id: str
#     template_id: Optional[str] = None
#     schedule_id: Optional[str] = None
#     delivery_method: str
#     delivery_config: Dict[str, Any] = {}
