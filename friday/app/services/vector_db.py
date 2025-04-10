from typing import List, Dict, Any, Optional
import logging
from pydantic import BaseModel
from qdrant_client import QdrantClient
from qdrant_client.http import models as qdrant_models

from app.config import settings

from app.models import TextChunk, Report, TestCase, TestStep, BuildInfo, Feature

logger = logging.getLogger(__name__)


class SearchResult(BaseModel):
    """Model representing a search result from the vector database."""
    id: str
    score: float
    payload: Dict[str, Any]


class VectorDBService:
    """Service for interacting with the Qdrant vector database."""

    def __init__(self, url: Optional[str] = None, api_key: Optional[str] = None,
                 collection_name: Optional[str] = None, vector_size: Optional[int] = None):
        """
        Initialize the Vector DB service with configuration.

        Args:
            url: Qdrant server URL (defaults to settings.QDRANT_URL)
            api_key: API key for authentication (optional)
            collection_name: Name of the collection (defaults to settings.CUCUMBER_COLLECTION)
            vector_size: Size of embedding vectors (defaults to settings.VECTOR_DIMENSION)
        """
        self.url = url or settings.QDRANT_URL
        self.api_key = api_key
        self.cucumber_collection = collection_name or settings.CUCUMBER_COLLECTION
        self.build_info_collection = settings.BUILD_INFO_COLLECTION
        self.vector_size = vector_size or settings.VECTOR_DIMENSION
        # Initialize client right away to avoid None access errors
        self.client = self._initialize_client()

    def _initialize_client(self) -> QdrantClient:
        """Initialize and return a Qdrant client."""
        try:
            client_params = {"url": self.url}
            if self.api_key:
                client_params["api_key"] = self.api_key

            client = QdrantClient(**client_params)

            # Check connection if not in the middle of initialization
            try:
                client.get_collections()
                logger.info("Successfully connected to Qdrant at %s", self.url)
            except Exception as e:
                logger.warning("Could not verify connection to Qdrant: %s", str(e))

            return client
        except Exception as e:
            logger.error("Failed to connect to Qdrant: %s", str(e))
            # Return a dummy client that will be reinitialized later
            # instead of raising an exception
            return QdrantClient(url=self.url)

    async def initialize(self) -> None:
        """Initialize the vector database connection and ensure collections exist."""
        logger.info("Initializing connection to Qdrant at %s", self.url)
        try:
            client_params = {"url": self.url}
            if self.api_key:
                client_params["api_key"] = self.api_key

            self.client = QdrantClient(**client_params)

            # Check connection
            self.client.get_collections()
            logger.info("Successfully connected to Qdrant at %s", self.url)

            # Ensure collections exist
            await self.ensure_collections_exist()

            logger.info("VectorDBService initialized successfully")
        except Exception as e:
            logger.error("Failed to initialize Qdrant connection: %s", str(e))
            raise ConnectionError(f"Could not connect to Qdrant: {str(e)}")

    async def ensure_collections_exist(self):
        """Ensure all required collections exist in Qdrant."""
        # Make sure client is initialized
        if self.client is None:
            self.client = self._initialize_client()

        collections = {
            self.cucumber_collection: self.vector_size,
            self.build_info_collection: self.vector_size
        }

        try:
            existing_collections = [
                collection.name for collection in self.client.get_collections().collections
            ]

            for collection_name, vector_size in collections.items():
                if collection_name not in existing_collections:
                    logger.info("Creating collection: %s", collection_name)
                    self.client.create_collection(
                        collection_name=collection_name,
                        vectors_config=qdrant_models.VectorParams(
                            size=vector_size,
                            distance=qdrant_models.Distance.COSINE
                        )
                    )
        except Exception as e:
            logger.error("Failed to ensure collections exist: %s", str(e))
            # Continue without raising to allow the service to start

    def store_chunk(self, text_chunk: TextChunk, embedding: List[float], collection_name: Optional[str] = None) -> None:
        """Store a text chunk with its embedding in the vector database."""
        # Make sure client is initialized
        if self.client is None:
            self.client = self._initialize_client()

        if collection_name is None:
            collection_name = self.cucumber_collection

        try:
            self.client.upsert(
                collection_name=collection_name,
                points=[
                    qdrant_models.PointStruct(
                        id=text_chunk.id,
                        vector=embedding,
                        payload={
                            "text": text_chunk.text,
                            "metadata": text_chunk.metadata.dict() if hasattr(text_chunk.metadata,
                                                                              'dict') else text_chunk.metadata,
                            "chunk_size": text_chunk.chunk_size
                        }
                    )
                ]
            )
            logger.info("Stored text chunk with ID: %s", text_chunk.id)
        except Exception as e:
            logger.error("Failed to store text chunk %s: %s", text_chunk.id, str(e))
            raise

    def store_report(self, report_id: str, embedding: List[float], report: Report) -> None:
        """Store a report with its embedding in the vector database."""
        # Make sure client is initialized
        if self.client is None:
            self.client = self._initialize_client()

        try:
            self.client.upsert(
                collection_name=self.cucumber_collection,
                points=[
                    qdrant_models.PointStruct(
                        id=report_id,
                        vector=embedding,
                        payload={
                            "type": "report",
                            **report.dict(exclude={"scenarios"})
                        }
                    )
                ]
            )
            logger.info("Stored report with ID: %s", report_id)
        except Exception as e:
            logger.error("Failed to store report %s: %s", report_id, str(e))
            raise

    def store_test_case(self, test_case_id: str, embedding: List[float], test_case: TestCase, report_id: str) -> None:
        """Store a test case with its embedding in the vector database."""
        # Make sure client is initialized
        if self.client is None:
            self.client = self._initialize_client()

        try:
            # Add the report_id to the payload to maintain the relationship
            payload = test_case.dict(exclude={"steps"})
            payload["report_id"] = report_id
            payload["type"] = "test_case"

            self.client.upsert(
                collection_name=self.cucumber_collection,
                points=[
                    qdrant_models.PointStruct(
                        id=test_case_id,
                        vector=embedding,
                        payload=payload
                    )
                ]
            )
            logger.info("Stored test case with ID: %s", test_case_id)
        except Exception as e:
            logger.error("Failed to store test case %s: %s", test_case_id, str(e))
            raise

    def store_test_step(self, step_id: str, embedding: List[float], step: TestStep, test_case_id: str) -> None:
        """Store a test step with its embedding in the vector database."""
        # Make sure client is initialized
        if self.client is None:
            self.client = self._initialize_client()

        try:
            # Add the test_case_id to the payload to maintain the relationship
            payload = step.dict()
            payload["test_case_id"] = test_case_id
            payload["type"] = "test_step"

            self.client.upsert(
                collection_name=self.cucumber_collection,
                points=[
                    qdrant_models.PointStruct(
                        id=step_id,
                        vector=embedding,
                        payload=payload
                    )
                ]
            )
            logger.info("Stored test step with ID: %s", step_id)
        except Exception as e:
            logger.error("Failed to store test step %s: %s", step_id, str(e))
            raise

    def store_build_info(self, build_id: str, embedding: List[float], build_info: BuildInfo) -> None:
        """Store build information with its embedding in the vector database."""
        # Make sure client is initialized
        if self.client is None:
            self.client = self._initialize_client()

        try:
            self.client.upsert(
                collection_name=self.build_info_collection,
                points=[
                    qdrant_models.PointStruct(
                        id=build_id,
                        vector=embedding,
                        payload={
                            "type": "build_info",
                            **build_info.dict()
                        }
                    )
                ]
            )
            logger.info("Stored build info with ID: %s", build_id)
        except Exception as e:
            logger.error("Failed to store build info %s: %s", build_id, str(e))
            raise

    def store_feature(self, feature_id: str, embedding: List[float], feature: Feature) -> None:
        """Store a feature with its embedding in the vector database."""
        # Make sure client is initialized
        if self.client is None:
            self.client = self._initialize_client()

        try:
            self.client.upsert(
                collection_name=self.cucumber_collection,
                points=[
                    qdrant_models.PointStruct(
                        id=feature_id,
                        vector=embedding,
                        payload={
                            "type": "feature",
                            **feature.dict(exclude={"scenarios"})
                        }
                    )
                ]
            )
            logger.info("Stored feature with ID: %s", feature_id)
        except Exception as e:
            logger.error("Failed to store feature %s: %s", feature_id, str(e))
            raise

    def search_chunks(self, query_embedding: List[float], filter_conditions: Optional[List] = None,
                      limit: int = None) -> List[SearchResult]:
        """Search for text chunks similar to the query embedding."""
        # Make sure client is initialized
        if self.client is None:
            self.client = self._initialize_client()

        if limit is None:
            limit = settings.DEFAULT_QUERY_LIMIT

        try:
            search_params = {
                "collection_name": self.cucumber_collection,
                "query_vector": query_embedding,
                "limit": limit
            }

            if filter_conditions:
                search_params["query_filter"] = qdrant_models.Filter(
                    must=filter_conditions
                )

            search_results = self.client.search(**search_params)

            return [
                SearchResult(
                    id=str(result.id),
                    score=result.score,
                    payload=result.payload
                )
                for result in search_results
            ]
        except Exception as e:
            logger.error("Failed to search chunks: %s", str(e))
            raise

    def search_reports(self, query_embedding: List[float], limit: int = None) -> List[SearchResult]:
        """Search for reports similar to the query embedding."""
        # Make sure client is initialized
        if self.client is None:
            self.client = self._initialize_client()

        if limit is None:
            limit = settings.DEFAULT_QUERY_LIMIT

        try:
            filter_condition = qdrant_models.FieldCondition(
                key="type",
                match=qdrant_models.MatchValue(value="report")
            )

            search_results = self.client.search(
                collection_name=self.cucumber_collection,
                query_vector=query_embedding,
                query_filter=qdrant_models.Filter(
                    must=[filter_condition]
                ),
                limit=limit
            )

            return [
                SearchResult(
                    id=str(result.id),
                    score=result.score,
                    payload=result.payload
                )
                for result in search_results
            ]
        except Exception as e:
            logger.error("Failed to search reports: %s", str(e))
            raise

    def search_test_cases(self, query_embedding: List[float], report_id: Optional[str] = None, limit: int = None) -> \
    List[SearchResult]:
        """
        Search for test cases similar to the query embedding.
        Optionally filter by report_id.
        """
        # Make sure client is initialized
        if self.client is None:
            self.client = self._initialize_client()

        if limit is None:
            limit = settings.DEFAULT_QUERY_LIMIT

        try:
            filter_conditions = [
                qdrant_models.FieldCondition(
                    key="type",
                    match=qdrant_models.MatchValue(value="test_case")
                )
            ]

            if report_id:
                filter_conditions.append(
                    qdrant_models.FieldCondition(
                        key="report_id",
                        match=qdrant_models.MatchValue(value=report_id)
                    )
                )

            search_results = self.client.search(
                collection_name=self.cucumber_collection,
                query_vector=query_embedding,
                query_filter=qdrant_models.Filter(
                    must=filter_conditions
                ),
                limit=limit
            )

            return [
                SearchResult(
                    id=str(result.id),
                    score=result.score,
                    payload=result.payload
                )
                for result in search_results
            ]
        except Exception as e:
            logger.error("Failed to search test cases: %s", str(e))
            raise

    def search_test_steps(self, query_embedding: List[float], test_case_id: Optional[str] = None, limit: int = None) -> \
    List[SearchResult]:
        """
        Search for test steps similar to the query embedding.
        Optionally filter by test_case_id.
        """
        # Make sure client is initialized
        if self.client is None:
            self.client = self._initialize_client()

        if limit is None:
            limit = settings.DEFAULT_QUERY_LIMIT * 4  # Steps are typically more numerous

        try:
            filter_conditions = [
                qdrant_models.FieldCondition(
                    key="type",
                    match=qdrant_models.MatchValue(value="test_step")
                )
            ]

            if test_case_id:
                filter_conditions.append(
                    qdrant_models.FieldCondition(
                        key="test_case_id",
                        match=qdrant_models.MatchValue(value=test_case_id)
                    )
                )

            search_results = self.client.search(
                collection_name=self.cucumber_collection,
                query_vector=query_embedding,
                query_filter=qdrant_models.Filter(
                    must=filter_conditions
                ),
                limit=limit
            )

            return [
                SearchResult(
                    id=str(result.id),
                    score=result.score,
                    payload=result.payload
                )
                for result in search_results
            ]
        except Exception as e:
            logger.error("Failed to search test steps: %s", str(e))
            raise

    def search_features(self, query_embedding: List[float], limit: int = None) -> List[SearchResult]:
        """Search for features similar to the query embedding."""
        # Make sure client is initialized
        if self.client is None:
            self.client = self._initialize_client()

        if limit is None:
            limit = settings.DEFAULT_QUERY_LIMIT

        try:
            filter_condition = qdrant_models.FieldCondition(
                key="type",
                match=qdrant_models.MatchValue(value="feature")
            )

            search_results = self.client.search(
                collection_name=self.cucumber_collection,
                query_vector=query_embedding,
                query_filter=qdrant_models.Filter(
                    must=[filter_condition]
                ),
                limit=limit
            )

            return [
                SearchResult(
                    id=str(result.id),
                    score=result.score,
                    payload=result.payload
                )
                for result in search_results
            ]
        except Exception as e:
            logger.error("Failed to search features: %s", str(e))
            raise

    def search_build_info(self, query_embedding: List[float], limit: int = None) -> List[SearchResult]:
        """Search for build information similar to the query embedding."""
        # Make sure client is initialized
        if self.client is None:
            self.client = self._initialize_client()

        if limit is None:
            limit = settings.DEFAULT_QUERY_LIMIT

        try:
            search_results = self.client.search(
                collection_name=self.build_info_collection,
                query_vector=query_embedding,
                limit=limit
            )

            return [
                SearchResult(
                    id=str(result.id),
                    score=result.score,
                    payload=result.payload
                )
                for result in search_results
            ]
        except Exception as e:
            logger.error("Failed to search build info: %s", str(e))
            raise

    def delete_report(self, report_id: str) -> None:
        """Delete a report and all its related test cases and steps."""
        # Make sure client is initialized
        if self.client is None:
            self.client = self._initialize_client()

        try:
            # First find all test cases associated with this report
            filter_condition = qdrant_models.FieldCondition(
                key="report_id",
                match=qdrant_models.MatchValue(value=report_id)
            )

            test_cases = self.client.scroll(
                collection_name=self.cucumber_collection,
                scroll_filter=qdrant_models.Filter(
                    must=[filter_condition]
                ),
                limit=1000  # Adjust based on expected maximum number of test cases
            )[0]

            # Delete each test case and its associated steps
            for test_case in test_cases:
                self.delete_test_case(str(test_case.id))

            # Finally delete the report
            self.client.delete(
                collection_name=self.cucumber_collection,
                points_selector=qdrant_models.PointIdsList(
                    points=[report_id]
                )
            )
            logger.info("Deleted report with ID: %s", report_id)
        except Exception as e:
            logger.error("Failed to delete report %s: %s", report_id, str(e))
            raise

    def delete_test_case(self, test_case_id: str) -> None:
        """Delete a test case and all its related steps."""
        # Make sure client is initialized
        if self.client is None:
            self.client = self._initialize_client()

        try:
            # First find all test steps associated with this test case
            filter_condition = qdrant_models.FieldCondition(
                key="test_case_id",
                match=qdrant_models.MatchValue(value=test_case_id)
            )

            # Delete all related test steps
            self.client.delete(
                collection_name=self.cucumber_collection,
                points_selector=qdrant_models.FilterSelector(
                    filter=qdrant_models.Filter(
                        must=[filter_condition]
                    )
                )
            )

            # Then delete the test case
            self.client.delete(
                collection_name=self.cucumber_collection,
                points_selector=qdrant_models.PointIdsList(
                    points=[test_case_id]
                )
            )
            logger.info("Deleted test case with ID: %s", test_case_id)
        except Exception as e:
            logger.error("Failed to delete test case %s: %s", test_case_id, str(e))
            raise

    def delete_build_info(self, build_id: str) -> None:
        """Delete build information."""
        # Make sure client is initialized
        if self.client is None:
            self.client = self._initialize_client()

        try:
            self.client.delete(
                collection_name=self.build_info_collection,
                points_selector=qdrant_models.PointIdsList(
                    points=[build_id]
                )
            )
            logger.info("Deleted build info with ID: %s", build_id)
        except Exception as e:
            logger.error("Failed to delete build info %s: %s", build_id, str(e))
            raise
