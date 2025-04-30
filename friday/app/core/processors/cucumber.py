"""
Cucumber report processor for Friday
"""
import json
import uuid
from datetime import datetime
from typing import Dict, List, Any

from app.core.processors.base import BaseProcessor
from app.models.domain import ChunkMetadata, Feature, Scenario, Step, TestRun, TestStatus
from app.services import datetime_service as dt


class CucumberProcessor(BaseProcessor):
    """Processor for Cucumber test reports"""

    async def process(self, data: List[bytes], metadata: Dict) -> Dict:
        """
        Process Cucumber test reports

        Args:
            data: List of Cucumber JSON reports as bytes
            metadata: Additional metadata (build_id, tags, etc.)

        Returns:
            Processing results with test run ID and statistics
        """
        # Parse JSON reports
        parsed_reports = []
        for report_bytes in data:
            try:
                report_json = json.loads(report_bytes.decode('utf-8'))
                parsed_reports.append(report_json)
            except json.JSONDecodeError:
                # Log error and continue with other reports
                continue

        if not parsed_reports:
            return {
                "success": False,
                "message": "No valid Cucumber reports found"
            }

        # Process reports into domain models
        features = []
        for report in parsed_reports:
            features.extend(self._parse_features(report))

        # Create test run
        test_run_id = str(uuid.uuid4())
        test_run = TestRun(
            id=test_run_id,
            timestamp=dt.now_utc(),
            features=features,
            build_info=None,  # Will be linked later with build info processor
            tags=metadata.get("tags", []),
            metadata=metadata.get("metadata", {})
        )

        # Process features and scenarios for RAG
        await self._process_test_run_for_rag(test_run)

        return {
            "test_run_id": test_run_id,
            "processed_features": len(test_run.features),
            "processed_scenarios": test_run.total_scenarios,
            "success": True,
            "message": "Successfully processed Cucumber reports"
        }

    def _parse_features(self, report: List[Dict]) -> List[Feature]:
        """
        Parse features from a Cucumber report

        Args:
            report: Cucumber report JSON

        Returns:
            List of Feature domain models
        """
        features = []

        for feature_json in report:
            # Parse feature
            feature_id = feature_json.get("id", str(uuid.uuid4()))
            feature_name = feature_json.get("name", "Unnamed Feature")
            feature_description = feature_json.get("description", "")
            feature_tags = [
                tag.get("name", "")
                for tag in feature_json.get("tags", [])
            ]

            # Parse scenarios
            scenarios = []
            for element in feature_json.get("elements", []):
                if element.get("type") not in ["scenario", "scenario_outline"]:
                    continue

                scenario_id = element.get("id", str(uuid.uuid4()))
                scenario_name = element.get("name", "Unnamed Scenario")
                scenario_description = element.get("description", "")
                scenario_tags = [
                    tag.get("name", "")
                    for tag in element.get("tags", [])
                ]

                # Parse steps
                steps = []
                for step_json in element.get("steps", []):
                    keyword = step_json.get("keyword", "").strip()
                    name = step_json.get("name", "")

                    # Parse result
                    result = step_json.get("result", {})
                    status_str = result.get("status", "undefined")
                    try:
                        status = TestStatus(status_str)
                    except ValueError:
                        status = TestStatus.UNDEFINED

                    duration = result.get("duration", 0)
                    error_message = result.get("error_message", None)

                    # Create step
                    step = Step(
                        name=name,
                        status=status,
                        duration=duration,
                        error_message=error_message,
                        keyword=keyword,
                        location=step_json.get("match", {}).get("location", "")
                    )
                    steps.append(step)

                # Determine scenario status based on steps
                if any(step.status == TestStatus.FAILED for step in steps):
                    scenario_status = TestStatus.FAILED
                elif any(step.status == TestStatus.UNDEFINED for step in steps):
                    scenario_status = TestStatus.UNDEFINED
                elif any(step.status == TestStatus.PENDING for step in steps):
                    scenario_status = TestStatus.PENDING
                elif any(step.status == TestStatus.SKIPPED for step in steps):
                    scenario_status = TestStatus.SKIPPED
                else:
                    scenario_status = TestStatus.PASSED

                # Create scenario
                scenario = Scenario(
                    id=scenario_id,
                    name=scenario_name,
                    description=scenario_description,
                    status=scenario_status,
                    steps=steps,
                    tags=scenario_tags
                )
                scenarios.append(scenario)

            # Create feature
            feature = Feature(
                id=feature_id,
                name=feature_name,
                description=feature_description,
                file_path=feature_json.get("uri", ""),
                scenarios=scenarios,
                tags=feature_tags
            )
            features.append(feature)

        return features

    async def _process_test_run_for_rag(self, test_run: TestRun) -> None:
        """
        Process a test run for RAG by chunking and embedding

        Args:
            test_run: Test run to process
        """
        build_id = test_run.build_info.build_id if test_run.build_info else None

        # Process each feature
        for feature in test_run.features:
            # Feature metadata
            feature_metadata = ChunkMetadata(
                test_run_id=test_run.id,
                feature_id=feature.id,
                scenario_id=None,
                build_id=build_id,
                chunk_type="feature",
                tags=feature.tags
            )

            # Process feature text
            feature_text = f"Feature: {feature.name}\n\n{feature.description}"
            await self.process_text(feature_text, feature_metadata.dict())

            # Process each scenario
            for scenario in feature.scenarios:
                # Scenario metadata
                scenario_metadata = ChunkMetadata(
                    test_run_id=test_run.id,
                    feature_id=feature.id,
                    scenario_id=scenario.id,
                    build_id=build_id,
                    chunk_type="scenario",
                    tags=feature.tags + scenario.tags
                )

                # Process scenario text
                steps_text = "\n".join([
                    f"{step.keyword} {step.name}"
                    for step in scenario.steps
                ])

                scenario_text = f"Scenario: {scenario.name}\n"
                if scenario.description:
                    scenario_text += f"{scenario.description}\n\n"
                scenario_text += steps_text

                await self.process_text(scenario_text, scenario_metadata.dict())

                # Process errors separately for easier retrieval
                error_steps = [
                    step for step in scenario.steps
                    if step.status == TestStatus.FAILED and step.error_message
                ]

                if error_steps:
                    error_metadata = ChunkMetadata(
                        test_run_id=test_run.id,
                        feature_id=feature.id,
                        scenario_id=scenario.id,
                        build_id=build_id,
                        chunk_type="error",
                        tags=feature.tags + scenario.tags
                    )

                    for step in error_steps:
                        error_text = f"Error in '{step.keyword} {step.name}':\n{step.error_message}"
                        await self.process_text(error_text, error_metadata.dict())