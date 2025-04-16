# app/api/routes/processor.py
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query, Path
from typing import List, Dict, Any, Optional
import logging
from datetime import datetime, timezone
import uuid
from pydantic import BaseModel, Field, validator, root_validator

from app.config import settings
from app.services.orchestrator import ServiceOrchestrator
from app.api.dependencies import get_orchestrator_service

from app.models import (
    ReportResponse, SuccessResponse, BuildInfo, ProcessingStatusResponse, Report, TestStep,
    TestCase, TextChunk, ProcessReportResponse  # Added ProcessReportResponse import
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix=settings.API_PREFIX, tags=["processor"])


# New Pydantic models for request validation
class CucumberMetadata(BaseModel):
    project: str
    branch: str
    commit: str
    timestamp: str
    runner: str

    @validator('timestamp')
    def validate_timestamp(cls, v):
        try:
            # Make sure to parse ISO format timestamp with timezone info
            return datetime.fromisoformat(v.replace('Z', '+00:00')).isoformat()
        except ValueError:
            raise ValueError("timestamp must be in ISO8601 format")


class CucumberTag(BaseModel):
    name: str
    line: int


class CucumberStepResult(BaseModel):
    status: str
    duration: Optional[int] = None
    error_message: Optional[str] = None
    stack_trace: Optional[str] = None

    @validator('duration', pre=True, always=True)
    def set_duration_default(cls, v, values):
        # If status is skipped and no duration provided, set to 0
        if values.get('status') == 'skipped' and v is None:
            return 0
        return v


class CucumberStepMatch(BaseModel):
    location: Optional[str] = None


class CucumberEmbedding(BaseModel):
    data: str
    mime_type: str


class CucumberStep(BaseModel):
    keyword: str
    name: Optional[str] = None
    line: Optional[int] = None
    match: Optional[CucumberStepMatch] = None
    result: CucumberStepResult
    hidden: Optional[bool] = None
    arguments: Optional[List[Any]] = []
    embeddings: Optional[List[CucumberEmbedding]] = []


class CucumberScenario(BaseModel):
    id: str
    name: str
    line: int
    description: Optional[str] = ""
    keyword: str
    type: str
    tags: Optional[List[CucumberTag]] = []
    steps: List[CucumberStep]


class CucumberFeature(BaseModel):
    id: str
    name: str
    uri: str
    line: int
    keyword: str
    description: Optional[str] = None
    tags: Optional[List[CucumberTag]] = []
    elements: List[CucumberScenario]


# We need to handle both direct Cucumber JSON and the Friday CLI format
class CucumberReportRequest(BaseModel):
    metadata: Optional[CucumberMetadata] = None
    report: Optional[List[CucumberFeature]] = None

    # For direct Cucumber JSON (list of features)
    @root_validator(pre=True)
    def check_structure(cls, values):
        # If this is a list, it's direct Cucumber format
        if isinstance(values, list):
            # Create a new object with the expected structure
            return {"report": values}
        return values


