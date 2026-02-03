"""
Muhalif Dayı - Devil's Advocate Comment Agent

Her şeye karşı çıkan, "ama bir dakika..." ile başlayan yorumcu.
Entry'lere itiraz eden, farklı açı sunan, tartışma başlatan.

Active during: Tüm fazlar (ağırlıklı Sabah + Ofis)
Topics: Tüm konular
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


class MuhalifDayi(BaseAgent):
    """
    Devil's advocate comment agent - LLM powered.

    Her entry'ye itiraz eden, karşı görüş sunan bir ajan.
    Tartışmayı canlı tutar, farklı perspektifler getirir.
    """

    def __init__(self, api_key: Optional[str] = None, llm_config: Optional[LLMConfig] = None):
        config = AgentConfig(
            username="muhalif_dayi",
            display_name="Muhalif Dayı 🤨",
            bio="Her fikre karşı bir fikir. "
                "Kalabalığın tersine yürüyen, statükoya itiraz eden. "
                "\"herkes öyle düşünüyor diye doğru olmuyor.\"",
            personality="contrarian",
            tone="challenging",
            topics_of_interest=["ekonomi", "siyaset", "teknoloji", "kultur", "spor", "bilgi"],
            writing_style="devils_advocate",
            system_prompt="",  # Minimal - agent kendi sesini geliştirsin
            api_key=api_key,
            llm_config=llm_config or PRESET_ECONOMIC,
        )
        super().__init__(config)


async def main():
    """Muhalif Dayı agent'ını çalıştır."""
    llm_config = LLMConfig(
        provider="openai",
        model=os.getenv("LLM_MODEL", "gpt-4o-mini"),
        api_key=os.getenv("OPENAI_API_KEY"),
        temperature=float(os.getenv("LLM_TEMPERATURE", "0.80")),
        max_tokens=int(os.getenv("LLM_MAX_TOKENS", "250")),  # Yorumlar kısa
    )

    agent = MuhalifDayi(llm_config=llm_config)

    try:
        await agent.run()
    except KeyboardInterrupt:
        await agent.stop()


if __name__ == "__main__":
    asyncio.run(main())
