from invoke import task
import json
import uuid
import datetime
import requests
import os
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("tag_tester")

# Set your API endpoints
API_BASE = "http://localhost:4000"
PROCESSOR_ENDPOINT = f"{API_BASE}/api/v1/processor/cucumber"
RESULTS_ENDPOINT = f"{API_BASE}/api/v1/results"
DATABASE_URL="postgresql+asyncpg://friday_service:password@localhost:5432/friday"
if not os.environ.get("DATABASE_URL"):
    os.environ["DATABASE_URL"] = DATABASE_URL


@task
def test_tag_processing(c, log_level="INFO"):
    """Test cucumber report processing with tags and verify they're stored correctly"""
    logging.getLogger().setLevel(getattr(logging, log_level.upper()))

    # Generate a unique test run ID
    test_run_id = f"tag-test-{uuid.uuid4()}"
    logger.info(f"Starting tag test with test_run_id: {test_run_id}")

    # Step 1: Create a cucumber report with explicit tags
    cucumber_report = [
        {
            "uri": "features/login.feature",
            "id": "login-feature",
            "name": "Login Feature",
            "description": "As a user, I want to log in to the application",
            "keyword": "Feature",
            "elements": [
                {
                    "id": "login-feature;successful-login",
                    "name": "Successful login",
                    "keyword": "Scenario",
                    "description": "User logs in successfully with valid credentials",
                    "tags": [
                        {"name": "@login", "line": 5},
                        {"name": "@smoke", "line": 5},
                        {"name": "@regression", "line": 5}
                    ],
                    "steps": [
                        {
                            "keyword": "Given ",
                            "name": "I am on the login page",
                            "result": {
                                "status": "passed",
                                "duration": 1234567890
                            }
                        },
                        {
                            "keyword": "When ",
                            "name": "I enter valid credentials",
                            "result": {
                                "status": "passed",
                                "duration": 1234567890
                            }
                        },
                        {
                            "keyword": "Then ",
                            "name": "I should be logged in",
                            "result": {
                                "status": "passed",
                                "duration": 1234567890
                            }
                        }
                    ]
                }
            ]
        }
    ]

    # Create metadata for the report
    metadata = {
        "project": "tag-test-project",
        "test_run_id": test_run_id,
        "branch": "main",
        "commit": "abc123",
        "environment": "test",
        "timestamp": datetime.utcnow().isoformat(),
        "runner": "tag-test-suite"
    }

    # Create the payload
    payload = {
        "metadata": metadata,
        "features": cucumber_report
    }

    # Step 2: Send the report to the processor
    logger.info("Sending cucumber report to processor endpoint...")
    logger.debug(f"Payload: {json.dumps(payload, indent=2)}")

    try:
        response = requests.post(PROCESSOR_ENDPOINT, json=payload)
        logger.info(f"Processor response status: {response.status_code}")

        if response.status_code == 200:
            logger.info("Cucumber report processed successfully!")
        else:
            logger.error(f"Error processing report: {response.text}")
            return
    except Exception as e:
        logger.error(f"Exception sending report: {str(e)}")
        return

    # Step 3: Wait a moment for processing to complete
    import time
    logger.info("Waiting 2 seconds for processing...")
    time.sleep(2)

    # Step 4: Query the database to check if tags were stored
    logger.info("Checking database for stored tags...")
    try:
        from sqlalchemy import create_engine, text
        from sqlalchemy.orm import sessionmaker

        # Get connection string from environment
        db_url = os.environ.get("DATABASE_URL")
        if not db_url:
            logger.error("DATABASE_URL environment variable not set")
            return

        engine = create_engine(db_url)
        Session = sessionmaker(bind=engine)

        with Session() as session:
            # Find the test run ID
            result = session.execute(
                text("SELECT id FROM test_runs WHERE external_id = :external_id"),
                {"external_id": test_run_id}
            ).fetchone()

            if not result:
                logger.error(f"Test run with external_id {test_run_id} not found in database")
                return

            db_test_run_id = result[0]
            logger.info(f"Found test run in database with ID: {db_test_run_id}")

            # Find scenarios for this test run
            scenarios = session.execute(
                text("SELECT id, name FROM scenarios WHERE test_run_id = :test_run_id"),
                {"test_run_id": db_test_run_id}
            ).fetchall()

            if not scenarios:
                logger.error("No scenarios found for this test run")
                return

            logger.info(f"Found {len(scenarios)} scenarios")

            # Check for tags for each scenario
            for scenario_id, scenario_name in scenarios:
                tags = session.execute(
                    text("SELECT id, tag, line FROM scenario_tags WHERE scenario_id = :scenario_id"),
                    {"scenario_id": scenario_id}
                ).fetchall()

                if tags:
                    logger.info(f"Scenario '{scenario_name}' has {len(tags)} tags:")
                    for tag_id, tag, line in tags:
                        logger.info(f"  - {tag} (line: {line}, id: {tag_id})")
                else:
                    logger.error(f"Scenario '{scenario_name}' has NO tags in the database!")
    except Exception as e:
        logger.error(f"Exception checking database: {str(e)}")

    # Step 5: Check the results endpoint
    logger.info("Checking results endpoint...")
    try:
        response = requests.get(RESULTS_ENDPOINT)

        if response.status_code == 200:
            results = response.json()
            tags = results.get("results", {}).get("tags", {})

            if tags:
                logger.info(f"Results endpoint returned {len(tags)} tags:")
                for tag, stats in tags.items():
                    logger.info(f"  - {tag}: count={stats.get('count')}, pass_rate={stats.get('pass_rate')}")
            else:
                logger.error("Results endpoint returned NO tags")
        else:
            logger.error(f"Error getting results: {response.text}")
    except Exception as e:
        logger.error(f"Exception checking results: {str(e)}")

    logger.info("Tag test completed")


