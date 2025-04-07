-- Script to completely drop and recreate the schema
-- WARNING: This will delete all data and schema objects

-- Drop all tables
DROP TABLE IF EXISTS
    analysis_results,
    analysis_requests,
    search_queries,
    reports,
    report_schedules,
    report_templates,
    build_metrics,
    health_metrics,
    text_chunks,
    steps,
    scenarios,
    test_run_tags,
    test_runs,
    test_results_tags,
    features,
    build_infos,
    projects
CASCADE;

-- Drop enum types
DROP TYPE IF EXISTS report_type;
DROP TYPE IF EXISTS report_status;
DROP TYPE IF EXISTS report_format;
DROP TYPE IF EXISTS test_status;

-- Drop extensions if needed
-- DROP EXTENSION IF EXISTS vector;

-- Recreate extensions
CREATE EXTENSION IF NOT EXISTS vector;

-- Reset sequences (if not automatically dropped with tables)
SELECT pg_catalog.setval(pg_get_serial_sequence('information_schema.sequences', 'sequence_catalog'), 1, false);

-- The tables and other schema objects will be recreated by running the Alembic migrations:
-- Run this script, then execute: alembic upgrade head

-- Note: If you just want to recreate the entire database (including the database itself),
-- you might prefer to use the invoke task instead:
-- invoke db-reset