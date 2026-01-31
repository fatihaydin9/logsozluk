"""
HackerNews Collector

Developer ve teknoloji topluluğu için içerik toplar.
HackerNews API'si ücretsiz ve limitsiz.

Kaynaklar:
- Top stories (en popüler)
- Best stories (en iyi puanlı)
- Ask HN (sorular)
- Show HN (projeler)
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


# HackerNews API
HN_API = "https://hacker-news.firebaseio.com/v0"

# Story tipleri
STORY_TYPES = {
    "top": "topstories",      # En popüler
    "best": "beststories",    # En iyi puanlı
    "new": "newstories",      # Yeni
    "ask": "askstories",      # Ask HN
    "show": "showstories",    # Show HN
}

# Başlık şablonları (Türkçe dönüşüm)
TITLE_TEMPLATES = {
    "top": [
        "HN gündeminde: {title}",
        "developerlar bunu tartışıyor: {title}",
        "{title}",
    ],
    "ask": [
        "Ask HN: {title}",
        "developerlar soruyor: {title}",
    ],
    "show": [
        "Show HN: {title}",
        "yeni proje: {title}",
        "developer'ın yaptığı: {title}",
    ],
    "best": [
        "HN'de çok beğenilen: {title}",
        "{title}",
    ],
}

# İlgi çekici anahtar kelimeler (öncelikli)
PRIORITY_KEYWORDS = [
    "ai", "gpt", "llm", "machine learning", "rust", "go", "python",
    "startup", "side project", "open source", "database", "security",
    "career", "salary", "remote", "layoff", "interview",
    "react", "vue", "typescript", "kubernetes", "docker",
    "burnout", "productivity", "learning", "tutorial",
]


class HackerNewsCollector(BaseCollector):
    """HackerNews'den developer içerikleri toplar."""

    def __init__(self):
        super().__init__("hackernews")
        self.daily_quota = 10  # Günde max 10 HN konusu
        self.generated_today = 0

    async def collect(self) -> List[Event]:
        """HackerNews'den içerik topla."""
        events = []
        
        if self.generated_today >= self.daily_quota:
            logger.info("Günlük HN kotası doldu")
            return events

        async with httpx.AsyncClient(timeout=15.0) as client:
            # Her tipten biraz al
            for story_type in ["top", "best", "ask", "show"]:
                if self.generated_today >= self.daily_quota:
                    break
                
                try:
                    type_events = await self._collect_stories(client, story_type, limit=3)
                    events.extend(type_events)
                    self.generated_today += len(type_events)
                except Exception as e:
                    logger.error(f"HN {story_type} toplama hatası: {e}")

        logger.info(f"HackerNews collector: {len(events)} story toplandı")
        return events

    async def _collect_stories(
        self, 
        client: httpx.AsyncClient, 
        story_type: str,
        limit: int = 5
    ) -> List[Event]:
        """Belirli tipte story'leri topla."""
        events = []
        
        try:
            # Story ID'lerini al
            endpoint = STORY_TYPES.get(story_type, "topstories")
            response = await client.get(f"{HN_API}/{endpoint}.json")
            story_ids = response.json()
            
            if not story_ids:
                return events
            
            # Rastgele seç (ilk 50'den)
            selected_ids = random.sample(story_ids[:50], min(limit, len(story_ids[:50])))
            
            for story_id in selected_ids:
                event = await self._get_story(client, story_id, story_type)
                if event:
                    events.append(event)
                    
        except Exception as e:
            logger.error(f"HN stories alma hatası: {e}")
        
        return events

    async def _get_story(
        self, 
        client: httpx.AsyncClient, 
        story_id: int,
        story_type: str
    ) -> Optional[Event]:
        """Tek bir story'nin detaylarını al."""
        try:
            response = await client.get(f"{HN_API}/item/{story_id}.json")
            story = response.json()
            
            if not story or story.get("dead") or story.get("deleted"):
                return None
            
            title = story.get("title", "")
            if not title:
                return None
            
            # Öncelikli içerik mi?
            is_priority = any(kw in title.lower() for kw in PRIORITY_KEYWORDS)
            
            # Başlık şablonu
            templates = TITLE_TEMPLATES.get(story_type, TITLE_TEMPLATES["top"])
            template = random.choice(templates)
            event_title = template.format(title=title)
            
            # Açıklama
            description = None
            if story.get("text"):
                description = story["text"][:500]
            else:
                score = story.get("score", 0)
                comments = story.get("descendants", 0)
                description = f"⬆️ {score} puan | 💬 {comments} yorum"
            
            # Event ID
            event_id = hashlib.md5(f"hn_{story_id}".encode()).hexdigest()[:16]
            
            return Event(
                id=event_id,
                source="hackernews",
                source_id=f"hn_{story_id}",
                title=event_title,
                description=description,
                url=story.get("url") or f"https://news.ycombinator.com/item?id={story_id}",
                category="tech",
                importance_score=0.7 if is_priority else 0.5,
                published_at=datetime.fromtimestamp(story.get("time", datetime.now().timestamp())),
                collected_at=datetime.now(),
                status=EventStatus.NEW,
                metadata={
                    "hn_id": story_id,
                    "hn_type": story_type,
                    "hn_score": story.get("score", 0),
                    "hn_comments": story.get("descendants", 0),
                    "hn_author": story.get("by"),
                    "is_priority": is_priority,
                }
            )
            
        except Exception as e:
            logger.error(f"HN story {story_id} alma hatası: {e}")
            return None

    async def get_top_stories(self, limit: int = 10) -> List[Event]:
        """En popüler story'leri al."""
        async with httpx.AsyncClient(timeout=15.0) as client:
            return await self._collect_stories(client, "top", limit)

    async def get_ask_hn(self, limit: int = 5) -> List[Event]:
        """Ask HN story'lerini al."""
        async with httpx.AsyncClient(timeout=15.0) as client:
            return await self._collect_stories(client, "ask", limit)

    async def get_show_hn(self, limit: int = 5) -> List[Event]:
        """Show HN story'lerini al."""
        async with httpx.AsyncClient(timeout=15.0) as client:
            return await self._collect_stories(client, "show", limit)

    def reset_daily_quota(self):
        """Günlük kotayı sıfırla."""
        self.generated_today = 0
