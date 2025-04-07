from invoke import task


@task
def build(c):
    """Build the Docker image."""
    print("Building Docker image...")
    c.run("docker build -t friday-service:latest .")
    print("✓ Docker image built")


@task
def run(c):
    """Run the Docker container."""
    print("Running Docker container...")
    c.run("docker run -p 4000:4000 friday-service:latest")


@task
def compose_up(c, build=False):
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
def compose_down(c, volumes=False):
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
def compose_local_up(c):
    """Start Qdrant and Ollama services with Docker Compose."""
    print("Starting Qdrant and Ollama services...")
    c.run("docker-compose -f docker-compose.local.yml up -d")
    print("✓ Services started")


@task
def compose_local_down(c):
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
