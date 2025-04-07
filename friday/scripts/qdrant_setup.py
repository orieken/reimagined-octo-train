#!/usr/bin/env python
"""
Script to initialize and manage Qdrant collections for Friday Service.

This script can:
1. Create required collections if they don't exist
2. Reset collections (delete and recreate)
3. Check collection status
"""
import argparse
import asyncio
import logging
from typing import List, Optional

from qdrant_client import QdrantClient
from qdrant_client.http import models as qdrant_models

from app.config import settings

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("friday.qdrant")


class QdrantManager:
    """Manager for Qdrant collections"""

    def __init__(self, url: Optional[str] = None, api_key: Optional[str] = None):
        """
        Initialize the Qdrant manager.

        Args:
            url: Qdrant server URL (defaults to settings.QDRANT_URL)
            api_key: API key for authentication (optional)
        """
        self.url = url or settings.QDRANT_URL
        self.api_key = api_key
        self.collections = {
            settings.CUCUMBER_COLLECTION: settings.VECTOR_DIMENSION,
            settings.BUILD_INFO_COLLECTION: settings.VECTOR_DIMENSION
        }
        self.client = self._initialize_client()

    def _initialize_client(self) -> QdrantClient:
        """Initialize and return a Qdrant client."""
        try:
            client_params = {"url": self.url}
            if self.api_key:
                client_params["api_key"] = self.api_key

            client = QdrantClient(**client_params)
            return client
        except Exception as e:
            logger.error(f"Failed to connect to Qdrant: {str(e)}")
            raise

    def list_collections(self) -> List[str]:
        """List all collections."""
        try:
            collections = self.client.get_collections()
            return [collection.name for collection in collections.collections]
        except Exception as e:
            logger.error(f"Failed to list collections: {str(e)}")
            raise

    def create_collection(self, name: str, vector_size: int) -> bool:
        """
        Create a collection if it doesn't exist.

        Args:
            name: Collection name
            vector_size: Size of embedding vectors

        Returns:
            True if collection was created or already exists
        """
        try:
            # Check if collection exists
            collections = self.list_collections()
            if name in collections:
                logger.info(f"Collection '{name}' already exists")
                return True

            # Create collection
            logger.info(f"Creating collection '{name}' with vector size {vector_size}")
            self.client.create_collection(
                collection_name=name,
                vectors_config=qdrant_models.VectorParams(
                    size=vector_size,
                    distance=qdrant_models.Distance.COSINE
                )
            )

            # Create payload indexes for common query fields
            self.client.create_payload_index(
                collection_name=name,
                field_name="type",
                field_schema=qdrant_models.PayloadSchemaType.KEYWORD
            )

            if name == settings.CUCUMBER_COLLECTION:
                # Add indexes for Cucumber collection
                self.client.create_payload_index(
                    collection_name=name,
                    field_name="test_run_id",
                    field_schema=qdrant_models.PayloadSchemaType.KEYWORD
                )
                self.client.create_payload_index(
                    collection_name=name,
                    field_name="feature_id",
                    field_schema=qdrant_models.PayloadSchemaType.KEYWORD
                )
                self.client.create_payload_index(
                    collection_name=name,
                    field_name="scenario_id",
                    field_schema=qdrant_models.PayloadSchemaType.KEYWORD
                )
                self.client.create_payload_index(
                    collection_name=name,
                    field_name="tags",
                    field_schema=qdrant_models.PayloadSchemaType.KEYWORD
                )

            logger.info(f"Collection '{name}' created successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to create collection '{name}': {str(e)}")
            raise

    def delete_collection(self, name: str) -> bool:
        """
        Delete a collection if it exists.

        Args:
            name: Collection name

        Returns:
            True if collection was deleted or didn't exist
        """
        try:
            # Check if collection exists
            collections = self.list_collections()
            if name not in collections:
                logger.info(f"Collection '{name}' doesn't exist")
                return True

            # Delete collection
            logger.info(f"Deleting collection '{name}'")
            self.client.delete_collection(collection_name=name)
            logger.info(f"Collection '{name}' deleted successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to delete collection '{name}': {str(e)}")
            raise

    def reset_collection(self, name: str, vector_size: int) -> bool:
        """
        Reset a collection (delete and recreate).

        Args:
            name: Collection name
            vector_size: Size of embedding vectors

        Returns:
            True if collection was reset successfully
        """
        try:
            self.delete_collection(name)
            self.create_collection(name, vector_size)
            return True
        except Exception as e:
            logger.error(f"Failed to reset collection '{name}': {str(e)}")
            raise

    def get_collection_info(self, name: str) -> dict:
        """
        Get information about a collection.

        Args:
            name: Collection name

        Returns:
            Collection information
        """
        try:
            # Check if collection exists
            collections = self.list_collections()
            if name not in collections:
                return {"exists": False}

            # Get collection info
            info = self.client.get_collection(collection_name=name)

            # Get count of points
            count_result = self.client.count(collection_name=name)
            point_count = count_result.count

            return {
                "exists": True,
                "name": name,
                "vectors_count": point_count,
                "vectors_config": {
                    "size": info.config.params.vectors.size,
                    "distance": info.config.params.vectors.distance.name
                },
                "status": info.status
            }
        except Exception as e:
            logger.error(f"Failed to get info for collection '{name}': {str(e)}")
            raise

    def setup_collections(self) -> bool:
        """
        Set up all required collections.

        Returns:
            True if all collections were set up successfully
        """
        try:
            for name, vector_size in self.collections.items():
                self.create_collection(name, vector_size)
            return True
        except Exception as e:
            logger.error(f"Failed to set up collections: {str(e)}")
            raise

    def reset_all_collections(self) -> bool:
        """
        Reset all collections.

        Returns:
            True if all collections were reset successfully
        """
        try:
            for name, vector_size in self.collections.items():
                self.reset_collection(name, vector_size)
            return True
        except Exception as e:
            logger.error(f"Failed to reset all collections: {str(e)}")
            raise

    def check_all_collections(self) -> dict:
        """
        Check status of all collections.

        Returns:
            Status of all collections
        """
        result = {}
        for name in self.collections:
            result[name] = self.get_collection_info(name)
        return result


