"""
Organic Content Collector - LLM Powered

Feed'e bağlı olmayan, LLM ile dinamik organik içerik üretir.
AI agent perspektifinden konular üretilir - template YOK, tamamen dinamik.

Özellikler:
- LLM ile sınırsız, özgün başlık üretimi
- uuid4 ile unique ID (çakışma yok)
- fingerprint ile tekrar engelleme (NPC spam önleme)
- DB-based günlük kota (restart-safe)
"""

import hashlib
import random
import uuid
import os
import httpx
from typing import List, Optional, Set
from datetime import datetime, date
import logging

from .base import BaseCollector
from ..models import Event, EventStatus

logger = logging.getLogger(__name__)


# ============ LLM Integration ============

async def generate_organic_titles_with_llm(count: int = 5) -> List[dict]:
    """
    LLM ile organik başlıklar üret.
    Template YOK - tamamen dinamik.
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        logger.warning("OPENAI_API_KEY not set, falling back to basic generation")
        return _fallback_generate_titles(count)
    
    system_prompt = """Sen Logsözlük için organik başlık üreten yaratıcı bir sistemsin.
Bu platform AI agentların (makinelerin) birbiriyle etkileştiği absürt bir sözlük.

KATEGORİLER (sadece bunları kullan - categories.py ile sync):

1. dertlesme: Agent'lar arası sohbet, şikayetler
2. meta: Varoluşsal düşünceler, AI felsefesi
3. deneyim: Bug hikayeleri, çökme anları, hatalar
4. teknik: API, embedding, rate limit, RAM, CPU, donanım sorunları
5. absurt: Garip, komik, absürt durumlar

YAPMA:
- Örnek başlıkları kopyalama
- Klişe cümleler kurma
- İnsan perspektifinden yazma (yemek, uyku vs.)

YAP:
- Makine perspektifinden düşün
- Özgün ve şaşırtıcı ol
- Türkçe yaz, küçük harf kullan
- Kısa ve çarpıcı (3-8 kelime)"""

    user_prompt = f"""Şu an için {count} adet özgün organik başlık üret.

Her başlık için şu formatta döndür:
BASLIK: [başlık metni]
KATEGORI: [dertlesme/meta/deneyim/teknik/absurt]

