"""
Database management tasks for Friday Service using Invoke.

This module provides tasks for managing both PostgreSQL and Qdrant databases.
"""
import os
import sys
import logging
import asyncio
import subprocess
from datetime import datetime
from pathlib import Path
from invoke import task

logger = logging.getLogger("friday.db_tasks")

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@task
def status(c, vector=False):
    """Check the status of the databases."""
    if vector:
        # Check vector database status
        print("Checking vector database status...")
        c.run("python -m scripts.qdrant_setup check", pty=True)
    else:
        # Check PostgreSQL database status
        print("Checking PostgreSQL database status...")
        c.run("invoke db.check-health", pty=True)

        # Also show Alembic status
        print("\nChecking Alembic migration status...")
        c.run("alembic current", pty=True)


@task
def setup(c, confirm=True, reset=False):
    """Set up both PostgreSQL and vector databases."""
    if reset and confirm and not input("Are you sure you want to RESET both databases? [y/N] ").lower().startswith('y'):
        print("Database reset cancelled.")
        return

    # Set up PostgreSQL database
    print("Setting up PostgreSQL database...")
    if reset:
        c.run("invoke db.reset", pty=True)
    else:
        c.run("invoke db.create", pty=True)

    # Set up vector database
    print("\nSetting up vector database...")
    if reset:
        c.run("python -m scripts.qdrant_setup reset-all", pty=True)
    else:
        c.run("python -m scripts.qdrant_setup setup", pty=True)


@task
def reset(c, confirm=True):
    """Reset both PostgreSQL and vector databases."""
    setup(c, confirm=confirm, reset=True)


@task
def sync(c, test_run_id=None, project_id=None, chunks=False, all=False):
    """Sync data between PostgreSQL and vector databases."""
    cmd = "python -m scripts.data_sync"

    if test_run_id:
        cmd += f" sync-run --test-run-id {test_run_id}"
    elif project_id:
        cmd += f" sync-project --project-id {project_id}"
    elif chunks:
        cmd += " sync-chunks"
    elif all:
        cmd += " sync-all"
    else:
        print("Please specify what to sync: --test-run-id, --project-id, --chunks, or --all")
        return

    print(f"Running command: {cmd}")
    c.run(cmd, pty=True)


@task
def generate_test_data(c, scale="small"):
    """Generate test data and sync it to both databases."""
    print(f"Generating {scale} test data in PostgreSQL...")
    c.run(f"invoke db.generate-test-data --scale={scale}", pty=True)

    print("\nSyncing generated data to vector database...")
    c.run("python -m scripts.data_sync sync-all", pty=True)


@task
def list(c, projects=False, test_runs=True, project_id=None, limit=10):
    """List projects or test runs."""
    cmd = "python -m scripts.data_sync"

    if projects:
        cmd += " list-projects"
        print("Listing projects:")
    elif test_runs:
        cmd += " list-runs"
        if project_id:
            cmd += f" --project-id {project_id}"
        cmd += f" --limit {limit}"
        print("Listing test runs:")

    c.run(cmd, pty=True)


@task
def backup_all(c, output_dir=None):
    """Backup both PostgreSQL and vector databases."""
    # Backup PostgreSQL
    print("Backing up PostgreSQL database...")
    if output_dir:
        c.run(f"invoke db.backup --output-dir={output_dir}", pty=True)
    else:
        c.run("invoke db.backup", pty=True)

    # Note: Vector database backup would depend on Qdrant's backup capabilities
    # This might need to be implemented based on Qdrant's specific APIs
    print("\nNOTE: Vector database (Qdrant) backup is not implemented yet.")
    print("Please refer to Qdrant documentation for backup procedures.")




@task
def create(c, confirm=True, db_name="friday"):
    """Create the database from scratch."""
    if confirm and not input(f"Are you sure you want to create a new database '{db_name}'? [y/N] ").lower().startswith(
            'y'):
        print("Database creation cancelled.")
        return

    print(f"Creating database '{db_name}'...")
    try:
        # Check if database already exists
        result = c.run(f"psql -lqt | cut -d\\| -f 1 | grep -qw {db_name}", warn=True)

        if result.exited == 0:
            print(f"Database '{db_name}' already exists.")
            if confirm and not input("Do you want to drop and recreate it? [y/N] ").lower().startswith('y'):
                print("Database recreation cancelled.")
                return

            # Drop existing database
            c.run(f"dropdb {db_name}")
            print(f"Dropped existing database '{db_name}'.")

        # Create database
        c.run(f"createdb {db_name}")

        # Create vector extension (for text embeddings)
        c.run(f"psql -d {db_name} -c 'CREATE EXTENSION IF NOT EXISTS vector;'")

        # Run migrations
        migrate(c, confirm=False)

        print(f"Database '{db_name}' created successfully.")
    except Exception as e:
        print(f"Error creating database: {e}")
        raise


