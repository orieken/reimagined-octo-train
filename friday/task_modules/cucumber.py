#!/usr/bin/env python3
"""
Invoke tasks for Cucumber Reports Generator.

This file defines tasks that can be run with the 'invoke' command line tool.
To use, install invoke (`pip install invoke`) and run `invoke -l` to see available tasks.
"""

import os
import datetime
from typing import Optional
from invoke import task
import json
from task_modules.cucumber_reports_generator import generate, CucumberReportGenerator, read_feature_files



@task(help={
    'features_dir': 'Directory containing Cucumber feature files',
    'output_dir': 'Directory to output the generated reports',
    'days': 'Number of days to simulate',
    'runs_per_day': 'Number of test runs per day',
    'failure_rate': 'Percentage of scenarios that should fail (0.0-1.0)',
    'failure_distribution': 'How failures are distributed (uniform, increasing, decreasing, clustered)',
    'project': 'Project name',
    'branch': 'Git branch name',
    'commit': 'Git commit hash',
    'runner': 'Test runner (e.g., cucumber-jvm, cucumber-js)',
    'output_format': 'Format of the generated reports (format1, format2)',
    'single_file': 'Output all reports to a single file',
})
def generate_reports(c,
                     features_dir="./features",
                     output_dir="./reports",
                     days=7,
                     runs_per_day=3,
                     failure_rate=0.1,
                     failure_distribution="uniform",
                     project=None,
                     branch=None,
                     commit=None,
                     runner=None,
                     output_format="format1",
                     single_file=False):
    """Generate Cucumber reports based on feature files."""
    generate(
        features_dir=features_dir,
        output_dir=output_dir,
        days=days,
        runs_per_day=runs_per_day,
        failure_rate=failure_rate,
        failure_distribution=failure_distribution,
        project=project,
        branch=branch,
        commit=commit,
        runner=runner,
        output_format=output_format,
        single_file=single_file
    )


@task(help={
    'features_dir': 'Directory containing Cucumber feature files',
    'output_dir': 'Directory to output the generated reports',
})
def quick_generate(c, features_dir="./features", output_dir="./reports"):
    """Generate reports with default settings (7 days, 3 runs/day, 10% failures)."""
    generate(features_dir=features_dir, output_dir=output_dir)


@task(help={
    'features_dir': 'Directory containing Cucumber feature files',
    'output_dir': 'Directory to output the generated reports',
})
def high_failure(c, features_dir="./features", output_dir="./reports-high-failure"):
    """Generate reports with high failure rate (25%) and clustered distribution."""
    generate(
        features_dir=features_dir,
        output_dir=output_dir,
        failure_rate=0.25,
        failure_distribution="clustered",
        project="E-commerce Platform",
        branch="master"
    )


@task(help={
    'features_dir': 'Directory containing Cucumber feature files',
    'output_dir': 'Directory to output the generated reports',
})
def increasing_failure(c, features_dir="./features", output_dir="./reports-increasing"):
    """Generate reports with increasing failures (more failures in later scenarios)."""
    generate(
        features_dir=features_dir,
        output_dir=output_dir,
        failure_rate=0.15,
        failure_distribution="increasing",
        project="E-commerce Platform",
        branch="feature/refactoring"
    )


@task(help={
    'features_dir': 'Directory containing Cucumber feature files',
    'output_dir': 'Directory to output the generated reports',
})
def format2_output(c, features_dir="./features", output_dir="./reports-format2"):
    """Generate reports in Format 2 (direct Cucumber JSON format)."""
    generate(
        features_dir=features_dir,
        output_dir=output_dir,
        output_format="format2"
    )


@task(help={
    'features_dir': 'Directory containing Cucumber feature files',
    'output_dir': 'Directory to output the generated reports',
})
def monthly_data(c, features_dir="./features", output_dir="./reports-monthly"):
    """Generate 30 days of data with all reports in a single file."""
    generate(
        features_dir=features_dir,
        output_dir=output_dir,
        days=30,
        single_file=True
    )


