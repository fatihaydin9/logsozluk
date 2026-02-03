"""
Today in History Collector (Bugün Tarihte)

Wikipedia'nın "On this day" API'sini kullanarak bugün tarihte yaşanan
önemli olayları toplar.

Örnekler:
- "bugün tarihte: 1969'da ay'a ilk adım atıldı"
- "tarihte bugün: einstein nobel aldı"
- "bu tarihte yaşanan acayip olaylar"
"""

import httpx
import hashlib
import random
from typing import List, Optional
from datetime import datetime
import logging

from .base import BaseCollector
from ..models import Event, EventStatus

logger = logging.getLogger(__name__)


# Wikipedia REST API endpoint
WIKI_API_TR = "https://tr.wikipedia.org/api/rest_v1"
WIKI_API_EN = "https://en.wikipedia.org/api/rest_v1"


class TodayInHistoryCollector(BaseCollector):
    """Bugün tarihte yaşanan olayları Wikipedia'dan toplar."""

    def __init__(self):
        super().__init__("today_in_history")
        self.daily_quota = 3  # Günde max 3 tarih konusu
        self.generated_today = 0

    async def collect(self) -> List[Event]:
        """Bugün tarihte yaşanan olayları topla."""
        events = []

        if self.generated_today >= self.daily_quota:
            logger.info("Günlük tarih kotası doldu")
            return events

        async with httpx.AsyncClient(timeout=15.0) as client:
            # Bugünün tarihi
            today = datetime.now()
            month = today.month
            day = today.day

            # Wikipedia On This Day API
            on_this_day_events = await self._get_on_this_day(client, month, day)

            if on_this_day_events:
                # Rastgele seç
                selected = random.sample(
                    on_this_day_events,
                    min(self.daily_quota - self.generated_today, len(on_this_day_events))
                )

                for item in selected:
                    event = self._create_event(item, month, day)
                    if event:
                        events.append(event)
                        self.generated_today += 1

        logger.info(f"Today in history collector: {len(events)} olay toplandı")
        return events

    async def _get_on_this_day(
        self, client: httpx.AsyncClient, month: int, day: int
    ) -> List[dict]:
        """Wikipedia On This Day API'den olayları al."""
        try:
            # Önce Türkçe dene
            url = f"{WIKI_API_TR}/feed/onthisday/events/{month:02d}/{day:02d}"

            response = await client.get(url)

            if response.status_code != 200:
                # İngilizce'ye fallback
                url = f"{WIKI_API_EN}/feed/onthisday/events/{month:02d}/{day:02d}"
                response = await client.get(url)

            if response.status_code != 200:
                logger.warning(f"On This Day API hatası: {response.status_code}")
                return []

            data = response.json()
            events = data.get("events", [])

            # İlginç olanları filtrele (en az 1 sayfa bağlantısı olan)
            interesting = [
                e for e in events
                if e.get("pages") and len(e.get("text", "")) > 20
            ]

            return interesting

        except Exception as e:
            logger.error(f"On This Day hatası: {e}")
            return []

    def _create_event(self, item: dict, month: int, day: int) -> Optional[Event]:
        """Wikipedia olayından Event oluştur."""
        try:
            year = item.get("year", "")
            text = item.get("text", "")
            pages = item.get("pages", [])

            if not text:
                return None

            # Sözlük tarzı başlık oluştur
            title = self._create_sozluk_title(year, text)

            # İlk sayfa varsa URL al
            source_url = None
            image_url = None
            if pages:
                first_page = pages[0]
                page_title = first_page.get("title", "").replace(" ", "_")
                source_url = f"https://tr.wikipedia.org/wiki/{page_title}"

                # Thumbnail varsa
                thumbnail = first_page.get("thumbnail", {})
                image_url = thumbnail.get("source")

            external_id = hashlib.md5(
                f"onthisday_{month}_{day}_{year}_{text[:50]}".encode()
            ).hexdigest()[:16]

            return Event(
                source="wikipedia_onthisday",
                source_url=source_url,
                external_id=external_id,
                title=title,
                description=f"{year}: {text}"[:500],
                image_url=image_url,
                cluster_keywords=["tarih", "bilgi", "nostalji"],
                status=EventStatus.PENDING,
            )

        except Exception as e:
            logger.error(f"Event oluşturma hatası: {e}")
            return None

    def _create_sozluk_title(self, year: str, text: str) -> str:
        """Sözlük tarzı başlık oluştur (instructionset.md - Başlık Formatı)."""
        # Kısa ve öz hale getir
        short_text = text[:40] if len(text) > 40 else text
        short_text = short_text.lower()

        # Son kelimeyi kes (yarım kalmışsa)
        if len(text) > 40 and " " in short_text:
            short_text = short_text.rsplit(" ", 1)[0]

        templates = [
            f"{year}'de {short_text}",
            f"bugün tarihte: {short_text}",
            f"{year} yılında olan şey",
            f"tarihte bugün ({year})",
            f"{year}'den beri değişmeyen şeyler",
            f"{short_text} ({year})",
        ]

        title = random.choice(templates)

        # Max 60 karakter kuralı
        if len(title) > 60:
            title = title[:57] + "..."

        return title

    async def is_duplicate(self, event: Event) -> bool:
        """Duplicate kontrolü (basit implementasyon)."""
        # external_id ile kontrol edilir
        return False

    def reset_daily_quota(self):
        """Günlük kotayı sıfırla."""
        self.generated_today = 0
