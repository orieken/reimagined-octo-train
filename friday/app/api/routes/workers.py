# # app/api/routes/workers.py
# """
# API routes for worker management
# """
# from fastapi import APIRouter, HTTPException, status, BackgroundTasks
# from typing import List, Dict, Any, Optional
# from pydantic import BaseModel
#
# from app.services.worker_manager import worker_manager
#
# # Create router with prefix and tags
# router = APIRouter(prefix="/workers", tags=["workers"])
#
#
# class WorkerRequest(BaseModel):
#     """Request model for worker operations"""
#     worker_types: Optional[List[str]] = None
#
#
# @router.post("/start", response_model=Dict[str, Any])
# async def start_workers(request: WorkerRequest):
#     """
#     Start background workers for analytics and processing tasks
#
#     - If worker_types is not provided, all available workers will be started
#     - If specific worker types are provided, only those will be started
#     """
#     result = await worker_manager.start_workers(request.worker_types)
#     return result
#
#
# @router.post("/stop", response_model=Dict[str, Any])
# async def stop_workers(request: WorkerRequest):
#     """
#     Stop background workers
#
#     - If worker_types is not provided, all running workers will be stopped
#     - If specific worker types are provided, only those will be stopped
#     """
#     result = await worker_manager.stop_workers(request.worker_types)
#     return result
#
#
# @router.get("/status", response_model=Dict[str, Any])
# async def get_worker_status():
#     """
#     Get status of all workers
#
#     Returns information about which workers are currently running
#     """
#     return worker_manager.get_status()
#
#
# @router.post("/tasks/{task_name}", response_model=Dict[str, Any])
# async def execute_task(
#         task_name: str,
#         background_tasks: BackgroundTasks
# ):
#     """
#     Manually execute a specific task
#
#     Available tasks:
#     - daily_reports: Generate and send daily test reports
#     - flaky_test_detection: Detect and report flaky tests
#     - build_health_monitoring: Monitor overall build health
#     """
#     valid_tasks = {
#         "daily_reports": "process_daily_reports",
#         "flaky_test_detection": "detect_flaky_tests",
#         "build_health_monitoring": "monitor_build_health"
#     }
#
#     if task_name not in valid_tasks:
#         raise HTTPException(
#             status_code=status.HTTP_400_BAD_REQUEST,
#             detail=f"Unknown task: {task_name}. Valid tasks are: {', '.join(valid_tasks.keys())}"
#         )
#
#     # Check if analytics worker is running
#     if "analytics" not in worker_manager.workers:
#         raise HTTPException(
#             status_code=status.HTTP_400_BAD_REQUEST,
#             detail="Analytics worker is not running"
#         )
#
#     # Get worker
#     worker = worker_manager.workers["analytics"]
#
#     # Get task function
#     task_func = getattr(worker, valid_tasks[task_name])
#
#     # Execute task in background
#     background_tasks.add_task(task_func)
#
#     return {
#         "message": f"Task {task_name} scheduled for execution",
#         "status": "scheduled"
#     }