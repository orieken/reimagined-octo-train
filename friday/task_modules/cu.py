# tasks.py
"""
Invoke tasks for the Friday Dashboard Test Data Generator.

This file contains tasks for setting up the environment, generating test data,
and synchronizing data between Qdrant and PostgreSQL.
"""

import os
import sys
import time
import json
from pathlib import Path
from invoke import task, Collection


@task
def setup(c, feature_dir="./features", output_dir="./generated_reports"):
    """Set up the directory structure for test data generation."""
    print(f"Setting up environment for Cucumber report generation...")

    # Create directories
    feature_dir_path = Path(feature_dir)
    output_dir_path = Path(output_dir)

    feature_dir_path.mkdir(exist_ok=True)
    output_dir_path.mkdir(exist_ok=True)

    print(f"Created directory: {feature_dir_path}")
    print(f"Created directory: {output_dir_path}")

    # Find feature files in current directory
    current_dir = Path(".")
    feature_files = list(current_dir.glob("*.feature"))

    if feature_files:
        print(f"Found {len(feature_files)} feature files to copy:")

        # Copy feature files to features directory
        for file_path in feature_files:
            print(f"  - {file_path.name}")
            if not (feature_dir_path / file_path.name).exists():
                c.run(f"cp {file_path} {feature_dir_path}/")

        print("Feature files copied successfully.")
    else:
        print("No feature files found in the current directory.")
        print(f"Please add feature files to {feature_dir_path} manually.")

    # Check if script files exist
    scripts = ["generate_reports.py", "sync_tags.py"]
    for script in scripts:
        script_path = Path(script)
        if not script_path.exists():
            print(f"Warning: {script} not found in current directory.")

    print("\nSetup complete!")


@task
def generate(c, count=3, post=False, api_url=None, feature_dir="./features", output_dir="./generated_reports",
             date_range=False, same_project=False):
    """
    Generate cucumber reports from feature files.

    Args:
        count: Number of reports to generate
        post: Whether to post reports to API
        api_url: Optional custom API URL
        feature_dir: Directory containing feature files
        output_dir: Directory to save generated reports
        date_range: If True, distribute reports over the last 7 days
        same_project: If True, use the same project for all reports
    """
    command = f"python ./task_modules/generate_reports.py --count {count} --feature-dir {feature_dir} --output-dir {output_dir}"

    if post:
        command += " --post"

    if api_url:
        command += f" --api-url {api_url}"

    if date_range:
        command += " --date-range"

    if same_project:
        command += " --same-project"

    print(f"Generating {count} cucumber reports...")
    c.run(command)

@task
def sync_tags(c, dry_run=False, direct=False, qdrant_url=None, pg_conn=None, report_tags=False):
    """
    Sync tags between Qdrant and PostgreSQL.

    Args:
        dry_run: Perform a dry run without making changes
        direct: Use direct query method instead of Qdrant lookup
        qdrant_url: Custom Qdrant URL
        pg_conn: Custom PostgreSQL connection string
        report_tags: Also create tags for test runs
    """
    command = "python sync_tags.py"

    if dry_run:
        command += " --dry-run"

    if direct:
        command += " --direct"

    if report_tags:
        command += " --report-tags"

    if qdrant_url:
        command += f" --qdrant-url {qdrant_url}"

    if pg_conn:
        command += f' --pg-conn "{pg_conn}"'

    print("Syncing tags between Qdrant and PostgreSQL...")
    c.run(command)


@task
def verify_tags(c, limit=10):
    """
    Verify tags in PostgreSQL database.

    Args:
        limit: Maximum number of records to show
    """
    print("Verifying tags in PostgreSQL...")

    # Count total scenario tags
    c.run("psql -c 'SELECT COUNT(*) AS total_tags FROM scenario_tags;'")

    # Count distinct scenarios with tags
    c.run("psql -c 'SELECT COUNT(DISTINCT scenario_id) AS scenarios_with_tags FROM scenario_tags;'")

    # Show sample data
    c.run(f"psql -c 'SELECT scenario_id, tag FROM scenario_tags LIMIT {limit};'")

    # Count tags by name
    c.run("psql -c 'SELECT tag, COUNT(*) AS count FROM scenario_tags GROUP BY tag ORDER BY count DESC LIMIT 10;'")


@task
def verify_results(c, endpoint="http://localhost:4000/api/v1/results"):
    """
    Verify that the /results endpoint returns tags.

    Args:
        endpoint: URL of the results endpoint
    """
    print(f"Verifying results endpoint: {endpoint}")

    try:
        import requests
        response = c.run(f"curl -s {endpoint}", hide=True)

        # Parse response
        data = json.loads(response.stdout)

        # Check for tags
        if "results" in data and "tags" in data["results"]:
            tags = data["results"]["tags"]
            if tags:
                print(f"SUCCESS: Found {len(tags)} tags in results!")
                print("\nSample tags:")
                for tag, stats in list(tags.items())[:5]:
                    print(f"  @{tag}: {stats['count']} scenarios, {stats['pass_rate'] * 100:.1f}% pass rate")
            else:
                print("WARNING: Tags object is empty. Sync may be needed.")
        else:
            print("ERROR: Could not find tags in response.")

    except Exception as e:
        print(f"Error verifying results: {str(e)}")


@task
def full_pipeline(c, count=5, api_url=None, date_range=False, same_project=False):
    """
    Run the full data generation pipeline.

    This task:
    1. Sets up the environment
    2. Generates reports and posts to API
    3. Syncs tags between databases
    4. Verifies tags in PostgreSQL
    5. Verifies tags in /results endpoint

    Args:
        count: Number of reports to generate
        api_url: Custom API URL
        date_range: If True, distribute reports over the last 7 days
        same_project: If True, use the same project for all reports
    """
    print("Starting full data generation pipeline...")

    # Set up environment
    setup(c)

    # Generate and post reports
    generate(c, count=count, post=True, api_url=api_url, date_range=date_range, same_project=same_project)

    # Give the API time to process
    print("\nWaiting 5 seconds for API to process reports...")
    time.sleep(5)

    # Sync tags
    sync_tags(c, direct=True, report_tags=True)

    # Verify in database
    verify_tags(c)

    # Verify in API
    verify_results(c)

    print("\nFull pipeline completed!")


@task
def clean(c, all=False):
    """
    Clean generated files.

    Args:
        all: Whether to clean all generated files (including features)
    """
    print("Cleaning generated files...")

    # Always clean reports
    c.run("rm -f ./generated_reports/*.json")

    if all:
        # Also clean features
        c.run("rm -rf ./features/*.feature")

    print("Cleaning complete!")


# Create a namespace for the tasks
ns = Collection()
ns.add_task(setup)
ns.add_task(generate)
ns.add_task(sync_tags)
ns.add_task(verify_tags)
ns.add_task(verify_results)
ns.add_task(full_pipeline)
ns.add_task(clean)