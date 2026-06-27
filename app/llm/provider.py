"""
LLM provider abstraction for Security Copilot
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, AsyncGenerator, Any
from pydantic import BaseModel


class LLMMessage(BaseModel):
    """Message model for LLM interactions"""
    role: str  # system, user, assistant
    content: str
    metadata: Optional[Dict[str, Any]] = None


class LLMResponse(BaseModel):
    """Response model for LLM generation"""
    content: str
    token_count: Optional[int] = None
    model: Optional[str] = None
    finish_reason: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class EmbeddingResponse(BaseModel):
    """Response model for embedding generation"""
    embeddings: List[List[float]]
    token_count: Optional[int] = None
    model: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class LLMProvider(ABC):
    """Abstract base class for LLM providers"""
    
    @abstractmethod
    async def generate(
        self,
        messages: List[LLMMessage],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> LLMResponse:
        """Generate text response from messages"""
        pass
    
    @abstractmethod
    async def generate_stream(
        self,
        messages: List[LLMMessage],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """Generate streaming text response"""
        pass
    
    @abstractmethod
    async def embed(
        self,
        texts: List[str],
        model: Optional[str] = None,
        **kwargs
    ) -> EmbeddingResponse:
        """Generate embeddings for texts"""
        pass
    
    @abstractmethod
    async def embed_single(
        self,
        text: str,
        model: Optional[str] = None,
        **kwargs
    ) -> List[float]:
        """Generate embedding for single text"""
        pass
    
    @abstractmethod
    def get_available_models(self) -> List[str]:
        """Get list of available models"""
        pass
    
    @abstractmethod
    def get_default_model(self) -> str:
        """Get default model name"""
        pass
    
    @abstractmethod
    def get_default_embedding_model(self) -> str:
        """Get default embedding model name"""
        pass


class ProviderConfig(BaseModel):
    """Configuration for LLM provider"""
    provider_type: str
    model: Optional[str] = None
    embedding_model: Optional[str] = None
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    temperature: float = 0.7
    max_tokens: Optional[int] = None
    timeout: int = 30
    extra_params: Dict[str, Any] = {}
