# app/services/cucumber_transformer.py
import json
import logging
from typing import Any, Dict, List
from uuid import uuid4

from app.models.domain import Feature, Scenario, Step
from app.models.base import TestStatus
from app.services.datetime_service import now_utc

from app.models.metadata import ReportMetadata

logger = logging.getLogger(__name__)


# Enhanced tag extraction in transform_cucumber_json_to_internal_model

def transform_cucumber_json_to_internal_model(raw_features: List[Dict[str, Any]], project_id: str) -> List[Feature]:
    features: List[Feature] = []
    logger.debug("[TRANSFORM] Starting Cucumber to internal model transformation")

    # Safety check
    if not isinstance(raw_features[0], dict):
        raise TypeError(f"Expected raw dicts, got {type(raw_features[0])}")

    # Debug the raw feature structure
    logger.info(
        f"[TRANSFORM] Raw feature structure example: {json.dumps(raw_features[0], indent=2, default=str)[:500]}...")

    # Check if raw features have tags at all
    has_feature_tags = any("tags" in feature for feature in raw_features)
    has_element_tags = any("elements" in feature and any("tags" in element for element in feature.get("elements", []))
                           for feature in raw_features)
    logger.info(f"[TRANSFORM] Features have tags: {has_feature_tags}, Elements have tags: {has_element_tags}")

    for raw_feature in raw_features:
        logger.debug("[TRANSFORM] Processing feature: %s", raw_feature.get("name"))
        feature_id = str(uuid4())
        feature_uri = raw_feature.get("uri", "")
        scenarios: List[Scenario] = []

        # Debug feature tags if any
        feature_tags = raw_feature.get("tags", [])
        if feature_tags:
            logger.info(f"[TRANSFORM] Feature '{raw_feature.get('name')}' has tags: {feature_tags}")

        for element in raw_feature.get("elements", []):
            logger.debug("[TRANSFORM]   Element: %s", element.get("name"))

            steps: List[Step] = []
            for idx, step in enumerate(element.get("steps", [])):
                # Step processing remains the same...
                result = step.get("result", {})
                duration = result.get("duration", 0.0)
                if duration > 1_000_000_000:
                    duration = duration / 1_000_000_000.0

                step_status = map_status(result.get("status"))

                step_model = Step(
                    id=str(uuid4()),
                    external_id=None,
                    keyword=step.get("keyword", ""),
                    name=step.get("name", "Unnamed Step"),
                    status=step_status,
                    duration=duration,
                    error_message=result.get("error_message"),
                    stack_trace=result.get("stack_trace"),
                    embeddings=[],
                    order=str(uuid4()),
                    start_time=None,
                    end_time=None,
                    created_at=now_utc(),
                    updated_at=now_utc(),
                )
                steps.append(step_model)

            # Extract tags with line numbers and add detailed logging
            tags = []
            tag_metadata = {}

            # Get raw tags and log them
            raw_tags = element.get("tags", [])
            logger.info(f"[TRANSFORM] Element '{element.get('name')}' has raw tags: {raw_tags}")

            for tag_obj in raw_tags:
                if isinstance(tag_obj, dict) and "name" in tag_obj:
                    tag_name = tag_obj["name"]
                    tags.append(tag_name)

                    # Store metadata including line number
                    tag_metadata[tag_name] = {
                        'line': tag_obj.get("line")
                    }
                    logger.info(f"[TRANSFORM] Extracted tag: {tag_name} with line: {tag_obj.get('line')}")

            logger.info(
                f"[TRANSFORM] Final extracted tags for {element.get('name')}: {tags} with metadata: {tag_metadata}")

            scenario_status = calculate_overall_status(steps)
            scenario_model = Scenario(
                id=str(uuid4()),
                external_id=element.get("id"),
                name=element.get("name", "Unnamed Scenario"),
                description=element.get("description", ""),
                status=scenario_status,
                duration=sum(s.duration or 0.0 for s in steps),
                steps=steps,
                tags=tags,
                tag_metadata=tag_metadata,
                is_flaky="@flaky" in tags,
                embeddings=[],
                created_at=now_utc(),
                updated_at=now_utc(),
                feature_id=feature_id,
                test_run_id=None,
                feature_file=feature_uri,
            )

            # Log the scenario model's tags
            logger.info(f"[TRANSFORM] Created scenario '{scenario_model.name}' with tags: {scenario_model.tags}")

            scenarios.append(scenario_model)

        feature_model = Feature(
            id=feature_id,
            external_id=feature_id,
            name=raw_feature.get("name", "Unnamed Feature"),
            description=raw_feature.get("description", ""),
            file_path=raw_feature.get("uri", ""),
            tags=[tag.get("name") for tag in raw_feature.get("tags", []) if isinstance(tag, dict)],
            created_at=now_utc(),
            updated_at=now_utc(),
            scenarios=scenarios,
            project_id=str(project_id),
        )

        logger.debug("[TRANSFORM]   Finished feature: %s with %d scenarios", feature_model.name, len(scenarios))
        features.append(feature_model)

    logger.debug("[TRANSFORM] Completed transformation with %d features", len(features))
    return features

