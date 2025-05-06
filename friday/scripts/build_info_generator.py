#!/usr/bin/env python3
"""
Friday CLI - Build Info Generator

This module extends the Friday CLI to generate and post build information data
to the test analytics platform.

Usage:
  ./friday-cli.py build-info --project <project_name> [options]

Options:
  --project         Project name
  --branch          Git branch (default: main)
  --commit          Git commit hash (default: random)
  --build-number    Build number (default: random)
  --status          Build status (success, failure, in_progress) (default: random)
  --url             Build URL (default: generated)
  --duration        Build duration in seconds (default: random between 60-1800)
  --agent           CI agent that ran the build (default: one of common CI systems)
  --backdate        Days to backdate the build info (default: 0)
  --runs            Number of build infos to generate (default: 1)
  --interval        Interval between builds in minutes (default: 240 - 4 hours)
  --api-url         API URL (default: http://localhost:4000/api/v1)
"""

import os
import sys
import argparse
import random
import json
import requests
import uuid
from datetime import datetime, timedelta

# Add this to your existing imports in friday-cli.py
from typing import Dict, Any, Optional, List

# Make sure these are defined at the top of your file
DEFAULT_API_URL = "http://localhost:4000/api/v1"
CI_AGENTS = ["jenkins", "github-actions", "gitlab-ci", "azure-pipelines", "circleci", "travis-ci"]
BUILD_STATUSES = ["success", "failure", "in_progress"]


def generate_fake_commit_hash():
    """Generate a realistic looking git commit hash"""
    return ''.join(random.choices('0123456789abcdef', k=40))


def generate_build_info(
        project: str,
        branch: str = "main",
        commit: Optional[str] = None,
        build_number: Optional[str] = None,
        status: Optional[str] = None,
        url: Optional[str] = None,
        duration: Optional[int] = None,
        agent: Optional[str] = None,
        timestamp: Optional[datetime] = None
) -> Dict[str, Any]:
    """
    Generate fake build information data
    """
    # Generate defaults for optional fields
    if not commit:
        commit = generate_fake_commit_hash()

    if not build_number:
        build_number = str(random.randint(100, 10000))

    if not status:
        status = random.choice(BUILD_STATUSES)

    if not url:
        url = f"https://ci.example.com/{project}/builds/{build_number}"

    if not duration:
        duration = random.randint(60, 1800)  # Random duration between 1 minute and 30 minutes

    if not agent:
        agent = random.choice(CI_AGENTS)

    if not timestamp:
        timestamp = datetime.utcnow()

    # Generate build info
    build_info = {
        "id": str(uuid.uuid4()),
        "project": project,
        "branch": branch,
        "commit": commit,
        "build_number": build_number,
        "status": status,
        "url": url,
        "duration": duration,
        "agent": agent,
        "timestamp": timestamp.isoformat() + "Z",
        "metadata": {
            "runner": agent,
            "node": f"runner-{random.randint(1, 50)}",
            "triggered_by": random.choice(["push", "pull_request", "schedule", "api", "manual"]),
            "environment": random.choice(["dev", "staging", "production", "test"])
        }
    }

    # Add test summary metrics if available
    if random.random() > 0.3:  # 70% chance to include test metrics
        build_info["test_summary"] = {
            "total": random.randint(50, 500),
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "flaky": random.randint(0, 10)
        }

        # Calculate passed/failed/skipped based on status
        total_tests = build_info["test_summary"]["total"]

        if status == "success":
            # High pass rate for successful builds
            build_info["test_summary"]["passed"] = int(total_tests * random.uniform(0.95, 1.0))
            build_info["test_summary"]["skipped"] = int(total_tests * random.uniform(0, 0.03))
            build_info["test_summary"]["failed"] = total_tests - build_info["test_summary"]["passed"] - \
                                                   build_info["test_summary"]["skipped"]
        elif status == "failure":
            # Some failures for failed builds
            build_info["test_summary"]["failed"] = int(total_tests * random.uniform(0.05, 0.3))
            build_info["test_summary"]["skipped"] = int(total_tests * random.uniform(0, 0.1))
            build_info["test_summary"]["passed"] = total_tests - build_info["test_summary"]["failed"] - \
                                                   build_info["test_summary"]["skipped"]
        else:  # in_progress
            # Some tests still pending
            completed = int(total_tests * random.uniform(0.5, 0.9))
            build_info["test_summary"]["passed"] = int(completed * random.uniform(0.8, 0.98))
            build_info["test_summary"]["failed"] = completed - build_info["test_summary"]["passed"]
            build_info["test_summary"]["skipped"] = int(total_tests * random.uniform(0, 0.05))
            build_info["test_summary"]["total"] = total_tests  # Restore total count

    return build_info


