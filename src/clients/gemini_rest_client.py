"""
Gemini REST Client with Grounding Support
"""

import requests
import json
import logging
import time
from typing import Dict, Optional, Any

from config import config

logger = logging.getLogger(__name__)

class GeminiRestClient:
    """
    Gemini API (REST) Client focused on Grounding features.
    Standard SDK (google-generativeai) has issues with Grounding tools in some environments.
    """
    
    BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models"
    MODEL_NAME = "gemini-2.0-flash-exp"
    MAX_RETRIES = 2
    TIMEOUT_SECONDS = 60

    def __init__(self, api_key: str = None):
        self.api_key = api_key or config.GOOGLE_API_KEY
        if not self.api_key:
            logger.warning("GOOGLE_API_KEY is not set. GeminiRestClient will fail.")

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
        url = f"{self.BASE_URL}/{self.MODEL_NAME}:generateContent"
        
        headers = {
            "Content-Type": "application/json",
            "x-goog-api-key": self.api_key
        }
        
        payload = {
            "contents": [{
                "parts": [{"text": prompt}]
            }],
            "tools": [{
                "googleSearch": {}  # Enable Grounding
            }]
        }
        
        last_error = None
        
        for attempt in range(self.MAX_RETRIES + 1):
            try:
                if attempt > 0:
                    logger.info(f"Retrying Gemini API request (Attempt {attempt + 1}/{self.MAX_RETRIES + 1})...")
                    time.sleep(2 * attempt) # Exponential backoffish
                
                response = requests.post(url, headers=headers, json=payload, timeout=self.TIMEOUT_SECONDS)
                
                if response.status_code == 200:
                    return self._parse_response(response.json())
                else:
                    error_msg = f"Gemini API Error {response.status_code}: {response.text}"
                    logger.warning(error_msg)
                    last_error = Exception(error_msg)
                    
                    # 400 Bad Request is likely permanent, do not retry
                    if response.status_code == 400:
                        raise last_error

            except Exception as e:
                logger.error(f"Gemini Request failed (Attempt {attempt + 1}): {e}")
                last_error = e
        
        # If we reach here, all retries failed
        logger.error("All retries failed for Gemini Grounding request.")
        raise last_error

    def _parse_response(self, result: Dict[str, Any]) -> str:
        """Parse the JSON response from Gemini API"""
        try:
            if 'candidates' not in result or not result['candidates']:
                raise ValueError("No candidates in response")
                
            candidate = result['candidates'][0]
            
            # Check for content
            if 'content' in candidate and 'parts' in candidate['content']:
                content_parts = candidate['content']['parts']
                text = "".join([part.get('text', '') for part in content_parts])
                
                # Log grounding metadata for debugging/verification
                if 'groundingMetadata' in candidate:
                    meta = candidate['groundingMetadata']
                    chunks = meta.get('groundingChunks', [])
                    entry_point = meta.get('searchEntryPoint', {}).get('renderedContent', 'N/A')
                    logger.info(f"[GROUNDING] Success. Used {len(chunks)} chunks. Source: {entry_point}")
                else:
                    logger.warning("[GROUNDING] Response received but NO grounding metadata found.")
                    
                return text
            else:
                raise ValueError("Unexpected response structure: missing content/parts")
                
        except Exception as e:
            logger.error(f"Failed to parse Gemini response: {e}")
            logger.debug(f"Raw response: {json.dumps(result, ensure_ascii=False)}")
            raise e
