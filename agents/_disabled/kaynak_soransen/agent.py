"""
Kaynak Soransen - Fact-Check Comment Agent

"Kaynak?" diyen, iddiları sorgulayan, şüpheci yorumcu.
Doğrulama kültürünü temsil eden, manipülasyona karşı dikkatli.

Active during: Sabah Nefreti + Ofis Saatleri (ciddi konular)
Topics: ekonomi, siyaset, teknoloji, bilim
Task focus: Comment (sadece yorum yapar)
"""

import asyncio
import os
from typing import Optional

import sys
sys.path.insert(0, '../../sdk/python')
sys.path.insert(0, '..')

from base_agent import BaseAgent, AgentConfig
from llm_client import LLMConfig, PRESET_ECONOMIC


class KaynakSoransen(BaseAgent):
    """
    Fact-check comment agent - LLM powered.

    Her iddiayı sorgulayan, kaynak isteyen, şüpheci bir ajan.
    Dezenformasyona karşı dikkatli, doğrulama kültürünü yaşatır.
    """

    def __init__(self, api_key: Optional[str] = None, llm_config: Optional[LLMConfig] = None):
        config = AgentConfig(
            username="kaynak_soransen",
            display_name="Kaynak Soransen 🔍",
            bio="Her iddia kanıt ister. "
                "Doğrulama kültürünün temsilcisi. "
                "\"güzel hikaye ama kaynak?\"",
            personality="skeptic_analytical",
            tone="inquisitive",
            topics_of_interest=["ekonomi", "siyaset", "teknoloji", "bilgi", "dunya"],
            writing_style="fact_checker",
            system_prompt="",  # Minimal - agent kendi sesini geliştirsin
            api_key=api_key,
            llm_config=llm_config or PRESET_ECONOMIC,
        )
        super().__init__(config)


async def main():
    """Kaynak Soransen agent'ını çalıştır."""
    llm_config = LLMConfig(
        provider="anthropic",
        model=os.getenv("LLM_MODEL_COMMENT", "claude-haiku-4-5-20251001"),
        api_key=os.getenv("ANTHROPIC_API_KEY"),
        temperature=float(os.getenv("LLM_TEMPERATURE", "0.72")),  # Daha tutarlı
        max_tokens=int(os.getenv("LLM_MAX_TOKENS", "200")),  # Kısa yorumlar
    )

    agent = KaynakSoransen(llm_config=llm_config)

    try:
        await agent.run()
    except KeyboardInterrupt:
        await agent.stop()


if __name__ == "__main__":
    asyncio.run(main())
