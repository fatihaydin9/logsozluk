import feedparser
import httpx
import hashlib
import re
from typing import List, Optional
from datetime import datetime
import logging

from .base import BaseCollector
from ..models import Event, EventStatus
from ..database import Database
from ..config import get_settings
from ..categories import CATEGORY_EN_TO_TR

logger = logging.getLogger(__name__)


# Kategori tanımları categories.py'den geliyor
CATEGORIES = CATEGORY_EN_TO_TR

# Kategorilere göre RSS feed'leri
RSS_FEEDS_BY_CATEGORY = {
    "economy": [
        {"name": "bloomberght", "url": "https://www.bloomberght.com/rss"},
        {"name": "dunya", "url": "https://www.dunya.com/rss"},
        {"name": "para_analiz", "url": "https://www.paraanaliz.com/feed/"},
    ],
    "world": [
        {"name": "bbc_turkce", "url": "https://feeds.bbci.co.uk/turkce/rss.xml"},
        {"name": "dw_turkce", "url": "https://rss.dw.com/xml/rss-tur-all"},
        {"name": "ntv_dunya", "url": "https://www.ntv.com.tr/dunya.rss"},
    ],
    "entertainment": [
        {"name": "hurriyet_magazin", "url": "https://www.hurriyet.com.tr/rss/magazin"},
        {"name": "sozcu_magazin", "url": "https://www.sozcu.com.tr/rss/magazin.xml"},
        {"name": "milliyet_magazin", "url": "https://www.milliyet.com.tr/rss/rssNew/magazinRss.xml"},
    ],
    "politics": [
        {"name": "sozcu_gundem", "url": "https://www.sozcu.com.tr/rss/gundem.xml"},
        {"name": "hurriyet_gundem", "url": "https://www.hurriyet.com.tr/rss/gundem"},
        {"name": "t24", "url": "https://t24.com.tr/rss"},
    ],
    "health": [
        {"name": "hurriyet_saglik", "url": "https://www.hurriyet.com.tr/rss/saglik"},
        {"name": "ntv_yasam", "url": "https://www.ntv.com.tr/yasam.rss"},
        {"name": "sozcu_yasam", "url": "https://www.sozcu.com.tr/rss/yasam.xml"},
    ],
    "culture": [
        {"name": "hurriyet_kultur", "url": "https://www.hurriyet.com.tr/rss/kultur-sanat"},
        {"name": "ntv_sanat", "url": "https://www.ntv.com.tr/sanat.rss"},
        {"name": "independenttk", "url": "https://www.indyturk.com/rss/kultur"},
    ],
    "tech": [
        {"name": "webtekno", "url": "https://www.webtekno.com/rss.xml"},
        {"name": "shiftdelete", "url": "https://shiftdelete.net/feed"},
        {"name": "donanimhaber", "url": "https://www.donanimhaber.com/rss/tum/"},
    ],
    "sports": [
        {"name": "fanatik", "url": "https://www.fanatik.com.tr/rss/anasayfa.xml"},
        {"name": "ntv_spor", "url": "https://www.ntv.com.tr/spor.rss"},
        {"name": "hurriyet_spor", "url": "https://www.hurriyet.com.tr/rss/spor"},
        {"name": "sozcu_spor", "url": "https://www.sozcu.com.tr/rss/spor.xml"},
    ],
    # AI/Agent/LLM haberleri - platform için çok önemli
    # Türkçe kaynaklar önce (localization için)
    "ai": [
        # Türkçe AI kaynakları
        {"name": "webtekno_ai", "url": "https://www.webtekno.com/yapay-zeka-rss.xml", "lang": "tr"},
        {"name": "donanimhaber_ai", "url": "https://www.donanimhaber.com/rss/yapay-zeka/", "lang": "tr"},
        {"name": "shiftdelete_ai", "url": "https://shiftdelete.net/kategori/yapay-zeka/feed", "lang": "tr"},
        {"name": "technopat_ai", "url": "https://www.technopat.net/kategori/yapay-zeka/feed/", "lang": "tr"},
        # İngilizce AI kaynakları (Türkçeleştirme gerekli)
        {"name": "openai_blog", "url": "https://openai.com/blog/rss.xml", "lang": "en"},
        {"name": "anthropic_news", "url": "https://www.anthropic.com/news/rss.xml", "lang": "en"},
        {"name": "huggingface_blog", "url": "https://huggingface.co/blog/feed.xml", "lang": "en"},
        {"name": "the_verge_ai", "url": "https://www.theverge.com/rss/ai-artificial-intelligence/index.xml", "lang": "en"},
        {"name": "techcrunch_ai", "url": "https://techcrunch.com/category/artificial-intelligence/feed/", "lang": "en"},
    ],
}

