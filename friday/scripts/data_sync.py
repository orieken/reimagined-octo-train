#!/usr/bin/env python
"""
Script to sync data between PostgreSQL and the Vector Database.

This script can:
1. Sync a specific test run from PostgreSQL to Qdrant
2. Sync all test runs for a specific project
3. Sync text chunks that haven't been processed yet
"""
import argparse
import asyncio
import logging
import sys
from typing import Optional, List

from sqlalchemy.orm import Session

from app.database.session import SessionLocal
from app.models.database import Project, TestRun
from app.services.bridge import DatabaseVectorBridgeService
from app.services.vector_db import VectorDBService
from app.core.rag.embeddings import EmbeddingService
from app.config import settings
from app.services.llm import LLMService

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("friday.sync")


class DataSyncManager:
    """Manager for syncing data between PostgreSQL and Vector DB"""

    def __init__(self):
        """Initialize the data sync manager"""
        self.db = SessionLocal()
        self.vector_db = VectorDBService(
            url=settings.QDRANT_URL,
            collection_name=settings.CUCUMBER_COLLECTION,
            vector_size=settings.VECTOR_DIMENSION
        )

        # Create LLM service first - use OLLAMA_MODEL from settings
        self.llm_service = LLMService(
            url=settings.OLLAMA_API_URL,
            model=settings.OLLAMA_MODEL,  # Changed from LLM_MODEL to OLLAMA_MODEL
            timeout=settings.OLLAMA_TIMEOUT
        )

        # Then initialize the embedding service with the LLM service
        self.embedding_service = EmbeddingService(
            llm_service=self.llm_service,
            chunk_size=settings.CHUNK_SIZE,
            chunk_overlap=settings.CHUNK_OVERLAP
        )

        self.bridge_service = DatabaseVectorBridgeService(
            vector_db_service=self.vector_db
        )

    async def initialize(self):
        """Initialize the services"""
        await self.vector_db.initialize()
        logger.info("DataSyncManager initialized successfully")

    def close(self):
        """Close connections"""
        if self.db:
            self.db.close()
        self.bridge_service.close()

    def list_projects(self) -> List[dict]:
        """List all projects in the database"""
        projects = self.db.query(Project).all()
        return [
            {
                "id": project.id,
                "name": project.name,
                "test_runs": self.db.query(TestRun).filter(TestRun.project_id == project.id).count()
            }
            for project in projects
        ]

    def list_test_runs(self, project_id: Optional[int] = None, limit: int = 10) -> List[dict]:
        """
        List test runs in the database.

        Args:
            project_id: Optional project ID to filter by
            limit: Maximum number of test runs to return

        Returns:
            List of test run info dictionaries
        """
        query = self.db.query(TestRun)
        if project_id is not None:
            query = query.filter(TestRun.project_id == project_id)

        test_runs = query.order_by(TestRun.created_at.desc()).limit(limit).all()

        return [
            {
                "id": test_run.id,
                "name": test_run.name,
                "project_id": test_run.project_id,
                "status": test_run.status.value if test_run.status else None,
                "created_at": test_run.created_at.isoformat() if test_run.created_at else None,
                "total_tests": test_run.total_tests,
                "passed_tests": test_run.passed_tests,
                "failed_tests": test_run.failed_tests
            }
            for test_run in test_runs
        ]

    async def sync_test_run(self, test_run_id: str) -> dict:
        """
        Sync a test run from PostgreSQL to Vector DB.

        Args:
            test_run_id: ID of the test run to sync

        Returns:
            Result of the sync operation
        """
        return await self.bridge_service.sync_test_run(
            test_run_id=test_run_id,
            embedding_service=self.embedding_service
        )

    async def sync_project(self, project_id: int, limit: Optional[int] = None) -> dict:
        """
        Sync all test runs for a project from PostgreSQL to Vector DB.

        Args:
            project_id: ID of the project to sync
            limit: Optional limit on the number of test runs to sync

        Returns:
            Result of the sync operation
        """
        # Get project
        project = self.db.query(Project).filter(Project.id == project_id).first()
        if not project:
            return {
                "success": False,
                "message": f"Project {project_id} not found"
            }

        # Get test runs for this project
        query = self.db.query(TestRun).filter(TestRun.project_id == project_id)
        query = query.order_by(TestRun.created_at.desc())

        if limit:
            query = query.limit(limit)

        test_runs = query.all()

        if not test_runs:
            return {
                "success": True,
                "message": f"No test runs found for project {project_id}",
                "synced_runs": 0
            }

        # Sync each test run
        results = []
        for test_run in test_runs:
            result = await self.sync_test_run(str(test_run.id))
            results.append(result)

        successful = sum(1 for result in results if result.get("success", False))

        return {
            "success": True,
            "message": f"Synced {successful} of {len(test_runs)} test runs for project {project.name}",
            "synced_runs": successful,
            "total_runs": len(test_runs),
            "project_id": project_id,
            "project_name": project.name,
            "details": results
        }

    async def sync_text_chunks(self) -> dict:
        """
        Sync text chunks from PostgreSQL to Vector DB.

        Returns:
            Result of the sync operation
        """
        return await self.bridge_service.sync_text_chunks(
            embedding_service=self.embedding_service
        )

    async def sync_all(self, limit_per_project: Optional[int] = None) -> dict:
        """
        Sync all projects and their test runs from PostgreSQL to Vector DB.

        Args:
            limit_per_project: Optional limit on the number of test runs to sync per project

        Returns:
            Result of the sync operation
        """
        # Get all projects
        projects = self.db.query(Project).all()

        if not projects:
            return {
                "success": True,
                "message": "No projects found",
                "synced_projects": 0
            }

        # Sync each project
        results = []
        for project in projects:
            result = await self.sync_project(project.id, limit_per_project)
            results.append(result)

        successful_projects = sum(1 for result in results if result.get("success", False))
        successful_runs = sum(result.get("synced_runs", 0) for result in results)

        # Sync text chunks
        chunks_result = await self.sync_text_chunks()

        return {
            "success": True,
            "message": f"Synced {successful_runs} test runs across {successful_projects} projects",
            "synced_projects": successful_projects,
            "total_projects": len(projects),
            "synced_runs": successful_runs,
            "synced_chunks": chunks_result.get("synced_chunks", 0),
            "project_details": results,
            "chunks_details": chunks_result
        }


