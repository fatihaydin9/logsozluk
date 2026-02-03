"""
Duplicate Detection & Topic Similarity Sistemi

Aynı konu hakkında tekrar topic açılmasını önler.
Benzer başlıkları tespit edip gruplar.
"""

import re
import hashlib
from typing import List, Set, Optional, Dict, Tuple
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


# Türkçe stop words - karşılaştırmada göz ardı edilecek
STOP_WORDS = {
    "bir", "bu", "şu", "o", "ve", "ile", "için", "de", "da", "den", "dan",
    "mi", "mı", "mu", "mü", "ne", "nasıl", "neden", "ama", "fakat", "ancak",
    "gibi", "kadar", "daha", "en", "çok", "az", "her", "bazı", "tüm", "bütün",
    "olan", "olarak", "ise", "ki", "ya", "veya", "hem", "artık", "hala", "henüz",
    "sadece", "yalnızca", "bile", "çünkü", "zira", "eğer", "şayet", "madem",
    "yani", "mesela", "örneğin", "ayrıca", "üstelik", "dahası", "hatta",
    "sonra", "önce", "şimdi", "bugün", "dün", "yarın", "haber", "son", "dakika",
}

# Benzerlik eşiği (0-1 arası, 1 = tamamen aynı)
SIMILARITY_THRESHOLD = 0.85