def post_build_info(build_info: Dict[str, Any], api_url: str = DEFAULT_API_URL) -> bool:
    """
    Post build information to the API
    """
    url = f"{api_url}/processor/build-info"

    try:
        print(f"Posting build info for project: {build_info['project']}, build: {build_info['build_number']}")
        response = requests.post(url, json=build_info)

        if response.status_code < 300:
            print(f"Success: Build info posted successfully")
            return True
        else:
            print(f"Error: {response.status_code} {response.reason}")
            print(json.dumps(response.json(), indent=2))
            return False
    except Exception as e:
        print(f"Error: {str(e)}")
        return False


def cmd_build_info(args):
    """
    Command handler for build-info subcommand
    """
    api_url = args.api_url.rstrip('/')
    base_timestamp = datetime.utcnow() - timedelta(days=args.backdate)

    for i in range(args.runs):
        # Calculate timestamp with specified interval
        run_timestamp = base_timestamp - timedelta(minutes=args.interval * i)

        # Allow explicit status or random selection
        status = args.status if args.status in BUILD_STATUSES else None

        # Build number should increment for consecutive runs
        build_number = str(int(args.build_number) - i) if args.build_number else None

        # Generate build info
        build_info = generate_build_info(
            project=args.project,
            branch=args.branch,
            commit=args.commit,
            build_number=build_number,
            status=status,
            url=args.url,
            duration=args.duration,
            agent=args.agent,
            timestamp=run_timestamp
        )

        # Post to API
        result = post_build_info(build_info, api_url)

        if not result and args.runs > 1:
            print(f"Warning: Failed to post build info #{i + 1}, continuing with remaining builds...")


# Add this to your parser setup in the main function:
def add_build_info_subcommand(subparsers):
    """Add the build-info subcommand to the CLI"""
    parser_build_info = subparsers.add_parser('build-info', help='Generate and post build information')
    parser_build_info.add_argument('--project', required=True, help='Project name')
    parser_build_info.add_argument('--branch', default='main', help='Git branch')
    parser_build_info.add_argument('--commit', help='Git commit hash (default: random)')
    parser_build_info.add_argument('--build-number', help='Build number (default: random)')
    parser_build_info.add_argument('--status', choices=BUILD_STATUSES, help='Build status')
    parser_build_info.add_argument('--url', help='Build URL (default: generated)')
    parser_build_info.add_argument('--duration', type=int, help='Build duration in seconds')
    parser_build_info.add_argument('--agent', choices=CI_AGENTS, help='CI agent that ran the build')
    parser_build_info.add_argument('--backdate', type=int, default=0, help='Days to backdate the build info')
    parser_build_info.add_argument('--runs', type=int, default=1, help='Number of build infos to generate')
    parser_build_info.add_argument('--interval', type=int, default=240, help='Interval between builds in minutes')
    parser_build_info.add_argument('--api-url', default=DEFAULT_API_URL, help='API URL')
    parser_build_info.set_defaults(func=cmd_build_info)


# Example of how to integrate with your existing main function:
"""
def main():
    parser = argparse.ArgumentParser(description='Friday CLI - Test Data Generator')
    subparsers = parser.add_subparsers(dest='command', help='Command to run')

    # Add existing subcommands
    add_cucumber_subcommand(subparsers)

    # Add the new build-info subcommand
    add_build_info_subcommand(subparsers)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    # Call the appropriate handler function
    args.func(args)

if __name__ == '__main__':
    main()
"""

# Standalone execution for testing
if __name__ == '__main__':
    # Create a simple parser just for testing this module
    parser = argparse.ArgumentParser(description='Build Info Generator')
    parser.add_argument('--project', required=True, help='Project name')
    parser.add_argument('--branch', default='main', help='Git branch')
    parser.add_argument('--commit', help='Git commit hash (default: random)')
    parser.add_argument('--build-number', help='Build number (default: random)')
    parser.add_argument('--status', choices=BUILD_STATUSES, help='Build status')
    parser.add_argument('--url', help='Build URL (default: generated)')
    parser.add_argument('--duration', type=int, help='Build duration in seconds')
    parser.add_argument('--agent', choices=CI_AGENTS, help='CI agent that ran the build')
    parser.add_argument('--backdate', type=int, default=0, help='Days to backdate the build info')
    parser.add_argument('--runs', type=int, default=1, help='Number of build infos to generate')
    parser.add_argument('--interval', type=int, default=240, help='Interval between builds in minutes')
    parser.add_argument('--api-url', default=DEFAULT_API_URL, help='API URL')

    args = parser.parse_args()

    # Generate and post build info
    build_info = generate_build_info(
        project=args.project,
        branch=args.branch,
        commit=args.commit,
        build_number=args.build_number,
        status=args.status,
        url=args.url,
        duration=args.duration,
        agent=args.agent,
        timestamp=datetime.utcnow() - timedelta(days=args.backdate)
    )

    # Post to API
    post_build_info(build_info, args.api_url)
