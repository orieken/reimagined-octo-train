# app/services/failure_analysis_service.py

import re
from typing import Optional, Dict, List


class FailureAnalysisService:
    _error_categories: Dict[str, List[str]] = {
        "UI Elements Not Found": [
            "element not found", "element not visible", "no such element",
            "element not interactable", "could not find", "cannot find", "not displayed"
        ],
        "Timeout Errors": [
            "timeout", "timed out", "wait time exceeded", "wait exceeded", "waited",
            "loading", "took too long"
        ],
        "Assertion Failures": [
            "assertion", "assert", "expected", "should be", "should have",
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

    def categorize_error(self, error_message: Optional[str], scenario_name: Optional[str] = None) -> str:
        if not error_message and scenario_name:
            scenario_lower = scenario_name.lower()
            if any(w in scenario_lower for w in ["submit", "click", "select", "enter"]):
                return "UI Elements Not Found"
            if any(w in scenario_lower for w in ["wait", "load", "display"]):
                return "Timeout Errors"
            if any(w in scenario_lower for w in ["verify", "check", "validate", "expect"]):
                return "Assertion Failures"
            if any(w in scenario_lower for w in ["api", "response", "data"]):
                return "API Errors"
            if "form" in scenario_lower:
                return "Form Validation Errors"
            if "login" in scenario_lower or "auth" in scenario_lower:
                return "Authentication Errors"
            if "checkout" in scenario_lower or "payment" in scenario_lower:
                return "Payment/Checkout Errors"
            if "search" in scenario_lower:
                return "Search Functionality Errors"
            if "profile" in scenario_lower or "account" in scenario_lower:
                return "User Account Errors"
            if "cart" in scenario_lower:
                return "Shopping Cart Errors"
            return "Functional Errors"

        if not error_message:
            return "Test Execution Errors"

        error_message = error_message.lower()
        for category, patterns in self._error_categories.items():
            if any(p in error_message for p in patterns):
                return category

        return "Other"

    def extract_element(
        self,
        error_message: Optional[str],
        category: str,
        scenario_name: Optional[str] = None,
        feature: Optional[str] = None
    ) -> str:
        if not error_message and scenario_name:
            scenario_lower = scenario_name.lower()

            ui_elements = [
                "button", "form", "input", "field", "page", "menu", "dropdown",
                "checkbox", "radio", "link", "image", "card", "modal", "dialog"
            ]
            business_elements = [
                "review", "rating", "product", "cart", "order", "account", "profile",
                "payment", "shipping", "login", "registration", "search", "checkout",
                "contact", "support", "price", "quantity", "description", "image"
            ]

            for element in ui_elements + business_elements:
                if element in scenario_lower:
                    match = re.search(fr'(?:the|a|an)\s+([^\s]*\s+{element}|{element})', scenario_lower)
                    if match:
                        return match.group(1).strip().title()
                    return element.title()

            for pattern in [
                r'(?:submitting|viewing|checking|adding|removing|updating|selecting)\s+(?:a|the|an)\s+(.*?)(?:\s+as|\s+with|\s+for|\s+when|$)',
                r'(?:attempt(?:ing)? to|trying to)\s+([^,\.]*)',
            ]:
                match = re.search(pattern, scenario_lower)
                if match:
                    return ' '.join(match.group(1).strip().split()[:3]).title()

            if feature and "Unknown" not in feature:
                return feature.split()[-1].title()

            words = scenario_lower.split()
            return ' '.join(words[:3]).title() if len(words) > 2 else "User Interaction"

        if not error_message:
            return {
                "UI Elements Not Found": "UI Component",
                "Timeout Errors": "Operation Timeout",
                "Assertion Failures": "Expected Condition",
                "Form Validation Errors": "Form Field",
                "Authentication Errors": "Authentication Flow",
                "Payment/Checkout Errors": "Payment Process",
                "Search Functionality Errors": "Search Results",
                "User Account Errors": "User Data",
                "Shopping Cart Errors": "Cart Item"
            }.get(category, feature.split()[-1].title() if feature else "Test Component")

        error_message = error_message.lower()

        if category == "UI Elements Not Found":
            for pattern in [
                r"element ['\"](.*?)['\"] not",
                r"element (.*?) not",
                r"(.*?) element not found",
                r"cannot find (.*?) element",
                r"could not find (.*)"
            ]:
                match = re.search(pattern, error_message)
                if match:
                    return match.group(1).strip().title()
            return "UI Element"

        if category == "Timeout Errors":
            if "api" in error_message or "response" in error_message:
                return "API Response"
            if "page" in error_message or "load" in error_message:
                return "Page Load"
            if "element" in error_message:
                return "Element Appearance"
            return "Operation Timeout"

        if category == "Assertion Failures":
            for pattern in [
                r"expected ['\"](.*?)['\"]",
                r"expected (.*?) to",
                r"assert (.*?) failed"
            ]:
                match = re.search(pattern, error_message)
                if match:
                    return match.group(1).strip().title()
            return "Test Assertion"

        return category
