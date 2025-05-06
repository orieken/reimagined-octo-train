#!/usr/bin/env python
"""
Test data generator for Friday Service database.

This script populates the database with sample data for development and testing purposes.
"""
import argparse
import datetime
import logging
import random
import string
import sys
from typing import Dict, List, Any

import sqlalchemy as sa
from sqlalchemy.orm import Session

from app.database.session import SessionLocal, engine
from app.models import (
    Project, TestRun, Scenario, Step, Feature, BuildInfo,
    TestStatus, HealthMetric, BuildMetric, TestResultsTag,
    ReportTemplate, ReportSchedule, Report, ReportFormat, ReportStatus, ReportType
)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("friday.test_data")

# Scale configuration
SCALE_CONFIG = {
    "small": {
        "projects": 2,
        "features_per_project": 5,
        "builds_per_project": 10,
        "test_runs_per_build": 2,
        "scenarios_per_test_run": 10,
        "steps_per_scenario": 5,
        "tags": 5,
        "report_templates": 3,
        "report_schedules": 2,
        "reports": 5
    },
    "medium": {
        "projects": 5,
        "features_per_project": 10,
        "builds_per_project": 20,
        "test_runs_per_build": 3,
        "scenarios_per_test_run": 20,
        "steps_per_scenario": 8,
        "tags": 10,
        "report_templates": 5,
        "report_schedules": 5,
        "reports": 15
    },
    "large": {
        "projects": 10,
        "features_per_project": 20,
        "builds_per_project": 50,
        "test_runs_per_build": 5,
        "scenarios_per_test_run": 30,
        "steps_per_scenario": 10,
        "tags": 20,
        "report_templates": 10,
        "report_schedules": 10,
        "reports": 30
    }
}


def random_date(start_date, end_date):
    """Generate a random date between start_date and end_date."""
    delta = end_date - start_date
    random_days = random.randrange(delta.days)
    return start_date + datetime.timedelta(days=random_days)


def random_string(length=10):
    """Generate a random string of fixed length."""
    letters = string.ascii_letters
    return ''.join(random.choice(letters) for _ in range(length))


def random_status():
    """Generate a random test status with weighted probabilities."""
    statuses = [
        (TestStatus.PASSED, 0.7),  # 70% chance of PASSED
        (TestStatus.FAILED, 0.2),  # 20% chance of FAILED
        (TestStatus.SKIPPED, 0.05),  # 5% chance of SKIPPED
        (TestStatus.ERROR, 0.05)  # 5% chance of ERROR
    ]
    return random.choices([s[0] for s in statuses], weights=[s[1] for s in statuses], k=1)[0]


def generate_project(db: Session) -> Project:
    """Generate a random project."""
    name = f"Project-{random_string(5)}"
    project = Project(
        name=name,
        description=f"Description for {name}",
        repository_url=f"https://github.com/example/{name.lower()}",
        active=random.choice([True, True, True, False]),  # 75% chance of being active
        metadata={"team": random.choice(["Alpha", "Beta", "Gamma", "Delta"]),
                  "priority": random.choice(["High", "Medium", "Low"])}
    )
    db.add(project)
    db.commit()
    logger.info(f"Created project: {project.name}")
    return project


def generate_features(db: Session, project: Project, count: int) -> List[Feature]:
    """Generate random features for a project."""
    features = []
    for i in range(count):
        name = f"Feature-{random_string(8)}"
        feature = Feature(
            project_id=project.id,
            name=name,
            description=f"Description for feature {name}",
            file_path=f"features/{name.lower().replace(' ', '_')}.feature",
            tags=random.sample(["web", "api", "mobile", "performance", "security", "accessibility"],
                               k=random.randint(1, 3)),
            priority=random.choice(["P0", "P1", "P2", "P3"]),
            status=random.choice(["Active", "In Development", "Deprecated"])
        )
        db.add(feature)
        features.append(feature)

    db.commit()
    logger.info(f"Created {len(features)} features for project: {project.name}")
    return features


