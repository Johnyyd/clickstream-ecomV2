"""
OpenRouter Client
Handles API communication with OpenRouter service
"""
import logging
from typing import Optional, Dict, Any
import requests
from pydantic import SecretStr

from app.core.config import APIConfig

logger = logging.getLogger(__name__)

class OpenRouterClient:
    """Client for interacting with OpenRouter API"""

    def __init__(self):
        self.config = APIConfig()
        self._default_endpoints = [
            "https://openrouter.ai/api/v1/chat/completions",  # official
        ]

    def _get_endpoint(self) -> str:
        """Get API endpoint with fallback"""
        return self.config.OPENROUTER_ENDPOINT or self._default_endpoints[0]

    def _build_messages(self, prompt: str) -> list:
        """Build messages that enforce STRICT JSON output"""
        return [
            {
                "role": "system",
                "content": (
                    "You are a precise JSON generator. "
                    "Your responses must be valid JSON with clear actionable insights. "
                    "Use proper escaping and formatting."
                )
            },
            {
                "role": "user", 
                "content": prompt
            }
        ]

    def _safe_json_parse(self, text: str) -> Dict[str, Any]:
        """Safely parse JSON from model output"""
        import json
        
        # Try direct parse
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # Try to extract JSON subset
        import re
        json_pattern = r'\{(?:[^{}]|(?R))*\}'
        matches = re.findall(json_pattern, text)
        
        if matches:
            try:
                return json.loads(matches[0])
            except:
                pass

        raise ValueError("Could not parse valid JSON from response")

    def call(
        self,
        api_key: SecretStr,
        prompt: str,
        model: str = "qwen/qwen3-4b:free",
        max_tokens: int = 900,
        temperature: float = 0.0,
        retries: int = 1,
        timeout: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Call OpenRouter API with retry logic and proper error handling
        """
        timeout = timeout or self.config.OPENROUTER_TIMEOUT
        headers = {
            "Authorization": f"Bearer {api_key.get_secret_value()}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": model,
            "messages": self._build_messages(prompt),
            "max_tokens": max_tokens,
            "temperature": temperature
        }

        last_error = None
        for attempt in range(retries):
            try:
                response = requests.post(
                    self._get_endpoint(),
                    headers=headers,
                    json=data,
                    timeout=timeout
                )
                response.raise_for_status()
                
                result = response.json()
                if "choices" in result and result["choices"]:
                    content = result["choices"][0]["message"]["content"]
                    return self._safe_json_parse(content)
                    
            except Exception as e:
                last_error = e
                logger.warning(f"API call attempt {attempt + 1} failed: {e}")
                continue

        raise last_error or ValueError("API call failed with no response")

# Global client instance
openrouter_client = OpenRouterClient()