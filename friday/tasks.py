# tasks.py
"""
Invoke tasks for the Friday service.
"""
from invoke import task, Collection
import task_modules.db
import task_modules.docker
import task_modules.chores
import task_modules.cucumber
import task_modules.cu

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

ns = Collection(
    task_modules.db,
    task_modules.docker,
    task_modules.chores,
    task_modules.cucumber,
    task_modules.cu,
    run_local,
    run
)