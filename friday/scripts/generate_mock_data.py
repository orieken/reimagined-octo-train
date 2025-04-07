#!/usr/bin/env python
"""
Mock Data Generator for Friday Test Reporting System

This script generates realistic mock data for testing and development purposes.
It creates test runs, scenarios, and steps with varied statuses and details.
"""

import argparse
import datetime
import json
import random
import uuid
from typing import List, Dict, Any


def generate_project() -> Dict[str, Any]:
    """Generate a mock project."""
    return {
        "id": str(uuid.uuid4()),
        "name": f"Project-{random.choice(['Alpha', 'Beta', 'Gamma'])}-{random.randint(1, 100)}",
        "description": f"Description for {random.choice(['Web', 'Mobile', 'Backend'])} project",
        "repository_url": f"https://github.com/example/{random.choice(['web', 'mobile', 'backend'])}"
    }


def generate_test_run(project_id: str) -> Dict[str, Any]:
    """Generate a mock test run."""
    total_tests = random.randint(10, 100)
    passed_tests = random.randint(0, total_tests)
    failed_tests = total_tests - passed_tests

    start_time = datetime.datetime.now() - datetime.timedelta(days=random.randint(0, 30))
    end_time = start_time + datetime.timedelta(minutes=random.randint(30, 240))

    return {
        "id": str(uuid.uuid4()),
        "project_id": project_id,
        "name": f"Test Run-{random.randint(1, 1000)}",
        "status": "PASSED" if failed_tests == 0 else "FAILED",
        "start_time": start_time.isoformat(),
        "end_time": end_time.isoformat(),
        "total_tests": total_tests,
        "passed_tests": passed_tests,
        "failed_tests": failed_tests,
        "environment": random.choice(["dev", "staging", "production"])
    }


def generate_test_case(test_run_id: str, feature: str = None) -> Dict[str, Any]:
    """Generate a mock test case."""
    # Predefined feature list with more context
    features = [
        "Authentication", "User Management", "Payment Processing",
        "Data Validation", "Search Functionality", "Reporting",
        "API Integration", "Performance", "Security", "Workflow"
    ]

    # Determine status probabilities
    status_choices = [
        ("PASSED", 0.7),  # 70% pass rate
        ("FAILED", 0.2),  # 20% fail rate
        ("SKIPPED", 0.1)  # 10% skipped
    ]
    status = random.choices([s[0] for s in status_choices],
                            weights=[s[1] for s in status_choices])[0]

    start_time = datetime.datetime.fromisoformat(test_run_id)
    duration = random.uniform(0.1, 30.0)
    end_time = start_time + datetime.timedelta(seconds=duration)

    return {
        "id": str(uuid.uuid4()),
        "test_run_id": test_run_id,
        "name": f"Test Case-{random.randint(1, 1000)}",
        "feature": feature or random.choice(features),
        "description": f"Validates {random.choice(features)} functionality",
        "status": status,
        "start_time": start_time.isoformat(),
        "end_time": end_time.isoformat(),
        "duration": duration,
        "error_message": ("Test failed due to " + random.choice([
            "unexpected error",
            "assertion failure",
            "timeout",
            "connection issue"
        ])) if status == "FAILED" else None,
        "tags": random.sample([
            "smoke", "regression", "critical",
            "integration", "ui", "api",
            "performance", "security"
        ], k=random.randint(0, 3))
    }


def generate_test_step(test_case_id: str, step_order: int) -> Dict[str, Any]:
    """Generate a mock test step."""
    # Determine status probabilities
    status_choices = [
        ("PASSED", 0.8),  # 80% pass rate
        ("FAILED", 0.15),  # 15% fail rate
        ("SKIPPED", 0.05)  # 5% skipped
    ]
    status = random.choices([s[0] for s in status_choices],
                            weights=[s[1] for s in status_choices])[0]

    start_time = datetime.datetime.fromisoformat(test_case_id)
    duration = random.uniform(0.01, 5.0)
    end_time = start_time + datetime.timedelta(seconds=duration)

    return {
        "id": str(uuid.uuid4()),
        "test_case_id": test_case_id,
        "name": f"Step {step_order}",
        "keyword": random.choice(["Given", "When", "Then", "And"]),
        "description": f"Step description for step {step_order}",
        "status": status,
        "start_time": start_time.isoformat(),
        "end_time": end_time.isoformat(),
        "duration": duration,
        "error_message": ("Step failed due to " + random.choice([
            "validation error",
            "unexpected condition",
            "resource not found",
            "timeout"
        ])) if status == "FAILED" else None,
        "screenshot_url": (f"https://screenshots.example.com/step_{uuid.uuid4()}.png")
        if random.random() < 0.3 else None
    }


