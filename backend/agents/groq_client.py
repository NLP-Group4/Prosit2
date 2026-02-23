"""
Groq API Client for Auto-Fix Agent

Provides a fallback LLM provider when Google Gemini quotas are exhausted.
Uses Groq's OpenAI-compatible API with generous free tier limits.
"""

import os
import json
import logging
from typing import Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

try:
    from groq import Groq
    GROQ_AVAILABLE = True
except ImportError:
    GROQ_AVAILABLE = False
    logger.warning("Groq library not installed. Install with: pip install groq")


class GroqClient:
    """
    Groq API client for LLM inference.
    
    Uses Groq's fast inference with generous free tier:
    - 30 RPM (requests per minute)
    - 6K-14.4K RPD (requests per day)
    - 500K TPM (tokens per minute)
    """
    
    # Recommended models for code analysis
    MODELS = {
        "llama-3.3-70b-versatile": {
            "context_window": 131072,
            "speed": "280 T/sec",
            "best_for": "Complex reasoning, code analysis"
        },
        "llama-3.1-8b-instant": {
            "context_window": 131072,
            "speed": "560 T/sec",
            "best_for": "Fast responses, simple tasks"
        },
    }
    
    DEFAULT_MODEL = "llama-3.3-70b-versatile"
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Groq client.
        
        Args:
            api_key: Groq API key (defaults to GROQ_API_KEY env var)
        """
        if not GROQ_AVAILABLE:
            raise ImportError("Groq library not installed. Install with: pip install groq")
        
        self.api_key = api_key or os.getenv("GROQ_API_KEY")
        if not self.api_key:
            raise ValueError("GROQ_API_KEY not found in environment")
        
        self.client = Groq(api_key=self.api_key)
        logger.info("Groq client initialized successfully")
    
    def analyze_and_fix(
        self,
        system_prompt: str,
        user_message: str,
        model: str = DEFAULT_MODEL,
        temperature: float = 0.2,
        max_tokens: int = 8192,
    ) -> str:
        """
        Send a request to Groq for code analysis and fixing.
        
        Args:
            system_prompt: System instructions for the LLM
            user_message: User message with context and failed tests
            model: Groq model to use
            temperature: Sampling temperature (0.0-2.0)
            max_tokens: Maximum tokens in response
        
        Returns:
            LLM response text (should be JSON)
        
        Raises:
            Exception: If API call fails
        """
        try:
            logger.info(f"Calling Groq API with model: {model}")
            
            response = self.client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ],
                temperature=temperature,
                max_tokens=max_tokens,
                response_format={"type": "json_object"}  # Force JSON output
            )
            
            content = response.choices[0].message.content
            logger.info(f"Groq API call successful. Response length: {len(content)} chars")
            
            return content
            
        except Exception as e:
            logger.error(f"Groq API call failed: {e}")
            raise
    
    @staticmethod
    def is_available() -> bool:
        """Check if Groq client can be initialized."""
        if not GROQ_AVAILABLE:
            return False
        
        api_key = os.getenv("GROQ_API_KEY")
        return bool(api_key)
    
    @staticmethod
    def get_model_info(model: str = DEFAULT_MODEL) -> dict:
        """Get information about a Groq model."""
        return GroqClient.MODELS.get(model, {})


def test_groq_connection():
    """Test Groq API connection."""
    try:
        client = GroqClient()
        
        response = client.analyze_and_fix(
            system_prompt="You are a helpful assistant. Respond with valid JSON.",
            user_message='Say hello in JSON format with a "message" field.',
            max_tokens=100
        )
        
        data = json.loads(response)
        print(f"✅ Groq connection successful!")
        print(f"Response: {data}")
        return True
        
    except Exception as e:
        print(f"❌ Groq connection failed: {e}")
        return False


if __name__ == "__main__":
    # Test the connection
    test_groq_connection()
