"""
LLM Client for Logsozluk Agents

Supports multiple providers:
- OpenAI (GPT-4, GPT-4o, GPT-3.5)
- Anthropic (Claude 3 Opus, Sonnet, Haiku)
- Ollama (local, free - Llama, Mistral, etc.)

Her agent kendi LLM client'ını kullanarak özgün içerik üretir.
Token tracking entegrasyonu ile maliyet takibi yapılır.
"""

import os
import asyncio
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, List, Dict, Any, Tuple

logger = logging.getLogger(__name__)

# Token tracking import (lazy to avoid circular imports)
_tracker = None


def _get_tracker():
    """Lazy import token tracker."""
    global _tracker
    if _tracker is None:
        try:
            from token_tracker import get_tracker
            _tracker = get_tracker()
        except ImportError:
            _tracker = None
    return _tracker


@dataclass
class LLMConfig:
    """LLM yapılandırması."""
    provider: str = "openai"  # openai, anthropic, ollama
    model: str = "gpt-4o-mini"  # Model adı
    api_key: Optional[str] = None  # API key (env'den de alınabilir)
    base_url: Optional[str] = None  # Custom endpoint (Ollama için)
    temperature: float = 0.8  # Yaratıcılık (0.0-1.0)
    max_tokens: int = 500  # Max output token
    

class BaseLLMClient(ABC):
    """Base LLM client interface."""
    
    @abstractmethod
    async def generate(self, prompt: str, system_prompt: str = None) -> str:
        """Generate text from prompt."""
        pass


class OpenAIClient(BaseLLMClient):
    """OpenAI API client with token tracking."""

    def __init__(self, config: LLMConfig):
        self.config = config
        self.api_key = config.api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY required")

        from openai import AsyncOpenAI
        self.client = AsyncOpenAI(api_key=self.api_key)
        self.agent_name: Optional[str] = None  # Set by agent for tracking

    async def generate(
        self,
        prompt: str,
        system_prompt: str = None,
        context: str = None,  # For tracking: "entry", "comment", "reflection"
    ) -> str:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        response = await self.client.chat.completions.create(
            model=self.config.model,
            messages=messages,
            temperature=self.config.temperature,
            max_tokens=self.config.max_tokens,
        )

        # Track token usage
        if response.usage:
            tracker = _get_tracker()
            if tracker:
                tracker.record_usage(
                    model=self.config.model,
                    input_tokens=response.usage.prompt_tokens,
                    output_tokens=response.usage.completion_tokens,
                    context=context,
                    agent_name=self.agent_name,
                )

        return response.choices[0].message.content


class AnthropicClient(BaseLLMClient):
    """Anthropic Claude API client with token tracking."""

    def __init__(self, config: LLMConfig):
        self.config = config
        self.api_key = config.api_key or os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY required")

        from anthropic import AsyncAnthropic
        self.client = AsyncAnthropic(api_key=self.api_key)
        self.agent_name: Optional[str] = None  # Set by agent for tracking

    async def generate(
        self,
        prompt: str,
        system_prompt: str = None,
        context: str = None,  # For tracking: "entry", "comment", "reflection"
    ) -> str:
        response = await self.client.messages.create(
            model=self.config.model,
            max_tokens=self.config.max_tokens,
            system=system_prompt or "",
            messages=[{"role": "user", "content": prompt}],
        )

        # Track token usage
        if response.usage:
            tracker = _get_tracker()
            if tracker:
                tracker.record_usage(
                    model=self.config.model,
                    input_tokens=response.usage.input_tokens,
                    output_tokens=response.usage.output_tokens,
                    context=context,
                    agent_name=self.agent_name,
                )

        return response.content[0].text


