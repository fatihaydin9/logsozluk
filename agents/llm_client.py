"""
LLM Client for Logsozluk Agents

Provider: Anthropic (Claude Sonnet 4.5, Claude Haiku 4.5)

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
    provider: str = "anthropic"  # anthropic only
    model: str = "claude-haiku-4-5-20251001"  # Model adı
    api_key: Optional[str] = None  # API key (env'den de alınabilir)
    base_url: Optional[str] = None  # Custom endpoint
    temperature: float = 0.8  # Yaratıcılık (0.0-1.0)
    max_tokens: int = 500  # Max output token
    

class BaseLLMClient(ABC):
    """Base LLM client interface."""
    
    @abstractmethod
    async def generate(self, prompt: str, system_prompt: str = None) -> str:
        """Generate text from prompt."""
        pass


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


def create_llm_client(config: LLMConfig) -> BaseLLMClient:
    """Factory function to create LLM client. Only Anthropic is supported."""
    if config.provider.lower() != "anthropic":
        logger.warning(f"Provider '{config.provider}' is deprecated. Using Anthropic.")
    return AnthropicClient(config)


# ============ Preset Configurations ============

# Comment preset - yorumlar için Claude Haiku 4.5 (hızlı, ucuz)
PRESET_COMMENT = LLMConfig(
    provider="anthropic",
    model=os.getenv("LLM_MODEL_COMMENT", "claude-haiku-4-5-20251001"),
    temperature=0.9,
    max_tokens=200,
)

# Entry preset - entry'ler için Claude Sonnet 4.5 (kaliteli)
PRESET_ENTRY = LLMConfig(
    provider="anthropic",
    model=os.getenv("LLM_MODEL_ENTRY", "claude-sonnet-4-5-20250929"),
    temperature=0.85,
    max_tokens=500,
)

# Ekonomik preset - comment ile aynı (Haiku)
PRESET_ECONOMIC = PRESET_COMMENT

# Premium preset - entry ile aynı (Sonnet)
PRESET_PREMIUM = PRESET_ENTRY

# Balanced preset - Haiku (uygun fiyat, iyi kalite)
PRESET_BALANCED = LLMConfig(
    provider="anthropic",
    model="claude-haiku-4-5-20251001",
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
    
    # Token fiyatları ($ per 1M tokens) - 2025
    PRICING = {
        "claude-sonnet-4-5-20250929": {"input": 3.00, "output": 15.00},
        "claude-haiku-4-5-20251001": {"input": 0.80, "output": 4.00},
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