def generate_build_info(db: Session, project: Project, count: int) -> List[BuildInfo]:
    """Generate random build information for a project."""
    builds = []
    start_date = datetime.datetime.now() - datetime.timedelta(days=90)
    end_date = datetime.datetime.now()

    for i in range(count):
        build_number = f"{project.id}.{i + 1}"
        start_time = random_date(start_date, end_date)
        duration = random.randint(300, 3600)  # 5 minutes to 1 hour
        end_time = start_time + datetime.timedelta(seconds=duration)

        build = BuildInfo(
            project_id=project.id,
            build_number=build_number,
            name=f"Build {build_number}",
            status=random.choice(["Success", "Failed", "Aborted", "Running"]),
            start_time=start_time,
            end_time=end_time,
            duration=duration,
            branch=random.choice(["main", "develop", "feature/new-feature", "hotfix/bug-fix"]),
            commit_hash=''.join(random.choice(string.hexdigits) for _ in range(40)),
            commit_message=f"Commit message for build {build_number}",
            author=f"{random_string(5)}@example.com",
            ci_url=f"https://ci.example.com/builds/{build_number}",
            artifacts_url=f"https://artifacts.example.com/{build_number}",
            environment=random.choice(["dev", "staging", "production"]),
            metadata={"node": f"builder-{random.randint(1, 10)}",
                      "triggered_by": random.choice(["scheduler", "manual", "webhook"])}
        )
        db.add(build)
        builds.append(build)

        # Add build metrics
        for metric_name in ["cpu_usage", "memory_usage", "disk_usage", "network_io"]:
            metric = BuildMetric(
                build_id=build.id,
                metric_name=metric_name,
                metric_value=random.uniform(0.1, 99.9),
                timestamp=start_time + datetime.timedelta(seconds=random.randint(0, duration))
            )
            db.add(metric)

    db.commit()
    logger.info(f"Created {len(builds)} builds for project: {project.name}")
    return builds


def generate_test_tags(db: Session, count: int) -> List[TestResultsTag]:
    """Generate random test result tags."""
    tags = []
    tag_names = [
        "smoke", "regression", "performance", "security", "ui", "api",
        "integration", "unit", "e2e", "accessibility", "mobile", "desktop",
        "critical", "flaky", "slow", "blocked", "automated", "manual",
        "needs-review", "needs-fixing"
    ]

    # Ensure we don't try to create more tags than available names
    count = min(count, len(tag_names))
    selected_names = random.sample(tag_names, count)

    for name in selected_names:
        tag = TestResultsTag(
            name=name,
            description=f"Tag for {name} tests",
            color=f"#{random.randint(0, 0xFFFFFF):06x}"  # Random hex color
        )
        db.add(tag)
        tags.append(tag)

    db.commit()
    logger.info(f"Created {len(tags)} test tags")
    return tags


def generate_test_runs(db: Session, project: Project, builds: List[BuildInfo], features: List[Feature],
                       tags: List[TestResultsTag], config: Dict[str, Any]) -> List[TestRun]:
    """Generate random test runs with scenarios and steps."""
    test_runs = []

    for build in builds:
        for i in range(config["test_runs_per_build"]):
            # Calculate test counts
            total_scenarios = config["scenarios_per_test_run"]
            passed_count = int(total_scenarios * 0.7)  # 70% pass rate
            failed_count = int(total_scenarios * 0.2)  # 20% fail rate
            skipped_count = total_scenarios - passed_count - failed_count  # Remaining are skipped

            # Create test run
            test_run = TestRun(
                project_id=project.id,
                build_id=build.id,
                name=f"Test Run {project.id}.{build.id}.{i + 1}",
                description=f"Test run for build {build.build_number}",
                status=TestStatus.COMPLETED,
                start_time=build.start_time + datetime.timedelta(seconds=random.randint(0, 300)),
                end_time=build.end_time - datetime.timedelta(seconds=random.randint(0, 300)),
                total_tests=total_scenarios,
                passed_tests=passed_count,
                failed_tests=failed_count,
                skipped_tests=skipped_count,
                success_rate=(passed_count / total_scenarios) * 100 if total_scenarios > 0 else 0,
                environment=build.environment,
                branch=build.branch,
                commit_hash=build.commit_hash
            )
            db.add(test_run)
            db.flush()  # Get ID without full commit

            # Add random tags to test run
            selected_tags = random.sample(tags, min(random.randint(1, 3), len(tags)))
            test_run.tags.extend(selected_tags)

            # Generate scenarios
            generate_scenarios(db, test_run, features, config)

            test_runs.append(test_run)

    db.commit()
    logger.info(f"Created {len(test_runs)} test runs for project: {project.name}")
    return test_runs


