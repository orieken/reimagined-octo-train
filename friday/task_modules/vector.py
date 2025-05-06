# tasks.py
from invoke import task
import logging
from qdrant_client import QdrantClient
from qdrant_client.http import models as qdrant_models
from app.config import settings

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("qdrant_setup")


@task
def setup_collections(c):
    """Set up Qdrant collections for the Friday Test Analysis service"""
    logger.info(f"Connecting to Qdrant at {settings.QDRANT_URL}")

    # Connect to Qdrant running in Docker
    client = QdrantClient(
        url=settings.QDRANT_URL,
        timeout=10,
    )

    # Collection name from configuration
    collection_name = settings.CUCUMBER_COLLECTION or "test_artifacts"

    # Check if collection exists
    collections = client.get_collections().collections
    collection_names = [coll.name for coll in collections]

    # Create collection if it doesn't exist
    if collection_name in collection_names:
        logger.info(f"Collection '{collection_name}' already exists")
    else:
        logger.info(f"Creating collection '{collection_name}'")
        client.create_collection(
            collection_name=collection_name,
            vectors_config=qdrant_models.VectorParams(
                size=settings.VECTOR_DIMENSION,
                distance=qdrant_models.Distance.COSINE
            )
        )
        logger.info(f"Collection '{collection_name}' created successfully")

    logger.info(f"Collection '{collection_name}' is ready for use with vector_db.py")
    return True


@task
def clear_collections(c, confirm=False):
    """Clear all points from the Qdrant collections but keep the collection structure"""
    if not confirm:
        logger.warning("This will delete all data in the collections!")
        logger.warning("Run with --confirm flag to proceed")
        return False

    logger.info(f"Connecting to Qdrant at {settings.QDRANT_URL}")
    client = QdrantClient(
        url=settings.QDRANT_URL,
        timeout=10,
    )

    # Collection name from configuration
    collection_name = settings.CUCUMBER_COLLECTION or "test_artifacts"

    # Check if collection exists
    collections = client.get_collections().collections
    collection_names = [coll.name for coll in collections]

    if collection_name in collection_names:
        logger.info(f"Clearing all points from collection '{collection_name}'")
        # Delete all points but keep the collection structure
        client.delete(
            collection_name=collection_name,
            points_selector=qdrant_models.FilterSelector(
                filter=qdrant_models.Filter()  # Empty filter selects all points
            )
        )
        logger.info(f"All points deleted from collection '{collection_name}'")
    else:
        logger.warning(f"Collection '{collection_name}' does not exist")

    return True


@task
def delete_collections(c, confirm=False):
    """Delete the Qdrant collections completely"""
    if not confirm:
        logger.warning("This will completely delete the collections!")
        logger.warning("Run with --confirm flag to proceed")
        return False

    logger.info(f"Connecting to Qdrant at {settings.QDRANT_URL}")
    client = QdrantClient(
        url=settings.QDRANT_URL,
        timeout=10,
    )

    # Collection name from configuration
    collection_name = settings.CUCUMBER_COLLECTION or "test_artifacts"

    # Check if collection exists
    collections = client.get_collections().collections
    collection_names = [coll.name for coll in collections]

    if collection_name in collection_names:
        logger.info(f"Deleting collection '{collection_name}'")
        client.delete_collection(collection_name=collection_name)
        logger.info(f"Collection '{collection_name}' deleted")
    else:
        logger.warning(f"Collection '{collection_name}' does not exist")

    return True


import json
import requests
from pprint import pprint


