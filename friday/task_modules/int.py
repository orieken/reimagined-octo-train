# int.py
import json

from invoke import task

@task
def test_processor(c):
    """Send a sample Cucumber report to the processor endpoint for testing."""
    print("🚀 Sending test payload to /api/v1/processor/cucumber...")
    payload = {
        "metadata": {
            "project": "demo-project",
            "branch": "main",
            "commit": "abcdef123456",
            "environment": "staging",
            "runner": "ci-runner-01",
            "timestamp": "2024-04-26T23:00:00Z",
            "test_run_id": "test-run-124"
        },
        "features": [
            {
                "name": "Login Feature",
                "description": "Testing login functionality",
                "uri": "features/login.feature",
                "tags": ["smoke"],
                "elements": [
                    {
                        "name": "Successful Login",
                        "description": "User can login with valid credentials",
                        "type": "scenario",
                        "tags": [
                            {"name": "@login","line": 1},
                            {"name": "@smoke", "line": 1},
                            {"name": "@regression", "line": 1}
                        ],
                        "steps": [
                            {
                                "name": "Navigate to login page",
                                "keyword": "Given",
                                "result": {
                                    "status": "passed",
                                    "duration": 1.23
                                }
                            },
                            {
                                "name": "Enter valid credentials",
                                "keyword": "When",
                                "result": {
                                    "status": "passed",
                                    "duration": 0.56
                                }
                            },
                            {
                                "name": "Click login button",
                                "keyword": "And",
                                "result": {
                                    "status": "passed",
                                    "duration": 0.78
                                }
                            }
                        ]
                    }
                ]
            }
        ]
    }

    c.run(
        f"""
        curl -X POST http://localhost:4000/api/v1/processor/cucumber \
        -H "Content-Type: application/json" \
        -d '{json.dumps(payload)}'
        """,
        pty=True
    )

@task
def healthcheck(c):
    """Ping the /processor/health endpoint."""
    print("🩺 Checking service health at /api/v1/processor/health...")
    c.run(
        """
        curl -X GET http://localhost:4000/api/v1/processor/health
        """,
        pty=True
    )


@task
def test_pro(c):
    """Send a sample Cucumber report to the processor endpoint for testing."""
    print("🚀 Sending test payload to /api/v1/processor/cucumber...")
    c.run(
        """
        curl -X POST http://localhost:4000/api/v1/processor/cucumber \
        -H "Content-Type: application/json" \
        -d '{
          "metadata": {
            "project": "demo-project",
            "branch": "main",
            "commit": "abcdef123456",
            "environment": "staging",
            "runner": "some-server-name",
            "timestamp": "2024-04-26T23:00:00Z",
            "test_run_id": "test-run-123"
          },
          "features": [
            {
              "name": "Login Feature",
              "description": "Testing login functionality",
              "uri": "features/login.feature",
              "tags": ["smoke"],
              "elements": [
                {
                  "name": "Successful Login",
                  "description": "User can login with valid credentials",
                  "type": "scenario",
                  "tags": ["login", "critical"],
                  "steps": [
                    {
                      "name": "Navigate to login page",
                      "keyword": "Given",
                      "result": { "status": "passed", "duration": 1.23 }
                    },
                    {
                      "name": "Enter valid credentials",
                      "keyword": "When",
                      "result": { "status": "passed", "duration": 0.56 }
                    },
                    {
                      "name": "Click login button",
                      "keyword": "And",
                      "result": { "status": "passed", "duration": 0.78 }
                    }
                  ]
                }
              ]
            }
          ]
        }'
        """,
        pty=True
    )
