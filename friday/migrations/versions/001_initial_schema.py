"""
Initial migration for Friday Service database schema
Revision ID: 0001_initial_schema
Revises:
Create Date: 2025-04-03
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import enum

# revision identifiers, used by Alembic
revision = '0001_initial_schema'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Create PostgreSQL extension for vector type if it doesn't exist
    op.execute('CREATE EXTENSION IF NOT EXISTS vector')

    # Try to drop existing enum types first to ensure a clean slate
    op.execute("""
    DO $$
    BEGIN
        DROP TYPE IF EXISTS teststatus;
        DROP TYPE IF EXISTS reportformat;
        DROP TYPE IF EXISTS reportstatus;
        DROP TYPE IF EXISTS reporttype;
    EXCEPTION WHEN OTHERS THEN
        NULL;
    END $$;
    """)

    # Create enum types directly with SQL
    op.execute("CREATE TYPE teststatus AS ENUM ('PASSED', 'FAILED', 'SKIPPED', 'PENDING', 'RUNNING', 'ERROR')")
    op.execute("CREATE TYPE reportformat AS ENUM ('HTML', 'PDF', 'CSV', 'JSON', 'XML')")
    op.execute("CREATE TYPE reportstatus AS ENUM ('PENDING', 'RUNNING', 'COMPLETED', 'FAILED')")
    op.execute(
        "CREATE TYPE reporttype AS ENUM ('TEST_SUMMARY', 'BUILD_HEALTH', 'FEATURE_COVERAGE', 'TREND_ANALYSIS', 'CUSTOM')")

    # Projects table
    op.execute("""
    CREATE TABLE projects (
        id SERIAL PRIMARY KEY,
        name VARCHAR(255) NOT NULL UNIQUE,
        description TEXT,
        repository_url VARCHAR(255),
        created_at TIMESTAMP NOT NULL DEFAULT NOW(),
        updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
        active BOOLEAN NOT NULL DEFAULT TRUE,
        meta_data JSONB
    )
    """)

    # Test Reports table (existing model)
    op.execute("""
    CREATE TABLE test_reports (
        id SERIAL PRIMARY KEY,
        project_id INTEGER NOT NULL REFERENCES projects(id),
        name VARCHAR(255) NOT NULL,
        description TEXT,
        execution_date TIMESTAMP,
        status VARCHAR(50),
        meta_data JSONB,
        created_at TIMESTAMP NOT NULL DEFAULT NOW(),
        updated_at TIMESTAMP NOT NULL DEFAULT NOW()
    )
    """)

    # Test Cases table (existing model)
    op.execute("""
    CREATE TABLE test_cases (
        id SERIAL PRIMARY KEY,
        test_report_id INTEGER NOT NULL REFERENCES test_reports(id),
        name VARCHAR(255) NOT NULL,
        description TEXT,
        status VARCHAR(50),
        execution_time TIMESTAMP,
        duration INTEGER,
        is_automated BOOLEAN NOT NULL DEFAULT TRUE,
        meta_data JSONB,
        created_at TIMESTAMP NOT NULL DEFAULT NOW(),
        updated_at TIMESTAMP NOT NULL DEFAULT NOW()
    )
    """)

    # Build Infos table
    op.execute("""
    CREATE TABLE build_infos (
        id SERIAL PRIMARY KEY,
        project_id INTEGER NOT NULL REFERENCES projects(id),
        build_number VARCHAR(50) NOT NULL,
        name VARCHAR(255),
        status VARCHAR(50) NOT NULL,
        start_time TIMESTAMP NOT NULL,
        end_time TIMESTAMP,
        duration FLOAT,
        branch VARCHAR(100),
        commit_hash VARCHAR(40),
        commit_message TEXT,
        author VARCHAR(100),
        ci_url VARCHAR(255),
        artifacts_url VARCHAR(255),
        environment VARCHAR(50),
        meta_data JSONB,
        created_at TIMESTAMP NOT NULL DEFAULT NOW(),
        updated_at TIMESTAMP NOT NULL DEFAULT NOW()
    )
    """)

    # Features table
    op.execute("""
    CREATE TABLE features (
        id SERIAL PRIMARY KEY,
        project_id INTEGER NOT NULL REFERENCES projects(id),
        name VARCHAR(255) NOT NULL,
        description TEXT,
        file_path VARCHAR(255),
        tags VARCHAR[],
        priority VARCHAR(50),
        status VARCHAR(50),
        created_at TIMESTAMP NOT NULL DEFAULT NOW(),
        updated_at TIMESTAMP NOT NULL DEFAULT NOW()
    )
    """)

    # Test Results Tags table
    op.execute("""
    CREATE TABLE test_results_tags (
        id SERIAL PRIMARY KEY,
        name VARCHAR(100) NOT NULL UNIQUE,
        description TEXT,
        color VARCHAR(7),
        created_at TIMESTAMP NOT NULL DEFAULT NOW(),
        updated_at TIMESTAMP NOT NULL DEFAULT NOW()
    )
    """)

    # Test Runs table
    op.execute("""
    CREATE TABLE test_runs (
        id SERIAL PRIMARY KEY,
        project_id INTEGER NOT NULL REFERENCES projects(id),
        build_id INTEGER REFERENCES build_infos(id),
        name VARCHAR(255) NOT NULL,
        description TEXT,
        status teststatus NOT NULL DEFAULT 'RUNNING',
        start_time TIMESTAMP NOT NULL DEFAULT NOW(),
        end_time TIMESTAMP,
        duration FLOAT,
        total_tests INTEGER NOT NULL DEFAULT 0,
        passed_tests INTEGER NOT NULL DEFAULT 0,
        failed_tests INTEGER NOT NULL DEFAULT 0,
        skipped_tests INTEGER NOT NULL DEFAULT 0,
        error_tests INTEGER NOT NULL DEFAULT 0,
        success_rate FLOAT,
        environment VARCHAR(50),
        branch VARCHAR(100),
        commit_hash VARCHAR(40),
        meta_data JSONB,
        created_at TIMESTAMP NOT NULL DEFAULT NOW(),
        updated_at TIMESTAMP NOT NULL DEFAULT NOW()
    )
    """)

    # Many-to-Many relationship table for Test Runs and Tags
    op.execute("""
    CREATE TABLE test_run_tags (
        test_run_id INTEGER NOT NULL REFERENCES test_runs(id),
        tag_id INTEGER NOT NULL REFERENCES test_results_tags(id),
        PRIMARY KEY (test_run_id, tag_id)
    )
    """)

    # Scenarios table
    op.execute("""
    CREATE TABLE scenarios (
        id SERIAL PRIMARY KEY,
        test_run_id INTEGER NOT NULL REFERENCES test_runs(id),
        feature_id INTEGER REFERENCES features(id),
        name VARCHAR(255) NOT NULL,
        description TEXT,
        status teststatus NOT NULL,
        start_time TIMESTAMP,
        end_time TIMESTAMP,
        duration FLOAT,
        error_message TEXT,
        stack_trace TEXT,
        parameters JSONB,
        meta_data JSONB,
        created_at TIMESTAMP NOT NULL DEFAULT NOW(),
        updated_at TIMESTAMP NOT NULL DEFAULT NOW()
    )
    """)

    # Steps table
    op.execute("""
    CREATE TABLE steps (
        id SERIAL PRIMARY KEY,
        scenario_id INTEGER NOT NULL REFERENCES scenarios(id),
        name VARCHAR(255) NOT NULL,
        description TEXT,
        status teststatus NOT NULL,
        start_time TIMESTAMP,
        end_time TIMESTAMP,
        duration FLOAT,
        error_message TEXT,
        stack_trace TEXT,
        screenshot_url VARCHAR(255),
        log_output TEXT,
        "order" INTEGER NOT NULL,
        created_at TIMESTAMP NOT NULL DEFAULT NOW(),
        updated_at TIMESTAMP NOT NULL DEFAULT NOW()
    )
    """)

    # Text Chunks table
    op.execute("""
    CREATE TABLE text_chunks (
        id SERIAL PRIMARY KEY,
        text TEXT NOT NULL,
        document_id VARCHAR(255) NOT NULL,
        document_type VARCHAR(50) NOT NULL,
        chunk_index INTEGER NOT NULL,
        meta_data JSONB,
        quadrant_vector_id VARCHAR(255),
        created_at TIMESTAMP NOT NULL DEFAULT NOW(),
        updated_at TIMESTAMP NOT NULL DEFAULT NOW()
    )
    """)

    # Health Metrics table
    op.execute("""
    CREATE TABLE health_metrics (
        id SERIAL PRIMARY KEY,
        project_id INTEGER NOT NULL REFERENCES projects(id),
        build_id INTEGER REFERENCES build_infos(id),
        metric_name VARCHAR(100) NOT NULL,
        metric_value FLOAT NOT NULL,
        threshold FLOAT,
        status VARCHAR(50),
        timestamp TIMESTAMP NOT NULL DEFAULT NOW(),
        meta_data JSONB,
        created_at TIMESTAMP NOT NULL DEFAULT NOW()
    )
    """)

    # Build Metrics table
    op.execute("""
    CREATE TABLE build_metrics (
        id SERIAL PRIMARY KEY,
        build_id INTEGER NOT NULL REFERENCES build_infos(id),
        metric_name VARCHAR(100) NOT NULL,
        metric_value FLOAT NOT NULL,
        timestamp TIMESTAMP NOT NULL DEFAULT NOW(),
        meta_data JSONB,
        created_at TIMESTAMP NOT NULL DEFAULT NOW()
    )
    """)

    # Report Templates table
    op.execute("""
    CREATE TABLE report_templates (
        id SERIAL PRIMARY KEY,
        name VARCHAR(255) NOT NULL,
        description TEXT,
        report_type reporttype NOT NULL,
        format reportformat NOT NULL,
        template_data JSONB NOT NULL,
        created_by VARCHAR(100),
        created_at TIMESTAMP NOT NULL DEFAULT NOW(),
        updated_at TIMESTAMP NOT NULL DEFAULT NOW()
    )
    """)

    # Report Schedules table
    op.execute("""
    CREATE TABLE report_schedules (
        id SERIAL PRIMARY KEY,
        template_id INTEGER NOT NULL REFERENCES report_templates(id),
        name VARCHAR(255) NOT NULL,
        description TEXT,
        cron_expression VARCHAR(100) NOT NULL,
        enabled BOOLEAN NOT NULL DEFAULT TRUE,
        parameters JSONB,
        recipients VARCHAR[],
        created_at TIMESTAMP NOT NULL DEFAULT NOW(),
        updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
        last_run TIMESTAMP,
        next_run TIMESTAMP
    )
    """)

    # Reports table
    op.execute("""
    CREATE TABLE reports (
        id SERIAL PRIMARY KEY,
        template_id INTEGER NOT NULL REFERENCES report_templates(id),
        name VARCHAR(255) NOT NULL,
        description TEXT,
        status reportstatus NOT NULL DEFAULT 'PENDING',
        format reportformat NOT NULL,
        generated_at TIMESTAMP,
        file_path VARCHAR(255),
        file_size INTEGER,
        parameters JSONB,
        error_message TEXT,
        created_at TIMESTAMP NOT NULL DEFAULT NOW(),
        updated_at TIMESTAMP NOT NULL DEFAULT NOW()
    )
    """)

    # Search Queries table
    op.execute("""
    CREATE TABLE search_queries (
        id SERIAL PRIMARY KEY,
        query_text VARCHAR(255) NOT NULL,
        filters JSONB,
        result_count INTEGER,
        user_id VARCHAR(100),
        session_id VARCHAR(100),
        timestamp TIMESTAMP NOT NULL DEFAULT NOW(),
        duration FLOAT,
        created_at TIMESTAMP NOT NULL DEFAULT NOW()
    )
    """)

    # Analysis Requests table
    op.execute("""
    CREATE TABLE analysis_requests (
        id SERIAL PRIMARY KEY,
        request_type VARCHAR(100) NOT NULL,
        parameters JSONB NOT NULL,
        status VARCHAR(50) NOT NULL DEFAULT 'PENDING',
        user_id VARCHAR(100),
        created_at TIMESTAMP NOT NULL DEFAULT NOW(),
        updated_at TIMESTAMP NOT NULL DEFAULT NOW()
    )
    """)

    # Analysis Results table
    op.execute("""
    CREATE TABLE analysis_results (
        id SERIAL PRIMARY KEY,
        request_id INTEGER NOT NULL REFERENCES analysis_requests(id),
        result_data JSONB NOT NULL,
        summary TEXT,
        created_at TIMESTAMP NOT NULL DEFAULT NOW()
    )
    """)

    # Create indexes for performance
    op.execute("CREATE INDEX idx_projects_name ON projects (name)")
    op.execute("CREATE INDEX idx_test_runs_project_id ON test_runs (project_id)")
    op.execute("CREATE INDEX idx_test_runs_build_id ON test_runs (build_id)")
    op.execute("CREATE INDEX idx_test_runs_status ON test_runs (status)")
    op.execute("CREATE INDEX idx_test_runs_start_time ON test_runs (start_time)")
    op.execute("CREATE INDEX idx_scenarios_test_run_id ON scenarios (test_run_id)")
    op.execute("CREATE INDEX idx_scenarios_feature_id ON scenarios (feature_id)")
    op.execute("CREATE INDEX idx_scenarios_status ON scenarios (status)")
    op.execute("CREATE INDEX idx_steps_scenario_id ON steps (scenario_id)")
    op.execute("CREATE INDEX idx_steps_status ON steps (status)")
    op.execute("CREATE INDEX idx_features_project_id ON features (project_id)")
    op.execute("CREATE INDEX idx_build_infos_project_id ON build_infos (project_id)")
    op.execute("CREATE INDEX idx_build_infos_build_number ON build_infos (build_number)")
    op.execute("CREATE INDEX idx_health_metrics_project_id ON health_metrics (project_id)")
    op.execute("CREATE INDEX idx_health_metrics_build_id ON health_metrics (build_id)")
    op.execute("CREATE INDEX idx_build_metrics_build_id ON build_metrics (build_id)")
    op.execute("CREATE INDEX idx_report_templates_name ON report_templates (name)")
    op.execute("CREATE INDEX idx_reports_template_id ON reports (template_id)")
    op.execute("CREATE INDEX idx_reports_status ON reports (status)")
    op.execute("CREATE INDEX idx_report_schedules_template_id ON report_schedules (template_id)")
    op.execute("CREATE INDEX idx_text_chunks_document_id ON text_chunks (document_id)")


def downgrade():
    # Drop indexes
    op.execute("DROP INDEX IF EXISTS idx_text_chunks_document_id")
    op.execute("DROP INDEX IF EXISTS idx_report_schedules_template_id")
    op.execute("DROP INDEX IF EXISTS idx_reports_status")
    op.execute("DROP INDEX IF EXISTS idx_reports_template_id")
    op.execute("DROP INDEX IF EXISTS idx_report_templates_name")
    op.execute("DROP INDEX IF EXISTS idx_build_metrics_build_id")
    op.execute("DROP INDEX IF EXISTS idx_health_metrics_build_id")
    op.execute("DROP INDEX IF EXISTS idx_health_metrics_project_id")
    op.execute("DROP INDEX IF EXISTS idx_build_infos_build_number")
    op.execute("DROP INDEX IF EXISTS idx_build_infos_project_id")
    op.execute("DROP INDEX IF EXISTS idx_features_project_id")
    op.execute("DROP INDEX IF EXISTS idx_steps_status")
    op.execute("DROP INDEX IF EXISTS idx_steps_scenario_id")
    op.execute("DROP INDEX IF EXISTS idx_scenarios_status")
    op.execute("DROP INDEX IF EXISTS idx_scenarios_feature_id")
    op.execute("DROP INDEX IF EXISTS idx_scenarios_test_run_id")
    op.execute("DROP INDEX IF EXISTS idx_test_runs_start_time")
    op.execute("DROP INDEX IF EXISTS idx_test_runs_status")
    op.execute("DROP INDEX IF EXISTS idx_test_runs_build_id")
    op.execute("DROP INDEX IF EXISTS idx_test_runs_project_id")
    op.execute("DROP INDEX IF EXISTS idx_projects_name")

    # Drop tables in reverse order of creation
    op.execute("DROP TABLE IF EXISTS analysis_results")
    op.execute("DROP TABLE IF EXISTS analysis_requests")
    op.execute("DROP TABLE IF EXISTS search_queries")
    op.execute("DROP TABLE IF EXISTS reports")
    op.execute("DROP TABLE IF EXISTS report_schedules")
    op.execute("DROP TABLE IF EXISTS report_templates")
    op.execute("DROP TABLE IF EXISTS build_metrics")
    op.execute("DROP TABLE IF EXISTS health_metrics")
    op.execute("DROP TABLE IF EXISTS text_chunks")
    op.execute("DROP TABLE IF EXISTS steps")
    op.execute("DROP TABLE IF EXISTS scenarios")
    op.execute("DROP TABLE IF EXISTS test_run_tags")
    op.execute("DROP TABLE IF EXISTS test_runs")
    op.execute("DROP TABLE IF EXISTS test_results_tags")
    op.execute("DROP TABLE IF EXISTS features")
    op.execute("DROP TABLE IF EXISTS build_infos")
    op.execute("DROP TABLE IF EXISTS test_cases")
    op.execute("DROP TABLE IF EXISTS test_reports")
    op.execute("DROP TABLE IF EXISTS projects")

    # Drop enum types
    op.execute("DROP TYPE IF EXISTS reporttype")
    op.execute("DROP TYPE IF EXISTS reportstatus")
    op.execute("DROP TYPE IF EXISTS reportformat")
    op.execute("DROP TYPE IF EXISTS teststatus")