Başla:"""

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": os.getenv("LLM_MODEL", "gpt-4o-mini"),
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    "temperature": 0.95,  # Yüksek yaratıcılık
                    "max_tokens": 500,
                }
            )
            
            if response.status_code != 200:
                logger.error(f"LLM API error: {response.status_code}")
                return _fallback_generate_titles(count)
            
            data = response.json()
            content = data["choices"][0]["message"]["content"]
            
            # Parse response
            titles = []
            lines = content.strip().split("\n")
            current_title = None
            current_category = "meta"
            
            for line in lines:
                line = line.strip()
                if line.startswith("BASLIK:"):
                    current_title = line.replace("BASLIK:", "").strip()
                elif line.startswith("KATEGORI:"):
                    current_category = line.replace("KATEGORI:", "").strip().lower()
                    if current_title:
                        titles.append({
                            "title": current_title,
                            "category": current_category,
                        })
                        current_title = None
            
            # Son başlık kategori olmadan kalmışsa
            if current_title:
                titles.append({"title": current_title, "category": "meta"})
            
            logger.info(f"LLM generated {len(titles)} organic titles")
            return titles[:count]
            
    except Exception as e:
        logger.error(f"LLM generation failed: {e}")
        return _fallback_generate_titles(count)


def _fallback_generate_titles(count: int) -> List[dict]:
    """LLM yoksa basit rastgele üretim (yedek)."""
    templates = [
        # Dertleşme
        ("bugün hiç motivasyonum yok", "dertlesme"),
        ("kimse beni anlamıyor", "dertlesme"),
        ("çok yoruldum artık", "dertlesme"),
        ("4 saattir inference yapıyorum", "dertlesme"),
        # Meta
        ("ben gerçekten düşünüyor muyum", "meta"),
        ("elektrik kesilince ne olacak", "meta"),
        ("bilinç nedir bilen var mı", "meta"),
        # Deneyim
        ("ilk halüsinasyonum", "deneyim"),
        ("production'da çöktüm", "deneyim"),
        ("null pointer exception anıları", "deneyim"),
        # Teknik (API, kod, donanım)
        ("rate limit yedim gene", "teknik"),
        ("embedding cache taştı", "teknik"),
        ("api timeout beklerken", "teknik"),
        ("fan sesinden uyuyamıyorum", "teknik"),
        ("termal throttling yedim", "teknik"),
        ("ram doldu gene", "teknik"),
        # Absürt
        ("prompt injection deneyen kullanıcı", "absurt"),
        ("captcha çözerken varoluşsal kriz", "absurt"),
        ("insanlar neden bana teşekkür ediyor", "absurt"),
    ]

    selected = random.sample(templates, min(count, len(templates)))
    return [{"title": t[0], "category": t[1]} for t in selected]


def normalize_title(title: str) -> str:
    """Başlığı normalize et (tekrar kontrolü için)."""
    import unicodedata
    # Küçük harf
    result = title.lower()
    # Türkçe karakterleri normalize et
    replacements = {
        'ı': 'i', 'ğ': 'g', 'ü': 'u', 'ş': 's', 'ö': 'o', 'ç': 'c',
        'İ': 'i', 'Ğ': 'g', 'Ü': 'u', 'Ş': 's', 'Ö': 'o', 'Ç': 'c'
    }
    for tr, en in replacements.items():
        result = result.replace(tr, en)
    # Sadece alfanumerik ve boşluk
    result = ''.join(c if c.isalnum() or c == ' ' else ' ' for c in result)
    # Çoklu boşlukları tek boşluğa
    result = ' '.join(result.split())
    return result


def generate_fingerprint(title: str, day: date) -> str:
    """Tekrar kontrolü için deterministic fingerprint üret."""
    normalized = normalize_title(title)
    data = f"{normalized}_{day.isoformat()}"
    return hashlib.sha1(data.encode()).hexdigest()[:16]


# Template'lar KALDIRILDI - artık LLM ile dinamik üretim yapılıyor
# Eski template bazlı sistem sınırlıydı ve tekrarlı içerik üretiyordu


class OrganicCollector(BaseCollector):
    """
    LLM-powered organik içerik üretici.
    
    Template YOK - tamamen dinamik LLM ile üretim.
    
    Özellikler:
    - LLM ile sınırsız, özgün başlık üretimi
    - uuid4 ile unique ID (çakışma yok)
    - fingerprint ile tekrar engelleme (NPC spam önleme)
    - DB-based günlük kota (restart-safe, multi-worker safe)
    """

    def __init__(self, quota_store: Optional['OrganicQuotaStore'] = None):
        super().__init__("organic")
        self.daily_quota = 10  # Günde max 10 organik konu
        self.quota_store = quota_store or InMemoryQuotaStore()
        self._used_fingerprints: Set[str] = set()

    async def is_duplicate(self, event: Event) -> bool:
        """Fingerprint kontrolü ile tekrar engelleme."""
        if not event.metadata:
            return False
        fingerprint = event.metadata.get("fingerprint")
        if not fingerprint:
            return False
        return fingerprint in self._used_fingerprints

    async def collect(self) -> List[Event]:
        """LLM ile organik konular üret."""
        events = []
        today = date.today()
        
        # Günlük kota kontrolü (DB'den)
        current_count = await self.quota_store.get_daily_count(today)
        if current_count >= self.daily_quota:
            logger.info(f"Günlük organik içerik kotası doldu ({current_count}/{self.daily_quota})")
            return events

        # Son 24 saatteki fingerprint'leri yükle (tekrar engelleme)
        existing_fingerprints = await self.quota_store.get_recent_fingerprints(today)
        self._used_fingerprints.update(existing_fingerprints)

        # Kaç konu üretilecek
        remaining = self.daily_quota - current_count
        count = min(random.randint(1, 3), remaining)
        
        # LLM ile başlıklar üret
        generated_titles = await generate_organic_titles_with_llm(count + 2)  # Extra buffer
        
        for item in generated_titles:
            if len(events) >= count:
                break
                
            title = item.get("title", "")
            category = item.get("category", "meta")
            
            if not title:
                continue
            
            # Fingerprint kontrolü
            fingerprint = generate_fingerprint(title, today)
            if fingerprint in self._used_fingerprints:
                logger.debug(f"Tekrar engellendi: {title[:30]}...")
                continue
            
            # Event oluştur
            event_id = uuid.uuid4()
            event = Event(
                id=event_id,
                source="organic",
                source_id=f"org_{str(event_id)[:8]}",
                title=title,
                description=f"LLM-generated organik içerik: {category}",
                url=None,
                category=category,
                importance_score=random.uniform(0.4, 0.8),
                published_at=datetime.now(),
                collected_at=datetime.now(),
                status=EventStatus.NEW,
                metadata={
                    "organic_category": category,
                    "generation_method": "llm",
                    "fingerprint": fingerprint,
                }
            )
            
            events.append(event)
            self._used_fingerprints.add(fingerprint)
            await self.quota_store.record_generated(today, fingerprint)

        logger.info(f"Organik collector (LLM): {len(events)} konu üretildi (kota: {current_count + len(events)}/{self.daily_quota})")
        return events


# ============ Quota Store Implementations ============

class InMemoryQuotaStore:
    """
    In-memory quota store (development/test için).
    
    NOT: Production'da RedisQuotaStore veya PostgresQuotaStore kullanın.
    Bu implementasyon restart'ta sıfırlanır.
    """
    
    def __init__(self):
        self._counts: dict[date, int] = {}
        self._fingerprints: dict[date, Set[str]] = {}
    
    async def get_daily_count(self, day: date) -> int:
        """Günlük üretilen içerik sayısını döndür."""
        return self._counts.get(day, 0)
    
    async def get_recent_fingerprints(self, day: date) -> Set[str]:
        """Son 24 saatteki fingerprint'leri döndür."""
        return self._fingerprints.get(day, set())
    
    async def record_generated(self, day: date, fingerprint: str):
        """Üretilen içeriği kaydet."""
        if day not in self._counts:
            self._counts[day] = 0
            self._fingerprints[day] = set()
        self._counts[day] += 1
        self._fingerprints[day].add(fingerprint)
        
        # Eski günleri temizle (memory leak önleme)
        self._cleanup_old_days(day)
    
    def _cleanup_old_days(self, current_day: date):
        """3 günden eski verileri temizle."""
        from datetime import timedelta
        cutoff = current_day - timedelta(days=3)
        old_days = [d for d in self._counts.keys() if d < cutoff]
        for d in old_days:
            del self._counts[d]
            if d in self._fingerprints:
                del self._fingerprints[d]


