"""
Friday Service - Cucumber Test Analysis with RAG Pipeline
Main application entry point
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi

from app.api.routes import processor, query, stats, test_results, health, trends, failures
from app.config import settings
from app.services.vector_db import VectorDBService

app = FastAPI(
    title="Friday Service",
    description="Cucumber Test Analysis with RAG Pipeline",
    version="0.1.0",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(processor.router, prefix="/processor", tags=["Processors"])
app.include_router(query.router, prefix="/query", tags=["Queries"])
app.include_router(stats.router, prefix="/stats", tags=["Statistics"])
app.include_router(test_results.router, tags=["Test Results"])
app.include_router(trends.router, tags=["Trends"])
app.include_router(failures.router, tags=["Failures"])
app.include_router(health.router, tags=["Health"])


# Custom OpenAPI schema
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title="Friday Service API",
        version="0.1.0",
        description="API for analyzing Cucumber test reports using RAG pipeline",
        routes=app.routes,
    )

    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi


@app.get("/", tags=["Health"])
async def root():
    """Root endpoint"""
    return {
        "status": "success",
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "message": f"Welcome to the {settings.APP_NAME}",
    }


@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    # Initialize the vector database
    vector_db_service = VectorDBService(
        url=settings.QDRANT_URL,
        collection_name=settings.QDRANT_COLLECTION,
        vector_size=settings.QDRANT_VECTOR_SIZE
    )
    await vector_db_service.initialize()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)