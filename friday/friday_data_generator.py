#!/usr/bin/env python3
"""
Friday Test Data Generator

This script generates sample data payloads for the Friday service:
- Build information with passing and failing builds
- Cucumber test results with random passing and failing scenarios

Usage:
  python friday_data_generator.py --build-info
  python friday_data_generator.py --cucumber
  python friday_data_generator.py --all

Options:
  --build-info    Generate build information payloads
  --cucumber      Generate Cucumber test result payloads
  --all           Generate both build info and Cucumber payloads
  --count N       Number of payloads to generate (default: 10)
  --output DIR    Output directory for generated files (default: ./generated_data)
  --send          Send the generated payloads to the Friday service
  --url URL       URL of the Friday service (default: http://localhost:4000)
"""

import argparse
import json
import os
import random
import requests
import uuid
from datetime import datetime, timedelta
import sys

# Constants
FEATURE_NAMES = [
    "User Authentication", "Product Search", "Shopping Cart", "Checkout Process",
    "Account Management", "Payment Processing", "Order History", "Product Reviews",
    "Wishlist Management", "Email Notifications", "Admin Dashboard", "Inventory Management",
    "User Registration", "Password Reset", "Product Recommendations", "Social Media Integration"
]

SCENARIO_TEMPLATES = [
    "User can {action}",
    "System allows {action}",
    "Admin can {action}",
    "Customer successfully {action}",
    "{action} works correctly",
    "Verify that {action}",
    "Test that {action}"
]

ACTIONS = [
    "log in with valid credentials",
    "search for products by keyword",
    "add items to cart",
    "remove items from cart",
    "complete checkout",
    "update personal information",
    "process payment",
    "view order history",
    "leave product reviews",
    "add items to wishlist",
    "receive email notifications",
    "access admin dashboard",
    "manage inventory",
    "register new account",
    "reset password",
    "view product recommendations"
]

STEP_TEMPLATES = [
    "Given {condition}",
    "When {action}",
    "And {action}",
    "Then {result}"
]

CONDITIONS = [
    "I am on the login page",
    "I am logged in as a user",
    "I am on the product page",
    "I am on the shopping cart page",
    "I am on the checkout page",
    "I have items in my cart",
    "I have created an account",
    "I am on the admin dashboard",
    "I am on the account page",
    "I am logged in as an admin"
]

STEP_ACTIONS = [
    "I enter my username and password",
    "I click the login button",
    "I search for \"{product}\"",
    "I click on the product",
    "I add the product to my cart",
    "I click the checkout button",
    "I enter my payment information",
    "I confirm my order",
    "I click on the account menu",
    "I update my profile information"
]

PRODUCTS = [
    "laptop", "smartphone", "headphones", "camera", "tablet",
    "monitor", "keyboard", "mouse", "printer", "speakers"
]

RESULTS = [
    "I should be redirected to the dashboard",
    "I should see my account information",
    "I should see the product in my cart",
    "I should see a confirmation message",
    "the item should be added to my cart",
    "the order should be placed successfully",
    "I should receive a confirmation email",
    "I should see my updated information",
    "the system should display an error message",
    "I should see the search results"
]

ERROR_MESSAGES = [
    "Expected \"Welcome to your account\" but found \"Invalid credentials\"",
    "Expected element #dashboard-widget to be visible, but it was not found",
    "Timed out waiting for element #confirmation-message to appear",
    "Expected \"Order Completed\" but found \"Error Processing Payment\"",
    "Element .product-item not found in DOM",
    "Network request to /api/checkout failed with status 500",
    "Expected \"true\" but got \"false\"",
    "Expected \"Success\" but got \"Failed: Invalid input\"",
    "Assertion failed: cart.items.length expected to be 1, but was 0",
    "Expected page title to be \"Dashboard\" but was \"Login\""
]

TAGS = [
    "@smoke", "@regression", "@ui", "@api", "@critical", "@high", "@medium", "@low",
    "@login", "@search", "@cart", "@checkout", "@account", "@payment", "@admin",
    "@jira-123", "@jira-456", "@jira-789", "@sprint-22", "@sprint-23", "@sprint-24"
]

BRANCHES = [
    "main", "develop", "feature/login-redesign", "feature/cart-optimization",
    "feature/payment-gateway", "feature/search-enhancements", "bugfix/checkout-error",
    "hotfix/login-security", "release/v2.5", "release/v2.6"
]


def generate_uuid():
    """Generate a random UUID string."""
    return str(uuid.uuid4())