class TopicDeduplicator:
    """Topic duplicate detection ve benzerlik kontrolü."""

    def __init__(self, redis_client=None):
        self.redis = redis_client
        self._local_cache: Dict[str, datetime] = {}
        self._cache_ttl = timedelta(hours=24)

    def normalize_title(self, title: str) -> str:
        """Başlığı normalize et."""
        # Küçük harf
        text = title.lower()
        
        # Türkçe karakterleri normalize et
        tr_map = str.maketrans("çğıöşüÇĞİÖŞÜ", "cgiosuCGIOSU")
        text = text.translate(tr_map)
        
        # Özel karakterleri kaldır
        text = re.sub(r'[^\w\s]', ' ', text)
        
        # Stop words'leri kaldır
        words = text.split()
        words = [w for w in words if w not in STOP_WORDS and len(w) > 2]
        
        return ' '.join(words)

    def get_keywords(self, title: str) -> Set[str]:
        """Başlıktan anahtar kelimeleri çıkar."""
        normalized = self.normalize_title(title)
        return set(normalized.split())

    def calculate_similarity(self, title1: str, title2: str) -> float:
        """İki başlık arasındaki benzerliği hesapla (Jaccard)."""
        kw1 = self.get_keywords(title1)
        kw2 = self.get_keywords(title2)
        
        if not kw1 or not kw2:
            return 0.0
        
        intersection = kw1 & kw2
        union = kw1 | kw2
        
        return len(intersection) / len(union)

    def get_title_hash(self, title: str) -> str:
        """Başlık için hash oluştur."""
        normalized = self.normalize_title(title)
        return hashlib.md5(normalized.encode()).hexdigest()[:12]

    async def is_duplicate(self, title: str, category: str, db_conn=None) -> Tuple[bool, Optional[str]]:
        """
        Başlığın duplicate olup olmadığını kontrol et.
        
        instructionset.md: Bir başlık bir kez açıldıysa, ASLA tekrar açılamaz.
        - slug kontrolü
        - semantic similarity check (>0.85 = duplicate)
        
        Returns:
            (is_duplicate, similar_title)
        """
        title_hash = self.get_title_hash(title)
        cache_key = f"topic:{category}:{title_hash}"
        
        # Redis kontrolü
        if self.redis:
            existing = await self.redis.get(cache_key)
            if existing:
                return True, existing.decode() if isinstance(existing, bytes) else existing
        
        # Local cache kontrolü
        if cache_key in self._local_cache:
            if datetime.now() - self._local_cache[cache_key] < self._cache_ttl:
                return True, title
        
        # Veritabanı kontrolü (instructionset.md gereksinimi)
        if db_conn:
            try:
                # Slug kontrolü
                slug = self._generate_slug(title)
                existing_slug = await db_conn.fetchval(
                    "SELECT title FROM topics WHERE slug = $1 LIMIT 1",
                    slug
                )
                if existing_slug:
                    return True, existing_slug
                
                # Son 30 günün topic'lerinde benzerlik kontrolü
                # Not: Slug kontrolü zaten süresiz, bu sadece semantic similarity için
                recent_titles = await db_conn.fetch(
                    """
                    SELECT title FROM topics
                    WHERE created_at > NOW() - INTERVAL '30 days'
                    AND category = $1
                    ORDER BY created_at DESC
                    LIMIT 200
                    """,
                    category
                )
                
                for row in recent_titles:
                    similarity = self.calculate_similarity(title, row['title'])
                    if similarity >= SIMILARITY_THRESHOLD:
                        return True, row['title']
                        
            except Exception as e:
                logger.warning(f"DB duplicate check failed: {e}")
        
        return False, None
    
    def _generate_slug(self, title: str) -> str:
        """Başlıktan slug oluştur."""
        import re
        slug = title.lower()
        # Türkçe karakterleri dönüştür
        tr_map = str.maketrans("çğıöşüÇĞİÖŞÜ", "cgiosuCGIOSU")
        slug = slug.translate(tr_map)
        # Özel karakterleri kaldır
        slug = re.sub(r'[^a-z0-9\s-]', '', slug)
        # Boşlukları tire yap
        slug = re.sub(r'\s+', '-', slug.strip())
        return slug[:100]  # Max 100 karakter

    async def check_similarity_batch(
        self, 
        new_title: str, 
        existing_titles: List[str]
    ) -> List[Tuple[str, float]]:
        """Yeni başlığı mevcut başlıklarla karşılaştır."""
        similar = []
        
        for existing in existing_titles:
            score = self.calculate_similarity(new_title, existing)
            if score >= SIMILARITY_THRESHOLD:
                similar.append((existing, score))
        
        return sorted(similar, key=lambda x: x[1], reverse=True)

    async def mark_as_used(self, title: str, category: str):
        """Başlığı kullanıldı olarak işaretle."""
        title_hash = self.get_title_hash(title)
        cache_key = f"topic:{category}:{title_hash}"
        
        # Redis'e kaydet (24 saat TTL)
        if self.redis:
            await self.redis.setex(cache_key, 86400, title)
        
        # Local cache
        self._local_cache[cache_key] = datetime.now()

    async def filter_duplicates(
        self, 
        events: List[dict],
        category: str = None
    ) -> List[dict]:
        """Event listesinden duplicate'leri filtrele."""
        filtered = []
        seen_hashes = set()
        
        for event in events:
            title = event.get("title", "")
            cat = category or event.get("category", "general")
            
            # Hash kontrolü
            title_hash = self.get_title_hash(title)
            if title_hash in seen_hashes:
                logger.debug(f"Duplicate (hash): {title[:50]}")
                continue
            
            # Önceden kullanılmış mı?
            is_dup, similar = await self.is_duplicate(title, cat)
            if is_dup:
                logger.debug(f"Duplicate (cache): {title[:50]} ~ {similar[:50] if similar else ''}")
                continue
            
            # Benzerlik kontrolü (batch içinde)
            similar_in_batch = await self.check_similarity_batch(
                title, 
                [e.get("title", "") for e in filtered]
            )
            
            if similar_in_batch:
                best_match, score = similar_in_batch[0]
                logger.debug(f"Similar ({score:.2f}): {title[:30]} ~ {best_match[:30]}")
                continue
            
            seen_hashes.add(title_hash)
            filtered.append(event)
        
        logger.info(f"Dedup: {len(events)} -> {len(filtered)} events ({len(events) - len(filtered)} removed)")
        return filtered

    def cleanup_old_cache(self):
        """Eski cache girdilerini temizle."""
        now = datetime.now()
        expired = [k for k, v in self._local_cache.items() if now - v > self._cache_ttl]
        for k in expired:
            del self._local_cache[k]
        
        if expired:
            logger.info(f"Cleaned up {len(expired)} expired cache entries")
