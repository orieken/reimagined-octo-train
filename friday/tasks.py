# tasks.py
"""
Invoke tasks for the Friday service.
"""
from invoke import task, Collection
from huggingface_hub import snapshot_download
import task_modules.db
# import task_modules.docker
# import task_modules.chores
# import task_modules.cucumber
import task_modules.tags
import task_modules.vector
import task_modules.test
import task_modules.int

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

import os
from sentence_transformers import SentenceTransformer

@task
def download_embeddings(c):
    """
    Download and snapshot the SentenceTransformer model properly to ./models/all-MiniLM-L6-v2
    """
    model_name = "sentence-transformers/all-MiniLM-L6-v2"
    output_dir = "./models/all-MiniLM-L6-v2"

    if os.path.exists(output_dir):
        print(f"✅ Embedding model already exists at {output_dir}")
        return

    print(f"📥 Downloading {model_name} into {output_dir}...")
    snapshot_download(repo_id=model_name, local_dir=output_dir, local_dir_use_symlinks=False)
    print("✅ Download complete.")

@task
def check_model_health(c):
    """
    🩺 Quickly load the local embedding model and test embedding a dummy text.
    """
    model_path = "./models/all-MiniLM-L6-v2"

    if not os.path.isdir(model_path):
        print(f"❌ Model directory not found at {model_path}. Please run 'invoke download-embeddings' first.")
        return

    print(f"🔍 Loading model from {model_path}...")
    model = SentenceTransformer(model_path)

    test_text = "Hello, this is a quick health check!"
    print(f"🧠 Embedding test text: '{test_text}'")

    try:
        embedding = model.encode([test_text])[0]
        print(f"✅ Successfully generated embedding of size {len(embedding)}.")
    except Exception as e:
        print(f"❌ Failed to generate embedding: {e}")

ns = Collection(
    task_modules.db,
    # task_modules.docker,
    # task_modules.chores,
    # task_modules.cucumber,
    task_modules.vector,
    task_modules.test,
    task_modules.tags,
    task_modules.int,
    run_local,
    run,
    download_embeddings,
    check_model_health
)