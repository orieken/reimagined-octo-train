"""
API routes for health checking
"""
from fastapi import APIRouter
from datetime import datetime

from app.config import settings

router = APIRouter()


@router.get("/health")
async def health_check():
    """
    Health check endpoint for the API

    Returns:
        dict: Health status information
    """
    return {
        "status": "success",
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "timestamp": datetime.utcnow().isoformat()
    }
