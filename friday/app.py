# app.py - Main FastAPI application file
from fastapi import FastAPI, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Dict, Any, Optional
import uvicorn
import json
import os
import time
from datetime import datetime
import httpx
from pydantic import BaseModel
import numpy as np
from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient
from qdrant_client.http import models as qdrant_models

from friday.app.config import settings

# Initialize the FastAPI app
app = FastAPI(
    title="Friday - Test Analysis RAG Pipeline",
    description="A microservice for processing and analyzing Cucumber test reports with RAG",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration
OLLAMA_API_URL = os.getenv("OLLAMA_API_URL", "http://ollama:11434")
QDRANT_URL = os.getenv("QDRANT_URL", "http://qdrant:6333")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
LLM_MODEL = os.getenv("LLM_MODEL", "llama3")
VECTOR_DIM = settings.VECTOR_DIMENSION  # Dimension for all-MiniLM-L6-v2

# Initialize the embedding model
model = SentenceTransformer(EMBEDDING_MODEL)

# Initialize Qdrant client
qdrant_client = QdrantClient(url=QDRANT_URL)

# Ensure collections exist
COLLECTIONS = {
    "test_artifacts": {
        "name": "test_artifacts",
        "vector_size": VECTOR_DIM
    },
    "build_info": {
        "name": "build_info",
        "vector_size": VECTOR_DIM
    }
}


# Initialize collections at startup
@app.on_event("startup")
async def startup_event():
    for collection_info in COLLECTIONS.values():
        try:
            qdrant_client.get_collection(collection_info["name"])
        except Exception:
            qdrant_client.create_collection(
                collection_name=collection_info["name"],
                vectors_config=qdrant_models.VectorParams(
                    size=collection_info["vector_size"],
                    distance=qdrant_models.Distance.COSINE
                )
            )
    print("✅ Collections initialized")


# Pydantic models
class CucumberReport(BaseModel):
    report_json: List[Dict[str, Any]]
    build_id: Optional[str] = None
    timestamp: Optional[str] = None


class BuildInfo(BaseModel):
    build_id: str
    build_number: str
    timestamp: str
    branch: str
    commit_hash: str
    additional_info: Optional[Dict[str, Any]] = None


class Query(BaseModel):
    query: str
    limit: Optional[int] = 5


# Helper functions
def extract_text_from_cucumber_report(report):
    """Extract meaningful text from cucumber report for embedding"""
    texts = []
    metadata = []

    for feature in report:
        feature_text = f"Feature: {feature.get('name', 'Unknown')}. {feature.get('description', '')}"

        for element in feature.get('elements', []):
            scenario_text = f"Scenario: {element.get('name', 'Unknown')}. Type: {element.get('type', 'Unknown')}"

            step_texts = []
            status = "passed"
            error_message = ""

            for step in element.get('steps', []):
                if step.get('hidden', False):
                    continue

                step_text = f"{step.get('keyword', '')} {step.get('name', '')}"
                step_texts.append(step_text)

                # Check for failures
                if step.get('result', {}).get('status') == 'failed':
                    status = "failed"
                    error_message = step.get('result', {}).get('error_message', '')

            # Combine all text
            combined_text = f"{feature_text} {scenario_text} Steps: {' '.join(step_texts)}"

            # Create metadata
            meta = {
                "feature_name": feature.get('name'),
                "feature_id": feature.get('id'),
                "scenario_name": element.get('name'),
                "scenario_id": element.get('id'),
                "uri": feature.get('uri'),
                "status": status,
                "error_message": error_message,
                "tags": [tag.get('name') for tag in element.get('tags', [])]
            }

            texts.append(combined_text)
            metadata.append(meta)

    return texts, metadata


async def query_ollama(prompt, context=None):
    """Query the Ollama API with a prompt and optional context"""
    async with httpx.AsyncClient(timeout=60.0) as client:
        payload = {
            "model": LLM_MODEL,
            "prompt": prompt,
            "stream": False
        }

        if context:
            payload["context"] = context

        response = await client.post(f"{OLLAMA_API_URL}/api/generate", json=payload)

        if response.status_code != 200:
            raise HTTPException(status_code=500, detail=f"Error from LLM API: {response.text}")

        return response.json()


# API Endpoints
@app.post("/processor/cucumber-reports")
async def process_cucumber_reports(report: CucumberReport):
    """Process and index cucumber reports using RAG pipeline"""

    # Generate timestamp if not provided
    if not report.timestamp:
        report.timestamp = datetime.now().isoformat()

    # Generate build_id if not provided
    if not report.build_id:
        report.build_id = f"build_{int(time.time())}"

    # Extract text from reports
    texts, metadata = extract_text_from_cucumber_report(report.report_json)

    # Create embeddings
    embeddings = model.encode(texts)

    # Add additional metadata
    for meta in metadata:
        meta["build_id"] = report.build_id
        meta["timestamp"] = report.timestamp

    # Create Qdrant points
    points = []
    for i, (embedding, meta) in enumerate(zip(embeddings, metadata)):
        points.append(
            qdrant_models.PointStruct(
                id=i,
                vector=embedding.tolist(),
                payload=meta
            )
        )

    # Add to vector database
    operation_info = qdrant_client.upsert(
        collection_name=COLLECTIONS["test_artifacts"]["name"],
        points=points
    )

    return {
        "status": "success",
        "message": f"Processed {len(texts)} scenarios from cucumber reports",
        "build_id": report.build_id,
        "timestamp": report.timestamp
    }


@app.post("/processor/build-info")
async def process_build_info(build_info: BuildInfo):
    """Process and index build information"""

    # Convert build info to text for embedding
    build_text = f"Build ID: {build_info.build_id}. Build Number: {build_info.build_number}. "
    build_text += f"Branch: {build_info.branch}. Commit: {build_info.commit_hash}. "
    build_text += f"Timestamp: {build_info.timestamp}. "

    if build_info.additional_info:
        for key, value in build_info.additional_info.items():
            build_text += f"{key}: {value}. "

    # Create embedding
    embedding = model.encode([build_text])[0]

    # Create metadata
    meta = build_info.dict()

    # Add to vector database
    operation_info = qdrant_client.upsert(
        collection_name=COLLECTIONS["build_info"]["name"],
        points=[
            qdrant_models.PointStruct(
                id=int(time.time()),
                vector=embedding.tolist(),
                payload=meta
            )
        ]
    )

    return {
        "status": "success",
        "message": "Build information processed successfully",
        "build_id": build_info.build_id
    }


@app.post("/query")
async def query_test_data(query_request: Query):
    """Query the test data using RAG pipeline"""

    # Encode the query
    query_embedding = model.encode([query_request.query])[0]

    # Search in both collections
    cucumber_results = qdrant_client.search(
        collection_name=COLLECTIONS["test_artifacts"]["name"],
        query_vector=query_embedding.tolist(),
        limit=query_request.limit
    )

    build_results = qdrant_client.search(
        collection_name=COLLECTIONS["build_info"]["name"],
        query_vector=query_embedding.tolist(),
        limit=3
    )

    # Combine results for context
    context = "Test Reports and Build Information:\n\n"

    # Add cucumber reports context
    for point in cucumber_results:
        payload = point.payload
        context += f"Feature: {payload.get('feature_name')}\n"
        context += f"Scenario: {payload.get('scenario_name')}\n"
        context += f"Status: {payload.get('status')}\n"
        if payload.get('status') == "failed":
            context += f"Error: {payload.get('error_message')}\n"
        context += f"Tags: {', '.join(payload.get('tags', []))}\n"
        context += f"Build ID: {payload.get('build_id')}\n\n"

    # Add build info context
    for point in build_results:
        payload = point.payload
        context += f"Build ID: {payload.get('build_id')}\n"
        context += f"Build Number: {payload.get('build_number')}\n"
        context += f"Branch: {payload.get('branch')}\n"
        context += f"Commit: {payload.get('commit_hash')}\n"
        context += f"Timestamp: {payload.get('timestamp')}\n\n"

    # Create prompt for LLM
    prompt = f"""
You are an assistant specialized in analyzing test reports and build data.
Use the following information to answer the user's query:

{context}

Query: {query_request.query}

Provide a detailed but concise analysis that answers the query directly.
Include relevant test information, statistics, failure analysis, and trends if applicable.
"""

    # Query LLM
    llm_response = await query_ollama(prompt)

    return {
        "query": query_request.query,
        "response": llm_response.get("response", ""),
        "sources": [
            {
                "feature": point.payload.get("feature_name"),
                "scenario": point.payload.get("scenario_name"),
                "similarity": point.score
            } for point in cucumber_results
        ],
        "build_info": [
            {
                "build_id": point.payload.get("build_id"),
                "build_number": point.payload.get("build_number"),
                "similarity": point.score
            } for point in build_results
        ]
    }


@app.get("/stats")
async def get_statistics():
    """Get overall statistics about the test data"""

    # Get all points from cucumber reports
    report_points = qdrant_client.scroll(
        collection_name=COLLECTIONS["test_artifacts"]["name"],
        limit=10000,
        with_payload=True,
        with_vectors=False
    )[0]

    # Calculate statistics
    total_scenarios = len(report_points)

    if total_scenarios == 0:
        return {
            "status": "success",
            "message": "No test data available",
            "statistics": {}
        }

    passed_scenarios = sum(1 for point in report_points if point.payload.get("status") == "passed")
    failed_scenarios = total_scenarios - passed_scenarios

    # Get unique builds
    build_ids = set(point.payload.get("build_id") for point in report_points)

    # Extract tags
    all_tags = []
    for point in report_points:
        all_tags.extend(point.payload.get("tags", []))

    tag_counts = {}
    for tag in all_tags:
        tag_counts[tag] = tag_counts.get(tag, 0) + 1

    # Top 10 tags by frequency
    top_tags = sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)[:10]

    return {
        "status": "success",
        "statistics": {
            "total_scenarios": total_scenarios,
            "passed_scenarios": passed_scenarios,
            "failed_scenarios": failed_scenarios,
            "pass_rate": passed_scenarios / total_scenarios if total_scenarios > 0 else 0,
            "unique_builds": len(build_ids),
            "top_tags": dict(top_tags)
        }
    }


if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=int(os.getenv("PORT", 4000)), reload=True)