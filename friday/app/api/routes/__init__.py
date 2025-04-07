"""
API routes for the Friday service
"""
from fastapi import APIRouter
from app.api.routes import(processor, analysis, test_results, failures, trends, health, query,
                           stats, notification, reporting, analytics, results,
                           # Adding new Phase 2 routes
                           # webhooks, workers
                           )

# Create main router
api_router = APIRouter()

# Include all route modules
api_router.include_router(processor.router)
api_router.include_router(query.router)
api_router.include_router(stats.router)
api_router.include_router(test_results.router)
api_router.include_router(health.router)
api_router.include_router(trends.router)
api_router.include_router(failures.router)
api_router.include_router(analysis.router)
api_router.include_router(notification.router)
api_router.include_router(reporting.router)
api_router.include_router(analytics.router)
api_router.include_router(results.router)

# Phase 2 routes
# api_router.include_router(webhooks.router)
# api_router.include_router(workers.router)