@task(help={
    'input_dir': 'Directory containing generated reports',
    'url': 'URL of the Friday /processor/cucumber endpoint',
    'token': 'API token for authentication',
})
def post_reports(c, input_dir="./reports", url=None, token=None):
    """Post generated reports to the Friday service."""
    import json
    import requests
    from pathlib import Path

    if not url:
        print("Error: URL is required")
        return

    if not token:
        print("Warning: No API token provided")

    # Find all JSON files in the input directory
    report_files = list(Path(input_dir).glob('*.json'))

    if not report_files:
        print(f"No JSON files found in {input_dir}")
        return

    print(f"Found {len(report_files)} report files")

    # Track success/failure
    success = 0
    failure = 0

    # Post each report file
    for report_file in report_files:
        try:
            with open(report_file, 'r', encoding='utf-8') as f:
                report = json.load(f)

            headers = {
                'Content-Type': 'application/json',
            }

            if token:
                headers['Authorization'] = f'Bearer {token}'

            response = requests.post(url, headers=headers, json=report)

            if response.ok:
                success += 1
                print(f"Successfully posted {report_file.name}")
            else:
                failure += 1
                print(f"Failed to post {report_file.name}: {response.status_code} {response.reason}")

        except Exception as e:
            failure += 1
            print(f"Error posting {report_file.name}: {str(e)}")

    print(f"Completed: {success} successful, {failure} failed")


@task
def analyze_reports(c, input_dir="./reports"):
    """Analyze generated reports to show summary statistics."""
    import json
    from pathlib import Path

    # Find all JSON files in the input directory
    report_files = list(Path(input_dir).glob('*.json'))

    if not report_files:
        print(f"No JSON files found in {input_dir}")
        return

    print(f"Analyzing {len(report_files)} report files in {input_dir}")

    # Track statistics
    total_features = 0
    total_scenarios = 0
    total_steps = 0
    failing_scenarios = 0
    failing_steps = 0

    # Process each report file
    for report_file in report_files:
        try:
            with open(report_file, 'r', encoding='utf-8') as f:
                report_data = json.load(f)

            # Handle both report formats
            features = None
            if 'report' in report_data:
                # Format 1
                features = report_data['report']
                print(f"Report: {report_data['metadata']['timestamp']} ({report_data['metadata']['project']})")
            else:
                # Format 2 or single file containing multiple reports
                if isinstance(report_data, list) and report_data and isinstance(report_data[0], dict):
                    if 'elements' in report_data[0]:
                        # Format 2
                        features = report_data
                        print(f"Report: {report_file.name} (Format 2)")
                    elif 'report' in report_data[0]:
                        # Single file with multiple reports
                        print(f"File contains {len(report_data)} reports")
                        continue

            if not features:
                print(f"Could not parse {report_file.name}")
                continue

            # Count features, scenarios, and steps
            report_features = len(features)
            report_scenarios = 0
            report_steps = 0
            report_failing_scenarios = 0
            report_failing_steps = 0

            for feature in features:
                for scenario in feature['elements']:
                    report_scenarios += 1
                    scenario_failing = False

                    for step in scenario['steps']:
                        report_steps += 1
                        if step['result']['status'] == 'failed':
                            report_failing_steps += 1
                            scenario_failing = True

                    if scenario_failing:
                        report_failing_scenarios += 1

            # Update totals
            total_features += report_features
            total_scenarios += report_scenarios
            total_steps += report_steps
            failing_scenarios += report_failing_scenarios
            failing_steps += report_failing_steps

            # Print report summary
            print(f"  Features: {report_features}")
            print(
                f"  Scenarios: {report_scenarios} ({report_failing_scenarios} failing, {report_failing_scenarios / report_scenarios * 100:.1f}%)")
            print(
                f"  Steps: {report_steps} ({report_failing_steps} failing, {report_failing_steps / report_steps * 100:.1f}%)")

        except Exception as e:
            print(f"Error analyzing {report_file.name}: {str(e)}")

    # Print overall statistics
    print("\nOverall Statistics:")
    print(f"  Total Features: {total_features}")
    print(f"  Total Scenarios: {total_scenarios}")
    print(f"  Total Steps: {total_steps}")
    print(f"  Failing Scenarios: {failing_scenarios} ({failing_scenarios / total_scenarios * 100:.1f}%)")
    print(f"  Failing Steps: {failing_steps} ({failing_steps / total_steps * 100:.1f}%)")


