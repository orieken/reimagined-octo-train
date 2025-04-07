#!/usr/bin/env python3
"""
Cucumber Report Generator for Friday CLI

This module provides functionality to generate realistic Cucumber JSON test reports
for testing the /processor/cucumber-reports endpoint.
"""

import json
import random
import string
from datetime import datetime


class CucumberReportGenerator:
    """Generate realistic Cucumber JSON test reports."""

    # Define realistic feature and scenario names
    FEATURES = [
        {"name": "User Authentication", "scenarios": [
            "User can login with valid credentials",
            "User cannot login with invalid credentials",
            "User can reset password",
            "User account is locked after multiple failed attempts",
            "User session expires after inactivity timeout"
        ]},
        {"name": "Shopping Cart", "scenarios": [
            "User can add items to cart",
            "User can remove items from cart",
            "Cart total updates correctly when items are added",
            "Cart persists items when user logs out and back in",
            "Out of stock items cannot be added to cart"
        ]},
        {"name": "Checkout Process", "scenarios": [
            "User can complete checkout with valid payment details",
            "User receives order confirmation after checkout",
            "User cannot complete checkout with invalid payment details",
            "User can apply valid discount code during checkout",
            "Shipping cost is calculated correctly based on address"
        ]},
        {"name": "Product Search", "scenarios": [
            "User can search for products by keyword",
            "Search results are displayed in relevance order",
            "Search filters work correctly",
            "No results page is displayed for invalid search terms",
            "Product recommendations appear on search results"
        ]},
        {"name": "User Profile", "scenarios": [
            "User can update personal information",
            "User can change password",
            "User can view order history",
            "User can manage saved payment methods",
            "User can update notification preferences"
        ]},
        {"name": "Admin Dashboard", "scenarios": [
            "Admin can view site analytics",
            "Admin can manage user accounts",
            "Admin can process refunds",
            "Admin can update product inventory",
            "Admin can view and filter order history"
        ]}
    ]

    # Define realistic error patterns
    ERROR_PATTERNS = [
        {
            "message": "Element not found: Failed to locate element {locator}",
            "trace": "org.openqa.selenium.NoSuchElementException: no such element: Unable to locate element: {locator}\n  at org.openqa.selenium.remote.RemoteWebDriver.findElement(RemoteWebDriver.java:352)\n  at org.openqa.selenium.remote.RemoteWebDriver.findElementBy(RemoteWebDriver.java:310)"
        },
        {
            "message": "Timeout waiting for page load",
            "trace": "org.openqa.selenium.TimeoutException: timeout: Timed out receiving message from renderer\n  at java.base/java.util.concurrent.ThreadPoolExecutor.runWorker(ThreadPoolExecutor.java:1128)\n  at java.base/java.util.concurrent.ThreadPoolExecutor$Worker.run(ThreadPoolExecutor.java:628)"
        },
        {
            "message": "API response status code 500",
            "trace": "java.lang.AssertionError: expected [200] but found [500]\n  at org.testng.Assert.fail(Assert.java:96)\n  at org.testng.Assert.failNotEquals(Assert.java:776)\n  at org.testng.Assert.assertEquals(Assert.java:118)"
        },
        {
            "message": "Expected text not present on page",
            "trace": "java.lang.AssertionError: Expected text 'Welcome, User' not found on page\n  at org.testng.Assert.fail(Assert.java:96)\n  at com.example.tests.UserLoginTest.verifyWelcomeMessage(UserLoginTest.java:42)"
        },
        {
            "message": "Database connection failed",
            "trace": "java.sql.SQLException: Connection refused: connect\n  at java.sql/java.sql.DriverManager.getConnection(DriverManager.java:677)\n  at java.sql/java.sql.DriverManager.getConnection(DriverManager.java:228)\n  at com.example.utils.DatabaseUtil.connect(DatabaseUtil.java:15)"
        }
    ]

    # Tags to be applied to features and scenarios
    TAGS = [
        "@smoke", "@regression", "@critical", "@ui", "@api",
        "@fast", "@slow", "@flaky", "@mobile", "@desktop",
        "@security", "@performance", "@accessibility"
    ]

    def __init__(self, num_features=0, num_scenarios=0, failure_rate=20,
                 project="default", branch="main", commit="latest", flaky_tests=True):
        """
        Initialize the generator with configuration parameters.

        Args:
            num_features: Number of features to generate (0 = random selection)
            num_scenarios: Number of scenarios per feature (0 = random selection)
            failure_rate: Percentage of scenarios that should fail (0-100)
            project: Project name for the test run
            branch: Branch name for the test run
            commit: Commit ID for the test run
            flaky_tests: Whether to include flaky tests that alternate between passing and failing
        """
        self.num_features = num_features
        self.num_scenarios = num_scenarios
        self.failure_rate = failure_rate
        self.project = project
        self.branch = branch
        self.commit = commit
        self.flaky_tests = flaky_tests

        # Seed for flaky test generation - change this between runs to simulate flakiness
        self.flaky_seed = random.randint(1, 1000)

    def _generate_id(self):
        """Generate a random ID for features and scenarios."""
        return ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))

    def _format_duration(self, duration_ms):
        """Format duration in milliseconds to nanoseconds for Cucumber JSON."""
        return duration_ms * 1000000

    def _generate_step_result(self, is_failing=False, step_index=0):
        """Generate a step result with appropriate status and error if failing."""
        duration_ms = random.randint(10, 5000)  # Random duration between 10ms and 5s

        # Make some steps take significantly longer
        if random.random() < 0.1:
            duration_ms *= 5

        result = {
            "status": "passed",
            "duration": self._format_duration(duration_ms)
        }

        # If this is a failing step, add error details
        if is_failing:
            error = random.choice(self.ERROR_PATTERNS)
            # Customize error message with more context
            error_message = error["message"].replace("{locator}", f"//div[@id='step-{step_index}']")
            result.update({
                "status": "failed",
                "error_message": error_message,
                "duration": self._format_duration(duration_ms),
            })

            # Add stack trace for some errors
            if random.random() < 0.8:
                result["stack_trace"] = error["trace"].replace("{locator}", f"//div[@id='step-{step_index}']")

        return result

    def _generate_step(self, step_index, keyword="Given"):
        """Generate a step with keyword and name."""
        keywords = ["Given", "When", "Then", "And"]
        keyword = keywords[min(step_index, len(keywords) - 1)]

        # Different step templates based on index to create realistic step patterns
        templates = [
            "{} the user is on the {} page",
            "{} the user enters valid credentials",
            "{} the user clicks the {} button",
            "{} the system validates the input",
            "{} the user should see a {} message"
        ]

        template = templates[step_index % len(templates)]
        placeholders = ["login", "registration", "checkout", "profile", "success", "error", "submit", "cancel"]
        placeholder = random.choice(placeholders)

        return {
            "keyword": keyword,
            "name": template.format(keyword, placeholder),
            "line": 10 + step_index * 2,
            "match": {
                "location": f"steps.StepDefinitions.step{step_index}()"
            }
        }

    def _is_test_flaky(self, scenario_id):
        """Determine if a test should be marked as flaky and if it's passing in this run."""
        if not self.flaky_tests:
            return False

        # Use a hash of scenario_id and flaky_seed to get consistent behavior for flaky tests
        hash_val = hash(f"{scenario_id}_{self.flaky_seed}")
        return hash_val % 10 == 0  # About 10% of tests are flaky

    def _should_test_fail(self, scenario_id):
        """Determine if a test should fail in this run, accounting for flakiness."""
        # First check if it's a designated flaky test
        if self._is_test_flaky(scenario_id):
            # For flaky tests, alternate pass/fail based on the flaky seed
            flaky_hash = hash(f"{scenario_id}_{self.flaky_seed}")
            return flaky_hash % 2 == 0  # 50% chance of failure for flaky tests

        # Otherwise, use the configured failure rate
        return random.random() * 100 < self.failure_rate

    def _generate_steps(self, scenario_id, num_steps=None):
        """Generate steps for a scenario, including results."""
        if num_steps is None:
            num_steps = random.randint(3, 8)  # Most scenarios have 3-8 steps

        steps = []
        should_fail = self._should_test_fail(scenario_id)

        # If test should fail, decide which step should fail
        failing_step = random.randint(0, num_steps - 1) if should_fail else -1

        for i in range(num_steps):
            step = self._generate_step(i)

            # Add result for the step
            is_failing_step = (i == failing_step)
            step["result"] = self._generate_step_result(is_failing_step, i)

            # If this step fails, skip remaining steps
            steps.append(step)
            if is_failing_step:
                # Add skipped steps
                for j in range(i + 1, num_steps):
                    skipped_step = self._generate_step(j)
                    skipped_step["result"] = {"status": "skipped"}
                    steps.append(skipped_step)
                break

        return steps

    def _generate_scenario(self, scenario_name, tags=None):
        """Generate a single scenario with steps and results."""
        scenario_id = self._generate_id()

        # Create tag list, selecting 0-3 tags
        if tags is None:
            num_tags = random.randint(0, 3)
            tags = random.sample(self.TAGS, num_tags)

        # Add flaky tag for flaky tests
        if self._is_test_flaky(scenario_id):
            tags.append("@flaky")

        scenario = {
            "id": scenario_id,
            "name": scenario_name,
            "line": random.randint(5, 100),
            "description": "",
            "keyword": "Scenario",
            "type": "scenario",
            "tags": [{"name": tag, "line": 1} for tag in tags],
            "steps": self._generate_steps(scenario_id)
        }

        return scenario

    def _generate_feature(self, feature_data):
        """Generate a single feature with scenarios."""
        feature_name = feature_data["name"]

        # Decide how many scenarios to include
        num_scenarios = self.num_scenarios if self.num_scenarios > 0 else min(len(feature_data["scenarios"]),
                                                                              random.randint(1, 5))

        # Select scenarios - either all or a random subset
        if num_scenarios >= len(feature_data["scenarios"]):
            selected_scenarios = feature_data["scenarios"]
        else:
            selected_scenarios = random.sample(feature_data["scenarios"], num_scenarios)

        # Select feature tags (1-2 tags)
        feature_tags = random.sample(self.TAGS, random.randint(1, 2))

        # Generate feature object
        feature = {
            "id": self._generate_id(),
            "name": feature_name,
            "uri": f"features/{feature_name.lower().replace(' ', '_')}.feature",
            "line": 1,
            "keyword": "Feature",
            "description": f"Tests for {feature_name} functionality",
            "tags": [{"name": tag, "line": 1} for tag in feature_tags],
            "elements": []
        }

        # Add scenarios to feature
        for scenario_name in selected_scenarios:
            # Pass some feature tags down to scenarios
            scenario_tags = []
            if random.random() < 0.7:  # 70% chance to inherit tags
                scenario_tags = random.sample(feature_tags,
                                              min(len(feature_tags), random.randint(0, len(feature_tags))))
            scenario = self._generate_scenario(scenario_name, scenario_tags)
            feature["elements"].append(scenario)

        return feature

    def generate(self, timestamp=None):
        """
        Generate a complete Cucumber JSON report.

        Args:
            timestamp: Optional timestamp for the report (default: current time)

        Returns:
            A list of feature objects representing the Cucumber JSON report
        """
        # Select features to include
        if self.num_features <= 0 or self.num_features > len(self.FEATURES):
            selected_features = random.sample(self.FEATURES, random.randint(1, len(self.FEATURES)))
        else:
            selected_features = random.sample(self.FEATURES, self.num_features)

        # Generate each feature
        features = [self._generate_feature(feature) for feature in selected_features]

        return features


if __name__ == "__main__":
    # Example usage
    generator = CucumberReportGenerator(
        num_features=3,
        num_scenarios=4,
        failure_rate=25,
        project="example-project",
        branch="main"
    )

    report = generator.generate()
    print(json.dumps(report, indent=2))
