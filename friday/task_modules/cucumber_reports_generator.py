#!/usr/bin/env python3
"""
Cucumber Reports Generator

Generates realistic, randomized Cucumber JSON reports with failures based on provided
feature files, optimized for ingestion by the /processor/cucumber endpoint.
"""

import os
import json
import random
import datetime
import re
from typing import List, Dict, Any, Optional, Union, Tuple


class CucumberReportGenerator:
    """Main class for generating Cucumber JSON reports with realistic failures."""

    def __init__(self):
        """Initialize the generator with default values."""
        # Predefined options for random metadata generation
        self.project_names = [
            "WebApp", "MobileApp", "BackendAPI", "CustomerPortal", "AdminDashboard",
            "CheckoutSystem", "UserManagement", "InventorySystem", "PaymentGateway"
        ]

        self.branch_names = [
            "main", "develop", "staging", "master", "feature/new-login",
            "feature/payment-redesign", "hotfix/security-patch", "release/v2.0",
            "bugfix/cart-issue", "enhancement/search-filtering"
        ]

        self.runner_names = [
            "cucumber-jvm", "cucumber-js", "cypress", "behave",
            "specflow", "cucumber-ruby", "behat", "serenity"
        ]

    def parse_feature_files(self, feature_contents: List[str]) -> List[Dict[str, Any]]:
        """
        Parse Cucumber feature files into a structured format.

        Args:
            feature_contents: List of feature file contents as strings

        Returns:
            List of structured feature objects
        """
        features = []

        for idx, content in enumerate(feature_contents):
            lines = content.strip().split('\n')
            current_feature = None
            current_scenario = None
            line_number = 1

            for line in lines:
                trimmed_line = line.strip()

                # Parse Feature
                if trimmed_line.startswith('Feature:'):
                    feature_name = trimmed_line[len('Feature:'):].strip()
                    feature_id = f"feature-{idx}-{self._slugify(feature_name)}"

                    current_feature = {
                        "uri": f"feature-file-{idx}.feature",
                        "id": feature_id,
                        "keyword": "Feature",
                        "name": feature_name,
                        "description": "",
                        "line": line_number,
                        "elements": []
                    }

                    features.append(current_feature)

                # Parse Scenario
                elif trimmed_line.startswith('Scenario:') and current_feature:
                    scenario_name = trimmed_line[len('Scenario:'):].strip()
                    scenario_id = f"scenario-{len(current_feature['elements'])}-{self._slugify(scenario_name)}"

                    current_scenario = {
                        "id": scenario_id,
                        "keyword": "Scenario",
                        "name": scenario_name,
                        "description": "",
                        "line": line_number,
                        "type": "scenario",
                        "steps": []
                    }

                    current_feature['elements'].append(current_scenario)

                # Parse Steps
                elif (any(trimmed_line.startswith(keyword) for keyword in
                          ['Given ', 'When ', 'Then ', 'And ', 'But ']) and
                      current_scenario):

                    # Extract keyword and step name
                    keyword = trimmed_line.split(' ')[0] + ' '
                    step_name = trimmed_line[len(keyword):].strip()

                    step = {
                        "keyword": keyword,
                        "name": step_name,
                        "line": line_number,
                        "result": {
                            "status": "passed"
                        }
                    }

                    current_scenario['steps'].append(step)

                line_number += 1

        return features

    def _slugify(self, text: str) -> str:
        """
        Convert text to a URL-friendly slug.

        Args:
            text: The string to convert

        Returns:
            A URL-friendly version of the string
        """
        return re.sub(r'[^a-z0-9]+', '-', text.lower()).strip('-')

    def generate_random_commit_hash(self) -> str:
        """
        Generate a random commit hash.

        Returns:
            A random 7-character git-like commit hash
        """
        return ''.join(random.choice('0123456789abcdef') for _ in range(7))

    def generate_realistic_error_message(self, step: Dict[str, Any]) -> str:
        """
        Generate a realistic error message based on step content.

        Args:
            step: The step dict containing the name and other properties

        Returns:
            A realistic error message string
        """
        step_text = step['name'].lower()

        # Common error messages for any step
        common_errors = [
            "Assertion failed: Expected element to be visible",
            "Timeout waiting for element to appear",
            "Element not found in DOM",
            "Expected 'success' but got 'error'",
            "Network request failed with status 500",
            "Unexpected alert present",
            "Unable to click on element",
            "Connection refused",
            "Expected true but got false",
            "Element is not clickable at point (X, Y)"
        ]

        # More specific errors based on step content
        if 'login' in step_text:
            specific_errors = [
                "Authentication failed: Invalid credentials",
                "Login form submission failed",
                "Session could not be established",
                "Expected to be redirected to dashboard but remained on login page"
            ]
            return random.choice(specific_errors)

        elif 'click' in step_text:
            specific_errors = [
                "Element is not clickable at point (120, 380)",
                "Button is disabled or not interactable",
                "Element not found: button",
                "Unexpected alert prevented click operation"
            ]
            return random.choice(specific_errors)

        elif 'enter' in step_text or 'input' in step_text:
            specific_errors = [
                "Input field is disabled or read-only",
                "Cannot focus on input element",
                "Invalid input value rejected by validation",
                "Form submission failed due to validation errors"
            ]
            return random.choice(specific_errors)

        elif 'see' in step_text or 'display' in step_text:
            specific_errors = [
                "Expected text not found on page",
                "Element was present but not visible",
                "Timeout waiting for text to appear",
                "Expected content missing from response"
            ]
            return random.choice(specific_errors)

        elif 'navigate' in step_text or 'redirect' in step_text:
            specific_errors = [
                "Navigation timeout after 30000ms",
                "Expected URL to contain 'dashboard' but got 'error'",
                "Unexpected redirection to login page",
                "Page load failed with status 404"
            ]
            return random.choice(specific_errors)

        # Default to common errors
        return random.choice(common_errors)

    def apply_failures(
            self,
            features: List[Dict[str, Any]],
            failure_rate: float,
            failure_distribution: str
    ) -> List[Dict[str, Any]]:
        """
        Apply failures to scenarios based on specified distribution pattern.

        Args:
            features: The parsed feature objects
            failure_rate: Percentage of scenarios that should fail (0.0-1.0)
            failure_distribution: How failures are distributed ('uniform', 'increasing', etc.)

        Returns:
            Features with failures applied according to the distribution
        """
        # Create a deep copy to avoid modifying the original
        features = json.loads(json.dumps(features))

        # Collect all scenarios
        all_scenarios = []
        for feature in features:
            for scenario in feature['elements']:
                all_scenarios.append({
                    'feature': feature,
                    'scenario': scenario
                })

        total_scenarios = len(all_scenarios)
        number_of_failures = round(total_scenarios * failure_rate)

        if number_of_failures == 0:
            return features

        # Apply different sorting/selection strategies based on distribution
        failing_scenarios = []

        if failure_distribution == "uniform":
            # Random selection
            indices = list(range(total_scenarios))
            random.shuffle(indices)
            failing_scenarios = [all_scenarios[i] for i in indices[:number_of_failures]]

        elif failure_distribution == "increasing":
            # Weight towards later scenarios
            for _ in range(number_of_failures):
                # Square of random value biases towards 1.0
                random_value = random.random() * random.random()
                # Convert to an index biased towards the end
                index = min(int((1 - random_value) * total_scenarios), total_scenarios - 1)
                failing_scenarios.append(all_scenarios[index])

        elif failure_distribution == "decreasing":
            # Weight towards earlier scenarios
            for _ in range(number_of_failures):
                # Square of random value biases towards 0.0
                random_value = random.random() * random.random()
                # Use directly as index biased towards the beginning
                index = min(int(random_value * total_scenarios), total_scenarios - 1)
                failing_scenarios.append(all_scenarios[index])

        elif failure_distribution == "clustered":
            # Select a few cluster starting points and expand from there
            number_of_clusters = max(1, round(number_of_failures / 3))
            cluster_start_indices = [random.randint(0, total_scenarios - 1) for _ in range(number_of_clusters)]

            remaining_failures = number_of_failures
            cluster_size = remaining_failures // number_of_clusters

            for cluster_index in cluster_start_indices:
                for i in range(cluster_size):
                    if remaining_failures <= 0:
                        break

                    scenario_index = (cluster_index + i) % total_scenarios
                    failing_scenarios.append(all_scenarios[scenario_index])
                    remaining_failures -= 1

                if remaining_failures <= 0:
                    break

                # Recalculate cluster size for remaining clusters
                if number_of_clusters > 1:
                    cluster_size = remaining_failures // (number_of_clusters - 1)
                    number_of_clusters -= 1

        # Apply failures to the selected scenarios
        for failure in failing_scenarios:
            scenario = failure['scenario']

            # Random number of failing steps (at least 1)
            num_failing_steps = max(1, random.randint(1, len(scenario['steps'])))

            # Select random steps to fail
            step_indices = list(range(len(scenario['steps'])))
            random.shuffle(step_indices)
            failing_step_indices = step_indices[:num_failing_steps]

            # Mark steps as failed
            for step_index in failing_step_indices:
                step = scenario['steps'][step_index]
                step['result']['status'] = 'failed'
                step['result']['error_message'] = self.generate_realistic_error_message(step)

                # Mark subsequent steps as skipped
                for i in range(step_index + 1, len(scenario['steps'])):
                    scenario['steps'][i]['result']['status'] = 'skipped'

        # Add some flakiness - small probability of non-failing scenarios having skipped/pending steps
        for entry in all_scenarios:
            scenario = entry['scenario']

            # Skip already failing scenarios
            if any(step['result']['status'] == 'failed' for step in scenario['steps']):
                continue

            for step in scenario['steps']:
                rand = random.random()
                if rand < 0.01:
                    step['result']['status'] = 'skipped'
                elif rand < 0.02:
                    step['result']['status'] = 'pending'
                elif rand < 0.03:
                    step['result']['status'] = 'undefined'

        return features

    def generate_reports(self, options: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Generate Cucumber JSON reports based on provided options.

        Args:
            options: Dictionary of configuration options

        Returns:
            List of generated report objects
        """
        feature_files = options.get('feature_files', [])
        days = options.get('days', 7)
        runs_per_day = options.get('runs_per_day', 3)
        failure_rate = options.get('failure_rate', 0.1)
        failure_distribution = options.get('failure_distribution', 'uniform')
        output_format = options.get('output_format', 'format1')

        # Parse feature files
        parsed_features = self.parse_feature_files(feature_files)

        # Generate reports
        reports = []
        base_date = datetime.datetime.now()

        # For each day
        for day in range(days):
            current_date = base_date - datetime.timedelta(days=days - day - 1)

            # For each run per day
            for run in range(runs_per_day):
                run_time = datetime.datetime(
                    year=current_date.year,
                    month=current_date.month,
                    day=current_date.day,
                    hour=8 + (9 * run) // runs_per_day,  # Distribute between 8am-5pm
                    minute=random.randint(0, 59)
                )

                # Create a deep copy of features to manipulate
                run_features = json.loads(json.dumps(parsed_features))

                # Apply failures based on distribution
                features_with_failures = self.apply_failures(
                    run_features,
                    failure_rate,
                    failure_distribution
                )

                # Generate metadata
                metadata = {
                    'project': options.get('project', random.choice(self.project_names)),
                    'branch': options.get('branch', random.choice(self.branch_names)),
                    'commit': options.get('commit', self.generate_random_commit_hash()),
                    'timestamp': run_time.isoformat(),
                    'runner': options.get('runner', random.choice(self.runner_names))
                }

                # Format according to chosen output format
                if output_format == 'format1':
                    report = {
                        'metadata': metadata,
                        'report': features_with_failures
                    }
                else:
                    report = features_with_failures

                reports.append(report)

        return reports


def read_feature_files(directory: str) -> List[str]:
    """
    Read all .feature files from a directory.

    Args:
        directory: Path to directory containing feature files

    Returns:
        List of feature file contents as strings
    """
    feature_files = []

    for filename in os.listdir(directory):
        if filename.endswith('.feature'):
            with open(os.path.join(directory, filename), 'r', encoding='utf-8') as f:
                feature_files.append(f.read())

    return feature_files


def ensure_directory_exists(directory: str) -> None:
    """
    Make sure a directory exists, creating it if necessary.

    Args:
        directory: Path to the directory
    """
    if not os.path.exists(directory):
        os.makedirs(directory, exist_ok=True)


def save_reports(reports: List[Dict[str, Any]], output_dir: str, single_file: bool = False) -> None:
    """
    Save generated reports to files.

    Args:
        reports: List of report objects
        output_dir: Directory to save reports to
        single_file: Whether to save all reports in a single file
    """
    ensure_directory_exists(output_dir)

    if single_file:
        # Save all reports to a single file
        output_file = os.path.join(output_dir, 'cucumber-reports.json')
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(reports, f, indent=2)
        print(f"All reports saved to {output_file}")
    else:
        # Save each report to a separate file
        for i, report in enumerate(reports):
            timestamp = report.get('metadata', {}).get('timestamp', datetime.datetime.now().isoformat())
            timestamp = timestamp.replace(':', '-').replace('.', '-')

            filename = f"report-{i + 1}-{timestamp}.json"
            output_file = os.path.join(output_dir, filename)

            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2)

        print(f"Reports saved to {output_dir}")


def generate(
        features_dir: str,
        output_dir: str,
        days: int = 7,
        runs_per_day: int = 3,
        failure_rate: float = 0.1,
        failure_distribution: str = 'uniform',
        project: Optional[str] = None,
        branch: Optional[str] = None,
        commit: Optional[str] = None,
        runner: Optional[str] = None,
        output_format: str = 'format1',
        single_file: bool = False
) -> None:
    """
    Main function to generate and save Cucumber reports.

    Args:
        features_dir: Directory containing feature files
        output_dir: Directory to save reports to
        days: Number of days to simulate
        runs_per_day: Number of test runs per day
        failure_rate: Percentage of scenarios that should fail (0.0-1.0)
        failure_distribution: How failures are distributed
        project: Project name (optional)
        branch: Git branch name (optional)
        commit: Git commit hash (optional)
        runner: Test runner (optional)
        output_format: Format of the generated reports ('format1' or 'format2')
        single_file: Whether to save all reports in a single file
    """
    print("Cucumber Reports Generator")
    print("-------------------------")

    # Read feature files
    print(f"Reading feature files from {features_dir}...")
    feature_files = read_feature_files(features_dir)

    if not feature_files:
        print(f"No .feature files found in {features_dir}")
        return

    print(f"Found {len(feature_files)} feature files")

    # Configure options for report generation
    options = {
        'feature_files': feature_files,
        'days': days,
        'runs_per_day': runs_per_day,
        'failure_rate': failure_rate,
        'failure_distribution': failure_distribution,
        'project': project,
        'branch': branch,
        'commit': commit,
        'runner': runner,
        'output_format': output_format
    }

    print(f"""Generating reports with:
  - Days: {days}
  - Runs per day: {runs_per_day}
  - Failure rate: {failure_rate * 100}%
  - Failure distribution: {failure_distribution}
  - Output format: {output_format}
    """)

    # Generate the reports
    generator = CucumberReportGenerator()
    reports = generator.generate_reports(options)

    print(f"Generated {len(reports)} reports")

    # Save reports
    save_reports(reports, output_dir, single_file)
    print("Done!")


if __name__ == "__main__":
    # Example usage
    generate(
        features_dir="./features",
        output_dir="./reports",
        days=7,
        runs_per_day=3,
        failure_rate=0.15,
        failure_distribution="uniform",
        project="E-commerce Platform",
        branch="feature/checkout-redesign",
        runner="cucumber-js",
        output_format="format1",
        single_file=False
    )