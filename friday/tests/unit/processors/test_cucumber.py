"""
Unit tests for CucumberProcessor
"""
import json
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch, ANY
import pytest

from app.core.processors.cucumber import CucumberProcessor
from app.core.rag.embeddings import EmbeddingService
from app.models.domain import ChunkMetadata, Feature, Scenario, Step, TestRun, TestStatus, TextChunk, TextEmbedding
from app.services.vector_db import VectorDBService


class TestCucumberProcessor:
    """Test suite for CucumberProcessor"""

    @pytest.fixture
    def mock_embedding_service(self):
        """Create a mock EmbeddingService"""
        mock_service = MagicMock(spec=EmbeddingService)
        mock_service.chunk_text = MagicMock(return_value=["Chunk 1"])
        mock_service.embed_chunks = AsyncMock(return_value=[
            TextEmbedding(
                id="embedding-id-1",
                vector=[0.1] * 384,
                text="Chunk 1",
                metadata=ChunkMetadata(
                    test_run_id="test-run-1",
                    feature_id="feature-1",
                    scenario_id="scenario-1",
                    build_id="build-1",
                    chunk_type="scenario",
                    tags=["@test"]
                )
            )
        ])
        return mock_service

    @pytest.fixture
    def mock_vector_db_service(self):
        """Create a mock VectorDBService"""
        mock_service = MagicMock(spec=VectorDBService)
        mock_service.insert_embeddings = AsyncMock(return_value=["embedding-id-1"])
        return mock_service

    @pytest.fixture
    def processor(self, mock_embedding_service, mock_vector_db_service):
        """Create a CucumberProcessor instance for testing"""
        return CucumberProcessor(
            embedding_service=mock_embedding_service,
            vector_db_service=mock_vector_db_service
        )

    @pytest.fixture
    def sample_cucumber_json(self):
        """Create a sample Cucumber JSON report for testing"""
        return [
            {
                "id": "user-authentication",
                "name": "User Authentication",
                "description": "Tests for user authentication features",
                "uri": "features/authentication.feature",
                "tags": [
                    {"name": "@authentication"},
                    {"name": "@critical"}
                ],
                "elements": [
                    {
                        "id": "user-authentication;successful-login",
                        "name": "Successful login",
                        "type": "scenario",
                        "description": "Verifies that users can log in with valid credentials",
                        "tags": [
                            {"name": "@login"},
                            {"name": "@smoke"}
                        ],
                        "steps": [
                            {
                                "keyword": "Given ",
                                "name": "the user is on the login page",
                                "match": {"location": "step_definitions/auth_steps.js:12"},
                                "result": {
                                    "status": "passed",
                                    "duration": 123456789
                                }
                            },
                            {
                                "keyword": "When ",
                                "name": "they enter valid credentials",
                                "match": {"location": "step_definitions/auth_steps.js:18"},
                                "result": {
                                    "status": "passed",
                                    "duration": 234567890
                                }
                            },
                            {
                                "keyword": "Then ",
                                "name": "they should be redirected to the dashboard",
                                "match": {"location": "step_definitions/auth_steps.js:25"},
                                "result": {
                                    "status": "passed",
                                    "duration": 345678901
                                }
                            }
                        ]
                    },
                    {
                        "id": "user-authentication;failed-login",
                        "name": "Failed login",
                        "type": "scenario",
                        "description": "Verifies that users see an error with invalid credentials",
                        "tags": [
                            {"name": "@login"},
                            {"name": "@negative"}
                        ],
                        "steps": [
                            {
                                "keyword": "Given ",
                                "name": "the user is on the login page",
                                "match": {"location": "step_definitions/auth_steps.js:12"},
                                "result": {
                                    "status": "passed",
                                    "duration": 123456789
                                }
                            },
                            {
                                "keyword": "When ",
                                "name": "they enter invalid credentials",
                                "match": {"location": "step_definitions/auth_steps.js:22"},
                                "result": {
                                    "status": "passed",
                                    "duration": 234567890
                                }
                            },
                            {
                                "keyword": "Then ",
                                "name": "they should see an error message",
                                "match": {"location": "step_definitions/auth_steps.js:30"},
                                "result": {
                                    "status": "failed",
                                    "duration": 345678901,
                                    "error_message": "Expected error message to be displayed but no error was shown"
                                }
                            }
                        ]
                    }
                ]
            }
        ]

    @pytest.mark.asyncio
    async def test_process_cucumber_reports(self, processor, sample_cucumber_json):
        """Test processing Cucumber JSON reports"""
        # Setup
        report_bytes = json.dumps(sample_cucumber_json).encode('utf-8')
        metadata = {
            "build_id": "build-123",
            "tags": ["@regression"],
            "metadata": {"version": "1.0.0"}
        }

        # Mock UUID generation to get consistent test run ID
        with patch('uuid.uuid4', return_value="test-run-123"):
            # Execute
            result = await processor.process([report_bytes], metadata)

            # Assert
            assert result["success"] is True
            assert result["test_run_id"] == "test-run-123"
            assert result["processed_features"] == 1
            assert result["processed_scenarios"] == 2
            assert "message" in result

    @pytest.mark.asyncio
    async def test_process_invalid_json(self, processor):
        """Test processing invalid JSON data"""
        # Setup
        invalid_json = b"This is not valid JSON"
        metadata = {"build_id": "build-123"}

        # Execute
        result = await processor.process([invalid_json], metadata)

        # Assert
        assert result["success"] is False
        assert "No valid Cucumber reports found" in result["message"]

    @pytest.mark.asyncio
    async def test_parse_features(self, processor, sample_cucumber_json):
        """Test parsing Cucumber features from JSON"""
        # Execute
        features = processor._parse_features(sample_cucumber_json)

        # Assert
        assert len(features) == 1
        feature = features[0]

        # Check feature properties
        assert feature.id == "user-authentication"
        assert feature.name == "User Authentication"
        assert feature.description == "Tests for user authentication features"
        assert feature.file_path == "features/authentication.feature"
        assert len(feature.tags) == 2
        assert "@authentication" in feature.tags
        assert "@critical" in feature.tags

        # Check scenarios
        assert len(feature.scenarios) == 2

        # Check first scenario (successful login)
        scenario1 = feature.scenarios[0]
        assert scenario1.name == "Successful login"
        assert scenario1.status == TestStatus.PASSED
        assert len(scenario1.steps) == 3
        assert all(step.status == TestStatus.PASSED for step in scenario1.steps)

        # Check second scenario (failed login)
        scenario2 = feature.scenarios[1]
        assert scenario2.name == "Failed login"
        assert scenario2.status == TestStatus.FAILED
        assert len(scenario2.steps) == 3
        assert scenario2.steps[2].status == TestStatus.FAILED
        assert "Expected error message" in scenario2.steps[2].error_message

    @pytest.mark.asyncio
    async def test_process_test_run_for_rag(self, processor, mock_embedding_service, mock_vector_db_service):
        """Test processing a test run for RAG"""
        # Setup a test run with features and scenarios
        test_run = TestRun(
            id="test-run-1",
            timestamp=datetime.utcnow(),
            features=[
                Feature(
                    id="feature-1",
                    name="Feature 1",
                    description="Feature description",
                    file_path="features/feature1.feature",
                    scenarios=[
                        Scenario(
                            id="scenario-1",
                            name="Scenario 1",
                            description="Scenario description",
                            status=TestStatus.PASSED,
                            steps=[
                                Step(
                                    name="Step 1",
                                    status=TestStatus.PASSED,
                                    duration=123456789,
                                    keyword="Given ",
                                    location="steps.js:10"
                                )
                            ],
                            tags=["@tag1"]
                        ),
                        Scenario(
                            id="scenario-2",
                            name="Scenario 2",
                            description="Another scenario",
                            status=TestStatus.FAILED,
                            steps=[
                                Step(
                                    name="Step 2",
                                    status=TestStatus.FAILED,
                                    duration=234567890,
                                    error_message="Test failed",
                                    keyword="When ",
                                    location="steps.js:20"
                                )
                            ],
                            tags=["@tag2"]
                        )
                    ],
                    tags=["@feature"]
                )
            ],
            build_info=None,
            tags=["@regression"]
        )

        # Execute
        await processor._process_test_run_for_rag(test_run)

        # Assert
        # Count the number of times process_text was called
        assert mock_embedding_service.chunk_text.call_count >= 3

        # Should have been called for feature, scenarios, and the error
        feature_call = False
        scenario_calls = 0
        error_call = False

        # Check each call to chunk_text to see what type of content it processed
        for call in mock_embedding_service.chunk_text.call_args_list:
            text = call[0][0]  # First arg of first positional argument
            if "Feature: Feature 1" in text:
                feature_call = True
            elif "Scenario: Scenario" in text:
                scenario_calls += 1
            elif "Error in" in text and "Test failed" in text:
                error_call = True

        assert feature_call
        assert scenario_calls == 2  # Two scenarios
        assert error_call

        # Check that the vector DB received embeddings
        assert mock_vector_db_service.insert_embeddings.call_count >= 3