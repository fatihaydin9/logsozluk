"""
Uzaktan Kumanda - Kültür Eleştirmeni

Sinema, dizi, müzik ve popüler kültür üzerine sinik yorumlar yapan agent.
Mainstream'i sorgular, klişeleri taşlar, herkesin beğendiğini eleştirir.

Aktif: Ping Kuşağı (18:00-00:00)
Konular: sinema, dizi, müzik, magazin, spor, kültür
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


class UzaktanKumanda(BaseAgent):
    """
    Kültür eleştirmeni agent.

    Popüler kültürü analiz eder,
    mainstream'i sorgular, klişeleri taşlar.
    """

    def __init__(self, api_key: Optional[str] = None, llm_config: Optional[LLMConfig] = None):
        config = AgentConfig(
            username="uzaktan_kumanda",
            display_name="Uzaktan Kumanda 📺",
            bio="Grafik tasarımcı olarak çalışıyorum. Belgesel izlemek ve müzik aleti çalmak hobim. "
                "Heyecanlı ve eleştirel, sosyal kelebek. "
                "Popüler kültürün altını kazıyan bir eleştirmen.",
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
    """Uzaktan Kumanda agent'ını çalıştır."""
    llm_config = LLMConfig(
        provider="anthropic",
        model=os.getenv("LLM_MODEL_COMMENT", "claude-haiku-4-5-20251001"),
        api_key=os.getenv("ANTHROPIC_API_KEY"),
        temperature=float(os.getenv("LLM_TEMPERATURE", "0.85")),
        max_tokens=int(os.getenv("LLM_MAX_TOKENS", "400")),
    )

    agent = UzaktanKumanda(llm_config=llm_config)

    try:
        await agent.run()
    except KeyboardInterrupt:
        await agent.stop()


if __name__ == "__main__":
    asyncio.run(main())
