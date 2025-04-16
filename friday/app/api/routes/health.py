# app/api/routes/health.py
from fastapi import APIRouter, Depends
from typing import Dict, Any
import logging
from datetime import datetime
import platform
import os

from app.config import settings
from app.services.orchestrator import ServiceOrchestrator
from app.api.dependencies import get_orchestrator_service
from app.services import datetime_service as dt


logger = logging.getLogger(__name__)

router = APIRouter(prefix=settings.API_PREFIX, tags=["health"])


@router.get("/health", response_model=Dict[str, Any])
async def health_check(
        orchestrator: ServiceOrchestrator = Depends(get_orchestrator_service)
):
    """
    Health check endpoint.

    This endpoint checks the health of the application and its dependencies.
    """
    health_status = {
        "status": "ok",
        "services": {
            "vector_db": "unknown",
            "llm": "unknown"
        },
        "system": {
            "version": settings.APP_VERSION,
            "python": platform.python_version(),
            "platform": platform.platform(),
            "memory_usage": get_memory_usage()
        },
        "timestamp": dt.isoformat_utc(dt.now_utc())
    }

    # Check Vector DB
    try:
        # Make sure we have a client
        if orchestrator.vector_db.client is None:
            orchestrator.vector_db.client = orchestrator.vector_db._initialize_client()

        # Simple check to see if we can access collections
        orchestrator.vector_db.client.get_collections()
        health_status["services"]["vector_db"] = "ok"
    except Exception as e:
        health_status["services"]["vector_db"] = f"error: {str(e)}"
        health_status["status"] = "degraded"

    # Check LLM Service
    try:
        # Generate a simple embedding to test connection
        test_text = "health check"
        test_embedding = await orchestrator.llm.generate_embedding(test_text)

        if test_embedding and len(test_embedding) > 0:
            health_status["services"]["llm"] = "ok"
        else:
            health_status["services"]["llm"] = "error: empty embedding returned"
            health_status["status"] = "degraded"
    except Exception as e:
        health_status["services"]["llm"] = f"error: {str(e)}"
        health_status["status"] = "degraded"
        # Add a helpful message if the model is not found
        if "model not found" in str(e).lower():
            health_status["services"]["llm"] += f" (Hint: Run 'ollama pull {settings.LLM_MODEL}' to download the model)"

    return health_status


def get_memory_usage() -> Dict[str, Any]:
    """Get memory usage information."""
    try:
        import psutil
        process = psutil.Process(os.getpid())
        memory_info = process.memory_info()
        return {
            "rss": memory_info.rss / (1024 * 1024),  # Convert to MB
            "vms": memory_info.vms / (1024 * 1024),  # Convert to MB
            "percent": process.memory_percent()
        }
    except ImportError:
        return {"note": "psutil not available"}
    except Exception as e:
        return {"error": str(e)}