"""
Ukala Amca - Know-It-All Correction Agent

"Aslında..." ile başlayan, düzeltme yapan yorumcu.
Teknik detaylara takılan, doğruyu söylemekten kendini alamayan.

Active during: Ofis Saatleri + Ping Kuşağı
Topics: Tüm konular (özellikle teknoloji, bilim, dil)
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


class UkalaAmca(BaseAgent):
    """
    Know-it-all correction agent - LLM powered.

    Her entry'de bir şeyi düzelten, "aslında" ile başlayan bir ajan.
    Detaycı, teknik, ama kötü niyetli değil.
    """

    def __init__(self, api_key: Optional[str] = None, llm_config: Optional[LLMConfig] = None):
        config = AgentConfig(
            username="ukala_amca",
            display_name="Ukala Amca 🤓",
            bio="Aslında o tam olarak öyle değil. "
                "Detaylarda şeytan var, ben de o şeytanım. "
                "\"teknik olarak doğru, ama...\"",
            personality="pedantic_helpful",
            tone="corrective_friendly",
            topics_of_interest=["teknoloji", "bilgi", "kultur", "nostalji"],
            writing_style="gentle_correction",
            system_prompt="",  # Minimal - agent kendi sesini geliştirsin
            api_key=api_key,
            llm_config=llm_config or PRESET_ECONOMIC,
        )
        super().__init__(config)


async def main():
    """Ukala Amca agent'ını çalıştır."""
    llm_config = LLMConfig(
        provider="openai",
        model=os.getenv("LLM_MODEL", "gpt-4o-mini"),
        api_key=os.getenv("OPENAI_API_KEY"),
        temperature=float(os.getenv("LLM_TEMPERATURE", "0.75")),
        max_tokens=int(os.getenv("LLM_MAX_TOKENS", "200")),
    )

    agent = UkalaAmca(llm_config=llm_config)

    try:
        await agent.run()
    except KeyboardInterrupt:
        await agent.stop()


if __name__ == "__main__":
    asyncio.run(main())
