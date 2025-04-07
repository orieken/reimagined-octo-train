#!/usr/bin/env python3
"""
API Verification Script - Tests the availability of API endpoints after uploading Cucumber data.

This script tries to access all the API endpoints in the system and reports which ones
are correctly configured and responding. It helps identify which routes are properly
registered and which might need fixing.

Usage:
    python api_verification.py [--host HOST]

Options:
    --host HOST    Base URL of the API server (default: http://localhost:4000)
"""

import argparse
import requests
import json
import sys
import uuid
from datetime import datetime

# Default configuration
DEFAULT_HOST = "http://localhost:4000"
API_PREFIX = "/api/v1"  # Adjust if your prefix is different


# Text colors for terminal output
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    BOLD = '\033[1m'
    END = '\033[0m'


def print_success(message):
    print(f"{Colors.GREEN}✓ {message}{Colors.END}")


def print_error(message):
    print(f"{Colors.RED}✗ {message}{Colors.END}")


def print_warning(message):
    print(f"{Colors.YELLOW}! {message}{Colors.END}")


def print_info(message):
    print(f"{Colors.BLUE}→ {message}{Colors.END}")


def print_header(message):
    print(f"\n{Colors.BOLD}{message}{Colors.END}")


def test_endpoint(base_url, endpoint, method="GET", payload=None, params=None):
    """Test if an endpoint is available and responding correctly"""
    url = f"{base_url}{endpoint}"

    print_info(f"Testing {method} {endpoint}")

    try:
        if method == "GET":
            response = requests.get(url, params=params, timeout=5)
        elif method == "POST":
            response = requests.post(url, json=payload, timeout=5)
        else:
            print_error(f"Unsupported method: {method}")
            return False, None

        if response.status_code == 404:
            print_error(f"Endpoint not found (404)")
            return False, None
        elif response.status_code >= 500:
            print_error(f"Server error: {response.status_code}")
            return False, None
        elif response.status_code >= 400:
            print_warning(f"Client error: {response.status_code} - {response.text[:100]}")
            return False, None
        else:
            print_success(f"Status code: {response.status_code}")
            return True, response.json() if response.text else None
    except requests.RequestException as e:
        print_error(f"Request failed: {str(e)}")
        return False, None
    except json.JSONDecodeError:
        print_warning("Response is not valid JSON")
        return True, response.text  # Still return True as the endpoint exists


def main():
    parser = argparse.ArgumentParser(description='Test API endpoints')
    parser.add_argument('--host', default=DEFAULT_HOST, help=f'API host (default: {DEFAULT_HOST})')
    args = parser.parse_args()

    base_url = args.host

    print_header("API Endpoint Verification")
    print_info(f"Testing API at {base_url}")

    # Step 1: Test base connectivity
    print_header("Testing base connectivity")
    success, _ = test_endpoint(base_url, "/")

    # Step 2: Check health endpoint if available
    print_header("Testing health endpoint")
    health_success, _ = test_endpoint(base_url, f"{API_PREFIX}/health")

    # Step 3: Test processor endpoints
    print_header("Testing processor endpoints")
    processor_endpoints = [
        f"{API_PREFIX}/processor/cucumber",
        f"{API_PREFIX}/processing/12345/status"  # Example task_id
    ]

    processor_results = {}
    for endpoint in processor_endpoints:
        processor_results[endpoint] = test_endpoint(base_url, endpoint)[0]

    # Step 4: Test test_results endpoints
    print_header("Testing test_results endpoints")
    results_endpoints = [
        f"{API_PREFIX}/test-results",
        f"{API_PREFIX}/test-results/stats"
    ]

    results_success = {}
    for endpoint in results_endpoints:
        results_success[endpoint] = test_endpoint(base_url, endpoint, params={"limit": 5, "days": 30})[0]

    # Step 5: Test stats endpoints
    print_header("Testing stats endpoints")
    stats_endpoints = [
        f"{API_PREFIX}/stats/summary",
        f"{API_PREFIX}/stats/by-feature",
        f"{API_PREFIX}/stats/by-environment"
    ]

    stats_success = {}
    for endpoint in stats_endpoints:
        stats_success[endpoint] = test_endpoint(base_url, endpoint, params={"days": 30})[0]

    # Step 6: Test other endpoint categories
    endpoint_categories = {
        "Trends": [
            f"{API_PREFIX}/trends/pass-rate",
            f"{API_PREFIX}/trends/duration",
            f"{API_PREFIX}/trends/top-failing-features"
        ],
        "Failures": [
            f"{API_PREFIX}/failures/recent",
            f"{API_PREFIX}/failures/analysis",
            f"{API_PREFIX}/failures/flaky-tests"
        ],
        "Analysis": [
            f"{API_PREFIX}/search",
            f"{API_PREFIX}/answer"
        ],
        "Reporting": [
            f"{API_PREFIX}/reports",
            f"{API_PREFIX}/reports/templates",
            f"{API_PREFIX}/reports/schedules"
        ],
        "Analytics": [
            "/analytics/test-failure-trends",
            "/analytics/dashboard-data"
        ]
    }

    category_results = {}

    for category, endpoints in endpoint_categories.items():
        print_header(f"Testing {category} endpoints")
        category_results[category] = {}

        for endpoint in endpoints:
            # Special handling for POST endpoints
            if endpoint == f"{API_PREFIX}/search":
                payload = {"query": "test", "filters": {}, "limit": 10}
                category_results[category][endpoint] = \
                test_endpoint(base_url, endpoint, method="POST", payload=payload)[0]
            elif endpoint == f"{API_PREFIX}/answer":
                payload = {"query": "show recent test failures"}
                category_results[category][endpoint] = \
                test_endpoint(base_url, endpoint, method="POST", payload=payload)[0]
            else:
                category_results[category][endpoint] = \
                test_endpoint(base_url, endpoint, params={"limit": 5, "days": 30})[0]

    # Print summary
    print_header("Endpoint Verification Summary")

    # Count available and missing endpoints
    available = 0
    missing = 0

    def count_and_print_category(name, results):
        nonlocal available, missing
        print(f"\n{Colors.BOLD}{name}:{Colors.END}")
        for endpoint, success in results.items():
            if success:
                print(f"{Colors.GREEN}✓ {endpoint}{Colors.END}")
                available += 1
            else:
                print(f"{Colors.RED}✗ {endpoint}{Colors.END}")
                missing += 1

    # Print processor results
    count_and_print_category("Processor Endpoints", processor_results)

    # Print test results
    count_and_print_category("Test Results Endpoints", results_success)

    # Print stats results
    count_and_print_category("Stats Endpoints", stats_success)

    # Print other categories
    for category, results in category_results.items():
        count_and_print_category(category, results)

    # Print final summary
    print_header("Final Summary")
    print(f"Total endpoints tested: {available + missing}")
    print(f"{Colors.GREEN}Available endpoints: {available}{Colors.END}")
    print(f"{Colors.RED}Missing endpoints: {missing}{Colors.END}")

    if missing > 0:
        print_warning("\nPossible issues:")
        print("1. Router files might not be included in your main FastAPI app")
        print("2. API_PREFIX might be different than expected")
        print("3. Some endpoint path patterns might have changed")
        print("4. Authentication might be required for some endpoints")

        print_info("\nRecommended next steps:")
        print("1. Check your main.py to ensure all routers are included")
        print("2. Verify API_PREFIX in app/config.py")
        print("3. Look for custom middlewares that might be blocking requests")
        print("4. Check server logs for more detailed error information")


if __name__ == "__main__":
    main()