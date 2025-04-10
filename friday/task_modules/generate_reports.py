#!/usr/bin/env python3
"""
Cucumber Report Generator for Friday Dashboard

This script generates realistic Cucumber JSON payloads from feature files
and posts them to the /processor/cucumber endpoint.
"""

import os
import sys
import json
import random
import uuid
import argparse
import datetime
import requests
from pathlib import Path
from typing import List, Dict, Any

# Configuration - adjust these values as needed
API_URL = "http://localhost:4000/api/v1/processor/cucumber"
FEATURE_DIR = "./features"  # Directory containing the feature files
OUTPUT_DIR = "./generated_reports"  # Directory to save generated reports


class CucumberReportGenerator:
    """Generate realistic Cucumber JSON reports from feature files."""

    def __init__(self, feature_dir: str, output_dir: str):
        """Initialize the generator with paths to feature files and output directory."""
        self.feature_dir = Path(feature_dir)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Common tags to randomly assign to scenarios
        self.common_tags = [
            "@regression", "@smoke", "@ui", "@critical", "@minor",
            "@major", "@high", "@medium", "@low", "@flaky",
            "@sprint-22", "@sprint-23", "@sprint-24", "@automated",
            "@jira-456", "@jira-789", "@jira-123", "@frontend",
            "@checkout", "@payment", "@catalog", "@account", "@authentication"
        ]

        # Project names for report metadata
        self.project_names = ["e-commerce", "online-store", "web-shop", "retail-platform"]

        # Branch names for report metadata
        self.branch_names = ["main", "develop", "feature/checkout-redesign", "feature/user-auth",
                             "bugfix/payment-issue"]

        # Environments for report metadata
        self.environments = ["dev", "staging", "qa", "production", "integration"]

        # Error messages to use for failures
        self.error_messages = [
            "Element not found: #product-list",
            "Expected element to be visible but it was not",
            "Timeout waiting for element .checkout-button",
            "Assertion failed: expected 'Success' but got 'Error'",
            "Network request failed: 404 Not Found",
            "Database connection error: timeout after 30s",
            "Expected redirect to '/confirmation' but got '/error'",
            "API returned 500 Internal Server Error",
            "Expected text 'Order Confirmed' was not found",
            "Element <button id='submit'> is not clickable at point (123, 456)"
        ]

        # Stack traces to use for failures
        self.stack_traces = [
            """org.openqa.selenium.NoSuchElementException: no such element: Unable to locate element: {"method":"css selector","selector":"#product-list"}
  (Session info: chrome=120.0.6099.130)
  at java.base/jdk.internal.reflect.NativeConstructorAccessorImpl.newInstance0(Native Method)
  at java.base/jdk.internal.reflect.NativeConstructorAccessorImpl.newInstance(NativeConstructorAccessorImpl.java:62)
  at steps.ProductSteps.theProductListShouldBeVisible(ProductSteps.java:42)""",

            """java.lang.AssertionError: expected [Success] but found [Error]
  at org.testng.Assert.fail(Assert.java:96)
  at org.testng.Assert.failNotEquals(Assert.java:776)
  at org.testng.Assert.assertEquals(Assert.java:90)
  at steps.PaymentSteps.paymentShouldSucceed(PaymentSteps.java:67)""",

            """org.openqa.selenium.TimeoutException: Expected condition failed: waiting for visibility of element located by By.cssSelector: .checkout-button (tried for 10 second(s) with 500 milliseconds interval)
  at org.openqa.selenium.support.ui.WebDriverWait.timeoutException(WebDriverWait.java:95)
  at org.openqa.selenium.support.ui.FluentWait.until(FluentWait.java:272)
  at steps.CheckoutSteps.clickCheckoutButton(CheckoutSteps.java:29)"""
        ]

    def _parse_feature_file(self, file_path: Path) -> Dict[str, Any]:
        """Parse a feature file into a structured dictionary."""
        with open(file_path, 'r') as f:
            content = f.read()

        lines = content.strip().split('\n')

        # Extract feature information
        feature_line = next((line for line in lines if line.strip().startswith("Feature:")), "Feature: Unknown")
        feature_name = feature_line.replace("Feature:", "").strip()
        feature_id = str(uuid.uuid4())

        # Find scenarios
        scenarios = []
        current_feature = feature_name

        i = 0
        while i < len(lines):
            line = lines[i].strip()

            # Check for new feature within the same file
            if line.startswith("Feature:") and i > 0:
                current_feature = line.replace("Feature:", "").strip()

            # Check for scenario
            if line.startswith("Scenario:"):
                scenario_name = line.replace("Scenario:", "").strip()
                scenario_id = str(uuid.uuid4())
                scenario_line = i + 1

                # Add tags to scenario (if any)
                tags = []
                if i > 0 and lines[i - 1].strip().startswith("@"):
                    tag_line = lines[i - 1].strip()
                    tags = [{"name": tag, "line": scenario_line - 1} for tag in tag_line.split()]

                # Randomly add 1-4 common tags if no tags were present
                if not tags:
                    num_tags = random.randint(1, 4)
                    selected_tags = random.sample(self.common_tags, num_tags)
                    tags = [{"name": tag, "line": scenario_line - 1} for tag in selected_tags]

                # Find steps
                steps = []
                step_index = i + 1

                while step_index < len(lines) and step_index < len(lines) and \
                        lines[step_index].strip() and not lines[step_index].strip().startswith("Scenario:") and \
                        not lines[step_index].strip().startswith("Feature:") and \
                        not lines[step_index].strip().startswith("@"):

                    step_line = lines[step_index].strip()

                    if step_line and any(
                            step_line.startswith(keyword) for keyword in ["Given ", "When ", "Then ", "And ", "But "]):
                        # Extract keyword and name
                        keyword_end = step_line.find(' ')
                        keyword = step_line[:keyword_end].strip()
                        name = step_line[keyword_end:].strip()

                        steps.append({
                            "keyword": keyword,
                            "name": name,
                            "line": step_index + 1
                        })

                    step_index += 1

                scenarios.append({
                    "id": scenario_id,
                    "name": scenario_name,
                    "line": scenario_line,
                    "description": "",
                    "keyword": "Scenario",
                    "type": "scenario",
                    "tags": tags,
                    "steps": steps,
                    "feature": current_feature  # Track which feature this scenario belongs to
                })

                i = step_index - 1

            i += 1

        return {
            "id": feature_id,
            "name": feature_name,
            "uri": file_path.name,
            "line": 1,
            "keyword": "Feature",
            "scenarios": scenarios
        }

    def _generate_step_result(self, step: Dict[str, Any], should_fail: bool = False) -> Dict[str, Any]:
        """Generate a realistic result for a step, including pass/fail/skipped status."""
        # Decide status
        if should_fail:
            status = "failed"
            # Choose a random error message and stack trace
            error_message = random.choice(self.error_messages)
            stack_trace = random.choice(self.stack_traces)
            duration = random.randint(500, 5000) * 1_000_000  # Duration in nanoseconds
        else:
            # Most steps pass, but some might be skipped
            status_options = ["passed"] * 9 + ["skipped"]
            status = random.choice(status_options)
            error_message = None
            stack_trace = None

            if status == "passed":
                # Passed steps have a duration
                duration = random.randint(50, 3000) * 1_000_000  # Duration in nanoseconds
            else:
                # Skipped steps have no duration
                duration = 0

        result = {
            "status": status,
            "duration": duration
        }

        if error_message:
            result["error_message"] = error_message

        if stack_trace:
            result["stack_trace"] = stack_trace

        # Create a complete step with result
        complete_step = step.copy()
        complete_step["result"] = result

        # Add a match field (location where the step is implemented)
        complete_step["match"] = {
            "location": f"steps.{step['keyword'].strip().lower()}Steps.java:{random.randint(10, 100)}"
        }

        return complete_step

    def _generate_scenario_results(self, scenario: Dict[str, Any]) -> Dict[str, Any]:
        """Generate realistic results for a scenario and its steps."""
        # Decide if this scenario should fail
        # 15% of scenarios fail
        should_fail = random.random() < 0.15

        # If scenario has a @flaky tag, increase chance of failure to 30%
        if any(tag["name"] == "@flaky" for tag in scenario["tags"]):
            should_fail = random.random() < 0.30

        # Process steps
        complete_steps = []
        failed_step_index = -1

        if should_fail:
            # If scenario should fail, randomly select which step will fail
            failed_step_index = random.randint(0, len(scenario["steps"]) - 1)

        for i, step in enumerate(scenario["steps"]):
            # Steps after a failure are skipped
            if failed_step_index >= 0 and i > failed_step_index:
                step_result = self._generate_step_result(step, False)  # Will be skipped
                step_result["result"]["status"] = "skipped"
                step_result["result"]["duration"] = 0
                complete_steps.append(step_result)
            else:
                # This step should fail if it's the designated failure step
                should_step_fail = (i == failed_step_index)
                complete_steps.append(self._generate_step_result(step, should_step_fail))

        # Create complete scenario with steps
        complete_scenario = scenario.copy()
        complete_scenario["steps"] = complete_steps

        # Remove temporary 'feature' field used during parsing
        feature_name = complete_scenario.pop("feature", None)

        return complete_scenario, feature_name

    def generate_report(self, timestamp: datetime.datetime = None, project: str = None) -> Dict[str, Any]:
        """
        Generate a complete Cucumber JSON report from feature files.

        Args:
            timestamp: Optional specific timestamp for the report
            project: Optional specific project name
        """
        # Load and parse all feature files
        feature_files = []
        for file_path in self.feature_dir.glob("*.feature"):
            feature_files.append(file_path)

        if not feature_files:
            raise ValueError(f"No feature files found in {self.feature_dir}")

        # Select a subset of feature files for this report
        num_features = min(random.randint(1, 5), len(feature_files))
        selected_features = random.sample(feature_files, num_features)

        # Parse selected feature files
        parsed_features = [self._parse_feature_file(file) for file in selected_features]

        # Group scenarios by feature
        feature_elements = {}

        for feature_data in parsed_features:
            for scenario in feature_data["scenarios"]:
                # Generate results for this scenario
                complete_scenario, feature_name = self._generate_scenario_results(scenario)

                # Find the correct feature to add this scenario to
                for f in parsed_features:
                    if f["name"] == feature_name:
                        if f["id"] not in feature_elements:
                            feature_elements[f["id"]] = {
                                "id": f["id"],
                                "name": f["name"],
                                "uri": f["uri"],
                                "line": f["line"],
                                "keyword": f["keyword"],
                                "elements": []
                            }

                        # Add this scenario to the feature
                        feature_elements[f["id"]]["elements"].append(complete_scenario)
                        break

        # Create the final report structure
        features = list(feature_elements.values())

        # Generate report metadata
        if timestamp is None:
            timestamp = datetime.datetime.now().replace(microsecond=0)

        timestamp_str = timestamp.isoformat()

        metadata = {
            "project": project if project else random.choice(self.project_names),
            "branch": random.choice(self.branch_names),
            "commit": uuid.uuid4().hex[:7],
            "timestamp": timestamp_str,
            "runner": "cucumber-junit"
        }

        # Add a random tag to the environment field
        metadata["environment"] = random.choice(self.environments)

        return {
            "metadata": metadata,
            "report": features
        }

    def generate_multiple_reports(self, count: int, date_range: bool = False,
                                  same_project: bool = False) -> List[Dict[str, Any]]:
        """
        Generate multiple Cucumber reports.

        Args:
            count: Number of reports to generate
            date_range: If True, distribute reports over the last 7 days
            same_project: If True, use the same project for all reports
        """
        reports = []

        # If using same project, select it now
        project = random.choice(self.project_names) if same_project else None

        for i in range(count):
            timestamp = None

            # If generating reports over a date range
            if date_range:
                # Calculate a random timestamp in the last 7 days
                days_ago = random.randint(0, 6)
                random_hour = random.randint(0, 23)
                random_minute = random.randint(0, 59)

                timestamp = datetime.datetime.now().replace(
                    hour=random_hour,
                    minute=random_minute,
                    second=0,
                    microsecond=0
                ) - datetime.timedelta(days=days_ago)

            reports.append(self.generate_report(timestamp=timestamp, project=project))

        return reports

    def save_reports(self, reports: List[Dict[str, Any]]) -> List[str]:
        """Save generated reports to the output directory and return file paths."""
        saved_paths = []
        for i, report in enumerate(reports):
            timestamp = report["metadata"]["timestamp"].replace(":", "-")
            filename = f"cucumber_report_{i + 1}_{timestamp}.json"
            filepath = self.output_dir / filename

            with open(filepath, 'w') as f:
                json.dump(report, f, indent=2)

            saved_paths.append(str(filepath))
            print(f"Saved report to {filepath}")

        return saved_paths

    def post_reports_to_api(self, reports: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Post reports to the API and return the responses."""
        responses = []

        for i, report in enumerate(reports):
            print(f"Posting report {i + 1}/{len(reports)} to {API_URL}...")

            try:
                response = requests.post(API_URL, json=report)
                response_data = response.json()

                print(f"  Status code: {response.status_code}")
                print(f"  Response: {response_data}")

                responses.append(response_data)

                # Add a small delay between requests
                if i < len(reports) - 1:
                    print("  Waiting 1 second before next request...")
                    import time
                    time.sleep(1)

            except Exception as e:
                print(f"  Error posting report: {e}")
                responses.append({"error": str(e)})

        return responses


def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(description="Generate and post Cucumber JSON reports")
    parser.add_argument("--count", type=int, default=3, help="Number of reports to generate")
    parser.add_argument("--feature-dir", type=str, default=FEATURE_DIR, help="Directory containing feature files")
    parser.add_argument("--output-dir", type=str, default=OUTPUT_DIR, help="Directory to save generated reports")
    parser.add_argument("--post", action="store_true", help="Post reports to the API")
    parser.add_argument("--api-url", type=str, default="http://localhost:4000/api/v1/processor/cucumber",
                        help="API endpoint URL")
    parser.add_argument("--date-range", action="store_true", help="Distribute reports over the last 7 days")
    parser.add_argument("--same-project", action="store_true", help="Use the same project for all reports")

    args = parser.parse_args()

    try:
        # Update global API_URL if provided
        global API_URL
        if args.api_url:
            API_URL = args.api_url

        # Initialize the generator
        generator = CucumberReportGenerator(args.feature_dir, args.output_dir)

        # Generate reports
        print(f"Generating {args.count} Cucumber reports...")
        if args.date_range:
            print("Distributing reports over the last 7 days")
        if args.same_project:
            print("Using the same project for all reports")

        reports = generator.generate_multiple_reports(
            args.count,
            date_range=args.date_range,
            same_project=args.same_project
        )

        # Save reports
        saved_paths = generator.save_reports(reports)

        # Post reports to API if requested
        if args.post:
            print("\nPosting reports to API...")
            responses = generator.post_reports_to_api(reports)

            print("\nAPI Response Summary:")
            for i, response in enumerate(responses):
                report_id = response.get("report_id", "N/A")
                status = response.get("status", "error")
                print(f"Report {i + 1}: Status={status}, ID={report_id}")

        print("\nDone!")

    except Exception as e:
        print(f"Error: {e}")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())