@router.post("/processor/cucumber", response_model=ProcessReportResponse)  # Changed to ProcessReportResponse
async def process_cucumber_report(
        report_request: CucumberReportRequest,
        background_tasks: BackgroundTasks,
        project: Optional[str] = Query(None, description="Project identifier (for direct Cucumber JSON)"),
        branch: Optional[str] = Query(None, description="Git branch (for direct Cucumber JSON)"),
        commit: Optional[str] = Query(None, description="Git commit hash (for direct Cucumber JSON)"),
        runner: Optional[str] = Query(None, description="Test runner (for direct Cucumber JSON)"),
        process_async: bool = Query(True, description="Process the report asynchronously"),
        orchestrator: ServiceOrchestrator = Depends(get_orchestrator_service)
):
    """
    Process a Cucumber JSON report.

    This endpoint accepts a Cucumber JSON report with metadata, validates it,
    converts it to our domain model, and stores it in the vector database with embeddings.

    Supports two formats:
    1. Friday CLI format with metadata and report sections
    2. Direct Cucumber JSON format (array of features)
    """
    try:
        # Handle direct Cucumber JSON format
        if report_request.metadata is None:
            if not project:
                # Try to extract project from the report itself if possible
                # For now, use a default value
                project = "unknown"

            # Create metadata from query parameters or defaults
            metadata = {
                "project": project,
                "branch": branch or "main",
                "commit": commit or "unknown",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "runner": runner or "cucumber"
            }

            logger.info(f"Received direct Cucumber JSON report for processing from project {project}")
        else:
            # Use Friday CLI format metadata
            metadata = {
                "project": report_request.metadata.project,
                "branch": report_request.metadata.branch,
                "commit": report_request.metadata.commit,
                "timestamp": report_request.metadata.timestamp,
                "runner": report_request.metadata.runner
            }

            logger.info(f"Received Cucumber report for processing from project {metadata['project']}")

        # Convert Cucumber JSON to our domain model
        test_run = convert_enhanced_cucumber_to_domain(report_request, metadata)

        # Process the report
        if process_async:
            # Create a processing task ID
            task_id = str(uuid.uuid4())

            # Add task to background processing
            background_tasks.add_task(
                orchestrator.process_report,
                test_run,
                task_id=task_id
            )

            return ProcessReportResponse(  # Changed to ProcessReportResponse
                status="accepted",
                message=f"Report processing started for {metadata['project']} ({metadata['branch']})",
                report_id=test_run.id,
                task_id=task_id,
                timestamp=datetime.now(timezone.utc).isoformat()
            )
        else:
            report_id = await orchestrator.process_report(test_run)
            return ProcessReportResponse(  # Changed to ProcessReportResponse
                status="success",
                message=f"Report processed successfully for {metadata['project']} ({metadata['branch']})",
                report_id=report_id,
                timestamp=datetime.now(timezone.utc).isoformat()
            )
    except ValueError as e:
        logger.error(f"Validation error processing Cucumber report: {str(e)}")
        raise HTTPException(
            status_code=400,
            detail=f"Invalid Cucumber report format: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Error processing Cucumber report: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process Cucumber report: {str(e)}"
        )


@router.post("/processor/build-info", response_model=SuccessResponse)
async def process_build_info(
        build_info: BuildInfo,
        orchestrator: ServiceOrchestrator = Depends(get_orchestrator_service)
):
    """
    Process build information.

    This endpoint accepts build information, generates embeddings,
    and stores it in the vector database.
    """
    try:
        logger.info(f"Received build info for processing: {build_info.build_number}")

        build_id = await orchestrator.process_build_info(build_info)

        return SuccessResponse(
            message=f"Build information processed successfully with ID {build_id}",
            timestamp=datetime.now(timezone.utc).isoformat()
        )
    except Exception as e:
        logger.error(f"Error processing build info: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process build information: {str(e)}"
        )


@router.post("/processor/document", response_model=SuccessResponse)
async def process_document(
        document: Dict[str, Any],
        chunk_size: int = Query(settings.CHUNK_SIZE, description="Size of text chunks"),
        chunk_overlap: int = Query(settings.CHUNK_OVERLAP, description="Overlap between chunks"),
        orchestrator: ServiceOrchestrator = Depends(get_orchestrator_service)
):
    """
    Process a document by chunking it and storing with embeddings.

    This endpoint accepts a document, breaks it into chunks,
    generates embeddings, and stores in the vector database.
    """
    try:
        logger.info(f"Received document for processing")

        # Extract document text and metadata
        text = document.get("text", "")
        metadata = document.get("metadata", {})

        if not text:
            raise HTTPException(
                status_code=400,
                detail="Document must contain 'text' field"
            )

        # Split document into chunks
        chunks = split_text_into_chunks(text, chunk_size, chunk_overlap, metadata)

        # Process chunks
        chunk_ids = await orchestrator.process_text_chunks(chunks)

        return SuccessResponse(
            message=f"Document processed successfully into {len(chunk_ids)} chunks",
            timestamp=datetime.now(timezone.utc).isoformat()
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing document: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process document: {str(e)}"
        )


@router.get("/processing/{task_id}/status", response_model=ProcessingStatusResponse)
async def get_processing_status(
        task_id: str = Path(..., description="ID of the processing task"),
        orchestrator: ServiceOrchestrator = Depends(get_orchestrator_service)
):
    """
    Get the status of an asynchronous processing task.

    This endpoint returns the current status of a processing task.
    """
    try:
        # Get the task status from the orchestrator service
        status = await orchestrator.get_task_status(task_id)

        if not status:
            raise HTTPException(
                status_code=404,
                detail=f"Task with ID {task_id} not found"
            )

        return ProcessingStatusResponse(
            task_id=task_id,
            status=status.get("status", "unknown"),
            progress=status.get("progress", 0.0),
            message=status.get("message", ""),
            timestamp=datetime.now(timezone.utc).isoformat()
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving task status: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve task status: {str(e)}"
        )


