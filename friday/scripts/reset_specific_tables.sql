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
    BEGIN
        EXECUTE 'SELECT setval(pg_get_serial_sequence(''' || table_name || ''', ''id''), 1, false);';
    EXCEPTION
        WHEN OTHERS THEN
            RAISE NOTICE 'No sequence found for table %', table_name;
    END;

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

-- 3. Reset all test data for a specific project
BEGIN;
    SET session_replication_role = 'replica';
    -- Replace X with the project_id you want to reset
    DELETE FROM test_runs WHERE project_id = X;
    DELETE FROM features WHERE project_id = X;
    DELETE FROM build_infos WHERE project_id = X;
    DELETE FROM health_metrics WHERE project_id = X;
    SET session_replication_role = 'origin';
COMMIT;

-- 4. Reset only failed test runs
BEGIN;
    SET session_replication_role = 'replica';
    DELETE FROM test_runs WHERE status = 'FAILED';
    SET session_replication_role = 'origin';
COMMIT;

-- 5. Reset all test runs older than a specific date
BEGIN;
    SET session_replication_role = 'replica';
    -- Replace 'YYYY-MM-DD' with the cutoff date
    DELETE FROM test_runs WHERE start_time < 'YYYY-MM-DD'::date;
    SET session_replication_role = 'origin';
COMMIT;

-- Note: These are example transactions. In practice, you would:
-- 1. Comment out all but the transaction you want to run
-- 2. Modify the specific values (like project_id or date) as needed
-- 3. Review the transaction before running it
-- 4. Consider taking a backup before running destructive operations