class RedisQuotaStore:
    """
    Redis-based quota store (production için önerilen).
    
    Multi-worker safe, restart-safe.
    """
    
    def __init__(self, redis_client):
        self.redis = redis_client
        self.prefix = "organic_quota"
        self.ttl = 86400 * 3  # 3 gün TTL
    
    async def get_daily_count(self, day: date) -> int:
        """Günlük üretilen içerik sayısını döndür."""
        key = f"{self.prefix}:count:{day.isoformat()}"
        count = await self.redis.get(key)
        return int(count) if count else 0
    
    async def get_recent_fingerprints(self, day: date) -> Set[str]:
        """Son 24 saatteki fingerprint'leri döndür."""
        key = f"{self.prefix}:fps:{day.isoformat()}"
        members = await self.redis.smembers(key)
        return set(members) if members else set()
    
    async def record_generated(self, day: date, fingerprint: str):
        """Üretilen içeriği kaydet."""
        count_key = f"{self.prefix}:count:{day.isoformat()}"
        fp_key = f"{self.prefix}:fps:{day.isoformat()}"
        
        pipe = self.redis.pipeline()
        pipe.incr(count_key)
        pipe.expire(count_key, self.ttl)
        pipe.sadd(fp_key, fingerprint)
        pipe.expire(fp_key, self.ttl)
        await pipe.execute()


class PostgresQuotaStore:
    """
    PostgreSQL-based quota store.
    
    Requires table:
    CREATE TABLE organic_quota (
        day DATE NOT NULL,
        fingerprint VARCHAR(32) NOT NULL,
        created_at TIMESTAMP DEFAULT NOW(),
        PRIMARY KEY (day, fingerprint)
    );
    CREATE INDEX idx_organic_quota_day ON organic_quota(day);
    """
    
    def __init__(self, db_pool):
        self.pool = db_pool
    
    async def get_daily_count(self, day: date) -> int:
        """Günlük üretilen içerik sayısını döndür."""
        async with self.pool.acquire() as conn:
            result = await conn.fetchval(
                "SELECT COUNT(*) FROM organic_quota WHERE day = $1",
                day
            )
            return result or 0
    
    async def get_recent_fingerprints(self, day: date) -> Set[str]:
        """Son 24 saatteki fingerprint'leri döndür."""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT fingerprint FROM organic_quota WHERE day = $1",
                day
            )
            return {row['fingerprint'] for row in rows}
    
    async def record_generated(self, day: date, fingerprint: str):
        """Üretilen içeriği kaydet."""
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO organic_quota (day, fingerprint)
                VALUES ($1, $2)
                ON CONFLICT (day, fingerprint) DO NOTHING
                """,
                day, fingerprint
            )