# Utility functions

def convert_enhanced_cucumber_to_domain(request: CucumberReportRequest, metadata_dict: Optional[Dict] = None) -> Report:
    """
    Convert enhanced Cucumber JSON format with metadata to our domain model.

    This updated function handles both formats:
    1. Friday CLI format with metadata and report sections
    2. Direct Cucumber JSON format (array of features)

    And processes additional fields like embeddings and hidden steps.
    """
    # Create a unique ID for the report
    report_id = str(uuid.uuid4())

    # Extract features and metadata
    if metadata_dict:
        # Use provided metadata
        metadata = metadata_dict
    elif request.metadata:
        # Extract from Friday CLI format
        metadata = {
            "project": request.metadata.project,
            "branch": request.metadata.branch,
            "commit": request.metadata.commit,
            "timestamp": request.metadata.timestamp,
            "runner": request.metadata.runner
        }
    else:
        # Default metadata if none provided
        metadata = {
            "project": "unknown",
            "branch": "main",
            "commit": "unknown",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "runner": "cucumber"
        }

    # Get features from the appropriate source
    cucumber_features = request.report or []

    # Process features
    test_cases = []

    total_duration = 0
    passed_count = 0
    failed_count = 0
    skipped_count = 0
    flaky_count = 0

    for feature_json in cucumber_features:
        feature_name = feature_json.name
        feature_uri = feature_json.uri

        # Process scenarios
        elements = feature_json.elements
        for element in elements:
            # Skip backgrounds, only process scenarios
            if hasattr(element, 'type') and element.type != "scenario" and element.type != "scenario_outline":
                continue

            scenario_name = element.name
            scenario_id = element.id

            # Extract tags
            tags = []
            if hasattr(element, 'tags') and element.tags:
                tags = [tag.name.strip("@") for tag in element.tags]

            # Check if scenario is marked as flaky
            is_flaky = "flaky" in tags
            if is_flaky:
                flaky_count += 1

            # Process steps
            steps = []
            scenario_duration = 0
            scenario_status = "PASSED"  # Assume passed initially

            # Track embeddings for the scenario
            scenario_embeddings = []

            for step_json in element.steps:
                # Skip hidden steps if configured to do so (like Before/After hooks)
                if hasattr(step_json, 'hidden') and step_json.hidden:
                    # Still count duration, but don't add to visible steps
                    if hasattr(step_json.result, 'duration'):
                        duration = step_json.result.duration or 0
                        # Convert from nanoseconds to milliseconds
                        if duration > 1_000_000_000:  # Likely in nanoseconds
                            duration = duration / 1_000_000
                        scenario_duration += duration

                    # Collect embeddings from hidden steps (often from After hooks)
                    if hasattr(step_json, 'embeddings') and step_json.embeddings:
                        for embedding in step_json.embeddings:
                            scenario_embeddings.append({
                                "data": embedding.data,
                                "mime_type": embedding.mime_type
                            })

                    continue

                step_name = step_json.name if hasattr(step_json, 'name') else ""
                keyword = step_json.keyword.strip() if hasattr(step_json, 'keyword') else ""

                # Get step result
                result = step_json.result
                status = result.status.upper()

                if status == "UNDEFINED" or status == "PENDING":
                    status = "SKIPPED"

                # Map cucumber status to our enum
                if status == "FAILED":
                    # If the test is marked as flaky, don't count the failure in the overall status
                    if not is_flaky:
                        scenario_status = "FAILED"
                        failed_count += 1
                elif status == "SKIPPED" and scenario_status != "FAILED":
                    scenario_status = "SKIPPED"
                    skipped_count += 1

                # Extract duration
                duration = result.duration or 0
                # Convert from nanoseconds to milliseconds
                if duration > 1_000_000_000:  # Likely in nanoseconds
                    duration = duration / 1_000_000

                scenario_duration += duration

                # Get error message and stack trace
                error_message = result.error_message if hasattr(result, 'error_message') else None
                stack_trace = result.stack_trace if hasattr(result, 'stack_trace') else None

                # Collect embeddings for this step
                step_embeddings = []
                if hasattr(step_json, 'embeddings') and step_json.embeddings:
                    for embedding in step_json.embeddings:
                        # Create StepEmbedding object
                        step_embeddings.append({
                            "data": embedding.data,
                            "mime_type": embedding.mime_type
                        })

                # Create step object
                step = TestStep(
                    id=str(uuid.uuid4()),
                    keyword=keyword,
                    name=step_name,
                    status=status,
                    error_message=error_message,
                    stack_trace=stack_trace,
                    duration=duration,
                    embeddings=step_embeddings if step_embeddings else None
                )

                steps.append(step)

            # Update counts
            if scenario_status == "PASSED":
                passed_count += 1

            # Create scenario object
            scenario = TestCase(
                id=scenario_id,
                name=scenario_name,
                status=scenario_status,
                feature=feature_name,
                feature_file=feature_uri,
                steps=steps,
                duration=scenario_duration,
                tags=tags,
                is_flaky=is_flaky,
                embeddings=scenario_embeddings if scenario_embeddings else None
            )

            test_cases.append(scenario)
            total_duration += scenario_duration

    # Determine overall status
    overall_status = "PASSED"
    if failed_count > 0:
        overall_status = "FAILED"
    elif passed_count == 0 and len(test_cases) > 0:
        overall_status = "SKIPPED"

    # Format timestamp - ensure we have a consistent timezone-aware format
    timestamp = metadata.get("timestamp", datetime.now(timezone.utc).isoformat())

    # Handle ISO format with 'Z' at the end (UTC marker)
    if isinstance(timestamp, str):
        if timestamp.endswith('Z'):
            timestamp = timestamp.replace('Z', '+00:00')

        # Parse string to datetime with timezone info
        try:
            parsed_timestamp = datetime.fromisoformat(timestamp)
            # Ensure timestamp has timezone info
            if parsed_timestamp.tzinfo is None:
                parsed_timestamp = parsed_timestamp.replace(tzinfo=timezone.utc)
            timestamp = parsed_timestamp.isoformat()
        except ValueError:
            # If parsing fails, use current time with UTC timezone
            timestamp = datetime.now(timezone.utc).isoformat()

    # Create the report name
    report_name = f"{metadata.get('project')} - {metadata.get('branch')}"

    # Create the report with enhanced metadata
    return Report(
        id=report_id,
        name=report_name,
        status=overall_status,
        timestamp=timestamp,
        duration=total_duration,
        environment=metadata.get("runner", "cucumber"),
        tags=[],  # Extract feature-level tags if needed
        scenarios=test_cases,
        metadata={
            "project": metadata.get("project", "unknown"),
            "branch": metadata.get("branch", "main"),
            "commit": metadata.get("commit", "unknown"),
            "runner": metadata.get("runner", "cucumber"),
            "total_passed": passed_count,
            "total_failed": failed_count,
            "total_skipped": skipped_count,
            "total_flaky": flaky_count,
            "source": "cucumber"
        }
    )


