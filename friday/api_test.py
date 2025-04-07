#!/usr/bin/env python3
"""
Test Stats API Testing Script

This script tests the API endpoints for the Test Stats service.
It makes requests to the various endpoints and displays the results.
"""

import argparse
import json
import requests
import sys
from typing import Dict, Any, List, Optional


class TestStatsAPITester:
    """Class for testing the Test Stats API endpoints."""

    def __init__(self, base_url: str):
        """
        Initialize the tester with the base URL.

        Args:
            base_url: Base URL of the API (e.g., http://localhost:8000)
        """
        self.base_url = base_url.rstrip('/')
        self.api_prefix = "/api/v1"  # Adjust according to your settings.API_PREFIX

    def make_request(self, endpoint: str, method: str = "GET", params: Optional[Dict[str, Any]] = None) -> Dict[
        str, Any]:
        """
        Make an HTTP request to the API.

        Args:
            endpoint: API endpoint (without base URL)
            method: HTTP method (GET, POST, etc.)
            params: Query parameters

        Returns:
            Response from the API as a dict
        """
        url = f"{self.base_url}{self.api_prefix}{endpoint}"
        print(f"\n>>> Making {method} request to {url}")
        if params:
            print(f"    with params: {params}")

        try:
            if method.upper() == "GET":
                response = requests.get(url, params=params)
            elif method.upper() == "POST":
                response = requests.post(url, json=params)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")

            print(f"<<< Status: {response.status_code}")
            if response.ok:
                return response.json()
            else:
                print(f"Error: {response.text}")
                return {"error": response.text}
        except Exception as e:
            print(f"Error making request: {str(e)}")
            return {"error": str(e)}

    def test_stats_endpoint(self) -> Dict[str, Any]:
        """
        Test the /stats endpoint.

        Returns:
            Response from the API
        """
        print("\n=== Testing /stats endpoint ===")
        return self.make_request("/stats")

    def test_stats_with_params(self, days: int = 30, environment: Optional[str] = None) -> Dict[str, Any]:
        """
        Test the /stats endpoint with parameters.

        Args:
            days: Number of days to analyze
            environment: Filter by environment

        Returns:
            Response from the API
        """
        print(f"\n=== Testing /stats with days={days}, environment={environment} ===")
        params = {"days": days}
        if environment:
            params["environment"] = environment
        return self.make_request("/stats", params=params)

    def test_stats_by_feature_endpoint(self) -> Dict[str, Any]:
        """
        Test the /stats/by-feature endpoint.

        Returns:
            Response from the API
        """
        print("\n=== Testing /stats/by-feature endpoint ===")
        return self.make_request("/stats/by-feature")

    def test_stats_by_feature_with_params(
            self,
            days: int = 30,
            environment: Optional[str] = None,
            limit: int = 10,
            sort_by: str = "pass_rate"
    ) -> Dict[str, Any]:
        """
        Test the /stats/by-feature endpoint with parameters.

        Args:
            days: Number of days to analyze
            environment: Filter by environment
            limit: Number of features to return
            sort_by: Field to sort by

        Returns:
            Response from the API
        """
        print(f"\n=== Testing /stats/by-feature with params ===")
        params = {
            "days": days,
            "limit": limit,
            "sort_by": sort_by
        }
        if environment:
            params["environment"] = environment
        return self.make_request("/stats/by-feature", params=params)

    def test_stats_by_environment_endpoint(self) -> Dict[str, Any]:
        """
        Test the /stats/by-environment endpoint.

        Returns:
            Response from the API
        """
        print("\n=== Testing /stats/by-environment endpoint ===")
        return self.make_request("/stats/by-environment")

    def test_stats_by_environment_with_params(self, days: int = 30) -> Dict[str, Any]:
        """
        Test the /stats/by-environment endpoint with parameters.

        Args:
            days: Number of days to analyze

        Returns:
            Response from the API
        """
        print(f"\n=== Testing /stats/by-environment with days={days} ===")
        params = {"days": days}
        return self.make_request("/stats/by-environment", params=params)

    def test_stats_summary_endpoint(self) -> Dict[str, Any]:
        """
        Test the /stats/summary endpoint.

        Returns:
            Response from the API
        """
        print("\n=== Testing /stats/summary endpoint ===")
        return self.make_request("/stats/summary")

    def run_all_tests(self) -> None:
        """Run all test cases."""
        print(f"Testing Test Stats API at {self.base_url}")

        # Test /stats endpoint
        stats_response = self.test_stats_endpoint()
        self.print_response(stats_response)

        # Test /stats with parameters
        stats_params_response = self.test_stats_with_params(days=15, environment="production")
        self.print_response(stats_params_response)

        # Test /stats/by-feature endpoint
        by_feature_response = self.test_stats_by_feature_endpoint()
        self.print_response(by_feature_response)

        # Test /stats/by-feature with parameters
        by_feature_params_response = self.test_stats_by_feature_with_params(
            days=15,
            environment="staging",
            limit=5,
            sort_by="failed_tests"
        )
        self.print_response(by_feature_params_response)

        # Test /stats/by-environment endpoint
        by_environment_response = self.test_stats_by_environment_endpoint()
        self.print_response(by_environment_response)

        # Test /stats/by-environment with parameters
        by_environment_params_response = self.test_stats_by_environment_with_params(days=7)
        self.print_response(by_environment_params_response)

        # Test /stats/summary endpoint
        summary_response = self.test_stats_summary_endpoint()
        self.print_response(summary_response)

    def print_response(self, response: Dict[str, Any]) -> None:
        """
        Print a formatted response.

        Args:
            response: API response as a dict
        """
        print("\nResponse:")
        if "error" in response:
            print(f"  Error: {response['error']}")
        else:
            print(json.dumps(response, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test the Test Stats API endpoints")
    parser.add_argument("--base-url", default="http://localhost:4000", help="Base URL of the API")

    args = parser.parse_args()

    tester = TestStatsAPITester(args.base_url)
    tester.run_all_tests()