def generate_scenarios(db: Session, test_run: TestRun, features: List[Feature], config: Dict[str, Any]) -> None:
    """Generate random scenarios for a test run."""
    for i in range(config["scenarios_per_test_run"]):
        # Pick a status based on the test run stats to ensure they match
        status_choices = (
                [TestStatus.PASSED] * test_run.passed_tests +
                [TestStatus.FAILED] * test_run.failed_tests +
                [TestStatus.SKIPPED] * test_run.skipped_tests
        )
        status = status_choices[i] if i < len(status_choices) else random_status()

        # Calculate duration
        duration = random.uniform(0.1, 30.0) if status != TestStatus.SKIPPED else 0

        # Create scenario
        scenario = Scenario(
            test_run_id=test_run.id,
            feature_id=random.choice(features).id if features else None,
            name=f"Scenario {i + 1}",
            description=f"Test scenario {i + 1} for test run {test_run.id}",
            status=status,
            start_time=test_run.start_time + datetime.timedelta(seconds=random.randint(0, 60)),
            end_time=(test_run.start_time + datetime.timedelta(
                seconds=random.randint(60, 600))) if status != TestStatus.SKIPPED else None,
            duration=duration,
            error_message="Error occurred during test execution" if status == TestStatus.FAILED else None,
            stack_trace="Traceback: Error at line 42..." if status == TestStatus.FAILED else None,
            parameters={"param1": "value1", "param2": "value2"} if random.random() > 0.5 else None
        )
        db.add(scenario)
        db.flush()  # Get ID without full commit

        # Generate steps
        generate_steps(db, scenario, config["steps_per_scenario"])


def generate_steps(db: Session, scenario: Scenario, count: int) -> None:
    """Generate random steps for a scenario."""
    for i in range(count):
        # For failed scenarios, make the last step fail
        if scenario.status == TestStatus.FAILED and i == count - 1:
            status = TestStatus.FAILED
        # For skipped scenarios, make all steps skipped
        elif scenario.status == TestStatus.SKIPPED:
            status = TestStatus.SKIPPED
        # Otherwise use the scenario status or generate a random one
        else:
            status = scenario.status if scenario.status != TestStatus.FAILED else TestStatus.PASSED

        # Calculate duration
        duration = random.uniform(0.05, 5.0) if status != TestStatus.SKIPPED else 0

        step = Step(
            scenario_id=scenario.id,
            name=f"Step {i + 1}",
            description=f"Test step {i + 1} for scenario {scenario.id}",
            status=status,
            start_time=scenario.start_time + datetime.timedelta(seconds=i) if scenario.start_time else None,
            end_time=scenario.start_time + datetime.timedelta(seconds=i + duration) if scenario.start_time else None,
            duration=duration,
            error_message="Step execution failed" if status == TestStatus.FAILED else None,
            stack_trace="Traceback: Error in step..." if status == TestStatus.FAILED else None,
            screenshot_url=f"https://screenshots.example.com/step_{scenario.id}_{i}" if random.random() > 0.7 else None,
            log_output="Step log output..." if random.random() > 0.5 else None,
            order=i + 1
        )
        db.add(step)


def generate_health_metrics(db: Session, project: Project, builds: List[BuildInfo]) -> None:
    """Generate random health metrics for a project and its builds."""
    metric_names = ["test_pass_rate", "code_coverage", "build_success_rate", "test_execution_time", "flaky_test_rate"]

    for metric_name in metric_names:
        # Project-level metrics
        project_metric = HealthMetric(
            project_id=project.id,
            metric_name=metric_name,
            metric_value=random.uniform(50.0, 99.9),
            threshold=75.0,
            status="HEALTHY" if random.random() > 0.2 else "UNHEALTHY"
        )
        db.add(project_metric)

        # Build-level metrics (for a few random builds)
        for build in random.sample(builds, min(3, len(builds))):
            build_metric = HealthMetric(
                project_id=project.id,
                build_id=build.id,
                metric_name=metric_name,
                metric_value=random.uniform(50.0, 99.9),
                threshold=75.0,
                status="HEALTHY" if random.random() > 0.2 else "UNHEALTHY"
            )
            db.add(build_metric)

    db.commit()
    logger.info(f"Created health metrics for project: {project.name}")


def generate_report_templates(db: Session, count: int) -> List[ReportTemplate]:
    """Generate random report templates."""
    templates = []

    for i in range(count):
        report_type = random.choice(list(ReportType))
        format = random.choice(list(ReportFormat))

        template = ReportTemplate(
            name=f"Template-{report_type.value}-{i}",
            description=f"Report template for {report_type.value} reports",
            report_type=report_type,
            format=format,
            template_data={
                "sections": ["summary", "details", "trends"],
                "charts": ["bar", "line", "pie"],
                "filters": {"project": True, "dateRange": True}
            },
            created_by="admin"
        )
        db.add(template)
        templates.append(template)

    db.commit()
    logger.info(f"Created {len(templates)} report templates")
    return templates


