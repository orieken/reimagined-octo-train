"""
Build information processor for Friday
"""
from typing import Dict, Any

from app.core.processors.base import BaseProcessor
from app.models.domain import BuildInfo, ChunkMetadata


class BuildInfoProcessor(BaseProcessor):
    """Processor for build information"""

    async def process(self, data: BuildInfo, metadata: Dict) -> Dict:
        """
        Process build information

        Args:
            data: Build information to process
            metadata: Additional metadata

        Returns:
            Processing results
        """
        # Create metadata for vector DB
        chunk_metadata = ChunkMetadata(
            test_run_id=metadata.get("test_run_id", ""),
            feature_id=None,
            scenario_id=None,
            build_id=data.build_id,
            chunk_type="build_info",
            tags=[]
        )

        # Create text representation of build info
        build_text = f"""
        Build ID: {data.build_id}
        Build Number: {data.build_number}
        Branch: {data.branch}
        Commit Hash: {data.commit_hash}
        Build Date: {data.build_date.isoformat()}
        """

        if data.build_url:
            build_text += f"Build URL: {data.build_url}\n"

        if data.metadata:
            build_text += "Additional Metadata:\n"
            for key, value in data.metadata.items():
                build_text += f"- {key}: {value}\n"

        # Process text for RAG
        await self.process_text(build_text, chunk_metadata.dict())

        return {
            "build_id": data.build_id,
            "success": True,
            "message": "Successfully processed build information"
        }