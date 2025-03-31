#!/usr/bin/env python
"""
Analysis script for the sample Cucumber report.
This script demonstrates how to extract insights from the Cucumber JSON report.
"""

import json
import sys
from datetime import datetime
from collections import Counter


def load_report(file_path):
    with open(file_path, 'r') as f:
        return json.load(f)


def analyze_report(report_data):
    """Analyze the Cucumber report and extract insights."""

    # Initialize counters
    total_features = len(report_data)
    total_scenarios = 0
    total_steps = 0
    passed_scenarios = 0
    failed_scenarios = 0
    passed_steps = 0
    failed_steps = 0
    skipped_steps = 0
    step_durations = []
    scenario_durations = []
    all_tags = []
    scenario_statuses = {}

    # Extract timestamp from filename (assuming format like cucumber_report-20250313T030707.json)
    timestamp_str = "unknown"
    if len(sys.argv) > 1:
        filename = sys.argv[1]
        if 'cucumber_report-' in filename:
            timestamp_part = filename.split('cucumber_report-')[1].split('.json')[0]
            try:
                timestamp = datetime.strptime(timestamp_part, '%Y%m%dT%H%M%S')
                timestamp_str = timestamp.strftime('%Y-%m-%d %H:%M:%S')
            except ValueError:
                pass

    # Iterate through features
    for feature in report_data:
        feature_name = feature.get('name', 'Unnamed Feature')

        # Iterate through scenarios
        for element in feature.get('elements', []):
            if element.get('type') == 'scenario':
                total_scenarios += 1
                scenario_name = element.get('name', 'Unnamed Scenario')

                # Extract tags
                for tag in element.get('tags', []):
                    tag_name = tag.get('name', '')
                    if tag_name:
                        all_tags.append(tag_name)

                # Calculate scenario duration and status
                scenario_duration = 0
                scenario_passed = True

                for step in element.get('steps', []):
                    total_steps += 1

                    result = step.get('result', {})
                    status = result.get('status', 'unknown')
                    duration = result.get('duration', 0) / 1000000000  # Convert nanoseconds to seconds

                    # Accumulate step data
                    if status == 'passed':
                        passed_steps += 1
                    elif status == 'failed':
                        failed_steps += 1
                        scenario_passed = False
                    elif status == 'skipped':
                        skipped_steps += 1

                    step_durations.append(duration)
                    scenario_duration += duration

                # Record scenario status
                scenario_statuses[f"{feature_name}: {scenario_name}"] = "Passed" if scenario_passed else "Failed"
                scenario_durations.append(scenario_duration)

                if scenario_passed:
                    passed_scenarios += 1
                else:
                    failed_scenarios += 1

    # Calculate statistics
    avg_step_duration = sum(step_durations) / len(step_durations) if step_durations else 0
    avg_scenario_duration = sum(scenario_durations) / len(scenario_durations) if scenario_durations else 0
    max_scenario_duration = max(scenario_durations) if scenario_durations else 0
    min_scenario_duration = min(scenario_durations) if scenario_durations else 0

    # Analyze tags
    tag_counts = Counter(all_tags)
    most_common_tags = tag_counts.most_common(5)

    # Prepare report
    results = {
        "timestamp": timestamp_str,
        "summary": {
            "total_features": total_features,
            "total_scenarios": total_scenarios,
            "passed_scenarios": passed_scenarios,
            "failed_scenarios": failed_scenarios,
            "pass_rate": (passed_scenarios / total_scenarios) * 100 if total_scenarios > 0 else 0,
            "total_steps": total_steps,
            "passed_steps": passed_steps,
            "failed_steps": failed_steps,
            "skipped_steps": skipped_steps
        },
        "durations": {
            "average_step_duration_seconds": avg_step_duration,
            "average_scenario_duration_seconds": avg_scenario_duration,
            "min_scenario_duration_seconds": min_scenario_duration,
            "max_scenario_duration_seconds": max_scenario_duration
        },
        "tags": {
            tag: count for tag, count in most_common_tags
        },
        "scenarios": scenario_statuses
    }

    return results


def main():
    if len(sys.argv) < 2:
        print("Usage: python analyze_cucumber.py <cucumber_report.json>")
        sys.exit(1)

    report_path = sys.argv[1]
    try:
        report_data = load_report(report_path)
        results = analyze_report(report_data)

        # Print results
        print(json.dumps(results, indent=2))

        # Summary stats
        print("\n=== SUMMARY ===")
        summary = results["summary"]
        print(f"Features: {summary['total_features']}")
        print(
            f"Scenarios: {summary['total_scenarios']} (Passed: {summary['passed_scenarios']}, Failed: {summary['failed_scenarios']})")
        print(f"Pass Rate: {summary['pass_rate']:.2f}%")
        print(
            f"Steps: {summary['total_steps']} (Passed: {summary['passed_steps']}, Failed: {summary['failed_steps']}, Skipped: {summary['skipped_steps']})")

        # Duration stats
        print("\n=== DURATIONS ===")
        durations = results["durations"]
        print(f"Average Step Duration: {durations['average_step_duration_seconds']:.3f}s")
        print(f"Average Scenario Duration: {durations['average_scenario_duration_seconds']:.3f}s")
        print(f"Min Scenario Duration: {durations['min_scenario_duration_seconds']:.3f}s")
        print(f"Max Scenario Duration: {durations['max_scenario_duration_seconds']:.3f}s")

        # Tag stats
        print("\n=== TOP TAGS ===")
        for tag, count in results["tags"].items():
            print(f"{tag}: {count}")

        # Failed scenarios
        print("\n=== FAILED SCENARIOS ===")
        failed = [name for name, status in results["scenarios"].items() if status == "Failed"]
        for scenario in failed:
            print(f"- {scenario}")

    except Exception as e:
        print(f"Error analyzing report: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()