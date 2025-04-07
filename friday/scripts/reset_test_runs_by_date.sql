-- Script to reset test runs older than a specified date
-- This script preserves the database schema while deleting test data selectively by date

-- This script uses a parameter :cutoff_date which should be passed when executing
-- For example: psql -v cutoff_date="'2025-01-01'" -f reset_test_runs_by_date.sql

-- If you're executing this directly in psql, you can set the variable like this:
-- \set cutoff_date "'2025-01-01'"

-- Check if the cutoff_date variable is defined
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_catalog.pg_namespace WHERE nspname = 'pg_temp') THEN
        RAISE EXCEPTION 'cutoff_date parameter is required. Example usage: psql -v cutoff_date="''2025-01-01''" -f reset_test_runs_by_date.sql';
    END IF;
END $$;

BEGIN;
    -- Disable foreign key constraints temporarily
    SET session_replication_role = 'replica';

    -- Output the cutoff date being used
    RAISE NOTICE 'Deleting test run data older than %', :'cutoff_date';

    -- Delete steps belonging to scenarios in old test runs
    DELETE FROM steps
    WHERE scenario_id IN (
        SELECT id FROM scenarios
        WHERE test_run_id IN (
            SELECT id FROM test_runs
            WHERE created_at < :cutoff_date::timestamp
        )
    );
    RAISE NOTICE 'Deleted steps from old test runs';

    -- Delete scenarios from old test runs
    DELETE FROM scenarios
    WHERE test_run_id IN (
        SELECT id FROM test_runs
        WHERE created_at < :cutoff_date::timestamp
    );
    RAISE NOTICE 'Deleted scenarios from old test runs';

    -- Delete test run tag associations
    DELETE FROM test_run_tags
    WHERE test_run_id IN (
        SELECT id FROM test_runs
        WHERE created_at < :cutoff_date::timestamp
    );
    RAISE NOTICE 'Deleted tag associations from old test runs';

    -- Delete health metrics associated with old test runs
    DELETE FROM health_metrics
    WHERE build_id IN (
        SELECT build_id FROM test_runs
        WHERE created_at < :cutoff_date::timestamp
        AND build_id IS NOT NULL
    );
    RAISE NOTICE 'Deleted health metrics from old test runs';

    -- Delete old test runs
    DELETE FROM test_runs WHERE created_at < :cutoff_date::timestamp;
    RAISE NOTICE 'Deleted old test runs';

    -- Re-enable foreign key constraints
    SET session_replication_role = 'origin';

    -- Output the number of remaining test runs
    SELECT count(*) AS remaining_test_runs FROM test_runs;
COMMIT;

-- Note: This script is designed to be executed with a specific cutoff date
-- If you're using the invoke tasks, you can use db-clean with a custom script:
-- invoke db-clean-custom --script=reset_test_runs_by_date.sql --params="cutoff_date='2025-01-01'"