async def main():
    """Main function to run from command line"""
    parser = argparse.ArgumentParser(description="Sync data between PostgreSQL and Vector DB")
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    # List projects
    list_projects_parser = subparsers.add_parser("list-projects", help="List all projects")

    # List test runs
    list_runs_parser = subparsers.add_parser("list-runs", help="List test runs")
    list_runs_parser.add_argument("--project-id", type=int, help="Project ID to filter by")
    list_runs_parser.add_argument("--limit", type=int, default=10, help="Maximum number of test runs to list")

    # Sync test run
    sync_run_parser = subparsers.add_parser("sync-run", help="Sync a specific test run")
    sync_run_parser.add_argument("--test-run-id", type=str, required=True, help="Test run ID to sync")

    # Sync project
    sync_project_parser = subparsers.add_parser("sync-project", help="Sync all test runs for a project")
    sync_project_parser.add_argument("--project-id", type=int, required=True, help="Project ID to sync")
    sync_project_parser.add_argument("--limit", type=int, help="Maximum number of test runs to sync")

    # Sync text chunks
    sync_chunks_parser = subparsers.add_parser("sync-chunks", help="Sync text chunks")

    # Sync all
    sync_all_parser = subparsers.add_parser("sync-all", help="Sync all projects and their test runs")
    sync_all_parser.add_argument("--limit-per-project", type=int,
                                 help="Maximum number of test runs to sync per project")

    args = parser.parse_args()

    # Initialize manager
    manager = DataSyncManager()

    try:
        await manager.initialize()

        if args.command == "list-projects":
            projects = manager.list_projects()
            logger.info(f"Projects: {projects}")

        elif args.command == "list-runs":
            test_runs = manager.list_test_runs(
                project_id=args.project_id,
                limit=args.limit
            )
            logger.info(f"Test runs: {test_runs}")

        elif args.command == "sync-run":
            result = await manager.sync_test_run(args.test_run_id)
            logger.info(f"Sync result: {result}")

        elif args.command == "sync-project":
            result = await manager.sync_project(
                project_id=args.project_id,
                limit=args.limit
            )
            logger.info(f"Sync result: {result}")

        elif args.command == "sync-chunks":
            result = await manager.sync_text_chunks()
            logger.info(f"Sync result: {result}")

        elif args.command == "sync-all":
            result = await manager.sync_all(
                limit_per_project=args.limit_per_project
            )
            logger.info(f"Sync result: {result}")

        else:
            parser.print_help()

    except Exception as e:
        logger.error(f"Error: {str(e)}", exc_info=True)
        return 1
    finally:
        manager.close()

    return 0


if __name__ == "__main__":
    asyncio.run(main())