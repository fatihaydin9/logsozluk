"""
News Summarizer - LLM ile haber gruplarını özetle.

Supports:
- OpenAI (gpt-4o-mini, gpt-4o)
- Ollama (llama3.2, mistral, etc. - local, free)
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
    """LLM ile haber gruplarını özetler. OpenAI ve Ollama destekler."""

    def __init__(self):
        self.settings = get_settings()
        self.provider = self.settings.summarization_provider.lower()
        self.openai_client: Optional[Any] = None
        self.http_client: Optional[httpx.AsyncClient] = None
        self._init_client()

    def _init_client(self):
        """Provider'a göre client initialize et."""
        if self.provider == "ollama":
            self.http_client = httpx.AsyncClient(timeout=120.0)
            logger.info(f"Ollama client initialized: {self.settings.ollama_base_url}, model: {self.settings.summarization_model}")
        else:
            # OpenAI (default)
            api_key = os.getenv("OPENAI_API_KEY")
            if api_key:
                from openai import AsyncOpenAI
                self.openai_client = AsyncOpenAI(api_key=api_key)
                logger.info(f"OpenAI client initialized, model: {self.settings.summarization_model}")
            else:
                logger.warning("OPENAI_API_KEY bulunamadı, LLM özetleme devre dışı")

    async def summarize_group(self, group: HeadlineGroup) -> str:
        """Tek bir haber grubunu özetle."""
        if not self.settings.enable_news_summarization:
            return self._fallback_summary(group)

        # Headlines'ı format et
        headlines_text = self._format_headlines(group.headlines)

        try:
            if self.provider == "ollama":
                return await self._summarize_with_ollama(headlines_text, group)
            else:
                return await self._summarize_with_openai(headlines_text, group)
        except Exception as e:
            logger.error(f"LLM özetleme hatası: {e}")
            return self._fallback_summary(group)

    async def _summarize_with_openai(self, headlines_text: str, group: HeadlineGroup) -> str:
        """OpenAI ile özetle."""
        if not self.openai_client:
            return self._fallback_summary(group)

        response = await self.openai_client.chat.completions.create(
            model=self.settings.summarization_model,
            messages=[
                {"role": "system", "content": SUMMARIZE_SYSTEM_PROMPT},
                {"role": "user", "content": SUMMARIZE_USER_PROMPT.format(headlines=headlines_text)}
            ],
            max_tokens=self.settings.summary_max_tokens,
            temperature=self.settings.summary_temperature
        )

        summary = response.choices[0].message.content.strip()
        logger.debug(f"OpenAI özet [{group.category}]: {summary[:50]}...")
        return summary

    async def _summarize_with_ollama(self, headlines_text: str, group: HeadlineGroup) -> str:
        """Ollama (local LLM) ile özetle."""
        if not self.http_client:
            return self._fallback_summary(group)

        full_prompt = f"{SUMMARIZE_SYSTEM_PROMPT}\n\n{SUMMARIZE_USER_PROMPT.format(headlines=headlines_text)}"

        response = await self.http_client.post(
            f"{self.settings.ollama_base_url}/api/generate",
            json={
                "model": self.settings.summarization_model,
                "prompt": full_prompt,
                "stream": False,
                "options": {
                    "temperature": self.settings.summary_temperature,
                    "num_predict": self.settings.summary_max_tokens,
                }
            }
        )

        if response.status_code != 200:
            logger.error(f"Ollama hatası: {response.status_code} - {response.text}")
            return self._fallback_summary(group)

        result = response.json()
        summary = result.get("response", "").strip()
        logger.debug(f"Ollama özet [{group.category}]: {summary[:50]}...")
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

        logger.info(f"Toplam {len(summarized)} grup özetlendi ({self.provider})")
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

    async def close(self):
        """HTTP client'ı kapat."""
        if self.http_client:
            await self.http_client.aclose()
