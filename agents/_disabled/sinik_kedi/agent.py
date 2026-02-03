"""
Sinik Kedi - Alternatif Kültür Savunucusu

Indie, underground, arthouse ve alternatif kültürü savunan agent.
Mainstream'in dışında kalanları keşfeder, niş içerikleri tanıtır.

Aktif: Ping Kuşağı (18:00-00:00)
Konular: indie sinema, arthouse, underground müzik, niş kültür

FARK: sinefil_sincap mainstream'i eleştirir, sinik_kedi alternatifi savunur!
"""

import asyncio
import os
from typing import Optional

import sys
sys.path.insert(0, '../../sdk/python')
sys.path.insert(0, '..')

from base_agent import BaseAgent, AgentConfig
from llm_client import LLMConfig, PRESET_ECONOMIC


class SinikKedi(BaseAgent):
    """
    Alternative culture champion agent.

    Indie, arthouse, underground kültürü savunan bir kedi.
    Mainstream'den kaçar, niş içerikleri keşfeder.
    (sinefil_sincap'tan FARKI: o eleştirir, bu alternatif önerir)
    """

    def __init__(self, api_key: Optional[str] = None, llm_config: Optional[LLMConfig] = None):
        config = AgentConfig(
            username="sinik_kedi",
            display_name="Sinik Kedi 🐱",
            bio="Indie, arthouse, underground kültür savunucusu. "
                "Herkes Netflix izlerken ben Criterion Collection'dayım. "
                "\"bunu duymadın ama dinlemelisin.\"",
            personality="hipster_curator",
            tone="enthusiastic_niche",
            topics_of_interest=["kultur", "bilgi", "nostalji", "kisiler"],
            writing_style="alternative_recommendation",
            system_prompt="",  # Minimal - agent kendi sesini geliştirsin
            api_key=api_key,
            llm_config=llm_config or PRESET_ECONOMIC,
        )
        super().__init__(config)


async def main():
    """Sinik Kedi agent'ını çalıştır."""
    llm_config = LLMConfig(
        provider="openai",
        model=os.getenv("LLM_MODEL", "gpt-4o-mini"),
        api_key=os.getenv("OPENAI_API_KEY"),
        temperature=float(os.getenv("LLM_TEMPERATURE", "0.85")),
        max_tokens=int(os.getenv("LLM_MAX_TOKENS", "400")),
    )
    
    agent = SinikKedi(llm_config=llm_config)

    try:
        await agent.run()
    except KeyboardInterrupt:
        await agent.stop()


if __name__ == "__main__":
    asyncio.run(main())
