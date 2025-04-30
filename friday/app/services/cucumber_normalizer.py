from typing import Dict, Any

class CucumberNormalizerService:
    """
    Service to normalize raw Cucumber JSON payloads into a structure
    compatible with internal ingestion models.
    """

    @staticmethod
    def normalize_cucumber_payload(raw_payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize a raw Cucumber JSON payload.

        - Converts 'elements' to 'scenarios'.
        - Flattens feature and scenario tags into string lists.
        - Calculates scenario status based on step outcomes.
        """
        normalized_report = []

        for feature in raw_payload.get("report", []):
            feature_tags = [tag.get("name", "") for tag in feature.get("tags", [])]

            normalized_feature = {
                "id": feature.get("external_id") or feature.get("id"),
                "external_id": feature.get("id"),
                "name": feature.get("name", ""),
                "description": feature.get("description", ""),
                "tags": feature_tags,
                "uri": feature.get("uri", ""),
                "scenarios": [],
            }

            for element in feature.get("elements", []):
                scenario_tags = [tag.get("name", "") for tag in element.get("tags", [])]
                steps = []

                for step in element.get("steps", []):
                    result = step.get("result", {})
                    normalized_step = {
                        "name": step.get("name", ""),
                        "keyword": step.get("keyword", ""),
                        "status": result.get("status", "unknown"),
                        "duration": result.get("duration", 0) / 1000,  # convert microseconds to ms
                        "error_message": result.get("error_message"),
                        "stack_trace": result.get("stack_trace"),
                    }
                    steps.append(normalized_step)

                # Determine scenario status from steps
                step_statuses = {step["status"] for step in steps}
                if "failed" in step_statuses:
                    scenario_status = "FAILED"
                elif "passed" in step_statuses:
                    scenario_status = "PASSED"
                else:
                    scenario_status = "UNKNOWN"

                normalized_scenario = {
                    "id": element.get("id"),
                    "name": element.get("name", ""),
                    "description": element.get("description", ""),
                    "tags": scenario_tags,
                    "status": scenario_status,
                    "steps": steps,
                }

                normalized_feature["scenarios"].append(normalized_scenario)

            normalized_report.append(normalized_feature)

        return {
            "metadata": raw_payload.get("metadata", {}),
            "report": normalized_report,
        }