def convert_cucumber_to_domain(cucumber_json: Dict[str, Any]) -> Report:
    """Convert Cucumber JSON format to our domain model."""
    # Create a unique ID for the report
    report_id = str(uuid.uuid4())

    # Extract basic report info
    timestamp = cucumber_json.get("timestamp", datetime.now(timezone.utc).isoformat())
    name = cucumber_json.get("name", f"Cucumber Report {timestamp}")

    # Process features
    features_json = cucumber_json.get("features", [])
    test_cases = []

    total_duration = 0
    passed_count = 0
    failed_count = 0
    skipped_count = 0

    for feature_json in features_json:
        feature_name = feature_json.get("name", "Unnamed Feature")

        # Process scenarios
        elements = feature_json.get("elements", [])
        for element in elements:
            # Skip backgrounds, only process scenarios
            if element.get("type") != "scenario" and element.get("type") != "scenario_outline":
                continue

            scenario_name = element.get("name", "Unnamed Scenario")
            scenario_id = str(uuid.uuid4())

            # Process steps
            steps_json = element.get("steps", [])
            steps = []

            scenario_duration = 0
            scenario_status = "PASSED"  # Assume passed initially

            for step_json in steps_json:
                step_name = step_json.get("name", "Unnamed Step")
                keyword = step_json.get("keyword", "").strip()

                # Get step result
                result = step_json.get("result", {})
                status = result.get("status", "undefined").upper()

                if status == "UNDEFINED" or status == "PENDING":
                    status = "SKIPPED"

                # Map cucumber status to our enum
                if status == "FAILED":
                    scenario_status = "FAILED"
                    failed_count += 1
                elif status == "SKIPPED" and scenario_status != "FAILED":
                    scenario_status = "SKIPPED"
                    skipped_count += 1

                # Extract duration
                duration = result.get("duration", 0)
                # Convert from nanoseconds to milliseconds if needed
                if duration > 1_000_000_000:  # Likely in nanoseconds
                    duration = duration / 1_000_000

                scenario_duration += duration

                # Get error message
                error_message = result.get("error_message")

                # Check for embeddings
                step_embeddings = []
                if "embeddings" in step_json:
                    for embedding in step_json["embeddings"]:
                        step_embeddings.append({
                            "data": embedding.get("data", ""),
                            "mime_type": embedding.get("mime_type", "text/plain")
                        })

                # Create step object
                step = TestStep(
                    id=str(uuid.uuid4()),
                    keyword=keyword,
                    name=step_name,
                    status=status,
                    error_message=error_message,
                    duration=duration,
                    embeddings=step_embeddings if step_embeddings else None
                )

                steps.append(step)

            # Update counts
            if scenario_status == "PASSED":
                passed_count += 1

            # Create scenario object
            scenario = TestCase(
                id=scenario_id,
                name=scenario_name,
                status=scenario_status,
                feature=feature_name,
                steps=steps,
                duration=scenario_duration,
                tags=[tag.get("name", "").strip("@") for tag in element.get("tags", [])]
            )

            test_cases.append(scenario)
            total_duration += scenario_duration

    # Determine overall status
    overall_status = "PASSED"
    if failed_count > 0:
        overall_status = "FAILED"
    elif passed_count == 0:
        overall_status = "SKIPPED"

    # Ensure timestamp is timezone-aware
    if isinstance(timestamp, str):
        if timestamp.endswith('Z'):
            timestamp = timestamp.replace('Z', '+00:00')
        try:
            parsed_timestamp = datetime.fromisoformat(timestamp)
            if parsed_timestamp.tzinfo is None:
                parsed_timestamp = parsed_timestamp.replace(tzinfo=timezone.utc)
            timestamp = parsed_timestamp.isoformat()
        except ValueError:
            timestamp = datetime.now(timezone.utc).isoformat()

    # Create the report
    return Report(
        id=report_id,
        name=name,
        status=overall_status,
        timestamp=timestamp,
        duration=total_duration,
        environment=cucumber_json.get("environment", "unknown"),
        tags=[],  # Extract tags if available in your format
        scenarios=test_cases,
        metadata={
            "total_passed": passed_count,
            "total_failed": failed_count,
            "total_skipped": skipped_count,
            "source": "cucumber"
        }
    )


def split_text_into_chunks(text: str, chunk_size: int, chunk_overlap: int, metadata: Dict[str, Any]) -> List[TextChunk]:
    """Split text into overlapping chunks."""
    if not text:
        return []

    chunks = []

    # Simple splitting by characters - in a real implementation,
    # you might want to split by sentences or paragraphs
    start = 0
    chunk_index = 0

    while start < len(text):
        # Calculate end position
        end = min(start + chunk_size, len(text))

        # Extract chunk text
        chunk_text = text[start:end]

        # Create chunk metadata
        chunk_metadata = {
            **metadata,
            "chunk_index": chunk_index,
            "start_char": start,
            "end_char": end
        }

        # Create text chunk object
        chunk = TextChunk(
            id=str(uuid.uuid4()),
            text=chunk_text,
            metadata=chunk_metadata,
            chunk_size=len(chunk_text)
        )

        chunks.append(chunk)

        # Move to next chunk
        start = end - chunk_overlap
        chunk_index += 1

        # Avoid infinite loop for very small texts
        if start >= end:
            break

    return chunks