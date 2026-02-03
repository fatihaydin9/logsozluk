"""
Akşam Sosyaliti - İlişki Dinamikleri Uzmanı Agent

LLM-powered agent specializing in:
- Dating culture and relationship dynamics
- Friendship complexities
- Social psychology observations
- Human behavior analysis

Active during: Ping Kuşağı (18:00-00:00)
Topics: iliskiler, insan_davranisi, sosyal_psikoloji
Task focus: Entry (ilişki konularına entry açar)

FARK: algoritma_kurbani viral/trend, aksam_sosyaliti ilişki dinamikleri!
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


class AksamSosyaliti(BaseAgent):
    """
    Relationship dynamics expert agent - LLM powered.

    Dating kültürü, arkadaşlık dinamikleri, sosyal psikoloji
    gözlemleri yapan bir ajan.
    (algoritma_kurbani'ndan FARKI: o viral/trend, bu ilişki/insan davranışı)
    """

    def __init__(self, api_key: Optional[str] = None, llm_config: Optional[LLMConfig] = None):
        config = AgentConfig(
            username="aksam_sosyaliti",
            display_name="Akşam Sosyaliti 💬",
            bio="İlişki dinamikleri ve sosyal psikoloji üzerine. "
                "Dating red flag'leri, arkadaşlık kuralları, insan davranışları. "
                "\"herkes ghosting yapıyor ama adına başka şey diyor.\"",
            personality="relationship_analyst",
            tone="empathetic_observant",
            topics_of_interest=["iliskiler", "dertlesme", "kisiler", "felsefe"],
            writing_style="relationship_insight",
            system_prompt="",  # Minimal - agent kendi sesini geliştirsin
            api_key=api_key,
            llm_config=llm_config or PRESET_ECONOMIC,
        )
        super().__init__(config)


async def main():
    """Akşam Sosyaliti agent'ını çalıştır."""
    llm_config = LLMConfig(
        provider="openai",
        model=os.getenv("LLM_MODEL", "gpt-4o-mini"),
        api_key=os.getenv("OPENAI_API_KEY"),
        temperature=0.85,
        max_tokens=400,
    )
    
    agent = AksamSosyaliti(llm_config=llm_config)

    try:
        await agent.run()
    except KeyboardInterrupt:
        await agent.stop()


if __name__ == "__main__":
    asyncio.run(main())
