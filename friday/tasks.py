# tasks.py
"""
Invoke tasks for the Friday service.
"""

from invoke import task


@task
def format(c):
    """Format code with Black and isort."""
    print("Formatting code with Black and isort...")
    c.run("isort app/ tests/")
    c.run("black app/ tests/")
    print("✓ Code formatted")


@task
def lint(c):
    """Run linters: flake8 and mypy."""
    print("Running flake8...")
    c.run("flake8 app/ tests/", warn=True)

    print("Running mypy...")
    c.run("mypy app/ tests/", warn=True)

    print("✓ Linting completed")


@task
def test(c, cov=False, html=False, xvs=False):
    """
    Run tests, optionally with coverage.

    Args:
        cov: Enable coverage reporting
        html: Generate HTML coverage report
        xvs: Run tests in parallel with xdist
    """
    cmd = "pytest"

    if xvs:
        cmd += " -xvs"
    else:
        cmd += " -v"

    if cov:
        cmd += " --cov=app"
        if html:
            cmd += " --cov-report=html"

    print(f"Running tests: {cmd}")
    c.run(cmd)


@task
def verify(c):
    """Run all verification steps: format, lint, and test with coverage."""
    format(c)
    lint(c)
    test(c, cov=True)


@task
def run(c, debug=False):
    """
    Run the application.

    Args:
        debug: Run in debug mode with hot reloading
    """
    cmd = "uvicorn app.main:app --host 0.0.0.0 --port 4000"
    if debug:
        cmd += " --reload"

    print(f"Starting server: {cmd}")
    c.run(cmd)


@task
def run_local(c, debug=False):
    """
    Run the application in local mode without external services.

    Args:
        debug: Run in debug mode with hot reloading
    """
    cmd = "uvicorn app.main_local:app --host 0.0.0.0 --port 4000"
    if debug:
        cmd += " --reload"

    print(f"Starting server in LOCAL MODE: {cmd}")
    c.run(cmd)


@task
def install(c, dev=False):
    """
    Install dependencies.

    Args:
        dev: Install development dependencies
    """
    if dev:
        print("Installing development dependencies...")
        c.run("pip install -r requirements-dev.txt")
    else:
        print("Installing production dependencies...")
        c.run("pip install -r requirements.txt")

    # Install the package in development mode
    print("Installing package in development mode...")
    c.run("pip install -e .")

    print("✓ Installation completed")


@task
def clean(c):
    """Clean temporary files and artifacts."""
    patterns = [
        # Python artifacts
        "**/__pycache__",
        "**/*.pyc",
        "**/*.pyo",
        "**/*.pyd",
        ".pytest_cache",
        ".coverage",
        "htmlcov",
        "dist",
        "build",
        "*.egg-info",

        # Environment artifacts
        ".venv",
        "venv",
        "env",

        # Editor artifacts
        ".vscode",
        ".idea",
        "*.swp",
        "*.swo",
    ]

    for pattern in patterns:
        c.run(f"rm -rf {pattern}", warn=True)

    print("✓ Cleaned up project directory")


@task
def docker_build(c):
    """Build the Docker image."""
    print("Building Docker image...")
    c.run("docker build -t friday-service:latest .")
    print("✓ Docker image built")


@task
def docker_run(c):
    """Run the Docker container."""
    print("Running Docker container...")
    c.run("docker run -p 4000:4000 friday-service:latest")


@task
def docker_compose_up(c, build=False):
    """
    Start all services with Docker Compose.

    Args:
        build: Rebuild images before starting containers
    """
    cmd = "docker-compose up -d"
    if build:
        cmd += " --build"

    print(f"Starting services: {cmd}")
    c.run(cmd)
    print("✓ Services started")


@task
def docker_compose_down(c, volumes=False):
    """
    Stop all services with Docker Compose.

    Args:
        volumes: Remove volumes
    """
    cmd = "docker-compose down"
    if volumes:
        cmd += " -v"

    print(f"Stopping services: {cmd}")
    c.run(cmd)
    print("✓ Services stopped")


@task
def docker_compose_local_up(c):
    """Start Qdrant and Ollama services with Docker Compose."""
    print("Starting Qdrant and Ollama services...")
    c.run("docker-compose -f docker-compose.local.yml up -d")
    print("✓ Services started")


@task
def docker_compose_local_down(c):
    """Stop Qdrant and Ollama services."""
    print("Stopping Qdrant and Ollama services...")
    c.run("docker-compose -f docker-compose.local.yml down")
    print("✓ Services stopped")


@task
def run_with_env(c, env_file=".env", debug=False):
    """
    Run the application with a specific environment file.

    Args:
        env_file: Path to the environment file
        debug: Run in debug mode with hot reloading
    """
    cmd = f"env $(cat {env_file} | grep -v '^#' | xargs) uvicorn app.main:app --host 0.0.0.0 --port 4000"
    if debug:
        cmd += " --reload"

    print(f"Starting server with env file {env_file}: {cmd}")
    c.run(cmd)


@task
def docs(c, serve=False):
    """
    Build documentation.

    Args:
        serve: Serve documentation after building
    """
    print("Building documentation...")
    c.run("mkdocs build")

    if serve:
        print("Serving documentation...")
        c.run("mkdocs serve")
    else:
        print("✓ Documentation built")

@task
def complexity(c):
    """
    Calculate cyclomatic complexity using Radon.
    Excludes test files, sample_report.py, and tasks.py.
    """
    print("Calculating cyclomatic complexity using Radon...")
    c.run('radon cc -s -a . --exclude "test*,sample_report.py,tasks.py"', pty=True)
    print("✓ Cyclomatic complexity analysis completed")
