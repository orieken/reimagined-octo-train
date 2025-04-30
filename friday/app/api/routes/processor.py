# app/api/routes/processor.py

import logging
from uuid import uuid4
from typing import List

from fastapi import APIRouter, Body, HTTPException
from fastapi.responses import JSONResponse
from starlette.status import HTTP_200_OK, HTTP_422_UNPROCESSABLE_ENTITY, HTTP_500_INTERNAL_SERVER_ERROR

from app.config import settings
from app.services import datetime_service as dt
from app.services.orchestrator import ServiceOrchestrator
from app.models.schemas import MetadataSchema
from app.models.database import TestStatus, Scenario

router = APIRouter(prefix=settings.API_PREFIX, tags=["processor"])
logger = logging.getLogger(__name__)


def calculate_overall_status(scenarios: List[Scenario]) -> TestStatus:
    if any(s.status == TestStatus.FAILED for s in scenarios):
        return TestStatus.FAILED
    elif all(s.status == TestStatus.PASSED for s in scenarios):
        return TestStatus.PASSED
    else:
        return TestStatus.PENDING


def ensure_metadata_complete(metadata: dict) -> dict:
    now_utc = dt.isoformat_utc(dt.now_utc())
    metadata.setdefault("project", "unknown-project")
    metadata.setdefault("branch", "unknown-branch")
    metadata.setdefault("commit", "unknown-commit")
    metadata.setdefault("environment", "default")
    metadata.setdefault("runner", "unknown-runner")
    metadata.setdefault("timestamp", now_utc)
    metadata.setdefault("test_run_id", str(uuid4()))
    return metadata


@router.post("/processor/cucumber", tags=["processor"])
async def process_cucumber_report(payload: dict = Body(...)):
    """
    Accepts a Cucumber JSON report + metadata block.
    Converts and stores to database and vector database.
    """
    try:
        metadata_raw = payload.get("metadata")
        feature_data = payload.get("features")

        if not metadata_raw or not feature_data:
            logger.warning("Missing required 'metadata' or 'features' in request")
            raise HTTPException(
                status_code=HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Missing required 'metadata' or 'features'"
            )

        metadata_dict = ensure_metadata_complete(metadata_raw)
        metadata = MetadataSchema(**metadata_dict)

        logger.debug("[PROCESSOR] Received metadata:\n%s", metadata.model_dump_json(indent=2))
        logger.debug("[PROCESSOR] Raw feature count: %d", len(feature_data))

        orchestrator = ServiceOrchestrator()
        await orchestrator.process_report(metadata=metadata, raw_features=feature_data)

        return JSONResponse(content={"status": "ok"}, status_code=HTTP_200_OK)

    except Exception as e:
        logger.exception("Failed to process cucumber report")
        return JSONResponse(content={"error": str(e)}, status_code=HTTP_500_INTERNAL_SERVER_ERROR)


@router.get("/health", tags=["System"])
async def health_check():
    """Health check endpoint for readiness and liveness probes."""
    return {
        "status": "ok",
        "message": "Friday Service is healthy"
    }
