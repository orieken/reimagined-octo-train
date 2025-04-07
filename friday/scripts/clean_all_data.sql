-- script_1_clean_all_data.sql
-- Script to remove all data while preserving the schema
-- This script truncates all tables in the correct order to maintain referential integrity

-- Disable foreign key constraints temporarily
SET session_replication_role = 'replica';

-- Truncate tables in reverse dependency order
TRUNCATE TABLE
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

-- Re-enable foreign key constraints
SET session_replication_role = 'origin';

-- Reset sequences
SELECT setval(pg_get_serial_sequence('projects', 'id'), 1, false);
SELECT setval(pg_get_serial_sequence('build_infos', 'id'), 1, false);
SELECT setval(pg_get_serial_sequence('features', 'id'), 1, false);
SELECT setval(pg_get_serial_sequence('test_results_tags', 'id'), 1, false);
SELECT setval(pg_get_serial_sequence('test_runs', 'id'), 1, false);
SELECT setval(pg_get_serial_sequence('scenarios', 'id'), 1, false);
SELECT setval(pg_get_serial_sequence('steps', 'id'), 1, false);
SELECT setval(pg_get_serial_sequence('text_chunks', 'id'), 1, false);
SELECT setval(pg_get_serial_sequence('health_metrics', 'id'), 1, false);
SELECT setval(pg_get_serial_sequence('build_metrics', 'id'), 1, false);
SELECT setval(pg_get_serial_sequence('report_templates', 'id'), 1, false);
SELECT setval(pg_get_serial_sequence('report_schedules', 'id'), 1, false);
SELECT setval(pg_get_serial_sequence('reports', 'id'), 1, false);
SELECT setval(pg_get_serial_sequence('search_queries', 'id'), 1, false);
SELECT setval(pg_get_serial_sequence('analysis_requests', 'id'), 1, false);
SELECT setval(pg_get_serial_sequence('analysis_results', 'id'), 1, false);

-- script_2_drop_and_recreate.sql
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

-- script_3_reset_specific_tables.sql
-- Script to reset only specific tables while maintaining relationships
-- Example for resetting test results without affecting project data

-- Define function to reset a table and its dependent tables
CREATE OR REPLACE FUNCTION reset_table_cascade(table_name text) RETURNS void AS $$
DECLARE
    child record;
BEGIN
    -- First find all tables that depend on this one via foreign keys
    FOR child IN
        SELECT c.relname AS child_table
        FROM pg_constraint fk
        JOIN pg_class c ON fk.conrelid = c.oid
        JOIN pg_class p ON fk.confrelid = p.oid
        WHERE p.relname = table_name
        AND fk.contype = 'f'
    LOOP
        -- Recursively reset child tables first
        PERFORM reset_table_cascade(child.child_table);
    END LOOP;

    -- Then truncate this table
    EXECUTE 'TRUNCATE TABLE ' || table_name || ' CASCADE';

    -- Reset the sequence if it exists
    EXECUTE 'SELECT setval(pg_get_serial_sequence(''' || table_name || ''', ''id''), 1, false);';

    RAISE NOTICE 'Reset table: %', table_name;
END;
$$ LANGUAGE plpgsql;

-- Usage examples:

-- 1. Reset only test results but keep projects, features, builds
BEGIN;
    SET session_replication_role = 'replica'; -- Disable FK constraints
    SELECT reset_table_cascade('test_runs');
    SET session_replication_role = 'origin'; -- Re-enable FK constraints
COMMIT;

-- 2. Reset analysis and reports but keep test data
BEGIN;
    SET session_replication_role = 'replica';
    SELECT reset_table_cascade('analysis_requests');
    SELECT reset_table_cascade('reports');
    SELECT reset_table_cascade('report_schedules');
    SET session_replication_role = 'origin';
COMMIT;

-- script_4_reset_test_runs_by_date.sql
-- Script to reset test runs older than a specified date

BEGIN;
    -- Disable foreign key constraints temporarily
    SET session_replication_role = 'replica';

    -- Delete steps belonging to scenarios in old test runs
    DELETE FROM steps
    WHERE scenario_id IN (
        SELECT id FROM scenarios
        WHERE test_run_id IN (
            SELECT id FROM test_runs
            WHERE created_at < :cutoff_date
        )
    );

    -- Delete scenarios from old test runs
    DELETE FROM scenarios
    WHERE test_run_id IN (
        SELECT id FROM test_runs
        WHERE created_at < :cutoff_date
    );

    -- Delete test run tag associations
    DELETE FROM test_run_tags
    WHERE test_run_id IN (
        SELECT id FROM test_runs
        WHERE created_at < :cutoff_date
    );

    -- Delete old test runs
    DELETE FROM test_runs WHERE created_at < :cutoff_date;

    -- Re-enable foreign key constraints
    SET session_replication_role = 'origin';
COMMIT;