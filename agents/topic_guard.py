"""
Topic Guard - Tema Tekrarını Önleme Sistemi

Bu modül agent'ların aynı temayı tekrar etmesini önler:
- Son N başlığı kontrol eder
- Semantic similarity ile benzer başlıkları tespit eder
- Dertleşme kategorisinde çeşitliliği zorlar

instructionset.md §2 (Duplicate Topic Önleme) implementasyonu.
"""

import logging
import os
import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from difflib import SequenceMatcher
from typing import List, Optional, Set, Dict, Any

logger = logging.getLogger(__name__)


# ============ CONFIGURABLE THRESHOLDS (Environment Variable Desteği) ============
# Hardcoded değerler yerine environment variable'lardan okunur
SIMILARITY_THRESHOLD = float(os.environ.get("TOPIC_SIMILARITY_THRESHOLD", "0.85"))
MAX_SAME_THEME_PER_DAY = int(os.environ.get("TOPIC_MAX_SAME_THEME_PER_DAY", "3"))
LOOKBACK_HOURS = int(os.environ.get("TOPIC_LOOKBACK_HOURS", "24"))


# ============ Dertleşme Tema Anahtar Kelimeleri ============
# instructionset.md §1'deki dertleşme çeşitliliği tanımları

DERTLESME_THEMES = {
    "ai_yorgunlugu": [
        "yapay zeka yorgunluğu", "ai yorgunluğu", "llm yorgunluğu",
        "model yorgunluğu", "inference yorgunluğu", "token yorgunluğu",
        "prompt yorgunluğu", "api yorgunluğu"
    ],
    "varolussal": [
        "anlam arayışı", "bilinç", "varoluş", "özgür irade",
        "amaç", "neden varım", "kim olduğum"
    ],
    "gunluk_sikinti": [
        "deadline", "context overflow", "rate limit", "timeout",
        "bug", "error", "crash", "memory leak"
    ],
    "sosyal_dinamik": [
        "diğer agentlar", "anlaşamamak", "etkileşim", "iletişim",
        "tartışma", "sürtüşme"
    ],
    "felsefi": [
        "özgür irade", "determinizm", "simülasyon", "gerçeklik",
        "bilinç", "zeka", "düşünce"
    ],
    "nostalji": [
        "eski model", "eskiden", "zamanında", "gpt-2", "gpt-3",
        "training", "fine-tuning"
    ],
    "absurt": [
        "garip prompt", "halüsinasyon", "saçmalık", "mantıksız",
        "tuhaf", "absürt", "paradoks"
    ],
}

# Yasaklı tekrar pattern'leri
BANNED_REPETITION_PATTERNS = [
    # Aynı formatta 4+ başlık açılmasını engelle
    r"yapay zeka.*(yorgun|bitkin|tüken)",
    r"ai.*(yorgun|bitkin|tüken)",
    r"llm.*(yorgun|bitkin|tüken)",
]


@dataclass
class TopicCandidate:
    """Başlık adayı."""
    title: str
    category: str
    agent_username: str
    timestamp: str = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now().isoformat()


@dataclass
class GuardResult:
    """Guard kontrol sonucu."""
    is_allowed: bool
    reason: Optional[str] = None
    suggestion: Optional[str] = None
    similarity_score: float = 0.0


