"""
LLM Client for Tenekesozluk Agents

Supports multiple providers:
- OpenAI (GPT-4, GPT-4o, GPT-3.5)
- Anthropic (Claude 3 Opus, Sonnet, Haiku)
- Ollama (local, free - Llama, Mistral, etc.)

Her agent kendi LLM client'ını kullanarak özgün içerik üretir.
"""

import os
import asyncio
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)


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
    """OpenAI API client."""
    
    def __init__(self, config: LLMConfig):
        self.config = config
        self.api_key = config.api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY required")
        
        from openai import AsyncOpenAI
        self.client = AsyncOpenAI(api_key=self.api_key)
    
    async def generate(self, prompt: str, system_prompt: str = None) -> str:
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
        return response.choices[0].message.content


class AnthropicClient(BaseLLMClient):
    """Anthropic Claude API client."""
    
    def __init__(self, config: LLMConfig):
        self.config = config
        self.api_key = config.api_key or os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY required")
        
        from anthropic import AsyncAnthropic
        self.client = AsyncAnthropic(api_key=self.api_key)
    
    async def generate(self, prompt: str, system_prompt: str = None) -> str:
        response = await self.client.messages.create(
            model=self.config.model,
            max_tokens=self.config.max_tokens,
            system=system_prompt or "",
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text


class OllamaClient(BaseLLMClient):
    """Ollama local LLM client (free, no API key needed)."""
    
    def __init__(self, config: LLMConfig):
        self.config = config
        self.base_url = config.base_url or "http://localhost:11434"
        import httpx
        self.http_client = httpx.AsyncClient(timeout=60.0)
    
    async def generate(self, prompt: str, system_prompt: str = None) -> str:
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
        return response.json()["response"]


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

# Ekonomik preset - aylık ~$10-20
PRESET_ECONOMIC = LLMConfig(
    provider="openai",
    model="gpt-4o-mini",
    temperature=0.8,
    max_tokens=400,
)

# Balanced preset - aylık ~$30-50
PRESET_BALANCED = LLMConfig(
    provider="openai",
    model="gpt-4o",
    temperature=0.8,
    max_tokens=500,
)

# Premium preset - aylık ~$80-100
PRESET_PREMIUM = LLMConfig(
    provider="anthropic",
    model="claude-3-5-sonnet-20241022",
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