@task
def check_qdrant(c, collection="test_artifacts", limit=10):
    """
    Query the Qdrant vector database directly to see what data is stored.

    Args:
        collection: The name of the collection to check (default: test_artifacts)
        limit: Maximum number of records to retrieve (default: 10)
    """
    print(f"📊 Checking Qdrant database collection: {collection}")

    # First, check if the collection exists
    response = requests.get("http://localhost:6333/collections")
    collections = response.json()

    print(f"Available collections: {', '.join([c['name'] for c in collections['result']['collections']])}")

    # Check if our collection exists
    if not any(c['name'] == collection for c in collections['result']['collections']):
        print(f"❌ Collection '{collection}' does not exist!")
        return

    # Get collection info
    response = requests.get(f"http://localhost:6333/collections/{collection}")
    collection_info = response.json()
    print(f"\nCollection info:")

    # Extract vector count - the structure might vary based on Qdrant version
    if 'vectors_count' in collection_info['result']:
        print(f"  - Vectors: {collection_info['result']['vectors_count']}")
    elif 'points_count' in collection_info['result']:
        print(f"  - Points: {collection_info['result']['points_count']}")
    else:
        # Just print the structure for debugging
        print(f"  - Structure: {json.dumps(collection_info['result'], indent=2)}")

    # Try to extract vector size safely
    try:
        if 'vector_size' in collection_info['result']:
            print(f"  - Vector size: {collection_info['result']['vector_size']}")
        elif 'config' in collection_info['result'] and 'params' in collection_info['result']['config']:
            vector_params = collection_info['result']['config']['params']
            if 'vectors' in vector_params and isinstance(vector_params['vectors'], dict):
                for vector_name, vector_config in vector_params['vectors'].items():
                    if isinstance(vector_config, dict):
                        print(f"  - Vector '{vector_name}' size: {vector_config.get('size', 'unknown')}")
                    else:
                        print(f"  - Vector '{vector_name}' config: {vector_config}")
            elif 'size' in vector_params:
                print(f"  - Vector size: {vector_params['size']}")
    except Exception as e:
        print(f"  - Could not determine vector size: {str(e)}")

    # Scroll through records
    scroll_url = f"http://localhost:6333/collections/{collection}/points/scroll"
    payload = {
        "limit": limit,
        "with_payload": True,
        "with_vector": False
    }

    try:
        response = requests.post(scroll_url, json=payload)
        response.raise_for_status()
        scroll_data = response.json()

        # Check if points exist in the response
        if 'result' not in scroll_data or 'points' not in scroll_data['result']:
            print("\n❌ No points data found in response!")
            print(f"Response: {json.dumps(scroll_data, indent=2)}")
            return

        points = scroll_data['result']['points']

        if not points:
            print("\n❌ No data found in collection!")
            return

        print(f"\n✅ Found {len(points)} records in collection:")

        for i, point in enumerate(points):
            print(f"\n--- Record {i + 1} ---")
            print(f"ID: {point['id']}")

            # Check if payload exists
            if 'payload' not in point or not point['payload']:
                print("❌ No payload found for this point!")
                continue

            # Clean up payload for better display
            payload = point['payload']

            # Get the type of record
            record_type = payload.get('type', 'unknown')
            print(f"Type: {record_type}")

            # Show key information based on record type
            if record_type == 'test_case':
                print(f"Name: {payload.get('name', 'N/A')}")
                print(f"Status: {payload.get('status', 'N/A')}")
                if 'tags' in payload and isinstance(payload['tags'], list):
                    print(f"Tags: {', '.join(payload.get('tags', []))}")
                else:
                    print(f"Tags: N/A")
            elif record_type == 'report':
                print(f"Project: {payload.get('project', 'N/A')}")
                print(f"Timestamp: {payload.get('timestamp', 'N/A')}")
                print(f"Environment: {payload.get('environment', 'N/A')}")

            # Print shortened payload for overview
            try:
                payload_str = json.dumps(payload, indent=2)
                if len(payload_str) > 500:
                    payload_str = payload_str[:500] + "..."
                print(f"Payload: {payload_str}")
            except Exception as e:
                print(f"Could not serialize payload: {str(e)}")

    except Exception as e:
        print(f"❌ Error querying records: {str(e)}")


