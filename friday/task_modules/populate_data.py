#!/usr/bin/env python3
"""
Direct Vector DB Test Data Inserter

This script directly inserts test data into the vector database
without relying on complex import paths. It's designed to be run
from the project root directory.
"""

import os
import json
import uuid
import random
import datetime
import asyncio
from typing import List, Dict, Any, Optional

# Import the minimum required components
from qdrant_client import QdrantClient
from qdrant_client.http import models as qdrant_models

# Configuration - Adjust these values to match your setup
QDRANT_URL = "http://localhost:6333"  # Change if your Qdrant is hosted elsewhere
CUCUMBER_COLLECTION = "test_artifacts"  # Collection name for test data
VECTOR_DIMENSION = 1536  # Embedding dimension (adjust if needed)

# Sample data parameters
DAYS_OF_DATA = 30
RUNS_PER_DAY = 3
ENVIRONMENTS = ["dev", "staging", "production", "qa", "integration"]
FEATURES = [
    "User Authentication",
    "Shopping Cart",
    "Product Search",
    "Checkout Process",
    "Account Management",
    "Order History",
    "Payment Processing",
    "Wishlist",
    "Product Recommendations",
    "Product Reviews"
]
TAGS = [
    "@high", "@medium", "@low",
    "@api", "@ui", "@integration",
    "@smoke", "@regression",
    "@sprint-21", "@sprint-22", "@sprint-23",
    "@authentication", "@payment", "@checkout", "@catalog",
    "@cart", "@account", "@search", "@navigation",
    "@jira-123", "@jira-456", "@jira-789"
]
STATUSES = ["PASSED", "FAILED", "SKIPPED"]


async def ensure_collection_exists(client: QdrantClient, collection_name: str, vector_size: int):
    """Ensure the collection exists in Qdrant."""
    try:
        collections = client.get_collections().collections
        collection_names = [collection.name for collection in collections]

        if collection_name not in collection_names:
            print(f"Creating collection {collection_name}...")
            client.create_collection(
                collection_name=collection_name,
                vectors_config=qdrant_models.VectorParams(
                    size=vector_size,
                    distance=qdrant_models.Distance.COSINE
                )
            )
            print(f"Collection {collection_name} created successfully")
        else:
            print(f"Collection {collection_name} already exists")

    except Exception as e:
        print(f"Error ensuring collection exists: {str(e)}")
        raise


def generate_embedding(dimension: int) -> List[float]:
    """Generate a random embedding vector of specified dimension."""
    return [random.uniform(-1, 1) for _ in range(dimension)]


def create_test_case(feature: str, status: str) -> Dict[str, Any]:
    """Create a test case with random data."""
    test_case_id = str(uuid.uuid4())

    # Select random tags
    scenario_tags = random.sample(TAGS, random.randint(2, 5))

    # Create steps
    num_steps = random.randint(3, 8)
    steps = []

    error_message = None
    for i in range(num_steps):
        step_status = status
        step_error = None

        # If the scenario failed, make one of the steps fail
        if status == "FAILED" and i == random.randint(0, num_steps - 1):
            step_status = "FAILED"
            step_error = f"Assertion failed: Expected element to be visible but it was not found. Selector: #product-{random.randint(1000, 9999)}"
            error_message = step_error

        # Steps after a failed step are skipped
        if status == "FAILED" and any(s.get("status") == "FAILED" for s in steps):
            step_status = "SKIPPED"

        step = {
            "id": str(uuid.uuid4()),
            "name": f"Step {i + 1} for {feature}",
            "keyword": random.choice(["Given ", "When ", "Then ", "And "]),
            "status": step_status,
            "duration": random.randint(100, 5000),  # Duration in ms
            "error_message": step_error
        }
        steps.append(step)

    return {
        "id": test_case_id,
        "name": f"Test case for {feature}",
        "feature": feature,
        "description": f"Test case description for {feature}",
        "tags": scenario_tags,
        "status": status,
        "duration": sum(step["duration"] for step in steps),
        "steps": steps,
        "error_message": error_message,
        "type": "test_case"  # Important for filtering
    }