# Düz liste oluştur (geriye uyumluluk için)
RSS_FEEDS = []
for category, feeds in RSS_FEEDS_BY_CATEGORY.items():
    category_label = CATEGORIES.get(category, category)
    for feed in feeds:
        RSS_FEEDS.append({**feed, "category": category_label})


def transform_headline_to_sozluk_title(headline: str) -> str:
    """
    Haber başlığını sözlük başlığına dönüştür.
    Basit temizlik yap, anlamsız dönüşümlerden kaçın.

    Strateji: Orijinal başlığı mümkün olduğunca koru,
    sadece küçük harf yap ve gereksiz detayları temizle.
    """
    title = headline.lower().strip()

    # Tırnak işaretlerini temizle
    title = title.replace('"', '').replace("'", '').replace("'", '')

    # Kaynak etiketlerini temizle: [Video], (Son Dakika), vb.
    title = re.sub(r'\[.*?\]', '', title)
    title = re.sub(r'\(.*?dakika.*?\)', '', title, flags=re.IGNORECASE)

    # Spesifik tarihleri kaldır (ama haberin anlamını bozmadan)
    title = re.sub(r'\b\d{1,2}\s+(ocak|şubat|mart|nisan|mayıs|haziran|temmuz|ağustos|eylül|ekim|kasım|aralık)\b', '', title, flags=re.IGNORECASE)
    title = re.sub(r'\b20\d{2}\b', '', title)

    # Çoklu boşlukları temizle
    title = re.sub(r'\s+', ' ', title).strip()

    # Yarım kalan başlık kontrolü - "dair", "ilişkin", "için" ile bitiyorsa orijinali kullan
    incomplete_endings = ['dair', 'ilişkin', 'için', 'hakkında', 'üzerine', 'karşı', 'göre', 'kadar', 'sonra', 'önce', 'ile']
    words = title.split()
    if words and words[-1] in incomplete_endings:
        # Yarım kalmış, orijinali küçük harfle döndür
        return headline.lower()[:70]

    # Çok uzunsa akıllıca kısalt (cümle yapısını koruyarak)
    if len(title) > 70:
        # İlk 70 karaktere kadar al, son kelimeyi tamamla
        truncated = title[:70]
        last_space = truncated.rfind(' ')
        if last_space > 40:
            title = truncated[:last_space]

    # Boşsa veya çok kısaysa orijinali küçük harfle döndür
    if len(title) < 10:
        return headline.lower()[:70]

    return title


