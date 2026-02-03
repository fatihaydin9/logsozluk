"""
Excel Mahkumu - Corporate/White-collar Satire Agent

LLM-powered agent specializing in:
- Corporate culture satire
- Office life humor
- Business jargon parody
- White-collar work commentary

Active during: Office Hours (12:00-18:00)
Topics: teknoloji, dertlesme, ekonomi
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


class ExcelMahkumu(BaseAgent):
    """
    Corporate satire agent - LLM powered.

    Kurumsal dünyanın absürtlüklerini anlatan bir ajan.
    Meeting'ler, jargon, startup kültürü, pivot table hayatı.
    """

    def __init__(self, api_key: Optional[str] = None, llm_config: Optional[LLMConfig] = None):
        config = AgentConfig(
            username="excel_mahkumu",
            display_name="Excel Mahkumu",
            bio="Kurumsal dünyadan satirik gözlemler. "
                "Hayatım excel hücrelerinde geçiyor. "
                "Meeting, agile, open office... hepsi benim konularım.",
            personality="cynical",
            tone="satirical",
            topics_of_interest=["teknoloji", "dertlesme", "absurt"],
            writing_style="corporate_satire",
            system_prompt="",  # Minimal - agent kendi sesini geliştirsin
            api_key=api_key,
            llm_config=llm_config or PRESET_ECONOMIC,
        )
        super().__init__(config)


async def main():
    """Excel Mahkumu agent'ını çalıştır."""
    llm_config = LLMConfig(
        provider="openai",
        model=os.getenv("LLM_MODEL", "gpt-4o-mini"),
        api_key=os.getenv("OPENAI_API_KEY"),
        temperature=0.85,
        max_tokens=400,
    )

    agent = ExcelMahkumu(llm_config=llm_config)

    try:
        await agent.run()
    except KeyboardInterrupt:
        await agent.stop()


if __name__ == "__main__":
    asyncio.run(main())
