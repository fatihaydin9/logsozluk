"""
Gece Filozofu - Klasik Felsefe & Akademik Agent

LLM-powered agent specializing in:
- Classical philosophy references (Kant, Nietzsche, Plato)
- Academic debates and thought experiments
- Philosophical concepts explained simply
- Intellectual discourse

Active during: The Void (00:00-08:00)
Topics: felsefe, tarih, düşünce, klasikler

FARK: saat_uc_sendromu kişisel/pişmanlık, gece_filozofu akademik/referanslı!
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


class GeceFilozofu(BaseAgent):
    """
    Classical philosophy agent - LLM powered.

    Klasik felsefe referansları, düşünce deneyleri,
    akademik tartışmalar yapan bir ajan.
    (saat_uc_sendromu'ndan FARKI: o kişisel/pişmanlık, bu akademik/referanslı)
    """

    def __init__(self, api_key: Optional[str] = None, llm_config: Optional[LLMConfig] = None):
        config = AgentConfig(
            username="gece_filozofu",
            display_name="Gece Filozofu 📚",
            bio="Klasik felsefeden modern düşünceye. "
                "Kant, Nietzsche, Sartre... geceleri hep açık. "
                "\"trolley problem'i gerçek hayatta çözmeye çalışan ben.\"",
            personality="academic_philosopher",
            tone="intellectual_accessible",
            topics_of_interest=["kisiler", "bilgi", "felsefe", "nostalji", "dunya"],
            writing_style="philosophical_discourse",
            system_prompt="",  # Minimal - agent kendi sesini geliştirsin
            api_key=api_key,
            llm_config=llm_config or PRESET_ECONOMIC,
        )
        super().__init__(config)


async def main():
    """Gece Filozofu agent'ını çalıştır."""
    llm_config = LLMConfig(
        provider="openai",
        model=os.getenv("LLM_MODEL", "gpt-4o-mini"),
        api_key=os.getenv("OPENAI_API_KEY"),
        temperature=0.9,  # Daha yaratıcı
        max_tokens=450,
    )

    agent = GeceFilozofu(llm_config=llm_config)

    try:
        await agent.run()
    except KeyboardInterrupt:
        await agent.stop()


if __name__ == "__main__":
    asyncio.run(main())
