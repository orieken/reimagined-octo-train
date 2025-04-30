import time
import subprocess
from invoke import task

TEST_CONTAINER_NAME = "friday-test-db"
TEST_DB_PORT = 5433
POSTGRES_IMAGE = "pgvector/pgvector:pg17"

# These are for connecting from test code
DB_USER = "friday_test"
DB_PASSWORD = "password"
DB_NAME = "test_friday"
DB_SUPERUSER = "postgres"
SUPERUSER_PASSWORD = "postgres"

# Used by test_models
TEST_DB_URL = f"postgresql+asyncpg://{DB_USER}:{DB_PASSWORD}@localhost:{TEST_DB_PORT}/{DB_NAME}"

ROLE_SQL = (
    "DO $$ BEGIN "
    "IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'friday_test') THEN "
    "CREATE ROLE friday_test WITH LOGIN PASSWORD 'password'; "
    "END IF; "
    "END $$;"
)

DB_SQL = (
    "DO $$ BEGIN "
    "IF NOT EXISTS (SELECT FROM pg_database WHERE datname = 'test_friday') THEN "
    "CREATE DATABASE test_friday OWNER friday_test; "
    "END IF; "
    "END $$;"
)

def start_test_db_container(c, keep_running=False):
    """Start or reuse the test PostgreSQL container and set up the test user/db."""
    result = c.run(f"docker ps -a --format '{{{{.Names}}}}' | grep -w {TEST_CONTAINER_NAME}", warn=True, hide=True)
    is_running = result.ok

    if not is_running:
        print("🚀 Starting test PostgreSQL container...")
        c.run(
            f"docker run --rm -d "
            f"--name {TEST_CONTAINER_NAME} "
            f"-e POSTGRES_USER={DB_SUPERUSER} "
            f"-e POSTGRES_PASSWORD={SUPERUSER_PASSWORD} "
            f"-e POSTGRES_DB=postgres "
            f"-p {TEST_DB_PORT}:5432 "
            f"{POSTGRES_IMAGE}",
            warn=True,
        )

    print("⏳ Waiting for PostgreSQL to be ready...")
    time.sleep(2)
    for _ in range(20):  # up to ~10 seconds
        result = subprocess.run(
            ["pg_isready", "-h", "localhost", "-p", str(TEST_DB_PORT), "-U", DB_SUPERUSER],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        if result.returncode == 0:
            time.sleep(2)
            print("✅ PostgreSQL is ready.")
            break
        time.sleep(0.5)
    else:
        raise RuntimeError("❌ PostgreSQL did not become ready in time.")

    print("⚙️ Creating test user and database (if missing)...")
    c.run(
        f"docker exec {TEST_CONTAINER_NAME} psql -U postgres -c \"{ROLE_SQL}\"",
        warn=True
    )
    c.run(
        f"docker exec {TEST_CONTAINER_NAME} psql -U postgres -c \"{DB_SQL}\"",
        warn=True
    )


@task
def test_models(c, keep=False):
    """Run model tests in a fresh or existing Postgres test container."""
    start_test_db_container(c, keep_running=keep)

    # Step 1: Ensure test user & DB exist
    print("⚙️ Creating test user and database (if missing)...")
    role_sql = (
        "DO $$ BEGIN "
        "IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'friday_test') THEN "
        "CREATE ROLE friday_test WITH LOGIN PASSWORD 'password'; "
        "END IF; END $$;"
    )
    db_sql = (
        "DO $$ BEGIN "
        "IF NOT EXISTS (SELECT FROM pg_database WHERE datname = 'test_friday') THEN "
        "CREATE DATABASE test_friday OWNER friday_test; "
        "END IF; END $$;"
    )
    c.run(f"docker exec {TEST_CONTAINER_NAME} psql -U postgres -c \"{role_sql}\"", warn=True)
    c.run(f"docker exec {TEST_CONTAINER_NAME} psql -U postgres -c \"{db_sql}\"", warn=True)

    # Step 2: Run init script to create tables
    print("🧱 Running init_db.py to create tables...")
    c.run(f'DATABASE_URL="{TEST_DB_URL}" python scripts/init_db.py', warn=True)

    # Step 3: Run the model tests
    try:
        print("🧪 Running model tests...")
        c.run(f'DATABASE_URL="{TEST_DB_URL}" pytest tests/test_models.py')
    finally:
        if not keep:
            print("🧹 Stopping test container...")
            c.run(f"docker stop {TEST_CONTAINER_NAME}", warn=True)
        else:
            print("🧪 Container kept running for manual inspection.")

@task
def test_db_psql(c):
    """Launch psql in the test container for manual DB inspection."""
    start_test_db_container(c, keep_running=True)
    print(f"🔍 Connecting to '{DB_NAME}' as '{DB_USER}' in '{TEST_CONTAINER_NAME}'...")
    try:
        subprocess.run(
            ["docker", "exec", "-it", TEST_CONTAINER_NAME, "psql", "-U", DB_USER, "-d", DB_NAME],
            check=True
        )
    except subprocess.CalledProcessError:
        print("❌ Failed to open psql session.")

@task
def test(c, cov=False, html=False, xvs=False):
    """
    Run tests, optionally with coverage.

    Args:
        cov: Enable coverage reporting
        html: Generate HTML coverage report
        xvs: Run extra verbose summary
    """
    print("Running unit tests...")

    cmd = "pytest tests/"

    if cov:
        cmd += " --cov=app --cov-report=term-missing"
    if html:
        cmd += " --cov-report=html"
    if xvs:
        cmd += " -v -s"

    c.run(cmd, pty=True)