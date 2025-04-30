#!/usr/bin/env python3
"""
Scenario Tags Sync Script

This script syncs tags between your Qdrant vector database and your PostgreSQL database.
It populates the scenario_tags table based on tag data from your test_artifacts collection.
"""

import sys
import os
import json
import logging
from typing import List, Dict, Any
import argparse
from datetime import datetime
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import SQLAlchemyError
from qdrant_client import QdrantClient
from qdrant_client.http import models as qdrant_models

from app.config import settings

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("scenario_tags_sync")

# Configuration
QDRANT_URL = os.environ.get("QDRANT_URL", "http://localhost:6333")
POSTGRESQL_URL = settings.DATABASE_URL
COLLECTION_NAME = os.environ.get("QDRANT_COLLECTION", "test_artifacts")


def get_db_session():
    """Create and return a database session."""
    engine = create_engine(POSTGRESQL_URL)
    Session = sessionmaker(bind=engine)
    return Session()


def get_qdrant_client():
    """Create and return a Qdrant client."""
    return QdrantClient(url=QDRANT_URL)


def get_test_case_tags_from_qdrant(client: QdrantClient, collection: str) -> Dict[str, List[str]]:
    """
    Retrieve all test cases with their tags from Qdrant.
    Returns a dictionary mapping test case IDs to lists of tags.
    """
    logger.info("Retrieving test cases with tags from Qdrant...")

    test_case_tags = {}
    limit = 100
    offset = 0
    total_processed = 0

    while True:
        # Get batch of test cases with tags
        test_cases = client.scroll(
            collection_name=collection,
            scroll_filter=qdrant_models.Filter(
                must=[
                    qdrant_models.FieldCondition(
                        key="type",
                        match=qdrant_models.MatchValue(value="test_case")
                    )
                ]
            ),
            limit=limit,
            offset=offset
        )[0]

        if not test_cases:
            break

        # Process this batch
        for test_case in test_cases:
            case_id = test_case.id
            tags = test_case.payload.get("tags", [])

            if tags and isinstance(tags, list):
                # Strip the '@' prefix if present and store in our map
                cleaned_tags = [tag.lstrip('@') for tag in tags]
                test_case_tags[case_id] = cleaned_tags

        # Update counters for next batch
        total_processed += len(test_cases)
        offset += limit
        logger.info(f"Processed {total_processed} test cases so far")

    logger.info(f"Retrieved tags for {len(test_case_tags)} test cases")
    return test_case_tags


def map_qdrant_ids_to_postgres_ids(db: Session) -> Dict[str, int]:
    """
    Create a mapping from Qdrant test case IDs to PostgreSQL scenario IDs.
    Assumes test cases and scenarios have a common identifier in their metadata.
    """
    logger.info("Creating mapping between Qdrant and PostgreSQL IDs...")

    # This query assumes there's some common ID field in the metadata
    # Adjust this based on your actual data structure
    query = text("""
        SELECT 
            id,
            meta_data->>'qdrant_id' as qdrant_id 
        FROM 
            scenarios 
        WHERE 
            meta_data->>'qdrant_id' IS NOT NULL
    """)

    id_mapping = {}

    try:
        result = db.execute(query)
        for row in result:
            pg_id = row[0]
            qdrant_id = row[1]
            id_mapping[qdrant_id] = pg_id

        logger.info(f"Created mapping for {len(id_mapping)} IDs")
    except SQLAlchemyError as e:
        logger.error(f"Error querying database: {str(e)}")

    return id_mapping


def get_existing_scenario_tags(db: Session) -> Dict[int, List[str]]:
    """
    Get existing scenario tags from the database.
    Returns a dictionary mapping scenario IDs to lists of tags.
    """
    logger.info("Retrieving existing scenario tags from database...")

    query = text("""
        SELECT 
            scenario_id, 
            tag 
        FROM 
            scenario_tags
    """)

    existing_tags = {}

    try:
        result = db.execute(query)
        for row in result:
            scenario_id = row[0]
            tag = row[1]

            if scenario_id not in existing_tags:
                existing_tags[scenario_id] = []

            existing_tags[scenario_id].append(tag)

        logger.info(f"Found {len(existing_tags)} scenarios with existing tags")
    except SQLAlchemyError as e:
        logger.error(f"Error querying existing tags: {str(e)}")

    return existing_tags


