# # app/workers/analytics_worker.py
# """
# Background worker for analytics tasks
# """
# import logging
# import asyncio
# import time
# from datetime import datetime, timedelta
# from typing import Dict, Any, List, Optional
# from sqlalchemy.orm import Session
#
# from app.database.session import get_db
# from app.models.database import HealthMetric
# from app.services.webhook_service import dispatch_event
# from app.services.notification import send_notification
#
# # Let's assume these functions exist in your analytics service
# # If they don't, you'll need to implement them separately
# from app.services.analytics_service import (
#     get_test_failure_metrics,
#     get_flaky_tests,
#     calculate_build_health_score
# )
#
# logger = logging.getLogger("friday.workers.analytics")
#
#
# class AnalyticsWorker:
#     """
#     Background worker for running analytics tasks periodically
#
#     This worker handles:
#     - Daily report generation
#     - Flaky test detection
#     - Build health monitoring
#     """
#
#     def __init__(self):
#         self.running = False
#         self.tasks = []
#
#     async def start(self):
#         """
#         Start the worker process
#         """
#         self.running = True
#         logger.info("Starting analytics worker")
#
#         # Schedule recurring tasks
#         self.tasks = [
#             asyncio.create_task(self._run_periodic(self.process_daily_reports, 86400)),  # Daily
#             asyncio.create_task(self._run_periodic(self.detect_flaky_tests, 43200)),  # Every 12 hours
#             asyncio.create_task(self._run_periodic(self.monitor_build_health, 3600)),  # Hourly
#         ]
#
#         try:
#             # Wait for all tasks to complete (they won't unless cancelled)
#             await asyncio.gather(*self.tasks)
#         except asyncio.CancelledError:
#             logger.info("Analytics worker tasks cancelled")
#         finally:
#             self.running = False
#
#     async def stop(self):
#         """
#         Stop all worker tasks
#         """
#         logger.info("Stopping analytics worker")
#         for task in self.tasks:
#             task.cancel()
#
#         # Wait for all tasks to be cancelled
#         await asyncio.gather(*self.tasks, return_exceptions=True)
#         self.tasks = []
#         self.running = False
#
#     async def _run_periodic(self, func, interval_seconds):
#         """
#         Run a function periodically
#
#         Args:
#             func: The function to run
#             interval_seconds: The interval in seconds
#         """
#         while self.running:
#             try:
#                 await func()
#             except Exception as e:
#                 logger.error(f"Error in periodic task {func.__name__}: {e}")
#
#             # Sleep until next interval
#             await asyncio.sleep(interval_seconds)
#
#     async def process_daily_reports(self):
#         """
#         Generate and send daily analytics reports
#         """
#         logger.info("Processing daily reports")
#
#         # Get database session
#         db = next(get_db())
#
#         try:
#             # Calculate metrics for last 24 hours
#             end_date = datetime.utcnow()
#             start_date = end_date - timedelta(days=1)
#
#             # This would need to be adjusted based on your actual project model
#             # Get all active projects (we'll use a dummy implementation for now)
#             try:
#                 projects = db.query(Project).filter(Project.is_active == True).all()
#             except:
#                 # Fallback to a dummy project if Project model doesn't exist
#                 logger.warning("Project model not found, using dummy project")
#                 projects = [type('obj', (object,), {'id': 1, 'name': 'Default Project', 'is_active': True})]
#
#             for project in projects:
#                 # Generate test failure metrics
#                 failure_metrics = get_test_failure_metrics(
#                     db,
#                     start_date=start_date,
#                     end_date=end_date,
#                     project_id=project.id
#                 )
#
#                 # Skip if no data
#                 if not failure_metrics:
#                     continue
#
#                 # Create report data
#                 report_data = {
#                     "project_id": project.id,
#                     "project_name": project.name,
#                     "date": end_date.strftime("%Y-%m-%d"),
#                     "metrics": failure_metrics,
#                     "summary": {
#                         "total_tests": sum(m["total_tests"] for m in failure_metrics),
#                         "failed_tests": sum(m["failed_tests"] for m in failure_metrics),
#                         "avg_failure_rate": round(
#                             sum(m["failure_rate"] for m in failure_metrics) / len(failure_metrics),
#                             2
#                         ) if failure_metrics else 0
#                     }
#                 }
#
#                 # Send notification with report
#                 await send_notification(
#                     title=f"Daily Test Report for {project.name}",
#                     message=f"Test failure rate: {report_data['summary']['avg_failure_rate']}%",
#                     data=report_data,
#                     notification_type="daily_report"
#                 )
#
#                 # Dispatch webhook event
#                 await dispatch_event(
#                     event_type="daily_report",
#                     data=report_data,
#                     db=db
#                 )
#
#         except Exception as e:
#             logger.error(f"Error processing daily reports: {e}")
#         finally:
#             db.close()
#
#     async def detect_flaky_tests(self):
#         """
#         Detect and report flaky tests
#         """
#         logger.info("Detecting flaky tests")
#
#         # Get database session
#         db = next(get_db())
#
#         try:
#             # Look at the last 7 days for flaky tests
#             end_date = datetime.utcnow()
#             start_date = end_date - timedelta(days=7)
#
#             # Get all active projects
#             try:
#                 projects = db.query(Project).filter(Project.is_active == True).all()
#             except:
#                 # Fallback to a dummy project if Project model doesn't exist
#                 logger.warning("Project model not found, using dummy project")
#                 projects = [type('obj', (object,), {'id': 1, 'name': 'Default Project', 'is_active': True})]
#
#             for project in projects:
#                 # Get flaky tests
#                 flaky_tests = get_flaky_tests(
#                     db,
#                     start_date=start_date,
#                     end_date=end_date,
#                     project_id=project.id,
#                     min_flake_rate=0.2,  # 20% flakiness threshold
#                     limit=10
#                 )
#
#                 # Skip if no flaky tests found
#                 if not flaky_tests:
#                     continue
#
#                 # Create report data
#                 report_data = {
#                     "project_id": project.id,
#                     "project_name": project.name,
#                     "date": end_date.strftime("%Y-%m-%d"),
#                     "flaky_tests": flaky_tests,
#                     "summary": {
#                         "total_flaky_tests": len(flaky_tests),
#                         "avg_flake_rate": round(
#                             sum(test["flake_rate"] for test in flaky_tests) / len(flaky_tests),
#                             3
#                         ) if flaky_tests else 0
#                     }
#                 }
#
#                 # Send notification about flaky tests
#                 await send_notification(
#                     title=f"Flaky Tests Detected in {project.name}",
#                     message=f"Found {len(flaky_tests)} flaky tests with average flake rate of {report_data['summary']['avg_flake_rate'] * 100}%",
#                     data=report_data,
#                     notification_type="flaky_tests"
#                 )
#
#                 # Dispatch webhook event
#                 await dispatch_event(
#                     event_type="flaky_tests_detected",
#                     data=report_data,
#                     db=db
#                 )
#
#         except Exception as e:
#             logger.error(f"Error detecting flaky tests: {e}")
#         finally:
#             db.close()
#
#     async def monitor_build_health(self):
#         """
#         Monitor overall build health and send alerts if health degrades
#         """
#         logger.info("Monitoring build health")
#
#         # Get database session
#         db = next(get_db())
#
#         try:
#             # Get all active projects
#             try:
#                 projects = db.query(Project).filter(Project.is_active == True).all()
#             except:
#                 # Fallback to a dummy project if Project model doesn't exist
#                 logger.warning("Project model not found, using dummy project")
#                 projects = [type('obj', (object,), {'id': 1, 'name': 'Default Project', 'is_active': True})]
#
#             for project in projects:
#                 # Get current health score
#                 current_score = calculate_build_health_score(
#                     db,
#                     project_id=project.id,
#                     days=7  # Last 7 days
#                 )
#
#                 # Get previous health score (from stored metrics or calculate)
#                 # Here we're recalculating for the previous 7-14 day period
#                 previous_end_date = datetime.utcnow() - timedelta(days=7)
#                 previous_start_date = previous_end_date - timedelta(days=7)
#
#                 # Query previous build metrics
#                 try:
#                     previous_metrics = db.query(BuildMetric).filter(
#                         BuildMetric.project_id == project.id,
#                         BuildMetric.timestamp.between(previous_start_date, previous_end_date)
#                     ).all()
#                 except:
#                     # Fallback if BuildMetric model doesn't exist
#                     logger.warning("BuildMetric model not found, skipping previous metrics query")
#                     previous_metrics = []
#
#                 # If we have metrics for the previous period, calculate score
#                 previous_score = None
#                 if previous_metrics:
#                     previous_score = calculate_build_health_score(
#                         db,
#                         project_id=project.id,
#                         days=14  # Previous 7-14 day period
#                     )
#
#                 # Store current health score for future reference
#                 health_metric = HealthMetric(
#                     project_id=project.id,
#                     score=current_score,
#                     timestamp=datetime.utcnow()
#                 )
#                 db.add(health_metric)
#                 db.commit()
#
#                 # Determine status based on score
#                 status = "Unknown"
#                 if current_score >= 90:
#                     status = "Excellent"
#                 elif current_score >= 75:
#                     status = "Good"
#                 elif current_score >= 60:
#                     status = "Fair"
#                 elif current_score >= 40:
#                     status = "Poor"
#                 else:
#                     status = "Critical"
#
#                 # Check if health has degraded significantly
#                 health_degraded = False
#                 if previous_score is not None and current_score < previous_score - 10:
#                     health_degraded = True
#
#                 # Create health data
#                 health_data = {
#                     "project_id": project.id,
#                     "project_name": project.name,
#                     "date": datetime.utcnow().strftime("%Y-%m-%d"),
#                     "current_score": current_score,
#                     "previous_score": previous_score,
#                     "status": status,
#                     "health_degraded": health_degraded
#                 }
#
#                 # Send notification if in poor/critical state or if health degraded
#                 if current_score < 60 or health_degraded:
#                     message = f"Build health is {status.lower()} with score {current_score}/100"
#                     if health_degraded:
#                         message += f" (degraded from {previous_score}/100)"
#
#                     await send_notification(
#                         title=f"Build Health Alert for {project.name}",
#                         message=message,
#                         data=health_data,
#                         notification_type="build_health"
#                     )
#
#                 # Always dispatch webhook event for build health updates
#                 await dispatch_event(
#                     event_type="build_health_update",
#                     data=health_data,
#                     db=db
#                 )
#
#         except Exception as e:
#             logger.error(f"Error monitoring build health: {e}")
#         finally:
#             db.close()