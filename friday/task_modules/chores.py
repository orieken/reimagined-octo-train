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