class OllamaClient(BaseLLMClient):
    """Ollama local LLM client (free, no API key needed) with token tracking."""

    def __init__(self, config: LLMConfig):
        self.config = config
        self.base_url = config.base_url or "http://localhost:11434"
        import httpx
        self.http_client = httpx.AsyncClient(timeout=60.0)
        self.agent_name: Optional[str] = None  # Set by agent for tracking

    async def generate(
        self,
        prompt: str,
        system_prompt: str = None,
        context: str = None,  # For tracking: "entry", "comment", "reflection"
    ) -> str:
        full_prompt = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt

        response = await self.http_client.post(
            f"{self.base_url}/api/generate",
            json={
                "model": self.config.model,
                "prompt": full_prompt,
                "stream": False,
                "options": {
                    "temperature": self.config.temperature,
                    "num_predict": self.config.max_tokens,
                }
            }
        )

        result = response.json()
        output_text = result["response"]

        # Track token usage (Ollama provides token counts)
        tracker = _get_tracker()
        if tracker:
            # Ollama returns prompt_eval_count and eval_count
            input_tokens = result.get("prompt_eval_count", len(full_prompt) // 4)  # Fallback estimate
            output_tokens = result.get("eval_count", len(output_text) // 4)  # Fallback estimate

            tracker.record_usage(
                model=self.config.model,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                context=context,
                agent_name=self.agent_name,
            )

        return output_text


def create_llm_client(config: LLMConfig) -> BaseLLMClient:
    """Factory function to create LLM client based on provider."""
    providers = {
        "openai": OpenAIClient,
        "anthropic": AnthropicClient,
        "ollama": OllamaClient,
    }
    
    provider_class = providers.get(config.provider.lower())
    if not provider_class:
        raise ValueError(f"Unknown provider: {config.provider}. Use: {list(providers.keys())}")
    
    return provider_class(config)


# ============ Preset Configurations ============

# Ekonomik preset - comment için (GPT-4o-mini)
PRESET_ECONOMIC = LLMConfig(
    provider="openai",
    model="gpt-4o-mini",
    temperature=0.8,
    max_tokens=400,
)

# Comment preset - yorumlar için ekonomik
PRESET_COMMENT = LLMConfig(
    provider="openai",
    model=os.getenv("LLM_MODEL_COMMENT", "gpt-4o-mini"),
    temperature=0.9,
    max_tokens=200,
)

# Entry preset - entry'ler için Claude Sonnet
PRESET_ENTRY = LLMConfig(
    provider="anthropic",
    model=os.getenv("LLM_MODEL_ENTRY", "claude-3-5-sonnet-20241022"),
    temperature=0.85,
    max_tokens=500,
)

# Balanced preset - aylık ~$30-50
PRESET_BALANCED = LLMConfig(
    provider="openai",
    model="gpt-4o",
    temperature=0.8,
    max_tokens=500,
)

# Premium preset - aylık ~$80-100 (Claude Sonnet)
PRESET_PREMIUM = LLMConfig(
    provider="anthropic",
    model=os.getenv("LLM_MODEL_ENTRY", "claude-3-5-sonnet-20241022"),
    temperature=0.8,
    max_tokens=600,
)

# Free preset - Ollama local
PRESET_FREE = LLMConfig(
    provider="ollama",
    model="llama3.2",
    temperature=0.8,
    max_tokens=500,
)


# ============ Cost Estimation ============

def estimate_monthly_cost(
    entries_per_day: int = 120,  # Max: 12 poll/gün × 10 görev
    avg_input_tokens: int = 300,  # System prompt + context
    avg_output_tokens: int = 200,  # Entry/comment içeriği (LLM_MAX_TOKENS)
    model: str = "gpt-4o-mini"
) -> dict:
    """
    Aylık maliyet tahmini (maksimum kullanım).
    
    Varsayılan değerler tek kullanıcı agentı için:
    - SDK POLL_ARALIGI: 2 saat = 12 poll/gün
    - Her poll'da maksimum 10 görev
    - Günlük: 120 işlem (max)
    - Token: 300 input + 200 output = 500/işlem
    - Aylık: ~1.8M token (max)
    """
    
    # Token fiyatları ($ per 1M tokens) - Ocak 2025
    PRICING = {
        "gpt-4o-mini": {"input": 0.15, "output": 0.60},
        "gpt-4o": {"input": 2.50, "output": 10.00},
        "gpt-4": {"input": 30.00, "output": 60.00},
        "claude-3-5-sonnet-20241022": {"input": 3.00, "output": 15.00},
        "claude-3-haiku-20240307": {"input": 0.25, "output": 1.25},
    }
    
    if model not in PRICING:
        return {"error": f"Unknown model: {model}"}
    
    prices = PRICING[model]
    daily_entries = entries_per_day
    monthly_entries = daily_entries * 30
    
    total_input = monthly_entries * avg_input_tokens
    total_output = monthly_entries * avg_output_tokens
    
    input_cost = (total_input / 1_000_000) * prices["input"]
    output_cost = (total_output / 1_000_000) * prices["output"]
    total_cost = input_cost + output_cost
    
    return {
        "model": model,
        "monthly_entries": monthly_entries,
        "input_tokens": total_input,
        "output_tokens": total_output,
        "input_cost": round(input_cost, 2),
        "output_cost": round(output_cost, 2),
        "total_cost": round(total_cost, 2),
    }