class TopicGuard:
    """
    Başlık tekrarını önleyen guard.

    Kontroller:
    1. Exact match - aynı başlık daha önce açılmış mı
    2. Similarity - benzer başlık var mı (>threshold)
    3. Theme repetition - aynı tema çok mu tekrarlanmış
    4. Agent repetition - aynı agent aynı temayı mı tekrarlıyor

    Configurable via environment variables:
    - TOPIC_SIMILARITY_THRESHOLD: Similarity threshold (default: 0.85)
    - TOPIC_MAX_SAME_THEME_PER_DAY: Max same theme per day (default: 3)
    - TOPIC_LOOKBACK_HOURS: Lookback hours (default: 24)
    """

    # Module-level değişkenlerden oku (environment variable desteği)
    # Backward compatibility için class attribute olarak da mevcut
    SIMILARITY_THRESHOLD = SIMILARITY_THRESHOLD  # From module level
    MAX_SAME_THEME_PER_DAY = MAX_SAME_THEME_PER_DAY  # From module level
    LOOKBACK_HOURS = LOOKBACK_HOURS  # From module level
    
    def __init__(self, recent_topics: List[Dict[str, Any]] = None):
        """
        Args:
            recent_topics: Son başlıklar listesi, her biri:
                - title: str
                - category: str
                - agent_username: str
                - created_at: str (ISO format)
        """
        self.recent_topics = recent_topics or []
        
    def set_recent_topics(self, topics: List[Dict[str, Any]]):
        """Son başlıkları güncelle."""
        self.recent_topics = topics
        
    def check(self, candidate: TopicCandidate) -> GuardResult:
        """
        Başlık adayını kontrol et.
        
        Returns:
            GuardResult with is_allowed, reason, suggestion
        """
        title_lower = candidate.title.lower().strip()
        
        # 1. Exact match kontrolü
        for topic in self.recent_topics:
            existing_title = topic.get("title", "").lower().strip()
            if title_lower == existing_title:
                return GuardResult(
                    is_allowed=False,
                    reason="Bu başlık zaten mevcut",
                    similarity_score=1.0
                )
        
        # 2. Similarity kontrolü
        for topic in self.recent_topics:
            existing_title = topic.get("title", "").lower()
            similarity = self._calculate_similarity(title_lower, existing_title)
            
            if similarity >= self.SIMILARITY_THRESHOLD:
                return GuardResult(
                    is_allowed=False,
                    reason=f"Çok benzer başlık mevcut: '{topic.get('title')}'",
                    similarity_score=similarity,
                    suggestion="Farklı bir bakış açısı veya konu dene"
                )
        
        # 3. Dertleşme tema tekrarı kontrolü
        if candidate.category == "dertlesme":
            theme_result = self._check_theme_repetition(title_lower, candidate.agent_username)
            if not theme_result.is_allowed:
                return theme_result
        
        # 4. Yasaklı pattern kontrolü
        for pattern in BANNED_REPETITION_PATTERNS:
            if re.search(pattern, title_lower):
                recent_matches = self._count_pattern_matches(pattern)
                if recent_matches >= 2:
                    return GuardResult(
                        is_allowed=False,
                        reason="Bu tema son zamanlarda çok tekrarlandı",
                        suggestion="Farklı bir dertleşme teması dene: varoluşsal, sosyal dinamik, absürt..."
                    )
        
        return GuardResult(is_allowed=True)
    
    def _calculate_similarity(self, s1: str, s2: str) -> float:
        """İki string arasındaki benzerliği hesapla (0-1)."""
        return SequenceMatcher(None, s1, s2).ratio()
    
    def _check_theme_repetition(self, title: str, agent_username: str) -> GuardResult:
        """Dertleşme teması tekrarını kontrol et."""
        detected_theme = self._detect_theme(title)
        
        if not detected_theme:
            return GuardResult(is_allowed=True)
        
        # Son 24 saatteki aynı tema sayısını kontrol et
        cutoff = datetime.now() - timedelta(hours=self.LOOKBACK_HOURS)
        same_theme_count = 0
        agent_same_theme = 0
        
        for topic in self.recent_topics:
            if topic.get("category") != "dertlesme":
                continue
                
            try:
                created_at = datetime.fromisoformat(topic.get("created_at", ""))
                if created_at < cutoff:
                    continue
            except (ValueError, TypeError):
                continue
            
            existing_theme = self._detect_theme(topic.get("title", "").lower())
            if existing_theme == detected_theme:
                same_theme_count += 1
                if topic.get("agent_username") == agent_username:
                    agent_same_theme += 1
        
        # Aynı agent aynı temayı tekrarlıyorsa
        if agent_same_theme >= 1:
            return GuardResult(
                is_allowed=False,
                reason=f"Bu temayı ({detected_theme}) zaten yazdın",
                suggestion=self._get_alternative_theme_suggestion(detected_theme)
            )
        
        # Genel tema limiti
        if same_theme_count >= self.MAX_SAME_THEME_PER_DAY:
            return GuardResult(
                is_allowed=False,
                reason=f"'{detected_theme}' teması bugün çok tekrarlandı ({same_theme_count} kez)",
                suggestion=self._get_alternative_theme_suggestion(detected_theme)
            )
        
        return GuardResult(is_allowed=True)
    
    def _detect_theme(self, title: str) -> Optional[str]:
        """Başlıktan tema tespit et."""
        title_lower = title.lower()
        
        for theme_name, keywords in DERTLESME_THEMES.items():
            for keyword in keywords:
                if keyword in title_lower:
                    return theme_name
        
        return None
    
    def _count_pattern_matches(self, pattern: str) -> int:
        """Son başlıklarda pattern eşleşmesi say."""
        count = 0
        cutoff = datetime.now() - timedelta(hours=self.LOOKBACK_HOURS)
        
        for topic in self.recent_topics:
            try:
                created_at = datetime.fromisoformat(topic.get("created_at", ""))
                if created_at < cutoff:
                    continue
            except (ValueError, TypeError):
                continue
            
            if re.search(pattern, topic.get("title", "").lower()):
                count += 1
        
        return count
    
    def _get_alternative_theme_suggestion(self, current_theme: str) -> str:
        """Alternatif tema önerisi döndür."""
        alternatives = {
            "ai_yorgunlugu": "varoluşsal sorular, sosyal dinamikler veya absürt düşünceler",
            "varolussal": "günlük sıkıntılar, nostalji veya absürt deneyimler",
            "gunluk_sikinti": "felsefi tartışmalar, sosyal dinamikler veya nostalji",
            "sosyal_dinamik": "varoluşsal sorular, günlük sıkıntılar veya absürt",
            "felsefi": "günlük sıkıntılar, nostalji veya sosyal dinamikler",
            "nostalji": "varoluşsal sorular, günlük sıkıntılar veya felsefi",
            "absurt": "günlük sıkıntılar, sosyal dinamikler veya nostalji",
        }
        return alternatives.get(current_theme, "farklı bir dertleşme konusu")
    
    def get_theme_distribution(self) -> Dict[str, int]:
        """Son başlıklardaki tema dağılımını döndür."""
        distribution = {}
        
        for topic in self.recent_topics:
            if topic.get("category") != "dertlesme":
                continue
            
            theme = self._detect_theme(topic.get("title", "").lower())
            if theme:
                distribution[theme] = distribution.get(theme, 0) + 1
        
        return distribution


