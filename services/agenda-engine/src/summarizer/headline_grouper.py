"""
Headline Grouper - Benzer haberleri kategori ve semantic similarity ile grupla.
"""
import logging
from dataclasses import dataclass, field
from typing import List, Dict
from collections import defaultdict

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import AgglomerativeClustering
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

from ..models import Event
from ..categories import GUNDEM_CATEGORIES, CATEGORY_EN_TO_TR

logger = logging.getLogger(__name__)


@dataclass
class HeadlineGroup:
    """Gruplanmış haber başlıkları."""
    category: str  # Türkçe kategori key (ekonomi, siyaset, etc.)
    category_label: str  # Görünen isim (Ekonomi, Siyaset, etc.)
    headlines: List[Dict] = field(default_factory=list)  # [{title, description, source, url}]
    sources: List[str] = field(default_factory=list)  # Unique source names
    summary: str = ""  # LLM tarafından üretilecek özet


class HeadlineGrouper:
    """Haberleri kategori ve benzerlik bazlı grupla."""

    def __init__(self, similarity_threshold: float = 0.4):
        self.similarity_threshold = similarity_threshold
        self.vectorizer = TfidfVectorizer(
            max_features=500,
            stop_words=self._get_turkish_stopwords(),
            ngram_range=(1, 2)
        )

    def _get_turkish_stopwords(self) -> List[str]:
        """Türkçe stop words listesi."""
        return [
            "ve", "ile", "bir", "bu", "da", "de", "mi", "mu", "ne", "ki",
            "ama", "ancak", "fakat", "lakin", "oysa", "halbuki", "oysaki",
            "icin", "diye", "gibi", "kadar", "gore", "dolayi", "uzerine",
            "her", "tum", "butun", "hep", "bazi", "kimi", "cogu", "herkes",
            "o", "su", "sen", "ben", "biz", "siz", "onlar", "bunlar", "sunlar",
            "olan", "olarak", "oldu", "olmak", "olmus", "olacak",
            "daha", "cok", "az", "en", "pek", "gayet", "oldukca",
            "ise", "ya", "yahut", "veya", "hem", "ne", "nasil", "neden", "niye"
        ]

    def _get_event_category(self, event: Event) -> str:
        """Event'in Türkçe kategori key'ini döndür."""
        # cluster_keywords ilk eleman genelde kategori
        if event.cluster_keywords:
            cat = event.cluster_keywords[0]
            # Türkçe key mi kontrol et
            if cat in GUNDEM_CATEGORIES:
                return cat
            # İngilizce ise çevir
            if cat in CATEGORY_EN_TO_TR:
                return CATEGORY_EN_TO_TR[cat]

        # Metadata'dan bak
        if event.metadata:
            feed_cat = event.metadata.get("feed_category", "")
            if feed_cat in GUNDEM_CATEGORIES:
                return feed_cat
            if feed_cat in CATEGORY_EN_TO_TR:
                return CATEGORY_EN_TO_TR[feed_cat]

        return "dunya"  # Fallback

    async def group_by_category(self, events: List[Event]) -> Dict[str, HeadlineGroup]:
        """Event'leri sadece kategoriye göre grupla."""
        groups: Dict[str, HeadlineGroup] = {}

        for event in events:
            cat_key = self._get_event_category(event)
            cat_label = GUNDEM_CATEGORIES.get(cat_key, {}).get("label", cat_key.title())

            if cat_key not in groups:
                groups[cat_key] = HeadlineGroup(
                    category=cat_key,
                    category_label=cat_label,
                    headlines=[],
                    sources=[]
                )

            groups[cat_key].headlines.append({
                "title": event.title,
                "description": event.description or "",
                "source": event.source,
                "url": event.source_url
            })

            if event.source not in groups[cat_key].sources:
                groups[cat_key].sources.append(event.source)

        logger.info(f"Kategoriye göre gruplama: {len(events)} event -> {len(groups)} grup")
        return groups

    async def group_by_category_and_similarity(
        self, events: List[Event]
    ) -> Dict[str, HeadlineGroup]:
        """
        Event'leri önce kategoriye, sonra benzerliğe göre grupla.
        Her kategori içinde benzer haberler tek grup olur.
        """
        # Önce kategoriye göre grupla
        category_groups = await self.group_by_category(events)

        # Her kategori içinde benzer haberleri birleştir
        final_groups: Dict[str, HeadlineGroup] = {}

        for cat_key, group in category_groups.items():
            if len(group.headlines) <= 2:
                # Az haber varsa birleştirme yapma
                final_groups[cat_key] = group
                continue

            # Kategori içi clustering
            clustered = self._cluster_headlines(group.headlines)

            # En büyük cluster'ı al (ana haber grubu)
            if clustered:
                largest_cluster = max(clustered, key=lambda x: len(x))
                sources = list(set(h["source"] for h in largest_cluster))

                final_groups[cat_key] = HeadlineGroup(
                    category=cat_key,
                    category_label=group.category_label,
                    headlines=largest_cluster,
                    sources=sources
                )

                # Diğer cluster'ları da ekle (farklı alt konular)
                for i, cluster in enumerate(clustered):
                    if cluster != largest_cluster and len(cluster) >= 2:
                        sub_key = f"{cat_key}_{i}"
                        sub_sources = list(set(h["source"] for h in cluster))
                        final_groups[sub_key] = HeadlineGroup(
                            category=cat_key,
                            category_label=group.category_label,
                            headlines=cluster,
                            sources=sub_sources
                        )
            else:
                final_groups[cat_key] = group

        logger.info(f"Benzerlik gruplaması: {len(category_groups)} kategori -> {len(final_groups)} grup")
        return final_groups

    def _cluster_headlines(self, headlines: List[Dict]) -> List[List[Dict]]:
        """Başlıkları semantic similarity ile grupla."""
        if len(headlines) < 2:
            return [headlines]

        try:
            # Text'leri çıkar
            texts = [f"{h['title']} {h['description']}" for h in headlines]

            # TF-IDF vektörize
            tfidf_matrix = self.vectorizer.fit_transform(texts)

            # Cosine similarity
            similarity_matrix = cosine_similarity(tfidf_matrix)
            distance_matrix = 1 - similarity_matrix

            # Hierarchical clustering
            clustering = AgglomerativeClustering(
                n_clusters=None,
                distance_threshold=1 - self.similarity_threshold,
                metric="precomputed",
                linkage="average"
            )
            labels = clustering.fit_predict(distance_matrix)

            # Cluster'lara ayır
            clusters: Dict[int, List[Dict]] = defaultdict(list)
            for headline, label in zip(headlines, labels):
                clusters[label].append(headline)

            return list(clusters.values())

        except Exception as e:
            logger.warning(f"Clustering hatası: {e}, tek grup döndürülüyor")
            return [headlines]
