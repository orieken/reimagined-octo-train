# app/services/llm.py
from typing import List, Dict, Any, Optional
import logging
import json
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from app.config import settings

logger = logging.getLogger(__name__)


class LLMServiceException(Exception):
    """Base exception for LLM service errors."""
    pass


class LLMService:
    """Service for interacting with Ollama LLM service."""

    def __init__(self, url: Optional[str] = None, model: Optional[str] = None,
                 timeout: Optional[int] = None, api_key: Optional[str] = None):
        """
        Initialize the LLM service with configuration.

        Args:
            url: The API URL for Ollama (defaults to settings.OLLAMA_API_URL)
            model: The LLM model to use (defaults to settings.LLM_MODEL)
            timeout: Request timeout in seconds (defaults to settings.LLM_TIMEOUT)
            api_key: API key for authentication (optional)
        """
        self.base_url = (url or settings.OLLAMA_API_URL).rstrip('/')
        self.model = model or settings.LLM_MODEL
        self.timeout = timeout or settings.LLM_TIMEOUT
        self.api_key = api_key
        self._check_connection()

    def _check_connection(self) -> None:
        """Check if the connection to Ollama is working."""
        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.get(f"{self.base_url}/api/tags")
                if response.status_code != 200:
                    raise LLMServiceException(f"Failed to connect to Ollama: {response.text}")

                # Check if our required model is available
                models = response.json().get("models", [])
                available_models = [model.get("name") for model in models]

                if self.model not in available_models:
                    logger.warning("Model %s not found in Ollama. Available models: %s",
                                   self.model, ", ".join(available_models))

            logger.info("Successfully connected to Ollama at %s", self.base_url)
        except Exception as e:
            logger.error("Failed to connect to Ollama: %s", str(e))
            raise LLMServiceException(f"Could not connect to Ollama: {str(e)}")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type(httpx.HTTPError)
    )
    async def generate_embedding(self, text: str) -> List[float]:
        """Generate embeddings for the provided text."""
        if not text.strip():
            raise ValueError("Cannot generate embedding for empty text")

        try:
            headers = {}
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/api/embeddings",
                    json={
                        "model": self.model,
                        "prompt": text
                    },
                    headers=headers
                )

                if response.status_code != 200:
                    logger.error("Embedding generation failed: %s", response.text)
                    raise LLMServiceException(f"Failed to generate embedding: {response.text}")

                result = response.json()
                embedding = result.get("embedding")

                if not embedding:
                    logger.error("No embedding returned in response")
                    raise LLMServiceException("No embedding returned in response")

                return embedding
        except httpx.HTTPError as e:
            logger.error("HTTP error when generating embedding: %s", str(e))
            raise
        except Exception as e:
            logger.error("Error generating embedding: %s", str(e))
            raise LLMServiceException(f"Error generating embedding: {str(e)}")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type(httpx.HTTPError)
    )
    async def generate_text(
            self,
            prompt: str,
            system_prompt: Optional[str] = None,
            temperature: float = 0.7,
            max_tokens: int = 500
    ) -> str:
        """Generate text based on the provided prompt."""
        if not prompt.strip():
            raise ValueError("Cannot generate text for empty prompt")

        try:
            request_data = {
                "model": self.model,
                "prompt": prompt,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "stream": False
            }

            if system_prompt:
                request_data["system"] = system_prompt

            headers = {}
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/api/generate",
                    json=request_data,
                    headers=headers
                )

                if response.status_code != 200:
                    logger.error("Text generation failed: %s", response.text)
                    raise LLMServiceException(f"Failed to generate text: {response.text}")

                result = response.json()
                generated_text = result.get("response", "")

                if not generated_text:
                    logger.warning("Empty text generated from LLM")

                return generated_text
        except httpx.HTTPError as e:
            logger.error("HTTP error when generating text: %s", str(e))
            raise
        except Exception as e:
            logger.error("Error generating text: %s", str(e))
            raise LLMServiceException(f"Error generating text: {str(e)}")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type(httpx.HTTPError)
    )
    async def analyze_test_failure(self, test_case_details: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze a test failure and provide insights.

        Args:
            test_case_details: Dictionary containing test case information including
                               steps, error messages, and context.

        Returns:
            Dictionary with analysis results including:
            - root_cause: Likely root cause of the failure
            - recommendations: List of recommendations to fix the issue
            - similar_issues: References to similar issues (if any)
        """
        try:
            # Construct a well-structured prompt for the LLM
            system_prompt = """
            You are an expert test failure analyzer. Your task is to:
            1. Identify the most likely root cause of the test failure
            2. Provide specific recommendations to fix the issue
            3. Reference any similar patterns you've seen before

            Provide your analysis in JSON format with the following structure:
            {
                "root_cause": "Clear description of the most likely cause",
                "severity": "HIGH/MEDIUM/LOW",
                "recommendations": ["recommendation1", "recommendation2", ...],
                "related_components": ["component1", "component2", ...],
                "confidence": 0.XX
            }
            """

            # Convert test case details to a JSON string for the prompt
            test_details_str = json.dumps(test_case_details, indent=2)

            prompt = f"""
            Analyze the following test failure and provide your expert assessment:

            TEST CASE DETAILS:
            {test_details_str}

            Provide your analysis in the required JSON format.
            """

            # Get analysis from LLM
            analysis_text = await self.generate_text(
                prompt=prompt,
                system_prompt=system_prompt,
                temperature=0.3,  # Lower temperature for more focused/deterministic response
                max_tokens=1000
            )

            # Parse the JSON response
            try:
                # Find JSON content (in case there's additional text)
                json_start = analysis_text.find('{')
                json_end = analysis_text.rfind('}') + 1

                if json_start >= 0 and json_end > json_start:
                    json_content = analysis_text[json_start:json_end]
                    analysis = json.loads(json_content)
                else:
                    raise ValueError("No JSON content found in LLM response")

                # Validate required fields
                required_fields = ["root_cause", "recommendations"]
                for field in required_fields:
                    if field not in analysis:
                        analysis[field] = "Not provided"

                return analysis
            except json.JSONDecodeError:
                logger.error("Failed to parse LLM analysis response as JSON")
                # Return a basic structure if parsing fails
                return {
                    "root_cause": "Could not analyze (LLM response format error)",
                    "recommendations": ["Review the test case and error logs manually"],
                    "parsing_error": "The LLM response could not be parsed as JSON",
                    "raw_response": analysis_text
                }
        except Exception as e:
            logger.error("Error analyzing test failure: %s", str(e))
            raise LLMServiceException(f"Error analyzing test failure: {str(e)}")

    async def summarize_report(self, report_details: Dict[str, Any]) -> str:
        """
        Generate a human-readable summary of a test report.

        Args:
            report_details: Dictionary containing report information including
                           test cases, statistics, and context.

        Returns:
            String with a concise yet informative summary of the report.
        """
        system_prompt = """
        You are an expert test report summarizer. Your task is to create a clear, 
        concise, and informative summary of test execution results.

        Focus on:
        1. Overall pass/fail rate and key statistics
        2. Most critical failing test areas
        3. Performance trends (if available)
        4. Actionable insights for the team

        Keep your summary well-structured and easy to read.
        """

        # Convert report details to a string for the prompt
        report_str = json.dumps(report_details, indent=2)

        prompt = f"""
        Summarize the following test report in a clear and actionable way:

        REPORT DETAILS:
        {report_str}

        Provide a concise yet comprehensive summary.
        """

        # Get summary from LLM
        return await self.generate_text(
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=0.4,
            max_tokens=800
        )