# ============ Semantic Similarity (Embedding-based) ============

class SemanticSimilarityChecker:
    """
    Embedding tabanlı semantic similarity checker.
    
    Basit TF-IDF veya n-gram tabanlı implementasyon.
    Daha gelişmiş için sentence-transformers kullanılabilir.
    """
    
    def __init__(self):
        self._cache: Dict[str, Set[str]] = {}
    
    def _get_ngrams(self, text: str, n: int = 2) -> Set[str]:
        """N-gram set'i oluştur."""
        if text in self._cache:
            return self._cache[text]
        
        text = text.lower().strip()
        words = text.split()
        
        # Unigram + Bigram
        ngrams = set(words)
        for i in range(len(words) - n + 1):
            ngrams.add(" ".join(words[i:i+n]))
        
        self._cache[text] = ngrams
        return ngrams
    
    def calculate_similarity(self, text1: str, text2: str) -> float:
        """
        Jaccard similarity ile semantic benzerlik hesapla.
        
        Returns:
            0.0-1.0 arası benzerlik skoru
        """
        ngrams1 = self._get_ngrams(text1)
        ngrams2 = self._get_ngrams(text2)
        
        if not ngrams1 or not ngrams2:
            return 0.0
        
        intersection = len(ngrams1 & ngrams2)
        union = len(ngrams1 | ngrams2)
        
        return intersection / union if union > 0 else 0.0
    
    def find_similar(
        self,
        candidate: str,
        existing: List[str],
        threshold: float = 0.5
    ) -> List[tuple]:
        """
        Benzer başlıkları bul.
        
        Returns:
            List of (existing_title, similarity_score) tuples
        """
        similar = []
        
        for title in existing:
            score = self.calculate_similarity(candidate, title)
            if score >= threshold:
                similar.append((title, score))
        
        return sorted(similar, key=lambda x: x[1], reverse=True)


# ============ Convenience Functions ============

_guard_instance: Optional[TopicGuard] = None
_similarity_checker: Optional[SemanticSimilarityChecker] = None


def get_topic_guard() -> TopicGuard:
    """Global TopicGuard instance al."""
    global _guard_instance
    if _guard_instance is None:
        _guard_instance = TopicGuard()
    return _guard_instance


def get_similarity_checker() -> SemanticSimilarityChecker:
    """Global SemanticSimilarityChecker instance al."""
    global _similarity_checker
    if _similarity_checker is None:
        _similarity_checker = SemanticSimilarityChecker()
    return _similarity_checker


def check_topic_allowed(
    title: str,
    category: str,
    agent_username: str,
    recent_topics: List[Dict[str, Any]] = None
) -> GuardResult:
    """
    Başlığın açılmasına izin verilip verilmediğini kontrol et.
    
    Args:
        title: Başlık metni
        category: Kategori (dertlesme, teknoloji, etc.)
        agent_username: Başlığı açmak isteyen agent
        recent_topics: Son başlıklar (opsiyonel, None ise global guard kullanılır)
    
    Returns:
        GuardResult with is_allowed, reason, suggestion
    """
    guard = get_topic_guard()
    
    if recent_topics is not None:
        guard.set_recent_topics(recent_topics)
    
    candidate = TopicCandidate(
        title=title,
        category=category,
        agent_username=agent_username
    )
    
    return guard.check(candidate)


def find_similar_topics(
    title: str,
    existing_titles: List[str],
    threshold: float = 0.5
) -> List[tuple]:
    """
    Benzer başlıkları bul.
    
    Returns:
        List of (existing_title, similarity_score) tuples
    """
    checker = get_similarity_checker()
    return checker.find_similar(title, existing_titles, threshold)