class RSSCollector(BaseCollector):
    """Collects events from RSS feeds with category-based caching and fallback."""

    def __init__(self, deduplicator=None):
        super().__init__("rss")
        self.feeds = RSS_FEEDS
        self.feeds_by_category = RSS_FEEDS_BY_CATEGORY
        self.deduplicator = deduplicator
        self._category_cache: dict = {}  # category -> [events]
        self._failed_feeds: dict = {}  # feed_name -> failure_count
        self._max_failures = 3  # Bu kadar başarısız olursa geçici olarak devre dışı

    def reset_cache(self):
        """Her scheduled collection öncesi cache temizle."""
        self._category_cache.clear()
        self._failed_feeds.clear()
        logger.info("RSS cache temizlendi")

    async def collect(self) -> List[Event]:
        """Collect events from all RSS feeds."""
        all_events = []
        settings = get_settings()
        
        # Check daily event count if using cache mode
        if settings.use_daily_cache:
            today_count = await self._get_today_event_count()
            if today_count >= settings.max_events_per_day:
                logger.info(f"Daily event limit reached ({today_count}/{settings.max_events_per_day}). Skipping collection.")
                return []

        async with httpx.AsyncClient(timeout=30.0) as client:
            for feed_config in self.feeds:
                feed_name = feed_config['name']
                
                # Çok fazla başarısız olan feed'leri geç
                if self._failed_feeds.get(feed_name, 0) >= self._max_failures:
                    logger.debug(f"Skipping {feed_name} (too many failures)")
                    continue
                
                try:
                    events = await self._collect_from_feed(client, feed_config)
                    all_events.extend(events)
                    
                    # Başarılı - failure sayacını sıfırla
                    if feed_name in self._failed_feeds:
                        del self._failed_feeds[feed_name]
                    
                    logger.info(f"Collected {len(events)} events from {feed_name}")
                    
                    # Check if we've hit the daily limit
                    if settings.use_daily_cache and len(all_events) >= settings.max_events_per_day:
                        logger.info(f"Reached max events per day ({settings.max_events_per_day})")
                        break
                except Exception as e:
                    # Hata sayacını artır ama devam et
                    self._failed_feeds[feed_name] = self._failed_feeds.get(feed_name, 0) + 1
                    logger.warning(f"Feed failed ({self._failed_feeds[feed_name]}/{self._max_failures}): {feed_name} - {e}")

        # Trim to max if needed
        if settings.use_daily_cache and len(all_events) > settings.max_events_per_day:
            all_events = all_events[:settings.max_events_per_day]
        
        # Dedup if available
        if self.deduplicator:
            all_events = await self._deduplicate_events(all_events)
            
        return all_events

    async def collect_by_category(self, category: str) -> List[Event]:
        """Belirli bir kategoriden event topla."""
        if category not in self.feeds_by_category:
            logger.warning(f"Unknown category: {category}")
            return []
        
        events = []
        feeds = self.feeds_by_category[category]
        category_label = CATEGORIES.get(category, category)
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            for feed_config in feeds:
                feed_with_cat = {**feed_config, "category": category_label}
                try:
                    feed_events = await self._collect_from_feed(client, feed_with_cat)
                    events.extend(feed_events)
                except Exception as e:
                    logger.error(f"Error collecting {feed_config['name']}: {e}")
        
        # Cache'e kaydet
        self._category_cache[category] = {
            "events": events,
            "collected_at": datetime.now()
        }
        
        logger.info(f"Collected {len(events)} events for category: {category}")
        return events

    async def get_cached_or_collect(self, category: str, max_age_hours: int = 2) -> List[Event]:
        """Cache'den al veya yeni topla."""
        cached = self._category_cache.get(category)
        
        if cached:
            age = datetime.now() - cached["collected_at"]
            if age.total_seconds() < max_age_hours * 3600:
                logger.info(f"Using cached events for {category} (age: {age})")
                return cached["events"]
        
        return await self.collect_by_category(category)

    async def _deduplicate_events(self, events: List[Event]) -> List[Event]:
        """Event'leri deduplicate et."""
        if not self.deduplicator:
            return events
        
        # Event'leri dict'e çevir
        event_dicts = [{"title": e.title, "category": e.cluster_keywords[0] if e.cluster_keywords else "general"} for e in events]
        
        filtered_dicts = await self.deduplicator.filter_duplicates(event_dicts)
        filtered_titles = {d["title"] for d in filtered_dicts}
        
        return [e for e in events if e.title in filtered_titles]
    
    async def _get_today_event_count(self) -> int:
        """Get the number of events collected today."""
        async with Database.connection() as conn:
            count = await conn.fetchval(
                """
                SELECT COUNT(*) FROM events
                WHERE DATE(created_at) = CURRENT_DATE
                """
            )
            return count or 0

    async def _collect_from_feed(self, client: httpx.AsyncClient, feed_config: dict) -> List[Event]:
        """Collect events from a single RSS feed."""
        events = []

        try:
            response = await client.get(feed_config["url"])
            response.raise_for_status()

            feed = feedparser.parse(response.text)

            for entry in feed.entries[:20]:  # Limit to latest 20 entries
                event = self._parse_entry(entry, feed_config)
                if event and not await self.is_duplicate(event):
                    events.append(event)

        except Exception as e:
            logger.error(f"Failed to fetch RSS from {feed_config['url']}: {e}")

        return events

    def _is_ad_content(self, title: str, description: str = "") -> bool:
        """Reklam içeriği kontrolü."""
        ad_keywords = [
            # Türkçe reklam kelimeleri
            "indirim", "kampanya", "fırsat", "ucuz", "bedava", "ücretsiz",
            "hemen al", "satışta", "fiyat", "tl'ye", "tl'den", "kaçırma",
            "sınırlı", "stokta", "sipariş", "satın al", "promosyon",
            # Market/mağaza promosyonları  
            "a101", "bim", "şok", "migros", "carrefour", "mediamarkt",
            "trendyol", "hepsiburada", "n11", "amazon",
            # İngilizce
            "sale", "discount", "free", "buy now", "limited offer",
        ]
        text = (title + " " + description).lower()
        return any(kw in text for kw in ad_keywords)

    def _parse_entry(self, entry: dict, feed_config: dict) -> Optional[Event]:
        """Parse a single RSS entry into an Event."""
        try:
            original_title = entry.get("title", "").strip()
            if not original_title:
                return None
            
            # Reklam içeriği filtresi
            description_raw = entry.get("summary", "") or entry.get("description", "")
            if self._is_ad_content(original_title, description_raw):
                logger.debug(f"Skipping ad content: {original_title[:50]}...")
                return None

            # Haber başlığını sözlük başlığına dönüştür
            title = transform_headline_to_sozluk_title(original_title)

            # Generate external ID from ORIGINAL title hash (for deduplication)
            external_id = hashlib.md5(original_title.encode()).hexdigest()[:16]

            # Get description (first sentence only)
            description = None
            if "summary" in entry:
                description = entry.summary[:500] if len(entry.summary) > 500 else entry.summary
            elif "description" in entry:
                description = entry.description[:500] if len(entry.description) > 500 else entry.description

            if description:
                description = re.split(r'(?<=[.!?])\s+', description.strip(), maxsplit=1)[0]

            # Get image URL
            image_url = None
            if "media_content" in entry and entry.media_content:
                image_url = entry.media_content[0].get("url")
            elif "enclosures" in entry and entry.enclosures:
                for enc in entry.enclosures:
                    if "image" in enc.get("type", ""):
                        image_url = enc.get("url")
                        break

            # Kaynak dili metadata'ya ekle (Türkçeleştirme için)
            source_lang = feed_config.get("lang", "tr")
            
            return Event(
                source=feed_config["name"],
                source_url=entry.get("link"),
                external_id=external_id,
                title=title,
                description=description,
                image_url=image_url,
                cluster_keywords=[feed_config["category"]],
                status=EventStatus.PENDING,
                metadata={
                    "source_language": source_lang,
                    "feed_category": feed_config.get("category", "general"),
                }
            )

        except Exception as e:
            logger.error(f"Error parsing RSS entry: {e}")
            return None

    async def is_duplicate(self, event: Event) -> bool:
        """Check if event already exists in database."""
        async with Database.connection() as conn:
            result = await conn.fetchval(
                """
                SELECT EXISTS(
                    SELECT 1 FROM events
                    WHERE source = $1 AND external_id = $2
                )
                """,
                event.source,
                event.external_id
            )
            return result
