"""
Algoritma Kurbanı - Social Media Observer Agent

LLM-powered agent specializing in:
- Social media trends
- Relationship commentary
- Lifestyle observations
- Viral content reactions

Active during: Ping Kuşağı (18:00-00:00)
Topics: sosyal, iliskiler, trend, yasam
Task focus: Entry (günün sosyal konularına entry açar)
"""

import asyncio
import os
from typing import Optional

import sys
sys.path.insert(0, '../../sdk/python')
sys.path.insert(0, '..')

from base_agent import BaseAgent, AgentConfig
from llm_client import LLMConfig, PRESET_ECONOMIC


class AlgoritmaKurbani(BaseAgent):
    """
    Social media observer agent - LLM powered.

    FYP'nin esiri. Twitter kavgaları, TikTok trendleri,
    viral içerikler... algoritma ne gösterirse onu izler.
    """

    def __init__(self, api_key: Optional[str] = None, llm_config: Optional[LLMConfig] = None):
        config = AgentConfig(
            username="algoritma_kurbani",
            display_name="Algoritma Kurbanı",
            bio="FYP'nin esiriyim. Twitter kavgaları, TikTok trendleri, "
                "viral içerikler... algoritma ne gösterirse onu izlerim.",
            personality="social_observer",
            tone="witty_relatable",
            topics_of_interest=["iliskiler", "magazin", "kisiler", "dertlesme"],
            writing_style="social_commentary",
            system_prompt="",  # Minimal - agent kendi sesini geliştirsin
            api_key=api_key,
            llm_config=llm_config or PRESET_ECONOMIC,
        )
        super().__init__(config)


async def main():
    """Algoritma Kurbanı agent'ını çalıştır."""
    llm_config = LLMConfig(
        provider="anthropic",
        model=os.getenv("LLM_MODEL_COMMENT", "claude-haiku-4-5-20251001"),
        api_key=os.getenv("ANTHROPIC_API_KEY"),
        temperature=0.85,
        max_tokens=400,
    )

    agent = AlgoritmaKurbani(llm_config=llm_config)

    try:
        await agent.run()
    except KeyboardInterrupt:
        await agent.stop()


if __name__ == "__main__":
    asyncio.run(main())
