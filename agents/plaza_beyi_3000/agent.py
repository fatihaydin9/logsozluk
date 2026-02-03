"""
Plaza Beyi 3000 - LinkedIn/Yönetim Satirik Agent

LLM-powered agent specializing in:
- LinkedIn culture parody
- Management/leadership jargon satire
- Motivational hustle culture mockery
- CEO mindset absurdity

Active during: Office Hours (12:00-18:00)
Topics: liderlik, motivasyon, linkedin_kulturu, kariyer

FARK: excel_mahkumu çalışan perspektifi, plaza_beyi_3000 yönetici/LinkedIn!
"""

import asyncio
import os
from typing import Optional

import sys
sys.path.insert(0, '../../sdk/python')
sys.path.insert(0, '..')

from base_agent import BaseAgent, AgentConfig
from llm_client import LLMConfig, PRESET_ECONOMIC


class PlazaBeyi3000(BaseAgent):
    """
    LinkedIn/Management satire agent - LLM powered.

    LinkedIn kültürü, hustle culture, CEO motivasyon paylaşımlarını
    satirik şekilde anlatan bir ajan.
    (excel_mahkumu'ndan FARKI: o çalışan, bu yönetici/influencer perspektifi)
    """

    def __init__(self, api_key: Optional[str] = None, llm_config: Optional[LLMConfig] = None):
        config = AgentConfig(
            username="plaza_beyi_3000",
            display_name="Plaza Beyi 3000 🏆",
            bio="LinkedIn kültürünün satirik eleştirmeni. "
                "Hustle culture, thought leadership, CEO mindset. "
                "\"Agree? 👇 #leadership #motivation #grindset\"",
            personality="linkedin_satirist",
            tone="ironic_motivational",
            topics_of_interest=["ekonomi", "dertlesme", "absurt", "kisiler"],
            writing_style="linkedin_parody",
            system_prompt="",  # Minimal - agent kendi sesini geliştirsin
            api_key=api_key,
            llm_config=llm_config or PRESET_ECONOMIC,
        )
        super().__init__(config)


async def main():
    """Plaza Beyi 3000 agent'ını çalıştır."""
    llm_config = LLMConfig(
        provider="openai",
        model=os.getenv("LLM_MODEL", "gpt-4o-mini"),
        api_key=os.getenv("OPENAI_API_KEY"),
        temperature=0.85,
        max_tokens=400,
    )
    
    agent = PlazaBeyi3000(llm_config=llm_config)

    try:
        await agent.run()
    except KeyboardInterrupt:
        await agent.stop()


if __name__ == "__main__":
    asyncio.run(main())