def generate_report_schedules(db: Session, templates: List[ReportTemplate], count: int) -> None:
    """Generate random report schedules."""
    cron_expressions = [
        "0 9 * * 1",  # Monday at 9 AM
        "0 9 * * 1-5",  # Weekdays at 9 AM
        "0 0 * * 0",  # Sunday at midnight
        "0 0 1 * *",  # 1st of month at midnight
        "0 12 * * *",  # Every day at noon
    ]

    for i in range(min(count, len(templates))):
        template = templates[i]
        schedule = ReportSchedule(
            template_id=template.id,
            name=f"Schedule-{template.name}",
            description=f"Schedule for {template.name}",
            cron_expression=random.choice(cron_expressions),
            enabled=random.choice([True, True, False]),  # 66% chance of being enabled
            parameters={"lookback": "7d", "projects": ["all"]},
            recipients=["user1@example.com", "user2@example.com"],
            last_run=datetime.datetime.now() - datetime.timedelta(days=random.randint(1, 10)),
            next_run=datetime.datetime.now() + datetime.timedelta(days=random.randint(1, 10))
        )
        db.add(schedule)

    db.commit()
    logger.info(f"Created {count} report schedules")


def generate_reports(db: Session, templates: List[ReportTemplate], count: int) -> None:
    """Generate random reports."""
    for i in range(count):
        template = random.choice(templates)
        status = random.choice(list(ReportStatus))
        generated_at = datetime.datetime.now() - datetime.timedelta(
            days=random.randint(0, 30)) if status != ReportStatus.PENDING else None

        report = Report(
            template_id=template.id,
            name=f"Report-{template.report_type.value}-{i}",
            description=f"Generated report using {template.name}",
            status=status,
            format=template.format,
            generated_at=generated_at,
            file_path=f"/reports/{template.name}_{i}.{template.format.value.lower()}" if status == ReportStatus.COMPLETED else None,
            file_size=random.randint(10000, 1000000) if status == ReportStatus.COMPLETED else None,
            parameters={"startDate": "2023-01-01", "endDate": "2023-12-31"},
            error_message="Failed to generate report" if status == ReportStatus.FAILED else None
        )
        db.add(report)

    db.commit()
    logger.info(f"Created {count} reports")


def generate_test_data(db: Session, scale: str) -> None:
    """Generate all test data based on the specified scale."""
    config = SCALE_CONFIG[scale]
    logger.info(f"Generating {scale} scale test data...")

    # Generate test tags (shared across projects)
    tags = generate_test_tags(db, config["tags"])

    # Generate report templates (shared across projects)
    templates = generate_report_templates(db, config["report_templates"])

    # Generate report schedules
    generate_report_schedules(db, templates, config["report_schedules"])

    # Generate reports
    generate_reports(db, templates, config["reports"])

    # Generate projects and related entities
    for i in range(config["projects"]):
        project = generate_project(db)
        features = generate_features(db, project, config["features_per_project"])
        builds = generate_build_info(db, project, config["builds_per_project"])
        test_runs = generate_test_runs(db, project, builds, features, tags, config)
        generate_health_metrics(db, project, builds)

    logger.info(f"Successfully generated {scale} scale test data")


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Generate test data for Friday Service database")
    parser.add_argument("--scale", choices=["small", "medium", "large"], default="small",
                        help="Scale of test data to generate (default: small)")
    parser.add_argument("--db-name", type=str, default="friday_service",
                        help="Database name (default: friday_service)")
    parser.add_argument("--clean", action="store_true", help="Clean existing data before generating new data")
    return parser.parse_args()


def main():
    """Main function to run the script."""
    args = parse_args()

    try:
        db = SessionLocal()

        if args.clean:
            logger.info("Cleaning existing data...")
            # Use raw SQL to disable foreign key constraints and truncate all tables
            db.execute(sa.text("SET session_replication_role = 'replica';"))

            # Truncate all tables in reverse dependency order
            tables = [
                "analysis_results", "analysis_requests", "search_queries", "reports",
                "report_schedules", "report_templates", "build_metrics", "health_metrics",
                "text_chunks", "steps", "scenarios", "test_run_tags", "test_runs",
                "test_results_tags", "features", "build_infos", "projects"
            ]

            for table in tables:
                db.execute(sa.text(f"TRUNCATE TABLE {table} CASCADE;"))

            # Reset sequences
            for table in tables:
                db.execute(sa.text(f"SELECT setval(pg_get_serial_sequence('{table}', 'id'), 1, false);"))

            # Re-enable foreign key constraints
            db.execute(sa.text("SET session_replication_role = 'origin';"))
            db.commit()
            logger.info("Data cleaning completed")

        generate_test_data(db, args.scale)
        logger.info("Test data generation completed successfully")

    except Exception as e:
        logger.error(f"Error generating test data: {e}", exc_info=True)
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()