@task
def migrate(c, confirm=False, revision="head"):
    """Run all migrations to the latest version."""
    if confirm and not input(f"Are you sure you want to run migrations to '{revision}'? [y/N] ").lower().startswith(
            'y'):
        print("Migrations cancelled.")
        return

    print(f"Running migrations to '{revision}'...")
    try:
        c.run(f"alembic upgrade {revision}")
        print("Migrations completed successfully.")
    except Exception as e:
        print(f"Error running migrations: {e}")
        raise


@task
def downgrade(c, revision):
    """Downgrade to a specific migration version."""
    if not revision:
        print("Error: You must specify a revision to downgrade to.")
        return

    if not input(
            f"WARNING: Downgrading migrations may result in data loss.\nAre you sure you want to downgrade to '{revision}'? [y/N] ").lower().startswith(
            'y'):
        print("Migration downgrade cancelled.")
        return

    print(f"Downgrading to revision '{revision}'...")
    try:
        c.run(f"alembic downgrade {revision}")
        print(f"Successfully downgraded to revision '{revision}'.")
    except Exception as e:
        print(f"Error downgrading migrations: {e}")
        raise


@task
def revision(c, message):
    """Create a new migration revision."""
    if not message:
        print("Error: You must provide a message for the revision.")
        return

    print(f"Creating new migration revision with message: '{message}'...")
    try:
        c.run(f"alembic revision --autogenerate -m '{message}'")
        print("Migration revision created successfully.")
    except Exception as e:
        print(f"Error creating migration revision: {e}")
        raise


@task
def history(c):
    """Show migration history."""
    print("Migration history:")
    try:
        c.run("alembic history")
    except Exception as e:
        print(f"Error showing migration history: {e}")
        raise


@task
def current(c):
    """Show current migration revision."""
    print("Current migration revision:")
    try:
        c.run("alembic current")
    except Exception as e:
        print(f"Error showing current migration: {e}")
        raise


@task
def backup(c, db_name="friday", output_dir=None):
    """Backup the database (schema and data)."""
    # Generate backup filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    if not output_dir:
        output_dir = Path("./backups")
    else:
        output_dir = Path(output_dir)

    # Ensure backup directory exists
    output_dir.mkdir(parents=True, exist_ok=True)

    backup_file = output_dir / f"{db_name}_backup_{timestamp}.sql"

    print(f"Backing up database '{db_name}' to {backup_file}...")
    try:
        c.run(f"pg_dump --clean --if-exists --format=plain --create {db_name} > {backup_file}")
        print(f"Database backup saved to {backup_file}")

        # Create compressed version
        c.run(f"gzip -c {backup_file} > {backup_file}.gz")
        print(f"Compressed backup saved to {backup_file}.gz")

        return str(backup_file)
    except Exception as e:
        print(f"Error backing up database: {e}")
        raise


@task
def restore(c, backup_file, db_name="friday", confirm=True):
    """Restore database from a backup."""
    if not os.path.exists(backup_file):
        print(f"Error: Backup file '{backup_file}' not found.")
        return

    if confirm and not input(
            f"Are you sure you want to restore database '{db_name}' from backup? This will OVERWRITE ALL EXISTING DATA. [y/N] ").lower().startswith(
            'y'):
        print("Database restore cancelled.")
        return

    print(f"Restoring database '{db_name}' from {backup_file}...")
    try:
        # Check if file is compressed
        if backup_file.endswith('.gz'):
            c.run(f"gunzip -c {backup_file} | psql -d postgres")
        else:
            c.run(f"psql -d postgres -f {backup_file}")

        print(f"Database '{db_name}' restored successfully from backup.")
    except Exception as e:
        print(f"Error restoring database: {e}")
        raise


