from fastapi import APIRouter, Depends
from typing import Dict, Any
import logging
from datetime import datetime, timedelta
import platform
import os

from app.config import settings
from app.services.orchestrator import ServiceOrchestrator
from app.api.dependencies import get_orchestrator_service
from app.services import datetime_service as dt
from sqlalchemy import text

logger = logging.getLogger(__name__)
router = APIRouter(prefix=settings.API_PREFIX, tags=["health"])

# Store startup time for uptime tracking
startup_time = datetime.utcnow()


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
            "llm": "unknown",
            "postgres_db": "unknown"
        },
        "system": {
            "version": settings.APP_VERSION,
            "python": platform.python_version(),
            "platform": platform.platform(),
            "memory_usage": get_memory_usage(),
            "uptime": str(timedelta(seconds=(datetime.utcnow() - startup_time).total_seconds()))
        },
        "timestamp": dt.isoformat_utc(dt.now_utc())
    }

    # Check Vector DB
    try:
        if orchestrator.vector_db.client is None:
            orchestrator.vector_db.client = orchestrator.vector_db._initialize_client()

        orchestrator.vector_db.client.get_collections()
        health_status["services"]["vector_db"] = "ok"
    except Exception as e:
        health_status["services"]["vector_db"] = f"error: {str(e)}"
        health_status["status"] = "degraded"

    # Check LLM Service
    try:
        test_text = "health check"
        test_embedding = await orchestrator.llm.generate_embedding(test_text)

        if test_embedding and len(test_embedding) > 0:
            health_status["services"]["llm"] = "ok"
        else:
            health_status["services"]["llm"] = "error: empty embedding returned"
            health_status["status"] = "degraded"
    except Exception as e:
        msg = str(e)
        health_status["services"]["llm"] = f"error: {msg}"
        health_status["status"] = "degraded"
        if "model not found" in msg.lower():
            health_status["services"]["llm"] += f" (Hint: Run 'ollama pull {settings.LLM_MODEL}' to download the model)"

    # Check PostgreSQL
    try:
        async with orchestrator.pg_service.session() as session:
            await session.execute(text("SELECT 1"))
        health_status["services"]["postgres_db"] = "ok"
    except Exception as e:
        health_status["services"]["postgres_db"] = f"error: {str(e)}"
        health_status["status"] = "degraded"

    return health_status


def get_memory_usage() -> Dict[str, Any]:
    """Get memory usage information."""
    try:
        import psutil
        process = psutil.Process(os.getpid())
        memory_info = process.memory_info()
        return {
            "rss": memory_info.rss / (1024 * 1024),
            "vms": memory_info.vms / (1024 * 1024),
            "percent": process.memory_percent()
        }
    except ImportError:
        return {"note": "psutil not available"}
    except Exception as e:
        return {"error": str(e)}