def generate_step(step_type, with_failure=False):
    """Generate a test step with appropriate keyword, name, and result."""
    if step_type.startswith("Given"):
        name = random.choice(CONDITIONS)
    elif step_type.startswith("Then") and with_failure:
        name = random.choice(RESULTS)
    elif step_type.startswith("When") or step_type.startswith("And"):
        action = random.choice(STEP_ACTIONS)
        if "{product}" in action:
            action = action.replace("{product}", random.choice(PRODUCTS))
        name = action
    else:
        name = random.choice(RESULTS)

    duration = random.randint(100000000, 1000000000)  # Duration in nanoseconds

    step = {
        "keyword": step_type.split()[0] + " ",
        "line": random.randint(10, 100),
        "name": name,
        "match": {
            "location": f"features/step_definitions/steps.ts:{random.randint(10, 200)}"
        },
        "result": {
            "status": "passed",
            "duration": duration
        }
    }

    if with_failure and step_type.startswith("Then"):
        step["result"]["status"] = "failed"
        step["result"]["error_message"] = random.choice(ERROR_MESSAGES)

    return step


def generate_scenario(feature_id, scenario_index, with_failure=False):
    """Generate a test scenario with steps, tags, and results."""
    action = random.choice(ACTIONS)
    template = random.choice(SCENARIO_TEMPLATES)
    scenario_name = template.replace("{action}", action)

    scenario_id = f"{feature_id};{scenario_name.lower().replace(' ', '-')}"

    # Generate 3-6 steps
    steps = []

    # Add hidden "Before" step
    steps.append({
        "keyword": "Before",
        "hidden": True,
        "result": {
            "status": "passed",
            "duration": random.randint(100000000, 500000000)
        }
    })

    # Add Given step
    steps.append(generate_step("Given condition", False))

    # Add When steps
    steps.append(generate_step("When action", False))

    # Add 0-2 And steps
    for _ in range(random.randint(0, 2)):
        steps.append(generate_step("And action", False))

    # Add Then step (possibly with failure)
    steps.append(generate_step("Then result", with_failure))

    # Add hidden "After" steps
    steps.append({
        "keyword": "After",
        "hidden": True,
        "result": {
            "status": "passed",
            "duration": random.randint(50000000, 200000000)
        },
        "embeddings": [
            {
                "data": "U3RhdHVzOiBQQVNTRUQuIER1cmF0aW9uOjBz" if not with_failure else "U3RhdHVzOiBGQUlMRUQuIER1cmF0aW9uOjBz",
                "mime_type": "text/plain"
            },
            {
                "data": "c2NyZWVuc2hvdC1lbWJlZGRhYmxl",
                "mime_type": "image/png"
            }
        ]
    })

    # Generate 1-4 random tags
    scenario_tags = []
    tag_count = random.randint(1, 4)
    selected_tags = random.sample(TAGS, tag_count)

    for i, tag in enumerate(selected_tags):
        scenario_tags.append({
            "name": tag,
            "line": scenario_index * 10 + i
        })

    return {
        "description": "",
        "id": scenario_id,
        "keyword": "Scenario",
        "line": scenario_index * 10,
        "name": scenario_name,
        "steps": steps,
        "tags": scenario_tags,
        "type": "scenario"
    }


def generate_feature(index):
    """Generate a feature with multiple scenarios."""
    feature_name = random.choice(FEATURE_NAMES)
    feature_id = feature_name.lower().replace(" ", "-")

    # Generate 1-5 scenarios per feature
    scenario_count = random.randint(1, 5)
    scenarios = []

    # At least one scenario should pass, and there should be some failures
    failure_count = random.randint(0, max(0, scenario_count - 1))
    failure_indices = random.sample(range(scenario_count), failure_count)

    for i in range(scenario_count):
        with_failure = i in failure_indices
        scenarios.append(generate_scenario(feature_id, i, with_failure))

    # Generate feature tags (1-2 tags)
    feature_tags = []
    tag_count = random.randint(1, 2)
    selected_tags = random.sample(TAGS, tag_count)

    for i, tag in enumerate(selected_tags):
        feature_tags.append({
            "name": tag,
            "line": i + 1
        })

    return {
        "description": f"  As a user\n  I want to {random.choice(ACTIONS)}\n  So that I can use the application effectively",
        "elements": scenarios,
        "id": feature_id,
        "line": index * 50,
        "keyword": "Feature",
        "name": feature_name,
        "tags": feature_tags,
        "uri": f"features/{feature_id}.feature"
    }