@task
def check_collections(c):
    """List all collections in the Qdrant database."""
    print("📋 Listing all Qdrant collections")

    try:
        response = requests.get("http://localhost:6333/collections")
        collections = response.json()

        if collections['result']['collections']:
            print("\nAvailable collections:")
            for coll in collections['result']['collections']:
                print(f"  - {coll['name']}")

                # Get more details about this collection
                try:
                    detail_response = requests.get(f"http://localhost:6333/collections/{coll['name']}")
                    detail = detail_response.json()

                    if 'result' in detail and 'points_count' in detail['result']:
                        print(f"    • Points count: {detail['result']['points_count']}")

                    if 'result' in detail and 'config' in detail['result']:
                        print(f"    • Configuration available")
                except Exception as e:
                    print(f"    • Error getting details: {str(e)}")
        else:
            print("No collections found in the database.")
    except Exception as e:
        print(f"❌ Error listing collections: {str(e)}")


@task
def direct_query(c, collection="test_artifacts", query_type="all", limit=10):
    """
    Direct query to the Qdrant database with different options.

    Args:
        collection: The collection to query
        query_type: Type of query (all, report, test_case, feature, step)
        limit: Maximum number of results
    """
    print(f"🔍 Directly querying {collection} for {query_type} records...")

    # Build filter based on query type
    filter_obj = {}
    if query_type != "all":
        filter_obj = {
            "must": [
                {
                    "key": "type",
                    "match": {
                        "value": query_type
                    }
                }
            ]
        }

    # Search endpoint allows filtering
    search_url = f"http://localhost:6333/collections/{collection}/points/scroll"
    payload = {
        "filter": filter_obj if query_type != "all" else None,
        "limit": limit,
        "with_payload": True,
        "with_vectors": False
    }

    try:
        response = requests.post(search_url, json=payload)
        response.raise_for_status()
        data = response.json()

        if 'result' not in data or 'points' not in data['result']:
            print(f"❌ Unexpected response format: {json.dumps(data, indent=2)}")
            return

        points = data['result']['points']

        if not points:
            print(f"No {query_type} records found.")
            return

        print(f"Found {len(points)} {query_type} records:")

        for i, point in enumerate(points):
            print(f"\n--- Record {i + 1} ---")
            print(f"ID: {point['id']}")

            if 'payload' in point:
                # Just show the first part of the payload
                try:
                    payload_str = json.dumps(point['payload'], indent=2)
                    if len(payload_str) > 300:
                        payload_str = payload_str[:300] + "..."
                    print(f"Payload (truncated): {payload_str}")
                except Exception as e:
                    print(f"Could not serialize payload: {str(e)}")
            else:
                print("No payload found.")

    except Exception as e:
        print(f"❌ Error querying Qdrant: {str(e)}")


@task
def check_cucumber_data(c, limit=10):
    """
    Check data specifically in the cucumber collection.
    This might be different from test_artifacts based on configuration.
    """
    # Read settings from config file if possible to get the actual collection name
    try:
        from app.config import settings
        collection_name = settings.CUCUMBER_COLLECTION
        print(f"Using collection name from settings: {collection_name}")
    except ImportError:
        collection_name = "test_artifacts"
        print(f"Could not import settings, using default collection name: {collection_name}")

    return check_qdrant(c, collection=collection_name, limit=limit)


from invoke import task
import json
import requests
import logging
from typing import Optional
from datetime import datetime, timedelta

