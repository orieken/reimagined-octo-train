import logging
from typing import List, Dict, Any
from uuid import UUID

from qdrant_client import QdrantClient
from qdrant_client.http import models as qdrant_models
from app.config import settings

logger = logging.getLogger(__name__)

COLLECTION_NAME = "test_artifacts"

class VectorDBService:
    def __init__(self):
        self.client = QdrantClient(
            url=settings.QDRANT_URL,
            timeout=10,
        )
        self.cucumber_collection = settings.CUCUMBER_COLLECTION or COLLECTION_NAME
        self.build_info_collection = settings.BUILD_INFO_COLLECTION or "build_info"

    async def ping(self) -> bool:
        try:
            collections = await self.client.get_collections()
            logger.info(f"✅ Vector DB collections: {collections.collections}")
            return True
        except Exception as e:
            logger.error(f"❌ Vector DB ping failed: {e}")
            return False

    def _build_payload(self, type_: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "type": type_,
            **metadata
        }

    def store_embedding(self, item_id: str, embedding: List[float], metadata: Dict[str, Any], type_: str):
        payload = self._build_payload(type_, metadata)
        return self.client.upsert(
            collection_name=COLLECTION_NAME,
            points=[
                qdrant_models.PointStruct(
                    id=str(item_id),
                    vector=embedding,
                    payload=payload,
                )
            ]
        )

    def store_test_run_embedding(self, test_run_id: UUID, embedding: List[float], metadata: Dict[str, Any]):
        return self.store_embedding(str(test_run_id), embedding, metadata, type_="report")

    def store_feature_embedding(self, feature_id: UUID, embedding: List[float], metadata: Dict[str, Any]):
        return self.store_embedding(str(feature_id), embedding, metadata, type_="feature")

    def store_scenario_embedding(self, scenario_id: UUID, embedding: List[float], metadata: Dict[str, Any]):
        return self.store_embedding(str(scenario_id), embedding, metadata, type_="scenario")

    def store_step_embedding(self, step_id: UUID, embedding: List[float], metadata: Dict[str, Any]):
        return self.store_embedding(str(step_id), embedding, metadata, type_="step")

    def store_build_embedding(self, build_id: UUID, embedding: List[float], metadata: Dict[str, Any]):
        return self.store_embedding(str(build_id), embedding, metadata, type_="build_info")
