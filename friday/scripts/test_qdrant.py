#!/usr/bin/env python3
"""
Simple script to check if data exists in Qdrant
"""

from qdrant_client import QdrantClient
from qdrant_client.http import models as qdrant_models

# Connect to Qdrant
QDRANT_URL = "http://localhost:6333"
COLLECTION_NAME = "test_artifacts"  # Change this if your collection has a different name

client = QdrantClient(url=QDRANT_URL)

# Check if collection exists
try:
    collections = client.get_collections().collections
    collection_names = [collection.name for collection in collections]

    if COLLECTION_NAME not in collection_names:
        print(f"Collection '{COLLECTION_NAME}' does not exist!")
        print(f"Available collections: {collection_names}")
        exit(1)

    print(f"Collection '{COLLECTION_NAME}' exists.")

    # Count total points
    total_count = client.count(collection_name=COLLECTION_NAME).count
    print(f"Total points in collection: {total_count}")

    # Count by type
    type_values = ["test_case", "report", "testcase", "TestCase"]
    for type_value in type_values:
        count = client.count(
            collection_name=COLLECTION_NAME,
            count_filter=qdrant_models.Filter(
                must=[
                    qdrant_models.FieldCondition(
                        key="type",
                        match=qdrant_models.MatchValue(value=type_value)
                    )
                ]
            )
        ).count
        print(f"Points with type='{type_value}': {count}")

    # Retrieve a sample point
    if total_count > 0:
        print("\nRetrieving a sample point...")
        points = client.scroll(
            collection_name=COLLECTION_NAME,
            limit=1,
            with_payload=True,
            with_vectors=False
        )[0]

        if points:
            point = points[0]
            print(f"Sample point ID: {point.id}")
            print("Payload keys:", list(point.payload.keys()))

            # If it's a test case, show key fields
            if point.payload.get("type") == "test_case":
                print("\nTest case details:")
                print(f"  Status: {point.payload.get('status')}")
                print(f"  Feature: {point.payload.get('feature')}")
                print(f"  Report ID: {point.payload.get('report_id')}")
                print(f"  Environment: {point.payload.get('environment')}")
                print(f"  Tags: {point.payload.get('tags')}")
        else:
            print("No points found in collection!")

except Exception as e:
    print(f"Error connecting to Qdrant: {str(e)}")