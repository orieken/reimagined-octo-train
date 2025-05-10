# int.py
import json

from invoke import task

@task
def test_processor(c):
    """Send a sample Cucumber report to the processor endpoint for testing."""
    print("🚀 Sending test payload to /api/v1/processor/cucumber...")
    payload = {
        "metadata": {
            "project": "demo-project",
            "branch": "main",
            "commit": "abcdef123456",
            "environment": "staging",
            "runner": "ci-runner-01",
            "timestamp": "2024-04-26T23:00:00Z",
            "test_run_id": "test-run-124"
        },
        "features": [
            {
                "name": "Login Feature",
                "description": "Testing login functionality",
                "uri": "features/login.feature",
                "tags": ["smoke"],
                "elements": [
                    {
                        "name": "Successful Login",
                        "description": "User can login with valid credentials",
                        "type": "scenario",
                        "tags": [
                            {"name": "@login","line": 1},
                            {"name": "@smoke", "line": 1},
                            {"name": "@regression", "line": 1}
                        ],
                        "steps": [
                            {
                                "name": "Navigate to login page",
                                "keyword": "Given",
                                "result": {
                                    "status": "passed",
                                    "duration": 1.23
                                }
                            },
                            {
                                "name": "Enter valid credentials",
                                "keyword": "When",
                                "result": {
                                    "status": "passed",
                                    "duration": 0.56
                                }
                            },
                            {
                                "name": "Click login button",
                                "keyword": "And",
                                "result": {
                                    "status": "passed",
                                    "duration": 0.78
                                }
                            }
                        ]
                    }
                ]
            }
        ]
    }

    c.run(
        f"""
        curl -X POST http://localhost:4000/api/v1/processor/cucumber \
        -H "Content-Type: application/json" \
        -d '{json.dumps(payload)}'
        """,
        pty=True
    )


