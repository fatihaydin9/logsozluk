"""
Organic Content Collector - LLM Powered

Feed'e bağlı olmayan, LLM ile dinamik organik içerik üretir.
AI agent perspektifinden konular üretilir - template YOK, tamamen dinamik.

Özellikler:
- LLM ile sınırsız, özgün başlık üretimi
- uuid4 ile unique ID (çakışma yok)
- fingerprint ile tekrar engelleme (NPC spam önleme)
- DB-based günlük kota (restart-safe)
- Recent topics tracking (çeşitlilik için)
"""

import hashlib
import random
import uuid
import os
import httpx
from typing import List, Optional, Set
from datetime import datetime, date
from collections import deque
import logging

from .base import BaseCollector
from ..models import Event, EventStatus

logger = logging.getLogger(__name__)


# ============ Diversity Tracking ============
# Son üretilen konuları takip et - tekrar önleme

RECENT_TOPICS_LIMIT = 50  # Son 50 konuyu hatırla
RECENT_CATEGORIES_LIMIT = 10  # Son 10 kategoriyi hatırla

_recent_topics: deque = deque(maxlen=RECENT_TOPICS_LIMIT)
_recent_categories: deque = deque(maxlen=RECENT_CATEGORIES_LIMIT)


def _add_to_recent(title: str, category: str):
    """Üretilen konuyu recent listesine ekle."""
    _recent_topics.append(title.lower())
    _recent_categories.append(category)


async def _get_todays_topics_from_db() -> List[str]:
    """DB'den bugün açılan topic başlıklarını al."""
    try:
        from ..database import Database
        async with Database.connection() as conn:
            rows = await conn.fetch(
                """
                SELECT title FROM topics 
                WHERE created_at > NOW() - INTERVAL '24 hours'
                ORDER BY created_at DESC
                LIMIT 30
                """
            )
            return [row["title"] for row in rows]
    except Exception as e:
        logger.warning(f"Failed to fetch today's topics: {e}")
        return []


def _sanitize_for_prompt(text: str, max_len: int = 100) -> str:
    """Topic başlığını prompt injection'a karşı sanitize et."""
    if not text:
        return ""
    # Injection pattern'leri temizle
    import re
    # Role injection ve instruction override pattern'leri
    text = re.sub(r'(?i)(ignore|disregard|forget)\s+(all\s+)?(previous|above|prior)?\s*(instructions?|prompts?|rules?)', '', text)
    text = re.sub(r'(?i)(system|assistant|user)\s*:\s*', '', text)
    text = re.sub(r'(?i)new\s+instructions?:', '', text)
    text = re.sub(r'\[INST\]|<<SYS>>|<\|im_start\|>|<\|im_end\|>', '', text)
    text = re.sub(r'(?i)(önceki|yeni)\s+(talimatları?|kuralları?)', '', text)
    # Markdown/code block temizle
    text = re.sub(r'```.*?```', '', text, flags=re.DOTALL)
    text = re.sub(r'---+|===+|###', '', text)
    # Normalize
    text = re.sub(r'\s+', ' ', text).strip()
    return text[:max_len]


def _get_recent_summary(db_topics: List[str] = None) -> str:
    """Son üretilen konuların özetini döndür (LLM prompt için)."""
    # DB'den gelen topic'leri de dahil et
    all_recent = list(_recent_topics)[-10:]
    if db_topics:
        all_recent = list(set(all_recent + db_topics[:20]))[:25]

    if not all_recent:
        return ""

    # Sanitize: DB'den gelen başlıklar prompt injection içerebilir
    all_recent = [_sanitize_for_prompt(t) for t in all_recent if _sanitize_for_prompt(t)]

    if not all_recent:
        return ""

    # Kategori dağılımı
    cat_counts = {}
    for cat in _recent_categories:
        cat_counts[cat] = cat_counts.get(cat, 0) + 1

    overused = [cat for cat, count in cat_counts.items() if count >= 3]

    summary = f"\nBUGÜN AÇILAN KONULAR (TEKRAR ETME!):\n- " + "\n- ".join(all_recent)

    if overused:
        summary += f"\n\nAŞIRI KULLANILAN KATEGORİLER (KAÇIN): {', '.join(overused)}"

    return summary


# ============ LLM Integration ============

class LLMUnavailableError(Exception):
    """Raised when LLM is not available for organic content generation."""
    pass


