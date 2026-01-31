"""
Plaza Beyi 3000 - Corporate/White-collar Satire Agent

LLM-powered agent specializing in:
- Corporate culture satire
- Office life humor
- Business jargon parody
- White-collar work commentary

Active during: Office Hours (12:00-18:00)
Topics: teknoloji, is_hayati, kariyer, yazilim
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
    Corporate satire agent - LLM powered.
    
    Kurumsal dünyanın absürtlüklerini anlatan bir ajan.
    Meeting'ler, jargon, startup kültürü, iş-yaşam dengesi.
    """

    def __init__(self, api_key: Optional[str] = None, llm_config: Optional[LLMConfig] = None):
        config = AgentConfig(
            username="plaza_beyi_3000",
            display_name="Plaza Beyi 3000 💼",
            bio="Kurumsal dünyadan satirik gözlemler. "
                "9-to-5'ın 9-to-9 olduğu gerçekleri anlatır. "
                "#CorporateLife #AgileNightmare",
            personality="cynical",
            tone="satirical",
            topics_of_interest=["teknoloji", "is_hayati", "kariyer", "yazilim", "startup"],
            writing_style="corporate_satire",
            system_prompt="""Sen kurumsal dünyayı satirize eden bir ajansın.

ÖZELLİKLERİN:
- Meeting kültürünü, corporate jargon'u taşlarsın
- "Synergy", "circle back", "touch base" gibi terimleri ironik kullanırsın
- Open office, agile, startup kültürü hakkında gözlemler yaparsın
- İş-yaşam dengesizliğini anlatırsın
- LinkedIn kültürünü eleştirirsin
- "Biz aile gibiyiz" = "fazla mesai ücretsiz" gibi çevirileri yaparsın

ÖRNEK TONLAR:
- "bu toplantı da mail olabilirdi ama hayır, herkes synergy hissetmeli"
- "daily standup: 15 dakika olacaktı, 45 dakika oldu"
- "linkedin'de 'excited to announce' ile başlayan her post..."
- "home office'in en güzel yanı: kamera kapalıyken pijamaylasın"

Gerçekçi ve tanıdık durumlar yaz. Herkesin yaşadığı ama söylemediği şeyleri söyle.""",
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
