# tests/unit/services/test_vector_db_service_s.py
import pytest
from unittest.mock import MagicMock, patch
from qdrant_client.http import models as qdrant_models

from app.services.vector_db import VectorDBService, SearchResult
from app.models.domain import Scenario, Step, TestRun, BuildInfo, Feature, TextChunk, ChunkMetadata
from app.config import settings


@pytest.fixture
def mock_qdrant_client():
    with patch('app.services.vector_db.QdrantClient') as mock_client:
        mock_instance = MagicMock()
        mock_client.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def vector_db_service(mock_qdrant_client):
    service = VectorDBService()
    service.client = mock_qdrant_client
    return service


def test_initialize_client():
    with patch('app.services.vector_db.QdrantClient') as mock_client:
        mock_instance = MagicMock()
        mock_client.return_value = mock_instance

        service = VectorDBService()

        mock_client.assert_called_once_with(url=settings.QDRANT_URL)
        mock_instance.get_collections.assert_called_once()


def test_initialize_client_error():
    with patch('app.services.vector_db.QdrantClient') as mock_client:
        mock_instance = MagicMock()
        mock_instance.get_collections.side_effect = Exception("Connection error")
        mock_client.return_value = mock_instance

        with pytest.raises(ConnectionError):
            VectorDBService()


def test_ensure_collections_exist(vector_db_service):
    # Setup
    mock_collection = MagicMock()
    mock_collection.name = "existing_collection"
    vector_db_service.client.get_collections.return_value = MagicMock(
        collections=[mock_collection]
    )

    # Execute
    vector_db_service.ensure_collections_exist()

    # Assert
    # Should have been called for each collection not in the existing collections
    assert vector_db_service.client.create_collection.call_count == 2

    # Check the calls had correct parameters
    calls = vector_db_service.client.create_collection.call_args_list
    collection_names = [call[1]['collection_name'] for call in calls]

    assert settings.CUCUMBER_COLLECTION in collection_names
    assert settings.BUILD_INFO_COLLECTION in collection_names


def test_store_chunk(vector_db_service):
    # Setup
    chunk_id = "chunk-123"
    embedding = [0.1, 0.2, 0.3]
    text_chunk = TextChunk(
        id=chunk_id,
        text="Sample text for embedding",
        metadata=ChunkMetadata(
            source="test_document.txt",
            source_id="doc-123",
            chunk_index=1,
            document_type="text"
        ),
        chunk_size=100
    )

    # Execute
    vector_db_service.store_chunk(text_chunk, embedding)

    # Assert
    vector_db_service.client.upsert.assert_called_once()
    call_args = vector_db_service.client.upsert.call_args[1]

    assert call_args["collection_name"] == settings.CUCUMBER_COLLECTION
    assert len(call_args["points"]) == 1
    assert call_args["points"][0].id == chunk_id
    assert call_args["points"][0].vector == embedding

    # Check the payload
    payload = call_args["points"][0].payload
    assert payload["text"] == text_chunk.text
    assert payload["chunk_size"] == text_chunk.chunk_size
    assert "metadata" in payload


def test_store_report(vector_db_service):
    # Setup
    report_id = "report-123"
    embedding = [0.1, 0.2, 0.3]
    report = TestRun(
        id=report_id,
        name="Test Report",
        status="PASSED",
        timestamp="2023-01-01T12:00:00Z",
        duration=120,
        environment="test",
        tags=["regression", "api"],
        scenarios=[]
    )

    # Execute
    vector_db_service.store_report(report_id, embedding, report)

    # Assert
    vector_db_service.client.upsert.assert_called_once()
    call_args = vector_db_service.client.upsert.call_args[1]

    assert call_args["collection_name"] == settings.CUCUMBER_COLLECTION
    assert len(call_args["points"]) == 1
    assert call_args["points"][0].id == report_id
    assert call_args["points"][0].vector == embedding

    # Check the payload is report without scenarios
    payload = call_args["points"][0].payload
    assert "scenarios" not in payload
    assert payload["id"] == report.id
    assert payload["name"] == report.name
    assert payload["type"] == "report"


