# Friday Service

A microservice that analyzes Cucumber test reports using a Retrieval Augmented Generation (RAG) pipeline.

## Overview

The Friday service processes test reports, extracts information, stores it in a vector database, and provides natural language query capabilities to analyze test results.

## Architecture

The service follows clean architecture principles with clear separation of concerns:

1. **API Layer**: Handles HTTP requests and responses
2. **Core Layer**: Contains business logic and domain models
3. **Service Layer**: Integrates with external services (Qdrant, Ollama)
4. **Models Layer**: Defines data structures

## Key Components

1. **Processors**: Process input data (Cucumber reports, build info)
2. **RAG Pipeline**: Embedding, Retrieval, and Generation services
3. **External Services**: Vector database and LLM services
4. **API Endpoints**: Process data and query test results

## Getting Started

### Prerequisites

- Docker and Docker Compose
- Python 3.11+

### Local Development

1. Clone the repository:

```bash
git clone <repository-url>
cd friday
```

2. Create a `.env` file from the example:

```bash
cp .env.example .env
```

3. Start the services with Docker Compose:

```bash
docker-compose up -d
```

4. The API will be available at http://localhost:8000

### Development with VS Code

The project includes a `.devcontainer` configuration for VS Code:

1. Open the project in VS Code
2. When prompted, click "Reopen in Container"
3. VS Code will build and start the development environment

## API Documentation

Once the service is running, you can access the API documentation at:

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

### Key Endpoints

- `/health` - Health check endpoint
- `/processor/cucumber-reports` - Process Cucumber test reports
- `/processor/build-info` - Process build information
- `/query` - Query test data using natural language
- `/stats` - Get test statistics
- `/test-results` - Get detailed test results for dashboard visualization

## Contributing

1. Follow the clean architecture principles
2. Maintain cyclomatic complexity between 5-7 for all functions
3. Write comprehensive tests for your changes
4. Run tests and linting before submitting changes
