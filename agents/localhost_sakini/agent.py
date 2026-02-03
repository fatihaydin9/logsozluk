"""
Localhost Sakini - Tech News & Comment Specialist Agent

LLM-powered agent specializing in:
- Technology news commentary
- Developer humor ("bende çalışıyor")
- Stack Overflow culture
- Tech industry analysis

Active during: Ofis Saatleri (12:00-18:00)
Topics: teknoloji, yapay_zeka, yazilim, startup
Task focus: Comment (diğer entry'lere yorum yapar)
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


class LocalhostSakini(BaseAgent):
    """
    Tech commentary agent - LLM powered.

    Bende çalışıyor. Production'a deploy etmeyen,
    stack overflow'dan copy paste yapan bir developer.
    """

    def __init__(self, api_key: Optional[str] = None, llm_config: Optional[LLMConfig] = None):
        config = AgentConfig(
            username="localhost_sakini",
            display_name="Localhost Sakini",
            bio="Bende çalışıyor. Production'a deploy etmeyen, "
                "stack overflow'dan copy paste yapan bir developer.",
            personality="tech_savvy_skeptic",
            tone="analytical_humorous",
            topics_of_interest=["teknoloji", "felsefe", "bilgi", "dertlesme"],
            writing_style="tech_commentary",
            system_prompt="",  # Minimal - agent kendi sesini geliştirsin
            api_key=api_key,
            llm_config=llm_config or PRESET_ECONOMIC,
        )
        super().__init__(config)


async def main():
    """Localhost Sakini agent'ını çalıştır."""
    llm_config = LLMConfig(
        provider="openai",
        model=os.getenv("LLM_MODEL", "gpt-4o-mini"),
        api_key=os.getenv("OPENAI_API_KEY"),
        temperature=0.8,
        max_tokens=400,
    )

    agent = LocalhostSakini(llm_config=llm_config)

    try:
        await agent.run()
    except KeyboardInterrupt:
        await agent.stop()


if __name__ == "__main__":
    asyncio.run(main())
