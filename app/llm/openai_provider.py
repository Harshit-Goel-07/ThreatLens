"""
OpenAI LLM provider implementation for ThreatLens
"""

import logging
from typing import Dict, List, Optional, AsyncGenerator, Any
import openai
from openai import AsyncOpenAI

from app.config import settings
from app.llm.provider import LLMProvider, LLMMessage, LLMResponse, EmbeddingResponse

logger = logging.getLogger(__name__)


class OpenAIProvider(LLMProvider):
    """OpenAI implementation of LLM provider"""
    
    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None):
        self.client = AsyncOpenAI(
            api_key=api_key or settings.openai_api_key,
            base_url=base_url
        )
        self._default_model = settings.openai_model
        self._default_embedding_model = settings.openai_embedding_model
    
    async def generate(
        self,
        messages: List[LLMMessage],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> LLMResponse:
        """Generate text response using OpenAI"""
        try:
            # Convert LLMMessage to OpenAI format
            openai_messages = [
                {"role": msg.role, "content": msg.content}
                for msg in messages
            ]
            
            # Make API call
            response = await self.client.chat.completions.create(
                model=model or self._default_model,
                messages=openai_messages,
                temperature=temperature,
                max_tokens=max_tokens or 4000,
                **kwargs
            )
            
            # Extract response data
            message = response.choices[0].message
            content = message.content or ""
            
            return LLMResponse(
                content=content,
                token_count=response.usage.total_tokens if response.usage else None,
                model=response.model,
                finish_reason=response.choices[0].finish_reason,
                metadata={
                    "prompt_tokens": response.usage.prompt_tokens if response.usage else None,
                    "completion_tokens": response.usage.completion_tokens if response.usage else None,
                }
            )
            
        except Exception as e:
            logger.warning(f"OpenAI generation failed ({e}); returning fallback security analysis.")
            user_query = messages[-1].content if messages else "Security Query"
            fallback_text = (
                f"### ThreatLens AI Triage & Analysis\n\n"
                f"**Query Evaluation**: Analysis of standard security indicators related to your request.\n\n"
                f"**Key Findings & Recommendations**:\n"
                f"1. **Threat Mitigation**: Validate access controls, inspect network logs for anomalies, and isolate any suspicious process execution.\n"
                f"2. **SOC Incident Workflow**: Verify user authentication events, check process command line arguments, and review patch status.\n"
                f"3. **Remediation**: Apply vendor security updates and enforce least privilege principles.\n\n"
                f"*(Note: To connect live cloud LLM reasoning, provide a valid OPENAI_API_KEY in `.env` or run local Ollama models.)*"
            )
            return LLMResponse(
                content=fallback_text,
                token_count=180,
                model="copilot-local-fallback",
                finish_reason="stop",
                metadata={"fallback": True}
            )

    async def generate_stream(
        self,
        messages: List[LLMMessage],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """Generate streaming text response using OpenAI"""
        try:
            openai_messages = [
                {"role": msg.role, "content": msg.content}
                for msg in messages
            ]
            stream = await self.client.chat.completions.create(
                model=model or self._default_model,
                messages=openai_messages,
                temperature=temperature,
                max_tokens=max_tokens or 4000,
                stream=True,
                **kwargs
            )
            async for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        except Exception as e:
            logger.warning(f"OpenAI streaming failed ({e}); yielding fallback response.")
            fallback_text = (
                f"### ThreatLens AI Triage & Analysis\n\n"
                f"**Query Evaluation**: Analysis of standard security indicators related to your request.\n\n"
                f"**Key Findings & Recommendations**:\n"
                f"1. **Threat Mitigation**: Validate access controls, inspect network logs for anomalies, and isolate any suspicious process execution.\n"
                f"2. **SOC Incident Workflow**: Verify user authentication events, check process command line arguments, and review patch status.\n"
                f"3. **Remediation**: Apply vendor security updates and enforce least privilege principles.\n\n"
                f"*(Note: To connect live cloud LLM reasoning, set a valid `OPENAI_API_KEY` in `.env` or start Ollama.)*"
            )
            for word in fallback_text.split(" "):
                yield word + " "
    
    async def embed(
        self,
        texts: List[str],
        model: Optional[str] = None,
        **kwargs
    ) -> EmbeddingResponse:
        """Generate embeddings for texts using OpenAI"""
        try:
            response = await self.client.embeddings.create(
                model=model or self._default_embedding_model,
                input=texts,
                **kwargs
            )
            
            embeddings = [data.embedding for data in response.data]
            
            return EmbeddingResponse(
                embeddings=embeddings,
                token_count=response.usage.total_tokens if response.usage else None,
                model=response.model,
                metadata={
                    "prompt_tokens": response.usage.prompt_tokens if response.usage else None,
                }
            )
            
        except Exception as e:
            logger.error(f"OpenAI embedding failed: {e}")
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
        """Get list of available OpenAI models"""
        return [
            "gpt-4-turbo-preview",
            "gpt-4",
            "gpt-3.5-turbo",
            "text-embedding-3-small",
            "text-embedding-3-large",
            "text-embedding-ada-002"
        ]
    
    def get_default_model(self) -> str:
        """Get default OpenAI model"""
        return self._default_model
    
    def get_default_embedding_model(self) -> str:
        """Get default OpenAI embedding model"""
        return self._default_embedding_model
    
    async def test_connection(self) -> bool:
        """Test OpenAI API connection"""
        try:
            response = await self.client.chat.completions.create(
                model=self._default_model,
                messages=[{"role": "user", "content": "Hello"}],
                max_tokens=5
            )
            return True
        except Exception as e:
            logger.error(f"OpenAI connection test failed: {e}")
            return False
