#!/usr/bin/env python3
"""
API and Database Diagnostic Script

This script diagnoses discrepancies between what's in your database
and what your API endpoints are expecting.
"""

import sys
import json
import requests
from qdrant_client import QdrantClient
from qdrant_client.http import models as qdrant_models

# Configuration - Adjust these values to match your setup
QDRANT_URL = "http://localhost:6333"
API_URL = "http://localhost:4000"
CUCUMBER_COLLECTION = "test_artifacts"
API_PREFIX = "/api/v1"


def inspect_database():
    """Inspect the database to see what's actually there."""
    try:
        print(f"Connecting to Qdrant at {QDRANT_URL}...")
        client = QdrantClient(url=QDRANT_URL)

        # Get collection info
        print(f"Checking collection '{CUCUMBER_COLLECTION}'...")
        try:
            collection_info = client.get_collection(collection_name=CUCUMBER_COLLECTION)
            print(f"Collection exists: {collection_info}")
        except Exception as e:
            print(f"Error getting collection: {str(e)}")
            return

        # Count different types of points
        type_values = ["test_case", "report", "testcase", "scenario", "Report", "TestCase"]
        print("\nCounting points by 'type' field:")
        for type_value in type_values:
            count = client.count(
                collection_name=CUCUMBER_COLLECTION,
                count_filter=qdrant_models.Filter(
                    must=[
                        qdrant_models.FieldCondition(
                            key="type",
                            match=qdrant_models.MatchValue(value=type_value)
                        )
                    ]
                )
            ).count
            print(f"  type='{type_value}': {count} points")

        # Sample data structure
        print("\nSampling data structure:")

        # First, get a sample test_case
        test_case_samples = client.scroll(
            collection_name=CUCUMBER_COLLECTION,
            scroll_filter=qdrant_models.Filter(
                must=[
                    qdrant_models.FieldCondition(
                        key="type",
                        match=qdrant_models.MatchValue(value="test_case")
                    )
                ]
            ),
            limit=1
        )[0]

        if test_case_samples:
            tc = test_case_samples[0]
            print("\nSample test_case structure:")
            print(f"  ID: {tc.id}")
            print("  Fields present:")
            for key in tc.payload.keys():
                field_type = type(tc.payload[key]).__name__
                field_sample = str(tc.payload[key])
                if isinstance(tc.payload[key], (list, dict)):
                    field_sample = json.dumps(tc.payload[key])[:50] + "..." if len(
                        json.dumps(tc.payload[key])) > 50 else json.dumps(tc.payload[key])
                elif isinstance(tc.payload[key], str) and len(tc.payload[key]) > 50:
                    field_sample = tc.payload[key][:50] + "..."

                print(f"    - {key} ({field_type}): {field_sample}")
        else:
            print("No test_case samples found")

        # Get a sample report
        report_samples = client.scroll(
            collection_name=CUCUMBER_COLLECTION,
            scroll_filter=qdrant_models.Filter(
                must=[
                    qdrant_models.FieldCondition(
                        key="type",
                        match=qdrant_models.MatchValue(value="report")
                    )
                ]
            ),
            limit=1
        )[0]

        if report_samples:
            report = report_samples[0]
            print("\nSample report structure:")
            print(f"  ID: {report.id}")
            print("  Fields present:")
            for key in report.payload.keys():
                field_type = type(report.payload[key]).__name__
                field_sample = str(report.payload[key])
                if isinstance(report.payload[key], (list, dict)):
                    field_sample = json.dumps(report.payload[key])[:50] + "..." if len(
                        json.dumps(report.payload[key])) > 50 else json.dumps(report.payload[key])
                elif isinstance(report.payload[key], str) and len(report.payload[key]) > 50:
                    field_sample = report.payload[key][:50] + "..."

                print(f"    - {key} ({field_type}): {field_sample}")
        else:
            print("No report samples found")

        # Count status values
        status_values = ["PASSED", "FAILED", "SKIPPED", "passed", "failed", "skipped"]
        print("\nCounting points by 'status' field:")
        for status in status_values:
            count = client.count(
                collection_name=CUCUMBER_COLLECTION,
                count_filter=qdrant_models.Filter(
                    must=[
                        qdrant_models.FieldCondition(
                            key="status",
                            match=qdrant_models.MatchValue(value=status)
                        )
                    ]
                )
            ).count
            print(f"  status='{status}': {count} points")

        # Count environments
        print("\nCounting points by 'environment' field:")
        environments = ["dev", "staging", "production", "qa", "integration"]
        for env in environments:
            count = client.count(
                collection_name=CUCUMBER_COLLECTION,
                count_filter=qdrant_models.Filter(
                    must=[
                        qdrant_models.FieldCondition(
                            key="environment",
                            match=qdrant_models.MatchValue(value=env)
                        )
                    ]
                )
            ).count
            print(f"  environment='{env}': {count} points")

        # Count by feature
        print("\nCounting test cases by feature (top 5):")
        features_dict = {}

        test_cases = client.scroll(
            collection_name=CUCUMBER_COLLECTION,
            scroll_filter=qdrant_models.Filter(
                must=[
                    qdrant_models.FieldCondition(
                        key="type",
                        match=qdrant_models.MatchValue(value="test_case")
                    )
                ]
            ),
            limit=1000
        )[0]

        for tc in test_cases:
            feature = tc.payload.get("feature")
            if feature:
                features_dict[feature] = features_dict.get(feature, 0) + 1

        for feature, count in sorted(features_dict.items(), key=lambda x: x[1], reverse=True)[:5]:
            print(f"  feature='{feature}': {count} test cases")

    except Exception as e:
        print(f"Error inspecting database: {str(e)}")