# Set up basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@task
def debug_stats_query(c, type_value="scenario", status=None, environment=None, collection="test_artifacts"):
    """
    Debug stats query by directly using the same filter conditions as the stats endpoints.

    Args:
        type_value: The type value to filter by (default: scenario)
        status: Optional status filter (PASSED, FAILED, SKIPPED)
        environment: Optional environment filter
        collection: Collection name to query
    """
    print(f"🔍 Debugging stats query in {collection} with type={type_value}, status={status}, environment={environment}")

    # Build filter conditions exactly like the stats endpoints do
    conditions = [
        {
            "key": "type",
            "match": {
                "value": type_value
            }
        }
    ]

    if status:
        conditions.append(
            {
                "key": "status",
                "match": {
                    "value": status
                }
            }
        )

    if environment:
        conditions.append(
            {
                "key": "environment",
                "match": {
                    "value": environment
                }
            }
        )

    filter_obj = {
        "must": conditions
    }

    # First, count how many points match this filter
    count_url = f"http://localhost:6333/collections/{collection}/points/count"
    payload = {
        "filter": filter_obj
    }

    try:
        print(f"Using filter: {json.dumps(filter_obj, indent=2)}")

        response = requests.post(count_url, json=payload)
        response.raise_for_status()
        count_data = response.json()

        count = count_data.get('result', {}).get('count', 0)
        print(f"✅ Found {count} matching records")

        if count == 0:
            # If count is 0, try to identify why by showing all possible types
            print("\nInvestigating available data...")

            # Check what types exist in the collection
            scroll_url = f"http://localhost:6333/collections/{collection}/points/scroll"
            scroll_payload = {
                "limit": 100,
                "with_payload": True,
                "with_vector": False
            }

            response = requests.post(scroll_url, json=scroll_payload)
            response.raise_for_status()
            scroll_data = response.json()

            points = scroll_data.get('result', {}).get('points', [])

            if not points:
                print("❌ No records found in the collection at all!")
                return

            # Analyze available types
            types = {}
            statuses = {}
            environments = {}

            for point in points:
                payload = point.get('payload', {})
                point_type = payload.get('type')
                point_status = payload.get('status')
                point_env = payload.get('environment')

                if point_type:
                    types[point_type] = types.get(point_type, 0) + 1
                if point_status:
                    statuses[point_status] = statuses.get(point_status, 0) + 1
                if point_env:
                    environments[point_env] = environments.get(point_env, 0) + 1

            print(f"\nAvailable types: {json.dumps(types, indent=2)}")
            print(f"Available statuses: {json.dumps(statuses, indent=2)}")
            print(f"Available environments: {json.dumps(environments, indent=2)}")

            # Try to find type='scenario' records specifically
            scenario_records = []
            for point in points:
                if point.get('payload', {}).get('type') == 'scenario':
                    scenario_records.append(point)

            if scenario_records:
                print(f"\nFound {len(scenario_records)} records with type='scenario':")
                for i, record in enumerate(scenario_records[:3]):  # Show just the first 3
                    print(f"\nScenario Record {i + 1}:")
                    print(f"ID: {record.get('id')}")
                    print(f"Payload: {json.dumps(record.get('payload', {}), indent=2)}")
            else:
                print("\n❌ No records with type='scenario' found!")

        else:
            # If we found records, show a sample
            scroll_url = f"http://localhost:6333/collections/{collection}/points/scroll"
            scroll_payload = {
                "filter": filter_obj,
                "limit": 3,  # Just get a few for debugging
                "with_payload": True,
                "with_vector": False
            }

            response = requests.post(scroll_url, json=scroll_payload)
            response.raise_for_status()
            scroll_data = response.json()

            points = scroll_data.get('result', {}).get('points', [])

            print(f"\nSample of matching records:")
            for i, point in enumerate(points):
                print(f"\nRecord {i + 1}:")
                print(f"ID: {point.get('id')}")
                print(f"Payload: {json.dumps(point.get('payload', {}), indent=2)}")

    except Exception as e:
        print(f"❌ Error running debug query: {str(e)}")


