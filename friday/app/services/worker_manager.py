# # app/services/worker_manager.py
# """
# Service for managing background workers
# """
# import logging
# import asyncio
# from typing import Dict, List, Optional, Any
#
# from app.workers.analytics_worker import AnalyticsWorker
#
# logger = logging.getLogger("friday.workers")
#
#
# class WorkerManager:
#     """
#     Manager for background workers
#
#     This service manages the lifecycle of all background workers in the application.
#     It provides methods to start, stop, and check the status of workers.
#     """
#
#     def __init__(self):
#         self.workers = {}
#         self.running = False
#
#     async def start_workers(self, worker_types: Optional[List[str]] = None) -> Dict[str, Any]:
#         """
#         Start specified workers or all workers if none specified
#
#         Args:
#             worker_types: Optional list of worker types to start
#
#         Returns:
#             Dict with message and list of running workers
#         """
#         self.running = True
#
#         # Define available worker types
#         available_workers = {
#             "analytics": AnalyticsWorker,
#         }
#
#         # If no workers specified, start all
#         if not worker_types:
#             worker_types = list(available_workers.keys())
#
#         # Start each worker
#         for worker_type in worker_types:
#             if worker_type not in available_workers:
#                 logger.warning(f"Unknown worker type: {worker_type}")
#                 continue
#
#             if worker_type in self.workers:
#                 logger.info(f"Worker {worker_type} already running")
#                 continue
#
#             # Create and start worker
#             worker = available_workers[worker_type]()
#             self.workers[worker_type] = worker
#
#             # Start worker in a background task
#             asyncio.create_task(worker.start())
#             logger.info(f"Started {worker_type} worker")
#
#         return {
#             "message": f"Started workers: {', '.join(worker_types)}",
#             "running_workers": list(self.workers.keys())
#         }
#
#     async def stop_workers(self, worker_types: Optional[List[str]] = None) -> Dict[str, Any]:
#         """
#         Stop specified workers or all workers if none specified
#
#         Args:
#             worker_types: Optional list of worker types to stop
#
#         Returns:
#             Dict with message and list of running workers
#         """
#         # If no workers specified, stop all
#         if not worker_types:
#             worker_types = list(self.workers.keys())
#
#         # Stop each worker
#         for worker_type in worker_types:
#             if worker_type not in self.workers:
#                 logger.warning(f"Worker {worker_type} not running")
#                 continue
#
#             # Stop worker
#             worker = self.workers[worker_type]
#             await worker.stop()
#
#             # Remove from running workers
#             del self.workers[worker_type]
#             logger.info(f"Stopped {worker_type} worker")
#
#         if not self.workers:
#             self.running = False
#
#         return {
#             "message": f"Stopped workers: {', '.join(worker_types)}",
#             "running_workers": list(self.workers.keys())
#         }
#
#     def get_status(self) -> Dict[str, Any]:
#         """
#         Get status of all workers
#
#         Returns:
#             Dict with running status and list of workers
#         """
#         return {
#             "running": self.running,
#             "workers": list(self.workers.keys())
#         }
#
#
# # Create global instance of worker manager
# worker_manager = WorkerManager()