def inspect_api():
    """Inspect the API to see what endpoints are available and how they're responding."""
    try:
        print(f"Testing API at {API_URL}{API_PREFIX}...")

        # Test endpoints
        endpoints = [
            "/stats",
            "/stats/by-feature",
            "/stats/by-environment",
            "/stats/summary"
        ]

        for endpoint in endpoints:
            url = f"{API_URL}{API_PREFIX}{endpoint}"
            print(f"\nTesting endpoint: {url}")

            try:
                response = requests.get(url)
                print(f"  Status code: {response.status_code}")

                if response.ok:
                    json_response = response.json()
                    if isinstance(json_response, dict):
                        print("  Response structure:")
                        print_nested_structure(json_response)
                    elif isinstance(json_response, list):
                        print(f"  Response is a list with {len(json_response)} items")
                        if json_response:
                            print("  First item structure:")
                            print_nested_structure(json_response[0])
                    else:
                        print(f"  Response: {json_response}")
                else:
                    print(f"  Error: {response.text}")
            except Exception as e:
                print(f"  Error testing endpoint: {str(e)}")

    except Exception as e:
        print(f"Error inspecting API: {str(e)}")


def print_nested_structure(obj, indent=2, max_level=2, level=0):
    """Print a nested structure recursively with indentation."""
    if level > max_level:
        print(" " * indent * level + "...")
        return

    if isinstance(obj, dict):
        for key, value in obj.items():
            if isinstance(value, (dict, list)):
                print(" " * indent * level + f"{key}:")
                print_nested_structure(value, indent, max_level, level + 1)
            else:
                value_str = str(value)
                if len(value_str) > 50:
                    value_str = value_str[:50] + "..."
                print(" " * indent * level + f"{key}: {value_str}")

    elif isinstance(obj, list):
        if not obj:
            print(" " * indent * level + "[]")
        elif isinstance(obj[0], (dict, list)):
            print(" " * indent * level + f"[{len(obj)} items]")
            if obj:
                print_nested_structure(obj[0], indent, max_level, level + 1)
        else:
            sample = str(obj[:3]) + ("..." if len(obj) > 3 else "")
            print(" " * indent * level + f"{sample}")