@task
def test_environment_filter(c, collection="test_artifacts"):
    """Test if environment values are correctly stored for filtering."""
    print("🔍 Testing environment filters...")

    # First, get all records to see what environment values exist
    scroll_url = f"http://localhost:6333/collections/{collection}/points/scroll"
    payload = {
        "limit": 100,
        "with_payload": True,
        "with_vector": False
    }

    try:
        response = requests.post(scroll_url, json=payload)
        response.raise_for_status()
        scroll_data = response.json()

        points = scroll_data.get('result', {}).get('points', [])

        print(f"Found {len(points)} total records")

        # Count records with environment in payload
        env_count = 0
        env_values = {}

        for point in points:
            payload = point.get('payload', {})
            if 'environment' in payload:
                env_count += 1
                env = payload['environment']
                env_values[env] = env_values.get(env, 0) + 1

        print(f"\n{env_count} records have 'environment' in their payload")
        print(f"Environment values distribution: {json.dumps(env_values, indent=2)}")

        # Check which records have environment
        print("\nChecking which types of records have environment field:")
        types_with_env = {}

        for point in points:
            payload = point.get('payload', {})
            if 'environment' in payload:
                point_type = payload.get('type', 'unknown')
                types_with_env[point_type] = types_with_env.get(point_type, 0) + 1

        print(f"Types with environment field: {json.dumps(types_with_env, indent=2)}")

        # Test a filter just on environment
        if env_values:
            test_env = next(iter(env_values.keys()))
            print(f"\nTesting filter with environment='{test_env}'")

            filter_obj = {
                "must": [
                    {
                        "key": "environment",
                        "match": {
                            "value": test_env
                        }
                    }
                ]
            }

            count_url = f"http://localhost:6333/collections/{collection}/points/count"
            count_payload = {
                "filter": filter_obj
            }

            response = requests.post(count_url, json=count_payload)
            response.raise_for_status()
            count_data = response.json()

            count = count_data.get('result', {}).get('count', 0)
            print(f"Found {count} records with environment='{test_env}'")

    except Exception as e:
        print(f"❌ Error testing environment filter: {str(e)}")


@task
def fix_data(c, collection="test_artifacts"):
    """
    Look for 'scenario' records and check if they have all required fields.
    If not, try to add missing fields from related 'report' records.
    """
    print("🛠️ Analyzing and trying to fix data issues...")

    # Get all records
    scroll_url = f"http://localhost:6333/collections/{collection}/points/scroll"
    payload = {
        "limit": 100,
        "with_payload": True,
        "with_vector": False
    }

    try:
        response = requests.post(scroll_url, json=payload)
        response.raise_for_status()
        scroll_data = response.json()

        points = scroll_data.get('result', {}).get('points', [])

        print(f"Found {len(points)} total records")

        # Separate by type
        scenarios = []
        reports = []

        for point in points:
            point_type = point.get('payload', {}).get('type')
            if point_type == 'scenario':
                scenarios.append(point)
            elif point_type == 'report':
                reports.append(point)

        print(f"Found {len(scenarios)} scenario records and {len(reports)} report records")

        # Create a map of report data for quick lookup
        report_data = {}
        for report in reports:
            report_id = report.get('id')
            report_data[report_id] = report.get('payload', {})

        # Check scenarios for missing data
        scenarios_missing_env = 0

        for scenario in scenarios:
            scenario_payload = scenario.get('payload', {})

            # Check if environment is missing
            if 'environment' not in scenario_payload:
                scenarios_missing_env += 1

        print(f"{scenarios_missing_env} scenario records are missing environment data")

        if scenarios_missing_env > 0:
            print("\nDetails of scenarios missing environment data:")
            for scenario in scenarios:
                scenario_payload = scenario.get('payload', {})
                if 'environment' not in scenario_payload:
                    print(f"ID: {scenario.get('id')}")
                    print(f"Payload: {json.dumps(scenario_payload, indent=2)}")
                    print("---")

            # Ask if user wants to fix the data
            fix = input(
                "\nWould you like to try to fix these scenarios by copying environment from related reports? (y/n): ")

            if fix.lower() == 'y':
                print("Fixing data...")
                # Implement the fix logic here
                # This would involve updating the records in Qdrant
            else:
                print("Skipping data fix.")

    except Exception as e:
        print(f"❌ Error analyzing data: {str(e)}")