# def transform_cucumber_json_to_internal_model(raw_features: List[Dict[str, Any]], project_id: str) -> List[Feature]:
#     features: List[Feature] = []
#     logger.debug("[TRANSFORM] Starting Cucumber to internal model transformation")
#
#     # Safety check
#     if not isinstance(raw_features[0], dict):
#         raise TypeError(f"Expected raw dicts, got {type(raw_features[0])}")
#
#     for raw_feature in raw_features:
#         logger.debug("[TRANSFORM] Processing feature: %s", raw_feature.get("name"))
#         feature_id = str(uuid4())
#         feature_uri = raw_feature.get("uri", "")
#         scenarios: List[Scenario] = []
#
#         for element in raw_feature.get("elements", []):
#             logger.debug("[TRANSFORM]   Element: %s", element.get("name"))
#
#             steps: List[Step] = []
#             for idx, step in enumerate(element.get("steps", [])):
#                 result = step.get("result", {})
#                 duration = result.get("duration", 0.0)
#                 if duration > 1_000_000_000:
#                     duration = duration / 1_000_000_000.0
#
#                 step_status = map_status(result.get("status"))
#
#                 step_model = Step(
#                     id=str(uuid4()),
#                     external_id=None,
#                     keyword=step.get("keyword", ""),
#                     name=step.get("name", "Unnamed Step"),
#                     status=step_status,
#                     duration=duration,
#                     error_message=result.get("error_message"),
#                     stack_trace=result.get("stack_trace"),
#                     embeddings=[],
#                     order=str(uuid4()),
#                     start_time=None,
#                     end_time=None,
#                     created_at=now_utc(),
#                     updated_at=now_utc(),
#                     scenario_id=None,
#                 )
#                 steps.append(step_model)
#
#             # Extract tags with line numbers
#             tags = []
#             tag_metadata = {}  # Dictionary to store tag metadata including line numbers
#
#             for tag_obj in element.get("tags", []):
#                 if isinstance(tag_obj, dict) and "name" in tag_obj:
#                     tag_name = tag_obj["name"]
#                     tags.append(tag_name)
#
#                     # Store metadata including line number
#                     tag_metadata[tag_name] = {
#                         'line': tag_obj.get("line")
#                     }
#
#             logger.debug(f"[TRANSFORM] Extracted tags for {element.get('name')}: {tags} with metadata: {tag_metadata}")
#
#             scenario_status = calculate_overall_status(steps)
#             scenario_model = Scenario(
#                 id=str(uuid4()),
#                 external_id=element.get("id"),
#                 name=element.get("name", "Unnamed Scenario"),
#                 description=element.get("description", ""),
#                 status=scenario_status,
#                 duration=sum(s.duration or 0.0 for s in steps),
#                 steps=steps,
#                 tags=tags,
#                 tag_metadata=tag_metadata,  # Add tag metadata with line numbers
#                 is_flaky="@flaky" in [tag.get("name") for tag in element.get("tags", []) if isinstance(tag, dict)],
#                 embeddings=[],
#                 created_at=now_utc(),
#                 updated_at=now_utc(),
#                 feature_id=feature_id,
#                 test_run_id=None,
#                 feature_file=feature_uri,  # Set feature_file to the URI
#             )
#
#             scenarios.append(scenario_model)
#
#         feature_model = Feature(
#             id=feature_id,
#             external_id=feature_id,
#             name=raw_feature.get("name", "Unnamed Feature"),
#             description=raw_feature.get("description", ""),
#             file_path=raw_feature.get("uri", ""),
#             tags=[tag.get("name") for tag in raw_feature.get("tags", []) if isinstance(tag, dict)],
#             created_at=now_utc(),
#             updated_at=now_utc(),
#             scenarios=scenarios,
#             project_id=str(project_id),
#         )
#
#         logger.debug("[TRANSFORM]   Finished feature: %s with %d scenarios", feature_model.name, len(scenarios))
#         features.append(feature_model)
#
#     logger.debug("[TRANSFORM] Completed transformation with %d features", len(features))
#     return features

def map_status(status: str) -> TestStatus:
    status = status.lower() if status else "unknown"
    if status == "passed":
        return TestStatus.PASSED
    elif status == "failed":
        return TestStatus.FAILED
    elif status in ("skipped", "pending"):
        return TestStatus.SKIPPED
    return TestStatus.UNKNOWN

def calculate_overall_status(steps: List[Step]) -> TestStatus:
    if any(s.status == TestStatus.FAILED for s in steps):
        return TestStatus.FAILED
    if all(s.status == TestStatus.PASSED for s in steps):
        return TestStatus.PASSED
    return TestStatus.SKIPPED

def _normalize_tags(tags: List[Any]) -> List[str]:
    normalized = []
    for tag in tags:
        if isinstance(tag, str):
            normalized.append(tag.strip("@"))
        elif isinstance(tag, dict) and "name" in tag:
            normalized.append(tag["name"].strip("@"))
    return normalized


def map_cucumber_status(cucumber_status: str) -> TestStatus:
    """Map cucumber step status to our TestStatus enum."""
    if cucumber_status == "passed":
        return TestStatus.PASSED
    elif cucumber_status == "failed":
        return TestStatus.FAILED
    elif cucumber_status == "skipped":
        return TestStatus.SKIPPED
    else:
        return TestStatus.UNKNOWN


def ensure_metadata_defaults(metadata: ReportMetadata) -> ReportMetadata:
    """
    Ensure all required metadata fields have default fallbacks.
    """
    if not metadata.environment:
        metadata.environment = "UNKNOWN"
    if not metadata.branch:
        metadata.branch = "UNKNOWN"
    if not metadata.commit:
        metadata.commit = "UNKNOWN"
    if not metadata.runner:
        metadata.runner = "UNKNOWN"
    if not metadata.timestamp:
        metadata.timestamp = now_utc()
    return metadata