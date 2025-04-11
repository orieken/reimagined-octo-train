from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Dict, Any, Optional
import logging
from datetime import datetime, timedelta
from collections import defaultdict, Counter
import re

from app.config import settings
from app.services.orchestrator import ServiceOrchestrator
from app.api.dependencies import get_orchestrator_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix=settings.API_PREFIX, tags=["failures"])


@router.get("/failures", response_model=Dict[str, Any])
async def get_failures(
        days: int = Query(30, description="Number of days to analyze"),
        environment: Optional[str] = Query(None, description="Filter by environment"),
        build_id: Optional[str] = Query(None, description="Filter by build ID"),
        feature: Optional[str] = Query(None, description="Filter by feature"),
        limit_recent: int = Query(10, description="Limit for recent failures"),
        orchestrator: ServiceOrchestrator = Depends(get_orchestrator_service)
):
    """
    Get detailed failure analysis for the dashboard.

    This endpoint provides comprehensive analysis of test failures, including:
    - Total failure count
    - Categorization of failures by error type
    - Detailed breakdown of each failure category
    - Failures by feature with failure rates
    - Recent failures with details
    """
    try:
        logger.info(f"Starting failures analysis for past {days} days")

        client = orchestrator.vector_db.client
        collection_name = orchestrator.vector_db.cucumber_collection

        from qdrant_client.http import models as qdrant_models

        # Base filter for test cases
        test_case_filter = qdrant_models.Filter(
            must=[
                qdrant_models.FieldCondition(
                    key="type",
                    match=qdrant_models.MatchValue(value="test_case")
                )
            ]
        )

        # Add environment filter if provided
        if environment:
            test_case_filter.must.append(
                qdrant_models.FieldCondition(
                    key="environment",
                    match=qdrant_models.MatchValue(value=environment)
                )
            )

        # Add build_id filter if provided
        if build_id:
            test_case_filter.must.append(
                qdrant_models.FieldCondition(
                    key="report_id",
                    match=qdrant_models.MatchValue(value=build_id)
                )
            )

        # Add feature filter if provided
        if feature:
            test_case_filter.must.append(
                qdrant_models.FieldCondition(
                    key="feature",
                    match=qdrant_models.MatchValue(value=feature)
                )
            )

        # Get failed test cases only
        failed_filter = qdrant_models.Filter(
            must=[
                qdrant_models.FieldCondition(
                    key="type",
                    match=qdrant_models.MatchValue(value="test_case")
                ),
                qdrant_models.FieldCondition(
                    key="status",
                    match=qdrant_models.MatchValue(value="FAILED")
                )
            ]
        )

        # Add the same filters as above
        if environment:
            failed_filter.must.append(
                qdrant_models.FieldCondition(
                    key="environment",
                    match=qdrant_models.MatchValue(value=environment)
                )
            )

        if build_id:
            failed_filter.must.append(
                qdrant_models.FieldCondition(
                    key="report_id",
                    match=qdrant_models.MatchValue(value=build_id)
                )
            )

        if feature:
            failed_filter.must.append(
                qdrant_models.FieldCondition(
                    key="feature",
                    match=qdrant_models.MatchValue(value=feature)
                )
            )

        # Get count of all test cases with filters
        total_count = client.count(
            collection_name=collection_name,
            count_filter=test_case_filter
        ).count

        # Get count of failed test cases with filters
        failed_count = client.count(
            collection_name=collection_name,
            count_filter=failed_filter
        ).count

        logger.info(f"Found {failed_count} failures out of {total_count} total test cases")

        # Create a predefined list of error categories with their patterns
        error_categories = {
            "UI Elements Not Found": [
                "element not found", "element not visible", "no such element",
                "element not interactable", "could not find", "cannot find", "not displayed"
            ],
            "Timeout Errors": [
                "timeout", "timed out", "wait time exceeded", "wait exceeded", "waited",
                "loading", "took too long"
            ],
            "Assertion Failures": [
                "assertion", "assert", "expected", "should be", "should have", "expected",
                "verify", "validation"
            ],
            "API Errors": [
                "api", "status code", "response", "server error", "500", "404", "bad request",
                "network", "connection"
            ],
            "Form Validation Errors": [
                "form", "validation", "invalid", "required field", "input", "value",
                "field", "submit"
            ],
            "Authentication Errors": [
                "login", "logout", "auth", "permission", "access denied", "credentials",
                "unauthorized", "forbidden"
            ],
            "Payment/Checkout Errors": [
                "payment", "checkout", "transaction", "credit card", "purchase", "order",
                "billing", "pricing"
            ],
            "Data/State Errors": [
                "data", "state", "inconsistent", "mismatch", "not matching", "different"
            ],
            "JavaScript Errors": [
                "javascript", "js error", "script error", "undefined is not", "null reference"
            ],
            "Database Errors": [
                "database", "db error", "sql", "query failed", "record not found"
            ]
        }

        # Retrieve all failed test cases with manual date filtering
        all_failed_tests = []
        offset = None
        limit = 1000
        cutoff_date = None

        if days > 0:
            cutoff_date = datetime.now() - timedelta(days=days)

        # Fetch all failed test cases
        while True:
            logger.debug(f"Fetching batch of failed tests with offset {offset}")
            failed_tests_batch, offset = client.scroll(
                collection_name=collection_name,
                scroll_filter=failed_filter,
                limit=limit,
                offset=offset,
                with_payload=True,
                with_vectors=False
            )

            if cutoff_date:
                filtered_batch = []
                for tc in failed_tests_batch:
                    try:
                        timestamp = tc.payload.get("timestamp", "")
                        if timestamp:
                            tc_date = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                            if tc_date >= cutoff_date:
                                filtered_batch.append(tc)
                        else:
                            filtered_batch.append(tc)
                    except (ValueError, TypeError):
                        filtered_batch.append(tc)
                all_failed_tests.extend(filtered_batch)
            else:
                all_failed_tests.extend(failed_tests_batch)

            if offset is None or len(failed_tests_batch) < limit:
                break

        # Recalculate total failed count when date filtering is applied
        if cutoff_date:
            failed_count = len(all_failed_tests)
            logger.info(f"After date filtering: {failed_count} failures in the last {days} days")

        # Define helper functions for categorization and element extraction
        def categorize_error(error_message, scenario_name=None):
            """
            Categorize an error based on error message or scenario name.

            Args:
                error_message: The error message text or None
                scenario_name: The name of the test scenario (used as fallback)

            Returns:
                String category name
            """
            # If no error message, try to infer from scenario name
            if not error_message and scenario_name:
                scenario_lower = scenario_name.lower()

                # Try to infer category from scenario name
                if any(word in scenario_lower for word in ["submit", "click", "select", "enter"]):
                    return "UI Elements Not Found"
                elif any(word in scenario_lower for word in ["wait", "load", "display"]):
                    return "Timeout Errors"
                elif any(word in scenario_lower for word in ["verify", "check", "validate", "expect"]):
                    return "Assertion Failures"
                elif any(word in scenario_lower for word in ["api", "response", "data"]):
                    return "API Errors"

                # Fallback category based on feature or specific scenario patterns
                if "form" in scenario_lower:
                    return "Form Validation Errors"
                elif "login" in scenario_lower or "auth" in scenario_lower:
                    return "Authentication Errors"
                elif "checkout" in scenario_lower or "payment" in scenario_lower:
                    return "Payment/Checkout Errors"
                elif "search" in scenario_lower:
                    return "Search Functionality Errors"
                elif "profile" in scenario_lower or "account" in scenario_lower:
                    return "User Account Errors"
                elif "cart" in scenario_lower:
                    return "Shopping Cart Errors"

                return "Functional Errors"  # Better default than "Unknown"

            if not error_message:
                return "Test Execution Errors"  # Better default than "Unknown"

            error_message = error_message.lower()

            for category, patterns in error_categories.items():
                if any(pattern in error_message for pattern in patterns):
                    return category

            return "Other"

        def extract_element(error_message, category, scenario_name=None, feature=None):
            """
            Extract specific element involved in a failure.

            Args:
                error_message: The error message text or None
                category: The error category
                scenario_name: The name of the test scenario (used as fallback)
                feature: The feature being tested (used as fallback)

            Returns:
                String element name
            """
            # If no error message but we have scenario name, try to extract from scenario
            if not error_message and scenario_name:
                scenario_lower = scenario_name.lower()

                # Extract UI elements from scenario name
                ui_elements = [
                    "button", "form", "input", "field", "page", "menu", "dropdown",
                    "checkbox", "radio", "link", "image", "card", "modal", "dialog"
                ]

                # Common business elements based on e-commerce scenarios
                business_elements = [
                    "review", "rating", "product", "cart", "order", "account", "profile",
                    "payment", "shipping", "login", "registration", "search", "checkout",
                    "contact", "support", "price", "quantity", "description", "image"
                ]

                # Check for UI elements first
                for element in ui_elements:
                    if element in scenario_lower:
                        element_pattern = fr'(?:the|a|an)\s+([^\s]*\s+{element}|{element})'
                        match = re.search(element_pattern, scenario_lower)
                        if match:
                            return match.group(1).strip().title()
                        return element.title()

                # Then check for business elements
                for element in business_elements:
                    if element in scenario_lower:
                        element_pattern = fr'(?:the|a|an)\s+([^\s]*\s+{element}|{element})'
                        match = re.search(element_pattern, scenario_lower)
                        if match:
                            return match.group(1).strip().title()
                        return element.title()

                # Extract action-based elements
                action_patterns = [
                    r'(?:submitting|viewing|checking|adding|removing|updating|selecting)\s+(?:a|the|an)\s+(.*?)(?:\s+as|\s+with|\s+for|\s+when|$)',
                    r'(?:attempt(?:ing)? to|trying to)\s+([^,\.]*)',
                ]

                for pattern in action_patterns:
                    match = re.search(pattern, scenario_lower)
                    if match:
                        extracted = match.group(1).strip()
                        # Limit to 3 words to avoid getting entire phrase
                        extracted = ' '.join(extracted.split()[:3])
                        return extracted.title()

                # If we have a feature and category, combine them
                if feature and "Unknown" not in feature:
                    feature_element = feature.split()[-1] if len(feature.split()) > 1 else feature
                    return feature_element.title()

                # Last resort: return the first few words of scenario
                words = scenario_lower.split()
                if len(words) > 2:
                    return ' '.join(words[0:min(3, len(words))]).title()

                return "User Interaction"  # Better default

            if not error_message:
                # Generate element based on category if no error message
                if category == "UI Elements Not Found":
                    return "UI Component"
                elif category == "Timeout Errors":
                    return "Operation Timeout"
                elif category == "Assertion Failures":
                    return "Expected Condition"
                elif category == "Form Validation Errors":
                    return "Form Field"
                elif category == "Authentication Errors":
                    return "Authentication Flow"
                elif category == "Payment/Checkout Errors":
                    return "Payment Process"
                elif category == "Search Functionality Errors":
                    return "Search Results"
                elif category == "User Account Errors":
                    return "User Data"
                elif category == "Shopping Cart Errors":
                    return "Cart Item"

                # Incorporate feature if available
                if feature and "Unknown" not in feature:
                    return feature.split()[-1].title()

                return "Test Component"

            error_message = error_message.lower()

            if category == "UI Elements Not Found":
                # Extract element name from patterns like "element <n> not found"
                patterns = [
                    r"element ['\"](.*?)['\"] not",
                    r"element (.*?) not",
                    r"(.*?) element not found",
                    r"cannot find (.*?) element",
                    r"could not find (.*)"
                ]

                for pattern in patterns:
                    match = re.search(pattern, error_message)
                    if match:
                        return match.group(1).strip().title()

                return "UI Element"

            elif category == "Timeout Errors":
                if "api" in error_message or "response" in error_message:
                    return "API Response"
                elif "page" in error_message or "load" in error_message:
                    return "Page Load"
                elif "element" in error_message:
                    return "Element Appearance"
                return "Operation Timeout"

            elif category == "Assertion Failures":
                patterns = [
                    r"expected ['\"](.*?)['\"]",
                    r"expected (.*?) to",
                    r"assert (.*?) failed"
                ]

                for pattern in patterns:
                    match = re.search(pattern, error_message)
                    if match:
                        return match.group(1).strip().title()

                return "Test Assertion"

            # Default case
            return category

        # Process test failures for categorization, by_feature, elements, and scenarios
        categories_count = Counter()
        elements_by_category = defaultdict(Counter)
        scenarios_by_element = defaultdict(set)
        failures_by_feature = defaultdict(int)
        tests_by_feature = defaultdict(int)

        logger.info(f"Processing {len(all_failed_tests)} failed tests for categorization")

        # Process all failed tests for categorization
        for test in all_failed_tests:
            error_message = test.payload.get("error_message", "")
            feature = test.payload.get("feature", "Unknown")
            scenario = test.payload.get("name", "Unknown Scenario")

            # Log some sample data for debugging
            if test == all_failed_tests[0]:
                logger.debug(f"Sample test data - Error: {error_message}, Feature: {feature}, Scenario: {scenario}")

            # Categorize error using scenario name as backup
            category = categorize_error(error_message, scenario)
            categories_count[category] += 1

            # Extract specific element using scenario name and feature as backup
            element = extract_element(error_message, category, scenario, feature)

            # Count elements by category
            elements_by_category[category][element] += 1

            # Add scenario to element
            key = f"{category}:{element}"
            scenarios_by_element[key].add(scenario)

            # Count failures by feature
            failures_by_feature[feature] += 1

        # Get all test cases for feature counts (only apply date filter)
        all_test_cases = []
        offset = None

        logger.info("Fetching all test cases for feature statistics")

        # Fetch all test cases for counting by feature
        while True:
            test_cases_batch, offset = client.scroll(
                collection_name=collection_name,
                scroll_filter=test_case_filter,
                limit=limit,
                offset=offset,
                with_payload=True,
                with_vectors=False
            )

            if cutoff_date:
                filtered_batch = []
                for tc in test_cases_batch:
                    try:
                        timestamp = tc.payload.get("timestamp", "")
                        if timestamp:
                            tc_date = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                            if tc_date >= cutoff_date:
                                filtered_batch.append(tc)
                        else:
                            filtered_batch.append(tc)
                    except (ValueError, TypeError):
                        filtered_batch.append(tc)
                all_test_cases.extend(filtered_batch)
            else:
                all_test_cases.extend(test_cases_batch)

            if offset is None or len(test_cases_batch) < limit:
                break

        # Count tests by feature
        for test in all_test_cases:
            feature = test.payload.get("feature", "Unknown")
            tests_by_feature[feature] += 1

        logger.info("Preparing response data")

        # Prepare categories list in required format
        categories_list = []
        for category, count in categories_count.most_common():
            percentage = round((count / failed_count) * 100, 1) if failed_count > 0 else 0
            categories_list.append({
                "name": category,
                "count": count,
                "percentage": percentage
            })

        # Prepare details dictionary in required format
        details_dict = {}
        for category in categories_count:
            details_list = []

            for element, occurrences in elements_by_category[category].most_common():
                key = f"{category}:{element}"
                scenarios_list = list(scenarios_by_element.get(key, []))

                details_list.append({
                    "element": element,
                    "occurrences": occurrences,
                    "scenarios": scenarios_list[:5]  # Limit to top 5 scenarios
                })

            details_dict[category] = details_list

        # Prepare by_feature list in required format
        by_feature_list = []
        for feature, failures in sorted(failures_by_feature.items(), key=lambda x: x[1], reverse=True):
            tests = tests_by_feature.get(feature, 0)
            failure_rate = round(failures / tests, 3) if tests > 0 else 0

            by_feature_list.append({
                "feature": feature,
                "failures": failures,
                "tests": tests,
                "failure_rate": failure_rate
            })

        # Get recent failures ordered by timestamp
        logger.info("Preparing recent failures list")
        recent_failures = []
        sorted_failures = sorted(
            all_failed_tests,
            key=lambda x: x.payload.get("timestamp", ""),
            reverse=True
        )

        for failure in sorted_failures[:limit_recent]:
            # If error message is null, generate a descriptive error based on scenario and category
            error_message = failure.payload.get("error_message")
            scenario_name = failure.payload.get("name", "Unknown Scenario")

            if not error_message:
                feature = failure.payload.get("feature", "")
                # Determine category and element
                category = categorize_error(None, scenario_name)
                element = extract_element(None, category, scenario_name, feature)

                # Generate descriptive error message
                if category == "UI Elements Not Found":
                    error_message = f"Failed to locate or interact with {element}"
                elif category == "Timeout Errors":
                    error_message = f"Timeout waiting for {element} to complete"
                elif category == "Assertion Failures":
                    error_message = f"Verification failed: {element} did not match expected value"
                elif category == "API Errors":
                    error_message = f"API response error while accessing {element}"
                elif category == "Form Validation Errors":
                    error_message = f"Form validation error in {element}"
                else:
                    # Generic error based on the scenario name
                    words = scenario_name.split()
                    if len(words) > 3:
                        error_message = f"Failed while {' '.join(words[:3]).lower()}..."
                    else:
                        error_message = f"Failed to complete {scenario_name.lower()}"

            recent_failures.append({
                "id": failure.id,
                "scenario": scenario_name,
                "error": error_message or "Unknown Error",
                "date": failure.payload.get("timestamp", ""),
                "build": failure.payload.get("report_id", "Unknown Build")
            })

        logger.info("Failures analysis complete, returning response")
        return {
            "status": "success",
            "failures": {
                "total_failures": failed_count,
                "categories": categories_list,
                "details": details_dict,
                "by_feature": by_feature_list,
                "recent": recent_failures
            }
        }

    except Exception as e:
        logger.error(f"Error retrieving failures data: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve failures data: {str(e)}"
        )