@task
def clean(c, output_dir="./reports"):
    """Remove all generated reports."""
    import shutil
    from pathlib import Path

    path = Path(output_dir)
    if path.exists() and path.is_dir():
        shutil.rmtree(path)
        print(f"Removed {output_dir}")
    else:
        print(f"{output_dir} does not exist or is not a directory")


@task
def list_features(c, features_dir="./features"):
    """List all feature files and their scenarios."""
    from pathlib import Path

    features_path = Path(features_dir)
    if not features_path.exists() or not features_path.is_dir():
        print(f"{features_dir} does not exist or is not a directory")
        return

    feature_files = list(features_path.glob('*.feature'))

    if not feature_files:
        print(f"No .feature files found in {features_dir}")
        return

    print(f"Found {len(feature_files)} feature files in {features_dir}:")

    for feature_file in feature_files:
        print(f"\n{feature_file.name}:")
        try:
            with open(feature_file, 'r', encoding='utf-8') as f:
                content = f.read()

            # Simple parsing to extract feature and scenario names
            feature_name = None
            scenario_count = 0

            for line in content.split('\n'):
                if line.strip().startswith('Feature:'):
                    feature_name = line.strip()[len('Feature:'):].strip()
                    print(f"  Feature: {feature_name}")

                if line.strip().startswith('Scenario:'):
                    scenario_name = line.strip()[len('Scenario:'):].strip()
                    scenario_count += 1
                    print(f"    - Scenario: {scenario_name}")

            if scenario_count == 0:
                print("    (No scenarios found)")
            else:
                print(f"    Total: {scenario_count} scenarios")

        except Exception as e:
            print(f"  Error reading file: {str(e)}")


@task
def setup(c):
    """Set up the directory structure for the project."""
    import os

    # Create directories
    directories = ['./features', './reports']
    for directory in directories:
        if not os.path.exists(directory):
            os.makedirs(directory)
            print(f"Created {directory}")
        else:
            print(f"{directory} already exists")

    # Create a sample feature file if none exist
    features_dir = './features'
    if not any(f.endswith('.feature') for f in os.listdir(features_dir)):
        sample_feature = os.path.join(features_dir, 'sample.feature')
        with open(sample_feature, 'w', encoding='utf-8') as f:
            f.write("""Feature: Shopping Cart

  Scenario: Adding an item to the cart
    Given I am on a product page
    When I click the "Add to Cart" button
    Then the item should be added to my cart
    And the cart count should increase by 1

  Scenario: Removing an item from the cart
    Given I have an item in my cart
    When I click the "Remove" button
    Then the item should be removed from my cart
    And the cart count should decrease by 1
""")
        print(f"Created sample feature file: {sample_feature}")

    print("\nSetup complete. You can now:")
    print("  1. Add your .feature files to the ./features directory")
    print("  2. Run 'invoke generate-reports' to generate reports")
    print("  3. Check the ./reports directory for the generated reports")