def generate_cucumber_report(build_id, timestamp):
    """Generate a complete Cucumber report with multiple features."""
    # Generate 2-5 features
    feature_count = random.randint(2, 5)
    features = []

    for i in range(feature_count):
        features.append(generate_feature(i))

    return {
        "report_json": features,
        "build_id": build_id,
        "timestamp": timestamp
    }


def generate_build_info(build_id, build_number, timestamp, success_rate=0.7):
    """Generate build information payload."""
    success = random.random() < success_rate

    return {
        "build_id": build_id,
        "build_number": build_number,
        "timestamp": timestamp,
        "branch": random.choice(BRANCHES),
        "commit_hash": uuid.uuid4().hex[:10],
        "additional_info": {
            "triggered_by": f"user-{random.randint(100, 999)}",
            "environment": random.choice(["dev", "staging", "production"]),
            "status": "success" if success else "failure",
            "duration_seconds": random.randint(120, 600),
            "test_pass_rate": random.uniform(0.6, 1.0) if success else random.uniform(0.0, 0.6)
        }
    }


def generate_data(count=10, output_dir="./generated_data", gen_build=True, gen_cucumber=True, send=False,
                  url="http://localhost:4000"):
    """Generate the specified number of test data payloads."""
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)

    # Generate the data
    if gen_build or gen_cucumber:
        # Generate timestamps for the last 30 days, one per day
        base_timestamp = datetime.now() - timedelta(days=count)
        timestamps = []
        build_ids = []
        build_numbers = []

        for i in range(count):
            timestamp = base_timestamp + timedelta(days=i)
            timestamps.append(timestamp.isoformat())
            build_ids.append(f"build-{i + 1}")
            build_numbers.append(str(i + 1))

        # Generate build info payloads
        if gen_build:
            build_info_dir = os.path.join(output_dir, "build_info")
            os.makedirs(build_info_dir, exist_ok=True)

            print(f"Generating {count} build info payloads...")
            for i in range(count):
                build_data = generate_build_info(build_ids[i], build_numbers[i], timestamps[i])

                # Save to file
                file_path = os.path.join(build_info_dir, f"build_info_{i + 1}.json")
                with open(file_path, 'w') as f:
                    json.dump(build_data, f, indent=2)

                print(f"  - Created {file_path}")

                # Send to API if requested
                if send:
                    try:
                        response = requests.post(f"{url}/processor/build-info", json=build_data)
                        print(f"  - Sent to API: {response.status_code}")
                    except Exception as e:
                        print(f"  - Error sending to API: {str(e)}")

        # Generate cucumber report payloads
        if gen_cucumber:
            cucumber_dir = os.path.join(output_dir, "cucumber_reports")
            os.makedirs(cucumber_dir, exist_ok=True)

            print(f"Generating {count} cucumber report payloads...")
            for i in range(count):
                cucumber_data = generate_cucumber_report(build_ids[i], timestamps[i])

                # Save to file
                file_path = os.path.join(cucumber_dir, f"cucumber_report_{i + 1}.json")
                with open(file_path, 'w') as f:
                    json.dump(cucumber_data, f, indent=2)

                print(f"  - Created {file_path}")

                # Send to API if requested
                if send:
                    try:
                        response = requests.post(f"{url}/processor/cucumber-reports", json=cucumber_data)
                        print(f"  - Sent to API: {response.status_code}")
                    except Exception as e:
                        print(f"  - Error sending to API: {str(e)}")

    print("Data generation complete!")


def main():
    """Parse command line arguments and execute the appropriate action."""
    parser = argparse.ArgumentParser(description='Generate sample data for Friday service')
    parser.add_argument('--build-info', action='store_true', help='Generate build information payloads')
    parser.add_argument('--cucumber', action='store_true', help='Generate Cucumber test result payloads')
    parser.add_argument('--all', action='store_true', help='Generate both build info and Cucumber payloads')
    parser.add_argument('--count', type=int, default=10, help='Number of payloads to generate (default: 10)')
    parser.add_argument('--output', type=str, default='./generated_data', help='Output directory for generated files')
    parser.add_argument('--send', action='store_true', help='Send the generated payloads to the Friday service')
    parser.add_argument('--url', type=str, default='http://localhost:4000', help='URL of the Friday service')

    args = parser.parse_args()

    # If no data type is specified, show help
    if not (args.build_info or args.cucumber or args.all):
        parser.print_help()
        sys.exit(1)

    # Generate data
    generate_data(
        count=args.count,
        output_dir=args.output,
        gen_build=args.build_info or args.all,
        gen_cucumber=args.cucumber or args.all,
        send=args.send,
        url=args.url
    )


if __name__ == "__main__":
    main()