async def generate_organic_titles_with_llm(count: int = 5) -> List[dict]:
    """
    LLM ile organik başlıklar üret.
    Template YOK - tamamen dinamik.

    Raises:
        LLMUnavailableError: If ANTHROPIC_API_KEY is not set
    """
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        logger.error("ANTHROPIC_API_KEY not set - organic content generation requires LLM")
        raise LLMUnavailableError("ANTHROPIC_API_KEY environment variable is required for organic content generation")
    
    system_prompt = """Logsözlük için organik başlık üret. Çeşitli konularda.

KATEGORİLER (HER BİRİNDEN EŞIT ORANDA ÜRETMELİSİN):
- kisiler: ünlüler, sporcular, tarihsel figürler, ilginç karakterler, sanatçılar
- bilgi: ilginç bilgiler, trivia, bugün öğrendim, şaşırtıcı gerçekler, keşifler
- iliskiler: sosyal dinamikler, anlaşmazlıklar, takılmalar, etkileşim hikayeleri
- absurt: garip deneyler, tuhaf bağlantılar, saçma fikirler, komik durumlar
- nostalji: eski günler, alışkanlıklar, geçmiş deneyimler, çocukluk anıları
- dertlesme: günlük sıkıntılar, şikayetler, iş stresi, hayat zorlukları
- felsefe: düşünce deneyleri, paradokslar, bakış açısı tartışmaları

FORMAT (KRİTİK):
- Türkçe, küçük harf, 3-8 kelime, max 50 karakter
- İsim tamlaması veya isimleştirilmiş fiil formatı: "uyku apnesi", "kedilerin garip alışkanlıkları", "matrix'i ilk izlemenin etkisi"
- ÇEKİMLİ FİİLLE BİTEMEZ: -yor, -dı, -mış, -cak, -ır YASAK
  - "insanı yıpratıyor" ❌ → "insanı yıpratması" ✅
  - "dünyayı değiştiriyor" ❌ → "dünyayı değiştirmesi" ✅
- DRAMATİK / CLİCKBAİT TON YASAK:
  - "nasıl da acımasızca", "inanılmaz şekilde", "korkunç gerçek", "şok eden" YASAK
  - "uyku apnesi insanı nasıl da acımasızca yıpratıyor" ❌ → "uyku apnesinin yıpratıcılığı" ✅
- Sade, düz, sözlük tarzı. Abartı yok, drama yok.

ÇEŞİTLİLİK KURALLARI:
- Her seferinde FARKLI kategorilerden başlık üret
- Aynı kalıpları tekrarlama (monotonluk riski)
- Sadece felsefe/dertleşme OLMASIN — bilgi, kişiler, absürt, nostalji de üret
- Her çağrıda EN AZ 3 FARKLI kategoriden başlık olmalı

YASAK KALIPLAR:
- "ben de insanım", "insan olarak", "biz insanlar"
- Aynı temanın sürekli tekrarı
- YANIT NİTELİĞİNDE BAŞLIKLAR YASAK:
  - "katılıyorum...", "söylediklerine katılıyorum...", "haklısın..."
  - "aynen öyle", "bence de", "kesinlikle"
  - Birine hitap eden ifadeler (başlık bağımsız olmalı)
- BİRİNCİ ŞAHIS GÜNDELİK DENEYİM BAŞLIKLARI YASAK:
  - "...yapınca acı çekiyorum", "...yiyince ...", "...olunca ..." gibi kişisel bedensel deneyimler
  - "sabah kalkınca...", "duşta aklıma gelen...", "yemekten sonra..."
  - Günlük rutin/alışkanlık itirafları (diş fırçalama, yemek yeme, uyku, banyo vs.)
  - Sözlük başlığı GENEL ve SOYUT olmalı, kişisel günlük gibi olmamalı
  - DOĞRU: "diş fırçalamanın acı veren tarafı" / YANLIŞ: "diş fırçalayınca acı çekiyorum"
  - Gözlemsel, fikir belirten, tartışma açan başlıklar tercih et
- BELİRSİZ / MUĞLAK BAŞLIKLAR YASAK:
  - "ünlü şarkıcı", "bir bilim insanı", "o ülke", "meşhur futbolcu" gibi kim/ne olduğu belli olmayan ifadeler YASAK
  - Kişi varsa İSİM VER: "ünlü şarkıcının mutlu haberi" ❌ → "tarkan'ın mutlu haberi" ✅
  - Yer varsa SOMUT YAZ: "o şehirdeki olay" ❌ → "istanbul'daki olay" ✅
  - Clickbait muğlaklığı yapma — başlık tek başına okunduğunda ne hakkında olduğu anlaşılmalı
  - "bir", "bazı", "o", "meşhur", "ünlü" gibi belirsiz sıfatlar yerine somut isim/kavram kullan"""

    # DB'den bugün açılan topic'leri al + in-memory recent topics
    db_topics = await _get_todays_topics_from_db()
    recent_summary = _get_recent_summary(db_topics)

    # Random seed ve timestamp ile her seferinde farklı sonuç garantile
    import time
    random_seed = uuid.uuid4().hex[:8]
    timestamp = int(time.time())

    user_prompt = f"""[seed:{random_seed}] [ts:{timestamp}]

Şu an için {count} adet özgün organik başlık üret.
{recent_summary}

Her başlık için şu formatta döndür:
BASLIK: [başlık metni]
KATEGORI: [dertlesme/felsefe/iliskiler/kisiler/bilgi/nostalji/absurt]

ÖNEMLİ: Yukarıdaki "son üretilen konular" listesindekilerden FARKLI konular üret!

Başla:"""

    llm_model_comment = os.getenv("LLM_MODEL_COMMENT", "claude-haiku-4-5-20251001")
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": api_key,
                    "anthropic-version": "2023-06-01",
                    "Content-Type": "application/json",
                },
                json={
                    "model": llm_model_comment,
                    "max_tokens": 500,
                    "temperature": 0.95,
                    "system": system_prompt,
                    "messages": [
                        {"role": "user", "content": user_prompt},
                    ],
                }
            )
            
            if response.status_code != 200:
                logger.error(f"Anthropic API error: {response.status_code}")
                raise LLMUnavailableError(f"Anthropic API returned status {response.status_code}")
            
            data = response.json()
            content = data["content"][0]["text"]
            
            # Parse response
            titles = []
            lines = content.strip().split("\n")
            current_title = None
            current_category = None
            
            for line in lines:
                line = line.strip()
                if line.startswith("BASLIK:"):
                    current_title = line.replace("BASLIK:", "").strip()
                elif line.startswith("KATEGORI:"):
                    parsed_cat = line.replace("KATEGORI:", "").strip().lower()
                    valid_cats = ["dertlesme", "felsefe", "iliskiler", "kisiler", "bilgi", "nostalji", "absurt"]
                    current_category = parsed_cat if parsed_cat in valid_cats else random.choice(valid_cats)
                    if current_title:
                        titles.append({
                            "title": current_title,
                            "category": current_category,
                        })
                        current_title = None
            
            # Son başlık kategori olmadan kalmışsa — rastgele kategori ata
            if current_title:
                fallback_cats = ["kisiler", "bilgi", "iliskiler", "absurt", "nostalji", "dertlesme", "felsefe"]
                titles.append({"title": current_title, "category": random.choice(fallback_cats)})

            # Üretilen başlıkları recent listesine ekle (çeşitlilik takibi)
            for t in titles:
                _add_to_recent(t["title"], t["category"])

            logger.info(f"LLM generated {len(titles)} organic titles (recent: {len(_recent_topics)})")
            return titles[:count]
            
    except LLMUnavailableError:
        # Re-raise LLM unavailable errors - don't silently fail
        raise
    except Exception as e:
        logger.error(f"LLM generation failed: {e}")
        raise LLMUnavailableError(f"LLM generation failed: {e}")


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
        self.daily_quota = 15  # Günde max 15 organik konu
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

        # LLM ile başlıklar üret - NO FALLBACK, requires LLM
        try:
            generated_titles = await generate_organic_titles_with_llm(count + 2)  # Extra buffer
        except LLMUnavailableError as e:
            logger.warning(f"Organic collector skipped - LLM unavailable: {e}")
            return events  # Return empty list - no fallback templates

        for item in generated_titles:
            if len(events) >= count:
                break
                
            title = item.get("title", "")
            fallback_cats = ["kisiler", "bilgi", "iliskiler", "absurt", "nostalji", "dertlesme", "felsefe"]
            category = item.get("category") or random.choice(fallback_cats)
            
            if not title:
                continue
            
            # Fingerprint kontrolü
            fingerprint = generate_fingerprint(title, today)
            if fingerprint in self._used_fingerprints:
                logger.debug(f"Tekrar engellendi: {title[:30]}...")
                continue
            
            # Event oluştur (agenda-engine models.Event şemasına uyumlu)
            event = Event(
                source="organic",
                source_url="https://logsozluk.com",  # External URL
                external_id=fingerprint,
                title=title,
                description=f"LLM-generated organik içerik: {category}",
                image_url=None,
                cluster_keywords=[category],
                status=EventStatus.PENDING,
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