def sync_tags(
        db: Session,
        qdrant_tags: Dict[str, List[str]],
        id_mapping: Dict[str, int],
        existing_tags: Dict[int, List[str]]
):
    """
    Sync tags from Qdrant to PostgreSQL.
    Only adds tags that don't already exist in the database.
    """
    logger.info("Syncing tags from Qdrant to PostgreSQL...")

    # Keep track of stats
    total_new_tags = 0
    total_scenarios_updated = 0

    # Prepare data for bulk insert
    new_tag_rows = []

    # Process each test case from Qdrant
    for qdrant_id, tags in qdrant_tags.items():
        # Skip if we can't map this ID to a PostgreSQL ID
        if qdrant_id not in id_mapping:
            continue

        pg_scenario_id = id_mapping[qdrant_id]
        existing_scenario_tags = existing_tags.get(pg_scenario_id, [])

        # Find tags that don't exist in the database yet
        new_tags = [tag for tag in tags if tag not in existing_scenario_tags]

        if new_tags:
            # Add new tag relationships to our bulk insert list
            for tag in new_tags:
                new_tag_rows.append({"scenario_id": pg_scenario_id, "tag": tag})

            total_new_tags += len(new_tags)
            total_scenarios_updated += 1

    # Perform bulk insert if we have new tags
    if new_tag_rows:
        try:
            # Convert list of dicts to a values string for bulk insert
            values_parts = []
            for row in new_tag_rows:
                values_parts.append(f"({row['scenario_id']}, '{row['tag']}')")

            values_str = ", ".join(values_parts)

            insert_query = text(f"""
                INSERT INTO scenario_tags (scenario_id, tag)
                VALUES {values_str}
                ON CONFLICT (scenario_id, tag) DO NOTHING
            """)

            db.execute(insert_query)
            db.commit()

            logger.info(f"Successfully added {total_new_tags} new tags to {total_scenarios_updated} scenarios")
        except SQLAlchemyError as e:
            db.rollback()
            logger.error(f"Error inserting tags: {str(e)}")
    else:
        logger.info("No new tags to add")


def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(description="Sync scenario tags between Qdrant and PostgreSQL")
    parser.add_argument("--dry-run", action="store_true", help="Perform a dry run without modifying the database")
    args = parser.parse_args()

    logger.info("Starting scenario tags sync process")

    # Get connections
    qdrant_client = get_qdrant_client()
    db_session = get_db_session()

    try:
        # Get test case tags from Qdrant
        test_case_tags = get_test_case_tags_from_qdrant(qdrant_client, COLLECTION_NAME)

        # Create ID mapping
        id_mapping = map_qdrant_ids_to_postgres_ids(db_session)

        # Get existing tags
        existing_tags = get_existing_scenario_tags(db_session)

        if args.dry_run:
            logger.info(f"DRY RUN: Would sync tags for up to {len(test_case_tags)} test cases")
            logger.info(f"Found {len(id_mapping)} mappable IDs between Qdrant and PostgreSQL")

            # Calculate how many new tags would be added in a real run
            mapped_cases = 0
            total_new_tags = 0

            for qdrant_id, tags in test_case_tags.items():
                if qdrant_id in id_mapping:
                    mapped_cases += 1
                    pg_scenario_id = id_mapping[qdrant_id]
                    existing_scenario_tags = existing_tags.get(pg_scenario_id, [])
                    new_tags = [tag for tag in tags if tag not in existing_scenario_tags]
                    total_new_tags += len(new_tags)

            logger.info(f"DRY RUN: Would add {total_new_tags} new tags to {mapped_cases} scenarios")
        else:
            # Perform the actual sync
            sync_tags(db_session, test_case_tags, id_mapping, existing_tags)

        logger.info("Tag sync process completed successfully")

    except Exception as e:
        logger.error(f"Error during tag sync process: {str(e)}", exc_info=True)
    finally:
        db_session.close()


def sync_with_direct_query(db: Session):
    """
    Alternative sync method that extracts tags directly from scenario metadata.
    Useful when Qdrant IDs don't map cleanly to PostgreSQL IDs.
    """
    logger.info("Performing direct metadata-based tag sync...")

    # This query extracts tags from the meta_data JSON field in the scenarios table
    # Assumes tags are stored as a JSON array in meta_data->tags
    extract_query = text("""
        WITH extracted_tags AS (
            SELECT 
                id as scenario_id,
                jsonb_array_elements_text(meta_data->'tags') as tag
            FROM 
                scenarios
            WHERE 
                meta_data ? 'tags' AND 
                jsonb_typeof(meta_data->'tags') = 'array'
        )
        SELECT scenario_id, tag FROM extracted_tags
        WHERE NOT EXISTS (
            SELECT 1 FROM scenario_tags
            WHERE scenario_tags.scenario_id = extracted_tags.scenario_id
            AND scenario_tags.tag = extracted_tags.tag
        )
    """)

    insert_query = text("""
        INSERT INTO scenario_tags (scenario_id, tag)
        WITH extracted_tags AS (
            SELECT 
                id as scenario_id,
                jsonb_array_elements_text(meta_data->'tags') as tag
            FROM 
                scenarios
            WHERE 
                meta_data ? 'tags' AND 
                jsonb_typeof(meta_data->'tags') = 'array'
        )
        SELECT scenario_id, tag FROM extracted_tags
        WHERE NOT EXISTS (
            SELECT 1 FROM scenario_tags
            WHERE scenario_tags.scenario_id = extracted_tags.scenario_id
            AND scenario_tags.tag = extracted_tags.tag
        )
        ON CONFLICT (scenario_id, tag) DO NOTHING
    """)

    try:
        # First check how many tags would be inserted
        result = db.execute(extract_query)
        rows = result.fetchall()
        tag_count = len(rows)

        if tag_count > 0:
            logger.info(f"Found {tag_count} new tags to insert from metadata")

            # Perform the insert
            result = db.execute(insert_query)
            db.commit()

            logger.info(f"Successfully inserted {result.rowcount} tags from metadata")
        else:
            logger.info("No new tags found in metadata")

        return tag_count
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Error during direct metadata sync: {str(e)}")
        return 0


if __name__ == "__main__":
    main()