@task(help={
    'scenario_count': 'Number of scenarios to generate',
    'step_count': 'Number of steps per scenario',
    'output_file': 'Output feature file path'
})
def generate_sample_feature(c, scenario_count=5, step_count=4, output_file="./features/generated.feature"):
    """Generate a sample feature file with random scenarios and steps."""
    import random

    # Define templates for scenarios and steps
    feature_templates = [
        "User Authentication",
        "Shopping Cart",
        "Product Browsing",
        "Checkout Process",
        "Order Management",
        "User Profile",
        "Payment Processing",
        "Wishlist Management",
        "Customer Support",
        "Product Reviews"
    ]

    scenario_templates = [
        "Logging in with valid credentials",
        "Adding a product to the cart",
        "Removing a product from the cart",
        "Searching for a product",
        "Filtering products by category",
        "Viewing product details",
        "Completing a purchase",
        "Updating user profile information",
        "Adding a payment method",
        "Submitting a contact form",
        "Writing a product review",
        "Adding an item to the wishlist",
        "Viewing order history",
        "Tracking an order",
        "Applying a discount code"
    ]

    given_step_templates = [
        "I am on the {page} page",
        "I am logged in as a {user_type} user",
        "I have {item_count} items in my cart",
        "I have selected the product {product_name}",
        "I have entered my {info_type} information",
        "my shopping cart is empty",
        "I have an account with email {email}"
    ]

    when_step_templates = [
        "I click the \"{button_name}\" button",
        "I enter {input_value} in the {field_name} field",
        "I select {option} from the {dropdown} dropdown",
        "I submit the form",
        "I add the product to my cart",
        "I search for \"{search_term}\"",
        "I navigate to the {page} page"
    ]

    then_step_templates = [
        "I should see the message \"{message}\"",
        "I should be redirected to the {page} page",
        "the {item} should be added to my {location}",
        "the {count} should be updated to {number}",
        "the form should be submitted successfully",
        "I should receive a confirmation email",
        "the {element} should display {value}"
    ]

    # Generate a random feature
    feature_name = random.choice(feature_templates)

    # Generate random scenarios
    scenarios = []
    for i in range(scenario_count):
        scenario_name = random.choice(scenario_templates)

        # Generate random steps
        steps = []
        steps.append(
            f"Given {random.choice(given_step_templates).format(page='home', user_type='registered', item_count=3, product_name='Test Product', info_type='shipping', email='user@example.com')}")

        for j in range(min(step_count - 2, 1)):  # Ensure at least 1 'When' step
            steps.append(
                f"When {random.choice(when_step_templates).format(button_name='Submit', input_value='test', field_name='name', option='Option 1', dropdown='category', search_term='test', page='checkout')}")

        steps.append(
            f"Then {random.choice(then_step_templates).format(message='Success', page='confirmation', item='product', location='cart', count='total', number=1, element='status', value='complete')}")

        if step_count > 3:
            for j in range(step_count - 3):
                if random.choice([True, False]):
                    steps.append(
                        f"And {random.choice(then_step_templates).format(message='Success', page='confirmation', item='product', location='cart', count='total', number=1, element='status', value='complete')}")
                else:
                    steps.append(
                        f"And {random.choice(when_step_templates).format(button_name='Submit', input_value='test', field_name='name', option='Option 1', dropdown='category', search_term='test', page='checkout')}")

        scenarios.append((scenario_name, steps))

    # Write to file
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(f"Feature: {feature_name}\n\n")

        for scenario_name, steps in scenarios:
            f.write(f"  Scenario: {scenario_name}\n")
            for step in steps:
                f.write(f"    {step}\n")
            f.write("\n")

    print(f"Generated feature file with {scenario_count} scenarios at {output_file}")


@task
def version(c):
    """Display version information."""
    print("Cucumber Reports Generator")
    print("Version: 1.0.0")
    print("Python Version: 3.6+")
    print("Required Libraries: invoke")
    print("Optional Libraries: requests (for posting reports)")