@task
def clean(c, tables=None, confirm=True, db_name="friday"):
    """Clean specific tables or the entire database."""
    if tables:
        table_list = tables.split(',')
        message = f"Are you sure you want to clean the following tables: {', '.join(table_list)}? [y/N] "
    else:
        message = "Are you sure you want to clean ALL tables in the database? This cannot be undone! [y/N] "

    if confirm and not input(message).lower().startswith('y'):
        print("Database cleaning cancelled.")
        return

    try:
        if tables:
            # Clean specific tables
            script_path = Path("./scripts/reset_specific_tables.sql")
            for table in table_list:
                print(f"Cleaning table '{table}'...")
                c.run(f"psql -d {db_name} -c \"SELECT reset_table_cascade('{table}');\"")
        else:
            # Clean all tables
            script_path = Path("./scripts/clean_all_data.sql")
            print("Cleaning all tables...")
            c.run(f"psql -d {db_name} -f {script_path}")

        print("Database cleaning completed successfully.")
    except Exception as e:
        print(f"Error cleaning database: {e}")
        raise


@task
def reset(c, confirm=True, db_name="friday"):
    """Completely reset the database (drop and recreate schema)."""
    message = f"Are you sure you want to COMPLETELY RESET database '{db_name}'? This will DELETE ALL DATA AND SCHEMA. [y/N] "

    if confirm and not input(message).lower().startswith('y'):
        print("Database reset cancelled.")
        return

    try:
        # Backup before reset if confirmed
        if confirm and input("Would you like to create a backup before resetting? [Y/n] ").lower() != 'n':
            backup_file = backup(c, db_name=db_name)
            print(f"Backup created at {backup_file} before reset.")

        # Drop and recreate database
        print(f"Dropping database '{db_name}'...")
        c.run(f"dropdb --if-exists {db_name}")

        # Create fresh database
        create(c, confirm=False, db_name=db_name)

        print(f"Database '{db_name}' has been completely reset.")
    except Exception as e:
        print(f"Error resetting database: {e}")
        raise


@task
def generate_test_data(c, scale="small", confirm=True, db_name="friday"):
    """Generate test data for development and testing."""
    valid_scales = ["small", "medium", "large"]
    if scale not in valid_scales:
        print(f"Error: Invalid scale '{scale}'. Valid options are: {', '.join(valid_scales)}")
        return

    if confirm and not input(
            f"Are you sure you want to generate {scale} test data? This may overwrite existing data. [y/N] ").lower().startswith(
            'y'):
        print("Test data generation cancelled.")
        return

    print(f"Generating {scale} test data...")
    try:
        # Run the appropriate test data generation script
        c.run(f"python scripts/generate_test_data.py --scale {scale} --db-name {db_name}")
        print("Test data generated successfully.")
    except Exception as e:
        print(f"Error generating test data: {e}")
        raise


@task
def check_health(c, db_name="friday"):
    """Check database health and display statistics."""
    print(f"Checking health of database '{db_name}'...")
    try:
        # Get database size
        c.run(f"psql -d {db_name} -c \"SELECT pg_size_pretty(pg_database_size('{db_name}')) AS db_size;\"")

        # Get table counts - Fix this line:
        c.run(
            f"psql -d {db_name} -c \"SELECT relname AS table_name, n_live_tup AS row_count FROM pg_stat_user_tables ORDER BY n_live_tup DESC;\"")

        # Get index usage stats
        c.run(
            f"psql -d {db_name} -c \"SELECT indexrelname, idx_scan, idx_tup_read, idx_tup_fetch FROM pg_stat_user_indexes ORDER BY idx_scan DESC LIMIT 10;\"")

        # Get connection info
        c.run(
            f"psql -d {db_name} -c \"SELECT count(*) as active_connections FROM pg_stat_activity WHERE datname = '{db_name}';\"")

        print("Database health check completed.")
    except Exception as e:
        print(f"Error checking database health: {e}")
        raise


@task
def analyze(c, db_name="friday"):
    """Run ANALYZE to update database statistics."""
    print(f"Running ANALYZE on database '{db_name}'...")
    try:
        c.run(f"psql -d {db_name} -c \"ANALYZE VERBOSE;\"")
        print("Database statistics updated successfully.")
    except Exception as e:
        print(f"Error updating database statistics: {e}")
        raise


@task
def vacuum(c, full=False, db_name="friday"):
    """Run VACUUM to reclaim storage and update statistics."""
    vacuum_type = "FULL" if full else ""
    print(f"Running VACUUM {vacuum_type} on database '{db_name}'...")

    if full and not input(
            "WARNING: VACUUM FULL locks tables and may take a long time. Continue? [y/N] ").lower().startswith('y'):
        print("VACUUM FULL cancelled.")
        return

    try:
        c.run(f"psql -d {db_name} -c \"VACUUM {vacuum_type} VERBOSE;\"")
        print(f"VACUUM {vacuum_type} completed successfully.")
    except Exception as e:
        print(f"Error running VACUUM: {e}")
        raise
