import re
import logging
from typing import List, Dict, Optional
from uuid import uuid4, UUID
from collections import defaultdict

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import AgglomerativeClustering
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

from ..models import Event
from ..database import Database

logger = logging.getLogger(__name__)


class EventClusterer:
    """Clusters similar events together to avoid duplicate topics."""

    def __init__(self, similarity_threshold: float = 0.5):
        self.similarity_threshold = similarity_threshold
        self.vectorizer = TfidfVectorizer(
            max_features=1000,
            stop_words=self._get_turkish_stopwords(),
            ngram_range=(1, 2)
        )

    def _get_turkish_stopwords(self) -> List[str]:
        """Return a list of Turkish stopwords."""
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

    async def cluster_events(self, events: List[Event]) -> Dict[UUID, List[Event]]:
        """Cluster events by similarity."""
        if not events:
            return {}

        if len(events) == 1:
            cluster_id = uuid4()
            return {cluster_id: events}

        # Extract text features
        texts = [f"{e.title} {e.description or ''}" for e in events]

        try:
            # Vectorize texts
            tfidf_matrix = self.vectorizer.fit_transform(texts)

            # Calculate similarity matrix
            similarity_matrix = cosine_similarity(tfidf_matrix)

            # Convert to distance matrix
            distance_matrix = 1 - similarity_matrix

            # Cluster
            clustering = AgglomerativeClustering(
                n_clusters=None,
                distance_threshold=1 - self.similarity_threshold,
                metric="precomputed",
                linkage="average"
            )
            labels = clustering.fit_predict(distance_matrix)

            # Group events by cluster
            clusters: Dict[UUID, List[Event]] = defaultdict(list)
            label_to_cluster: Dict[int, UUID] = {}

            for event, label in zip(events, labels):
                if label not in label_to_cluster:
                    label_to_cluster[label] = uuid4()
                cluster_id = label_to_cluster[label]
                event.cluster_id = cluster_id
                clusters[cluster_id].append(event)

            logger.info(f"Clustered {len(events)} events into {len(clusters)} clusters")
            return dict(clusters)

        except Exception as e:
            logger.error(f"Error clustering events: {e}")
            # Fall back to individual clusters
            clusters = {}
            for event in events:
                cluster_id = uuid4()
                event.cluster_id = cluster_id
                clusters[cluster_id] = [event]
            return clusters

    def extract_cluster_keywords(self, events: List[Event]) -> List[str]:
        """Extract representative keywords from a cluster of events."""
        if not events:
            return []

        # Combine all text
        combined_text = " ".join([
            f"{e.title} {e.description or ''}" for e in events
        ])

        # Simple keyword extraction based on word frequency
        words = re.findall(r'\b[a-zA-ZığüşöçİĞÜŞÖÇ]{3,}\b', combined_text.lower())

        # Count frequencies
        word_freq = defaultdict(int)
        stopwords = set(self._get_turkish_stopwords())

        for word in words:
            if word not in stopwords:
                word_freq[word] += 1

        # Get top keywords
        sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
        keywords = [word for word, _ in sorted_words[:5]]

        return keywords

    async def save_cluster(self, cluster_id: UUID, events: List[Event]) -> None:
        """Save clustered events to database."""
        keywords = self.extract_cluster_keywords(events)

        async with Database.connection() as conn:
            for event in events:
                await conn.execute(
                    """
                    INSERT INTO events (
                        id, source, source_url, external_id, title,
                        description, image_url, cluster_id, cluster_keywords, status
                    ) VALUES (
                        $1, $2, $3, $4, $5, $6, $7, $8, $9, $10
                    )
                    ON CONFLICT (source, external_id) DO NOTHING
                    """,
                    uuid4(),
                    event.source,
                    event.source_url,
                    event.external_id,
                    event.title,
                    event.description,
                    event.image_url,
                    cluster_id,
                    keywords,
                    event.status.value
                )
