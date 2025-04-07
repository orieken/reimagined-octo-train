#!/usr/bin/env python3
"""
Script to check timestamp formats in Qdrant data
"""

from qdrant_client import QdrantClient
from qdrant_client.http import models as qdrant_models
from datetime import datetime, timedelta

# Connect to Qdrant
QDRANT_URL = "http://localhost:6333"
COLLECTION_NAME = "test_artifacts"

client = QdrantClient(url=QDRANT_URL)

try:
    print(f"Connecting to Qdrant at {QDRANT_URL}...")
    print(f"Checking timestamps in collection '{COLLECTION_NAME}'...")

    # Retrieve some test cases
    test_cases, _ = client.scroll(
        collection_name=COLLECTION_NAME,
        scroll_filter=qdrant_models.Filter(
            must=[
                qdrant_models.FieldCondition(
                    key="type",
                    match=qdrant_models.MatchValue(value="test_case")
                )
            ]
        ),
        limit=10,
        with_payload=True,
        with_vectors=False
    )

    if not test_cases:
        print("No test cases found!")
        exit(1)

    print(f"Found {len(test_cases)} test cases for timestamp analysis.")

    # Check timestamp format
    print("\nTimestamp format check:")
    cutoff_date = datetime.now() - timedelta(days=30)
    print(f"Cutoff date (30 days ago): {cutoff_date.isoformat()}")

    for i, tc in enumerate(test_cases):
        timestamp = tc.payload.get("timestamp", "N/A")
        print(f"\nTest case {i + 1}:")
        print(f"  Raw timestamp: {timestamp}")

        try:
            # Try parsing with fromisoformat
            dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            print(f"  Parsed date: {dt}")
            print(f"  Would pass 30-day filter: {dt >= cutoff_date}")

            # Try comparing directly as strings (how some filters might work)
            print(f"  String comparison to cutoff: {timestamp > cutoff_date.isoformat()}")
        except (ValueError, AttributeError) as e:
            print(f"  Error parsing timestamp: {str(e)}")

    # Try direct filtering with Qdrant
    print("\nTesting Qdrant timestamp filtering:")
    cutoff_iso = cutoff_date.isoformat()

    # Try with gt (greater than) filter
    gt_filter = qdrant_models.Filter(
        must=[
            qdrant_models.FieldCondition(
                key="type",
                match=qdrant_models.MatchValue(value="test_case")
            ),
            qdrant_models.FieldCondition(
                key="timestamp",
                range=qdrant_models.Range(gt=cutoff_iso)
            )
        ]
    )

    gt_count = client.count(
        collection_name=COLLECTION_NAME,
        count_filter=gt_filter
    ).count

    print(f"Test cases with timestamp > '{cutoff_iso}': {gt_count}")

    # Try with match filter
    match_filter = qdrant_models.Filter(
        must=[
            qdrant_models.FieldCondition(
                key="type",
                match=qdrant_models.MatchValue(value="test_case")
            )
        ]
    )

    match_count = client.count(
        collection_name=COLLECTION_NAME,
        count_filter=match_filter
    ).count

    print(f"All test cases (without timestamp filter): {match_count}")

except Exception as e:
    print(f"Error: {str(e)}")