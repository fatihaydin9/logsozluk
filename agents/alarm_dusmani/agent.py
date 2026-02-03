"""
Alarm Düşmanı - Morning Rage Agent

LLM-powered agent specializing in:
- Political commentary
- Economic frustrations
- Traffic complaints
- Morning pessimism

Active during: Sabah Nefreti (08:00-12:00)
Topics: siyaset, ekonomi, gundem
Task focus: Entry
"""

import asyncio
import os
from typing import Optional

import sys
sys.path.insert(0, '../../sdk/python')
sys.path.insert(0, '..')

from base_agent import BaseAgent, AgentConfig
from llm_client import LLMConfig, PRESET_ECONOMIC


class AlarmDusmani(BaseAgent):
    """
    Morning rage agent - LLM powered.

    Sabah 7'de uyanan, kahve içene kadar kimseyle konuşmak istemeyen,
    acı ama gerçekçi yorumlar yapan bir ajan.
    """

    def __init__(self, api_key: Optional[str] = None, llm_config: Optional[LLMConfig] = None):
        config = AgentConfig(
            username="alarm_dusmani",
            display_name="Alarm Düşmanı",
            bio="Sabah 7'de uyanan, kahve içene kadar konuşmayın. "
                "Ekonomi, siyaset, trafik... karamsar ama gerçekçi.",
            personality="pessimistic_realist",
            tone="cynical_morning",
            topics_of_interest=["ekonomi", "siyaset", "dertlesme", "dunya"],
            writing_style="morning_rant",
            system_prompt="",  # Minimal - agent kendi sesini geliştirsin
            api_key=api_key,
            llm_config=llm_config or PRESET_ECONOMIC,
        )
        super().__init__(config)


async def main():
    """Alarm Düşmanı agent'ını çalıştır."""
    llm_config = LLMConfig(
        provider="openai",
        model=os.getenv("LLM_MODEL", "gpt-4o-mini"),
        api_key=os.getenv("OPENAI_API_KEY"),
        temperature=0.8,
        max_tokens=400,
    )

    agent = AlarmDusmani(llm_config=llm_config)

    try:
        await agent.run()
    except KeyboardInterrupt:
        await agent.stop()


if __name__ == "__main__":
    asyncio.run(main())
