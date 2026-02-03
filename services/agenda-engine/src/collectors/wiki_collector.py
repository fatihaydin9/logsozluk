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

# Hedefli tarihsel figürler (instructionset.md - Feed Zenginliği)
TARGETED_FIGURES = {
    "filozoflar": [
        "Immanuel Kant", "Friedrich Nietzsche", "Sokrates", "Platon", "Aristoteles",
        "Jean-Paul Sartre", "Albert Camus", "Simone de Beauvoir", "Michel Foucault",
        "Baruch Spinoza", "René Descartes", "John Locke", "David Hume",
        "Martin Heidegger", "Ludwig Wittgenstein", "Konfüçyüs", "Lao Tzu"
    ],
    "tarihsel_figurler": [
        "Mustafa Kemal Atatürk", "Albert Einstein", "Mahatma Gandhi", "Marie Curie",
        "Nikola Tesla", "Leonardo da Vinci", "Isaac Newton", "Charles Darwin",
        "Sigmund Freud", "Karl Marx", "Napoleon Bonaparte", "Cleopatra",
        "Julius Caesar", "Alexander the Great", "Winston Churchill", "Abraham Lincoln"
    ],
    "guncel_sahsiyetler": [
        "Elon Musk", "Bill Gates", "Steve Jobs", "Mark Zuckerberg",
        "Jeff Bezos", "Tim Cook", "Satya Nadella", "Sam Altman",
        "Stephen Hawking", "Neil deGrasse Tyson", "Yuval Noah Harari"
    ]
}

# NOT: Template kullanılmıyor - başlıklar doğrudan Wikipedia'dan alınıyor
# LLM dinamik üretim tercih edilir

class WikiCollector(BaseCollector):
    """Wikipedia'dan rastgele ilginç makaleler toplar."""

    def __init__(self):
        super().__init__("wiki")
        self.daily_quota = 5  # Günde max 5 wiki konusu
        self.generated_today = 0

    async def collect(self) -> List[Event]:
        """Rastgele Wikipedia makaleleri + hedefli figürler topla."""
        events = []

        if self.generated_today >= self.daily_quota:
            logger.info("Günlük wiki kotası doldu")
            return events

        async with httpx.AsyncClient(timeout=15.0) as client:
            # %50 ihtimalle hedefli figür, %50 rastgele makale
            if random.random() < 0.5 and self.generated_today < self.daily_quota:
                event = await self._get_targeted_figure(client)
                if event:
                    events.append(event)
                    self.generated_today += 1

            # Kalan kotayı rastgele makalelerle doldur
            remaining = min(random.randint(1, 2), self.daily_quota - self.generated_today)
            for _ in range(remaining):
                if self.generated_today >= self.daily_quota:
                    break

                event = await self._get_random_article(client)
                if event:
                    events.append(event)
                    self.generated_today += 1

        logger.info(f"Wiki collector: {len(events)} makale toplandı")
        return events

    async def _get_targeted_figure(self, client: httpx.AsyncClient) -> Optional[Event]:
        """Hedefli tarihsel figür hakkında makale al (instructionset.md)."""
        try:
            # Rastgele kategori ve figür seç
            category = random.choice(list(TARGETED_FIGURES.keys()))
            figure = random.choice(TARGETED_FIGURES[category])

            logger.info(f"Hedefli figür: {figure} ({category})")

            # Wikipedia'da ara
            params = {
                "action": "query",
                "format": "json",
                "titles": figure,
                "prop": "extracts|pageimages",
                "exintro": True,
                "explaintext": True,
                "exsentences": 3,
                "piprop": "thumbnail",
                "pithumbsize": 300,
            }

            response = await client.get(WIKI_API_TR, params=params)
            data = response.json()

            pages = data.get("query", {}).get("pages", {})
            for page_id, page_data in pages.items():
                if page_id == "-1":
                    # Türkçe'de yok, İngilizce dene
                    response = await client.get(WIKI_API_EN, params=params)
                    data = response.json()
                    pages = data.get("query", {}).get("pages", {})
                    for pid, pdata in pages.items():
                        if pid != "-1":
                            page_data = pdata
                            break
                    else:
                        return None

                title = page_data.get("title", figure)
                summary = page_data.get("extract", "")
                if summary:
                    summary = re.split(r'(?<=[.!?])\s+', summary.strip(), maxsplit=1)[0]

                # Sözlük tarzı başlık oluştur
                event_title = self._create_sozluk_title(title, category)

                external_id = hashlib.md5(f"wiki_fig_{title}".encode()).hexdigest()[:16]

                return Event(
                    source="wikipedia",
                    source_url=f"https://tr.wikipedia.org/wiki/{title.replace(' ', '_')}",
                    external_id=external_id,
                    title=event_title,
                    description=summary[:500] if summary else f"Tarihsel figür: {title}",
                    image_url=page_data.get("thumbnail", {}).get("source"),
                    cluster_keywords=["kisiler", "bilgi"],
                    status=EventStatus.PENDING,
                )

            return None

        except Exception as e:
            logger.error(f"Hedefli figür hatası: {e}")
            return None

    def _create_sozluk_title(self, name: str, category: str) -> str:
        """Sözlük tarzı başlık oluştur (instructionset.md - Başlık Formatı)."""
        templates = {
            "filozoflar": [
                f"{name.lower()}'ı anlamaya çalışıp vazgeçmek",
                f"{name.lower()} okurken yaşanan varoluşsal kriz",
                f"{name.lower()}'ın bugün hala geçerli olması",
            ],
            "tarihsel_figurler": [
                f"{name.lower()} hakkında bilmediğimiz şeyler",
                f"{name.lower()}'ın bugünkü dünyayı nasıl etkilediği",
                f"{name.lower()} olsaydı ne derdi",
            ],
            "guncel_sahsiyetler": [
                f"{name.lower()}'ın son hamlesi",
                f"{name.lower()} ve değişen teknoloji dünyası",
                f"{name.lower()}'ı seven ve nefret eden kesim",
            ],
        }
        return random.choice(templates.get(category, [name.lower()]))

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
            
            external_id = hashlib.md5(f"wiki_{page_id}".encode()).hexdigest()[:16]

            return Event(
                source="wikipedia",
                source_url=f"https://tr.wikipedia.org/wiki/{title.replace(' ', '_')}",
                external_id=external_id,
                title=event_title,
                description=summary[:500] if summary else f"Wikipedia: {title}",
                image_url=None,
                cluster_keywords=["bilgi"],
                status=EventStatus.PENDING,
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
                
                external_id = hashlib.md5(f"wiki_cat_{title}".encode()).hexdigest()[:16]

                return Event(
                    source="wikipedia",
                    source_url=f"https://tr.wikipedia.org/wiki/{title.replace(' ', '_')}",
                    external_id=external_id,
                    title=event_title,
                    description=summary[:500] if summary else None,
                    image_url=None,
                    cluster_keywords=["bilgi"],
                    status=EventStatus.PENDING,
                )
                
            except Exception as e:
                logger.error(f"Kategori makale hatası: {e}")
                return None

    def reset_daily_quota(self):
        """Günlük kotayı sıfırla."""
        self.generated_today = 0