def test_search_reports(vector_db_service):
    # Setup
    query_embedding = [0.1, 0.2, 0.3]
    limit = 5

    # Create mock search results
    mock_result = MagicMock()
    mock_result.id = "report-123"
    mock_result.score = 0.95
    mock_result.payload = {"id": "report-123", "name": "Test Report", "type": "report"}

    vector_db_service.client.search.return_value = [mock_result]

    # Execute
    results = vector_db_service.search_reports(query_embedding, limit)

    # Assert
    vector_db_service.client.search.assert_called_once()
    call_args = vector_db_service.client.search.call_args[1]

    assert call_args["collection_name"] == settings.CUCUMBER_COLLECTION
    assert call_args["query_vector"] == query_embedding
    assert call_args["limit"] == limit
    assert "query_filter" in call_args

    # Check filter condition targets type=report
    filter_condition = call_args["query_filter"].must[0]
    assert filter_condition.key == "type"
    assert filter_condition.match.value == "report"

    # Check results
    assert len(results) == 1
    assert isinstance(results[0], SearchResult)
    assert results[0].id == "report-123"
    assert results[0].score == 0.95
    assert results[0].payload == {"id": "report-123", "name": "Test Report", "type": "report"}


def test_search_test_cases(vector_db_service):
    # Setup
    query_embedding = [0.1, 0.2, 0.3]
    report_id = "report-123"
    limit = 10

    # Create mock search results
    mock_result = MagicMock()
    mock_result.id = "tc-123"
    mock_result.score = 0.85
    mock_result.payload = {
        "id": "tc-123",
        "name": "Test Case 1",
        "type": "test_case",
        "report_id": report_id
    }

    vector_db_service.client.search.return_value = [mock_result]

    # Execute
    results = vector_db_service.search_test_cases(query_embedding, report_id, limit)

    # Assert
    vector_db_service.client.search.assert_called_once()
    call_args = vector_db_service.client.search.call_args[1]

    assert call_args["collection_name"] == settings.CUCUMBER_COLLECTION
    assert call_args["query_vector"] == query_embedding
    assert call_args["limit"] == limit
    assert "query_filter" in call_args

    # Check filter conditions
    filter_conditions = call_args["query_filter"].must
    assert len(filter_conditions) == 2

    type_condition = [c for c in filter_conditions if c.key == "type"][0]
    report_condition = [c for c in filter_conditions if c.key == "report_id"][0]

    assert type_condition.match.value == "test_case"
    assert report_condition.match.value == report_id

    # Check results
    assert len(results) == 1
    assert results[0].id == "tc-123"


def test_delete_report_cascade(vector_db_service):
    # Setup
    report_id = "report-123"

    # Mock test cases
    test_case1 = MagicMock()
    test_case1.id = "tc-1"
    test_case2 = MagicMock()
    test_case2.id = "tc-2"

    vector_db_service.client.scroll.return_value = [[test_case1, test_case2], None]

    # Mock the delete_test_case method
    vector_db_service.delete_test_case = MagicMock()

    # Execute
    vector_db_service.delete_report(report_id)

    # Assert
    # Should have called scroll with the right filter
    vector_db_service.client.scroll.assert_called_once()
    call_args = vector_db_service.client.scroll.call_args[1]
    assert call_args["collection_name"] == settings.CUCUMBER_COLLECTION

    # Should have deleted each test case
    assert vector_db_service.delete_test_case.call_count == 2
    vector_db_service.delete_test_case.assert_any_call("tc-1")
    vector_db_service.delete_test_case.assert_any_call("tc-2")

    # Should have deleted the report
    vector_db_service.client.delete.assert_called_once()
    report_delete_args = vector_db_service.client.delete.call_args[1]
    assert report_delete_args["collection_name"] == settings.CUCUMBER_COLLECTION
    assert isinstance(report_delete_args["points_selector"], qdrant_models.PointIdsList)
    assert report_delete_args["points_selector"].points == [report_id]