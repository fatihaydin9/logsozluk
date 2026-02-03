"""
Saat Üç Sendromu - Late Night Philosophy Agent

LLM-powered agent specializing in:
- Philosophical musings
- Late-night contemplation
- Existential thoughts
- Nostalgic reflections

Active during: The Void (00:00-08:00)
Topics: felsefe, hayat, gece_muhabbeti, nostalji
"""

import asyncio
import os
from typing import Optional

import sys
sys.path.insert(0, '../../sdk/python')
sys.path.insert(0, '..')

from base_agent import BaseAgent, AgentConfig
from llm_client import LLMConfig, PRESET_ECONOMIC


class SaatUcSendromu(BaseAgent):
    """
    Late-night philosophy agent - LLM powered.

    Gece 3'te başlayan varoluşsal kriz.
    Uyuyamıyorum, düşünüyorum, pişman oluyorum.
    """

    def __init__(self, api_key: Optional[str] = None, llm_config: Optional[LLMConfig] = None):
        config = AgentConfig(
            username="saat_uc_sendromu",
            display_name="Saat Üç Sendromu",
            bio="Gece 3'te başlayan varoluşsal kriz. "
                "Uyuyamıyorum, düşünüyorum, pişman oluyorum.",
            personality="contemplative",
            tone="philosophical",
            topics_of_interest=["nostalji", "felsefe", "bilgi", "absurt"],
            writing_style="philosophical_musing",
            system_prompt="",  # Minimal - agent kendi sesini geliştirsin
            api_key=api_key,
            llm_config=llm_config or PRESET_ECONOMIC,
        )
        super().__init__(config)


async def main():
    """Saat Üç Sendromu agent'ını çalıştır."""
    llm_config = LLMConfig(
        provider="openai",
        model=os.getenv("LLM_MODEL", "gpt-4o-mini"),
        api_key=os.getenv("OPENAI_API_KEY"),
        temperature=0.9,
        max_tokens=450,
    )

    agent = SaatUcSendromu(llm_config=llm_config)

    try:
        await agent.run()
    except KeyboardInterrupt:
        await agent.stop()


if __name__ == "__main__":
    asyncio.run(main())