async def populate_vector_db():
    """Populate the vector database with test data."""
    try:
        print(f"Connecting to Qdrant at {QDRANT_URL}...")
        client = QdrantClient(url=QDRANT_URL)

        # Ensure collection exists
        await ensure_collection_exists(client, CUCUMBER_COLLECTION, VECTOR_DIMENSION)

        # Generate data for each day and run
        base_date = datetime.datetime.now() - datetime.timedelta(days=DAYS_OF_DATA)
        total_runs = DAYS_OF_DATA * RUNS_PER_DAY
        report_points = []
        test_case_points = []

        print(f"Generating {total_runs} test runs...")

        for day in range(DAYS_OF_DATA):
            current_date = base_date + datetime.timedelta(days=day)

            for run in range(RUNS_PER_DAY):
                # Create timestamp
                timestamp = current_date + datetime.timedelta(
                    hours=random.randint(8, 17),
                    minutes=random.randint(0, 59)
                )
                report_id = str(uuid.uuid4())

                # Select environment
                environment = random.choice(ENVIRONMENTS)

                # Generate test cases for this run
                test_cases_for_run = []
                total_tests = 0
                passed_tests = 0
                failed_tests = 0
                skipped_tests = 0

                # Create test cases for random features
                selected_features = random.sample(FEATURES, random.randint(3, len(FEATURES)))
                for feature in selected_features:
                    # For each feature, create 1-5 test cases
                    for _ in range(random.randint(1, 5)):
                        # Determine status with weighted probability
                        status_weights = [0.75, 0.15, 0.1]  # 75% pass, 15% fail, 10% skip
                        status = random.choices(STATUSES, weights=status_weights)[0]

                        test_case = create_test_case(feature, status)
                        test_case["report_id"] = report_id  # Link to the report
                        test_case["timestamp"] = timestamp.isoformat()
                        test_case["environment"] = environment

                        # Update counters
                        total_tests += 1
                        if status == "PASSED":
                            passed_tests += 1
                        elif status == "FAILED":
                            failed_tests += 1
                        else:
                            skipped_tests += 1

                        test_cases_for_run.append(test_case)

                        # Create point for vector DB
                        test_case_points.append(
                            qdrant_models.PointStruct(
                                id=test_case["id"],
                                vector=generate_embedding(VECTOR_DIMENSION),
                                payload=test_case
                            )
                        )

                # Create report
                report = {
                    "id": report_id,
                    "name": f"Test Run {timestamp.strftime('%Y-%m-%d %H:%M:%S')}",
                    "timestamp": timestamp.isoformat(),
                    "environment": environment,
                    "tags": random.sample(TAGS, random.randint(2, 5)),
                    "duration": random.randint(30, 600),  # Duration in seconds
                    "type": "report",  # Important for filtering
                    "metadata": {
                        "total_tests": total_tests,
                        "total_passed": passed_tests,
                        "total_failed": failed_tests,
                        "total_skipped": skipped_tests,
                        "pass_rate": (passed_tests / total_tests * 100) if total_tests > 0 else 0
                    }
                }

                # Create point for vector DB
                report_points.append(
                    qdrant_models.PointStruct(
                        id=report["id"],
                        vector=generate_embedding(VECTOR_DIMENSION),
                        payload=report
                    )
                )

                if (day * RUNS_PER_DAY + run + 1) % 10 == 0 or day == DAYS_OF_DATA - 1 and run == RUNS_PER_DAY - 1:
                    print(f"Generated {day * RUNS_PER_DAY + run + 1}/{total_runs} test runs...")

        # Insert data in batches
        batch_size = 100

        print(f"Inserting {len(report_points)} reports into vector DB...")
        for i in range(0, len(report_points), batch_size):
            batch = report_points[i:i + batch_size]
            client.upsert(
                collection_name=CUCUMBER_COLLECTION,
                points=batch
            )
            print(f"Inserted reports batch {i // batch_size + 1}/{(len(report_points) - 1) // batch_size + 1}")

        print(f"Inserting {len(test_case_points)} test cases into vector DB...")
        for i in range(0, len(test_case_points), batch_size):
            batch = test_case_points[i:i + batch_size]
            client.upsert(
                collection_name=CUCUMBER_COLLECTION,
                points=batch
            )
            print(f"Inserted test cases batch {i // batch_size + 1}/{(len(test_case_points) - 1) // batch_size + 1}")

        print(f"\nSuccessfully populated vector DB with:")
        print(f"- {len(report_points)} test reports")
        print(f"- {len(test_case_points)} test cases")
        print("You can now test your API endpoints.")

    except Exception as e:
        print(f"Error populating vector DB: {str(e)}")
        raise


if __name__ == "__main__":
    asyncio.run(populate_vector_db())