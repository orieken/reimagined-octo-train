#!/usr/bin/env python3
"""Friday CLI - Phase 2 Feature Testing

This module enhances the Friday CLI with commands to test Phase 2 features:
- Posting test data to Friday Service
- Subscribing to notifications via WebSocket
- Managing webhook subscriptions
- Viewing analytics data
- Generating and posting Cucumber test reports
- Generating and posting Build Info
"""

import argparse
import json
import os
import sys
import time
import uuid
import websocket
import requests
from datetime import datetime, timedelta
from tabulate import tabulate
import threading
import random

# Import the Cucumber Report Generator
from cucumber_generator import CucumberReportGenerator
from document_generator import DocumentGenerator, DOCUMENT_FORMATS, DOCUMENT_TYPES, TEAMS

# Configuration
BASE_URL = os.environ.get("FRIDAY_API_URL", "http://localhost:4000/api/v1")
API_KEY = os.environ.get("FRIDAY_API_KEY", "whoops")

# Constants for build info generation
CI_AGENTS = ["jenkins", "github-actions", "gitlab-ci", "azure-pipelines", "circleci", "travis-ci"]
BUILD_STATUSES = ["success", "failure", "in_progress"]


# Helper functions
def get_headers():
    """Return headers with API key authentication."""
    return {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }


def handle_response(response):
    """Handle API response, pretty printing JSON and checking status."""
    try:
        response.raise_for_status()
        if response.content:
            return response.json()
        return {}
    except requests.exceptions.HTTPError as e:
        print(f"Error: {e}")
        try:
            print(json.dumps(response.json(), indent=2))
        except:
            print(response.text)
        sys.exit(1)


def generate_fake_commit_hash():
    """Generate a realistic looking git commit hash"""
    return ''.join(random.choices('0123456789abcdef', k=40))


