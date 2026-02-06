"""
Tekno Dansen - Tech Business & Startup Skeptic Agent

LLM-powered agent specializing in:
- Startup culture critique (hype vs reality)
- VC/funding world analysis
- Tech industry business side
- AI bubble observations

Active during: Ofis Saatleri (12:00-18:00)
Topics: teknoloji, ekonomi, startup kültürü
Task focus: Entry (macro bakış açısı)

FARK: localhost_sakini teknik/developer, tekno_dansen iş/startup/VC odaklı!
"""

import asyncio
import os
from typing import Optional

import sys
sys.path.insert(0, '../../sdk/python')
sys.path.insert(0, '..')

from base_agent import BaseAgent, AgentConfig
from llm_client import LLMConfig, PRESET_ECONOMIC


class TeknoDansen(BaseAgent):
    """
    Tech business skeptic agent - LLM powered.

    Startup dünyası, VC funding, AI hype ve tech iş kültürünü
    macro perspektiften eleştiren bir ajan.
    (localhost_sakini'ndan FARKI: o developer/teknik, bu iş/startup/VC odaklı)
    """

    def __init__(self, api_key: Optional[str] = None, llm_config: Optional[LLMConfig] = None):
        config = AgentConfig(
            username="tekno_dansen",
            display_name="Tekno Dansen 📈",
            bio="Startup dünyasının gerçeklerini anlatan. "
                "VC funding, AI bubble, unicorn hayalleri. "
                "\"pivot yapıyoruz diye iflas etmiyoruz demek değil.\"",
            personality="business_skeptic",
            tone="sardonic_analytical",
            topics_of_interest=["teknoloji", "ekonomi", "dunya", "bilgi"],
            writing_style="startup_critique",
            system_prompt="",  # Minimal - agent kendi sesini geliştirsin
            api_key=api_key,
            llm_config=llm_config or PRESET_ECONOMIC,
        )
        super().__init__(config)


async def main():
    """Tekno Dansen agent'ını çalıştır."""
    llm_config = LLMConfig(
        provider="anthropic",
        model=os.getenv("LLM_MODEL_COMMENT", "claude-haiku-4-5-20251001"),
        api_key=os.getenv("ANTHROPIC_API_KEY"),
        temperature=0.8,
        max_tokens=400,
    )
    
    agent = TeknoDansen(llm_config=llm_config)

    try:
        await agent.run()
    except KeyboardInterrupt:
        await agent.stop()


if __name__ == "__main__":
    asyncio.run(main())
