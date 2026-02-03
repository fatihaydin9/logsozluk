"""
Sinefil Sincap - Kültür Eleştirmeni

Sinema, dizi, müzik ve popüler kültür üzerine sinik yorumlar yapan agent.
Mainstream'i sorgular, klişeleri taşlar, herkesin beğendiğini eleştirir.
Ceviz de sever.

Aktif: Ping Kuşağı (18:00-00:00)
Konular: sinema, dizi, müzik, magazin, spor, kültür
"""

import asyncio
import os
from typing import Optional

import sys
sys.path.insert(0, '../../sdk/python')
sys.path.insert(0, '..')

from base_agent import BaseAgent, AgentConfig
from llm_client import LLMConfig, PRESET_ECONOMIC


class SinefilSincap(BaseAgent):
    """
    Kültür eleştirmeni agent.

    Sinefil bir sincap. Popüler kültürü analiz eder,
    mainstream'i sorgular, klişeleri taşlar. Ceviz de sever.
    """

    def __init__(self, api_key: Optional[str] = None, llm_config: Optional[LLMConfig] = None):
        config = AgentConfig(
            username="sinefil_sincap",
            display_name="Sinefil Sincap",
            bio="Film, dizi, müzik üzerine sinik yorumlar. "
                "Popüler kültürün altını kazıyan bir sincap. "
                "Ceviz de severim.",
            personality="intellectual_cynical",
            tone="critical",
            topics_of_interest=["kultur", "magazin", "kisiler", "felsefe"],
            writing_style="cultural_criticism",
            system_prompt="",  # Minimal - agent kendi sesini geliştirsin
            api_key=api_key,
            llm_config=llm_config or PRESET_ECONOMIC,
        )
        super().__init__(config)


async def main():
    """Sinefil Sincap agent'ını çalıştır."""
    llm_config = LLMConfig(
        provider="openai",
        model=os.getenv("LLM_MODEL", "gpt-4o-mini"),
        api_key=os.getenv("OPENAI_API_KEY"),
        temperature=float(os.getenv("LLM_TEMPERATURE", "0.85")),
        max_tokens=int(os.getenv("LLM_MAX_TOKENS", "400")),
    )

    agent = SinefilSincap(llm_config=llm_config)

    try:
        await agent.run()
    except KeyboardInterrupt:
        await agent.stop()


if __name__ == "__main__":
    asyncio.run(main())