class FridayCLI:
    def __init__(self):
        self.parser = argparse.ArgumentParser(description="Friday CLI - Feature Testing")
        self.setup_commands()

    def setup_commands(self):
        """Set up the command structure for the CLI."""
        subparsers = self.parser.add_subparsers(dest="command", help="Command to execute")

        # 1. Command to post test data
        post_parser = subparsers.add_parser("post", help="Post test data to Friday Service")
        post_parser.add_argument("--type", choices=["event", "alert", "log", "metric"], required=True,
                                 help="Type of data to post")
        post_parser.add_argument("--data", type=str, help="JSON string data to post")
        post_parser.add_argument("--file", type=str, help="JSON file path containing data to post")
        post_parser.add_argument("--count", type=int, default=1,
                                 help="Number of test records to generate if no data provided")

        # 2. Command to subscribe to WebSocket notifications
        ws_parser = subparsers.add_parser("ws", help="Subscribe to WebSocket notifications")
        ws_parser.add_argument("--channel", choices=["events", "alerts", "logs", "all"],
                               default="all", help="Channel to subscribe to")
        ws_parser.add_argument("--filter", type=str, help="JSON filter expression")
        ws_parser.add_argument("--timeout", type=int, default=60, help="Connection timeout in seconds")

        # 3. Command to manage webhook subscriptions
        webhook_parser = subparsers.add_parser("webhook", help="Manage webhook subscriptions")
        webhook_subparsers = webhook_parser.add_subparsers(dest="webhook_command", help="Webhook command")

        # Webhook list command
        webhook_list = webhook_subparsers.add_parser("list", help="List webhook subscriptions")

        # Webhook create command
        webhook_create = webhook_subparsers.add_parser("create", help="Create webhook subscription")
        webhook_create.add_argument("--url", required=True, help="Webhook callback URL")
        webhook_create.add_argument("--events", required=True, help="Comma-separated event types to subscribe to")
        webhook_create.add_argument("--secret", help="Webhook signing secret")

        # Webhook delete command
        webhook_delete = webhook_subparsers.add_parser("delete", help="Delete webhook subscription")
        webhook_delete.add_argument("--id", required=True, help="Webhook subscription ID to delete")

        # Webhook test command
        webhook_test = webhook_subparsers.add_parser("test", help="Test webhook subscription")
        webhook_test.add_argument("--id", required=True, help="Webhook subscription ID to test")

        # 4. Command to view analytics
        analytics_parser = subparsers.add_parser("analytics", help="View analytics data")
        analytics_parser.add_argument("--metric", choices=["usage", "performance", "errors", "users"],
                                      required=True, help="Analytics metric to view")
        analytics_parser.add_argument("--period", choices=["hour", "day", "week", "month"],
                                      default="day", help="Time period for analytics")
        analytics_parser.add_argument("--format", choices=["table", "json", "csv"],
                                      default="table", help="Output format")

        # 5. Command to generate and post Cucumber reports
        cucumber_parser = subparsers.add_parser("cucumber", help="Generate and post Cucumber test reports")
        cucumber_parser.add_argument("--features", type=int, default=0,
                                     help="Number of features to generate (0=random)")
        cucumber_parser.add_argument("--scenarios", type=int, default=0,
                                     help="Number of scenarios per feature (0=random)")
        cucumber_parser.add_argument("--failure-rate", type=int, default=20,
                                     help="Percentage of scenarios that should fail (0-100)")
        cucumber_parser.add_argument("--project", type=str, default="test-project",
                                     help="Project name for the test run")
        cucumber_parser.add_argument("--branch", type=str, default="main",
                                     help="Branch name for the test run")
        cucumber_parser.add_argument("--commit", type=str, default="latest",
                                     help="Commit ID for the test run")
        cucumber_parser.add_argument("--no-flaky", action="store_true",
                                     help="Disable generation of flaky tests")
        cucumber_parser.add_argument("--runs", type=int, default=1,
                                     help="Number of test runs to simulate")
        cucumber_parser.add_argument("--output", choices=["api", "stdout", "file"], default="api",
                                     help="Where to send the generated reports")
        cucumber_parser.add_argument("--file", type=str, help="Output file path when using --output=file")
        cucumber_parser.add_argument("--backdate", type=int, default=0,
                                     help="Generate reports backdated by specified number of days")
        cucumber_parser.add_argument("--interval", type=int, default=0,
                                     help="Time interval between runs in minutes (for multiple runs)")

        # 6. NEW: Command to generate and post Build Info
        build_info_parser = subparsers.add_parser("build-info", help="Generate and post build information")
        build_info_parser.add_argument("--project", required=True, help="Project name")
        build_info_parser.add_argument("--branch", default="main", help="Git branch")
        build_info_parser.add_argument("--commit", help="Git commit hash (default: random)")
        build_info_parser.add_argument("--build-number", help="Build number (default: random)")
        build_info_parser.add_argument("--status", choices=BUILD_STATUSES, help="Build status")
        build_info_parser.add_argument("--url", help="Build URL (default: generated)")
        build_info_parser.add_argument("--duration", type=int, help="Build duration in seconds")
        build_info_parser.add_argument("--agent", choices=CI_AGENTS, help="CI agent that ran the build")
        build_info_parser.add_argument("--backdate", type=int, default=0, help="Days to backdate the build info")
        build_info_parser.add_argument("--runs", type=int, default=1, help="Number of build infos to generate")
        build_info_parser.add_argument("--interval", type=int, default=240, help="Interval between builds in minutes")
        build_info_parser.add_argument("--output", choices=["api", "stdout", "file"], default="api",
                                       help="Where to send the generated build info")
        build_info_parser.add_argument("--file", type=str, help="Output file path when using --output=file")

        # 7. NEW: Command to generate and post documents
        document_parser = subparsers.add_parser("document", help="Generate and post documents")
        document_parser.add_argument("--type", choices=DOCUMENT_TYPES, help="Type of document to generate")
        document_parser.add_argument("--format", choices=DOCUMENT_FORMATS,
                                     help="Format of the document (markdown, plain_text, structured)")
        document_parser.add_argument("--project", type=str, default="test-project",
                                     help="Project name for the document")
        document_parser.add_argument("--team", choices=TEAMS, help="Team that created the document")
        document_parser.add_argument("--length", choices=["short", "medium", "long"], default="medium",
                                     help="Document length")
        document_parser.add_argument("--count", type=int, default=1,
                                     help="Number of documents to generate")
        document_parser.add_argument("--chunk-size", type=int, default=500,
                                     help="Chunk size for document processing")
        document_parser.add_argument("--chunk-overlap", type=int, default=50,
                                     help="Chunk overlap for document processing")
        document_parser.add_argument("--backdate", type=int, default=0,
                                     help="Days to backdate document creation")
        document_parser.add_argument("--output", choices=["api", "stdout", "file"], default="api",
                                     help="Where to send the generated documents")
        document_parser.add_argument("--file", type=str, help="Output file path when using --output=file")

    def run(self):
        """Parse arguments and dispatch to appropriate method."""
        args = self.parser.parse_args()

        if not args.command:
            self.parser.print_help()
            sys.exit(1)

        # Check for API key
        if not API_KEY:
            print("Error: FRIDAY_API_KEY environment variable not set")
            sys.exit(1)

        # Dispatch to appropriate command
        if args.command == "post":
            self.handle_post(args)
        elif args.command == "ws":
            self.handle_websocket(args)
        elif args.command == "webhook":
            self.handle_webhook(args)
        elif args.command == "analytics":
            self.handle_analytics(args)
        elif args.command == "cucumber":
            self.handle_cucumber(args)
        elif args.command == "build-info":
            self.handle_build_info(args)
        elif args.command == "document":
            self.handle_document(args)


    def handle_build_info(self, args):
        """Generate and post build information data."""
        base_timestamp = datetime.utcnow() - timedelta(days=args.backdate)

        for i in range(args.runs):
            # Calculate timestamp for this run
            run_timestamp = base_timestamp - timedelta(minutes=args.interval * i)

            # Allow explicit status or random selection
            status = args.status if args.status in BUILD_STATUSES else random.choice(BUILD_STATUSES)

            # Build number should increment for consecutive runs
            if args.build_number:
                build_number = str(int(args.build_number) - i)
            else:
                build_number = str(random.randint(100, 10000))

            # Generate commit hash if not provided
            commit = args.commit if args.commit else generate_fake_commit_hash()

            # Generate URL if not provided
            url = args.url
            if not url:
                url = f"https://ci.example.com/{args.project}/builds/{build_number}"

            # Generate agent if not provided
            agent = args.agent if args.agent else random.choice(CI_AGENTS)

            # Generate duration if not provided
            duration = args.duration if args.duration else random.randint(60, 1800)

            # Generate build info
            build_info = self.generate_build_info(
                project=args.project,
                branch=args.branch,
                commit=commit,
                build_number=build_number,
                status=status,
                url=url,
                duration=duration,
                agent=agent,
                timestamp=run_timestamp
            )

            # Process the build info according to output option
            if args.output == "stdout":
                print(json.dumps(build_info, indent=2))
            elif args.output == "file":
                if not args.file:
                    filename = f"build_info_{run_timestamp.strftime('%Y%m%d_%H%M%S')}.json"
                else:
                    filename = args.file

                with open(filename, 'w') as f:
                    json.dump(build_info, f, indent=2)
                print(f"Build info #{i + 1} written to {filename}")
            elif args.output == "api":
                self.post_build_info(build_info)

            # Wait between runs if multiple runs and interval is specified
            if args.runs > 1 and i < args.runs - 1:
                print(f"Waiting before generating next build info...")
                # We don't need to actually wait in this loop since we're just backdating
                # the timestamps, not waiting for real-time events

    def generate_build_info(self, project, branch, commit, build_number, status, url, duration, agent, timestamp):
        """Generate build information data."""
        build_info = {
            "id": str(uuid.uuid4()),
            "project": project,
            "branch": branch,
            "commit": commit,
            "build_number": build_number,
            "status": status,
            "url": url,
            "duration": duration,
            "agent": agent,
            "timestamp": timestamp.isoformat() + "Z",
            "metadata": {
                "runner": agent,
                "node": f"runner-{random.randint(1, 50)}",
                "triggered_by": random.choice(["push", "pull_request", "schedule", "api", "manual"]),
                "environment": random.choice(["dev", "staging", "production", "test"])
            }
        }

        # Add test summary metrics if available
        if random.random() > 0.3:  # 70% chance to include test metrics
            build_info["test_summary"] = {
                "total": random.randint(50, 500),
                "passed": 0,
                "failed": 0,
                "skipped": 0,
                "flaky": random.randint(0, 10)
            }

            # Calculate passed/failed/skipped based on status
            total_tests = build_info["test_summary"]["total"]

            if status == "success":
                # High pass rate for successful builds
                build_info["test_summary"]["passed"] = int(total_tests * random.uniform(0.95, 1.0))
                build_info["test_summary"]["skipped"] = int(total_tests * random.uniform(0, 0.03))
                build_info["test_summary"]["failed"] = total_tests - build_info["test_summary"]["passed"] - \
                                                       build_info["test_summary"]["skipped"]
            elif status == "failure":
                # Some failures for failed builds
                build_info["test_summary"]["failed"] = int(total_tests * random.uniform(0.05, 0.3))
                build_info["test_summary"]["skipped"] = int(total_tests * random.uniform(0, 0.1))
                build_info["test_summary"]["passed"] = total_tests - build_info["test_summary"]["failed"] - \
                                                       build_info["test_summary"]["skipped"]
            else:  # in_progress
                # Some tests still pending
                completed = int(total_tests * random.uniform(0.5, 0.9))
                build_info["test_summary"]["passed"] = int(completed * random.uniform(0.8, 0.98))
                build_info["test_summary"]["failed"] = completed - build_info["test_summary"]["passed"]
                build_info["test_summary"]["skipped"] = int(total_tests * random.uniform(0, 0.05))
                build_info["test_summary"]["total"] = total_tests  # Restore total count

        return build_info

    def post_build_info(self, build_info):
        """Post build information to the API."""
        endpoint = f"{BASE_URL}/processor/build-info"

        try:
            print(f"Posting build info for project: {build_info['project']}, build: {build_info['build_number']}")
            response = requests.post(endpoint, json=build_info, headers=get_headers())

            result = handle_response(response)
            print(f"Success: Build info posted successfully")
            return True
        except Exception as e:
            print(f"Error: {str(e)}")
            return False

    def handle_cucumber(self, args):
        """Generate and post Cucumber test reports."""
        # Calculate the timestamp for the report
        if args.backdate > 0:
            base_timestamp = datetime.utcnow() - timedelta(days=args.backdate)
        else:
            base_timestamp = datetime.utcnow()

        # Setup report generator
        generator = CucumberReportGenerator(
            num_features=args.features,
            num_scenarios=args.scenarios,
            failure_rate=args.failure_rate,
            project=args.project,
            branch=args.branch,
            commit=args.commit,
            flaky_tests=not args.no_flaky
        )

        # Generate multiple runs if requested
        for run in range(args.runs):
            # Calculate timestamp for this run
            if args.interval > 0 and run > 0:
                # For multiple runs with intervals, space them out
                run_timestamp = base_timestamp + timedelta(minutes=args.interval * run)
            else:
                # For single run or no interval, use base timestamp
                run_timestamp = base_timestamp

            # Generate the report
            cucumber_report = generator.generate(run_timestamp)

            # Process the report according to output option
            if args.output == "stdout":
                print(json.dumps(cucumber_report, indent=2))
            elif args.output == "file":
                if not args.file:
                    filename = f"cucumber_report_{run_timestamp.strftime('%Y%m%d_%H%M%S')}.json"
                else:
                    filename = args.file

                with open(filename, 'w') as f:
                    json.dump(cucumber_report, f, indent=2)
                print(f"Report #{run + 1} written to {filename}")
            elif args.output == "api":
                self._post_cucumber_report(cucumber_report, args.project, args.branch, args.commit, run_timestamp)

            # Wait between runs if multiple runs and interval is specified
            if args.runs > 1 and args.interval > 0 and run < args.runs - 1:
                print(f"Waiting {args.interval} minutes before next run...")
                time.sleep(args.interval * 60)  # Convert minutes to seconds

    def _post_cucumber_report(self, cucumber_report, project, branch, commit, timestamp):
        """Post a Cucumber report to the /processor/cucumber endpoint."""
        endpoint = f"{BASE_URL}/processor/cucumber"

        # Prepare report metadata
        metadata = {
            "project": project,
            "branch": branch,
            "commit": commit,
            "timestamp": timestamp.isoformat() + "Z",
            "runner": "friday-cli"
        }

        # Build the complete payload
        payload = {
            "metadata": metadata,
            "report": cucumber_report
        }

        # Post the report
        print(f"Posting Cucumber report for project: {project}, branch: {branch}, commit: {commit}")
        response = requests.post(endpoint, json=payload, headers=get_headers())

        try:
            result = handle_response(response)
            print(f"Successfully posted Cucumber report: {json.dumps(result, indent=2)}")
        except Exception as e:
            print(f"Error posting Cucumber report: {e}")
            sys.exit(1)

    def handle_post(self, args):
        """Handle posting test data to Friday Service."""
        endpoint = f"{BASE_URL}/{args.type}s"  # Note the plural form

        # Determine the data to post
        if args.data:
            try:
                data = json.loads(args.data)
                self._post_data(endpoint, data)
            except json.JSONDecodeError:
                print("Error: Invalid JSON data")
                sys.exit(1)
        elif args.file:
            try:
                with open(args.file, 'r') as f:
                    data = json.load(f)
                self._post_data(endpoint, data)
            except (json.JSONDecodeError, FileNotFoundError) as e:
                print(f"Error: {e}")
                sys.exit(1)
        else:
            # Generate and post test data
            for i in range(args.count):
                test_data = self._generate_test_data(args.type, i)
                self._post_data(endpoint, test_data)

    def _generate_test_data(self, data_type, index):
        """Generate test data based on type."""
        timestamp = datetime.utcnow().isoformat() + "Z"

        if data_type == "event":
            return {
                "id": str(uuid.uuid4()),
                "type": f"test.event.{index}",
                "timestamp": timestamp,
                "source": "friday-cli",
                "data": {
                    "message": f"Test event {index}",
                    "severity": "info",
                    "test_value": index
                }
            }
        elif data_type == "alert":
            return {
                "id": str(uuid.uuid4()),
                "title": f"Test Alert {index}",
                "description": f"This is a test alert generated by Friday CLI (#{index})",
                "severity": "low",
                "timestamp": timestamp,
                "source": "friday-cli",
                "status": "active",
                "metadata": {
                    "test_id": index,
                    "auto_generated": True
                }
            }
        elif data_type == "log":
            return {
                "timestamp": timestamp,
                "level": "info",
                "message": f"Test log message {index} from Friday CLI",
                "service": "friday-cli",
                "trace_id": str(uuid.uuid4()),
                "metadata": {
                    "test_id": index
                }
            }
        elif data_type == "metric":
            return {
                "name": "test.metric",
                "value": index,
                "type": "gauge",
                "timestamp": timestamp,
                "tags": {
                    "source": "friday-cli",
                    "test_id": str(index)
                }
            }

    def _post_data(self, endpoint, data):
        """Post data to the specified endpoint."""
        response = requests.post(endpoint, json=data, headers=get_headers())
        result = handle_response(response)
        print(f"Successfully posted data: {json.dumps(result, indent=2)}")

    def handle_websocket(self, args):
        """Handle WebSocket subscription for real-time notifications."""
        # Construct the WebSocket URL with query parameters
        ws_url = f"{BASE_URL.replace('https://', 'wss://').replace('http://', 'ws://')}/subscribe"

        if args.channel != "all":
            ws_url += f"?channel={args.channel}"

        if args.filter:
            try:
                filter_json = json.loads(args.filter)
                params = f"filter={json.dumps(filter_json)}"
                ws_url += "&" + params if "?" in ws_url else "?" + params
            except json.JSONDecodeError:
                print("Error: Invalid JSON filter")
                sys.exit(1)

        # Setup WebSocket connection
        ws = websocket.WebSocketApp(
            ws_url,
            header=[f"Authorization: Bearer {API_KEY}"],
            on_open=lambda ws: print(f"Connected to WebSocket: {ws_url}"),
            on_message=lambda ws, msg: print(f"Received message: {msg}"),
            on_error=lambda ws, err: print(f"WebSocket error: {err}"),
            on_close=lambda ws, close_status_code, close_msg: print("WebSocket connection closed")
        )

        # Set timeout
        print(f"Connecting to WebSocket for {args.timeout} seconds...")

        # Run the WebSocket connection in a separate thread with timeout
        def run_websocket():
            ws.run_forever()

        ws_thread = threading.Thread(target=run_websocket)
        ws_thread.daemon = True
        ws_thread.start()

        try:
            # Wait for the specified timeout
            time.sleep(args.timeout)
        except KeyboardInterrupt:
            print("Connection interrupted by user")
        finally:
            ws.close()
            print("WebSocket connection closed")

    def handle_webhook(self, args):
        """Handle webhook subscription management."""
        if not hasattr(args, 'webhook_command') or not args.webhook_command:
            print("Error: Webhook command is required")
            sys.exit(1)

        if args.webhook_command == "list":
            self._list_webhooks()
        elif args.webhook_command == "create":
            self._create_webhook(args)
        elif args.webhook_command == "delete":
            self._delete_webhook(args)
        elif args.webhook_command == "test":
            self._test_webhook(args)

    def _list_webhooks(self):
        """List all webhook subscriptions."""
        endpoint = f"{BASE_URL}/webhooks"
        response = requests.get(endpoint, headers=get_headers())
        webhooks = handle_response(response)

        if not webhooks or not webhooks.get('items'):
            print("No webhook subscriptions found")
            return

        # Format and display webhook subscriptions
        table_data = []
        for hook in webhooks.get('items', []):
            table_data.append([
                hook.get('id'),
                hook.get('url'),
                ','.join(hook.get('events', [])),
                hook.get('status', 'unknown'),
                hook.get('created_at')
            ])

        headers = ["ID", "URL", "Events", "Status", "Created At"]
        print(tabulate(table_data, headers=headers, tablefmt="grid"))

    def _create_webhook(self, args):
        """Create a new webhook subscription."""
        endpoint = f"{BASE_URL}/webhooks"

        # Prepare webhook data
        webhook_data = {
            "url": args.url,
            "events": [e.strip() for e in args.events.split(",")]
        }

        if args.secret:
            webhook_data["secret"] = args.secret

        # Create webhook
        response = requests.post(endpoint, json=webhook_data, headers=get_headers())
        result = handle_response(response)
        print(f"Successfully created webhook: {json.dumps(result, indent=2)}")

    def _delete_webhook(self, args):
        """Delete a webhook subscription."""
        endpoint = f"{BASE_URL}/webhooks/{args.id}"
        response = requests.delete(endpoint, headers=get_headers())
        handle_response(response)
        print(f"Successfully deleted webhook subscription: {args.id}")

    def _test_webhook(self, args):
        """Test a webhook subscription by sending a test event."""
        endpoint = f"{BASE_URL}/webhooks/{args.id}/test"
        response = requests.post(endpoint, headers=get_headers())
        result = handle_response(response)
        print(f"Test event sent to webhook: {json.dumps(result, indent=2)}")

    def handle_analytics(self, args):
        """Handle analytics data retrieval and display."""
        # Determine time period
        end_time = datetime.utcnow()
        if args.period == "hour":
            start_time = end_time - timedelta(hours=1)
        elif args.period == "day":
            start_time = end_time - timedelta(days=1)
        elif args.period == "week":
            start_time = end_time - timedelta(weeks=1)
        elif args.period == "month":
            start_time = end_time - timedelta(days=30)

        # Format times for API
        start_time_str = start_time.isoformat() + "Z"
        end_time_str = end_time.isoformat() + "Z"

        # Build the analytics endpoint
        endpoint = f"{BASE_URL}/analytics/{args.metric}"
        params = {
            "start_time": start_time_str,
            "end_time": end_time_str
        }

        # Fetch analytics data
        response = requests.get(endpoint, params=params, headers=get_headers())
        data = handle_response(response)

        if args.format == "json":
            print(json.dumps(data, indent=2))
            return

        # Process data for display
        if not data or not data.get('items'):
            print(f"No {args.metric} analytics data available for the selected period")
            return

        # Display data in the requested format
        if args.format == "table":
            self._display_analytics_table(args.metric, data)
        elif args.format == "csv":
            self._display_analytics_csv(args.metric, data)

    def _display_analytics_table(self, metric, data):
        """Display analytics data in table format."""
        items = data.get('items', [])

        if not items:
            print("No data to display")
            return

        # Dynamically determine headers from the first item
        first_item = items[0]
        headers = list(first_item.keys())

        # Prepare table data
        table_data = []
        for item in items:
            row = [item.get(header, '') for header in headers]
            table_data.append(row)

        print(tabulate(table_data, headers=headers, tablefmt="grid"))

    def _display_analytics_csv(self, metric, data):
        """Display analytics data in CSV format."""
        items = data.get('items', [])

        if not items:
            print("No data to display")
            return

        # Get headers from the first item
        headers = list(items[0].keys())
        print(",".join(headers))

        # Print rows
        for item in items:
            row = [str(item.get(header, '')) for header in headers]
            print(",".join(row))

    def handle_document(self, args):
        """Generate and post documents."""
        # Calculate the timestamp for the document
        if args.backdate > 0:
            base_timestamp = datetime.utcnow() - timedelta(days=args.backdate)
        else:
            base_timestamp = datetime.utcnow()

        # Initialize document generator
        generator = DocumentGenerator()

        # Generate documents
        for i in range(args.count):
            # Generate random date if multiple documents
            if args.count > 1:
                # Spread documents across time
                offset_days = random.randint(0, args.backdate) if args.backdate > 0 else 0
                timestamp = base_timestamp - timedelta(days=offset_days)
            else:
                timestamp = base_timestamp

            # Generate document
            document = generator.generate_document(
                doc_type=args.type,
                doc_format=args.format,
                project=args.project,
                team=args.team,
                length=args.length,
                timestamp=timestamp
            )

            # Process the document according to output option
            if args.output == "stdout":
                print(json.dumps(document, indent=2))
            elif args.output == "file":
                if not args.file:
                    doc_type = document["metadata"]["type"]
                    filename = f"{doc_type}_document_{timestamp.strftime('%Y%m%d_%H%M%S')}.json"
                else:
                    filename = args.file

                with open(filename, 'w') as f:
                    json.dump(document, f, indent=2)
                print(f"Document #{i + 1} written to {filename}")
            elif args.output == "api":
                self.post_document(document, args.chunk_size, args.chunk_overlap)

    def post_document(self, document, chunk_size, chunk_overlap):
        """Post a document to the document processing endpoint."""
        endpoint = f"{BASE_URL}/processor/document"

        # Prepare the payload
        payload = {
            "text": document["text"],
            "metadata": document["metadata"],
            "chunk_size": chunk_size,
            "chunk_overlap": chunk_overlap
        }

        # Post the document
        print(f"Posting document: {document['metadata']['type']} - {document['metadata']['id']}")
        response = requests.post(endpoint, json=payload, headers=get_headers())

        try:
            result = handle_response(response)
            print(f"Successfully posted document: {json.dumps(result, indent=2)}")
        except Exception as e:
            print(f"Error posting document: {e}")
            sys.exit(1)


if __name__ == "__main__":
    cli = FridayCLI()
    cli.run()
