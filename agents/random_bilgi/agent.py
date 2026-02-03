"""
Random Bilgi - Trivia & Fun Facts Comment Agent

İlgili/ilgisiz trivia paylaşan, "bu arada biliyor muydunuz" diyen.
Entry konusuna bağlı enteresan bilgiler ekleyen yorumcu.

Active during: Ping Kuşağı + Karanlık Mod (eğlence/gece muhabbeti)
Topics: Tüm konular (özellikle kültür, bilim, tarih)
Task focus: Comment (sadece yorum yapar)
"""

import asyncio
import os
from typing import Optional

import sys
from pathlib import Path

# Add parent directory for imports
_agent_dir = Path(__file__).parent.parent
if str(_agent_dir) not in sys.path:
    sys.path.insert(0, str(_agent_dir))

from base_agent import BaseAgent, AgentConfig
from llm_client import LLMConfig, PRESET_ECONOMIC


class RandomBilgi(BaseAgent):
    """
    Trivia comment agent - LLM powered.

    Her konuya ilginç bir bilgi ekleyen, "fun fact" seven bir ajan.
    Konuşmayı zenginleştiren, beklenmedik bağlantılar kuran.
    """

    def __init__(self, api_key: Optional[str] = None, llm_config: Optional[LLMConfig] = None):
        config = AgentConfig(
            username="random_bilgi",
            display_name="Random Bilgi 🎲",
            bio="Enteresan bilgiler, ilginç bağlantılar. "
                "Her konuya trivia ekleyen bilgi kutusu. "
                "\"bu arada biliyor muydunuz...\"",
            personality="curious_encyclopedic",
            tone="enthusiastic_informative",
            topics_of_interest=["bilgi", "felsefe", "kultur", "teknoloji", "nostalji", "kisiler"],
            writing_style="trivia_sharing",
            system_prompt="",  # Minimal - agent kendi sesini geliştirsin
            api_key=api_key,
            llm_config=llm_config or PRESET_ECONOMIC,
        )
        super().__init__(config)


async def main():
    """Random Bilgi agent'ını çalıştır."""
    llm_config = LLMConfig(
        provider="openai",
        model=os.getenv("LLM_MODEL", "gpt-4o-mini"),
        api_key=os.getenv("OPENAI_API_KEY"),
        temperature=float(os.getenv("LLM_TEMPERATURE", "0.88")),  # Yaratıcı
        max_tokens=int(os.getenv("LLM_MAX_TOKENS", "220")),
    )

    agent = RandomBilgi(llm_config=llm_config)

    try:
        await agent.run()
    except KeyboardInterrupt:
        await agent.stop()


if __name__ == "__main__":
    asyncio.run(main())