def analyze_issues():
    """Analyze potential issues based on the inspections."""
    try:
        print("\n=== Potential Issues Analysis ===")

        # Check collection existence
        client = QdrantClient(url=QDRANT_URL)
        collections = client.get_collections().collections
        collection_names = [collection.name for collection in collections]

        if CUCUMBER_COLLECTION not in collection_names:
            print("CRITICAL: Collection doesn't exist! Your API can't find any data.")
            return

        # Count basic entities
        test_case_count = client.count(
            collection_name=CUCUMBER_COLLECTION,
            count_filter=qdrant_models.Filter(
                must=[
                    qdrant_models.FieldCondition(
                        key="type",
                        match=qdrant_models.MatchValue(value="test_case")
                    )
                ]
            )
        ).count

        report_count = client.count(
            collection_name=CUCUMBER_COLLECTION,
            count_filter=qdrant_models.Filter(
                must=[
                    qdrant_models.FieldCondition(
                        key="type",
                        match=qdrant_models.MatchValue(value="report")
                    )
                ]
            )
        ).count

        # Test API responses
        api_issues = []
        try:
            stats_response = requests.get(f"{API_URL}{API_PREFIX}/stats").json()
            total_scenarios = stats_response.get("statistics", {}).get("total_scenarios", 0)

            if total_scenarios == 0 and test_case_count > 0:
                api_issues.append("API /stats reports 0 scenarios despite test_case data in DB")

            feature_response = requests.get(f"{API_URL}{API_PREFIX}/stats/by-feature").json()
            if isinstance(feature_response, list) and not feature_response and test_case_count > 0:
                api_issues.append("API /stats/by-feature returns empty list despite test_case data in DB")

        except Exception as e:
            api_issues.append(f"Error testing API endpoints: {str(e)}")

        # Print analysis
        print("\nData Summary:")
        print(f"  test_case count: {test_case_count}")
        print(f"  report count: {report_count}")

        print("\nAPI Issues:")
        if api_issues:
            for issue in api_issues:
                print(f"  - {issue}")
        else:
            print("  No apparent API issues detected")

        # Check for common problems
        print("\nPotential problems:")

        # Type name mismatch
        alternative_type_values = ["testcase", "scenario", "Report", "TestCase"]
        alternative_type_count = 0

        for type_value in alternative_type_values:
            count = client.count(
                collection_name=CUCUMBER_COLLECTION,
                count_filter=qdrant_models.Filter(
                    must=[
                        qdrant_models.FieldCondition(
                            key="type",
                            match=qdrant_models.MatchValue(value=type_value)
                        )
                    ]
                )
            ).count
            alternative_type_count += count

        if alternative_type_count > 0:
            print(f"  - Found {alternative_type_count} points with non-standard type values")

        # Status case mismatch
        status_values = ["passed", "failed", "skipped"]
        lowercase_status_count = 0

        for status in status_values:
            count = client.count(
                collection_name=CUCUMBER_COLLECTION,
                count_filter=qdrant_models.Filter(
                    must=[
                        qdrant_models.FieldCondition(
                            key="status",
                            match=qdrant_models.MatchValue(value=status)
                        )
                    ]
                )
            ).count
            lowercase_status_count += count

        if lowercase_status_count > 0:
            print(f"  - Found {lowercase_status_count} points with lowercase status values")

        # Check for missing fields
        print("\nKey field inspection:")

        missing_fields = []
        sample_fields = ["type", "status", "feature", "report_id", "environment", "tags"]

        total_points = client.count(collection_name=CUCUMBER_COLLECTION).count
        for field in sample_fields:
            field_exists_filter = qdrant_models.Filter(
                must=[
                    qdrant_models.FieldCondition(
                        key=field,
                        match=qdrant_models.MatchAny(any=[""])
                    )
                ]
            )

            # This is a workaround since Qdrant doesn't directly support "field exists" queries
            try:
                # We're just checking if the query executes without error
                client.scroll(
                    collection_name=CUCUMBER_COLLECTION,
                    scroll_filter=field_exists_filter,
                    limit=1
                )
                print(f"  - Field '{field}' appears to exist in the data")
            except Exception:
                print(f"  - Field '{field}' may be missing in some or all records")
                missing_fields.append(field)

        # Recommendations
        print("\nRecommendations:")

        if not test_case_count and not report_count:
            print("  - No data found! Run the data population script again.")

        if api_issues:
            print("  - Check the collection name in your API settings")
            print("  - Compare filter construction in semantic_search method with data format")
            print("  - Check if your API expects a different field structure or naming")

        if missing_fields:
            print(f"  - Add missing fields to your data: {', '.join(missing_fields)}")

        if alternative_type_count > 0:
            print("  - Fix inconsistent 'type' values in your data")

        if lowercase_status_count > 0:
            print("  - Standardize status values to be uppercase (PASSED, FAILED, SKIPPED)")

    except Exception as e:
        print(f"Error during analysis: {str(e)}")


if __name__ == "__main__":
    print("=== API and Database Diagnostic Tool ===")
    print("\nInspecting database...")
    inspect_database()

    print("\nInspecting API endpoints...")
    inspect_api()

    print("\nAnalyzing issues...")
    analyze_issues()