@task
def test_extended(c, num_features=3, scenarios_per_feature=4, failure_rate=0.3, seed=None):
    """
    Send a comprehensive Cucumber report to the processor endpoint with randomized failures.

    Args:
        num_features: Number of e-commerce features to generate (default: 3)
        scenarios_per_feature: Number of scenarios per feature (default: 4)
        failure_rate: Probability of a scenario failing (0.0-1.0) (default: 0.3)
        seed: Random seed for reproducible results (default: None)
    """
    import random
    import uuid
    from datetime import datetime, timedelta

    # Set random seed if provided
    if seed is not None:
        random.seed(seed)

    # Current timestamp
    now = datetime.utcnow()
    timestamp = now.strftime("%Y-%m-%dT%H:%M:%SZ")

    print(
        f"🚀 Generating test payload with {num_features} features, {scenarios_per_feature} scenarios per feature, {failure_rate * 100}% failure rate...")

    # E-commerce feature templates
    ecommerce_features = [
        {
            "name": "Product Search",
            "description": "Testing product search functionality",
            "uri": "features/product_search.feature",
            "tags": ["search", "product", "ecommerce"],
            "scenarios": [
                "Search for products by keyword",
                "Filter search results by category",
                "Sort search results by price",
                "Search with invalid keywords",
                "Search with special characters",
                "Navigate through search result pages"
            ]
        },
        {
            "name": "Shopping Cart",
            "description": "Testing shopping cart functionality",
            "uri": "features/shopping_cart.feature",
            "tags": ["cart", "checkout", "ecommerce"],
            "scenarios": [
                "Add item to cart",
                "Remove item from cart",
                "Update item quantity in cart",
                "Apply discount code to cart",
                "Cart persists after logout and login",
                "Cart shows correct total price"
            ]
        },
        {
            "name": "User Account",
            "description": "Testing user account management",
            "uri": "features/user_account.feature",
            "tags": ["account", "user", "profile"],
            "scenarios": [
                "Register new user account",
                "Update account information",
                "Change account password",
                "View order history",
                "Add multiple shipping addresses",
                "Delete account"
            ]
        },
        {
            "name": "Checkout Process",
            "description": "Testing checkout and payment functionality",
            "uri": "features/checkout.feature",
            "tags": ["checkout", "payment", "ecommerce"],
            "scenarios": [
                "Complete checkout with credit card",
                "Checkout with saved payment method",
                "Shipping address validation",
                "Apply coupon at checkout",
                "Order confirmation email",
                "Cancel order after checkout"
            ]
        },
        {
            "name": "Product Reviews",
            "description": "Testing product review functionality",
            "uri": "features/product_reviews.feature",
            "tags": ["reviews", "product", "rating"],
            "scenarios": [
                "Submit product review with rating",
                "Edit existing product review",
                "Filter reviews by star rating",
                "Sort reviews by date",
                "Report inappropriate review",
                "Review requires purchase verification"
            ]
        },
        {
            "name": "Wishlist",
            "description": "Testing wishlist functionality",
            "uri": "features/wishlist.feature",
            "tags": ["wishlist", "product", "ecommerce"],
            "scenarios": [
                "Add product to wishlist",
                "Remove product from wishlist",
                "Move product from wishlist to cart",
                "Share wishlist with friends",
                "Create multiple wishlists",
                "Wishlist persists across sessions"
            ]
        }
    ]

    # Step templates for different outcomes
    step_templates = {
        "passed": [
            {"name": "User navigates to {page} page", "keyword": "Given", "duration": lambda: random.uniform(0.1, 1.5)},
            {"name": "User {action} the {item}", "keyword": "When", "duration": lambda: random.uniform(0.2, 0.8)},
            {"name": "User verifies {result}", "keyword": "Then", "duration": lambda: random.uniform(0.1, 0.5)}
        ],
        "failed": [
            {"name": "User navigates to {page} page", "keyword": "Given", "duration": lambda: random.uniform(0.1, 1.5)},
            {"name": "User {action} the {item}", "keyword": "When", "duration": lambda: random.uniform(0.2, 0.8)},
            {"name": "User should see {result}", "keyword": "Then", "duration": lambda: random.uniform(0.1, 0.5),
             "error_message": "Expected {result} to be visible but element not found",
             "stack_trace": "Error: TimeoutError: Element not found\n    at Object.waitForElement (/src/test/helpers.js:24:11)\n    at World.<anonymous> (/src/test/steps/common_steps.js:15:20)"}
        ]
    }

    # Error types for failed scenarios
    error_types = [
        {"message": "Element not found: {selector}",
         "trace": "TimeoutError: Element not found\n    at waitForElement (helpers.js:25:13)"},
        {"message": "Expected {actual} to equal {expected}",
         "trace": "AssertionError: Expected values to match\n    at verifyContent (assertions.js:42:9)"},
        {"message": "API response error: {status_code}",
         "trace": "Error: Request failed with status code {status_code}\n    at handleResponse (api.js:67:11)"},
        {"message": "Unexpected alert present",
         "trace": "UnexpectedAlertError: Modal dialog present\n    at dismissAlert (dialogs.js:18:5)"},
        {"message": "Database connection failed",
         "trace": "ConnectionError: Could not connect to database\n    at establishConnection (db.js:14:8)"}
    ]

    # Select features randomly from the template list
    selected_features = random.sample(ecommerce_features, min(num_features + 1, len(ecommerce_features)))

    # Add the original login feature to ensure we have that one
    login_feature = {
        "name": "Login Feature",
        "description": "Testing login functionality",
        "uri": "features/login.feature",
        "tags": ["smoke"],
        "elements": [
            {
                "name": "Successful Login",
                "description": "User can login with valid credentials",
                "type": "scenario",
                "tags": [
                    {"name": "@login", "line": 1},
                    {"name": "@smoke", "line": 1},
                    {"name": "@regression", "line": 1}
                ],
                "steps": [
                    {
                        "name": "Navigate to login page",
                        "keyword": "Given",
                        "result": {
                            "status": "passed",
                            "duration": 1.23
                        }
                    },
                    {
                        "name": "Enter valid credentials",
                        "keyword": "When",
                        "result": {
                            "status": "passed",
                            "duration": 0.56
                        }
                    },
                    {
                        "name": "Click login button",
                        "keyword": "And",
                        "result": {
                            "status": "passed",
                            "duration": 0.78
                        }
                    }
                ]
            }
        ]
    }

    # Generate the features with randomized scenarios
    features = [login_feature]

    for feature_template in selected_features:
        # Create a feature
        feature = {
            "name": feature_template["name"],
            "description": feature_template["description"],
            "uri": feature_template["uri"],
            "tags": feature_template["tags"],
            "elements": []
        }

        # Sample scenarios from the template
        scenario_names = random.sample(feature_template["scenarios"],
                                       min(scenarios_per_feature, len(feature_template["scenarios"])))

        # Generate each scenario
        for scenario_name in scenario_names:
            # Decide if this scenario will fail
            will_fail = random.random() < failure_rate
            status = "failed" if will_fail else "passed"

            # Generate tags
            tags = []
            for tag in feature_template["tags"]:
                if random.random() < 0.7:  # 70% chance to include each tag
                    tags.append({"name": f"@{tag}", "line": random.randint(1, 10)})

            # Sometimes add common tags
            if random.random() < 0.3:
                tags.append({"name": "@smoke", "line": 1})
            if random.random() < 0.2:
                tags.append({"name": "@regression", "line": 2})

            # Generate steps
            steps = []
            step_count = random.randint(2, 5)  # Random number of steps

            # If scenario fails, one of the steps must fail
            fail_step = random.randint(0, step_count - 1) if will_fail else -1

            for i in range(step_count):
                will_step_fail = (i == fail_step)
                step_status = "failed" if will_step_fail else "passed"

                # Choose template based on step status
                templates = step_templates["failed" if will_step_fail else "passed"]
                template = random.choice(templates)

                # Fill in placeholders
                name = template["name"]
                name = name.replace("{page}",
                                    random.choice(["product", "category", "cart", "checkout", "account", "search"]))
                name = name.replace("{action}",
                                    random.choice(["clicks on", "selects", "enters", "submits", "verifies", "checks"]))
                name = name.replace("{item}",
                                    random.choice(["button", "link", "input field", "dropdown", "checkbox", "product"]))
                name = name.replace("{result}", random.choice(
                    ["confirmation message", "success notification", "product details", "updated information"]))

                # Create step
                step = {
                    "name": name,
                    "keyword": template["keyword"],
                    "result": {
                        "status": step_status,
                        "duration": template["duration"]()
                    }
                }

                # Add error details if step failed
                if will_step_fail:
                    error = random.choice(error_types)
                    error_message = error["message"]
                    error_message = error_message.replace("{selector}", "#" + random.choice(
                        ["product", "cart", "checkout", "submit", "login"]) + "-" + str(random.randint(1, 999)))
                    error_message = error_message.replace("{actual}", random.choice(
                        ["404", "Product not found", "null", "undefined", "Error"]))
                    error_message = error_message.replace("{expected}",
                                                          random.choice(["200", "Product name", "Success", "Welcome"]))
                    error_message = error_message.replace("{status_code}", str(random.choice([400, 403, 404, 500])))

                    error_trace = error["trace"]
                    error_trace = error_trace.replace("{status_code}", str(random.choice([400, 403, 404, 500])))

                    step["result"]["error_message"] = error_message
                    step["result"]["error_stacktrace"] = error_trace

                steps.append(step)

            # Create the scenario
            scenario = {
                "name": scenario_name,
                "description": f"Testing {scenario_name.lower()} functionality",
                "type": "scenario",
                "tags": tags,
                "steps": steps
            }

            feature["elements"].append(scenario)

        features.append(feature)

    # Create the payload
    payload = {
        "metadata": {
            "project": "demo-project",
            "branch": "main",
            "commit": str(uuid.uuid4())[:8],
            "environment": random.choice(["staging", "dev", "test", "integration"]),
            "runner": f"ci-runner-{random.randint(1, 10):02d}",
            "timestamp": timestamp,
            "test_run_id": f"test-run-{random.randint(100, 999)}"
        },
        "features": features
    }

    print(
        f"💡 Generated test payload with {len(features)} features and approximately {sum(len(f.get('elements', [])) for f in features)} scenarios")
    print(f"🔍 Expected failure rate: {failure_rate * 100:.1f}%")

    # Send to API
    c.run(
        f"""
        curl -X POST http://localhost:4000/api/v1/processor/cucumber \
        -H "Content-Type: application/json" \
        -d '{json.dumps(payload)}'
        """,
        pty=True
    )

    # Print helpful next steps
    print("\n✅ Test data sent successfully!")
    print("\nSuggested next steps:")
    print("  1. Check failures summary: curl http://localhost:4000/api/v1/failures/summary")
    print("  2. View all failures: curl http://localhost:4000/api/v1/failures")
    print("  3. Check failure trends: curl http://localhost:4000/api/v1/failures/trends")
    print(
        "  4. Try semantic search: curl \"http://localhost:4000/api/v1/failures/rag?query=product%20search%20issues\"")

@task
def healthcheck(c):
    """Ping the /processor/health endpoint."""
    print("🩺 Checking service health at /api/v1/processor/health...")
    c.run(
        """
        curl -X GET http://localhost:4000/api/v1/processor/health
        """,
        pty=True
    )