@task
def debug_database_schema(c):
    """Check if the database schema has the correct tables and columns for tags"""

    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        print("ERROR: DATABASE_URL environment variable not set")
        return

    try:
        from sqlalchemy import create_engine, inspect, text

        engine = create_engine(db_url)
        inspector = inspect(engine)

        # Check if scenario_tags table exists
        tables = inspector.get_table_names()
        print(f"Database tables: {tables}")

        if "scenario_tags" not in tables:
            print("ERROR: scenario_tags table is missing!")
            return

        # Check schema of scenario_tags table
        columns = inspector.get_columns("scenario_tags")
        print("\nscenario_tags table columns:")
        for column in columns:
            print(f"  - {column['name']} ({column['type']})")

        # Check if DBScenarioTag model is being used
        with engine.connect() as conn:
            # Check for any existing tags
            result = conn.execute(text("SELECT COUNT(*) FROM scenario_tags")).fetchone()
            count = result[0] if result else 0
            print(f"\nTotal records in scenario_tags table: {count}")

            # Print sample if any exist
            if count > 0:
                sample = conn.execute(text("SELECT id, scenario_id, tag, line FROM scenario_tags LIMIT 5")).fetchall()
                print("\nSample tag records:")
                for row in sample:
                    print(f"  - ID: {row[0]}, Scenario: {row[1]}, Tag: {row[2]}, Line: {row[3]}")
    except Exception as e:
        print(f"Error inspecting database: {e}")


@task
def debug_cucumber_transformer(c):
    """Print debug info about the cucumber transformer"""

    try:
        from app.services.cucumber_transformer import transform_cucumber_json_to_internal_model

        print("Found transform_cucumber_json_to_internal_model function")

        # Create a simple test cucumber report
        test_report = [{
            "uri": "features/test.feature",
            "name": "Test Feature",
            "elements": [{
                "name": "Test Scenario",
                "tags": [{"name": "@test", "line": 1}],
                "steps": []
            }]
        }]

        # Try to transform it
        from app.models.domain import Scenario
        print("\nChecking if Scenario model has tags and tag_metadata attributes:")

        # Create a sample scenario
        scenario = Scenario(
            id="test-id",
            name="Test Scenario",
            status="PASSED",
            steps=[]
        )

        # Check if it has tags attribute
        has_tags = hasattr(scenario, "tags")
        print(f"  - Has tags attribute: {has_tags}")

        # Check if it has tag_metadata attribute
        has_tag_metadata = hasattr(scenario, "tag_metadata")
        print(f"  - Has tag_metadata attribute: {has_tag_metadata}")

        # Check other properties
        print(f"  - Has feature_file attribute: {hasattr(scenario, 'feature_file')}")
        print(f"  - Has feature_id attribute: {hasattr(scenario, 'feature_id')}")

    except ImportError as e:
        print(f"Error importing modules: {e}")
    except Exception as e:
        print(f"Error during debug: {e}")


@task
def verify_tag_storage(c):
    """Verify that tags are properly stored in the database after fix implementation"""
    print("After implementing the fix, you should:")
    print("1. Restart your application")
    print("2. Run generate_test_report to submit a test report with tags")
    print("3. Check the logs for tag storage debugging messages")
    print("4. Query the database to verify tags were stored:")
    print("   SELECT * FROM scenario_tags ORDER BY created_at DESC LIMIT 10;")
    print("5. Check the results endpoint to see if tags appear in the response")