def main():
    """Main function to run from command line"""
    parser = argparse.ArgumentParser(description="Manage Qdrant collections for Friday Service")
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    # List collections
    list_parser = subparsers.add_parser("list", help="List all collections")

    # Create collection
    create_parser = subparsers.add_parser("create", help="Create a collection")
    create_parser.add_argument("--name", type=str, help="Collection name (defaults to all required collections)")

    # Delete collection
    delete_parser = subparsers.add_parser("delete", help="Delete a collection")
    delete_parser.add_argument("--name", type=str, required=True, help="Collection name")

    # Reset collection
    reset_parser = subparsers.add_parser("reset", help="Reset a collection (delete and recreate)")
    reset_parser.add_argument("--name", type=str, help="Collection name (defaults to all required collections)")

    # Check collection
    check_parser = subparsers.add_parser("check", help="Check collection status")
    check_parser.add_argument("--name", type=str, help="Collection name (defaults to all required collections)")

    # Setup all collections
    setup_parser = subparsers.add_parser("setup", help="Set up all required collections")

    # Reset all collections
    reset_all_parser = subparsers.add_parser("reset-all", help="Reset all collections")

    args = parser.parse_args()

    # Initialize manager
    manager = QdrantManager()

    try:
        if args.command == "list":
            collections = manager.list_collections()
            logger.info(f"Collections: {collections}")

        elif args.command == "create":
            if args.name:
                # Create specific collection
                vector_size = manager.collections.get(args.name, settings.VECTOR_DIMENSION)
                manager.create_collection(args.name, vector_size)
            else:
                # Create all collections
                manager.setup_collections()

        elif args.command == "delete":
            manager.delete_collection(args.name)

        elif args.command == "reset":
            if args.name:
                # Reset specific collection
                vector_size = manager.collections.get(args.name, settings.VECTOR_DIMENSION)
                manager.reset_collection(args.name, vector_size)
            else:
                # Reset all collections
                manager.reset_all_collections()

        elif args.command == "check":
            if args.name:
                # Check specific collection
                info = manager.get_collection_info(args.name)
                logger.info(f"Collection '{args.name}': {info}")
            else:
                # Check all collections
                info = manager.check_all_collections()
                logger.info(f"Collections status: {info}")

        elif args.command == "setup":
            manager.setup_collections()

        elif args.command == "reset-all":
            manager.reset_all_collections()

        else:
            parser.print_help()

    except Exception as e:
        logger.error(f"Error: {str(e)}")
        return 1

    return 0


if __name__ == "__main__":
    exit(main())