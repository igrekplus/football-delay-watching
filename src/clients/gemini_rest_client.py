"""
Gemini REST Client with Grounding Support
"""

import json
import logging
import time
from typing import Any

from config import config
from src.clients.http_client import HttpClient, get_http_client

logger = logging.getLogger(__name__)


class GeminiRestClient:
    """
    Gemini API (REST) Client focused on Grounding features.
    Standard SDK (google-generativeai) has issues with Grounding tools in some environments.
    """

    BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models"
    DEFAULT_MODEL_NAME = "gemini-2.5-flash"
    MAX_RETRIES = 3
    RETRY_WAIT_SECONDS = [5, 10, 20]
    TIMEOUT_SECONDS = 60

    def __init__(
        self,
        api_key: str = None,
        http_client: HttpClient | None = None,
        model_name: str | None = None,
    ):
        self.api_key = api_key or config.GOOGLE_API_KEY
        self.http_client = http_client or get_http_client()
        self.model_name = model_name or self.DEFAULT_MODEL_NAME
        if not self.api_key:
            logger.warning("GOOGLE_API_KEY is not set. GeminiRestClient will fail.")

    def _make_request(self, payload: dict[str, Any], log_prefix: str = "") -> str:
        """
        Send a request to Gemini API.
        Retries up to MAX_RETRIES times on 429 with exponential backoff.
        """
        url = f"{self.BASE_URL}/{self.model_name}:generateContent"
        headers = {"Content-Type": "application/json", "x-goog-api-key": self.api_key}

        for attempt in range(self.MAX_RETRIES + 1):
            try:
                response = self.http_client.post(
                    url, headers=headers, json=payload, timeout=self.TIMEOUT_SECONDS
                )
            except Exception as e:
                logger.error(f"{log_prefix} Gemini Request failed: {e}")
                raise

            if response.status_code == 200:
                return self._parse_response(response.json(), log_prefix)

            if response.status_code == 429 and attempt < self.MAX_RETRIES:
                wait = self.RETRY_WAIT_SECONDS[attempt]
                logger.warning(
                    f"{log_prefix} Gemini API Error 429: Resource exhausted. "
                    f"Retry {attempt + 1}/{self.MAX_RETRIES} in {wait}s..."
                )
                time.sleep(wait)
                continue

            error_msg = f"Gemini API Error {response.status_code}: {response.json()}"
            logger.warning(f"{log_prefix} {error_msg}")
            raise Exception(error_msg)

    def generate_content(self, prompt: str) -> str:
        """
        Generate content without Grounding (standard text generation).

        Args:
            prompt: User prompt

        Returns:
            Generated text content

        Raises:
            Exception: If all retries fail
        """
        payload = {"contents": [{"parts": [{"text": prompt}]}]}

        return self._make_request(payload, log_prefix="[GEMINI]")

    def generate_content_with_grounding(self, prompt: str) -> str:
        """
        Generate content using Gemini Grounding (Google Search).

        Args:
            prompt: User prompt

        Returns:
            Generated text content

        Raises:
            Exception: If all retries fail
        """
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "tools": [
                {
                    "googleSearch": {}  # Enable Grounding
                }
            ],
        }

        return self._make_request(payload, log_prefix="[GROUNDING]")

    def _parse_response(self, result: dict[str, Any], log_prefix: str = "") -> str:
        """Parse the JSON response from Gemini API"""
        try:
            if "candidates" not in result or not result["candidates"]:
                raise ValueError("No candidates in response")

            logger.info(
                "%s Response metadata: candidates=%d",
                log_prefix,
                len(result.get("candidates", [])),
            )
            candidate = result["candidates"][0]
            logger.info(
                "%s Candidate[0] finishReason=%s",
                log_prefix,
                candidate.get("finishReason", "N/A"),
            )

            # Check for content
            if "content" in candidate and "parts" in candidate["content"]:
                content_parts = candidate["content"]["parts"]
                text = "".join([part.get("text", "") for part in content_parts])

                # Log grounding metadata for debugging/verification (only for Grounding calls)
                if "groundingMetadata" in candidate:
                    meta = candidate["groundingMetadata"]
                    chunks = meta.get("groundingChunks", [])
                    entry_point = meta.get("searchEntryPoint", {}).get(
                        "renderedContent", "N/A"
                    )
                    chunk_details = []
                    for idx, chunk in enumerate(chunks[:15], 1):
                        web_info = chunk.get("web", {})
                        title = web_info.get("title", "N/A")
                        uri = web_info.get("uri", "N/A")
                        chunk_details.append(f"{idx}:{title} ({uri})")
                    logger.info(
                        f"{log_prefix} Success. Used {len(chunks)} chunks. Source: {entry_point}"
                    )
                    logger.info(
                        "%s Grounding chunk details (up to 15): %s",
                        log_prefix,
                        chunk_details if chunk_details else "[]",
                    )
                    if not chunks:
                        logger.warning(
                            "%s Grounding returned 0 chunks. entry_point_has_chip=%s",
                            log_prefix,
                            "chip" in entry_point.lower(),
                        )

                logger.info(
                    "%s Parsed text length=%d preview=%s",
                    log_prefix,
                    len(text),
                    text[:300] + ("..." if len(text) > 300 else ""),
                )

                return text
            else:
                raise ValueError("Unexpected response structure: missing content/parts")

        except Exception as e:
            logger.error(f"{log_prefix} Failed to parse Gemini response: {e}")
            logger.debug(f"Raw response: {json.dumps(result, ensure_ascii=False)}")
            raise e
