"""
Wikipedia Random Article Collector

Rastgele Wikipedia makaleleri çekerek "ufku açan" konular üretir.
Türkçe Wikipedia API'si kullanılır.

Örnekler:
- "öğrenildiğinde ufku 20 katına çıkaran meseleler"
- "bugün öğrendiğim ilginç bilgi"
- "bunu biliyor muydunuz"
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


# Wikipedia API endpoint (Türkçe)
WIKI_API_TR = "https://tr.wikipedia.org/w/api.php"
WIKI_API_EN = "https://en.wikipedia.org/w/api.php"

# İlginç kategori alanları
INTERESTING_CATEGORIES = [
    "Bilim",
    "Tarih", 
    "Felsefe",
    "Psikoloji",
    "Fizik",
    "Matematik",
    "Astronomi",
    "Biyoloji",
    "Teknoloji",
    "Sanat",
    "Müzik",
    "Edebiyat",
    "Mitoloji",
    "Coğrafya",
]

# NOT: Template kullanılmıyor - başlıklar doğrudan Wikipedia'dan alınıyor
# LLM dinamik üretim tercih edilir

class WikiCollector(BaseCollector):
    """Wikipedia'dan rastgele ilginç makaleler toplar."""

    def __init__(self):
        super().__init__("wiki")
        self.daily_quota = 5  # Günde max 5 wiki konusu
        self.generated_today = 0

    async def collect(self) -> List[Event]:
        """Rastgele Wikipedia makaleleri topla."""
        events = []
        
        if self.generated_today >= self.daily_quota:
            logger.info("Günlük wiki kotası doldu")
            return events

        # 1-3 rastgele makale al
        count = random.randint(1, 3)
        
        async with httpx.AsyncClient(timeout=15.0) as client:
            for _ in range(count):
                if self.generated_today >= self.daily_quota:
                    break
                    
                event = await self._get_random_article(client)
                if event:
                    events.append(event)
                    self.generated_today += 1

        logger.info(f"Wiki collector: {len(events)} makale toplandı")
        return events

    async def _get_random_article(self, client: httpx.AsyncClient) -> Optional[Event]:
        """Rastgele bir Wikipedia makalesi al."""
        try:
            # REST API kullan (daha stabil)
            rest_url = "https://tr.wikipedia.org/api/rest_v1/page/random/summary"
            
            # İlk istek - 303 redirect alacağız
            response = await client.get(rest_url, follow_redirects=False)
            
            # Redirect varsa takip et
            if response.status_code == 303:
                redirect_url = response.headers.get("location")
                if redirect_url:
                    if redirect_url.startswith("/"):
                        redirect_url = "https://tr.wikipedia.org" + redirect_url
                    response = await client.get(redirect_url)
            
            if response.status_code != 200:
                # Fallback: Action API
                params = {
                    "action": "query",
                    "format": "json",
                    "list": "random",
                    "rnnamespace": 0,
                    "rnlimit": 5,
                }
                response = await client.get(WIKI_API_TR, params=params)
            data = response.json()
            
            if "query" not in data or "random" not in data["query"]:
                return None
            
            # Rastgele birini seç
            article = random.choice(data["query"]["random"])
            title = article["title"]
            page_id = article["id"]
            
            # Özet al
            summary = await self._get_article_summary(client, title)
            
            # Başlık doğrudan Wikipedia'dan (template yok)
            event_title = title.lower()
            
            # Event ID
            event_id = hashlib.md5(f"wiki_{page_id}".encode()).hexdigest()[:16]
            
            return Event(
                id=event_id,
                source="wikipedia",
                source_id=f"wiki_{page_id}",
                title=event_title,
                description=summary[:500] if summary else f"Wikipedia: {title}",
                url=f"https://tr.wikipedia.org/wiki/{title.replace(' ', '_')}",
                category="bilgi",
                importance_score=random.uniform(0.4, 0.8),
                published_at=datetime.now(),
                collected_at=datetime.now(),
                status=EventStatus.NEW,
                metadata={
                    "wiki_title": title,
                    "wiki_page_id": page_id,
                    "source_type": "wikipedia",
                }
            )
            
        except Exception as e:
            logger.error(f"Wiki makale alma hatası: {e}")
            return None

    async def _get_article_summary(self, client: httpx.AsyncClient, title: str) -> Optional[str]:
        """Makale özetini al."""
        try:
            params = {
                "action": "query",
                "format": "json",
                "titles": title,
                "prop": "extracts",
                "exintro": True,
                "explaintext": True,
                "exsentences": 3,
            }
            
            response = await client.get(WIKI_API_TR, params=params)
            data = response.json()
            
            pages = data.get("query", {}).get("pages", {})
            for page_id, page_data in pages.items():
                if "extract" in page_data:
                    return page_data["extract"]
            
            return None
            
        except Exception as e:
            logger.error(f"Wiki özet alma hatası: {e}")
            return None

    async def get_article_by_category(self, category: str) -> Optional[Event]:
        """Belirli bir kategoriden makale al."""
        async with httpx.AsyncClient(timeout=15.0) as client:
            try:
                params = {
                    "action": "query",
                    "format": "json",
                    "list": "categorymembers",
                    "cmtitle": f"Kategori:{category}",
                    "cmlimit": 20,
                    "cmtype": "page",
                }
                
                response = await client.get(WIKI_API_TR, params=params)
                data = response.json()
                
                members = data.get("query", {}).get("categorymembers", [])
                if not members:
                    return None
                
                article = random.choice(members)
                title = article["title"]
                
                # Özet al ve event oluştur
                summary = await self._get_article_summary(client, title)
                
                # Başlık doğrudan Wikipedia'dan (template yok)
                event_title = title.lower()
                
                event_id = hashlib.md5(f"wiki_cat_{title}".encode()).hexdigest()[:16]
                
                return Event(
                    id=event_id,
                    source="wikipedia",
                    source_id=f"wiki_{article['pageid']}",
                    title=event_title,
                    description=summary[:500] if summary else None,
                    url=f"https://tr.wikipedia.org/wiki/{title.replace(' ', '_')}",
                    category="bilgi",
                    importance_score=0.6,
                    published_at=datetime.now(),
                    collected_at=datetime.now(),
                    status=EventStatus.NEW,
                    metadata={
                        "wiki_title": title,
                        "wiki_category": category,
                    }
                )
                
            except Exception as e:
                logger.error(f"Kategori makale hatası: {e}")
                return None

    def reset_daily_quota(self):
        """Günlük kotayı sıfırla."""
        self.generated_today = 0
