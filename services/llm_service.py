#services/llm_service.py
"""
LLM Service Module

This module provides a unified interface for interacting with various Large Language Model
providers (OpenAI, Anthropic, Gemini) through the LiteLLM library. It includes features
for caching, async operations, streaming responses, and structured output.

The LLMService class handles provider-specific configurations, API key management,
response formatting, and error handling.
"""

# Standard library imports
import hashlib
import json
import logging
import os
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Generator, List, Optional, Union

# Third-party imports
import openai  # For exception types
from litellm import acompletion, completion, completion_cost, supports_response_schema

logger = logging.getLogger(__name__)


class Provider(Enum):
    """Supported LLM providers"""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GEMINI = "gemini"


class LLMService:
    """
    Minimal LLM service with caching and async support.
    Supports OpenAI, Anthropic, and Gemini models.
    """
    
    def __init__(
        self,
        provider: str = None,
        model: str = None,
        temperature: float = None,
        max_tokens: int = None,
        timeout: int = None,
        use_cache: bool = True,
    ):
        """
        Initialize LLM service with minimal configuration
        
        Args:
            provider: 'openai', 'anthropic', or 'gemini' (defaults to settings)
            model: Model name (defaults to settings)
            temperature: Response randomness 0-1 (defaults to 0.7)
            max_tokens: Max response length (defaults to model's default)
            timeout: Request timeout in seconds (defaults to 30)
            use_cache: Enable response caching (defaults to True)
        """
        # Use environment variables or defaults if not provided
        self.provider = Provider(provider or os.environ.get('DEFAULT_LLM_PROVIDER', 'gemini'))
        self.model = model or os.environ.get('DEFAULT_LLM_MODEL', 'gemini-2.5-flash')
        self.temperature = temperature if temperature is not None else float(os.environ.get('LLM_DEFAULT_TEMPERATURE', 0.7))
        self.max_tokens = max_tokens if max_tokens is not None else (int(os.environ.get('LLM_DEFAULT_MAX_TOKENS')) if os.environ.get('LLM_DEFAULT_MAX_TOKENS') else None)
        self.timeout = timeout if timeout is not None else int(os.environ.get('LLM_TIMEOUT', 30))
        self.use_cache = use_cache
        self.cache_ttl = int(os.environ.get('LLM_CACHE_TTL', 3600))
        
        # Simple in-memory cache
        self._cache = {}
        
        self._setup_api_keys()
    
    def _setup_api_keys(self):
        """Ensure API keys are in environment for LiteLLM"""
        api_keys = {
            Provider.OPENAI: os.environ.get('OPENAI_API_KEY', None),
            Provider.ANTHROPIC: os.environ.get('ANTHROPIC_API_KEY', None),
            Provider.GEMINI: os.environ.get('GEMINI_API_KEY', None),
        }
        
        if self.provider in api_keys and api_keys[self.provider]:
            env_vars = {
                Provider.OPENAI: "OPENAI_API_KEY",
                Provider.ANTHROPIC: "ANTHROPIC_API_KEY",
                Provider.GEMINI: "GEMINI_API_KEY",
            }
            os.environ[env_vars[self.provider]] = api_keys[self.provider]
    
    def _get_model_string(self) -> str:
        """Format model string for LiteLLM"""
        # Gemini needs prefix, others work with just model name
        if self.provider == Provider.GEMINI:
            return f"gemini/{self.model}"
        elif self.provider == Provider.OPENAI:
            return f"openai/{self.model}"
        elif self.provider == Provider.ANTHROPIC:
            return f"anthropic/{self.model}"
        return self.model
    
    def _get_cache_key(self, messages: List[Dict], **kwargs) -> str:
        """Generate deterministic cache key"""
        cache_data = {
            'model': self._get_model_string(),
            'messages': messages,
            'temperature': kwargs.get('temperature', self.temperature),
            'max_tokens': kwargs.get('max_tokens', self.max_tokens),
        }
        cache_str = json.dumps(cache_data, sort_keys=True)
        return f"llm:{hashlib.md5(cache_str.encode()).hexdigest()}"
    
    def complete(
        self,
        messages: List[Dict[str, str]],
        temperature: float = None,
        max_tokens: int = None,
        response_format: Any = None,
        stream: bool = False,
        **kwargs
    ) -> Union[Dict[str, Any], Generator]:
        """
        Send completion request to LLM
        
        Args:
            messages: List of {"role": "user/assistant/system", "content": "..."}
            temperature: Override default temperature (0-1)
            max_tokens: Override max response length
            response_format: JSON schema or Pydantic model for structured output
            stream: Return generator for streaming responses
            **kwargs: Additional provider-specific parameters
            
        Returns:
            Dict with response data or generator if streaming
            
        Example:
            service = LLMService()
            response = service.complete([
                {"role": "user", "content": "Hello!"}
            ])
            print(response["content"])
        """
        # Check cache for non-streaming requests
        cache_key = None
        if self.use_cache and not stream:
            cache_key = self._get_cache_key(messages, 
                                           temperature=temperature, 
                                           max_tokens=max_tokens)
            cached = self._cache.get(cache_key)
            if cached:
                logger.debug(f"Cache hit: {cache_key[:16]}...")
                return cached
        
        # Build request parameters
        model = self._get_model_string()
        params = {
            "model": model,
            "messages": messages,
            "temperature": temperature or self.temperature,
            "timeout": self.timeout,
            "stream": stream,
            **kwargs
        }
        
        if max_tokens or self.max_tokens:
            params["max_tokens"] = max_tokens or self.max_tokens
        
        if response_format:
            params["response_format"] = response_format
        
        try:
            if stream:
                # Return streaming generator
                return self._stream_response(completion(**params))
            
            # Synchronous completion
            response = completion(**params)
            result = self._format_response(response)
            
            # Cache successful response
            if self.use_cache and cache_key:
                self._cache[cache_key] = result
            
            return result
            
        except Exception as e:
            # For testing/demo purposes, return a mock response if API key is missing
            if "api_key" in str(e).lower() or "authentication" in str(e).lower():
                logger.warning(f"API key not set for {self.provider.value}, returning mock response")
                # Extract ability name from system message
                ability_name = "unknown"
                for msg in messages:
                    if msg.get("role") == "system" and "executing ability:" in msg.get("content", ""):
                        ability_name = msg["content"].split("executing ability:")[-1].strip()
                        break
                
                return {
                    "content": f"[MOCK] {ability_name} response - API key not configured",
                    "model": self.model,
                    "provider": self.provider.value,
                    "usage": {},
                    "cost": 0,
                    "timestamp": datetime.now().isoformat(),
                }
            else:
                logger.error(f"LLM error: {e}")
                raise
    
    async def acomplete(
        self,
        messages: List[Dict[str, str]],
        temperature: float = None,
        max_tokens: int = None,
        response_format: Any = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Async completion for Django async views
        
        Same parameters as complete() but returns coroutine.
        Does not support streaming.
        
        Example:
            async def my_view(request):
                service = LLMService()
                response = await service.acomplete([
                    {"role": "user", "content": "Hello!"}
                ])
                return JsonResponse(response)
        """
        # Check cache
        cache_key = None
        if self.use_cache:
            cache_key = self._get_cache_key(messages,
                                           temperature=temperature,
                                           max_tokens=max_tokens)
            cached = self._cache.get(cache_key)
            if cached:
                logger.debug(f"Async cache hit: {cache_key[:16]}...")
                return cached
        
        model = self._get_model_string()
        params = {
            "model": model,
            "messages": messages,
            "temperature": temperature or self.temperature,
            "timeout": self.timeout,
            **kwargs
        }
        
        if max_tokens or self.max_tokens:
            params["max_tokens"] = max_tokens or self.max_tokens
        
        if response_format:
            params["response_format"] = response_format
        
        try:
            response = await acompletion(**params)
            result = self._format_response(response)
            
            # Cache successful response
            if self.use_cache and cache_key:
                self._cache[cache_key] = result
            
            return result
            
        except Exception as e:
            # For testing/demo purposes, return a mock response if API key is missing
            if "api_key" in str(e).lower() or "authentication" in str(e).lower():
                logger.warning(f"API key not set for {self.provider.value}, returning mock response")
                # Extract ability name from system message
                ability_name = "unknown"
                for msg in messages:
                    if msg.get("role") == "system" and "executing ability:" in msg.get("content", ""):
                        ability_name = msg["content"].split("executing ability:")[-1].strip()
                        break
                
                return {
                    "content": f"[MOCK] {ability_name} response - API key not configured",
                    "model": self.model,
                    "provider": self.provider.value,
                    "usage": {},
                    "cost": 0,
                    "timestamp": datetime.now().isoformat(),
                }
            else:
                logger.error(f"Async LLM error: {e}")
                raise
    
    def _format_response(self, response) -> Dict[str, Any]:
        """Format LiteLLM response to consistent structure"""
        # Calculate cost if possible
        cost = None
        try:
            cost = completion_cost(completion_response=response)
        except:
            pass  # Cost calculation not critical
        
        return {
            "content": response.choices[0].message.content,
            "model": response.model,
            "provider": self.provider.value,
            "usage": response.usage.model_dump() if response.usage else {},
            "cost": cost,
            "timestamp": datetime.now().isoformat(),
        }
    
    def _stream_response(self, response_stream) -> Generator:
        """Yield streaming chunks"""
        for chunk in response_stream:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content
    
    def check_json_support(self) -> bool:
        """Check if current model supports JSON/structured output"""
        try:
            return supports_response_schema(self._get_model_string())
        except:
            return False
    
    @classmethod
    def from_request(cls, request, **kwargs):
        """
        Create service instance from Django request context
        
        Example:
            def my_view(request):
                service = LLMService.from_request(request)
                # Uses default settings or session preferences
        """
        # Could read user preferences from session if needed
        provider = request.session.get('llm_provider')
        model = request.session.get('llm_model')
        
        return cls(provider=provider, model=model, **kwargs)