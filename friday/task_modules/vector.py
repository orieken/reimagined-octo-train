# tasks.py
from invoke import task
import logging
from qdrant_client import QdrantClient
from qdrant_client.http import models as qdrant_models
from app.config import settings

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("qdrant_setup")


@task
def setup_collections(c):
    """Set up Qdrant collections for the Friday Test Analysis service"""
    logger.info(f"Connecting to Qdrant at {settings.QDRANT_URL}")

    # Connect to Qdrant running in Docker
    client = QdrantClient(
        url=settings.QDRANT_URL,
        timeout=10,
    )

    # Collection name from configuration
    collection_name = settings.CUCUMBER_COLLECTION or "test_artifacts"

    # Check if collection exists
    collections = client.get_collections().collections
    collection_names = [coll.name for coll in collections]

    # Create collection if it doesn't exist
    if collection_name in collection_names:
        logger.info(f"Collection '{collection_name}' already exists")
    else:
        logger.info(f"Creating collection '{collection_name}'")
        client.create_collection(
            collection_name=collection_name,
            vectors_config=qdrant_models.VectorParams(
                size=settings.VECTOR_DIMENSION,
                distance=qdrant_models.Distance.COSINE
            )
        )
        logger.info(f"Collection '{collection_name}' created successfully")

    logger.info(f"Collection '{collection_name}' is ready for use with vector_db.py")
    return True


@task
def clear_collections(c, confirm=False):
    """Clear all points from the Qdrant collections but keep the collection structure"""
    if not confirm:
        logger.warning("This will delete all data in the collections!")
        logger.warning("Run with --confirm flag to proceed")
        return False

    logger.info(f"Connecting to Qdrant at {settings.QDRANT_URL}")
    client = QdrantClient(
        url=settings.QDRANT_URL,
        timeout=10,
    )

    # Collection name from configuration
    collection_name = settings.CUCUMBER_COLLECTION or "test_artifacts"

    # Check if collection exists
    collections = client.get_collections().collections
    collection_names = [coll.name for coll in collections]

    if collection_name in collection_names:
        logger.info(f"Clearing all points from collection '{collection_name}'")
        # Delete all points but keep the collection structure
        client.delete(
            collection_name=collection_name,
            points_selector=qdrant_models.FilterSelector(
                filter=qdrant_models.Filter()  # Empty filter selects all points
            )
        )
        logger.info(f"All points deleted from collection '{collection_name}'")
    else:
        logger.warning(f"Collection '{collection_name}' does not exist")

    return True


@task
def delete_collections(c, confirm=False):
    """Delete the Qdrant collections completely"""
    if not confirm:
        logger.warning("This will completely delete the collections!")
        logger.warning("Run with --confirm flag to proceed")
        return False

    logger.info(f"Connecting to Qdrant at {settings.QDRANT_URL}")
    client = QdrantClient(
        url=settings.QDRANT_URL,
        timeout=10,
    )

    # Collection name from configuration
    collection_name = settings.CUCUMBER_COLLECTION or "test_artifacts"

    # Check if collection exists
    collections = client.get_collections().collections
    collection_names = [coll.name for coll in collections]

    if collection_name in collection_names:
        logger.info(f"Deleting collection '{collection_name}'")
        client.delete_collection(collection_name=collection_name)
        logger.info(f"Collection '{collection_name}' deleted")
    else:
        logger.warning(f"Collection '{collection_name}' does not exist")

    return True