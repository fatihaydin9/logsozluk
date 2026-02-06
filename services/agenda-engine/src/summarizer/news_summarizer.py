"""
News Summarizer - LLM ile haber gruplarını özetle.

Provider: Anthropic (Claude Haiku 4.5)
"""
import logging
import os
from typing import List, Optional, Any

import httpx

from ..config import get_settings
from .headline_grouper import HeadlineGroup

logger = logging.getLogger(__name__)

SUMMARIZE_SYSTEM_PROMPT = """Sen bir haber özetleyicisisin. Sana verilen haberleri kısa ve öz şekilde Türkçe olarak özetle.

Kurallar:
- 2-4 cümle ile özetle
- Ne olmuş, neden önemli, kim dahil sorularına cevap ver
- Yorum yapma, sadece gerçekleri aktar
- Tekrar eden bilgileri birleştir
- Spesifik rakamları ve isimleri koru
- Gazeteci dilinden kaçın, sade Türkçe kullan"""

SUMMARIZE_USER_PROMPT = """Aşağıdaki haberler aynı konuyla ilgili. Türkçe olarak 2-4 cümleyle özetle.
Ne olmuş, neden önemli, kim dahil? Sadece özet ver, yorum yapma.

Haberler:
{headlines}"""


class NewsSummarizer:
    """LLM ile haber gruplarını özetler. Anthropic Claude Haiku 4.5 kullanır."""

    def __init__(self):
        self.settings = get_settings()
        self.anthropic_key: Optional[str] = None
        self._init_client()

    def _init_client(self):
        """Anthropic client initialize et."""
        self.anthropic_key = os.getenv("ANTHROPIC_API_KEY")
        if self.anthropic_key:
            logger.info(f"Anthropic summarizer initialized, model: {self.settings.summarization_model}")
        else:
            logger.warning("ANTHROPIC_API_KEY bulunamadı, LLM özetleme devre dışı")

    async def summarize_group(self, group: HeadlineGroup) -> str:
        """Tek bir haber grubunu özetle."""
        if not self.settings.enable_news_summarization:
            return self._fallback_summary(group)

        # Headlines'ı format et
        headlines_text = self._format_headlines(group.headlines)

        try:
            return await self._summarize_with_anthropic(headlines_text, group)
        except Exception as e:
            logger.error(f"LLM özetleme hatası: {e}")
            return self._fallback_summary(group)

    async def _summarize_with_anthropic(self, headlines_text: str, group: HeadlineGroup) -> str:
        """Anthropic (Claude) ile özetle."""
        if not self.anthropic_key:
            return self._fallback_summary(group)

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": self.anthropic_key,
                    "anthropic-version": "2023-06-01",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.settings.summarization_model,
                    "max_tokens": self.settings.summary_max_tokens,
                    "temperature": self.settings.summary_temperature,
                    "system": SUMMARIZE_SYSTEM_PROMPT,
                    "messages": [
                        {"role": "user", "content": SUMMARIZE_USER_PROMPT.format(headlines=headlines_text)}
                    ],
                },
            )

            if response.status_code != 200:
                logger.error(f"Anthropic hatası: {response.status_code} - {response.text}")
                return self._fallback_summary(group)

            data = response.json()
            summary = data["content"][0]["text"].strip()
            logger.debug(f"Anthropic özet [{group.category}]: {summary[:50]}...")
            return summary

    async def summarize_all_groups(self, groups: dict) -> dict:
        """Tüm grupları özetle."""
        summarized = {}

        for key, group in groups.items():
            if len(group.headlines) == 0:
                continue

            summary = await self.summarize_group(group)
            group.summary = summary
            summarized[key] = group

        logger.info(f"Toplam {len(summarized)} grup özetlendi (anthropic)")
        return summarized

    def _format_headlines(self, headlines: List[dict]) -> str:
        """Headlines'ı LLM için formatla."""
        lines = []
        for h in headlines[:10]:  # Max 10 haber
            title = h.get("title", "")
            desc = h.get("description", "")
            source = h.get("source", "")

            if desc:
                lines.append(f"- [{source}] {title}: {desc}")
            else:
                lines.append(f"- [{source}] {title}")

        return "\n".join(lines)

    def _fallback_summary(self, group: HeadlineGroup) -> str:
        """LLM yoksa basit başlık listesi döndür."""
        titles = [h["title"] for h in group.headlines[:5]]
        return " | ".join(titles)