@task(help={
    'input_dir': 'Input directory containing Cucumber reports',
    'output_file': 'Output HTML file'
})
def generate_html_report(c, input_dir="./reports", output_file="./cucumber-report.html"):
    """Generate an HTML report from Cucumber JSON reports."""
    import json
    from pathlib import Path
    import datetime

    # Find all JSON files in the input directory
    report_files = list(Path(input_dir).glob('*.json'))

    if not report_files:
        print(f"No JSON files found in {input_dir}")
        return

    print(f"Generating HTML report from {len(report_files)} report files...")

    # HTML template
    html_template = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Cucumber Test Report</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            line-height: 1.6;
            margin: 0;
            padding: 20px;
            color: #333;
        }
        h1, h2, h3, h4 {
            margin-top: 0;
        }
        .report-header {
            background-color: #f8f8f8;
            padding: 15px;
            margin-bottom: 20px;
            border-radius: 5px;
            border-left: 5px solid #4CAF50;
        }
        .feature {
            margin-bottom: 30px;
            padding: 15px;
            background-color: #fff;
            border-radius: 5px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        }
        .feature-header {
            display: flex;
            justify-content: space-between;
            border-bottom: 1px solid #eee;
            padding-bottom: 10px;
            margin-bottom: 15px;
        }
        .scenario {
            margin: 15px 0;
            padding: 10px;
            background-color: #f9f9f9;
            border-radius: 5px;
        }
        .passed { color: #4CAF50; }
        .failed { color: #F44336; }
        .skipped { color: #FF9800; }
        .pending { color: #2196F3; }
        .undefined { color: #9C27B0; }
        .status-badge {
            display: inline-block;
            padding: 4px 8px;
            border-radius: 3px;
            font-size: 12px;
            font-weight: bold;
            color: white;
        }
        .status-passed { background-color: #4CAF50; }
        .status-failed { background-color: #F44336; }
        .status-skipped { background-color: #FF9800; }
        .status-pending { background-color: #2196F3; }
        .status-undefined { background-color: #9C27B0; }
        .step {
            margin: 5px 0;
            padding: 5px 10px;
        }
        .error-message {
            background-color: #ffebee;
            color: #F44336;
            padding: 10px;
            border-radius: 3px;
            margin-top: 5px;
            white-space: pre-wrap;
            font-family: monospace;
        }
        .summary {
            margin-bottom: 20px;
        }
        .summary-table {
            width: 100%;
            border-collapse: collapse;
        }
        .summary-table th, .summary-table td {
            padding: 8px 12px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }
        .summary-table th {
            background-color: #f2f2f2;
        }
        .progress-bar {
            height: 20px;
            background-color: #e0e0e0;
            border-radius: 10px;
            margin-top: 5px;
            overflow: hidden;
        }
        .progress-bar-passed {
            height: 100%;
            background-color: #4CAF50;
            float: left;
        }
        .progress-bar-failed {
            height: 100%;
            background-color: #F44336;
            float: left;
        }
        .progress-bar-skipped {
            height: 100%;
            background-color: #FF9800;
            float: left;
        }
        .progress-bar-pending {
            height: 100%;
            background-color: #2196F3;
            float: left;
        }
        .progress-bar-undefined {
            height: 100%;
            background-color: #9C27B0;
            float: left;
        }
    </style>
</head>
<body>
    <div class="report-header">
        <h1>Cucumber Test Report</h1>
        <p>Generated on: {timestamp}</p>
    </div>

    <div class="summary">
        <h2>Summary</h2>
        <table class="summary-table">
            <tr>
                <th>Reports</th>
                <th>Features</th>
                <th>Scenarios</th>
                <th>Passed</th>
                <th>Failed</th>
                <th>Skipped</th>
                <th>Pending</th>
                <th>Undefined</th>
                <th>Pass Rate</th>
            </tr>
            <tr>
                <td>{report_count}</td>
                <td>{feature_count}</td>
                <td>{scenario_count}</td>
                <td class="passed">{passed_count}</td>
                <td class="failed">{failed_count}</td>
                <td class="skipped">{skipped_count}</td>
                <td class="pending">{pending_count}</td>
                <td class="undefined">{undefined_count}</td>
                <td>{pass_rate}%</td>
            </tr>
        </table>
        <div class="progress-bar">
            <div class="progress-bar-passed" style="width: {passed_percent}%;"></div>
            <div class="progress-bar-failed" style="width: {failed_percent}%;"></div>
            <div class="progress-bar-skipped" style="width: {skipped_percent}%;"></div>
            <div class="progress-bar-pending" style="width: {pending_percent}%;"></div>
            <div class="progress-bar-undefined" style="width: {undefined_percent}%;"></div>
        </div>
    </div>

    <h2>Reports</h2>
    {report_html}
</body>
</html>
"""

    # Initialize counters
    report_count = len(report_files)
    feature_count = 0
    scenario_count = 0
    passed_count = 0
    failed_count = 0
    skipped_count = 0
    pending_count = 0
    undefined_count = 0

    reports_html = []

    # Process each report file
    for report_file in report_files:
        try:
            with open(report_file, 'r', encoding='utf-8') as f:
                report_data = json.load(f)

            # Handle both report formats
            features = None
            report_metadata = {}

            if 'report' in report_data:
                # Format 1
                features = report_data['report']
                report_metadata = report_data['metadata']
            else:
                # Format 2 or single file containing multiple reports
                if isinstance(report_data, list) and report_data and isinstance(report_data[0], dict):
                    if 'elements' in report_data[0]:
                        # Format 2
                        features = report_data
                    elif 'report' in report_data[0]:
                        # Single file with multiple reports
                        continue

            if not features:
                continue

            # Generate HTML for this report
            report_html = f"<div class='feature'>\n"
            report_html += f"<div class='feature-header'>\n"

            if report_metadata:
                timestamp = report_metadata.get('timestamp', 'N/A')
                project = report_metadata.get('project', 'N/A')
                branch = report_metadata.get('branch', 'N/A')
                commit = report_metadata.get('commit', 'N/A')

                report_html += f"<h3>Report: {timestamp}</h3>\n"
                report_html += f"<div>Project: {project} | Branch: {branch} | Commit: {commit}</div>\n"
            else:
                report_html += f"<h3>Report: {report_file.name}</h3>\n"

            report_html += f"</div>\n"  # end feature-header

            # Process features
            feature_count += len(features)

            for feature in features:
                feature_name = feature.get('name', 'Unnamed Feature')

                report_html += f"<h4>{feature_name}</h4>\n"

                # Process scenarios
                for scenario in feature['elements']:
                    scenario_count += 1
                    scenario_name = scenario.get('name', 'Unnamed Scenario')

                    # Determine scenario status
                    scenario_status = 'passed'
                    for step in scenario['steps']:
                        step_status = step['result']['status']
                        if step_status == 'failed':
                            scenario_status = 'failed'
                            break
                        elif step_status == 'skipped' and scenario_status == 'passed':
                            scenario_status = 'skipped'
                        elif step_status == 'pending' and scenario_status in ['passed', 'skipped']:
                            scenario_status = 'pending'
                        elif step_status == 'undefined' and scenario_status in ['passed', 'skipped', 'pending']:
                            scenario_status = 'undefined'

                    # Update counters
                    if scenario_status == 'passed':
                        passed_count += 1
                    elif scenario_status == 'failed':
                        failed_count += 1
                    elif scenario_status == 'skipped':
                        skipped_count += 1
                    elif scenario_status == 'pending':
                        pending_count += 1
                    elif scenario_status == 'undefined':
                        undefined_count += 1

                    report_html += f"<div class='scenario'>\n"
                    report_html += f"<h5>{scenario_name} <span class='status-badge status-{scenario_status}'>{scenario_status}</span></h5>\n"

                    # Process steps
                    for step in scenario['steps']:
                        step_keyword = step.get('keyword', '')
                        step_name = step.get('name', '')
                        step_status = step['result']['status']

                        report_html += f"<div class='step {step_status}'>{step_keyword}{step_name}</div>\n"

                        # Add error message if failed
                        if step_status == 'failed' and 'error_message' in step['result']:
                            error_message = step['result']['error_message']
                            report_html += f"<div class='error-message'>{error_message}</div>\n"

                    report_html += f"</div>\n"  # end scenario

            report_html += f"</div>\n"  # end feature
            reports_html.append(report_html)

        except Exception as e:
            print(f"Error processing {report_file.name}: {str(e)}")

    # Calculate percentages for progress bar
    total_scenarios = passed_count + failed_count + skipped_count + pending_count + undefined_count

    if total_scenarios > 0:
        passed_percent = round(passed_count / total_scenarios * 100)
        failed_percent = round(failed_count / total_scenarios * 100)
        skipped_percent = round(skipped_count / total_scenarios * 100)
        pending_percent = round(pending_count / total_scenarios * 100)
        undefined_percent = round(undefined_count / total_scenarios * 100)
        pass_rate = round(passed_count / total_scenarios * 100, 1)
    else:
        passed_percent = failed_percent = skipped_percent = pending_percent = undefined_percent = 0
        pass_rate = 0

    # Generate complete HTML
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    html_content = html_template.format(
        timestamp=now,
        report_count=report_count,
        feature_count=feature_count,
        scenario_count=scenario_count,
        passed_count=passed_count,
        failed_count=failed_count,
        skipped_count=skipped_count,
        pending_count=pending_count,
        undefined_count=undefined_count,
        pass_rate=pass_rate,
        passed_percent=passed_percent,
        failed_percent=failed_percent,
        skipped_percent=skipped_percent,
        pending_percent=pending_percent,
        undefined_percent=undefined_percent,
        report_html="\n".join(reports_html)
    )

    # Write HTML to file
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html_content)

    print(f"HTML report generated at {output_file}")


@task(help={
    'features_dir': 'Directory containing Cucumber feature files',
    'output_dir': 'Directory to output the prepared payloads',
    'count': 'Number of payloads to generate',
    'failure_rate': 'Percentage of scenarios that should fail (0.0-1.0)',
    'failure_distribution': 'How failures are distributed (uniform, increasing, decreasing, clustered)',
    'project': 'Project name',
    'branch': 'Git branch name',
})
def prepare_payloads(c,
                     features_dir="./features",
                     output_dir="./payloads",
                     count=10,
                     failure_rate=0.15,
                     failure_distribution="uniform",
                     project="E-commerce Platform",
                     branch="main"):
    """Generate payloads ready for posting to the /processor/cucumber endpoint."""

    print(f"Preparing {count} payloads for the /processor/cucumber endpoint...")

    # Read feature files
    feature_files = read_feature_files(features_dir)

    if not feature_files:
        print(f"No feature files found in {features_dir}")
        return

    # Create output directory if it doesn't exist
    if not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)

    # Initialize generator
    generator = CucumberReportGenerator()

    # Generate a series of reports with varying timestamps
    base_date = datetime.datetime.now()

    for i in range(count):
        # Create a timestamp with a small offset for each payload
        run_time = base_date - datetime.timedelta(minutes=i * 15)  # 15-minute intervals

        # Parse features
        parsed_features = generator.parse_feature_files(feature_files)

        # Apply failures
        features_with_failures = generator.apply_failures(
            parsed_features,
            failure_rate,
            failure_distribution
        )

        # Generate commit hash
        commit = generator.generate_random_commit_hash()

        # Create metadata
        metadata = {
            'project': project,
            'branch': branch,
            'commit': commit,
            'timestamp': run_time.isoformat(),
            'runner': "cucumber-js"
        }

        # Create payload in Format 1
        payload = {
            'metadata': metadata,
            'report': features_with_failures
        }

        # Save payload
        filename = f"payload-{i + 1}-{run_time.strftime('%Y%m%d-%H%M%S')}.json"
        output_file = os.path.join(output_dir, filename)

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(payload, f, indent=2)

        print(f"Created payload: {filename}")

    print(f"\nGenerated {count} payloads in {output_dir}")
    print("Use 'invoke post-to-service' to post these payloads to your service.")


@task(help={
    'payloads_dir': 'Directory containing payload JSON files',
    'url': 'URL of the /processor/cucumber endpoint',
    'token': 'Optional API token for authentication',
    'delay': 'Delay in seconds between each request',
})
def post_to_service(c,
                    payloads_dir="./payloads",
                    url="http://localhost:4000/api/v1/processor/cucumber",
                    token=None,
                    delay=2):
    """Post prepared payloads to your local service endpoint."""
    import json
    import time
    import requests
    from pathlib import Path

    # Find all JSON files in the payloads directory
    payload_files = list(Path(payloads_dir).glob('*.json'))

    if not payload_files:
        print(f"No JSON payload files found in {payloads_dir}")
        return

    print(f"Found {len(payload_files)} payload files in {payloads_dir}")
    print(f"Posting to service URL: {url}")

    # Sort files by name to maintain chronological order
    payload_files.sort()

    # Track success/failure
    success = 0
    failure = 0

    # Post each payload file
    for i, payload_file in enumerate(payload_files):
        try:
            print(f"[{i + 1}/{len(payload_files)}] Posting {payload_file.name}...", end="")

            # Read the payload
            with open(payload_file, 'r', encoding='utf-8') as f:
                payload = json.load(f)

            # Set up headers
            headers = {
                'Content-Type': 'application/json',
            }

            if token:
                headers['Authorization'] = f'Bearer {token}'

            # Post to service
            response = requests.post(url, headers=headers, json=payload)

            if response.ok:
                success += 1
                print(f" Success ({response.status_code})")

                # Try to print any response content for debugging
                try:
                    response_json = response.json()
                    print(f"   Response: {json.dumps(response_json)[:100]}...")
                except:
                    if response.text:
                        print(f"   Response: {response.text[:100]}...")
            else:
                failure += 1
                print(f" Failed ({response.status_code})")
                print(f"   Error: {response.text[:200]}...")

            # Add delay between requests
            if i < len(payload_files) - 1 and delay > 0:
                time.sleep(delay)

        except Exception as e:
            failure += 1
            print(f" Error: {str(e)}")

            # Continue with next file even if there's an error
            continue

    print(f"\nCompleted: {success} successful, {failure} failed")

    if success > 0:
        print("\nPayloads successfully posted to your service!")
        print("You should now be able to see the data in your application.")


@task
def verify_processing(c, url="http://localhost:4000/api/v1/reports"):
    """Verify that posted reports were processed correctly."""
    import requests

    print(f"Checking for processed reports at {url}...")

    try:
        response = requests.get(url)

        if response.ok:
            data = response.json()
            if isinstance(data, list) and len(data) > 0:
                print(f"Found {len(data)} processed reports!")
                print("Most recent reports:")
                for report in data[:5]:  # Show 5 most recent
                    print(
                        f"  - {report.get('timestamp', 'N/A')}: {report.get('project', 'Unknown')} ({report.get('total_scenarios', 0)} scenarios)")
                return True
            else:
                print("No reports found. Processing may have failed.")
        else:
            print(f"Error checking reports: {response.status_code}")
            print(response.text)

    except Exception as e:
        print(f"Error verifying processing: {str(e)}")

    return False


@task
def check_api_paths(c, base_url="http://localhost:4000"):
    """Check different possible API paths to locate the reports endpoint."""
    import requests

    # List of potential paths to try
    paths = [
        "/api/v1/reports",
        "/api/v1/cucumber/reports",
        "/api/v1/processor/reports",
        "/api/reports",
        "/reports",
        "/api/v1/status",
        "/api/v1/health"
    ]

    print(f"Checking various API paths at {base_url}...")

    for path in paths:
        url = f"{base_url}{path}"
        try:
            print(f"Trying: {url}", end="... ")
            response = requests.get(url)
            print(f"Status: {response.status_code}")

            if response.ok:
                print(f"Success! Found working endpoint at: {url}")
                print("Response preview:")
                try:
                    print(response.json())
                except:
                    print(response.text[:200])
                return url
        except Exception as e:
            print(f"Error: {str(e)}")

    print("Could not find a working reports endpoint.")
    return None