"""
Google Gemini Provider.

Integrates with Google Gemini API for Flash and Pro models.
Uses the official google-genai SDK with async support.
"""

import time
from typing import Optional

from google import genai
from google.genai import errors as genai_errors
from google.genai import types
from google.oauth2 import service_account

from src.config import get_settings
from src.providers.base import (
    BaseProvider,
    ProviderError,
    ProviderModelNotFoundError,
    ProviderRateLimitError,
    ProviderResponse,
    ProviderTimeoutError,
)

VERTEX_AI_SCOPES = ["https://www.googleapis.com/auth/cloud-platform"]


class GeminiProvider(BaseProvider):
    """
    Provider for Google Gemini, via either of two auth paths to the same API:

    - Vertex AI with a service account (settings.use_vertex_ai=True, the
      default). Confirmed empirically on this project to get full paid-tier
      throughput -- the AI Studio API key path below throttled the newest
      Gemini model generation to a 15 req/min free-tier limit despite paid
      tier being enabled on the account, and 404'd on gemini-2.5-pro as
      deprecated for new users. Both worked cleanly through Vertex.
    - AI Studio API key (settings.use_vertex_ai=False). Lower setup cost --
      no GCP project or service account needed -- so kept as a fallback for
      anyone re-running this project against their own key.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        timeout: int = 60,
    ):
        """
        Initialize GeminiProvider.

        Args:
            api_key: Google API key, only used when use_vertex_ai=False
                (defaults to settings)
            timeout: Request timeout in seconds
        """
        settings = get_settings()
        self.timeout = timeout
        self.api_key: Optional[str] = None

        if settings.use_vertex_ai:
            if not settings.google_application_credentials:
                raise ProviderError(
                    "USE_VERTEX_AI=true but GOOGLE_APPLICATION_CREDENTIALS is not set "
                    "(path to a service account JSON key file)",
                    self.name,
                    retriable=False,
                )

            credentials = service_account.Credentials.from_service_account_file(
                settings.google_application_credentials,
                scopes=VERTEX_AI_SCOPES,
            )
            project_id = settings.vertex_project_id or credentials.project_id

            self._client = genai.Client(
                vertexai=True,
                credentials=credentials,
                project=project_id,
                location=settings.vertex_location,
            )
        else:
            self.api_key = api_key or settings.google_api_key
            if not self.api_key:
                raise ProviderError(
                    "GOOGLE_API_KEY not configured",
                    self.name,
                    retriable=False,
                )
            self._client = genai.Client(api_key=self.api_key)
    
    @property
    def name(self) -> str:
        return "gemini"
    
    async def generate(self, prompt: str, model: str) -> ProviderResponse:
        """
        Generate completion using Gemini API.
        
        Uses the async generate_content method.
        """
        start_time = time.perf_counter()
        
        try:
            # Create the request
            response = await self._client.aio.models.generate_content(
                model=model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.7,
                    max_output_tokens=2048,
                ),
            )
            
            latency_ms = int((time.perf_counter() - start_time) * 1000)
            
            # Extract text from response
            text = ""
            if response.candidates:
                for candidate in response.candidates:
                    if candidate.content and candidate.content.parts:
                        for part in candidate.content.parts:
                            if hasattr(part, 'text'):
                                text += part.text or ""
            
            # Get token counts from usage metadata
            prompt_tokens = self._estimate_tokens(prompt)
            completion_tokens = self._estimate_tokens(text)
            
            if response.usage_metadata:
                prompt_tokens = response.usage_metadata.prompt_token_count or prompt_tokens
                completion_tokens = response.usage_metadata.candidates_token_count or completion_tokens
            
            return ProviderResponse(
                text=text,
                model=model,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                latency_ms=latency_ms,
                raw_response=None,  # Complex object, skip for now
            )
            
        except genai_errors.APIError as e:
            raise self._classify_error(e)

        except Exception as e:
            # Non-API errors (network issues, etc.) -- treat as retriable.
            raise ProviderError(f"Gemini error: {e}", self.name)

    def _classify_error(self, e: "genai_errors.APIError") -> ProviderError:
        """
        Map a Gemini APIError to the right ProviderError subclass.

        Uses the SDK's structured HTTP status code (e.code), not string
        matching on the error message. Message-substring matching previously
        classified a 404 "model deprecated" error as a rate limit, because the
        error text linked to a migration doc at a URL containing the
        substring "migrate-to-interactions" -- which contains "rate". That
        misclassification caused the retry/backoff path to retry a request
        that could never succeed, instead of failing fast or escalating tier.
        """
        if e.code == 404:
            return ProviderModelNotFoundError(f"Gemini model not found: {e}", self.name)
        if e.code == 429:
            return ProviderRateLimitError(f"Gemini rate limit exceeded: {e}", self.name)
        if e.code == 504 or e.code == 408:
            return ProviderTimeoutError(f"Gemini request timed out: {e}", self.name)
        return ProviderError(f"Gemini API error: {e}", self.name)

    async def health_check(self) -> bool:
        """
        Check if Gemini API is accessible.
        
        Tries to list models as a simple health check.
        """
        try:
            # Simple check - just verify a client was constructed (either auth
            # path raises in __init__ if misconfigured, so reaching here means
            # credentials were accepted). Full health check would make an API call.
            return self._client is not None
        except Exception:
            return False
    
    async def generate_structured(
        self,
        prompt: str,
        json_schema: dict,
        model: str,
        system_prompt: Optional[str] = None,
    ) -> tuple[dict | list, int, int, int]:
        """
        Generate structured JSON output conforming to schema.
        
        Uses Gemini's responseSchema feature for guaranteed JSON.
        
        Args:
            prompt: User prompt
            json_schema: JSON Schema the response must conform to
            model: Model to use
            system_prompt: Optional system instruction
            
        Returns:
            Tuple of (parsed_data, prompt_tokens, completion_tokens, latency_ms)
        """
        start_time = time.perf_counter()
        
        try:
            # Build config with JSON schema
            config = types.GenerateContentConfig(
                temperature=0.3,  # Lower temp for structured output
                max_output_tokens=4096,
                response_mime_type="application/json",
                response_schema=json_schema,
            )
            
            # Add system instruction if provided
            if system_prompt:
                config.system_instruction = system_prompt
            
            response = await self._client.aio.models.generate_content(
                model=model,
                contents=prompt,
                config=config,
            )
            
            latency_ms = int((time.perf_counter() - start_time) * 1000)
            
            # Get token counts
            prompt_tokens = self._estimate_tokens(prompt)
            completion_tokens = 0
            
            if response.usage_metadata:
                prompt_tokens = response.usage_metadata.prompt_token_count or prompt_tokens
                completion_tokens = response.usage_metadata.candidates_token_count or 0
            
            # Parse the structured response
            # response.parsed contains the already-parsed JSON
            if hasattr(response, 'parsed') and response.parsed is not None:
                return response.parsed, prompt_tokens, completion_tokens, latency_ms
            
            # Fallback to parsing response text
            import json
            text = ""
            if response.candidates:
                for candidate in response.candidates:
                    if candidate.content and candidate.content.parts:
                        for part in candidate.content.parts:
                            if hasattr(part, 'text'):
                                text += part.text or ""
            
            completion_tokens = completion_tokens or self._estimate_tokens(text)
            parsed = json.loads(text)
            return parsed, prompt_tokens, completion_tokens, latency_ms
            
        except genai_errors.APIError as e:
            raise self._classify_error(e)

        except Exception as e:
            raise ProviderError(f"Gemini structured output error: {e}", self.name)
    
    async def close(self):
        """Close provider resources."""
        # google-genai client doesn't need explicit cleanup
        pass
