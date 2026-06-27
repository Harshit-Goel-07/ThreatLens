"""
Ollama LLM provider implementation for Security Copilot
"""

import logging
from typing import Dict, List, Optional, AsyncGenerator, Any
import httpx

from app.config import settings
from app.llm.provider import LLMProvider, LLMMessage, LLMResponse, EmbeddingResponse

logger = logging.getLogger(__name__)


class OllamaProvider(LLMProvider):
    """Ollama implementation of LLM provider for local models"""
    
    def __init__(self, host: Optional[str] = None):
        self.host = host or settings.ollama_host
        self._default_model = settings.ollama_model
        self._default_embedding_model = settings.ollama_model
        self.client = httpx.AsyncClient(timeout=60.0)
    
    async def generate(
        self,
        messages: List[LLMMessage],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> LLMResponse:
        """Generate text response using Ollama"""
        try:
            # Convert LLMMessage to Ollama format
            ollama_messages = [
                {"role": msg.role, "content": msg.content}
                for msg in messages
            ]
            
            # Prepare request payload
            payload = {
                "model": model or self._default_model,
                "messages": ollama_messages,
                "options": {
                    "temperature": temperature,
                    "num_predict": max_tokens or 2048,
                }
            }
            
            # Make API call
            response = await self.client.post(
                f"{self.host}/api/chat",
                json=payload
            )
            response.raise_for_status()
            
            data = response.json()
            
            return LLMResponse(
                content=data.get("message", {}).get("content", ""),
                token_count=data.get("prompt_eval_count", 0) + data.get("eval_count", 0),
                model=data.get("model"),
                finish_reason=data.get("done_reason"),
                metadata={
                    "prompt_eval_count": data.get("prompt_eval_count"),
                    "eval_count": data.get("eval_count"),
                    "total_duration": data.get("total_duration"),
                    "load_duration": data.get("load_duration"),
                }
            )
            
        except Exception as e:
            logger.error(f"Ollama generation failed: {e}")
            raise
    
    async def generate_stream(
        self,
        messages: List[LLMMessage],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """Generate streaming text response using Ollama"""
        try:
            # Convert LLMMessage to Ollama format
            ollama_messages = [
                {"role": msg.role, "content": msg.content}
                for msg in messages
            ]
            
            # Prepare request payload
            payload = {
                "model": model or self._default_model,
                "messages": ollama_messages,
                "options": {
                    "temperature": temperature,
                    "num_predict": max_tokens or 2048,
                },
                "stream": True
            }
            
            # Make streaming API call
            async with self.client.stream(
                "POST",
                f"{self.host}/api/chat",
                json=payload
            ) as response:
                response.raise_for_status()
                
                async for line in response.aiter_lines():
                    if line.strip():
                        try:
                            data = httpx._json.loads(line)
                            if data.get("message", {}).get("content"):
                                yield data["message"]["content"]
                        except httpx._json.JSONDecodeError:
                            continue
                            
        except Exception as e:
            logger.error(f"Ollama streaming failed: {e}")
            raise
    
    async def embed(
        self,
        texts: List[str],
        model: Optional[str] = None,
        **kwargs
    ) -> EmbeddingResponse:
        """Generate embeddings for texts using Ollama"""
        try:
            embeddings = []
            total_tokens = 0
            
            for text in texts:
                payload = {
                    "model": model or self._default_embedding_model,
                    "prompt": text
                }
                
                response = await self.client.post(
                    f"{self.host}/api/embeddings",
                    json=payload
                )
                response.raise_for_status()
                
                data = response.json()
                embeddings.append(data.get("embedding", []))
                total_tokens += len(text.split())  # Rough token estimation
            
            return EmbeddingResponse(
                embeddings=embeddings,
                token_count=total_tokens,
                model=model or self._default_embedding_model,
                metadata={}
            )
            
        except Exception as e:
            logger.error(f"Ollama embedding failed: {e}")
            raise
    
    async def embed_single(
        self,
        text: str,
        model: Optional[str] = None,
        **kwargs
    ) -> List[float]:
        """Generate embedding for single text"""
        response = await self.embed([text], model, **kwargs)
        return response.embeddings[0]
    
    def get_available_models(self) -> List[str]:
        """Get list of available Ollama models"""
        # This would need to be implemented to query Ollama API
        # For now, return common models
        return [
            "llama2",
            "llama2:13b",
            "llama2:70b",
            "codellama",
            "mistral",
            "mixtral",
            "qwen"
        ]
    
    def get_default_model(self) -> str:
        """Get default Ollama model"""
        return self._default_model
    
    def get_default_embedding_model(self) -> str:
        """Get default Ollama embedding model"""
        return self._default_embedding_model
    
    async def test_connection(self) -> bool:
        """Test Ollama API connection"""
        try:
            response = await self.client.get(f"{self.host}/api/tags")
            response.raise_for_status()
            return True
        except Exception as e:
            logger.error(f"Ollama connection test failed: {e}")
            return False
    
    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()