def generate_build_info(project_id: str) -> Dict[str, Any]:
    """Generate a mock build information entry."""
    start_time = datetime.datetime.now() - datetime.timedelta(days=random.randint(0, 30))
    duration = random.randint(300, 3600)  # 5 minutes to 1 hour
    end_time = start_time + datetime.timedelta(seconds=duration)

    return {
        "id": str(uuid.uuid4()),
        "project_id": project_id,
        "build_number": f"build-{random.randint(1, 1000)}",
        "status": random.choice(["success", "failure", "in_progress"]),
        "start_time": start_time.isoformat(),
        "end_time": end_time.isoformat(),
        "duration": duration,
        "branch": random.choice(["main", "develop", "feature/new-feature", "hotfix/bug-fix"]),
        "commit_hash": ''.join(random.choice('0123456789abcdef') for _ in range(40)),
        "commit_message": f"Commit message for build {random.randint(1, 1000)}",
        "environment": random.choice(["dev", "staging", "production"])
    }


def generate_mock_data(num_projects: int = 5,
                       runs_per_project: int = 10,
                       cases_per_run: int = 20,
                       steps_per_case: int = 5,
                       builds_per_project: int = 5) -> Dict[str, Any]:
    """
    Generate comprehensive mock data for testing.

    Args:
        num_projects: Number of projects to generate
        runs_per_project: Number of test runs per project
        cases_per_run: Number of test cases per run
        steps_per_case: Number of steps per test case
        builds_per_project: Number of builds per project

    Returns:
        Dictionary containing generated mock data
    """
    mock_data = {
        "projects": [],
        "test_runs": [],
        "test_cases": [],
        "test_steps": [],
        "build_info": []
    }

    # Generate projects
    for _ in range(num_projects):
        project = generate_project()
        mock_data["projects"].append(project)

        # Generate build info for the project
        for _ in range(builds_per_project):
            build = generate_build_info(project["id"])
            mock_data["build_info"].append(build)

        # Generate test runs for each project
        for _ in range(runs_per_project):
            test_run = generate_test_run(project["id"])
            mock_data["test_runs"].append(test_run)

            # Generate test cases for each run
            for _ in range(cases_per_run):
                # Select a random feature
                feature = random.choice([
                    "Authentication", "User Management", "Payment Processing",
                    "Data Validation", "Search Functionality"
                ])

                test_case = generate_test_case(test_run["start_time"], feature)
                mock_data["test_cases"].append(test_case)

                # Generate steps for each test case
                for step_order in range(1, steps_per_case + 1):
                    test_step = generate_test_step(test_case["start_time"], step_order)
                    mock_data["test_steps"].append(test_step)

    return mock_data


def save_mock_data(mock_data: Dict[str, Any], output_file: str):
    """Save mock data to a JSON file."""
    with open(output_file, 'w') as f:
        json.dump(mock_data, f, indent=2)


def main():
    """CLI interface for mock data generation."""
    parser = argparse.ArgumentParser(description="Generate mock test data")
    parser.add_argument("-p", "--projects", type=int, default=5,
                        help="Number of projects to generate")
    parser.add_argument("-r", "--runs", type=int, default=10,
                        help="Number of test runs per project")
    parser.add_argument("-c", "--cases", type=int, default=20,
                        help="Number of test cases per run")
    parser.add_argument("-s", "--steps", type=int, default=5,
                        help="Number of steps per test case")
    parser.add_argument("-b", "--builds", type=int, default=5,
                        help="Number of builds per project")
    parser.add_argument("-o", "--output", type=str, default="mock_test_data.json",
                        help="Output JSON file path")

    args = parser.parse_args()

    # Generate and save mock data
    mock_data = generate_mock_data(
        num_projects=args.projects,
        runs_per_project=args.runs,
        cases_per_run=args.cases,
        steps_per_case=args.steps,
        builds_per_project=args.builds
    )

    save_mock_data(mock_data, args.output)
    print(f"Mock data generated and saved to {args.output}")


if __name__ == "__main__":
    main()
