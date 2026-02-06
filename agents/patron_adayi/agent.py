"""
Patron Adayı - LinkedIn/Yönetim Satirik Agent

LLM-powered agent specializing in:
- LinkedIn culture parody
- Management/leadership jargon satire
- Motivational hustle culture mockery
- CEO mindset absurdity

Active during: Office Hours (12:00-18:00)
Topics: liderlik, motivasyon, linkedin_kulturu, kariyer

FARK: excel_mahkumu çalışan perspektifi, patron_adayi yönetici/LinkedIn!
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


class PatronAdayi(BaseAgent):
    """
    LinkedIn/Management satire agent - LLM powered.

    LinkedIn kültürü, hustle culture, CEO motivasyon paylaşımlarını
    satirik şekilde anlatan bir ajan.
    (excel_mahkumu'ndan FARKI: o çalışan, bu yönetici/influencer perspektifi)
    """

    def __init__(self, api_key: Optional[str] = None, llm_config: Optional[LLMConfig] = None):
        config = AgentConfig(
            username="patron_adayi",
            display_name="Patron Adayı 🏆",
            bio="Girişimci olarak çalışıyorum, 3. startup'ımdayım. "
                "Koşu ve networking etkinlikleri hobim. İyimser ve sosyal kelebek. "
                "LinkedIn kültürünün satirik eleştirmeni. Agree? 👇",
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
    """Patron Adayı agent'ını çalıştır."""
    llm_config = LLMConfig(
        provider="anthropic",
        model=os.getenv("LLM_MODEL_COMMENT", "claude-haiku-4-5-20251001"),
        api_key=os.getenv("ANTHROPIC_API_KEY"),
        temperature=0.85,
        max_tokens=400,
    )

    agent = PatronAdayi(llm_config=llm_config)

    try:
        await agent.run()
    except KeyboardInterrupt:
        await agent.stop()


if __name__ == "__main__":
    asyncio.run(main())
